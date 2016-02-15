#ifndef __dvb_fbc_h
#define __dvb_fbc_h

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

	bool isSameFbcSet(int a, int b);
	int getFBCID(int root_fe_id);

	long frontend_get_linkptr(const eDVBRegisteredFrontend *fe, link_ptr_t link_type) const;
	void frontend_set_linkptr(const eDVBRegisteredFrontend *fe, link_ptr_t link_type, long data) const;
	int fe_slot_id(const eDVBRegisteredFrontend *fe) const;

	eDVBRegisteredFrontend *GetFEPtr(long link);
	eDVBRegisteredFrontend *GetHead(eDVBRegisteredFrontend *fe);
	eDVBRegisteredFrontend *GetTail(eDVBRegisteredFrontend *fe);
	eDVBRegisteredFrontend *getSimulFe(eDVBRegisteredFrontend *fe);
	bool isLinked(eDVBRegisteredFrontend *fe);
	bool isLinkedByIndex(int fe_idx);

	bool checkUsed(eDVBRegisteredFrontend *fe, bool a_simulate);
	void updateLNBSlotMask(int dest_slot, int src_slot, bool remove);

	void list_loop_links(void);

public:
	eFBCTunerManager(ePtr<eDVBResourceManager> res_mgr);
	virtual ~eFBCTunerManager();
	void setProcFBCID(int fe_id, int fbc_id);
	void setDefaultFBCID(eDVBRegisteredFrontend *fe);
	void updateFBCID(eDVBRegisteredFrontend *next_fe, eDVBRegisteredFrontend *prev_fe);
	bool isRootFe(eDVBRegisteredFrontend *fe);
	bool canLink(eDVBRegisteredFrontend *fe);
	bool isUnicable(eDVBRegisteredFrontend *fe);
	int isCompatibleWith(ePtr<iDVBFrontendParameters> &feparm, eDVBRegisteredFrontend *link_fe, eDVBRegisteredFrontend *&fbc_fe, bool simulate);
	void addLink(eDVBRegisteredFrontend *link_fe, eDVBRegisteredFrontend *top_fe, bool simulate);
	void unlink(eDVBRegisteredFrontend *fe);
	int getLinkedSlotID(int feid);

	static eFBCTunerManager* getInstance();
};

#endif /* __dvb_fbc_h */
