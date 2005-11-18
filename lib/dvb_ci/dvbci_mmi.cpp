/* DVB CI MMI */

#include <lib/dvb_ci/dvbci_mmi.h>

eDVBCIMMISession::eDVBCIMMISession(eDVBCISlot *tslot)
{
	slot = tslot;
	slot->mmi_session = this;
}

eDVBCIMMISession::~eDVBCIMMISession()
{
	slot->mmi_session = 0;
}

int eDVBCIMMISession::receivedAPDU(const unsigned char *tag, const void *data, int len)
{
	printf("SESSION(%d)/MMI %02x %02x %02x: ", session_nb, tag[0], tag[1],tag[2]);
	for (int i=0; i<len; i++)
		printf("%02x ", ((const unsigned char*)data)[i]);
	printf("\n");

	if ((tag[0]==0x9f) && (tag[1]==0x88))
	{
		switch (tag[2])
		{
			case 0x01:
			printf("MMI display control\n");
			if (((unsigned char*)data)[0] != 1)
				printf("kann ich nicht. aber das sag ich dem modul nicht.\n");
			state=stateDisplayReply;
			return 1;
		case 0x09:
		case 0x0c:
		{
			unsigned char *d=(unsigned char*)data;
			unsigned char *max=((unsigned char*)d) + len;
			printf("Tmenu_last\n");
			if (d > max)
				break;
			int n=*d++;
			if (n == 0xFF)
				n=0;
			else
				n++;
			printf("%d texts\n", n);
			for (int i=0; i < (n+3); ++i)
			{
				int textlen;
				if ((d+3) > max)
					break;
				printf("text tag: %02x %02x %02x\n", d[0], d[1], d[2]);
				d+=3;
				d+=parseLengthField(d, textlen);
				printf("%d bytes text\n", textlen);
				if ((d+textlen) > max)
					break;
				while (textlen--)
					printf("%c", *d++);
				printf("\n");
			}
			break;
		}
		default:
			printf("unknown APDU tag 9F 88 %02x\n", tag[2]);
			break;
		}
	}
	return 0;
}

int eDVBCIMMISession::doAction()
{
	switch (state)
	{
	case stateStarted:
		state=stateIdle;
		break;
	case stateDisplayReply:
	{
		unsigned char tag[]={0x9f, 0x88, 0x02};
		unsigned char data[]={0x01, 0x01};
		sendAPDU(tag, data, 2);
		state=stateFakeOK;
		return 1;
		break;
	}
	case stateFakeOK:
	{
		unsigned char tag[]={0x9f, 0x88, 0x0b};
		unsigned char data[]={5};
		sendAPDU(tag, data, 1);
		state=stateIdle;
		break;
	}
	case stateIdle:
		break;
	default:
		break;
	}
	return 0;
}

int eDVBCIMMISession::stopMMI()
{
	printf("eDVBCIMMISession::stopMMI()\n");

	unsigned char tag[]={0x9f, 0x88, 0x00};
	unsigned char data[]={0x00};
	sendAPDU(tag, data, 1);
}

