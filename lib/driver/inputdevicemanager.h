#ifndef __inputdevicemanager_h
#define __inputdevicemanager_h

#include <lib/base/ebase.h>
#include <lib/base/object.h>
#include <lib/base/smartptr.h>
#include <lib/python/python.h>

#include <stdint.h>
#include <string>
#include <vector>
#include <map>

#define DFU_BATTERY_MIN 20

class eInputDeviceManager;
class IrProtocol;
class IrKey;

class IrProtocol
{
public:
	enum
	{
		IR_PROTO_NEC = 0,
		IR_PROTO_SIRC = 1,
		IR_PROTO_JVC = 2,
		IR_PROTO_RC5 = 3,
		IR_PROTO_REP_NEC = 4,
		IR_PROTO_REP_JVC = 5,
		IR_PROTO_CUSTOM = 6,
		IR_PROTO_REP_CUSTOM = 7
	};

	int carrierPeriod;
	int carrierLow;
	int toggleMask;
	int startBits;
	int startOnTime;
	int startTotalTime;
	int oneOnTime;
	int oneTotalTime;
	int zeroOnTime;
	int zeroTotalTime;
	int stopBits;
	int stopOnTime;
	int stopTotalTime;
	int repeatMs;
	int repeatProtocolId;

	IrProtocol(int carrierPeriod = 0, int carrierLow = 0, int toggleMask = 0,
		int startBits = 0, int startOnTime = 0, int startTotalTime = 0,
		int oneOnTime = 0, int oneTotalTime = 0,
		int zeroOnTime = 0, int zeroTotalTime = 0,
		int stopBits = 0, int stopOnTime = 0, int stopTotalTime = 0,
		int repeatMs = 0, int repeatProtocolId = 0);
};

class IrKey
{
public:
	enum
	{
		CODE_POWER = 0,
		CODE_MODE = 1,
		CODE_MUTE = 2,
		CODE_1 = 3,
		CODE_2 = 4,
		CODE_3 = 5,
		CODE_4 = 6,
		CODE_5 = 7,
		CODE_6 = 8,
		CODE_7 = 9,
		CODE_8 = 10,
		CODE_9 = 11,
		CODE_0 = 12,
		CODE_PREVIOUS = 13,
		CODE_NEXT = 14,
		CODE_REWIND = CODE_PREVIOUS,
		CODE_FASTFORWARD = CODE_NEXT,
		CODE_VOLUMEUP = 15,
		CODE_VOLUMEDOWN = 16,
		CODE_EXIT = 17,
		CODE_CHANNELUP = 18,
		CODE_CHANNELDOWN = 19,
		CODE_INFO = 20,
		CODE_MENU = 21,
		CODE_AUDIO = 22,
		CODE_VIDEO = 23,
		CODE_UP = 24,
		CODE_DOWN = 25,
		CODE_LEFT = 26,
		CODE_RIGHT = 27,
		CODE_OK = 28,
		CODE_RED = 29,
		CODE_GREEN = 30,
		CODE_YELLOW = 31,
		CODE_BLUE = 32,
		CODE_PREVIOUSSONG = 33,
		CODE_PLAY = 34,
		CODE_STOP = 35,
		CODE_NEXTSONG = 36,
		CODE_NEXSONG = CODE_NEXTSONG,
		CODE_TEXT = 37,
		CODE_RECORD = 38
	};

	int keyCode;
	int protocolId;
	uint32_t makeMessage;
	int makeLength;
	uint32_t repeatMessage;
	int repeatLength;

	IrKey(int keyCode = 0, int protocolId = 0, uint32_t makeMessage = 0,
		int makeLength = 0, uint32_t repeatMessage = 0, int repeatLength = 0);
};

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

class eManagedInputDevice: public iObject
{
	DECLARE_REF(eManagedInputDevice);

	friend class eInputDeviceManager;

	std::string m_address;
	std::string m_name;
	std::string m_shortName;
	int m_versionMajor;
	int m_versionMinor;
	int m_batteryLevel;
	int m_rssi;
	int m_state;
	bool m_encrypted;
	bool m_connected;
	bool m_bound;
	bool m_ready;
	bool m_isDfu;
	eInputDeviceManager *m_manager;

	void setManager(eInputDeviceManager *manager);
	void setAddress(const std::string &address);
	void setName(const std::string &name);
	void setShortName(const std::string &shortName);
	void setVersion(int major, int minor);
	void setBatteryLevel(int batteryLevel);
	void setRssi(int rssi);
	void setStateFlags(int rawState);
	void setDfu(bool isDfu);

protected:
	~eManagedInputDevice();

public:
	enum
	{
		TYPE_UNDEF = 0,
		TYPE_DREAMBLE = 1
	};
	enum
	{
		STATE_DISCONNECTED = 0,
		STATE_CONNECTING = 1,
		STATE_CONNECTED = 2
	};

	eManagedInputDevice(eInputDeviceManager *manager = 0, const std::string &address = "");

	int type() const { return TYPE_DREAMBLE; }
	std::string address() const { return m_address; }
	std::string name() const { return m_name; }
	std::string shortName() const { return m_shortName; }
	std::string version() const;
	int batteryLevel() const { return m_batteryLevel; }
	int rssi() const { return m_rssi; }
	bool encrypted() const { return m_encrypted; }
	int state() const { return m_state; }
	bool connected() const { return m_connected; }
	bool bound() const { return m_bound; }
	bool ready() const { return m_ready; }
	bool isDfu() const { return m_isDfu; }
	int checkVersion(int major, int minor = 0) const;

	int connect();
	int disconnect();
	int vibrate();
	int setLedColor(int rgb);
	int setLedColorIr(int rgb);
	int setIrProtocol(bool isRepeat, IrProtocol *protocol);
	int setIrKey(IrKey *key);
	int resetIr();
	int getIrKeyCount();
	int dfu();
	int dfuFlash(const char *datFile, const char *binFile);
};

typedef eManagedInputDevice eManagedInputDevicePtr;

class eInputDeviceManager
{
	static eInputDeviceManager *instance;

#ifndef SWIG
	int m_fd;
	bool m_available;
	bool m_responding;
	int m_versionMajor;
	int m_versionMinor;
	ePtr<eSocketNotifier> m_notifier;
	ePtr<eTimer> m_scanTimer;
	std::map<std::string, eManagedInputDevice*> m_devices;

	int sendCommand(uint8_t command, const uint8_t *payload = 0, size_t payloadLen = 0);
	int sendDeviceCommand(uint8_t command, eManagedInputDevice *device, const uint8_t *payload = 0, size_t payloadLen = 0);
	void socketActivated(int what);
	void scanTimeout();
	void processFrame(const uint8_t *data, size_t len);
	eManagedInputDevice *findOrCreateDevice(const std::string &address);
	eManagedInputDevice *findDeviceByProtocolAddress(const uint8_t *addr);
	void updateDeviceList();
	void updateDeviceState(eManagedInputDevice *device);
	std::string addressToString(const uint8_t *addr) const;
	bool parseAddress(const std::string &address, uint8_t *addr) const;
	int sendRgbCommand(uint8_t command, eManagedInputDevice *device, int rgb);
#endif

public:
	eInputDeviceManager();
	~eInputDeviceManager();
	enum
	{
		FEATURE_UNCONNECTED_KEYPRESS = 1,
		FEATURE_DFU_UPDATE = 2
	};

	PSignal0<void> deviceListChanged;
	PSignal2<void, const char*, int> deviceStateChanged;
	PSignal2<void, const char*, int> unboundRemoteKeyPressed;
	PSignal2<void, const char*, int> irKeyCount;
	PSignal2<void, int, int> dfuEvent;
	PSignal2<void, int, int> dfuProgress;
	PSignal1<void, const char*> batteryLow;

	static eInputDeviceManager *getInstance();

	void start();
	void stop();
	bool hasFeature(int feature) const;
	bool available() const;
	bool responding() const;
	std::string version() const;
	eManagedInputDevice *getDevice(const std::string &address);
#ifndef SWIG
	std::vector<eManagedInputDevice*> getAvailableDevicesRaw();
	std::vector<eManagedInputDevice*> getConnectedDevicesRaw();
#endif
	void rescan();
	void refresh();
	int connectDevice(eManagedInputDevice *device);
	int disconnectDevice(eManagedInputDevice *device);
	int vibrate(eManagedInputDevice *device = 0);
	int setLedColor(eManagedInputDevice *device, int rgb);
	int setLedColorIr(eManagedInputDevice *device, int rgb);
	int setIrProtocol(eManagedInputDevice *device, bool isRepeat, IrProtocol *protocol);
	int setIrKey(eManagedInputDevice *device, IrKey *key);
	int resetIr(eManagedInputDevice *device);
	int getIrKeyCount(eManagedInputDevice *device);
	int dfu(eManagedInputDevice *device);
	int dfuFlash(eManagedInputDevice *device, const char *datFile, const char *binFile);
};

#endif // __inputdevicemanager_h
