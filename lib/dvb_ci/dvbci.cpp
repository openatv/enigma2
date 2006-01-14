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

	eDVBCISession::deleteSessions(slot);

	return slot->reset();
}

int eDVBCIInterfaces::enableTS(int slotid, int enable)
{
	eDVBCISlot *slot;

	if( (slot = getSlot(slotid)) == 0 )
		return -1;

	int tunernum = 0;
	if (enable)
	{
		tunernum=-1;
		PMTHandlerList::iterator it = m_pmt_handlers.begin();
		while (it != m_pmt_handlers.end())
		{
			if ( it->cislot == slot )
			{
				eDVBServicePMTHandler *pmthandler = it->pmthandler;
				eUsePtr<iDVBChannel> channel;
				if (!pmthandler->getChannel(channel))
				{
					ePtr<iDVBFrontend> frontend;
					if (!channel->getFrontend(frontend))
					{
						eDVBFrontend *fe = (eDVBFrontend*) &(*frontend);
						tunernum = fe->getID();
					}
				}
				break;
			}
			++it;
		}
		if ( tunernum == -1 )
		{
			eFatal("couldn't find the correct tuner num in enableTS");
			return -1;
		}
	}
	return slot->enableTS(enable, tunernum);
}

int eDVBCIInterfaces::initialize(int slotid)
{
	eDVBCISlot *slot;

	if( (slot = getSlot(slotid)) == 0 )
		return -1;

	slot->resetPrevSentCAPMTVersion();
	PMTHandlerList::iterator it = m_pmt_handlers.begin();
	while (it != m_pmt_handlers.end())
	{
		if ( it->cislot == slot )
		{
			slot->sendCAPMT(it->pmthandler);  // send capmt
			break;
		}
		++it;
	}

	return slot->initialize();
}

int eDVBCIInterfaces::sendCAPMT(int slotid)
{
	eDVBCISlot *slot;

	if( (slot = getSlot(slotid)) == 0 )
		return -1;

	slot->resetPrevSentCAPMTVersion();
	PMTHandlerList::iterator it = m_pmt_handlers.begin();
	while (it != m_pmt_handlers.end())
	{
		if ( it->cislot == slot )
		{
			slot->sendCAPMT(it->pmthandler);  // send capmt
			return 0;
		}
		++it;
	}

	return -1;
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

	eDebug("[eDVBCIInterfaces] addPMTHandler %s", service.toString().c_str());

	// HACK the first service get the CI..
	eSmartPtrList<eDVBCISlot>::iterator ci_it(m_slots.begin());
	for (; ci_it != m_slots.end(); ++ci_it)
	{
		if (ci_it->use_count)
			continue;
		ci_it->use_count=1;
		new_handler.cislot = ci_it;
		new_handler.cislot->resetPrevSentCAPMTVersion();
	}

	if (ci_it == m_slots.end())
	{
		PMTHandlerList::iterator it = m_pmt_handlers.begin();
		while (it != m_pmt_handlers.end())
		{
			eServiceReferenceDVB ref;
			it->pmthandler->getService(ref);
			if ( service == ref && it->cislot )
			{
				new_handler.cislot = it->cislot;
				++new_handler.cislot->use_count;
				break;
			}
			++it;
		}
	}

	m_pmt_handlers.push_back(new_handler);
}

void eDVBCIInterfaces::removePMTHandler(eDVBServicePMTHandler *pmthandler)
{
	PMTHandlerList::iterator it=std::find(m_pmt_handlers.begin(),m_pmt_handlers.end(),pmthandler);
	if (it != m_pmt_handlers.end())
	{
		eDVBCISlot *slot = it->cislot;
//		eDVBServicePMTHandler *pmthandler = it->pmthandler;
		m_pmt_handlers.erase(it);
		if (slot && !--slot->use_count)
		{
#if 0
			eDebug("[eDVBCIInterfaces] remove last pmt handler for service %s send empty capmt");
			std::vector<uint16_t> caids;
			caids.push_back(0xFFFF);
			slot->resetPrevSentCAPMTVersion();
			slot->sendCAPMT(pmthandler, caids);
#endif
	// check if another service is running
			it = m_pmt_handlers.begin();
			while (it != m_pmt_handlers.end())
			{
				if ( !it->cislot )
				{
					it->cislot = slot;
					++slot->use_count;
					slot->resetPrevSentCAPMTVersion();
					slot->sendCAPMT(it->pmthandler);
					break;
				}
				++it;
			}
		}
	}
}

void eDVBCIInterfaces::gotPMT(eDVBServicePMTHandler *pmthandler)
{
	eDebug("[eDVBCIInterfaces] gotPMT");
	PMTHandlerList::iterator it=std::find(m_pmt_handlers.begin(), m_pmt_handlers.end(), pmthandler);
	eServiceReferenceDVB service;
	if ( it != m_pmt_handlers.end() && it->cislot)
		it->cislot->sendCAPMT(pmthandler);
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
			enableTS(0);
			printf("ci removed\n");
			eDVBCISession::deleteSessions(this);
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
	use_count = 0;
	
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
	enableTS(0);
}

void eDVBCISlot::setAppManager( eDVBCIApplicationManagerSession *session )
{
	application_manager=session;
}

void eDVBCISlot::setMMIManager( eDVBCIMMISession *session )
{
	mmi_session = session;
}

void eDVBCISlot::setCAManager( eDVBCICAManagerSession *session )
{
	ca_manager = session;
}

int eDVBCISlot::getSlotID()
{
	return slotid;
}

int eDVBCISlot::reset()
{
	printf("edvbcislot: reset requested\n");

	enableTS(0);

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
	if (!ca_manager)
	{
		eDebug("no ca_manager (no CI plugged?)");
		return -1;
	}
	const std::vector<uint16_t> &caids = ids.empty() ? ca_manager->getCAIDs() : ids;
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
			eDebug("ca_manager %p dump capmt:", ca_manager);
			for(int i=0;i<wp;i++)
				eDebugNoNewLine("%02x ", raw_data[i]);
			eDebug("");
#endif
			//dont need tag and lenfield
			ca_manager->sendCAPMT(raw_data + hlen, wp - hlen);
			prev_sent_capmt_version = pmt_version;
		}
	}
	return 0;
}

int eDVBCISlot::enableTS(int enable, int tuner)
{
	printf("eDVBCISlot::enableTS(%d %d)\n", enable, tuner);

	FILE *input0, *input1, *ci;
	if((input0 = fopen("/proc/stb/tsmux/input0", "wb")) == NULL) {
		printf("cannot open /proc/stb/tsmux/input0\n");
		return 0;
	}
	if((input1 = fopen("/proc/stb/tsmux/input1", "wb")) == NULL) {
		printf("cannot open /proc/stb/tsmux/input1\n");
		return 0;
	}
	if((ci = fopen("/proc/stb/tsmux/input2", "wb")) == NULL) {
		printf("cannot open /proc/stb/tsmux/input2\n");
		return 0;
	}

	fprintf(ci, "%s", tuner==0 ? "A" : "B");  // configure CI data source (TunerA, TunerB)
	fprintf(input0, "%s", tuner==0 && enable ? "CI" : "A"); // configure ATI input 0 data source
	fprintf(input1, "%s", tuner==1 && enable ? "CI" : "B"); // configure ATI input 1 data source

	fclose(input0);
	fclose(input1);
	fclose(ci);
	return 0;
}

void eDVBCISlot::resendCAPMT()
{
	eDVBCIInterfaces::getInstance()->sendCAPMT(slotid);
}

eAutoInitP0<eDVBCIInterfaces> init_eDVBCIInterfaces(eAutoInitNumbers::dvb, "CI Slots");
