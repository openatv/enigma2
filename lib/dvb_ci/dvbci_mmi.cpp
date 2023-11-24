/* DVB CI MMI */

#include <lib/dvb_ci/dvbci_mmi.h>
#include <lib/dvb_ci/dvbci_ui.h>

#include <string>

/*
PyObject *list = PyList_New(len);
for (i=0; i<len; ++i) {
	PyObject *tuple = PyTuple_New(3); // 3 eintrge im tuple
	PyTuple_SetItem(tuple, 0, PyUnicode_FromString("eintrag 1"))
	PyTuple_SetItem(tuple, 1, PyLong_FromLong(31337));
	PyTuple_SetItem(tuple, 2, PyUnicode_FromString("eintrag 3"))
	PyList_SetItem(list, i, tuple);
}
return list;
*/

eDVBCIMMISession::eDVBCIMMISession(eDVBCISlot *tslot)
{
	slot = tslot;
	slot->setMMIManager(this);
	is_mmi_active = false;
}

eDVBCIMMISession::~eDVBCIMMISession()
{
	slot->setMMIManager(NULL);
	if (is_mmi_active)
		/* emit */ eDVBCI_UI::getInstance()->m_messagepump.send(eDVBCIInterfaces::Message(eDVBCIInterfaces::Message::mmiSessionDestroyed, slot->getSlotID()));
}

int eDVBCIMMISession::receivedAPDU(const unsigned char *tag, const void *data, int len)
{
	eTraceNoNewLineStart("[CI%d MMI] SESSION(%d)/MMI %02x %02x %02x: ", slot->getSlotID(), session_nb, tag[0], tag[1],tag[2]);
	for (int i=0; i<len; i++)
		eTraceNoNewLineStart("%02x ", ((const unsigned char*)data)[i]);
	eTraceNoNewLineStart("\n");

	if ((tag[0]==0x9f) && (tag[1]==0x88))
	{
		/* emit */ eDVBCI_UI::getInstance()->m_messagepump.send(eDVBCIInterfaces::Message(eDVBCIInterfaces::Message::mmiDataReceived, slot->getSlotID(), tag, (unsigned char*) data, len));
		if (tag[2] == 0x01)
		{
			state=stateDisplayReply;
			return 1;
		}
		else
			is_mmi_active = true;
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
	eDebug("[CI%d MMI] eDVBCIMMISession::stopMMI()", slot->getSlotID());

	unsigned char tag[]={0x9f, 0x88, 0x00};
	unsigned char data[]={0x00};
	sendAPDU(tag, data, 1);

	return 0;
}

int eDVBCIMMISession::answerText(int answer)
{
	eDebug("[CI%d MMI] eDVBCIMMISession::answerText(%d)", slot->getSlotID(), answer);

	unsigned char tag[]={0x9f, 0x88, 0x0B};
	unsigned char data[]={0x00};
	data[0] = answer & 0xff;
	sendAPDU(tag, data, 1);

	return 0;
}

int eDVBCIMMISession::answerEnq(char *answer)
{
	unsigned int len = strlen(answer);
	eDebug("[CI%d MMI] eDVBCIMMISession::answerEnq(%d bytes)", slot->getSlotID(), len);

	unsigned char data[len+1];
	data[0] = 0x01; // answer ok
	memcpy(data+1, answer, len);

	unsigned char tag[]={0x9f, 0x88, 0x08};
	sendAPDU(tag, data, len+1);

	return 0;
}

int eDVBCIMMISession::cancelEnq()
{
	eDebug("[CI%d MMI] eDVBCIMMISession::cancelEnq()", slot->getSlotID());

	unsigned char tag[]={0x9f, 0x88, 0x08};
	unsigned char data[]={0x00}; // canceled
	sendAPDU(tag, data, 1);

	return 0;
}

