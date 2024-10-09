/* DVB CI Resource Manager */

#include <lib/base/eerror.h>
#include <lib/dvb_ci/dvbci_resmgr.h>
#include <lib/dvb_ci/dvbci_ccmgr_helper.h>

int eDVBCIResourceManagerSession::receivedAPDU(const unsigned char *tag,const void *data, int len)
{
	eTraceNoNewLineStart("[CI%d RM] SESSION(%d) %02x %02x %02x: ", slot->getSlotID(), session_nb, tag[0], tag[1], tag[2]);
	for (int i=0; i<len; i++)
		eTraceNoNewLineStart("%02x ", ((const unsigned char*)data)[i]);
	eTraceNoNewLineStart("\n");
	if ((tag[0]==0x9f) && (tag[1]==0x80))
	{
		switch (tag[2])
		{
		case 0x10:  // profile enquiry
			eDebug("[CI%d RM] cam profile inquiry", slot->getSlotID());
			state=stateProfileEnquiry;
			return 1;
			break;
		case 0x11: // Tprofile
			eDebugNoNewLineStart("[CI%d RM] can do: ", slot->getSlotID());
			if (!len)
				eDebugNoNewLine("nothing");
			else
				for (int i=0; i<len; i++)
					eDebugNoNewLine("%02x ", ((const unsigned char*)data)[i]);
			eDebugNoNewLine("\n");

			if (state == stateFirstProfileEnquiry)
			{
				// profile change
				return 1;
			}
			state=stateFinal;
			break;
		default:
			eWarning("[CI%d RM] unknown APDU tag 9F 80 %02x", slot->getSlotID(), tag[2]);
		}
	}

	return 0;
}

int eDVBCIResourceManagerSession::doAction()
{
	switch (state)
	{
	case stateStarted:
	{
		const unsigned char tag[3]={0x9F, 0x80, 0x10}; // profile enquiry
		sendAPDU(tag);
		state = stateFirstProfileEnquiry;
		return 0;
	}
	case stateFirstProfileEnquiry:
	{
		const unsigned char tag[3]={0x9F, 0x80, 0x12}; // profile change
		sendAPDU(tag);
		state=stateProfileChange;
		return 0;
	}
	case stateProfileChange:
	{
		eWarning("[CI%d RM] cannot deal with statProfileChange", slot->getSlotID());
		break;
	}
	case stateProfileEnquiry:
	{
		const unsigned char tag[3]={0x9F, 0x80, 0x11};
		const unsigned char data[][4]=
			{
				{0x00, 0x01, 0x00, 0x41},
				{0x00, 0x02, 0x00, 0x41},
				{0x00, 0x03, 0x00, 0x41},
//				{0x00, 0x20, 0x00, 0x41}, // host control
				{0x00, 0x24, 0x00, 0x41},
				{0x00, 0x40, 0x00, 0x41},
//				{0x00, 0x10, 0x00, 0x41}, // auth.
			};
		const unsigned char data_v2[][4]=
			{
				{0x00, 0x01, 0x00, 0x41}, // res mgr 1
//				{0x00, 0x01, 0x00, 0x42}, // res mgr 2
				{0x00, 0x02, 0x00, 0x41}, // app mgr 1
				{0x00, 0x02, 0x00, 0x42}, // app mgr 2
				{0x00, 0x02, 0x00, 0x43}, // app mgr 3
				{0x00, 0x02, 0x00, 0x45}, // app mgr 5
				{0x00, 0x03, 0x00, 0x41}, // ca mgr
				{0x00, 0x20, 0x00, 0x41}, // host ctrl 1
				{0x00, 0x20, 0x00, 0x42}, // host ctrl 2
				{0x00, 0x20, 0x00, 0x43}, // host ctrl 3
				{0x00, 0x24, 0x00, 0x41}, // datetime
				{0x00, 0x40, 0x00, 0x41}, // mmi
//				{0x00, 0x10, 0x00, 0x41},
				{0x00, 0x41, 0x00, 0x41}, // app mmi 1
				{0x00, 0x41, 0x00, 0x42}, // app mmi 2
				{0x00, 0x8c, 0x10, 0x01}, // content ctrl 1
				{0x00, 0x8c, 0x10, 0x02}, // content ctrl 2
				{0x00, 0x8c, 0x10, 0x04}, // content ctrl 4
				{0x00, 0x8d, 0x10, 0x01}, // Host lang ctrl
				{0x00, 0x8e, 0x10, 0x01}, // Cam upgrade
				{0x00, 0x8f, 0x10, 0x01}, // operator profile 1
				{0x00, 0x8f, 0x10, 0x02}, // operator profile 2
//				{0x00, 0x97, 0x10, 0x01},
//				{0x00, 0x60, 0x60, 0x03},
//				{0x00, 0x04, 0x10, 0x01},
			};
		const unsigned char data_v2_no_operator[][4]=
			{
				{0x00, 0x01, 0x00, 0x41}, // res mgr 1
//				{0x00, 0x01, 0x00, 0x42}, // res mgr 2
				{0x00, 0x02, 0x00, 0x41}, // app mgr 1
				{0x00, 0x02, 0x00, 0x42}, // app mgr 2
				{0x00, 0x02, 0x00, 0x43}, // app mgr 3
				{0x00, 0x02, 0x00, 0x45}, // app mgr 5
				{0x00, 0x03, 0x00, 0x41}, // ca mgr
				{0x00, 0x20, 0x00, 0x41}, // host ctrl 1
				{0x00, 0x20, 0x00, 0x42}, // host ctrl 2
				{0x00, 0x20, 0x00, 0x43}, // host ctrl 3
				{0x00, 0x24, 0x00, 0x41}, // datetime
				{0x00, 0x40, 0x00, 0x41}, // mmi
//				{0x00, 0x10, 0x00, 0x41},
				{0x00, 0x41, 0x00, 0x41}, // app mmi 1
				{0x00, 0x41, 0x00, 0x42}, // app mmi 2
				{0x00, 0x8c, 0x10, 0x01}, // content ctrl 1
				{0x00, 0x8c, 0x10, 0x02}, // content ctrl 2
				{0x00, 0x8c, 0x10, 0x04}, // content ctrl 4
				{0x00, 0x8d, 0x10, 0x01}, // Host lang ctrl
				{0x00, 0x8e, 0x10, 0x01}, // Cam upgrade
				//{0x00, 0x8f, 0x10, 0x01}, // operator profile 1
				//{0x00, 0x8f, 0x10, 0x02}, // operator profile 2
//				{0x00, 0x97, 0x10, 0x01},
//				{0x00, 0x60, 0x60, 0x03},
//				{0x00, 0x04, 0x10, 0x01},
			};
		
		bool operator_profile_disabled = slot->getIsOperatorProfileDisabled();

		bool ciplus = ciplus_cert_param_files_exists();
		const void *p = ciplus ? (operator_profile_disabled ? data_v2_no_operator : data_v2) : data;
		int len = ciplus ? (operator_profile_disabled ? sizeof(data_v2_no_operator) : sizeof(data_v2)) : sizeof(data);
		sendAPDU(tag, p, len);
		state=stateFinal;
		return 0;
	}
	case stateFinal:
		eWarning("[CI%d RM] Should not happen: action on stateFinal", slot->getSlotID());
	default:
		break;
	}
	return 0;
}
