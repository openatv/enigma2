#include <stdio.h>
#include <stdlib.h>
#include <lib/base/eerror.h>
#include <lib/base/eerroroutput.h>
#include <unistd.h>
#include <fcntl.h>
#include <lib/base/cfile.h>

DEFINE_REF(eErrorOutput)
extern char *printtime(char buffer[], int size);

eErrorOutput::eErrorOutput():
	messages(this,1),
	printout_timer(eTimer::create(this))
{
	threadrunning=true;
	fprintf(stderr, "[eErrorOutput] Constructor\n");
	fprintf(stderr, "[eErrorOutput] PIPE_BUF: %d\n", PIPE_BUF);
	pipe2(pipe_fd, O_NONBLOCK);
	{
		int max_pipe_size;
		CFile f("/proc/sys/fs/pipe-max-size", "r");
		if (f)
			if (fscanf(f, "%d", &max_pipe_size) == 1)
				fprintf(stderr, "[eErrorOutput] F_SETPIPE_SZ: %d\n", fcntl(pipe_fd[0], F_SETPIPE_SZ, max_pipe_size));
	}
	fcntl(2, F_SETFL, O_NONBLOCK);
	CONNECT(messages.recv_msg, eErrorOutput::gotMessage);
	CONNECT(printout_timer->timeout, eErrorOutput::printout);
	printout_timer->start(100, true);
	fprintf(stderr, "[eErrorOutput] F_GETPIPE_SZ 0: %d\n", fcntl(pipe_fd[0], F_GETPIPE_SZ, 0));
}

eErrorOutput::~eErrorOutput()
{
	fprintf(stderr, "[eErrorOutput] Destructor\n");
	printout_timer->stop();
	messages.send(Message::quit);
	kill();
}

void eErrorOutput::thread()
{
	fprintf(stderr, "[eErrorOutput] start thread\n");
	hasStarted();
	nice(4);
	runLoop();
	fprintf(stderr, "[eErrorOutput] behind runloop\n");
}

void eErrorOutput::gotMessage( const Message &msg )
{
	fprintf(stderr, "[eErrorOutput] message %d\n" ,msg.type);
	switch (msg.type)
	{
		case  Message::quit:
			quit(0);
			break;
		default:
		{}
	}
}

void eErrorOutput::thread_finished()
{
	threadrunning=false;
	printout();
}

void eErrorOutput::printout()
{
	static int r = 0;
	static int w = 0;
	static char c[PIPE_BUF] = "";
	static int pos = 0;
	static int cnt = 0;

	char timebuffer[32];

	if(!cnt)
	{
		pos = 0;
		r = read(pipe_fd[0], c, PIPE_BUF);
		if(r > 0)
			cnt = r;
	}

	if(cnt)
	{
		w = write(2, &c[pos] , cnt);
		if(w > 0)
		{
			cnt -= w;
			pos += w;
		}
//		{
//			usleep(10000);
//			fprintf(stderr, "[eErrorOutput] error: read= %dbyte(s) write= %dbyte(s) %s\n", r, w, strerror(errno));
//		}
//		else
//			fprintf(stderr, "error: %s\n",strerror(errno));
	}

	//	printtime(timebuffer, sizeof(timebuffer));
//	fprintf(stderr, "%s [eErrorOutput] error: read= %dbyte(s) write= %dbyte(s) \n",timebuffer, r, w);

	if(r == PIPE_BUF)
		printout_timer->start(25, true);
	else
		printout_timer->start(100, true);
}
