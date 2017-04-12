#include <lib/dvb/esection.h>
#include <lib/base/eerror.h>

void eGTable::sectionRead(const uint8_t *d)
{
	unsigned int last_section_number = d[7];
	m_table.flags &= ~eDVBTableSpec::tfAnyVersion;
	m_table.flags |= eDVBTableSpec::tfThisVersion;
	m_table.version = (d[5]>>1)&0x1F;

		/* if a section is missing, we retry reading the
		   whole data up to 5 times. if after that the
		   section is still missing, we timeout. */
	if (m_tries > 5 * totalSections(last_section_number))
	{
		timeout();
		return;
	}

	m_tries++;

	if (createTable(d[6], d, last_section_number + 1))
	{
		if (m_timeout)
			m_timeout->stop();
		if (m_reader)
		{
			m_reader->stop();
			m_reader=0;
		}
		m_sectionRead_conn=0;
		ready = 1;
		tableReady(error);
	} else if ((m_table.flags & eDVBTableSpec::tfHaveTimeout) && m_timeout)
		m_timeout->start(m_table.timeout, 1); // reset timeout
}

void eGTable::timeout()
{
	TABLE_eDebug("[eGTable] timeout %04x!", m_table.pid);
	if (m_reader)
	{
		m_reader->stop();
		m_reader=0;
	}
	m_sectionRead_conn=0;
	ready = 1;
	error = -1;
	tableReady(error);
}

eGTable::eGTable():
	error(0)
{
}

DEFINE_REF(eGTable);

RESULT eGTable::start(iDVBSectionReader *reader, const eDVBTableSpec &table)
{
	RESULT res;
	m_table = table;

	m_reader = reader;
	m_reader->connectRead(sigc::mem_fun(*this, &eGTable::sectionRead), m_sectionRead_conn);

	m_tries = 0;

	// setup filter struct
	eDVBSectionFilterMask mask;

	memset(&mask, 0, sizeof(mask));
	mask.pid   = m_table.pid;
	mask.flags = 0;

	if (m_table.flags & eDVBTableSpec::tfCheckCRC)
		mask.flags |= eDVBSectionFilterMask::rfCRC;

	if (m_table.flags & eDVBTableSpec::tfHaveTID)
	{
		mask.data[0] = m_table.tid;
		if (m_table.flags & eDVBTableSpec::tfHaveTIDMask)
			mask.mask[0] = m_table.tid_mask;
		else
			mask.mask[0] = 0xFF;
	}

	if (m_table.flags & eDVBTableSpec::tfHaveTIDExt)
	{
		mask.data[1] = m_table.tidext >> 8;
		mask.data[2] = m_table.tidext;
		if (m_table.flags & eDVBTableSpec::tfHaveTIDExtMask)
		{
			mask.mask[1] = m_table.tidext_mask >> 8;
			mask.mask[2] = m_table.tidext_mask;
		}
		else
		{
			mask.mask[1] = 0xFF;
			mask.mask[2] = 0xFF;
		}
	}

	if (!(m_table.flags & eDVBTableSpec::tfAnyVersion))
	{
		TABLE_eDebug("[eGTable] doing version filtering");
		mask.data[3] |= (m_table.version << 1)|1;
		mask.mask[3] |= 0x3f;
		if (!(m_table.flags & eDVBTableSpec::tfThisVersion))
			mask.mode[3] |= 0x3e; // negative filtering
	} else
		TABLE_eDebug("[eGTable] no version filtering");

	TABLE_eDebug("%04x:  %02x %02x %02x %02x %02x %02x",
		mask.pid,
		mask.data[0], mask.data[1], mask.data[2],
		mask.data[3], mask.data[4], mask.data[5]);
	TABLE_eDebug("mask:  %02x %02x %02x %02x %02x %02x",
		mask.mask[0], mask.mask[1], mask.mask[2],
		mask.mask[3], mask.mask[4], mask.mask[5]);
	TABLE_eDebug("mode:  %02x %02x %02x %02x %02x %02x",
		mask.mode[0], mask.mode[1], mask.mode[2],
		mask.mode[3], mask.mode[4], mask.mode[5]);

	if ((res = m_reader->start(mask)))
	{
		TABLE_eDebug("[eGTable] reader failed to start.");
		return res;
	}

	if (m_table.flags & eDVBTableSpec::tfHaveTimeout)
	{
		m_timeout = eTimer::create(eApp);
		m_timeout->start(m_table.timeout, 1); // begin timeout
		CONNECT(m_timeout->timeout, eGTable::timeout);
	}

	return 0;
}

RESULT eGTable::start(iDVBDemux *demux, const eDVBTableSpec &table)
{
	int res;
	ePtr<iDVBSectionReader> reader;
	res = demux->createSectionReader(eApp, reader);
	if (res)
		return res;
	return start(reader, table);
}

eGTable::~eGTable()
{
}

void eAUGTable::slotTableReady(int error)
{
	getNext(error);
}
