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
	messages(this,1),
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
	kill();  // i dont understand why this is needed .. in ~eThread::eThread is a kill() to..
}

void eBackgroundFileEraser::thread()
{
	hasStarted();
	nice(5);
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
	if (msg.filename.empty())
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
			struct stat st;
			int i = ::stat(c_filename, &st);
			// truncate only if the file exists and does not have any hard links
			if ((i == 0) && (st.st_nlink == 1))
			{
				if (st.st_size > erase_speed)
				{
					int fd = ::open(c_filename, O_WRONLY|O_SYNC);
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
						::ftruncate(fd, st.st_size);
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
