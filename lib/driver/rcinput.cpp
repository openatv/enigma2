#include <lib/driver/rcinput.h>

#include <lib/base/eerror.h>

#include <sys/ioctl.h>
#include <linux/input.h>
#include <linux/kd.h>
#include <sys/stat.h>
#include <fcntl.h>

#include <lib/base/ebase.h>
#include <lib/base/init.h>
#include <lib/base/init_num.h>
#include <lib/driver/input_fake.h>

void eRCDeviceInputDev::handleCode(long rccode)
{
	struct input_event *ev = (struct input_event *)rccode;
	if (ev->type!=EV_KEY)
		return;

	if (ev->type!=EV_KEY)
		return;

	int km = iskeyboard ? input->getKeyboardMode() : eRCInput::kmNone;

	switch (ev->code)
	{
	case KEY_LEFTSHIFT:
	case KEY_RIGHTSHIFT:
		shiftState = ev->value;
		break;
	case KEY_CAPSLOCK:
		if (ev->value == 1) capsState = !capsState;
		break;
	}

	if (km == eRCInput::kmAll)
		return;

	if (km == eRCInput::kmAscii)
	{
		bool ignore = false;
		bool ascii = (ev->code > 0 && ev->code < 61);
		switch (ev->code)
		{
			case KEY_LEFTCTRL:
			case KEY_RIGHTCTRL:
			case KEY_LEFTSHIFT:
			case KEY_RIGHTSHIFT:
			case KEY_LEFTALT:
			case KEY_RIGHTALT:
			case KEY_CAPSLOCK:
				ignore = true;
				break;
			case KEY_RESERVED:
			case KEY_ESC:
			case KEY_TAB:
			case KEY_BACKSPACE:
			case KEY_ENTER:
			case KEY_INSERT:
			case KEY_DELETE:
			case KEY_MUTE:
				ascii = false;
			default:
				break;
		}
		if (ignore) return;
		if (ascii)
		{
			if (ev->value)
			{
				if (consoleFd >= 0)
				{
					struct kbentry ke;
					/* off course caps is not the same as shift, but this will have to do for now */
					ke.kb_table = (shiftState || capsState) ? K_SHIFTTAB : K_NORMTAB;
					ke.kb_index = ev->code;
					::ioctl(consoleFd, KDGKBENT, &ke);
					if (ke.kb_value)
					{
						/* emit */ input->keyPressed(eRCKey(this, ke.kb_value & 0xff, eRCKey::flagAscii));
					}
				}
			}
			return;
		}
	}

#if KEY_PLAY_ACTUALLY_IS_KEY_PLAYPAUSE
	if (ev->code == KEY_PLAY)
	{
		if (id == "dreambox advanced remote control (native)")
		{
			/* 8k rc has a KEY_PLAYPAUSE key, which sends KEY_PLAY events. Correct this, so we do not have to place hacks in the keymaps. */
			ev->code = KEY_PLAYPAUSE;
		}
	}
#endif

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

eRCDeviceInputDev::eRCDeviceInputDev(eRCInputEventDriver *driver, int consolefd)
	:eRCDevice(driver->getDeviceName(), driver), iskeyboard(driver->isKeyboard()),
	ismouse(driver->isPointerDevice()),
	consoleFd(consolefd), shiftState(false), capsState(false)
{
	setExclusive(true);
	eDebug("Input device \"%s\" is a %s", id.c_str(), iskeyboard ? "keyboard" : (ismouse ? "mouse" : "remotecontrol"));
}

void eRCDeviceInputDev::setExclusive(bool b)
{
	if (!iskeyboard && !ismouse)
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

	int consoleFd;

public:
	eInputDeviceInit()
	{
		int i = 0;
		consoleFd = ::open("/dev/tty0", O_RDWR);
		while (1)
		{
			struct stat s;
			char filename[128];
			sprintf(filename, "/dev/input/event%d", i);
			if (stat(filename, &s))
				break;
			eRCInputEventDriver *p;
			m_drivers.push_back(p = new eRCInputEventDriver(filename));
			m_devices.push_back(new eRCDeviceInputDev(p, consoleFd));
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
		if (consoleFd >= 0)
		{
			::close(consoleFd);
		}
	}
};

eAutoInitP0<eInputDeviceInit> init_rcinputdev(eAutoInitNumbers::rc+1, "input device driver");
