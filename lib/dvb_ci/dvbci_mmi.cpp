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
	eDVBCI_UI::getInstance()->mmiSessionDestroyed(slot->getSlotID());
}

int eDVBCIMMISession::receivedAPDU(const unsigned char *tag, const void *data, int len)
{
	eDebugNoNewLine("SESSION(%d)/MMI %02x %02x %02x: ", session_nb, tag[0], tag[1],tag[2]);
	for (int i=0; i<len; i++)
		eDebugNoNewLine("%02x ", ((const unsigned char*)data)[i]);
	eDebug("");

	if ((tag[0]==0x9f) && (tag[1]==0x88))
	{
		switch (tag[2])
		{
		case 0x00:		//Tmmi_close
		{
			unsigned char *d=(unsigned char*)data;
			int timeout=0;
			if (d[3] == 1)
			{
				if (len > 4)
					timeout = d[4];
				else
				{
					eDebug("mmi close tag incorrect.. no timeout given.. assume 5 seconds");
					timeout = 5;
				}
			}
			else if (timeout>1)
				eDebug("mmi close tag incorrect.. byte 4 should be 0 or 1");
			eDVBCI_UI::getInstance()->mmiScreenClose(slot->getSlotID(), timeout);
			break;
		}
		case 0x01:
			eDebug("MMI display control");
			if (((unsigned char*)data)[0] != 1)
				eDebug("kann ich nicht. aber das sag ich dem modul nicht.");
			state=stateDisplayReply;
			return 1;
		case 0x07:		//Tmenu_enq
		{
			unsigned char *d=(unsigned char*)data;
			unsigned char *max=((unsigned char*)d) + len;
			int textlen = len - 2;

			eDebug("in enq");
			
			if ((d+2) > max)
				break;
				
			int blind = *d++ & 1;
			int alen = *d++;

			eDebug("%d bytes text", textlen);
			if ((d+textlen) > max)
				break;
			
			char str[textlen + 1];
			memcpy(str, ((char*)d), textlen);
			str[textlen] = '\0';
			
			eDebug("enq-text: %s",str);
			
			eDVBCI_UI::getInstance()->mmiScreenEnq(slot->getSlotID(), blind, alen, (char*)convertDVBUTF8(str).c_str());

			break;		
		}
		case 0x09:		//Tmenu_last
		case 0x0c:		//Tlist_last
		{
			unsigned char *d=(unsigned char*)data;
			unsigned char *max=((unsigned char*)d) + len;
			int pos = 0;
			eDebug("Tmenu_last");
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
			eDebug("%d texts", n);
			for (int i=0; i < (n+3); ++i)
			{
				int textlen;
				if ((d+3) > max)
					break;
				eDebug("text tag: %02x %02x %02x", d[0], d[1], d[2]);
				d+=3;
				d+=parseLengthField(d, textlen);
				eDebug("%d bytes text", textlen);
				if ((d+textlen) > max)
					break;
					
				char str[textlen + 1];
				memcpy(str, ((char*)d), textlen);
				str[textlen] = '\0';
				
				eDVBCI_UI::getInstance()->mmiScreenAddText(slot->getSlotID(), pos++, (char*)convertDVBUTF8(str).c_str());
					
				while (textlen--)
					eDebugNoNewLine("%c", *d++);
				eDebug("");
			}
			eDVBCI_UI::getInstance()->mmiScreenFinish(slot->getSlotID());
			break;
		}
		default:
			eDebug("unknown APDU tag 9F 88 %02x", tag[2]);
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
	eDebug("eDVBCIMMISession::stopMMI()");

	unsigned char tag[]={0x9f, 0x88, 0x00};
	unsigned char data[]={0x00};
	sendAPDU(tag, data, 1);
	
	return 0;
}

int eDVBCIMMISession::answerText(int answer)
{
	eDebug("eDVBCIMMISession::answerText(%d)",answer);

	unsigned char tag[]={0x9f, 0x88, 0x0B};
	unsigned char data[]={0x00};
	data[0] = answer & 0xff;
	sendAPDU(tag, data, 1);
	
	return 0;
}

int eDVBCIMMISession::answerEnq(char *answer)
{
	unsigned int len = strlen(answer);
	eDebug("eDVBCIMMISession::answerEnq(%d bytes)", len);

	unsigned char data[len+1];
	data[0] = 0x01; // answer ok
	memcpy(data+1, answer, len);

	unsigned char tag[]={0x9f, 0x88, 0x08};
	sendAPDU(tag, data, len+1);

	return 0;
}

int eDVBCIMMISession::cancelEnq()
{
	eDebug("eDVBCIMMISession::cancelEnq()");

	unsigned char tag[]={0x9f, 0x88, 0x08};
	unsigned char data[]={0x00}; // canceled
	sendAPDU(tag, data, 1);
	
	return 0;
}

