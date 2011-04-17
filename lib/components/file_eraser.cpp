#include <lib/components/file_eraser.h>
#include <lib/base/ioprio.h>
#include <lib/base/eerror.h>
#include <lib/base/init.h>
#include <lib/base/init_num.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>
#include <errno.h>

eBackgroundFileEraser *eBackgroundFileEraser::instance;

eBackgroundFileEraser::eBackgroundFileEraser()
	:messages(this,1), stop_thread_timer(eTimer::create(this))
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
			// if rename fails, try deleting the file itself without renaming.
			eDebug("Rename %s -> %s failed.", filename.c_str(), delname.c_str());
			delname = filename;
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
		const char* c_filename = msg.filename.c_str();
		eDebug("[eBackgroundFileEraser] deleting '%s'", c_filename);
		struct stat st;
		if (::stat(c_filename, &st) == 0)
		{
			// Erase 50MB per second...
			static const off_t ERASE_BLOCK_SIZE = 25*1024*1024;
			while (st.st_size > ERASE_BLOCK_SIZE)
			{
				st.st_size -= ERASE_BLOCK_SIZE;
				if (::truncate(c_filename, st.st_size) != 0)
				{
					eDebug("Failed to truncate %s", c_filename);
					break; // don't try again, just unlink
				}
				usleep(500000); // wait half a second
			}
		}
		if ( ::unlink(c_filename) < 0 )
			eDebug("remove file %s failed (%m)", c_filename);
		stop_thread_timer->start(1000, true); // stop thread in one seconds
	}
}

eAutoInitP0<eBackgroundFileEraser> init_eBackgroundFilEraser(eAutoInitNumbers::configuration+1, "Background File Eraser");
