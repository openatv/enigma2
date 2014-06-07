#ifndef __dvbci_dvbci_tc_h
#define __dvbci_dvbci_tc_h

#include <lib/base/ebase.h>
#include <lib/base/object.h>
#include <lib/dvb_ci/dvbci.h>

#define SLMS	256

class eDVBCISession
{
	DECLARE_REF(eDVBCISession);
	static ePtr<eDVBCISession> sessions[SLMS];
	static void createSession(eDVBCISlot *slot, const unsigned char *resource_identifier, unsigned char &status, ePtr<eDVBCISession> &ptr);
	static void sendSPDU(eDVBCISlot *slot, unsigned char tag,const void *data, int len, unsigned short session_nb, const void *apdu=0,int alen=0);
	static void sendOpenSessionResponse(eDVBCISlot *slot,unsigned char session_status, const unsigned char *resource_identifier,unsigned short session_nb);
	void recvCreateSessionResponse(const unsigned char *data);
	void recvCloseSessionRequest(const unsigned char *data);
protected:
	int state;
	int status;
	int action;
	eDVBCISlot *slot;		//base only
	unsigned short session_nb;
	virtual int receivedAPDU(const unsigned char *tag, const void *data, int len) = 0;
	void sendAPDU(const unsigned char *tag, const void *data=0,int len=0);
	void sendSPDU(unsigned char tag, const void *data, int len,const void *apdu=0, int alen=0);
	virtual int doAction()=0;
	void handleClose();
public:
	virtual ~eDVBCISession();

	static void deleteSessions(const eDVBCISlot *slot);

	int poll() { if (action) { action=doAction(); return 1; } return 0; }
	enum { stateInCreation, stateBusy, stateInDeletion, stateStarted, statePrivate};

	static int parseLengthField(const unsigned char *pkt, int &len);
	static int buildLengthField(unsigned char *pkt, int len);

	static void receiveData(eDVBCISlot *slot, const unsigned char *ptr, size_t len);

	int getState() { return state; }
	int getStatus() { return status; }

	static int pollAll();

};

#endif
