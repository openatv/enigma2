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

int eDVBCIInterfaces::getSlotState(int slotid)
{
	eDVBCISlot *slot;

	if( (slot = getSlot(slotid)) == 0 )
		return eDVBCISlot::stateInvalid;

	return slot->getState();
}

int eDVBCIInterfaces::reset(int slotid)
{
	eDVBCISlot *slot;

	if( (slot = getSlot(slotid)) == 0 )
		return -1;

	eDVBCISession::deleteSessions(slot);
	ciRemoved(slot);

	return slot->reset();
}

int eDVBCIInterfaces::enableTS(int slotid, int enable)
{
	eDVBCISlot *slot;

	if( (slot = getSlot(slotid)) == 0 )
		return -1;

	int tunernum = 0;
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
	return slot->enableTS(enable, tunernum);
}

int eDVBCIInterfaces::initialize(int slotid)
{
	eDVBCISlot *slot;

	if( (slot = getSlot(slotid)) == 0 )
		return -1;

	slot->removeService();

	return sendCAPMT(slotid);
}

int eDVBCIInterfaces::sendCAPMT(int slotid)
{
	eDVBCISlot *slot;

	if( (slot = getSlot(slotid)) == 0 )
		return -1;

	PMTHandlerList::iterator it = m_pmt_handlers.begin();
	while (it != m_pmt_handlers.end())
	{
		if ( it->cislot == slot )
			slot->sendCAPMT(it->pmthandler);  // send capmt
		++it;
	}

	return 0;
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

void eDVBCIInterfaces::ciRemoved(eDVBCISlot *slot)
{
	for (PMTHandlerList::iterator it(m_pmt_handlers.begin());
		it != m_pmt_handlers.end(); ++it)
	{
		if (it->cislot == slot)
		{
			eServiceReferenceDVB ref;
			it->pmthandler->getServiceReference(ref);
			slot->removeService(ref.getServiceID().get());
			if (!--slot->use_count)
				enableTS(slot->getSlotID(), 0);
			it->cislot=0;
		}
	}
}

void eDVBCIInterfaces::recheckPMTHandlers()
{
//	eDebug("recheckPMTHAndlers()");
	for (PMTHandlerList::iterator it(m_pmt_handlers.begin());
		it != m_pmt_handlers.end(); ++it)
	{
		CAID_LIST caids;
		ePtr<eDVBService> service;
		eServiceReferenceDVB ref;
		eDVBServicePMTHandler *pmthandler = it->pmthandler;
		eDVBServicePMTHandler::program p;

		pmthandler->getServiceReference(ref);
		pmthandler->getService(service);
		if (!pmthandler->getProgramInfo(p))
		{
			int cnt=0;
			for (std::set<uint16_t>::reverse_iterator x(p.caids.rbegin()); x != p.caids.rend(); ++x, ++cnt)
				caids.push_front(*x);
			if (service && cnt)
				service->m_ca = caids;
		}

		if (it->cislot)
			continue; // already running

		if (service)
			caids = service->m_ca;

		if (!caids.empty())
		{
			for (eSmartPtrList<eDVBCISlot>::iterator ci_it(m_slots.begin()); ci_it != m_slots.end(); ++ci_it)
			{
				if (ci_it->getState() == eDVBCISlot::stateInvalid)
					ci_it->reset();

				bool useThis=false;
				eDVBCICAManagerSession *ca_manager = ci_it->getCAManager();
				if (ca_manager)
				{
					const std::vector<uint16_t> &ci_caids = ca_manager->getCAIDs();
					for (CAID_LIST::iterator ca(caids.begin()); ca != caids.end(); ++ca)
					{
						std::vector<uint16_t>::const_iterator z =
							std::lower_bound(ci_caids.begin(), ci_caids.end(), *ca);
						if ( z != ci_caids.end() && *z == *ca )
						{
							eDebug("found ci for caid %04x", *z);
							useThis=true;
							break;
						}
					}
				}

				if (useThis)
				{
					bool send_ca_pmt = false;
					if (ci_it->use_count)  // check if this CI can descramble more than one service
					{
						PMTHandlerList::iterator tmp = m_pmt_handlers.begin();
						while (tmp != m_pmt_handlers.end())
						{
							if ( tmp->cislot )
							{
								bool canHandleMultipleServices=false;
								eServiceReferenceDVB ref2;
								tmp->pmthandler->getServiceReference(ref2);
								eDVBChannelID s1, s2;
								if (ref != ref2)
								{
									ref.getChannelID(s1);
									ref2.getChannelID(s2);
									// FIXME .. build a "ci can handle multiple services" config entry
									// Yes / No / Auto
									if ( eDVBCI_UI::getInstance()->getAppName(ci_it->getSlotID()) == "AlphaCrypt" )
									{
										canHandleMultipleServices = true;
										eDebug("Alphacrypt can handle multiple services");
									}
								}
								if (ref == ref2 || (s1 == s2 && canHandleMultipleServices) )
								{
									it->cislot = tmp->cislot;
									++it->cislot->use_count;
									send_ca_pmt = true;
//									eDebug("usecount now %d", it->cislot->use_count);
									break;
								}
							}
							++tmp;
						}
					}
					else
					{
						ci_it->use_count=1;
						it->cislot = ci_it;
//						eDebug("usecount now %d", it->cislot->use_count);
						enableTS(ci_it->getSlotID(), 1);
						send_ca_pmt = true;
					}
					if (send_ca_pmt)
						gotPMT(pmthandler);
				}
			}
		}
	}
}

void eDVBCIInterfaces::addPMTHandler(eDVBServicePMTHandler *pmthandler)
{
	// check if this pmthandler is already registered
	PMTHandlerList::iterator it = m_pmt_handlers.begin();
	while (it != m_pmt_handlers.end())
	{
		if ( *it++ == pmthandler )
			return;
	}

	eServiceReferenceDVB ref;
	pmthandler->getServiceReference(ref);
	eDebug("[eDVBCIInterfaces] addPMTHandler %s", ref.toString().c_str());

	m_pmt_handlers.push_back(CIPmtHandler(pmthandler));
	recheckPMTHandlers();
}

void eDVBCIInterfaces::removePMTHandler(eDVBServicePMTHandler *pmthandler)
{
	PMTHandlerList::iterator it=std::find(m_pmt_handlers.begin(),m_pmt_handlers.end(),pmthandler);
	if (it != m_pmt_handlers.end())
	{
		eDVBCISlot *slot = it->cislot;
		eDVBServicePMTHandler *pmthandler = it->pmthandler;
		m_pmt_handlers.erase(it);

		eServiceReferenceDVB service_to_remove;
		pmthandler->getServiceReference(service_to_remove);

		bool sameServiceExist=false;
		for (PMTHandlerList::iterator i=m_pmt_handlers.begin(); i != m_pmt_handlers.end(); ++i)
		{
			eServiceReferenceDVB ref;
			i->pmthandler->getServiceReference(ref);
			if ( ref == service_to_remove )
			{
				sameServiceExist=true;
				break;
			}
		}

		if (slot && !sameServiceExist)
		{
			if (slot->getNumOfServices() > 1)
			{
				eDebug("[eDVBCIInterfaces] remove last pmt handler for service %s send empty capmt",
					service_to_remove.toString().c_str());
				std::vector<uint16_t> caids;
				caids.push_back(0xFFFF);
				slot->sendCAPMT(pmthandler, caids);  // send a capmt without caids to remove a running service
			}
			slot->removeService(service_to_remove.getServiceID().get());
		}

		if (slot && !--slot->use_count)
		{
			ASSERT(!slot->getNumOfServices());
			enableTS(slot->getSlotID(),0);
		}
	}
	// check if another service is waiting for the CI
	recheckPMTHandlers();
}

void eDVBCIInterfaces::gotPMT(eDVBServicePMTHandler *pmthandler)
{
	eDebug("[eDVBCIInterfaces] gotPMT");
	PMTHandlerList::iterator it=std::find(m_pmt_handlers.begin(), m_pmt_handlers.end(), pmthandler);
	if (it != m_pmt_handlers.end() && it->cislot)
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
	int res=0;
	//int i;
	//printf("< ");
	//for(i=0;i<len;i++)
	//	printf("%02x ",data[i]);
	//printf("\n");

	if (sendqueue.empty())
		res = ::write(fd, data, len);

	if (res < 0 || (unsigned int)res != len)
	{
		unsigned char *d = new unsigned char[len];
		memcpy(d, data, len);
		sendqueue.push( queueData(d, len) );
		notifier->setRequested(eSocketNotifier::Read | eSocketNotifier::Priority | eSocketNotifier::Write);
	}

	return res;
}

void eDVBCISlot::data(int what)
{
	if(what == eSocketNotifier::Priority) {
		if(state != stateRemoved) {
			state = stateRemoved;
			printf("ci removed\n");
			while(sendqueue.size())
			{
				delete [] sendqueue.top().data;
				sendqueue.pop();
			}
			eDVBCIInterfaces::getInstance()->ciRemoved(this);
			eDVBCISession::deleteSessions(this);
			notifier->setRequested(eSocketNotifier::Read);
			eDVBCI_UI::getInstance()->setState(getSlotID(),0);
		}
		return;
	}

	if (state == stateInvalid)
		return;

	if(state != stateInserted) {
		eDebug("ci inserted");
		state = stateInserted;
		eDVBCI_UI::getInstance()->setState(getSlotID(),1);
		notifier->setRequested(eSocketNotifier::Read|eSocketNotifier::Priority);
		/* enable PRI to detect removal or errors */
	}

	if (what & eSocketNotifier::Read) {
		__u8 data[4096];
		int r;
		r = ::read(fd, data, 4096);
		if(r > 0) {
//			int i;
//			printf("> ");
//			for(i=0;i<r;i++)
//				printf("%02x ",data[i]);
//			printf("\n");
			eDVBCISession::receiveData(this, data, r);
			eDVBCISession::pollAll();
			return;
		}
	}
	else if (what & eSocketNotifier::Write) {
		if (!sendqueue.empty()) {
			const queueData &qe = sendqueue.top();
			int res = ::write(fd, qe.data, qe.len);
			if (res >= 0 && (unsigned int)res == qe.len)
			{
				delete [] qe.data;
				sendqueue.pop();
			}
		}
		else
			notifier->setRequested(eSocketNotifier::Read|eSocketNotifier::Priority);
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
	state = stateInvalid;

	if (fd >= 0)
	{
		notifier = new eSocketNotifier(context, fd, eSocketNotifier::Read | eSocketNotifier::Priority | eSocketNotifier::Write);
		CONNECT(notifier->activated, eDVBCISlot::data);
	} else
	{
		perror(filename);
	}

	enableTS(0, 0);
}

eDVBCISlot::~eDVBCISlot()
{
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

	if (state == stateInvalid)
	{
		unsigned char buf[256];
		eDebug("ci flush");
		while(::read(fd, buf, 256)>0);
		state = stateResetted;
	}

	while(sendqueue.size())
	{
		delete [] sendqueue.top().data;
		sendqueue.pop();
	}

	ioctl(fd, 0);

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

	if(mmi_session)
		mmi_session->answerEnq(value);

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

		eServiceReferenceDVB ref;
		pmthandler->getServiceReference(ref);
		uint16_t program_number = ref.getServiceID().get();
		std::map<uint16_t, uint8_t>::iterator it =
			running_services.find(program_number);

		if ( it != running_services.end() &&
			(pmt_version == it->second) &&
			!(caids.size() == 1 && caids[0] == 0xFFFF) )
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

//			eDebug("send %s capmt for service %04x",
//				it != running_services.end() ? "UPDATE" : running_services.empty() ? "ONLY" : "ADD",
//				program_number);

			CaProgramMapSection capmt(*i++,
				it != running_services.end() ? 0x05 /*update*/ : running_services.empty() ? 0x03 /*only*/ : 0x04 /*add*/, 0x01, caids );
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
//			eDebug("ca_manager %p dump capmt:", ca_manager);
//			for(int i=0;i<wp;i++)
//				eDebugNoNewLine("%02x ", raw_data[i]);
//			eDebug("");
#endif
			if (caids.size() == 1 && caids[0] == 0xFFFF)
			{
//				eDebugNoNewLine("SEND EMPTY CAPMT.. old version is %02x", raw_data[hlen+3]);
				raw_data[hlen+3] &= ~0x3E;
				raw_data[hlen+3] |= ((pmt_version+1) & 0x1F) << 1;
//				eDebug(" new version is %02x", raw_data[hlen+3]);
			}

			//dont need tag and lenfield
			ca_manager->sendCAPMT(raw_data + hlen, wp - hlen);
			running_services[program_number] = pmt_version;
		}
	}
	return 0;
}

void eDVBCISlot::removeService(uint16_t program_number)
{
	if (program_number == 0xFFFF)
		running_services.clear();  // remove all
	else
		running_services.erase(program_number);  // remove single service
}

int eDVBCISlot::enableTS(int enable, int tuner)
{
//	printf("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n");
//	printf("eDVBCISlot::enableTS(%d %d)\n", enable, tuner);

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

eAutoInitP0<eDVBCIInterfaces> init_eDVBCIInterfaces(eAutoInitNumbers::dvb, "CI Slots");
