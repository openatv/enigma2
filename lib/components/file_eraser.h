#ifndef __lib_components_file_eraser_h
#define __lib_components_file_eraser_h

#include <lib/base/thread.h>
#include <lib/base/message.h>
#include <lib/base/ebase.h>
#include <sys/types.h>

class eBackgroundFileEraser: public eMainloop, private eThread, public sigc::trackable
{
	struct Message
	{
		std::string filename;
		bool timeshift = false;
		int directoryFd = -1;
		dev_t device = 0;
		ino_t inode = 0;
		Message()
		{}
		Message(const std::string& afilename)
			:filename(afilename)
		{}
		Message(const std::string& afilename, int fd, dev_t dev, ino_t ino)
			:filename(afilename), timeshift(true), directoryFd(fd), device(dev), inode(ino)
		{}
	};
	eFixedMessagePump<Message> messages;
	static eBackgroundFileEraser *instance;
	void gotMessage(const Message &message);
	void _eraseTimeshift(const Message &message);
	void thread();
	void idle();
	ePtr<eTimer> stop_thread_timer;
	off_t erase_speed;
	int erase_flags;
#ifndef SWIG
public:
#endif
	eBackgroundFileEraser();
	~eBackgroundFileEraser();
#ifdef SWIG
public:
#endif
	void erase(const std::string& filename);
#ifndef SWIG
	// Takes ownership of a pinned directory FD; no storage I/O in the caller.
	void eraseTimeshift(const std::string& filename, int directoryFd, dev_t device, ino_t inode);
	void releaseTimeshiftDirectory(int directoryFd);
#endif
	void setEraseSpeed(int inMBperSecond);
	void setEraseFlags(int flags);
	static eBackgroundFileEraser *getInstance() { return instance; }
	static const int ERASE_FLAG_HDD = 1;
	static const int ERASE_FLAG_OTHER = 2;
};

#endif
