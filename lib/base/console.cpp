#include <lib/base/console.h>
#include <lib/base/eerror.h>
#include <sys/vfs.h> // for statfs
#include <unistd.h>
#include <signal.h>
#include <errno.h>
#include <poll.h>

int bidirpipe(int pfd[], char *cmd , char *argv[])
{
	int pfdin[2];  /* from child to parent */
	int pfdout[2]; /* from parent to child */
	int pfderr[2]; /* stderr from child to parent */
	int pid;       /* child's pid */

	if ( pipe(pfdin) == -1 || pipe(pfdout) == -1 || pipe(pfderr) == -1)
		return(-1);

	if ( ( pid = fork() ) == -1 )
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

		execvp(cmd,argv);
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

int eConsoleAppContainer::execute( const std::string &cmd )
{
	if (running())
		return -1;
	pid=-1;
	killstate=0;
//	eDebug("cmd = %s", cmd.c_str() );
	int cnt=2; // path to app + terminated 0
	std::string str(cmd.length()?cmd:"");

	// kill spaces at beginning
	unsigned int pos = str.find_first_not_of(' ');
	if (pos != std::string::npos && pos)
		str = str.substr(pos);

	// kill spaces at the end
	pos = str.find_last_not_of(' ');
	if (pos != std::string::npos && (pos+1) < str.length())
		str = str.erase(pos+1);

	unsigned int slen=str.length();
	if (!slen)
		return -2;

	std::map<char,char> brackets;
	brackets.insert(std::pair<char,char>('\'','\''));
	brackets.insert(std::pair<char,char>('"','"'));
	brackets.insert(std::pair<char,char>('`','`'));
	brackets.insert(std::pair<char,char>('(',')'));
	brackets.insert(std::pair<char,char>('{','}'));
	brackets.insert(std::pair<char,char>('[',']'));
	brackets.insert(std::pair<char,char>('<','>'));

	unsigned int idx=str.find(' ');
	std::string path = str.substr(0, idx != std::string::npos ? idx : slen );
//	eDebug("path = %s", path.c_str() );
	unsigned int plen = path.length();

	std::string cmds = slen > plen ? str.substr( plen+1 ) : "";
	unsigned int clen = cmds.length();
//	eDebug("cmds = %s", cmds.c_str() );

	idx = 0;
	std::map<char,char>::iterator it = brackets.find(cmds[idx]);
	while ( (idx = cmds.find(' ',idx) ) != std::string::npos )  // count args
	{
		if (it != brackets.end())
		{
			if (cmds[idx-1] == it->second)
				it = brackets.end();
		}
		if (it == brackets.end())
		{
			cnt++;
			it = brackets.find(cmds[idx+1]);
		}
		idx++;
	}

//	eDebug("idx = %d, %d counted spaces", idx, cnt-2);

	if ( clen )
	{
		cnt++;
//		eDebug("increase cnt");
	}

//	eDebug("%d args", cnt-2);
	char **argv = new char*[cnt];  // min two args... path and terminating 0
//	eDebug("%d args", cnt);
	argv[0] = new char[ plen+1 ];
//	eDebug("new argv[0] %d bytes (%s)", plen+1, path.c_str());
	strcpy( argv[0], path.c_str() );
	argv[cnt-1] = 0;               // set terminating null

	if ( cnt > 2 )  // more then default args?
	{
		cnt=1;  // do not overwrite path in argv[0]

		it = brackets.find(cmds[0]);
		idx=0;
		while ( (idx = cmds.find(' ',idx)) != std::string::npos )  // parse all args..
		{
			bool bracketClosed=false;
			if ( it != brackets.end() )
			{
				if (cmds[idx-1]==it->second)
				{
					it = brackets.end();
					bracketClosed=true;
				}
			}
			if ( it == brackets.end() )
			{
				std::string tmp = cmds.substr(0, idx);
				if (bracketClosed)
				{
					tmp.erase(0,1);
					tmp.erase(tmp.length()-1, 1);
					bracketClosed=false;
				}
//				eDebug("new argv[%d] %d bytes (%s)", cnt, tmp.length()+1, tmp.c_str());
				argv[cnt] = new char[ tmp.length()+1 ];
//				eDebug("idx=%d, arg = %s", idx, tmp.c_str() );
				strcpy( argv[cnt++], tmp.c_str() );
				cmds.erase(0, idx+1);
//				eDebug("str = %s", cmds.c_str() );
				it = brackets.find(cmds[0]);
				idx=0;
			}
			else
				idx++;
		}
		if ( it != brackets.end() )
		{
			cmds.erase(0,1);
			cmds.erase(cmds.length()-1, 1);
		}
		// store the last arg
//		eDebug("new argv[%d] %d bytes (%s)", cnt, cmds.length()+1, cmds.c_str());
		argv[cnt] = new char[ cmds.length()+1 ];
		strcpy( argv[cnt], cmds.c_str() );
	}
	else
		cnt=1;

  // get one read ,one write and the err pipe to the prog..

//	int tmp=0;
//	while(argv[tmp])
//		eDebug("%d is %s", tmp, argv[tmp++]);
  
	pid = bidirpipe(fd, argv[0], argv);

	while ( cnt >= 0 )  // release heap memory
	{
//		eDebug("delete argv[%d]", cnt);
		delete [] argv[cnt--];
	}
//	eDebug("delete argv");
	delete [] argv;
	
	if ( pid == -1 )
		return -3;

//	eDebug("pipe in = %d, out = %d, err = %d", fd[0], fd[1], fd[2]);

	in = new eSocketNotifier(eApp, fd[0], eSocketNotifier::Read|eSocketNotifier::Priority|eSocketNotifier::Hungup );
	out = new eSocketNotifier(eApp, fd[1], eSocketNotifier::Write, false);  
	err = new eSocketNotifier(eApp, fd[2], eSocketNotifier::Read|eSocketNotifier::Priority );
	CONNECT(in->activated, eConsoleAppContainer::readyRead);
	CONNECT(out->activated, eConsoleAppContainer::readyWrite);
	CONNECT(err->activated, eConsoleAppContainer::readyErrRead);
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
		eDebug("user kill(SIGKILL) console App");
		killstate=-1;
		::kill(pid, SIGKILL);
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
		::kill(pid, SIGINT);
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
		char buf[2048];
		int rd;
		while((rd = read(fd[0], buf, 2047)) > 0)
		{
/*			for ( int i = 0; i < rd; i++ )
				eDebug("%d = %c (%02x)", i, buf[i], buf[i] );*/
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
		/*emit*/ appClosed(killstate);
	}
}

void eConsoleAppContainer::readyErrRead(int what)
{
	if (what & (eSocketNotifier::Priority|eSocketNotifier::Read))
	{
//		eDebug("what = %d");
		char buf[2048];
		int rd;
		while((rd = read(fd[2], buf, 2047)) > 0)
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
	out->start();
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
