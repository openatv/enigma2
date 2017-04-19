#include <sstream>
#include <fcntl.h>
#include <sys/ioctl.h>

#include <ios>
#include <fstream>
#include <sstream>
#include <iomanip>

#include <lib/base/init.h>
#include <lib/base/init_num.h>
#include <lib/base/cfile.h>
#include <lib/base/ebase.h>

#include <lib/base/eerror.h>
#include <lib/base/nconfig.h> // access to python config
#include <lib/dvb/db.h>
#include <lib/dvb/pmt.h>
#include <lib/dvb_ci/dvbci.h>
#include <lib/dvb_ci/dvbci_session.h>
#include <lib/dvb_ci/dvbci_camgr.h>
#include <lib/dvb_ci/dvbci_ui.h>
#include <lib/dvb_ci/dvbci_appmgr.h>
#include <lib/dvb_ci/dvbci_mmi.h>

#include <dvbsi++/ca_program_map_section.h>

//#define CIDEBUG 1

#ifdef CIDEBUG
	#define eDebugCI(x...) eDebug(x)
#else
	#define eDebugCI(x...)
#endif

eDVBCIInterfaces *eDVBCIInterfaces::instance = 0;


eCIClient::eCIClient(eDVBCIInterfaces *handler, int socket) : eUnixDomainSocket(socket, 1, eApp), parent(handler)
{
	receivedData = NULL;
	receivedCmd = 0;
	CONNECT(connectionClosed_, eCIClient::connectionLost);
	CONNECT(readyRead_, eCIClient::dataAvailable);
}

void eCIClient::connectionLost()
{
	if (parent) parent->connectionLost();
}

void eCIClient::dataAvailable()
{
	if (!receivedCmd)
	{
		if ((unsigned int)bytesAvailable() < sizeof(ciplus_header)) return;
		if ((unsigned int)readBlock((char*)&header, sizeof(ciplus_header)) < sizeof(ciplus_header)) return;
		header.magic = ntohl(header.magic);
		header.cmd = ntohl(header.cmd);
		header.size = ntohl(header.size);
		if (header.magic != CIPLUSHELPER_MAGIC)
		{
			if (parent) parent->connectionLost();
			return;
		}
		receivedCmd = header.cmd;
		receivedCmdSize = header.size;
	}
	if (receivedCmdSize)
	{
		if ((unsigned int)bytesAvailable() < receivedCmdSize) return;
		if (receivedCmdSize) delete [] receivedData;
		receivedData = new unsigned char[receivedCmdSize];
		if ((unsigned int)readBlock((char*)receivedData, receivedCmdSize) < receivedCmdSize) return;

		ciplus_message *message = (ciplus_message *)receivedData;
		switch (header.cmd)
		{
		default:
			{
				unsigned char *data = &receivedData[sizeof(ciplus_message)];
				parent->getSlot(ntohl(message->slot))->send(data, ntohl(message->size));
			}
			break;
		case eCIClient::CIPLUSHELPER_STATE_CHANGED:
			{
				eDVBCISession::setAction(ntohl(message->session), receivedData[sizeof(ciplus_message)]);
			}
			break;
		}
		receivedCmdSize = 0;
		receivedCmd = 0;
	}
}

void eCIClient::sendData(int cmd, int slot, int session, unsigned long idtag, unsigned char *tag, unsigned char *data, int len)
{
	ciplus_message message;
	message.slot = ntohl(slot);
	message.idtag = ntohl(idtag);
	memcpy(&message.tag, tag, 4);
	message.session = ntohl(session);
	message.size = ntohl(len);

	ciplus_header header;
	header.magic = htonl(CIPLUSHELPER_MAGIC);
	header.size = htonl(sizeof(message) + len);
	header.cmd = htonl(cmd);

	writeBlock((const char*)&header, sizeof(header));
	writeBlock((const char*)&message, sizeof(message));
	if (len)
	{
		writeBlock((const char*)data, len);
	}
}

void eDVBCIInterfaces::newConnection(int socket)
{
	if (client)
	{
		delete client;
	}
	client = new eCIClient(this, socket);
}

void eDVBCIInterfaces::connectionLost()
{
	if (client)
	{
		delete client;
		client = NULL;
	}
}

void eDVBCIInterfaces::sendDataToHelper(int cmd, int slot, int session, unsigned long idtag, unsigned char *tag, unsigned char *data, int len)
{
	if (client)	client->sendData(cmd, slot, session, idtag, tag, data, len);
}

bool eDVBCIInterfaces::isClientConnected()
{
	if (client) return true;
	return false;
}

#define CIPLUS_SERVER_SOCKET "/tmp/.listen.ciplus.socket"

eDVBCIInterfaces::eDVBCIInterfaces()
 : eServerSocket(CIPLUS_SERVER_SOCKET, eApp)
{
	int num_ci = 0;
	std::stringstream path;

	instance = this;
	client = NULL;

	eDebug("[CI] scanning for common interfaces..");

	for (;;)
	{
		path.str("");
		path.clear();
		path << "/dev/ci" << num_ci;

		if(::access(path.str().c_str(), R_OK) < 0)
			break;

		ePtr<eDVBCISlot> cislot;

		cislot = new eDVBCISlot(eApp, num_ci);
		m_slots.push_back(cislot);

		++num_ci;
	}

	for (eSmartPtrList<eDVBCISlot>::iterator it(m_slots.begin()); it != m_slots.end(); ++it)
		it->setSource("A");

	for (int tuner_no = 0; tuner_no < 26; ++tuner_no) // NOTE: this assumes tuners are A .. Z max.
	{
		path.str("");
		path.clear();
		path << "/proc/stb/tsmux/input" << tuner_no << "_choices";

		if(::access(path.str().c_str(), R_OK) < 0)
			break;

		setInputSource(tuner_no, eDVBCISlot::getTunerLetter(tuner_no));
	}

	eDebug("[CI] done, found %d common interface slots", num_ci);
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

	eDebug("[CI] FIXME: request for unknown slot");

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

	return slot->reset();
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
		eDVBCISlot *tmp = it->cislot;
		while (tmp && tmp != slot)
			tmp = tmp->linked_next;
		if (tmp)
		{
			tmp->sendCAPMT(it->pmthandler);  // send capmt
			break;
		}
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
	if (slot->use_count)
	{
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
					if (hSlot == slot) {
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
			setInputSource(slot->current_tuner, slot->current_source);
		slot->linked_next = 0;
		slot->use_count=0;
		slot->plugged=true;
		slot->user_mapped=false;
		slot->removeService(0xFFFF);
		recheckPMTHandlers();
	}
}

static bool canDescrambleMultipleServices(int slotid)
{
	char configStr[255];
	snprintf(configStr, 255, "config.ci.%d.canDescrambleMultipleServices", slotid);
	std::string str = eConfigManager::getConfigValue(configStr);
	if ( str == "auto" )
	{
		std::string appname = eDVBCI_UI::getInstance()->getAppName(slotid);
		if (appname.find("AlphaCrypt") != std::string::npos || appname.find("Multi") != std::string::npos)
			return true;
	}
	else if (str == "yes")
		return true;
	return false;
}

void eDVBCIInterfaces::recheckPMTHandlers()
{
	eDebugCI("[CI] recheckPMTHAndlers()");
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

		eDebugCI("[CI] recheck %p %s", pmthandler, ref.toString().c_str());
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
			while(tmp)
			{
				if (!tmp->running_services.empty())
					break;
				tmp=tmp->linked_next;
			}
			if (tmp) // we dont like to change tsmux for running services
			{
				eDebugCI("[CI] already assigned and running CI!\n");
				continue;
			}
		}

		if (!pmthandler->getProgramInfo(p))
		{
			int cnt=0;
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
			eDebugCI("[CI] check Slot %d", ci_it->getSlotID());
			bool useThis=false;
			bool user_mapped=true;
			eDVBCICAManagerSession *ca_manager = ci_it->getCAManager();

			if (ca_manager)
			{
				int mask=0;
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
						if ( z != ci_caids.end() && *z == *ca )
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
				while(tmp)
				{
					if (tmp == ci_it)
						break;
					tmp=tmp->linked_next;
				}
				if (tmp) // ignore already assigned cislots...
				{
					eDebugCI("[CI] already assigned!");
					continue;
				}
				eDebugCI("[CI] current slot %d usecount %d", ci_it->getSlotID(), ci_it->use_count);
				if (ci_it->use_count)  // check if this CI can descramble more than one service
				{
					bool found = false;
					useThis = false;
					PMTHandlerList::iterator tmp = m_pmt_handlers.begin();
					while (!found && tmp != m_pmt_handlers.end())
					{
						eDebugCI("[CI] .");
						eDVBCISlot *tmp_cislot = tmp->cislot;
						while (!found && tmp_cislot)
						{
							eDebugCI("[CI] ..");
							eServiceReferenceDVB ref2;
							tmp->pmthandler->getServiceReference(ref2);
							if ( tmp_cislot == ci_it && it->pmthandler != tmp->pmthandler )
							{
								eDebugCI("[CI] check pmthandler %s for same service/tp", ref2.toString().c_str());
								eDVBChannelID s1, s2;
								if (ref != ref2)
								{
									eDebugCI("[CI] different services!");
									ref.getChannelID(s1);
									ref2.getChannelID(s2);
								}
								if (ref == ref2 || (s1 == s2 && canDescrambleMultipleServices(tmp_cislot->getSlotID())))
								{
									found = true;
									eDebugCI("[CI] found!");
									eDVBCISlot *tmpci = it->cislot = tmp->cislot;
									while(tmpci)
									{
										++tmpci->use_count;
										eDebug("[CI] (2)CISlot %d, usecount now %d", tmpci->getSlotID(), tmpci->use_count);
										tmpci=tmpci->linked_next;
									}
								}
							}
							tmp_cislot=tmp_cislot->linked_next;
						}
						eDebugCI("[CI] ...");
						++tmp;
					}
				}

				if (useThis)
				{
					if (ci_it->user_mapped)  // we dont like to link user mapped CIs
					{
						eDebugCI("[CI] user mapped CI already in use... dont link!");
						continue;
					}

					++ci_it->use_count;
					eDebug("[CI] (1)Slot %d, usecount now %d", ci_it->getSlotID(), ci_it->use_count);

					std::stringstream ci_source;
					ci_source << "CI";
					if (getNumOfSlots() > 1) // Only receivers with more that 1 CI expect number after CI
					{
						ci_source << ci_it->getSlotID();
					}

					if (!it->cislot)
					{
						int tunernum = -1;
						eUsePtr<iDVBChannel> channel;
						if (!pmthandler->getChannel(channel))
						{
							ePtr<iDVBFrontend> frontend;
							if (!channel->getFrontend(frontend))
							{
								eDVBFrontend *fe = (eDVBFrontend*) &(*frontend);
								tunernum = fe->getSlotID();
							}
						}
						ASSERT(tunernum != -1);
						ci_it->current_tuner = tunernum;
						setInputSource(tunernum, ci_source.str());
						ci_it->setSource(eDVBCISlot::getTunerLetter(tunernum));
					}
					else
					{
						ci_it->current_tuner = it->cislot->current_tuner;
						ci_it->linked_next = it->cislot;
						ci_it->setSource(ci_it->linked_next->current_source);
						ci_it->linked_next->setSource(ci_source.str());
					}
					it->cislot = ci_it;
					eDebugCI("[CI] assigned!");
					gotPMT(pmthandler);
				}

				if (it->cislot && user_mapped) // CI assigned to this pmthandler in this run.. and user mapped? then we break here.. we dont like to link other CIs to user mapped CIs
				{
					eDebugCI("[CI] user mapped CI assigned... dont link CIs!");
					break;
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
		eDVBCISlot *base_slot = slot;
		eDVBServicePMTHandler *pmthandler = it->pmthandler;
		m_pmt_handlers.erase(it);

		eServiceReferenceDVB service_to_remove;
		pmthandler->getServiceReference(service_to_remove);

		bool sameServiceExist=false;
		for (PMTHandlerList::iterator i=m_pmt_handlers.begin(); i != m_pmt_handlers.end(); ++i)
		{
			if (i->cislot)
			{
				eServiceReferenceDVB ref;
				i->pmthandler->getServiceReference(ref);
				if ( ref == service_to_remove )
				{
					sameServiceExist=true;
					break;
				}
			}
		}

		while(slot)
		{
			eDVBCISlot *next = slot->linked_next;
			if (!sameServiceExist)
			{
				eDebug("[eDVBCIInterfaces] remove last pmt handler for service %s send empty capmt",
					service_to_remove.toString().c_str());
				std::vector<uint16_t> caids;
				caids.push_back(0xFFFF);
				slot->sendCAPMT(pmthandler, caids);  // send a capmt without caids to remove a running service
				slot->removeService(service_to_remove.getServiceID().get());
			}

			if (!--slot->use_count)
			{
				if (slot->linked_next)
					slot->linked_next->setSource(slot->current_source);
				else
					setInputSource(slot->current_tuner, slot->current_source);

				if (base_slot != slot)
				{
					eDVBCISlot *tmp = it->cislot;
					while(tmp->linked_next != slot)
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
	eDebug("[eDVBCIInterfaces] gotPMT");
	PMTHandlerList::iterator it=std::find(m_pmt_handlers.begin(), m_pmt_handlers.end(), pmthandler);
	if (it != m_pmt_handlers.end() && it->cislot)
	{
		eDVBCISlot *tmp = it->cislot;
		while(tmp)
		{
			eDebugCI("[CI] check slot %d %d %d", tmp->getSlotID(), tmp->running_services.empty(), canDescrambleMultipleServices(tmp->getSlotID()));
			if (tmp->running_services.empty() || canDescrambleMultipleServices(tmp->getSlotID()))
				tmp->sendCAPMT(pmthandler);
			tmp = tmp->linked_next;
		}
	}
}

int eDVBCIInterfaces::getMMIState(int slotid)
{
	eDVBCISlot *slot;

	if( (slot = getSlot(slotid)) == 0 )
		return -1;

	return slot->getMMIState();
}

int eDVBCIInterfaces::setInputSource(int tuner_no, const std::string &source)
{
	char buf[64];
	snprintf(buf, sizeof(buf), "/proc/stb/tsmux/input%d", tuner_no);

	if (CFile::write(buf, source.c_str()) == -1)
	{
		eDebug("[CI] eDVBCIInterfaces setInputSource for input %s failed!", source.c_str());
		return 0;
	}

	eDebug("[CI] eDVBCIInterfaces setInputSource(%d, %s)", tuner_no, source.c_str());
	return 0;
}

PyObject *eDVBCIInterfaces::getDescrambleRules(int slotid)
{
	eDVBCISlot *slot = getSlot(slotid);
	if (!slot)
	{
		char tmp[255];
		snprintf(tmp, 255, "eDVBCIInterfaces::getDescrambleRules try to get rules for CI Slot %d... but just %zd slots are available", slotid, m_slots.size());
		PyErr_SetString(PyExc_StandardError, tmp);
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
	while(caids)
	{
		--caids;
		PyList_SET_ITEM(caid_list, caids, PyLong_FromLong(*caid_it));
		++caid_it;
	}
	serviceSet::iterator ref_it(slot->possible_services.begin());
	while(services)
	{
		--services;
		PyList_SET_ITEM(service_list, services, PyString_FromString(ref_it->toString().c_str()));
		++ref_it;
	}
	providerSet::iterator provider_it(slot->possible_providers.begin());
	while(providers)
	{
		ePyObject tuple = PyTuple_New(2);
		PyTuple_SET_ITEM(tuple, 0, PyString_FromString(provider_it->first.c_str()));
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

RESULT eDVBCIInterfaces::setDescrambleRules(int slotid, SWIG_PYOBJECT(ePyObject) obj )
{
	eDVBCISlot *slot = getSlot(slotid);
	if (!slot)
	{
		char tmp[255];
		snprintf(tmp, 255, "eDVBCIInterfaces::setDescrambleRules try to set rules for CI Slot %d... but just %zd slots are available", slotid, m_slots.size());
		PyErr_SetString(PyExc_StandardError, tmp);
		return -1;
	}
	if (!PyTuple_Check(obj))
	{
		char tmp[255];
		snprintf(tmp, 255, "2nd argument of setDescrambleRules is not a tuple.. it is a '%s'!!", PyObject_TypeStr(obj));
		PyErr_SetString(PyExc_StandardError, tmp);
		return -1;
	}
	if (PyTuple_Size(obj) != 3)
	{
		const char *errstr = "eDVBCIInterfaces::setDescrambleRules not enough entrys in argument tuple!!\n"
			"first argument should be a pythonlist with possible services\n"
			"second argument should be a pythonlist with possible providers/dvbnamespace tuples\n"
			"third argument should be a pythonlist with possible caids";
		PyErr_SetString(PyExc_StandardError, errstr);
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
		PyErr_SetString(PyExc_StandardError, errstr);
		return -1;
	}
	slot->possible_caids.clear();
	slot->possible_services.clear();
	slot->possible_providers.clear();
	int size = PyList_Size(service_list);
	while(size)
	{
		--size;
		ePyObject refstr = PyList_GET_ITEM(service_list, size);
		if (!PyString_Check(refstr))
		{
			char buf[255];
			snprintf(buf, 255, "eDVBCIInterfaces::setDescrambleRules entry in service list is not a string.. it is '%s'!!", PyObject_TypeStr(refstr));
			PyErr_SetString(PyExc_StandardError, buf);
			return -1;
		}
		char *tmpstr = PyString_AS_STRING(refstr);
		eServiceReference ref(tmpstr);
		if (ref.valid())
			slot->possible_services.insert(ref);
		else
			eDebug("[CI] eDVBCIInterfaces::setDescrambleRules '%s' is not a valid service reference... ignore!!", tmpstr);
	};
	size = PyList_Size(provider_list);
	while(size)
	{
		--size;
		ePyObject tuple = PyList_GET_ITEM(provider_list, size);
		if (!PyTuple_Check(tuple))
		{
			char buf[255];
			snprintf(buf, 255, "eDVBCIInterfaces::setDescrambleRules entry in provider list is not a tuple it is '%s'!!", PyObject_TypeStr(tuple));
			PyErr_SetString(PyExc_StandardError, buf);
			return -1;
		}
		if (PyTuple_Size(tuple) != 2)
		{
			char buf[255];
			snprintf(buf, 255, "eDVBCIInterfaces::setDescrambleRules provider tuple has %zd instead of 2 entries!!", PyTuple_Size(tuple));
			PyErr_SetString(PyExc_StandardError, buf);
			return -1;
		}
		if (!PyString_Check(PyTuple_GET_ITEM(tuple, 0)))
		{
			char buf[255];
			snprintf(buf, 255, "eDVBCIInterfaces::setDescrambleRules 1st entry in provider tuple is not a string it is '%s'", PyObject_TypeStr(PyTuple_GET_ITEM(tuple, 0)));
			PyErr_SetString(PyExc_StandardError, buf);
			return -1;
		}
		if (!PyLong_Check(PyTuple_GET_ITEM(tuple, 1)))
		{
			char buf[255];
			snprintf(buf, 255, "eDVBCIInterfaces::setDescrambleRules 2nd entry in provider tuple is not a long it is '%s'", PyObject_TypeStr(PyTuple_GET_ITEM(tuple, 1)));
			PyErr_SetString(PyExc_StandardError, buf);
			return -1;
		}
		char *tmpstr = PyString_AS_STRING(PyTuple_GET_ITEM(tuple, 0));
		uint32_t orbpos = PyLong_AsUnsignedLong(PyTuple_GET_ITEM(tuple, 1));
		if (strlen(tmpstr))
			slot->possible_providers.insert(std::pair<std::string, uint32_t>(tmpstr, orbpos));
		else
			eDebug("[CI] eDVBCIInterfaces::setDescrambleRules ignore invalid entry in provider tuple (string is empty)!!");
	};
	size = PyList_Size(caid_list);
	while(size)
	{
		--size;
		ePyObject caid = PyList_GET_ITEM(caid_list, size);
		if (!PyLong_Check(caid))
		{
			char buf[255];
			snprintf(buf, 255, "eDVBCIInterfaces::setDescrambleRules entry in caid list is not a long it is '%s'!!", PyObject_TypeStr(caid));
			PyErr_SetString(PyExc_StandardError, buf);
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
	eDVBCISlot *slot = getSlot(slotid);
	if (!slot)
	{
		char tmp[255];
		snprintf(tmp, 255, "eDVBCIInterfaces::readCICaIds try to get CAIds for CI Slot %d... but just %zd slots are available", slotid, m_slots.size());
		PyErr_SetString(PyExc_StandardError, tmp);
	}
	else
	{
		int idx=0;
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

int eDVBCIInterfaces::setCIClockRate(int slotid, int rate)
{
	eDVBCISlot *slot = getSlot(slotid);
	if (slot)
		return slot->setClockRate(rate);
	return -1;
}

int eDVBCISlot::send(const unsigned char *data, size_t len)
{
	int res=0;
	//int i;
	//eDebugNoNewLineStart("< ");
	//for(i=0;i<len;i++)
	//	eDebugNoNewLine("%02x ",data[i]);
	//eDebugNoNewLine("\n");

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
	eDebugCI("[CI] Slot %d what %d\n", getSlotID(), what);
	if(what == eSocketNotifier::Priority) {
		if(state != stateRemoved) {
			state = stateRemoved;
			while(sendqueue.size())
			{
				delete [] sendqueue.top().data;
				sendqueue.pop();
			}
			eDVBCISession::deleteSessions(this);
			eDVBCIInterfaces::getInstance()->ciRemoved(this);
			notifier->setRequested(eSocketNotifier::Read);
			eDVBCI_UI::getInstance()->setState(getSlotID(),0);
		}
		return;
	}

	if (state == stateInvalid)
		reset();

	if(state != stateInserted) {
		eDebug("[CI] ci inserted in slot %d", getSlotID());
		state = stateInserted;
		eDVBCI_UI::getInstance()->setState(getSlotID(),1);
		notifier->setRequested(eSocketNotifier::Read|eSocketNotifier::Priority);
		/* enable PRI to detect removal or errors */
	}

	if (what & eSocketNotifier::Read) {
		uint8_t data[4096];
		int r;
		r = ::read(fd, data, 4096);
		if(r > 0) {
//			int i;
//			eDebugNoNewLineStart("> ");
//			for(i=0;i<r;i++)
//				eDebugNoNewLine("%02x ",data[i]);
//			eDebugNoNewLine("\n");
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
	linked_next = 0;
	user_mapped = false;
	plugged = true;

	slotid = nr;

	sprintf(filename, "/dev/ci%d", nr);

//	possible_caids.insert(0x1702);
//	possible_providers.insert(providerPair("PREMIERE", 0xC00000));
//	possible_services.insert(eServiceReference("1:0:1:2A:4:85:C00000:0:0:0:"));

	fd = ::open(filename, O_RDWR | O_NONBLOCK | O_CLOEXEC);

	eDebugCI("[CI] Slot %d has fd %d", getSlotID(), fd);
	state = stateInvalid;

	if (fd >= 0)
	{
		notifier = eSocketNotifier::create(context, fd, eSocketNotifier::Read | eSocketNotifier::Priority | eSocketNotifier::Write);
		CONNECT(notifier->activated, eDVBCISlot::data);
	} else
	{
		perror(filename);
	}
}

eDVBCISlot::~eDVBCISlot()
{
	eDVBCISession::deleteSessions(this);
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
	eDebug("[CI] Slot %d: reset requested", getSlotID());

	if (state == stateInvalid)
	{
		unsigned char buf[256];
		eDebug("[CI] flush");
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
	eDebug("[CI] Slot %d: startMMI()", getSlotID());

	if(application_manager)
		application_manager->startMMI();

	return 0;
}

int eDVBCISlot::stopMMI()
{
	eDebug("[CI] Slot %d: stopMMI()", getSlotID());

	if(mmi_session)
		mmi_session->stopMMI();

	return 0;
}

int eDVBCISlot::answerText(int answer)
{
	eDebug("[CI] Slot %d: answerText(%d)", getSlotID(), answer);

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
	eDebug("[CI] Slot %d: answerENQ(%s)", getSlotID(), value);

	if(mmi_session)
		mmi_session->answerEnq(value);

	return 0;
}

int eDVBCISlot::cancelEnq()
{
	eDebug("[CI] Slot %d: cancelENQ", getSlotID());

	if(mmi_session)
		mmi_session->cancelEnq();

	return 0;
}

int eDVBCISlot::sendCAPMT(eDVBServicePMTHandler *pmthandler, const std::vector<uint16_t> &ids)
{
	if (!ca_manager)
	{
		eDebug("[CI] no ca_manager (no CI plugged?)");
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
		bool sendEmpty = caids.size() == 1 && caids[0] == 0xFFFF;

		if ( it != running_services.end() &&
			(pmt_version == it->second) &&
			!sendEmpty )
		{
			eDebug("[CI] [eDVBCISlot] dont send self capmt version twice");
			return -1;
		}

		std::vector<ProgramMapSection*>::const_iterator i=ptr->getSections().begin();
		if ( i == ptr->getSections().end() )
			return -1;
		else
		{
			unsigned char raw_data[2048];

//			eDebug("[CI] send %s capmt for service %04x to slot %d",
//				it != running_services.end() ? "UPDATE" : running_services.empty() ? "ONLY" : "ADD",
//				program_number, slotid);

			CaProgramMapSection capmt(*i++,
				it != running_services.end() ? 0x05 /*update*/ : running_services.empty() ? 0x03 /*only*/ : 0x04 /*add*/, 0x01, caids );
			while( i != ptr->getSections().end() )
			{
		//			eDebug("[CI] append");
				capmt.append(*i++);
			}
			capmt.writeToBuffer(raw_data);

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

			if (sendEmpty)
			{
//				eDebugNoNewLineStart("[CI[ SEND EMPTY CAPMT.. old version is %02x", raw_data[hlen+3]);
				if (sendEmpty && running_services.size() == 1)  // check if this is the capmt for the last running service
					raw_data[hlen] = 0x03; // send only instead of update... because of strange effects with alphacrypt
				raw_data[hlen+3] &= ~0x3E;
				raw_data[hlen+3] |= ((pmt_version+1) & 0x1F) << 1;
//				eDebugNoNewLine(" new version is %02x\n", raw_data[hlen+3]);
			}

//			eDebugNoNewLineStart("[CI[ ca_manager %p dump capmt:", ca_manager);
//			for(int i=0;i<wp;i++)
//				eDebugNoNewLine("%02x ", raw_data[i]);
//			eDebugNoNewLine("\n");

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

int eDVBCISlot::setSource(const std::string &source)
{
	char buf[64];
	current_source = source;

	if (eDVBCIInterfaces::getInstance()->getNumOfSlots() > 1) // FIXME .. we force DM8000 when more than one CI Slot is avail
	{
		snprintf(buf, sizeof(buf), "/proc/stb/tsmux/ci%d_input", slotid);
	}
	else // DM7025
	{
		snprintf(buf, sizeof(buf), "/proc/stb/tsmux/input2");
	}

	if(CFile::write(buf, source.c_str()) == -1)
	{
		eDebug("[CI] Slot: %d setSource: %s failed!", getSlotID(), source.c_str());
		return 0;
	}

	eDebug("[CI] Slot: %d setSource: %s", getSlotID(), source.c_str());
	return 0;
}

int eDVBCISlot::setClockRate(int rate)
{
	char buf[64];
	snprintf(buf, sizeof(buf), "/proc/stb/tsmux/ci%d_tsclk", slotid);
	if(CFile::write(buf, rate ? "high" : "normal") == -1)
		return -1;
	return 0;
}

eAutoInitP0<eDVBCIInterfaces> init_eDVBCIInterfaces(eAutoInitNumbers::dvb, "CI Slots");
