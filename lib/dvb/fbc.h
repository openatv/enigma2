#ifndef __dvb_fbc_h
#define __dvb_fbc_h

/* FBC Manager */
#include <lib/base/ebase.h>
#include <lib/base/object.h>
#include <lib/base/eptrlist.h>
#include <lib/dvb/idvb.h>

class eDVBResourceManager;
class eDVBRegisteredFrontend;

class eFBCTunerManager: public iObject, public Object
{
private:
	DECLARE_REF(eFBCTunerManager);
	ePtr<eDVBResourceManager> m_res_mgr;
	int m_fbc_tuner_num;
	static bool isDestroyed;

	int getFBCTunerNum();
	void procInit();
	bool isSameFbcSet(int a, int b);
	bool isSupportDVBS(eDVBRegisteredFrontend *fe);
	int getFBCID(int root_fe_id);

	eDVBRegisteredFrontend *getPrev(eDVBRegisteredFrontend *fe);
	eDVBRegisteredFrontend *getNext(eDVBRegisteredFrontend *fe);
	eDVBRegisteredFrontend *getTop(eDVBRegisteredFrontend *fe);
	eDVBRegisteredFrontend *getLast(eDVBRegisteredFrontend *fe);
	bool isLinked(eDVBRegisteredFrontend *fe);
	bool isLinkedByIndex(int fe_idx);
	bool checkTop(eDVBRegisteredFrontend *fe);
	int connectLinkByIndex(int link_fe_index, int prev_fe_index, int next_fe_index, bool simulate);
	int connectLinkByIndex(int link_fe_index, int prev_fe_index, bool simulate);
	int disconnectLinkByIndex(int link_fe_index, int prev_fe_index, int next_fe_index, bool simulate);
	int disconnectLinkByIndex(int link_fe_index, int prev_fe_index, bool simulate);
	int connectLink(eDVBRegisteredFrontend *link_fe, eDVBRegisteredFrontend *prev_fe, eDVBRegisteredFrontend *next_fe, bool simulate);
	int connectLink(eDVBRegisteredFrontend *link_fe, eDVBRegisteredFrontend *prev_fe, bool simulate);
	int disconnectLink(eDVBRegisteredFrontend *link_fe, eDVBRegisteredFrontend *prev_fe, eDVBRegisteredFrontend *next_fe, bool simulate);
	int disconnectLink(eDVBRegisteredFrontend *linkable_fe, eDVBRegisteredFrontend *top_fe, bool simulate);
	void connectLinkNoSimulate(eDVBRegisteredFrontend *link_fe, eDVBRegisteredFrontend *top_fe);
	void disconnectLinkNoSimulate(eDVBRegisteredFrontend *link_fe);

	bool checkUsed(eDVBRegisteredFrontend *fe, bool a_simulate);
	void connectSortedLink(eDVBRegisteredFrontend *link_fe, eDVBRegisteredFrontend *top_fe, bool simulate);
	int updateLNBSlotMask(int dest_slot, int src_slot, bool remove);
	void printLinks(eDVBRegisteredFrontend *fe);

public:
	eFBCTunerManager();
	virtual ~eFBCTunerManager();
	int setProcFBCID(int fe_id, int fbc_id);
	int setDefaultFBCID(eDVBRegisteredFrontend *fe);
	void updateFBCID(eDVBRegisteredFrontend *next_fe, eDVBRegisteredFrontend *prev_fe);
	bool isRootFeSlot(int fe_slot_id);
	bool isRootFe(eDVBRegisteredFrontend *fe);
	bool canLink(eDVBRegisteredFrontend *fe);
	bool isUnicable(eDVBRegisteredFrontend *fe);
	int isCompatibleWith(ePtr<iDVBFrontendParameters> &feparm, eDVBRegisteredFrontend *link_fe, bool simulate);
	int isCompatibleWith(ePtr<iDVBFrontendParameters> &feparm, eDVBRegisteredFrontend *link_fe, eDVBRegisteredFrontend *&fbc_fe, bool simulate);
	void addLink(eDVBRegisteredFrontend *link_fe, eDVBRegisteredFrontend *top_fe, bool simulate);
	void unset(eDVBRegisteredFrontend *fe);
	bool canAllocateLink(eDVBRegisteredFrontend *fe, bool simulate);

	static eFBCTunerManager* getInstance()
	{
		if (isDestroyed == true)
		{
			eDebug("eFBCTunerManager is already destroyed!");
			return 0;
		}
		static eFBCTunerManager instance;
		return &instance;
	}

	int getLinkedSlotID(int feid);
};

#endif /* __dvb_fbc_h */