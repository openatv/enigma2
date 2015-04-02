#include <sys/types.h>
#include <sys/stat.h>
#include <lib/base/init_num.h>
#include <lib/base/init.h>
#include <lib/dvb/metaparser.h>
#include <lib/service/servicem2ts.h>

DEFINE_REF(eServiceFactoryM2TS)

class eM2TSFile: public iTsSource
{
	DECLARE_REF(eM2TSFile);
	eSingleLock m_lock;
public:
	eM2TSFile(const char *filename);
	~eM2TSFile();

	// iTsSource
	ssize_t read(off_t offset, void *buf, size_t count);
	off_t length();
	off_t offset();
	int valid();
private:
	int m_sync_offset;
	int m_fd;
	off_t m_current_offset;
	off_t m_length;
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
	int isPlayable(const eServiceReference &ref, const eServiceReference &ignore, bool simulate) { return 1; }
	int getInfo(const eServiceReference &ref, int w);
	std::string getInfoString(const eServiceReference &ref,int w);
	long long getFileSize(const eServiceReference &ref);
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
	ePtr<iTsSource> source = file;

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

long long eStaticServiceM2TSInformation::getFileSize(const eServiceReference &ref)
{
	return m_parser.m_filesize;
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

eM2TSFile::eM2TSFile(const char *filename):
	m_lock(),
	m_sync_offset(0),
	m_fd(::open(filename, O_RDONLY | O_LARGEFILE | O_CLOEXEC)),
	m_current_offset(0),
	m_length(0)
{
	if (m_fd != -1)
		m_current_offset = m_length = lseek_internal(0, SEEK_END);
}

eM2TSFile::~eM2TSFile()
{
	if (m_fd != -1)
		::close(m_fd);
}

off_t eM2TSFile::lseek_internal(off_t offset, int whence)
{
	off_t ret;

	ret = ::lseek(m_fd, offset, whence);
	return ret <= 0 ? ret : (ret % 192) + (ret*188) / 192;
}

ssize_t eM2TSFile::read(off_t offset, void *b, size_t count)
{
	eSingleLocker l(m_lock);
	unsigned char tmp[192*3];
	unsigned char *buf = (unsigned char*)b;

	size_t rd=0;
	offset = (offset % 188) + (offset * 192) / 188;

sync:
	if ((offset+m_sync_offset) != m_current_offset)
	{
//		eDebug("[eM2TSFile] seekTo %lld", offset+m_sync_offset);
		m_current_offset = lseek_internal(offset+m_sync_offset, SEEK_SET);
		if (m_current_offset < 0)
			return m_current_offset;
	}

	while (rd < count) {
		size_t ret;
		ret = ::read(m_fd, tmp, 192);
		if (ret < 0 || ret < 192)
			return rd ? rd : ret;

		if (tmp[4] != 0x47)
		{
			if (rd > 0) {
				eDebug("[eM2TSFile] short read at pos %lld async!!", m_current_offset);
				return rd;
			}
			else {
				int x=0;
				ret = ::read(m_fd, tmp+192, 384);

#if 0
				eDebugNoNewLineStart("[eM2TSFile] m2ts out of sync at pos %lld, real %lld:", offset + m_sync_offset, m_current_offset);
				for (; x < 192; ++x)
					eDebugNoNewLine(" %02x", tmp[x]);
				eDebugNoNewLine("\n");
				x=0;
#else
				eDebug("[eM2TSFile] m2ts out of sync at pos %lld, real %lld", offset + m_sync_offset, m_current_offset);
#endif
				for (; x < 192; ++x)
				{
					if (tmp[x] == 0x47 && tmp[x+192] == 0x47)
					{
						int add_offs = (x - 4);
						eDebug("[eM2TSFile] sync found at pos %d, sync_offset is now %d, old was %d", x, add_offs + m_sync_offset, m_sync_offset);
						m_sync_offset += add_offs;
						goto sync;
					}
				}
			}
		}

		memcpy(buf+rd, tmp+4, 188);

		rd += 188;
		m_current_offset += 188;
	}

	m_sync_offset %= 188;

	return rd;
}

int eM2TSFile::valid()
{
	return m_fd != -1;
}

off_t eM2TSFile::length()
{
	return m_length;
}

off_t eM2TSFile::offset()
{
	return m_current_offset;
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

ePtr<iTsSource> eServiceM2TS::createTsSource(eServiceReferenceDVB &ref, int packetsize)
{
	ePtr<iTsSource> source = new eM2TSFile(ref.path.c_str());
	return source;
}

RESULT eServiceM2TS::isCurrentlySeekable()
{
	return 1; // for fast winding we need index files... so only skip forward/backward yet
}

eAutoInitPtr<eServiceFactoryM2TS> init_eServiceFactoryM2TS(eAutoInitNumbers::service+1, "eServiceFactoryM2TS");
