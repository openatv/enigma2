#include <unistd.h>
#include <fcntl.h>
#include <errno.h>
#include <stddef.h>
#include <stdint.h>
#include <sys/ioctl.h>
#include <string.h>

#include <lib/base/init.h>
#include <lib/base/init_num.h>
#include <lib/base/eerror.h>
#include <lib/base/ebase.h>
#include <lib/base/nconfig.h>
#include <lib/driver/input_fake.h>
#include <lib/driver/hdmi_cec.h>
#include <lib/driver/avcontrol.h>
/* NOTE: this header will move to linux uapi, once the cec framework is out of staging */
#include <lib/driver/linux-uapi-cec.h>

#define CEC_VENDOR_ENIGMA2_STB          0x000934

/*
 * Amlogic AOCEC userspace ABI. This backend uses /dev/cec and transfers
 * complete CEC wire frames: header, opcode and operands.
 */
#define AML_CEC_IOC_MAGIC               'C'
#define AML_CEC_IOC_GET_PHYSICAL_ADDR   _IOR(AML_CEC_IOC_MAGIC, 0x00, uint16_t)
#define AML_CEC_IOC_SET_OPTION_SYS_CTRL _IOW(AML_CEC_IOC_MAGIC, 0x08, uint32_t)
#define AML_CEC_IOC_ADD_LOGICAL_ADDR    _IOW(AML_CEC_IOC_MAGIC, 0x0b, uint32_t)
#define AML_CEC_IOC_CLR_LOGICAL_ADDR    _IOW(AML_CEC_IOC_MAGIC, 0x0c, uint32_t)
#define AML_CEC_IOC_SET_DEVICE_TYPE     _IOW(AML_CEC_IOC_MAGIC, 0x0d, uint32_t)

static const uint32_t *getLogicalAddressCandidates(unsigned char deviceType, size_t &addressCount)
{
	static const uint32_t tvAddresses[] = { CEC_LOG_ADDR_TV };
	static const uint32_t recorderAddresses[] = { CEC_LOG_ADDR_RECORD_1, CEC_LOG_ADDR_RECORD_2, CEC_LOG_ADDR_RECORD_3 };
	static const uint32_t tunerAddresses[] = { CEC_LOG_ADDR_TUNER_1, CEC_LOG_ADDR_TUNER_2, CEC_LOG_ADDR_TUNER_3, CEC_LOG_ADDR_TUNER_4 };
	static const uint32_t playbackAddresses[] = { CEC_LOG_ADDR_PLAYBACK_1, CEC_LOG_ADDR_PLAYBACK_2, CEC_LOG_ADDR_PLAYBACK_3 };
	static const uint32_t audioAddresses[] = { CEC_LOG_ADDR_AUDIOSYSTEM };
	static const uint32_t unregisteredAddresses[] = { CEC_LOG_ADDR_UNREGISTERED };

	switch (deviceType)
	{
	case CEC_OP_PRIM_DEVTYPE_TV:
		addressCount = sizeof(tvAddresses) / sizeof(tvAddresses[0]);
		return tvAddresses;
	case CEC_OP_PRIM_DEVTYPE_RECORD:
		addressCount = sizeof(recorderAddresses) / sizeof(recorderAddresses[0]);
		return recorderAddresses;
	case CEC_OP_PRIM_DEVTYPE_TUNER:
		addressCount = sizeof(tunerAddresses) / sizeof(tunerAddresses[0]);
		return tunerAddresses;
	case CEC_OP_PRIM_DEVTYPE_PLAYBACK:
		addressCount = sizeof(playbackAddresses) / sizeof(playbackAddresses[0]);
		return playbackAddresses;
	case CEC_OP_PRIM_DEVTYPE_AUDIOSYSTEM:
		addressCount = sizeof(audioAddresses) / sizeof(audioAddresses[0]);
		return audioAddresses;
	default:
		addressCount = sizeof(unregisteredAddresses) / sizeof(unregisteredAddresses[0]);
		return unregisteredAddresses;
	}
}

static int configureAmlogicCEC(int fd, unsigned char deviceType)
{
	if (::ioctl(fd, AML_CEC_IOC_SET_DEVICE_TYPE, (uint32_t)deviceType) < 0)
		return -1;

	size_t addressCount = 0;
	const uint32_t *addresses = getLogicalAddressCandidates(deviceType, addressCount);
	::ioctl(fd, AML_CEC_IOC_CLR_LOGICAL_ADDR, 0);
	for (size_t i = 0; i < addressCount; ++i)
	{
		if (::ioctl(fd, AML_CEC_IOC_ADD_LOGICAL_ADDR, addresses[i]) >= 0)
			return addresses[i];
	}
	return -1;
}

static int hexValue(char value)
{
	if (value >= '0' && value <= '9')
		return value - '0';
	if (value >= 'A' && value <= 'F')
		return value - 'A' + 10;
	if (value >= 'a' && value <= 'f')
		return value - 'a' + 10;
	return -1;
}

eHdmiCEC *eHdmiCEC::instance = NULL;

DEFINE_REF(eHdmiCEC::eCECMessage);

eHdmiCEC::eCECMessage::eCECMessage(int addr, int cmd, char *data, int length)
{
	address = addr;
	command = cmd;
	dataLength = 0;
	memset(messageData, 0, sizeof(messageData));
	control0 = control1 = control2 = control3 = 0;

	if (length < 0)
		length = 0;
	if (length > (int)sizeof(messageData)) length = sizeof(messageData);
	if (length && data)
	{
		memcpy(messageData, data, length);
		if (length > 0) control0 = data[0];
		if (length > 1) control1 = data[1];
		if (length > 2) control2 = data[2];
		if (length > 3) control3 = data[3];
		dataLength = length;
	}
}

int eHdmiCEC::eCECMessage::getAddress()
{
	return address;
}

int eHdmiCEC::eCECMessage::getCommand()
{
	return command;
}

int eHdmiCEC::eCECMessage::getData(char *data, int length)
{
	if (!data || length <= 0)
		return 0;
	if (length > (int)dataLength) length = dataLength;
	memcpy(data, messageData, length);
	return length;
}

eHdmiCEC::eHdmiCEC()
: eRCDriver(eRCInput::getInstance())
{
	ASSERT(!instance);
	instance = this;
	linuxCEC = false;
	amlogicCEC = false;
	hdmiFd = -1;
	fixedAddress = false;
	physicalAddress[0] = 0x10;
	physicalAddress[1] = 0x00;
	logicalAddress = CEC_LOG_ADDR_TUNER_1;
	deviceType = CEC_LOG_ADDR_TUNER_1; /* default: tuner / set-top box */

	hdmiFd = ::open("/dev/cec0", O_RDWR | O_CLOEXEC);
	if (hdmiFd >= 0)
	{
		__u32 monitor = CEC_MODE_INITIATOR | CEC_MODE_FOLLOWER;
		struct cec_caps caps = {};

		::ioctl(hdmiFd, CEC_ADAP_G_CAPS, &caps);

		if (caps.capabilities & CEC_CAP_LOG_ADDRS)
		{
			struct cec_log_addrs laddrs = {};

			::ioctl(hdmiFd, CEC_ADAP_S_LOG_ADDRS, &laddrs);
			memset(&laddrs, 0, sizeof(laddrs));

			/*
			 * NOTE: cec_version, osd_name and deviceType should be made configurable,
			 * CEC_ADAP_S_LOG_ADDRS delayed till the desired values are available
			 * (saves us some startup speed as well, polling for a free logical address
			 * takes some time)
			 */
			laddrs.cec_version = CEC_OP_CEC_VERSION_2_0;
			strcpy(laddrs.osd_name, "Enigma2 STB");
			laddrs.vendor_id = CEC_VENDOR_ENIGMA2_STB;

			switch (deviceType)
			{
			case CEC_LOG_ADDR_TV:
				laddrs.log_addr_type[laddrs.num_log_addrs] = CEC_LOG_ADDR_TYPE_TV;
				laddrs.all_device_types[laddrs.num_log_addrs] = CEC_OP_ALL_DEVTYPE_TV;
				laddrs.primary_device_type[laddrs.num_log_addrs] = CEC_OP_PRIM_DEVTYPE_TV;
				break;
			case CEC_LOG_ADDR_RECORD_1:
				laddrs.log_addr_type[laddrs.num_log_addrs] = CEC_LOG_ADDR_TYPE_RECORD;
				laddrs.all_device_types[laddrs.num_log_addrs] = CEC_OP_ALL_DEVTYPE_RECORD;
				laddrs.primary_device_type[laddrs.num_log_addrs] = CEC_OP_PRIM_DEVTYPE_RECORD;
				break;
			case CEC_LOG_ADDR_TUNER_1:
				laddrs.log_addr_type[laddrs.num_log_addrs] = CEC_LOG_ADDR_TYPE_TUNER;
				laddrs.all_device_types[laddrs.num_log_addrs] = CEC_OP_ALL_DEVTYPE_TUNER;
				laddrs.primary_device_type[laddrs.num_log_addrs] = CEC_OP_PRIM_DEVTYPE_TUNER;
				break;
			case CEC_LOG_ADDR_PLAYBACK_1:
				laddrs.log_addr_type[laddrs.num_log_addrs] = CEC_LOG_ADDR_TYPE_PLAYBACK;
				laddrs.all_device_types[laddrs.num_log_addrs] = CEC_OP_ALL_DEVTYPE_PLAYBACK;
				laddrs.primary_device_type[laddrs.num_log_addrs] = CEC_OP_PRIM_DEVTYPE_PLAYBACK;
				break;
			case CEC_LOG_ADDR_AUDIOSYSTEM:
				laddrs.log_addr_type[laddrs.num_log_addrs] = CEC_LOG_ADDR_TYPE_AUDIOSYSTEM;
				laddrs.all_device_types[laddrs.num_log_addrs] = CEC_OP_ALL_DEVTYPE_AUDIOSYSTEM;
				laddrs.primary_device_type[laddrs.num_log_addrs] = CEC_OP_PRIM_DEVTYPE_AUDIOSYSTEM;
				break;
			default:
				laddrs.log_addr_type[laddrs.num_log_addrs] = CEC_LOG_ADDR_TYPE_UNREGISTERED;
				laddrs.all_device_types[laddrs.num_log_addrs] = CEC_OP_ALL_DEVTYPE_SWITCH;
				laddrs.primary_device_type[laddrs.num_log_addrs] = CEC_OP_PRIM_DEVTYPE_SWITCH;
				break;
			}
			laddrs.num_log_addrs++;

			if (::ioctl(hdmiFd, CEC_ADAP_S_LOG_ADDRS, &laddrs) < 0)
				eDebug("[eHdmiCEC] CEC_ADAP_S_LOG_ADDRS failed on /dev/cec0: %m");
		}

		if (::ioctl(hdmiFd, CEC_S_MODE, &monitor) < 0)
			eDebug("[eHdmiCEC] CEC_S_MODE failed on /dev/cec0: %m");

		linuxCEC = true;
		eDebug("[eHdmiCEC] using Linux CEC backend on /dev/cec0");
	}

	if (!linuxCEC)
	{
		hdmiFd = ::open("/dev/cec", O_RDWR | O_NONBLOCK | O_CLOEXEC);
		if (hdmiFd >= 0)
		{
			uint32_t enable = 1;
			if (::ioctl(hdmiFd, AML_CEC_IOC_SET_OPTION_SYS_CTRL, enable) >= 0)
			{
				int address = configureAmlogicCEC(hdmiFd, deviceType);
				if (address >= 0)
				{
					logicalAddress = address;
					amlogicCEC = true;
					eDebug("[eHdmiCEC] using Amlogic AOCEC backend on /dev/cec, logical address %X", logicalAddress);
				}
				else
				{
					eDebug("[eHdmiCEC] Amlogic AOCEC logical address setup failed: %m");
				}
			}
			else
			{
				eDebug("[eHdmiCEC] Amlogic AOCEC system-control setup failed: %m");
			}

			if (!amlogicCEC)
			{
				enable = 0;
				::ioctl(hdmiFd, AML_CEC_IOC_SET_OPTION_SYS_CTRL, enable);
				::close(hdmiFd);
				hdmiFd = -1;
			}
		}
	}

	if (!linuxCEC && !amlogicCEC)
	{
#ifdef DREAMBOX
#define HDMIDEV "/dev/misc/hdmi_cec0"
#else
#define HDMIDEV "/dev/hdmi_cec"
#endif

		hdmiFd = ::open(HDMIDEV, O_RDWR | O_NONBLOCK | O_CLOEXEC);
		if (hdmiFd >= 0)
		{

#ifdef DREAMBOX
			unsigned int val = 0;
			::ioctl(hdmiFd, 4, &val);
#else
			::ioctl(hdmiFd, 0); /* flush old messages */
#endif
			eDebug("[eHdmiCEC] using legacy HDMI-CEC backend on %s", HDMIDEV);
		}
	}

	if (hdmiFd >= 0)
	{
		messageNotifier = eSocketNotifier::create(eApp, hdmiFd, eSocketNotifier::Read | eSocketNotifier::Priority);
		CONNECT(messageNotifier->activated, eHdmiCEC::hdmiEvent);
	}
	else
	{
		eDebug("[eHdmiCEC] cannot open HDMI-CEC device (/dev/cec0, /dev/cec, %s): %m", HDMIDEV);
	}

	getAddressInfo();
}

eHdmiCEC::~eHdmiCEC()
{
	if (amlogicCEC && hdmiFd >= 0)
	{
		uint32_t enable = 0;
		if (::ioctl(hdmiFd, AML_CEC_IOC_SET_OPTION_SYS_CTRL, enable) < 0)
			eDebug("[eHdmiCEC] disabling Amlogic AOCEC system-control failed: %m");
	}
	if (hdmiFd >= 0) ::close(hdmiFd);
}

eHdmiCEC *eHdmiCEC::getInstance()
{
	return instance;
}

void eHdmiCEC::reportPhysicalAddress()
{
	struct cec_message txmessage = {};
	memset(&txmessage, 0, sizeof(txmessage));
	txmessage.address = 0x0f; /* broadcast */
	txmessage.data[0] = 0x84; /* report address */
	txmessage.data[1] = physicalAddress[0];
	txmessage.data[2] = physicalAddress[1];
	txmessage.data[3] = deviceType;
	txmessage.length = 4;
	sendMessage(txmessage);
}

void eHdmiCEC::getAddressInfo()
{
	if (hdmiFd >= 0)
	{
		bool hasdata = false;
		struct addressinfo addressinfo = {};
		
		if (linuxCEC)
		{
			__u16 phys_addr;
			struct cec_log_addrs laddrs = {};

			if (::ioctl(hdmiFd, CEC_ADAP_G_PHYS_ADDR, &phys_addr) >= 0 &&
				::ioctl(hdmiFd, CEC_ADAP_G_LOG_ADDRS, &laddrs) >= 0 &&
				laddrs.num_log_addrs > 0)
			{
				addressinfo.physical[0] = (phys_addr >> 8) & 0xff;
				addressinfo.physical[1] = phys_addr & 0xff;
				addressinfo.logical = laddrs.log_addr[0];

				switch (laddrs.log_addr_type[0])
				{
				case CEC_LOG_ADDR_TYPE_TV:
					addressinfo.type = CEC_LOG_ADDR_TV;
					break;
				case CEC_LOG_ADDR_TYPE_RECORD:
					addressinfo.type = CEC_LOG_ADDR_RECORD_1;
					break;
				case CEC_LOG_ADDR_TYPE_TUNER:
					addressinfo.type = CEC_LOG_ADDR_TUNER_1;
					break;
				case CEC_LOG_ADDR_TYPE_PLAYBACK:
					addressinfo.type = CEC_LOG_ADDR_PLAYBACK_1;
					break;
				case CEC_LOG_ADDR_TYPE_AUDIOSYSTEM:
					addressinfo.type = CEC_LOG_ADDR_AUDIOSYSTEM;
					break;
				case CEC_LOG_ADDR_TYPE_UNREGISTERED:
				default:
					addressinfo.type = CEC_LOG_ADDR_UNREGISTERED;
					break;
				}
				hasdata = true;
			}
		}
		else if (amlogicCEC)
		{
			uint16_t phys_addr = 0xffff;
			if (::ioctl(hdmiFd, AML_CEC_IOC_GET_PHYSICAL_ADDR, &phys_addr) >= 0)
			{
				addressinfo.physical[0] = (phys_addr >> 8) & 0xff;
				addressinfo.physical[1] = phys_addr & 0xff;
				addressinfo.logical = logicalAddress;
				addressinfo.type = deviceType;
				hasdata = true;
			}
		}
		else
		{
			if (::ioctl(hdmiFd, 1, &addressinfo) >= 0)
			{
				hasdata = true;
#if DREAMBOX
				/* we do not get the device type, check the logical address to determine the type */
				switch (addressinfo.logical)
				{
				case 0x1:
				case 0x2:
				case 0x9:
					addressinfo.type = 1; /* recorder */
					break;
				case 0x3:
				case 0x6:
				case 0x7:
				case 0xa:
					addressinfo.type = 3; /* tuner */
					break;
				case 0x4:
				case 0x8:
				case 0xb:
					addressinfo.type = 4; /* playback */
					break;
				}
#endif
			}
		}
		if (hasdata)
		{
			deviceType = addressinfo.type;
			logicalAddress = addressinfo.logical;
			if (!fixedAddress)
			{
				if (memcmp(physicalAddress, addressinfo.physical, sizeof(physicalAddress)))
				{
					eDebug("[eHdmiCEC] detected physical address change: %02X%02X --> %02X%02X", physicalAddress[0], physicalAddress[1], addressinfo.physical[0], addressinfo.physical[1]);
					memcpy(physicalAddress, addressinfo.physical, sizeof(physicalAddress));
					reportPhysicalAddress();
					/* emit */ addressChanged((physicalAddress[0] << 8) | physicalAddress[1]);
				}
			}
		}
	}
}

int eHdmiCEC::getLogicalAddress()
{
	return logicalAddress;
}

int eHdmiCEC::getPhysicalAddress()
{
	return (physicalAddress[0] << 8) | physicalAddress[1];
}

void eHdmiCEC::setFixedPhysicalAddress(int address)
{
	if (address)
	{
		fixedAddress = true;
		physicalAddress[0] = (address >> 8) & 0xff;
		physicalAddress[1] = address & 0xff;
		if (linuxCEC)
		{
			__u16 phys_addr = address & 0xffff;
			if (::ioctl(hdmiFd, CEC_ADAP_S_PHYS_ADDR, &phys_addr) < 0)
				eDebug("[eHdmiCEC] CEC_ADAP_S_PHYS_ADDR failed: %m");
		}
		/* report our (possibly new) address */
		reportPhysicalAddress();
	}
	else
	{
		fixedAddress = false;
		/* get our current address */
		getAddressInfo();
	}
}

int eHdmiCEC::getDeviceType()
{
	return deviceType;
}

bool eHdmiCEC::getActiveStatus()
{
	bool active = true;
	eAVControl *avc = eAVControl::getInstance();
	if (avc)
		active = avc->isEncoderActive();
	return active;
}

void eHdmiCEC::hdmiEvent(int what)
{
	if (what & eSocketNotifier::Priority)
	{
		if (linuxCEC)
		{
			struct cec_event cecevent = {};
			::ioctl(hdmiFd, CEC_DQEVENT, &cecevent);
			if (cecevent.event == CEC_EVENT_STATE_CHANGE)
			{
				/* do not bother decoding the new address, just get the address in getAddressInfo */
			}
		}
		getAddressInfo();
	}

	if (what & eSocketNotifier::Read)
	{
		bool hasdata = false;
		struct cec_rx_message rxmessage = {};
		if (linuxCEC)
		{
			struct cec_msg msg = {};
			if (::ioctl(hdmiFd, CEC_RECEIVE, &msg) >= 0 &&
				msg.len >= 2 && msg.len <= CEC_MAX_MSG_SIZE)
			{
				rxmessage.address = cec_msg_initiator(&msg);
				rxmessage.length = msg.len - 1;
				memcpy(rxmessage.data, &msg.msg[1], rxmessage.length);
				hasdata = true;
			}
		}
		else if (amlogicCEC)
		{
			unsigned char frame[CEC_MAX_MSG_SIZE] = {};
			ssize_t length = ::read(hdmiFd, frame, sizeof(frame));
			if (length >= 2 && length <= (ssize_t)sizeof(frame))
			{
				rxmessage.address = (frame[0] >> 4) & 0x0f;
				rxmessage.length = length - 1;
				memcpy(rxmessage.data, &frame[1], rxmessage.length);
				hasdata = true;
			}
		}
		else
		{
#ifdef DREAMBOX
			if (::ioctl(hdmiFd, 2, &rxmessage) >= 0)
			{
				hasdata = true;
			}
			unsigned int val = 0;
			::ioctl(hdmiFd, 4, &val);
#else
			if (::read(hdmiFd, &rxmessage, 2) == 2)
			{
				if (::read(hdmiFd, &rxmessage.data, rxmessage.length) == rxmessage.length)
				{
					hasdata = true;
				}
			}
#endif
		}
		bool hdmicec_enabled = eConfigManager::getConfigBoolValue("config.hdmicec.enabled", false);
		if (hasdata && hdmicec_enabled && rxmessage.length > 0)
		{
			bool keypressed = false;
			static unsigned char pressedkey = 0;

			eDebugNoNewLineStart("[eHdmiCEC] received message");
			eDebugNoNewLine(" %02X", rxmessage.address);
			for (int i = 0; i < rxmessage.length; i++)
			{
				eDebugNoNewLine(" %02X", rxmessage.data[i]);
			}
			eDebugNoNewLine("\n");
			bool hdmicec_report_active_menu = eConfigManager::getConfigBoolValue("config.hdmicec.report_active_menu", false);
			if (hdmicec_report_active_menu)
			{
				switch (rxmessage.data[0])
				{
					case 0x44: /* key pressed */
						if (rxmessage.length < 2)
							break;
						keypressed = true;
						pressedkey = rxmessage.data[1];
						[[fallthrough]];
					case 0x45: /* key released */
					{
						long code = translateKey(pressedkey);
						if (keypressed) code |= 0x80000000;
						for (std::list<eRCDevice*>::iterator i(listeners.begin()); i != listeners.end(); ++i)
						{
							(*i)->handleCode(code);
						}
						break;
					}
				}
			}
			int operandLength = rxmessage.length > 1 ? rxmessage.length - 1 : 0;
			ePtr<iCECMessage> msg = new eCECMessage(rxmessage.address, rxmessage.data[0], (char*)&rxmessage.data[1], operandLength);
			messageReceived(msg);
		}
	}
}

long eHdmiCEC::translateKey(unsigned char code)
{
	long key = 0;
	switch (code)
	{
		case 0x32:
			key = 0x8b;
			break;
		case 0x20:
			key = 0x0b;
			break;
		case 0x21:
			key = 0x02;
			break;
		case 0x22:
			key = 0x03;
			break;
		case 0x23:
			key = 0x04;
			break;
		case 0x24:
			key = 0x05;
			break;
		case 0x25:
			key = 0x06;
			break;
		case 0x26:
			key = 0x07;
			break;
		case 0x27:
			key = 0x08;
			break;
		case 0x28:
			key = 0x09;
			break;
		case 0x29:
			key = 0x0a;
			break;
		case 0x30:
			key = 0x192;
			break;
		case 0x31:
			key = 0x193;
			break;
		case 0x44:
			key = 0xcf;
			break;
		case 0x45:
			key = 0x80;
			break;
		case 0x46:
			key = 0x77;
			break;
		case 0x47:
			key = 0xa7;
			break;
		case 0x48:
			key = 0xa8;
			break;
		case 0x49:
			key = 0xd0;
			break;
		case 0x53:
			key = 0x16d;
			break;
		case 0x54:
			key = 0x16a;
			break;
		case 0x60:
			key = 0xcf;
			break;
		case 0x61:
			key = 0xa4;
			break;
		case 0x62:
			key = 0xa7;
			break;
		case 0x64:
			key = 0x80;
			break;
		case 0x00:
			key = 0x160;
			break;
		case 0x03:
			key = 0x69;
			break;
		case 0x04:
			key = 0x6a;
			break;
		case 0x01:
			key = 0x67;
			break;
		case 0x02:
			key = 0x6c;
			break;
		case 0x0d:
			key = 0xae;
			break;
		case 0x72:
			key = 0x18e;
			break;
		case 0x71:
			key = 0x191;
			break;
		case 0x73:
			key = 0x18f;
			break;
		case 0x74:
			key = 0x190;
			break;
		default:
			key = 0x8b;
			eDebug("eHdmiCEC: unknown code 0x%02X", (unsigned int)(code & 0xFF));
			break;
	}
	return key;
}

void eHdmiCEC::sendMessage(struct cec_message &message)
{
	if (hdmiFd >= 0)
	{
		eDebugNoNewLineStart("[eHdmiCEC] send message");
		eDebugNoNewLine(" %02X", message.address);
		for (int i = 0; i < message.length; i++)
		{
			eDebugNoNewLine(" %02X", message.data[i]);
		}
		eDebugNoNewLine("\n");
		if (linuxCEC)
		{
			struct cec_msg msg;
			int payloadLength = message.length;
			if (payloadLength > CEC_MAX_MSG_SIZE - 1)
			{
				eDebug("[eHdmiCEC] truncating oversized CEC payload from %d to %d bytes", payloadLength, CEC_MAX_MSG_SIZE - 1);
				payloadLength = CEC_MAX_MSG_SIZE - 1;
			}
			cec_msg_init(&msg, logicalAddress, message.address);
			memcpy(&msg.msg[1], message.data, payloadLength);
			msg.len = payloadLength + 1;
			if (::ioctl(hdmiFd, CEC_TRANSMIT, &msg) < 0)
				eDebug("[eHdmiCEC] CEC_TRANSMIT failed: %m");
		}
		else if (amlogicCEC)
		{
			unsigned char frame[CEC_MAX_MSG_SIZE] = {};
			int payloadLength = message.length;
			if (payloadLength > CEC_MAX_MSG_SIZE - 1)
				payloadLength = CEC_MAX_MSG_SIZE - 1;
			frame[0] = ((logicalAddress & 0x0f) << 4) | (message.address & 0x0f);
			memcpy(&frame[1], message.data, payloadLength);

			ssize_t status = -1;
			for (int attempt = 0; attempt < 3; ++attempt)
			{
				do
				{
					status = ::write(hdmiFd, frame, payloadLength + 1);
				}
				while (status < 0 && errno == EINTR);
				if (status == 0 || status == payloadLength + 1)
					break;
				if (attempt < 2)
					usleep(10000);
			}
			if (status < 0)
				eDebug("[eHdmiCEC] Amlogic AOCEC transmit failed: %m");
			else if (status != 0 && status != payloadLength + 1)
				eDebug("[eHdmiCEC] Amlogic AOCEC transmit failed, status %d", (int)status);
		}
		else
		{
#ifdef DREAMBOX
			message.flag = 1;
			::ioctl(hdmiFd, 3, &message);
#else
			ssize_t ret = ::write(hdmiFd, &message, 2 + message.length);
			if (ret < 0) eDebug("[eHdmiCEC] write failed: %m");
#endif
		}
	}
}

void eHdmiCEC::sendMessage(unsigned char address, unsigned char cmd, char *data, int length)
{
	struct cec_message message = {};
	if (length < 0 || !data)
		length = 0;
	/* CEC_MAX_MSG_SIZE includes the initiator/destination header byte. */
	if (length > CEC_MAX_MSG_SIZE - 2)
		length = CEC_MAX_MSG_SIZE - 2;
	message.address = address;
	if (length > (int)(sizeof(message.data) - 1)) length = sizeof(message.data) - 1;
	message.length = length + 1;
	message.data[0] = cmd;
	if (length)
		memcpy(&message.data[1], data, length);
	sendMessage(message);
}

void eHdmiCEC::sendMessageBytes(unsigned char address, unsigned char cmd, char *hexdata)
{
	struct cec_message message = {};
	message.address = address;
	message.length = 1;
	message.data[0] = cmd;

	if (hexdata)
	{
		int highNibble = -1;
		for (const char *item = hexdata; *item && message.length < CEC_MAX_MSG_SIZE - 1 && message.length < sizeof(message.data); ++item)
		{
			int nibble = hexValue(*item);
			if (nibble < 0)
				continue;
			if (highNibble < 0)
			{
				highNibble = nibble;
			}
			else
			{
				message.data[message.length++] = (highNibble << 4) | nibble;
				highNibble = -1;
			}
		}
	}

	sendMessage(message);
}

void eHdmiCECDevice::handleCode(long code)
{
	if (code & 0x80000000)
	{
		/*emit*/ input->keyPressed(eRCKey(this, code & 0xffff, 0));
	}
	else
	{
		/*emit*/ input->keyPressed(eRCKey(this, code & 0xffff, eRCKey::flagBreak));
	}
}

eHdmiCECDevice::eHdmiCECDevice(eRCDriver *driver)
 : eRCDevice("Hdmi-CEC", driver)
{
}

const char *eHdmiCECDevice::getDescription() const
{
	return "Hdmi-CEC device";
}

class eHdmiCECInit
{
	eHdmiCEC driver;
	eHdmiCECDevice device;

public:
	eHdmiCECInit(): driver(), device(&driver)
	{
	}
};

eAutoInitP0<eHdmiCECInit> init_hdmicec(eAutoInitNumbers::rc + 2, "Hdmi CEC driver");
