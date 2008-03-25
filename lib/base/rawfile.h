#ifndef __lib_base_rawfile_h
#define __lib_base_rawfile_h

#include <string>

class eRawFile
{
public:
	eRawFile();
	~eRawFile();
	
	int open(const char *filename, int cached = 0);
	void setfd(int fd);
	off_t lseek(off_t offset, int whence);
	int close();
	ssize_t read(void *buf, size_t count); /* NOTE: you must be able to handle short reads! */
	off_t length();
	int valid();
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
