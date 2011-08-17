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

void eHdmiCEC::getAddressInfo(unsigned char *physicaladdress, unsigned char &logicaladdress, unsigned char &type)
{
	physicaladdress[0] = 0x10;
	physicaladdress[1] = 0x00;
	logicaladdress = 3;
	type = 3;
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
			physicaladdress[0] = addressinfo.physical[0];
			physicaladdress[1] = addressinfo.physical[1];
			type = addressinfo.type;
			logicaladdress = addressinfo.logical;
		}
	}
}

int eHdmiCEC::getLogicalAddress()
{
	unsigned char physicaladdress[2];
	unsigned char logicaladdress, type;
	getAddressInfo(physicaladdress, logicaladdress, type);
	return logicaladdress;
}

int eHdmiCEC::getPhysicalAddress()
{
	unsigned char physicaladdress[2];
	unsigned char logicaladdress, type;
	getAddressInfo(physicaladdress, logicaladdress, type);
	return (physicaladdress[0] << 8) | physicaladdress[1];
}

int eHdmiCEC::getDeviceType()
{
	unsigned char physicaladdress[2];
	unsigned char logicaladdress, type;
	getAddressInfo(physicaladdress, logicaladdress, type);
	return type;
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
	struct cec_message rxmessage, txmessage;
	if (::read(hdmiFd, &rxmessage, 2) == 2)
	{
		if (::read(hdmiFd, &rxmessage.data, rxmessage.length) == rxmessage.length)
		{
			bool keypressed = false;
			unsigned char logicaladdress, devicetype;
			static unsigned char pressedkey = 0;

			eDebugNoNewLine("eHdmiCEC: received message");
			for (int i = 0; i < rxmessage.length; i++)
			{
				eDebugNoNewLine(" %02X", rxmessage.data[i]);
			}
			eDebug(" ");
			txmessage.length = 0; /* no reply */
			txmessage.address = 0; /* TV */
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
				case 0x46: /* request name */
					txmessage.data[0] = 0x47; /* set name */
					strcpy((char*)&txmessage.data[1], "linux stb");
					txmessage.length = 11;
					break;
				case 0x8f: /* request power status */
					txmessage.data[0] = 0x90; /* report power */
					txmessage.data[1] = getActiveStatus() ? 0x00 : 0x01;
					txmessage.length = 2;
					break;
				case 0x83: /* request address */
					txmessage.address = 0x0f; /* broadcast */
					txmessage.data[0] = 0x84; /* report address */
					getAddressInfo(&txmessage.data[1], logicaladdress, devicetype);
					txmessage.data[3] = devicetype;
					txmessage.length = 4;
					break;
				case 0x86: /* request streaming path */
					if (getActiveStatus())
					{
						txmessage.address = 0x0f; /* broadcast */
						txmessage.data[0] = 0x82; /* report active source */
						getAddressInfo(&txmessage.data[1], logicaladdress, devicetype);
						txmessage.length = 3;
					}
					break;
				case 0x85: /* request active source */
					if (getActiveStatus())
					{
						txmessage.address = 0x0f; /* broadcast */
						txmessage.data[0] = 0x82; /* report active source */
						getAddressInfo(&txmessage.data[1], logicaladdress, devicetype);
						txmessage.length = 3;
					}
					break;
				case 0x8c: /* request vendor id */
					txmessage.data[0] = 0x87; /* vendor id */
					txmessage.data[1] = 0x00; /* example: panasonic */
					txmessage.data[2] = 0x80;
					txmessage.data[3] = 0x45;
					txmessage.length = 4;
					break;
				case 0x8d: /* menu request */
					if (txmessage.data[1] == 0x02) /* query */
					{
						txmessage.data[0] = 0x8e; /* menu status */
						txmessage.data[1] = getActiveStatus() ? 0x00 : 0x01; /* menu activated / deactivated (reporting 'menu active' will activate rc passthrough mode on some tv's) */
						txmessage.length = 2;
					}
					break;
			}

			if (txmessage.length)
			{
				sendMessage(txmessage);
			}
			else
			{
				/* we did not reply, allow the command to be handled by external components */
				/* there is no simple way to pass the complete message object to python, so we support only single byte commands for now */
				messageReceived(rxmessage.address, rxmessage.data[0]);
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

void eHdmiCEC::sendMessage(struct cec_message &message)
{
	if (hdmiFd >= 0)
	{
		eDebugNoNewLine("eHdmiCEC: send message");
		for (int i = 0; i < message.length; i++)
		{
			eDebugNoNewLine(" %02X", message.data[i]);
		}
		eDebug(" ");
		::write(hdmiFd, &message, 2 + message.length);
	}
}

void eHdmiCEC::sendMessage(unsigned char address, unsigned char length, char *data)
{
	struct cec_message message;
	message.address = address;
	if (length > sizeof(message.data)) length = (unsigned char)sizeof(message.data);
	message.length = length;
	memcpy(message.data, data, length);
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
