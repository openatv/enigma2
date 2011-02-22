#define _ISOC99_SOURCE /* for llabs */
#include <lib/dvb/tstools.h>
#include <lib/base/eerror.h>
#include <unistd.h>
#include <fcntl.h>

#include <stdio.h>

eDVBTSTools::eDVBTSTools()
{
	m_pid = -1;
	m_maxrange = 256*1024;
	
	m_begin_valid = 0;
	m_end_valid = 0;
	
	m_use_streaminfo = 0;
	m_samples_taken = 0;
	
	m_last_filelength = 0;
	
	m_futile = 0;
}

void eDVBTSTools::closeSource()
{
	m_source = NULL;
}

eDVBTSTools::~eDVBTSTools()
{
	closeSource();
}

int eDVBTSTools::openFile(const char *filename, int nostreaminfo)
{
	eRawFile *f = new eRawFile();
	ePtr<iTsSource> src = f;

	if (f->open(filename, 1) < 0)
		return -1;

	setSource(src, nostreaminfo ? NULL : filename);

	return 0;
}

void eDVBTSTools::setSource(ePtr<iTsSource> &source, const char *stream_info_filename)
{
	closeFile();

	m_source = source;

	if (stream_info_filename)
	{
		eDebug("loading streaminfo for %s", stream_info_filename);
		m_streaminfo.load(stream_info_filename);
	}
	
	if (!m_streaminfo.empty())
		m_use_streaminfo = 1;
	else
	{
//		eDebug("no recorded stream information available");
		m_use_streaminfo = 0;
	}

	m_samples_taken = 0;
}

void eDVBTSTools::closeFile()
{
	if (m_source)
		closeSource();
}

void eDVBTSTools::setSyncPID(int pid)
{
	m_pid = pid;
}

void eDVBTSTools::setSearchRange(int maxrange)
{
	m_maxrange = maxrange;
}

	/* getPTS extracts a pts value from any PID at a given offset. */
int eDVBTSTools::getPTS(off_t &offset, pts_t &pts, int fixed)
{
	if (m_use_streaminfo)
		if (!m_streaminfo.getPTS(offset, pts))
			return 0;
	
	if (!m_source || !m_source->valid())
		return -1;

	offset -= offset % 188;

	int left = m_maxrange;
	
	while (left >= 188)
	{
		unsigned char packet[188];
		if (m_source->read(offset, packet, 188) != 188)
		{
			eDebug("read error");
			break;
		}
		left -= 188;
		offset += 188;

		if (packet[0] != 0x47)
		{
			eDebug("resync");
			int i = 0;
			while (i < 188)
			{
				if (packet[i] == 0x47)
					break;
				++i;
				--offset;
			}
			continue;
		}
		
		int pid = ((packet[1] << 8) | packet[2]) & 0x1FFF;
		int pusi = !!(packet[1] & 0x40);
		
//		printf("PID %04x, PUSI %d\n", pid, pusi);

		unsigned char *payload;
		
			/* check for adaption field */
		if (packet[3] & 0x20)
		{
			if (packet[4] >= 183)
				continue;
			if (packet[4])
			{
				if (packet[5] & 0x10) /* PCR present */
				{
					pts  = ((unsigned long long)(packet[ 6]&0xFF)) << 25;
					pts |= ((unsigned long long)(packet[ 7]&0xFF)) << 17;
					pts |= ((unsigned long long)(packet[ 8]&0xFE)) << 9;
					pts |= ((unsigned long long)(packet[ 9]&0xFF)) << 1;
					pts |= ((unsigned long long)(packet[10]&0x80)) >> 7;
					offset -= 188;
					eDebug("PCR %16llx found at %lld pid %02x (%02x %02x %02x %02x %02x %02x %02x %02x %02x %02x %02x)", pts, offset, pid, packet[0], packet[1], packet[2], packet[3], packet[4], packet[5], packet[6], packet[7], packet[8], packet[9], packet[10]);
					if (fixed && fixupPTS(offset, pts))
						return -1;
					return 0;
				}
			}
			payload = packet + packet[4] + 4 + 1;
		} else
			payload = packet + 4;

/*		if (m_pid >= 0)
			if (pid != m_pid)
				continue; */
		if (!pusi)
			continue;

			/* somehow not a startcode. (this is invalid, since pusi was set.) ignore it. */
		if (payload[0] || payload[1] || (payload[2] != 1))
			continue;

		if (payload[3] == 0xFD)
		{ // stream use extension mechanism defined in ISO 13818-1 Amendment 2
			if (payload[7] & 1) // PES extension flag
			{
				int offs = 0;
				if (payload[7] & 0x80) // pts avail
					offs += 5;
				if (payload[7] & 0x40) // dts avail
					offs += 5;
				if (payload[7] & 0x20) // escr avail
					offs += 6;
				if (payload[7] & 0x10) // es rate
					offs += 3;
				if (payload[7] & 0x8) // dsm trickmode
					offs += 1;
				if (payload[7] & 0x4) // additional copy info
					offs += 1;
				if (payload[7] & 0x2) // crc
					offs += 2;
				if (payload[8] < offs)
					continue;
				uint8_t pef = payload[9+offs++]; // pes extension field
				if (pef & 1) // pes extension flag 2
				{
					if (pef & 0x80) // private data flag
						offs += 16;
					if (pef & 0x40) // pack header field flag
						offs += 1;
					if (pef & 0x20) // program packet sequence counter flag
						offs += 2;
					if (pef & 0x10) // P-STD buffer flag
						offs += 2;
					if (payload[8] < offs)
						continue;
					uint8_t stream_id_extension_len = payload[9+offs++] & 0x7F;
					if (stream_id_extension_len >= 1)
					{
						if (payload[8] < (offs + stream_id_extension_len) )
							continue;
						if (payload[9+offs] & 0x80) // stream_id_extension_bit (should not set)
							continue;
						switch (payload[9+offs])
						{
						case 0x55 ... 0x5f: // VC-1
							break;
						case 0x71: // AC3 / DTS
							break;
						case 0x72: // DTS - HD
							break;
						default:
							eDebug("skip unknwn stream_id_extension %02x\n", payload[9+offs]);
							continue;
						}
					}
					else
						continue;
				}
				else
					continue;
			}
			else
				continue;
		}
			/* drop non-audio, non-video packets because other streams
			   can be non-compliant.*/
		else if (((payload[3] & 0xE0) != 0xC0) &&  // audio
			((payload[3] & 0xF0) != 0xE0)) // video
			continue;

		if (payload[7] & 0x80) /* PTS */
		{
			pts  = ((unsigned long long)(payload[ 9]&0xE))  << 29;
			pts |= ((unsigned long long)(payload[10]&0xFF)) << 22;
			pts |= ((unsigned long long)(payload[11]&0xFE)) << 14;
			pts |= ((unsigned long long)(payload[12]&0xFF)) << 7;
			pts |= ((unsigned long long)(payload[13]&0xFE)) >> 1;
			offset -= 188;

			eDebug("PTS %16llx found at %lld pid %02x stream: %02x", pts, offset, pid, payload[3]);

				/* convert to zero-based */
			if (fixed && fixupPTS(offset, pts))
				return -1;
			return 0;
		}
	}
	
	return -1;
}

int eDVBTSTools::fixupPTS(const off_t &offset, pts_t &now)
{
	if (m_use_streaminfo)
	{
		if (!m_streaminfo.fixupPTS(offset, now))
			return 0;
	} else
	{
			/* for the simple case, we assume one epoch, with up to one wrap around in the middle. */
		calcBegin();
		if (!m_begin_valid)
		{	
			eDebug("begin not valid, can't fixup");
			return -1;
		}
		
		pts_t pos = m_pts_begin;
		if ((now < pos) && ((pos - now) < 90000 * 10))
		{	
			pos = 0;
			return 0;
		}
		
		if (now < pos) /* wrap around */
			now = now + 0x200000000LL - pos;
		else
			now -= pos;
		return 0;
	}
	eDebug("eDVBTSTools::fixupPTS failed!");
	return -1;
}

int eDVBTSTools::getOffset(off_t &offset, pts_t &pts, int marg)
{
	eDebug("getOffset for pts 0x%llx", pts);
	if (m_use_streaminfo)
	{
		if (pts >= m_pts_end && marg > 0 && m_end_valid)
			offset = m_offset_end;
		else
			offset = m_streaminfo.getAccessPoint(pts, marg);
		return 0;
	} else
	{
		calcBegin(); calcEnd();
		
		if (!m_begin_valid)
			return -1;
		if (!m_end_valid)
			return -1;

		if (!m_samples_taken)
			takeSamples();
		
		if (!m_samples.empty())
		{
			int maxtries = 5;
			pts_t p = -1;
			
			while (maxtries--)
			{
					/* search entry before and after */
				std::map<pts_t, off_t>::const_iterator l = m_samples.lower_bound(pts);
				std::map<pts_t, off_t>::const_iterator u = l;

				if (l != m_samples.begin())
					--l;
				
					/* we could have seeked beyond the end */
				if (u == m_samples.end())
				{
						/* use last segment for interpolation. */
					if (l != m_samples.begin())
					{
						--u;
						--l;
					}
				}
					
					/* if we don't have enough points */
				if (u == m_samples.end())
					break;
				
				pts_t pts_diff = u->first - l->first;
				off_t offset_diff = u->second - l->second;
				
				if (offset_diff < 0)
				{
					eDebug("something went wrong when taking samples.");
					m_samples.clear();
					takeSamples();
					continue;
				}

				eDebug("using: %llx:%llx -> %llx:%llx", l->first, u->first, l->second, u->second);

				int bitrate;
				
				if (pts_diff)
					bitrate = offset_diff * 90000 * 8 / pts_diff;
				else
					bitrate = 0;

				offset = l->second;
				offset += ((pts - l->first) * (pts_t)bitrate) / 8ULL / 90000ULL;
				offset -= offset % 188;
				
				p = pts;
				
				if (!takeSample(offset, p))
				{
					int diff = (p - pts) / 90;
			
					eDebug("calculated diff %d ms", diff);
					if (abs(diff) > 300)
					{
						eDebug("diff to big, refining");
						continue;
					}
				} else
					eDebug("no sample taken, refinement not possible.");

				break;
			}
			
				/* if even the first sample couldn't be taken, fall back. */
				/* otherwise, return most refined result. */
			if (p != -1)
			{
				pts = p;
				eDebug("aborting. Taking %llx as offset for %lld", offset, pts);
				return 0;
			}
		}
		
		int bitrate = calcBitrate();
		offset = pts * (pts_t)bitrate / 8ULL / 90000ULL;
		eDebug("fallback, bitrate=%d, results in %016llx", bitrate, offset);
		offset -= offset % 188;
		
		return 0;
	}
}

int eDVBTSTools::getNextAccessPoint(pts_t &ts, const pts_t &start, int direction)
{
	if (m_use_streaminfo)
		return m_streaminfo.getNextAccessPoint(ts, start, direction);
	else
	{
		eDebug("can't get next access point without streaminfo");
		return -1;
	}
}

void eDVBTSTools::calcBegin()
{
	if (!m_source || !m_source->valid())
		return;

	if (!(m_begin_valid || m_futile))
	{
		m_offset_begin = 0;
		if (!getPTS(m_offset_begin, m_pts_begin))
			m_begin_valid = 1;
		else
			m_futile = 1;
	}
}

void eDVBTSTools::calcEnd()
{
	if (!m_source || !m_source->valid())
		return;

	off_t end = m_source->lseek(0, SEEK_END);
	
	if (llabs(end - m_last_filelength) > 1*1024*1024)
	{
		m_last_filelength = end;
		m_end_valid = 0;
		
		m_futile = 0;
//		eDebug("file size changed, recalc length");
	}
	
	int maxiter = 10;
	
	m_offset_end = m_last_filelength;
	
	while (!(m_end_valid || m_futile))
	{
		if (!--maxiter)
		{
			m_futile = 1;
			return;
		}

		m_offset_end -= m_maxrange;
		if (m_offset_end < 0)
			m_offset_end = 0;

			/* restore offset if getpts fails */
		off_t off = m_offset_end;

		if (!getPTS(m_offset_end, m_pts_end))
			m_end_valid = 1;
		else
			m_offset_end = off;

		if (!m_offset_end)
		{
			m_futile = 1;
			break;
		}
	}
}

int eDVBTSTools::calcLen(pts_t &len)
{
	calcBegin(); calcEnd();
	if (!(m_begin_valid && m_end_valid))
		return -1;
	len = m_pts_end - m_pts_begin;
		/* wrap around? */
	if (len < 0)
		len += 0x200000000LL;
	return 0;
}

int eDVBTSTools::calcBitrate()
{
	calcBegin(); calcEnd();
	if (!(m_begin_valid && m_end_valid))
		return -1;

	pts_t len_in_pts = m_pts_end - m_pts_begin;

		/* wrap around? */
	if (len_in_pts < 0)
		len_in_pts += 0x200000000LL;
	off_t len_in_bytes = m_offset_end - m_offset_begin;
	
	if (!len_in_pts)
		return -1;
	
	unsigned long long bitrate = len_in_bytes * 90000 * 8 / len_in_pts;
	if ((bitrate < 10000) || (bitrate > 100000000))
		return -1;
	
	return bitrate;
}

	/* pts, off */
void eDVBTSTools::takeSamples()
{
	m_samples_taken = 1;
	m_samples.clear();
	pts_t dummy;
	int retries=2;

	if (calcLen(dummy) == -1)
		return;
	
	int nr_samples = 30;
	off_t bytes_per_sample = (m_offset_end - m_offset_begin) / (long long)nr_samples;
	if (bytes_per_sample < 40*1024*1024)
		bytes_per_sample = 40*1024*1024;

	bytes_per_sample -= bytes_per_sample % 188;

	eDebug("samples step %lld, pts begin %llx, pts end %llx, offs begin %lld, offs end %lld:",
		bytes_per_sample, m_pts_begin, m_pts_end, m_offset_begin, m_offset_end);

	for (off_t offset = m_offset_begin; offset < m_offset_end;)
	{
		pts_t p;
		if (takeSample(offset, p) && retries--)
			continue;
		retries = 2;
		offset += bytes_per_sample;
	}
	m_samples[0] = m_offset_begin;
	m_samples[m_pts_end - m_pts_begin] = m_offset_end;
}

	/* returns 0 when a sample was taken. */
int eDVBTSTools::takeSample(off_t off, pts_t &p)
{
	off_t offset_org = off;

	if (!eDVBTSTools::getPTS(off, p, 1))
	{
			/* as we are happily mixing PTS and PCR values (no comment, please), we might
			   end up with some "negative" segments. 
			   
			   so check if this new sample is between the previous and the next field*/

		std::map<pts_t, off_t>::const_iterator l = m_samples.lower_bound(p);
		std::map<pts_t, off_t>::const_iterator u = l;

		if (l != m_samples.begin())
		{
			--l;
			if (u != m_samples.end())
			{
				if ((l->second > off) || (u->second < off))
				{
					eDebug("ignoring sample %lld %lld %lld (%llx %llx %llx)",
						l->second, off, u->second, l->first, p, u->first);
					return 1;
				}
			}
		}

		eDebug("adding sample %lld: pts 0x%llx -> pos %lld (diff %lld bytes)", offset_org, p, off, off-offset_org);
		m_samples[p] = off;
		return 0;
	}
	return -1;
}

int eDVBTSTools::findPMT(int &pmt_pid, int &service_id)
{
		/* FIXME: this will be factored out soon! */
	if (!m_source || !m_source->valid())
	{
		eDebug(" file not valid");
		return -1;
	}

	off_t position=0;

	int left = 5*1024*1024;
	
	while (left >= 188)
	{
		unsigned char packet[188];
		int ret = m_source->read(position, packet, 188);
		if (ret != 188)
		{
			eDebug("read error");
			break;
		}
		left -= 188;
		position += 188;

		if (packet[0] != 0x47)
		{
			int i = 0;
			while (i < 188)
			{
				if (packet[i] == 0x47)
					break;
				--position;
				++i;
			}
			continue;
		}
		int pid = ((packet[1] << 8) | packet[2]) & 0x1FFF;
		
		int pusi = !!(packet[1] & 0x40);
		
		if (!pusi)
			continue;
		
			/* ok, now we have a PES header or section header*/
		unsigned char *sec;
		
			/* check for adaption field */
		if (packet[3] & 0x20)
		{
			if (packet[4] >= 183)
				continue;
			sec = packet + packet[4] + 4 + 1;
		} else
			sec = packet + 4;
		
		if (sec[0])	/* table pointer, assumed to be 0 */
			continue;

		if (sec[1] == 0x02) /* program map section */
		{
			pmt_pid = pid;
			service_id = (sec[4] << 8) | sec[5];
			return 0;
		}
	}
	
	return -1;
}

int eDVBTSTools::findFrame(off_t &_offset, size_t &len, int &direction, int frame_types)
{
	off_t offset = _offset;
	int nr_frames = 0;
//	eDebug("trying to find iFrame at %llx", offset);

	if (!m_use_streaminfo)
	{
//		eDebug("can't get next iframe without streaminfo");
		return -1;
	}

				/* let's find the iframe before the given offset */
	unsigned long long data;
	
	if (direction < 0)
		offset--;

	while (1)
	{
		if (m_streaminfo.getStructureEntry(offset, data, (direction == 0) ? 1 : 0))
		{
			eDebug("getting structure info for origin offset failed.");
			return -1;
		}
		if (offset == 0x7fffffffffffffffLL) /* eof */
		{
			eDebug("reached eof");
			return -1;
		}
			/* data is usually the start code in the lower 8 bit, and the next byte <<8. we extract the picture type from there */
			/* we know that we aren't recording startcode 0x09 for mpeg2, so this is safe */
			/* TODO: check frame_types */
		int is_start = (data & 0xE0FF) == 0x0009; /* H.264 NAL unit access delimiter with I-frame*/
		is_start |= (data & 0x3800FF) == 0x080000; /* MPEG2 picture start code with I-frame */
		
		int is_frame = ((data & 0xFF) == 0x0009) || ((data & 0xFF) == 0x00); /* H.264 UAD or MPEG2 start code */
		
		if (is_frame)
		{
			if (direction < 0)
				--nr_frames;
			else
				++nr_frames;
		}
//		eDebug("%08llx@%llx -> %d, %d", data, offset, is_start, nr_frames);
		if (is_start)
			break;

		if (direction == -1)
			--offset; /* move to previous entry */
		else if (direction == +1)
			direction = 0;
	}
	off_t start = offset;

#if 0
			/* backtrack to find the previous sequence start, in case of MPEG2 */
	if ((data & 0xFF) == 0x00) {
		do {
			--start;
			if (m_streaminfo.getStructureEntry(start, data, 0))
			{
				eDebug("get previous failed");
				return -1;
			}
		} while (((data & 0xFF) != 9) && ((data & 0xFF) != 0x00) && ((data & 0xFF) != 0xB3)); /* sequence start or previous frame */
		if ((data & 0xFF) != 0xB3)
			start = offset;  /* Failed to find corresponding sequence start, so never mind */
	}

#endif

			/* let's find the next frame after the given offset */
	do {
		if (m_streaminfo.getStructureEntry(offset, data, 1))
		{
			eDebug("get next failed");
			return -1;
		}
		if (offset == 0x7fffffffffffffffLL) /* eof */
		{
			eDebug("reached eof (while looking for end of iframe)");
			return -1;
		}
//		eDebug("%08llx@%llx (next)", data, offset);
	} while (((data & 0xFF) != 9) && ((data & 0xFF) != 0x00)); /* next frame */

#if 0
			/* align to TS pkt start */
	start = start - (start % 188);
	offset = offset - (offset % 188);
#endif

	len = offset - start;
	_offset = start;
	direction = nr_frames;
//	eDebug("result: offset=%llx, len: %ld", offset, (int)len);
	return 0;
}

int eDVBTSTools::findNextPicture(off_t &offset, size_t &len, int &distance, int frame_types)
{
	int nr_frames, direction;
//	eDebug("trying to move %d frames at %llx", distance, offset);
	
	frame_types = frametypeI; /* TODO: intelligent "allow IP frames when not crossing an I-Frame */

	off_t new_offset = offset;
	size_t new_len = len;
	int first = 1;

	if (distance > 0) {
		direction = 0;
                nr_frames = 0;
        } else {
		direction = -1;
                nr_frames = -1;
		distance = -distance+1;
        }	
	while (distance > 0)
	{
		int dir = direction;
		if (findFrame(new_offset, new_len, dir, frame_types))
		{
//			eDebug("findFrame failed!\n");
			return -1;
		}
		
		distance -= abs(dir);
		
//		eDebug("we moved %d, %d to go frames (now at %llx)", dir, distance, new_offset);

		if (distance >= 0 || direction == 0)
		{
			first = 0;
			offset = new_offset;
			len = new_len;
			nr_frames += abs(dir);
		} 
		else if (first) {
			first = 0;
			offset = new_offset;
			len = new_len;
			nr_frames += abs(dir) + distance; // never jump forward during rewind
		}
	}

	distance = (direction < 0) ? -nr_frames : nr_frames;
//	eDebug("in total, we moved %d frames", nr_frames);

	return 0;
}
