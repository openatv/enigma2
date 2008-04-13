#ifndef __LIB_BASE_CONSOLE_H__
#define __LIB_BASE_CONSOLE_H__

#include "Python.h"
#include <string>
#include <lib/base/ebase.h>
#include <lib/python/connections.h>
#include <queue>

#ifndef SWIG
struct queue_data
{
	queue_data( char *data, int len )
		:data(data), len(len)
	{
	}
	char *data;
	int len;
};
#endif

class eConsoleAppContainer: public Object
{
#ifndef SWIG
	int fd[3];
	int pid;
	int killstate;
	std::queue<struct queue_data> outbuf;
	eSocketNotifier *in, *out, *err;
	void readyRead(int what);
	void readyErrRead(int what);
	void readyWrite(int what);
	void closePipes();
#endif
public:
	eConsoleAppContainer();
	int execute( const char *str );
	int execute( const char *cmdline, const char *const argv[] );
	int execute( PyObject *cmdline, PyObject *args );
	~eConsoleAppContainer();
	int getPID() { return pid; }
	void kill();
	void sendCtrlC();
	void write( const char *data, int len );
	void write( PyObject *data );
	bool running() { return (fd[0]!=-1) && (fd[1]!=-1) && (fd[2]!=-1); }
	PSignal1<void, const char*> dataAvail;
	PSignal1<void,int> dataSent;
	PSignal1<void,int> appClosed;
};

#endif // __LIB_BASE_CONSOLE_H__
