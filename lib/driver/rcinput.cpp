#include <lib/driver/rcinput.h>

#include <lib/base/eerror.h>

#include <sys/ioctl.h>
#include <linux/input.h>
#include <sys/stat.h>

#include <lib/base/ebase.h>
#include <lib/base/init.h>
#include <lib/base/init_num.h>
#include <lib/driver/input_fake.h>

void eRCDeviceInputDev::handleCode(long rccode)
{
	struct input_event *ev = (struct input_event *)rccode;
	if (ev->type!=EV_KEY)
		return;

//	eDebug("%x %x %x", ev->value, ev->code, ev->type);

	if (ev->type!=EV_KEY)
		return;

	int km = iskeyboard ? input->getKeyboardMode() : eRCInput::kmNone;

//	eDebug("keyboard mode %d", km);
	
	if (km == eRCInput::kmAll)
		return;

	if (km == eRCInput::kmAscii)
	{
//		eDebug("filtering.. %d", ev->code);
		bool filtered = ( ev->code > 0 && ev->code < 61 );
		switch (ev->code)
		{
			case KEY_RESERVED:
			case KEY_ESC:
			case KEY_TAB:
			case KEY_BACKSPACE:
			case KEY_ENTER:
			case KEY_LEFTCTRL:
			case KEY_RIGHTSHIFT:
			case KEY_LEFTALT:
			case KEY_CAPSLOCK:
			case KEY_INSERT:
			case KEY_DELETE:
			case KEY_MUTE:
				filtered=false;
			default:
				break;
		}
		if (filtered)
			return;
//		eDebug("passed!");
	}

	switch (ev->value)
	{
	case 0:
		/*emit*/ input->keyPressed(eRCKey(this, ev->code, eRCKey::flagBreak));
		break;
	case 1:
		/*emit*/ input->keyPressed(eRCKey(this, ev->code, 0));
		break;
	case 2:
		/*emit*/ input->keyPressed(eRCKey(this, ev->code, eRCKey::flagRepeat));
		break;
	}
}

eRCDeviceInputDev::eRCDeviceInputDev(eRCInputEventDriver *driver)
	:eRCDevice(driver->getDeviceName(), driver), iskeyboard(false)
{
	if (strcasestr(id.c_str(), "keyboard") != NULL)
		iskeyboard = true;
	setExclusive(true);
	eDebug("Input device \"%s\" is %sa keyboard.", id.c_str(), iskeyboard ? "" : "not ");
}

void eRCDeviceInputDev::setExclusive(bool b)
{
	if (!iskeyboard)
		driver->setExclusive(b);
}

const char *eRCDeviceInputDev::getDescription() const
{
	return id.c_str();
}

class eInputDeviceInit
{
	ePtrList<eRCInputEventDriver> m_drivers;
	ePtrList<eRCDeviceInputDev> m_devices;
public:
	eInputDeviceInit()
	{
		int i = 0;
		while (1)
		{
			struct stat s;
			char filename[128];
			sprintf(filename, "/dev/input/event%d", i);
			if (stat(filename, &s))
				break;
			eRCInputEventDriver *p;
			m_drivers.push_back(p = new eRCInputEventDriver(filename));
			m_devices.push_back(new eRCDeviceInputDev(p));
			++i;
		}
		eDebug("Found %d input devices!", i);
	}
	
	~eInputDeviceInit()
	{
		while (m_drivers.size())
		{
			delete m_devices.back();
			m_devices.pop_back();
			delete m_drivers.back();
			m_drivers.pop_back();
		}
	}
};

eAutoInitP0<eInputDeviceInit> init_rcinputdev(eAutoInitNumbers::rc+1, "input device driver");
