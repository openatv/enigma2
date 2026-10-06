#include <lib/components/file_eraser.h>
#include <lib/base/ioprio.h>
#include <lib/base/eerror.h>
#include <lib/base/init.h>
#include <lib/base/init_num.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <unistd.h>
#include <errno.h>

eBackgroundFileEraser *eBackgroundFileEraser::instance;

eBackgroundFileEraser::eBackgroundFileEraser():
	messages(this,1, "eBackgroundFileEraser"),
	stop_thread_timer(eTimer::create(this)),
	erase_speed(20 << 20),
	erase_flags(ERASE_FLAG_HDD)
{
	if (!instance)
		instance=this;
	CONNECT(messages.recv_msg, eBackgroundFileEraser::gotMessage);
	CONNECT(stop_thread_timer->timeout, eBackgroundFileEraser::idle);
}

void eBackgroundFileEraser::idle()
{
	quit(0);
}

eBackgroundFileEraser::~eBackgroundFileEraser()
{
	erase_flags = 0; // Stop erasing in background, do it ASAP
	messages.send(Message());
	if (instance==this)
		instance=0;
	// Wait for the thread to complete. Must do that here,
	// because in C++ the object will be demoted after this
	// returns.
	kill();
}

void eBackgroundFileEraser::thread()
{
	hasStarted();
	if (nice(5) == -1)
	{
		eDebug("[eBackgroundFileEraser] thread failed to modify scheduling priority (%m)");
	}
	setIoPrio(IOPRIO_CLASS_BE, 7);
	reset();
	runLoop();
	stop_thread_timer->stop();
}

void eBackgroundFileEraser::erase(const std::string& filename)
{
	if (!filename.empty())
	{
		std::string delname(filename);
		delname.append(".del");
		if (rename(filename.c_str(), delname.c_str())<0)
		{
			// if rename fails with ENOENT (file doesn't exist), do nothing
			if (errno == ENOENT)
			{
				return;
			} else
			// if rename fails, try deleting the file itself without renaming.
			{
				eDebug("[eBackgroundFileEraser] Rename %s -> %s failed: %m", filename.c_str(), delname.c_str());
				delname = filename;
			}
		}
		messages.send(Message(delname));
		run();
	}
}

void eBackgroundFileEraser::gotMessage(const Message &msg )
{
	if (msg.timeshift)
	{
		_eraseTimeshift(msg);
		stop_thread_timer->start(1000, true);
	}
	else if (msg.filename.empty())
	{
		quit(0);
	}
	else
	{
		std::vector<char> v_filename(msg.filename.begin(), msg.filename.end());
		v_filename.push_back('\0');
		const char* c_filename = &v_filename[0];

		bool unlinked = false;
		eDebug("[eBackgroundFileEraser] deleting '%s'", c_filename);
		if ((((erase_flags & ERASE_FLAG_HDD) != 0) && (strncmp(c_filename, "/media/hdd/", 11) == 0)) ||
		    ((erase_flags & ERASE_FLAG_OTHER) != 0))
		{
			struct stat st = {};
			int i = ::stat(c_filename, &st);
			// truncate only if the file exists and does not have any hard links
			if ((i == 0) && (st.st_nlink == 1))
			{
				if (st.st_size > erase_speed)
				{
					int fd = ::open(c_filename, O_WRONLY|O_SYNC); //NOSONAR
					if (fd == -1)
					{
						eDebug("[eBackgroundFileEraser] Cannot open %s for writing: %m", c_filename);
					}
					else
					{
						// Remove directory entry (file still open, so not erased yet)
						if (::unlink(c_filename) == 0)
							unlinked = true;
						st.st_size -= st.st_size % erase_speed; // align on erase_speed
						if (::ftruncate(fd, st.st_size) != 0)
						{
							eDebug("[eBackgroundFileEraser] Failed to truncate %s: %m", c_filename);
						}
						usleep(500000); // even if truncate fails, wait a moment
						while ((st.st_size > erase_speed) && (erase_flags != 0))
						{
							st.st_size -= erase_speed;
							if (::ftruncate(fd, st.st_size) != 0)
							{
								eDebug("[eBackgroundFileEraser] Failed to truncate %s: %m", c_filename);
								break; // don't try again
							}
							usleep(500000); // wait half a second
						}
						::close(fd);
					}
				}
			}
		}
		if (!unlinked)
		{
			if ( ::unlink(c_filename) < 0 )
				eDebug("[eBackgroundFileEraser] removing %s failed: %m", c_filename);
		}
		stop_thread_timer->start(1000, true); // stop thread in one seconds
	}
}

void eBackgroundFileEraser::_eraseTimeshift(const Message &msg)
{
	// The message owns this FD exactly once; message-pump copies do not close it.
	struct DirectoryCloser
	{
		int fd;
		~DirectoryCloser()
		{
			if (fd >= 0 && close(fd) < 0)
				eWarning("[eBackgroundFileEraser] closing time shift directory failed: %m");
		}
	} directory{msg.directoryFd};
	if (msg.directoryFd < 0 || msg.filename.empty())
		return;
	const std::string name = msg.filename.substr(msg.filename.find_last_of('/') + 1);
	if (name.empty() || name == "." || name == "..")
		return;
	auto matchesBase = [&]()
	{
		struct stat status = {};
		if (fstatat(msg.directoryFd, name.c_str(), &status, AT_SYMLINK_NOFOLLOW) < 0)
		{
			eWarning("[eBackgroundFileEraser] cannot verify time shift %s: %m", msg.filename.c_str());
			return false;
		}
		if (!S_ISREG(status.st_mode) || status.st_dev != msg.device || status.st_ino != msg.inode)
		{
			eWarning("[eBackgroundFileEraser] retaining replaced time shift %s", msg.filename.c_str());
			return false;
		}
		return true;
	};
	if (!matchesBase())
		return;
	auto removePart = [&](const std::string &part)
	{
		if (!matchesBase())
			return -1;
		struct stat status = {};
		if (fstatat(msg.directoryFd, part.c_str(), &status, AT_SYMLINK_NOFOLLOW) < 0)
		{
			if (errno == ENOENT)
				return 0;
			eWarning("[eBackgroundFileEraser] cannot verify time shift part %s: %m", part.c_str());
			return -1;
		}
		if (!S_ISREG(status.st_mode) || status.st_dev != msg.device)
		{
			eWarning("[eBackgroundFileEraser] retaining replaced time shift part %s", part.c_str());
			return -1;
		}
		if (unlinkat(msg.directoryFd, part.c_str(), 0) < 0)
		{
			eWarning("[eBackgroundFileEraser] removing time shift part %s failed: %m", part.c_str());
			return -1;
		}
		return 1;
	};
	// Keep the base as an ownership anchor until all related names are removed.
	for (unsigned int part = 1; part < 1000; ++part)
	{
		char suffix[8];
		snprintf(suffix, sizeof(suffix), ".%03u", part);
		int result = removePart(name + suffix);
		if (result < 0)
			return;
		if (!result)
			break;
	}
	for (const char *suffix : {".sc", ".ap", ".cuts", ".meta", ".eit"})
		if (removePart(name + suffix) < 0)
			return;
	if (matchesBase() && unlinkat(msg.directoryFd, name.c_str(), 0) < 0)
		eWarning("[eBackgroundFileEraser] removing time shift %s failed: %m", msg.filename.c_str());
}

void eBackgroundFileEraser::eraseTimeshift(const std::string& filename, int directoryFd, dev_t device, ino_t inode)
{
	if (directoryFd < 0)
		return;
	messages.send(Message(filename, directoryFd, device, inode));
	run();
}

void eBackgroundFileEraser::releaseTimeshiftDirectory(int directoryFd)
{
	eraseTimeshift(std::string(), directoryFd, 0, 0);
}

void eBackgroundFileEraser::setEraseSpeed(int inMBperSecond)
{
	off_t value = inMBperSecond;
	value <<= 19; // erase_speed is in MB per half second
	erase_speed = value;
}

void eBackgroundFileEraser::setEraseFlags(int flags)
{
	erase_flags = flags;
}


eAutoInitP0<eBackgroundFileEraser> init_eBackgroundFilEraser(eAutoInitNumbers::configuration+1, "Background File Eraser");
