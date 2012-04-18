#ifndef DISABLE_DREAMBOX_RC

#include <lib/driver/rcdreambox2.h>

#include <lib/base/eerror.h>

#include <sys/ioctl.h>
#include <linux/input.h>
#include <sys/stat.h>

#include <lib/base/ebase.h>
#include <lib/base/init.h>
#include <lib/base/init_num.h>
#include <lib/driver/input_fake.h>


int eRCDeviceDreambox2::getKeyCode(int key)
{
	switch (key)
	{
	case 0x00: return KEY_0;
	case 0x01: return KEY_1;
	case 0x02: return KEY_2;
	case 0x03: return KEY_3;
	case 0x04: return KEY_4;
	case 0x05: return KEY_5;
	case 0x06: return KEY_6;
	case 0x07: return KEY_7;
	case 0x08: return KEY_8;
	case 0x09: return KEY_9;
	case 0x0a: return KEY_VOLUMEUP;
	case 0x0b: return KEY_VOLUMEDOWN;
	case 0x0c: return KEY_TV;
	case 0x0d: return KEY_CHANNELUP;
	case 0x0e: return KEY_CHANNELDOWN;
	case 0x0f: return KEY_POWER;
	case 0x20: return KEY_MENU;
	case 0x21: return KEY_UP;
	case 0x22: return KEY_DOWN;
	case 0x23: return KEY_LEFT;
	case 0x24: return KEY_RIGHT;
	case 0x25: return KEY_OK;
	case 0x26: return KEY_AUDIO;
	case 0x27: return KEY_VIDEO;
	case 0x28: return KEY_INFO;
	case 0x40: return KEY_RED;
	case 0x41: return KEY_GREEN;
	case 0x42: return KEY_YELLOW;
	case 0x43: return KEY_BLUE;
	case 0x44: return KEY_MUTE;
	case 0x45: return KEY_TEXT;
	case 0x50: return KEY_RIGHT;
	case 0x51: return KEY_LEFT;
	case 0x52: return KEY_ESC;
	case 0x53: return KEY_RADIO;
	case 0x54: return KEY_HELP;
	}
	return -1;
}

void eRCDeviceDreambox2::handleCode(int rccode)
{
	/*eDebug("eRCDeviceDreambox2::handleCode rccode=%d 0x%x", rccode, rccode);*/
	if (rccode == 0x00FF) /* break code */
	{
		timeout.stop();
		repeattimer.stop();
		timeOut();
		return;
	}
	timeout.start(1500, 1);
	int old = ccode;
	ccode = rccode;
	if ((old != -1) && (((old & 0x7FFF) != (rccode & 0x7FFF)) || !(rccode & 0x8000)))
	{
		repeattimer.stop();
		/*emit*/ input->keyPressed(eRCKey(this, getKeyCode(old&0x7FFF), eRCKey::flagBreak));
	}
	if ((old^rccode)&0x7FFF)
	{
		input->keyPressed(eRCKey(this, getKeyCode(rccode&0x7FFF), 0));
	}
	else if (rccode&0x8000 && !repeattimer.isActive())
	{
		repeattimer.start(getRepeatDelay(), 1);
	}
}

int eRCDeviceDreambox2::getRepeatDelay()
{
	/* TODO: configure repeat delay? */
	return 500;
}

int eRCDeviceDreambox2::getRepeatRate()
{
	/* TODO: configure repeat rate? */
	return 50;
}

void eRCDeviceDreambox2::timeOut()
{
	int oldcc = ccode;
	ccode = -1;
	repeattimer.stop();
	if (oldcc != -1)
	{
		input->keyPressed(eRCKey(this, getKeyCode(oldcc&0x7FFF), eRCKey::flagBreak));
	}
}

void eRCDeviceDreambox2::repeat()
{
	if (ccode != -1)
	{
		input->keyPressed(eRCKey(this, getKeyCode(ccode&0x7FFF), eRCKey::flagRepeat));
	}
	repeattimer.start(getRepeatRate(), 1);
}

eRCDeviceDreambox2::eRCDeviceDreambox2(eRCDriver *driver)
 : eRCDevice("Dreambox2", driver), timeout(eApp), repeattimer(eApp)
{
	ccode = -1;
	CONNECT(timeout.timeout, eRCDeviceDreambox2::timeOut);
	CONNECT(repeattimer.timeout, eRCDeviceDreambox2::repeat);
}

const char *eRCDeviceDreambox2::getDescription() const
{
	return "dreambox RC";
}

int eRCDeviceDreamboxButton::getKeyCode(int button)
{
	switch (button)
	{
	case 1: return KEY_LEFT;
	case 2: return KEY_RIGHT;
	case 3: return KEY_POWER;
	}
	return -1;
}

void eRCDeviceDreamboxButton::handleCode(int code)
{
	code = (~code) & 0x7;
	int l = last;
	last = code;
	for (int i = 0; i < 4; i++)
	{
		if ((l & ~code) & (1 << i))
		{
			/*emit*/ input->keyPressed(eRCKey(this, getKeyCode(i), eRCKey::flagBreak));
		}
		else if ((~l & code) & (1 << i))
		{
			/*emit*/ input->keyPressed(eRCKey(this, getKeyCode(i), 0));
		}
	}
	if (code)
	{
		repeattimer.start(getRepeatDelay(), 1);
	}
	else
	{
		repeattimer.stop();
	}
}

int eRCDeviceDreamboxButton::getRepeatDelay()
{
	/* TODO: configure repeat delay? */
	return 500;
}

int eRCDeviceDreamboxButton::getRepeatRate()
{
	/* TODO: configure repeat rate? */
	return 50;
}

void eRCDeviceDreamboxButton::repeat()
{
	for (int i = 0; i < 4; i++)
	{
		if (last & (1<<i))
		{
			/*emit*/ input->keyPressed(eRCKey(this, getKeyCode(i), eRCKey::flagRepeat));
		}
	}
	repeattimer.start(getRepeatRate(), 1);
}

eRCDeviceDreamboxButton::eRCDeviceDreamboxButton(eRCDriver *driver)
 : eRCDevice("DreamboxButton", driver), repeattimer(eApp)
{
	last = 0;
	CONNECT(repeattimer.timeout, eRCDeviceDreamboxButton::repeat);
}

const char *eRCDeviceDreamboxButton::getDescription() const
{
	return "dreambox buttons";
}

class eRCDeviceDreambox2Init
{
	eRCShortDriver *m_driver;
	eRCDeviceDreambox2 *m_device;
	eRCShortDriver *m_buttondriver;
	eRCDeviceDreamboxButton *m_buttondevice;

public:
	eRCDeviceDreambox2Init()
	 : m_driver(NULL), m_device(NULL), m_buttondriver(NULL), m_buttondevice(NULL)
	{
		struct stat s;
		if (::access("/dev/rawir2", R_OK) >= 0)
		{
			m_driver = new eRCShortDriver("/dev/rawir2");
			m_device = new eRCDeviceDreambox2(m_driver);
		}
		if (::access("/dev/dbox/fpkeys0", R_OK) >= 0)
		{
			m_buttondriver = new eRCShortDriver("/dev/dbox/fpkeys0");
			m_buttondevice = new eRCDeviceDreamboxButton(m_buttondriver);
		}
	}
	~eRCDeviceDreambox2Init()
	{
		delete m_buttondevice;
		delete m_buttondriver;
		delete m_device;
		delete m_driver;
	}
};

eAutoInitP0<eRCDeviceDreambox2Init> init_rcdreamboxrc(eAutoInitNumbers::rc+1, "dreambox rc/button devices");

#endif // DISABLE_DREAMBOX_RC
