#include <unistd.h>
#include <fcntl.h>
#include <sys/ioctl.h>
#include <string.h>

#include <lib/base/init.h>
#include <lib/base/init_num.h>
#include <lib/base/eerror.h>
#include <lib/base/ebase.h>
#include <lib/base/nconfig.h>
#include <lib/driver/input_fake.h>
#include <lib/driver/hdmi_cec.h>
#include <lib/driver/avswitch.h>

eHdmiCEC *eHdmiCEC::instance = NULL;

DEFINE_REF(eHdmiCEC::eCECMessage);

eHdmiCEC::eCECMessage::eCECMessage(int addr, int cmd, char *data, int length)
{
	address = addr;
	command = cmd;
	if (length > (int)sizeof(messageData)) length = sizeof(messageData);
	if (length && data) memcpy(messageData, data, length);
	dataLength = length;
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
	if (length > (int)dataLength) length = dataLength;
	memcpy(data, messageData, length);
	return length;
}

eHdmiCEC::eHdmiCEC()
: eRCDriver(eRCInput::getInstance())
{
	ASSERT(!instance);
	instance = this;
	fixedAddress = false;
	physicalAddress[0] = 0x10;
	physicalAddress[1] = 0x00;
	logicalAddress = 1;
	deviceType = 1; /* default: recorder */
#ifdef DREAMBOX
	hdmiFd = ::open("/dev/misc/hdmi_cec0", O_RDWR | O_NONBLOCK | O_CLOEXEC);
#else
	hdmiFd = ::open("/dev/hdmi_cec", O_RDWR | O_NONBLOCK | O_CLOEXEC);
#endif
	if (hdmiFd >= 0)
	{

#ifdef DREAMBOX
		unsigned int val = 0;
		::ioctl(hdmiFd, 4, &val);
#else
		::ioctl(hdmiFd, 0); /* flush old messages */
#endif
		getAddressInfo();
		messageNotifier = eSocketNotifier::create(eApp, hdmiFd, eSocketNotifier::Read | eSocketNotifier::Priority);
		CONNECT(messageNotifier->activated, eHdmiCEC::hdmiEvent);
	}
}

eHdmiCEC::~eHdmiCEC()
{
	if (hdmiFd >= 0) ::close(hdmiFd);
}

eHdmiCEC *eHdmiCEC::getInstance()
{
	return instance;
}

void eHdmiCEC::reportPhysicalAddress()
{
	struct cec_message txmessage;
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
#if DREAMBOX
		struct
		{
			unsigned char physical[2];
			unsigned char logical;
			unsigned char type;
		} addressinfo;

		if (::ioctl(hdmiFd, 1, &addressinfo) >= 0)
		{
			hasdata = true;
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
		}
#else
		struct
		{
			unsigned char logical;
			unsigned char physical[2];
			unsigned char type;
		} addressinfo;
		if (::ioctl(hdmiFd, 1, &addressinfo) >= 0)
		{
			hasdata = true;
		}
#endif
		if (hasdata)
		{
			deviceType = addressinfo.type;
			logicalAddress = addressinfo.logical;
			if (!fixedAddress)
			{
				if (memcmp(physicalAddress, addressinfo.physical, sizeof(physicalAddress)))
				{
					eDebug("eHdmiCEC: detected physical address change: %02X%02X --> %02X%02X", physicalAddress[0], physicalAddress[1], addressinfo.physical[0], addressinfo.physical[1]);
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
	eAVSwitch *avswitch = eAVSwitch::getInstance();
	if (avswitch) active = avswitch->isActive();
	return active;
}

void eHdmiCEC::hdmiEvent(int what)
{
	if (what & eSocketNotifier::Priority)
	{
		getAddressInfo();
	}

	if (what & eSocketNotifier::Read)
	{
		bool hasdata = false;
#ifdef DREAMBOX
		struct cec_rx_message rxmessage;
		if (::ioctl(hdmiFd, 2, &rxmessage) >= 0)
		{
			hasdata = true;
		}
		unsigned int val = 0;
		::ioctl(hdmiFd, 4, &val);
#else
		struct cec_message rxmessage;
		if (::read(hdmiFd, &rxmessage, 2) == 2)
		{
			if (::read(hdmiFd, &rxmessage.data, rxmessage.length) == rxmessage.length)
			{
				hasdata = true;
			}
		}
#endif
		bool hdmicec_enabled = eConfigManager::getConfigBoolValue("config.hdmicec.enabled", false);
		if (hasdata && hdmicec_enabled)
		{
			bool keypressed = false;
			static unsigned char pressedkey = 0;

			eDebugNoNewLineStart("eHdmiCEC: received message");
			for (int i = 0; i < rxmessage.length; i++)
			{
				eDebugNoNewLine(" %02X", rxmessage.data[i]);
			}
			eDebugNoNewLineEnd(" ");
			bool hdmicec_report_active_menu = eConfigManager::getConfigBoolValue("config.hdmicec.report_active_menu", false);
			if (hdmicec_report_active_menu)
			{
				switch (rxmessage.data[0])
				{
					case 0x44: /* key pressed */
						keypressed = true;
						pressedkey = rxmessage.data[1];
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
			ePtr<iCECMessage> msg = new eCECMessage(rxmessage.address, rxmessage.data[0], (char*)&rxmessage.data[1], rxmessage.length);
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
			key = 0x166;
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
			break;
	}
	return key;
}

void eHdmiCEC::sendMessage(struct cec_message &message)
{
	if (hdmiFd >= 0)
	{
		eDebugNoNewLineStart("eHdmiCEC: send message");
		for (int i = 0; i < message.length; i++)
		{
			eDebugNoNewLine(" %02X", message.data[i]);
		}
		eDebugNoNewLineEnd(" ");
#ifdef DREAMBOX
		message.flag = 1;
		::ioctl(hdmiFd, 3, &message);
#else
		::write(hdmiFd, &message, 2 + message.length);
#endif
	}
}

void eHdmiCEC::sendMessage(unsigned char address, unsigned char cmd, char *data, int length)
{
	struct cec_message message;
	message.address = address;
	if (length > (int)(sizeof(message.data) - 1)) length = sizeof(message.data) - 1;
	message.length = length + 1;
	message.data[0] = cmd;
	memcpy(&message.data[1], data, length);
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
