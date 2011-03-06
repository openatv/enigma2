#include <unistd.h>
#include <fcntl.h>
#include <sys/ioctl.h>
#include <string.h>

#include <lib/base/init.h>
#include <lib/base/init_num.h>
#include <lib/base/eerror.h>
#include <lib/base/ebase.h>
#include <lib/driver/hdmi_cec.h>

eHdmiCEC *eHdmiCEC::instance = NULL;

eHdmiCEC::eHdmiCEC()
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

void eHdmiCEC::hdmiEvent(int what)
{
	struct cec_message message;
	if (::read(hdmiFd, &message, 2) == 2)
	{
		if (::read(hdmiFd, &message.data, message.length) == message.length)
		{
			/* there is no simple way to pass the complete message object to python, so we support only single byte commands for now */
			messageReceived(message.address, message.data[0]);
		}
	}
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
		::write(hdmiFd, &message, 2 + length);
	}
}

eAutoInitP0<eHdmiCEC> init_hdmicec(eAutoInitNumbers::rc, "Hdmi CEC driver");
