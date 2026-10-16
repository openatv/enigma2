#include <lib/driver/inputdevicedfu.h>

#include <algorithm>

namespace
{
uint32_t read32le(const uint8_t *data)
{
	return uint32_t(data[0]) | (uint32_t(data[1]) << 8) |
		(uint32_t(data[2]) << 16) | (uint32_t(data[3]) << 24);
}

void write32le(uint8_t *data, uint32_t value)
{
	for (int index = 0; index < 4; ++index)
		data[index] = uint8_t(value >> (8 * index));
}

/* Reflected IEEE CRC32, as returned by the RCU. The existing DVB CRC uses
 * a different bit order. Keep the unfinalized accumulator between packets.
 */
uint32_t updateCrc(uint32_t crc, const uint8_t *data, size_t size)
{
	for (size_t index = 0; index < size; ++index)
	{
		crc ^= data[index];
		for (int bit = 0; bit < 8; ++bit)
			crc = (crc >> 1) ^ (0xedb88320U & (0U - (crc & 1U)));
	}
	return crc;
}
}

eDreamBleDfuSession::eDreamBleDfuSession(Send send, Event event, Event progress, Timer timer)
	: m_send(send), m_event(event), m_progress(progress), m_timer(timer), m_state(IDLE),
	  m_section(0), m_command(0), m_offset(0), m_objectEnd(0), m_maxObject(0),
	  m_pendingBytes(0), m_crc(0xffffffffU), m_notifyRetries(0), m_generation(0)
{
}

bool eDreamBleDfuSession::start(const std::vector<uint8_t> &dat, const std::vector<uint8_t> &bin)
{
	if (active() || dat.empty() || dat.size() > 4096 || bin.empty() || bin.size() > MAX_FILE_SIZE)
		return false;
	++m_generation;
	m_dat = dat;
	m_bin = bin;
	m_section = DFU_FIRMWARE_TYPE_DAT;
	m_notifyRetries = 0;
	notify();
	return active();
}

void eDreamBleDfuSession::stop()
{
	++m_generation;
	m_state = IDLE;
	m_timer(0);
	m_dat.clear();
	m_bin.clear();
}

void eDreamBleDfuSession::fail(int event, int value)
{
	stop();
	m_event(event, value);
}

void eDreamBleDfuSession::disconnected()
{
	if (active())
		fail(DFU_EVT_UPLOAD_ERROR, m_section);
}

const std::vector<uint8_t> &eDreamBleDfuSession::firmware() const
{
	return m_section == DFU_FIRMWARE_TYPE_DAT ? m_dat : m_bin;
}

bool eDreamBleDfuSession::send(uint8_t command, const uint8_t *data, size_t size, int error)
{
	m_timer(RESPONSE_TIMEOUT);
	if (m_send(command, data, size))
		return true;
	fail(error, m_section);
	return false;
}

void eDreamBleDfuSession::notify()
{
	m_state = NOTIFY;
	send(0xd0, 0, 0, DFU_EVT_ENABLE_NOTIFY_ERROR);
}

void eDreamBleDfuSession::beginSection(uint8_t section)
{
	m_section = section;
	m_offset = m_objectEnd = m_maxObject = m_pendingBytes = 0;
	m_crc = 0xffffffffU;
	const uint8_t command[] = { READ_OBJECT, section };
	control(command, sizeof(command));
}

void eDreamBleDfuSession::control(const uint8_t *data, size_t size)
{
	m_state = CONTROL;
	m_command = data[0];
	send(0xd1, data, size, DFU_EVT_WRITE_CONTROL_ERROR);
}

void eDreamBleDfuSession::createObject()
{
	size_t size = std::min(m_maxObject, firmware().size() - m_offset);
	if (!size)
	{
		fail(DFU_EVT_OBJECT_CREATE_ERROR, m_section);
		return;
	}
	m_objectEnd = m_offset + size;
	uint8_t command[] = { 1, m_section, 0, 0, 0, 0 };
	write32le(command + 2, size);
	control(command, sizeof(command));
}

void eDreamBleDfuSession::streamData()
{
	if (m_offset == m_objectEnd)
	{
		const uint8_t command = 3;
		control(&command, 1);
		return;
	}
	m_pendingBytes = std::min(size_t(64), m_objectEnd - m_offset);
	m_state = DATA;
	send(0xd2, firmware().data() + m_offset, m_pendingBytes, DFU_EVT_UPLOAD_ERROR);
}

void eDreamBleDfuSession::receive(const uint8_t *data, size_t size)
{
	if (!active() || !data || !size)
		return;
	if (data[0] == 0xd0 && m_state == NOTIFY)
	{
		if (size != 2)
			fail(DFU_EVT_ENABLE_NOTIFY_ERROR, m_section);
		else if (data[1] == 1)
			beginSection(DFU_FIRMWARE_TYPE_DAT);
		else if (m_notifyRetries++ < 4)
		{
			m_state = NOTIFY_RETRY;
			m_timer(1000);
		}
		else
			fail(DFU_EVT_ENABLE_NOTIFY_ERROR, m_section);
	}
	else if (data[0] == 0xd2 && m_state == DATA)
	{
		if (size != 2 || data[1] != 1)
		{
			fail(DFU_EVT_UPLOAD_ERROR, m_section);
			return;
		}
		m_crc = updateCrc(m_crc, firmware().data() + m_offset, m_pendingBytes);
		m_offset += m_pendingBytes;
		m_state = DATA_DELAY;
		m_timer(100);
		m_progress(m_offset, firmware().size());
	}
	else if (data[0] == 0xd4 && m_state == CONTROL)
		controlResponse(data + 1, size - 1);
	/* D1 FF also precedes successful control responses in DreamOS captures.
	 * D3 confirms transport completion, but only D4 is the RCU result.
	 * Neither acknowledgement advances the command or disables its timeout.
	 */
}

void eDreamBleDfuSession::controlResponse(const uint8_t *data, size_t size)
{
	if (size < 3 || data[0] != DFU_TAG_RESPONSE || data[1] != m_command)
	{
		fail(DFU_EVT_WRITE_CONTROL_ERROR, m_command);
		return;
	}
	m_timer(0);
	if (data[2] != 1)
	{
		if (m_command == 4)
			fail(DFU_EVT_EXECUTE_ERROR, (int(data[2]) << 8) | (size > 3 ? data[3] : 0));
		else
			fail(DFU_EVT_COMMAND_ERROR, m_command == READ_OBJECT ? int(DFU_CMD_READ_OBJECT) : int(m_command));
		return;
	}
	unsigned int generation = m_generation;
	switch (m_command)
	{
		case READ_OBJECT:
			if (size != 15 || !(m_maxObject = read32le(data + 3)) || m_maxObject > MAX_FILE_SIZE ||
				(m_section == DFU_FIRMWARE_TYPE_DAT && m_maxObject < m_dat.size()))
			{
				fail(DFU_EVT_OBJECT_READ_ERROR, m_section);
				return;
			}
			/* DreamOS starts a new object instead of resuming an old upload.
			 * CREATE of DAT resets the remote's previous transaction.
			 */
			m_event(DFU_EVT_OBJECT_READ_SUCCESS, m_section);
			if (generation == m_generation && active())
				createObject();
			break;
		case 1:
			if (size != 3)
			{
				fail(DFU_EVT_OBJECT_CREATE_ERROR, m_section);
				return;
			}
			m_event(DFU_EVT_OBJECT_CREATE_SUCCESS, m_section);
			if (generation == m_generation && active())
				streamData();
			break;
		case 3:
			if (size != 11 || read32le(data + 3) != m_offset || read32le(data + 7) != (m_crc ^ 0xffffffffU))
			{
				fail(DFU_EVT_CHECKSUM_INVALID, m_section);
				return;
			}
			m_event(DFU_EVT_CHECKSUM_VALID, m_section);
			if (generation == m_generation && active())
			{
				const uint8_t command = 4;
				control(&command, 1);
			}
			break;
		case 4:
			if (size != 3)
			{
				fail(DFU_EVT_EXECUTE_ERROR, 0);
				return;
			}
			if (m_offset < firmware().size())
				createObject();
			else if (m_section == DFU_FIRMWARE_TYPE_DAT)
			{
				m_state = NEXT_SECTION;
				m_event(DFU_EVT_EXECUTE_SUCCESS, DFU_FIRMWARE_TYPE_DAT);
				if (generation == m_generation && active())
					beginSection(DFU_FIRMWARE_TYPE_BIN);
			}
			else
			{
				stop();
				m_event(DFU_EVT_EXECUTE_SUCCESS, DFU_FIRMWARE_TYPE_BIN);
			}
			break;
	}
}

void eDreamBleDfuSession::timeout()
{
	if (m_state == NOTIFY_RETRY)
		notify();
	else if (m_state == DATA_DELAY)
		streamData();
	else if (m_state == NOTIFY)
		fail(DFU_EVT_ENABLE_NOTIFY_ERROR, m_section);
	else if (m_state == CONTROL)
		fail(DFU_EVT_WRITE_CONTROL_ERROR, m_command);
	else if (active())
		fail(DFU_EVT_UPLOAD_ERROR, m_section);
}
