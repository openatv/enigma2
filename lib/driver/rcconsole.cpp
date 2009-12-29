#include <lib/base/init.h>
#include <lib/base/init_num.h>
#include <lib/base/eerror.h>
#include <lib/driver/rcconsole.h>
#include <stdio.h>
#include <fcntl.h>

eRCConsoleDriver::eRCConsoleDriver(const char *filename): eRCDriver(eRCInput::getInstance())
{
	handle=open(filename, O_RDONLY|O_NONBLOCK);
	if (handle<0)
	{
		eDebug("failed to open %s", filename);
		sn=0;
	} else
	{
		sn=eSocketNotifier::create(eApp, handle, eSocketNotifier::Read);
		CONNECT(sn->activated, eRCConsoleDriver::keyPressed);
	}
	
		/* set console mode */
	struct termios t;
	tcgetattr(handle, &t);
	ot = t;
	t.c_lflag &= ~(ECHO | ICANON | ECHOK | ECHOE | ECHONL);
	tcsetattr(handle, TCSANOW,&t);
}

eRCConsoleDriver::~eRCConsoleDriver()
{
	tcsetattr(handle,TCSANOW, &ot);
 	if (handle>=0)
		close(handle);
}

void eRCConsoleDriver::keyPressed(int)
{
	unsigned char data[16];
	unsigned char *d = data;
	int num = read(handle, data, 16);
	int code=-1;
	
	int km = input->getKeyboardMode();

	if (km == eRCInput::kmNone)
		return;

	while (num--)
	{
//		eDebug("console code %08x\n", *d);
		if (km == eRCInput::kmAll)
			code = *d++;
		else
		{
			if (*d == 27) // escape code
			{
				while (num)
				{
					num--;
					if (*++d != '[')
						break;
				}
				code = -1;
			} else
				code = *d;
			++d;

			if (code < 32)			/* control characters */
				code = -1;
			else switch(code)
			{
			case 0x7E:  // mute, einfg, entf
			case 0x7F:  // backspace
			code = -1;
			default:
				break;
			}
		}

		if (code != -1)
			for (std::list<eRCDevice*>::iterator i(listeners.begin()); i!=listeners.end(); ++i)
			{
//				eDebug("ascii %08x", code);
				(*i)->handleCode(code);
			}
	}
}

void eRCConsole::handleCode(long code)
{
	input->keyPressed(eRCKey(this, code, eRCKey::flagAscii));
}

eRCConsole::eRCConsole(eRCDriver *driver)
			: eRCDevice("Console", driver)
{
}

const char *eRCConsole::getDescription() const
{
	return "Console";
}

const char *eRCConsole::getKeyDescription(const eRCKey &key) const
{
	return 0;
}

int eRCConsole::getKeyCompatibleCode(const eRCKey &key) const
{
	return key.code;
}

class eRCConsoleInit
{
	eRCConsoleDriver driver;
	eRCConsole device;
public:
	eRCConsoleInit(): driver("/dev/vc/0"), device(&driver)
	{
	}
};

eAutoInitP0<eRCConsoleInit> init_rcconsole(eAutoInitNumbers::rc+1, "Console RC Driver");
