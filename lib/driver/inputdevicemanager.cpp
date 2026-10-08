#include <lib/driver/inputdevicemanager.h>

#include <lib/base/eerror.h>
#include <lib/base/init.h>
#include <lib/base/init_num.h>

#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/types.h>
#include <unistd.h>

#ifndef DREAMBLE_DEVICE
#define DREAMBLE_DEVICE "/dev/ble"
#endif

#ifndef DREAMBLE_ENABLE_IR_PROGRAMMING
#define DREAMBLE_ENABLE_IR_PROGRAMMING 1
#endif

DEFINE_REF(eManagedInputDevice);

IrProtocol::IrProtocol(int carrierPeriod, int carrierLow, int toggleMask,
	int startBits, int startOnTime, int startTotalTime,
	int oneOnTime, int oneTotalTime,
	int zeroOnTime, int zeroTotalTime,
	int stopBits, int stopOnTime, int stopTotalTime,
	int repeatMs, int repeatProtocolId)
	: carrierPeriod(carrierPeriod), carrierLow(carrierLow), toggleMask(toggleMask),
	  startBits(startBits), startOnTime(startOnTime), startTotalTime(startTotalTime),
	  oneOnTime(oneOnTime), oneTotalTime(oneTotalTime),
	  zeroOnTime(zeroOnTime), zeroTotalTime(zeroTotalTime),
	  stopBits(stopBits), stopOnTime(stopOnTime), stopTotalTime(stopTotalTime),
	  repeatMs(repeatMs), repeatProtocolId(repeatProtocolId)
{
}

IrKey::IrKey(int keyCode, int protocolId, uint32_t makeMessage,
	int makeLength, uint32_t repeatMessage, int repeatLength)
	: keyCode(keyCode), protocolId(protocolId), makeMessage(makeMessage),
	  makeLength(makeLength), repeatMessage(repeatMessage), repeatLength(repeatLength)
{
}


static void put16be(uint8_t *dst, int value)
{
	uint16_t v = (uint16_t)value;
	dst[0] = (uint8_t)(v >> 8);
	dst[1] = (uint8_t)v;
}

static uint8_t encodeIrProtocolId(int protocolId)
{
	switch (protocolId)
	{
		case IrProtocol::IR_PROTO_NEC:
			return 0x00;
		case IrProtocol::IR_PROTO_SIRC:
			return 0x01;
		case IrProtocol::IR_PROTO_JVC:
			return 0x02;
		case IrProtocol::IR_PROTO_RC5:
			return 0x03;
		case IrProtocol::IR_PROTO_REP_NEC:
			return 0x04;
		case IrProtocol::IR_PROTO_REP_JVC:
			return 0x05;
		case IrProtocol::IR_PROTO_CUSTOM:
			return 0x10;
		case IrProtocol::IR_PROTO_REP_CUSTOM:
			return 0x11;
		default:
			return (uint8_t)protocolId;
	}
}

static uint8_t encodeIrKeyCode(int keyCode)
{
	/*
	 * DreamBLE IR key payloads use the compact RCU matrix position,
	 * not the IrKey enum index.  The table is the same offset/mask
	 * matrix used by the 0x1A unconnected-key event decoder.
	 */
	static const uint8_t keyCodeLut[] = {
		0x40, /* CODE_POWER */
		0x20, /* CODE_MODE */
		0x00, /* CODE_MUTE */
		0x12, /* CODE_1 */
		0x32, /* CODE_2 */
		0x52, /* CODE_3 */
		0x13, /* CODE_4 */
		0x33, /* CODE_5 */
		0x53, /* CODE_6 */
		0x14, /* CODE_7 */
		0x34, /* CODE_8 */
		0x54, /* CODE_9 */
		0x35, /* CODE_0 */
		0x15, /* CODE_PREVIOUS / CODE_REWIND */
		0x55, /* CODE_NEXT / CODE_FASTFORWARD */
		0x10, /* CODE_VOLUMEUP */
		0x11, /* CODE_VOLUMEDOWN */
		0x30, /* CODE_EXIT */
		0x50, /* CODE_CHANNELUP */
		0x51, /* CODE_CHANNELDOWN */
		0x05, /* CODE_INFO */
		0x45, /* CODE_MENU */
		0x07, /* CODE_AUDIO */
		0x47, /* CODE_VIDEO */
		0x25, /* CODE_UP */
		0x27, /* CODE_DOWN */
		0x06, /* CODE_LEFT */
		0x46, /* CODE_RIGHT */
		0x26, /* CODE_OK */
		0x04, /* CODE_RED */
		0x03, /* CODE_GREEN */
		0x23, /* CODE_YELLOW */
		0x43, /* CODE_BLUE */
		0x01, /* CODE_PREVIOUSSONG */
		0x21, /* CODE_PLAY */
		0x22, /* CODE_STOP */
		0x41, /* CODE_NEXTSONG */
		0x42, /* CODE_TEXT */
		0x02  /* CODE_RECORD */
	};
	if (keyCode >= 0 && keyCode < (int)(sizeof(keyCodeLut) / sizeof(keyCodeLut[0])))
		return keyCodeLut[keyCode];
	return (uint8_t)keyCode;
}

static void putIrMessage(uint8_t *dst, uint32_t message, int length)
{
	/*
	 * DreamOS stores a message block as:
	 *   16 low message bits, bit length, 16 high message bits, reserved.
	 * This exactly reproduces the traced Denon payloads and still keeps
	 * the full 32-bit value for NEC-like protocols.
	 */
	dst[0] = (uint8_t)(message >> 8);
	dst[1] = (uint8_t)message;
	dst[2] = (uint8_t)length;
	dst[3] = (uint8_t)(message >> 24);
	dst[4] = (uint8_t)(message >> 16);
	dst[5] = 0x00;
}

eManagedInputDevice::eManagedInputDevice(eInputDeviceManager *manager, const std::string &address)
	: m_address(address), m_name("DM Remote"), m_shortName("DM Remote"),
	  m_versionMajor(0), m_versionMinor(0), m_batteryLevel(0), m_rssi(0),
	  m_state(STATE_DISCONNECTED), m_encrypted(false), m_connected(false),
	  m_bound(false), m_ready(false), m_isDfu(false), m_manager(manager)
{
}

eManagedInputDevice::~eManagedInputDevice()
{
}

void eManagedInputDevice::setManager(eInputDeviceManager *manager)
{
	m_manager = manager;
}

void eManagedInputDevice::setAddress(const std::string &address)
{
	m_address = address;
}

void eManagedInputDevice::setName(const std::string &name)
{
	if (!name.empty())
		m_name = name;
}

void eManagedInputDevice::setShortName(const std::string &shortName)
{
	if (!shortName.empty())
		m_shortName = shortName;
}

void eManagedInputDevice::setVersion(int major, int minor)
{
	m_versionMajor = major;
	m_versionMinor = minor;
}

void eManagedInputDevice::setBatteryLevel(int batteryLevel)
{
	m_batteryLevel = batteryLevel;
}

void eManagedInputDevice::setRssi(int rssi)
{
	m_rssi = rssi;
}

void eManagedInputDevice::setStateFlags(int rawState)
{
	m_state = rawState;

	/* Observed DreamBLE states:
	 *   0x01 -> connected, not bound
	 *   0x82 -> connected + bound/ready
	 * Further state bits still need focused traces. Keep decoding conservative.
	 */
	m_connected = (rawState == 0x01) || (rawState & 0x80);
	m_bound = (rawState & 0x02) != 0;
	m_encrypted = (rawState & 0x40) != 0;
	m_ready = m_connected && m_bound;

	if (!m_connected)
	{
		m_bound = false;
		m_encrypted = false;
		m_ready = false;
	}
}

void eManagedInputDevice::setDfu(bool isDfu)
{
	m_isDfu = isDfu;
}

std::string eManagedInputDevice::version() const
{
	char buf[32];
	snprintf(buf, sizeof(buf), "%d.%d", m_versionMajor, m_versionMinor);
	return buf;
}

int eManagedInputDevice::checkVersion(int major, int minor) const
{
	/* IR programming is deliberately disabled until E8/E9/EA payloads are
	 * fully traced. Hide the DreamOS IR setup entry that is gated by 1.3.
	 */
#if !DREAMBLE_ENABLE_IR_PROGRAMMING
	if (major == 1 && minor >= 3)
		return -1;
#endif
	if (m_versionMajor != major)
		return m_versionMajor - major;
	return m_versionMinor - minor;
}

int eManagedInputDevice::connect()
{
	return m_manager ? m_manager->connectDevice(this) : -1;
}

int eManagedInputDevice::disconnect()
{
	return m_manager ? m_manager->disconnectDevice(this) : -1;
}

int eManagedInputDevice::vibrate()
{
	return m_manager ? m_manager->vibrate(this) : -1;
}

int eManagedInputDevice::setLedColor(int rgb)
{
	return m_manager ? m_manager->setLedColor(this, rgb) : -1;
}

int eManagedInputDevice::setLedColorIr(int rgb)
{
	return m_manager ? m_manager->setLedColorIr(this, rgb) : -1;
}

int eManagedInputDevice::setIrProtocol(bool isRepeat, IrProtocol *protocol)
{
	return m_manager ? m_manager->setIrProtocol(this, isRepeat, protocol) : -1;
}

int eManagedInputDevice::setIrKey(IrKey *key)
{
	return m_manager ? m_manager->setIrKey(this, key) : -1;
}

int eManagedInputDevice::resetIr()
{
	return m_manager ? m_manager->resetIr(this) : -1;
}

int eManagedInputDevice::getIrKeyCount()
{
	return m_manager ? m_manager->getIrKeyCount(this) : -1;
}

int eManagedInputDevice::dfu()
{
	return m_manager ? m_manager->dfu(this) : eInputDeviceDfuFlasher::DFU_ERROR;
}

int eManagedInputDevice::dfuFlash(const char *datFile, const char *binFile)
{
	return m_manager ? m_manager->dfuFlash(this, datFile, binFile) : eInputDeviceDfuFlasher::DFU_ERROR;
}

eInputDeviceManager *eInputDeviceManager::instance = 0;

eInputDeviceManager *eInputDeviceManager::getInstance()
{
	return instance;
}

eInputDeviceManager::eInputDeviceManager()
	: m_fd(-1), m_available(false), m_responding(false),
	  m_versionMajor(0), m_versionMinor(0)
{
	ASSERT(!instance);
	instance = this;
	start();
}

eInputDeviceManager::~eInputDeviceManager()
{
	stop();
	for (std::map<std::string, eManagedInputDevice*>::iterator it = m_devices.begin(); it != m_devices.end(); ++it)
		it->second->Release();
	m_devices.clear();
	instance = 0;
}

void eInputDeviceManager::start()
{
#ifdef DREAMNEXTGEN
	if (m_fd >= 0)
		return;

	m_fd = ::open(DREAMBLE_DEVICE, O_RDWR | O_NONBLOCK);
	if (m_fd < 0)
	{
		eDebug("[eInputDeviceManager] cannot open %s: %m", DREAMBLE_DEVICE);
		m_available = false;
		m_responding = false;
		return;
	}

	m_available = true;
	m_notifier = eSocketNotifier::create(eApp, m_fd, eSocketNotifier::Read);
	CONNECT(m_notifier->activated, eInputDeviceManager::socketActivated);
	m_scanTimer = eTimer::create(eApp);
	CONNECT(m_scanTimer->timeout, eInputDeviceManager::scanTimeout);
	eDebug("[eInputDeviceManager] DreamBLE module opened: %s", DREAMBLE_DEVICE);

	sendCommand(0x05);
	refresh();
#else
	eDebug("[eInputDeviceManager] DreamBLE backend disabled: DREAMNEXTGEN not defined");
#endif
}

void eInputDeviceManager::stop()
{
	if (m_scanTimer)
		m_scanTimer->stop();
	m_notifier = 0;
	m_scanTimer = 0;
	if (m_fd >= 0)
	{
		::close(m_fd);
		m_fd = -1;
	}
	m_available = false;
	m_responding = false;
}

bool eInputDeviceManager::hasFeature(int feature) const
{
	switch (feature)
	{
		case FEATURE_UNCONNECTED_KEYPRESS:
			return true;
		case FEATURE_DFU_UPDATE:
			return false;
		default:
			return false;
	}
}

bool eInputDeviceManager::available() const
{
	return m_available;
}

bool eInputDeviceManager::responding() const
{
	return m_responding;
}

std::string eInputDeviceManager::version() const
{
	char buf[32];
	snprintf(buf, sizeof(buf), "%d.%d", m_versionMajor, m_versionMinor);
	return buf;
}

eManagedInputDevice *eInputDeviceManager::getDevice(const std::string &address)
{
	if (address.empty())
		return 0;
	return findOrCreateDevice(address);
}

std::vector<eManagedInputDevice*> eInputDeviceManager::getAvailableDevicesRaw()
{
	std::vector<eManagedInputDevice*> ret;
	for (std::map<std::string, eManagedInputDevice*>::iterator it = m_devices.begin(); it != m_devices.end(); ++it)
		ret.push_back(it->second);
	return ret;
}

std::vector<eManagedInputDevice*> eInputDeviceManager::getConnectedDevicesRaw()
{
	std::vector<eManagedInputDevice*> ret;
	for (std::map<std::string, eManagedInputDevice*>::iterator it = m_devices.begin(); it != m_devices.end(); ++it)
		if (it->second->connected())
			ret.push_back(it->second);
	return ret;
}

void eInputDeviceManager::rescan()
{
	uint8_t payload = 0x01;
	sendCommand(0x66, &payload, 1);
	if (m_scanTimer)
		m_scanTimer->startLongTimer(5);
}

void eInputDeviceManager::refresh()
{
	sendCommand(0x62);
}

int eInputDeviceManager::connectDevice(eManagedInputDevice *device)
{
	if (!device)
		return -1;
	return sendDeviceCommand(0x64, device);
}

int eInputDeviceManager::disconnectDevice(eManagedInputDevice *device)
{
	if (!device)
		return -1;
	int ret = sendDeviceCommand(0x65, device);
	if (!ret)
	{
		/* Update the OpenATV UI immediately. The DreamBLE adapter may send
		 * the authoritative 0x6D state event later, but the disconnect command
		 * already succeeded at this point.
		 */
		device->setStateFlags(0);
		updateDeviceState(device);
		updateDeviceList();
		refresh();
	}
	return ret;
}

int eInputDeviceManager::vibrate(eManagedInputDevice *device)
{
	uint8_t payload = 0x01;

	if (device)
		return sendDeviceCommand(0xC0, device, &payload, 1);

	/* OpenATV global listbox haptic feedback calls vibrate() without a
	 * specific device. In that case vibrate all connected DreamBLE remotes.
	 */
	int result = -1;
	for (std::map<std::string, eManagedInputDevice*>::iterator it = m_devices.begin(); it != m_devices.end(); ++it)
	{
		eManagedInputDevice *current = it->second;
		if (!current || !current->connected())
			continue;

		int ret = sendDeviceCommand(0xC0, current, &payload, 1);
		if (!ret)
			result = 0;
		else if (result)
			result = ret;
	}
	return result;
}

int eInputDeviceManager::setLedColor(eManagedInputDevice *device, int rgb)
{
	return sendRgbCommand(0xB0, device, rgb);
}

int eInputDeviceManager::setLedColorIr(eManagedInputDevice *device, int rgb)
{
	return sendRgbCommand(0xEB, device, rgb);
}

int eInputDeviceManager::setIrProtocol(eManagedInputDevice *device, bool isRepeat, IrProtocol *protocol)
{
	if (!device || !protocol)
		return -1;
#if DREAMBLE_ENABLE_IR_PROGRAMMING
	uint8_t payload[29];
	memset(payload, 0, sizeof(payload));

	payload[0] = isRepeat ? 0x01 : 0x00;
	put16be(payload + 1, protocol->carrierPeriod);
	put16be(payload + 3, protocol->carrierLow);
	put16be(payload + 5, protocol->toggleMask);
	payload[7] = (uint8_t)protocol->startBits;
	put16be(payload + 8, protocol->startOnTime);
	put16be(payload + 10, protocol->startTotalTime);
	/* payload[12..13] are reserved in the traced DreamOS payload. */
	put16be(payload + 14, protocol->zeroOnTime);
	put16be(payload + 16, protocol->zeroTotalTime);
	put16be(payload + 18, protocol->oneOnTime);
	put16be(payload + 20, protocol->oneTotalTime);
	payload[22] = (uint8_t)protocol->stopBits;
	put16be(payload + 23, protocol->stopOnTime);
	put16be(payload + 25, protocol->stopTotalTime);
	payload[27] = (uint8_t)protocol->repeatMs;
	payload[28] = encodeIrProtocolId(protocol->repeatProtocolId);

	eDebug("[eInputDeviceManager] send IR protocol command 0xea to %s repeat=%d", device->address().c_str(), isRepeat ? 1 : 0);
	return sendDeviceCommand(0xEA, device, payload, sizeof(payload));
#else
	(void)isRepeat;
	eDebug("[eInputDeviceManager] IR protocol programming is disabled until the 0xEA payload is traced");
	return -1;
#endif
}

int eInputDeviceManager::setIrKey(eManagedInputDevice *device, IrKey *key)
{
	if (!device || !key)
		return -1;
#if DREAMBLE_ENABLE_IR_PROGRAMMING
	uint8_t payload[20];
	memset(payload, 0, sizeof(payload));

	payload[0] = encodeIrKeyCode(key->keyCode);
	payload[1] = encodeIrProtocolId(key->protocolId);
	putIrMessage(payload + 2, key->repeatMessage, key->repeatLength);
	putIrMessage(payload + 8, key->makeMessage, key->makeLength);

	eDebug("[eInputDeviceManager] send IR key command 0xe9 to %s key=0x%02x protocol=0x%02x make=0x%08x/%d repeat=0x%08x/%d",
		device->address().c_str(), payload[0], payload[1], key->makeMessage, key->makeLength, key->repeatMessage, key->repeatLength);
	return sendDeviceCommand(0xE9, device, payload, sizeof(payload));
#else
	eDebug("[eInputDeviceManager] IR key programming is disabled until the 0xE9 payload is traced");
	return -1;
#endif
}

int eInputDeviceManager::resetIr(eManagedInputDevice *device)
{
	if (!device)
		return -1;
#if DREAMBLE_ENABLE_IR_PROGRAMMING
	uint8_t payload;
	payload = 0xFF;
	sendDeviceCommand(0xE8, device, &payload, 1);
	payload = 0xF0;
	return sendDeviceCommand(0xE8, device, &payload, 1);
#else
	eDebug("[eInputDeviceManager] IR reset is disabled until IR programming is enabled");
	return -1;
#endif
}

int eInputDeviceManager::getIrKeyCount(eManagedInputDevice *device)
{
	if (!device)
		return -1;
	return sendDeviceCommand(0xE6, device);
}

int eInputDeviceManager::dfu(eManagedInputDevice *device)
{
	(void)device;
	return eInputDeviceDfuFlasher::DFU_ERROR;
}

int eInputDeviceManager::dfuFlash(eManagedInputDevice *device, const char *datFile, const char *binFile)
{
	(void)device;
	(void)datFile;
	(void)binFile;
	return eInputDeviceDfuFlasher::DFU_ERROR;
}

int eInputDeviceManager::sendRgbCommand(uint8_t command, eManagedInputDevice *device, int rgb)
{
	if (!device)
		return -1;
	/* The public Python/API value is RGB (0xRRGGBB), matching the UI labels.
	 * The DreamBLE adapter expects the payload in BGR byte order.
	 * Keeping the API RGB avoids leaking the transport quirk into the plugin.
	 */
	uint8_t red = (rgb >> 16) & 0xFF;
	uint8_t green = (rgb >> 8) & 0xFF;
	uint8_t blue = rgb & 0xFF;
	uint8_t payload[3];
	payload[0] = blue;
	payload[1] = green;
	payload[2] = red;
	eDebug("[eInputDeviceManager] send LED command 0x%02x to %s rgb=0x%06x payload_bgr=%02x%02x%02x", command, device->address().c_str(), rgb & 0xFFFFFF, payload[0], payload[1], payload[2]);
	return sendDeviceCommand(command, device, payload, sizeof(payload));
}

int eInputDeviceManager::sendCommand(uint8_t command, const uint8_t *payload, size_t payloadLen)
{
	if (m_fd < 0)
		return -1;

	uint8_t buf[128];
	if (payloadLen + 1 > sizeof(buf))
		return -1;

	buf[0] = command;
	if (payload && payloadLen)
		memcpy(buf + 1, payload, payloadLen);

	ssize_t written = ::write(m_fd, buf, payloadLen + 1);
	if (written != (ssize_t)(payloadLen + 1))
	{
		eDebug("[eInputDeviceManager] write command 0x%02x failed: %m", command);
		return -1;
	}
	return 0;
}

int eInputDeviceManager::sendDeviceCommand(uint8_t command, eManagedInputDevice *device, const uint8_t *payload, size_t payloadLen)
{
	if (!device)
		return -1;

	uint8_t buf[128];
	uint8_t addr[6];
	if (!parseAddress(device->address(), addr))
		return -1;
	if (payloadLen + 6 > sizeof(buf))
		return -1;

	memcpy(buf, addr, sizeof(addr));
	if (payload && payloadLen)
		memcpy(buf + sizeof(addr), payload, payloadLen);
	return sendCommand(command, buf, sizeof(addr) + payloadLen);
}

void eInputDeviceManager::socketActivated(int what)
{
	(void)what;
	uint8_t buf[256];

	while (m_fd >= 0)
	{
		ssize_t ret = ::read(m_fd, buf, sizeof(buf));
		if (ret < 0)
		{
			if (errno != EAGAIN && errno != EWOULDBLOCK)
				eDebug("[eInputDeviceManager] read failed: %m");
			break;
		}
		if (ret == 0)
			break;
		processFrame(buf, ret);
	}
}

void eInputDeviceManager::scanTimeout()
{
	sendCommand(0x67);
	refresh();
}

std::string eInputDeviceManager::addressToString(const uint8_t *addr) const
{
	char tmp[32];
	snprintf(tmp, sizeof(tmp), "%02x:%02x:%02x:%02x:%02x:%02x",
		addr[5], addr[4], addr[3], addr[2], addr[1], addr[0]);
	return tmp;
}

bool eInputDeviceManager::parseAddress(const std::string &address, uint8_t *addr) const
{
	unsigned int p[6];
	if (sscanf(address.c_str(), "%x:%x:%x:%x:%x:%x", &p[0], &p[1], &p[2], &p[3], &p[4], &p[5]) != 6)
		return false;
	for (int i = 0; i < 6; ++i)
	{
		if (p[i] > 0xFF)
			return false;
		addr[i] = (uint8_t)p[5 - i];
	}
	return true;
}

eManagedInputDevice *eInputDeviceManager::findOrCreateDevice(const std::string &address)
{
	std::map<std::string, eManagedInputDevice*>::iterator it = m_devices.find(address);
	if (it != m_devices.end())
		return it->second;

	eManagedInputDevice *device = new eManagedInputDevice(this, address);
	device->AddRef();
	m_devices[address] = device;
	deviceListChanged();
	return device;
}

eManagedInputDevice *eInputDeviceManager::findDeviceByProtocolAddress(const uint8_t *addr)
{
	return findOrCreateDevice(addressToString(addr));
}

void eInputDeviceManager::updateDeviceList()
{
	deviceListChanged();
}

void eInputDeviceManager::updateDeviceState(eManagedInputDevice *device)
{
	if (!device)
		return;
	deviceStateChanged(device->address().c_str(), device->state());
}

void eInputDeviceManager::processFrame(const uint8_t *data, size_t len)
{
	if (!data || !len)
		return;

	uint8_t cmd = data[0];
	m_responding = true;

	switch (cmd)
	{
		case 0x05:
			if (len >= 4 && data[1] == 0x01)
			{
				m_versionMajor = data[3];
				m_versionMinor = data[2];
				eDebug("[eInputDeviceManager] Central firmware version: %s", version().c_str());
			}
			break;

		case 0x62:
			if (len >= 9 && data[1] == 0x01)
			{
				eManagedInputDevice *device = findDeviceByProtocolAddress(data + 2);
				device->setStateFlags(data[8]);
				if (device->connected() && (device->batteryLevel() <= 0 || device->version() == "0.0"))
				{
					sendDeviceCommand(0xD6, device);
					sendDeviceCommand(0xE1, device);
				}
				updateDeviceState(device);
				updateDeviceList();
			}
			break;

		case 0x68:
		case 0x69:
			if (len >= 8)
			{
				eManagedInputDevice *device = findDeviceByProtocolAddress(data + 1);
				device->setRssi((int8_t)data[7]);
				if (len > 8)
				{
					std::string name((const char*)data + 8, len - 8);
					device->setName(name);
					device->setShortName(name);
				}
				updateDeviceList();
			}
			break;

		case 0x6A:
			if (len >= 7)
			{
				findDeviceByProtocolAddress(data + 1);
				updateDeviceList();
			}
			break;

		case 0x6B:
			if (len >= 8)
			{
				eManagedInputDevice *device = findDeviceByProtocolAddress(data + 1);
				device->setRssi((int8_t)data[7]);
				updateDeviceState(device);
			}
			break;

		case 0x6C:
			if (len >= 8)
			{
				eManagedInputDevice *device = findDeviceByProtocolAddress(data + 1);
				device->setBatteryLevel(data[7]);
				if (data[7] && data[7] < DFU_BATTERY_MIN)
					batteryLow(device->address().c_str());
				updateDeviceState(device);
			}
			break;

		case 0x6D:
			if (len >= 8)
			{
				eManagedInputDevice *device = findDeviceByProtocolAddress(data + 1);
				device->setStateFlags(data[7]);
				if (device->connected())
				{
					sendDeviceCommand(0xD6, device);
					sendDeviceCommand(0xE1, device);
				}
				updateDeviceState(device);
				updateDeviceList();
			}
			break;

		case 0xB0:
		case 0xEB:
			if (len >= 2)
				eDebug("[eInputDeviceManager] LED command 0x%02x response: 0x%02x", cmd, data[1]);
			break;

		case 0xE6:
		case 0xE8:
		case 0xE9:
		case 0xEA:
			if (len >= 2)
				eDebug("[eInputDeviceManager] IR command 0x%02x response: 0x%02x", cmd, data[1]);
			break;

		case 0xD7:
			if (len >= 9)
			{
				eManagedInputDevice *device = findDeviceByProtocolAddress(data + 1);
				device->setVersion(data[8], data[7]);
				updateDeviceState(device);
			}
			break;

		case 0xE7:
			if (len >= 8)
			{
				eManagedInputDevice *device = findDeviceByProtocolAddress(data + 1);
				irKeyCount(device->address().c_str(), data[7]);
			}
			break;

		case 0x1A:
			if (len >= 13)
			{
				static const struct
				{
					uint8_t offset;
					uint8_t mask;
					int key;
				} keyLut[] = {
					{4, 0x01, 116}, {2, 0x01, 373}, {0, 0x01, 113},
					{1, 0x04, 2}, {3, 0x04, 3}, {5, 0x04, 4},
					{1, 0x08, 5}, {3, 0x08, 6}, {5, 0x08, 7},
					{1, 0x10, 8}, {3, 0x10, 9}, {5, 0x10, 10},
					{3, 0x20, 11}, {1, 0x20, 412}, {5, 0x20, 407},
					{1, 0x01, 115}, {1, 0x02, 114}, {3, 0x01, 174},
					{5, 0x01, 402}, {5, 0x02, 403}, {0, 0x20, 358},
					{4, 0x20, 139}, {0, 0x80, 392}, {4, 0x80, 393},
					{2, 0x20, 103}, {2, 0x80, 108}, {0, 0x40, 105},
					{4, 0x40, 106}, {2, 0x40, 352}, {0, 0x10, 398},
					{0, 0x08, 399}, {2, 0x08, 400}, {4, 0x08, 401},
					{0, 0x02, 165}, {2, 0x02, 207}, {2, 0x04, 128},
					{4, 0x02, 163}, {4, 0x04, 388}, {0, 0x04, 167}
				};
				std::string address = addressToString(data + 7);
				for (unsigned int i = 0; i < sizeof(keyLut) / sizeof(keyLut[0]); ++i)
				{
					if (data[1 + keyLut[i].offset] & keyLut[i].mask)
					{
						unboundRemoteKeyPressed(address.c_str(), keyLut[i].key);
						break;
					}
				}
			}
			break;

		default:
			break;
	}
}

/* Initialize after the generic rc input layer has been registered. */
eAutoInitP0<eInputDeviceManager> init_inputdevicemanager(eAutoInitNumbers::rc + 2, "dreamble input device manager");
