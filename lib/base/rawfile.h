#ifndef __lib_base_rawfile_h
#define __lib_base_rawfile_h

#include <string>
#include <vector>
#include <lib/base/itssource.h>

class eRawFile: public iTsSource
{
	DECLARE_REF(eRawFile);
	eSingleLock m_lock;
public:
	eRawFile(unsigned int packetsize = 188);
	~eRawFile();
	int open(const char *filename);

	// iTsSource
	ssize_t read(off_t offset, void *buf, size_t count);
	off_t length();
	off_t offset();
	int valid();
private:
	int m_fd;
	std::vector<off_t> m_file_offsets;
	off_t m_totallength;
	off_t m_last_offset;
	int m_current_file;
	std::string m_basename;

	int close();
	int scan();
	off_t switchOffset(off_t off);
	std::string _filename(int nr) const;
	int openFileUncached(int nr);
};

#endif
