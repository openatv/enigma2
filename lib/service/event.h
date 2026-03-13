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
#include <lib/dvb/atsc.h>

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
#ifndef SWIG
	eComponentData& operator =(const eComponentData &) = default;
#endif
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
#ifndef SWIG
	eGenreData& operator =(const eGenreData &) = default;
#endif
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
#ifndef SWIG
	eParentalData& operator =(const eParentalData &) = default;
#endif
	eParentalData() { m_country_code = ""; m_rating = 0; }
	std::string getCountryCode(void) const { return m_country_code; }
	int getRating(void) const { return m_rating; }
};
SWIG_TEMPLATE_TYPEDEF(ePtr<eParentalData>, eParentalDataPtr);


struct eCridData_ENUMS
{
	// CRID matches are for all CRIDs of that class:
	// SERIES_MATCH matches both SERIES and SERIES_AU
	enum {
		EPISODE = 0x1,
		SERIES = 0x2,
		RECOMMENDATION = 0x3,

		// Australian CRID types are 0x31-0x33
		// FreeTV Australia Operational Practice
		// OP-72: Implementation of Content Reference
		// IDs by Australian Television Broadcasters

		OFFSET_AU = 0x30,
		EPISODE_AU = EPISODE + OFFSET_AU,
		SERIES_AU = SERIES + OFFSET_AU,
		RECOMMENDATION_AU = RECOMMENDATION + OFFSET_AU,
	};
};

SWIG_IGNORE(eCridData);
struct eCridData: public eCridData_ENUMS
{
	friend class eServiceEvent;
	DECLARE_REF(eCridData);
	uint8_t m_type;
	uint8_t m_location;
	std::string m_crid;
public:
	eCridData(const eCridData& d) { *this = d; }
	eCridData() { m_crid = ""; m_type = 0; m_location = 0; }
	int getLocation(void) const { return m_location; }
	int getType(void) const { return m_type; }
	std::string getCrid(void) const { return m_crid; }
};
SWIG_TEMPLATE_TYPEDEF(ePtr<eCridData>, eCridDataPtr);


SWIG_ALLOW_OUTPUT_SIMPLE(eServiceReference);  // needed for SWIG_OUTPUT in eServiceEvent::getLinkageService

struct eServiceEventEnums
{
public:
	// CRID matches are for all CRIDs of that class:
	// SERIES_MATCH matches both SERIES and SERIES_AU
	enum {
		SERIES_MATCH = 1 << eCridData::SERIES,
		EPISODE_MATCH = 1 << eCridData::EPISODE,
		RECOMMENDATION_MATCH = 1 << eCridData::RECOMMENDATION,
		ALL_MATCH = SERIES_MATCH | EPISODE_MATCH | RECOMMENDATION_MATCH,
	};
};

SWIG_IGNORE(eServiceEvent);
class eServiceEvent: public iObject
{
	DECLARE_REF(eServiceEvent);
	static std::string crid_scheme;
	static std::string normalise_crid(std::string crid, ePtr<eDVBService> service);
	bool loadLanguage(Event *event, const std::string &lang, int tsidonid, int sid);
	std::list<eComponentData> m_component_data;
	std::list<eServiceReference> m_linkage_services;
	std::list<eGenreData> m_genres;
	std::list<eParentalData> m_ratings;
	time_t m_begin;
	int m_duration;
	int m_event_id;
	int m_pdc_pil;
	int m_running_status;
	std::string m_event_name, m_short_description, m_extended_description, m_extra_event_data, m_epg_source, m_extended_description_items;
	std::string m_series_crid, m_episode_crid, m_recommendation_crid;
	static std::string m_language, m_language_alternative;
	std::list<eCridData> m_crids;
	static int m_UTF8CorrectMode;
	// .. additional info
public:
	eServiceEvent();
#ifndef SWIG
	RESULT parseFrom(Event *evt, int tsidonid, int sid);
	RESULT parseFrom(Event *evt, int tsidonid=0);
	RESULT parseFrom(ATSCEvent *evt);
	RESULT parseFrom(const ExtendedTextTableSection *sct);
	RESULT parseFrom(const std::string& filename, int tsidonid, int sid);
	RESULT parseFrom(const std::string& filename, int tsidonid=0);
	static void setEPGLanguage(const std::string& language) { m_language = language; }
	static void setEPGLanguageAlternative(const std::string& language) { m_language_alternative = language; }
	static void setUTF8CorrectMode (int mode) { m_UTF8CorrectMode = mode; }
	void setExtendedDescription (const std::string& value) { m_extended_description = value; }
	void setShortDescription (const std::string& value) { m_short_description = value; }
	void setEventName (const std::string& value) { m_event_name = value; }
	void setDuration (int value) { m_duration = value; }
#endif
	time_t getBeginTime() const { return m_begin; }
	int getDuration() const { return m_duration; }
	int getEventId() const { return m_event_id; }
	int getPdcPil() const { return m_pdc_pil; }
	int getRunningStatus() const { return m_running_status; }
	std::string getEventName() const { return m_event_name; }
	std::string getShortDescription() const { return m_short_description; }
	std::string getExtendedDescription() const { return m_extended_description; }
	std::string getExtraEventData() const { return m_extra_event_data; }
	std::string getEPGSource() const { return m_epg_source; }
	std::string getBeginTimeString() const;
	std::string getSeriesCRID() const { return m_series_crid; }
	std::string getEpisodeCRID() const { return m_episode_crid; }
	std::string getRecommendationCRID() const { return m_recommendation_crid; }
	SWIG_VOID(RESULT) getComponentData(ePtr<eComponentData> &SWIG_OUTPUT, int tagnum) const;
	// Naming to parallel getGenreDataList & getParentalDataList
	PyObject *getComponentDataList() const;
	PyObject *getComponentData() const
	{
		return getComponentDataList();
	}
	int getNumOfLinkageServices() const { return m_linkage_services.size(); }
	SWIG_VOID(RESULT) getLinkageService(eServiceReference &SWIG_OUTPUT, eServiceReference &parent, int num) const;
	SWIG_VOID(RESULT) getGenreData(ePtr<eGenreData> &SWIG_OUTPUT) const;
	PyObject *getGenreDataList() const;
#ifndef SWIG
	// Deprecated, doesn't differentiate from
	// getGenreData(ePtr<eGenreData> &SWIG_OUTPUT) in Python
	PyObject *getGenreData() const
	{
		return getGenreDataList();
	}
#endif
	SWIG_VOID(RESULT) getParentalData(ePtr<eParentalData> &SWIG_OUTPUT) const;
	PyObject *getParentalDataList() const;
#ifndef SWIG
	// Deprecated, doesn't differentiate from
	// getParentalData(ePtr<eParentalData> &SWIG_OUTPUT) in Python
	PyObject *getParentalData() const
	{
		return getParentalDataList();
	}
#endif

	PyObject *getCridData(int mask) const;
	static void setDebug(bool debug) {m_Debug = debug;}
	private:
		static bool m_Debug;
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
SWIG_EXTEND(ePtr<eServiceEvent>,
	static void setUTF8CorrectMode(int mode)
	{
		eServiceEvent::setUTF8CorrectMode(mode);
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
