/* DVB CI MMI */

#include <lib/dvb_ci/dvbci_mmi.h>
#include <lib/dvb_ci/dvbci_ui.h>
#include <lib/base/estring.h>

/*
PyObject *list = PyList_New(len);
for (i=0; i<len; ++i) {
	PyObject *tuple = PyTuple_New(3); // 3 eintrge im tuple
	PyTuple_SetItem(tuple, 0, PyString_FromString("eintrag 1"))
	PyTuple_SetItem(tuple, 1, PyInt_FromLong(31337));
	PyTuple_SetItem(tuple, 2, PyString_FromString("eintrag 3"))
	PyList_SetItem(list, i, tuple);
}
return list;
*/

eDVBCIMMISession::eDVBCIMMISession(eDVBCISlot *tslot)
{
	slot = tslot;
	slot->setMMIManager(this);
}

eDVBCIMMISession::~eDVBCIMMISession()
{
	slot->setMMIManager(NULL);
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
		case 0x07:		//Tmenu_enq
		{
			unsigned char *d=(unsigned char*)data;
			unsigned char *max=((unsigned char*)d) + len;
			int textlen = len - 2;

			printf("in enq\n");
			
			if ((d+2) > max)
				break;
				
			int blind = *d++ & 1;
			int alen = *d++;

			printf("%d bytes text\n", textlen);
			if ((d+textlen) > max)
				break;
			
			char str[textlen + 1];
			memcpy(str, ((char*)d), textlen);
			str[textlen] = '\0';
			
			printf("enq-text: %s\n",str);
			
			eDVBCI_UI::getInstance()->mmiScreenEnq(slot->getSlotID(), blind, alen, (char*)convertDVBUTF8(str).c_str());

			break;		
		}
		case 0x09:		//Tmenu_last
		case 0x0c:		//Tlist_last
		{
			unsigned char *d=(unsigned char*)data;
			unsigned char *max=((unsigned char*)d) + len;
			int pos = 0;
			printf("Tmenu_last\n");
			if (d > max)
				break;
			int n=*d++;
			
			if(tag[2] == 0x09)	//menu
				eDVBCI_UI::getInstance()->mmiScreenBegin(slot->getSlotID(), 0);
			else								//list
				eDVBCI_UI::getInstance()->mmiScreenBegin(slot->getSlotID(), 1);
			
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
					
				char str[textlen + 1];
				memcpy(str, ((char*)d), textlen);
				str[textlen] = '\0';
				
				eDVBCI_UI::getInstance()->mmiScreenAddText(slot->getSlotID(), pos++, (char*)convertDVBUTF8(str).c_str());
					
				while (textlen--)
					printf("%c", *d++);
				printf("\n");
			}
			eDVBCI_UI::getInstance()->mmiScreenFinish(slot->getSlotID());
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
		state=stateIdle;
		//state=stateFakeOK;
		//return 1;
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
	
	return 0;
}

int eDVBCIMMISession::answerText(int answer)
{
	printf("eDVBCIMMISession::answerText(%d)\n",answer);

	unsigned char tag[]={0x9f, 0x88, 0x0B};
	unsigned char data[]={0x00};
	data[0] = answer & 0xff;
	sendAPDU(tag, data, 1);
	
	return 0;
}

int eDVBCIMMISession::answerEnq(char *answer)
{
	unsigned int len = strlen(answer);
	printf("eDVBCIMMISession::answerEnq(%d bytes)\n", len);

	unsigned char data[len+1];
	data[0] = 0x01; // answer ok
	memcpy(data+1, answer, len);

	unsigned char tag[]={0x9f, 0x88, 0x08};
	sendAPDU(tag, data, len+1);

	return 0;
}

int eDVBCIMMISession::cancelEnq()
{
	printf("eDVBCIMMISession::cancelEnq()\n");

	unsigned char tag[]={0x9f, 0x88, 0x08};
	unsigned char data[]={0x00}; // canceled
	sendAPDU(tag, data, 1);
	
	return 0;
}

