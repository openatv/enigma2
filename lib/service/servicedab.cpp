#include <lib/service/servicedab.h>
#include <lib/service/dabdecoder.h>

#include <algorithm>
#include <cerrno>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <ctime>
#include <limits>

#include <arpa/inet.h>
#include <fcntl.h>
#include <poll.h>
#include <sys/socket.h>
#include <unistd.h>

#include <gst/gst.h>

#include <lib/base/eerror.h>
#include <lib/base/init.h>
#include <lib/base/init_num.h>
#include <lib/dvb/metaparser.h>
#include <lib/service/service.h>

namespace
{
constexpr size_t TS_PACKET_SIZE = 188;
constexpr size_t PSI_MAX_SIZE = 0x0fff;
constexpr uint64_t LOAS_PROBE_MS = 8000;
constexpr uint64_t LOAS_PROBE_OVERRUNS = 3;

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
}

eDABWorkerStats::eDABWorkerStats()
	: bytes(0), tsPackets(0), syncErrors(0), continuityErrors(0), mpeSections(0),
	  udpPackets(0), ediPackets(0), afPackets(0), etiFrames(0), ficFrames(0),
	  mscFrames(0), audioFrames(0), crcErrors(0), padPackets(0), dlsLabels(0),
	  motSegments(0), motDataGroups(0), slides(0), serviceRevision(0), ensembleId(0),
	  serviceCount(0), slideFormat(0), bitrate(0),
	  serviceFound(false), dabplus(false), error(0)
{
	memset(services, 0, sizeof(services));
	serviceLabel[0] = 0;
	ensembleLabel[0] = 0;
	dynamicLabel[0] = 0;
}

eDABWorker::eDABWorker(int fd, int pid, eDABTransport transport, uint32_t destinationIp, uint16_t destinationPort,
	uint32_t serviceId, uint16_t ensembleId, const AudioCallback &audioCallback,
	const ImageCallback &imageCallback,
	eFixedMessagePump<eDABWorkerStats> &pump)
	: m_fd(fd), m_pid(pid), m_transport(transport), m_destination_ip(destinationIp), m_destination_port(destinationPort),
	  m_pump(pump), m_stop(false), m_started(false), m_last_cc(-1),
	  m_last_publish_ms(0), m_section_expected(0),
	  m_decoder(new eDABDecoder(serviceId, ensembleId, audioCallback, imageCallback))
{
	m_input.reserve(TS_PACKET_SIZE * 512);
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
		eDebug("[eDABWorker] unable to lower worker priority: %m");

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
	while (m_input.size() - offset >= TS_PACKET_SIZE)
	{
		if (m_input[offset] != 0x47)
		{
			++m_stats.syncErrors;
			++offset;
			continue;
		}
		if (m_input.size() - offset >= TS_PACKET_SIZE * 2 && m_input[offset + TS_PACKET_SIZE] != 0x47)
		{
			++m_stats.syncErrors;
			++offset;
			continue;
		}
		processTSPacket(&m_input[offset]);
		offset += TS_PACKET_SIZE;
	}
	if (offset)
		m_input.erase(m_input.begin(), m_input.begin() + offset);
	if (m_input.size() > TS_PACKET_SIZE * 4)
	{
		m_stats.syncErrors += m_input.size();
		m_input.clear();
	}
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
	if (payloadPresent && m_last_cc >= 0 && ((m_last_cc + 1) & 0x0f) != cc)
	{
		++m_stats.continuityErrors;
		clearSection();
		if (m_ts_adapter)
			m_ts_adapter->reset();
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
		if (offset >= TS_PACKET_SIZE)
			return;
	}
	if (m_transport == DAB_TRANSPORT_MPE_EDI)
		processPayload(packet + offset, TS_PACKET_SIZE - offset, packet[1] & 0x40);
	else if (m_ts_adapter)
		m_ts_adapter->feedPayload(packet + offset, TS_PACKET_SIZE - offset, packet[1] & 0x40);
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
	if (m_stats.serviceRevision != m_decoder->serviceRevision())
	{
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
	if (!force && now - m_last_publish_ms < 1000)
		return;
	m_last_publish_ms = now;
	m_pump.send(m_stats);
}

DEFINE_REF(eStaticServiceDABInfo);

eStaticServiceDABInfo::eStaticServiceDABInfo()
{
}

RESULT eStaticServiceDABInfo::getName(const eServiceReference &ref, std::string &name)
{
	name = dabName(ref);
	return 0;
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
		return "DAB over DVB";
	case iServiceInformation::sDescription:
		return "Native DAB-over-DVB service";
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
	eDebug("[eServiceDABRecord] recording DAB+ ADTS to '%s'", m_filename.c_str());
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
		eDebug("[eServiceDABRecord] stopped '%s' after %llu bytes", m_filename.c_str(),
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
		eDABWorker::ImageCallback(), m_worker_pump));
	if (!m_worker->start())
	{
		stopTap();
		return false;
	}
	std::vector<int> pids(1, pid);
	if (!m_parent_tap->startTapToFD(m_socket[1], pids, TS_PACKET_SIZE))
	{
		stopTap();
		return false;
	}
	m_tap_running = true;
	eDebug("[eServiceDABRecord] native PID tap started pid=%04x dabSid=%04x target=%s",
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
	char slideBase[64];
	snprintf(slideBase, sizeof(slideBase), "/tmp/dab-sls-%04x", m_reference.getUnsignedData(6) & 0xffff);
	m_slide_jpeg_path = std::string(slideBase) + ".jpg";
	m_slide_png_path = std::string(slideBase) + ".png";
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

RESULT eServiceDAB::start()
{
	if (m_running)
		return 0;
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
	if (!m_running && !m_parent && !m_worker)
		return 0;
	stopTap();
	if (m_parent)
		m_parent->stop();
	m_parent_event_connection = nullptr;
	m_parent = nullptr;
	m_running = false;
	m_event(this, evStopped);
	return 0;
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
	unlink(m_slide_jpeg_path.c_str());
	unlink(m_slide_png_path.c_str());
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
		m_worker_pump));
	if (!m_worker->start())
	{
		stopTap();
		return false;
	}
	std::vector<int> pids(1, pid);
	if (!m_parent_tap->startTapToFD(m_socket[1], pids, TS_PACKET_SIZE))
	{
		eWarning("[eServiceDAB] unable to start PID tap for %04x", pid);
		stopTap();
		return false;
	}
	m_tap_running = true;
	m_audio_probe_deadline = m_audio_loas ? monotonicMilliseconds() + LOAS_PROBE_MS : 0;
	eDebug("[eServiceDAB] native PID tap started pid=%04x dabSid=%04x eid=%04x target=%s",
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
	const bool slideChanged = m_stats.slides != stats.slides;
	const bool servicesChanged = m_stats.serviceRevision != stats.serviceRevision;
	const bool radioMetaChanged = m_stats.serviceFound != stats.serviceFound ||
		m_stats.dabplus != stats.dabplus || m_stats.bitrate != stats.bitrate ||
		strcmp(m_stats.serviceLabel, stats.serviceLabel) != 0 ||
		strcmp(m_stats.ensembleLabel, stats.ensembleLabel) != 0;
	m_transfer_bps = stats.bytes >= m_last_bytes ? stats.bytes - m_last_bytes : 0;
	m_last_bytes = stats.bytes;
	m_stats = stats;
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
		stopTap();
		if (!startTap())
			eWarning("[eServiceDAB] unable to restart the tap with the software decoder");
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
		eDebug("[eServiceDAB] ensemble transport detected: target='%s' ts=%llu mpe=%llu udp=%llu edi=%llu eti=%llu",
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
		eDebug("[eServiceDAB] audio decoded: sid=%04x label='%s' ensemble='%s' bitrate=%d frames=%llu pad=%llu",
			m_reference.getUnsignedData(6) & 0xffff, stats.serviceLabel, stats.ensembleLabel,
			stats.bitrate, static_cast<unsigned long long>(stats.audioFrames),
			static_cast<unsigned long long>(stats.padPackets));
	}
	if (dlsChanged && stats.dlsLabels)
		eDebug("[eServiceDAB] DLS: '%s' (labels=%llu, MOT X-PAD segments=%llu, data groups=%llu)",
			stats.dynamicLabel, static_cast<unsigned long long>(stats.dlsLabels),
			static_cast<unsigned long long>(stats.motSegments),
			static_cast<unsigned long long>(stats.motDataGroups));
	if (slideChanged && stats.slides)
		eDebug("[eServiceDAB] SLS image decoded: '%s' (slides=%llu, format=%d)",
			slidePath().c_str(), static_cast<unsigned long long>(stats.slides), stats.slideFormat);
	if (servicesChanged && stats.serviceCount)
	{
		eDebug("[eServiceDAB] ensemble scan: eid=%04x label='%s' services=%d revision=%llu",
			stats.ensembleId, stats.ensembleLabel, stats.serviceCount,
			static_cast<unsigned long long>(stats.serviceRevision));
		for (int i = 0; i < stats.serviceCount; ++i)
			eDebug("[eServiceDAB] scan service: sid=%08x label='%s' bitrate=%d codec=%s",
				stats.services[i].serviceId, stats.services[i].label, stats.services[i].bitrate,
				stats.services[i].dabplus ? "DAB+" : "DAB/MP2");
	}
	if (dlsChanged)
		m_event(this, evUpdatedRadioText);
	if (radioMetaChanged)
		m_event(this, evUpdatedRtpText);
	if (slideChanged || servicesChanged)
		m_event(this, evUpdatedInfo);
	if (stats.error && m_running)
		eWarning("[eServiceDAB] worker stopped with error %d", stats.error);
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
	GstElementFactory *factory = gst_element_factory_find(factoryName);
	if (!factory)
		return false;
	/* Require stream-format to name loas. A caps query would also match a sink
	 * that leaves the field open, and such a sink decodes the access units as
	 * plain AAC instead of LATM. */
	bool accepted = false;
	for (const GList *entry = gst_element_factory_get_static_pad_templates(factory); entry; entry = entry->next)
	{
		GstStaticPadTemplate *padTemplate = static_cast<GstStaticPadTemplate *>(entry->data);
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
	return accepted;
}

bool eServiceDAB::startAudioPipeline()
{
	if (m_audio_pipeline)
		return true;
#ifdef DREAMNEXTGEN
	const char *sink = "dreamaudiosink";
#else
	const char *sink = "dvbaudiosink";
#endif
	/* A sink that takes LOAS decodes in hardware. Fall back to the software
	 * decoder only when it does not, dvbaudiosink advertises raw audio but
	 * never consumes it. */
	m_audio_loas = !loasSinkRejected() && sinkAcceptsLOAS(sink);
	std::string description =
		"appsrc name=dabsource is-live=true format=time do-timestamp=false block=false "
		"! queue name=dabqueue max-size-buffers=64 max-size-bytes=524288 max-size-time=2000000000 leaky=downstream ! ";
	if (!m_audio_loas)
		description += "faad ! audioconvert ! audioresample ! ";
	description += sink;
	description += " name=dabaudiosink";
	GError *error = nullptr;
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
	if (!m_audio_source || !m_audio_queue)
	{
		stopAudioPipeline();
		return false;
	}
	g_signal_connect(m_audio_queue, "overrun", G_CALLBACK(eServiceDAB::audioQueueOverrun), this);
	GstElement *audioSink = gst_bin_get_by_name(GST_BIN(m_audio_pipeline), "dabaudiosink");
	if (audioSink)
	{
		if (g_object_class_find_property(G_OBJECT_GET_CLASS(audioSink), "e2-sync"))
			g_object_set(audioSink, "e2-sync", FALSE, nullptr);
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
	m_audio_next_pts = 0;
	m_audio_format = 0;
	m_audio_caps_set = false;
	m_audio_queue_overruns = 0;
	m_reported_audio_queue_overruns = 0;
	if (!access("/tmp/dab-capture", F_OK))
	{
		m_audio_capture = fopen("/tmp/dab-audio.aac", "wb");
		if (m_audio_capture)
			eDebug("[eServiceDAB] diagnostic AAC capture enabled: /tmp/dab-audio.aac");
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
		eDebug("[eServiceDAB] AAC hardware decode configured: LOAS %u Hz channels=%u sbr=%d ps=%d",
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
	eDebug("[eServiceDAB] AAC software decode configured: core=%u Hz channels=%u sbr=%d ps=%d",
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

void eServiceDAB::audioQueueOverrun(GstElement *, void *userData)
{
	static_cast<eServiceDAB *>(userData)->m_audio_queue_overruns.fetch_add(1);
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
}

std::string eServiceDAB::slidePath() const
{
	if (!m_stats.slides)
		return std::string();
	return m_stats.slideFormat == 1 ? m_slide_jpeg_path :
		(m_stats.slideFormat == 3 ? m_slide_png_path : std::string());
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
	ptr = nullptr;
	return -1;
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
	case sTagImage:
	case sTagPreviewImage:
	case sDABServiceList:
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
		return "DAB over DVB";
	case sDescription:
		if (m_stats.audioFrames)
			return "Native DAB+ audio active";
		if (m_stats.serviceFound)
			return "DAB service found; waiting for audio superframe";
		return m_input_seen ? "DAB ensemble data active; reading ensemble information" : "Waiting for DAB-over-DVB data";
	case sServiceref:
		return m_reference.toString();
	case sTagTitle:
		if (m_stats.dynamicLabel[0])
			return m_stats.dynamicLabel;
		return m_stats.serviceLabel[0] ? m_stats.serviceLabel : dabName(m_reference);
	case sTagArtist:
		return m_stats.serviceLabel[0] ? m_stats.serviceLabel : dabName(m_reference);
	case sTagCodec:
		return m_stats.serviceFound ? (m_stats.dabplus ? "DAB+ HE-AAC" : "DAB MPEG Audio Layer II") : "DAB (probing)";
	case sTagBitrate:
		snprintf(text, sizeof(text), "%d kbit/s", m_stats.bitrate);
		return text;
	case sTagImage:
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
