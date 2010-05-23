#ifndef __lib_components_file_eraser_h
#define __lib_components_file_eraser_h

#include <lib/base/thread.h>
#include <lib/base/message.h>
#include <lib/base/ebase.h>

class eBackgroundFileEraser: public eMainloop, private eThread, public Object
{
	struct Message
	{
		int type;
		std::string filename;
		enum
		{
			erase,
			quit
		};
		Message(int type=0)
			:type(type)
		{}
		Message(int type, const std::string& afilename)
			:type(type), filename(afilename)
		{}
	};
	eFixedMessagePump<Message> messages;
	static eBackgroundFileEraser *instance;
	void gotMessage(const Message &message);
	void thread();
	void idle();
	ePtr<eTimer> stop_thread_timer;
#ifndef SWIG
public:
#endif
	eBackgroundFileEraser();
	~eBackgroundFileEraser();
#ifdef SWIG
public:
#endif
	void erase(const std::string& filename);
	static eBackgroundFileEraser *getInstance() { return instance; }
};

#endif
