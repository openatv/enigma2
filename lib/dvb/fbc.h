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
	typedef enum
	{
		link_prev,
		link_next
	} link_ptr_t;

	DECLARE_REF(eFBCTunerManager);
	ePtr<eDVBResourceManager> m_res_mgr;
	int m_fbc_tuner_num;
	static eFBCTunerManager* m_instance;
	static const int FBC_TUNER_SET = 8;

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

	int fe_slot_id(const eDVBRegisteredFrontend *fe) const;

	long frontend_get_linkptr(const eDVBRegisteredFrontend *fe, link_ptr_t link_type) const;
	void frontend_set_linkptr(const eDVBRegisteredFrontend *fe, link_ptr_t link_type, long data) const;

public:
	eFBCTunerManager(ePtr<eDVBResourceManager> res_mgr);
	virtual ~eFBCTunerManager();
	void setProcFBCID(int fe_id, int fbc_id);
	void setDefaultFBCID(eDVBRegisteredFrontend *fe);
	void updateFBCID(eDVBRegisteredFrontend *next_fe, eDVBRegisteredFrontend *prev_fe);
	bool isRootFeSlot(int fe_slot_id);
	bool isRootFe(eDVBRegisteredFrontend *fe);
	bool canLink(eDVBRegisteredFrontend *fe);
	bool isUnicable(eDVBRegisteredFrontend *fe);
	int isCompatibleWith(ePtr<iDVBFrontendParameters> &feparm, eDVBRegisteredFrontend *link_fe, bool simulate);
	int isCompatibleWith(ePtr<iDVBFrontendParameters> &feparm, eDVBRegisteredFrontend *link_fe, eDVBRegisteredFrontend *&fbc_fe, bool simulate);
	void addLink(eDVBRegisteredFrontend *link_fe, eDVBRegisteredFrontend *top_fe, bool simulate);
	void unset(eDVBRegisteredFrontend *fe);
	int getLinkedSlotID(int feid);

	static eFBCTunerManager* getInstance();
};

#endif /* __dvb_fbc_h */
