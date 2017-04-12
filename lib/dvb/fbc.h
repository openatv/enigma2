#ifndef __dvb_fbc_h
#define __dvb_fbc_h

#include <lib/base/ebase.h>
#include <lib/base/object.h>
#include <lib/base/eptrlist.h>
#include <lib/dvb/idvb.h>

#include <map>
#include <bitset>

class eDVBResourceManager;
class eDVBFrontend;
class eDVBRegisteredFrontend;

class eFBCTunerManager: public iObject, public sigc::trackable
{
private:
	typedef std::bitset<8> connect_choices_t;

	typedef struct
	{
		int					set_id;
		bool				is_root;
		int					id;
		int					default_id;
		connect_choices_t	connect_choices;
	} tuner_t;

	typedef std::map<int, tuner_t> tuners_t;

	typedef enum
	{
		link_prev,
		link_next
	} link_ptr_t;

	DECLARE_REF(eFBCTunerManager);
	ePtr<eDVBResourceManager> m_res_mgr;
	static eFBCTunerManager* m_instance;
	tuners_t m_tuners;

	static int ReadProcInt(int, const std::string &);
	static void WriteProcInt(int, const std::string &, int);
	static void LoadConnectChoices(int, connect_choices_t &);
	static void SetProcFBCID(int, int, bool);
	static int FESlotID(eDVBRegisteredFrontend *);
	static bool IsLinked(eDVBRegisteredFrontend *);
	static bool IsSCR(eDVBRegisteredFrontend *);
	static eDVBRegisteredFrontend* FrontendGetLinkPtr(eDVBFrontend *, link_ptr_t);
	static eDVBRegisteredFrontend* FrontendGetLinkPtr(eDVBRegisteredFrontend *, link_ptr_t);
	static void FrontendSetLinkPtr(eDVBRegisteredFrontend *, link_ptr_t, eDVBRegisteredFrontend *);
	static eDVBRegisteredFrontend *GetFEPtr(long);
	static long GetFELink(eDVBRegisteredFrontend *ptr);
	static eDVBRegisteredFrontend *GetHead(eDVBRegisteredFrontend *);
	static eDVBRegisteredFrontend *GetTail(eDVBRegisteredFrontend *);
	static void UpdateLNBSlotMask(int, int, bool);

	bool IsFBCLink(int fe_id) const;
	bool IsSameFBCSet(int, int) const;
	bool IsRootFE(eDVBRegisteredFrontend *) const;
	bool IsFEUsed(eDVBRegisteredFrontend *, bool) const;
	int GetFBCID(int) const;
	int GetDefaultFBCID(int) const;

	eDVBRegisteredFrontend *GetSimulFE(eDVBRegisteredFrontend *) const;

	void ConnectLink(eDVBRegisteredFrontend *, eDVBRegisteredFrontend *, eDVBRegisteredFrontend *, bool) const;
	void DisconnectLink(eDVBRegisteredFrontend *, eDVBRegisteredFrontend *, eDVBRegisteredFrontend *, bool) const;

	void PrintLinks(eDVBRegisteredFrontend *fe) const;

public:
	static eFBCTunerManager* getInstance();
	eFBCTunerManager(ePtr<eDVBResourceManager> res_mgr);
	virtual ~eFBCTunerManager();

	int GetFBCSetID(int) const;
	int getLinkedSlotID(int feid) const;
	void SetDefaultFBCID(eDVBRegisteredFrontend *) const;
	void UpdateFBCID(eDVBRegisteredFrontend *, eDVBRegisteredFrontend *) const;
	int IsCompatibleWith(ePtr<iDVBFrontendParameters> &, eDVBRegisteredFrontend *, eDVBRegisteredFrontend *&, bool) const;
	bool CanLink(eDVBRegisteredFrontend *) const;
	void AddLink(eDVBRegisteredFrontend *, eDVBRegisteredFrontend *, bool) const;
	void Unlink(eDVBRegisteredFrontend *) const;
};

#endif
