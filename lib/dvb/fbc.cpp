/* FBC Manager */
#include <lib/dvb/fbc.h>
#include <lib/dvb/dvb.h>
#include <lib/dvb/sec.h>
#include <lib/base/object.h>

#include <unistd.h>
#include <fcntl.h>

//#define FBC_DEBUG

#ifdef FBC_DEBUG
#define eFecDebug(arg...) eDebug(arg)
#else
#define eFecDebug(arg...)
#endif

static int getProcData(const char* filename)
{
	int res = -1;
	FILE *fp = fopen(filename,"r");
	if(fp)
	{
		fscanf(fp, "%d", &res);
		fclose(fp);
	}
	else
	{
		eFecDebug("[*][eFBCTunerManager::getProcData] open failed, %s: %m", filename);
	}
	return res;
}

static void setProcData(const char* filename, int value)
{
	eDebug("[*] setProcData %s -> %d", filename, value);
	FILE *fp = fopen(filename, "w");
	if(fp)
	{
		fprintf(fp, "%d", value);
		fclose(fp);
	}
	else
	{
		eFecDebug("[*][eFBCTunerManager::setProcData] open failed, %s: %m", filename);
	}
}

static void loadConnectChoices(const char* filename, bool *connect_choices)
{
	FILE *fp = fopen(filename,"r");
	if(fp)
	{
		int c;
		while(EOF != (c = fgetc(fp)))
		{
			if(isdigit(c))
				connect_choices[c - '0'] = true;
		}
		fclose(fp);
	}
	else
	{
		eFecDebug("[*][eFBCTunerManager::LoadFbcRootChoices] open failed, %s: %m", filename);
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
	if (!m_instance)
		m_instance = this;

	eSmartPtrList<eDVBRegisteredFrontend> &frontends = m_res_mgr->m_frontend;
	eSmartPtrList<eDVBRegisteredFrontend> &frontends_simulate = m_res_mgr->m_simulate_frontend;
	/* each FBC set has 8 tuners. */
	/* first set : 0, 1, 2, 3, 4, 5, 6, 7 */
	/* second set : 8, 9, 10, 11, 12, 13, 14, 15 */
	/* first, second frontend is top on a set */

	bool isRoot;
	int fe_id = -1;
	int fbcSetID = -2;
	int fbcIndex = 0;
	int initFbcId = -1;
	int prevFbcSetID = -1;
	char procFileName[128];
	std::string proc_fe;
	bool connect_choices[32] = {false};

	for (eSmartPtrList<eDVBRegisteredFrontend>::iterator it(frontends.begin()); it != frontends.end(); ++it)
	{
		// continue for DVB-C FBC Tuner
		if (!(it->m_frontend->supportsDeliverySystem(SYS_DVBS, false) || it->m_frontend->supportsDeliverySystem(SYS_DVBS2, false)))
			continue;

		fe_id = feSlotID(it);
		snprintf(procFileName, sizeof(procFileName), "/proc/stb/frontend/%d/fbc_set_id", fe_id);
		fbcSetID = getProcData(procFileName);
		if (fbcSetID != -1)
		{
			if (prevFbcSetID != fbcSetID)
			{
				prevFbcSetID = fbcSetID;
				memset(connect_choices, 0, sizeof(connect_choices));
				snprintf(procFileName, sizeof(procFileName), "/proc/stb/frontend/%d/fbc_connect_choices", fe_id);
				loadConnectChoices(procFileName, connect_choices);
				fbcIndex =0; // reset
			}

			isRoot = false;
			if (fbcIndex < sizeof(connect_choices)/sizeof(connect_choices[0]))
			{
				isRoot = connect_choices[fbcIndex];
			}

			initFbcId = isRoot ? fbcIndex : 0;

			FBC_TUNER elem = {fbcSetID, fbcIndex, isRoot, initFbcId};
			m_fbc_tuners[fe_id] = elem;

			/* set default fbc ID */
			setProcFBCID(fe_id, initFbcId, false);

			/* enable fbc tuner */
			it->m_frontend->setFBCTuner(true);

			fbcIndex++;
		}
	}

	for (eSmartPtrList<eDVBRegisteredFrontend>::iterator it(frontends_simulate.begin()); it != frontends_simulate.end(); ++it)
	{
		// continue for DVB-C FBC Tuner
		if (!(it->m_frontend->supportsDeliverySystem(SYS_DVBS, false) || it->m_frontend->supportsDeliverySystem(SYS_DVBS2, false)))
			continue;

		fe_id = feSlotID(it);
		snprintf(procFileName, sizeof(procFileName), "/proc/stb/frontend/%d/fbc_set_id", fe_id);
		fbcSetID = getProcData(procFileName);
		if (fbcSetID != -1)
		{
			/* enable fbc tuner */
			it->m_frontend->setFBCTuner(true);
		}
	}
}

eFBCTunerManager::~eFBCTunerManager()
{
	if (m_instance == this)
		m_instance = 0;
}

int eFBCTunerManager::setProcFBCID(int fe_id, int fbc_connect, bool is_linked)
{
	eFecDebug("[*][eFBCTunerManager::setProcFBCID] %d -> %d", fe_id, fbc_connect);
	char filename[128];

	/* set root */
	sprintf(filename, "/proc/stb/frontend/%d/fbc_connect", fe_id);
	setProcData(filename, fbc_connect);

	/* set linked */
	sprintf(filename, "/proc/stb/frontend/%d/fbc_link", fe_id);
	setProcData(filename, (int)is_linked);

	return 0;
}


int eFBCTunerManager::feSlotID(const eDVBRegisteredFrontend *fe) const
{
	return fe->m_frontend->getSlotID();
}

void eFBCTunerManager::setDefaultFBCID(eDVBRegisteredFrontend *fe)
{
	int fe_id = feSlotID(fe);
	setProcFBCID(fe_id, getDefaultFBCID(fe_id), isLinked(fe));
}

void eFBCTunerManager::updateFBCID(eDVBRegisteredFrontend *next_fe, eDVBRegisteredFrontend *prev_fe)
{
	setProcFBCID(feSlotID(next_fe), getFBCID(feSlotID(getTop(prev_fe))), isLinked(next_fe));
}

bool eFBCTunerManager::isLinked(eDVBRegisteredFrontend *fe) const
{
 
	long linked_prev_ptr = -1;
	fe->m_frontend->getData(eDVBFrontend::LINKED_PREV_PTR, linked_prev_ptr);
	return (linked_prev_ptr != -1);
}

bool eFBCTunerManager::isUnicable(eDVBRegisteredFrontend *fe) const
{
	int slot_idx = feSlotID(fe);
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

bool eFBCTunerManager::isFeUsed(eDVBRegisteredFrontend *fe, bool a_simulate) const
{
	if (fe->m_inuse > 0)
		return true;

	bool simulate = !a_simulate;

	eSmartPtrList<eDVBRegisteredFrontend> &frontends = simulate ? m_res_mgr->m_simulate_frontend : m_res_mgr->m_frontend;
	for (eSmartPtrList<eDVBRegisteredFrontend>::iterator it(frontends.begin()); it != frontends.end(); ++it)
	{
		if (feSlotID(it) == feSlotID(fe))
		{
			return (it->m_inuse >0);
		}
	}

	eDebug("[*][eFBCTunerManager::isFeUsed] ERROR! can not found fe ptr (feid : %d, simulate : %d)", feSlotID(fe), simulate);
	return false;
}

bool eFBCTunerManager::isSameFbcSet(int fe_a, int fe_b)
{
	return m_fbc_tuners[fe_a].fbcSetID == m_fbc_tuners[fe_b].fbcSetID;
}

bool eFBCTunerManager::isRootFe(eDVBRegisteredFrontend *fe)
{
	return m_fbc_tuners[feSlotID(fe)].isRoot;
}

int eFBCTunerManager::getFBCID(int fe_id)
{
	return m_fbc_tuners[fe_id].fbcIndex;
}

int eFBCTunerManager::getDefaultFBCID(int fe_id)
{
	return m_fbc_tuners[fe_id].initFbcId;
}

int eFBCTunerManager::getFBCSetID(int fe_id)
{
	return m_fbc_tuners[fe_id].fbcSetID;
}

eDVBRegisteredFrontend *eFBCTunerManager::getPrev(eDVBRegisteredFrontend *fe) const
{
	eDVBRegisteredFrontend *prev_fe = NULL;
	long linked_prev_ptr = -1;
	fe->m_frontend->getData(eDVBFrontend::LINKED_PREV_PTR, linked_prev_ptr);
	if (linked_prev_ptr != -1)
		prev_fe = (eDVBRegisteredFrontend *)linked_prev_ptr;
	return prev_fe;
}

eDVBRegisteredFrontend *eFBCTunerManager::getNext(eDVBRegisteredFrontend *fe) const
{
	eDVBRegisteredFrontend *next_fe = NULL;
	long linked_next_ptr = -1;
	fe->m_frontend->getData(eDVBFrontend::LINKED_NEXT_PTR, linked_next_ptr);
	if (linked_next_ptr != -1)
		next_fe = (eDVBRegisteredFrontend *)linked_next_ptr;
	return next_fe;
}

eDVBRegisteredFrontend *eFBCTunerManager::getTop(eDVBRegisteredFrontend *fe) const
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

eDVBRegisteredFrontend *eFBCTunerManager::getLast(eDVBRegisteredFrontend *fe) const
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

eDVBRegisteredFrontend *eFBCTunerManager::getSimulFe(eDVBRegisteredFrontend *fe) const
{
	eSmartPtrList<eDVBRegisteredFrontend> &frontends = m_res_mgr->m_simulate_frontend;

	for (eSmartPtrList<eDVBRegisteredFrontend>::iterator it(frontends.begin()); it != frontends.end(); it++)
		if (feSlotID(*it) == feSlotID(fe))
			return(*it);

	return((eDVBRegisteredFrontend *)0);
}

void eFBCTunerManager::connectLink(eDVBRegisteredFrontend *link_fe, eDVBRegisteredFrontend *prev_fe, eDVBRegisteredFrontend *next_fe, bool simulate)
{
	if (next_fe)
		eFecDebug("	[*][eFBCTunerManager::connectLink] connect %d->%d->%d %s", feSlotID(prev_fe), feSlotID(link_fe), feSlotID(next_fe), simulate?"(simulate)":"");
	else
		eFecDebug("	[*][eFBCTunerManager::connectLink] connect %d->%d %s", feSlotID(prev_fe), feSlotID(link_fe), simulate?"(simulate)":"");

	prev_fe->m_frontend->setData(eDVBFrontend::LINKED_NEXT_PTR, (long)link_fe);
	link_fe->m_frontend->setData(eDVBFrontend::LINKED_PREV_PTR, (long)prev_fe);
	if (next_fe)
	{
		link_fe->m_frontend->setData(eDVBFrontend::LINKED_NEXT_PTR, (long)next_fe);
		next_fe->m_frontend->setData(eDVBFrontend::LINKED_PREV_PTR, (long)link_fe);
	}
}

void eFBCTunerManager::disconnectLink(eDVBRegisteredFrontend *link_fe, eDVBRegisteredFrontend *prev_fe, eDVBRegisteredFrontend *next_fe, bool simulate)
{
	if (next_fe)
		eFecDebug("	[*][eFBCTunerManager::disconnectLink] disconnect %d->%d->%d %s", feSlotID(prev_fe), feSlotID(link_fe), feSlotID(next_fe), simulate?"(simulate)":"");
	else
		eFecDebug("	[*][eFBCTunerManager::disconnectLink] disconnect %d->%d %s", feSlotID(prev_fe), feSlotID(link_fe), simulate?"(simulate)":"");

	if (next_fe)
	{
		prev_fe->m_frontend->setData(eDVBFrontend::LINKED_NEXT_PTR, (long)next_fe);
		next_fe->m_frontend->setData(eDVBFrontend::LINKED_PREV_PTR, (long)prev_fe);

		link_fe->m_frontend->setData(eDVBFrontend::LINKED_PREV_PTR, (long)-1);
		link_fe->m_frontend->setData(eDVBFrontend::LINKED_NEXT_PTR, (long)-1);
	}
	else
	{
		prev_fe->m_frontend->setData(eDVBFrontend::LINKED_NEXT_PTR, (long)-1);
		link_fe->m_frontend->setData(eDVBFrontend::LINKED_PREV_PTR, (long)-1);
	}
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

		if(!isSameFbcSet(feSlotID(link_fe), feSlotID(it)))
			continue;

		if(it->m_inuse == 0) // No link to a fe not in use.
			continue;

		if(isLinked(*it)) // No link to a fe linked to another.
			continue;

		if(isUnicable(*it))
			continue;

		eDVBRegisteredFrontend *top_fe = *it;
		eDVBRegisteredFrontend *prev_fe = getLast(top_fe);

		/* connect link */
		connectLink(link_fe, prev_fe, NULL, simulate);

		/* enable linked fe */
		link_fe->m_frontend->setEnabled(true);

		/* add slot mask*/
		updateLNBSlotMask(feSlotID(link_fe), feSlotID(*it), false);

		/* get score */
		int c = link_fe->m_frontend->isCompatibleWith(feparm);
		if (c > best_score)
		{
			best_score = c;
			fbc_fe = (eDVBRegisteredFrontend *)*it;
		}

		eFecDebug("[*][eFBCTunerManager::isCompatibleWith] score : %d (%d->%d)", c, feSlotID(it), feSlotID(link_fe));

		ASSERT(!getNext(link_fe));
		ASSERT(getPrev(link_fe));
		ASSERT(getLast(top_fe) == link_fe);

		/* disconnect link */
		disconnectLink(link_fe, prev_fe, NULL, simulate);

		/* disable linked fe */
		link_fe->m_frontend->setEnabled(false);

		/* remove slot mask*/
		updateLNBSlotMask(feSlotID(link_fe), feSlotID(top_fe), true);
	}

	eFecDebug("[*][eFBCTunerManager::isCompatibleWith] fe : %p(%d), score : %d %s", link_fe, feSlotID(link_fe), best_score, simulate?"(simulate)":"");

	return best_score;
}

/* attach link_fe to tail of fe linked list */
void eFBCTunerManager::addLink(eDVBRegisteredFrontend *link_fe, eDVBRegisteredFrontend *top_fe, bool simulate)
{
	//printLinks(link_fe);

	eFecDebug("	[*][eFBCTunerManager::addLink] addLink : %p(%d)->%p(%d) %s", top_fe, feSlotID(top_fe), link_fe, feSlotID(link_fe), simulate?"(simulate)":"");

	eDVBRegisteredFrontend *next_fe = NULL;
	eDVBRegisteredFrontend *prev_fe = NULL;

	if(isRootFe(link_fe) || !isRootFe(top_fe))
		return;

	/* search prev/next fe */
	next_fe = top_fe;
	while(true)
	{
		prev_fe = next_fe;
		next_fe = getNext(prev_fe);
		if ((next_fe == NULL) || (feSlotID(next_fe) > feSlotID(link_fe)))
			break;
	}

	/* connect */
	connectLink(link_fe, prev_fe, next_fe, simulate);

	/* enable linked fe */
	link_fe->m_frontend->setEnabled(true);

	/* simulate connect */
	if (!simulate)
	{
		eDVBRegisteredFrontend *simulate_prev_fe = NULL;
		eDVBRegisteredFrontend *simulate_link_fe = NULL;
		eDVBRegisteredFrontend *simulate_next_fe = NULL;

		simulate_prev_fe = getSimulFe(prev_fe);
		simulate_link_fe = getSimulFe(link_fe);

		if (next_fe) 
			simulate_next_fe = getSimulFe(next_fe);

		eFecDebug("	[*][eFBCTunerManager::addLink] simulate fe : %p -> %p -> %p", simulate_prev_fe, simulate_link_fe, simulate_next_fe);

		connectLink(simulate_link_fe, simulate_prev_fe, simulate_next_fe, !simulate);

		/* enable simulate linked fe */
		simulate_link_fe->m_frontend->setEnabled(true);
	}

	/* set proc fbc_id */
	if (!simulate)
		setProcFBCID(feSlotID(link_fe), getFBCID(feSlotID(top_fe)), isLinked(link_fe));

	/* add slot mask*/
	updateLNBSlotMask(feSlotID(link_fe), feSlotID(top_fe), false);

	//printLinks(link_fe);
}

/* if fe, fe_simulated is unused, unlink current frontend from linked things. */
/* all unused linked fbc fe must be unlinked! */
void eFBCTunerManager::unLink(eDVBRegisteredFrontend *link_fe)
{
	bool simulate = link_fe->m_frontend->is_simulate();
	eFecDebug("	[*][eFBCTunerManager::unLink] fe id : %p(%d) %s", link_fe, feSlotID(link_fe), simulate?"(simulate)":"");

	if (isRootFe(link_fe) || isFeUsed(link_fe, simulate) || isUnicable(link_fe) || !isLinked(link_fe))
	{
		eFecDebug("	[*][eFBCTunerManager::unLink] skip..");
		return;
	}

	//printLinks(link_fe);

	eDVBRegisteredFrontend *prev_fe = getPrev(link_fe);
	eDVBRegisteredFrontend *next_fe = getNext(link_fe);

	ASSERT(prev_fe);

	disconnectLink(link_fe, prev_fe, next_fe, simulate);

	/* disable linked fe */
	link_fe->m_frontend->setEnabled(false);

	/* simulate disconnect */
	if (!simulate)
	{
		eDVBRegisteredFrontend *simulate_prev_fe = NULL;
		eDVBRegisteredFrontend *simulate_link_fe = NULL;
		eDVBRegisteredFrontend *simulate_next_fe = NULL;

		simulate_prev_fe = getSimulFe(prev_fe);
		simulate_link_fe = getSimulFe(link_fe);

		if (next_fe) 
			simulate_next_fe = getSimulFe(next_fe);

		disconnectLink(simulate_link_fe, simulate_prev_fe, simulate_next_fe, !simulate);

		/* enable simulate linked fe */
		simulate_link_fe->m_frontend->setEnabled(false);
	}

	/* set default proc fbc_id */
	//setDefaultFBCID(link_fe);

	/* remove slot mask*/
	updateLNBSlotMask(feSlotID(link_fe), feSlotID(getTop(prev_fe)), true);

	//printLinks(link_fe);
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
			eFecDebug("[*][eFBCTunerManager::updateLNBSlotMask] m_slot_mask : %d", lnb_param.m_slot_mask);

			if (!remove)
				lnb_param.m_slot_mask |= (1 << dest_slot);
			else
				lnb_param.m_slot_mask &= ~(1 << dest_slot);

			eFecDebug("[*][eFBCTunerManager::updateLNBSlotMask] changed m_slot_mask : %d", lnb_param.m_slot_mask);
			found = 1;
		}
	}

	if (!found)
		eFecDebug("[*][eFBCTunerManager::updateLNBSlotMask] src %d not found", src_slot);

	return 0;
}

bool eFBCTunerManager::canLink(eDVBRegisteredFrontend *fe)
{
	return !(isRootFe(fe) || getPrev(fe) || getNext(fe) || isUnicable(fe));
}

int eFBCTunerManager::getLinkedSlotID(int fe_id) const
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
				link = feSlotID(prev_fe);
			}
			break;
		}
	}

	eFecDebug(" [*][eFBCTunerManager::getLinkedSlotID] fe_id : %d, link : %d", fe_id, link);

	return link;
}

bool eFBCTunerManager::isFBCLink(int fe_id)
{
	bool res = false;
	std::map<int, FBC_TUNER>::iterator it = m_fbc_tuners.find(fe_id);
	if (it != m_fbc_tuners.end())
	{
		res = !it->second.isRoot;
	}
	return res;
}

void eFBCTunerManager::printLinks(eDVBRegisteredFrontend *fe) const
{
	long linked_prev_ptr = -1;
	eDVBRegisteredFrontend *linked_prev_fe = fe;
	fe->m_frontend->getData(eDVBFrontend::LINKED_PREV_PTR, linked_prev_ptr);
	while (linked_prev_ptr != -1)
	{
		linked_prev_fe = (eDVBRegisteredFrontend*) linked_prev_ptr;
		linked_prev_fe->m_frontend->getData(eDVBFrontend::LINKED_PREV_PTR, (long&)linked_prev_ptr);
	}

	long linked_next_ptr = -1;
	eDVBRegisteredFrontend *linked_next_fe = linked_prev_fe;
	eFecDebug("	[*][eFBCTunerManager::printLinks] fe id : %d (%p), inuse : %d, enabled : %d, fbc : %d", feSlotID(linked_next_fe), linked_next_fe, linked_next_fe->m_inuse, linked_next_fe->m_frontend->getEnabled(), linked_next_fe->m_frontend->is_FBCTuner());
	linked_prev_fe->m_frontend->getData(eDVBFrontend::LINKED_NEXT_PTR, linked_next_ptr);
	while (linked_next_ptr != -1)
	{
		linked_next_fe = (eDVBRegisteredFrontend*) linked_next_ptr;
		eFecDebug("	[*][eFBCTunerManager::printLinks] fe id : %d (%p), inuse : %d, enabled : %d, fbc : %d", feSlotID(linked_next_fe), linked_next_fe, linked_next_fe->m_inuse, linked_next_fe->m_frontend->getEnabled(), linked_next_fe->m_frontend->is_FBCTuner());
		linked_next_fe->m_frontend->getData(eDVBFrontend::LINKED_NEXT_PTR, (long&)linked_next_ptr);
	}

	eSmartPtrList<eDVBRegisteredFrontend> &frontends = m_res_mgr->m_frontend;
	for (eSmartPtrList<eDVBRegisteredFrontend>::iterator it(frontends.begin()); it != frontends.end(); ++it)
	{
		int prev = -1;
		int next = -1;
		long prev_ptr = -1;
		long next_ptr = -1;
		it->m_frontend->getData(eDVBFrontend::LINKED_PREV_PTR, prev_ptr);
		it->m_frontend->getData(eDVBFrontend::LINKED_NEXT_PTR, next_ptr);
		if (prev_ptr != -1)
		{
			eDVBRegisteredFrontend *prev_fe = (eDVBRegisteredFrontend *)prev_ptr;
			prev = feSlotID(prev_fe);
		}

		if (next_ptr != -1)
		{
			eDVBRegisteredFrontend *next_fe = (eDVBRegisteredFrontend *)next_ptr;
			next = feSlotID(next_fe);
		}
		
		eFecDebug("	[*][eFBCTunerManager::printLinks] fe_id : %2d, inuse : %d, enabled : %d, fbc : %d, prev : %2d, cur : %2d, next : %2d", feSlotID(it), it->m_inuse, it->m_frontend->getEnabled(), it->m_frontend->is_FBCTuner(), prev, feSlotID(it), next);
	}

	eSmartPtrList<eDVBRegisteredFrontend> &simulate_frontends = m_res_mgr->m_simulate_frontend;
	for (eSmartPtrList<eDVBRegisteredFrontend>::iterator it(simulate_frontends.begin()); it != simulate_frontends.end(); ++it)
	{
		int prev = -1;
		int next = -1;
		long prev_ptr = -1;
		long next_ptr = -1;
		it->m_frontend->getData(eDVBFrontend::LINKED_PREV_PTR, prev_ptr);
		it->m_frontend->getData(eDVBFrontend::LINKED_NEXT_PTR, next_ptr);
		if (prev_ptr != -1)
		{
			eDVBRegisteredFrontend *prev_fe = (eDVBRegisteredFrontend *)prev_ptr;
			prev = feSlotID(prev_fe);
		}

		if (next_ptr != -1)
		{
			eDVBRegisteredFrontend *next_fe = (eDVBRegisteredFrontend *)next_ptr;
			next = feSlotID(next_fe);
		}
		
		eFecDebug("	[*][eFBCTunerManager::printLinks] fe_id : %2d, inuse : %d, enabled : %d, fbc : %d, prev : %2d, cur : %2d, next : %2d (simulate)", feSlotID(it), it->m_inuse, it->m_frontend->getEnabled(), it->m_frontend->is_FBCTuner(), prev, feSlotID(it), next);
	}
}

