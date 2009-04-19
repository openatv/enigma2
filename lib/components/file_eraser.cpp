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
	messages.send(Message::quit);
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

void eBackgroundFileEraser::erase(const char *filename)
{
	if (filename)
	{
		char buf[255];
		snprintf(buf, 255, "%s.del", filename);
		if (rename(filename, buf)<0)
			;/*perror("rename file failed !!!");*/
		else
		{
			messages.send(Message(Message::erase, strdup(buf)));
			run();
		}
	}
}

void eBackgroundFileEraser::gotMessage(const Message &msg )
{
	switch (msg.type)
	{
		case Message::erase:
			if ( msg.filename )
			{
				if ( ::unlink(msg.filename) < 0 )
					eDebug("remove file %s failed (%m)", msg.filename);
				else
					eDebug("file %s erased", msg.filename);
				free((char*)msg.filename);
			}
			stop_thread_timer->start(1000, true); // stop thread in one seconds
			break;
		case Message::quit:
			quit(0);
			break;
		default:
			eDebug("unhandled thread message");
	}
}

eAutoInitP0<eBackgroundFileEraser> init_eBackgroundFilEraser(eAutoInitNumbers::configuration+1, "Background File Eraser");
