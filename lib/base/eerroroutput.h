#ifndef __E_ERROROUTPUT__
#define __E_ERROROUTPUT__

#include <lib/base/eerror.h>
#include <lib/base/thread.h>
#include <lib/base/message.h>
#include <lib/base/ebase.h>


class eErrorOutput: public eMainloop, public eThread, public Object
{
	DECLARE_REF(eErrorOutput)
	struct Message
	{
		int type;
		enum
		{
			quit
		};
		Message(int type=0)
			:type(type) {}
	};
	ePtr<eTimer> printout_timer;
	eFixedMessagePump<Message> messages;
	void gotMessage(const Message &message);
	void thread_finished();
	void printout();
public:
	bool threadrunning;
	int pipe_fd[2];
#ifndef SWIG
	eErrorOutput();
	~eErrorOutput();
#endif
	void thread();
};

#endif // __E_ERROROUTPUT__
