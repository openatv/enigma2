#ifndef __ATSC_H__
#define __ATSC_H__

#include <sys/types.h>
#include <lib/dvb/specs.h>

#include <dvbsi++/long_crc_section.h>
#include <dvbsi++/descriptor_container.h>

class StringSegment
{
protected:
	std::vector<uint8_t> dataBytes;
	uint8_t mode;
	uint8_t compression;

public:
	StringSegment(const uint8_t *const buffer);
	~StringSegment(void);

	const uint8_t getMode(void) const;
	const uint8_t getCompression(void) const;
	const std::vector<uint8_t> &getData(void) const;
	const std::string getValue(void) const;
};

class StringValue
{
protected:
	std::string iso639LanguageCode;
	uint32_t size;
	std::vector<StringSegment *> segments;

public:
	StringValue(const uint8_t *const buffer);
	~StringValue(void);

	const uint32_t getSize(void) const;
	const std::string &getIso639LanguageCode(void) const;
	const std::vector<StringSegment *> &getSegments(void) const;
	const std::string getValue(void) const;
};

typedef std::list<StringValue*> StringValueList;
typedef StringValueList::iterator StringValueListIterator;
typedef StringValueList::const_iterator StringValueListConstIterator;

class MultipleStringStructure
{
protected:
	StringValueList strings;

public:
	MultipleStringStructure(const uint8_t *const buffer);
	~MultipleStringStructure(void);

	const StringValueList *getStrings(void) const;
};

class VirtualChannel : public DescriptorContainer
{
protected:
	std::string name;
	unsigned transportStreamId : 16;
	unsigned serviceId : 16;
	unsigned sourceId : 16;
	unsigned serviceType : 6;
	unsigned accessControlled : 1;
	unsigned descriptorsLoopLength : 10;

public:
	VirtualChannel(const uint8_t *const buffer, bool terrestrial);
	~VirtualChannel(void);

	const std::string &getName(void) const;
	uint16_t getTransportStreamId(void) const;
	uint16_t getServiceId(void) const;
	uint16_t getSourceId(void) const;
	uint8_t getServiceType(void) const;
	uint16_t getDescriptorsLoopLength(void) const;
	bool isAccessControlled(void) const;
};

typedef std::list<VirtualChannel*> VirtualChannelList;
typedef VirtualChannelList::iterator VirtualChannelListIterator;
typedef VirtualChannelList::const_iterator VirtualChannelListConstIterator;

class VirtualChannelTableSection : public LongCrcSection
{
protected:
	unsigned transportStreamId : 16;
	unsigned versionNumber : 5;
	VirtualChannelList channels;

public:
	VirtualChannelTableSection(const uint8_t * const buffer);
	~VirtualChannelTableSection(void);

	static const uint16_t LENGTH = 4096;
	static const uint16_t PID = 0x1ffb;
	static const int TID = 0xc8;
	static const uint32_t TIMEOUT = 5000;

	uint8_t getVersion(void) const;
	uint16_t getTransportStreamId(void) const;
	const VirtualChannelList *getChannels(void) const;
};

class ExtendedChannelNameDescriptor : public Descriptor
{
protected:
	MultipleStringStructure *value;

public:
	ExtendedChannelNameDescriptor(const uint8_t * const buffer);
	~ExtendedChannelNameDescriptor(void);

	const std::string getName(void) const;
};

class SystemTimeTableSection : public DescriptorContainer, public LongCrcSection
{
protected:
	unsigned versionNumber : 5;
	unsigned systemTime : 32;
	unsigned gpsOffset : 8;

public:
	SystemTimeTableSection(const uint8_t * const buffer);
	~SystemTimeTableSection(void);

	static const uint16_t LENGTH = 4096;
	static const uint16_t PID = 0x1ffb;
	static const int TID = 0xcd;
	static const uint32_t TIMEOUT = 5000;

	uint8_t getVersion(void) const;
	uint32_t getSystemTime(void) const;
	uint8_t getGPSOffset(void) const;
};

class MasterGuideTable : public DescriptorContainer
{
protected:
	unsigned PID : 16;
	unsigned tableType : 16;
	unsigned numberBytes : 32;
	unsigned descriptorsLoopLength : 10;

public:
	MasterGuideTable(const uint8_t *const buffer);
	~MasterGuideTable(void);

	uint16_t getPID(void) const;
	uint16_t getTableType(void) const;
	uint32_t getNumberBytes(void) const;
	uint16_t getDescriptorsLoopLength(void) const;
};

typedef std::list<MasterGuideTable*> MasterGuideTableList;
typedef MasterGuideTableList::iterator MasterGuideTableListIterator;
typedef MasterGuideTableList::const_iterator MasterGuideTableListConstIterator;

class MasterGuideTableSection : public LongCrcSection
{
protected:
	unsigned versionNumber : 5;
	MasterGuideTableList tables;

public:
	MasterGuideTableSection(const uint8_t * const buffer);
	~MasterGuideTableSection(void);

	static const uint16_t LENGTH = 4096;
	static const uint16_t PID = 0x1ffb;
	static const int TID = 0xc7;
	static const uint32_t TIMEOUT = 1000;

	uint8_t getVersion(void) const;
	const MasterGuideTableList *getTables(void) const;
};

class ATSCEvent : public DescriptorContainer
{
protected:
	MultipleStringStructure *title;
	unsigned eventId : 14;
	unsigned startTime : 32;
	unsigned ETMLocation : 2;
	unsigned lengthInSeconds : 20;
	unsigned titleLength : 8;
	unsigned descriptorsLoopLength : 12;

public:
	ATSCEvent(const uint8_t *const buffer);
	~ATSCEvent(void);

	const std::string getTitle(const std::string &language) const;
	uint16_t getEventId(void) const;
	uint32_t getStartTime(void) const;
	uint8_t getETMLocation(void) const;
	uint32_t getLengthInSeconds(void) const;
	uint16_t getTitleLength(void) const;
	uint16_t getDescriptorsLoopLength(void) const;
};

typedef std::list<ATSCEvent*> ATSCEventList;
typedef ATSCEventList::iterator ATSCEventListIterator;
typedef ATSCEventList::const_iterator ATSCEventListConstIterator;

class ATSCEventInformationSection : public LongCrcSection
{
protected:
	unsigned versionNumber : 5;
	ATSCEventList events;

public:
	ATSCEventInformationSection(const uint8_t * const buffer);
	~ATSCEventInformationSection(void);

	static const uint16_t LENGTH = 4096;
	static const int TID = 0xcb;
	static const uint32_t TIMEOUT = 5000;

	uint8_t getVersion(void) const;
	const ATSCEventList *getEvents(void) const;
};

class ExtendedTextTableSection : public LongCrcSection
{
protected:
	unsigned versionNumber : 5;
	unsigned ETMId : 32;
	MultipleStringStructure *message;

public:
	ExtendedTextTableSection(const uint8_t * const buffer);
	~ExtendedTextTableSection(void);

	static const uint16_t LENGTH = 4096;
	static const int TID = 0xcc;
	static const uint32_t TIMEOUT = 10000;

	uint8_t getVersion(void) const;
	uint32_t getETMId(void) const;
	const std::string getMessage(const std::string &language) const;
};

struct eDVBVCTSpec
{
	eDVBTableSpec m_spec;
public:
	eDVBVCTSpec()
	{
		m_spec.pid      = VirtualChannelTableSection::PID;
		m_spec.tid      = VirtualChannelTableSection::TID;
		m_spec.tid_mask = 0xfe;
		m_spec.timeout  = VirtualChannelTableSection::TIMEOUT;
		m_spec.flags    = eDVBTableSpec::tfAnyVersion |
			eDVBTableSpec::tfHaveTID | eDVBTableSpec::tfHaveTIDMask |
			eDVBTableSpec::tfCheckCRC | eDVBTableSpec::tfHaveTimeout;
	}
	operator eDVBTableSpec &()
	{
		return m_spec;
	}
};

struct eDVBSTTSpec
{
	eDVBTableSpec m_spec;
public:
	eDVBSTTSpec()
	{
		m_spec.pid      = SystemTimeTableSection::PID;
		m_spec.tid      = SystemTimeTableSection::TID;
		m_spec.timeout  = SystemTimeTableSection::TIMEOUT;
		m_spec.flags    = eDVBTableSpec::tfAnyVersion |
			eDVBTableSpec::tfHaveTID |
			eDVBTableSpec::tfCheckCRC | eDVBTableSpec::tfHaveTimeout;
	}
	operator eDVBTableSpec &()
	{
		return m_spec;
	}
};

struct eATSCMGTSpec
{
	eDVBTableSpec m_spec;
public:
	eATSCMGTSpec()
	{
		m_spec.pid      = MasterGuideTableSection::PID;
		m_spec.tid      = MasterGuideTableSection::TID;
		m_spec.timeout  = MasterGuideTableSection::TIMEOUT;
		m_spec.flags    = eDVBTableSpec::tfAnyVersion |
			eDVBTableSpec::tfHaveTID |
			eDVBTableSpec::tfCheckCRC | eDVBTableSpec::tfHaveTimeout;
	}
	operator eDVBTableSpec &()
	{
		return m_spec;
	}
};

struct eATSCEITSpec
{
	eDVBTableSpec m_spec;
public:
	eATSCEITSpec(int pid, int source_id)
	{
		m_spec.pid      = pid;
		m_spec.tid      = ATSCEventInformationSection::TID;
		m_spec.tidext   = source_id;
		m_spec.timeout  = ATSCEventInformationSection::TIMEOUT;
		m_spec.flags    = eDVBTableSpec::tfAnyVersion |
			eDVBTableSpec::tfHaveTID | eDVBTableSpec::tfHaveTIDExt |
			eDVBTableSpec::tfCheckCRC | eDVBTableSpec::tfHaveTimeout;
	}
	operator eDVBTableSpec &()
	{
		return m_spec;
	}
};

struct eATSCETTSpec
{
	eDVBTableSpec m_spec;
public:
	eATSCETTSpec(int pid)
	{
		m_spec.pid      = pid;
		m_spec.tid      = ExtendedTextTableSection::TID;
		m_spec.timeout  = ExtendedTextTableSection::TIMEOUT;
		m_spec.flags    = eDVBTableSpec::tfAnyVersion |
			eDVBTableSpec::tfHaveTID |
			eDVBTableSpec::tfCheckCRC | eDVBTableSpec::tfHaveTimeout;
	}
	operator eDVBTableSpec &()
	{
		return m_spec;
	}
};

#endif
