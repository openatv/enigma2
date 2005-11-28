#ifndef __lib_service_event_h
#define __lib_service_event_h

#ifndef SWIG
#include <time.h>
#include <lib/base/object.h>
#include <list>
#include <string>
class Event;
#endif

class eServiceEvent: public iObject
{
DECLARE_REF(eServiceEvent);
#ifndef SWIG
	bool loadLanguage(Event *event, std::string lang, int tsidonid);
#endif
public:
#ifndef SWIG
	struct linkage_service
	{
		uint16_t sid;
		uint16_t onid;
		uint16_t tsid;
		std::string description;
	};
	std::list<linkage_service> m_linkage_services;
	time_t m_begin;
	int m_duration;
	std::string m_event_name, m_short_description, m_extended_description;
	// .. additional info
	RESULT parseFrom(Event *evt, int tsidonid=0);
#endif
	time_t getBeginTime() { return m_begin; }
	int getDuration() { return m_duration; }
	std::string getEventName() { return m_event_name; }
	std::string getShortDescription() { return m_short_description; }
	std::string getExtendedDescription() { return m_extended_description; }
	std::string getBeginTimeString();
};

TEMPLATE_TYPEDEF(ePtr<eServiceEvent>, eServiceEventPtr);
#ifndef SWIG

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
