#include <lib/dvb/fbc.h>
#include <lib/dvb/dvb.h>
#include <lib/dvb/sec.h>
#include <lib/base/object.h>
#include <lib/base/esimpleconfig.h>

#include <unistd.h>
#include <fcntl.h>

#include <ios>
#include <fstream>
#include <sstream>
#include <iomanip>

int eFBCTunerManager::ReadProcInt(int fe_index, const std::string & entry)
{
	std::ifstream file;
	std::stringstream path;
	path << "/proc/stb/frontend/" << fe_index << "/" << entry;
	file.open(path.str().c_str());
	if(!file.is_open())
		return(-1);

#ifdef HAVE_DM_FBC
	std::string value;
	file >> value;
#else
	int value;
	file >> value;
#endif

	if(file.bad() || file.fail())
		return(-1);

#ifdef HAVE_DM_FBC
	return(value == "A" ? 0 : 1);
#else
	return(value);
#endif

}

void eFBCTunerManager::WriteProcInt(int fe_index, const std::string & entry, int value)
{
	std::stringstream path;
	std::ofstream file;

	path << "/proc/stb/frontend/" << fe_index << "/" << entry;
	file.open(path.str().c_str());

	if(!file.is_open())
		return;

	file << value;
}

void eFBCTunerManager::WriteProcStr(int fe_index, const std::string & entry, int value)
{
	std::stringstream path;
	std::ofstream file;

	path << "/proc/stb/frontend/" << fe_index << "/" << entry;
	file.open(path.str().c_str());

	if(!file.is_open())
		return;

	char configStr[255];
	snprintf(configStr, 255, "config.Nims.%d.dvbs.input", fe_index);
	std::string str = eSimpleConfig::getString(configStr, "A");
	file << str.c_str();
}

#ifdef HAVE_DM_FBC
void eFBCTunerManager::LoadConnectChoices(int fe_index, std::string &choices)
{
	std::stringstream path;
	std::ifstream file;
	std::string line;
	std::string::const_iterator it;
	int fbc_id;

	path << "/proc/stb/frontend/"  << fe_index << "/input_choices";
	file.open(path.str().c_str());

	if(!file.is_open())
		return;

	file >> choices;

	if(file.bad() || file.fail())
		return;
}
#else
void eFBCTunerManager::LoadConnectChoices(int fe_index, connect_choices_t &choices)
{
	std::stringstream path;
	std::ifstream file;
	std::string line;
	std::string::const_iterator it;
	int fbc_id;

	path << "/proc/stb/frontend/"  << fe_index << "/fbc_connect_choices";
	file.open(path.str().c_str());

	if(!file.is_open())
		return;

	getline(file, line);

	if(file.bad() || file.fail())
		return;

	choices.reset();

	for(it = line.begin(); it != line.end(); it++)
	{
		if(isdigit(*it))
		{
			fbc_id = (char)*it - '0';

			if((fbc_id >= 0) && (fbc_id < (int)choices.size()))
				choices.set(fbc_id);
		}
	}
}
#endif

DEFINE_REF(eFBCTunerManager);

eFBCTunerManager* eFBCTunerManager::m_instance = (eFBCTunerManager*)0;

eFBCTunerManager* eFBCTunerManager::getInstance()
{
	return m_instance;
}

eFBCTunerManager::eFBCTunerManager(ePtr<eDVBResourceManager> res_mgr)
	:m_res_mgr(res_mgr)
{
	eSmartPtrList<eDVBRegisteredFrontend> &frontends = m_res_mgr->m_frontend;
	eSmartPtrList<eDVBRegisteredFrontend> &frontends_simulate = m_res_mgr->m_simulate_frontend;
	tuner_t	tuner;
	int	fe_id, fbc_prev_set_id;
	/* each FBC set has 8 tuners. */
	/* first set : 0, 1, 2, 3, 4, 5, 6, 7 */
	/* second set : 8, 9, 10, 11, 12, 13, 14, 15 */
	/* first, second frontend is top on a set */

	if (!m_instance)
		m_instance = this;

	tuner.id = 0;

	fe_id = -1;
	fbc_prev_set_id = -1;

	for (eSmartPtrList<eDVBRegisteredFrontend>::iterator it(frontends.begin()); it != frontends.end(); ++it)
	{
		// continue for DVB-C FBC Tuner

		it->m_frontend->setFBCTuner(false); // TODO TEST

		if (!(it->m_frontend->supportsDeliverySystem(SYS_DVBS, false) || it->m_frontend->supportsDeliverySystem(SYS_DVBS2, false)))
			continue; // ignore DVB-C/T FBC tuners because they need no special treatment

		fe_id = FESlotID(it);
#ifdef HAVE_DM_FBC
		tuner.set_id = ReadProcInt(fe_id, "input");
#else
		tuner.set_id = ReadProcInt(fe_id, "fbc_set_id");
#endif
		if(tuner.set_id >= 0)
		{
			if(fbc_prev_set_id != tuner.set_id)
			{
				fbc_prev_set_id = tuner.set_id;
#ifdef HAVE_DM_FBC
				LoadConnectChoices(fe_id, tuner.input_choices);
#else
				LoadConnectChoices(fe_id, tuner.connect_choices);
#endif
				tuner.id = 0;
			}
#ifdef HAVE_DM_FBC
			tuner.is_root = tuner.id < 2;
#else
			if(tuner.id < (int)tuner.connect_choices.size())
				tuner.is_root = tuner.connect_choices.test(tuner.id);
			else
				tuner.is_root = false;

#endif

			tuner.default_id = tuner.is_root ? tuner.id : 0;
			m_tuners[fe_id] = tuner;

			/* set default fbc ID */
			SetProcFBCID(fe_id, tuner.default_id, false);

			/* enable fbc tuner */
			it->m_frontend->setFBCTuner(true);

			tuner.id++;
		}
	}

	for (eSmartPtrList<eDVBRegisteredFrontend>::iterator it(frontends_simulate.begin()); it != frontends_simulate.end(); ++it)
	{
		// continue for DVB-C FBC Tuner

		it->m_frontend->setFBCTuner(false); // TODO TEST

		if (!(it->m_frontend->supportsDeliverySystem(SYS_DVBS, false) || it->m_frontend->supportsDeliverySystem(SYS_DVBS2, false)))
			continue;

#ifdef HAVE_DM_FBC
		if(ReadProcInt(FESlotID(it), "input") >= 0)
			it->m_frontend->setFBCTuner(true);
#else
		if(ReadProcInt(FESlotID(it), "fbc_set_id") >= 0)
			it->m_frontend->setFBCTuner(true);
#endif

	}
}

eFBCTunerManager::~eFBCTunerManager()
{
	if(m_instance == this)
		m_instance = (eFBCTunerManager*)0;
}

void eFBCTunerManager::SetProcFBCID(int fe_id, int fbc_connect, bool fbc_is_linked)
{
	eTrace("[*][eFBCTunerManager::SetProcFBCID] %d -> %d", fe_id, fbc_connect);
#ifdef HAVE_DM_FBC
	WriteProcStr(fe_id, "input", fbc_connect);
#else

	/* set root */
	WriteProcInt(fe_id, "fbc_connect", fbc_connect);

	/* set linked */
	WriteProcInt(fe_id, "fbc_link", fbc_is_linked ? 1 : 0);
#endif
}

int eFBCTunerManager::FESlotID(eDVBRegisteredFrontend *fe)
{
	return fe->m_frontend->getSlotID();
}

void eFBCTunerManager::SetDefaultFBCID(eDVBRegisteredFrontend *fe) const
{
	int fe_id = FESlotID(fe);
	SetProcFBCID(fe_id, GetDefaultFBCID(fe_id), IsLinked(fe));
}

void eFBCTunerManager::UpdateFBCID(eDVBRegisteredFrontend *next_fe, eDVBRegisteredFrontend *prev_fe) const
{
	SetProcFBCID(FESlotID(next_fe), GetFBCID(FESlotID(GetHead(prev_fe))), IsLinked(next_fe));
}

bool eFBCTunerManager::IsLinked(eDVBRegisteredFrontend *fe)
{
	return(!!(FrontendGetLinkPtr(fe, link_prev)));
}

bool eFBCTunerManager::isUnicable(eDVBRegisteredFrontend *fe)
{
	ePtr<eDVBSatelliteEquipmentControl> sec = eDVBSatelliteEquipmentControl::getInstance();
	int slot_idx = FESlotID(fe);
	bool is_unicable = false;

	for (int idx=0; idx <= sec->m_lnbidx; ++idx )
	{
		eDVBSatelliteLNBParameters &lnb_param = sec->m_lnbs[idx];
		if ( lnb_param.m_slot_mask & (1 << slot_idx) )
		{
			is_unicable = lnb_param.SatCR_idx != -1;
			break;
		}
	}
	return is_unicable;
}

bool eFBCTunerManager::IsFEUsed(eDVBRegisteredFrontend *fe, bool a_simulate) const
{
	if (fe->m_inuse > 0)
		return true;

	bool simulate = !a_simulate;

	eSmartPtrList<eDVBRegisteredFrontend> &frontends = simulate ? m_res_mgr->m_simulate_frontend : m_res_mgr->m_frontend;

	for (eSmartPtrList<eDVBRegisteredFrontend>::iterator it(frontends.begin()); it != frontends.end(); ++it)
		if (FESlotID(*it) == FESlotID(fe))
			return(it->m_inuse > 0);

	eDebug("[*][eFBCTunerManager::isFeUsed] ERROR! can not found fe ptr (feid : %d, simulate : %d)", FESlotID(fe), simulate);
	return false;
}

bool eFBCTunerManager::IsSameFBCSet(int fe_a, int fe_b) const
{
	tuners_t::const_iterator a, b;

	a = m_tuners.find(fe_a);
	b = m_tuners.find(fe_b);

	if((a == m_tuners.end()) || (b == m_tuners.end()))
		return(false);

	return(a->second.set_id == b->second.set_id);
}

bool eFBCTunerManager::IsRootFE(eDVBRegisteredFrontend *fe) const
{
	tuners_t::const_iterator a;

	if((a = m_tuners.find(FESlotID(fe))) == m_tuners.end())
		return(false);

	return a->second.is_root;
}

int eFBCTunerManager::GetFBCID(int fe_id) const
{
	tuners_t::const_iterator a;

	if((a = m_tuners.find(fe_id)) == m_tuners.end())
		return(-1);

	return a->second.id;
}

int eFBCTunerManager::GetDefaultFBCID(int fe_id) const
{
	tuners_t::const_iterator a;

	if((a = m_tuners.find(fe_id)) == m_tuners.end())
		return(-1);

	return a->second.default_id;
}

int eFBCTunerManager::GetFBCSetID(int fe_id) const
{
	tuners_t::const_iterator a;

	if((a = m_tuners.find(fe_id)) == m_tuners.end())
		return(-1);

	return(a->second.set_id);
}

eDVBRegisteredFrontend *eFBCTunerManager::GetFEPtr(long link)
{
	if(link == -1)
		link = 0;

	return((eDVBRegisteredFrontend *)link);
}

long eFBCTunerManager::GetFELink(eDVBRegisteredFrontend *ptr)
{
	long link = (long)ptr;

	if(link == 0)
		link = -1;

	return(link);
}

eDVBRegisteredFrontend *eFBCTunerManager::FrontendGetLinkPtr(eDVBFrontend *fe, link_ptr_t link_type)
{
	int data_type;
	long data;

	switch(link_type)
	{
		case(link_prev): data_type = eDVBFrontend::LINKED_PREV_PTR; break;
		case(link_next): data_type = eDVBFrontend::LINKED_NEXT_PTR; break;
		default: return(GetFEPtr(-1));
	}

	if(fe->getData(data_type, data)) // returns != 0 on error
		data = -1;

	return(GetFEPtr(data));
}


eDVBRegisteredFrontend *eFBCTunerManager::FrontendGetLinkPtr(eDVBRegisteredFrontend *fe, link_ptr_t link_type)
{
	return(FrontendGetLinkPtr(fe->m_frontend, link_type));
}

void eFBCTunerManager::FrontendSetLinkPtr(eDVBRegisteredFrontend *fe, link_ptr_t link_type, eDVBRegisteredFrontend *ptr)
{
	int data_type;

	switch(link_type)
	{
		case(link_prev): data_type = eDVBFrontend::LINKED_PREV_PTR; break;
		case(link_next): data_type = eDVBFrontend::LINKED_NEXT_PTR; break;
		default: return;
	}

	fe->m_frontend->setData(data_type, GetFELink(ptr));
}

eDVBRegisteredFrontend *eFBCTunerManager::GetHead(eDVBRegisteredFrontend *fe)
{
	eDVBRegisteredFrontend *prev_fe;

	while((prev_fe = FrontendGetLinkPtr(fe, link_prev)))
		fe = prev_fe;

	return(fe);
}

eDVBRegisteredFrontend *eFBCTunerManager::GetTail(eDVBRegisteredFrontend *fe)
{
	eDVBRegisteredFrontend *next_fe;

	while((next_fe = FrontendGetLinkPtr(fe, link_next)))
		fe = next_fe;

	return(fe);
}

eDVBRegisteredFrontend *eFBCTunerManager::GetSimulFE(eDVBRegisteredFrontend *fe) const
{
	eSmartPtrList<eDVBRegisteredFrontend> &frontends = m_res_mgr->m_simulate_frontend;

	for (eSmartPtrList<eDVBRegisteredFrontend>::iterator it(frontends.begin()); it != frontends.end(); it++)
		if (FESlotID(*it) == FESlotID(fe))
			return(*it);

	return((eDVBRegisteredFrontend *)0);
}

void eFBCTunerManager::ConnectLink(eDVBRegisteredFrontend *link_fe, eDVBRegisteredFrontend *prev_fe, eDVBRegisteredFrontend *next_fe, bool simulate) const
{
	if (next_fe)
		eTrace("	[*][eFBCTunerManager::connectLink] connect %d->%d->%d %s", FESlotID(prev_fe), FESlotID(link_fe), FESlotID(next_fe), simulate?"(simulate)":"");
	else
		eTrace("	[*][eFBCTunerManager::connectLink] connect %d->%d %s", FESlotID(prev_fe), FESlotID(link_fe), simulate?"(simulate)":"");

	FrontendSetLinkPtr(prev_fe, link_next, link_fe);
	FrontendSetLinkPtr(link_fe, link_prev, prev_fe);
	FrontendSetLinkPtr(link_fe, link_next, next_fe);

	if (next_fe)
		FrontendSetLinkPtr(next_fe, link_prev, link_fe);
}

void eFBCTunerManager::DisconnectLink(eDVBRegisteredFrontend *link_fe, eDVBRegisteredFrontend *prev_fe, eDVBRegisteredFrontend *next_fe, bool simulate) const
{
	if (next_fe)
		eTrace("	[*][eFBCTunerManager::DisconnectLink] disconnect %d->%d->%d %s", FESlotID(prev_fe), FESlotID(link_fe), FESlotID(next_fe), simulate?"(simulate)":"");
	else
		eTrace("	[*][eFBCTunerManager::DisconnectLink] disconnect %d->%d %s", FESlotID(prev_fe), FESlotID(link_fe), simulate?"(simulate)":"");

	FrontendSetLinkPtr(link_fe, link_prev, (eDVBRegisteredFrontend *)0);
	FrontendSetLinkPtr(link_fe, link_next, (eDVBRegisteredFrontend *)0);
	FrontendSetLinkPtr(prev_fe, link_next, next_fe);

	if (next_fe)
		FrontendSetLinkPtr(next_fe, link_prev, prev_fe);
}

int eFBCTunerManager::IsCompatibleWith(ePtr<iDVBFrontendParameters> &feparm, eDVBRegisteredFrontend *link_fe, eDVBRegisteredFrontend *&fbc_fe, bool simulate) const
{
	eSmartPtrList<eDVBRegisteredFrontend> &frontends = simulate ? m_res_mgr->m_simulate_frontend : m_res_mgr->m_frontend;
	eDVBRegisteredFrontend *fe_insert_point;
	int best_score, new_score;

	best_score = 0;

	for (eSmartPtrList<eDVBRegisteredFrontend>::iterator it(frontends.begin()); it != frontends.end(); ++it)
	{
		if (!it->m_frontend->is_FBCTuner())
			continue;

		if (!IsRootFE(*it))
			continue;

		if(!it->m_frontend->getEnabled())
			continue;

		if(!IsSameFBCSet(FESlotID(link_fe), FESlotID(it)))
			continue;

		if(it->m_inuse == 0) // No link to a fe not in use.
			continue;

		if(IsLinked(*it)) // No link to a fe linked to another.
			continue;

		if(isUnicable(*it))
			continue;

		// temporarily add this leaf to the current "linked" chain, at the tail

		fe_insert_point = GetTail(*it);


		/* connect link */
		ConnectLink(link_fe, /*prev_fe*/fe_insert_point, /*next_fe*/(eDVBRegisteredFrontend *)0, simulate);

		/* enable linked fe */
		link_fe->m_frontend->setEnabled(true);

		/* add slot mask*/
		UpdateLNBSlotMask(FESlotID(link_fe), FESlotID(*it), false);

		/* get score */
		new_score = link_fe->m_frontend->isCompatibleWith(feparm);
		if (new_score > best_score)
		{
			best_score = new_score;
			fbc_fe = *it;
		}

		eTrace("[*][eFBCTunerManager::isCompatibleWith] score : %d (%d->%d)", new_score, FESlotID(it), FESlotID(link_fe));


		/* disconnect link */
		DisconnectLink(link_fe, /*prev_fe*/fe_insert_point, /*next_fe*/(eDVBRegisteredFrontend *)0, simulate);

		/* disable linked fe */
		link_fe->m_frontend->setEnabled(false);

		/* remove slot mask*/
		UpdateLNBSlotMask(FESlotID(link_fe), FESlotID(*it), true);
	}

	eTrace("[*][eFBCTunerManager::isCompatibleWith] fe : %p(%d), score : %d %s", link_fe, FESlotID(link_fe), best_score, simulate?"(simulate)":"");

	return best_score;
}

/* attach link_fe to tail of fe linked list */
void eFBCTunerManager::AddLink(eDVBRegisteredFrontend *leaf, eDVBRegisteredFrontend *root, bool simulate) const
{
	eDVBRegisteredFrontend *leaf_insert_after, *leaf_insert_before, *leaf_current, *leaf_next;

	//PrintLinks(link_fe);

	eTrace("	[*][eFBCTunerManager::addLink] (leaf: %d, link to top fe: %d, simulate: %d", FESlotID(leaf), FESlotID(root), simulate);



	if(IsRootFE(leaf) || !IsRootFE(root))
		return;


	// find the entry where to insert the leaf, it must be between slotid(leaf)-1 and slotid(leaf)+1

	leaf_next			= (eDVBRegisteredFrontend *)0;
	leaf_insert_after	= (eDVBRegisteredFrontend *)0;
	leaf_insert_before	= (eDVBRegisteredFrontend *)0;

	for(leaf_current = root; leaf_current; leaf_current = leaf_next)
	{
		leaf_next = FrontendGetLinkPtr(leaf_current, link_next);

		leaf_insert_after = leaf_current;
		leaf_insert_before = leaf_next;

		if(leaf_next && (FESlotID(leaf_next) > FESlotID(leaf)))
			break;
	}


	/* connect */
	ConnectLink(leaf, leaf_insert_after, leaf_insert_before, simulate);

	/* enable linked fe */
	leaf->m_frontend->setEnabled(true);

	/* simulate connect */
	if (!simulate)
	{
		eDVBRegisteredFrontend *simul_root, *simul_leaf;

		simul_root = GetSimulFE(root);
		simul_leaf = GetSimulFE(leaf);

		if(IsRootFE(simul_root))
		{
			leaf_insert_after = (eDVBRegisteredFrontend *)0;
			leaf_insert_before = (eDVBRegisteredFrontend *)0;

			for(leaf_current = simul_root; leaf_current; leaf_current = leaf_next)
			{
				leaf_next = FrontendGetLinkPtr(leaf_current, link_next);

				leaf_insert_after = leaf_current;
				leaf_insert_before = leaf_next;

				if(leaf_next && (FESlotID(leaf_next) > FESlotID(leaf)))
					break;
			}

			eTrace("	[*][eFBCTunerManager::addLink] simulate fe : %p -> %p -> %p", leaf_insert_after, simul_leaf, leaf_insert_before);


			ConnectLink(simul_leaf, leaf_insert_after, leaf_insert_before, true);

			/* enable simulate linked fe */
			simul_leaf->m_frontend->setEnabled(true);
		}
	}

	/* set proc fbc_id */
	if (!simulate)
		SetProcFBCID(FESlotID(leaf), GetFBCID(FESlotID(root)), IsLinked(leaf));

	/* add slot mask*/
	UpdateLNBSlotMask(FESlotID(leaf), FESlotID(root), false);

	//PrintLinks(link_fe);
}

/* if fe, fe_simulated is unused, unlink current frontend from linked things. */
/* all unused linked fbc fe must be unlinked! */
void eFBCTunerManager::Unlink(eDVBRegisteredFrontend *fe) const
{
	eDVBRegisteredFrontend *simul_fe;
	bool simulate = fe->m_frontend->is_simulate();
	eTrace("	[*][eFBCTunerManager::unLink] fe id : %p(%d) %s", fe, FESlotID(fe), simulate?"(simulate)":"");

	if (IsRootFE(fe) || IsFEUsed(fe, simulate) || isUnicable(fe) || !IsLinked(fe))
	{
		eTrace("	[*][eFBCTunerManager::unLink] skip..");
		return;
	}

	//PrintLinks(link_fe);

	DisconnectLink(fe, FrontendGetLinkPtr(fe, link_prev), FrontendGetLinkPtr(fe, link_next), simulate);

	/* disable linked fe */
	fe->m_frontend->setEnabled(false);

	/* simulate disconnect */
	if (!simulate)
	{
		if((simul_fe = GetSimulFE(fe)) && !IsRootFE(simul_fe) && !IsFEUsed(simul_fe, true) &&
				!isUnicable(simul_fe) && IsLinked(simul_fe))
		{
			DisconnectLink(simul_fe, FrontendGetLinkPtr(simul_fe, link_prev), FrontendGetLinkPtr(simul_fe, link_next), true);
			/* enable simulate linked fe */
			simul_fe->m_frontend->setEnabled(false);

		}

	}

	/* set default proc fbc_id */
	//SetDefaultFBCID(link_fe);

	/* remove slot mask*/
	UpdateLNBSlotMask(FESlotID(fe), FESlotID(GetHead(fe)), true);

	//PrintLinks(link_fe);
}

void eFBCTunerManager::UpdateLNBSlotMask(int dest_slot, int src_slot, bool remove)
{
	ePtr<eDVBSatelliteEquipmentControl> sec = eDVBSatelliteEquipmentControl::getInstance();
	int idx, sec_lnbidx;

	sec_lnbidx = sec->m_lnbidx;

	int found = 0;
	for (idx=0; idx <= sec_lnbidx; ++idx )
	{
		eDVBSatelliteLNBParameters &lnb_param = sec->m_lnbs[idx];
		if ( lnb_param.m_slot_mask & (1 << src_slot) )
		{
			eTrace("[*][eFBCTunerManager::UpdateLNBSlotMask] m_slot_mask : %d", lnb_param.m_slot_mask);

			if (remove)
				lnb_param.m_slot_mask &= ~(1 << dest_slot);
			else
				lnb_param.m_slot_mask |= (1 << dest_slot);

			eTrace("[*][eFBCTunerManager::UpdateLNBSlotMask] changed m_slot_mask : %d", lnb_param.m_slot_mask);
			found = 1;
		}
	}

	if (!found)
		eTrace("[*][eFBCTunerManager::UpdateLNBSlotMask] src %d not found", src_slot);

}

bool eFBCTunerManager::CanLink(eDVBRegisteredFrontend *fe) const
{
	if(IsRootFE(fe))
		return false;

	if(FrontendGetLinkPtr(fe, link_prev) || FrontendGetLinkPtr(fe, link_next))
		return false;

	if(isUnicable(fe))
		return false;

	return true;
}

int eFBCTunerManager::getLinkedSlotID(int fe_id) const
{
	int link = -1;
	eDVBRegisteredFrontend *prev_fe;
	eSmartPtrList<eDVBRegisteredFrontend> &frontends = m_res_mgr->m_frontend;
	for (eSmartPtrList<eDVBRegisteredFrontend>::iterator it(frontends.begin()); it != frontends.end(); ++it) {
		if((it->m_frontend->getSlotID() == fe_id) && ((prev_fe = FrontendGetLinkPtr(it, link_prev)))) {
		
			link = FESlotID(prev_fe);
			break;
		}
	}

	eTrace(" [*][eFBCTunerManager::getLinkedSlotID] fe_id : %d, link : %d", fe_id, link);

	return link;
}

bool eFBCTunerManager::IsFBCLink(int fe_id) const
{
	std::map<int, tuner_t>::const_iterator it;

	if((it = m_tuners.find(fe_id)) == m_tuners.end())
		return(false);

	return(!it->second.is_root);
}

void eFBCTunerManager::PrintLinks(eDVBRegisteredFrontend *fe) const
{

	eSmartPtrList<eDVBRegisteredFrontend> &frontends = m_res_mgr->m_frontend;
	eSmartPtrList<eDVBRegisteredFrontend> &simulate_frontends = m_res_mgr->m_simulate_frontend;

	eDVBRegisteredFrontend *current_fe, *prev_ptr, *next_ptr;
	int prev, next;

	current_fe = GetHead(fe);


	eTrace(" [*][eFBCTunerManager::printLinks] fe id : %d (%p), inuse : %d, enabled : %d, fbc : %d", FESlotID(current_fe), current_fe, current_fe->m_inuse, current_fe->m_frontend->getEnabled(), current_fe->m_frontend->is_FBCTuner());

	while ((current_fe = FrontendGetLinkPtr(current_fe, link_next)))
		eTrace(" [*][eFBCTunerManager::printLinks] fe id : %d (%p), inuse : %d, enabled : %d, fbc : %d", FESlotID(current_fe), current_fe, current_fe->m_inuse, current_fe->m_frontend->getEnabled(), current_fe->m_frontend->is_FBCTuner());


	for (eSmartPtrList<eDVBRegisteredFrontend>::iterator it(frontends.begin()); it != frontends.end(); ++it)
	{
		if ((prev_ptr = FrontendGetLinkPtr(&*it->m_frontend, link_prev)))
			prev = FESlotID(prev_ptr);
		else
			prev = -1;

		if ((next_ptr = FrontendGetLinkPtr(&*it->m_frontend, link_next)))
			next = FESlotID(next_ptr);
		else
			next = -1;

		eTrace(" [*][eFBCTunerManager::printLinks] fe_id : %2d, inuse : %d, enabled : %d, fbc : %d, prev : %2d, cur : %2d, next : %2d", FESlotID(it), it->m_inuse, it->m_frontend->getEnabled(), it->m_frontend->is_FBCTuner(), prev, FESlotID(it), next);
	}

	for (eSmartPtrList<eDVBRegisteredFrontend>::iterator it(simulate_frontends.begin()); it != simulate_frontends.end(); ++it)
	{
		if ((prev_ptr = FrontendGetLinkPtr(&*it->m_frontend, link_prev)))
			prev = FESlotID(prev_ptr);
		else
			prev = -1;

		if ((next_ptr = FrontendGetLinkPtr(&*it->m_frontend, link_next)))
			next = FESlotID(next_ptr);
		else
			next = -1;

		eTrace(" [*][eFBCTunerManager::printLinks] fe_id : %2d, inuse : %d, enabled : %d, fbc : %d, prev : %2d, cur : %2d, next : %2d (simulate)", FESlotID(it), it->m_inuse, it->m_frontend->getEnabled(), it->m_frontend->is_FBCTuner(), prev, FESlotID(it), next);
	}
}

