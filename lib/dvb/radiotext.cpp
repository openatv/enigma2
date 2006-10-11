#include <lib/base/eerror.h>
#include <lib/dvb/radiotext.h>
#include <lib/dvb/idemux.h>
#include <lib/gdi/gpixmap.h>

DEFINE_REF(eDVBRadioTextParser);

eDVBRadioTextParser::eDVBRadioTextParser(iDVBDemux *demux)
	:bytesread(0), ptr(0), p1(-1), p2(-1), msgPtr(0), state(0)
{
	setStreamID(0xC0, 0xC0);

	if (demux->createPESReader(eApp, m_pes_reader))
		eDebug("failed to create PES reader!");
	else
		m_pes_reader->connectRead(slot(*this, &eDVBRadioTextParser::processData), m_read_connection);
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

void eDVBRadioTextParser::connectUpdatedRadiotext(const Slot0<void> &slot, ePtr<eConnection> &connection)
{
	connection = new eConnection(this, m_updated_radiotext.connect(slot));
}

void eDVBRadioTextParser::processPESPacket(__u8 *data, int len)
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
		int protection_bit = data[pos + 1] & 1;
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
			int ancillary_len = 1 + data[offs - 1];
			offs -= ancillary_len;
			while(offs < pos)
				gotAncillaryByte(data[offs++]);
		}
	}
}

void eDVBRadioTextParser::gotAncillaryByte(__u8 data)
{
	buf[bytesread]=data;
	bytesread+=1;
	if ( bytesread == 128 )
	{
		while(ptr<128)
		{
			if ( buf[ptr] == 0xFD )
			{
				if (p1 == -1)
					p1 = ptr;
				else
					p2 = ptr;
			}
			if ( p1 != -1 && p2 != -1 )
			{
				int cnt=buf[--p2];
				while ( cnt-- > 0 )
				{
					unsigned char c = buf[--p2];
					if ( state == 1 )
						crc=0xFFFF;
					if ( state >= 1 && state < 11 )
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
							if ( c==0x0A ) // message element code 0x0A Radio Text
								++state;
							else
								state=0;
							break;
						case 6: // Data Set Number ... ignore
						case 7: // Program Service Number ... ignore
							++state;
							break;
						case 8: // Message Element Length
							todo=c;
							if ( !todo || todo > 65 || todo > leninfo-4)
								state=0;
							else
							{
								++state;
								todo-=2;
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
							if(todo)
								--todo;
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
								/*emit*/ m_updated_radiotext();
							}
							else
								eDebug("invalid radiotext crc (%s)", message);
							state=0;
							break;
					}
				}
				p1=ptr;
				p2=-1;
			}
			++ptr;
		}
		if (p1 != -1 && (128-p1) != 128)
		{
			bytesread=ptr=128-p1;
			memcpy(buf, buf+p1, ptr);
			p1=0;
		}
		else
			bytesread=ptr=0;
	}
}

int eDVBRadioTextParser::start(int pid)
{
	if (m_pes_reader)
		return m_pes_reader->start(pid);
	else
		return -1;
}

