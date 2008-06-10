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
		_exit(0);
	}
	if (close(pfdout[0]) == -1 || close(pfdin[1]) == -1 || close(pfderr[1]) == -1)
			return(-1);

	pfd[0] = pfdin[0];
	pfd[1] = pfdout[1];
	pfd[2] = pfderr[0];

	return(pid);
}

eConsoleAppContainer::eConsoleAppContainer()
:pid(-1), killstate(0), in(0), out(0), err(0)
{
	for (int i=0; i < 3; ++i)
		fd[i]=-1;
}

static char brakets[][2] = {
	{ '\'','\'' },
	{'"','"'},
	{'`','`'},
	{'(',')'},
	{'{','}'},
	{'[',']'},
	{'<','>'}
};

static char *find_bracket(char ch)
{
	size_t idx=0;
	while (idx < sizeof(brakets)/2) {
		if (brakets[idx][0] == ch)
			return &brakets[idx][0];
		++idx;
	}
	return NULL;
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
	int cnt=0, slen=strlen(cmd);
	char buf[slen+1];
	char *tmp=0, *argv[64], *path=buf, *cmds = buf;
	memcpy(buf, cmd, slen+1);

//	printf("cmd = %s, len %d\n", cmd, slen);

	// kill spaces at beginning
	while(path[0] == ' ') {
		++path;
		++cmds;
		--slen;
	}

	// kill spaces at the end
	while(slen && path[slen-1] == ' ') {
		path[slen-1] = 0;
		--slen;
	}

	if (!slen)
		return -2;

	tmp = strchr(path, ' ');
	if (tmp) {
		*tmp = 0;
		cmds = tmp+1;
		while(*cmds && *cmds == ' ')
			++cmds;
	}
	else
		cmds = path+slen;

	memset(argv, 0, sizeof(argv));
	argv[cnt++] = path;

	if (*cmds) {
		char *argb=NULL, *it=NULL;
		while ( (tmp = strchr(cmds, ' ')) ) {
			if (!it && *cmds && (it = find_bracket(*cmds)) )
				*cmds = 'X'; // replace open braket...
			if (!argb) // not arg begin
				argb = cmds;
			if (it && *(tmp-1) == it[1]) {
				*argb = it[0]; // set old char for open braket
				it = 0;
			}
			if (!it) { // end of arg
				*tmp = 0;
				argv[cnt++] = argb;
				argb=0; // reset arg begin
			}
			cmds = tmp+1;
			while (*cmds && *cmds == ' ')
				++cmds;
		}
		argv[cnt++] = argb ? argb : cmds;
		if (it)
		    *argv[cnt-1] = it[0]; // set old char for open braket
	}

//	int tmp=0;
//	while(argv[tmp])
//		eDebug("%d is %s", tmp, argv[tmp++]);
	return execute(argv[0], argv);
}

int eConsoleAppContainer::execute(const char *cmdline, const char * const argv[])
{
	if (running())
		return -1;

	pid=-1;
	killstate=0;

	// get one read ,one write and the err pipe to the prog..
	pid = bidirpipe(fd, cmdline, argv, m_cwd.length() ? m_cwd.c_str() : 0);

	if ( pid == -1 )
		return -3;

//	eDebug("pipe in = %d, out = %d, err = %d", fd[0], fd[1], fd[2]);

	::fcntl(fd[1], F_SETFL, O_NONBLOCK);
	::fcntl(fd[2], F_SETFL, O_NONBLOCK);
	in = new eSocketNotifier(eApp, fd[0], eSocketNotifier::Read|eSocketNotifier::Priority|eSocketNotifier::Hungup );
	out = new eSocketNotifier(eApp, fd[1], eSocketNotifier::Write, false);  
	err = new eSocketNotifier(eApp, fd[2], eSocketNotifier::Read|eSocketNotifier::Priority );
	CONNECT(in->activated, eConsoleAppContainer::readyRead);
	CONNECT(out->activated, eConsoleAppContainer::readyWrite);
	CONNECT(err->activated, eConsoleAppContainer::readyErrRead);

	return 0;
}

int eConsoleAppContainer::execute( PyObject *cmdline, PyObject *args )
{
	if (!PyString_Check(cmdline))
		return -1;
	if (!PyList_Check(args))
		return -1;
	const char *argv[PyList_Size(args) + 1];
	int i;
	for (i = 0; i < PyList_Size(args); ++i)
	{
		PyObject *arg = PyList_GetItem(args, i); /* borrowed ref */
		if (!arg)
			return -1;
		if (!PyString_Check(arg))
			return -1;
		argv[i] = PyString_AsString(arg); /* borrowed pointer */
	}
	argv[i] = 0;

	return execute(PyString_AsString(cmdline), argv); /* borrowed pointer */
}

eConsoleAppContainer::~eConsoleAppContainer()
{
	kill();
}

void eConsoleAppContainer::kill()
{
	if ( killstate != -1 && pid != -1 )
	{
		eDebug("user kill(SIGKILL) console App");
		killstate=-1;
		/*
		 * Use a negative pid value, to signal the whole process group
		 * ('pid' might not even be running anymore at this point)
		 */
		::kill(-pid, SIGKILL);
		closePipes();
	}
	while( outbuf.size() ) // cleanup out buffer
	{
		queue_data d = outbuf.front();
		outbuf.pop();
		delete [] d.data;
	}
	delete in;
	delete out;
	delete err;
	in=out=err=0;
}

void eConsoleAppContainer::sendCtrlC()
{
	if ( killstate != -1 && pid != -1 )
	{
		eDebug("user send SIGINT(Ctrl-C) to console App");
		/*
		 * Use a negative pid value, to signal the whole process group
		 * ('pid' might not even be running anymore at this point)
		 */
		::kill(-pid, SIGINT);
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
	eDebug("pipes closed");
	while( outbuf.size() ) // cleanup out buffer
	{
		queue_data d = outbuf.front();
		outbuf.pop();
		delete [] d.data;
	}
	pid = -1;
}

void eConsoleAppContainer::readyRead(int what)
{
	bool hungup = what & eSocketNotifier::Hungup;
	if (what & (eSocketNotifier::Priority|eSocketNotifier::Read))
	{
//		eDebug("what = %d");
		char buf[2049];
		int rd;
		while((rd = read(fd[0], buf, 2048)) > 0)
		{
			buf[rd]=0;
			/*emit*/ dataAvail(buf);
			if (!hungup)
				break;
		}
	}
	if (hungup)
	{
		eDebug("child has terminated");
		closePipes();
		int childstatus;
		int retval = killstate;
		/*
		 * We have to call 'wait' on the child process, in order to avoid zombies.
		 * Also, this gives us the chance to provide better exit status info to appClosed.
		 */
		if (::waitpid(pid, &childstatus, 0) > 0)
		{
			if (WIFEXITED(childstatus))
			{
				retval = WEXITSTATUS(childstatus);
			}
		}
		/*emit*/ appClosed(retval);
	}
}

void eConsoleAppContainer::readyErrRead(int what)
{
	if (what & (eSocketNotifier::Priority|eSocketNotifier::Read))
	{
//		eDebug("what = %d");
		char buf[2049];
		int rd;
		while((rd = read(fd[2], buf, 2048)) > 0)
		{
/*			for ( int i = 0; i < rd; i++ )
				eDebug("%d = %c (%02x)", i, buf[i], buf[i] );*/
			buf[rd]=0;
			/*emit*/ dataAvail(buf);
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

void eConsoleAppContainer::write( PyObject *data )
{
	char *buffer;
	int length;
	if (PyString_AsStringAndSize(data, &buffer, &length))
		return;
	if (buffer && length)
		write(buffer, length);
}

void eConsoleAppContainer::readyWrite(int what)
{
	if (what&eSocketNotifier::Write && outbuf.size() )
	{
		queue_data d = outbuf.front();
		outbuf.pop();
		if ( ::write( fd[1], d.data, d.len ) != d.len )
		{
			/* emit */ dataSent(-1);
//			eDebug("writeError");
		}
		else
		{
			/* emit */ dataSent(0);
//			eDebug("write ok");
		}
		delete [] d.data;
	}
	if ( !outbuf.size() )
		out->stop();
}
