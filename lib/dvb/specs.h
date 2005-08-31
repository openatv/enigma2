#ifndef __lib_dvb_specs_h
#define __lib_dvb_specs_h

#include <lib/dvb/idvb.h>
#include <lib/dvb/idemux.h>
#include <lib/dvb_si/pmt.h>
#include <lib/dvb_si/sdt.h>
#include <lib/dvb_si/nit.h>
#include <lib/dvb_si/bat.h>
#include <lib/dvb_si/pat.h>
#include <lib/dvb_si/eit.h>

struct eDVBPMTSpec
{
	eDVBTableSpec m_spec;
public:
	eDVBPMTSpec(int pid, int sid)
	{
		m_spec.pid     = pid;
		m_spec.tid     = ProgramMapTable::TID;
		m_spec.tidext  = sid;
		m_spec.timeout = 20000; // ProgramMapTable::TIMEOUT;
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
		m_spec.pid     = ServiceDescriptionTable::PID;
		m_spec.tid     = ServiceDescriptionTable::TID;
		m_spec.timeout = 20000; // ServiceDescriptionTable::TIMEOUT;
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
		m_spec.pid     = NetworkInformationTable::PID;
		m_spec.tid     = NetworkInformationTable::TID;
		m_spec.timeout = NetworkInformationTable::TIMEOUT;
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
		m_spec.pid     = BouquetAssociationTable::PID;
		m_spec.tid     = BouquetAssociationTable::TID;
		m_spec.timeout = BouquetAssociationTable::TIMEOUT;
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
		m_spec.pid     = ProgramAssociationTable::PID;
		m_spec.tid     = ProgramAssociationTable::TID;
		m_spec.timeout = 20000; // ProgramAssociationTable::TIMEOUT;
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
		m_spec.pid     = EventInformationTable::PID;
		m_spec.tid     = EventInformationTable::TID;
		m_spec.tidext  = sid;
		m_spec.timeout = EventInformationTable::TIMEOUT;
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
