#include <lib/base/init_num.h>
#include <lib/base/init.h>
#include <lib/service/servicem2ts.h>

DEFINE_REF(eServiceFactoryM2TS)

class eM2TSFile: public iDataSource
{
	DECLARE_REF(eM2TSFile);
	eSingleLock m_lock;
public:
	eM2TSFile(const char *filename, bool cached=false);
	~eM2TSFile();

	// iDataSource
	off_t lseek(off_t offset, int whence);
	ssize_t read(off_t offset, void *buf, size_t count);
	off_t length();
	int valid();
private:
	int m_fd;     /* for uncached */
	FILE *m_file; /* for cached */
	off_t m_current_offset, m_length;
	bool m_cached;
	off_t lseek_internal(off_t offset, int whence);
};

DEFINE_REF(eM2TSFile);

eM2TSFile::eM2TSFile(const char *filename, bool cached)
	:m_lock(false), m_fd(-1), m_file(NULL), m_current_offset(0), m_length(0), m_cached(cached)
{
	eDebug("eM2TSFile %p %s", this, filename);
	if (!m_cached)
		m_fd = ::open(filename, O_RDONLY | O_LARGEFILE);
	else
		m_file = ::fopen64(filename, "rb");
	if (valid())
		m_current_offset = m_length = lseek_internal(0, SEEK_END);
}

eM2TSFile::~eM2TSFile()
{
	eDebug("~eM2TSFile %p", this);
	if (m_cached)
	{
		if (m_file)
		{
			::fclose(m_file);
			m_file = 0;
		}
	}
	else
	{
		if (m_fd >= 0)
			::close(m_fd);
		m_fd = -1;
	}
}

off_t eM2TSFile::lseek(off_t offset, int whence)
{
	eSingleLocker l(m_lock);

	offset = offset * 192 / 188;
	ASSERT(!(offset % 192));

	if (offset != m_current_offset)
		m_current_offset = lseek_internal(offset, whence);

	return m_current_offset;
}

off_t eM2TSFile::lseek_internal(off_t offset, int whence)
{
	off_t ret;

	if (!m_cached)
		ret = ::lseek(m_fd, offset, whence);
	else
	{
		if (::fseeko(m_file, offset, whence) < 0)
			perror("fseeko");
		ret = ::ftello(m_file);
	}
	return ret <= 0 ? ret : ret*188/192;
}

ssize_t eM2TSFile::read(off_t offset, void *b, size_t count)
{
	eSingleLocker l(m_lock);
	unsigned char tmp[192];
	unsigned char *buf = (unsigned char*)b;
	size_t rd=0;

	offset = offset * 192 / 188;
	ASSERT(!(offset % 192));

	ASSERT(!(count % 188));

	if (offset != m_current_offset)
	{
		m_current_offset = lseek_internal(offset, SEEK_SET);
		if (m_current_offset < 0)
			return m_current_offset;
	}

	while (rd < count) {
		size_t ret;
		if (!m_cached)
			ret = ::read(m_fd, tmp, 192);
		else
			ret = ::fread(tmp, 1, 192, m_file);
		if (ret > 0)
			m_current_offset += ret;
		if (ret < 0 || ret < 192)
			return rd ? rd : ret;
		memcpy(buf+rd, tmp+4, 188);
		rd += 188;
	}

	return rd;
}

int eM2TSFile::valid()
{
	if (!m_cached)
		return m_fd != -1;
	else
		return !!m_file;
}

off_t eM2TSFile::length()
{
	return m_length;
}

eServiceFactoryM2TS::eServiceFactoryM2TS()
{
	ePtr<eServiceCenter> sc;
	eDebug("!!!!!!!!!!!!!!!!!!!eServiceFactoryM2TS");
	eServiceCenter::getPrivInstance(sc);
	if (sc)
	{
		std::list<std::string> extensions;
		extensions.push_back("m2ts");
		extensions.push_back("mts");
		sc->addServiceFactory(eServiceFactoryM2TS::id, this, extensions);
	}
}

eServiceFactoryM2TS::~eServiceFactoryM2TS()
{
	ePtr<eServiceCenter> sc;
	
	eServiceCenter::getPrivInstance(sc);
	if (sc)
		sc->removeServiceFactory(eServiceFactoryM2TS::id);
}

RESULT eServiceFactoryM2TS::play(const eServiceReference &ref, ePtr<iPlayableService> &ptr)
{
	ptr = new eServiceM2TS(ref);
	return 0;
}

RESULT eServiceFactoryM2TS::record(const eServiceReference &ref, ePtr<iRecordableService> &ptr)
{
	ptr=0;
	return -1;
}

RESULT eServiceFactoryM2TS::list(const eServiceReference &ref, ePtr<iListableService> &ptr)
{
	ptr=0;
	return -1;
}

RESULT eServiceFactoryM2TS::info(const eServiceReference &ref, ePtr<iStaticServiceInformation> &ptr)
{
	return 0;
}

RESULT eServiceFactoryM2TS::offlineOperations(const eServiceReference &ref, ePtr<iServiceOfflineOperations> &ptr)
{
	ptr = 0;
	return -1;
}

eServiceM2TS::eServiceM2TS(const eServiceReference &ref)
	:eDVBServicePlay(ref, NULL)
{
	eDebug("eServiceM2TS %p", this);
}

eServiceM2TS::~eServiceM2TS()
{
	eDebug("~eServiceM2TS %p", this);
}

ePtr<iDataSource> eServiceM2TS::createDataSource(const eServiceReferenceDVB &ref)
{
	ePtr<iDataSource> source = new eM2TSFile(ref.path.c_str());
	return source;
}

eAutoInitPtr<eServiceFactoryM2TS> init_eServiceFactoryM2TS(eAutoInitNumbers::service+1, "eServiceFactoryM2TS");
