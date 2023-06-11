#ifndef __dvb_fbc_h
#define __dvb_fbc_h

/* FBC Manager */
#include <lib/base/ebase.h>
#include <lib/base/object.h>
#include <lib/base/eptrlist.h>
#include <lib/dvb/idvb.h>
#include <map>

class eDVBResourceManager;
class eDVBFrontend;
class eDVBRegisteredFrontend;

typedef struct fbc_tuner
{
	int fbcSetID;
	unsigned int fbcIndex;
	bool isRoot;
	int initFbcId;
}FBC_TUNER;


class eFBCTunerManager: public iObject, public sigc::trackable
{
private:
	typedef enum
	{
		link_prev,
		link_next
	} link_ptr_t;

	DECLARE_REF(eFBCTunerManager);
	ePtr<eDVBResourceManager> m_res_mgr;
	static eFBCTunerManager *m_instance;
	std::map<int, FBC_TUNER> m_fbc_tuners;

	void SetProcFBCID(int fe_id, int root_idx, bool is_linked);
	int FESlotID(const eDVBRegisteredFrontend *fe) const;
	bool IsLinked(eDVBRegisteredFrontend *fe) const;
 	bool isUnicable(eDVBRegisteredFrontend *fe) const;
	static eDVBRegisteredFrontend* FrontendGetLinkPtr(eDVBFrontend *, link_ptr_t);
	static eDVBRegisteredFrontend* FrontendGetLinkPtr(eDVBRegisteredFrontend *, link_ptr_t);
	static void FrontendSetLinkPtr(eDVBRegisteredFrontend *, link_ptr_t, eDVBRegisteredFrontend *);
	static eDVBRegisteredFrontend *GetFEPtr(long);
	static long GetFELink(eDVBRegisteredFrontend *ptr);
 	bool IsFEUsed(eDVBRegisteredFrontend *fe, bool a_simulate) const;
	bool IsSameFBCSet(int fe_id_a, int fe_id_b);
	bool IsRootFE(eDVBRegisteredFrontend *fe);
	int GetFBCID(int fe_id);
	int GetDefaultFBCID(int fe_id);

	eDVBRegisteredFrontend *getPrev(eDVBRegisteredFrontend *fe) const;
	eDVBRegisteredFrontend *getNext(eDVBRegisteredFrontend *fe) const;
	eDVBRegisteredFrontend *GetHead(eDVBRegisteredFrontend *fe) const;
	eDVBRegisteredFrontend *GetTail(eDVBRegisteredFrontend *fe) const;
	eDVBRegisteredFrontend *GetSimulFE(eDVBRegisteredFrontend *fe) const;

	void ConnectLink(eDVBRegisteredFrontend *link_fe, eDVBRegisteredFrontend *prev_fe, eDVBRegisteredFrontend *next_fe, bool simulate) const;
	void DisconnectLink(eDVBRegisteredFrontend *link_fe, eDVBRegisteredFrontend *prev_fe, eDVBRegisteredFrontend *next_fe, bool simulate) const;
	int UpdateLNBSlotMask(int dest_slot, int src_slot, bool remove);
	void PrintLinks(eDVBRegisteredFrontend *fe) const;

public:
	static eFBCTunerManager* getInstance();
	eFBCTunerManager(ePtr<eDVBResourceManager> res_mgr);
	virtual ~eFBCTunerManager();
	void SetDefaultFBCID(eDVBRegisteredFrontend *fe);
	void UpdateFBCID(eDVBRegisteredFrontend *next_fe, eDVBRegisteredFrontend *prev_fe);
	int IsCompatibleWith(ePtr<iDVBFrontendParameters> &feparm, eDVBRegisteredFrontend *link_fe, eDVBRegisteredFrontend *&fbc_fe, bool simulate);
	void AddLink(eDVBRegisteredFrontend *link_fe, eDVBRegisteredFrontend *top_fe, bool simulate);
	void Unlink(eDVBRegisteredFrontend *link_fe);
	bool CanLink(eDVBRegisteredFrontend *fe);
	int getLinkedSlotID(int feid) const;
	int getFBCSetID(int fe_id);
	bool IsFBCLink(int fe_id);
};

#endif /* __dvb_fbc_h */

