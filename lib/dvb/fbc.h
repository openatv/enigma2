#ifndef __dvb_fbc_h
#define __dvb_fbc_h

/* FBC Manager */
#include <lib/base/ebase.h>
#include <lib/base/object.h>
#include <lib/base/eptrlist.h>
#include <lib/dvb/idvb.h>
#include <map>

class eDVBResourceManager;
class eDVBRegisteredFrontend;

typedef struct fbc_tuner
{
	int fbcSetID;
	int fbcIndex;
	bool isRoot;
	int initFbcId;
}FBC_TUNER;


class eFBCTunerManager: public iObject, public Object
{
private:
	DECLARE_REF(eFBCTunerManager);
	ePtr<eDVBResourceManager> m_res_mgr;
	static eFBCTunerManager *m_instance;
	std::map<int, FBC_TUNER> m_fbc_tuners;

	int setProcFBCID(int fe_id, int root_idx, bool is_linked);
	int feSlotID(const eDVBRegisteredFrontend *fe) const;
	bool isLinked(eDVBRegisteredFrontend *fe) const;
 	bool isUnicable(eDVBRegisteredFrontend *fe) const;
 	bool isFeUsed(eDVBRegisteredFrontend *fe, bool a_simulate) const;
	bool isSameFbcSet(int fe_id_a, int fe_id_b);
	bool isRootFe(eDVBRegisteredFrontend *fe);
	int getFBCID(int fe_id);
	int getDefaultFBCID(int fe_id);

	eDVBRegisteredFrontend *getPrev(eDVBRegisteredFrontend *fe) const;
	eDVBRegisteredFrontend *getNext(eDVBRegisteredFrontend *fe) const;
	eDVBRegisteredFrontend *getTop(eDVBRegisteredFrontend *fe) const;
	eDVBRegisteredFrontend *getLast(eDVBRegisteredFrontend *fe) const;
	eDVBRegisteredFrontend *getSimulFe(eDVBRegisteredFrontend *fe) const;

	void connectLink(eDVBRegisteredFrontend *link_fe, eDVBRegisteredFrontend *prev_fe, eDVBRegisteredFrontend *next_fe, bool simulate);
	void disconnectLink(eDVBRegisteredFrontend *link_fe, eDVBRegisteredFrontend *prev_fe, eDVBRegisteredFrontend *next_fe, bool simulate);
	int updateLNBSlotMask(int dest_slot, int src_slot, bool remove);
	void printLinks(eDVBRegisteredFrontend *fe) const;

public:
	static eFBCTunerManager* getInstance();
	eFBCTunerManager(ePtr<eDVBResourceManager> res_mgr);
	virtual ~eFBCTunerManager();
	void setDefaultFBCID(eDVBRegisteredFrontend *fe);
	void updateFBCID(eDVBRegisteredFrontend *next_fe, eDVBRegisteredFrontend *prev_fe);
	int isCompatibleWith(ePtr<iDVBFrontendParameters> &feparm, eDVBRegisteredFrontend *link_fe, eDVBRegisteredFrontend *&fbc_fe, bool simulate);
	void addLink(eDVBRegisteredFrontend *link_fe, eDVBRegisteredFrontend *top_fe, bool simulate);
	void unLink(eDVBRegisteredFrontend *link_fe);
	bool canLink(eDVBRegisteredFrontend *fe);
	int getLinkedSlotID(int feid) const;
	int getFBCSetID(int fe_id);
	bool isFBCLink(int fe_id);
};

#endif /* __dvb_fbc_h */

