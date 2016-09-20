#ifndef __lib_service_event_h
#define __lib_service_event_h

#ifndef SWIG
#include <time.h>
#include <list>
#include <string>
class Event;
#endif

#include <lib/base/object.h>
#include <lib/service/iservice.h>

SWIG_IGNORE(eComponentData);
struct eComponentData
{
	friend class eServiceEvent;
	DECLARE_REF(eComponentData);
	uint8_t m_streamContent;
	uint8_t m_componentType;
	uint8_t m_componentTag;
	std::string m_iso639LanguageCode;
	std::string m_text;
public:
	eComponentData(const eComponentData& d) { *this = d; }
	eComponentData() { m_streamContent = m_componentType = m_componentTag = 0; }
	int getStreamContent(void) const { return m_streamContent; }
	int getComponentType(void) const { return m_componentType; }
	int getComponentTag(void) const { return m_componentTag; }
	std::string getIso639LanguageCode(void) const { return m_iso639LanguageCode; }
	std::string getText(void) const { return m_text; }
};
SWIG_TEMPLATE_TYPEDEF(ePtr<eComponentData>, eComponentDataPtr);

SWIG_IGNORE(eGenreData);
struct eGenreData
{
	friend class eServiceEvent;
	DECLARE_REF(eGenreData);
	uint8_t m_level1;
	uint8_t m_level2;
	uint8_t m_user1;
	uint8_t m_user2;
public:
	eGenreData(const eGenreData& d) { *this = d; }
	eGenreData() { m_level1 = m_level2 = m_user1 = m_user2 = 0; }
	int getLevel1(void) const { return m_level1; }
	int getLevel2(void) const { return m_level2; }
	int getUser1(void) const { return m_user1; }
	int getUser2(void) const { return m_user2; }
};
SWIG_TEMPLATE_TYPEDEF(ePtr<eGenreData>, eGenreDataPtr);

SWIG_IGNORE(eParentalData);
struct eParentalData
{
	friend class eServiceEvent;
	DECLARE_REF(eParentalData);
	std::string m_country_code;
	uint8_t m_rating;
public:
	eParentalData(const eParentalData& d) { *this = d; }
	eParentalData() { m_country_code = ""; m_rating = 0; }
	std::string getCountryCode(void) const { return m_country_code; }
	int getRating(void) const { return m_rating; }
};
SWIG_TEMPLATE_TYPEDEF(ePtr<eParentalData>, eParentalDataPtr);


SWIG_ALLOW_OUTPUT_SIMPLE(eServiceReference);  // needed for SWIG_OUTPUT in eServiceEvent::getLinkageService

SWIG_IGNORE(eServiceEvent);
class eServiceEvent: public iObject
{
	DECLARE_REF(eServiceEvent);
	bool loadLanguage(Event *event, const std::string &lang, int tsidonid);
	std::list<eComponentData> m_component_data;
	std::list<eServiceReference> m_linkage_services;
	std::list<eGenreData> m_genres;
	std::list<eParentalData> m_ratings;
	time_t m_begin;
	int m_duration;
	int m_event_id;
	int m_pdc_pil;
	int m_running_status;
	std::string m_event_name, m_short_description, m_extended_description;
	static std::string m_language, m_language_alternative;
	// .. additional info
public:
#ifndef SWIG
	RESULT parseFrom(Event *evt, int tsidonid=0);
	RESULT parseFrom(const std::string& filename, int tsidonid=0);
	static void setEPGLanguage(const std::string& language) { m_language = language; }
	static void setEPGLanguageAlternative(const std::string& language) { m_language_alternative = language; }
#endif
	time_t getBeginTime() const { return m_begin; }
	int getDuration() const { return m_duration; }
	int getEventId() const { return m_event_id; }
	int getPdcPil() const { return m_pdc_pil; }
	int getRunningStatus() const { return m_running_status; }
	std::string getEventName() const { return m_event_name; }
	std::string getShortDescription() const { return m_short_description; }
	std::string getExtendedDescription() const { return m_extended_description; }
	std::string getBeginTimeString() const;
	SWIG_VOID(RESULT) getComponentData(ePtr<eComponentData> &SWIG_OUTPUT, int tagnum) const;
	PyObject *getComponentData() const;
	int getNumOfLinkageServices() const { return m_linkage_services.size(); }
	SWIG_VOID(RESULT) getLinkageService(eServiceReference &SWIG_OUTPUT, eServiceReference &parent, int num) const;
	SWIG_VOID(RESULT) getGenreData(ePtr<eGenreData> &SWIG_OUTPUT) const;
	PyObject *getGenreData() const;
	SWIG_VOID(RESULT) getParentalData(ePtr<eParentalData> &SWIG_OUTPUT) const;
	PyObject *getParentalData() const;
};
SWIG_TEMPLATE_TYPEDEF(ePtr<eServiceEvent>, eServiceEvent);
SWIG_EXTEND(ePtr<eServiceEvent>,
	static void setEPGLanguage(const std::string& language)
	{
		eServiceEvent::setEPGLanguage(language);
	}
);
SWIG_EXTEND(ePtr<eServiceEvent>,
	static void setEPGLanguageAlternative(const std::string& language)
	{
		eServiceEvent::setEPGLanguageAlternative(language);
	}
);

#ifndef SWIG
SWIG_IGNORE(eDebugClass);
class eDebugClass: public iObject
{
	DECLARE_REF(eDebugClass);
public:
	int x;
	static void getDebug(ePtr<eDebugClass> &ptr, int x) { ptr = new eDebugClass(x); }
	eDebugClass(int i) { printf("build debug class %d\n", i); x = i; }
	~eDebugClass() { printf("remove debug class %d\n", x); }
};
SWIG_TEMPLATE_TYPEDEF(ePtr<eDebugClass>, eDebugClassPtr);
#endif

#endif
