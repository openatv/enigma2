#ifndef __service_ievent_h
#define __service_ievent_h

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

#endif
