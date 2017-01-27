#include <lib/dvb/fbc.h>
#include <lib/dvb/dvb.h>
#include <lib/dvb/sec.h>
#include <lib/base/object.h>

#include <unistd.h>
#include <fcntl.h>

#include <ios>
#include <fstream>
#include <sstream>
#include <iomanip>

int eFBCTunerManager::ReadProcInt(int fe_index, const std::string & entry)
{
	int value;
	std::stringstream path;
	std::ifstream file;

	path << "/proc/stb/frontend/" << fe_index << "/" << entry;
	file.open(path.str().c_str());

	if(!file.is_open())
		return(-1);

	file >> value;

	if(file.bad() || file.fail())
		return(-1);

	return(value);
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
	int		fe_id, fbc_prev_set_id;

	if(!m_instance)
		m_instance = this;

	tuner.id = 0;
	fbc_prev_set_id = -1;

	for (eSmartPtrList<eDVBRegisteredFrontend>::iterator it(frontends.begin()); it != frontends.end(); ++it)
	{
		it->m_frontend->set_FBCTuner(false);

		if (!(it->m_frontend->supportsDeliverySystem(SYS_DVBS, false) || it->m_frontend->supportsDeliverySystem(SYS_DVBS2, false)))
			continue; // ignore DVB-C/T FBC tuners because they need no special treatment

		fe_id = FESlotID(it);
		tuner.set_id = ReadProcInt(fe_id, "fbc_set_id");

		if(tuner.set_id >= 0)
		{
			if(fbc_prev_set_id != tuner.set_id)
			{
				fbc_prev_set_id = tuner.set_id;
				LoadConnectChoices(fe_id, tuner.connect_choices);
				tuner.id = 0;
			}

			if(tuner.id < (int)tuner.connect_choices.size())
				tuner.is_root = tuner.connect_choices.test(tuner.id);
			else
				tuner.is_root = false;

			tuner.default_id = tuner.is_root ? tuner.id : 0;
			m_tuners[fe_id] = tuner;
			SetProcFBCID(fe_id, tuner.default_id, false);
			it->m_frontend->set_FBCTuner(true);

			tuner.id++;
		}
	}

	for (eSmartPtrList<eDVBRegisteredFrontend>::iterator it(frontends_simulate.begin()); it != frontends_simulate.end(); ++it)
	{
		it->m_frontend->set_FBCTuner(false);

		if (!(it->m_frontend->supportsDeliverySystem(SYS_DVBS, false) || it->m_frontend->supportsDeliverySystem(SYS_DVBS2, false)))
			continue;

		if(ReadProcInt(FESlotID(it), "fbc_set_id") >= 0)
			it->m_frontend->set_FBCTuner(true);
	}
}

eFBCTunerManager::~eFBCTunerManager()
{
	if(m_instance == this)
		m_instance = (eFBCTunerManager*)0;
}

void eFBCTunerManager::SetProcFBCID(int fe_id, int fbc_connect, bool fbc_is_linked)
{
	WriteProcInt(fe_id, "fbc_connect", fbc_connect);
	WriteProcInt(fe_id, "fbc_link", fbc_is_linked ? 1 : 0);
}

int eFBCTunerManager::FESlotID(eDVBRegisteredFrontend *fe)
{
	return(fe->m_frontend->getSlotID());
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

bool eFBCTunerManager::IsSCR(eDVBRegisteredFrontend *fe)
{
	ePtr<eDVBSatelliteEquipmentControl> sec = eDVBSatelliteEquipmentControl::getInstance();
	int slot_idx = FESlotID(fe);
	int idx;

	for (idx = 0; idx <= sec->m_lnbidx; ++idx)
	{
		eDVBSatelliteLNBParameters &lnb_param = sec->m_lnbs[idx];

		if (lnb_param.m_slot_mask & (1 << slot_idx))
			return(lnb_param.SatCR_format != SatCR_format_none);
	}

	return(false);
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
	//if (next_fe)
		//fprintf(stderr, "**** [*][eFBCTunerManager::connectLink] connect %d->%d->%d %s\n", FESlotID(prev_fe), FESlotID(link_fe), FESlotID(next_fe), simulate?"(simulate)":"");
	//else
		//fprintf(stderr, "**** [*][eFBCTunerManager::connectLink] connect %d->%d %s\n", FESlotID(prev_fe), FESlotID(link_fe), simulate?"(simulate)":"");

	FrontendSetLinkPtr(prev_fe, link_next, link_fe);
	FrontendSetLinkPtr(link_fe, link_prev, prev_fe);
	FrontendSetLinkPtr(link_fe, link_next, next_fe);

	if (next_fe)
		FrontendSetLinkPtr(next_fe, link_prev, link_fe);
}

void eFBCTunerManager::DisconnectLink(eDVBRegisteredFrontend *link_fe, eDVBRegisteredFrontend *prev_fe, eDVBRegisteredFrontend *next_fe, bool simulate) const
{
	//if (next_fe)
		//fprintf(stderr, "**** [*][eFBCTunerManager::disconnectLink] disconnect %d->%d->%d %s\n", FESlotID(prev_fe), FESlotID(link_fe), FESlotID(next_fe), simulate?"(simulate)":"");
	//else
		//fprintf(stderr, "**** [*][eFBCTunerManager::disconnectLink] disconnect %d->%d %s\n", FESlotID(prev_fe), FESlotID(link_fe), simulate?"(simulate)":"");

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

		if(it->m_inuse == 0)
			continue;

		if(IsLinked(*it))
			continue;

		if(IsSCR(*it))
			continue;

		// temporarily add this leaf to the current "linked" chain, at the tail

		fe_insert_point = GetTail(*it);
		ConnectLink(link_fe, /*prev_fe*/fe_insert_point, /*next_fe*/(eDVBRegisteredFrontend *)0, simulate);
		link_fe->m_frontend->setEnabled(true);
		UpdateLNBSlotMask(FESlotID(link_fe), FESlotID(*it), false);

		// get score when leaf is added

		new_score = link_fe->m_frontend->isCompatibleWith(feparm);

		if (new_score > best_score)
		{
			best_score = new_score;
			fbc_fe = *it;
		}

		// now remove the leaf tuner again

		DisconnectLink(link_fe, /*prev_fe*/fe_insert_point, /*next_fe*/(eDVBRegisteredFrontend *)0, simulate);
		link_fe->m_frontend->setEnabled(false);
		UpdateLNBSlotMask(FESlotID(link_fe), FESlotID(*it), true);
	}

	return best_score;
}

void eFBCTunerManager::AddLink(eDVBRegisteredFrontend *leaf, eDVBRegisteredFrontend *root, bool simulate) const
{
	eDVBRegisteredFrontend *leaf_insert_after, *leaf_insert_before, *leaf_current, *leaf_next;

	//fprintf(stderr, "\n**** addLink(leaf: %d, link to top fe: %d, simulate: %d\n", FESlotID(leaf), FESlotID(root), simulate);

	//PrintLinks(root);

	if (IsRootFE(leaf) || !IsRootFE(root))
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

	ConnectLink(leaf, leaf_insert_after, leaf_insert_before, simulate);
	leaf->m_frontend->setEnabled(true);

	if(!simulate) // act on simulate frontends
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

			ConnectLink(simul_leaf, leaf_insert_after, leaf_insert_before, true);
			simul_leaf->m_frontend->setEnabled(true);
		}
	}

	if(!simulate)
		SetProcFBCID(FESlotID(leaf), GetFBCID(FESlotID(root)), IsLinked(leaf));

	UpdateLNBSlotMask(FESlotID(leaf), FESlotID(root), /*remove*/false);

	//PrintLinks(root);
}

void eFBCTunerManager::Unlink(eDVBRegisteredFrontend *fe) const
{
	eDVBRegisteredFrontend *simul_fe;
	bool simulate;

	simulate = fe->m_frontend->is_simulate();

	if (IsRootFE(fe) || IsFEUsed(fe, simulate) || IsSCR(fe) || !IsLinked(fe))
		return;

	//PrintLinks(fe);

	DisconnectLink(fe, FrontendGetLinkPtr(fe, link_prev), FrontendGetLinkPtr(fe, link_next), simulate);
	fe->m_frontend->setEnabled(false);

	if(!simulate) // also act on the simulation frontends
	{
		if((simul_fe = GetSimulFE(fe)) && !IsRootFE(simul_fe) && !IsFEUsed(simul_fe, true) &&
				!IsSCR(simul_fe) && IsLinked(simul_fe))
		{
			DisconnectLink(simul_fe, FrontendGetLinkPtr(simul_fe, link_prev), FrontendGetLinkPtr(simul_fe, link_next), true);
			simul_fe->m_frontend->setEnabled(false);
		}
	}

	//PrintLinks(fe);

	//setDefaultFBCID(link_fe);
	UpdateLNBSlotMask(FESlotID(fe), FESlotID(GetHead(fe)), /*remove*/true);
}

void eFBCTunerManager::UpdateLNBSlotMask(int dest_slot, int src_slot, bool remove)
{
	ePtr<eDVBSatelliteEquipmentControl> sec = eDVBSatelliteEquipmentControl::getInstance();
	int idx, sec_lnbidx;

	sec_lnbidx = sec->m_lnbidx;

	for (idx = 0; idx <= sec_lnbidx; ++idx)
	{
		eDVBSatelliteLNBParameters &lnb_param = sec->m_lnbs[idx];

		if (lnb_param.m_slot_mask & (1 << src_slot))
		{
			if (remove)
				lnb_param.m_slot_mask &= ~(1 << dest_slot);
			else
				lnb_param.m_slot_mask |= (1 << dest_slot);
		}
	}
}

bool eFBCTunerManager::CanLink(eDVBRegisteredFrontend *fe) const
{
	if(IsRootFE(fe))
		return false;

	if(FrontendGetLinkPtr(fe, link_prev) || FrontendGetLinkPtr(fe, link_next))
		return false;

	if(IsSCR(fe))
		return false;

	return true;
}

int eFBCTunerManager::getLinkedSlotID(int fe_id) const
{
	eDVBRegisteredFrontend *prev_fe;
	eSmartPtrList<eDVBRegisteredFrontend> &frontends = m_res_mgr->m_frontend;

	for (eSmartPtrList<eDVBRegisteredFrontend>::iterator it(frontends.begin()); it != frontends.end(); ++it)
		if((it->m_frontend->getSlotID() == fe_id) && ((prev_fe = FrontendGetLinkPtr(it, link_prev))))
			return(FESlotID(prev_fe));

	return -1;
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

	fprintf(stderr, "**** [*][eFBCTunerManager::printLinks] fe id : %d (%p), inuse : %d, enabled : %d, fbc : %d\n", FESlotID(current_fe), current_fe, current_fe->m_inuse, current_fe->m_frontend->getEnabled(), current_fe->m_frontend->is_FBCTuner());

	while ((current_fe = FrontendGetLinkPtr(current_fe, link_next)))
		fprintf(stderr, "**** [*][eFBCTunerManager::printLinks] fe id : %d (%p), inuse : %d, enabled : %d, fbc : %d\n", FESlotID(current_fe), current_fe, current_fe->m_inuse, current_fe->m_frontend->getEnabled(), current_fe->m_frontend->is_FBCTuner());

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

		fprintf(stderr, "**** [*][eFBCTunerManager::printLinks] fe_id : %2d, inuse : %d, enabled : %d, fbc : %d, prev : %2d, cur : %2d, next : %2d\n", FESlotID(it), it->m_inuse, it->m_frontend->getEnabled(), it->m_frontend->is_FBCTuner(), prev, FESlotID(it), next);
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

		fprintf(stderr, "**** [*][eFBCTunerManager::printLinks] fe_id : %2d, inuse : %d, enabled : %d, fbc : %d, prev : %2d, cur : %2d, next : %2d (simulate)\n", FESlotID(it), it->m_inuse, it->m_frontend->getEnabled(), it->m_frontend->is_FBCTuner(), prev, FESlotID(it), next);
	}
}
