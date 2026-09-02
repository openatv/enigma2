#include <lib/service/servicedab.h>
#include <lib/service/dabdecoder.h>
#include <lib/service/dabpacketdecoder.h>
#include <lib/service/dabspi.h>

#include <algorithm>
#include <cerrno>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <ctime>
#include <fstream>
#include <iterator>
#include <limits>
#include <map>
#include <sstream>

#include <arpa/inet.h>
#include <fcntl.h>
#include <poll.h>
#include <signal.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <sys/wait.h>
#include <unistd.h>

#include <gst/gst.h>

#include <lib/base/eerror.h>
#include <lib/base/init.h>
#include <lib/base/init_num.h>
#include <lib/base/nconfig.h>
#include <lib/base/esimpleconfig.h>
#include <lib/dvb/decoder.h>
#include <lib/dvb/epgcache.h>
#include <lib/dvb/metaparser.h>
#include <lib/service/dabdebug.h>
#include <lib/service/service.h>

namespace
{
constexpr size_t DAB_TS_PACKET_SIZE = 188;
constexpr size_t PSI_MAX_SIZE = 0x0fff;
constexpr uint64_t LOAS_PROBE_MS = 8000;
constexpr uint64_t LOAS_PROBE_OVERRUNS = 3;
constexpr uint16_t DAB_LIVE_EPG_EVENT_ID = 0xdab0;
constexpr int DAB_LIVE_EPG_WINDOW = 4 * 60 * 60;

/* Latched when a sink advertises LOAS but does not consume it. */
bool &loasSinkRejected()
{
	static bool rejected = false;
	return rejected;
}

uint64_t monotonicMilliseconds()
{
	struct timespec now = {};
	clock_gettime(CLOCK_MONOTONIC, &now);
	return static_cast<uint64_t>(now.tv_sec) * 1000 + static_cast<uint64_t>(now.tv_nsec / 1000000);
}

std::string dabName(const eServiceReference &ref)
{
	if (!ref.name.empty())
		return ref.name;
	char text[48];
	snprintf(text, sizeof(text), "DAB service 0x%04x", ref.getUnsignedData(6) & 0xffff);
	return text;
}

std::string dabCacheDirectory()
{
	/* /media/hdd is backed by the configured disk or network mount. Images
	 * therefore survive a reboot when storage is available; on diskless boxes
	 * OpenATV provides the same path in volatile storage. */
	const char *directory = "/media/hdd/dab-cache";
	if ((mkdir(directory, 0755) == 0 || errno == EEXIST) && access(directory, W_OK | X_OK) == 0)
		return directory;
	directory = "/tmp";
	return directory;
}

bool parseSPIImageName(const std::string &name, uint32_t &serviceId, unsigned int &width, unsigned int &height)
{
	/* Broadcasters use several SPI logo naming schemes.  NDR prefixes the
	 * service id (e.g. e0_d882_320x240_3.png), while the national ensemble
	 * starts with it (e.g. d210_Dlf_320x240.png).  WDR also uses a hyphen
	 * after the id. */
	for (size_t marker = 0; marker + 4 < name.size(); ++marker)
	{
		if (marker && name[marker - 1] != '_')
			continue;
		char *end = nullptr;
		const unsigned long value = strtoul(name.c_str() + marker, &end, 16);
		if (end != name.c_str() + marker + 4 || value == 0 || value > 0xffff || (*end != '_' && *end != '-'))
			continue;
		serviceId = static_cast<uint32_t>(value);
		width = 0;
		height = 0;
		for (size_t dimension = name.find('_', marker + 4); dimension != std::string::npos; dimension = name.find('_', dimension + 1))
		{
			char *widthEnd = nullptr;
			const unsigned long parsedWidth = strtoul(name.c_str() + dimension + 1, &widthEnd, 10);
			if (widthEnd == name.c_str() + dimension + 1 || *widthEnd != 'x')
				continue;
			char *heightEnd = nullptr;
			const unsigned long parsedHeight = strtoul(widthEnd + 1, &heightEnd, 10);
			if (heightEnd == widthEnd + 1 || (*heightEnd != '_' && *heightEnd != '.' && *heightEnd != '\0'))
				continue;
			if (parsedWidth && parsedWidth <= 8192 && parsedHeight && parsedHeight <= 8192)
			{
				width = static_cast<unsigned int>(parsedWidth);
				height = static_cast<unsigned int>(parsedHeight);
			}
			break;
		}
		return true;
	}
	return false;
}
}

class eDABFrontendData : public iDVBFrontendData
{
	DECLARE_REF(eDABFrontendData);

public:
	int getNumber() const override { return -1; }
	std::string getTypeDescription() const override { return "DAB+ USB"; }
};

class eDABFrontendStatus : public iDVBFrontendStatus
{
	DECLARE_REF(eDABFrontendStatus);

public:
	eDABFrontendStatus(bool synced, int quality, int snrCentidB)
		: m_synced(synced), m_quality(quality), m_snr_centidb(snrCentidB) { }

	int getState() const override { return m_synced ? stateLock : stateTuning; }
	std::string getStateDescription() const override { return m_synced ? "LOCKED" : "TUNING"; }
	int getLocked() const override { return m_synced; }
	int getSynced() const override { return m_synced; }
	int getBER() const override { return 0; }
	int getSNR() const override { return m_synced && m_quality >= 0 ? m_quality * 65535 / 100 : 0; }
	int getSNRdB() const override { return m_synced ? m_snr_centidb : -1; }
	int getSignalPower() const override { return 0; }

private:
	bool m_synced;
	int m_quality;
	int m_snr_centidb;
};

DEFINE_REF(eDABFrontendData);
DEFINE_REF(eDABFrontendStatus);

eDABWorkerStats::eDABWorkerStats()
	: bytes(0), tsPackets(0), syncErrors(0), continuityErrors(0), mpeSections(0),
	  udpPackets(0), ediPackets(0), afPackets(0), etiFrames(0), ficFrames(0),
	  mscFrames(0), audioFrames(0), crcErrors(0), padPackets(0), dlsLabels(0),
	  motSegments(0), motDataGroups(0), slides(0), serviceRevision(0), spiRevision(0), dlPlusRevision(0), logoRevision(0), ensembleId(0),
	  serviceCount(0), slideFormat(0), bitrate(0), snrCentidB(-1), ficQuality(-1), mscQuality(-1), rfSynced(false),
	  serviceFound(false), dabplus(false), error(0)
{
	memset(services, 0, sizeof(services));
	serviceLabel[0] = 0;
	ensembleLabel[0] = 0;
	dynamicLabel[0] = 0;
	dlPlusItemTitle[0] = 0;
	dlPlusItemArtist[0] = 0;
	dlPlusItemGenre[0] = 0;
	dlPlusProgrammeNow[0] = 0;
	dlPlusProgrammeNext[0] = 0;
	dlPlusProgrammePart[0] = 0;
	dlPlusProgrammeHost[0] = 0;
	tunerName[0] = 0;
	language[0] = 0;
	programType[0] = 0;
	protection[0] = 0;
}

eDABWorker::eDABWorker(int fd, int pid, eDABTransport transport, uint32_t destinationIp, uint16_t destinationPort,
	uint32_t serviceId, uint16_t ensembleId, const AudioCallback &audioCallback,
	const ImageCallback &imageCallback, const MOTCallback &motCallback,
	eFixedMessagePump<eDABWorkerStats> &pump)
	: m_fd(fd), m_pid(pid), m_transport(transport), m_destination_ip(destinationIp), m_destination_port(destinationPort),
	  m_pump(pump), m_stop(false), m_started(false), m_last_cc(-1),
	  m_last_publish_ms(0), m_section_expected(0),
	  m_decoder(new eDABDecoder(serviceId, ensembleId, audioCallback, imageCallback,
		[this, motCallback](const uint8_t *data, size_t length, int contentType, int contentSubType,
			const std::string &contentName, uint16_t transportId) {
			if (!motCallback)
				return;
			const int result = motCallback(data, length, contentType, contentSubType, contentName, transportId);
			if (result & 1)
				++m_stats.spiRevision;
			if (result & 2)
				++m_stats.logoRevision;
			if (result)
				m_publish_pending = true;
		}))
{
	m_input.reserve(DAB_TS_PACKET_SIZE * 512);
	m_section.reserve(PSI_MAX_SIZE);
	if (m_transport != DAB_TRANSPORT_MPE_EDI)
		m_ts_adapter.reset(new eDABTSAdapter(m_transport, [this](const uint8_t *frame, size_t length) {
			m_decoder->feedETI(frame, length);
			updateDecoderStats();
		}));
}

eDABWorker::~eDABWorker()
{
	stop();
}

bool eDABWorker::start()
{
	if (m_started)
		return true;
	m_stop = false;
	m_started = run() == 0;
	return m_started;
}

void eDABWorker::stop()
{
	if (!m_started)
		return;
	m_stop = true;
	shutdown(m_fd, SHUT_RD);
	kill();
	m_started = false;
}

void eDABWorker::thread()
{
	hasStarted();
	if (nice(5) == -1)
		eDABDebug("[eDABWorker] unable to lower worker priority: %m");

	uint8_t buffer[32768];
	while (!m_stop)
	{
		struct pollfd descriptor = {};
		descriptor.fd = m_fd;
		descriptor.events = POLLIN;
		const int result = poll(&descriptor, 1, 250);
		if (result < 0)
		{
			if (errno == EINTR)
				continue;
			m_stats.error = errno;
			break;
		}
		if (result > 0 && (descriptor.revents & (POLLERR | POLLHUP | POLLNVAL)))
		{
			if (!m_stop)
				m_stats.error = EPIPE;
			break;
		}
		if (result > 0 && (descriptor.revents & POLLIN))
		{
			const ssize_t received = read(m_fd, buffer, sizeof(buffer));
			if (received > 0)
			{
				m_stats.bytes += static_cast<uint64_t>(received);
				processInput(buffer, static_cast<size_t>(received));
			}
			else if (received == 0)
			{
				if (!m_stop)
					m_stats.error = EPIPE;
				break;
			}
			else if (errno != EINTR && errno != EAGAIN)
			{
				m_stats.error = errno;
				break;
			}
		}
		publish();
	}
	publish(true);
}

void eDABWorker::processInput(const uint8_t *data, size_t length)
{
	m_input.insert(m_input.end(), data, data + length);
	size_t offset = 0;
	while (m_input.size() - offset >= DAB_TS_PACKET_SIZE)
	{
		if (m_input[offset] != 0x47)
		{
			++m_stats.syncErrors;
			++offset;
			continue;
		}
		if (m_input.size() - offset >= DAB_TS_PACKET_SIZE * 2 && m_input[offset + DAB_TS_PACKET_SIZE] != 0x47)
		{
			++m_stats.syncErrors;
			++offset;
			continue;
		}
		processTSPacket(&m_input[offset]);
		offset += DAB_TS_PACKET_SIZE;
	}
	if (offset)
		m_input.erase(m_input.begin(), m_input.begin() + offset);
}

void eDABWorker::processTSPacket(const uint8_t *packet)
{
	if (packet[0] != 0x47 || (packet[1] & 0x80))
		return;
	const int pid = ((packet[1] & 0x1f) << 8) | packet[2];
	if (pid != m_pid)
		return;
	++m_stats.tsPackets;

	const bool payloadPresent = packet[3] & 0x10;
	const bool adaptationPresent = packet[3] & 0x20;
	const int cc = packet[3] & 0x0f;
	if (payloadPresent && m_last_cc >= 0)
	{
		if (cc == m_last_cc)
			return;  // A packet may be sent twice, feeding it again would corrupt the section.
		if (((m_last_cc + 1) & 0x0f) != cc)
		{
			++m_stats.continuityErrors;
			clearSection();
			if (m_ts_adapter)
				m_ts_adapter->reset();
		}
	}
	if (payloadPresent)
		m_last_cc = cc;
	if (!payloadPresent)
		return;

	size_t offset = 4;
	if (adaptationPresent)
	{
		const size_t adaptationLength = packet[4];
		offset += adaptationLength + 1;
		if (offset >= DAB_TS_PACKET_SIZE)
			return;
	}
	if (m_transport == DAB_TRANSPORT_MPE_EDI)
		processPayload(packet + offset, DAB_TS_PACKET_SIZE - offset, packet[1] & 0x40);
	else if (m_ts_adapter)
		m_ts_adapter->feedPayload(packet + offset, DAB_TS_PACKET_SIZE - offset, packet[1] & 0x40);
}

void eDABWorker::processPayload(const uint8_t *payload, size_t length, bool unitStart)
{
	if (!length)
		return;
	if (!unitStart)
	{
		appendSection(payload, length);
		return;
	}

	const size_t pointer = payload[0];
	++payload;
	--length;
	if (pointer > length)
	{
		clearSection();
		return;
	}
	if (!m_section.empty() && pointer)
		appendSection(payload, pointer);
	payload += pointer;
	length -= pointer;
	if (!m_section.empty())
		clearSection();
	parseNewSections(payload, length);
}

void eDABWorker::appendSection(const uint8_t *data, size_t length)
{
	if (m_section.empty())
		return;
	size_t offset = 0;
	if (!m_section_expected)
	{
		const size_t headerBytes = std::min<size_t>(3 - m_section.size(), length);
		m_section.insert(m_section.end(), data, data + headerBytes);
		offset += headerBytes;
		if (m_section.size() < 3)
			return;
		m_section_expected = 3 + (((m_section[1] & 0x0f) << 8) | m_section[2]);
		if (m_section_expected <= 3 || m_section_expected > PSI_MAX_SIZE)
		{
			clearSection();
			return;
		}
	}
	const size_t wanted = m_section_expected > m_section.size() ? m_section_expected - m_section.size() : 0;
	const size_t copy = std::min(wanted, length - offset);
	m_section.insert(m_section.end(), data + offset, data + offset + copy);
	if (m_section.size() == m_section_expected)
	{
		processMPESection(m_section.data(), m_section.size());
		clearSection();
	}
}

void eDABWorker::parseNewSections(const uint8_t *data, size_t length)
{
	while (length && data[0] != 0xff)
	{
		if (length < 3)
		{
			m_section.assign(data, data + length);
			m_section_expected = 0;
			return;
		}
		const size_t sectionLength = 3 + (((data[1] & 0x0f) << 8) | data[2]);
		if (sectionLength <= 3 || sectionLength > PSI_MAX_SIZE)
			return;
		if (sectionLength > length)
		{
			m_section.assign(data, data + length);
			m_section_expected = sectionLength;
			return;
		}
		processMPESection(data, sectionLength);
		data += sectionLength;
		length -= sectionLength;
	}
}

void eDABWorker::processMPESection(const uint8_t *section, size_t length)
{
	if (section[0] != 0x3e)
		return;
	++m_stats.mpeSections;
	if (length < 12 + 20 + 8 + 4)
		return;

	const uint8_t *ip = section + 12;
	if ((ip[0] >> 4) != 4 || ip[9] != 17)
		return;
	const size_t ipHeaderLength = static_cast<size_t>(ip[0] & 0x0f) * 4;
	if (ipHeaderLength < 20 || 12 + ipHeaderLength + 8 > length - 4)
		return;
	const size_t ipLength = (static_cast<size_t>(ip[2]) << 8) | ip[3];
	if (ipLength < ipHeaderLength + 8 || 12 + ipLength > length - 4)
		return;

	uint32_t destinationIp = 0;
	memcpy(&destinationIp, ip + 16, sizeof(destinationIp));
	const uint8_t *udp = ip + ipHeaderLength;
	const uint16_t destinationPort = static_cast<uint16_t>((udp[2] << 8) | udp[3]);
	const size_t udpLength = (static_cast<size_t>(udp[4]) << 8) | udp[5];
	if (udpLength < 8 || udpLength > ipLength - ipHeaderLength)
		return;
	if (m_destination_ip && destinationIp != m_destination_ip)
		return;
	if (m_destination_port && destinationPort != m_destination_port)
		return;

	++m_stats.udpPackets;
	const uint8_t *edi = udp + 8;
	const size_t ediLength = udpLength - 8;
	if (ediLength >= 2 && ((edi[0] == 'A' && edi[1] == 'F') || (edi[0] == 'P' && edi[1] == 'F')))
	{
		++m_stats.ediPackets;
		m_decoder->feedEDI(edi, ediLength);
		updateDecoderStats();
	}
}

void eDABWorker::updateDecoderStats()
{
	m_stats.afPackets = m_decoder->afPackets();
	m_stats.etiFrames = m_decoder->etiFrames();
	m_stats.ficFrames = m_decoder->ficFrames();
	m_stats.mscFrames = m_decoder->mscFrames();
	m_stats.audioFrames = m_decoder->audioFrames();
	m_stats.crcErrors = m_decoder->crcErrors();
	m_stats.padPackets = m_decoder->padPackets();
	m_stats.dlsLabels = m_decoder->dlsLabels();
	m_stats.motSegments = m_decoder->motSegments();
	m_stats.motDataGroups = m_decoder->motDataGroups();
	m_stats.slides = m_decoder->slides();
	m_stats.slideFormat = m_decoder->slideFormat();
	m_stats.bitrate = m_decoder->bitrate();
	m_stats.serviceFound = m_decoder->serviceFound();
	m_stats.dabplus = m_decoder->isDABPlus();
	strncpy(m_stats.serviceLabel, m_decoder->serviceLabel().c_str(), sizeof(m_stats.serviceLabel) - 1);
	m_stats.serviceLabel[sizeof(m_stats.serviceLabel) - 1] = 0;
	strncpy(m_stats.ensembleLabel, m_decoder->ensembleLabel().c_str(), sizeof(m_stats.ensembleLabel) - 1);
	m_stats.ensembleLabel[sizeof(m_stats.ensembleLabel) - 1] = 0;
	strncpy(m_stats.dynamicLabel, m_decoder->dynamicLabel().c_str(), sizeof(m_stats.dynamicLabel) - 1);
	m_stats.dynamicLabel[sizeof(m_stats.dynamicLabel) - 1] = 0;
	m_stats.dlPlusRevision = m_decoder->dlPlusRevision();
	strncpy(m_stats.dlPlusItemTitle, m_decoder->dlPlusItemTitle().c_str(), sizeof(m_stats.dlPlusItemTitle) - 1);
	m_stats.dlPlusItemTitle[sizeof(m_stats.dlPlusItemTitle) - 1] = 0;
	strncpy(m_stats.dlPlusItemArtist, m_decoder->dlPlusItemArtist().c_str(), sizeof(m_stats.dlPlusItemArtist) - 1);
	m_stats.dlPlusItemArtist[sizeof(m_stats.dlPlusItemArtist) - 1] = 0;
	strncpy(m_stats.dlPlusItemGenre, m_decoder->dlPlusItemGenre().c_str(), sizeof(m_stats.dlPlusItemGenre) - 1);
	m_stats.dlPlusItemGenre[sizeof(m_stats.dlPlusItemGenre) - 1] = 0;
	strncpy(m_stats.dlPlusProgrammeNow, m_decoder->dlPlusProgrammeNow().c_str(), sizeof(m_stats.dlPlusProgrammeNow) - 1);
	m_stats.dlPlusProgrammeNow[sizeof(m_stats.dlPlusProgrammeNow) - 1] = 0;
	strncpy(m_stats.dlPlusProgrammeNext, m_decoder->dlPlusProgrammeNext().c_str(), sizeof(m_stats.dlPlusProgrammeNext) - 1);
	m_stats.dlPlusProgrammeNext[sizeof(m_stats.dlPlusProgrammeNext) - 1] = 0;
	strncpy(m_stats.dlPlusProgrammePart, m_decoder->dlPlusProgrammePart().c_str(), sizeof(m_stats.dlPlusProgrammePart) - 1);
	m_stats.dlPlusProgrammePart[sizeof(m_stats.dlPlusProgrammePart) - 1] = 0;
	strncpy(m_stats.dlPlusProgrammeHost, m_decoder->dlPlusProgrammeHost().c_str(), sizeof(m_stats.dlPlusProgrammeHost) - 1);
	m_stats.dlPlusProgrammeHost[sizeof(m_stats.dlPlusProgrammeHost) - 1] = 0;
	if (m_stats.serviceRevision != m_decoder->serviceRevision())
	{
		m_publish_pending = true;  // A scan waits for this to stop changing.
		const std::vector<eDABDecoder::ServiceInfo> services = m_decoder->serviceList();
		m_stats.serviceRevision = m_decoder->serviceRevision();
		m_stats.ensembleId = m_decoder->ensembleId();
		m_stats.serviceCount = std::min<int>(services.size(), DAB_MAX_SCANNED_SERVICES);
		for (int i = 0; i < m_stats.serviceCount; ++i)
		{
			m_stats.services[i].serviceId = services[i].serviceId;
			m_stats.services[i].bitrate = services[i].bitrate;
			m_stats.services[i].dabplus = services[i].dabplus;
			strncpy(m_stats.services[i].label, services[i].label.c_str(), sizeof(m_stats.services[i].label) - 1);
			m_stats.services[i].label[sizeof(m_stats.services[i].label) - 1] = 0;
		}
	}
}

void eDABWorker::clearSection()
{
	m_section.clear();
	m_section_expected = 0;
}

void eDABWorker::publish(bool force)
{
	const uint64_t now = monotonicMilliseconds();
	if (!force && !m_publish_pending && now - m_last_publish_ms < 1000)
		return;
	m_publish_pending = false;
	m_last_publish_ms = now;
	m_pump.send(m_stats);
}

/*
 * RTL-SDR is intentionally kept out of the Enigma2 main loop.  This worker
 * owns the optional userspace receiver backend and forwards compressed LOAS
 * audio plus small metadata updates.  No DVB frontend is registered for the
 * USB device, so it cannot accidentally be allocated for TV reception.
 */
class eDABSDRWorker : private eThread
{
public:
	typedef std::function<void(const uint8_t *, size_t)> LOASCallback;
	typedef std::function<void(const uint8_t *, size_t, int)> ImageCallback;
	typedef std::function<bool(const std::string &, const std::string &)> SPIImageCallback;
	typedef std::function<int(const std::string &)> SPICallback;
	typedef std::function<int(const uint8_t *, size_t, int, int,
		const std::string &, uint16_t)> MOTCallback;

	eDABSDRWorker(const std::string &channel, uint32_t serviceId, const std::string &motCachePrefix, const LOASCallback &loasCallback,
		const ImageCallback &imageCallback, const SPIImageCallback &spiImageCallback,
		const SPICallback &spiCallback, const MOTCallback &motCallback,
		eFixedMessagePump<eDABWorkerStats> &pump)
		: m_channel(channel), m_service_id(serviceId), m_mot_cache_prefix(motCachePrefix), m_loas_callback(loasCallback),
		  m_image_callback(imageCallback), m_spi_image_callback(spiImageCallback), m_spi_callback(spiCallback),
		  m_mot_callback(motCallback),
		  m_pump(pump), m_stop(false), m_started(false),
		  m_child_pid(-1), m_stdin_fd(-1), m_last_publish_ms(0), m_last_loas_ms(0)
	{
		/* eConfigManager belongs to Enigma2's main thread. Cache every setting
		 * before eThread::run() starts instead of querying it from thread(). */
		m_ppm = configValue("config.dab.rtlsdr.ppm", "0");
		m_device = configValue("config.dab.rtlsdr.deviceIndex", "0");
		m_automatic_gain = eConfigManager::getConfigBoolValue("config.dab.rtlsdr.automaticGain", true);
		m_gain = configValue("config.dab.rtlsdr.gain", "35");
		m_loas.reserve(32768);
		m_stderr.reserve(4096);
	}

	~eDABSDRWorker()
	{
		stop();
	}

	bool start()
	{
		if (m_started)
			return true;
		m_stop = false;
		m_started = run() == 0;
		return m_started;
	}

	void stop()
	{
		if (!m_started)
			return;
		m_stop = true;
		const int child = m_child_pid.load();
		if (child > 0)
			::kill(child, SIGTERM);
		if (m_stdin_fd >= 0)
		{
			close(m_stdin_fd);
			m_stdin_fd = -1;
		}
		eThread::kill();
		m_started = false;
	}

private:
	static std::string configValue(const char *key, const char *fallback)
	{
		const std::string value = eConfigManager::getConfigValue(key);
		return value.empty() ? fallback : value;
	}

	static std::string jsonValue(const std::string &line, const char *key)
	{
		const std::string marker = std::string("\"") + key + "\":\"";
		const size_t begin = line.find(marker);
		if (begin == std::string::npos)
			return std::string();
		const size_t valueBegin = begin + marker.size();
		std::string value;
		bool escaped = false;
		for (size_t index = valueBegin; index < line.size(); ++index)
		{
			const char character = line[index];
			if (escaped)
			{
				switch (character)
				{
				case 'n': value += '\n'; break;
				case 'r': value += '\r'; break;
				case 't': value += '\t'; break;
				case '\\': value += '\\'; break;
				case '"': value += '"'; break;
				default: value += character; break;
				}
				escaped = false;
			}
			else if (character == '\\')
				escaped = true;
			else if (character == '"')
				return value;
			else
				value += character;
		}
		return std::string();
	}

	void thread() override
	{
		int audioPipe[2] = {-1, -1};
		int errorPipe[2] = {-1, -1};
		int inputPipe[2] = {-1, -1};
		if (pipe(audioPipe) || pipe(errorPipe) || pipe(inputPipe))
		{
			m_stats.error = errno;
			closePipes(audioPipe, errorPipe, inputPipe);
			hasStarted();
			publish(true);
			return;
		}

		std::string sid;
		if (m_service_id)
		{
			char text[16];
			snprintf(text, sizeof(text), "%x", m_service_id);
			sid = text;
		}
		std::vector<std::string> arguments;
		const char *backend = "/usr/bin/dab-rtlsdr-welle-e2";
		arguments.push_back(backend);
		arguments.push_back("-C");
		arguments.push_back(m_channel);
		arguments.push_back("-p");
		arguments.push_back(m_ppm);
		arguments.push_back("-D");
		arguments.push_back(m_device);
		if (!m_mot_cache_prefix.empty())
		{
			arguments.push_back("-Z");
			arguments.push_back(m_mot_cache_prefix);
		}
		arguments.push_back(m_automatic_gain ? "-Q" : "-G");
		if (!m_automatic_gain)
			arguments.push_back(m_gain);
		if (!sid.empty())
		{
			arguments.push_back("-S");
			arguments.push_back(sid);
		}
		std::vector<char *> argv;
		for (size_t index = 0; index < arguments.size(); ++index)
			argv.push_back(const_cast<char *>(arguments[index].c_str()));
		argv.push_back(nullptr);

		const pid_t child = fork();
		if (child < 0)
		{
			m_stats.error = errno;
			closePipes(audioPipe, errorPipe, inputPipe);
			hasStarted();
			publish(true);
			return;
		}
		if (child == 0)
		{
			dup2(inputPipe[0], STDIN_FILENO);
			dup2(audioPipe[1], STDOUT_FILENO);
			dup2(errorPipe[1], STDERR_FILENO);
			closePipes(audioPipe, errorPipe, inputPipe);
			execv(argv[0], argv.data());
			_exit(127);
		}

		m_child_pid = child;
		eDABDebug("[eDABSDRWorker] using receiver backend '%s'", backend);
		close(audioPipe[1]);
		close(errorPipe[1]);
		close(inputPipe[0]);
		m_stdin_fd = inputPipe[1];
#ifdef F_SETPIPE_SZ
		/* SPI directories can deliver dozens of logo objects in one burst.
		 * Their callbacks perform file/cache work in this reader thread, so a
		 * small kernel pipe would otherwise make the decoder block on stdout
		 * and temporarily starve the audio pipeline. */
		fcntl(audioPipe[0], F_SETPIPE_SZ, 1024 * 1024);
#endif
		fcntl(audioPipe[0], F_SETFL, fcntl(audioPipe[0], F_GETFL) | O_NONBLOCK);
		fcntl(errorPipe[0], F_SETFL, fcntl(errorPipe[0], F_GETFL) | O_NONBLOCK);
		hasStarted();
		eDABDebug("[eDABSDRWorker] started channel=%s sid=%08x device=%s gain=%s",
			m_channel.c_str(), m_service_id, m_device.c_str(), m_automatic_gain ? "automatic" : m_gain.c_str());

		bool audioOpen = true;
		bool errorOpen = true;
		while (!m_stop && (audioOpen || errorOpen))
		{
			struct pollfd descriptors[2] = {};
			descriptors[0].fd = audioPipe[0];
			descriptors[0].events = audioOpen ? POLLIN : 0;
			descriptors[1].fd = errorPipe[0];
			descriptors[1].events = errorOpen ? POLLIN : 0;
			const int result = poll(descriptors, 2, 250);
			if (result < 0 && errno != EINTR)
			{
				m_stats.error = errno;
				break;
			}
			if (audioOpen && result > 0 && descriptors[0].revents)
				audioOpen = readAudio(audioPipe[0]);
			if (errorOpen && result > 0 && descriptors[1].revents)
				errorOpen = readMetadata(errorPipe[0], audioPipe[0], audioOpen);
			publish();
		}

		if (!m_stop)
		{
			int status = 0;
			if (waitpid(child, &status, 0) == child && (!WIFEXITED(status) || WEXITSTATUS(status)))
				m_stats.error = WIFEXITED(status) && WEXITSTATUS(status) == 22 ? ETIMEDOUT : EPIPE;
		}
		else
		{
			::kill(child, SIGTERM);
			for (int retry = 0; retry < 20; ++retry)
			{
				int status = 0;
				if (waitpid(child, &status, WNOHANG) == child)
					break;
				usleep(50000);
				if (retry == 19)
				{
					::kill(child, SIGKILL);
					waitpid(child, &status, 0);
				}
			}
		}
		m_child_pid = -1;
		close(audioPipe[0]);
		close(errorPipe[0]);
		if (m_stdin_fd >= 0)
		{
			close(m_stdin_fd);
			m_stdin_fd = -1;
		}
		publish(true);
	}

	static void closePipes(int (&audioPipe)[2], int (&errorPipe)[2], int (&inputPipe)[2])
	{
		for (int index = 0; index < 2; ++index)
		{
			if (audioPipe[index] >= 0)
				close(audioPipe[index]);
			if (errorPipe[index] >= 0)
				close(errorPipe[index]);
			if (inputPipe[index] >= 0)
				close(inputPipe[index]);
		}
	}

	bool readAudio(int fd)
	{
		uint8_t buffer[32768];
		const ssize_t bytes = read(fd, buffer, sizeof(buffer));
		if (bytes > 0)
		{
			m_stats.bytes += bytes;
			m_loas.insert(m_loas.end(), buffer, buffer + bytes);
			while (m_loas.size() >= 3)
			{
				if (m_loas[0] != 0x56 || (m_loas[1] & 0xe0) != 0xe0)
				{
					m_loas.erase(m_loas.begin());
					continue;
				}
				const size_t frameLength = 3 + ((static_cast<size_t>(m_loas[1] & 0x1f) << 8) | m_loas[2]);
				if (m_loas.size() < frameLength)
					break;
				const uint64_t now = monotonicMilliseconds();
				if (m_last_loas_ms && now - m_last_loas_ms > 750)
					eWarning("[eDABSDRWorker] LOAS delivery gap=%llu ms before frame=%llu",
						static_cast<unsigned long long>(now - m_last_loas_ms),
						static_cast<unsigned long long>(m_stats.audioFrames + 1));
				m_last_loas_ms = now;
				m_loas_callback(m_loas.data(), frameLength);
				m_loas.erase(m_loas.begin(), m_loas.begin() + frameLength);
				++m_stats.audioFrames;
				m_stats.serviceFound = true;
				m_publish_pending = true;
			}
			return true;
		}
		return bytes < 0 && (errno == EAGAIN || errno == EINTR);
	}

	bool drainAudio(int fd)
	{
		for (int pass = 0; pass < 16; ++pass)
		{
			struct pollfd descriptor = {};
			descriptor.fd = fd;
			descriptor.events = POLLIN;
			const int ready = poll(&descriptor, 1, 0);
			if (ready <= 0 || !(descriptor.revents & POLLIN))
				return true;
			if (!readAudio(fd))
				return false;
		}
		return true;
	}

	bool readMetadata(int fd, int audioFd, bool &audioOpen)
	{
		char buffer[4096];
		const ssize_t bytes = read(fd, buffer, sizeof(buffer));
		if (bytes > 0)
		{
			m_stderr.append(buffer, bytes);
			size_t newline;
			while ((newline = m_stderr.find('\n')) != std::string::npos)
			{
				handleMetadataLine(m_stderr.substr(0, newline));
				m_stderr.erase(0, newline + 1);
				/* Do not let a directory full of SPI logos monopolise the
				 * worker: drain compressed audio between metadata callbacks. */
				if (audioOpen)
					audioOpen = drainAudio(audioFd);
			}
			return true;
		}
		return bytes < 0 && (errno == EAGAIN || errno == EINTR);
	}

	void handleMetadataLine(const std::string &line)
	{
		if (line.compare(0, 6, "Found ") == 0 && line.size() > 12 && line.compare(line.size() - 6, 6, " tuner") == 0)
		{
			const std::string tuner = line.substr(6, line.size() - 12);
			snprintf(m_stats.tunerName, sizeof(m_stats.tunerName), "%s", tuner.c_str());
			m_publish_pending = true;
			eDABDebug("[eDABSDRWorker] receiver tuner='%s'", m_stats.tunerName);
			return;
		}
		const std::string programName = jsonValue(line, "programName");
		const std::string programId = jsonValue(line, "programId");
		if (!programName.empty() && !programId.empty() && programName.find("(data)") == std::string::npos)
		{
			char *end = nullptr;
			const unsigned long sid = strtoul(programId.c_str(), &end, 16);
			if (end && !*end && sid)
				addService(static_cast<uint32_t>(sid), programName);
			return;
		}
		const std::string selectedName = jsonValue(line, "ps");
		if (!selectedName.empty())
		{
			snprintf(m_stats.serviceLabel, sizeof(m_stats.serviceLabel), "%s", selectedName.c_str());
			m_publish_pending = true;
			return;
		}
		const std::string snr = jsonValue(line, "snr");
		if (!snr.empty())
		{
			const std::string synced = jsonValue(line, "synced");
			m_stats.snrCentidB = static_cast<int>(strtod(snr.c_str(), nullptr) * 100.0 + 0.5);
			m_stats.rfSynced = synced == "true" || synced == "1" || synced == "on" || synced == "yes";
			m_publish_pending = true;
			eDABDebug("[eDABSDRWorker] RF sync=%s snr=%s dB offset=%s Hz",
				synced.c_str(), snr.c_str(), jsonValue(line, "offset").c_str());
			return;
		}
		const std::string ficQuality = jsonValue(line, "fic_quality");
		if (!ficQuality.empty())
		{
			m_stats.ficQuality = std::max(0, std::min(100, atoi(ficQuality.c_str())));
			m_publish_pending = true;
			eDABDebug("[eDABSDRWorker] FIC quality=%s%%", ficQuality.c_str());
			return;
		}
		const std::string mscQuality = jsonValue(line, "msc_quality");
		if (!mscQuality.empty())
		{
			m_stats.mscQuality = std::max(0, std::min(100, atoi(mscQuality.c_str())));
			m_publish_pending = true;
			eDABDebug("[eDABSDRWorker] MSC quality=%s (frame RS AAC)", mscQuality.c_str());
			return;
		}
		const std::string radioText = jsonValue(line, "radiotext");
		if (!radioText.empty())
		{
			snprintf(m_stats.dynamicLabel, sizeof(m_stats.dynamicLabel), "%s", radioText.c_str());
			++m_stats.dlsLabels;
			m_publish_pending = true;
			return;
		}
		const std::string dlPlusReset = jsonValue(line, "dl_plus_reset");
		if (!dlPlusReset.empty())
		{
			m_stats.dlPlusItemTitle[0] = 0;
			m_stats.dlPlusItemArtist[0] = 0;
			m_stats.dlPlusItemGenre[0] = 0;
			m_stats.dlPlusProgrammeNow[0] = 0;
			m_stats.dlPlusProgrammeNext[0] = 0;
			m_stats.dlPlusProgrammePart[0] = 0;
			m_stats.dlPlusProgrammeHost[0] = 0;
			++m_stats.dlPlusRevision;
			m_publish_pending = true;
			return;
		}
		const std::string dlPlusType = jsonValue(line, "dl_plus_type");
		const std::string dlPlusValue = jsonValue(line, "dl_plus");
		if (!dlPlusType.empty())
		{
			char *destination = nullptr;
			size_t destinationSize = 0;
			switch (atoi(dlPlusType.c_str()))
			{
			case 1: destination = m_stats.dlPlusItemTitle; destinationSize = sizeof(m_stats.dlPlusItemTitle); break;
			case 4: destination = m_stats.dlPlusItemArtist; destinationSize = sizeof(m_stats.dlPlusItemArtist); break;
			case 11: destination = m_stats.dlPlusItemGenre; destinationSize = sizeof(m_stats.dlPlusItemGenre); break;
			case 33: destination = m_stats.dlPlusProgrammeNow; destinationSize = sizeof(m_stats.dlPlusProgrammeNow); break;
			case 34: destination = m_stats.dlPlusProgrammeNext; destinationSize = sizeof(m_stats.dlPlusProgrammeNext); break;
			case 35: destination = m_stats.dlPlusProgrammePart; destinationSize = sizeof(m_stats.dlPlusProgrammePart); break;
			case 36: destination = m_stats.dlPlusProgrammeHost; destinationSize = sizeof(m_stats.dlPlusProgrammeHost); break;
			default: break;
			}
			if (destination && strncmp(destination, dlPlusValue.c_str(), destinationSize) != 0)
			{
				snprintf(destination, destinationSize, "%s", dlPlusValue.c_str());
				++m_stats.dlPlusRevision;
				m_publish_pending = true;
			}
			return;
		}
		const std::string bitrate = jsonValue(line, "bitrate");
		const std::string dabType = jsonValue(line, "dabType");
		if (!bitrate.empty() && !dabType.empty())
		{
			const std::string language = jsonValue(line, "language");
			const std::string programType = jsonValue(line, "programType");
			const std::string protection = jsonValue(line, "protectionLevel");
			m_stats.bitrate = atoi(bitrate.c_str());
			m_stats.dabplus = dabType == "DAB+";
			m_stats.serviceFound = true;
			snprintf(m_stats.language, sizeof(m_stats.language), "%s", language.c_str());
			snprintf(m_stats.programType, sizeof(m_stats.programType), "%s", programType.c_str());
			snprintf(m_stats.protection, sizeof(m_stats.protection), "%s", protection.c_str());
			for (int index = 0; index < m_stats.serviceCount; ++index)
				if (m_stats.services[index].serviceId == m_service_id)
				{
					m_stats.services[index].bitrate = m_stats.bitrate;
					m_stats.services[index].dabplus = m_stats.dabplus;
				}
			m_publish_pending = true;
			return;
		}
		const std::string dataService = jsonValue(line, "data_service");
		if (!dataService.empty())
		{
			const int dscType = atoi(jsonValue(line, "dsc_type").c_str());
			const int subchannel = atoi(jsonValue(line, "subchannel").c_str());
			const int packetAddress = atoi(jsonValue(line, "packet_address").c_str());
			if (dscType == 60 && subchannel >= 0 && subchannel < 64 &&
				packetAddress > 0 && packetAddress < 1023)
			{
				const uint32_t key = (static_cast<uint32_t>(subchannel) << 10) |
					static_cast<uint32_t>(packetAddress);
				if (m_packet_decoders.find(key) == m_packet_decoders.end())
				{
					m_packet_decoders[key].reset(new eDABPacketDecoder(packetAddress,
						[this](const uint8_t *data, size_t length, int contentType,
							int contentSubType, const std::string &contentName, uint16_t transportId) {
							if (!m_mot_callback)
								return;
							const int result = m_mot_callback(data, length, contentType,
								contentSubType, contentName, transportId);
							if (result == 1)
								++m_stats.spiRevision;
							else if (result == 2)
								++m_stats.logoRevision;
							if (result)
								m_publish_pending = true;
						}));
				}
			}
			eDABDebug("[eDABSDRWorker] data component service='%s' app=%s dsc=%s subchannel=%s",
				dataService.c_str(), jsonValue(line, "app_type").c_str(),
				jsonValue(line, "dsc_type").c_str(), jsonValue(line, "subchannel").c_str());
			return;
		}
		const std::string packetStream = jsonValue(line, "packet_stream");
		if (!packetStream.empty())
		{
			const int subchannel = atoi(jsonValue(line, "subchannel").c_str());
			if (subchannel < 0 || subchannel >= 64 || (packetStream.size() & 1) ||
				packetStream.size() > 65536)
				return;
			std::vector<uint8_t> data(packetStream.size() / 2);
			for (size_t index = 0; index < data.size(); ++index)
			{
				const char high = packetStream[index * 2];
				const char low = packetStream[index * 2 + 1];
				const int highValue = high >= '0' && high <= '9' ? high - '0' :
					(high >= 'a' && high <= 'f' ? high - 'a' + 10 : -1);
				const int lowValue = low >= '0' && low <= '9' ? low - '0' :
					(low >= 'a' && low <= 'f' ? low - 'a' + 10 : -1);
				if (highValue < 0 || lowValue < 0)
					return;
				data[index] = static_cast<uint8_t>((highValue << 4) | lowValue);
			}
			for (std::map<uint32_t, std::unique_ptr<eDABPacketDecoder> >::iterator decoder =
				m_packet_decoders.begin(); decoder != m_packet_decoders.end(); ++decoder)
				if (static_cast<int>(decoder->first >> 10) == subchannel)
					decoder->second->feed(data.data(), data.size());
			return;
		}
		const std::string spiService = jsonValue(line, "spi_service");
		if (!spiService.empty())
		{
			eDABDebug("[eDABSDRWorker] SPI service='%s' subchannel=%s",
				spiService.c_str(), jsonValue(line, "subchannel").c_str());
			return;
		}
		const std::string spiImage = jsonValue(line, "spi_image");
		if (!spiImage.empty())
		{
			const size_t marker = spiImage.rfind("dab-spi-image-");
			if (marker != std::string::npos && marker + 18 <= spiImage.size())
			{
				char *end = nullptr;
				const unsigned long transportId = strtoul(spiImage.c_str() + marker + 14, &end, 16);
				std::map<uint16_t, std::string>::const_iterator entry = m_spi_entries.find(transportId & 0xffff);
				if (entry != m_spi_entries.end() && m_spi_image_callback &&
					m_spi_image_callback(spiImage, entry->second))
				{
					++m_stats.logoRevision;
					m_publish_pending = true;
				}
				else if (entry == m_spi_entries.end())
					eDABDebug("[eDABSDRWorker] cached unmapped SPI image '%s'", spiImage.c_str());
			}
			return;
		}
		const std::string spiEntry = jsonValue(line, "spi_entry");
		if (!spiEntry.empty())
		{
			const size_t separator = spiEntry.find(':');
			if (separator != std::string::npos)
			{
				char *end = nullptr;
				const unsigned long transportId = strtoul(spiEntry.c_str(), &end, 16);
				if (end == spiEntry.c_str() + separator && transportId <= 0xffff)
				{
					const std::string contentName = spiEntry.substr(separator + 1);
					if (m_spi_entries[transportId] != contentName)
					{
						m_spi_entries[transportId] = contentName;
						eDABDebug("[eDABSDRWorker] SPI directory entry='%s' contentType=%s",
							spiEntry.c_str(), jsonValue(line, "content_type").c_str());
					}
				}
			}
			return;
		}
		const std::string spiProgress = jsonValue(line, "spi_progress");
		if (!spiProgress.empty())
		{
			eDABDebug("[eDABSDRWorker] SPI object progress tid:received:expected:bytes=%s", spiProgress.c_str());
			return;
		}
		const std::string motPath = jsonValue(line, "mot");
		if (!motPath.empty())
		{
			std::ifstream file(motPath.c_str(), std::ios::binary);
			if (file)
			{
				std::vector<uint8_t> image((std::istreambuf_iterator<char>(file)), std::istreambuf_iterator<char>());
				const int format = motPath.size() >= 4 && motPath.substr(motPath.size() - 4) == ".png" ? 3 : 1;
				if (!image.empty())
				{
					m_image_callback(image.data(), image.size(), format);
					m_stats.slideFormat = format;
					++m_stats.slides;
					m_publish_pending = true;
				}
			}
			return;
		}
		const std::string spiPath = jsonValue(line, "spi");
		if (!spiPath.empty())
		{
			eDABDebug("[eDABSDRWorker] received SPI object '%s'", spiPath.c_str());
			if (m_spi_callback && m_spi_callback(spiPath) > 0)
			{
				++m_stats.spiRevision;
				m_publish_pending = true;
			}
			return;
		}
		if (line.compare(0, 9, "ensemble ") == 0)
		{
			const size_t marker = line.rfind(" is (");
			const size_t close = line.rfind(") recognized");
			if (marker != std::string::npos && close != std::string::npos && close > marker + 5)
			{
				const std::string name = line.substr(9, marker - 9);
				const std::string id = line.substr(marker + 5, close - marker - 5);
				m_stats.ensembleId = static_cast<uint16_t>(strtoul(id.c_str(), nullptr, 16));
				snprintf(m_stats.ensembleLabel, sizeof(m_stats.ensembleLabel), "%s", name.c_str());
				m_stats.etiFrames = 1;
				m_publish_pending = true;
			}
		}
	}

	void addService(uint32_t sid, const std::string &name)
	{
		for (int index = 0; index < m_stats.serviceCount; ++index)
			if (m_stats.services[index].serviceId == sid)
				return;
		if (m_stats.serviceCount >= DAB_MAX_SCANNED_SERVICES)
			return;
		eDABScannedService &service = m_stats.services[m_stats.serviceCount++];
		service.serviceId = sid;
		service.bitrate = 0;
		service.dabplus = false;
		snprintf(service.label, sizeof(service.label), "%s", name.c_str());
		++m_stats.serviceRevision;
		m_publish_pending = true;
	}

	void publish(bool force = false)
	{
		const uint64_t now = monotonicMilliseconds();
		if (!force && !m_publish_pending && now - m_last_publish_ms < 1000)
			return;
		m_publish_pending = false;
		m_last_publish_ms = now;
		m_pump.send(m_stats);
	}

	std::string m_channel;
	uint32_t m_service_id;
	std::string m_mot_cache_prefix;
	std::string m_ppm;
	std::string m_device;
	bool m_automatic_gain;
	std::string m_gain;
	LOASCallback m_loas_callback;
	ImageCallback m_image_callback;
	SPIImageCallback m_spi_image_callback;
	SPICallback m_spi_callback;
	MOTCallback m_mot_callback;
	std::map<uint16_t, std::string> m_spi_entries;
	std::map<uint32_t, std::unique_ptr<eDABPacketDecoder> > m_packet_decoders;
	eFixedMessagePump<eDABWorkerStats> &m_pump;
	std::atomic<bool> m_stop;
	bool m_started;
	std::atomic<int> m_child_pid;
	int m_stdin_fd;
	uint64_t m_last_publish_ms;
	uint64_t m_last_loas_ms;
	bool m_publish_pending = false;
	eDABWorkerStats m_stats;
	std::vector<uint8_t> m_loas;
	std::string m_stderr;
};

DEFINE_REF(eStaticServiceDABInfo);

eStaticServiceDABInfo::eStaticServiceDABInfo()
{
}

RESULT eStaticServiceDABInfo::getName(const eServiceReference &ref, std::string &name)
{
	name = dabName(ref);
	return 0;
}

RESULT eStaticServiceDABInfo::getEvent(const eServiceReference &ref, ePtr<eServiceEvent> &event, time_t startTime)
{
	return eEPGCache::getInstance()->lookupEventTime(ref, startTime, event);
}

int eStaticServiceDABInfo::getLength(const eServiceReference &)
{
	return -1;
}

int eStaticServiceDABInfo::getInfo(const eServiceReference &ref, int w)
{
	switch (w)
	{
	case iServiceInformation::sIsCrypted:
		return 0;
	case iServiceInformation::sSID:
		return ref.getUnsignedData(6) & 0xffff;
	case iServiceInformation::sTSID:
		return ref.getUnsignedData(2);
	case iServiceInformation::sONID:
		return ref.getUnsignedData(3);
	case iServiceInformation::sNamespace:
		return ref.getUnsignedData(4);
	case iServiceInformation::sProvider:
	case iServiceInformation::sDescription:
	case iServiceInformation::sServiceref:
		return iServiceInformation::resIsString;
	default:
		return iServiceInformation::resNA;
	}
}

std::string eStaticServiceDABInfo::getInfoString(const eServiceReference &ref, int w)
{
	switch (w)
	{
	case iServiceInformation::sProvider:
		return ref.path.compare(0, 13, "dab://rtlsdr/") == 0 ? "DAB+ USB receiver" : "DAB over DVB";
	case iServiceInformation::sDescription:
		return ref.path.compare(0, 13, "dab://rtlsdr/") == 0 ? "Native RTL-SDR DAB service" : "Native DAB-over-DVB service";
	case iServiceInformation::sServiceref:
		return ref.toString();
	default:
		return std::string();
	}
}

int eStaticServiceDABInfo::isPlayable(const eServiceReference &, const eServiceReference &, bool)
{
	return 1;
}

DEFINE_REF(eServiceFactoryDAB);

eServiceFactoryDAB::eServiceFactoryDAB()
{
	ePtr<eServiceCenter> center;
	eServiceCenter::getPrivInstance(center);
	if (center)
	{
		std::list<std::string> extensions;
		center->addServiceFactory(id, this, extensions);
	}
	m_service_info = new eStaticServiceDABInfo();
}

eServiceFactoryDAB::~eServiceFactoryDAB()
{
	ePtr<eServiceCenter> center;
	eServiceCenter::getPrivInstance(center);
	if (center)
		center->removeServiceFactory(id);
}

RESULT eServiceFactoryDAB::play(const eServiceReference &ref, ePtr<iPlayableService> &ptr)
{
	ptr = new eServiceDAB(ref);
	return 0;
}

RESULT eServiceFactoryDAB::record(const eServiceReference &ref, ePtr<iRecordableService> &ptr)
{
	ptr = new eServiceDABRecord(ref);
	return 0;
}

RESULT eServiceFactoryDAB::list(const eServiceReference &, ePtr<iListableService> &ptr)
{
	ptr = nullptr;
	return -1;
}

RESULT eServiceFactoryDAB::info(const eServiceReference &, ePtr<iStaticServiceInformation> &ptr)
{
	ptr = m_service_info;
	return 0;
}

RESULT eServiceFactoryDAB::offlineOperations(const eServiceReference &, ePtr<iServiceOfflineOperations> &ptr)
{
	ptr = nullptr;
	return -1;
}

DEFINE_REF(eServiceDABRecord);

eServiceDABRecord::eServiceDABRecord(const eServiceReference &ref)
	: m_reference(ref), m_worker_pump(eApp, 1, "eServiceDABRecord"), m_file_fd(-1),
	  m_state(stateIdle), m_simulate(false), m_tuned(false), m_tap_running(false),
	  m_running_event_sent(false), m_write_error_reported(false), m_write_error(0),
	  m_error(NoError), m_written_bytes(0)
{
	m_socket[0] = -1;
	m_socket[1] = -1;
	CONNECT(m_worker_pump.recv_msg, eServiceDABRecord::workerMessage);
}

eServiceDABRecord::~eServiceDABRecord()
{
	stop();
}

RESULT eServiceDABRecord::connectEvent(const sigc::slot<void(iRecordableService *, int)> &event,
	ePtr<eConnection> &connection)
{
	connection = new eConnection(static_cast<iRecordableService *>(this), m_event.connect(event));
	return 0;
}

RESULT eServiceDABRecord::getError(int &error)
{
	error = m_error;
	return 0;
}

eServiceReferenceDVB eServiceDABRecord::parentReference() const
{
	eServiceReferenceDVB parent;
	parent.setServiceType(m_reference.getUnsignedData(0));
	parent.setServiceID(eServiceID(m_reference.getUnsignedData(1)));
	parent.setTransportStreamID(eTransportStreamID(m_reference.getUnsignedData(2)));
	parent.setOriginalNetworkID(eOriginalNetworkID(m_reference.getUnsignedData(3)));
	parent.setDVBNamespace(eDVBNamespace(m_reference.getUnsignedData(4)));
	return parent;
}

bool eServiceDABRecord::parseTransport(eDABTransport &transport, uint32_t &ip, uint16_t &port) const
{
	transport = DAB_TRANSPORT_MPE_EDI;
	ip = 0;
	port = 0;
	const std::string prefix("dab://");
	if (m_reference.path.compare(0, prefix.size(), prefix) != 0)
		return false;
	const std::string destination = m_reference.path.substr(prefix.size());
	if (destination == "tsniv2ni")
	{
		transport = DAB_TRANSPORT_TSNI;
		return true;
	}
	if (destination == "ts2na12")
	{
		transport = DAB_TRANSPORT_TSNA12;
		return true;
	}
	if (destination == "ts2na" || destination == "ts2na0")
	{
		transport = DAB_TRANSPORT_TSNA0;
		return true;
	}
	const size_t separator = destination.rfind(':');
	if (separator == std::string::npos)
		return false;
	const std::string address = destination.substr(0, separator);
	char *end = nullptr;
	const unsigned long parsedPort = strtoul(destination.c_str() + separator + 1, &end, 10);
	if (!end || *end || parsedPort > std::numeric_limits<uint16_t>::max() || !parsedPort)
		return false;
	if (inet_pton(AF_INET, address.c_str(), &ip) != 1)
		return false;
	port = static_cast<uint16_t>(parsedPort);
	return true;
}

bool eServiceDABRecord::prepareParent()
{
	ePtr<eServiceCenter> center;
	eServiceCenter::getPrivInstance(center);
	if (!center || center->play(parentReference(), m_parent) || !m_parent)
		return false;
	m_parent->connectEvent(sigc::mem_fun(*this, &eServiceDABRecord::parentEvent), m_parent_event_connection);
	m_parent->setTarget(0, true);
	m_event(this, evTuneStart);
	if (m_parent->start())
	{
		m_parent_event_connection = nullptr;
		m_parent = nullptr;
		return false;
	}
	return true;
}

RESULT eServiceDABRecord::prepare(const char *filename, time_t beginTime, time_t,
	int, const char *name, const char *description, const char *tags,
	bool, bool, int)
{
	if (m_state != stateIdle || !filename || !*filename)
		return errMisconfiguration;
	eDABTransport transport;
	uint32_t destinationIp;
	uint16_t destinationPort;
	if (!parseTransport(transport, destinationIp, destinationPort))
		return errMisconfiguration;

	m_filename = filename;
	m_state = statePrepared;
	if (!prepareParent())
	{
		m_state = stateIdle;
		m_error = errNoResources;
		return m_error;
	}

	eDVBMetaParser meta;
	meta.m_time_create = beginTime;
	meta.m_ref = parentReference();
	meta.m_data_ok = 1;
	meta.m_packet_size = 0;
	meta.m_scrambled = 0;
	if (name)
		meta.m_name = name;
	if (description)
		meta.m_description = description;
	if (tags)
		meta.m_tags = tags;
	if (meta.updateMeta(m_filename))
		eWarning("[eServiceDABRecord] unable to write metadata for '%s'", m_filename.c_str());
	return 0;
}

RESULT eServiceDABRecord::prepareStreaming(bool, bool)
{
	return -1;
}

RESULT eServiceDABRecord::start(bool simulate)
{
	m_simulate = simulate;
	m_event(this, evStart);
	if (simulate)
	{
		m_state = stateRecording;
		m_event(this, evRecordRunning);
		return 0;
	}
	if (m_state != statePrepared)
		return errMisconfiguration;

	m_file_fd = ::open(m_filename.c_str(), O_WRONLY | O_CREAT | O_TRUNC | O_LARGEFILE | O_CLOEXEC, 0666);
	if (m_file_fd < 0)
	{
		m_error = errOpenRecordFile;
		m_event(this, evRecordFailed);
		return m_error;
	}
	m_state = stateRecording;
	eDABDebug("[eServiceDABRecord] recording DAB+ LOAS to '%s'", m_filename.c_str());
	if (m_tuned && !startTap())
	{
		::close(m_file_fd);
		m_file_fd = -1;
		m_state = statePrepared;
		reportFailure(errNoResources, evRecordFailed);
		return m_error;
	}
	return 0;
}

RESULT eServiceDABRecord::stop()
{
	if (m_state == stateIdle && !m_parent && !m_worker && m_file_fd < 0)
		return 0;
	const bool notify = m_state != stateIdle;
	m_state = stateIdle;
	stopTap();
	if (m_parent)
		m_parent->stop();
	m_parent_event_connection = nullptr;
	m_parent = nullptr;
	if (m_file_fd >= 0)
	{
		::close(m_file_fd);
		m_file_fd = -1;
	}
	if (!m_simulate && !m_filename.empty())
		eDABDebug("[eServiceDABRecord] stopped '%s' after %llu bytes", m_filename.c_str(),
			static_cast<unsigned long long>(m_written_bytes));
	m_tuned = false;
	m_running_event_sent = false;
	if (notify)
		m_event(this, evRecordStopped);
	return 0;
}

bool eServiceDABRecord::startTap()
{
	if (m_tap_running)
		return true;
	if (!m_parent || m_parent->tap(m_parent_tap) || !m_parent_tap)
		return false;
	if (socketpair(AF_UNIX, SOCK_STREAM | SOCK_CLOEXEC, 0, m_socket) < 0)
	{
		m_parent_tap = nullptr;
		return false;
	}
	eDABTransport transport;
	uint32_t destinationIp;
	uint16_t destinationPort;
	if (!parseTransport(transport, destinationIp, destinationPort))
	{
		stopTap();
		return false;
	}
	const int pid = m_reference.getUnsignedData(5) & 0x1fff;
	m_worker.reset(new eDABWorker(m_socket[0], pid, transport, destinationIp, destinationPort,
		m_reference.getUnsignedData(6), m_reference.getUnsignedData(7) & 0xffff,
		[this](const uint8_t *, size_t, const uint8_t *data, size_t length, uint64_t, uint8_t) {
			writeAudio(data, length);
		},
		eDABWorker::ImageCallback(), eDABWorker::MOTCallback(), m_worker_pump));
	if (!m_worker->start())
	{
		stopTap();
		return false;
	}
	std::vector<int> pids(1, pid);
	if (!m_parent_tap->startTapToFD(m_socket[1], pids, DAB_TS_PACKET_SIZE))
	{
		stopTap();
		return false;
	}
	m_tap_running = true;
	eDABDebug("[eServiceDABRecord] native PID tap started pid=%04x dabSid=%04x target=%s",
		pid, m_reference.getUnsignedData(6) & 0xffff, m_reference.path.c_str());
	if (!m_running_event_sent)
	{
		m_running_event_sent = true;
		m_event(this, evRecordRunning);
	}
	return true;
}

void eServiceDABRecord::stopTap()
{
	if (m_parent_tap && m_tap_running)
		m_parent_tap->stopTapToFD();
	m_tap_running = false;
	if (m_worker)
	{
		m_worker->stop();
		m_worker.reset();
	}
	for (int &fd : m_socket)
	{
		if (fd >= 0)
		{
			::close(fd);
			fd = -1;
		}
	}
	m_parent_tap = nullptr;
}

void eServiceDABRecord::parentEvent(iPlayableService *, int event)
{
	switch (event)
	{
	case iPlayableService::evTunedIn:
		m_tuned = true;
		m_event(this, evTunedIn);
		if (m_state == stateRecording && !m_simulate && !startTap())
			reportFailure(errNoResources, evRecordFailed);
		break;
	case iPlayableService::evNewProgramInfo:
		if (m_state == stateRecording && m_tuned && !m_tap_running && !startTap())
			reportFailure(errNoResources, evRecordFailed);
		break;
	case iPlayableService::evTuneFailed:
		m_tuned = false;
		reportFailure(errTuneFailed, evTuneFailed);
		break;
	default:
		break;
	}
}

void eServiceDABRecord::writeAudio(const uint8_t *data, size_t length)
{
	if (m_file_fd < 0 || !data || !length || m_write_error.load())
		return;
	while (length)
	{
		const ssize_t written = ::write(m_file_fd, data, length);
		if (written < 0 && errno == EINTR)
			continue;
		if (written <= 0)
		{
			int expected = 0;
			m_write_error.compare_exchange_strong(expected, written < 0 ? errno : EIO);
			return;
		}
		m_written_bytes += static_cast<uint64_t>(written);
		data += written;
		length -= static_cast<size_t>(written);
	}
}

void eServiceDABRecord::workerMessage(const eDABWorkerStats &stats)
{
	if (m_state != stateRecording)
		return;
	const int writeError = m_write_error.load();
	if (writeError && !m_write_error_reported)
	{
		m_write_error_reported = true;
		reportFailure(writeError == ENOSPC ? errDiskFull : errOpenRecordFile, evRecordWriteError);
	}
	else if (stats.error && !m_write_error_reported)
		reportFailure(errNoResources, evRecordFailed);
}

void eServiceDABRecord::reportFailure(int error, int event)
{
	m_error = error;
	m_event(this, event);
}

RESULT eServiceDABRecord::frontendInfo(ePtr<iFrontendInformation> &ptr)
{
	if (m_parent)
		return m_parent->frontendInfo(ptr);
	ptr = nullptr;
	return -1;
}

RESULT eServiceDABRecord::stream(ePtr<iStreamableService> &ptr)
{
	ptr = nullptr;
	return -1;
}

RESULT eServiceDABRecord::subServices(ePtr<iSubserviceList> &ptr)
{
	ptr = nullptr;
	return -1;
}

RESULT eServiceDABRecord::getServiceType(int &serviceType)
{
	serviceType = m_reference.getUnsignedData(0);
	return 0;
}

RESULT eServiceDABRecord::getFilenameExtension(std::string &extension)
{
	extension = ".aac";
	return 0;
}

DEFINE_REF(eServiceDAB);

eServiceDAB::eServiceDAB(const eServiceReference &ref)
	: m_reference(ref), m_worker_pump(eApp, 1, "eServiceDAB"), m_running(false),
	  m_tap_running(false), m_input_seen(false), m_audio_seen(false), m_parent_state(-1), m_last_bytes(0),
	  m_transfer_bps(0), m_audio_pipeline(nullptr), m_audio_source(nullptr), m_audio_queue(nullptr),
	  m_audio_capture(nullptr), m_audio_next_pts(0), m_audio_format(0), m_audio_caps_set(false),
	  m_audio_queue_overruns(0),
	  m_reported_audio_queue_overruns(0)
{
	m_socket[0] = -1;
	m_socket[1] = -1;
	/* Keep SLS and station logos across zaps and, when /media/hdd is backed by
	 * storage, across reboots. Include transport, EId and the complete SId so
	 * equally numbered services from different ensembles never share an entry. */
	m_cache_directory = dabCacheDirectory();
	m_source_hash = 2166136261u;
	for (const unsigned char character : m_reference.path)
	{
		m_source_hash ^= character;
		m_source_hash *= 16777619u;
	}
	char slideBase[192];
	snprintf(slideBase, sizeof(slideBase), "%s/dab-sls-%08x-%04x-%08x",
		m_cache_directory.c_str(), m_source_hash, m_reference.getUnsignedData(7) & 0xffff,
		m_reference.getUnsignedData(6));
	m_slide_jpeg_path = std::string(slideBase) + ".jpg";
	m_slide_png_path = std::string(slideBase) + ".png";
	char logoBase[192];
	snprintf(logoBase, sizeof(logoBase), "%s/dab-logo-%08x-%04x-%08x",
		m_cache_directory.c_str(), m_source_hash, m_reference.getUnsignedData(7) & 0xffff,
		m_reference.getUnsignedData(6));
	m_logo_base = logoBase;
	CONNECT(m_worker_pump.recv_msg, eServiceDAB::workerMessage);
}

eServiceDAB::~eServiceDAB()
{
	stop();
}

RESULT eServiceDAB::connectEvent(const sigc::slot<void(iPlayableService *, int)> &event, ePtr<eConnection> &connection)
{
	connection = new eConnection(static_cast<iPlayableService *>(this), m_event.connect(event));
	return 0;
}

eServiceReferenceDVB eServiceDAB::parentReference() const
{
	eServiceReferenceDVB parent;
	parent.setServiceType(m_reference.getUnsignedData(0));
	parent.setServiceID(eServiceID(m_reference.getUnsignedData(1)));
	parent.setTransportStreamID(eTransportStreamID(m_reference.getUnsignedData(2)));
	parent.setOriginalNetworkID(eOriginalNetworkID(m_reference.getUnsignedData(3)));
	parent.setDVBNamespace(eDVBNamespace(m_reference.getUnsignedData(4)));
	return parent;
}

bool eServiceDAB::parseTransport(eDABTransport &transport, uint32_t &ip, uint16_t &port) const
{
	transport = DAB_TRANSPORT_MPE_EDI;
	ip = 0;
	port = 0;
	const std::string prefix("dab://");
	if (m_reference.path.compare(0, prefix.size(), prefix) != 0)
		return false;
	const std::string destination = m_reference.path.substr(prefix.size());
	if (destination == "tsniv2ni")
	{
		transport = DAB_TRANSPORT_TSNI;
		return true;
	}
	if (destination == "ts2na12")
	{
		transport = DAB_TRANSPORT_TSNA12;
		return true;
	}
	if (destination == "ts2na" || destination == "ts2na0")
	{
		transport = DAB_TRANSPORT_TSNA0;
		return true;
	}
	const size_t separator = destination.rfind(':');
	if (separator == std::string::npos)
		return false;
	const std::string address = destination.substr(0, separator);
	char *end = nullptr;
	const unsigned long parsedPort = strtoul(destination.c_str() + separator + 1, &end, 10);
	if (!end || *end || parsedPort > std::numeric_limits<uint16_t>::max() || !parsedPort)
		return false;
	if (inet_pton(AF_INET, address.c_str(), &ip) != 1)
		return false;
	port = static_cast<uint16_t>(parsedPort);
	return true;
}

bool eServiceDAB::parseRTLSDRChannel(std::string &channel) const
{
	const std::string prefix("dab://rtlsdr/");
	if (m_reference.path.compare(0, prefix.size(), prefix) != 0)
		return false;
	channel = m_reference.path.substr(prefix.size());
	static const char *validChannels[] = {
		"5A", "5B", "5C", "5D", "6A", "6B", "6C", "6D",
		"7A", "7B", "7C", "7D", "8A", "8B", "8C", "8D",
		"9A", "9B", "9C", "9D", "10A", "10B", "10C", "10D",
		"11A", "11B", "11C", "11D", "12A", "12B", "12C", "12D",
		"13A", "13B", "13C", "13D", "13E", "13F"
	};
	return std::find(validChannels, validChannels + sizeof(validChannels) / sizeof(validChannels[0]), channel) !=
		validChannels + sizeof(validChannels) / sizeof(validChannels[0]);
}

RESULT eServiceDAB::start()
{
	if (m_running)
		return 0;
	std::string sdrChannel;
	if (parseRTLSDRChannel(sdrChannel))
	{
		if (!eConfigManager::getConfigBoolValue("config.dab.rtlsdr.enabled", false))
		{
			eWarning("[eServiceDAB] RTL-SDR service requested while the receiver is disabled");
			return -1;
		}
		m_running = true;
		m_event(this, evStart);
		if (!startRTLSDR())
		{
			m_running = false;
			m_event(this, evTuneFailed);
			return -1;
		}
		m_parent_state = evTunedIn;
		m_event(this, evTunedIn);
		return 0;
	}
	eDABTransport transport;
	uint32_t destinationIp;
	uint16_t destinationPort;
	if (!parseTransport(transport, destinationIp, destinationPort))
	{
		eWarning("[eServiceDAB] invalid destination '%s'", m_reference.path.c_str());
		return -1;
	}

	ePtr<eServiceCenter> center;
	eServiceCenter::getPrivInstance(center);
	if (!center || center->play(parentReference(), m_parent) || !m_parent)
	{
		eWarning("[eServiceDAB] unable to create parent DVB service");
		return -1;
	}
	m_parent->connectEvent(sigc::mem_fun(*this, &eServiceDAB::parentEvent), m_parent_event_connection);
	m_parent->setTarget(0, true);
	m_running = true;
	m_event(this, evStart);
	const RESULT result = m_parent->start();
	if (result)
	{
		m_running = false;
		m_parent_event_connection = nullptr;
		m_parent = nullptr;
		m_event(this, evTuneFailed);
	}
	return result;
}

RESULT eServiceDAB::stop()
{
	if (!m_running && !m_parent && !m_worker && !m_sdr_worker)
		return 0;
	stopRTLSDR();
	stopTap();
	if (m_parent)
		m_parent->stop();
	m_radio_picture_decoder = nullptr;
	m_parent_event_connection = nullptr;
	m_parent = nullptr;
	m_running = false;
	m_event(this, evStopped);
	return 0;
}

bool eServiceDAB::startRTLSDR()
{
	if (m_sdr_worker)
		return true;
	std::string channel;
	if (!parseRTLSDRChannel(channel))
		return false;
	const uint32_t serviceId = m_reference.getUnsignedData(6);
	char motCachePrefix[192];
	snprintf(motCachePrefix, sizeof(motCachePrefix), "%s/dab-mot-%08x-%04x",
		m_cache_directory.c_str(), m_source_hash, m_reference.getUnsignedData(7) & 0xffff);
	/* A SID of zero is the transient scan service.  It needs ensemble and
	 * service metadata only, so no audio pipeline is opened while scanning. */
	if (serviceId && !startAudioPipeline(true))
		return false;
	m_sdr_worker.reset(new eDABSDRWorker(channel, serviceId, motCachePrefix,
		[this](const uint8_t *data, size_t length) { pushLOAS(data, length); },
		[this](const uint8_t *data, size_t length, int format) { storeSlide(data, length, format); },
		[this](const std::string &path, const std::string &contentName) { return cacheSPIImage(path, contentName); },
		[this](const std::string &path) { return importSPI(path); },
		[this](const uint8_t *data, size_t length, int contentType, int contentSubType,
			const std::string &contentName, uint16_t transportId) {
			return handleMOTObject(data, length, contentType, contentSubType, contentName, transportId);
		},
		m_worker_pump));
	if (!m_sdr_worker->start())
	{
		m_sdr_worker.reset();
		stopAudioPipeline();
		return false;
	}
	eDABDebug("[eServiceDAB] RTL-SDR receiver started channel=%s dabSid=%08x",
		channel.c_str(), serviceId);
	if (serviceId)
		showRadioPicture();
	const std::string cachedSlide = slidePath();
	if (!cachedSlide.empty())
	{
		eDABDebug("[eServiceDAB] using cached SLS image: '%s'", cachedSlide.c_str());
		m_event(this, evUpdatedInfo);
	}
	m_audio_probe_deadline = serviceId && m_audio_loas ? monotonicMilliseconds() + LOAS_PROBE_MS : 0;
	return true;
}

void eServiceDAB::stopRTLSDR()
{
	if (!m_sdr_worker)
		return;
	m_audio_probe_deadline = 0;
	m_sdr_worker->stop();
	m_sdr_worker.reset();
	stopAudioPipeline();
}

bool eServiceDAB::startTap()
{
	if (m_tap_running)
		return true;
	if (!m_parent || m_parent->tap(m_parent_tap) || !m_parent_tap)
		return false;
	if (socketpair(AF_UNIX, SOCK_STREAM | SOCK_CLOEXEC, 0, m_socket) < 0)
	{
		eWarning("[eServiceDAB] socketpair failed: %m");
		m_parent_tap = nullptr;
		return false;
	}
	uint32_t destinationIp = 0;
	uint16_t destinationPort = 0;
	eDABTransport transport;
	if (!parseTransport(transport, destinationIp, destinationPort))
	{
		stopTap();
		return false;
	}
	const int pid = m_reference.getUnsignedData(5) & 0x1fff;
	startAudioPipeline();
	m_worker.reset(new eDABWorker(m_socket[0], pid, transport, destinationIp, destinationPort,
		m_reference.getUnsignedData(6), m_reference.getUnsignedData(7) & 0xffff,
		[this](const uint8_t *data, size_t length, const uint8_t *framed, size_t framedLength,
			uint64_t durationNs, uint8_t config) {
			if (m_audio_capture)
				fwrite(framed, 1, framedLength, m_audio_capture);
			if (m_audio_loas)
				pushAudio(framed, framedLength, durationNs, config);
			else
				pushAudio(data, length, durationNs, config);
		},
		[this](const uint8_t *data, size_t length, int format) { storeSlide(data, length, format); },
		[this](const uint8_t *data, size_t length, int contentType, int contentSubType,
			const std::string &contentName, uint16_t transportId) {
			return handleMOTObject(data, length, contentType, contentSubType, contentName, transportId);
		},
		m_worker_pump));
	if (!m_worker->start())
	{
		stopTap();
		return false;
	}
	std::vector<int> pids(1, pid);
	if (!m_parent_tap->startTapToFD(m_socket[1], pids, DAB_TS_PACKET_SIZE))
	{
		eWarning("[eServiceDAB] unable to start PID tap for %04x", pid);
		stopTap();
		return false;
	}
	m_tap_running = true;
	if (m_reference.getUnsignedData(6))
		showRadioPicture();
	const std::string cachedSlide = slidePath();
	if (!cachedSlide.empty())
	{
		eDABDebug("[eServiceDAB] using cached SLS image: '%s'", cachedSlide.c_str());
		m_event(this, evUpdatedInfo);
	}
	m_audio_probe_deadline = m_audio_loas ? monotonicMilliseconds() + LOAS_PROBE_MS : 0;
	eDABDebug("[eServiceDAB] native PID tap started pid=%04x dabSid=%04x eid=%04x target=%s",
		pid, m_reference.getUnsignedData(6) & 0xffff, m_reference.getUnsignedData(7) & 0xffff,
		m_reference.path.c_str());
	return true;
}

void eServiceDAB::stopTap()
{
	if (m_parent_tap && m_tap_running)
		m_parent_tap->stopTapToFD();
	m_tap_running = false;
	if (m_worker)
	{
		m_worker->stop();
		m_worker.reset();
	}
	stopAudioPipeline();
	for (int &fd : m_socket)
	{
		if (fd >= 0)
		{
			close(fd);
			fd = -1;
		}
	}
	m_parent_tap = nullptr;
}

void eServiceDAB::parentEvent(iPlayableService *, int event)
{
	m_parent_state = event;
	switch (event)
	{
	case evTunedIn:
		m_event(this, evTunedIn);
		startTap();
		break;
	case evNewProgramInfo:
		if (!m_tap_running)
			startTap();
		else if (m_reference.getUnsignedData(6))
		{
			/* The parent DVB service updates decoder 0 once more after the tap
			 * has started.  On some Broadcom drivers that clears the radio still
			 * picture which was just written by startTap().  Re-apply it after
			 * the parent's decoder update so radio.mvi remains visible until an
			 * SLS image arrives. */
			m_radio_picture_decoder = nullptr;
			showRadioPicture();
		}
		break;
	case evTuneFailed:
		m_event(this, evTuneFailed);
		break;
	default:
		break;
	}
}

void eServiceDAB::workerMessage(const eDABWorkerStats &stats)
{
	const bool dlsChanged = strcmp(m_stats.dynamicLabel, stats.dynamicLabel) != 0;
	const bool dlPlusChanged = m_stats.dlPlusRevision != stats.dlPlusRevision ||
		strcmp(m_stats.dlPlusItemTitle, stats.dlPlusItemTitle) != 0 ||
		strcmp(m_stats.dlPlusItemArtist, stats.dlPlusItemArtist) != 0 ||
		strcmp(m_stats.dlPlusProgrammeNow, stats.dlPlusProgrammeNow) != 0;
	const bool slideChanged = m_stats.slides != stats.slides;
	const bool servicesChanged = m_stats.serviceRevision != stats.serviceRevision;
	const bool receiverChanged = strcmp(m_stats.tunerName, stats.tunerName) != 0;
	const bool epgChanged = m_stats.spiRevision != stats.spiRevision;
	const bool logoChanged = m_stats.logoRevision != stats.logoRevision;
	const bool radioMetaChanged = m_stats.serviceFound != stats.serviceFound ||
		m_stats.dabplus != stats.dabplus || m_stats.bitrate != stats.bitrate ||
		strcmp(m_stats.serviceLabel, stats.serviceLabel) != 0 ||
		strcmp(m_stats.ensembleLabel, stats.ensembleLabel) != 0 ||
		strcmp(m_stats.language, stats.language) != 0 ||
		strcmp(m_stats.programType, stats.programType) != 0 ||
		strcmp(m_stats.protection, stats.protection) != 0;
	m_transfer_bps = stats.bytes >= m_last_bytes ? stats.bytes - m_last_bytes : 0;
	m_last_bytes = stats.bytes;
	m_stats = stats;
	updateDLPlusEPG(dlPlusChanged);
	pollAudioBus();
	const uint64_t queueOverruns = m_audio_queue_overruns.load();
	/* The sink advertised LOAS but leaves the queue to overflow, so it does not
	 * consume what it claimed to take. Re-tap with the software decoder. */
	if (queueOverruns >= LOAS_PROBE_OVERRUNS && m_audio_probe_deadline && monotonicMilliseconds() < m_audio_probe_deadline)
	{
		loasSinkRejected() = true;
		m_audio_probe_deadline = 0;
		eWarning("[eServiceDAB] sink does not consume LOAS after %llu overruns, falling back to the software decoder",
			static_cast<unsigned long long>(queueOverruns));
		if (m_sdr_worker)
		{
			stopRTLSDR();
			if (!startRTLSDR())
				eWarning("[eServiceDAB] unable to restart the SDR receiver with the software decoder");
		}
		else
		{
			stopTap();
			if (!startTap())
				eWarning("[eServiceDAB] unable to restart the tap with the software decoder");
		}
		return;
	}
	if (queueOverruns != m_reported_audio_queue_overruns)
	{
		guint levelBuffers = 0;
		guint levelBytes = 0;
		guint64 levelTime = 0;
		if (m_audio_queue)
			g_object_get(m_audio_queue, "current-level-buffers", &levelBuffers,
				"current-level-bytes", &levelBytes, "current-level-time", &levelTime, nullptr);
		eWarning("[eServiceDAB] audio queue overrun: total=%llu level=%u buffers/%u bytes/%llu ms",
			static_cast<unsigned long long>(queueOverruns), levelBuffers, levelBytes,
			static_cast<unsigned long long>(levelTime / GST_MSECOND));
		m_reported_audio_queue_overruns = queueOverruns;
	}
	if (!m_input_seen && stats.etiFrames)
	{
		m_input_seen = true;
		eDABDebug("[eServiceDAB] ensemble transport detected: target='%s' ts=%llu mpe=%llu udp=%llu edi=%llu eti=%llu",
			m_reference.path.c_str(),
			static_cast<unsigned long long>(stats.tsPackets),
			static_cast<unsigned long long>(stats.mpeSections),
			static_cast<unsigned long long>(stats.udpPackets),
			static_cast<unsigned long long>(stats.ediPackets),
			static_cast<unsigned long long>(stats.etiFrames));
	}
	if (!m_audio_seen && stats.audioFrames)
	{
		m_audio_seen = true;
		eDABDebug("[eServiceDAB] audio decoded: sid=%04x label='%s' ensemble='%s' bitrate=%d frames=%llu pad=%llu",
			m_reference.getUnsignedData(6) & 0xffff, stats.serviceLabel, stats.ensembleLabel,
			stats.bitrate, static_cast<unsigned long long>(stats.audioFrames),
			static_cast<unsigned long long>(stats.padPackets));
	}
	if (dlsChanged && stats.dlsLabels)
		eDABDebug("[eServiceDAB] DLS: '%s' (labels=%llu, MOT X-PAD segments=%llu, data groups=%llu)",
			stats.dynamicLabel, static_cast<unsigned long long>(stats.dlsLabels),
			static_cast<unsigned long long>(stats.motSegments),
			static_cast<unsigned long long>(stats.motDataGroups));
	if (slideChanged && stats.slides)
		eDABDebug("[eServiceDAB] SLS image decoded: '%s' (slides=%llu, format=%d)",
			slidePath().c_str(), static_cast<unsigned long long>(stats.slides), stats.slideFormat);
	if (servicesChanged && stats.serviceCount)
	{
		eDABDebug("[eServiceDAB] ensemble scan: eid=%04x label='%s' services=%d revision=%llu",
			stats.ensembleId, stats.ensembleLabel, stats.serviceCount,
			static_cast<unsigned long long>(stats.serviceRevision));
		for (int i = 0; i < stats.serviceCount; ++i)
			eDABDebug("[eServiceDAB] scan service: sid=%08x label='%s' bitrate=%d codec=%s",
				stats.services[i].serviceId, stats.services[i].label, stats.services[i].bitrate,
				stats.services[i].dabplus ? "DAB+" : "DAB/MP2");
	}
	if (dlsChanged)
		m_event(this, evUpdatedRadioText);
	if (radioMetaChanged || dlPlusChanged)
		m_event(this, evUpdatedRtpText);
	if (slideChanged || logoChanged || servicesChanged || receiverChanged)
		m_event(this, evUpdatedInfo);
	if (epgChanged)
		m_event(this, evUpdatedEventInfo);
	if (stats.error && m_running)
		eWarning("[eServiceDAB] worker stopped with error %d", stats.error);
}

void eServiceDAB::updateDLPlusEPG(bool force)
{
	if (!m_stats.dlPlusProgrammeNow[0])
		return;
	const uint64_t monotonicNow = monotonicMilliseconds();
	if (!force && monotonicNow < m_next_live_epg_check)
		return;
	m_next_live_epg_check = monotonicNow + 60000;
	const time_t now = time(nullptr);
	ePtr<eServiceEvent> current;
	const bool haveCurrent = eEPGCache::getInstance()->lookupEventTime(m_reference, -1, current) == 0 && current;
	const bool ownCurrent = haveCurrent && current->getEventId() == DAB_LIVE_EPG_EVENT_ID &&
		current->getBeginTime() == m_live_epg_start && current->getEventName() == m_live_epg_title;
	/* Never replace a timed SPI event.  A DL+ fallback is created only while
	 * the normal EPG cache has no current programme. */
	if (haveCurrent && !ownCurrent)
		return;

	const std::string title(m_stats.dlPlusProgrammeNow);
	if (!ownCurrent || title != m_live_epg_title)
	{
		m_live_epg_start = now;
		m_live_epg_title = title;
	}
	else if (current->getBeginTime() + current->getDuration() > now + 30 * 60)
		return;

	std::string description(m_stats.dlPlusProgrammePart);
	if (m_stats.dlPlusProgrammeHost[0])
	{
		if (!description.empty())
			description += " | ";
		description += m_stats.dlPlusProgrammeHost;
	}
	const int duration = std::max<int>(DAB_LIVE_EPG_WINDOW,
		static_cast<int>(now - m_live_epg_start) + DAB_LIVE_EPG_WINDOW);
	std::vector<eServiceReference> references(1, m_reference);
	eEPGCache::getInstance()->submitEventData(references, m_live_epg_start, duration,
		m_live_epg_title.c_str(), description.c_str(), "",
		std::vector<uint8_t>(), std::vector<eit_parental_rating>(), DAB_LIVE_EPG_EVENT_ID);
	eDABDebug("[eServiceDAB] DL+ live EPG programme='%s' start=%lld duration=%d",
		m_live_epg_title.c_str(), static_cast<long long>(m_live_epg_start), duration);
	m_event(this, evUpdatedEventInfo);
}

static bool structureOffersLOAS(const GstStructure *structure)
{
	const GValue *value = gst_structure_get_value(structure, "stream-format");
	if (!value)
		return false;
	if (G_VALUE_HOLDS_STRING(value))
		return g_strcmp0(g_value_get_string(value), "loas") == 0;
	if (GST_VALUE_HOLDS_LIST(value))
	{
		for (guint index = 0; index < gst_value_list_get_size(value); ++index)
		{
			const GValue *item = gst_value_list_get_value(value, index);
			if (G_VALUE_HOLDS_STRING(item) && g_strcmp0(g_value_get_string(item), "loas") == 0)
				return true;
		}
	}
	return false;
}

bool eServiceDAB::sinkAcceptsLOAS(const char *factoryName)
{
	eDABDebug("[eServiceDAB] probing LOAS support for sink '%s'", factoryName);
	GstElementFactory *factory = gst_element_factory_find(factoryName);
	if (!factory)
	{
		eWarning("[eServiceDAB] audio sink factory '%s' is unavailable", factoryName);
		return false;
	}
	/* Require stream-format to name loas. A caps query would also match a sink
	 * that leaves the field open, and such a sink decodes the access units as
	 * plain AAC instead of LATM. */
	bool accepted = false;
	for (const GList *entry = gst_element_factory_get_static_pad_templates(factory); entry; entry = entry->next)
	{
		GstStaticPadTemplate *padTemplate = static_cast<GstStaticPadTemplate *>(entry->data);
		if (!padTemplate)
			continue;
		if (padTemplate->direction != GST_PAD_SINK)
			continue;
		GstCaps *caps = gst_static_pad_template_get_caps(padTemplate);
		if (!caps)
			continue;
		for (guint index = 0; index < gst_caps_get_size(caps); ++index)
		{
			if (structureOffersLOAS(gst_caps_get_structure(caps, index)))
			{
				accepted = true;
				break;
			}
		}
		gst_caps_unref(caps);
		if (accepted)
			break;
	}
	gst_object_unref(factory);
	eDABDebug("[eServiceDAB] sink '%s' LOAS support=%d", factoryName, accepted);
	return accepted;
}

bool eServiceDAB::startAudioPipeline(bool loasInput)
{
	if (m_audio_pipeline)
		return true;
	eDABDebug("[eServiceDAB] starting audio pipeline input=%s", loasInput ? "LOAS" : "raw AAC");
#ifdef DREAMNEXTGEN
	const char *hardwareSink = "dreamaudiosink";
#else
	const char *hardwareSink = "dvbaudiosink";
#endif
	/* A sink that takes LOAS decodes in hardware. Fall back to the software
	 * decoder only when it does not, dvbaudiosink advertises raw audio but
	 * never consumes it. */
	m_audio_input_loas = loasInput;
	m_audio_loas = !loasSinkRejected() && sinkAcceptsLOAS(hardwareSink);
	eDABDebug("[eServiceDAB] selected %s decode via '%s'", m_audio_loas ? "hardware" : "software", hardwareSink);
	std::string description =
		"appsrc name=dabsource is-live=true format=time do-timestamp=false block=false "
		"! queue name=dabqueue min-threshold-buffers=24 max-size-buffers=256 "
		"max-size-bytes=1048576 max-size-time=5000000000 leaky=downstream ! ";
	if (loasInput)
	{
		description += "aacparse ! ";
		if (!m_audio_loas)
			description += "avdec_aac_latm ! audioconvert ! audioresample ! ";
	}
	else if (!m_audio_loas)
		description += "faad ! audioconvert ! audioresample ! ";
	description += hardwareSink;
	description += " name=dabaudiosink";
	GError *error = nullptr;
	eDABDebug("[eServiceDAB] creating GStreamer pipeline: %s", description.c_str());
	m_audio_pipeline = gst_parse_launch(description.c_str(), &error);
	if (!m_audio_pipeline)
	{
		eWarning("[eServiceDAB] unable to create audio pipeline: %s", error ? error->message : "unknown error");
		if (error)
			g_error_free(error);
		return false;
	}
	if (error)
	{
		eWarning("[eServiceDAB] audio pipeline warning: %s", error->message);
		g_error_free(error);
	}
	m_audio_source = gst_bin_get_by_name(GST_BIN(m_audio_pipeline), "dabsource");
	m_audio_queue = gst_bin_get_by_name(GST_BIN(m_audio_pipeline), "dabqueue");
	eDABDebug("[eServiceDAB] pipeline elements source=%p queue=%p", m_audio_source, m_audio_queue);
	if (!m_audio_source || !m_audio_queue)
	{
		stopAudioPipeline();
		return false;
	}
	if (loasInput)
	{
		GstCaps *caps = gst_caps_new_simple("audio/mpeg",
			"mpegversion", G_TYPE_INT, 4,
			"stream-format", G_TYPE_STRING, "loas",
			"framed", G_TYPE_BOOLEAN, TRUE, nullptr);
		if (!caps)
		{
			stopAudioPipeline();
			return false;
		}
		g_object_set(m_audio_source, "caps", caps, nullptr);
		gst_caps_unref(caps);
		eDABDebug("[eServiceDAB] LOAS appsrc caps configured");
	}
	g_signal_connect(m_audio_queue, "overrun", G_CALLBACK(eServiceDAB::audioQueueOverrun), this);
	GstElement *audioSink = gst_bin_get_by_name(GST_BIN(m_audio_pipeline), "dabaudiosink");
	if (audioSink)
	{
		if (g_object_class_find_property(G_OBJECT_GET_CLASS(audioSink), "e2-sync"))
		{
#ifdef DREAMNEXTGEN
			/* DreamAudio uses e2-sync=true to identify pure audio. DAB has no
			 * video PTS against which its userspace A/V anchor could run. */
			g_object_set(audioSink, "e2-sync", TRUE, nullptr);
#else
			g_object_set(audioSink, "e2-sync", FALSE, nullptr);
#endif
		}
		if (g_object_class_find_property(G_OBJECT_GET_CLASS(audioSink), "e2-async"))
			g_object_set(audioSink, "e2-async", FALSE, nullptr);
		gst_object_unref(audioSink);
	}
	if (gst_element_set_state(m_audio_pipeline, GST_STATE_PLAYING) == GST_STATE_CHANGE_FAILURE)
	{
		eWarning("[eServiceDAB] audio pipeline refused PLAYING state");
		stopAudioPipeline();
		return false;
	}
	eDABDebug("[eServiceDAB] audio pipeline is starting in PLAYING state");
	m_audio_next_pts = 0;
	m_audio_format = 0;
	m_audio_caps_set = loasInput;
	m_audio_queue_overruns = 0;
	m_reported_audio_queue_overruns = 0;
	if (!access("/tmp/dab-capture", F_OK))
	{
		m_audio_capture = fopen("/tmp/dab-audio.aac", "wb");
		if (m_audio_capture)
			eDABDebug("[eServiceDAB] diagnostic AAC capture enabled: /tmp/dab-audio.aac");
	}
	return true;
}

void eServiceDAB::stopAudioPipeline()
{
	if (m_audio_capture)
	{
		fclose(m_audio_capture);
		m_audio_capture = nullptr;
	}
	if (m_audio_source)
	{
		GstFlowReturn flow = GST_FLOW_OK;
		g_signal_emit_by_name(m_audio_source, "end-of-stream", &flow);
		gst_object_unref(m_audio_source);
		m_audio_source = nullptr;
	}
	if (m_audio_queue)
	{
		gst_object_unref(m_audio_queue);
		m_audio_queue = nullptr;
	}
	if (m_audio_pipeline)
	{
		gst_element_set_state(m_audio_pipeline, GST_STATE_NULL);
		gst_object_unref(m_audio_pipeline);
		m_audio_pipeline = nullptr;
	}
	m_audio_next_pts = 0;
	m_audio_format = 0;
	m_audio_caps_set = false;
	m_audio_input_loas = false;
}

void eServiceDAB::setAudioCaps(uint8_t config)
{
	if (!m_audio_source || (m_audio_caps_set && m_audio_format == config))
		return;
	const bool dacRate = config & 0x40;
	const bool sbr = config & 0x20;
	const bool stereo = config & 0x10;
	const bool ps = config & 0x08;
	const unsigned coreSampleIndexTable[4] = {5, 8, 3, 6}; // 32, 16, 48, 24 kHz
	const unsigned coreSampleRateTable[4] = {32000, 16000, 48000, 24000};
	const unsigned formatIndex = (dacRate ? 2 : 0) | (sbr ? 1 : 0);
	const unsigned coreSampleIndex = coreSampleIndexTable[formatIndex];
	const unsigned coreChannels = stereo ? 2 : 1;
	if (m_audio_loas)
	{
		// The StreamMuxConfig carries the AudioSpecificConfig, no codec_data needed.
		const unsigned rate = sbr ? coreSampleRateTable[formatIndex] * 2 : coreSampleRateTable[formatIndex];
		GstCaps *loasCaps = gst_caps_new_simple("audio/mpeg",
			"mpegversion", G_TYPE_INT, 4,
			"rate", G_TYPE_INT, static_cast<int>(rate),
			"channels", G_TYPE_INT, static_cast<int>(coreChannels),
			"stream-format", G_TYPE_STRING, "loas",
			"framed", G_TYPE_BOOLEAN, TRUE, nullptr);
		if (!loasCaps)
			return;
		g_object_set(m_audio_source, "caps", loasCaps, nullptr);
		gst_caps_unref(loasCaps);
		m_audio_format = config;
		m_audio_caps_set = true;
		eDABDebug("[eServiceDAB] AAC hardware decode configured: LOAS %u Hz channels=%u sbr=%d ps=%d",
			rate, coreChannels, sbr, ps);
		return;
	}
	uint8_t asc[7] = {
		static_cast<uint8_t>((2 << 3) | (coreSampleIndex >> 1)),
		static_cast<uint8_t>(((coreSampleIndex & 1) << 7) | (coreChannels << 3) | 0b100)
	};
	size_t ascLength = 2;
	if (sbr)
	{
		asc[ascLength++] = 0x56;
		asc[ascLength++] = 0xe5;
		asc[ascLength++] = static_cast<uint8_t>(0x80 | ((dacRate ? 3 : 5) << 3));
		if (ps)
		{
			asc[ascLength - 1] |= 0x05;
			asc[ascLength++] = 0x48;
			asc[ascLength++] = 0x80;
		}
	}
	GstBuffer *codecData = gst_buffer_new_allocate(nullptr, ascLength, nullptr);
	if (!codecData)
		return;
	gst_buffer_fill(codecData, 0, asc, ascLength);
	GstCaps *caps = gst_caps_new_simple("audio/mpeg",
		"mpegversion", G_TYPE_INT, 4,
		"rate", G_TYPE_INT, static_cast<int>(coreSampleRateTable[formatIndex]),
		"channels", G_TYPE_INT, static_cast<int>(coreChannels),
		"stream-format", G_TYPE_STRING, "raw",
		"framed", G_TYPE_BOOLEAN, TRUE,
		"codec_data", GST_TYPE_BUFFER, codecData, nullptr);
	gst_buffer_unref(codecData);
	if (!caps)
		return;
	g_object_set(m_audio_source, "caps", caps, nullptr);
	gst_caps_unref(caps);
	m_audio_format = config;
	m_audio_caps_set = true;
	eDABDebug("[eServiceDAB] AAC software decode configured: core=%u Hz channels=%u sbr=%d ps=%d",
		coreSampleRateTable[formatIndex], coreChannels, sbr, ps);
}

void eServiceDAB::pushAudio(const uint8_t *data, size_t length, uint64_t durationNs, uint8_t config)
{
	if (!data || !length || !durationNs)
		return;
	setAudioCaps(config);
	if (!m_audio_caps_set)
		return;
	if (!m_audio_source)
		return;
	GstBuffer *buffer = gst_buffer_new_allocate(nullptr, length, nullptr);
	if (!buffer)
		return;
	gst_buffer_fill(buffer, 0, data, length);
	GST_BUFFER_PTS(buffer) = m_audio_next_pts;
	GST_BUFFER_DTS(buffer) = m_audio_next_pts;
	GST_BUFFER_DURATION(buffer) = durationNs;
	m_audio_next_pts += durationNs;
	GstFlowReturn flow = GST_FLOW_OK;
	g_signal_emit_by_name(m_audio_source, "push-buffer", buffer, &flow);
	gst_buffer_unref(buffer);
	if (flow != GST_FLOW_OK)
		eWarning("[eServiceDAB] unable to push audio buffer: %s", gst_flow_get_name(flow));
}

void eServiceDAB::pushLOAS(const uint8_t *data, size_t length)
{
	if (!data || !length || !m_audio_source || !m_audio_input_loas)
		return;
	if (m_audio_capture)
		fwrite(data, 1, length, m_audio_capture);
	GstBuffer *buffer = gst_buffer_new_allocate(nullptr, length, nullptr);
	if (!buffer)
		return;
	gst_buffer_fill(buffer, 0, data, length);
	GstFlowReturn flow = GST_FLOW_OK;
	g_signal_emit_by_name(m_audio_source, "push-buffer", buffer, &flow);
	gst_buffer_unref(buffer);
	if (flow != GST_FLOW_OK)
		eWarning("[eServiceDAB] unable to push RTL-SDR LOAS buffer: %s", gst_flow_get_name(flow));
}

void eServiceDAB::audioQueueOverrun(GstElement *, void *userData)
{
	static_cast<eServiceDAB *>(userData)->m_audio_queue_overruns.fetch_add(1);
}

void eServiceDAB::showRadioPicture()
{
	if (m_radio_picture_decoder)
		return;
	const bool showRadioBackground = eSimpleConfig::getBool("config.misc.showradiopic", true);
	const std::string radioPicture = eConfigManager::getConfigValue(
		showRadioBackground ? "config.misc.radiopic" : "config.misc.blackradiopic");
	if (radioPicture.empty())
		return;
	m_radio_picture_decoder = new eTSMPEGDecoder(nullptr, 0);
	/* Unlike a normal DVB radio service, DAB owns a separate parent service
	 * whose decoder remains stopped. Returning the video device to that demux
	 * after the usual 150 ms still-picture timeout clears the frame on Broadcom
	 * drivers. Keep the memory-source frame until this DAB service stops; SLS is
	 * displayed as a GUI layer above it. */
	m_radio_picture_decoder->showSinglePic(radioPicture.c_str(), true);
}

void eServiceDAB::storeSlide(const uint8_t *data, size_t length, int format)
{
	static const uint8_t pngSignature[] = { 0x89, 'P', 'N', 'G', 0x0d, 0x0a, 0x1a, 0x0a };
	if (!data || !length || length > 2 * 1024 * 1024)
		return;
	const std::string *path = nullptr;
	if (format == 1 && length >= 3 && data[0] == 0xff && data[1] == 0xd8 && data[2] == 0xff)
		path = &m_slide_jpeg_path;
	else if (format == 3 && length >= sizeof(pngSignature) && !memcmp(data, pngSignature, sizeof(pngSignature)))
		path = &m_slide_png_path;
	if (!path)
		return;

	const std::string temporary = *path + ".tmp";
	FILE *file = fopen(temporary.c_str(), "wb");
	if (!file)
	{
		eWarning("[eServiceDAB] unable to create SLS image '%s': %m", temporary.c_str());
		return;
	}
	bool written = fwrite(data, 1, length, file) == length;
	if (fclose(file) != 0)
		written = false;
	if (!written || rename(temporary.c_str(), path->c_str()) < 0)
	{
		eWarning("[eServiceDAB] unable to store SLS image '%s': %m", path->c_str());
		unlink(temporary.c_str());
	}
	else
	{
		/* A broadcaster may change the SLS image format.  Keep only the most
		 * recently received variant so a later service instance cannot select
		 * an obsolete file. */
		unlink(path == &m_slide_jpeg_path ? m_slide_png_path.c_str() : m_slide_jpeg_path.c_str());
	}
}

bool eServiceDAB::cacheSPIImage(const std::string &path, const std::string &contentName)
{
	std::ifstream source(path.c_str(), std::ios::binary);
	if (!source)
		return false;
	std::vector<uint8_t> image((std::istreambuf_iterator<char>(source)), std::istreambuf_iterator<char>());
	return cacheSPIImageData(image.data(), image.size(), contentName);
}

bool eServiceDAB::cacheSPIImageData(const uint8_t *data, size_t length, const std::string &contentName)
{
	uint32_t serviceId = 0;
	unsigned int width = 0;
	unsigned int height = 0;
	if (!parseSPIImageName(contentName, serviceId, width, height))
	{
		eDABDebug("[eServiceDAB] SPI image has no service mapping: '%s'", contentName.c_str());
		return false;
	}
	if (!data || !length || length > 2 * 1024 * 1024)
		return false;
	static const uint8_t pngSignature[] = { 0x89, 'P', 'N', 'G', 0x0d, 0x0a, 0x1a, 0x0a };
	const bool png = length >= sizeof(pngSignature) && !memcmp(data, pngSignature, sizeof(pngSignature));
	const bool jpeg = length >= 3 && data[0] == 0xff && data[1] == 0xd8 && data[2] == 0xff;
	if (!png && !jpeg)
		return false;

	char cacheBase[192];
	snprintf(cacheBase, sizeof(cacheBase), "%s/dab-logo-%08x-%04x-%08x",
		m_cache_directory.c_str(), m_source_hash, m_reference.getUnsignedData(7) & 0xffff, serviceId);
	const std::string scorePath = std::string(cacheBase) + ".score";
	const uint64_t score = width && height ? static_cast<uint64_t>(width) * height : 1;
	uint64_t cachedScore = 0;
	std::ifstream scoreFile(scorePath.c_str());
	if (scoreFile)
		scoreFile >> cachedScore;
	const std::string destination = std::string(cacheBase) + (png ? ".png" : ".jpg");
	if (cachedScore >= score && access(destination.c_str(), R_OK) == 0)
	{
		if (cachedScore > score)
			return false;
		/* Do not rewrite an unchanged logo on every carousel pass, but do
		 * replace it when the broadcaster updates the artwork without
		 * changing its dimensions. */
		std::ifstream cached(destination.c_str(), std::ios::binary | std::ios::ate);
		if (cached && cached.tellg() == static_cast<std::streamoff>(length))
		{
			cached.seekg(0, std::ios::beg);
			std::vector<uint8_t> cachedImage(length);
			if (cached.read(reinterpret_cast<char *>(cachedImage.data()), length) &&
				std::equal(cachedImage.begin(), cachedImage.end(), data))
				return false;
		}
	}

	const std::string temporary = destination + ".tmp";
	FILE *file = fopen(temporary.c_str(), "wb");
	if (!file)
		return false;
	bool written = fwrite(data, 1, length, file) == length;
	if (fclose(file) != 0)
		written = false;
	if (!written || rename(temporary.c_str(), destination.c_str()) < 0)
	{
		unlink(temporary.c_str());
		return false;
	}
	unlink((std::string(cacheBase) + (png ? ".jpg" : ".png")).c_str());
	const std::string scoreTemporary = scorePath + ".tmp";
	FILE *scoreOutput = fopen(scoreTemporary.c_str(), "w");
	if (scoreOutput)
	{
		fprintf(scoreOutput, "%llu\n", static_cast<unsigned long long>(score));
		if (fclose(scoreOutput) == 0)
			rename(scoreTemporary.c_str(), scorePath.c_str());
		else
			unlink(scoreTemporary.c_str());
	}
	eDABDebug("[eServiceDAB] cached SPI logo sid=%04x size=%ux%u path='%s'",
		serviceId, width, height, destination.c_str());
	return serviceId == (m_reference.getUnsignedData(6) & 0xffff);
}

int eServiceDAB::importSPI(const std::string &path)
{
	std::ifstream source(path.c_str(), std::ios::binary);
	if (!source)
		return 0;
	std::vector<uint8_t> data((std::istreambuf_iterator<char>(source)), std::istreambuf_iterator<char>());
	return importSPIData(data.data(), data.size(), path);
}

int eServiceDAB::importSPIData(const uint8_t *data, size_t length, const std::string &source)
{
	eDABSPIDecoder decoder;
	std::vector<eDABSPIEvent> events;
	std::string error;
	if (!decoder.decodeData(data, length, m_reference.getUnsignedData(7) & 0xffff, events, error))
	{
		eWarning("[eServiceDAB] unable to decode SPI object '%s': %s", source.c_str(), error.c_str());
		return 0;
	}

	int imported = 0;
	for (std::vector<eDABSPIEvent>::const_iterator event = events.begin(); event != events.end(); ++event)
	{
		std::vector<eServiceReference> references;
		for (std::vector<uint32_t>::const_iterator serviceId = event->serviceIds.begin();
			serviceId != event->serviceIds.end(); ++serviceId)
		{
			/* Audio DAB services use a 16-bit SId. The 32-bit form belongs to
			 * data services and cannot identify an Enigma2 radio entry. */
			if (!*serviceId || *serviceId > 0xffff)
				continue;
			eServiceReference reference(m_reference);
			reference.setUnsignedData(6, *serviceId);
			if (event->ensembleId)
				reference.setUnsignedData(7, event->ensembleId);
			reference.name.clear();
			references.push_back(reference);
		}
		if (references.empty())
			continue;
		eEPGCache::getInstance()->submitEventData(references, event->start, event->duration,
			event->title.c_str(), event->shortDescription.c_str(), event->longDescription.c_str(),
			std::vector<uint8_t>(), std::vector<eit_parental_rating>(), 0);
		++imported;
	}
	eDABDebug("[eServiceDAB] imported %d programme events from SPI object '%s'", imported, source.c_str());
	return imported;
}

int eServiceDAB::handleMOTObject(const uint8_t *data, size_t length, int contentType,
	int contentSubType, const std::string &contentName, uint16_t transportId)
{
	char source[96];
	snprintf(source, sizeof(source), "native MOT tid=%04x type=%d/%d name=%s",
		transportId, contentType, contentSubType, contentName.c_str());
	if (contentType == 7)
	{
		char cachePath[192];
		snprintf(cachePath, sizeof(cachePath), "%s/dab-spi-%08x-%04x-%04x.bin",
			m_cache_directory.c_str(), m_source_hash, m_reference.getUnsignedData(7) & 0xffff,
			transportId);
		const std::string temporary = std::string(cachePath) + ".tmp";
		FILE *file = fopen(temporary.c_str(), "wb");
		if (file)
		{
			bool written = fwrite(data, 1, length, file) == length;
			if (fclose(file) != 0)
				written = false;
			if (written)
				rename(temporary.c_str(), cachePath);
			else
				unlink(temporary.c_str());
		}
		return importSPIData(data, length, source) > 0 ? 1 : 0;
	}
	if (contentType == 2)
		return cacheSPIImageData(data, length, contentName) ? 2 : 0;
	return 0;
}

std::string eServiceDAB::slidePath() const
{
	if (m_stats.slides)
	{
		const std::string &current = m_stats.slideFormat == 1 ? m_slide_jpeg_path : m_slide_png_path;
		if ((m_stats.slideFormat == 1 || m_stats.slideFormat == 3) && access(current.c_str(), R_OK) == 0)
			return current;
	}
	if (access(m_slide_jpeg_path.c_str(), R_OK) == 0)
		return m_slide_jpeg_path;
	if (access(m_slide_png_path.c_str(), R_OK) == 0)
		return m_slide_png_path;
	return std::string();
}

std::string eServiceDAB::logoPath() const
{
	const std::string logoJpeg = m_logo_base + ".jpg";
	const std::string logoPng = m_logo_base + ".png";
	if (access(logoJpeg.c_str(), R_OK) == 0)
		return logoJpeg;
	if (access(logoPng.c_str(), R_OK) == 0)
		return logoPng;
	return std::string();
}

void eServiceDAB::pollAudioBus()
{
	if (!m_audio_pipeline)
		return;
	GstBus *bus = gst_element_get_bus(m_audio_pipeline);
	if (!bus)
		return;
	GstMessage *message;
	while ((message = gst_bus_pop_filtered(bus,
		static_cast<GstMessageType>(GST_MESSAGE_ERROR | GST_MESSAGE_WARNING))) != nullptr)
	{
		GError *error = nullptr;
		gchar *debug = nullptr;
		if (GST_MESSAGE_TYPE(message) == GST_MESSAGE_ERROR)
		{
			gst_message_parse_error(message, &error, &debug);
			eWarning("[eServiceDAB] GStreamer error from %s: %s; %s",
				GST_OBJECT_NAME(GST_MESSAGE_SRC(message)), error ? error->message : "unknown error",
				debug ? debug : "no debug details");
		}
		else
		{
			gst_message_parse_warning(message, &error, &debug);
			eWarning("[eServiceDAB] GStreamer warning from %s: %s; %s",
				GST_OBJECT_NAME(GST_MESSAGE_SRC(message)), error ? error->message : "unknown warning",
				debug ? debug : "no debug details");
		}
		if (error)
			g_error_free(error);
		g_free(debug);
		gst_message_unref(message);
	}
	gst_object_unref(bus);
}

RESULT eServiceDAB::setTarget(int, bool)
{
	return 0;
}

RESULT eServiceDAB::seek(ePtr<iSeekableService> &ptr) { ptr = nullptr; return -1; }
RESULT eServiceDAB::pause(ePtr<iPauseableService> &ptr) { ptr = nullptr; return -1; }
RESULT eServiceDAB::info(ePtr<iServiceInformation> &ptr) { ptr = this; return 0; }
RESULT eServiceDAB::audioTracks(ePtr<iAudioTrackSelection> &ptr) { ptr = nullptr; return -1; }
RESULT eServiceDAB::audioChannel(ePtr<iAudioChannelSelection> &ptr) { ptr = nullptr; return -1; }
RESULT eServiceDAB::subServices(ePtr<iSubserviceList> &ptr) { ptr = nullptr; return -1; }

RESULT eServiceDAB::frontendInfo(ePtr<iFrontendInformation> &ptr)
{
	if (m_parent)
		return m_parent->frontendInfo(ptr);
	if (m_sdr_worker)
	{
		ptr = this;
		return 0;
	}
	ptr = nullptr;
	return -1;
}

int eServiceDAB::getFrontendInfo(int w)
{
	const int quality = m_stats.mscQuality >= 0 ? m_stats.mscQuality : m_stats.ficQuality;
	switch (w)
	{
	case iFrontendInformation_ENUMS::signalQuality:
		return m_stats.rfSynced && quality >= 0 ? quality * 65535 / 100 : 0;
	case iFrontendInformation_ENUMS::signalQualitydB:
		return m_stats.rfSynced ? m_stats.snrCentidB : -1;
	case iFrontendInformation_ENUMS::lockState:
	case iFrontendInformation_ENUMS::syncState:
		return m_stats.rfSynced;
	case iFrontendInformation_ENUMS::bitErrorRate:
	case iFrontendInformation_ENUMS::signalPower:
		return 0;
	case iFrontendInformation_ENUMS::frontendNumber:
		return -1;
	case iFrontendInformation_ENUMS::isUsbTuner:
		return 1;
	default:
		return 0;
	}
}

ePtr<iDVBFrontendData> eServiceDAB::getFrontendData()
{
	ePtr<iDVBFrontendData> data = new eDABFrontendData();
	return data;
}

ePtr<iDVBFrontendStatus> eServiceDAB::getFrontendStatus()
{
	const int quality = m_stats.mscQuality >= 0 ? m_stats.mscQuality : m_stats.ficQuality;
	ePtr<iDVBFrontendStatus> status = new eDABFrontendStatus(m_stats.rfSynced, quality, m_stats.snrCentidB);
	return status;
}

ePtr<iDVBTransponderData> eServiceDAB::getTransponderData(bool)
{
	return nullptr;
}

RESULT eServiceDAB::timeshift(ePtr<iTimeshiftService> &ptr) { ptr = nullptr; return -1; }
RESULT eServiceDAB::tap(ePtr<iTapService> &ptr) { ptr = nullptr; return -1; }
RESULT eServiceDAB::cueSheet(ePtr<iCueSheet> &ptr) { ptr = nullptr; return -1; }
RESULT eServiceDAB::subtitle(ePtr<iSubtitleOutput> &ptr) { ptr = nullptr; return -1; }
RESULT eServiceDAB::audioDelay(ePtr<iAudioDelay> &ptr) { ptr = nullptr; return -1; }
RESULT eServiceDAB::rdsDecoder(ePtr<iRdsDecoder> &ptr) { ptr = this; return 0; }
RESULT eServiceDAB::stream(ePtr<iStreamableService> &ptr) { ptr = nullptr; return -1; }
RESULT eServiceDAB::streamed(ePtr<iStreamedService> &ptr) { ptr = nullptr; return -1; }
RESULT eServiceDAB::keys(ePtr<iServiceKeys> &ptr) { ptr = nullptr; return -1; }
void eServiceDAB::setQpipMode(bool, bool) { }

std::string eServiceDAB::getText(int x)
{
	if (x == RadioText)
		return m_stats.dynamicLabel;
	if (x == RtpText)
	{
		std::string text = m_stats.dabplus ? "DAB+" : "DAB";
		if (m_stats.ensembleLabel[0])
			text += std::string(" | ") + m_stats.ensembleLabel;
		if (m_stats.bitrate > 0)
		{
			char bitrate[32];
			snprintf(bitrate, sizeof(bitrate), " | %d kbit/s", m_stats.bitrate);
			text += bitrate;
		}
		return text;
	}
	return std::string();
}

void eServiceDAB::showRassSlidePicture() { }
void eServiceDAB::showRassInteractivePic(int, int) { }

ePyObject eServiceDAB::getRassInteractiveMask()
{
	Py_RETURN_NONE;
}

RESULT eServiceDAB::getName(std::string &name)
{
	name = dabName(m_reference);
	return 0;
}

RESULT eServiceDAB::getEvent(ePtr<eServiceEvent> &event, int nowNext)
{
	ePtr<eServiceEvent> current;
	if (!nowNext)
		return eEPGCache::getInstance()->lookupEventTime(m_reference, -1, event);
	if (eEPGCache::getInstance()->lookupEventTime(m_reference, -1, current) < 0 || !current)
	{
		event = nullptr;
		return -1;
	}
	return eEPGCache::getInstance()->lookupEventTime(m_reference,
		current->getBeginTime() + current->getDuration(), event);
}

int eServiceDAB::getInfo(int w)
{
	switch (w)
	{
	case sIsCrypted:
		return 0;
	case sSID:
		return m_reference.getUnsignedData(6) & 0xffff;
	case sTSID:
		return m_reference.getUnsignedData(2);
	case sONID:
		return m_reference.getUnsignedData(3);
	case sNamespace:
		return m_reference.getUnsignedData(4);
	case sDVBState:
		return m_parent_state;
	case sDABServiceRevision:
		return static_cast<int>(m_stats.serviceRevision);
	case sDABEnsembleId:
		return m_stats.ensembleId ? m_stats.ensembleId : (m_reference.getUnsignedData(7) & 0xffff);
	case sDABFICQuality:
		return m_stats.ficQuality;
	case sDABMSCQuality:
		return m_stats.mscQuality;
	case sTransferBPS:
		return static_cast<int>(std::min<uint64_t>(m_transfer_bps, std::numeric_limits<int>::max()));
	case sProvider:
	case sDescription:
	case sServiceref:
	case sTagTitle:
	case sTagArtist:
	case sTagComment:
	case sTagCodec:
	case sTagBitrate:
	case sTagGenre:
	case sTagLanguageCode:
	case sTagImage:
	case sTagPreviewImage:
	case sDABServiceList:
	case sDABReceiverName:
	case sDABChannel:
	case sDABEnsembleLabel:
	case sDABProtection:
	case sDABDynamicLabel:
		return resIsString;
	default:
		return resNA;
	}
}

std::string eServiceDAB::getInfoString(int w)
{
	char text[256];
	switch (w)
	{
	case sProvider:
		return m_reference.path.compare(0, 13, "dab://rtlsdr/") == 0 ? "DAB+ USB receiver" : "DAB over DVB";
	case sDescription:
		if (m_stats.audioFrames)
			return m_audio_input_loas ? "Native DAB+ USB AAC audio active" : "Native DAB+ audio active";
		if (m_stats.serviceFound)
			return "DAB service found; waiting for audio superframe";
		return m_input_seen ? "DAB ensemble data active; reading ensemble information" :
			(m_reference.path.compare(0, 13, "dab://rtlsdr/") == 0 ? "Waiting for DAB USB receiver data" : "Waiting for DAB-over-DVB data");
	case sServiceref:
		return m_reference.toString();
	case sTagTitle:
		if (m_stats.dlPlusItemTitle[0])
			return m_stats.dlPlusItemTitle;
		if (m_stats.dlPlusProgrammeNow[0])
			return m_stats.dlPlusProgrammeNow;
		return m_stats.serviceLabel[0] ? m_stats.serviceLabel : dabName(m_reference);
	case sTagArtist:
		if (m_stats.dlPlusItemArtist[0])
			return m_stats.dlPlusItemArtist;
		return m_stats.serviceLabel[0] ? m_stats.serviceLabel : dabName(m_reference);
	case sTagCodec:
		return m_stats.serviceFound ? (m_stats.dabplus ? "DAB+ HE-AAC" : "DAB MPEG Audio Layer II") : "DAB (probing)";
	case sTagBitrate:
		snprintf(text, sizeof(text), "%d kbit/s", m_stats.bitrate);
		return text;
	case sTagGenre:
		if (m_stats.dlPlusItemGenre[0])
			return m_stats.dlPlusItemGenre;
		return m_stats.programType;
	case sTagLanguageCode:
		return m_stats.language;
	case sTagImage:
		return logoPath();
	case sTagPreviewImage:
		return slidePath();
	case sDABServiceList:
	{
		std::string result;
		for (int i = 0; i < m_stats.serviceCount; ++i)
		{
			char entry[128];
			snprintf(entry, sizeof(entry), "%08x\t%d\t%d\t%s\n", m_stats.services[i].serviceId,
				m_stats.services[i].bitrate, m_stats.services[i].dabplus ? 1 : 0, m_stats.services[i].label);
			result += entry;
		}
		return result;
	}
	case sDABReceiverName:
		return m_stats.tunerName;
	case sDABChannel:
	{
		std::string channel;
		return parseRTLSDRChannel(channel) ? channel : std::string();
	}
	case sDABEnsembleLabel:
		return m_stats.ensembleLabel;
	case sDABProtection:
		return m_stats.protection;
	case sDABDynamicLabel:
		return m_stats.dynamicLabel;
	case sTagComment:
		snprintf(text, sizeof(text), "PID %04x, EDI %llu, AF %llu, ETI %llu, FIC %llu, MSC %llu, AAC %llu, PAD %llu, DLS %llu, MOT segments %llu, groups %llu, slides %llu, CRC errors %llu",
			m_reference.getUnsignedData(5) & 0x1fff,
			static_cast<unsigned long long>(m_stats.ediPackets),
			static_cast<unsigned long long>(m_stats.afPackets),
			static_cast<unsigned long long>(m_stats.etiFrames),
			static_cast<unsigned long long>(m_stats.ficFrames),
			static_cast<unsigned long long>(m_stats.mscFrames),
			static_cast<unsigned long long>(m_stats.audioFrames),
			static_cast<unsigned long long>(m_stats.padPackets),
			static_cast<unsigned long long>(m_stats.dlsLabels),
			static_cast<unsigned long long>(m_stats.motSegments),
			static_cast<unsigned long long>(m_stats.motDataGroups),
			static_cast<unsigned long long>(m_stats.slides),
			static_cast<unsigned long long>(m_stats.crcErrors));
		return text;
	default:
		return std::string();
	}
}

eAutoInitPtr<eServiceFactoryDAB> init_eServiceFactoryDAB(eAutoInitNumbers::service + 1, "eServiceFactoryDAB");
