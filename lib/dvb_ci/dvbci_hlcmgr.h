#ifndef __dvbci_dvbci_hlcmgr_h
#define __dvbci_dvbci_hlcmgr_h

#include <lib/dvb_ci/dvbci_session.h>

class eDVBCIHostLanguageAndCountrySession: public eDVBCISession
{
	enum {
		stateCountryEnquiry=statePrivate,
		stateLanguageEnquiry,
		stateFinal
	};

	static const std::map<std::string, std::string> m_languageMap;
	static std::map<std::string, std::string> createLanguageMap();

	int receivedAPDU(const unsigned char *tag, const void *data, int len);
	int doAction();
};

#endif
