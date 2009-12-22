#include <lib/dvb/pvrparse.h>
#include <lib/base/eerror.h>
#include <byteswap.h>

#ifndef BYTE_ORDER
#error no byte order defined!
#endif

eMPEGStreamInformation::eMPEGStreamInformation()
	: m_structure_cache_valid(0), m_structure_read(0), m_structure_write(0)
{
}

eMPEGStreamInformation::~eMPEGStreamInformation()
{
	if (m_structure_read)
		fclose(m_structure_read);
	if (m_structure_write)
		fclose(m_structure_write);
}

int eMPEGStreamInformation::startSave(const char *filename)
{
	m_filename = filename;
	m_structure_write = fopen((m_filename + ".sc").c_str(), "wb");
	return 0;
}

int eMPEGStreamInformation::stopSave(void)
{
	if (m_structure_write)
	{
		fclose(m_structure_write);
		m_structure_write = 0;
	}
	if (m_filename == "")
		return -1;
	FILE *f = fopen((m_filename + ".ap").c_str(), "wb");
	if (!f)
		return -1;
	
	for (std::map<off_t, pts_t>::const_iterator i(m_access_points.begin()); i != m_access_points.end(); ++i)
	{
		unsigned long long d[2];
#if BYTE_ORDER == BIG_ENDIAN
		d[0] = i->first;
		d[1] = i->second;
#else
		d[0] = bswap_64(i->first);
		d[1] = bswap_64(i->second);
#endif
		fwrite(d, sizeof(d), 1, f);
	}
	fclose(f);
	
	return 0;
}

int eMPEGStreamInformation::load(const char *filename)
{
	m_filename = filename;
	if (m_structure_read)
		fclose(m_structure_read);
	m_structure_read = fopen((std::string(m_filename) + ".sc").c_str(), "rb");
	FILE *f = fopen((std::string(m_filename) + ".ap").c_str(), "rb");
	if (!f)
		return -1;
	m_access_points.clear();
	m_pts_to_offset.clear();
	while (1)
	{
		unsigned long long d[2];
		if (fread(d, sizeof(d), 1, f) < 1)
			break;
		
#if BYTE_ORDER == LITTLE_ENDIAN
		d[0] = bswap_64(d[0]);
		d[1] = bswap_64(d[1]);
#endif
		m_access_points[d[0]] = d[1];
		m_pts_to_offset.insert(std::pair<pts_t,off_t>(d[1], d[0]));
	}
	fclose(f);
	fixupDiscontinuties();
	return 0;
}

bool eMPEGStreamInformation::empty()
{
	return m_access_points.empty();
}

void eMPEGStreamInformation::fixupDiscontinuties()
{
	m_timestamp_deltas.clear();
	if (!m_access_points.size())
		return;
		
//	eDebug("Fixing discontinuities ...");

			/* if we have no delta at the beginning, extrapolate it */
	if ((m_access_points.find(0) == m_access_points.end()) && (m_access_points.size() > 1))
	{
		std::map<off_t,pts_t>::const_iterator second = m_access_points.begin();
		std::map<off_t,pts_t>::const_iterator first  = second++;
		if (first->first < second->first) /* i.e., not equal or broken */
		{
			off_t diff = second->first - first->first;
			pts_t tdiff = second->second - first->second;
			tdiff *= first->first;
			tdiff /= diff;
			m_timestamp_deltas[0] = first->second - tdiff;
//			eDebug("first delta is %08llx", first->second - tdiff);
		}
	}

	if (m_timestamp_deltas.empty())
		m_timestamp_deltas[m_access_points.begin()->first] = m_access_points.begin()->second;

	pts_t currentDelta = m_timestamp_deltas.begin()->second, lastpts_t = 0;
	for (std::map<off_t,pts_t>::const_iterator i(m_access_points.begin()); i != m_access_points.end(); ++i)
	{
		pts_t current = i->second - currentDelta;
		pts_t diff = current - lastpts_t;
		
		if (llabs(diff) > (90000*5)) // 5sec diff
		{
//			eDebug("%llx < %llx, have discont. new timestamp is %llx (diff is %llx)!", current, lastpts_t, i->second, diff);
			currentDelta = i->second - lastpts_t; /* FIXME: should be the extrapolated new timestamp, based on the current rate */
//			eDebug("current delta now %llx, making current to %llx", currentDelta, i->second - currentDelta);
			m_timestamp_deltas[i->first] = currentDelta;
		}
		lastpts_t = i->second - currentDelta;
	}
	
	
//	eDebug("ok, found %d disconts.", m_timestamp_deltas.size());

#if 0	
	for (off_t x=0x25807E34ULL; x < 0x25B3CF70; x+= 100000)
	{
		off_t o = x;
		pts_t p;
		int r = getPTS(o, p);
		eDebug("%08llx -> %08llx | %08llx, %d, %08llx %08llx", x, getDelta(x), getInterpolated(x), r, o, p);
	}
#endif
}

pts_t eMPEGStreamInformation::getDelta(off_t offset)
{
	if (!m_timestamp_deltas.size())
		return 0;
	std::map<off_t,pts_t>::iterator i = m_timestamp_deltas.upper_bound(offset);

		/* i can be the first when you query for something before the first PTS */
	if (i != m_timestamp_deltas.begin())
		--i;

	return i->second;
}

int eMPEGStreamInformation::fixupPTS(const off_t &offset, pts_t &ts)
{
	if (!m_timestamp_deltas.size())
		return -1;

	std::multimap<pts_t, off_t>::const_iterator 
		l = m_pts_to_offset.upper_bound(ts - 60 * 90000), 
		u = m_pts_to_offset.upper_bound(ts + 60 * 90000), 
		nearest = m_pts_to_offset.end();

	while (l != u)
	{
		if ((nearest == m_pts_to_offset.end()) || (llabs(l->first - ts) < llabs(nearest->first - ts)))
			nearest = l;
		++l;
	}
	if (nearest == m_pts_to_offset.end())
		return 1;

	ts -= getDelta(nearest->second);

	return 0;
}

int eMPEGStreamInformation::getPTS(off_t &offset, pts_t &pts)
{
	std::map<off_t,pts_t>::iterator before = m_access_points.lower_bound(offset);

		/* usually, we prefer the AP before the given offset. however if there is none, we take any. */
	if (before != m_access_points.begin())
		--before;
	
	if (before == m_access_points.end())
	{
		pts = 0;
		return -1;
	}
	
	offset = before->first;
	pts = before->second - getDelta(offset);
	
	return 0;
}

pts_t eMPEGStreamInformation::getInterpolated(off_t offset)
{
		/* get the PTS values before and after the offset. */
	std::map<off_t,pts_t>::iterator before, after;
	after = m_access_points.upper_bound(offset);
	before = after;

	if (before != m_access_points.begin())
		--before;
	else	/* we query before the first known timestamp ... FIXME */
		return 0;

		/* empty... */
	if (before == m_access_points.end())
		return 0;

		/* if after == end, then we need to extrapolate ... FIXME */
	if ((before->first == offset) || (after == m_access_points.end()))
		return before->second - getDelta(offset);
	
	pts_t before_ts = before->second - getDelta(before->first);
	pts_t after_ts = after->second - getDelta(after->first);
	
//	eDebug("%08llx .. ? .. %08llx", before_ts, after_ts);
//	eDebug("%08llx .. %08llx .. %08llx", before->first, offset, after->first);
	
	pts_t diff = after_ts - before_ts;
	off_t diff_off = after->first - before->first;
	
	diff = (offset - before->first) * diff / diff_off;
//	eDebug("%08llx .. %08llx .. %08llx", before_ts, before_ts + diff, after_ts);
	return before_ts + diff;
}
 
off_t eMPEGStreamInformation::getAccessPoint(pts_t ts, int marg)
{
		/* FIXME: more efficient implementation */
	off_t last = 0;
	off_t last2 = 0;
	pts_t lastc = 0;
	ts += 1; // Add rounding error margin
	for (std::map<off_t, pts_t>::const_iterator i(m_access_points.begin()); i != m_access_points.end(); ++i)
	{
		pts_t delta = getDelta(i->first);
		pts_t c = i->second - delta;
		if (c > ts) {
			if (marg > 0)
				return (last + i->first)/376*188;
			else if (marg < 0)
				return (last + last2)/376*188;
			else
				return last;
		}
		lastc = c;
		last2 = last;
		last = i->first;
	}
	if (marg < 0)
		return (last + last2)/376*188;
	else
		return last;
}

int eMPEGStreamInformation::getNextAccessPoint(pts_t &ts, const pts_t &start, int direction)
{
	off_t offset = getAccessPoint(start);
	pts_t c1, c2;
	std::map<off_t, pts_t>::const_iterator i = m_access_points.find(offset);
	if (i == m_access_points.end())
	{
		eDebug("getNextAccessPoint: initial AP not found");
		return -1;
	}
	c1 = i->second - getDelta(i->first);
	while (direction)
	{
		if (direction > 0)
		{
			if (i == m_access_points.end())
				return -1;
			++i;
			c2 = i->second - getDelta(i->first);
			if (c1 == c2) { // Discontinuity
				++i;
				c2 = i->second - getDelta(i->first);
			}
			c1 = c2;
			direction--;
		}
		if (direction < 0)
		{
			if (i == m_access_points.begin())
			{
				eDebug("at start");
				return -1;
			}
			--i;
			c2 = i->second - getDelta(i->first);
			if (c1 == c2) { // Discontinuity
				--i;
				c2 = i->second - getDelta(i->first);
			}
			c1 = c2;
			direction++;
		}
	}
	ts = i->second - getDelta(i->first);
	eDebug("fine, at %llx - %llx = %llx", ts, i->second, getDelta(i->first));
	eDebug("fine, at %lld - %lld = %lld", ts, i->second, getDelta(i->first));
	return 0;
}

void eMPEGStreamInformation::writeStructureEntry(off_t offset, structure_data data)
{
	unsigned long long d[2];
#if BYTE_ORDER == BIG_ENDIAN
	d[0] = offset;
	d[1] = data;
#else
	d[0] = bswap_64(offset);
	d[1] = bswap_64(data);
#endif
	if (m_structure_write)
		fwrite(d, sizeof(d), 1, m_structure_write);
}

int eMPEGStreamInformation::getStructureEntry(off_t &offset, unsigned long long &data, int get_next)
{
	if (!m_structure_read)
	{
		eDebug("getStructureEntry failed because of no m_structure_read");
		return -1;
	}

	const int struture_cache_entries = sizeof(m_structure_cache) / 16;
	if ((!m_structure_cache_valid) || ((off_t)m_structure_cache[0] > offset) || ((off_t)m_structure_cache[(struture_cache_entries - (get_next ? 2 : 1)) * 2] <= offset))
	{
		fseek(m_structure_read, 0, SEEK_END);
		int l = ftell(m_structure_read);
		unsigned long long d[2];
		const int entry_size = sizeof d;

			/* do a binary search */
		int count = l / entry_size;
		int i = 0;
		
		while (count)
		{
			int step = count >> 1;
			
			fseek(m_structure_read, (i + step) * entry_size, SEEK_SET);
			if (!fread(d, 1, entry_size, m_structure_read))
			{
				eDebug("read error at entry %d", i);
				return -1;
			}
			
#if BYTE_ORDER != BIG_ENDIAN
			d[0] = bswap_64(d[0]);
			d[1] = bswap_64(d[1]);
#endif
//			eDebug("%d: %08llx > %llx", i, d[0], d[1]);
			
			if (d[0] < (unsigned long long)offset)
			{
				i += step + 1;
				count -= step + 1;
			} else
				count = step;
		}
		
		eDebug("found %d", i);
		
			/* put that in the middle */
		i -= struture_cache_entries / 2;
		if (i < 0)
			i = 0;
		eDebug("cache starts at %d", i);
		fseek(m_structure_read, i * entry_size, SEEK_SET);
		int num = fread(m_structure_cache, entry_size, struture_cache_entries, m_structure_read);
		eDebug("%d entries", num);
		for (i = 0; i < struture_cache_entries; ++i)
		{
			if (i < num)
			{
#if BYTE_ORDER != BIG_ENDIAN
				m_structure_cache[i * 2] = bswap_64(m_structure_cache[i * 2]);
				m_structure_cache[i * 2 + 1] = bswap_64(m_structure_cache[i * 2 + 1]);
#endif
			} else
			{
				m_structure_cache[i * 2] = 0x7fffffffffffffffULL; /* fill with harmless content */
				m_structure_cache[i * 2 + 1] = 0;
			}
		}
		m_structure_cache_valid = 1;
	}
	
	int i = 0;
	while ((off_t)m_structure_cache[i * 2] <= offset)
	{
		++i;
		if (i == struture_cache_entries)
		{
			eDebug("structure data consistency fail!, we are looking for %llx, but last entry is %llx", offset, m_structure_cache[i*2-2]);
			return -1;
		}
	}
	if (!i)
	{
		eDebug("structure data (first entry) consistency fail!");
		return -1;
	}
	
	if (!get_next)
		--i;

//	eDebug("[%d] looked for %llx, found %llx=%llx", sizeof offset, offset, m_structure_cache[i * 2], m_structure_cache[i * 2 + 1]);
	offset = m_structure_cache[i * 2];
	data = m_structure_cache[i * 2 + 1];
	return 0;
}

eMPEGStreamParserTS::eMPEGStreamParserTS(eMPEGStreamInformation &streaminfo): m_streaminfo(streaminfo), m_pktptr(0), m_pid(-1), m_need_next_packet(0), m_skip(0), m_last_pts_valid(0)
{
}

int eMPEGStreamParserTS::processPacket(const unsigned char *pkt, off_t offset)
{
	if (!wantPacket(pkt))
		eWarning("something's wrong.");

	const unsigned char *end = pkt + 188, *begin = pkt;
	
	int pusi = !!(pkt[1] & 0x40);
	
	if (!(pkt[3] & 0x10)) /* no payload? */
		return 0;

	if (pkt[3] & 0x20) // adaptation field present?
		pkt += pkt[4] + 4 + 1;  /* skip adaptation field and header */
	else
		pkt += 4; /* skip header */

	if (pkt > end)
	{
		eWarning("[TSPARSE] dropping huge adaption field");
		return 0;
	}

	pts_t pts = 0;
	int ptsvalid = 0;
	
	if (pusi)
	{
			// ok, we now have the start of the payload, aligned with the PES packet start.
		if (pkt[0] || pkt[1] || (pkt[2] != 1))
		{
			eWarning("broken startcode");
			return 0;
		}

		if (pkt[7] & 0x80) // PTS present?
		{
			pts  = ((unsigned long long)(pkt[ 9]&0xE))  << 29;
			pts |= ((unsigned long long)(pkt[10]&0xFF)) << 22;
			pts |= ((unsigned long long)(pkt[11]&0xFE)) << 14;
			pts |= ((unsigned long long)(pkt[12]&0xFF)) << 7;
			pts |= ((unsigned long long)(pkt[13]&0xFE)) >> 1;
			ptsvalid = 1;
			
			m_last_pts = pts;
			m_last_pts_valid = 1;

	#if 0		
			int sec = pts / 90000;
			int frm = pts % 90000;
			int min = sec / 60;
			sec %= 60;
			int hr = min / 60;
			min %= 60;
			int d = hr / 24;
			hr %= 24;
			
			eDebug("pts: %016llx %d:%02d:%02d:%02d:%05d", pts, d, hr, min, sec, frm);
	#endif
		}
		
			/* advance to payload */
		pkt += pkt[8] + 9;
	}

	while (pkt < (end-4))
	{
		int pkt_offset = pkt - begin;
		if (!(pkt[0] || pkt[1] || (pkt[2] != 1)))
		{
//			eDebug("SC %02x %02x %02x %02x, %02x", pkt[0], pkt[1], pkt[2], pkt[3], pkt[4]);
			int sc = pkt[3];
			
			if (m_streamtype == 0) /* mpeg2 */
			{
				if ((sc == 0x00) || (sc == 0xb3) || (sc == 0xb8)) /* picture, sequence, group start code */
				{
					unsigned long long data = sc | (pkt[4] << 8) | (pkt[5] << 16) | (pkt[6] << 24);
					m_streaminfo.writeStructureEntry(offset + pkt_offset, data  & 0xFFFFFFFFULL);
				}
				if (pkt[3] == 0xb3) /* sequence header */
				{
					if (ptsvalid)
					{
						m_streaminfo.m_access_points[offset] = pts;
	//					eDebug("Sequence header at %llx, pts %llx", offset, pts);
					} else
						/*eDebug("Sequence header but no valid PTS value.")*/;
				}
			}

			if (m_streamtype == 1) /* H.264 */
			{
				if (sc == 0x09)
				{
						/* store image type */
					unsigned long long data = sc | (pkt[4] << 8);
					m_streaminfo.writeStructureEntry(offset + pkt_offset, data);
				}
				if (pkt[3] == 0x09 &&   /* MPEG4 AVC NAL unit access delimiter */
					 (pkt[4] >> 5) == 0) /* and I-frame */
				{
					if (ptsvalid)
					{
						m_streaminfo.m_access_points[offset] = pts;
	//				eDebug("MPEG4 AVC UAD at %llx, pts %llx", offset, pts);
					} else
						/*eDebug("MPEG4 AVC UAD but no valid PTS value.")*/;
				}
			}
		}
		++pkt;
	}
	return 0;
}

inline int eMPEGStreamParserTS::wantPacket(const unsigned char *hdr) const
{
	if (hdr[0] != 0x47)
	{
		eDebug("missing sync!");
		return 0;
	}
	int ppid = ((hdr[1]&0x1F) << 8) | hdr[2];

	if (ppid != m_pid)
		return 0;
		
	if (m_need_next_packet)  /* next packet (on this pid) was required? */
		return 1;
	
	if (hdr[1] & 0x40)	 /* pusi set: yes. */
		return 1;

	return m_streamtype == 0; /* we need all packets for MPEG2, but only PUSI packets for H.264 */
}

void eMPEGStreamParserTS::parseData(off_t offset, const void *data, unsigned int len)
{
	const unsigned char *packet = (const unsigned char*)data;
	const unsigned char *packet_start = packet;
	
			/* sorry for the redundant code here, but there are too many special cases... */
	while (len)
	{
			/* emergency resync. usually, this should not happen, because the data should 
			   be sync-aligned.
			   
			   to make this code work for non-strictly-sync-aligned data, (for example, bad 
			   files) we fix a possible resync here by skipping data until the next 0x47.
			   
			   if this is a false 0x47, the packet will be dropped by wantPacket, and the
			   next time, sync will be re-established. */
		int skipped = 0;
		while (!m_pktptr && len)
		{
			if (packet[0] == 0x47)
				break;
			len--;
			packet++;
			skipped++;
		}
		
		if (skipped)
			eDebug("SYNC LOST: skipped %d bytes.", skipped);
		
		if (!len)
			break;
		
		if (m_pktptr)
		{
				/* skip last packet */
			if (m_pktptr < 0)
			{
				unsigned int skiplen = -m_pktptr;
				if (skiplen > len)
					skiplen = len;
				packet += skiplen;
				len -= skiplen;
				m_pktptr += skiplen;
				continue;
			} else if (m_pktptr < 4) /* header not complete, thus we don't know if we want this packet */
			{
				unsigned int storelen = 4 - m_pktptr;
				if (storelen > len)
					storelen = len;
				memcpy(m_pkt + m_pktptr, packet,  storelen);
				
				m_pktptr += storelen;
				len -= storelen;
				packet += storelen;
				
				if (m_pktptr == 4)
					if (!wantPacket(m_pkt))
					{
							/* skip packet */
						packet += 184;
						len -= 184;
						m_pktptr = 0;
						continue;
					}
			}
				/* otherwise we complete up to the full packet */
			unsigned int storelen = 188 - m_pktptr;
			if (storelen > len)
				storelen = len;
			memcpy(m_pkt + m_pktptr, packet,  storelen);
			m_pktptr += storelen;
			len -= storelen;
			packet += storelen;
			
			if (m_pktptr == 188)
			{
				m_need_next_packet = processPacket(m_pkt, offset + (packet - packet_start));
				m_pktptr = 0;
			}
		} else if (len >= 4)  /* if we have a full header... */
		{
			if (wantPacket(packet))  /* decide wheter we need it ... */
			{
				if (len >= 188)          /* packet complete? */
				{
					m_need_next_packet = processPacket(packet, offset + (packet - packet_start)); /* process it now. */
				} else
				{
					memcpy(m_pkt, packet, len);  /* otherwise queue it up */
					m_pktptr = len;
				}
			}

				/* skip packet */
			int sk = len;
			if (sk >= 188)
				sk = 188;
			else if (!m_pktptr) /* we dont want this packet, otherwise m_pktptr = sk (=len) > 4 */
				m_pktptr = sk - 188;

			len -= sk;
			packet += sk;
		} else             /* if we don't have a complete header */
		{
			memcpy(m_pkt, packet, len);   /* complete header next time */
			m_pktptr = len;
			packet += len;
			len = 0;
		}
	}
}

void eMPEGStreamParserTS::setPid(int _pid, int type)
{
	m_pktptr = 0;
	m_pid = _pid;
	m_streamtype = type;
}

int eMPEGStreamParserTS::getLastPTS(pts_t &last_pts)
{
	if (!m_last_pts_valid)
	{
		last_pts = 0;
		return -1;
	}
	last_pts = m_last_pts;
	return 0;
}

