#ifndef __esection_h
#define __esection_h

#include <lib/dvb/idemux.h>
#include <set>

#define TABLE_eDebug(x...) do { if (m_debug) eDebug(x); } while(0)
#define TABLE_eDebugNoNewLine(x...) do { if (m_debug) eDebugNoNewLine(x); } while(0)

class eGTable: public iObject, public Object
{
	DECLARE_REF(eGTable);
	ePtr<iDVBSectionReader> m_reader;
	eDVBTableSpec m_table;

	unsigned int m_tries;

	ePtr<eTimer> m_timeout;

	void sectionRead(const uint8_t *data);
	void timeout();
	ePtr<eConnection> m_sectionRead_conn;
protected:
	static const bool m_debug = false;
	virtual int createTable(unsigned int nr, const uint8_t *data, unsigned int max)=0;
	virtual unsigned int totalSections(unsigned int max) { return max + 1; }
public:
	Signal1<void, int> tableReady;
	eGTable();
	RESULT start(iDVBSectionReader *reader, const eDVBTableSpec &table);
	RESULT start(iDVBDemux *reader, const eDVBTableSpec &table);
	RESULT getSpec(eDVBTableSpec &spec) { spec = m_table; return 0; }
	virtual ~eGTable();
	int error;
	int ready;
};

template <class Section>
class eTable: public eGTable
{
private:
	std::vector<Section*> sections;
	std::set<int> avail;
	unsigned char m_section_data[4096];
protected:
	int createTable(unsigned int nr, const uint8_t *data, unsigned int max)
	{
		unsigned int ssize = sections.size();
		if (max < ssize || nr >= max)
		{
			TABLE_eDebug("kaputt max(%d) < ssize(%d) || nr(%d) >= max(%d)",
				max, ssize, nr, max);
			return 0;
		}
		if (avail.find(nr) != avail.end())
			delete sections[nr];

		memset(m_section_data, 0, 4096);
		memcpy(m_section_data, data, 4096);

		sections.resize(max);
		sections[nr] = new Section(data);
		avail.insert(nr);

		for (unsigned int i = 0; i < max; ++i)
			if (avail.find(i) != avail.end())
				TABLE_eDebugNoNewLine("+");
			else
				TABLE_eDebugNoNewLine("-");

		TABLE_eDebug(" %zd/%d TID %02x", avail.size(), max, data[0]);

		if (avail.size() == max)
		{
			TABLE_eDebug("done!");
			return 1;
		} else
			return 0;
	}
public:
	std::vector<Section*> &getSections() { return sections; }
	unsigned char* getBufferData() { return m_section_data; }
	~eTable()
	{
		for (std::set<int>::iterator i(avail.begin()); i != avail.end(); ++i)
			delete sections[*i];
	}
};

class eAUGTable: public Object
{
protected:
	void slotTableReady(int);
public:
	Signal1<void, int> tableReady;
	virtual void getNext(int err)=0;
};

template <class Table>
class eAUTable: public eAUGTable
{
	ePtr<Table> current, next;		// current is READY AND ERRORFREE, next is not yet ready
	int first;
	ePtr<iDVBDemux> m_demux;
	ePtr<iDVBSectionReader> m_reader;
	eMainloop *ml;

	/* needed to detect broken table version handling (seen on some m2ts files) */
	struct timespec m_prev_table_update;
	int m_table_cnt;

	void begin(eMainloop *m)
	{
		m_table_cnt = 0;
		ml = m;
		first= 1;
		current = 0;
		next = new Table();
		CONNECT(next->tableReady, eAUTable::slotTableReady);
	}

public:

	eAUTable()
	{
	}

	~eAUTable()
	{
		stop();
	}

	void stop()
	{
		current = next = 0;
		m_demux = 0;
		m_reader = 0;
	}

	int begin(eMainloop *m, const eDVBTableSpec &spec, ePtr<iDVBDemux> demux)
	{
		begin(m);
		m_demux = demux;
		m_reader = 0;
		next->start(demux, spec);
		return 0;
	}

	int begin(eMainloop *m, const eDVBTableSpec &spec, ePtr<iDVBSectionReader> reader)
	{
		begin(m);
		m_demux = 0;
		m_reader = reader;
		next->start(reader, spec);
		return 0;
	}

	int get()
	{
		if (current)
		{
			/*emit*/ tableReady(0);
			return 0;
		} else if (!next)
		{
			/*emit*/ tableReady(-1);
			return 0;
		} else
			return 1;
	}

	RESULT getCurrent(ePtr<Table> &ptr)
	{
		if (!current)
			return -1;
		ptr = current;
		return 0;
	}

#if 0
	void abort()
	{
		eDebug("eAUTable: aborted!");
		if (next)
			next->abort();
		delete next;
		next=0;
	}
#endif

	int ready()
	{
		return !!current;
	}

	void inject(Table *t)
	{
		next=t;
		getNext(0);
	}

	void getNext(int error)
	{
		current = 0;
		if (error)
		{
			next=0;
			if (first)
				/*emit*/ tableReady(error);
			first=0;
			return;
		} else
			current=next;

		next=0;
		first=0;

		ASSERT(current->ready);

		/*emit*/ tableReady(0);

		eDVBTableSpec spec;

		if (current && (!current->getSpec(spec)))
		{
			/* detect broken table version handling (seen on some m2ts files) */
			if (m_table_cnt)
			{
				if (abs(timeout_usec(m_prev_table_update)) > 500000)
					m_table_cnt = -1;
				else if (m_table_cnt > 1) // two pmt update within one second
				{
					eDebug("Seen two consecutive table version changes within 500ms. "
					    "This seems broken, so auto update for pid %04x, table %02x is now disabled!!",
					    spec.pid, spec.tid);
					m_table_cnt = 0;
					return;
				}
			}

			++m_table_cnt;
			clock_gettime(CLOCK_MONOTONIC, &m_prev_table_update);

			next = new Table();
			CONNECT(next->tableReady, eAUTable::slotTableReady);
			spec.flags &= ~(eDVBTableSpec::tfAnyVersion|eDVBTableSpec::tfThisVersion|eDVBTableSpec::tfHaveTimeout);
			if (m_demux)
			{
				next->eGTable::start(m_demux, spec);
			}
			else if (m_reader)
			{
				next->eGTable::start(m_reader, spec);
			}
		}
	}
};

#endif
