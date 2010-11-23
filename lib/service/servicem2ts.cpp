#include <lib/base/init_num.h>
#include <lib/base/init.h>
#include <lib/dvb/metaparser.h>
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

class eStaticServiceM2TSInformation: public iStaticServiceInformation
{
	DECLARE_REF(eStaticServiceM2TSInformation);
	eServiceReference m_ref;
	eDVBMetaParser m_parser;
public:
	eStaticServiceM2TSInformation(const eServiceReference &ref);
	RESULT getName(const eServiceReference &ref, std::string &name);
	int getLength(const eServiceReference &ref);
	RESULT getEvent(const eServiceReference &ref, ePtr<eServiceEvent> &SWIG_OUTPUT, time_t start_time);
	int isPlayable(const eServiceReference &ref, const eServiceReference &ignore) { return 1; }
	int getInfo(const eServiceReference &ref, int w);
	std::string getInfoString(const eServiceReference &ref,int w);
	PyObject *getInfoObject(const eServiceReference &r, int what);
};

DEFINE_REF(eStaticServiceM2TSInformation);

eStaticServiceM2TSInformation::eStaticServiceM2TSInformation(const eServiceReference &ref)
{
	m_ref = ref;
	m_parser.parseFile(ref.path);
}

RESULT eStaticServiceM2TSInformation::getName(const eServiceReference &ref, std::string &name)
{
	ASSERT(ref == m_ref);
	if (m_parser.m_name.size())
		name = m_parser.m_name;
	else
	{
		name = ref.path;
		size_t n = name.rfind('/');
		if (n != std::string::npos)
			name = name.substr(n + 1);
	}
	return 0;
}

int eStaticServiceM2TSInformation::getLength(const eServiceReference &ref)
{
	ASSERT(ref == m_ref);
	
	eDVBTSTools tstools;
	
	struct stat s;
	stat(ref.path.c_str(), &s);

	eM2TSFile *file = new eM2TSFile(ref.path.c_str());
	ePtr<iDataSource> source = file;

	if (!source->valid())
		return 0;

	tstools.setSource(source);

			/* check if cached data is still valid */
	if (m_parser.m_data_ok && (s.st_size == m_parser.m_filesize) && (m_parser.m_length))
		return m_parser.m_length / 90000;

	/* open again, this time with stream info */
	tstools.setSource(source, ref.path.c_str());

			/* otherwise, re-calc length and update meta file */
	pts_t len;
	if (tstools.calcLen(len))
		return 0;

	m_parser.m_length = len;
	m_parser.m_filesize = s.st_size;
	m_parser.updateMeta(ref.path);
	return m_parser.m_length / 90000;
}

int eStaticServiceM2TSInformation::getInfo(const eServiceReference &ref, int w)
{
	switch (w)
	{
	case iServiceInformation::sDescription:
		return iServiceInformation::resIsString;
	case iServiceInformation::sServiceref:
		return iServiceInformation::resIsString;
	case iServiceInformation::sFileSize:
		return m_parser.m_filesize;
	case iServiceInformation::sTimeCreate:
		if (m_parser.m_time_create)
			return m_parser.m_time_create;
		else
			return iServiceInformation::resNA;
	default:
		return iServiceInformation::resNA;
	}
}

std::string eStaticServiceM2TSInformation::getInfoString(const eServiceReference &ref,int w)
{
	switch (w)
	{
	case iServiceInformation::sDescription:
		return m_parser.m_description;
	case iServiceInformation::sServiceref:
		return m_parser.m_ref.toString();
	case iServiceInformation::sTags:
		return m_parser.m_tags;
	default:
		return "";
	}
}

PyObject *eStaticServiceM2TSInformation::getInfoObject(const eServiceReference &r, int what)
{
	switch (what)
	{
	case iServiceInformation::sFileSize:
		return PyLong_FromLongLong(m_parser.m_filesize);
	default:
		Py_RETURN_NONE;
	}
}

RESULT eStaticServiceM2TSInformation::getEvent(const eServiceReference &ref, ePtr<eServiceEvent> &evt, time_t start_time)
{
	if (!ref.path.empty())
	{
		ePtr<eServiceEvent> event = new eServiceEvent;
		std::string filename = ref.path;
		filename.erase(filename.length()-4, 2);
		filename+="eit";
		if (!event->parseFrom(filename, (m_parser.m_ref.getTransportStreamID().get()<<16)|m_parser.m_ref.getOriginalNetworkID().get()))
		{
			evt = event;
			return 0;
		}
	}
	evt = 0;
	return -1;
}

DEFINE_REF(eM2TSFile);

eM2TSFile::eM2TSFile(const char *filename, bool cached)
	:m_lock(false), m_fd(-1), m_file(NULL), m_current_offset(0), m_length(0), m_cached(cached)
{
	if (!m_cached)
		m_fd = ::open(filename, O_RDONLY | O_LARGEFILE);
	else
		m_file = ::fopen64(filename, "rb");
	if (valid())
		m_current_offset = m_length = lseek_internal(0, SEEK_END);
}

eM2TSFile::~eM2TSFile()
{
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

	offset = (offset * 192) / 188;
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
	return ret <= 0 ? ret : (ret*188)/192;
}

ssize_t eM2TSFile::read(off_t offset, void *b, size_t count)
{
	eSingleLocker l(m_lock);
	unsigned char tmp[192];
	unsigned char *buf = (unsigned char*)b;
	size_t rd=0;

	offset = (offset * 192) / 188;
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
		if (ret < 0 || ret < 192)
			return rd ? rd : ret;
		memcpy(buf+rd, tmp+4, 188);

		ASSERT(buf[rd] == 0x47);

		rd += 188;
		m_current_offset += 188;
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
	ptr=new eStaticServiceM2TSInformation(ref);
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
}

ePtr<iDataSource> eServiceM2TS::createDataSource(eServiceReferenceDVB &ref)
{
	ePtr<iDataSource> source = new eM2TSFile(ref.path.c_str());
	return source;
}

RESULT eServiceM2TS::isCurrentlySeekable()
{
	return 1; // for fast winding we need index files... so only skip forward/backward yet
}

eAutoInitPtr<eServiceFactoryM2TS> init_eServiceFactoryM2TS(eAutoInitNumbers::service+1, "eServiceFactoryM2TS");
