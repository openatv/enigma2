#include <sstream>
#include <fcntl.h>
#include <sys/ioctl.h>

#include <ios>
#include <fstream>
#include <sstream>
#include <iomanip>
#include <string>

#include <lib/base/init.h>
#include <lib/base/init_num.h>
#include <lib/base/cfile.h>
#include <lib/base/ebase.h>

#include <lib/base/eerror.h>
#include <lib/base/nconfig.h> // access to python config
#include <lib/base/esimpleconfig.h>
#include <lib/dvb/db.h>
#include <lib/dvb/pmt.h>
#include <lib/dvb_ci/dvbci.h>
#include <lib/dvb_ci/dvbci_session.h>
#include <lib/dvb_ci/dvbci_camgr.h>
#include <lib/dvb_ci/dvbci_ui.h>
#include <lib/dvb_ci/dvbci_appmgr.h>
#include <lib/dvb_ci/dvbci_mmi.h>
#include <lib/dvb_ci/dvbci_ccmgr.h>

#include <dvbsi++/ca_program_map_section.h>

eDVBCIInterfaces *eDVBCIInterfaces::instance = 0;

pthread_mutex_t eDVBCIInterfaces::m_pmt_handler_lock = PTHREAD_RECURSIVE_MUTEX_INITIALIZER_NP;
pthread_mutex_t eDVBCIInterfaces::m_slot_lock = PTHREAD_RECURSIVE_MUTEX_INITIALIZER_NP;

static char *readInputCI(int NimNumber)
{
	char id1[] = "NIM Socket";
	char id2[] = "Input_Name";
	char keys1[] = "1234567890";
    char keys2[] = "123456789ABCDabcd";
	char *inputName = 0;
	char buf[256];
	FILE *f;

	f = fopen("/proc/bus/nim_sockets", "rt");
	if (f)
	{
		while (fgets(buf, sizeof(buf), f))
		{
			char *p = strcasestr(buf, id1);
			if (!p)
				continue;

			p += strlen(id1);
			p += strcspn(p, keys1);
			if (*p && strtol(p, 0, 0) == NimNumber)
				break;
		}

		while (fgets(buf, sizeof(buf), f))
		{
			if (strcasestr(buf, id1))
				break;

			char *p = strcasestr(buf, id2);
			if (!p)
				continue;

			p = strchr(p + strlen(id2), ':');
			if (!p)
				continue;

			p++;
			p += strcspn(p, keys2);
			size_t len = strspn(p, keys2);
			if (len > 0)
			{
				inputName = strndup(p, len);
				break;
			}
		}

		fclose(f);
	}

	return inputName;
}

static std::string getTunerLetterDM(int NimNumber)
{
	char *srcCI = readInputCI(NimNumber);
	if (srcCI)
	{
		std::string ret = std::string(srcCI);
		free(srcCI);
		return ret;
	}
	return eDVBCISlot::getTunerLetter(NimNumber);
}

eDVBCIInterfaces::eDVBCIInterfaces()
	: m_messagepump_thread(this, 1, "dvbci"), m_messagepump_main(eApp, 1, "dvbci"), m_runTimer(eTimer::create(this))
{
	int num_ci = 0;
	std::stringstream path;

	instance = this;
	m_stream_interface = interface_none;
	m_stream_finish_mode = finish_none;

	CONNECT(m_messagepump_thread.recv_msg, eDVBCIInterfaces::gotMessageThread);
	CONNECT(m_messagepump_main.recv_msg, eDVBCIInterfaces::gotMessageMain);
	m_runTimer->start(750, false);

	eDebug("[CI] scanning for common interfaces..");

	singleLock s(m_slot_lock);

	for (;;)
	{
		path.str("");
		path.clear();
		path << "/dev/ci" << num_ci;

		if (::access(path.str().c_str(), R_OK) < 0)
			break;

		ePtr<eDVBCISlot> cislot;

		cislot = new eDVBCISlot(this, num_ci);
		m_slots.push_back(cislot);

		++num_ci;
	}

	for (eSmartPtrList<eDVBCISlot>::iterator it(m_slots.begin()); it != m_slots.end(); ++it)
#ifdef DREAMBOX_DUAL_TUNER
		it->setSource(getTunerLetterDM(0));
#else
		it->setSource("A");
#endif

	for (int tuner_no = 0; tuner_no < 26; ++tuner_no) // NOTE: this assumes tuners are A .. Z max.
	{
		path.str("");
		path.clear();
		path << "/proc/stb/tsmux/input" << tuner_no << "_choices";

		if (::access(path.str().c_str(), R_OK) < 0)
			break;

#ifdef DREAMBOX_DUAL_TUNER
		setInputSource(tuner_no, getTunerLetterDM(tuner_no));
#else
		setInputSource(tuner_no, eDVBCISlot::getTunerLetter(tuner_no));
#endif
	}

	eDebug("[CI] done, found %d common interface slots", num_ci);

	if (num_ci)
	{
		static const char *proc_ci_choices = "/proc/stb/tsmux/ci0_input_choices";

		if (CFile::contains_word(proc_ci_choices, "PVR")) // lowest prio = PVR
			m_stream_interface = interface_use_pvr;

		if (CFile::contains_word(proc_ci_choices, "DVR")) // low prio = DVR
			m_stream_interface = interface_use_dvr;

		if (CFile::contains_word(proc_ci_choices, "DVR0")) // high prio = DVR0
			m_stream_interface = interface_use_dvr;

		if (m_stream_interface == interface_none) // fallback = DVR
		{
			m_stream_interface = interface_use_dvr;
			eDebug("[CI] Streaming CI routing interface not advertised, assuming DVR method");
		}

		if (CFile::contains_word(proc_ci_choices, "PVR_NONE")) // low prio = PVR_NONE
			m_stream_finish_mode = finish_use_pvr_none;

		if (CFile::contains_word(proc_ci_choices, "NONE")) // high prio = NONE
			m_stream_finish_mode = finish_use_none;

		if (m_stream_finish_mode == finish_none) // fallback = "tuner"
		{
			m_stream_finish_mode = finish_use_tuner_a;
			eDebug("[CI] Streaming CI finish interface not advertised, assuming \"tuner\" method");
		}
	}

	run();
}

eDVBCIInterfaces::~eDVBCIInterfaces()
{
	m_messagepump_thread.send(1); // stop thread
	kill();						  // join
}

eDVBCIInterfaces *eDVBCIInterfaces::getInstance()
{
	return instance;
}

void eDVBCIInterfaces::thread()
{
	hasStarted();
	if (nice(4) == -1)
	{
		eDebug("[CI] thread failed to modify scheduling priority (%m)");
	}
	runLoop();
}

// runs in the thread
void eDVBCIInterfaces::gotMessageThread(const int &message)
{
	quit(0); // quit thread
}

// runs in the e2 mainloop
void eDVBCIInterfaces::gotMessageMain(const int &message)
{
	recheckPMTHandlers();
}

eDVBCISlot *eDVBCIInterfaces::getSlot(int slotid)
{
	singleLock s(m_slot_lock);
	for (eSmartPtrList<eDVBCISlot>::iterator i(m_slots.begin()); i != m_slots.end(); ++i)
		if (i->getSlotID() == slotid)
			return i;

	eWarning("[CI] FIXME: request for unknown slot");

	return 0;
}

int eDVBCIInterfaces::getSlotState(int slotid)
{
	eDVBCISlot *slot;

	singleLock s(m_slot_lock);
	if ((slot = getSlot(slotid)) == 0)
		return eDVBCISlot::stateInvalid;

	return slot->getState();
}

int eDVBCIInterfaces::reset(int slotid)
{
	eDVBCISlot *slot;

	singleLock s(m_slot_lock);
	if ((slot = getSlot(slotid)) == 0)
		return -1;

	return slot->reset();
}

int eDVBCIInterfaces::initialize(int slotid)
{
	eDVBCISlot *slot;

	singleLock s(m_slot_lock);
	if ((slot = getSlot(slotid)) == 0)
		return -1;

	slot->removeService();

	return sendCAPMT(slotid);
}

int eDVBCIInterfaces::sendCAPMT(int slotid)
{
	eDVBCISlot *slot;

	singleLock s1(m_slot_lock);
	if ((slot = getSlot(slotid)) == 0)
		return -1;

	singleLock s2(m_pmt_handler_lock);
	PMTHandlerList::iterator it = m_pmt_handlers.begin();
	while (it != m_pmt_handlers.end())
	{
		eDVBCISlot *tmp = it->cislot;
		while (tmp && tmp != slot)
			tmp = tmp->linked_next;
		if (tmp)
		{
			tmp->sendCAPMT(it->pmthandler); // send capmt
			break;
		}
		++it;
	}

	return 0;
}

int eDVBCIInterfaces::startMMI(int slotid)
{
	eDVBCISlot *slot;

	singleLock s(m_slot_lock);
	if ((slot = getSlot(slotid)) == 0)
		return -1;

	return slot->startMMI();
}

int eDVBCIInterfaces::stopMMI(int slotid)
{
	eDVBCISlot *slot;

	singleLock s(m_slot_lock);
	if ((slot = getSlot(slotid)) == 0)
		return -1;

	return slot->stopMMI();
}

int eDVBCIInterfaces::answerText(int slotid, int answer)
{
	eDVBCISlot *slot;

	singleLock s(m_slot_lock);
	if ((slot = getSlot(slotid)) == 0)
		return -1;

	return slot->answerText(answer);
}

int eDVBCIInterfaces::answerEnq(int slotid, char *value)
{
	eDVBCISlot *slot;

	singleLock s(m_slot_lock);
	if ((slot = getSlot(slotid)) == 0)
		return -1;

	return slot->answerEnq(value);
}

int eDVBCIInterfaces::cancelEnq(int slotid)
{
	eDVBCISlot *slot;

	singleLock s(m_slot_lock);
	if ((slot = getSlot(slotid)) == 0)
		return -1;

	return slot->cancelEnq();
}

void eDVBCIInterfaces::ciRemoved(eDVBCISlot *slot)
{
	if (slot->use_count)
	{
		singleLock s1(m_pmt_handler_lock);
		singleLock s2(m_slot_lock);
		eDebug("[CI] Slot %d: removed... usecount %d", slot->getSlotID(), slot->use_count);
		for (PMTHandlerList::iterator it(m_pmt_handlers.begin());
			 it != m_pmt_handlers.end(); ++it)
		{
			if (it->cislot == slot) // remove the base slot
				it->cislot = slot->linked_next;
			else if (it->cislot)
			{
				eDVBCISlot *prevSlot = it->cislot, *hSlot = it->cislot->linked_next;
				while (hSlot)
				{
					if (hSlot == slot)
					{
						prevSlot->linked_next = slot->linked_next;
						break;
					}
					prevSlot = hSlot;
					hSlot = hSlot->linked_next;
				}
			}
		}
		if (slot->linked_next)
			slot->linked_next->setSource(slot->current_source);
		else // last CI in chain
#ifdef DREAMBOX_DUAL_TUNER
			setInputSource(slot->current_tuner, getTunerLetterDM(slot->current_tuner));
#else
			setInputSource(slot->current_tuner, eDVBCISlot::getTunerLetter(slot->current_tuner));
#endif
		slot->linked_next = 0;
		slot->use_count = 0;
		slot->plugged = true;
		slot->user_mapped = false;
		slot->removeService(0xFFFF);
		executeRecheckPMTHandlersInMainloop(); // calls recheckPMTHandlers in the e2 mainloop
	}
}

bool eDVBCIInterfaces::canDescrambleMultipleServices(eDVBCISlot *slot)
{
	singleLock s(m_slot_lock);
	char configStr[255];
	snprintf(configStr, 255, "config.ci.%d.canDescrambleMultipleServices", slot->getSlotID());
	std::string str = eSimpleConfig::getString(configStr, "auto");
	if (str == "auto")
	{
		if (slot->getAppManager())
		{
			std::string appname = slot->getAppManager()->getAppName();
			if (appname.find("AlphaCrypt") != std::string::npos || appname.find("Multi") != std::string::npos)
				return true;
		}
	}
	else if (str == "yes")
		return true;
	return false;
}

// executes recheckPMTHandlers in the e2 mainloop
void eDVBCIInterfaces::executeRecheckPMTHandlersInMainloop()
{
	m_messagepump_main.send(1);
}

// has to run in the e2 mainloop to be able to access the pmt handler
void eDVBCIInterfaces::recheckPMTHandlers()
{
	singleLock s1(m_pmt_handler_lock);
	singleLock s2(m_slot_lock);
	eTrace("[CI] recheckPMTHAndlers()");
	for (PMTHandlerList::iterator it(m_pmt_handlers.begin());
		 it != m_pmt_handlers.end(); ++it)
	{
		CAID_LIST caids;
		ePtr<eDVBService> service;
		eServiceReferenceDVB ref;
		eDVBCISlot *tmp = it->cislot;
		eDVBServicePMTHandler *pmthandler = it->pmthandler;
		eDVBServicePMTHandler::program p;
		bool plugged_cis_exist = false;

		pmthandler->getServiceReference(ref);
		pmthandler->getService(service);

		eTrace("[CI] recheck %p %s", pmthandler, ref.toString().c_str());
		for (eSmartPtrList<eDVBCISlot>::iterator ci_it(m_slots.begin()); ci_it != m_slots.end(); ++ci_it)
			if (ci_it->plugged && ci_it->getCAManager())
			{
				eDebug("[CI] Slot %d plugged", ci_it->getSlotID());
				ci_it->plugged = false;
				plugged_cis_exist = true;
			}

		// check if this pmt handler has already assigned CI(s) .. and this CI(s) are already running
		if (!plugged_cis_exist)
		{
			while (tmp)
			{
				if (!tmp->running_services.empty())
					break;
				tmp = tmp->linked_next;
			}
			if (tmp) // we dont like to change tsmux for running services
			{
				eTrace("[CI] already assigned and running CI!\n");
				continue;
			}
		}

		if (!pmthandler->getProgramInfo(p))
		{
			int cnt = 0;
			std::set<eDVBServicePMTHandler::program::capid_pair> set(p.caids.begin(), p.caids.end());
			for (std::set<eDVBServicePMTHandler::program::capid_pair>::reverse_iterator x(set.rbegin()); x != set.rend(); ++x, ++cnt)
				caids.push_front(x->caid);
			if (service && cnt)
				service->m_ca = caids;
		}

		if (service)
			caids = service->m_ca;

		if (caids.empty())
			continue; // unscrambled service

		for (eSmartPtrList<eDVBCISlot>::iterator ci_it(m_slots.begin()); ci_it != m_slots.end(); ++ci_it)
		{
			eTrace("[CI] check Slot %d", ci_it->getSlotID());
			bool useThis = false;
			bool user_mapped = true;
			eDVBCICAManagerSession *ca_manager = ci_it->getCAManager();

			if (ca_manager)
			{
				int mask = 0;
				if (!ci_it->possible_services.empty())
				{
					mask |= 1;
					serviceSet::iterator it = ci_it->possible_services.find(ref);
					if (it != ci_it->possible_services.end())
					{
						eDebug("[CI] '%s' is in service list of slot %d... so use it", ref.toString().c_str(), ci_it->getSlotID());
						useThis = true;
					}
					else // check parent
					{
						eServiceReferenceDVB parent_ref = ref.getParentServiceReference();
						if (parent_ref)
						{
							it = ci_it->possible_services.find(ref);
							if (it != ci_it->possible_services.end())
							{
								eDebug("[CI] parent '%s' of '%s' is in service list of slot %d... so use it",
									   parent_ref.toString().c_str(), ref.toString().c_str(), ci_it->getSlotID());
								useThis = true;
							}
						}
					}
				}
				if (!useThis && !ci_it->possible_providers.empty())
				{
					eDVBNamespace ns = ref.getDVBNamespace();
					mask |= 2;
					if (!service) // subservice?
					{
						eServiceReferenceDVB parent_ref = ref.getParentServiceReference();
						eDVBDB::getInstance()->getService(parent_ref, service);
					}
					if (service)
					{
						providerSet::iterator it = ci_it->possible_providers.find(providerPair(service->m_provider_name, ns.get()));
						if (it != ci_it->possible_providers.end())
						{
							eDebug("[CI] '%s/%08x' is in provider list of slot %d... so use it", service->m_provider_name.c_str(), ns.get(), ci_it->getSlotID());
							useThis = true;
						}
					}
				}
				if (!useThis && !ci_it->possible_caids.empty())
				{
					mask |= 4;
					for (CAID_LIST::iterator ca(caids.begin()); ca != caids.end(); ++ca)
					{
						caidSet::iterator it = ci_it->possible_caids.find(*ca);
						if (it != ci_it->possible_caids.end())
						{
							eDebug("[CI] caid '%04x' is in caid list of slot %d... so use it", *ca, ci_it->getSlotID());
							useThis = true;
							break;
						}
					}
				}
				if (!useThis && !mask)
				{
					const std::vector<uint16_t> &ci_caids = ca_manager->getCAIDs();
					for (CAID_LIST::iterator ca(caids.begin()); ca != caids.end(); ++ca)
					{
						std::vector<uint16_t>::const_iterator z =
							std::lower_bound(ci_caids.begin(), ci_caids.end(), *ca);
						if (z != ci_caids.end() && *z == *ca)
						{
							eDebug("[CI] The CI in Slot %d has said it can handle caid %04x... so use it", ci_it->getSlotID(), *z);
							useThis = true;
							user_mapped = false;
							break;
						}
					}
				}
			}

			if (useThis)
			{
				// check if this CI is already assigned to this pmthandler
				eDVBCISlot *tmp = it->cislot;
				while (tmp)
				{
					if (tmp == ci_it)
						break;
					tmp = tmp->linked_next;
				}
				if (tmp) // ignore already assigned cislots...
				{
					eTrace("[CI] already assigned!");
					continue;
				}
				eTrace("[CI] current slot %d usecount %d", ci_it->getSlotID(), ci_it->use_count);
				if (ci_it->use_count) // check if this CI can descramble more than one service
				{
					bool found = false;
					useThis = false;
					PMTHandlerList::iterator tmp = m_pmt_handlers.begin();
					while (!found && tmp != m_pmt_handlers.end())
					{
						eTrace("[CI] .");
						eDVBCISlot *tmp_cislot = tmp->cislot;
						while (!found && tmp_cislot)
						{
							eTrace("[CI] ..");
							eServiceReferenceDVB ref2;
							tmp->pmthandler->getServiceReference(ref2);
							if (tmp_cislot == ci_it && it->pmthandler != tmp->pmthandler)
							{
								eTrace("[CI] check pmthandler %s for same service/tp", ref2.toString().c_str());
								eDVBChannelID s1, s2;
								if (ref != ref2)
								{
									eTrace("[CI] different services!");
									ref.getChannelID(s1);
									ref2.getChannelID(s2);
								}
								if (ref == ref2 || (s1 == s2 && canDescrambleMultipleServices(tmp_cislot)))
								{
									found = true;
									eTrace("[CI] found!");
									eDVBCISlot *tmpci = it->cislot = tmp->cislot;
									while (tmpci)
									{
										++tmpci->use_count;
										eTrace("[CI] (2)CISlot %d, usecount now %d", tmpci->getSlotID(), tmpci->use_count);
										tmpci = tmpci->linked_next;
									}
								}
							}
							tmp_cislot = tmp_cislot->linked_next;
						}
						eTrace("[CI] ...");
						++tmp;
					}
				}

				if (useThis)
				{
					if (ci_it->user_mapped) // we dont like to link user mapped CIs
					{
						eTrace("[CI] user mapped CI already in use... dont link!");
						continue;
					}

					++ci_it->use_count;
					eDebug("[CI] (1)Slot %d, usecount now %d", ci_it->getSlotID(), ci_it->use_count);

					std::stringstream ci_source;
					ci_source << "CI" << ci_it->getSlotID();

					if (!it->cislot)
					{
						int tunernum = -1;
						eUsePtr<iDVBChannel> channel;
						if (!pmthandler->getChannel(channel))
						{
							ePtr<iDVBFrontend> frontend;
							if (!channel->getFrontend(frontend))
							{
								eDVBFrontend *fe = (eDVBFrontend *)&(*frontend);
								tunernum = fe->getSlotID();
							}
							if (tunernum != -1)
							{
								setInputSource(tunernum, ci_source.str());
#ifdef DREAMBOX_DUAL_TUNER
								ci_it->setSource(getTunerLetterDM(tunernum));
#else
								ci_it->setSource(eDVBCISlot::getTunerLetter(tunernum));
#endif
							}
							else
							{
								/*
								 * No associated frontend, this must be a DVR source
								 *
								 * No need to set tuner input (setInputSource), because we have no tuner.
								 */

								switch (m_stream_interface)
								{
								case interface_use_dvr:
								{
									std::stringstream source;
									source << "DVR" << channel->getDvrId();
									ci_it->setSource(source.str());
									break;
								}

								case interface_use_pvr:
								{
									ci_it->setSource("PVR");
									break;
								}

								default:
								{
									eDebug("[CI] warning: no valid CI streaming interface");
									break;
								}
								}
							}
						}
						ci_it->current_tuner = tunernum;
					}
					else
					{
						ci_it->current_tuner = it->cislot->current_tuner;
						ci_it->linked_next = it->cislot;
						ci_it->setSource(ci_it->linked_next->current_source);
						ci_it->linked_next->setSource(ci_source.str());
					}
					it->cislot = ci_it;
					it->cislot->setCamMgrRoutingActive(true);
					eTrace("[CI] assigned!");
					gotPMT(pmthandler);
				}

				if (it->cislot && user_mapped) // CI assigned to this pmthandler in this run.. and user mapped? then we break here.. we dont like to link other CIs to user mapped CIs
				{
					eTrace("[CI] user mapped CI assigned... dont link CIs!");
					break;
				}
			}
		}
	}
}

void eDVBCIInterfaces::addPMTHandler(eDVBServicePMTHandler *pmthandler)
{
	singleLock s(m_pmt_handler_lock);
	// check if this pmthandler is already registered
	PMTHandlerList::iterator it = m_pmt_handlers.begin();
	while (it != m_pmt_handlers.end())
	{
		if (*it++ == pmthandler)
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
	singleLock s1(m_pmt_handler_lock);
	singleLock s2(m_slot_lock);
	PMTHandlerList::iterator it = std::find(m_pmt_handlers.begin(), m_pmt_handlers.end(), pmthandler);
	if (it != m_pmt_handlers.end())
	{
		eDVBCISlot *slot = it->cislot;
		eDVBCISlot *base_slot = slot;
		eDVBServicePMTHandler *pmthandler = it->pmthandler;
		m_pmt_handlers.erase(it);

		eServiceReferenceDVB service_to_remove;
		pmthandler->getServiceReference(service_to_remove);

		bool sameServiceExist = false;
		for (PMTHandlerList::iterator i = m_pmt_handlers.begin(); i != m_pmt_handlers.end(); ++i)
		{
			if (i->cislot)
			{
				eServiceReferenceDVB ref;
				i->pmthandler->getServiceReference(ref);
				if (ref == service_to_remove)
				{
					sameServiceExist = true;
					break;
				}
			}
		}

		while (slot)
		{
			eDVBCISlot *next = slot->linked_next;
			if (!sameServiceExist)
			{
				eDebug("[eDVBCIInterfaces] remove last pmt handler for service %s send empty capmt",
					   service_to_remove.toString().c_str());
				std::vector<uint16_t> caids;
				caids.push_back(0xFFFF);
				slot->sendCAPMT(pmthandler, caids); // send a capmt without caids to remove a running service
				slot->removeService(service_to_remove.getServiceID().get());

				if (slot->current_tuner == -1)
				{
					// no previous tuner to go back to, signal to CI interface CI action is finished

					std::string finish_source;

					switch (m_stream_finish_mode)
					{
					case finish_use_tuner_a:
					{
#ifdef DREAMBOX_DUAL_TUNER
						finish_source = getTunerLetterDM(0);
#else
						finish_source = "A";
#endif
						break;
					}

					case finish_use_pvr_none:
					{
						finish_source = "PVR_NONE";
						break;
					}

					case finish_use_none:
					{
						finish_source = "NONE";
						break;
					}

					default:
						(void)0;
					}

					if (finish_source == "")
					{
						eDebug("[CI] warning: CI streaming finish mode not set, assuming \"tuner A\"");
#ifdef DREAMBOX_DUAL_TUNER
						finish_source = getTunerLetterDM(0);
#else
						finish_source = "A";
#endif
					}

					slot->setSource(finish_source);
				}
			}

			if (!--slot->use_count)
			{
				if (slot->linked_next)
					slot->linked_next->setSource(slot->current_source);
				else
#ifdef DREAMBOX_DUAL_TUNER
					setInputSource(slot->current_tuner, getTunerLetterDM(slot->current_tuner));
#else
					setInputSource(slot->current_tuner, eDVBCISlot::getTunerLetter(slot->current_tuner));
#endif

				if (base_slot != slot)
				{
					eDVBCISlot *tmp = it->cislot;
					while (tmp->linked_next != slot)
						tmp = tmp->linked_next;
					ASSERT(tmp);
					if (slot->linked_next)
						tmp->linked_next = slot->linked_next;
					else
						tmp->linked_next = 0;
				}
				else // removed old base slot.. update ptr
					base_slot = slot->linked_next;
				slot->linked_next = 0;
				slot->user_mapped = false;
			}
			eDebug("[CI] (3) slot %d usecount is now %d", slot->getSlotID(), slot->use_count);
			slot = next;
		}
		// check if another service is waiting for the CI
		recheckPMTHandlers();
	}
}

void eDVBCIInterfaces::gotPMT(eDVBServicePMTHandler *pmthandler)
{
	// language config can only be accessed by e2 mainloop
	if (m_language == "")
		m_language = eConfigManager::getConfigValue("config.misc.locale");

	singleLock s1(m_pmt_handler_lock);
	singleLock s2(m_slot_lock);
	eDebug("[eDVBCIInterfaces] gotPMT");
	PMTHandlerList::iterator it = std::find(m_pmt_handlers.begin(), m_pmt_handlers.end(), pmthandler);
	if (it != m_pmt_handlers.end() && it->cislot)
	{
		eDVBCISlot *tmp = it->cislot;
		while (tmp)
		{
			eTrace("[CI] check slot %d %d %d", tmp->getSlotID(), tmp->running_services.empty(), canDescrambleMultipleServices(tmp));
			if (tmp->running_services.empty() || canDescrambleMultipleServices(tmp))
			{
				tmp->setCaParameter(pmthandler);
				tmp->sendCAPMT(pmthandler);
			}
			tmp = tmp->linked_next;
		}
	}
}

bool eDVBCIInterfaces::isCiConnected(eDVBServicePMTHandler *pmthandler)
{
	bool ret = false;
	PMTHandlerList::iterator it=std::find(m_pmt_handlers.begin(), m_pmt_handlers.end(), pmthandler);
	if (it != m_pmt_handlers.end() && it->cislot)
	{
		ret = true;
	}
	return ret;
}

int eDVBCIInterfaces::getMMIState(int slotid)
{
	eDVBCISlot *slot;

	singleLock s(m_slot_lock);
	if ((slot = getSlot(slotid)) == 0)
		return -1;

	return slot->getMMIState();
}

int eDVBCIInterfaces::setInputSource(int tuner_no, const std::string &source)
{
	if (tuner_no >= 0)
	{
		char buf[64];
		snprintf(buf, sizeof(buf), "/proc/stb/tsmux/input%d", tuner_no);

		if (CFile::write(buf, source.c_str()) == -1)
		{
			eDebug("[CI] eDVBCIInterfaces setInputSource for input %s failed!", source.c_str());
			return 0;
		}

		eDebug("[CI] eDVBCIInterfaces setInputSource(%d, %s)", tuner_no, source.c_str());
	}
	return 0;
}

PyObject *eDVBCIInterfaces::getDescrambleRules(int slotid)
{
	singleLock s(m_slot_lock);
	eDVBCISlot *slot = getSlot(slotid);
	if (!slot)
	{
		char tmp[255];
		snprintf(tmp, 255, "eDVBCIInterfaces::getDescrambleRules try to get rules for CI Slot %d... but just %zd slots are available", slotid, m_slots.size());
		PyErr_SetString(PyExc_ValueError, tmp);
		return 0;
	}
	ePyObject tuple = PyTuple_New(3);
	int caids = slot->possible_caids.size();
	int services = slot->possible_services.size();
	int providers = slot->possible_providers.size();
	ePyObject caid_list = PyList_New(caids);
	ePyObject service_list = PyList_New(services);
	ePyObject provider_list = PyList_New(providers);
	caidSet::iterator caid_it(slot->possible_caids.begin());
	while (caids)
	{
		--caids;
		PyList_SET_ITEM(caid_list, caids, PyLong_FromLong(*caid_it));
		++caid_it;
	}
	serviceSet::iterator ref_it(slot->possible_services.begin());
	while (services)
	{
		--services;
		PyList_SET_ITEM(service_list, services, PyUnicode_FromString(ref_it->toString().c_str()));
		++ref_it;
	}
	providerSet::iterator provider_it(slot->possible_providers.begin());
	while (providers)
	{
		ePyObject tuple = PyTuple_New(2);
		PyTuple_SET_ITEM(tuple, 0, PyUnicode_FromString(provider_it->first.c_str()));
		PyTuple_SET_ITEM(tuple, 1, PyLong_FromUnsignedLong(provider_it->second));
		--providers;
		PyList_SET_ITEM(provider_list, providers, tuple);
		++provider_it;
	}
	PyTuple_SET_ITEM(tuple, 0, service_list);
	PyTuple_SET_ITEM(tuple, 1, provider_list);
	PyTuple_SET_ITEM(tuple, 2, caid_list);
	return tuple;
}

const char *PyObject_TypeStr(PyObject *o)
{
	return o->ob_type && o->ob_type->tp_name ? o->ob_type->tp_name : "unknown object type";
}

RESULT eDVBCIInterfaces::setDescrambleRules(int slotid, SWIG_PYOBJECT(ePyObject) obj)
{
	singleLock s(m_slot_lock);
	eDVBCISlot *slot = getSlot(slotid);
	if (!slot)
	{
		char tmp[255];
		snprintf(tmp, 255, "eDVBCIInterfaces::setDescrambleRules try to set rules for CI Slot %d... but just %zd slots are available", slotid, m_slots.size());
		PyErr_SetString(PyExc_ValueError, tmp);
		return -1;
	}
	if (!PyTuple_Check(obj))
	{
		char tmp[255];
		snprintf(tmp, 255, "2nd argument of setDescrambleRules is not a tuple.. it is a '%s'!!", PyObject_TypeStr(obj));
		PyErr_SetString(PyExc_TypeError, tmp);
		return -1;
	}
	if (PyTuple_Size(obj) != 3)
	{
		const char *errstr = "eDVBCIInterfaces::setDescrambleRules not enough entrys in argument tuple!!\n"
							 "first argument should be a pythonlist with possible services\n"
							 "second argument should be a pythonlist with possible providers/dvbnamespace tuples\n"
							 "third argument should be a pythonlist with possible caids";
		PyErr_SetString(PyExc_TypeError, errstr);
		return -1;
	}
	ePyObject service_list = PyTuple_GET_ITEM(obj, 0);
	ePyObject provider_list = PyTuple_GET_ITEM(obj, 1);
	ePyObject caid_list = PyTuple_GET_ITEM(obj, 2);
	if (!PyList_Check(service_list) || !PyList_Check(provider_list) || !PyList_Check(caid_list))
	{
		char errstr[512];
		snprintf(errstr, 512, "eDVBCIInterfaces::setDescrambleRules incorrect data types in argument tuple!!\n"
							  "first argument(%s) should be a pythonlist with possible services (reference strings)\n"
							  "second argument(%s) should be a pythonlist with possible providers (providername strings)\n"
							  "third argument(%s) should be a pythonlist with possible caids (ints)",
				 PyObject_TypeStr(service_list), PyObject_TypeStr(provider_list), PyObject_TypeStr(caid_list));
		PyErr_SetString(PyExc_TypeError, errstr);
		return -1;
	}
	slot->possible_caids.clear();
	slot->possible_services.clear();
	slot->possible_providers.clear();
	int size = PyList_Size(service_list);
	while (size)
	{
		--size;
		ePyObject refstr = PyList_GET_ITEM(service_list, size);
		if (!PyUnicode_Check(refstr))
		{
			char buf[255];
			snprintf(buf, 255, "eDVBCIInterfaces::setDescrambleRules entry in service list is not a string.. it is '%s'!!", PyObject_TypeStr(refstr));
			PyErr_SetString(PyExc_TypeError, buf);
			return -1;
		}
		const char *tmpstr = PyUnicode_AsUTF8(refstr);
		eServiceReference ref(tmpstr);
		if (ref.valid())
			slot->possible_services.insert(ref);
		else
			eDebug("[CI] eDVBCIInterfaces::setDescrambleRules '%s' is not a valid service reference... ignore!!", tmpstr);
	};
	size = PyList_Size(provider_list);
	while (size)
	{
		--size;
		ePyObject tuple = PyList_GET_ITEM(provider_list, size);
		if (!PyTuple_Check(tuple))
		{
			char buf[255];
			snprintf(buf, 255, "eDVBCIInterfaces::setDescrambleRules entry in provider list is not a tuple it is '%s'!!", PyObject_TypeStr(tuple));
			PyErr_SetString(PyExc_TypeError, buf);
			return -1;
		}
		if (PyTuple_Size(tuple) != 2)
		{
			char buf[255];
			snprintf(buf, 255, "eDVBCIInterfaces::setDescrambleRules provider tuple has %zd instead of 2 entries!!", PyTuple_Size(tuple));
			PyErr_SetString(PyExc_TypeError, buf);
			return -1;
		}
		if (!PyUnicode_Check(PyTuple_GET_ITEM(tuple, 0)))
		{
			char buf[255];
			snprintf(buf, 255, "eDVBCIInterfaces::setDescrambleRules 1st entry in provider tuple is not a string it is '%s'", PyObject_TypeStr(PyTuple_GET_ITEM(tuple, 0)));
			PyErr_SetString(PyExc_TypeError, buf);
			return -1;
		}
		if (!PyLong_Check(PyTuple_GET_ITEM(tuple, 1)))
		{
			char buf[255];
			snprintf(buf, 255, "eDVBCIInterfaces::setDescrambleRules 2nd entry in provider tuple is not a long it is '%s'", PyObject_TypeStr(PyTuple_GET_ITEM(tuple, 1)));
			PyErr_SetString(PyExc_TypeError, buf);
			return -1;
		}
		const char *tmpstr = PyUnicode_AsUTF8(PyTuple_GET_ITEM(tuple, 0));
		uint32_t orbpos = PyLong_AsUnsignedLong(PyTuple_GET_ITEM(tuple, 1));
		if (strlen(tmpstr))
			slot->possible_providers.insert(std::pair<std::string, uint32_t>(tmpstr, orbpos));
		else
			eDebug("[CI] eDVBCIInterfaces::setDescrambleRules ignore invalid entry in provider tuple (string is empty)!!");
	};
	size = PyList_Size(caid_list);
	while (size)
	{
		--size;
		ePyObject caid = PyList_GET_ITEM(caid_list, size);
		if (!PyLong_Check(caid))
		{
			char buf[255];
			snprintf(buf, 255, "eDVBCIInterfaces::setDescrambleRules entry in caid list is not a long it is '%s'!!", PyObject_TypeStr(caid));
			PyErr_SetString(PyExc_TypeError, buf);
			return -1;
		}
		int tmpcaid = PyLong_AsLong(caid);
		if (tmpcaid > 0 && tmpcaid < 0x10000)
			slot->possible_caids.insert(tmpcaid);
		else
			eDebug("[CI] eDVBCIInterfaces::setDescrambleRules %d is not a valid caid... ignore!!", tmpcaid);
	};
	return 0;
}

PyObject *eDVBCIInterfaces::readCICaIds(int slotid)
{
	singleLock s(m_slot_lock);
	eDVBCISlot *slot = getSlot(slotid);
	if (!slot)
	{
		char tmp[255];
		snprintf(tmp, 255, "eDVBCIInterfaces::readCICaIds try to get CAIds for CI Slot %d... but just %zd slots are available", slotid, m_slots.size());
		PyErr_SetString(PyExc_ValueError, tmp);
	}
	else
	{
		int idx = 0;
		eDVBCICAManagerSession *ca_manager = slot->getCAManager();
		const std::vector<uint16_t> *ci_caids = ca_manager ? &ca_manager->getCAIDs() : 0;
		ePyObject list = PyList_New(ci_caids ? ci_caids->size() : 0);
		if (ci_caids)
		{
			for (std::vector<uint16_t>::const_iterator it = ci_caids->begin(); it != ci_caids->end(); ++it)
				PyList_SET_ITEM(list, idx++, PyLong_FromLong(*it));
		}
		return list;
	}
	return 0;
}

int eDVBCIInterfaces::setCIEnabled(int slotid, bool enabled)
{
	eDVBCISlot *slot = getSlot(slotid);
	if (slot)
		return slot->setEnabled(enabled);
	return -1;
}

int eDVBCIInterfaces::setCIClockRate(int slotid, const std::string &rate)
{
	singleLock s(m_slot_lock);
	eDVBCISlot *slot = getSlot(slotid);
	if (slot)
		return slot->setClockRate(rate);
	return -1;
}

/* For authentication process transponder data needs to be routed through the CI (doesn't matter which channel)
   This is mandatory for many CI+ 1.3 modules. For many CI+ 1.2 modules you can also switch to an encrypted channel
   (with correct caid) */
void eDVBCIInterfaces::setCIPlusRouting(int slotid)
{
	int ciplus_routing_tunernum;
	std::string ciplus_routing_input;
	std::string ciplus_routing_ci_input;

	eDebug("[CI] setCIRouting slotid=%d", slotid);
	singleLock s(m_pmt_handler_lock);
	if (m_pmt_handlers.size() == 0)
	{
		eDebug("[CI] setCIRouting no pmt handler available! Unplug/plug again the CI module.");
		return;
	}

	eDVBCISlot *slot = getSlot(slotid);
	if (slot->isCamMgrRoutingActive()) // CamMgr has already set up routing. Don't change that.
	{
		eDebug("[CI] CamMgrRouting is active -> return");
		return;
	}

	PMTHandlerList::iterator it = m_pmt_handlers.begin();
	while (it != m_pmt_handlers.end())
	{
		int tunernum = -1;
		eUsePtr<iDVBChannel> channel;
		if (!it->pmthandler->getChannel(channel))
		{
			ePtr<iDVBFrontend> frontend;
			if (!channel->getFrontend(frontend))
			{
				eDVBFrontend *fe = (eDVBFrontend *)&(*frontend);
				tunernum = fe->getSlotID();
			}
		}
		eTrace("[CI] setCIRouting tunernum=%d", tunernum);
		if (tunernum < 0)
			continue;

		ciplus_routing_tunernum = slot->getCIPlusRoutingTunerNum();

		// read and store old routing config
		char file_name[64];
		char tmp[8];
		int rd;

		snprintf(file_name, 64, "/proc/stb/tsmux/input%d", tunernum);
		int fd = open(file_name, O_RDONLY);
		if (fd > -1)
		{
			rd = read(fd, tmp, 8);
			if (rd > 0)
			{
				if (ciplus_routing_tunernum != tunernum)
					ciplus_routing_input = std::string(tmp, rd - 1);
			}
			else
				continue;
			close(fd);
		}
		else
			continue;

		snprintf(file_name, 64, "/proc/stb/tsmux/ci%d_input", slotid);
		fd = open(file_name, O_RDONLY);
		if (fd > -1)
		{
			rd = read(fd, tmp, 8);
			if (rd > 0)
			{
				if (ciplus_routing_tunernum != tunernum)
					ciplus_routing_ci_input = std::string(tmp, rd - 1);
			}
			else
				continue;
			close(fd);
		}
		else
			continue;

		std::stringstream new_input_source;
		new_input_source << "CI" << slot->getSlotID();

		setInputSource(tunernum, new_input_source.str());
#ifdef DREAMBOX_DUAL_TUNER
		slot->setSource(getTunerLetterDM(tunernum));
#else
		slot->setSource(eDVBCISlot::getTunerLetter(tunernum));
#endif

		slot->setCIPlusRoutingParameter(tunernum, ciplus_routing_input, ciplus_routing_ci_input);
		eDebug("[CI] CIRouting active slotid=%d tuner=%d old_input=%s old_ci_input=%s", slotid, tunernum, ciplus_routing_input.c_str(), ciplus_routing_ci_input.c_str());
		break;

		++it;
	}
}

void eDVBCIInterfaces::revertCIPlusRouting(int slotid)
{
	eDVBCISlot *slot = getSlot(slotid);

	int ciplus_routing_tunernum = slot->getCIPlusRoutingTunerNum();
	std::string ciplus_routing_input = slot->getCIPlusRoutingInput();
	std::string ciplus_routing_ci_input = slot->getCIPlusRoutingCIInput();

	eDebug("[CI] revertCIPlusRouting: camMgrActive=%d ciRoutingActive=%d slot=%d tuner=%d input=%s ci_input=%s", slot->isCamMgrRoutingActive(), slot->ciplusRoutingDone(), slotid, ciplus_routing_tunernum, ciplus_routing_input.c_str(), ciplus_routing_ci_input.c_str());

	if (slot->isCamMgrRoutingActive() || // CamMgr has set up routing. Don't revert that.
		slot->ciplusRoutingDone())		 // need to only run once during CI initialization
	{
		slot->setCIPlusRoutingDone();
		return;
	}

	slot->setSource(ciplus_routing_ci_input);
	setInputSource(ciplus_routing_tunernum, ciplus_routing_input);

	slot->setCIPlusRoutingDone();
}

int eDVBCISlot::send(const unsigned char *data, size_t len)
{
	singleLock s(eDVBCIInterfaces::m_slot_lock);
	int res = 0;
	unsigned int i;
	eTraceNoNewLineStart("[CI%d] < ", slotid);
	for (i = 0; i < len; i++)
		eTraceNoNewLine("%02x ", data[i]);
	eTraceNoNewLine("\n");

	if (sendqueue.empty())
		res = ::write(fd, data, len);

	if (res < 0 || (unsigned int)res != len)
	{
		unsigned char *d = new unsigned char[len];
		memcpy(d, data, len);
		sendqueue.push(queueData(d, len));
		notifier->setRequested(eSocketNotifier::Read | eSocketNotifier::Priority | eSocketNotifier::Write);
	}

	return res;
}

void eDVBCISlot::data(int what)
{
	singleLock s(eDVBCIInterfaces::m_slot_lock);
	eTrace("[CI%d] what %d\n", slotid, what);
	if (what == eSocketNotifier::Priority)
	{
		if (state != stateRemoved)
		{
			state = stateRemoved;
			while (sendqueue.size())
			{
				delete[] sendqueue.top().data;
				sendqueue.pop();
			}
			eDVBCISession::deleteSessions(this);
			eDVBCIInterfaces::getInstance()->ciRemoved(this);
			notifier->setRequested(eSocketNotifier::Read);
			/* emit */ eDVBCI_UI::getInstance()->m_messagepump.send(eDVBCIInterfaces::Message(eDVBCIInterfaces::Message::slotStateChanged, getSlotID(), 0));
		}
		return;
	}

	if (state == stateInvalid)
		reset();

	if (state != stateInserted)
	{
		eDebug("[CI%d] ci inserted", slotid);
		state = stateInserted;
		/* emit */ eDVBCI_UI::getInstance()->m_messagepump.send(eDVBCIInterfaces::Message(eDVBCIInterfaces::Message::slotStateChanged, getSlotID(), 1));
		notifier->setRequested(eSocketNotifier::Read | eSocketNotifier::Priority);
		/* enable PRI to detect removal or errors */
	}

	if (what & eSocketNotifier::Read)
	{
		uint8_t data[4096];
		int r;
		r = ::read(fd, data, 4096);
		if (r > 0)
		{
			int i;
			eTraceNoNewLineStart("[CI%d] > ", slotid);
			for (i = 0; i < r; i++)
				eTraceNoNewLine("%02x ", data[i]);
			eTraceNoNewLine("\n");
			eDVBCISession::receiveData(this, data, r);
			eDVBCISession::pollAll();
			return;
		}
	}
	else if (what & eSocketNotifier::Write)
	{
		if (!sendqueue.empty())
		{
			const queueData &qe = sendqueue.top();
			int res = ::write(fd, qe.data, qe.len);
			if (res >= 0 && (unsigned int)res == qe.len)
			{
				delete[] qe.data;
				sendqueue.pop();
			}
		}
		else
			notifier->setRequested(eSocketNotifier::Read | eSocketNotifier::Priority);
	}
}

DEFINE_REF(eDVBCISlot);

eDVBCISlot::eDVBCISlot(eMainloop *context, int nr) : startup_timeout(eTimer::create(context))
{
	slotid = nr;
	m_isCamMgrRoutingActive = false;
	m_ciPlusRoutingDone = false;
	m_ca_demux_id = -1;
	m_context = context;
	m_ciplus_routing_tunernum = -1;
	state = stateDisabled;
	application_manager = 0;
	mmi_session = 0;
	ca_manager = 0;
	cc_manager = 0;
	use_count = 0;
	linked_next = 0;
	user_mapped = false;
	plugged = false;
	m_ci_version = versionUnknown;
	char configStr[255];
	snprintf(configStr, 255, "config.ci.%d.enabled", slotid);
	bool enabled = eSimpleConfig::getBool(configStr, true);
	snprintf(configStr, 255, "config.ci.%d.disable_operator_profile", slotid);
	m_operator_profiles_disabled = eSimpleConfig::getBool(configStr, false);
	snprintf(configStr, 255, "config.ci.%d.alternative_ca_handling", slotid);
	m_alt_ca_handling = eSimpleConfig::getInt(configStr, 0);
	if (enabled)
	{
		int bootDelay = eSimpleConfig::getInt("config.cimisc.bootDelay", 5);
		if (bootDelay)
		{
			CONNECT(startup_timeout->timeout, eDVBCISlot::openDevice);
			startup_timeout->start(1000 * bootDelay, true);
		}
		else
			openDevice();
	}
	else
		/* emit */ eDVBCI_UI::getInstance()->m_messagepump.send(eDVBCIInterfaces::Message(eDVBCIInterfaces::Message::slotStateChanged, getSlotID(), 3)); // state disabled
}

void eDVBCISlot::openDevice()
{
	char filename[128];

	plugged = true;

	sprintf(filename, "/dev/ci%d", slotid);

	//	possible_caids.insert(0x1702);
	//	possible_providers.insert(providerPair("PREMIERE", 0xC00000));
	//	possible_services.insert(eServiceReference("1:0:1:2A:4:85:C00000:0:0:0:"));

	fd = ::open(filename, O_RDWR | O_NONBLOCK | O_CLOEXEC);

	eTrace("[CI%d] has fd %d", slotid, fd);
	state = stateInvalid;

	if (fd >= 0)
	{
		notifier = eSocketNotifier::create(m_context, fd, eSocketNotifier::Read | eSocketNotifier::Priority | eSocketNotifier::Write);
		CONNECT(notifier->activated, eDVBCISlot::data);
	}
	else
	{
		perror(filename);
	}
}

eDVBCISlot::~eDVBCISlot()
{
	eDVBCISession::deleteSessions(this);
	close(fd);
}

void eDVBCISlot::closeDevice()
{
	close(fd);
	fd = -1;
	notifier->stop();
	data(eSocketNotifier::Priority);
	state = stateDisabled;
}

void eDVBCISlot::setAppManager(eDVBCIApplicationManagerSession *session)
{
	singleLock s(eDVBCIInterfaces::m_slot_lock);
	application_manager = session;
}

void eDVBCISlot::setMMIManager(eDVBCIMMISession *session)
{
	singleLock s(eDVBCIInterfaces::m_slot_lock);
	mmi_session = session;
}

void eDVBCISlot::setCAManager(eDVBCICAManagerSession *session)
{
	singleLock s(eDVBCIInterfaces::m_slot_lock);
	ca_manager = session;
}

void eDVBCISlot::setCCManager(eDVBCICcSession *session)
{
	singleLock s(eDVBCIInterfaces::m_slot_lock);
	cc_manager = session;
}

int eDVBCISlot::getSlotID()
{
	singleLock s(eDVBCIInterfaces::m_slot_lock);
	return slotid;
}

int eDVBCISlot::getVersion()
{
	return m_ci_version;
}

void eDVBCISlot::determineCIVersion()
{
	char lv1Info[256] = {0};

	if (ioctl(fd, 1, lv1Info) < 0)
	{
		eTrace("[CI%d] ioctl not supported: assume CI+ version 1", slotid);
		m_ci_version = versionCIPlus1;
		return;
	}

	if (strlen(lv1Info) == 0)
	{
		eTrace("[CI%d] no LV1 info: assume CI+ version 1", slotid);
		m_ci_version = versionCIPlus1;
		return;
	}

	const char *str1 = "$compatible[";
	int len1 = strlen(str1);
	char *compatId = 0;

	for (unsigned int i = 0; i <= (sizeof(lv1Info) - len1); i++)
	{
		if (strncasecmp(&lv1Info[i], str1, len1) == 0)
		{
			i += len1;
			for (unsigned int j = i; j <= (sizeof(lv1Info) - 2); j++)
			{
				if (strncmp(&lv1Info[j], "]$", 2) == 0)
				{
					lv1Info[j] = '\0';
					compatId = &lv1Info[i];
					break;
				}
			}
		}
	}

	if (!compatId)
	{
		eTrace("[CI%d] CI CAM detected", slotid);
		m_ci_version = versionCI;
		return;
	}

	eTrace("[CI%d] CI+ compatibility ID: %s", slotid, compatId);

	char *label, *id, flag = '+';
	int version = versionCI;

	while ((label = strsep(&compatId, " ")) != 0)
	{
		if (*label == '\0')
			continue;

		if (strncasecmp(label, "ciplus", 6) == 0)
		{
			id = strchr(label, '=');
			if (id)
			{
				*id++ = '\0';
				if (*id == '-' || *id == '+' || *id == '*')
					flag = *id++;

				version = strtol(id, 0, 0);
				eDebug("[CI%d] CI+ %c%d CAM detected", slotid, flag, version);
				break;
			}
		}
	}

	m_ci_version = version;
}

int eDVBCISlot::getNumOfServices()
{
	singleLock s(eDVBCIInterfaces::m_slot_lock);
	return running_services.size();
}

void eDVBCISlot::setCIPlusRoutingParameter(int tunernum, std::string ciplus_routing_input, std::string ciplus_routing_ci_input)
{
	m_ciplus_routing_tunernum = tunernum;
	m_ciplus_routing_input = ciplus_routing_input;
	m_ciplus_routing_ci_input = ciplus_routing_ci_input;
}

int eDVBCISlot::reset()
{
	eDebug("[CI%d] reset requested", slotid);

	if (state == stateInvalid)
	{
		unsigned char buf[256];
		eDebug("[CI%d] flush", slotid);
		while (::read(fd, buf, 256) > 0)
			;
		state = stateResetted;
	}

	while (sendqueue.size())
	{
		delete[] sendqueue.top().data;
		sendqueue.pop();
	}

	ioctl(fd, 0);

	return 0;
}

int eDVBCISlot::startMMI()
{
	eDebug("[CI%d] startMMI()", slotid);

	if (application_manager)
		application_manager->startMMI();

	return 0;
}

int eDVBCISlot::stopMMI()
{
	eDebug("[CI%d] stopMMI()", slotid);

	if (mmi_session)
		mmi_session->stopMMI();

	return 0;
}

int eDVBCISlot::answerText(int answer)
{
	eDebug("[CI%d] answerText(%d)", slotid, answer);

	if (mmi_session)
		mmi_session->answerText(answer);

	return 0;
}

int eDVBCISlot::getMMIState()
{
	if (mmi_session)
		return 1;

	return 0;
}

int eDVBCISlot::answerEnq(char *value)
{
	eDebug("[CI%d] answerENQ(%s)", slotid, value);

	if (mmi_session)
		mmi_session->answerEnq(value);

	return 0;
}

int eDVBCISlot::cancelEnq()
{
	eDebug("[CI%d] cancelENQ", slotid);

	if (mmi_session)
		mmi_session->cancelEnq();

	return 0;
}

int eDVBCISlot::setCaParameter(eDVBServicePMTHandler *pmthandler)
{
	ePtr<iDVBDemux> demux;
	eDVBServicePMTHandler::program program;
	eServiceReferenceDVB ref;
	uint8_t dmx_id;
	eUsePtr<iDVBChannel> channel;
	ePtr<iDVBFrontend> frontend;

	eDebug("[CI%d] setCaParameter", slotid);

	if (!pmthandler->getDataDemux(demux))
	{
		if (!demux->getCADemuxID(dmx_id))
		{
			m_ca_demux_id = dmx_id;
			eDebug("[CI%d] CA demux_id = %d", slotid, m_ca_demux_id);
		}
		else
			m_ca_demux_id = -1;
	}

	pmthandler->getServiceReference(ref);
	m_program_number = ref.getServiceID().get();

	pmthandler->getProgramInfo(program);
	m_audio_number = program.audioStreams.size();

	if (m_audio_number > 16)
		m_audio_number = 16;
	for (int i = 0; i < m_audio_number; i++)
	{
		m_audio_pids[i] = program.audioStreams[i].pid;
	}

	m_video_pid = program.videoStreams.empty() ? 0 : program.videoStreams[0].pid;
	m_audio_pid = program.audioStreams.empty() ? 0 : program.audioStreams[program.defaultAudioStream].pid;

	m_tunernum = -1;
	if (!pmthandler->getChannel(channel))
	{
		if (!channel->getFrontend(frontend))
		{
			eDVBFrontend *fe = (eDVBFrontend *)&(*frontend);
			m_tunernum = fe->getSlotID();
			if (m_tunernum > 7 && !fe->is_FBCTuner()) // use vu ioctl only for second FBC tuner
			{
				m_tunernum = -1;
			}
		}
		eDebug("[CI%d] tunernum = %d", slotid, m_tunernum);
	}

	return 0;
}

int eDVBCISlot::sendCAPMT(eDVBServicePMTHandler *pmthandler, const std::vector<uint16_t> &ids)
{
	if (!ca_manager)
	{
		eDebug("[CI%d] no ca_manager (no CI plugged?)", slotid);
		return -1;
	}
	const std::vector<uint16_t> &caids = ids.empty() ? ca_manager->getCAIDs() : ids;
	ePtr<eTable<ProgramMapSection>> ptr;
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
		bool sendEmpty = caids.size() == 1 && caids[0] == 0xFFFF;

		if (it != running_services.end() &&
			(pmt_version == it->second) &&
			!sendEmpty)
		{
			eDebug("[CI%d] dont send self capmt version twice", slotid);
			return -1;
		}

		std::vector<ProgramMapSection *>::const_iterator i = ptr->getSections().begin();
		if (i == ptr->getSections().end())
			return -1;
		else
		{
			unsigned char raw_data[2048];

			//			eDebug("[CI%d] send %s capmt for service %04x",
			//				slotid, it != running_services.end() ? "UPDATE" : running_services.empty() ? "ONLY" : "ADD",
			//				program_number);

			CaProgramMapSection capmt(*i++,
									  it != running_services.end() ? 0x05 /*update*/ : running_services.empty() ? 0x03 /*only*/
																												: 0x04 /*add*/,
									  0x01, caids);
			while (i != ptr->getSections().end())
			{
				//			eDebug("[CI%d] append", slotid);
				capmt.append(*i++);
			}
			capmt.writeToBuffer(raw_data);

			// begin calc capmt length
			int wp = 0;
			int hlen;
			if (raw_data[3] & 0x80)
			{
				int i = 0;
				int lenbytes = raw_data[3] & ~0x80;
				while (i < lenbytes)
					wp = (wp << 8) | raw_data[4 + i++];
				wp += 4;
				wp += lenbytes;
				hlen = 4 + lenbytes;
			}
			else
			{
				wp = raw_data[3];
				wp += 4;
				hlen = 4;
			}
			// end calc capmt length

			if (sendEmpty)
			{
				//				eDebugNoNewLineStart("[CI%d[ SEND EMPTY CAPMT.. old version is %02x", slotid, raw_data[hlen+3]);
				if (sendEmpty && running_services.size() == 1) // check if this is the capmt for the last running service
					raw_data[hlen] = 0x03;					   // send only instead of update... because of strange effects with alphacrypt
				raw_data[hlen + 3] &= ~0x3E;
				raw_data[hlen + 3] |= ((pmt_version + 1) & 0x1F) << 1;
				//				eDebugNoNewLine(" new version is %02x\n", raw_data[hlen+3]);
			}

			//			eDebugNoNewLineStart("[CI%d[ ca_manager %p dump capmt:", slotid, ca_manager);
			//			for(int i=0;i<wp;i++)
			//				eDebugNoNewLine("%02x ", raw_data[i]);
			//			eDebugNoNewLine("\n");

			// dont need tag and lenfield
			ca_manager->sendCAPMT(raw_data + hlen, wp - hlen);
			running_services[program_number] = pmt_version;

			std::vector<uint16_t> pids;
			int prg_info_len = ((raw_data[hlen + 4] << 8) | raw_data[hlen + 5]) & 0xfff;
			int es_info_len = 0;
			for (int jj = hlen + prg_info_len + 6; jj < wp; jj += es_info_len + 5)
			{
				uint16_t es_pid = ((raw_data[jj + 1] << 8) | raw_data[jj + 2]) & 0x1fff;
				pids.push_back(es_pid);
				es_info_len = ((raw_data[jj + 3] << 8) | raw_data[jj + 4]) & 0xfff;
			}

			if (cc_manager)
			{
				if (!sendEmpty)
					cc_manager->addProgram(program_number, pids);
				else
					cc_manager->removeProgram(program_number, pids);
			}
		}
	}
	return 0;
}

void eDVBCISlot::removeService(uint16_t program_number)
{
	if (program_number == 0xFFFF)
		running_services.clear(); // remove all
	else
		running_services.erase(program_number); // remove single service
}

int eDVBCISlot::setSource(const std::string &source)
{
	char buf[64];
	current_source = source;
	snprintf(buf, sizeof(buf), "/proc/stb/tsmux/ci%d_input", slotid);

	if (CFile::write(buf, source.c_str()) == -1)
	{
		eDebug("[CI%d] setSource: %s failed!", slotid, source.c_str());
		return 0;
	}

	eDebug("[CI%d] setSource: %s", slotid, source.c_str());
	return 0;
}

int eDVBCISlot::setClockRate(const std::string &rate)
{
	char buf[64];
	snprintf(buf, sizeof(buf), "/proc/stb/tsmux/ci%d_tsclk", slotid);
	if (CFile::writeStr(buf, rate) == -1)
		return -1;
	return 0;
}

int eDVBCISlot::setEnabled(bool enabled)
{
	eDebug("[CI%d] Enabled: %d, state %d", slotid, enabled, state);
	if (enabled && state != stateDisabled)
		return 0;

	if (!enabled && state == stateDisabled)
		return 0;

	if (enabled)
		openDevice();
	else
	{
		closeDevice();
		/* emit */ eDVBCI_UI::getInstance()->m_messagepump.send(eDVBCIInterfaces::Message(eDVBCIInterfaces::Message::slotStateChanged, getSlotID(), 3)); // state disabled
	}
	return 0;
}

eAutoInitP0<eDVBCIInterfaces> init_eDVBCIInterfaces(eAutoInitNumbers::dvb, "CI Slots");
