#ifndef __DVB_CAHANDLER_H_
#define __DVB_CAHANDLER_H_

#include <lib/python/connections.h>

#ifndef SWIG

#include <lib/network/serversocket.h>
#include <dvbsi++/program_map_section.h>
#include <lib/base/eptrlist.h>
#include <lib/dvb/idvb.h>
#include <lib/dvb/esection.h>

/*
 * eDVBCAHandler provides external clients with CAPMT objects
 *
 * The traditional way of receiving this information was by providing a listening
 * socket on /tmp/camd.socket.
 * For every channel change, a connection will be opened, and a CAPMT object is transmitted.
 *
 * This has a few disadvantages:
 * 1. a new connection has to be opened for each channel change
 * 2. only one external client can receive CAPMT objects
 * 3. when the client restarts, it has no way of requesting the DVBCAHandler
 * to reconnect
 *
 * To overcome these disadvantages, a new method has been added;
 * eDVBCAHandler now also provides a serversocket on "/tmp/.listen.camd.socket".
 * Clients can connect to this socket, and receive CAPMT objects as channel
 * changes occur. The socket should be left open.
 * Clients should check the ca_pmt_list_management field in the CAPMT objects, to
 * determine whether an object is the first or last object in the list, an object in the middle,
 * or perhaps an update for an existing service.
 *
 * the DVBCAHandler will immediately (re)transmit the current list of CAPMT objects when
 * the client (re)connects.
 *
 */

/* CAPMT client sockets */
#define PMT_SERVER_SOCKET "/tmp/.listen.camd.socket"
#define PMT_CLIENT_SOCKET "/tmp/camd.socket"

 /* ca_pmt_list_management values: */

#define LIST_MORE 0x00
												/* CA application should append a 'MORE' CAPMT object the list,
												 * and start receiving the next object
												 */
#define LIST_FIRST 0x01
												/* CA application should clear the list when a 'FIRST' CAPMT object
												 * is received, and start receiving the next object
												 */
#define LIST_LAST 0x02
												/* CA application should append a 'LAST' CAPMT object to the list,
												 * and start working with the list
												 */
#define LIST_ONLY 0x03
												/* CA application should clear the list when an 'ONLY' CAPMT object
												 * is received, and start working with the object
												 */
#define LIST_ADD 0x04
												/* CA application should append an 'ADD' CAPMT object to the current list,
												 * and start working with the updated list
												 */
#define LIST_UPDATE 0x05
												/* CA application should replace an entry in the list with an
												 * 'UPDATE' CAPMT object, and start working with the updated list
												 */

/* ca_pmt_cmd_id's: */
#define CMD_OK_DESCRAMBLING 0x01
												/* CA application should start descrambling the service in this CAPMT object,
												 * as soon as the list of CAPMT objects is complete
												 */
#define CMD_OK_MMI					0x02
#define CMD_QUERY						0x03
#define CMD_NOT_SELECTED		0x04
												/* CA application should stop descrambling this service
												 * (used when the last service in a list has left, note
												 * that there is no CI definition to send an empty list)
												 */

class eDVBCAHandler;

class ePMTClient : public eUnixDomainSocket
{
	unsigned char receivedTag[4];
	int receivedLength;
	unsigned char *receivedValue;
	char *displayText;
protected:
	eDVBCAHandler *parent;
	void connectionLost();
	void dataAvailable();
	void clientTLVReceived(unsigned char *tag, int length, unsigned char *value);
	void parseTLVObjects(unsigned char *data, int size);
public:
	ePMTClient(eDVBCAHandler *handler, int socket);
};

class eDVBCAService: public eUnixDomainSocket
{
	eServiceReferenceDVB m_service;
	uint8_t m_used_demux[8];
	uint8_t m_adapter;
	uint32_t m_service_type_mask;
	uint64_t m_prev_build_hash;
	uint32_t m_crc32;
	int m_version;
	unsigned char m_capmt[2048];
	ePtr<eTimer> m_retryTimer;
public:
	eDVBCAService(const eServiceReferenceDVB &service);
	~eDVBCAService();

	std::string toString();
	int getCAPMTVersion();
	int getNumberOfDemuxes();
	uint8_t getUsedDemux(int index);
	void setUsedDemux(int index, uint8_t value);
	uint8_t getAdapter();
	void setAdapter(uint8_t value);
	void addServiceType(int type);
	void sendCAPMT();
	int writeCAPMTObject(eSocket *socket, int list_management = -1);
	int buildCAPMT(eTable<ProgramMapSection> *ptr);
	void connectionLost();
};

typedef std::map<eServiceReferenceDVB, eDVBCAService*> CAServiceMap;

#endif

SWIG_IGNORE(iCryptoInfo);
class iCryptoInfo : public iObject
{
public:
#ifdef SWIG
	iCryptoInfo();
	~iCryptoInfo();
#endif
	PSignal1<void, const char*> clientname;
	PSignal1<void, const char*> clientinfo;
	PSignal1<void, const char*> verboseinfo;
	PSignal1<void, int> usedcaid;
	PSignal1<void, int> decodetime;
	PSignal1<void, const char*> usedcardid;
};
SWIG_TEMPLATE_TYPEDEF(ePtr<iCryptoInfo>, iCryptoInfoPtr);

#ifndef SWIG
class eDVBCAHandler: public eServerSocket, public iCryptoInfo
#else
class eDVBCAHandler : public iCryptoInfo
#endif
{
DECLARE_REF(eDVBCAHandler);
#ifndef SWIG
	CAServiceMap services;
	ePtrList<ePMTClient> clients;
	ePtr<eTimer> serviceLeft;
	std::map<eServiceReferenceDVB, ePtr<eTable<ProgramMapSection> > > pmtCache;

	void newConnection(int socket);
	void processPMTForService(eDVBCAService *service, eTable<ProgramMapSection> *ptr);
	void distributeCAPMT();
	void serviceGone();
#endif
	static eDVBCAHandler *instance;
public:
	eDVBCAHandler();
#ifndef SWIG
	~eDVBCAHandler();

	int registerService(const eServiceReferenceDVB &service, int adapter, int demux_nums[2], int servicetype, eDVBCAService *&caservice);
	int unregisterService(const eServiceReferenceDVB &service , int adapter, int demux_nums[2], eTable<ProgramMapSection> *ptr);
	void handlePMT(const eServiceReferenceDVB &service, ePtr<eTable<ProgramMapSection> > &ptr);
	void connectionLost(ePMTClient *client);

	static eDVBCAHandler *getInstance() { return instance; }
#endif
	static SWIG_VOID(RESULT) getCryptoInfo(ePtr<iCryptoInfo> &SWIG_NAMED_OUTPUT(ptr)) { ptr = instance; return 0; }
};

#endif // __DVB_CAHANDLER_H_
