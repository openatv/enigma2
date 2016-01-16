#include <lib/dvb/fbc.h>
#include <lib/dvb/dvb.h>
#include <lib/dvb/sec.h>
#include <lib/base/cfile.h>
#include <lib/base/object.h>

#include <unistd.h>
#include <fcntl.h>

DEFINE_REF(eFBCTunerManager);

eFBCTunerManager* eFBCTunerManager::m_instance = (eFBCTunerManager*)0;

eFBCTunerManager* eFBCTunerManager::getInstance()
{
	return m_instance;
}

eFBCTunerManager::eFBCTunerManager(ePtr<eDVBResourceManager> res_mgr)
	:m_res_mgr(res_mgr)
{
	char tmp[128];
	eSmartPtrList<eDVBRegisteredFrontend> &frontends = m_res_mgr->m_frontend;

	m_instance = this;

	// FIXME
	// This finds the number of virtual tuners even though we want to know
	// the number of physical ("root") tuners. The calculation in the return
	// statement is just a guess and works for now.

	for(m_fbc_tuner_num = 0; m_fbc_tuner_num < 128; m_fbc_tuner_num++)
	{
		snprintf(tmp, sizeof(tmp), "/proc/stb/frontend/%d/fbc_id", m_fbc_tuner_num);

		if(access(tmp, F_OK))
			break;
	}

	/* number of fbc tuners in one set */
	m_fbc_tuner_num /= (FBC_TUNER_SET / 2);

	/* each FBC set has 8 tuners */
	/* first set: 0-7 */
	/* second set: 8-16 */
	/* first, second frontend is top on a set */

	for (eSmartPtrList<eDVBRegisteredFrontend>::iterator it(frontends.begin()); it != frontends.end(); ++it)
		setDefaultFBCID(*it);
}

eFBCTunerManager::~eFBCTunerManager()
{
	m_instance = (eFBCTunerManager*)0;
}

int eFBCTunerManager::fe_slot_id(const eDVBRegisteredFrontend *fe) const
{
	return(fe->m_frontend->getSlotID());
}

long eFBCTunerManager::frontend_get_linkptr(const eDVBRegisteredFrontend *fe, link_ptr_t link_type) const
{
	int data_type;
	long data;

	switch(link_type)
	{
		case(link_prev): data_type = eDVBFrontend::LINKED_PREV_PTR; break;
		case(link_next): data_type = eDVBFrontend::LINKED_NEXT_PTR; break;
		default: return(-1);
	}

	if(fe->m_frontend->getData(data_type, data)) // returns != 0 on error
		data = -1;

	return(data);
}

void eFBCTunerManager::frontend_set_linkptr(const eDVBRegisteredFrontend *fe, link_ptr_t link_type, long data) const
{
	int data_type;

	switch(link_type)
	{
		case(link_prev): data_type = eDVBFrontend::LINKED_PREV_PTR; break;
		case(link_next): data_type = eDVBFrontend::LINKED_NEXT_PTR; break;
		default: return;
	}

	fe->m_frontend->setData(data_type, data);
}

void eFBCTunerManager::setProcFBCID(int fe_id, int fbc_id)
{
	char tmp[64];
	snprintf(tmp, sizeof(tmp), "/proc/stb/frontend/%d/fbc_id", fe_id);

	if(isLinkedByIndex(fe_id))
		fbc_id += 0x10; // 0x10 mask: linked, 0x0f (?) mask: fbc_id // FIXME: shouldn't this be |=?

	CFile::writeIntHex(tmp, fbc_id);
}

bool eFBCTunerManager::isRootFe(eDVBRegisteredFrontend *fe)
{
	return (fe_slot_id(fe) % FBC_TUNER_SET) < m_fbc_tuner_num;
}

bool eFBCTunerManager::isSameFbcSet(int a, int b)
{
	return((a / FBC_TUNER_SET) == (b / FBC_TUNER_SET));
}

int eFBCTunerManager::getFBCID(int top_fe_id)
{
	return (((2 * top_fe_id) / FBC_TUNER_SET) + (top_fe_id % FBC_TUNER_SET)); /* (0,1,8,9,16,17...) -> (0,1,2,3,4,5...) */
}

void eFBCTunerManager::setDefaultFBCID(eDVBRegisteredFrontend *fe)
{
	setProcFBCID(fe_slot_id(fe), isRootFe(fe) ? getFBCID(fe_slot_id(fe)) : 0);
}

void eFBCTunerManager::updateFBCID(eDVBRegisteredFrontend *next_fe, eDVBRegisteredFrontend *prev_fe)
{
	setProcFBCID(fe_slot_id(next_fe), getFBCID(fe_slot_id(getTop(prev_fe))));
}

eDVBRegisteredFrontend *eFBCTunerManager::getPrev(eDVBRegisteredFrontend *fe)
{
	long link;

	if((link = frontend_get_linkptr(fe, link_prev)) == -1)
		link = 0;

	return((eDVBRegisteredFrontend *)link);
}

eDVBRegisteredFrontend *eFBCTunerManager::getNext(eDVBRegisteredFrontend *fe)
{
	long link;

	if((link = frontend_get_linkptr(fe, link_next)) == -1)
		link = 0;

	return((eDVBRegisteredFrontend *)link);
}

eDVBRegisteredFrontend *eFBCTunerManager::getTop(eDVBRegisteredFrontend *fe)
{
	eDVBRegisteredFrontend *prev_fe;
	long linked_prev_ptr;

	//FIXME: assumed sizeof(*) == sizeof(long)

	for(prev_fe = fe;
			(linked_prev_ptr = frontend_get_linkptr(prev_fe, link_prev)) != -1;
			prev_fe = (eDVBRegisteredFrontend *)linked_prev_ptr)
		(void)0;

	return(prev_fe);
}

eDVBRegisteredFrontend *eFBCTunerManager::getLast(eDVBRegisteredFrontend *fe)
{
	eDVBRegisteredFrontend *next_fe;
	long linked_next_ptr;

	for(next_fe = fe;
			(linked_next_ptr = frontend_get_linkptr(next_fe, link_next)) != -1;
			next_fe = (eDVBRegisteredFrontend *)linked_next_ptr)
		(void)0;

	return(next_fe);
}

bool eFBCTunerManager::isLinked(eDVBRegisteredFrontend *fe)
{
	return(!(getPrev(fe) == (eDVBRegisteredFrontend *)0));
}

bool eFBCTunerManager::isLinkedByIndex(int fe_idx)
{
	bool linked = false;
	eSmartPtrList<eDVBRegisteredFrontend> &frontends = m_res_mgr->m_frontend;

	for (eSmartPtrList<eDVBRegisteredFrontend>::iterator it(frontends.begin()); it != frontends.end(); ++it)
	{
		if (fe_slot_id(it) == fe_idx)
		{
			linked = isLinked(*it);
			break;
		}
	}
	return linked;
}

int eFBCTunerManager::connectLinkByIndex(int link_fe_index, int prev_fe_index, int next_fe_index, bool simulate)
{
	eSmartPtrList<eDVBRegisteredFrontend> &frontends = simulate ? m_res_mgr->m_simulate_frontend : m_res_mgr->m_frontend;

	eDVBRegisteredFrontend *link_fe = (eDVBRegisteredFrontend *)0;
	eDVBRegisteredFrontend *prev_fe = (eDVBRegisteredFrontend *)0;
	eDVBRegisteredFrontend *next_fe = (eDVBRegisteredFrontend *)0;

	for (eSmartPtrList<eDVBRegisteredFrontend>::iterator it(frontends.begin()); it != frontends.end(); ++it)
	{
		if (fe_slot_id(it) == prev_fe_index)
			prev_fe = *it;
		else if (fe_slot_id(it) == next_fe_index)
			next_fe = *it;
		else if (fe_slot_id(it) == link_fe_index)
			link_fe = *it;
	}

	if (prev_fe && next_fe && link_fe)
	{
		link_fe->m_frontend->setEnabled(true);

		frontend_set_linkptr(prev_fe, link_next, (long)link_fe);
		frontend_set_linkptr(link_fe, link_prev, (long)prev_fe);
		frontend_set_linkptr(link_fe, link_next, (long)next_fe);
		frontend_set_linkptr(next_fe, link_prev, (long)link_fe);
	}
	else
		return -1;

	return 0;
}

int eFBCTunerManager::connectLinkByIndex(int link_fe_index, int prev_fe_index, bool simulate)
{
	eSmartPtrList<eDVBRegisteredFrontend> &frontends = simulate ? m_res_mgr->m_simulate_frontend : m_res_mgr->m_frontend;

	eDVBRegisteredFrontend *link_fe = (eDVBRegisteredFrontend *)0;
	eDVBRegisteredFrontend *prev_fe = (eDVBRegisteredFrontend *)0;

	for (eSmartPtrList<eDVBRegisteredFrontend>::iterator it(frontends.begin()); it != frontends.end(); ++it)
	{
		if (fe_slot_id(it) == prev_fe_index)
			prev_fe = *it;
		else if (fe_slot_id(it) == link_fe_index)
			link_fe = *it;
	}

	if (prev_fe && link_fe)
	{
		link_fe->m_frontend->setEnabled(true);

		frontend_set_linkptr(prev_fe, link_next, (long)link_fe);
		frontend_set_linkptr(link_fe, link_prev, (long)prev_fe);
	}
	else
		return -1;

	return 0;
}

int eFBCTunerManager::disconnectLinkByIndex(int link_fe_index, int prev_fe_index, int next_fe_index, bool simulate)
{
	eSmartPtrList<eDVBRegisteredFrontend> &frontends = simulate ? m_res_mgr->m_simulate_frontend : m_res_mgr->m_frontend;

	eDVBRegisteredFrontend *link_fe = (eDVBRegisteredFrontend *)0;
	eDVBRegisteredFrontend *prev_fe = (eDVBRegisteredFrontend *)0;
	eDVBRegisteredFrontend *next_fe = (eDVBRegisteredFrontend *)0;

	for (eSmartPtrList<eDVBRegisteredFrontend>::iterator it(frontends.begin()); it != frontends.end(); ++it)
	{
		if (fe_slot_id(it) == prev_fe_index)
			prev_fe = *it;
		else if (fe_slot_id(it) == next_fe_index)
			next_fe = *it;
		else if (fe_slot_id(it) == link_fe_index)
			link_fe = *it;
	}

	if (prev_fe && next_fe && link_fe)
	{
		frontend_set_linkptr(prev_fe, link_next, (long)next_fe);
		frontend_set_linkptr(next_fe, link_prev, (long)prev_fe);
		frontend_set_linkptr(link_fe, link_prev, -1);
		frontend_set_linkptr(link_fe, link_next, -1);

		link_fe->m_frontend->setEnabled(false);
	}
	else
		return -1;

	return 0;
}
int eFBCTunerManager::disconnectLinkByIndex(int link_fe_index, int prev_fe_index, bool simulate)
{
	eSmartPtrList<eDVBRegisteredFrontend> &frontends = simulate ? m_res_mgr->m_simulate_frontend : m_res_mgr->m_frontend;

	eDVBRegisteredFrontend *link_fe = (eDVBRegisteredFrontend *)0;
	eDVBRegisteredFrontend *prev_fe = (eDVBRegisteredFrontend *)0;

	for (eSmartPtrList<eDVBRegisteredFrontend>::iterator it(frontends.begin()); it != frontends.end(); ++it)
	{
		if (fe_slot_id(it) == prev_fe_index)
			prev_fe = *it;
		else if (fe_slot_id(it) == link_fe_index)
			link_fe = *it;
	}

	if (prev_fe && link_fe)
	{
		frontend_set_linkptr(prev_fe, link_next, -1);
		frontend_set_linkptr(link_fe, link_prev, -1);

		link_fe->m_frontend->setEnabled(false);
	}
	else
		return -1;

	return 0;
}

int eFBCTunerManager::connectLink(eDVBRegisteredFrontend *link_fe, eDVBRegisteredFrontend *prev_fe, eDVBRegisteredFrontend *next_fe, bool simulate)
{
	int ret;

	if(!(ret = connectLinkByIndex(fe_slot_id(link_fe), fe_slot_id(prev_fe), fe_slot_id(next_fe), !simulate)))
	{
		frontend_set_linkptr(prev_fe, link_next, (long)link_fe);
		frontend_set_linkptr(link_fe, link_prev, (long)prev_fe);
		frontend_set_linkptr(link_fe, link_next, (long)next_fe);
		frontend_set_linkptr(next_fe, link_prev, (long)link_fe);

		link_fe->m_frontend->setEnabled(true);	
	}

	return ret;
}

int eFBCTunerManager::connectLink(eDVBRegisteredFrontend *link_fe, eDVBRegisteredFrontend *prev_fe, bool simulate)
{
	int ret;

	if(!(ret = connectLinkByIndex(fe_slot_id(link_fe), fe_slot_id(prev_fe), !simulate)))
	{
		frontend_set_linkptr(prev_fe, link_next, (long)link_fe);
		frontend_set_linkptr(link_fe, link_prev, (long)prev_fe);

		link_fe->m_frontend->setEnabled(true);
	}

	return ret;
}

int eFBCTunerManager::disconnectLink(eDVBRegisteredFrontend *link_fe, eDVBRegisteredFrontend *prev_fe, eDVBRegisteredFrontend *next_fe, bool simulate)
{
	int ret;

	if(!(ret = disconnectLinkByIndex(fe_slot_id(link_fe), fe_slot_id(prev_fe), fe_slot_id(next_fe), !simulate)))
	{
		frontend_set_linkptr(prev_fe, link_next, (long)next_fe);
		frontend_set_linkptr(next_fe, link_prev, (long)prev_fe);
		frontend_set_linkptr(link_fe, link_prev, -1);
		frontend_set_linkptr(link_fe, link_next, -1);

		link_fe->m_frontend->setEnabled(false);
	}

	return ret;
}

int eFBCTunerManager::disconnectLink(eDVBRegisteredFrontend *link_fe, eDVBRegisteredFrontend *prev_fe, bool simulate)
{
	int ret;

	if(!(ret = disconnectLinkByIndex(fe_slot_id(link_fe), fe_slot_id(prev_fe), !simulate)))
	{
		frontend_set_linkptr(prev_fe, link_next, -1);
		frontend_set_linkptr(link_fe, link_prev, -1);

		link_fe->m_frontend->setEnabled(false);
	}

	return ret;
}

void eFBCTunerManager::connectLinkNoSimulate(eDVBRegisteredFrontend *link_fe, eDVBRegisteredFrontend *top_fe)
{
	eDVBRegisteredFrontend *last_fe = getLast(top_fe);

	frontend_set_linkptr(last_fe, link_next, (long)link_fe);
	frontend_set_linkptr(link_fe, link_prev, (long)last_fe);

	link_fe->m_frontend->setEnabled(true);

	updateLNBSlotMask(fe_slot_id(link_fe), fe_slot_id(top_fe), false);
}

void eFBCTunerManager::disconnectLinkNoSimulate(eDVBRegisteredFrontend *link_fe)
{
	if(getNext(link_fe))
		return;

	eDVBRegisteredFrontend *prev_fe = getPrev(link_fe);

	if(!prev_fe)
		return;

	frontend_set_linkptr(prev_fe, link_next, -1);
	frontend_set_linkptr(link_fe, link_prev, -1);

	link_fe->m_frontend->setEnabled(false);

	updateLNBSlotMask(fe_slot_id(link_fe), fe_slot_id(prev_fe), true);
}

bool eFBCTunerManager::checkUsed(eDVBRegisteredFrontend *fe, bool a_simulate)
{
	if (fe->m_inuse > 0)
		return true;

	bool simulate = !a_simulate;

	eSmartPtrList<eDVBRegisteredFrontend> &frontends = simulate ? m_res_mgr->m_simulate_frontend : m_res_mgr->m_frontend;

	for (eSmartPtrList<eDVBRegisteredFrontend>::iterator it(frontends.begin()); it != frontends.end(); ++it)
		if (fe_slot_id(it) == fe_slot_id(fe))
			return(it->m_inuse > 0);

	return false;
}

bool eFBCTunerManager::canLink(eDVBRegisteredFrontend *fe)
{
	if(isRootFe(fe))
		return false;

	if(getPrev(fe) || getNext(fe))
		return false;

	if(isUnicable(fe))
		return false;

	return true;
}

bool eFBCTunerManager::isUnicable(eDVBRegisteredFrontend *fe)
{
	ePtr<eDVBSatelliteEquipmentControl> sec = eDVBSatelliteEquipmentControl::getInstance();
	int slot_idx = fe_slot_id(fe);
	bool is_unicable = false;
	int idx;

	for (idx = 0; idx <= sec->m_lnbidx; ++idx)
	{
		eDVBSatelliteLNBParameters &lnb_param = sec->m_lnbs[idx];

		if (lnb_param.m_slot_mask & (1 << slot_idx))
		{
			is_unicable = lnb_param.SatCR_idx != -1;
			break;
		}
	}
	return is_unicable;
}

int eFBCTunerManager::isCompatibleWith(ePtr<iDVBFrontendParameters> &feparm, eDVBRegisteredFrontend *link_fe, bool simulate)
{
	eDVBRegisteredFrontend *best_fbc_fe;

	return isCompatibleWith(feparm, link_fe, best_fbc_fe, simulate);
}

int eFBCTunerManager::isCompatibleWith(ePtr<iDVBFrontendParameters> &feparm, eDVBRegisteredFrontend *link_fe, eDVBRegisteredFrontend *&fbc_fe, bool simulate)
{
	int best_score = 0;
	int c;

	eSmartPtrList<eDVBRegisteredFrontend> &frontends = simulate ? m_res_mgr->m_simulate_frontend : m_res_mgr->m_frontend;

	for (eSmartPtrList<eDVBRegisteredFrontend>::iterator it(frontends.begin()); it != frontends.end(); ++it)
	{
		if (!it->m_frontend->is_FBCTuner())
			continue;

		if (!isRootFe(*it))
			continue;

		if(!it->m_frontend->getEnabled())
			continue;

		if(!isSameFbcSet(fe_slot_id(link_fe), fe_slot_id(it)))
			continue;

		if(it->m_inuse == 0)
			continue;

		if(isLinked(*it))
			continue;

		if(isUnicable(*it))
			continue;

		connectLinkNoSimulate(link_fe, *it);

		c = link_fe->m_frontend->isCompatibleWith(feparm);

		if (c > best_score)
		{
			best_score = c;
			fbc_fe = (eDVBRegisteredFrontend *)*it;
		}

		disconnectLinkNoSimulate(link_fe);
	}

	return best_score;
}

void eFBCTunerManager::connectSortedLink(eDVBRegisteredFrontend *link_fe, eDVBRegisteredFrontend *top_fe, bool simulate)
{
	eDVBRegisteredFrontend *prev_fe;
	eDVBRegisteredFrontend *next_fe;

	int link_fe_id;
	int top_fe_id;
	int prev_fe_id;
	int res;
	long linked_next_ptr;

	link_fe_id = fe_slot_id(link_fe);
	top_fe_id = fe_slot_id(top_fe);

	if((prev_fe_id = link_fe_id - 1) < 0)
		return;

	next_fe = top_fe;
	linked_next_ptr = frontend_get_linkptr(top_fe, link_next);

	while(linked_next_ptr != -1)
	{
		next_fe = (eDVBRegisteredFrontend *)linked_next_ptr;
		linked_next_ptr = frontend_get_linkptr(next_fe, link_next);

		if (fe_slot_id(next_fe) == prev_fe_id)
			break;
	}

	prev_fe = next_fe;

	next_fe = getNext(prev_fe);	

	if (next_fe)
	{
		if((res = connectLink(link_fe, prev_fe, next_fe, simulate)))
			return;
	}
	else
	{
		if((res = connectLink(link_fe, prev_fe, simulate)))
			return;
	}

	setProcFBCID(link_fe_id, getFBCID(top_fe_id));
	updateLNBSlotMask(link_fe_id, top_fe_id, false);
}

void eFBCTunerManager::addLink(eDVBRegisteredFrontend *link_fe, eDVBRegisteredFrontend *top_fe, bool simulate)
{
	if (!isRootFe(top_fe))
		return;

	connectSortedLink(link_fe, top_fe, simulate);
}

/* all unused linked fbc fe must be unlinked! */
void eFBCTunerManager::unset(eDVBRegisteredFrontend *fe)
{
	bool simulate = fe->m_frontend->is_simulate();
	int res;

	if (isRootFe(fe))
		return;

	if(checkUsed(fe, simulate))
		return;

	if(isUnicable(fe))
		return;

	eDVBRegisteredFrontend *linked_prev_fe = getPrev(fe);
	eDVBRegisteredFrontend *linked_next_fe = getNext(fe);

	if (!linked_prev_fe)
		return;

	if (linked_next_fe)
	{
		if((res = disconnectLink(fe, linked_prev_fe, linked_next_fe, simulate)))
			return;
	}
	else
	{
		if((res = disconnectLink(fe, linked_prev_fe, simulate)))
			return;
	}

	setProcFBCID(fe_slot_id(fe), 0);
	updateLNBSlotMask(fe_slot_id(fe), fe_slot_id(linked_prev_fe), true);
}

int eFBCTunerManager::updateLNBSlotMask(int dest_slot, int src_slot, bool remove)
{
	int idx;
	ePtr<eDVBSatelliteEquipmentControl> sec = eDVBSatelliteEquipmentControl::getInstance();

	int sec_lnbidx = sec->m_lnbidx;

	for (idx = 0; idx <= sec_lnbidx; ++idx)
	{
		eDVBSatelliteLNBParameters &lnb_param = sec->m_lnbs[idx];

		if (lnb_param.m_slot_mask & (1 << src_slot))
		{
			if (!remove)
				lnb_param.m_slot_mask |= (1 << dest_slot);
			else
				lnb_param.m_slot_mask &= ~(1 << dest_slot);
		}
	}

	return 0;
}

int eFBCTunerManager::getLinkedSlotID(int fe_id)
{
	eDVBRegisteredFrontend *prev_fe;
	eSmartPtrList<eDVBRegisteredFrontend> &frontends = m_res_mgr->m_frontend;
	int link;
	long prev_ptr;

	prev_fe = 0;
	link = -1;

	for (eSmartPtrList<eDVBRegisteredFrontend>::iterator it(frontends.begin()); it != frontends.end(); ++it)
	{
		if(it->m_frontend->getSlotID() == fe_id)
		{
			if((prev_ptr = frontend_get_linkptr(it, link_prev)) != -1)
			{
				prev_fe = (eDVBRegisteredFrontend *)prev_ptr;
				link = fe_slot_id(prev_fe);
			}
			break;
		}
	}

	return link;
}

void eFBCTunerManager::list_loop_links(void)
{
	long prev_ptr, next_ptr;
	eSmartPtrList<eDVBRegisteredFrontend> &frontends = m_res_mgr->m_frontend;

	for (eSmartPtrList<eDVBRegisteredFrontend>::iterator it(frontends.begin()); it != frontends.end(); ++it)
	{
		prev_ptr = frontend_get_linkptr(it, link_prev);
		next_ptr = frontend_get_linkptr(it, link_next);

		printf("**** tuner %d, prev_link:", it->m_frontend->getSlotID());

		if(prev_ptr == 0)
			printf("<0>");
		else
			if(prev_ptr == -1)
				printf("<-1>");
			else
				printf("%d", ((eDVBRegisteredFrontend *)prev_ptr)->m_frontend->getSlotID());

		printf(", next_link:");

		if(next_ptr == 0)
			printf("<0>");
		else
			if(next_ptr == -1)
				printf("<-1>");
			else
				printf("%d", ((eDVBRegisteredFrontend *)next_ptr)->m_frontend->getSlotID());

		printf("\n");
	}
}
