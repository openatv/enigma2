#ifndef __ATSC_H__
#define __ATSC_H__

#include <sys/types.h>

#include <dvbsi++/long_crc_section.h>
#include <dvbsi++/descriptor_container.h>

class VirtualChannel : public DescriptorContainer
{
protected:
	std::string name;
	unsigned transportStreamId : 16;
	unsigned serviceId : 16;
	unsigned serviceType : 6;
	unsigned accessControlled : 1;
	unsigned descriptorsLoopLength : 10;

public:
	VirtualChannel(const uint8_t *const buffer, bool terrestrial);
	~VirtualChannel(void);

	const std::string &getName(void) const;
	uint16_t getTransportStreamId(void) const;
	uint16_t getServiceId(void) const;
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

class ExtendedChannelNameDescriptor
{
protected:
	std::string name;

public:
	ExtendedChannelNameDescriptor(const uint8_t * const buffer);
	~ExtendedChannelNameDescriptor(void);

	const std::string &getName(void) const;
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
		m_spec.timeout  = VirtualChannelTableSection::TIMEOUT;
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
