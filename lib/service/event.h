#ifndef __lib_service_event_h
#define __lib_service_event_h

#include <time.h>
#include <lib/base/object.h>
#include <string>
class Event;

class eServiceEvent: public iObject
{
DECLARE_REF(eServiceEvent);
public:
	time_t m_begin;
	int m_duration;
	std::string m_event_name, m_description;
	// .. additional info
	
	RESULT parseFrom(Event *evt);
};

TEMPLATE_TYPEDEF(ePtr<eServiceEvent>, eServiceEventPtr);

class eDebugClass: public iObject
{
	DECLARE_REF(eDebugClass);
public:
	int x;
	static void getDebug(ePtr<eDebugClass> &ptr, int x) { ptr = new eDebugClass(x); }
	eDebugClass(int i) { printf("build debug class %d\n", i); x = i; }
	~eDebugClass() { printf("remove debug class %d\n", x); }
};

// TEMPLATE_TYPEDEF(ePtr<eDebugClass>, eDebugClassPtr);

#endif
