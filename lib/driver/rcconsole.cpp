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
		sn=new eSocketNotifier(eApp, handle, eSocketNotifier::Read);
		CONNECT(sn->activated, eRCConsoleDriver::keyPressed);
		eRCInput::getInstance()->setFile(handle);
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
	if (sn)
		delete sn;
}

void eRCConsoleDriver::keyPressed(int)
{
	char data[16];
	char *d = data;
	int num = read(handle, data, 16);
	int code=-1;
	
	int km = input->getKeyboardMode();

	while (num--)
	{
//		eDebug("console code %02x\n", *d++);
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
			if (code == 0x7F)		/* delete */
				code = -1;
		}

		if (code != -1)
			for (std::list<eRCDevice*>::iterator i(listeners.begin()); i!=listeners.end(); ++i)
			{
//				eDebug("ascii %08x", code);
				(*i)->handleCode(/*0x8000|*/code);
			}
	}
}

void eRCConsole::handleCode(int code)
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
