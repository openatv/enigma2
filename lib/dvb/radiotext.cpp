#include <lib/base/eerror.h>
#include <lib/dvb/radiotext.h>
#include <lib/dvb/idemux.h>
#include <lib/gdi/gpixmap.h>

DEFINE_REF(eDVBRdsDecoder);

eDVBRdsDecoder::eDVBRdsDecoder(iDVBDemux *demux, int type)
	:msgPtr(0), bsflag(0), qdar_pos(0), t_ptr(0), qdarmvi_show(0), state(0)
	,m_type(type), m_pid(-1), m_abortTimer(eTimer::create(eApp))
{
	setStreamID(0xC0, 0xC0);

	memset(rass_picture_mask, 0, sizeof(rass_picture_mask));
	memset(rtp_item, 0, sizeof(rtp_item));

	if (demux->createPESReader(eApp, m_pes_reader))
		eDebug("failed to create PES reader!");
	else if (type == 0)
		m_pes_reader->connectRead(slot(*this, &eDVBRdsDecoder::processData), m_read_connection);
	else
		m_pes_reader->connectRead(slot(*this, &eDVBRdsDecoder::gotAncillaryData), m_read_connection);
	CONNECT(m_abortTimer->timeout, eDVBRdsDecoder::abortNonAvail);
}

eDVBRdsDecoder::~eDVBRdsDecoder()
{
	// delete cached rass slides
	for (int page=0; page < 10; ++page)
	{
		unsigned char mask = rass_picture_mask[(page*4)/8];
		if (page % 2)
			mask >>= 4;
		int subpage=0;
		while(mask)
		{
			if (mask & 1)
			{
				std::string filename = getRassPicture(page, subpage);
				if (filename.length())
					remove(filename.c_str());
			}
			mask >>= 1;
			++subpage;
		}
	}
	remove("/tmp/RassLast.mvi");
}

#define SWAP(x)	((x<<8)|(x>>8))
#define LO(x)	(x&0xFF)

static inline unsigned short crc_ccitt_byte( unsigned short crc, unsigned char c )
{
	crc = SWAP(crc) ^ c;
	crc = crc ^ (LO(crc) >> 4);
	crc = crc ^ (SWAP(LO(crc)) << 4) ^ (LO(crc) << 5);
	return crc;
}

static int bitrate[3][3][16] = {
	{
		// MPEG-2, L3
		{-1,8000,16000,24000,32000,40000,48000,56000,64000,80000,96000,112000,128000,144000,160000,0}, 
		// MPEG-2, L2
		{-1,8000,16000,24000,32000,40000,48000,56000,64000,80000,96000,112000,128000,144000,160000,0},
		// MPEG-2, L1
		{-1,32000,48000,56000,64000,80000,96000,112000,128000,144000,160000,176000,192000,224000,256000,0}
	},
	{
		// MPEG-1, L3
		{-1,32000,40000,48000,56000,64000,80000,96000,112000,128000,160000,192000,224000,256000,320000,0}, 
		// MPEG-1, L2
		{-1,32000,48000,56000,64000,80000,96000,112000,128000,160000,192000,224000,256000,320000,384000,0},
		// MPEG-1, L1
		{-1,32000,64000,96000,128000,160000,192000,224000,256000,288000,320000,352000,384000,416000,448000,0}
	},
	{
		//MPEG-2.5, L3??
		{-1,6000,8000,10000,12000,16000,20000,24000,28000,320000,40000,48000,56000,64000,80000,0},
		//MPEG-2.5, L2
		{-1,6000,8000,10000,12000,16000,20000,24000,28000,320000,40000,48000,56000,64000,80000,0},
		//MPEG-2.5, L1
		{-1,8000,12000,16000,20000,24000,32000,40000,48000,560000,64000,80000,96000,112000,128000,0}
	}
};

static int frequency[3][4] = {
	// MPEG2 - 22.05, 24, 16khz
	{ 22050,24000,16000,0 },
	// MPEG1 - 44.1, 48, 32khz
	{ 44100,48000,32000,0 },
	// MPEG2.5 - 11.025, 12, 8khz
	{ 11025,12000,8000,0 }
};

void eDVBRdsDecoder::connectEvent(const Slot1<void, int> &slot, ePtr<eConnection> &connection)
{
	connection = new eConnection(this, m_event.connect(slot));
}

void eDVBRdsDecoder::addToPictureMask(int id)
{
	int page = id / 1000;
	int tmp = page > 0 ? id / page : id;
	int subpage = 0;
	while(tmp > 1000)
	{
		++subpage;
		tmp -= 1000;
		tmp *= 10;
	}
	int index = (page*4+subpage)/8;
	int val = (page%2) ? 16 * (1 << subpage) : (1 << subpage);
	if (rass_picture_mask[index] & val) // already have this picture
		return;
	rass_picture_mask[index] |= val;
	/* emit */ m_event(RassInteractivePicMaskChanged);
}

void eDVBRdsDecoder::removeFromPictureMask(int id)
{
	int page = id / 1000;
	int tmp = page > 0 ? id / page : id;
	int subpage = 0;
	while(tmp > 1000)
	{
		++subpage;
		tmp -= 1000;
		tmp *= 10;
	}
	int index = (page*4)/8;
	int val = (page%2) ? 16 * (1 << subpage) : (1 << subpage);
	if (rass_picture_mask[index] & val) // have this picture
	{
		rass_picture_mask[index] &= ~val;
		/* emit */ m_event(RassInteractivePicMaskChanged);
	}
}

void eDVBRdsDecoder::processPESPacket(__u8 *data, int len)
{
	int pos=9+data[8];// skip pes header

	while (pos < len)
	{
		if ((0xFF & data[pos]) != 0xFF || (0xF0 & data[pos + 1]) != 0xF0)
			return;

		int padding_bit = (data[pos + 2]>>1) & 1;
		int mode = (data[pos + 3]>>6) & 3;
		int channel = mode == 3 ? 1 : 2;
		int id = (data[pos + 1] >> 3) & 1;
		int emphasis_bit = data[pos + 3] & 3;
		//int protection_bit = data[pos + 1] & 1;
		int rate = -1;
		int sample_freq = -1;
		int layer = -1;

		if (emphasis_bit == 2 && id == 1 )
			id = 2;

		if ((layer = (data[pos + 1]>>1) & 3) < 1)
			return;

		if ((rate = bitrate[id][layer - 1][(data[pos + 2]>>4) & 0xf]) < 1)
			return;

		if ((sample_freq = frequency[id][(data[pos + 2]>>2) & 3]) == 0)
			return;

		if (id == 1 && layer == 2)
		{
			if (rate / channel < 32000)
				return;
			if (rate / channel > 192000)
				return;
		}

		int frame_size = layer < 3 ?
			(144 * rate / sample_freq) + padding_bit :
			((12 * rate / sample_freq) * 4) + (4 * padding_bit);

		pos += frame_size;

#if 0
//		eDebug("protection_bit ? %d", protection_bit);
//		int offs = protection_bit ? pos - 1 : pos - 3;
//		if (data[offs] != 0xFD)
//			offs += 2;
//		eDebug("%02x %02x %02x %02x %02x", data[offs-2], data[offs-1], data[offs], data[offs+1], data[offs+2]);
#else
		int offs = pos - 1;
#endif

		if (data[offs] == 0xFD)
		{
			m_abortTimer->stop();
			int ancillary_len = 1 + data[offs - 1];
			offs -= ancillary_len;
			gotAncillaryData(data+offs, ancillary_len-1);
		}
	}
}

void eDVBRdsDecoder::process_qdar(unsigned char *buf)
{
	if (buf[0] == 0x40 && buf[1] == 0xDA)
	{
		unsigned int item,cnt,ctrl,item_type;
		unsigned long item_length,id,item_no,ptr,tmp;
		unsigned short crc_qdar,crc_read;
		char fname[50];
		ptr=4;cnt=0;
		item=buf[2]<<8; // Number of Items
		item|=buf[3];
		
		while ( cnt++ < item ) //read in items
		{
			id=buf[ptr++]<<8; //QDarID
			id|=buf[ptr++];
			
			item_no=buf[ptr++]<<8; // Item Number
			item_no|=buf[ptr++];
			
			ctrl=buf[ptr++]; //controlbyte
			item_type=buf[ptr++]; //item type
			
			item_length=buf[ptr++]<<24; // Item length
			item_length|=buf[ptr++]<<16;
			item_length|=buf[ptr++]<<8;
			item_length|=buf[ptr++];
			
			ptr=ptr+4; // rfu Bytes ... not used
			tmp=ptr; // calc crc
			crc_qdar=0xFFFF;
			while (tmp < ptr+item_length)
				crc_qdar = crc_ccitt_byte(crc_qdar, buf[tmp++]);
		
			crc_read=buf[ptr+item_length]<<8;
			crc_read|=buf[ptr+item_length+1];
			//eDebug("[RDS/Rass] CRC read: %04X calculated: %04X",crc_read,crc_qdar^0xFFFF);

			if (crc_read == (crc_qdar^0xFFFF)) // process item
			{
				switch(item_type)
				{
					case 0x01: //Stillframe
						if (ctrl&0x01) // display slide
						{
							sprintf(fname,"/tmp/RassLast.mvi");
							FILE *fh=fopen(fname,"wb");
							fwrite(buf+ptr,1,item_length-2,fh);
							fclose(fh);
							/*emit*/ m_event(RecvRassSlidePic);
							qdarmvi_show=1;
						}
						if (ctrl&0x02) // save slide for interactive mode
						{
							if (id == 0 || id >= 1000)
							{
								sprintf(fname,"/tmp/Rass%04d.mvi",(int)id);
								FILE *fh=fopen(fname,"wb");
								fwrite(buf+ptr,1,item_length-2,fh);
								fclose(fh);
								addToPictureMask(id);
							}
							else
								eDebug("ignore recv interactive picture id %lu", id);
						}
						if (ctrl&0x04) // display slide if nothing had been displayed yet
						{
							if (qdarmvi_show != 1)
							{
								sprintf(fname,"/tmp/RassLast.mvi");
								FILE *fh=fopen(fname,"wb");
								fwrite(buf+ptr,1,item_length-2,fh);
								fclose(fh);
								/*emit*/ m_event(RecvRassSlidePic);
								qdarmvi_show=1;
							}
						}
						if (ctrl&0x08) // delete slide
						{
							eDebug("delete slide id %lu, item_no %lu", id, item_no);
							if (id == 0 || id >= 1000)
							{
								eDebug("delete %lu", id);
								removeFromPictureMask(id);
								sprintf(fname,"/tmp/Rass%04d.mvi",(int)id); // was item_no ? ! ?
								remove(fname);
							}
							else
								eDebug("ignore del interactive picture id %lu", id);
						}
						break;
					default: //nothing more yet defined
						break;
				}
			} 
			else
			{
				eDebug("[RDS/Rass] CRC error, skip Rass-Qdar-Item");
			}
			
			ptr=+item_length;
		}
	}
	else
	{
		eDebug("[RDS/Rass] No Rass-QDAR archive (%02X %02X) so skipping !\n",buf[0],buf[1]);
	}
}

void eDVBRdsDecoder::gotAncillaryData(const __u8 *buf, int len)
{
	if (len <= 0)
		return;
	int pos = m_type ? 0 : len-1;
	while ( len )
	{
		unsigned char c = buf[pos];

		pos += m_type ? 1 : -1;

		--len;

		if (bsflag == 1) // byte stuffing
		{
			bsflag=2;
			switch (c)
			{
				case 0x00: c=0xFD; break;
				case 0x01: c=0xFE; break;
				case 0x02: c=0xFF; break;
			}
		}

		if (c == 0xFD && bsflag ==0) 
			bsflag=1;
		else
			bsflag=0;
					
		if (bsflag == 0) 
		{
			if ( state == 1 )
				crc=0xFFFF;
			if (( state >= 1 && state < 11 ) || ( state >=26 && state < 36 ))
				crc = crc_ccitt_byte(crc, c);

			switch (state)
			{
				case 0:
					if ( c==0xFE )  // Startkennung
						state=1;
					break;
				case 1: // 10bit Site Address + 6bit Encoder Address
				case 2:
				case 3: // Sequence Counter
					++state;
					break;
				case 4:
					leninfo=c;
					++state;
					break;
				case 5:
					switch (c)
					{
						case 0x0A: // Radiotext
							++state;
							break;
						case 0x46: // Radiotext Plus tags
							state=38;
							break;
						case 0xDA: // Rass
							state=26;
							break;
						default: // reset to state 0
							state=0;
					}
					break;

					// process Radiotext
				case 6: // Data Set Number ... ignore
				case 7: // Program Service Number ... ignore
					++state;
					break;
				case 8: // Message Element Length
					text_len=c;
					if ( !text_len || text_len > 65 || text_len > leninfo-4)
						state=0;
					else
					{
						++state;
						text_len-=2;
						msgPtr=0;
					}
					break;
				case 9: // Radio Text Status bit:
					// 0   = AB-flagcontrol
					// 1-4 = Transmission-Number
					// 5-6 = Buffer-Config
					++state; // ignore ...
					break;
				case 10:
					// TODO build a complete radiotext charcode to UTF8 conversion table for all character > 0x80
					switch (c)
					{
						case 0 ... 0x7f: break;
						case 0x8d: c='ß'; break;
						case 0x91: c='ä'; break;
						case 0xd1: c='Ä'; break;
						case 0x97: c='ö'; break;
						case 0xd7: c='Ö'; break;
						case 0x99: c='ü'; break;
						case 0xd9: c='Ü'; break;
						default: c=' '; break;  // convert all unknown to space
					}
					message[msgPtr++]=c;
					if(text_len)
						--text_len;
					else
						++state;
					break;
				case 11:
					crc16=c<<8;
					++state;
					break;
				case 12:
					crc16|=c;
					message[msgPtr--]=0;
					while(message[msgPtr] == ' ' && msgPtr > 0)
						message[msgPtr--] = 0;
					if ( crc16 == (crc^0xFFFF) )
					{
						eDebug("radiotext: (%s)", message);
						/*emit*/ m_event(RadioTextChanged);
						memcpy(lastmessage,message,66);
					}
					else
						eDebug("invalid radiotext crc (%s)", message);
					state=0;
					break;

				// process Rass
				case 26: //MEL
					text_len = c;
					text_len2 = c;
					++state;
					text_len-=9;
					text_len2-=9;
					t_ptr=0;
					break;
				case 27: // SID not used atm
					++state;
					break;
				case 28: // SID not used atm
					++state;
					break;
				case 29: // PNR packet number
					part=c<<16;
					++state;
					break;
				case 30: // PNR packet number
					part|=c<<8;
					++state;
					break;
				case 31: // PNR packet number
					part|=c;
					++state;
					break;
				case 32: // NOP number of packets
					parts=c<<16;
					++state;
					break;
				case 33: // NOP number of packets
					parts|=c<<8;
					++state;
					break;
				case 34: // NOP number of packets
					parts|=c;
					++state;
					break;
				case 35:
					datamessage[t_ptr++]=c;
					if(text_len) 
						--text_len;
					else
						++state;
					break;
				case 36:
					crc16=c<<8;
					++state;
					break;
				case 37:
					crc16|=c;
					//eDebug("[RDS/Rass] CRC read: %04X CRC calculated: %04X",crc16,crc^0xFFFF);
					state=0;
					if ( crc16 == (crc^0xFFFF) ) 
					{
						if (partcnt == -1) 
							partcnt=1;
						if (partcnt == part)
						{
							memcpy(qdar+qdar_pos,datamessage,text_len2+1);
							qdar_pos=qdar_pos+text_len2+1;
							if (partcnt == parts)
							{
								process_qdar(qdar); // decode qdar archive
								qdar_pos=0;
								partcnt=-1;
							}
							else
								++partcnt;
						}
						else
						{
							qdar_pos=0;
							partcnt=-1;
						}
					}
					else
					{
						eDebug("[RDS/Rass] CRC error, skip Rass-Qdar-Packet");
						eDebug("[RDS/Rass] CRC read: %04X CRC calculated: %04X",crc16,crc^0xFFFF);
						partcnt=-1;
					}
					state=0;
					break;

				// process RT plus tags ... 
				case 38: // Message Element Length
					text_len=c;	
					++state;
					break;
				case 39: // Application ID 
				case 40: // always 0x4BD7 so we ignore it ;)
				case 41: // Applicationgroup Typecode/PTY ... ignore
					++state;
					break;
				case 42:
					rtp_buf[0]=c;
					++state;
					break;
				case 43:
					rtp_buf[1]=c;
					++state;
					break;
				case 44:
					rtp_buf[2]=c;
					++state;
					break;
				case 45:
					rtp_buf[3]=c;
					++state;
					break;
				case 46: // bit 10#4 = Item Togglebit
					// bit 10#3 = Item Runningbit
					// Tag1: bit 10#2..11#5 = Contenttype, 11#4..12#7 = Startmarker, 12#6..12#1 = Length
					rtp_buf[4]=c;
					if (lastmessage[0] == 0) // no rds message till now ? quit ...
						break;
					int rtp_typ[2],rtp_start[2],rtp_len[2];
					rtp_typ[0]   = (0x38 & rtp_buf[0]<<3) | rtp_buf[1]>>5;
					rtp_start[0] = (0x3e & rtp_buf[1]<<1) | rtp_buf[2]>>7;
					rtp_len[0]   = 0x3f & rtp_buf[2]>>1;
					// Tag2: bit 12#0..13#3 = Contenttype, 13#2..14#5 = Startmarker, 14#4..14#0 = Length(5bit)
					rtp_typ[1]   = (0x20 & rtp_buf[2]<<5) | rtp_buf[3]>>3;
					rtp_start[1] = (0x38 & rtp_buf[3]<<3) | rtp_buf[4]>>5;
					rtp_len[1]   = 0x1f & rtp_buf[4];
									
					unsigned char rtplus_osd_tmp[64];
					
					if (rtp_start[0] < 66 && (rtp_len[0]+rtp_start[0]) < 66)
					{
						memcpy(rtp_item[rtp_typ[0]],lastmessage+rtp_start[0],rtp_len[0]+1);
						rtp_item[rtp_typ[0]][rtp_len[0]+1]=0;
					}
									
					if (rtp_typ[0] != rtp_typ[1])
					{
						if (rtp_start[1] < 66 && (rtp_len[1]+rtp_start[1]) < 66)
						{
							memcpy(rtp_item[rtp_typ[1]],lastmessage+rtp_start[1],rtp_len[1]+1);
							rtp_item[rtp_typ[1]][rtp_len[1]+1]=0;
						}
					}

					// main RTPlus item_types used by the radio stations:
					// 1 title
					// 4 artist
					// 24 info.date_time
					// 31 stationname
					// 32 program.now
					// 39 homepage
					// 41 phone.hotline
					// 46 email.hotline
					// todo: make a window to display all saved items ...
	
					//create RTPlus OSD for title/artist
					rtplus_osd[0]=0;
								
					if ( rtp_item[4][0] != 0 )//artist
						sprintf((char*)rtplus_osd_tmp," (%s)",rtp_item[4]);
								
					if ( rtp_item[1][0] != 0 )//title
						sprintf((char*)rtplus_osd,"%s%s",rtp_item[1],rtplus_osd_tmp);
									
					if ( rtplus_osd[0] != 0 )
					{
						/*emit*/ m_event(RtpTextChanged);
						eDebug("RTPlus: %s",rtplus_osd);
					}
						
					state=0;
					break;
			}
		}
	}
}

std::string eDVBRdsDecoder::getRassPicture(int page, int subpage)
{
	int val=0;
	
	switch(subpage)
	{
		case 0:
			val=page*1000;
			break;
		case 1:
			val=page*1100;
			break;
		case 2:
			val=page*1110;
			break;
		case 3:
			val=page*1111;
			break;
	}
	char fname[50];
	sprintf(fname,"/tmp/Rass%04d.mvi",val);
	return fname;
}

int eDVBRdsDecoder::start(int pid)
{
	int ret = -1;
	if (m_pes_reader && !(ret = m_pes_reader->start(pid)) && m_type == 0)
		m_abortTimer->startLongTimer(20);
	m_pid = pid;
	return ret;
}

void eDVBRdsDecoder::abortNonAvail()
{
	eDebug("no ancillary data in audio stream... abort radiotext pes parser");
	if (m_pes_reader)
		m_pes_reader->stop();
}

ePyObject eDVBRdsDecoder::getRassPictureMask()
{
	ePyObject ret = PyTuple_New(5);
	PyTuple_SET_ITEM(ret, 0, PyInt_FromLong(rass_picture_mask[0]));
	PyTuple_SET_ITEM(ret, 1, PyInt_FromLong(rass_picture_mask[1]));
	PyTuple_SET_ITEM(ret, 2, PyInt_FromLong(rass_picture_mask[2]));
	PyTuple_SET_ITEM(ret, 3, PyInt_FromLong(rass_picture_mask[3]));
	PyTuple_SET_ITEM(ret, 4, PyInt_FromLong(rass_picture_mask[4]));
	return ret;
}
