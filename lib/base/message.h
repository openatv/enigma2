#ifndef __lib_base_message_h
#define __lib_base_message_h

#include <queue>
#include <lib/base/ebase.h>
#include <lib/python/connections.h>
#include <lib/python/swig.h>
#include <unistd.h>
#include <lib/base/elock.h>
#include <lib/base/wrappers.h>
#include <sys/eventfd.h>

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

class FD
{
protected:
	int m_fd;
public:
	FD(int fd): m_fd(fd) {}
	~FD()
	{
		::close(m_fd);
	}
};

/**
 * \brief A messagepump with fixed-length packets.
 *
 * Based on \ref eMessagePump, with this class you can send and receive fixed size messages.
 * Automatically creates a eSocketNotifier and gives you a callback.
 */
template<class T>
class eFixedMessagePump: public Object, FD
{
	eSingleLock lock;
	ePtr<eSocketNotifier> sn;
	std::queue<T> m_queue;
	void do_recv(int)
	{
		uint64_t data;
		if (::read(m_fd, &data, sizeof(data)) <= 0)
		{
			eFatal("[eFixedMessagePump] read error %m");
			return;
		}

		/* eventfd reads the number of writes since the last read. This
		 * will not exceed 4G, so an unsigned int is big enough to count
		 * down the events. */
		for(unsigned int count = (unsigned int)data; count != 0; --count)
		{
			lock.lock();
			if (m_queue.empty())
			{
				lock.unlock();
				eFatal("[eFixedMessagePump] Got event but queue is empty");
				break;
			}
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
	}
	void trigger_event()
	{
		static const uint64_t data = 1;
		if (::write(m_fd, &data, sizeof(data)) < 0)
			eFatal("[eFixedMessagePump] write error %m");
	}
public:
	Signal1<void,const T&> recv_msg;
	void send(const T &msg)
	{
		{
			eSingleLocker s(lock);
			m_queue.push(msg);
		}
		trigger_event();
	}
	eFixedMessagePump(eMainloop *context, int mt):
		FD(eventfd(0, EFD_CLOEXEC)),
		sn(eSocketNotifier::create(context, m_fd, eSocketNotifier::Read, false))
	{
		CONNECT(sn->activated, eFixedMessagePump<T>::do_recv);
		sn->start();
	}
	~eFixedMessagePump()
	{
		/* sn is refcounted and still referenced, so call stop() here */
		sn->stop();
	}
};
#endif

class ePythonMessagePump: public eMessagePumpMT, public Object
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
