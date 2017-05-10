#ifndef __socket_mmi_h
#define __socket_mmi_h

#include <string>
#include <lib/mmi/mmi_ui.h>
#include <lib/python/connections.h>

#ifndef SWIG
#include <lib/base/buffer.h>
#include <lib/base/ebase.h>
#include <sys/socket.h>
#include <sys/types.h>
#include <sys/un.h>
class eSocketMMIHandler: public sigc::trackable
{
	eIOBuffer buffer;
	int listenfd, connfd, clilen;
	struct sockaddr_un servaddr;
	ePtr<eSocketNotifier> listensn, connsn;
	void listenDataAvail(int what);
	void connDataAvail(int what);
	void closeConn();
	const char *sockname;
	char *name;
public:
	const char *getName() const { return name; }
	sigc::signal4<int, int, const unsigned char*, const void *, int> mmi_progress;
	int send_to_mmisock( void *, size_t );
	bool connected() { return !!connsn; }
	eSocketMMIHandler();
	~eSocketMMIHandler();
};
#endif

class eSocket_UI: public eMMI_UI
{
	eSocketMMIHandler handler;
	static eSocket_UI *instance;
#ifdef SWIG
	eSocket_UI();
	~eSocket_UI();
#endif
	void stateChanged(int val) { socketStateChanged(val); }
public:
	PSignal1<void,int> socketStateChanged;
#ifndef SWIG
	eSocket_UI();
#endif
	static eSocket_UI *getInstance();
	void setInit(int slot);
	void setReset(int slot);
	int startMMI(int slot);
	int stopMMI(int slot);
	int answerMenu(int slot, int answer);
	int answerEnq(int slot, char *val);
	int cancelEnq(int slot);
	int getState(int slot);
	int getMMIState(int slot);
	const char *getName(int) const { return handler.getName() ? handler.getName() : "MMI Socket"; }
};

#endif
