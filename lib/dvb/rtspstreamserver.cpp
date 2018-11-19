/*
 * Copyright (C) 2017-2027 Catalin Toda <catalinii@yahoo.com>
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 2 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program; if not, write to the Free Software
 * Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307
 * USA
 *
 */

#include <sys/select.h>
#include <unistd.h>
#include <string.h>
#include <strings.h>
#include <sys/types.h>
#include <pwd.h>
#include <shadow.h>
#include <crypt.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <time.h>
#include <linux/dvb/frontend.h>
#include <linux/dvb/dmx.h>
#include <linux/dvb/ca.h>
#include <linux/dvb/version.h>

#include <iomanip>
#include <sstream>

#include <lib/base/modelinformation.h>
#include <lib/base/eerror.h>
#include <lib/base/init.h>
#include <lib/base/init_num.h>
#include <lib/base/wrappers.h>
#include <lib/base/nconfig.h>
#include <lib/base/cfile.h>
#include <lib/base/e2avahi.h>
#include <lib/dvb/decoder.h>
#include <lib/dvb/rtspstreamserver.h>
#include <lib/dvb/encoder.h>
#include <lib/dvb/db.h>
#include <lib/dvb_ci/dvbci.h>
#include <lib/network/uri.h>

#include "absdiff.h"

#define _ADD_PIDS 1
#define _DEL_PIDS 2
#define _PIDS 3

#ifndef SYS_DVBC2
#define SYS_DVBC2 19 // support for DVB-C2 DD
#endif

#ifndef SYS_DVBT2
#define SYS_DVBT2 16
#endif

static int global_stream_id = 0;

const char *app_name = "enigma2";
const char *version = "0.1";

std::set<eServiceReferenceDVB> processed_sr;

eRTSPStreamClient::eRTSPStreamClient(eRTSPStreamServer *handler, int socket, const std::string remotehost)
	: parent(handler), encoderFd(-1), streamFd(socket), streamThread(NULL), m_remotehost(remotehost)
{
	session_id = 0;
	stream_id = 0;
	eDebug("Client starting %d", streamFd);
	init_rtsp();
}

eRTSPStreamClient::~eRTSPStreamClient()
{
	eDebug("Client terminating %d", streamFd);
	pids.clear();
	update_service_list();
	rsn->stop();
	stop();
	if (streamThread)
	{
		streamThread->stop();
		delete streamThread;
	}
	if (encoderFd >= 0)
	{
		if (eEncoder::getInstance())
			eEncoder::getInstance()->freeEncoder(encoderFd);
	}
	if (streamFd >= 0)
		::close(streamFd);
	eDebug("done disconnecting client, %d", streamFd);
}

void eRTSPStreamClient::init_rtsp()
{
	running = false;
	fp = NULL;
	freq = 0;
	pol = -1;
	sys = 0;
	first = true;
	fe = 0;
	src = 0;
	buf_size = 0;
	m_serviceref = "";
	mr = NULL;
	clear_previous_channel = 0;
	m_tuned = 0;
	m_channel = NULL;
	tune_completed = 0;
	m_record_no_pids = 1;
	time_addsr = 0;
	transponder_id = 0;
	proto = PROTO_RTSP_TCP;
}

void eRTSPStreamClient::start()
{
	rsn = eSocketNotifier::create(eApp, streamFd, eSocketNotifier::Read);
	CONNECT(rsn->activated, eRTSPStreamClient::notifier);
}

void eRTSPStreamClient::getFontends(int &dvbt, int &dvbt2, int &dvbs2, int &dvbc, int &dvbc2)
{
	ePtr<eDVBResourceManager> m_res_mgr;
	eDVBResourceManager::getInstance(m_res_mgr);
	eSmartPtrList<eDVBRegisteredFrontend> &frontends = m_res_mgr->m_frontend;
	dvbt = 0;
	dvbt2 = 0;
	dvbs2 = 0;
	dvbc = 0;
	dvbc2 = 0;
	for (eSmartPtrList<eDVBRegisteredFrontend>::iterator it(frontends.begin()); it != frontends.end(); ++it)
	{
		if (it->m_frontend->supportsDeliverySystem((fe_delivery_system_t)SYS_DVBS2, false))
			dvbs2++;
#ifdef SYS_DVBC_ANNEX_A
		if (it->m_frontend->supportsDeliverySystem((fe_delivery_system_t)SYS_DVBC_ANNEX_A, false))
#else
		if (it->m_frontend->supportsDeliverySystem((fe_delivery_system_t)SYS_DVBC_ANNEX_AC, false))
#endif
			dvbc++;
		if (it->m_frontend->supportsDeliverySystem((fe_delivery_system_t)SYS_DVBC2, false))
			dvbc2++;
		if (it->m_frontend->supportsDeliverySystem((fe_delivery_system_t)SYS_DVBT2, false))
			dvbt2++;
		if (it->m_frontend->supportsDeliverySystem((fe_delivery_system_t)SYS_DVBT, false))
			dvbt++;
	}
	dvbt = dvbt - dvbt2;
	dvbc = dvbc - dvbc2;

	if (dvbt < 0)
		dvbt = 0;
	if (dvbc < 0)
		dvbc = 0;

	eDebug("Identified: dvbt %d, dvbt2 %d, dvbs2 %d, dvbc %d, dvbc2 %d", dvbt, dvbt2, dvbs2, dvbc, dvbc2);
}

int eRTSPStreamClient::getOrbitalPosition(int fe, int src)
{
	int op = 0;

	int current_src = 0;
	eDVBSatelliteEquipmentControl *m_sec = eDVBSatelliteEquipmentControl::getInstance();

	if (src < 0 || src >= (int)sizeof(m_sec->m_lnbs))
	{
		eDebug("invalid src %d", src);
		return 0;
	}
	for (int i = 0; i < 144; i++)
	{
		eDVBSatelliteLNBParameters &lnb_param = m_sec->m_lnbs[i];
		int op1 = 0;
		if (lnb_param.m_satellites.size() > 0)
		{
			for (std::map<int, eDVBSatelliteSwitchParameters>::iterator sit = lnb_param.m_satellites.begin(); sit != lnb_param.m_satellites.end(); ++sit)
				op1 = sit->first;
			eDebug("LNB OP %d", op1);
		}
		if ((fe >= 0) && (lnb_param.m_slot_mask & (1 << fe)))
		{
			current_src++;
			op = op1;
		}
		eDebug("%d: orbital position %d, m_slot_mask %d, lnNum %d, old OP %d", i, op1, lnb_param.m_slot_mask, lnb_param.m_satellites.size(), lnb_param.SatCR_idx); //lnb_param.LNBNum, lnb_param.old_orbital_position);
		if (current_src >= src)
		{
			eDebug("orbital position matched to %d", op1);
			op = op1;
			break;
		}
	}
	//		op = sit->first;
	if (op)
		eDebug("found orbital position %d for src %d", op, src);
	else
		eDebug("orbital position not found for src %d", src);
	return op;
}

std::string eRTSPStreamClient::searchServiceRef(int sys, int freq, int pol, int orbital_position, int sid)
{
	eDebug("start %s", __FUNCTION__);
	eDVBFrontendParametersSatellite sat1;
	eDVBFrontendParametersTerrestrial ter1;
	eDVBFrontendParametersCable cab1;
	int found = 0;
	memset(&sat, 0, sizeof(sat));
	memset(&ter, 0, sizeof(ter));
	memset(&cab, 0, sizeof(cab));
	const eServiceReferenceDVB *srvc = NULL;
	for (std::map<eServiceReferenceDVB, ePtr<eDVBService>>::iterator i(m_dvbdb->m_services.begin());
		 i != m_dvbdb->m_services.end(); ++i)
	{
		found = 0;
		unsigned int flags = 0;
		eDVBChannelID chid;
		ePtr<iDVBFrontendParameters> p;
		const eServiceReferenceDVB &s = i->first;
		s.getChannelID(chid);
		m_dvbdb->getChannelFrontendData(chid, p);
		flags = i->second->m_flags;
		if (!p)
			continue;
		if (!p->getDVBS(sat1) && ((sys == SYS_DVBS) || (sys == SYS_DVBS2)))
		{
			//			eDebug("freq = %d, sat.freq %d, OP %d, SOP %d, pol %d pol %d", freq, sat1.frequency, orbital_position, sat1.orbital_position, pol, sat1.polarisation);
			if ((absdiff(sat1.frequency, freq) < 2000) && sat1.polarisation == pol && orbital_position == sat1.orbital_position)
			{
				sat = sat1;
				eDebug("Adding %s to the list for frequency %d (%s) f:%x", s.toString().c_str(), sat.frequency, i->second->m_service_name.c_str(), flags);
				srvc = &i->first;
				found = 1;
			}
		}

		if (!p->getDVBT(ter1) && ((sys == SYS_DVBT) || (sys == SYS_DVBT2)))
		{
			if ((absdiff(ter1.frequency / 1000, freq) < 2000))
			{
				ter = ter1;
				eDebug("Adding %s to the list (%s) f:%x", s.toString().c_str(), i->second->m_service_name.c_str(), flags);
				srvc = &i->first;
				found = 1;
			}
		}
#ifdef SYS_DVBC_ANNEX_A
		if (!p->getDVBC(cab1) && ((sys == SYS_DVBC_ANNEX_A) || (sys == SYS_DVBC2)))
#else
		if (!p->getDVBC(cab1) && ((sys == SYS_DVBC_ANNEX_AC) || (sys == SYS_DVBC2)))
#endif
		{
			if ((absdiff(cab1.frequency, freq) < 2000))
			{
				cab = cab1;
				eDebug("Adding %s to the list (%s) f:%x", s.toString().c_str(), i->second->m_service_name.c_str(), flags);
				srvc = &i->first;
				found = 1;
			}
		}

		std::set<eServiceReferenceDVB>::iterator it = processed_sr.find(s);
		int not_available = (it == processed_sr.end());
		if (found)
		{
			if (addCachedPids(i->second, s))
			{
				if (not_available)
				{
					eDebug("SR %s does not have cached pids", s.toString().c_str());
					not_cached_sr.insert(s);
				}
				else
					eDebug("SR %s was already attempted and does not have cached pids, not adding", s.toString().c_str());
			}
		}
	}
	if (srvc)
	{
		//		return srvc->toString();
		const eServiceReferenceDVB srv(srvc->getDVBNamespace(), srvc->getTransportStreamID(), srvc->getOriginalNetworkID(), eServiceID(sid), srvc->getServiceType(), srvc->getSourceID());
		return srv.toString();
	}
	eDebug("end %s", __FUNCTION__);
	return "";
}

void eRTSPStreamClient::process_pids(int op, const std::string &pid_str)
{
	eDebug("%s: operation %d, pid_str %s (len pids: %d)", __FUNCTION__, op, pid_str.c_str(), pids.size());

	if (op == _PIDS)
	{
		pids.clear();

		if (pid_str.find("all") != std::string::npos)
		{
			pids.insert(8192);
			update_service_list();
			return;
		}
	}

	std::stringstream ss(pid_str);
	std::string s;

	while (!ss.eof())
	{
		std::getline(ss, s, ',');
		if (s.empty())
			break;
		int p = atoi(s.c_str());
		if (p < 0 || p > 8191)
			continue;
		if (op == _PIDS || op == _ADD_PIDS)
			add_pid(p);
		if (op == _DEL_PIDS)
			del_pid(p);
	}
	update_service_list();
}

const char *fe_delsys[] =
	{"undefined", "dvbc", "dvbcb", "dvbt", "dss", "dvbs", "dvbs2", "dvbh", "isdbt",
	 "isdbs", "isdbc", "atsc", "atscmh", "dmbth", "cmmb", "dab", "dvbt2",
	 "turbo", "dvbcc", "dvbc2",
	 NULL};

const char *fe_pol[] = {"h", "v", "l", "r", NULL};

int eRTSPStreamClient::satip2enigma(std::string satipstr)
{
	int new_freq = 0, new_pol = -1, new_sys = 0, sid = 0;
	int do_tune = 0;

	eDVBResourceManager::getInstance(m_mgr);
	/* als Primary datenbank setzen */
	m_dvbdb = eDVBDB::getInstance();
	eDebug("Start %s", __FUNCTION__);

	URI u(satipstr); // parse URL using new class URI

	eDebug("Is URL %s valid? %d fe=%s src=%s freq=%s msys=%s pol=%s sid=%s addpids=%s delpids=%s pids=%s",
		   satipstr.c_str(), u.Valid(), u.Query("fe").c_str(), u.Query("src").c_str(), u.Query("freq").c_str(),
		   u.Query("msys").c_str(), u.Query("pol").c_str(), u.Query("sid").c_str(), u.Query("addpids").c_str(),
		   u.Query("delpids").c_str(), u.Query("pids").c_str());

	if (!u.Query("fe").empty())
		fe = atoi(u.Query("fe").c_str()) + 1;

	if (!u.Query("src").empty())
		src = atoi(u.Query("src").c_str()) - 1;

	if (!u.Query("freq").empty())
		new_freq = atof(u.Query("freq").c_str()) * 1000;

	if (!u.Query("msys").empty())
	{
		new_sys = 0;
		const char *s = u.Query("msys").c_str();
		for (int i = 0; fe_delsys[i]; i++)
			if (!strncasecmp(s, fe_delsys[i], strlen(fe_delsys[i])))
				new_sys = i;
	}

	if (!u.Query("pol").empty())
	{
		new_pol = -1;
		const char *s = u.Query("pol").c_str();
		for (int i = 0; fe_pol[i]; i++)
			if (!strncasecmp(s, fe_pol[i], strlen(fe_pol[i])))
				new_pol = i;
	}

	if (!u.Query("sid").empty())
		sid = atoi(u.Query("sid").c_str());

	if (freq && new_freq && freq != new_freq)
		do_tune = 1;

	if (pol != -1 && new_pol != -1 && pol != new_pol)
		do_tune = 1;

	eDebug("initial values, freq %d, pol %d, sys %d, old freq = %d, tune %d", new_freq, new_pol, new_sys, freq, do_tune);

	if (do_tune)
	{
		eDebug("Tuning multiple transponders not supported, state %d", m_state);
		clear_previous_channel = 1;
		this->pids.clear();
		//	m_state = stateIdle;
		update_pids();
		return -1;
		stop();

		eDebug("free service handler, state %d", m_state);
		m_service_handler.free();

		eDebug("done freeing service handler");
		m_mgr->removeChannel(m_channel);
		m_channel->stop();
		m_record = NULL;
		init_rtsp();
		clear_previous_channel = 1;
		//return -1;
	}

	if (new_freq)
		freq = new_freq;
	if (new_pol != -1)
		pol = new_pol;
	if (new_sys)
		sys = new_sys;

	if (!u.Query("addpids").empty())
		process_pids(_ADD_PIDS, u.Query("addpids"));

	if (!u.Query("delpids").empty())
		process_pids(_DEL_PIDS, u.Query("delpids"));

	if (!u.Query("pids").empty() && u.Query("addpids").empty() && u.Query("delpids").empty())
		process_pids(_PIDS, u.Query("pids"));

	int op = 0;
	if (sys == SYS_DVBS || sys == SYS_DVBS2)
		op = getOrbitalPosition(fe, src);
	// searchServiceRef should be executed just once, when freq= is specified

	std::string sref;
	if (new_freq > 0)
	{
		sref = searchServiceRef(sys, freq, pol, op, sid);
		eDebug("tunning to %d, pol %d, sys %d -> SR: %s", freq, pol, sys, sref.c_str());
	}

	if ((new_freq > 0) && !sref.empty()) // 0 - horizontal, 1 - vertical , 2 ->left, 3->Right
	{
		eDebug("Using service ref %s, state %d %d", sref.c_str(), m_state, stateIdle);
		m_serviceref = sref;
		running = true;
		if (!stream_id)
		{
			stream_id = __sync_add_and_fetch(&global_stream_id, 1);
			session_id = random();
		}
	}
	else
		eDebug("no service ref used");
	return 0;
}

int eRTSPStreamClient::addCachedPids(ePtr<eDVBService> service, eServiceReferenceDVB s)
{
	int found = 0;
	for (int x = 0; x < 5; ++x)
	{
		int entry = service->getCacheEntry((eDVBService::cacheID)x);
		if (entry != -1)
		{
			eDebug("Found cached pid %d [%x]", entry, entry);
			pid_sr[entry] = s;
			found = 1;
		}
	}
	return !found;
}

void eRTSPStreamClient::update_service_list()
{
	eServiceReferenceDVB sr;
	//	uint64_t now = eFilePushThreadRecorder::getTick();
	std::set<eServiceReferenceDVB> new_sr, obsolete_sr, delete_cached;
	if (clear_previous_channel == 1)
		return;

	for (std::map<eServiceReferenceDVB, eDVBServicePMTHandler *>::iterator it = active_services.begin(); it != active_services.end(); it++)
		obsolete_sr.insert(it->first);

	std::set<eServiceReferenceDVB>::iterator it;

	// check if we have cached vpid, if no keep the PMTHandler added until we do

	for (it = not_cached_sr.begin(); it != not_cached_sr.end(); it++)
	{
		eServiceReferenceDVB ref = it->getParentServiceReference();
		ePtr<eDVBService> service;

		if (!ref.valid())
			ref = *it;

		if (eDVBDB::getInstance()->getService(ref, service))
		{
			eDebug("Service reference %s not found in the DB", ref.toString().c_str());
			continue;
		}
		eDVBServicePMTHandler::program p;
		std::map<eServiceReferenceDVB, eDVBServicePMTHandler *>::iterator it3 = active_services.find(*it);
		if (it3 != active_services.end())
		{
			eDebug("getting program info for %s", it->toString().c_str());
			if (it3->second->getProgramInfo(p))
				eDebug("getting program info failed for %s", it->toString().c_str());
			else
			{ // cache the pid, next time we won't be needed to create the pmt handler
				int vpid = -1, vpidtype = -1, apid = -1, apidtype = -1;
				for (std::vector<eDVBServicePMTHandler::videoStream>::const_iterator
						 i(p.videoStreams.begin());
					 i != p.videoStreams.end(); ++i)
				{
					eDebug("Identified vpid %d, type %d", i->pid, i->type);
					if (vpid == -1)
					{
						vpid = i->pid;
						vpidtype = i->type;
					}
				}
				for (std::vector<eDVBServicePMTHandler::audioStream>::const_iterator
						 i(p.audioStreams.begin());
					 i != p.audioStreams.end(); ++i)
				{
					eDebug("Identified apid %d, type %d", i->pid, i->type); // we do not really need the apids, for video channels
					if (apid == -1)
					{
						apid = i->pid;
						apidtype = i->type;
					}
				}

				if (apid != -1) // keep code consistent with streamdvb.cpp: eDVBServicePlay::selectAudioStream
				{
					eDebug("Adding apid %d for service %s", apid, ref.toString().c_str());
					service->setCacheEntry(eDVBService::cMPEGAPID, apidtype == eDVBAudio::aMPEG ? apid : -1);
					service->setCacheEntry(eDVBService::cAC3PID, apidtype == eDVBAudio::aAC3 ? apid : -1);
					service->setCacheEntry(eDVBService::cDDPPID, apidtype == eDVBAudio::aDDP ? apid : -1);
					service->setCacheEntry(eDVBService::cAACHEAPID, apidtype == eDVBAudio::aAACHE ? apid : -1);
					service->setCacheEntry(eDVBService::cAACAPID, apidtype == eDVBAudio::aAAC ? apid : -1);
					service->setCacheEntry(eDVBService::cDRAAPID, apidtype == eDVBAudio::aDRA ? apid : -1);
					if (vpid == -1)
						continue;
				}
				if (vpid != -1) // keep code consistent with streamdvb.cpp: eDVBServicePlay::updateDecoder
				{
					eDebug("Adding vpid %d for service %s", vpid, ref.toString().c_str());
					service->setCacheEntry(eDVBService::cVPID, vpid);
					service->setCacheEntry(eDVBService::cVTYPE, vpidtype == eDVBVideo::MPEG2 ? -1 : vpidtype);
					pid_sr[vpid] = ref;
					delete_cached.insert(ref);
					continue;
				}
			}
		}
		if (m_record && !time_addsr)
			time_addsr = eFilePushThreadRecorder::getTick();
		if (time_addsr && (eFilePushThreadRecorder::getTick() - time_addsr > 2000))
		{
			eDebug("deleting SR %s because it timed out", ref.toString().c_str());
			delete_cached.insert(ref);
			processed_sr.insert(ref);
			continue;
		}
		if (pids.size() > 0)
		{
			eDebug("Service Ref %s still does not have cached pids, adding", ref.toString().c_str());
			new_sr.insert(ref);
			obsolete_sr.erase(ref);
		}
	}

	for (it = delete_cached.begin(); it != delete_cached.end(); it++)
		not_cached_sr.erase(*it);

	for (std::set<int>::iterator it = pids.begin(); it != pids.end(); it++)
	{
		int pid = *it;
		std::map<int, eServiceReferenceDVB>::iterator it2 = pid_sr.find(pid);
		if (it2 != pid_sr.end())
		{
			sr = it2->second;
			obsolete_sr.erase(sr);
			std::map<eServiceReferenceDVB, eDVBServicePMTHandler *>::iterator it3 = active_services.find(sr);
			if (it3 == active_services.end())
			{
				eDebug("Found SR %s for pid %d", sr.toString().c_str(), pid);
				new_sr.insert(sr);
			}
			//			else eDebug("SR %s already in the list for pid %d", sr.toString().c_str(), pid );
			buf_size = 1;
		}
	}

	if (m_record || (pids.size() == 0))
	{
		for (std::set<eServiceReferenceDVB>::iterator it = obsolete_sr.begin(); it != obsolete_sr.end(); it++)
		{
			eDVBServicePMTHandler *pmth = active_services[*it];
			eDebug("Deleting service reference %s", it->toString().c_str());
			delete (pmth);
			active_services.erase(*it);
		}

		for (std::set<eServiceReferenceDVB>::iterator it = new_sr.begin(); it != new_sr.end(); it++)
		{

			//			eDVBChannelID chid;//(dvbnamespace,transport_stream_id,original_network_id);
			std::map<eServiceReferenceDVB, eDVBServicePMTHandler *>::iterator it3 = active_services.find(*it);
			if (it3 == active_services.end())
			{
				eServiceReferenceDVB m_ref = *it;
				eDVBServicePMTHandler *pmth = new eDVBServicePMTHandler();
				eDebug("New PMT Handler for SR %s", it->toString().c_str());
				pmth->tune(m_ref, 0, 0, 0, NULL, eDVBServicePMTHandler::scrambled_streamserver, 1);
				active_services[*it] = pmth;
				ePtr<iDVBDemux> m_demux;
				if (!pmth->getDataDemux(m_demux))
				{
					uint8_t d, a, od = -1, oa = -1;
					m_demux->getCADemuxID(d);
					m_demux->getCAAdapterID(a);
					if (!m_service_handler.getDataDemux(m_demux))
					{
						m_demux->getCADemuxID(od);
						m_demux->getCAAdapterID(oa);
					}
					eDebug("got demux %d adapter %d, original demux: %d adapter %d ", d, a, od, oa);
				}

				buf_size = 1;

				//				CONNECT(pmth->serviceEvent, eRTSPStreamClient::serviceEvent);
			}
			//			else eDebug("SR %s already in the list %s", it->toString().c_str(), it3->first.toString().c_str());
		}
	}
}

void eRTSPStreamClient::add_pid(int p)
{
	if (p < 0 || p > 8192)
		return;
	std::set<int>::iterator findIter = std::find(pids.begin(), pids.end(), p);
	if (findIter != pids.end())
	{
		eDebug("pid already in the list %d", p);
		return;
	}
	pids.insert(p);
	update_pids();
	//	update_service_list();
}

void eRTSPStreamClient::update_pids()
{
	eDebug("update pids called: %d pids in the queue", pids.size());
	std::set<int>::iterator it = pids.find(0);
	if (pids.size() > 0 && it == pids.end())
		pids.insert(0);
	if (running && m_record)
		recordPids(pids, -1, -1, iDVBTSRecorder::none);
}

void eRTSPStreamClient::del_pid(int p)
{
	std::set<int>::iterator findIter = std::find(pids.begin(), pids.end(), p);
	if (findIter == pids.end())
	{
		eDebug("pid already removed from the list %d", p);
		return;
	}

	pids.erase(p);
	update_pids();

	//	update_service_list();
}

const char *event_desc[] = {"NoResources", "TuneFailed", "NoPAT", "NoPATEntry", "NoPMT", "NewProgramInfo", "Tuned", "PreStart", "SOF", "EOF", "Misconfiguration", "HBBTVInfo", "Stopped"};

int eRTSPStreamClient::set_demux_buffer(int size)
{
	if (!m_record)
		return -1;
	return 0;
	int rv;
	eDVBTSRecorder *rec = (eDVBTSRecorder *)(iDVBTSRecorder *)m_record;

	rv = rec->setBufferSize(size);
	eDebug("Set DEMUX BUFFER TO %d, returned %d", size, rv);
	return rv;
}

void eRTSPStreamClient::eventUpdate(int event)
{
	if (event >= 0 && event <= (int)sizeof(event_desc))
		eDebug("eventUpdate %s", event_desc[event]);
	else
		eDebug("eventUpdate %d", event);

	if (event == eDVBServicePMTHandler::eventNoResources && m_mgr)
	{
		ePtr<iDVBFrontend> frontend;
		eDebug("No available tunners");
		for (std::list<eDVBResourceManager::active_channel>::iterator i(m_mgr->m_active_channels.begin()); i != m_mgr->m_active_channels.end(); ++i)
		{
			i->m_channel->getFrontend(frontend);
			eDVBFrontend *f = (eDVBFrontend *)(iDVBFrontend *)frontend;
			if (f)
				eDebug("Adapter %d slot %d frequency %d", f->getDVBID(), f->getSlotID(), frontend->readFrontendData(iFrontendInformation_ENUMS::frequency));
		}
	}
	if (event == eDVBServicePMTHandler::eventNoPMT || event == eDVBServicePMTHandler::eventNoPMT || event == eDVBServicePMTHandler::eventNoPATEntry)
		clear_previous_channel = 0;

	if (running && m_record)
	{
		mr = (eDVBRecordFileThread *)((eDVBTSRecorder *)(iDVBTSRecorder *)m_record)->m_thread;
		if (mr->getProtocol() != proto)
		{
			eDebug("Setting protocol %d", proto);
			mr->setProtocol(proto);
			mr->setSession(session_id, stream_id);
			update_pids();
		}
	}

	update_service_list();
}

std::string eRTSPStreamClient::get_current_timestamp()
{
	time_t date;
	struct tm *t;
	char buffer[40];

	time(&date);
	t = gmtime(&date);
	if (!t)
		return "Sat, Jan 1 00:00:20 2000 GMT";

	strftime(buffer, sizeof(buffer), "%a, %b %d %H:%M:%S %Y GMT", t);

	return std::string(buffer);
}

void eRTSPStreamClient::http_response(int sock, int rc, const std::string &ah, const std::string &desc, int cseq, int lr)
{
	std::stringstream ss;

	if (!lr)
		lr = desc.size();

	ss << "RTSP"
	   << "/1.0"
	   << " ";

	if (rc == 200)
		ss << rc << " "
		   << "OK";
	else if (rc == 400)
		ss << rc << " "
		   << "Bad Request";
	else if (rc == 403)
		ss << rc << " "
		   << "Forbidden";
	else if (rc == 404)
		ss << rc << " "
		   << "Not Found";
	else if (rc == 500)
		ss << rc << " "
		   << "Internal Server Error";
	else if (rc == 501)
		ss << rc << " "
		   << "Not Implemented";
	else if (rc == 405)
		ss << rc << " "
		   << "Method Not Allowed";
	else if (rc == 454)
		ss << rc << " "
		   << "Session Not Found";
	else
	{
		rc = 503;
		ss << rc << " "
		   << "Service Unavailable";
	}
	ss << "\r\n";

	ss << "Date: " << get_current_timestamp() << "\r\n";

	if (session_id && ah.find("Session") == std::string::npos && rc != 454)
		ss << "Session: " << std::setfill('0') << std::setw(10) << session_id << "\r\n";

	if (cseq > 0)
		ss << "Cseq: " << cseq << "\r\n";

	ss << ah << "\r\n";

	ss << "Server: " << app_name << "/" << version << "\r\n";

	if (lr > 0)
		ss << "Content-Length: " << lr << "\r\n\r\n"
		   << desc;
	else
		ss << "\r\n";

	char *resp = strdup(ss.str().c_str());
	int len = strlen(resp);

	eDebug("reply to %d, mr %p, len %d: %s", sock, mr, len, resp);

	if (mr)
	{
		mr->pushReply((void *)resp, len);
	}
	else
	{
		struct timespec tv, rem;
		tv.tv_sec = 0;
		tv.tv_nsec = 5000000;
		int times = 20;
		int pos = 0;
		int rb = 0;
		while (pos < len)
		{
			rb = send(sock, resp + pos, len - pos, MSG_NOSIGNAL);
			if (rb > 0)
				pos += rb;
			if (pos == len)
				break;
			if (rb == -1 && (errno != EAGAIN && errno != EWOULDBLOCK))
				break;
			if (rb == 0)
				break;
			eDebug("partial write %d out of %d for socket %d", pos, len, sock);
			nanosleep(&tv, &rem);
			if (times-- < 0)
				break;
		}
		if (pos < len)
			eDebug("error writing %d out of %d to socket %d, errno: %d", pos, len, sock, errno);
		eDebug("wrote successfully %d", len);
	}

	free(resp);
}

const char *fe_inversion[] =
	{"off", "on", "", // auto
	 NULL};
const char *fe_rolloff[] =
	{"0.35", "0.20", "0.25", "", //auto
	 NULL};
const char *fe_modulation_sat[] =
	{"", "qpsk", "8psk", "16qam", "16apsk", "32apsk", "dqpsk",
	 NULL};
const char *fe_modulation_ter[] =
	{"qpsk", "16qam", "64qam", "", "256qam",
	 NULL};
const char *fe_modulation_cab[] =
	{"", "16qam", "32qam", "64qam", "128qam", "256qam",
	 NULL};

const char *fe_pilot[] =
	{"on", "off", "", //auto
	 NULL};
const char *fe_fec[] =
	{"", "12", "23", "34", "56", "78", "89", "35", "45", "910", "67", "25", "none",
	 NULL};

const char *fe_bw[] =
	{"8", "7", "6", " ", //auto
	 NULL};

const char *fe_tmode[] =
	{"2k", "8k", "", //auto
	 "4k", "1k", "16k", "32k", "c1", "c3780",
	 NULL};
const char *fe_gi[] =
	{"132", "116", "18", "14", "", // auto
	 "1128", "19128", "19256", "pn420", "pn595", "pn945",
	 NULL};

std::string eRTSPStreamClient::describe_frontend()
{
	std::stringstream ss;
	int strength = 0, status = 0, snr = 0;
	m_channel = NULL;
	m_channel = (eDVBChannel *)(iDVBChannel *)m_service_handler.m_channel;
	ePtr<iDVBFrontend> frontend;
	if (m_channel)
	{
		m_channel->getFrontend(frontend);
		if (frontend)
		{
			int init_snr = snr = frontend->readFrontendData(iFrontendInformation_ENUMS::signalQuality);
			int init_str = strength = frontend->readFrontendData(iFrontendInformation_ENUMS::signalPower);
			status = ((frontend->readFrontendData(iFrontendInformation_ENUMS::frontendStatus) & FE_HAS_LOCK) > 0);
			if (snr > 65535)
				snr = snr >> 28;
			else
				snr = snr >> 12;
			strength = strength >> 8;
			eDVBFrontend *f = (eDVBFrontend *)(iDVBFrontend *)frontend;
			eDebug("%s: adapter %d slot %d frequency %d, snr: %d -> %d, strength: %d -> %d", __FUNCTION__, f->getDVBID(), f->getSlotID(), frontend->readFrontendData(iFrontendInformation_ENUMS::frequency), init_snr, snr, init_str, strength);
		}
	}
	if (sys == 0)
		ss << "ver=1.0;src=1;tuner=" << fe + 1 << ",0,0,0,0,,,,,,,";
	else if (sys == SYS_DVBS || sys == SYS_DVBS2)
	{
		ss << "ver=1.0;src=" << src + 1;
		ss << ";tuner=" << fe + 1;
		ss << "," << strength;
		ss << "," << status;
		ss << "," << snr;
		ss << "," << sat.frequency / 1000;
		ss << "," << fe_pol[sat.polarisation];
		ss << "," << fe_modulation_sat[sat.modulation];
		ss << "," << fe_pilot[sat.pilot];
		ss << "," << fe_rolloff[sat.rolloff];
		ss << "," << fe_delsys[sys];
		ss << "," << sat.symbol_rate / 1000;
		ss << "," << fe_fec[sat.fec];
	}
	else if (sys == SYS_DVBT || sys == SYS_DVBT2)
	{
		ss << "ver=1.1;tuner=" << fe + 1;
		ss << "," << strength;
		ss << "," << status;
		ss << "," << snr;
		ss << "," << std::setprecision(2) << std::fixed << (double)ter.frequency / 1000000.0;
		ss << "," << ter.bandwidth / 1000000;
		ss << "," << fe_delsys[sys];
		ss << "," << fe_tmode[ter.transmission_mode];
		ss << "," << fe_modulation_ter[ter.modulation];
		ss << "," << fe_gi[ter.guard_interval];
		ss << ","
		   << "";
		ss << "," << ter.plp_id;
		ss << "," << 0;
		ss << "," << 0;
	}
	else
	{
		ss << "ver=1.2;tuner=" << fe + 1;
		ss << "," << strength;
		ss << "," << status;
		ss << "," << snr;
		ss << "," << std::setprecision(2) << std::fixed << (double)cab.frequency / 1000.0;
		ss << "," << 8;
		ss << "," << fe_delsys[sys];
		ss << "," << fe_modulation_cab[cab.modulation];
		ss << "," << cab.symbol_rate;
		ss << "," << 0;
		ss << "," << 0;
		ss << "," << 0;
		ss << "," << cab.inversion;
	}

	ss << ";pids=";

	if (!pids.empty())
	{
		std::set<int>::iterator it = pids.begin();
		ss << *it;
		for (it++; it != pids.end(); it++)
			ss << "," << *it;
	}

	std::string s = ss.str();
	eDebug("describe_frontend => %s", s.c_str());
	return s;
}

void eRTSPStreamClient::notifier(int what)
{
	if (!(what & eSocketNotifier::Read))
		return;

	ePtr<eRTSPStreamClient> ref = this;
	std::string transport_reply;
	std::string public_str = "Public: OPTIONS, DESCRIBE, SETUP, PLAY, TEARDOWN";

	{
		char tmpbuf[4096];
		int len;

		if ((len = singleRead(streamFd, tmpbuf, sizeof(tmpbuf))) <= 0)
		{
			eDebug("error on reading from socket %d", streamFd);
			rsn->stop();
			stop();
			parent->connectionLost(this);
			return;
		}
		tmpbuf[len] = 0;
		eDebug("rtsp read %d\n%s", len, tmpbuf);

		request.append(tmpbuf, len);
	}

	const char *buf = request.c_str();

	if ((request.find("\n\n") == std::string::npos) && (request.find("\r\n\r\n") == std::string::npos))
	{
		eDebug("New Line not found, continuing to read");
		return;
	}

	int cseq = 0;
	const char *sep = ::strcasestr(buf, "cseq:");
	if (sep)
		cseq = strtol(sep + 5, NULL, 10);

	int pos1 = request.find(' ', 0) + 1;
	int pos = request.find(' ', pos1 + 1);
	std::string url = urlDecode(request.substr(pos1, pos - pos1));
	eDebug("URL = %s", url.c_str());
	eDebug("method = /%s/", request.substr(0, pos1).c_str());
	if ((request.substr(0, 5) != "GET /") && ((request.find("?") != std::string::npos)) && ((request.find("freq=") != std::string::npos) || (request.find("pids=") != std::string::npos)))
	{
		if (satip2enigma(url))
		{
			http_response(streamFd, 404, "Error: Tuning multiple transponders not supported", "", cseq, 0);
			goto done;
		}
	}

	if ((request.substr(0, 8) == "OPTIONS "))
	{
		http_response(streamFd, 200, public_str, "", cseq, 0);
		update_service_list();
		goto done;
	}

	if ((request.substr(0, 9) == "DESCRIBE "))
	{
		std::stringstream ss;

		ss << "m=video 0 RTP/AVP 33\r\nc=IN IP4 0.0.0.0\r\na=control:stream=" << stream_id + 1 << "\r\n";
		ss << "a=fmtp:33 " << describe_frontend() << "\r\nb=AS:5000\r\n"
		   << "a=" << (running ? "sendonly" : "inactive") << "\r\n";

		// TODO: NEEDS CHANGED
		if (!stream_id)
		{
			http_response(streamFd, 404, public_str, "", cseq, 0);
			goto done;
		}

		size_t pos = request.find('?', 10);
		if (pos == std::string::npos)
			pos = request.find(' ', 10);

		std::string ah = "Content-type: application/sdp\r\nContent-Base: " + request.substr(9, pos - 9);

		http_response(streamFd, 200, ah, ss.str(), cseq, 0);
		goto done;
	}

	if ((request.substr(0, 6) == "SETUP ") || (request.substr(0, 5) == "PLAY "))
	{
		bool transport = !!::strcasestr(buf, "transport:");
		bool tcp = !!::strcasestr(buf, "RTP/AVP/TCP");
		bool port = !!::strcasestr(buf, "client_port=");

		if (transport && tcp)
		{
			proto = PROTO_RTSP_TCP;
			std::stringstream tr;
			tr << "Transport: RTP/AVP/TCP;interleaved=0-1\r\n";
			tr << "Session: " << std::setfill('0') << std::setw(10) << session_id;
			tr << ";timeout=" << 30 << "\r\n"
			   << "com.ses.streamID: " << stream_id;
			transport_reply = tr.str();
		}
		if (transport && port)
		{
			eDebug("UDP transport not supported to %s, use RTSP over TCP", m_remotehost.c_str());
			http_response(streamFd, 405, "UDP: Not supported, use rtsp over tcp", "", cseq, 0);
			goto done;
			/*
			   //FIXME parse port
			   int client_port = map_intd(port, NULL, -1);
			   char *rhost = (char *)m_remotehost.c_str();
			   proto = PROTO_RTSP_UDP;
			   eDebug("attempting to connect to %s:%d",rhost, client_port);
			   remote_socket = udp_connect(rhost, client_port);
			   if(remote_socket < 0 )
			   {
			   eDebug("Could not create udp socket to %s:%d", rhost, client_port);
			   http_response(streamFd, 404, public_str, "", cseq, 0);
			   goto done;

			   }
			   snprintf(transport_reply, sizeof(transport_reply),
			         "Transport: RTP/AVP;unicast;destination=%s;source=%s;client_port=%d-%d;server_port=%d-%d\r\nSession: %010d;timeout=%d\r\ncom.ses.streamID: %d",
			         rhost, get_sock_shost(remote_socket),
			         client_port,
			         client_port + 1,
			   //							opts.start_rtp, opts.start_rtp + 1,
			         get_sock_sport(remote_socket),
			         get_sock_sport(remote_socket) + 1, session_id,
			         30, stream_id);
			 */
		}
		if ((request.substr(0, 6) == "SETUP "))
		{
			if (transport)
				http_response(streamFd, 200, transport_reply, "", cseq, 0);
			else
				http_response(streamFd, 454, public_str, "", cseq, 0);
			goto done;
		}
	}

	if (request.substr(0, 5) == "PLAY ")
	{
		if (!tune_completed && (m_serviceref.size() > 1) && (proto > 0))
		{
			eDebug("starting the stream server with string %s", m_serviceref.c_str());
			if (eDVBServiceStream::start(m_serviceref.c_str(), streamFd) >= 0)
			{
				tune_completed = true;
				m_useencoder = false;
			}
		}
		else if (!tune_completed)
		{
			eDebug("No service ref detected: <%s>, proto %d", m_serviceref.c_str(), proto);
			http_response(streamFd, 404, "Transponder: Not Found in Enigma DB, do network scan", "", cseq, 0);
			goto done;
		}
		else if (proto == 0)
		{
			eDebug("No (TCP) transport detected  detected: <%s>", m_serviceref.c_str());
			http_response(streamFd, 405, "rtsp_over_tcp: not specified", "", cseq, 0);
			goto done;
		}
		http_response(streamFd, 200, transport_reply.empty() ? public_str : transport_reply, "", cseq, 0);

		goto done;
	}

	if (request.substr(0, 5) == "GET /")
	{
		std::stringstream ss;
		std::string s;
		int tuner_s2, tuner_t, tuner_c, tuner_t2, tuner_c2;

		eModelInformation &modelinformation = eModelInformation::getInstance();

		// TODO Add atsc tuner
		getFontends(tuner_t, tuner_t2, tuner_s2, tuner_c, tuner_c2);

		ss << "<?xml version=\"1.0\"?>";
		ss << "<root xmlns=\"urn:schemas-upnp-org:device-1-0\" configId=\"0\">";
		ss << "<specVersion><major>1</major><minor>1</minor></specVersion>";
		ss << "<device><deviceType>urn:ses-com:device:SatIPServer:1</deviceType>";
		ss << "<friendlyName>" << app_name << "</friendlyName>";
		ss << "<manufacturer>" << modelinformation.MachineBrand() << "</manufacturer>";
		ss << "<manufacturerURL>" << modelinformation.Url() << "</manufacturerURL>";
		ss << "<modelDescription>" << modelinformation.Creator() << "</modelDescription>";
		ss << "<modelName>" << modelinformation.MachineName() << "</modelName>";
		ss << "<modelNumber>1.1</modelNumber>";
		ss << "<modelURL>" << modelinformation.Url() << "</modelURL>";
		ss << "<serialNumber>1</serialNumber>";
		ss << "<UDN>uuid:11223344-9999-0001-b7ae-" << modelinformation.Date() << "</UDN>";
		ss << "<iconList>";
		//ss << "<icon><mimetype>image/png</mimetype><width>48</width><height>48</height><depth>24</depth><url>/sm.png</url></icon>";
		//ss << "<icon><mimetype>image/png</mimetype><width>120</width><height>120</height><depth>24</depth><url>/lr.png</url></icon>";
		//ss <<"<icon><mimetype>image/jpeg</mimetype><width>48</width><height>48</height><depth>24</depth><url>/sm.jpg</url></icon>";
		//ss <<"<icon><mimetype>image/jpeg</mimetype><width>120</width><height>120</height><depth>24</depth><url>/lr.jpg</url></icon>";
		ss << "</iconList>";
		ss << "<presentationURL>http://" << m_remotehost << ":" << parent->Port() << "/</presentationURL>\r\n";
		ss << "<satip:X_SATIPCAP xmlns:satip=\"urn:ses-com:satip\">";

		if (tuner_s2)
		{
			ss << "DVBS2-" << tuner_s2;
			s = ",";
		}
		if (tuner_t)
		{
			ss << s << "DVBT-" << tuner_t;
			s = ",";
		}
		if (tuner_c)
		{
			ss << s << "DVBC-" << tuner_c;
			s = ",";
		}
		if (tuner_t2)
		{
			ss << s << "DVBT2-" << tuner_t2;
			s = ",";
		}
		if (tuner_c2)
		{
			ss << s << "DVBC2-" << tuner_c2;
			s = ",";
		}
		if (!s.length())
		{
			ss << "DVBS2-0";
		}

		ss << "</satip:X_SATIPCAP>";
		ss << "</device></root>";

		s = ss.str();

		ss.str(std::string());
		ss.clear();

		ss << "HTTP/1.0 200 OK\r\nCACHE-CONTROL: no-cache\r\nContent-type: text/xml\r\n";
		ss << "X-SATIP-RTSP-Port: " << parent->Port() << "\r\n";
		ss << "Content-Length: " << s.length() << "\r\n\r\n";
		ss << s;

		s = ss.str();

		writeAll(streamFd, s.c_str(), s.length());
		rsn->stop();
		parent->connectionLost(this);
		return;
	}
	if (!running)
	{
		const char *reply = "HTTP/1.0 400 Bad Request\r\n\r\n";
		writeAll(streamFd, reply, strlen(reply));
		rsn->stop();
		parent->connectionLost(this);
		return;
	}
done:
	request.clear();
}

void eRTSPStreamClient::stopStream()
{
	ePtr<eRTSPStreamClient> ref = this;
	rsn->stop();
	parent->connectionLost(this);
}

std::string eRTSPStreamClient::getRemoteHost()
{
	return m_remotehost;
}

std::string eRTSPStreamClient::getServiceref()
{
	return m_serviceref;
}

bool eRTSPStreamClient::isUsingEncoder()
{
	return m_useencoder;
}

DEFINE_REF(eRTSPStreamServer);

eRTSPStreamServer *eRTSPStreamServer::m_instance = NULL;

eRTSPStreamServer::eRTSPStreamServer()
	: eServerSocket(8554, eApp)
{
	m_instance = this;
	//	e2avahi_announce(NULL, "_e2stream._tcp", 8001);
}

eRTSPStreamServer::~eRTSPStreamServer()
{
	for (eSmartPtrList<eRTSPStreamClient>::iterator it = clients.begin(); it != clients.end();)
	{
		it = clients.erase(it);
	}
}

eRTSPStreamServer *eRTSPStreamServer::getInstance()
{
	return m_instance;
}

void eRTSPStreamServer::newConnection(int socket)
{
	ePtr<eRTSPStreamClient> client = new eRTSPStreamClient(this, socket, RemoteHost());
	clients.push_back(client);
	client->start();
}

void eRTSPStreamServer::connectionLost(eRTSPStreamClient *client)
{
	eSmartPtrList<eRTSPStreamClient>::iterator it = std::find(clients.begin(), clients.end(), client);
	if (it != clients.end())
	{
		clients.erase(it);
	}
}

void eRTSPStreamServer::stopStream()
{
	eSmartPtrList<eRTSPStreamClient>::iterator it = clients.begin();
	if (it != clients.end())
	{
		it->stopStream();
	}
}

PyObject *eRTSPStreamServer::getConnectedClients()
{
	ePyObject ret;
	int idx = 0;
	int cnt = clients.size();
	ret = PyList_New(cnt);
	for (eSmartPtrList<eRTSPStreamClient>::iterator it = clients.begin(); it != clients.end(); ++it)
	{
		ePyObject tuple = PyTuple_New(3);
		PyTuple_SET_ITEM(tuple, 0, PyString_FromString((char *)it->getRemoteHost().c_str()));
		PyTuple_SET_ITEM(tuple, 1, PyString_FromString((char *)it->getServiceref().c_str()));
		PyTuple_SET_ITEM(tuple, 2, PyInt_FromLong(it->isUsingEncoder()));
		PyList_SET_ITEM(ret, idx++, tuple);
	}
	return ret;
}

eAutoInitPtr<eRTSPStreamServer> init_eRTSPStreamServer(eAutoInitNumbers::service + 1, "RTSP Stream server");
