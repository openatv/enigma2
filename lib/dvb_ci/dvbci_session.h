#ifndef __dvbci_dvbci_tc_h
#define __dvbci_dvbci_tc_h

#include <lib/base/ebase.h>
#include <lib/dvb_ci/dvbci.h>

#define SLMS	256

class eDVBCISession
{
	static eDVBCISession *sessions[SLMS];
	static eDVBCISession *eDVBCISession::createSession(eDVBCISlot *slot, const unsigned char *resource_identifier, unsigned char &status);
	void eDVBCISession::sendSPDU(eDVBCISlot *slot, unsigned char tag,const void *data, int len, unsigned short session_nb, const void *apdu=0,int alen=0);
	void sendOpenSessionResponse(eDVBCISlot *slot,unsigned char session_status, const unsigned char *resource_identifier,unsigned short session_nb);
protected:
	int state;
	int status;
	int action;
	eDVBCISlot *slot;		//base only
	unsigned short session_nb;
public:
	eDVBCISession(eDVBCISlot *cislot);
	~eDVBCISession();

	enum { stateInCreation, stateBusy, stateInDeletion, stateStarted, statePrivate};
	
	int parseLengthField(const unsigned char *pkt, int &len);
	int buildLengthField(unsigned char *pkt, int len);

	void receiveData(const unsigned char *ptr, size_t len);
	
	int getState() { return state; }
	int getStatus() { return status; }
};

#endif
