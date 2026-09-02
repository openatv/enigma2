#include <lib/service/dabspi.h>

#include <algorithm>
#include <cctype>
#include <fstream>
#include <iterator>
#include <map>
#include <sstream>

namespace
{
enum SPIElementTag
{
	CDATA = 0x01,
	EPG = 0x02,
	TOKEN_TABLE = 0x04,
	DEFAULT_BEARER = 0x05,
	DEFAULT_LANGUAGE = 0x06,
	SHORT_NAME = 0x10,
	MEDIUM_NAME = 0x11,
	LONG_NAME = 0x12,
	MEDIA_DESCRIPTION = 0x13,
	LOCATION = 0x19,
	SHORT_DESCRIPTION = 0x1a,
	LONG_DESCRIPTION = 0x1b,
	PROGRAMME = 0x1c,
	SCHEDULE = 0x21,
	SCOPE = 0x24,
	SERVICE_SCOPE = 0x25,
	TIME = 0x2c,
	PROGRAMME_EVENT = 0x2e
};

struct TLV
{
	uint8_t tag = 0;
	const uint8_t *value = nullptr;
	size_t length = 0;
	size_t total = 0;
};

struct Node
{
	uint8_t tag = 0;
	std::map<uint8_t, std::vector<uint8_t> > attributes;
	std::vector<Node> children;
	std::string text;
};

bool readTLV(const uint8_t *data, size_t available, TLV &tlv)
{
	if (available < 2)
		return false;
	tlv.tag = data[0];
	size_t header = 2;
	size_t length = data[1];
	if (length == 0xfe)
	{
		if (available < 4)
			return false;
		length = (static_cast<size_t>(data[2]) << 8) | data[3];
		header = 4;
	}
	else if (length == 0xff)
	{
		if (available < 5)
			return false;
		length = (static_cast<size_t>(data[2]) << 16) |
			(static_cast<size_t>(data[3]) << 8) | data[4];
		header = 5;
	}
	if (length > available - header)
		return false;
	tlv.value = data + header;
	tlv.length = length;
	tlv.total = header + length;
	return true;
}

std::string trimText(const std::string &text)
{
	size_t begin = 0;
	while (begin < text.size() && (text[begin] == 0 || std::isspace(static_cast<unsigned char>(text[begin]))))
		++begin;
	size_t end = text.size();
	while (end > begin && (text[end - 1] == 0 || std::isspace(static_cast<unsigned char>(text[end - 1]))))
		--end;
	return text.substr(begin, end - begin);
}

uint32_t unsignedValue(const std::vector<uint8_t> &value)
{
	uint32_t result = 0;
	const size_t first = value.size() > 4 ? value.size() - 4 : 0;
	for (size_t index = first; index < value.size(); ++index)
		result = (result << 8) | value[index];
	return result;
}

class BinaryDecoder
{
public:
	BinaryDecoder()
		: m_tokens(20)
	{
	}

	bool decode(const std::vector<uint8_t> &data, uint16_t fallbackEnsembleId,
		std::vector<eDABSPIEvent> &events, std::string &error)
	{
		TLV rootTLV;
		if (data.empty() || !readTLV(data.data(), data.size(), rootTLV))
		{
			error = "truncated root TLV";
			return false;
		}
		if (rootTLV.tag != EPG)
		{
			std::ostringstream message;
			message << "unsupported SPI root tag 0x" << std::hex << unsigned(rootTLV.tag);
			error = message.str();
			return false;
		}
		Node root;
		if (!decodeNode(rootTLV, root, error))
			return false;

		std::vector<const Node *> schedules;
		findChildren(root, SCHEDULE, schedules);
		for (std::vector<const Node *>::const_iterator schedule = schedules.begin(); schedule != schedules.end(); ++schedule)
			decodeSchedule(**schedule, fallbackEnsembleId, events);
		return true;
	}

private:
	bool decodeNode(const TLV &tlv, Node &node, std::string &error)
	{
		node.tag = tlv.tag;
		size_t offset = 0;
		while (offset < tlv.length)
		{
			TLV item;
			if (!readTLV(tlv.value + offset, tlv.length - offset, item))
			{
				error = "truncated child TLV";
				return false;
			}
			if (item.tag >= 0x80)
				node.attributes[item.tag & 0x0f] = std::vector<uint8_t>(item.value, item.value + item.length);
			else if (item.tag == TOKEN_TABLE)
			{
				if (!decodeTokenTable(item, error))
					return false;
			}
			else if (item.tag == CDATA)
				node.text += decodeText(item.value, item.length);
			else if (item.tag == DEFAULT_BEARER || item.tag == DEFAULT_LANGUAGE)
			{
				/* These are compact top-level metadata fields, not nested TLVs.
				 * Their raw values supply omitted bearer/xml:lang attributes.  The
				 * EPG cache does not currently expose either value, but the decoder
				 * must still consume them without interpreting their payload as a
				 * child element. */
			}
			else if (item.tag > DEFAULT_LANGUAGE && item.tag < 0x80)
			{
				Node child;
				if (!decodeNode(item, child, error))
					return false;
				node.children.push_back(child);
			}
			offset += item.total;
		}
		node.text = trimText(node.text);
		return true;
	}

	bool decodeTokenTable(const TLV &tlv, std::string &error)
	{
		std::fill(m_tokens.begin(), m_tokens.end(), std::string());
		size_t offset = 0;
		while (offset < tlv.length)
		{
			if (tlv.length - offset < 2)
			{
				error = "truncated SPI token table";
				return false;
			}
			const uint8_t token = tlv.value[offset++];
			const size_t length = tlv.value[offset++];
			if (length > tlv.length - offset)
			{
				error = "invalid SPI token length";
				return false;
			}
			if (token < m_tokens.size())
				m_tokens[token].assign(reinterpret_cast<const char *>(tlv.value + offset), length);
			offset += length;
		}
		return true;
	}

	std::string decodeText(const uint8_t *data, size_t length) const
	{
		std::string result;
		for (size_t index = 0; index < length; ++index)
		{
			const uint8_t value = data[index];
			if (value > 0 && value < m_tokens.size() && value != 0x09 && value != 0x0a && value != 0x0d)
				result += m_tokens[value];
			else
				result += static_cast<char>(value);
		}
		return result;
	}

	static void findChildren(const Node &node, uint8_t tag, std::vector<const Node *> &result)
	{
		for (std::vector<Node>::const_iterator child = node.children.begin(); child != node.children.end(); ++child)
		{
			if (child->tag == tag)
				result.push_back(&*child);
			findChildren(*child, tag, result);
		}
	}

	static const Node *firstChild(const Node &node, uint8_t tag)
	{
		for (std::vector<Node>::const_iterator child = node.children.begin(); child != node.children.end(); ++child)
			if (child->tag == tag)
				return &*child;
		return nullptr;
	}

	static std::string childText(const Node &node, uint8_t tag)
	{
		const Node *child = firstChild(node, tag);
		return child ? child->text : std::string();
	}

	static bool decodeBearer(const std::vector<uint8_t> &value, uint16_t fallbackEnsembleId,
		uint32_t &serviceId, uint16_t &ensembleId)
	{
		if (value.empty())
			return false;
		const bool ensemblePresent = (value[0] & 0x40) != 0;
		const bool longServiceId = (value[0] & 0x20) != 0;
		size_t offset = 1;
		ensembleId = fallbackEnsembleId;
		if (ensemblePresent)
		{
			if (value.size() < offset + 3)
				return false;
			/* ECC precedes the two-byte DAB ensemble identifier. */
			++offset;
			ensembleId = (static_cast<uint16_t>(value[offset]) << 8) | value[offset + 1];
			offset += 2;
		}
		const size_t sidLength = longServiceId ? 4 : 2;
		if (value.size() < offset + sidLength)
			return false;
		serviceId = 0;
		for (size_t index = 0; index < sidLength; ++index)
			serviceId = (serviceId << 8) | value[offset + index];
		return serviceId != 0;
	}

	static bool decodeTimePoint(const std::vector<uint8_t> &value, time_t &result)
	{
		if (value.size() < 4)
			return false;
		const uint32_t dateAndFlags = (static_cast<uint32_t>(value[0]) << 16) |
			(static_cast<uint32_t>(value[1]) << 8) | value[2];
		const uint32_t mjd = (dateAndFlags >> 6) & 0x1ffff;
		const uint16_t clock = (static_cast<uint16_t>(value[2]) << 8) | value[3];
		const int hour = (clock >> 6) & 0x1f;
		const int minute = clock & 0x3f;
		int second = 0;
		if (value[2] & 0x08)
		{
			if (value.size() < 6)
				return false;
			second = value[4] >> 2;
		}
		if (mjd < 40587 || hour > 23 || minute > 59 || second > 59)
			return false;
		/* The encoded time point is UTC. LTO is descriptive and must not be
		 * applied here; Enigma2 localises the Unix timestamp for display. */
		result = static_cast<time_t>(static_cast<int64_t>(mjd - 40587) * 86400 +
			hour * 3600 + minute * 60 + second);
		return true;
	}

	static void scopeServices(const Node &schedule, uint16_t fallbackEnsembleId,
		std::vector<uint32_t> &serviceIds, uint16_t &ensembleId)
	{
		std::vector<const Node *> scopes;
		findChildren(schedule, SERVICE_SCOPE, scopes);
		for (std::vector<const Node *>::const_iterator scope = scopes.begin(); scope != scopes.end(); ++scope)
		{
			std::map<uint8_t, std::vector<uint8_t> >::const_iterator id = (*scope)->attributes.find(0);
			uint32_t serviceId = 0;
			uint16_t bearerEnsemble = fallbackEnsembleId;
			if (id != (*scope)->attributes.end() && decodeBearer(id->second, fallbackEnsembleId, serviceId, bearerEnsemble))
			{
				if (std::find(serviceIds.begin(), serviceIds.end(), serviceId) == serviceIds.end())
					serviceIds.push_back(serviceId);
				if (bearerEnsemble)
					ensembleId = bearerEnsemble;
			}
		}
	}

	static bool decodeLocation(const Node &programme, time_t &start, int &duration)
	{
		const Node *location = firstChild(programme, LOCATION);
		if (!location)
			return false;
		const Node *time = firstChild(*location, TIME);
		if (!time)
			return false;
		std::map<uint8_t, std::vector<uint8_t> >::const_iterator encodedTime = time->attributes.find(2);
		if (encodedTime == time->attributes.end())
			encodedTime = time->attributes.find(0);
		std::map<uint8_t, std::vector<uint8_t> >::const_iterator encodedDuration = time->attributes.find(3);
		if (encodedDuration == time->attributes.end())
			encodedDuration = time->attributes.find(1);
		if (encodedTime == time->attributes.end() || encodedDuration == time->attributes.end() ||
			!decodeTimePoint(encodedTime->second, start) || encodedDuration->second.size() < 2)
			return false;
		duration = static_cast<int>((static_cast<uint16_t>(encodedDuration->second[0]) << 8) |
			encodedDuration->second[1]);
		return duration > 0;
	}

	static void decodeProgramme(const Node &programme, const std::vector<uint32_t> &serviceIds,
		uint16_t ensembleId, std::vector<eDABSPIEvent> &events)
	{
		eDABSPIEvent event;
		event.serviceIds = serviceIds;
		event.ensembleId = ensembleId;
		std::map<uint8_t, std::vector<uint8_t> >::const_iterator shortId = programme.attributes.find(1);
		if (shortId != programme.attributes.end())
			event.shortId = unsignedValue(shortId->second);
		if (!decodeLocation(programme, event.start, event.duration))
			return;

		event.title = childText(programme, MEDIUM_NAME);
		if (event.title.empty())
			event.title = childText(programme, LONG_NAME);
		if (event.title.empty())
			event.title = childText(programme, SHORT_NAME);
		const Node *media = firstChild(programme, MEDIA_DESCRIPTION);
		if (media)
		{
			event.shortDescription = childText(*media, SHORT_DESCRIPTION);
			event.longDescription = childText(*media, LONG_DESCRIPTION);
		}
		if (!event.serviceIds.empty() && !event.title.empty())
			events.push_back(event);
	}

	static void decodeSchedule(const Node &schedule, uint16_t fallbackEnsembleId,
		std::vector<eDABSPIEvent> &events)
	{
		std::vector<uint32_t> serviceIds;
		uint16_t ensembleId = fallbackEnsembleId;
		scopeServices(schedule, fallbackEnsembleId, serviceIds, ensembleId);
		for (std::vector<Node>::const_iterator child = schedule.children.begin(); child != schedule.children.end(); ++child)
		{
			if (child->tag != PROGRAMME)
				continue;
			decodeProgramme(*child, serviceIds, ensembleId, events);
			/* A programmeEvent has its own timing and may refine its parent's
			 * title/description. Import it only when it carries a complete event. */
			for (std::vector<Node>::const_iterator sub = child->children.begin(); sub != child->children.end(); ++sub)
				if (sub->tag == PROGRAMME_EVENT)
					decodeProgramme(*sub, serviceIds, ensembleId, events);
		}
	}

	std::vector<std::string> m_tokens;
};
}

bool eDABSPIDecoder::decodeFile(const std::string &path, uint16_t fallbackEnsembleId,
	std::vector<eDABSPIEvent> &events, std::string &error)
{
	std::ifstream file(path.c_str(), std::ios::binary);
	if (!file)
	{
		error = "unable to open SPI object";
		return false;
	}
	std::vector<uint8_t> data((std::istreambuf_iterator<char>(file)), std::istreambuf_iterator<char>());
	if (data.size() > 1024 * 1024)
	{
		error = "SPI object exceeds safety limit";
		return false;
	}
	return decodeData(data.data(), data.size(), fallbackEnsembleId, events, error);
}

bool eDABSPIDecoder::decodeData(const uint8_t *data, size_t length, uint16_t fallbackEnsembleId,
	std::vector<eDABSPIEvent> &events, std::string &error)
{
	events.clear();
	if (!data || !length)
	{
		error = "empty SPI object";
		return false;
	}
	if (length > 1024 * 1024)
	{
		error = "SPI object exceeds safety limit";
		return false;
	}
	std::vector<uint8_t> input(data, data + length);
	BinaryDecoder decoder;
	return decoder.decode(input, fallbackEnsembleId, events, error);
}
