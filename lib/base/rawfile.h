#ifndef __lib_base_rawfile_h
#define __lib_base_rawfile_h

#include <string>
#include <lib/base/object.h>

class iDataSource: public iObject
{
public:
	virtual off_t lseek(off_t offset, int whence)=0;
	virtual ssize_t read(void *buf, size_t count)=0; /* NOTE: you must be able to handle short reads! */
	virtual off_t length()=0;
	virtual off_t position()=0;
	virtual int valid()=0;
	virtual eSingleLock &getLock()=0;
	virtual bool is_shared()=0;
};

class iDataSourcePositionRestorer
{
	ePtr<iDataSource> &m_source;
	off_t m_position;
public:
	iDataSourcePositionRestorer(ePtr<iDataSource> &source)
		:m_source(source)
	{
		if (m_source->is_shared())
			m_position = m_source->position();
	}
	~iDataSourcePositionRestorer()
	{
		if (m_source->is_shared())
			m_source->lseek(m_position, SEEK_SET);
	}
};

class eRawFile: public iDataSource
{
	DECLARE_REF(eRawFile);
	eSingleLock m_lock;
public:
	eRawFile();
	~eRawFile();
	int open(const char *filename, int cached = 0);
	void setfd(int fd);
	off_t lseek(off_t offset, int whence);
	int close();
	ssize_t read(void *buf, size_t count); /* NOTE: you must be able to handle short reads! */
	off_t length();
	off_t position();
	int valid();
	eSingleLock &getLock();
	bool is_shared() { return ref.count > 1; }
private:
	int m_fd;     /* for uncached */
	FILE *m_file; /* for cached */
	int m_cached;
	std::string m_basename;
	off_t m_splitsize, m_totallength, m_current_offset, m_base_offset, m_last_offset;
	int m_nrfiles;
	void scan();
	int m_current_file;
	int switchOffset(off_t off);
	FILE *openFileCached(int nr);
	int openFileUncached(int nr);
};

#endif
