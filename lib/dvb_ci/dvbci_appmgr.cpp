/* DVB CI Application Manager */

#include <lib/base/eerror.h>
#include <lib/dvb_ci/dvbci_appmgr.h>
#include <lib/dvb_ci/dvbci_ui.h>
#include <lib/base/estring.h>

eDVBCIApplicationManagerSession::eDVBCIApplicationManagerSession(eDVBCISlot *tslot)
{
	slot = tslot;
	slot->setAppManager(this);
	m_app_name = "";
}

eDVBCIApplicationManagerSession::~eDVBCIApplicationManagerSession()
{
	slot->setAppManager(NULL);
}

int eDVBCIApplicationManagerSession::receivedAPDU(const unsigned char *tag, const void *data, int len)
{
	eTraceNoNewLine("[CI%d AM] SESSION(%d)/APP %02x %02x %02x: ", slot->getSlotID(), session_nb, tag[0], tag[1], tag[2]);
	for (int i = 0; i < len; i++)
		eTraceNoNewLine("%02x ", ((const unsigned char *)data)[i]);
	eTraceNoNewLine("\n");

	if ((tag[0] == 0x9f) && (tag[1] == 0x80))
	{
		switch (tag[2])
		{
		case 0x21:
		{
			int dl;
			eDebug("[CI%d AM] application info:", slot->getSlotID());
			eDebug("[CI%d AM]   len: %d", slot->getSlotID(), len);
			eDebug("[CI%d AM]   application_type: %d", slot->getSlotID(), ((unsigned char *)data)[0]);
			eDebug("[CI%d AM]   application_manufacturer: %02x %02x", slot->getSlotID(), ((unsigned char *)data)[2], ((unsigned char *)data)[1]);
			eDebug("[CI%d AM]   manufacturer_code: %02x %02x", slot->getSlotID(), ((unsigned char *)data)[4], ((unsigned char *)data)[3]);
			dl = ((unsigned char *)data)[5];
			if ((dl + 6) > len)
			{
				eDebug("[CI%d AM] warning, invalid length (%d vs %d)", slot->getSlotID(), dl + 6, len);
				dl = len - 6;
			}
			char str[dl + 1];
			memcpy(str, ((char *)data) + 6, dl);
			str[dl] = '\0';

			m_app_name = str;
			if (m_app_name.size() > 0 && !isUTF8(m_app_name))
			{
				eDebug("[CI%d AM]   menu string is not UTF8 hex output:%s\nstr output:%s\n", slot->getSlotID(), string_to_hex(m_app_name).c_str(), m_app_name.c_str());
				m_app_name = convertLatin1UTF8(m_app_name);
				eDebug("[CI%d AM]   fixed menu string: %s", slot->getSlotID(), m_app_name.c_str());
			}
			else
			{
				eDebug("[CI%d AM]   menu string: %s", slot->getSlotID(), m_app_name.c_str());
			}
			/* emit */ eDVBCI_UI::getInstance()->m_messagepump.send(eDVBCIInterfaces::Message(eDVBCIInterfaces::Message::appNameChanged, slot->getSlotID(), m_app_name.c_str()));

			/* emit */ eDVBCI_UI::getInstance()->m_messagepump.send(eDVBCIInterfaces::Message(eDVBCIInterfaces::Message::slotStateChanged, slot->getSlotID(), 2));
			break;
		}
		default:
			eWarning("[CI%d AM] unknown APDU tag 9F 80 %02x", slot->getSlotID(), tag[2]);
			break;
		}
	}
	return 0;
}

int eDVBCIApplicationManagerSession::doAction()
{
	switch (state)
	{
	case stateStarted:
	{
		const unsigned char tag[3] = {0x9F, 0x80, 0x20}; // application manager info e    sendAPDU(tag);
		sendAPDU(tag);
		state = stateFinal;
		return 1;
	}
	case stateFinal:
		eDebug("[CI%d AM] in final state.", slot->getSlotID());
		wantmenu = 0;
		if (wantmenu)
		{
			eDebug("[CI%d AM] wantmenu: sending Tenter_menu", slot->getSlotID());
			const unsigned char tag[3] = {0x9F, 0x80, 0x22}; // Tenter_menu
			sendAPDU(tag);
			wantmenu = 0;
			return 0;
		}
		else
			return 0;
	default:
		return 0;
	}
}

int eDVBCIApplicationManagerSession::startMMI()
{
	eDebug("[CI%d AM] in appmanager -> startmmi()", slot->getSlotID());
	const unsigned char tag[3] = {0x9F, 0x80, 0x22}; // Tenter_menu
	sendAPDU(tag);
	return 0;
}
