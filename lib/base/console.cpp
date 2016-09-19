#include <lib/base/console.h>
#include <lib/base/eerror.h>
#include <sys/vfs.h> // for statfs
#include <unistd.h>
#include <signal.h>
#include <errno.h>
#include <poll.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <fcntl.h>

int bidirpipe(int pfd[], const char *cmd , const char * const argv[], const char *cwd )
{
	int pfdin[2];  /* from child to parent */
	int pfdout[2]; /* from parent to child */
	int pfderr[2]; /* stderr from child to parent */
	int pid;       /* child's pid */

	if ( pipe(pfdin) == -1 || pipe(pfdout) == -1 || pipe(pfderr) == -1)
		return(-1);

	if ( ( pid = vfork() ) == -1 )
		return(-1);
	else if (pid == 0) /* child process */
	{
		setsid();
		if ( close(0) == -1 || close(1) == -1 || close(2) == -1 )
			_exit(0);

		if (dup(pfdout[0]) != 0 || dup(pfdin[1]) != 1 || dup(pfderr[1]) != 2 )
			_exit(0);

		if (close(pfdout[0]) == -1 || close(pfdout[1]) == -1 ||
				close(pfdin[0]) == -1 || close(pfdin[1]) == -1 ||
				close(pfderr[0]) == -1 || close(pfderr[1]) == -1 )
			_exit(0);

		for (unsigned int i=3; i < 90; ++i )
			close(i);

		if (cwd)
			chdir(cwd);

		execvp(cmd, (char * const *)argv);
				/* the vfork will actually suspend the parent thread until execvp is called. thus it's ok to use the shared arg/cmdline pointers here. */
		eDebug("[eConsoleAppContainer] Finished %s", cmd);
		_exit(0);
	}
	if (close(pfdout[0]) == -1 || close(pfdin[1]) == -1 || close(pfderr[1]) == -1)
			return(-1);

	pfd[0] = pfdin[0];
	pfd[1] = pfdout[1];
	pfd[2] = pfderr[0];

	return(pid);
}

DEFINE_REF(eConsoleAppContainer);

eConsoleAppContainer::eConsoleAppContainer():
	pid(-1),
	killstate(0),
	buffer(2049)
{
	for (int i=0; i < 3; ++i)
	{
		fd[i]=-1;
		filefd[i]=-1;
	}
}

int eConsoleAppContainer::setCWD( const char *path )
{
	struct stat dir_stat;

	if (stat(path, &dir_stat) == -1)
		return -1;

	if (!S_ISDIR(dir_stat.st_mode))
		return -2;

	m_cwd = path;
	return 0;
}

int eConsoleAppContainer::execute( const char *cmd )
{
	int argc = 3;
	const char *argv[argc + 1];
	argv[0] = "/bin/sh";
	argv[1] = "-c";
	argv[2] = cmd;
	argv[argc] = NULL;

	return execute(argv[0], argv);
}

int eConsoleAppContainer::execute(const char *cmdline, const char * const argv[])
{
	if (running())
		return -1;

	eDebug("[eConsoleAppContainer] Starting %s", cmdline);
	pid=-1;
	killstate=0;

	// get one read, one write and the err pipe to the prog..
	pid = bidirpipe(fd, cmdline, argv, m_cwd.empty() ? 0 : m_cwd.c_str());

	if ( pid == -1 ) {
		eDebug("[eConsoleAppContainer] failed to start %s", cmdline);
		return -3;
	}

//	eDebug("[eConsoleAppContainer] pipe in = %d, out = %d, err = %d", fd[0], fd[1], fd[2]);

	::fcntl(fd[0], F_SETFL, O_NONBLOCK);
	::fcntl(fd[1], F_SETFL, O_NONBLOCK);
	::fcntl(fd[2], F_SETFL, O_NONBLOCK);
	in = eSocketNotifier::create(eApp, fd[0], eSocketNotifier::Read|eSocketNotifier::Priority|eSocketNotifier::Hungup );
	out = eSocketNotifier::create(eApp, fd[1], eSocketNotifier::Write, false);
	err = eSocketNotifier::create(eApp, fd[2], eSocketNotifier::Read|eSocketNotifier::Priority );
	CONNECT(in->activated, eConsoleAppContainer::readyRead);
	CONNECT(out->activated, eConsoleAppContainer::readyWrite);
	CONNECT(err->activated, eConsoleAppContainer::readyErrRead);
	in->m_clients.push_back(this);
	out->m_clients.push_back(this);
	err->m_clients.push_back(this);

	return 0;
}

eConsoleAppContainer::~eConsoleAppContainer()
{
	kill();
}

void eConsoleAppContainer::kill()
{
	if ( killstate != -1 && pid != -1 )
	{
		eDebug("[eConsoleAppContainer] user kill(SIGKILL)");
		killstate=-1;
		/*
		 * Use a negative pid value, to signal the whole process group
		 * ('pid' might not even be running anymore at this point)
		 */
		::kill(-pid, SIGKILL);
		closePipes();
	}
	while( !outbuf.empty() ) // cleanup out buffer
	{
		queue_data d = outbuf.front();
		outbuf.pop();
		delete [] d.data;
	}
	in = 0;
	out = 0;
	err = 0;

	for (int i=0; i < 3; ++i)
	{
		if ( filefd[i] >= 0 )
			close(filefd[i]);
	}
}

void eConsoleAppContainer::sendCtrlC()
{
	if ( killstate != -1 && pid != -1 )
	{
		eDebug("[eConsoleAppContainer] user send SIGINT(Ctrl-C)");
		/*
		 * Use a negative pid value, to signal the whole process group
		 * ('pid' might not even be running anymore at this point)
		 */
		::kill(-pid, SIGINT);
	}
}

void eConsoleAppContainer::sendEOF()
{
	if (out)
		out->stop();
	if (fd[1] != -1)
	{
		::close(fd[1]);
		fd[1]=-1;
	}
}

void eConsoleAppContainer::closePipes()
{
	if (in)
		in->stop();
	if (out)
		out->stop();
	if (err)
		err->stop();
	if (fd[0] != -1)
	{
		::close(fd[0]);
		fd[0]=-1;
	}
	if (fd[1] != -1)
	{
		::close(fd[1]);
		fd[1]=-1;
	}
	if (fd[2] != -1)
	{
		::close(fd[2]);
		fd[2]=-1;
	}
	while( outbuf.size() ) // cleanup out buffer
	{
		queue_data d = outbuf.front();
		outbuf.pop();
		delete [] d.data;
	}
	in = 0; out = 0; err = 0;
	pid = -1;
}

void eConsoleAppContainer::readyRead(int what)
{
	bool hungup = what & eSocketNotifier::Hungup;
	if (what & (eSocketNotifier::Priority|eSocketNotifier::Read))
	{
//		eDebug("[eConsoleAppContainer] readyRead what = %d", what);
		char* buf = &buffer[0];
		int rd;
		while((rd = read(fd[0], buf, 2048)) > 0)
		{
			buf[rd]=0;
			/*emit*/ dataAvail(buf);
			stdoutAvail(buf);
			if ( filefd[1] >= 0 )
				::write(filefd[1], buf, rd);
			if (!hungup)
				break;
		}
	}
	readyErrRead(eSocketNotifier::Priority|eSocketNotifier::Read); /* be sure to flush all data which might be already written */
	if (hungup)
	{
		int childstatus;
		int retval = killstate;
		/*
		 * We have to call 'wait' on the child process, in order to avoid zombies.
		 * Also, this gives us the chance to provide better exit status info to appClosed.
		 */
		if (::waitpid(-pid, &childstatus, 0) > 0)
		{
			if (WIFEXITED(childstatus))
			{
				retval = WEXITSTATUS(childstatus);
			}
		}
		closePipes();
		/*emit*/ appClosed(retval);
	}
}

void eConsoleAppContainer::readyErrRead(int what)
{
	if (what & (eSocketNotifier::Priority|eSocketNotifier::Read))
	{
//		eDebug("[eConsoleAppContainer] readyErrRead what = %d", what);
		char* buf = &buffer[0];
		int rd;
		while((rd = read(fd[2], buf, 2048)) > 0)
		{
/*			for ( int i = 0; i < rd; i++ )
				eDebug("[eConsoleAppContainer] %d = %c (%02x)", i, buf[i], buf[i] );*/
			buf[rd]=0;
			/*emit*/ dataAvail(buf);
			stderrAvail(buf);
		}
	}
}

void eConsoleAppContainer::write( const char *data, int len )
{
	char *tmp = new char[len];
	memcpy(tmp, data, len);
	outbuf.push(queue_data(tmp,len));
	if (out)
		out->start();
}

void eConsoleAppContainer::readyWrite(int what)
{
	if (what&eSocketNotifier::Write && outbuf.size() )
	{
		queue_data &d = outbuf.front();
		int wr = ::write( fd[1], d.data+d.dataSent, d.len-d.dataSent );
		if (wr < 0)
			eDebug("[eConsoleAppContainer] write on fd=%d failed: %m", fd[1]);
		else
			d.dataSent += wr;
		if (d.dataSent == d.len)
		{
			outbuf.pop();
			delete [] d.data;
			if ( filefd[0] == -1 )
			/* emit */ dataSent(0);
		}
	}
	if ( !outbuf.size() )
	{
		if ( filefd[0] >= 0 )
		{
			char* buf = &buffer[0];
			int rsize = read(filefd[0], buf, 2048);
			if ( rsize > 0 )
				write(buf, rsize);
			else
			{
				close(filefd[0]);
				filefd[0] = -1;
				::close(fd[1]);
				eDebug("[eConsoleAppContainer] readFromFile done - closing stdin pipe");
				fd[1]=-1;
				dataSent(0);
				out->stop();
			}
		}
		else
			out->stop();
	}
}
