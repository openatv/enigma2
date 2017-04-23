#ifndef __lib_base_message_h
#define __lib_base_message_h

#include <queue>
#include <lib/base/ebase.h>
#include <lib/python/connections.h>
#include <lib/python/swig.h>
#include <unistd.h>
#include <lib/base/elock.h>
#include <lib/base/wrappers.h>


/**
 * \brief A generic messagepump.
 *
 * You can send and receive messages with this class. Internally a fifo is used,
 * so you can use them together with a \c eMainloop.
 */
#ifndef SWIG
class eMessagePumpMT
{
	int fd[2];
	eLock content;
public:
	eMessagePumpMT();
	virtual ~eMessagePumpMT();
protected:
	int send(const void *data, int len);
	int recv(void *data, int len); // blockierend
	int getInputFD() const { return fd[1]; }
	int getOutputFD() const { return fd[0]; }
};

/**
 * \brief A messagepump with fixed-length packets.
 *
 * Based on \ref eMessagePump, with this class you can send and receive fixed size messages.
 * Automatically creates a eSocketNotifier and gives you a callback.
 */
template<class T>
class eFixedMessagePump: public sigc::trackable
{
	ePtr<eSocketNotifier> sn;
	std::queue<T> m_queue;
	int m_pipe[2];
	eSingleLock lock;
	void do_recv(int)
	{
		char byte;
		if (singleRead(m_pipe[0], &byte, sizeof(byte)) <= 0) return;

		lock.lock();
		if (!m_queue.empty())
		{
			T msg = m_queue.front();
			m_queue.pop();
			lock.unlock();
			/*
			 * We should not deliver the message while holding the lock,
			 * not even if we would use a recursive mutex.
			 * We would risk deadlock when pump writer and reader share another
			 * mutex besides this one, which could be grabbed / released
			 * in a different order
			 */
			/*emit*/ recv_msg(msg);
		}
		else
		{
			lock.unlock();
		}
	}
public:
	sigc::signal1<void,const T&> recv_msg;
	void send(const T &msg)
	{
		{
			eSingleLocker s(lock);
			m_queue.push(msg);
		}
		char byte = 0;
		writeAll(m_pipe[1], &byte, sizeof(byte));
	}
	eFixedMessagePump(eMainloop *context, int mt)
	{
		pipe(m_pipe);
		sn = eSocketNotifier::create(context, m_pipe[0], eSocketNotifier::Read, false);
		CONNECT(sn->activated, eFixedMessagePump<T>::do_recv);
		sn->start();
	}
	~eFixedMessagePump()
	{
		close(m_pipe[0]);
		close(m_pipe[1]);
	}
};
#endif

class ePythonMessagePump: public eMessagePumpMT, public sigc::trackable
{
	ePtr<eSocketNotifier> sn;
	void do_recv(int)
	{
		int msg;
		recv(&msg, sizeof(msg));
		/*emit*/ recv_msg(msg);
	}
public:
	PSignal1<void,int> recv_msg;
	void send(int msg)
	{
		eMessagePumpMT::send(&msg, sizeof(msg));
	}
	ePythonMessagePump()
	{
		sn=eSocketNotifier::create(eApp, getOutputFD(), eSocketNotifier::Read);
		CONNECT(sn->activated, ePythonMessagePump::do_recv);
		sn->start();
	}
	void start() { if (sn) sn->start(); }
	void stop() { if (sn) sn->stop(); }
};

#endif
