#ifndef __lib_service_event_h
#define __lib_service_event_h

#ifndef PYTHON
#include <time.h>
#include <lib/base/object.h>
#include <string>
class Event;
#endif

class eServiceEvent: public iObject
{
DECLARE_REF(eServiceEvent);
public:
#ifndef PYTHON
	time_t m_begin;
	int m_duration;
	std::string m_event_name, m_short_description, m_extended_description;
	// .. additional info
	bool loadLanguage(Event *event, std::string lang);
	RESULT parseFrom(Event *evt);
#endif
	time_t getBeginTime() { return m_begin; }
	int getDuration() { return m_duration; }
	std::string getEventName() { return m_event_name; }
	std::string getShortDescription() { return m_short_description; }
	std::string getExtendedDescription() { return m_extended_description; }
	std::string getBeginTimeString();
};

#ifndef PYTHON
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

#endif
