#ifndef __DVB_RTSPSTREAMSERVER_H_
#define __DVB_RTSPSTREAMSERVER_H_

#include <lib/network/serversocket.h>
#include <lib/service/servicedvbstream.h>
#include <lib/nav/core.h>
#include <lib/dvb/db.h>

#define PROTO_RTSP_UDP 1
#define PROTO_RTSP_TCP 2
#define PROTO_HTTP 3

#ifndef SWIG
class eRTSPStreamServer;

class eRTSPStreamClient : public eDVBServiceStream
{
  protected:
	eRTSPStreamServer *parent;
	int encoderFd;
	int streamFd;
	eDVBRecordFileThread *mr;

	eDVBRecordStreamThread *streamThread;
	std::string m_remotehost;
	std::string m_serviceref;
	bool m_useencoder;
	int proto;
	int freq, pol, sys;
	int session_id, stream_id;
	int buf_size;
	char clear_previous_channel;
	uint64_t time_addsr;
	int transponder_id;
	bool running, tune_completed;
	bool first;
	void notifier(int);
	ePtr<eSocketNotifier> rsn;
	std::set<int> pids;
	std::map<int, eServiceReferenceDVB> pid_sr;
	std::string request;
	std::set<eServiceReferenceDVB> not_cached_sr;
	int src, fe;
	eDVBFrontendParametersSatellite sat;
	eDVBFrontendParametersTerrestrial ter;
	eDVBFrontendParametersCable cab;
	eDVBFrontendParametersATSC atsc;

	std::map<eServiceReferenceDVB, eDVBServicePMTHandler *> active_services;

	void streamStopped()
	{
		//	stopStream();
	}
	void tuneFailed()
	{
		//	stopStream();
	}
	virtual void eventUpdate(int event);
	int satip2enigma(std::string satipstr);
	int getOrbitalPosition(int, int);
	void init_rtsp();
	void update_pids();
	void add_pid(int p);
	void del_pid(int p);
	eServiceReferenceDVB *new_service_ref(int sid);
	eDVBFrontendParameters *fp;
	ePtr<eDVBResourceManager> m_mgr;
	eDVBDB *m_dvbdb;
	eDVBChannel *m_channel;
	std::string searchServiceRef(int sys, int freq, int pol, int orbital_position, int sid);
	eServiceReferenceDVB *getServiceforPid(int p);
	int addCachedPids(ePtr<eDVBService> service, eServiceReferenceDVB s);
	void update_service_list();
	int set_demux_buffer(int size);
	void process_pids(int op, const std::string &pid_str);
	std::string get_current_timestamp();
	void http_response(int sock, int rc, const std::string &ah, const std::string &desc, int cseq, int lr);
	std::string describe_frontend();
	void getFontends(int &dvbt, int &dvbt2, int &dvbs2, int &dvbc, int &dvbc2);

  public:
	void stopStream();
	eRTSPStreamClient(eRTSPStreamServer *handler, int socket, const std::string remotehost);
	~eRTSPStreamClient();

	void start();
	std::string getRemoteHost();
	std::string getServiceref();
	bool isUsingEncoder();
};
#endif

class eRTSPStreamServer : public eServerSocket
{
	DECLARE_REF(eRTSPStreamServer);
	static eRTSPStreamServer *m_instance;

	eSmartPtrList<eRTSPStreamClient> clients;

	void newConnection(int socket);

#ifdef SWIG
	eRTSPStreamServer();
	~eRTSPStreamServer();
#endif
  public:
#ifndef SWIG
	eRTSPStreamServer();
	~eRTSPStreamServer();

	void connectionLost(eRTSPStreamClient *client);
#endif

	static eRTSPStreamServer *getInstance();
	void stopStream();
	PyObject *getConnectedClients();
};

#endif /* __DVB_STREAMSERVER_H_ */
