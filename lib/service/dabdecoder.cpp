#include <lib/service/dabdecoder.h>

#include <algorithm>
#include <cctype>
#include <cstring>

#include <lib/base/eerror.h>

namespace
{
struct UEPProfile
{
	uint16_t bitrate;
	uint16_t size;
};

/* EN 300 401, table of the 64 short-form UEP profiles. */
const UEPProfile uepProfiles[64] = {
	{32,16},{32,21},{32,24},{32,29},{32,35},{48,24},{48,29},{48,35},
	{48,42},{48,52},{56,29},{56,35},{56,42},{56,52},{64,32},{64,42},
	{64,48},{64,58},{64,70},{80,40},{80,52},{80,58},{80,70},{80,84},
	{96,48},{96,58},{96,70},{96,84},{96,104},{112,58},{112,70},{112,84},
	{112,104},{128,64},{128,84},{128,96},{128,116},{128,140},{160,80},{160,104},
	{160,116},{160,140},{160,168},{192,96},{192,116},{192,140},{192,168},{192,208},
	{224,116},{224,140},{224,168},{224,208},{224,232},{256,128},{256,168},{256,192},
	{256,232},{256,280},{320,160},{320,208},{320,280},{384,192},{384,280},{384,416}
};

struct EEPProfile
{
	uint8_t sizeMultiplier;
	uint8_t rateMultiplier;
};

const EEPProfile eepProfiles[8] = {
	{12,8},{8,8},{6,8},{4,8},{27,32},{21,32},{18,32},{15,32}
};

class LATMBitWriter
{
public:
	LATMBitWriter() = default;

	void addBits(uint32_t value, size_t count)
	{
		while (count)
		{
			const size_t usedBits = m_byte_bits & 7;  // Keeps the range provable, m_byte_bits is unsigned.
			if (!usedBits)
				m_data.push_back(0);
			const size_t freeBits = 8 - usedBits;
			const size_t copyBits = std::min(count, freeBits);
			const uint8_t copyData = static_cast<uint8_t>((value >> (count - copyBits)) & (0xff >> (8 - copyBits)));
			m_data.back() |= static_cast<uint8_t>(copyData << (freeBits - copyBits));
			m_byte_bits = (usedBits + copyBits) % 8;
			count -= copyBits;
		}
	}

	void addBytes(const uint8_t *data, size_t length)
	{
		for (size_t i = 0; i < length; ++i)
			addBits(data[i], 8);
	}

	std::vector<uint8_t> finishAudioSyncStream()
	{
		if (m_data.size() < 3 || m_data.size() - 3 > 0x1fff)
			return std::vector<uint8_t>();
		const size_t payloadLength = m_data.size() - 3;
		m_data[1] |= static_cast<uint8_t>((payloadLength >> 8) & 0x1f);
		m_data[2] = static_cast<uint8_t>(payloadLength & 0xff);
		return m_data;
	}

private:
	std::vector<uint8_t> m_data;
	size_t m_byte_bits = 0;
};
}

eDABDecoder::PFCollection::PFCollection()
	: fragmentCount(0), nominalLength(0), fec(false), rsk(0), rsz(0),
	  addressed(false), source(0), destination(0), received(0)
{
}

eDABDecoder::eDABDecoder(uint32_t serviceId, uint16_t ensembleId, const AudioCallback &audioCallback,
	const ImageCallback &imageCallback)
	: m_service_id(serviceId), m_ensemble_id(ensembleId), m_audio_callback(audioCallback),
	  m_image_callback(imageCallback), m_pad_decoder(this, true),
	  m_selected_subchannel(-1), m_selected_start_address(-1), m_selected_bitrate(0),
	  m_selected_dabplus(false), m_superframe_part_size(0), m_superframe_parts(0),
	  m_af_packets(0), m_eti_frames(0), m_fic_frames(0), m_msc_frames(0),
	  m_audio_frames(0), m_crc_errors(0), m_pad_packets(0), m_dls_labels(0),
	  m_slides(0), m_service_revision(0), m_slide_format(0)
{
	m_pad_decoder.Reset();
	m_pad_decoder.SetMOTAppType(12); // unencrypted MOT in X-PAD
}

eDABDecoder::~eDABDecoder()
{
}

std::vector<eDABDecoder::ServiceInfo> eDABDecoder::serviceList() const
{
	std::vector<ServiceInfo> result;
	result.reserve(m_services.size());
	for (std::map<uint32_t, Service>::const_iterator service = m_services.begin(); service != m_services.end(); ++service)
	{
		if (service->second.subchannel < 0)
			continue;
		std::map<int, Subchannel>::const_iterator subchannel = m_subchannels.find(service->second.subchannel);
		if (subchannel == m_subchannels.end() || !subchannel->second.bitrate)
			continue;
		ServiceInfo info;
		info.serviceId = service->first;
		info.bitrate = subchannel->second.bitrate;
		info.dabplus = service->second.dabplus;
		info.label = service->second.label;
		result.push_back(info);
	}
	return result;
}

uint16_t eDABDecoder::read16(const uint8_t *data)
{
	return static_cast<uint16_t>((data[0] << 8) | data[1]);
}

uint32_t eDABDecoder::read24(const uint8_t *data)
{
	return (static_cast<uint32_t>(data[0]) << 16) |
		(static_cast<uint32_t>(data[1]) << 8) | data[2];
}

uint32_t eDABDecoder::read32(const uint8_t *data)
{
	return (static_cast<uint32_t>(data[0]) << 24) |
		(static_cast<uint32_t>(data[1]) << 16) |
		(static_cast<uint32_t>(data[2]) << 8) | data[3];
}

uint16_t eDABDecoder::crc16(uint16_t crc, const uint8_t *data, size_t length, uint16_t polynomial)
{
	while (length--)
	{
		crc ^= static_cast<uint16_t>(*data++) << 8;
		for (int bit = 0; bit < 8; ++bit)
			crc = static_cast<uint16_t>((crc & 0x8000) ? (crc << 1) ^ polynomial : crc << 1);
	}
	return crc;
}

bool eDABDecoder::checkInvertedCRC(const uint8_t *data, size_t length)
{
	if (length < 2)
		return false;
	const uint16_t expected = read16(data + length - 2);
	const uint16_t calculated = static_cast<uint16_t>(crc16(0xffff, data, length - 2, 0x1021) ^ 0xffff);
	return expected == calculated;
}

bool eDABDecoder::checkFireCode(const uint8_t *data, size_t length)
{
	if (length < 11)
		return false;
	const uint16_t expected = read16(data);
	return crc16(0, data + 2, 9, 0x782f) == expected;
}

std::string eDABDecoder::decodeLabel(const uint8_t *data, size_t length, int charset)
{
	std::string label = DABlinPAD::CharsetTools::ConvertTextToUTF8(data, length, charset, false, nullptr);
	while (!label.empty() && label[label.size() - 1] == ' ')
		label.resize(label.size() - 1);
	return label;
}

void eDABDecoder::feedEDI(const uint8_t *data, size_t length)
{
	if (!data || length < 2)
		return;
	if (data[0] == 'A' && data[1] == 'F')
		processAF(data, length);
	else if (data[0] == 'P' && data[1] == 'F')
	{
		size_t offset = 0;
		while (offset + 14 <= length)
		{
			const size_t used = processPF(data + offset, length - offset);
			if (!used)
				break;
			offset += used;
		}
	}
}

void eDABDecoder::feedETI(const uint8_t *data, size_t length)
{
	if (!data || length < 16 ||
		(data[0] != 0xff || !((data[1] == 0x07 && data[2] == 0x3a && data[3] == 0xb6) ||
			(data[1] == 0xf8 && data[2] == 0xc5 && data[3] == 0x49))))
		return;
	const bool ficPresent = data[5] & 0x80;
	const size_t streamCount = data[5] & 0x7f;
	const int mode = (data[6] >> 3) & 3;
	const size_t frameLengthWords = ((static_cast<size_t>(data[6]) & 7) << 8) | data[7];
	if (streamCount > 64 || !ficPresent || !frameLengthWords)
		return;
	const size_t endOfHeader = 8 + streamCount * 4;
	if (endOfHeader + 4 > length || !checkInvertedCRC(data + 4, endOfHeader))
	{
		++m_crc_errors;
		return;
	}
	const size_t ficLength = mode == 3 ? 128 : 96;
	const size_t mstStart = endOfHeader + 4;
	if (mstStart + ficLength > length)
		return;

	std::vector<Stream> streams;
	streams.reserve(streamCount);
	size_t position = mstStart + ficLength;
	for (size_t index = 0; index < streamCount; ++index)
	{
		const uint8_t *stc = data + 8 + index * 4;
		const size_t streamLength = (((static_cast<size_t>(stc[2]) & 3) << 8) | stc[3]) * 8;
		if (!streamLength || position + streamLength > length)
			return;
		Stream stream;
		stream.subchannel = stc[0] >> 2;
		stream.startAddress = ((stc[0] & 3) << 8) | stc[1];
		stream.data.assign(data + position, data + position + streamLength);
		streams.push_back(stream);
		position += streamLength;
	}
	/* The MST CRC decides. FL is not compared against the parsed end, the frame
	 * can come from eDABTSAdapter, whose reconstruction need not place the
	 * fields where a broadcast ETI-NI frame does. */
	if (position + 2 > length || !checkInvertedCRC(data + mstStart, position + 2 - mstStart))
	{
		++m_crc_errors;
		return;
	}
	++m_eti_frames;
	parseFIC(data + mstStart, ficLength);
	feedMSC(streams);
}

void eDABDecoder::processAF(const uint8_t *data, size_t length)
{
	if (length < 12 || data[0] != 'A' || data[1] != 'F')
		return;
	const size_t tagLength = read32(data + 2);
	const bool hasCRC = data[8] & 0x80;
	if (((data[8] >> 4) & 7) != 1 || (data[8] & 0x0f) != 0 || data[9] != 'T')
		return;
	// LEN is 32 bit, adding to it wraps a 32-bit size_t.
	const size_t overhead = hasCRC ? 12 : 10;
	if (tagLength > length - overhead)
		return;
	if (hasCRC && !checkInvertedCRC(data, overhead + tagLength))
	{
		++m_crc_errors;
		return;
	}
	++m_af_packets;
	processTags(data + 10, tagLength);
}

size_t eDABDecoder::processPF(const uint8_t *data, size_t length)
{
	if (length < 14 || data[0] != 'P' || data[1] != 'F')
		return 0;
	const uint16_t sequence = read16(data + 2);
	const uint32_t index = read24(data + 4);
	const uint32_t count = read24(data + 7);
	const bool fec = data[10] & 0x80;
	const bool addressed = data[10] & 0x40;
	const uint16_t payloadLength = read16(data + 10) & 0x3fff;
	if (!count || index >= count || count > 4096 || payloadLength > 8192)
		return 0;
	size_t position = 12;
	uint8_t rsk = 0;
	uint8_t rsz = 0;
	uint16_t source = 0;
	uint16_t destination = 0;
	if (fec)
	{
		if (position + 2 > length)
			return 0;
		rsk = data[position++];
		rsz = data[position++];
	}
	if (addressed)
	{
		if (position + 4 > length)
			return 0;
		source = read16(data + position);
		destination = read16(data + position + 2);
		position += 4;
	}
	if (position + 2 + payloadLength > length)
		return 0;
	if (fec && !checkInvertedCRC(data, position + 2))
	{
		++m_crc_errors;
		return position + 2 + payloadLength;
	}
	position += 2; // PFT header CRC

	PFCollection &collector = m_pf_collectors[sequence];
	const bool incompatible = collector.fragmentCount &&
		(collector.fragmentCount != count || collector.fec != fec || collector.rsk != rsk ||
		 collector.rsz != rsz || collector.addressed != addressed || collector.source != source ||
		 collector.destination != destination);
	if (!collector.fragmentCount || incompatible)
	{
		collector = PFCollection();
		collector.fragmentCount = count;
		collector.nominalLength = payloadLength;
		collector.fec = fec;
		collector.rsk = rsk;
		collector.rsz = rsz;
		collector.addressed = addressed;
		collector.source = source;
		collector.destination = destination;
		collector.arrival = ++m_pf_arrival;
		collector.fragments.resize(count);
	}
	if (collector.fragments[index].empty())
	{
		collector.fragments[index].assign(data + position, data + position + payloadLength);
		++collector.received;
	}
	if (collector.received == collector.fragmentCount)
	{
		std::vector<uint8_t> af;
		if (reconstructPF(sequence, collector, af))
			processAF(af.data(), af.size());
		m_pf_collectors.erase(sequence);
	}
	trimPFCollectors();
	return position + payloadLength;
}

bool eDABDecoder::reconstructPF(uint16_t, PFCollection &collector, std::vector<uint8_t> &af)
{
	if (!collector.fec)
	{
		size_t total = 0;
		for (size_t i = 0; i < collector.fragments.size(); ++i)
			total += collector.fragments[i].size();
		af.reserve(total);
		for (size_t i = 0; i < collector.fragments.size(); ++i)
			af.insert(af.end(), collector.fragments[i].begin(), collector.fragments[i].end());
		return af.size() >= 12;
	}
	if (!collector.rsk || collector.nominalLength == 0)
		return false;
	const size_t rows = collector.nominalLength;
	const size_t columns = collector.fragmentCount;
	std::vector<uint8_t> rs(rows * columns, 0);
	for (size_t column = 0; column < columns; ++column)
	{
		if (collector.fragments[column].size() != rows)
			return false;
		for (size_t row = 0; row < rows; ++row)
			rs[row * columns + column] = collector.fragments[column][row];
	}
	const size_t codeword = static_cast<size_t>(collector.rsk) + 48;
	const size_t chunks = rs.size() / codeword;
	if (!chunks || chunks * collector.rsk < collector.rsz)
		return false;
	af.reserve(chunks * collector.rsk - collector.rsz);
	for (size_t chunk = 0; chunk < chunks; ++chunk)
		af.insert(af.end(), rs.begin() + chunk * codeword,
			rs.begin() + chunk * codeword + collector.rsk);
	if (collector.rsz)
		af.resize(af.size() - collector.rsz);
	/* Satellite delivery is normally error-free. RS correction is deliberately
	 * deferred; the AF CRC rejects an uncorrected packet instead of emitting bad audio. */
	return af.size() >= 12;
}

void eDABDecoder::trimPFCollectors()
{
	// Drop by age. begin() is the lowest sequence number, which is the newest
	// collector right after the 16 bit sequence wraps.
	while (m_pf_collectors.size() > 8)
	{
		auto oldest = m_pf_collectors.begin();
		for (auto entry = m_pf_collectors.begin(); entry != m_pf_collectors.end(); ++entry)
		{
			if (entry->second.arrival < oldest->second.arrival)
				oldest = entry;
		}
		m_pf_collectors.erase(oldest);
	}
}

void eDABDecoder::processTags(const uint8_t *data, size_t length)
{
	std::vector<uint8_t> fic;
	std::vector<Stream> streams;
	bool isETI = false;
	size_t position = 0;
	while (position + 8 <= length)
	{
		const uint32_t id = read32(data + position);
		const uint32_t bitLength = read32(data + position + 4);
		if (bitLength & 7)
			return;
		const size_t valueLength = bitLength / 8;
		position += 8;
		if (valueLength > length - position)
			return;
		const uint8_t *value = data + position;
		if (id == 0x2a707472 && valueLength == 8) // *ptr
			isETI = read32(value) == 0x44455449 && read16(value + 4) == 0 && read16(value + 6) == 0;
		else if (id == 0x64657469 && valueLength >= 6) // deti
		{
			const uint16_t deti = read16(value);
			const bool atstf = deti & 0x8000;
			const bool ficf = deti & 0x4000;
			const uint32_t etiHeader = read32(value + 2);
			const int mode = (etiHeader >> 22) & 3;
			const size_t ficLength = ficf ? (mode == 3 ? 128 : 96) : 0;
			const size_t ficOffset = 6 + (atstf ? 8 : 0);
			if (ficLength && ficOffset + ficLength <= valueLength)
				fic.assign(value + ficOffset, value + ficOffset + ficLength);
		}
		else if ((id & 0xffffff00) == 0x65737400 && (id & 0xff) && valueLength >= 3) // estN
		{
			const uint32_t sstc = read24(value);
			Stream stream;
			stream.subchannel = (sstc >> 18) & 0x3f;
			stream.startAddress = (sstc >> 8) & 0x3ff;
			stream.data.assign(value + 3, value + valueLength);
			streams.push_back(stream);
		}
		position += valueLength;
	}
	if (!isETI || fic.empty())
		return;
	++m_eti_frames;
	parseFIC(fic.data(), fic.size());
	feedMSC(streams);
}

void eDABDecoder::parseFIC(const uint8_t *data, size_t length)
{
	++m_fic_frames;
	for (size_t fib = 0; fib + 32 <= length; fib += 32)
	{
		if (!checkInvertedCRC(data + fib, 32))  // The last two bytes carry the FIB CRC.
		{
			++m_crc_errors;
			continue;
		}
		size_t position = 0;
		while (position < 30 && data[fib + position] != 0xff)
		{
			const uint8_t header = data[fib + position];
			const int type = header >> 5;
			const size_t figLength = header & 0x1f;
			if (!figLength || position + 1 + figLength > 30)
				break;
			const uint8_t *fig = data + fib + position + 1;
			if (type == 0)
				parseFIG0(fig, figLength);
			else if (type == 1)
				parseFIG1(fig, figLength);
			position += figLength + 1;
		}
	}
	resolveService();
}

void eDABDecoder::parseFIG0(const uint8_t *data, size_t length)
{
	if (!length)
		return;
	const bool otherEnsemble = data[0] & 0x40;
	const bool longSid = data[0] & 0x20;
	const int extension = data[0] & 0x1f;
	if (otherEnsemble)
		return;
	size_t position = 1;
	if (extension == 0 && position + 2 <= length)
	{
		const uint16_t eid = read16(data + position);
		if (!m_ensemble_id)
		{
			m_ensemble_id = eid;
			++m_service_revision;
		}
	}
	else if (extension == 1)
	{
		while (position + 3 <= length)
		{
			const uint16_t first = read16(data + position);
			const int subchannelId = first >> 10;
			Subchannel subchannel;
			subchannel.startAddress = first & 0x3ff;
			const uint8_t form = data[position + 2];
			if (form & 0x80)
			{
				if (position + 4 > length)
					break;
				const int option = (form >> 4) & 7;
				const int protection = (form >> 2) & 3;
				const int profile = option * 4 + protection;
				subchannel.size = ((form & 3) << 8) | data[position + 3];
				if (profile >= 0 && profile < 8 && subchannel.size % eepProfiles[profile].sizeMultiplier == 0)
					subchannel.bitrate = subchannel.size / eepProfiles[profile].sizeMultiplier * eepProfiles[profile].rateMultiplier;
				position += 4;
			}
			else
			{
				const int tableIndex = form & 0x3f;
				subchannel.size = uepProfiles[tableIndex].size;
				subchannel.bitrate = uepProfiles[tableIndex].bitrate;
				position += 3;
			}
			std::map<int, Subchannel>::const_iterator previous = m_subchannels.find(subchannelId);
			if (previous == m_subchannels.end() || previous->second.startAddress != subchannel.startAddress ||
				previous->second.size != subchannel.size || previous->second.bitrate != subchannel.bitrate)
			{
				m_subchannels[subchannelId] = subchannel;
				++m_service_revision;
			}
		}
	}
	else if (extension == 2)
	{
		while (position + (longSid ? 5 : 3) <= length)
		{
			const uint32_t sid = longSid ? read32(data + position) : read16(data + position);
			position += longSid ? 4 : 2;
			const int components = data[position++] & 0x0f;
			for (int component = 0; component < components && position + 2 <= length; ++component)
			{
				const uint16_t description = read16(data + position);
				position += 2;
				if ((description >> 14) == 0)
				{
					Service &service = m_services[sid];
					const bool primary = description & 2;
					if (primary || service.subchannel < 0)
					{
						const int subchannel = (description >> 2) & 0x3f;
						const bool dabplus = ((description >> 8) & 0x3f) == 0x3f;
						if (service.subchannel != subchannel || service.dabplus != dabplus)
						{
							service.subchannel = subchannel;
							service.dabplus = dabplus;
							++m_service_revision;
						}
					}
				}
			}
		}
	}
}

void eDABDecoder::parseFIG1(const uint8_t *data, size_t length)
{
	if (length < 1)
		return;
	const int extension = data[0] & 7;
	const bool otherEnsemble = data[0] & 8;
	const int charset = data[0] >> 4;
	if (otherEnsemble)
		return;
	if (extension == 0 && length >= 19)
	{
		const uint16_t eid = read16(data + 1);
		if (!m_ensemble_id || eid == m_ensemble_id)
		{
			const std::string label = decodeLabel(data + 3, 16, charset);
			if (m_ensemble_label != label)
			{
				m_ensemble_label = label;
				++m_service_revision;
			}
		}
	}
	else if (extension == 1 && length >= 21)
	{
		const uint16_t sid = read16(data + 1);
		const std::string label = decodeLabel(data + 3, 16, charset);
		if (m_services[sid].label != label)
		{
			m_services[sid].label = label;
			++m_service_revision;
		}
	}
	else if (extension == 5 && length >= 23)
	{
		const uint32_t sid = read32(data + 1);
		const std::string label = decodeLabel(data + 5, 16, charset);
		if (m_services[sid].label != label)
		{
			m_services[sid].label = label;
			++m_service_revision;
		}
	}
}

void eDABDecoder::resolveService()
{
	std::map<uint32_t, Service>::const_iterator service = m_services.find(m_service_id);
	if (service == m_services.end() || service->second.subchannel < 0)
		return;
	std::map<int, Subchannel>::const_iterator subchannel = m_subchannels.find(service->second.subchannel);
	if (subchannel == m_subchannels.end() || !subchannel->second.bitrate)
		return;
	const bool changed = m_selected_subchannel != service->second.subchannel ||
		m_selected_bitrate != subchannel->second.bitrate || m_selected_dabplus != service->second.dabplus;
	m_selected_subchannel = service->second.subchannel;
	m_selected_start_address = subchannel->second.startAddress;
	m_selected_bitrate = subchannel->second.bitrate;
	m_selected_dabplus = service->second.dabplus;
	m_service_label = service->second.label;
	if (changed)
	{
		m_superframe.clear();
		m_superframe_parts = 0;
		m_superframe_part_size = 0;
		eDebug("[eDABDecoder] service sid=%08x label='%s' subch=%d sad=%d bitrate=%d codec=%s ensemble='%s'",
			m_service_id, m_service_label.c_str(), m_selected_subchannel, m_selected_start_address,
			m_selected_bitrate, m_selected_dabplus ? "DAB+" : "DAB/MP2", m_ensemble_label.c_str());
	}
}

void eDABDecoder::feedMSC(const std::vector<Stream> &streams)
{
	if (m_selected_subchannel < 0)
		return;
	for (size_t i = 0; i < streams.size(); ++i)
	{
		if (streams[i].subchannel != m_selected_subchannel)
			continue;
		++m_msc_frames;
		if (m_selected_dabplus)
			feedDABPlus(streams[i].data.data(), streams[i].data.size());
		return;
	}
}

void eDABDecoder::feedDABPlus(const uint8_t *data, size_t length)
{
	if (!data || length < 11 || m_selected_bitrate <= 0)
		return;
	if (!m_superframe_parts)
	{
		if (!checkFireCode(data, length))
			return;
		m_superframe.clear();
		m_superframe_part_size = length;
		m_superframe.reserve(length * 5);
	}
	if (length != m_superframe_part_size)
	{
		m_superframe.clear();
		m_superframe_parts = 0;
		return;
	}
	m_superframe.insert(m_superframe.end(), data, data + length);
	if (++m_superframe_parts == 5)
	{
		processSuperframe();
		m_superframe.clear();
		m_superframe_parts = 0;
	}
}

void eDABDecoder::processSuperframe()
{
	const int rsColumns = m_selected_bitrate / 8;
	const size_t audioSize = static_cast<size_t>(rsColumns) * 110;
	if (rsColumns <= 0 || m_superframe.size() < audioSize || m_superframe.size() != m_superframe_part_size * 5)
		return;
	const uint8_t config = m_superframe[2];
	const bool dacRate = config & 0x40;
	const bool sbr = config & 0x20;
	const int auCountTable[4] = {4, 2, 6, 3};
	const int auCount = auCountTable[(dacRate ? 2 : 0) | (sbr ? 1 : 0)];
	const uint64_t auDurationNs = 120000000ULL / static_cast<uint64_t>(auCount);
	uint16_t starts[7] = {};
	if (auCount == 2)
	{
		starts[0] = 5;
		starts[1] = static_cast<uint16_t>((m_superframe[3] << 4) | (m_superframe[4] >> 4));
	}
	else if (auCount == 3)
	{
		starts[0] = 6;
		starts[1] = static_cast<uint16_t>((m_superframe[3] << 4) | (m_superframe[4] >> 4));
		starts[2] = static_cast<uint16_t>(((m_superframe[4] & 0x0f) << 8) | m_superframe[5]);
	}
	else if (auCount == 4)
	{
		starts[0] = 8;
		starts[1] = static_cast<uint16_t>((m_superframe[3] << 4) | (m_superframe[4] >> 4));
		starts[2] = static_cast<uint16_t>(((m_superframe[4] & 0x0f) << 8) | m_superframe[5]);
		starts[3] = static_cast<uint16_t>((m_superframe[6] << 4) | (m_superframe[7] >> 4));
	}
	else
	{
		starts[0] = 11;
		starts[1] = static_cast<uint16_t>((m_superframe[3] << 4) | (m_superframe[4] >> 4));
		starts[2] = static_cast<uint16_t>(((m_superframe[4] & 0x0f) << 8) | m_superframe[5]);
		starts[3] = static_cast<uint16_t>((m_superframe[6] << 4) | (m_superframe[7] >> 4));
		starts[4] = static_cast<uint16_t>(((m_superframe[7] & 0x0f) << 8) | m_superframe[8]);
		starts[5] = static_cast<uint16_t>((m_superframe[9] << 4) | (m_superframe[10] >> 4));
	}
	starts[auCount] = static_cast<uint16_t>(audioSize);
	for (int au = 0; au < auCount; ++au)
	{
		if (!starts[au] || starts[au + 1] <= starts[au] || starts[au + 1] > audioSize)
			continue;
		const size_t size = starts[au + 1] - starts[au];
		if (size < 3)
			continue;
		const uint8_t *payload = m_superframe.data() + starts[au];
		uint16_t crc = crc16(0xffff, payload, size - 2, 0x1021);
		const uint8_t inverted[2] = {static_cast<uint8_t>(payload[size - 2] ^ 0xff),
			static_cast<uint8_t>(payload[size - 1] ^ 0xff)};
		if (crc16(crc, inverted, 2, 0x1021) != 0)
		{
			++m_crc_errors;
			continue;
		}
		inspectPAD(payload, size - 2);
		emitLOAS(payload, size - 2, config, auDurationNs);
	}
}

void eDABDecoder::inspectPAD(const uint8_t *data, size_t length)
{
	/* DAB+ carries PAD in an AAC data_stream_element (DSE). */
	if (length < 2 || (data[0] >> 5) != 4)
		return;
	size_t position = 2;
	size_t count = data[1];
	if (count == 255)
	{
		if (length < 3)
			return;
		count += data[2];
		++position;
	}
	if (position + count > length || count < 2)
		return;
	++m_pad_packets;
	const uint8_t *pad = data + position;
	m_pad_decoder.Process(pad, count - 2, true, pad + count - 2);
}

void eDABDecoder::PADChangeDynamicLabel(const DABlinPAD::DL_STATE &label)
{
	const std::string text = DABlinPAD::CharsetTools::ConvertTextToUTF8(
		label.raw.empty() ? nullptr : &label.raw[0], label.raw.size(), label.charset, false, nullptr);
	if (text != m_dynamic_label)
	{
		m_dynamic_label = text;
		++m_dls_labels;
	}
}

void eDABDecoder::PADChangeSlide(const DABlinPAD::MOT_FILE &slide)
{
	if (slide.data.empty())
		return;
	int format = 0;
	if (slide.content_sub_type == DABlinPAD::MOT_FILE::CONTENT_SUB_TYPE_JFIF)
		format = 1;
	else if (slide.content_sub_type == DABlinPAD::MOT_FILE::CONTENT_SUB_TYPE_PNG)
		format = 3;
	else
		return;
	m_slide_format = format;
	++m_slides;
	if (m_image_callback)
		m_image_callback(&slide.data[0], slide.data.size(), format);
}

void eDABDecoder::emitLOAS(const uint8_t *data, size_t length, uint8_t config, uint64_t durationNs)
{
	if (!m_audio_callback || !length)
		return;
	const bool dacRate = config & 0x40;
	const bool sbr = config & 0x20;
	const bool stereo = config & 0x10;
	const unsigned coreSampleIndexTable[4] = {5, 8, 3, 6}; // 32, 16, 48, 24 kHz
	const unsigned extensionSampleIndex = dacRate ? 3 : 5; // 48 or 32 kHz
	const unsigned coreSampleIndex = coreSampleIndexTable[(dacRate ? 2 : 0) | (sbr ? 1 : 0)];
	const unsigned channels = stereo ? 2 : 1;

	/* DAB+ access units use the 960-sample AAC transform. ADTS cannot signal
	 * that transform, so wrap each AU in LOAS/LATM with an AudioSpecificConfig
	 * carrying GASpecificConfig.frameLengthFlag = 1. This follows the untouched
	 * DAB+ output used by DABlin. */
	LATMBitWriter writer;
	writer.addBits(0x2b7, 11); // AudioSyncStream syncword
	writer.addBits(0, 13); // audioMuxLengthBytes, filled by finishAudioSyncStream()
	writer.addBits(0, 1); // useSameStreamMux
	writer.addBits(0, 1); // audioMuxVersion
	writer.addBits(1, 1); // allStreamsSameTimeFraming
	writer.addBits(0, 6); // numSubFrames
	writer.addBits(0, 4); // numProgram
	writer.addBits(0, 3); // numLayer
	if (sbr)
	{
		writer.addBits(5, 5); // SBR
		writer.addBits(coreSampleIndex, 4);
		writer.addBits(channels, 4);
		writer.addBits(extensionSampleIndex, 4);
		writer.addBits(2, 5); // AAC-LC core
	}
	else
	{
		writer.addBits(2, 5); // AAC-LC
		writer.addBits(coreSampleIndex, 4);
		writer.addBits(channels, 4);
	}
	writer.addBits(0b100, 3); // 960 transform, no core dependency/extension
	writer.addBits(0, 3); // frameLengthType
	writer.addBits(0xff, 8); // latmBufferFullness
	writer.addBits(0, 1); // otherDataPresent
	writer.addBits(0, 1); // crcCheckPresent
	for (size_t remaining = length; remaining >= 255; remaining -= 255)
		writer.addBits(0xff, 8);
	writer.addBits(length % 255, 8);
	writer.addBytes(data, length);
	std::vector<uint8_t> frame = writer.finishAudioSyncStream();
	if (frame.empty())
		return;
	++m_audio_frames;
	m_audio_callback(data, length, frame.data(), frame.size(), durationNs, config);
}
