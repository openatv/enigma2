#include <lib/driver/rcinput.h>

#include <sys/ioctl.h>
#include <linux/input.h>
#include <sys/stat.h>

#include <lib/base/ebase.h>
#include <lib/base/init.h>
#include <lib/base/init_num.h>
#include <lib/driver/input_fake.h>

void eRCDeviceInputDev::handleCode(int rccode)
{
	struct input_event *ev = (struct input_event *)rccode;
	if (ev->type!=EV_KEY)
		return;
	eDebug("%x %x %x", ev->value, ev->code, ev->type);
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

eRCDeviceInputDev::eRCDeviceInputDev(eRCInputEventDriver *driver): eRCDevice(driver->getDeviceName(), driver)
{
}

const char *eRCDeviceInputDev::getDescription() const
{
	return id.c_str();
}

const char *eRCDeviceInputDev::getKeyDescription(const eRCKey &key) const
{
	switch (key.code)
	{
	case KEY_0: return "0";
	case KEY_1: return "1";
	case KEY_2: return "2";
	case KEY_3: return "3";
	case KEY_4: return "4";
	case KEY_5: return "5";
	case KEY_6: return "6";
	case KEY_7: return "7";
	case KEY_8: return "8";
	case KEY_9: return "9";
	case KEY_RIGHT: return "rechts";
	case KEY_LEFT: return "links";
	case KEY_UP: return "oben";
	case KEY_DOWN: return "unten";
	case KEY_OK: return "ok";
	case KEY_MUTE: return "mute";
	case KEY_POWER: return "power";
	case KEY_GREEN: return "gruen";
	case KEY_YELLOW: return "gelb";
	case KEY_RED: return "rot";
	case KEY_BLUE: return "blau";
	case KEY_VOLUMEUP: return "Lautstaerke plus";
	case KEY_VOLUMEDOWN: return "Lautstaerke minus";
	case KEY_HELP: return "?";
	case KEY_SETUP: return "d-Box";
#if 0
	case KEY_TOPLEFT: return "oben links";
	case KEY_TOPRIGHT: return "oben rechts";
	case KEY_BOTTOMLEFT: return "unten links";
	case KEY_BOTTOMRIGHT: return "unten rechts";
#endif
	case KEY_HOME: return "home";
	default: return 0;
	}
}

int eRCDeviceInputDev::getKeyCompatibleCode(const eRCKey &key) const
{
	switch (key.code)
	{
		case KEY_0: return eRCInput::RC_0;
		case KEY_1: return eRCInput::RC_1;
		case KEY_2: return eRCInput::RC_2;
		case KEY_3: return eRCInput::RC_3;
		case KEY_4: return eRCInput::RC_4;
		case KEY_5: return eRCInput::RC_5;
		case KEY_6: return eRCInput::RC_6;
		case KEY_7: return eRCInput::RC_7;
		case KEY_8: return eRCInput::RC_8;
		case KEY_9: return eRCInput::RC_9;
		case KEY_RIGHT: return eRCInput::RC_RIGHT;
		case KEY_LEFT: return eRCInput::RC_LEFT;
		case KEY_UP: return eRCInput::RC_UP;
		case KEY_DOWN: return eRCInput::RC_DOWN;
		case KEY_OK: return eRCInput::RC_OK;
		case KEY_MUTE: return eRCInput::RC_MUTE;
		case KEY_POWER: return eRCInput::RC_STANDBY;
		case KEY_GREEN: return eRCInput::RC_GREEN;
		case KEY_YELLOW: return eRCInput::RC_YELLOW;
		case KEY_RED: return eRCInput::RC_RED;
		case KEY_VOLUMEUP: return eRCInput::RC_PLUS;
		case KEY_BLUE: return eRCInput::RC_BLUE;
		case KEY_VOLUMEDOWN: return eRCInput::RC_MINUS;
		case KEY_HELP: return eRCInput::RC_HELP;
		case KEY_SETUP: return eRCInput::RC_DBOX;
		case KEY_HOME: return eRCInput::RC_HOME;
	}
	return -1;
}


class eInputDeviceInit
{
	eRCInputEventDriver driver;
	eRCDeviceInputDev deviceInputDev;
public:
	eInputDeviceInit(): driver("/dev/input/event0"), deviceInputDev(&driver)
	{
	}
};

eAutoInitP0<eInputDeviceInit> init_rcinputdev(eAutoInitNumbers::rc+1, "input device driver");
