#ifndef __inputdevicedfu_h
#define __inputdevicedfu_h

class eInputDeviceDfuFlasher
{
public:
	enum
	{
		DFU_CMD_NONE = 0,
		DFU_CMD_CREATE_OBJECT = 1,
		DFU_CMD_SELECT_OBJECT = 2,
		DFU_CMD_CHECKSUM = 3,
		DFU_CMD_EXECUTE = 4,
		DFU_CMD_READ_OBJECT = 5,
		DFU_TAG_RESPONSE = 0x60,
		DFU_LOWBAT = -2,
		DFU_ERROR = -1,
		DFU_SUCCESS = 0,
		DFU_EVT_BATTERY_LOW = 1,
		DFU_EVT_ENABLE_NOTIFY_ERROR = 2,
		DFU_EVT_FILE_INVALID = 3,
		DFU_EVT_FILE_READ_ERROR = 4,
		DFU_EVT_COMMAND_ERROR = 5,
		DFU_EVT_CHECKSUM_INVALID = 6,
		DFU_EVT_CHECKSUM_VALID = 7,
		DFU_EVT_OBJECT_READ_SUCCESS = 8,
		DFU_EVT_OBJECT_READ_ERROR = 9,
		DFU_EVT_OBJECT_CREATE_SUCCESS = 10,
		DFU_EVT_OBJECT_CREATE_ERROR = 11,
		DFU_EVT_EXECUTE_SUCCESS = 12,
		DFU_EVT_EXECUTE_ERROR = 13,
		DFU_EVT_UPLOAD_ERROR = 14,
		DFU_EVT_WRITE_CONTROL_ERROR = 15,
		DFU_FIRMWARE_TYPE_DAT = 1,
		DFU_FIRMWARE_TYPE_BIN = 2
	};
};

#ifndef SWIG
#include <stddef.h>
#include <stdint.h>
#include <functional>
#include <vector>

/* The transport and timer belong to the device manager. Keeping the DFU
 * state machine independent allows replaying real adapter traffic in tests.
 */
class eDreamBleDfuSession: public eInputDeviceDfuFlasher
{
public:
	typedef std::function<bool(uint8_t, const uint8_t*, size_t)> Send;
	typedef std::function<void(int, int)> Event;
	typedef std::function<void(int)> Timer;

	eDreamBleDfuSession(Send send, Event event, Event progress, Timer timer);
	bool start(const std::vector<uint8_t> &dat, const std::vector<uint8_t> &bin);
	void receive(const uint8_t *data, size_t size);
	void timeout();
	void stop();
	void disconnected();
	bool active() const { return m_state != IDLE; }

private:
	enum State { IDLE, NOTIFY, NOTIFY_RETRY, CONTROL, DATA, DATA_DELAY, NEXT_SECTION };
	enum { READ_OBJECT = 6, RESPONSE_TIMEOUT = 5000, MAX_FILE_SIZE = 1024 * 1024 };
	Send m_send;
	Event m_event;
	Event m_progress;
	Timer m_timer;
	State m_state;
	std::vector<uint8_t> m_dat, m_bin;
	uint8_t m_section, m_command;
	size_t m_offset, m_objectEnd, m_maxObject, m_pendingBytes;
	uint32_t m_crc;
	unsigned int m_notifyRetries, m_generation;

	const std::vector<uint8_t> &firmware() const;
	bool send(uint8_t command, const uint8_t *data, size_t size, int error);
	void notify();
	void beginSection(uint8_t section);
	void control(const uint8_t *data, size_t size);
	void createObject();
	void streamData();
	void controlResponse(const uint8_t *data, size_t size);
	void fail(int event, int value);
};
#endif

#endif
