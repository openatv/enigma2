#ifndef __lib_base_message_h
#define __lib_base_message_h

#include <queue>
#include <lib/base/ebase.h>
#include <lib/python/connections.h>
#include <lib/python/swig.h>
#include <unistd.h>
#include <lib/base/elock.h>
#include <lib/base/wrappers.h>
#ifndef HAVE_HISILICON
#include <sys/eventfd.h>
#endif

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

#ifndef HAVE_HISILICON
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
#endif

/**
 * \brief A messagepump with fixed-length packets.
 *
 * Based on \ref eMessagePump, with this class you can send and receive fixed size messages.
 * Automatically creates a eSocketNotifier and gives you a callback.
 */
template<class T>
#ifndef HAVE_HISILICON
class eFixedMessagePump: public sigc::trackable, FD
#else
class eFixedMessagePump: public sigc::trackable
#endif
{
	const char *name;
	eSingleLock lock;
	ePtr<eSocketNotifier> sn;
	std::queue<T> m_queue;
#ifdef HAVE_HISILICON
	int m_pipe[2];
#endif
	void do_recv(int)
	{
#ifndef HAVE_HISILICON
		uint64_t data;
		if (::read(m_fd, &data, sizeof(data)) <= 0)
		{
			eWarning("[eFixedMessagePump<%s>] read error %m", name);
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
				eWarning("[eFixedMessagePump<%s>] Got event but queue is empty", name);
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
#else
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
#endif
	}
#ifndef HAVE_HISILICON
	void trigger_event()
	{
		static const uint64_t data = 1;
		if (::write(m_fd, &data, sizeof(data)) < 0)
			eFatal("[eFixedMessagePump<%s>] write error %m", name);
	}
#endif
public:
	sigc::signal1<void,const T&> recv_msg;
	void send(const T &msg)
	{
		{
			eSingleLocker s(lock);
			m_queue.push(msg);
		}
#ifndef HAVE_HISILICON
		trigger_event();
#else
		char byte = 0;
		writeAll(m_pipe[1], &byte, sizeof(byte));
#endif
	}
#ifndef HAVE_HISILICON
	eFixedMessagePump(eMainloop *context, int mt, const char *name):
		FD(eventfd(0, EFD_CLOEXEC)),
		name(name),
		sn(eSocketNotifier::create(context, m_fd, eSocketNotifier::Read, false))
	{
		CONNECT(sn->activated, eFixedMessagePump<T>::do_recv);
		sn->start();
	}
	eFixedMessagePump(eMainloop *context, int mt):
		FD(eventfd(0, EFD_CLOEXEC)),
		sn(eSocketNotifier::create(context, m_fd, eSocketNotifier::Read, false))
	{
		CONNECT(sn->activated, eFixedMessagePump<T>::do_recv);
		sn->start();
	}
#else
	eFixedMessagePump(eMainloop *context, int mt)
	{
		if (pipe(m_pipe) == -1)
		{
			eDebug("[eFixedMessagePump] failed to create pipe (%m)");
		}
		sn = eSocketNotifier::create(context, m_pipe[0], eSocketNotifier::Read, false);
		CONNECT(sn->activated, eFixedMessagePump<T>::do_recv);
		sn->start();
	}
	eFixedMessagePump(eMainloop *context, int mt, const char *name):
		name(name)
	{
		if (pipe(m_pipe) == -1)
		{
			eDebug("[eFixedMessagePump] failed to create pipe (%m)");
		}
		sn = eSocketNotifier::create(context, m_pipe[0], eSocketNotifier::Read, false);
		CONNECT(sn->activated, eFixedMessagePump<T>::do_recv);
		sn->start();
	}
#endif
	~eFixedMessagePump()
	{
#ifndef HAVE_HISILICON
		/* sn is refcounted and still referenced, so call stop() here */
		sn->stop();
#else
		close(m_pipe[0]);
		close(m_pipe[1]);
#endif
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
