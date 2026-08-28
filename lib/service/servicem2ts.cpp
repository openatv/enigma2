#include <sys/types.h>
#include <sys/stat.h>
#include <algorithm>
#include <cerrno>
#include <condition_variable>
#include <cstdlib>
#include <cstring>
#include <mutex>
#include <thread>
#include <vector>
#include <lib/base/init_num.h>
#include <lib/base/init.h>
#include <lib/dvb/metaparser.h>
#include <lib/service/servicem2ts.h>

#ifdef HAVE_LIBBLURAY
extern "C" {
#include <libbluray/bluray.h>
}
#endif

#ifdef HAVE_LIBUDFREAD
extern "C" {
#include <udfread/udfread.h>
}
#endif

DEFINE_REF(eServiceFactoryM2TS)

#ifdef HAVE_LIBBLURAY
class eBlurayReadAhead;
#endif

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
	pts_t duration() const;
private:
	int m_sync_offset;
	int m_fd;
	off_t m_current_offset;
	off_t m_length;
	pts_t m_duration;
	off_t lseek_internal(off_t offset, int whence);
#ifdef HAVE_LIBBLURAY
	BLURAY *m_bluray;
	eBlurayReadAhead *m_bluray_reader;
#endif
#ifdef HAVE_LIBUDFREAD
	udfread *m_udf;
	UDFFILE *m_udf_file;
#endif
};

class eStaticServiceM2TSInformation: public iStaticServiceInformation
{
	DECLARE_REF(eStaticServiceM2TSInformation);
	eServiceReference m_ref;
	eDVBMetaParser m_parser;
	std::string m_txtdescription;
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
	m_txtdescription = m_parser.parseTxtFile(ref.path);
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

	struct stat s = {};
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
	case iServiceInformation::sExtendedDescription:
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
	case iServiceInformation::sExtendedDescription:
		return m_txtdescription;
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
		if (!event->parseFrom(filename, (m_parser.m_ref.getTransportStreamID().get()<<16)|m_parser.m_ref.getOriginalNetworkID().get(), m_parser.m_ref.getServiceID().get()))
		{
			evt = event;
			return 0;
		}
	}
	evt = 0;
	return -1;
}

DEFINE_REF(eM2TSFile);

static off_t m2tsToTsOffset(off_t offset)
{
	return offset <= 0 ? offset : (offset % 192) + (offset * 188) / 192;
}

static off_t tsToM2TSOffset(off_t offset)
{
	return offset <= 0 ? offset : (offset % 188) + (offset * 192) / 188;
}

#ifdef HAVE_LIBBLURAY
/*
 * Optical drives occasionally pause while repositioning or retrying a sector.
 * Feeding bd_read() directly from the PVR push thread exposes every such pause
 * to the decoders.  Keep a Blu-ray-only asynchronous reserve in front of that
 * thread.  The cache contains the original 192-byte M2TS packets; conversion to
 * 188-byte TS packets remains in eM2TSFile::read().
 */
class eBlurayReadAhead
{
public:
	explicit eBlurayReadAhead(BLURAY *bluray):
		m_bluray(bluray),
		m_buffer((32 * 1024 * 1024 / 192) * 192),
		m_readPosition(0),
		m_writePosition(0),
		m_buffered(0),
		m_bufferOffset(bd_tell(bluray)),
		m_seekTarget(0),
		m_generation(0),
		m_seekPending(false),
		m_seekInProgress(false),
		m_eof(false),
		m_error(false),
		m_stop(false),
		m_thread(&eBlurayReadAhead::run, this)
	{
		eDebug("[eBlurayReadAhead] started %zu MiB cache at position %jd",
				m_buffer.size() >> 20, (intmax_t)m_bufferOffset);
	}

	~eBlurayReadAhead()
	{
		{
			std::lock_guard<std::mutex> lock(m_mutex);
			m_stop = true;
			m_condition.notify_all();
		}
		if (m_thread.joinable())
			m_thread.join();
	}

	ssize_t read(off_t offset, void *data, size_t count)
	{
		if (!count)
			return 0;

		std::unique_lock<std::mutex> lock(m_mutex);
		if (offset != m_bufferOffset)
		{
			/* A small forward jump may still be inside the current cache. */
			if (offset > m_bufferOffset &&
					static_cast<uint64_t>(offset - m_bufferOffset) <= m_buffered)
			{
				size_t skip = offset - m_bufferOffset;
				m_readPosition = (m_readPosition + skip) % m_buffer.size();
				m_buffered -= skip;
				m_bufferOffset = offset;
				m_condition.notify_all();
			}
			else
			{
				++m_generation;
				m_seekTarget = offset;
				m_seekPending = true;
				m_eof = false;
				m_error = false;
				m_buffered = 0;
				m_readPosition = 0;
				m_writePosition = 0;
				m_condition.notify_all();
				m_condition.wait(lock, [this]() {
					return m_stop || (!m_seekPending && !m_seekInProgress);
				});
			}
		}

		size_t copied = 0;
		unsigned char *output = static_cast<unsigned char *>(data);
		while (copied < count && !m_stop)
		{
			m_condition.wait(lock, [this]() {
				return m_stop || m_buffered || m_eof || m_error ||
						m_seekPending || m_seekInProgress;
			});
			if (m_seekPending || m_seekInProgress)
				continue;
			if (!m_buffered)
				break;

			size_t bytes = std::min(count - copied, m_buffered);
			bytes = std::min(bytes, m_buffer.size() - m_readPosition);
			memcpy(output + copied, &m_buffer[m_readPosition], bytes);
			m_readPosition = (m_readPosition + bytes) % m_buffer.size();
			m_buffered -= bytes;
			m_bufferOffset += bytes;
			copied += bytes;
			m_condition.notify_all();
		}

		if (!copied && m_error)
		{
			errno = EIO;
			return -1;
		}
		return copied;
	}

private:
	static int64_t seekExact(BLURAY *bluray, int64_t target)
	{
		int64_t position = bd_seek(bluray, target);
		if (position < 0 || position > target)
			return -1;

		unsigned char discard[64 * 1024];
		while (position < target)
		{
			uint64_t remaining = target - position;
			int request = remaining < sizeof(discard) ? remaining : sizeof(discard);
			int bytes = bd_read(bluray, discard, request);
			if (bytes <= 0)
				return -1;
			position += bytes;
		}
		return position;
	}

	void run()
	{
		std::vector<unsigned char> input(512 * 1024);
		std::unique_lock<std::mutex> lock(m_mutex);
		while (!m_stop)
		{
			if (m_seekPending)
			{
				const int64_t target = m_seekTarget;
				const unsigned int generation = m_generation;
				m_seekPending = false;
				m_seekInProgress = true;
				lock.unlock();
				int64_t position = seekExact(m_bluray, target);
				lock.lock();
				if (generation == m_generation)
				{
					m_seekInProgress = false;
					m_error = position < 0;
					m_eof = false;
					m_bufferOffset = target;
					m_condition.notify_all();
				}
				continue;
			}

			if (m_eof || m_error || m_buffer.size() - m_buffered < 192)
			{
				m_condition.wait(lock, [this]() {
					return m_stop || m_seekPending ||
							(!m_eof && !m_error && m_buffer.size() - m_buffered >= 192);
				});
				continue;
			}

			size_t request = std::min(input.size(), m_buffer.size() - m_buffered);
			request -= request % 192;
			const unsigned int generation = m_generation;
			lock.unlock();
			int bytes = bd_read(m_bluray, input.data(), request);
			lock.lock();
			if (generation != m_generation)
				continue;
			if (bytes <= 0)
			{
				m_error = bytes < 0;
				m_eof = bytes == 0;
				m_condition.notify_all();
				continue;
			}

			size_t first = std::min(static_cast<size_t>(bytes),
					m_buffer.size() - m_writePosition);
			memcpy(&m_buffer[m_writePosition], input.data(), first);
			if (first < static_cast<size_t>(bytes))
				memcpy(&m_buffer[0], input.data() + first, bytes - first);
			m_writePosition = (m_writePosition + bytes) % m_buffer.size();
			m_buffered += bytes;
			m_condition.notify_all();
		}
	}

	BLURAY *m_bluray;
	std::vector<unsigned char> m_buffer;
	size_t m_readPosition;
	size_t m_writePosition;
	size_t m_buffered;
	int64_t m_bufferOffset;
	int64_t m_seekTarget;
	unsigned int m_generation;
	bool m_seekPending;
	bool m_seekInProgress;
	bool m_eof;
	bool m_error;
	bool m_stop;
	std::mutex m_mutex;
	std::condition_variable m_condition;
	std::thread m_thread;
};
#endif

eM2TSFile::eM2TSFile(const char *filename):
	m_lock(),
	m_sync_offset(0),
	m_fd(-1),
	m_current_offset(0),
	m_length(0),
	m_duration(0)
{
#ifdef HAVE_LIBUDFREAD
	m_udf = NULL;
	m_udf_file = NULL;
#endif
#ifdef HAVE_LIBBLURAY
	m_bluray = NULL;
	m_bluray_reader = NULL;
	const char *blurayScheme = "bluray://";
	if (!strncmp(filename, blurayScheme, strlen(blurayScheme)))
	{
		std::string uri = filename + strlen(blurayScheme);
		std::string keyfile;
		std::string menuLanguage;
		std::string audioLanguage;
		std::string countryCode;
		int title = -1;
		int region = 0;
		size_t queryPos = uri.find('?');
		std::string discPath = uri.substr(0, queryPos);
		if (queryPos != std::string::npos)
		{
			std::string query = uri.substr(queryPos + 1);
			size_t start = 0;
			while (start <= query.length())
			{
				size_t end = query.find('&', start);
				std::string option = query.substr(start, end - start);
				size_t separator = option.find('=');
				if (separator != std::string::npos)
				{
					std::string name = option.substr(0, separator);
					std::string value = option.substr(separator + 1);
					if (name == "title")
					{
						char *valueEnd = NULL;
						long parsed = strtol(value.c_str(), &valueEnd, 10);
						if (valueEnd != value.c_str() && !*valueEnd && parsed >= 0)
							title = parsed;
					}
					else if (name == "keyfile")
						keyfile = value;
					else if (name == "menu")
						menuLanguage = value;
					else if (name == "audio")
						audioLanguage = value;
					else if (name == "country")
						countryCode = value;
					else if (name == "region")
					{
						char *valueEnd = NULL;
						long parsed = strtol(value.c_str(), &valueEnd, 10);
						if (valueEnd != value.c_str() && !*valueEnd && (parsed == 1 || parsed == 2 || parsed == 4))
							region = parsed;
					}
				}
				if (end == std::string::npos)
					break;
				start = end + 1;
			}
		}

		if (!discPath.empty() && title >= 0)
		{
			m_bluray = bd_open(discPath.c_str(), keyfile.empty() ? NULL : keyfile.c_str());
			if (m_bluray)
			{
				if (!menuLanguage.empty())
				{
					bd_set_player_setting_str(m_bluray, BLURAY_PLAYER_SETTING_MENU_LANG, menuLanguage.c_str());
					bd_set_player_setting_str(m_bluray, BLURAY_PLAYER_SETTING_PG_LANG, menuLanguage.c_str());
				}
				if (!audioLanguage.empty())
					bd_set_player_setting_str(m_bluray, BLURAY_PLAYER_SETTING_AUDIO_LANG, audioLanguage.c_str());
				if (!countryCode.empty())
					bd_set_player_setting_str(m_bluray, BLURAY_PLAYER_SETTING_COUNTRY_CODE, countryCode.c_str());
				if (region)
					bd_set_player_setting(m_bluray, BLURAY_PLAYER_SETTING_REGION_CODE, region);
				int titleCount = bd_get_titles(m_bluray, TITLES_RELEVANT, 180);
				if (title >= titleCount || !bd_select_title(m_bluray, title))
				{
					eWarning("[eM2TSFile] unable to select Blu-ray title %d from '%s'", title, discPath.c_str());
					bd_close(m_bluray);
					m_bluray = NULL;
				}
				else
				{
					m_length = m2tsToTsOffset((off_t)bd_get_title_size(m_bluray));
					BLURAY_TITLE_INFO *titleInfo = bd_get_title_info(m_bluray, title, 0);
					if (titleInfo)
					{
						m_duration = titleInfo->duration;
						bd_free_title_info(titleInfo);
					}
					m_bluray_reader = new eBlurayReadAhead(m_bluray);
					eDebug("[eM2TSFile] opened Blu-ray title %d from '%s', size %jd, duration %jd",
							title, discPath.c_str(), (intmax_t)m_length, (intmax_t)m_duration);
				}
			}
		}
		if (!m_bluray)
			eWarning("[eM2TSFile] unable to open Blu-ray service '%s'", filename);
		return;
	}
#endif
#ifdef HAVE_LIBUDFREAD
	std::string udf_file = filename;
	size_t pos = udf_file.find("/BDMV");
	if (pos != std::string::npos && (udf_file.find(".iso") != std::string::npos || udf_file.find(".img") != std::string::npos || udf_file.find(".nrg") != std::string::npos))
	{
		eDebug("[eM2TSFile] try open as udf file:%s", filename);
		std::string file_path = udf_file.substr(pos);
		udf_file = udf_file.substr(0, pos);
		m_udf = udfread_init();
		if (m_udf)
		{
			if (udfread_open(m_udf, udf_file.c_str()) < 0)
				eDebug("[eM2TSFile] udfread_open(%s) failed!", udf_file.c_str());
			else
			{
				m_udf_file = udfread_file_open(m_udf, file_path.c_str());
				if (!m_udf_file)
				{
					eDebug("[eM2TSFile] udfread_file_open(%s) failed!", file_path.c_str());
					udfread_close(m_udf);
					m_udf = NULL;
				}
				else
					m_fd = 0;
			}
		}
	}
#endif
	if (m_fd == -1)
		m_fd = ::open(filename, O_RDONLY | O_LARGEFILE | O_CLOEXEC);

	if (m_fd != -1)
		m_current_offset = m_length = lseek_internal(0, SEEK_END);
}

eM2TSFile::~eM2TSFile()
{
#ifdef HAVE_LIBBLURAY
	delete m_bluray_reader;
	m_bluray_reader = NULL;
	if (m_bluray)
	{
		bd_close(m_bluray);
		m_bluray = NULL;
	}
#endif
#ifdef HAVE_LIBUDFREAD
	if (m_udf_file)
	{
		udfread_file_close(m_udf_file);
		udfread_close(m_udf);
		m_udf_file = NULL;
		m_udf = NULL;
		m_fd = -1;
	}
#endif
	if (m_fd != -1)
		::close(m_fd);
}

off_t eM2TSFile::lseek_internal(off_t offset, int whence)
{
	off_t ret;

#ifdef HAVE_LIBUDFREAD
	if (m_udf_file)
		ret = udfread_file_seek(m_udf_file, offset, whence);
	else
#endif
		ret = ::lseek(m_fd, offset, whence);
	return m2tsToTsOffset(ret);
}

ssize_t eM2TSFile::read(off_t offset, void *b, size_t count)
{
	eSingleLocker l(m_lock);
	unsigned char tmp[192*3];
	unsigned char *buf = (unsigned char*)b;

	size_t rd=0;
#ifdef HAVE_LIBBLURAY
	if (m_bluray_reader)
	{
		const off_t inputOffset = tsToM2TSOffset(offset);
		const size_t packets = count / 188;
		const size_t inputSize = packets * 192;
		std::vector<unsigned char> input(inputSize);
		ssize_t inputRead = m_bluray_reader->read(inputOffset, input.data(), inputSize);
		if (inputRead <= 0)
			return inputRead;

		const size_t completePackets = inputRead / 192;
		for (size_t packet = 0; packet < completePackets; ++packet)
		{
			const unsigned char *source = input.data() + packet * 192;
			if (source[4] != 0x47)
			{
				eWarning("[eM2TSFile] Blu-ray M2TS packet out of sync at pos %jd", (intmax_t)(inputOffset + packet * 192));
				break;
			}
			memcpy(buf + rd, source + 4, 188);
			rd += 188;
		}
		m_current_offset = offset + rd;
		return rd;
	}
#endif
	offset = tsToM2TSOffset(offset);

sync:
	if ((offset+m_sync_offset) != m_current_offset)
	{
//		eDebug("[eM2TSFile] seekTo %lld", offset+m_sync_offset);
		m_current_offset = lseek_internal(offset+m_sync_offset, SEEK_SET);
		if (m_current_offset < 0)
			return m_current_offset;
	}
	while (rd < count) {
		ssize_t ret;
#ifdef HAVE_LIBUDFREAD
		if (m_udf_file)
			ret = udfread_file_read(m_udf_file, tmp, 192);
		else
#endif
			ret = ::read(m_fd, tmp, 192);
		if (ret < 0 || ret < 192)
			return rd ? rd : ret;

		if (tmp[4] != 0x47)
		{
			if (rd > 0) {
				eDebug("[eM2TSFile] short read at pos %jd async!!", (intmax_t)m_current_offset);
				return rd;
			}
			else {
				int x=0;
#ifdef HAVE_LIBUDFREAD
				if (m_udf_file)
					ret = udfread_file_read(m_udf_file, tmp+192, 384);
				else
#endif
					ret = ::read(m_fd, tmp+192, 384);

#if 0
				eDebugNoNewLineStart("[eM2TSFile] m2ts out of sync at pos %lld, real %lld:", offset + m_sync_offset, m_current_offset);
				for (; x < 192; ++x)
					eDebugNoNewLine(" %02x", tmp[x]);
				eDebugNoNewLine("\n");
				x=0;
#else
				eDebug("[eM2TSFile] m2ts out of sync at pos %jd, real %jd", (intmax_t)(offset + m_sync_offset), (intmax_t)m_current_offset);
#endif
				for (; x < 192; ++x)
				{
					if (tmp[x] == 0x47 && tmp[x+192] == 0x47)
					{
						int add_offs = (x - 4);
						eDebug("[eM2TSFile] sync found at pos %d, sync_offset is now %d, old was %d", x, add_offs + m_sync_offset, m_sync_offset);
						m_sync_offset += add_offs;
						// FIXME do not use goto
						goto sync; // NOSONAR
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
#ifdef HAVE_LIBBLURAY
	if (m_bluray)
		return 1;
#endif
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

pts_t eM2TSFile::duration() const
{
	return m_duration;
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
	ptr = nullptr;
	return -1;
}

RESULT eServiceFactoryM2TS::list(const eServiceReference &ref, ePtr<iListableService> &ptr)
{
	ptr = nullptr;
	return -1;
}

RESULT eServiceFactoryM2TS::info(const eServiceReference &ref, ePtr<iStaticServiceInformation> &ptr)
{
	ptr = new eStaticServiceM2TSInformation(ref);
	return 0;
}

RESULT eServiceFactoryM2TS::offlineOperations(const eServiceReference &ref, ePtr<iServiceOfflineOperations> &ptr)
{
	ptr = nullptr;
	return -1;
}

eServiceM2TS::eServiceM2TS(const eServiceReference &ref)
	:eDVBServicePlay(ref, NULL),
	m_bluray_duration(0)
{
#ifdef HAVE_LIBBLURAY
	if (!ref.path.compare(0, 9, "bluray://"))
	{
		/*
		 * Keep the URI on the streamclient path.  Treating it as a regular PVR
		 * changes service startup and time handling, but transport controls still
		 * need a cue sheet for the local libbluray source.
		 */
		m_cue = new eCueSheet();
		eDebug("[eServiceM2TS] enabled transport controls for Blu-ray URI");
	}
#endif
}

RESULT eServiceM2TS::seek(ePtr<iSeekableService> &ptr)
{
#ifdef HAVE_LIBBLURAY
	if (!m_reference.path.compare(0, 9, "bluray://"))
	{
		ptr = this;
		return 0;
	}
#endif
	return eDVBServicePlay::seek(ptr);
}

RESULT eServiceM2TS::pause(ePtr<iPauseableService> &ptr)
{
#ifdef HAVE_LIBBLURAY
	if (!m_reference.path.compare(0, 9, "bluray://"))
	{
		ptr = this;
		return 0;
	}
#endif
	return eDVBServicePlay::pause(ptr);
}

ePtr<iTsSource> eServiceM2TS::createTsSource(eServiceReferenceDVB &ref, int packetsize)
{
	eM2TSFile *file = new eM2TSFile(ref.path.c_str());
	if (!ref.path.compare(0, 9, "bluray://"))
		m_bluray_duration = file->duration();
	ePtr<iTsSource> source = file;
	return source;
}

RESULT eServiceM2TS::getLength(pts_t &len)
{
	if (m_bluray_duration > 0)
	{
		len = m_bluray_duration;
		return 0;
	}
	return eDVBServicePlay::getLength(len);
}

RESULT eServiceM2TS::isCurrentlySeekable()
{
	return 1; // for fast winding we need index files... so only skip forward/backward yet
}

RESULT eServiceM2TS::getName(std::string &name)
{
#ifdef HAVE_LIBBLURAY
	if (!m_reference.path.compare(0, 9, "bluray://") && !m_reference.name.empty())
	{
		name = m_reference.name;
		return 0;
	}
#endif
	return eDVBServicePlay::getName(name);
}

eAutoInitPtr<eServiceFactoryM2TS> init_eServiceFactoryM2TS(eAutoInitNumbers::service+1, "eServiceFactoryM2TS");
