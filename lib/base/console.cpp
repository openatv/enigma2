/*
 * console.cpp
 *
 * Copyright (C) 2002 Felix Domke <tmbinc@tuxbox.org>
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 2 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program; if not, write to the Free Software
 * Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
 *
 * $Id: console.cpp,v 1.1 2003-10-17 15:35:47 tmbinc Exp $
 */

#include <lib/base/console.h>

#include <lib/base/estring.h>
#include <sys/vfs.h> // for statfs
#include <unistd.h>
#include <signal.h>
#include <errno.h>

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
		if ( close(0) == -1 || close(1) == -1 || close(2) == -1 )
			_exit(0);

		if (dup(pfdout[0]) != 0 || dup(pfdin[1]) != 1 || dup(pfderr[1]) != 2 )
			_exit(0);

		if (close(pfdout[0]) == -1 || close(pfdout[1]) == -1 ||
				close(pfdin[0]) == -1 || close(pfdin[1]) == -1 ||
				close(pfderr[0]) == -1 || close(pfderr[1]) == -1 )
			_exit(0);

		execv(cmd,argv);
		_exit(0);
	}
	if (close(pfdout[0]) == -1 || close(pfdin[1]) == -1 || close(pfderr[1]) == -1)
			return(-1);

	pfd[0] = pfdin[0];
	pfd[1] = pfdout[1];
	pfd[2] = pfderr[0];

	return(pid);
}

eConsoleAppContainer::eConsoleAppContainer( const eString &cmd )
:pid(-1), killstate(0), outbuf(0)
{
//	eDebug("cmd = %s", cmd.c_str() );
	memset(fd, 0, sizeof(fd) );
	int cnt=2; // path to app + terminated 0
	eString str(cmd?cmd:"");

	while( str.length() && str[0] == ' ' )  // kill spaces at beginning
		str = str.mid(1);

	while( str.length() && str[str.length()-1] == ' ' )  // kill spaces at the end
		str = str.left( str.length() - 1 );

	if (!str.length())
		return;

	unsigned int idx=0;
	eString path = str.left( (idx = str.find(' ')) != eString::npos ? idx : str.length() );
//	eDebug("path = %s", path.c_str() );

	eString cmds = str.mid( path.length()+1 );
//	eDebug("cmds = %s", cmds.c_str() );

	idx = 0;
	while ( (idx = cmds.find(' ',idx) ) != eString::npos )  // count args
	{
		cnt++;
		idx++;
	}

//	eDebug("idx = %d, %d counted spaces", idx, cnt-2);

	if ( cmds.length() )
	{
		cnt++;
//		eDebug("increase cnt");
	}

//	eDebug("%d args", cnt-2);
	char **argv = new char*[cnt];  // min two args... path and terminating 0
	argv[0] = new char[ path.length() ];
	strcpy( argv[0], path.c_str() );
	argv[cnt-1] = 0;               // set terminating null

	if ( cnt > 2 )  // more then default args?
	{
		cnt=1;  // do not overwrite path in argv[0]

		while ( (idx = cmds.find(' ')) != eString::npos )  // parse all args..
		{
			argv[cnt] = new char[ idx ];
//			eDebug("idx=%d, arg = %s", idx, cmds.left(idx).c_str() );
			strcpy( argv[cnt++], cmds.left( idx ).c_str() );
			cmds = cmds.mid(idx+1);
//			eDebug("str = %s", cmds.c_str() );
		}
		// store the last arg
		argv[cnt] = new char[ cmds.length() ];
		strcpy( argv[cnt], cmds.c_str() );
	}

  // get one read ,one write and the err pipe to the prog..
  
	if ( (pid = bidirpipe(fd, argv[0], argv)) == -1 )
	{
		while ( cnt-- > 0 )
			delete [] argv[cnt];
		delete [] argv;
		return;
	}

	while ( cnt-- > 0 )  // release heap memory
		delete [] argv[cnt];
	delete [] argv;

	eDebug("pipe in = %d, out = %d, err = %d", fd[0], fd[1], fd[2]);

	in = new eSocketNotifier(eApp, fd[0], 19 );  // 19 = POLLIN, POLLPRI, POLLHUP
	out = new eSocketNotifier(eApp, fd[1], eSocketNotifier::Write);  // POLLOUT
	err = new eSocketNotifier(eApp, fd[2], 19 );  // 19 = POLLIN, POLLPRI, POLLHUP
	CONNECT(in->activated, eConsoleAppContainer::readyRead);
	CONNECT(out->activated, eConsoleAppContainer::readyWrite);
	CONNECT(err->activated, eConsoleAppContainer::readyErrRead);
	signal(SIGCHLD, SIG_IGN);   // no zombie when child killed
}

eConsoleAppContainer::~eConsoleAppContainer()
{
	if ( running() )
	{
		killstate=-1;
		kill();
	}
	if ( outbuf )
		delete [] outbuf;
}

void eConsoleAppContainer::kill()
{
	killstate=-1;
	system( eString().sprintf("kill %d", pid).c_str() );
	eDebug("user kill console App");
}

void eConsoleAppContainer::closePipes()
{
	in->stop();
	out->stop();
	err->stop();
	::close(fd[0]);
	fd[0]=0;
	::close(fd[1]);
	fd[1]=0;
	::close(fd[2]);
	fd[2]=0;
	eDebug("pipes closed");
}

void eConsoleAppContainer::readyRead(int what)
{
	if (what & POLLPRI|POLLIN)
	{
		eDebug("what = %d");
		char buf[2048];
		int readed = read(fd[0], buf, 2048);
		eDebug("%d bytes read", readed);
		if ( readed != -1 && readed )
			/*emit*/ dataAvail( eString( buf ) );
		else if (readed == -1)
			eDebug("readerror %d", errno);
	}
	if (what & eSocketNotifier::Hungup)
	{
		eDebug("child has terminated");
		closePipes();
		/*emit*/ appClosed(killstate);
	}
}

void eConsoleAppContainer::readyErrRead(int what)
{
	if (what & POLLPRI|POLLIN)
	{
		eDebug("what = %d");
		char buf[2048];
		int readed = read(fd[2], buf, 2048);
		eDebug("%d bytes read", readed);
		if ( readed != -1 && readed )
			/*emit*/ dataAvail( eString( buf ) );
		else if (readed == -1)
			eDebug("readerror %d", errno);
	}
}

void eConsoleAppContainer::write( const eString & str )
{
	outbuf = new char[ str.length()];
	strcpy( outbuf, str.c_str() );
}

void eConsoleAppContainer::readyWrite(int what)
{
	if (what == 4 && outbuf)
	{
		if ( ::write( fd[1], outbuf, strlen(outbuf) ) != (int) strlen(outbuf) )
		{
			/* emit */ dataSent(-1);
			eDebug("writeError");
		}
		else
		{
			/* emit */ dataSent(0);
			eDebug("write ok");
		}

		delete outbuf;
		outbuf=0;
	}
}
