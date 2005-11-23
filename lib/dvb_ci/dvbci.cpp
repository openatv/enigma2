#include <fcntl.h>
#include <sys/ioctl.h>

#include <lib/base/init.h>
#include <lib/base/init_num.h>
#include <lib/base/ebase.h>

#include <lib/base/eerror.h>
#include <lib/dvb/pmt.h>
#include <lib/dvb_ci/dvbci.h>
#include <lib/dvb_ci/dvbci_session.h>
#include <lib/dvb_ci/dvbci_camgr.h>
#include <lib/dvb_ci/dvbci_ui.h>
#include <lib/dvb_ci/dvbci_appmgr.h>
#include <lib/dvb_ci/dvbci_mmi.h>

#include <dvbsi++/ca_program_map_section.h>

eDVBCIInterfaces *eDVBCIInterfaces::instance = 0;

eDVBCIInterfaces::eDVBCIInterfaces()
{
	int num_ci = 0;
	
	instance = this;
	
	eDebug("scanning for common interfaces..");

	while (1)
	{
		struct stat s;
		char filename[128];
		sprintf(filename, "/dev/ci%d", num_ci);

		if (stat(filename, &s))
			break;

		ePtr<eDVBCISlot> cislot;

		cislot = new eDVBCISlot(eApp, num_ci);
		m_slots.push_back(cislot);

		++num_ci;
	}

	eDebug("done, found %d common interface slots", num_ci);
}

eDVBCIInterfaces::~eDVBCIInterfaces()
{
}

eDVBCIInterfaces *eDVBCIInterfaces::getInstance()
{
	return instance;
}

eDVBCISlot *eDVBCIInterfaces::getSlot(int slotid)
{
	for(eSmartPtrList<eDVBCISlot>::iterator i(m_slots.begin()); i != m_slots.end(); ++i)
		if(i->getSlotID() == slotid)
			return i;

	printf("FIXME: request for unknown slot\n");
			
	return 0;
}

int eDVBCIInterfaces::reset(int slotid)
{
	eDVBCISlot *slot;

	if( (slot = getSlot(slotid)) == 0 )
		return -1;
	
	return slot->reset();
}

int eDVBCIInterfaces::initialize(int slotid)
{
	eDVBCISlot *slot;

	if( (slot = getSlot(slotid)) == 0 )
		return -1;
	
	return slot->initialize();
}

int eDVBCIInterfaces::startMMI(int slotid)
{
	eDVBCISlot *slot;

	if( (slot = getSlot(slotid)) == 0 )
		return -1;
	
	return slot->startMMI();
}

int eDVBCIInterfaces::stopMMI(int slotid)
{
	eDVBCISlot *slot;

	if( (slot = getSlot(slotid)) == 0 )
		return -1;
	
	return slot->stopMMI();
}

int eDVBCIInterfaces::answerText(int slotid, int answer)
{
	eDVBCISlot *slot;

	if( (slot = getSlot(slotid)) == 0 )
		return -1;
	
	return slot->answerText(answer);
}

int eDVBCIInterfaces::answerEnq(int slotid, char *value)
{
	eDVBCISlot *slot;

	if( (slot = getSlot(slotid)) == 0 )
		return -1;
	
	return slot->answerEnq(value);
}

int eDVBCIInterfaces::cancelEnq(int slotid)
{
	eDVBCISlot *slot;

	if( (slot = getSlot(slotid)) == 0 )
		return -1;
	
	return slot->cancelEnq();
}

void eDVBCIInterfaces::addPMTHandler(eDVBServicePMTHandler *pmthandler)
{
	CIPmtHandler new_handler(pmthandler);

	eServiceReferenceDVB service;
	pmthandler->getService(service);

	PMTHandlerSet::iterator it = m_pmt_handlers.begin();
	while (it != m_pmt_handlers.end())
	{
		eServiceReferenceDVB ref;
		it->pmthandler->getService(ref);
		if ( service == ref && it->usedby )
			new_handler.usedby = it->usedby;
		break;
	}
	m_pmt_handlers.insert(new_handler);
}

void eDVBCIInterfaces::removePMTHandler(eDVBServicePMTHandler *pmthandler)
{
	PMTHandlerSet::iterator it=m_pmt_handlers.find(pmthandler);
	if (it != m_pmt_handlers.end())
	{
		eDVBCISlot *slot = it->usedby;
		eDVBServicePMTHandler *pmthandler = it->pmthandler;
		m_pmt_handlers.erase(it);
		if (slot)
		{
			eServiceReferenceDVB removed_service;
			pmthandler->getService(removed_service);
			PMTHandlerSet::iterator it=m_pmt_handlers.begin();
			while (it != m_pmt_handlers.end())
			{
				eServiceReferenceDVB ref;
				it->pmthandler->getService(ref);
				if (ref == removed_service)
					break;
				++it;
			}
			if ( it == m_pmt_handlers.end() && slot->getPrevSentCAPMTVersion() != 0xFF  )
			{
				std::vector<uint16_t> caids;
				caids.push_back(0xFFFF);
				slot->sendCAPMT(pmthandler, caids);
			}
		}
	}
}

void eDVBCIInterfaces::gotPMT(eDVBServicePMTHandler *pmthandler)
{
	eDebug("[eDVBCIInterfaces] gotPMT");
	PMTHandlerSet::iterator it=m_pmt_handlers.find(pmthandler);
	eServiceReferenceDVB service;
	if ( it != m_pmt_handlers.end() )
	{
		eDebug("[eDVBCIInterfaces] usedby %p", it->usedby);
		if (!it->usedby)
		{
			// HACK this assigns ALL RUNNING SERVICES to the first free CI !!!
			for (eSmartPtrList<eDVBCISlot>::iterator ci_it(m_slots.begin()); ci_it != m_slots.end(); ++ci_it)
			{
/*				eDVBCISlot **usedby = &it->usedby;
				*usedby = ci_it;
				(*usedby)->resetPrevSentCAPMTVersion();
				break;
				*/
			}
		}
		if (it->usedby)
			it->usedby->sendCAPMT(pmthandler);
	}
}

int eDVBCIInterfaces::getMMIState(int slotid)
{
	eDVBCISlot *slot;

	if( (slot = getSlot(slotid)) == 0 )
		return -1;
	
	return slot->getMMIState();
}

int eDVBCISlot::send(const unsigned char *data, size_t len)
{
	int res;
	//int i;
	//printf("< ");
	//for(i=0;i<len;i++)
	//	printf("%02x ",data[i]);
	//printf("\n");

	res = ::write(fd, data, len);

	//printf("write() %d\n",res);

	notifier->setRequested(eSocketNotifier::Read | eSocketNotifier::Priority | eSocketNotifier::Write);

	return res;
}

void eDVBCISlot::data(int what)
{
	if(what == eSocketNotifier::Priority) {
		if(state != stateRemoved) {
			state = stateRemoved;
			printf("ci removed\n");
			notifier->setRequested(eSocketNotifier::Read);
			//HACK
			eDVBCI_UI::getInstance()->setState(0,0);
		}
		return;
	}

	__u8 data[4096];
	int r;
	r = ::read(fd, data, 4096);

	if(state != stateInserted) {
		state = stateInserted;
		eDebug("ci inserted");

		//HACK
		eDVBCI_UI::getInstance()->setState(0,1);

		/* enable PRI to detect removal or errors */
		notifier->setRequested(eSocketNotifier::Read|eSocketNotifier::Priority|eSocketNotifier::Write);
	}

	if(r > 0) {
		//int i;
		//printf("> ");
		//for(i=0;i<r;i++)
		//	printf("%02x ",data[i]);
		//printf("\n");
		eDVBCISession::receiveData(this, data, r);
		notifier->setRequested(eSocketNotifier::Read|eSocketNotifier::Priority|eSocketNotifier::Write);
		return;
	}

	if(what == eSocketNotifier::Write) {
		if(eDVBCISession::pollAll() == 0) {
			notifier->setRequested(eSocketNotifier::Read | eSocketNotifier::Priority);
		}
	}
}

DEFINE_REF(eDVBCISlot);

eDVBCISlot::eDVBCISlot(eMainloop *context, int nr)
{
	char filename[128];

	application_manager = 0;
	mmi_session = 0;
	ca_manager = 0;
	
	slotid = nr;

	sprintf(filename, "/dev/ci%d", nr);

	fd = ::open(filename, O_RDWR | O_NONBLOCK);

	eDebug("eDVBCISlot has fd %d", fd);
	
	state = stateInserted;

	if (fd >= 0)
	{
		notifier = new eSocketNotifier(context, fd, eSocketNotifier::Read | eSocketNotifier::Priority);
		CONNECT(notifier->activated, eDVBCISlot::data);
	} else
	{
		perror(filename);
	}
}

eDVBCISlot::~eDVBCISlot()
{
}

int eDVBCISlot::getSlotID()
{
	return slotid;
}

int eDVBCISlot::reset()
{
	printf("edvbcislot: reset requested\n");

	ioctl(fd, 0);

	return 0;
}

int eDVBCISlot::initialize()
{
	printf("edvbcislot: initialize()\n");
	return 0;
}

int eDVBCISlot::startMMI()
{
	printf("edvbcislot: startMMI()\n");
	
	if(application_manager)
		application_manager->startMMI();
	
	return 0;
}

int eDVBCISlot::stopMMI()
{
	printf("edvbcislot: stopMMI()\n");

	if(mmi_session)
		mmi_session->stopMMI();
	
	return 0;
}

int eDVBCISlot::answerText(int answer)
{
	printf("edvbcislot: answerText(%d)\n", answer);

	if(mmi_session)
		mmi_session->answerText(answer);

	return 0;
}

int eDVBCISlot::getMMIState()
{
	if(mmi_session)
		return 1;

	return 0;
}

int eDVBCISlot::answerEnq(char *value)
{
	printf("edvbcislot: answerENQ(%s)\n", value);
	return 0;
}

int eDVBCISlot::cancelEnq()
{
	printf("edvbcislot: cancelENQ\n");

	if(mmi_session)
		mmi_session->cancelEnq();

	return 0;
}

int eDVBCISlot::sendCAPMT(eDVBServicePMTHandler *pmthandler, const std::vector<uint16_t> &ids)
{
	const std::vector<uint16_t> &caids = ids.empty() && ca_manager ? ca_manager->getCAIDs() : ids;
	ePtr<eTable<ProgramMapSection> > ptr;
	if (pmthandler->getPMT(ptr))
		return -1;
	else
	{
		eDVBTableSpec table_spec;
		ptr->getSpec(table_spec);
		int pmt_version = table_spec.version & 0x1F; // just 5 bits
		if ( pmt_version == prev_sent_capmt_version )
		{
			eDebug("[eDVBCISlot] dont sent self capmt version twice");
			return -1;
		}
		std::vector<ProgramMapSection*>::const_iterator i=ptr->getSections().begin();
		if ( i == ptr->getSections().end() )
			return -1;
		else
		{
			unsigned char raw_data[2048];
			CaProgramMapSection capmt(*i++, prev_sent_capmt_version != 0xFF ? 0x05 /*update*/ : 0x03 /*only*/, 0x01, caids );
			while( i != ptr->getSections().end() )
			{
		//			eDebug("append");
				capmt.append(*i++);
			}
			capmt.writeToBuffer(raw_data);
#if 1
// begin calc capmt length
			int wp=0;
			int hlen;
			if ( raw_data[3] & 0x80 )
			{
				int i=0;
				int lenbytes = raw_data[3] & ~0x80;
				while(i < lenbytes)
					wp = (wp << 8) | raw_data[4 + i++];
				wp+=4;
				wp+=lenbytes;
				hlen = 4 + lenbytes;
			}
			else
			{
				wp = raw_data[3];
				wp+=4;
				hlen = 4;
			}
// end calc capmt length
			if (!ca_manager)
				eDebug("no ca_manager !!! dump unfiltered capmt:");
			else
				eDebug("ca_manager %p dump capmt:", ca_manager);
			for(int i=0;i<wp;i++)
				eDebugNoNewLine("%02x ", raw_data[i]);
			eDebug("");
#endif
			if (ca_manager)
			{
				//dont need tag and lenfield
				ca_manager->sendCAPMT(raw_data + hlen, wp - hlen);
				prev_sent_capmt_version = pmt_version;
			}
		}
	}
	
}

eAutoInitP0<eDVBCIInterfaces> init_eDVBCIInterfaces(eAutoInitNumbers::dvb, "CI Slots");
