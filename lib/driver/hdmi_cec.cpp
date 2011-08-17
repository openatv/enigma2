#include <unistd.h>
#include <fcntl.h>
#include <sys/ioctl.h>
#include <string.h>

#include <lib/base/init.h>
#include <lib/base/init_num.h>
#include <lib/base/eerror.h>
#include <lib/base/ebase.h>
#include <lib/driver/input_fake.h>
#include <lib/driver/hdmi_cec.h>
#include <lib/driver/avswitch.h>

eHdmiCEC *eHdmiCEC::instance = NULL;

eHdmiCEC::eHdmiCEC()
: eRCDriver(eRCInput::getInstance())
{
	ASSERT(!instance);
	instance = this;
	hdmiFd = ::open("/dev/hdmi_cec", O_RDWR | O_NONBLOCK);
	if (hdmiFd >= 0)
	{
		messageNotifier = eSocketNotifier::create(eApp, hdmiFd, eSocketNotifier::Read);
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

void eHdmiCEC::getPhysicalAddress(unsigned char *data)
{
	data[0] = 0x10;
	data[1] = 0x00;
	if (hdmiFd >= 0)
	{
		struct
		{
			unsigned char logical;
			unsigned char physical[2];
			unsigned char type;
		} addressinfo;
		if (ioctl(hdmiFd, 1, &addressinfo) >= 0)
		{
			data[0] = addressinfo.physical[0];
			data[1] = addressinfo.physical[1];
		}
	}
}

int eHdmiCEC::getPhysicalAddress()
{
	unsigned char data[2];
	getPhysicalAddress(data);
	return (data[0] << 8) | data[1];
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
	struct cec_message message;
	if (::read(hdmiFd, &message, 2) == 2)
	{
		if (::read(hdmiFd, &message.data, message.length) == message.length)
		{
			bool keypressed = false;
			static unsigned char pressedkey = 0;

			/* there is no simple way to pass the complete message object to python, so we support only single byte commands for now */
			messageReceived(message.address, message.data[0]);
			eDebugNoNewLine("eHdmiCEC: received message");
			for (int i = 0; i < message.length; i++)
			{
				eDebugNoNewLine(" %02X", message.data[i]);
			}
			eDebug("");
			message.address = 0; /* TV */
			switch (message.data[0])
			{
				case 0x44: /* key pressed */
					keypressed = true;
					pressedkey = message.data[1];
				case 0x45: /* key released */
				{
					long code = translateKey(pressedkey);
					if (keypressed) code |= 0x80000000;
					for (std::list<eRCDevice*>::iterator i(listeners.begin()); i != listeners.end(); ++i)
					{
						(*i)->handleCode(code);
					}
					message.length = 0; /* no reply */
					break;
				}
				case 0x46: /* request name */
					message.data[0] = 0x47; /* set name */
					strcpy(&message.data[1], "linux stb");
					message.length = 11;
					break;
				case 0x8f: /* request power status */
					message.data[0] = 0x90; /* report power */
					message.data[1] = getActiveStatus() ? 0x00 : 0x01;
					message.length = 2;
					break;
				case 0x83: /* request address */
					message.address = 0x0f; /* broadcast */
					message.data[0] = 0x84; /* report address */
					getPhysicalAddress(&message.data[1]);
					message.length = 3;
					break;
				case 0x86: /* request streaming path */
					message.address = 0x0f; /* broadcast */
					message.data[0] = getActiveStatus() ? 0x82 : 0x9d; /* report active / inactive */
					getPhysicalAddress(&message.data[1]);
					message.length = 3;
					break;
				case 0x85: /* request active source */
					message.address = 0x0f; /* broadcast */
					message.data[0] = getActiveStatus() ? 0x82 : 0x9d; /* report active / inactive */
					getPhysicalAddress(&message.data[1]);
					message.length = 3;
					break;
				case 0x8c: /* request vendor id */
					message.data[0] = 0x87; /* vendor id */
					message.data[1] = 0x00; /* example: panasonic */
					message.data[2] = 0x80;
					message.data[3] = 0x45;
					message.length = 4;
					break;
				case 0x8d: /* menu request */
					if (message.data[1] == 0x02) /* query */
					{
						message.data[0] = 0x8e; /* menu status */
						message.data[1] = getActiveStatus() ? 0x00 : 0x01; /* menu activated / deactivated (reporting 'menu active' will activate rc passthrough mode on some tv's) */
						message.length = 2;
					}
					break;
				default:
					message.length = 0; /* no reply */
					break;
			}

			if (message.length)
			{
				sendMessage(message.address, message.length, message.data);
			}
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
		case 0x53:
			key = 0x166;
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

void eHdmiCEC::sendMessage(unsigned char address, unsigned char length, char *data)
{
	if (hdmiFd >= 0)
	{
		struct cec_message message;
		message.address = address;
		if (length > sizeof(message.data)) length = sizeof(message.data);
		message.length = length;
		memcpy(message.data, data, length);
		eDebugNoNewLine("eHdmiCEC: send message");
		for (int i = 0; i < message.length; i++)
		{
			eDebugNoNewLine(" %02X", message.data[i]);
		}
		eDebug("");
		::write(hdmiFd, &message, 2 + length);
	}
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
