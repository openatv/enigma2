#ifndef __lib_service_event_h
#define __lib_service_event_h

#include <time.h>
#include <lib/base/object.h>
#include <string>
class Event;

class eServiceEvent: public iObject
{
DECLARE_REF;
public:
	time_t m_begin;
	int m_duration;
	std::string m_event_name, m_description;
	// .. additional info
	
	RESULT parseFrom(Event *evt);
};

TEMPLATE_TYPEDEF(ePtr<eServiceEvent>, eServiceEventPtr);

#endif
