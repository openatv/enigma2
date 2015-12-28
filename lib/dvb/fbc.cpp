#include <lib/dvb/fbc.h>
#include <lib/dvb/dvb.h>
#include <lib/dvb/sec.h>
#include <lib/base/object.h>

#include <unistd.h>
#include <fcntl.h>

DEFINE_REF(eFBCTunerManager);

bool eFBCTunerManager::isDestroyed = false;

eFBCTunerManager::eFBCTunerManager()
{
	ePtr<eDVBResourceManager> res_mgr;
	eDVBResourceManager::getInstance(res_mgr);
	m_res_mgr = res_mgr;

	/* num of fbc tuner in one set */
	m_fbc_tuner_num = getFBCTunerNum();
	procInit();
}

int eFBCTunerManager::fe_slot_id(const eDVBRegisteredFrontend *fe) const
{
	return(fe->m_frontend->getSlotID());
}

eFBCTunerManager::~eFBCTunerManager()
{
	isDestroyed = true;
}

void eFBCTunerManager::procInit()
{
	eSmartPtrList<eDVBRegisteredFrontend> &frontends = m_res_mgr->m_frontend;

	/* 1 FBC set has 8 tuners. */
	/* 1st set : 0, 1, 2, 3, 4, 5, 6, 7 */
	/* 2nd set : 8, 9, 10, 11, 12, 13, 14, 15 */
	/* 1st, 2nd frontend is top on a set */

	for (eSmartPtrList<eDVBRegisteredFrontend>::iterator it(frontends.begin()); it != frontends.end(); ++it)
	{
		if (!it->m_frontend->is_FBCTuner())
			continue;

		if (isRootFe(*it))
		{
			setProcFBCID(fe_slot_id(it), getFBCID(fe_slot_id(it)));
		}
	}
}

int eFBCTunerManager::getFBCTunerNum()
{
	char tmp[255];
	int fbc_tuner_num = 0;
	int fd = open("/proc/stb/info/chipset", O_RDONLY);
	if(fd < 0) {
		eDebug("open failed, /proc/stb/info/chipset!");
	}
	else
	{
		read(fd, tmp, 255);
		close(fd);

		if (!!strstr(tmp, "7376"))
			fbc_tuner_num = 2;
	}
	return fbc_tuner_num;
}

int eFBCTunerManager::setProcFBCID(int fe_id, int fbc_id)
{
	char filename[128];
	char data[4];
	sprintf(filename, "/proc/stb/frontend/%d/fbc_id", fe_id);
	int fd = open(filename, O_RDWR);
	if(fd < 0) {
		eDebug("[*][eFBCTunerManager::setProcFBCID] open failed, %s: %m", filename);
		return -1;
	}
	else
	{
		if(isLinkedByIndex(fe_id))
			fbc_id += 0x10; // 0x10 : isLinked, 0x01 : fbc_id

		sprintf(data, "%x", fbc_id);
		write(fd, data, strlen(data));
		close(fd);
	}
	return 0;
}

bool eFBCTunerManager::isRootFeSlot(int fe_slot_id)
{
	return (fe_slot_id%8 < m_fbc_tuner_num) ? true : false;
}


bool eFBCTunerManager::isRootFe(eDVBRegisteredFrontend *fe)
{
	return isRootFeSlot(fe_slot_id(fe));
}

bool eFBCTunerManager::isSameFbcSet(int a, int b)
{
	return (a/8) == (b/8) ? true : false;
}

bool eFBCTunerManager::isSupportDVBS(eDVBRegisteredFrontend *fe)
{
	return (fe->m_frontend->supportsDeliverySystem(SYS_DVBS, true) || fe->m_frontend->supportsDeliverySystem(SYS_DVBS2, true)) ? true : false;
}

int eFBCTunerManager::getFBCID(int top_fe_id)
{
	return 2*top_fe_id/8 + top_fe_id%8; /* (0,1,8,9,16,17...) -> (0,1,2,3,4,5...)*/
}

int eFBCTunerManager::setDefaultFBCID(eDVBRegisteredFrontend *fe)
{
	if (!isRootFe(fe))
		return -1;

	return setProcFBCID(fe_slot_id(fe), getFBCID(fe_slot_id(fe)));
}

void eFBCTunerManager::updateFBCID(eDVBRegisteredFrontend *next_fe, eDVBRegisteredFrontend *prev_fe)
{
	eDVBRegisteredFrontend *top_fe = getTop(prev_fe);
	setProcFBCID(fe_slot_id(next_fe), getFBCID(fe_slot_id(top_fe)));
}

eDVBRegisteredFrontend *eFBCTunerManager::getPrev(eDVBRegisteredFrontend *fe)
{
	eDVBRegisteredFrontend *prev_fe = NULL;
	long linked_prev_ptr = -1;
	fe->m_frontend->getData(eDVBFrontend::LINKED_PREV_PTR, linked_prev_ptr);
	if (linked_prev_ptr != -1)
		prev_fe = (eDVBRegisteredFrontend *)linked_prev_ptr;
	return prev_fe;
}

eDVBRegisteredFrontend *eFBCTunerManager::getNext(eDVBRegisteredFrontend *fe)
{
	eDVBRegisteredFrontend *next_fe = NULL;
	long linked_next_ptr = -1;
	fe->m_frontend->getData(eDVBFrontend::LINKED_NEXT_PTR, linked_next_ptr);
	if (linked_next_ptr != -1)
		next_fe = (eDVBRegisteredFrontend *)linked_next_ptr;
	return next_fe;
}

eDVBRegisteredFrontend *eFBCTunerManager::getTop(eDVBRegisteredFrontend *fe)
{
	eDVBRegisteredFrontend *prev_fe = fe;
	long linked_prev_ptr = -1;
	fe->m_frontend->getData(eDVBFrontend::LINKED_PREV_PTR, linked_prev_ptr);
	while(linked_prev_ptr != -1)
	{
		prev_fe = (eDVBRegisteredFrontend *)linked_prev_ptr;
		prev_fe->m_frontend->getData(eDVBFrontend::LINKED_PREV_PTR, linked_prev_ptr);
	}
	return prev_fe;
}

eDVBRegisteredFrontend *eFBCTunerManager::getLast(eDVBRegisteredFrontend *fe)
{
	eDVBRegisteredFrontend *next_fe = fe;
	long linked_next_ptr = -1;
	fe->m_frontend->getData(eDVBFrontend::LINKED_NEXT_PTR, linked_next_ptr);
	while(linked_next_ptr != -1)
	{
		next_fe = (eDVBRegisteredFrontend *)linked_next_ptr;
		next_fe->m_frontend->getData(eDVBFrontend::LINKED_NEXT_PTR, linked_next_ptr);
	}
	return next_fe;
}

bool eFBCTunerManager::isLinked(eDVBRegisteredFrontend *fe)
{
	return getPrev(fe) ? true:false;
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

bool eFBCTunerManager::checkTop(eDVBRegisteredFrontend *fe)
{
	return getPrev(fe) ? false:true;
}

int eFBCTunerManager::connectLinkByIndex(int link_fe_index, int prev_fe_index, int next_fe_index, bool simulate)
{
	eSmartPtrList<eDVBRegisteredFrontend> &frontends = simulate ? m_res_mgr->m_simulate_frontend : m_res_mgr->m_frontend;

	eDVBRegisteredFrontend *link_fe=NULL;
	eDVBRegisteredFrontend *prev_fe=NULL;
	eDVBRegisteredFrontend *next_fe=NULL;

	for (eSmartPtrList<eDVBRegisteredFrontend>::iterator it(frontends.begin()); it != frontends.end(); ++it)
	{
		if (fe_slot_id(it) == prev_fe_index)
		{
			prev_fe = *it;
		}
		else if (fe_slot_id(it) == next_fe_index)
		{
			next_fe = *it;
		}
		else if (fe_slot_id(it) == link_fe_index)
		{
			link_fe = *it;
		}
	}

	if (prev_fe && next_fe && link_fe)
	{
		/* enable linked fe */
		link_fe->m_frontend->setEnabled(true);

		/* connect */
		prev_fe->m_frontend->setData(eDVBFrontend::LINKED_NEXT_PTR, (long)link_fe);
		link_fe->m_frontend->setData(eDVBFrontend::LINKED_PREV_PTR, (long)prev_fe);

		link_fe->m_frontend->setData(eDVBFrontend::LINKED_NEXT_PTR, (long)next_fe);
		next_fe->m_frontend->setData(eDVBFrontend::LINKED_PREV_PTR, (long)link_fe);
	}
	else
	{
		eDebug("	[*][eFBCTunerManager::connectLinkByIndex] connect failed! (prev_fe : %p, next_fe : %p, link_fe : %p, %s)", prev_fe, next_fe, link_fe, simulate?"simulate":"");
		return -1;
	}

	return 0;
}

int eFBCTunerManager::connectLinkByIndex(int link_fe_index, int prev_fe_index, bool simulate)
{
	eSmartPtrList<eDVBRegisteredFrontend> &frontends = simulate ? m_res_mgr->m_simulate_frontend : m_res_mgr->m_frontend;

	eDVBRegisteredFrontend *link_fe=NULL;
	eDVBRegisteredFrontend *prev_fe=NULL;

	for (eSmartPtrList<eDVBRegisteredFrontend>::iterator it(frontends.begin()); it != frontends.end(); ++it)
	{
		if (fe_slot_id(it) == prev_fe_index)
		{
			prev_fe = *it;
		}
		else if (fe_slot_id(it) == link_fe_index)
		{
			link_fe = *it;
		}
	}

	if (prev_fe && link_fe)
	{
		/* enable linked fe */
		link_fe->m_frontend->setEnabled(true);

		/* connect */
		prev_fe->m_frontend->setData(eDVBFrontend::LINKED_NEXT_PTR, (long)link_fe);
		link_fe->m_frontend->setData(eDVBFrontend::LINKED_PREV_PTR, (long)prev_fe);
	}
	else
	{
		eDebug("	[*][eFBCTunerManager::connectLinkByIndex] connect failed! (prev_fe : %p, link_fe : %p, %s)", prev_fe, link_fe, simulate?"simulate":"");
		return -1;
	}

	return 0;
}

int eFBCTunerManager::disconnectLinkByIndex(int link_fe_index, int prev_fe_index, int next_fe_index, bool simulate)
{
	eSmartPtrList<eDVBRegisteredFrontend> &frontends = simulate ? m_res_mgr->m_simulate_frontend : m_res_mgr->m_frontend;

	eDVBRegisteredFrontend *link_fe=NULL;
	eDVBRegisteredFrontend *prev_fe=NULL;
	eDVBRegisteredFrontend *next_fe=NULL;

	for (eSmartPtrList<eDVBRegisteredFrontend>::iterator it(frontends.begin()); it != frontends.end(); ++it)
	{
		if (fe_slot_id(it) == prev_fe_index)
		{
			prev_fe = *it;
		}
		else if (fe_slot_id(it) == next_fe_index)
		{
			next_fe = *it;
		}
		else if (fe_slot_id(it) == link_fe_index)
		{
			link_fe = *it;
		}
	}

	if (prev_fe && next_fe && link_fe)
	{
		/* disconnect */
		prev_fe->m_frontend->setData(eDVBFrontend::LINKED_NEXT_PTR, (long)next_fe);
		next_fe->m_frontend->setData(eDVBFrontend::LINKED_PREV_PTR, (long)prev_fe);

		link_fe->m_frontend->setData(eDVBFrontend::LINKED_PREV_PTR, (long)-1);
		link_fe->m_frontend->setData(eDVBFrontend::LINKED_NEXT_PTR, (long)-1);

		/* enable linked fe */
		link_fe->m_frontend->setEnabled(false);
	}
	else
	{
		eDebug("	[*][eFBCTunerManager::disconnectLinkByIndex] disconnect failed! (prev_fe : %p, next_fe : %p, link_fe : %p, %s)", prev_fe, next_fe, link_fe, simulate?"simulate":"");
		return -1;
	}

	return 0;
}
int eFBCTunerManager::disconnectLinkByIndex(int link_fe_index, int prev_fe_index, bool simulate)
{
	eSmartPtrList<eDVBRegisteredFrontend> &frontends = simulate ? m_res_mgr->m_simulate_frontend : m_res_mgr->m_frontend;

	eDVBRegisteredFrontend *link_fe=NULL;
	eDVBRegisteredFrontend *prev_fe=NULL;

	for (eSmartPtrList<eDVBRegisteredFrontend>::iterator it(frontends.begin()); it != frontends.end(); ++it)
	{
		if (fe_slot_id(it) == prev_fe_index)
		{
			prev_fe = *it;
		}
		else if (fe_slot_id(it) == link_fe_index)
		{
			link_fe = *it;
		}
	}

	if (prev_fe && link_fe)
	{
		/* disconnect */
		prev_fe->m_frontend->setData(eDVBFrontend::LINKED_NEXT_PTR, (long)-1);
		link_fe->m_frontend->setData(eDVBFrontend::LINKED_PREV_PTR, (long)-1);

		/* enable linked fe */
		link_fe->m_frontend->setEnabled(false);
	}
	else
	{
		eDebug("	[*][eFBCTunerManager::disconnectLinkByIndex] disconnect failed! (prev_fe : %p, link_fe : %p, %s)", prev_fe, link_fe, simulate?"simulate":"");
		return -1;
	}

	return 0;
}

int eFBCTunerManager::connectLink(eDVBRegisteredFrontend *link_fe, eDVBRegisteredFrontend *prev_fe, eDVBRegisteredFrontend *next_fe, bool simulate)
{
	int ret = connectLinkByIndex(fe_slot_id(link_fe), fe_slot_id(prev_fe), fe_slot_id(next_fe), !simulate);
	if(!ret)
	{
		prev_fe->m_frontend->setData(eDVBFrontend::LINKED_NEXT_PTR, (long)link_fe);
		link_fe->m_frontend->setData(eDVBFrontend::LINKED_PREV_PTR, (long)prev_fe);

		link_fe->m_frontend->setData(eDVBFrontend::LINKED_NEXT_PTR, (long)next_fe);
		next_fe->m_frontend->setData(eDVBFrontend::LINKED_PREV_PTR, (long)link_fe);

		/* enable linked fe */
		link_fe->m_frontend->setEnabled(true);	
	}

	return ret;
}

int eFBCTunerManager::connectLink(eDVBRegisteredFrontend *link_fe, eDVBRegisteredFrontend *prev_fe, bool simulate)
{
	int ret = connectLinkByIndex(fe_slot_id(link_fe), fe_slot_id(prev_fe), !simulate);
	if(!ret)
	{
		prev_fe->m_frontend->setData(eDVBFrontend::LINKED_NEXT_PTR, (long)link_fe);
		link_fe->m_frontend->setData(eDVBFrontend::LINKED_PREV_PTR, (long)prev_fe);

		/* enable linked fe */
		link_fe->m_frontend->setEnabled(true);
	}

	return ret;
}

int eFBCTunerManager::disconnectLink(eDVBRegisteredFrontend *link_fe, eDVBRegisteredFrontend *prev_fe, eDVBRegisteredFrontend *next_fe, bool simulate)
{
	int ret = disconnectLinkByIndex(fe_slot_id(link_fe), fe_slot_id(prev_fe), fe_slot_id(next_fe), !simulate);
	if(!ret)
	{
		prev_fe->m_frontend->setData(eDVBFrontend::LINKED_NEXT_PTR, (long)next_fe);
		next_fe->m_frontend->setData(eDVBFrontend::LINKED_PREV_PTR, (long)prev_fe);

		link_fe->m_frontend->setData(eDVBFrontend::LINKED_PREV_PTR, (long)-1);
		link_fe->m_frontend->setData(eDVBFrontend::LINKED_NEXT_PTR, (long)-1);

		link_fe->m_frontend->setEnabled(false);
	}

	return ret;
}

int eFBCTunerManager::disconnectLink(eDVBRegisteredFrontend *link_fe, eDVBRegisteredFrontend *prev_fe, bool simulate)
{
	int ret = disconnectLinkByIndex(fe_slot_id(link_fe), fe_slot_id(prev_fe), !simulate);
	if(!ret)
	{
		prev_fe->m_frontend->setData(eDVBFrontend::LINKED_NEXT_PTR, (long)-1);
		link_fe->m_frontend->setData(eDVBFrontend::LINKED_PREV_PTR, (long)-1);

		link_fe->m_frontend->setEnabled(false);
	}

	return ret;
}

/* no set pair simulate fe */
/* no set proc fbc_id */
void eFBCTunerManager::connectLinkNoSimulate(eDVBRegisteredFrontend *link_fe, eDVBRegisteredFrontend *top_fe)
{
	eDVBRegisteredFrontend *last_fe = getLast(top_fe);

	last_fe->m_frontend->setData(eDVBFrontend::LINKED_NEXT_PTR, (long)link_fe);
	link_fe->m_frontend->setData(eDVBFrontend::LINKED_PREV_PTR, (long)last_fe);

	/* enable linked fe */
	link_fe->m_frontend->setEnabled(true);

	/* add slot mask*/
	updateLNBSlotMask(fe_slot_id(link_fe), fe_slot_id(top_fe), false);
}

/* no set pair simulate fe */
/* no set proc fbc_id */
void eFBCTunerManager::disconnectLinkNoSimulate(eDVBRegisteredFrontend *link_fe)
{
	if(getNext(link_fe))
		return;

	eDVBRegisteredFrontend *prev_fe = getPrev(link_fe);

	if(!prev_fe)
		return;

	prev_fe->m_frontend->setData(eDVBFrontend::LINKED_NEXT_PTR, (long)-1);
	link_fe->m_frontend->setData(eDVBFrontend::LINKED_PREV_PTR, (long)-1);
		
	/* enable linked fe */
	link_fe->m_frontend->setEnabled(false);

	/* add slot mask*/
	updateLNBSlotMask(fe_slot_id(link_fe), fe_slot_id(prev_fe), true);
}

bool eFBCTunerManager::checkUsed(eDVBRegisteredFrontend *fe, bool a_simulate)
{
	if (fe->m_inuse > 0)
		return true;

	bool simulate = !a_simulate;

	eSmartPtrList<eDVBRegisteredFrontend> &frontends = simulate ? m_res_mgr->m_simulate_frontend : m_res_mgr->m_frontend;
	for (eSmartPtrList<eDVBRegisteredFrontend>::iterator it(frontends.begin()); it != frontends.end(); ++it)
	{
		if (fe_slot_id(it) == fe_slot_id(fe))
		{
			return (it->m_inuse >0)?true:false;
		}
	}

	eDebug("[*][eFBCTunerManager::checkUsed] ERROR! can not found fe ptr (feid : %d, simulate : %d)", fe_slot_id(fe), simulate);
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
	int slot_idx = fe_slot_id(fe);
	bool is_unicable = false;

	ePtr<eDVBSatelliteEquipmentControl> sec = eDVBSatelliteEquipmentControl::getInstance();
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

int eFBCTunerManager::isCompatibleWith(ePtr<iDVBFrontendParameters> &feparm, eDVBRegisteredFrontend *link_fe, bool simulate)
{
	eDVBRegisteredFrontend *best_fbc_fe;
	return isCompatibleWith(feparm, link_fe, best_fbc_fe, simulate);
}

int eFBCTunerManager::isCompatibleWith(ePtr<iDVBFrontendParameters> &feparm, eDVBRegisteredFrontend *link_fe, eDVBRegisteredFrontend *&fbc_fe, bool simulate)
{
	int best_score = 0;

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

		if(it->m_inuse == 0) // No link to a fe not in use.
			continue;

		if(isLinked(*it)) // No link to a fe linked to another.
			continue;

		if(isUnicable(*it))
			continue;

		/* connect link */
		connectLinkNoSimulate(link_fe, *it);

		/* get score */
		int c = link_fe->m_frontend->isCompatibleWith(feparm);

		if (c > best_score)
		{
			best_score = c;
			fbc_fe = (eDVBRegisteredFrontend *)*it;
		}

		/* disconnect link */
		disconnectLinkNoSimulate(link_fe);
	}

	return best_score;
}

void eFBCTunerManager::connectSortedLink(eDVBRegisteredFrontend *link_fe, eDVBRegisteredFrontend *top_fe, bool simulate)
{
	int link_fe_id = fe_slot_id(link_fe);
	int top_fe_id = fe_slot_id(top_fe);
	int prev_fe_id = link_fe_id - 1;

	if (prev_fe_id < 0)
		return;

	/* serach prev fe */
	eDVBRegisteredFrontend *next_fe = top_fe;
	long linked_next_ptr = -1;
	top_fe->m_frontend->getData(eDVBFrontend::LINKED_NEXT_PTR, linked_next_ptr);
	while(linked_next_ptr != -1)
	{
		next_fe = (eDVBRegisteredFrontend *)linked_next_ptr;
		next_fe->m_frontend->getData(eDVBFrontend::LINKED_NEXT_PTR, linked_next_ptr);
		if (fe_slot_id(next_fe) == prev_fe_id)
			break;
	}

	eDVBRegisteredFrontend *prev_fe = next_fe;

	/* get next fe */
	next_fe = getNext(prev_fe);	

	/* connect */
	if (next_fe)
	{
		int res = connectLink(link_fe, prev_fe, next_fe, simulate);
		if (res)
		{
			eDebug("[*][eFBCTunerManager::connectSortedLink] ERROR! connect link failed! (%d->%d->%d)", fe_slot_id(prev_fe), fe_slot_id(link_fe), fe_slot_id(next_fe));
			return;
		}
	}
	else
	{
		int res = connectLink(link_fe, prev_fe, simulate);
		if (res)
		{
			eDebug("[*][eFBCTunerManager::connectSortedLink] ERROR! connect link failed! (%d->%d)", fe_slot_id(prev_fe), fe_slot_id(link_fe));
			return;
		}
	}

	/* set proc fbc_id */
	setProcFBCID(link_fe_id, getFBCID(top_fe_id));

	/* add slot mask*/
	updateLNBSlotMask(link_fe_id, top_fe_id, false);
}

/* attach link_fe to tail of fe linked list */
void eFBCTunerManager::addLink(eDVBRegisteredFrontend *link_fe, eDVBRegisteredFrontend *top_fe, bool simulate)
{
	if (!isRootFe(top_fe))
		return;

	connectSortedLink(link_fe, top_fe, simulate);
}

/* if fe, fe_simulated is unused, unlink current frontend from linked things. */
/* all unused linked fbc fe must be unlinked! */
void eFBCTunerManager::unset(eDVBRegisteredFrontend *fe)
{
	bool simulate = fe->m_frontend->is_simulate();

	if (isRootFe(fe))
		return;

	if(checkUsed(fe, simulate))
		return;

	if(isUnicable(fe))
		return;

	eDVBRegisteredFrontend *linked_prev_fe = getPrev(fe);
	eDVBRegisteredFrontend *linked_next_fe = getNext(fe);

	if (!linked_prev_fe)
	{
		eDebug("[*][eFBCTunerManager::unset] ERROR! can not found prev linked frontend (fe_id : %d)", fe_slot_id(fe));
		return;
	}

	if (linked_next_fe)
	{
		int res = disconnectLink(fe, linked_prev_fe, linked_next_fe, simulate);
		if (res)
		{
			eDebug("[*][eFBCTunerManager::unset] ERROR! disconnect link failed! (%d->%d->%d)", fe_slot_id(linked_prev_fe), fe_slot_id(fe), fe_slot_id(linked_next_fe));
			return;
		}
	}
	else
	{
		int res = disconnectLink(fe, linked_prev_fe, simulate);
		if (res)
		{
			eDebug("[*][eFBCTunerManager::unset] ERROR! disconnect link failed! (%d->%d)", fe_slot_id(linked_prev_fe), fe_slot_id(fe));
			return;
		}
	}

	/* set proc fbc_id (skip) */

	/* remove slot mask*/
	updateLNBSlotMask(fe_slot_id(fe), fe_slot_id(linked_prev_fe), true);
}

bool eFBCTunerManager::canAllocateLink(eDVBRegisteredFrontend *fe, bool simulate)
{
	if (!isRootFe(fe))
		return false;

	if (isLinked(fe))
		return false;

	eSmartPtrList<eDVBRegisteredFrontend> &frontends = simulate ? m_res_mgr->m_simulate_frontend : m_res_mgr->m_frontend;
	for (eSmartPtrList<eDVBRegisteredFrontend>::iterator it(frontends.begin()); it != frontends.end(); ++it)
	{
		if (it->m_frontend->is_FBCTuner() && !isRootFe(*it) && isSameFbcSet(fe_slot_id(fe), fe_slot_id(it)) && !it->m_frontend->getEnabled() && !isLinked(*it))
			return true;
	}

	return false;
}

int eFBCTunerManager::updateLNBSlotMask(int dest_slot, int src_slot, bool remove)
{
	ePtr<eDVBSatelliteEquipmentControl> sec = eDVBSatelliteEquipmentControl::getInstance();

	int sec_lnbidx = sec->m_lnbidx;

	int found = 0;
	for (int idx=0; idx <= sec_lnbidx; ++idx )
	{
		eDVBSatelliteLNBParameters &lnb_param = sec->m_lnbs[idx];
		if ( lnb_param.m_slot_mask & (1 << src_slot) )
		{
			if (!remove)
				lnb_param.m_slot_mask |= (1 << dest_slot);
			else
				lnb_param.m_slot_mask &= ~(1 << dest_slot);

			found = 1;
		}
	}

	return 0;
}

int eFBCTunerManager::getLinkedSlotID(int fe_id)
{
	int link = -1;
	eSmartPtrList<eDVBRegisteredFrontend> &frontends = m_res_mgr->m_frontend;
	for (eSmartPtrList<eDVBRegisteredFrontend>::iterator it(frontends.begin()); it != frontends.end(); ++it)
	{
		if(it->m_frontend->getSlotID() == fe_id)
		{
			long prev_ptr = -1;
			it->m_frontend->getData(eDVBFrontend::LINKED_PREV_PTR, prev_ptr);
			if (prev_ptr != -1)
			{
				eDVBRegisteredFrontend *prev_fe = (eDVBRegisteredFrontend *)prev_ptr;
				link = fe_slot_id(prev_fe);
			}
			break;
		}
	}

	return link;
}
