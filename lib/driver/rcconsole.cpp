#include <lib/base/init.h>
#include <lib/base/init_num.h>
#include <lib/base/eerror.h>
#include <lib/driver/rcconsole.h>
#include <stdio.h>
#include <fcntl.h>

eRCConsoleDriver::eRCConsoleDriver(const char *filename): eRCDriver(eRCInput::getInstance()), m_escape(false)
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

	if (handle >= 0)
	{
			/* set console mode */
		struct termios t;
		tcgetattr(handle, &t);
		ot = t;
		t.c_lflag &= ~(ECHO | ICANON | ECHOK | ECHOE | ECHONL);
		tcsetattr(handle, TCSANOW,&t);
	}
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
	unsigned char code;

	int km = input->getKeyboardMode();

	if (km == eRCInput::kmNone)
		return;

	while (num-- > 0)
	{
		code = *d++;
//		eDebug("console code %02x\n", code);
		if (km == eRCInput::kmAscii) {
			if (m_escape) {
				if (code != '[')
					m_escape = false;
				continue;
			}

			if (code == 27) // escape code
				m_escape = true;

			if ((code < 32) ||	// control characters
			    (code == 0x7e) ||	// mute, einfg, entf
			    (code == 0x7f))	// backspace
				continue;
		}

		for (std::list<eRCDevice*>::iterator i(listeners.begin()); i!=listeners.end(); ++i)
		{
//			eDebug("ascii %02x", code);
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
	eRCConsoleInit(): driver("/dev/tty0"), device(&driver)
	{
	}
};

eAutoInitP0<eRCConsoleInit> init_rcconsole(eAutoInitNumbers::rc+1, "Console RC Driver");
