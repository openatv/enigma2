#ifndef __internetcheck_h__
#define __internetcheck_h__

#include <lib/base/thread.h>
#include <lib/python/python.h>
#include <lib/base/message.h>
#include <lib/base/ebase.h>


class eInternetCheck: public eMainloop, public eThread, public sigc::trackable, public iObject
{
	DECLARE_REF(eInternetCheck);

private:
	bool m_callback;
	int m_result;
	int m_timeout;
	std::string m_host;
	bool m_threadrunning;

	eFixedMessagePump<int> msg_thread, msg_main;

	void gotMessage(const int &message);
	void thread();
	void thread_finished();
public:
	PSignal1<void, int> callback;

	eInternetCheck();
	~eInternetCheck();

	RESULT startThread(const char *host, int timeout=3, bool async=false);
};

#endif // __internetcheck_h__
