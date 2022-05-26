#ifndef __dvb_fcc_h
#define __dvb_fcc_h

#include <lib/dvb/idvb.h>
#include <lib/base/object.h>
#include <lib/service/iservice.h>
#include <connection.h>

class eNavigation;

class FCCServiceChannels
{
private:
	std::map<eDVBChannelID, int> m_fcc_chids;

public:
	void addFCCService(const eServiceReference &service);
	void removeFCCService(const eServiceReference &service);
	int getFCCChannelID(std::map<eDVBChannelID, int> &fcc_chids);
};

typedef struct _tagFccElem
{
	eServiceReference m_service_reference;
	ePtr<eConnection> m_service_event_conn;
	int m_state;
	bool m_useNormalDecode;
}FCCServiceElem;

class eFCCServiceManager: public iObject, public sigc::trackable
{
	DECLARE_REF(eFCCServiceManager);
private:
	eNavigation *m_core;
	static eFCCServiceManager* m_instance;
	std::map<ePtr<iPlayableService>, FCCServiceElem, std::less<iPlayableService*> > m_FCCServices;
	FCCServiceChannels m_fccServiceChannels;

	bool m_fcc_enable;

	void FCCEvent(iPlayableService* service, int event);
public:
	PSignal1<void, int> m_fcc_event;
	static eFCCServiceManager* getInstance();
	eFCCServiceManager(eNavigation *navptr);
	~eFCCServiceManager();

	enum
	{
		fcc_state_preparing,
		fcc_state_decoding,
		fcc_state_failed
	};
	SWIG_VOID(RESULT)  playFCCService(const eServiceReference &ref, ePtr<iPlayableService> &SWIG_OUTPUT);
	RESULT stopFCCService(const eServiceReference &sref);
	RESULT stopFCCService();
	RESULT cleanupFCCService();
	RESULT tryFCCService(const eServiceReference &service, ePtr<iPlayableService> &ptr);
	PyObject *getFCCServiceList();
	void printFCCServices();
	int isLocked(ePtr<iPlayableService> service);
	static int getFCCChannelID(std::map<eDVBChannelID, int> &fcc_chids);
	static bool checkAvailable(const eServiceReference &ref);
	void setFCCEnable(int enable) { m_fcc_enable = (enable != 0); }
	bool isEnable() { return m_fcc_enable; }
	bool isStateDecoding(iPlayableService* service);
	void setNormalDecoding(iPlayableService* service);
};

#endif /* __dvb_fcc_h */
