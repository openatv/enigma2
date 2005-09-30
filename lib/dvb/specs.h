#ifndef __lib_dvb_specs_h
#define __lib_dvb_specs_h

#include <lib/dvb/idvb.h>
#include <lib/dvb/idemux.h>
#include <dvbsi++/program_map_section.h>
#include <dvbsi++/service_description_section.h>
#include <dvbsi++/network_information_section.h>
#include <dvbsi++/bouquet_association_section.h>
#include <dvbsi++/program_association_section.h>
#include <dvbsi++/event_information_section.h>

struct eDVBPMTSpec
{
	eDVBTableSpec m_spec;
public:
	eDVBPMTSpec(int pid, int sid)
	{
		m_spec.pid     = pid;
		m_spec.tid     = ProgramMapSection::TID;
		m_spec.tidext  = sid;
		m_spec.timeout = 20000; // ProgramMapSection::TIMEOUT;
		m_spec.flags   = eDVBTableSpec::tfAnyVersion | 
			eDVBTableSpec::tfHaveTID | eDVBTableSpec::tfHaveTIDExt | 
			eDVBTableSpec::tfCheckCRC | eDVBTableSpec::tfHaveTimeout;
	}
	operator eDVBTableSpec &()
	{
		return m_spec;
	}
};

struct eDVBSDTSpec
{
	eDVBTableSpec m_spec;
public:
	eDVBSDTSpec()
	{
		m_spec.pid     = ServiceDescriptionSection::PID;
		m_spec.tid     = ServiceDescriptionSection::TID;
		m_spec.timeout = 20000; // ServiceDescriptionSection::TIMEOUT;
		m_spec.flags   = eDVBTableSpec::tfAnyVersion |
			eDVBTableSpec::tfHaveTID | eDVBTableSpec::tfCheckCRC |
			eDVBTableSpec::tfHaveTimeout;
	}
	operator eDVBTableSpec &()
	{
		return m_spec;
	}
};

struct eDVBNITSpec
{
	eDVBTableSpec m_spec;
public:
	eDVBNITSpec()
	{
		m_spec.pid     = NetworkInformationSection::PID;
		m_spec.tid     = NetworkInformationSection::TID;
		m_spec.timeout = NetworkInformationSection::TIMEOUT;
		m_spec.flags   = eDVBTableSpec::tfAnyVersion |
			eDVBTableSpec::tfHaveTID | eDVBTableSpec::tfCheckCRC |
			eDVBTableSpec::tfHaveTimeout;
	}
	operator eDVBTableSpec &()
	{
		return m_spec;
	}
};

struct eDVBBATSpec
{
	eDVBTableSpec m_spec;
public:
	eDVBBATSpec()
	{
		m_spec.pid     = BouquetAssociationSection::PID;
		m_spec.tid     = BouquetAssociationSection::TID;
		m_spec.timeout = BouquetAssociationSection::TIMEOUT;
		m_spec.flags   = eDVBTableSpec::tfAnyVersion |
			eDVBTableSpec::tfHaveTID | eDVBTableSpec::tfCheckCRC |
			eDVBTableSpec::tfHaveTimeout;
	}
	operator eDVBTableSpec &()
	{
		return m_spec;
	}
};

struct eDVBPATSpec
{
	eDVBTableSpec m_spec;
public:
	eDVBPATSpec()
	{
		m_spec.pid     = ProgramAssociationSection::PID;
		m_spec.tid     = ProgramAssociationSection::TID;
		m_spec.timeout = 20000; // ProgramAssociationSection::TIMEOUT;
		m_spec.flags   = eDVBTableSpec::tfAnyVersion |
			eDVBTableSpec::tfHaveTID | eDVBTableSpec::tfCheckCRC |
			eDVBTableSpec::tfHaveTimeout;
	}
	operator eDVBTableSpec &()
	{
		return m_spec;
	}
};

class eDVBEITSpec
{
	eDVBTableSpec m_spec;
public:
		/* this is for now&next on actual transponder. */
	eDVBEITSpec(int sid)
	{
		m_spec.pid     = EventInformationSection::PID;
		m_spec.tid     = EventInformationSection::TID;
		m_spec.tidext  = sid;
		m_spec.timeout = EventInformationSection::TIMEOUT;
		m_spec.flags   = eDVBTableSpec::tfAnyVersion | 
			eDVBTableSpec::tfHaveTID | eDVBTableSpec::tfHaveTIDExt |
			eDVBTableSpec::tfCheckCRC | eDVBTableSpec::tfHaveTimeout;
	}
	operator eDVBTableSpec &()
	{
		return m_spec;
	}
};

#endif
