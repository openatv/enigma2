#include <lib/driver/rc.h>

#include <asm/types.h>
#include <stdio.h>
#include <fcntl.h>
#include <unistd.h>

#include <lib/base/init.h>
#include <lib/base/init_num.h>
#include <lib/base/eerror.h>

/*
 *  note on the enigma input layer:
 *  the enigma input layer (rc*) supports n different devices which
 *  all have completely different interfaces, mapped down to 32bit +
 *  make/break/release codes mapped down (via xml files) to "actions".
 *  this was necessary to support multiple remote controls with proprietary
 *  interfaces. now everybody is using input devices, and thus adding
 *  another input layer seems to be a bit overkill. BUT:
 *  image a remote control with two hundred buttons. each and every function
 *  in enigma can be bound to a button. no need to use them twice.
 *  for example, you would have KEY_MENU assigned to a menu for setup etc.,
 *  but no audio and video settings, since you have special keys for that,
 *  and you don't want to display a big menu with entries that are available
 *  with another single key.
 *  then image a remote control with ten buttons. do you really want to waste
 *  KEY_MENU for a simple menu? you need the audio/video settings there too.
 *  take this just as a (bad) example. another (better) example might be front-
 *  button-keys. usually you have KEY_UP, KEY_DOWN, KEY_POWER. you don't want
 *  them to behave like the remote-control-KEY_UP, KEY_DOWN and KEY_POWER,
 *  don't you?
 *  so here we can map same keys of different input devices to different
 *  actions. have fun.
 */

eRCDevice::eRCDevice(std::string id, eRCDriver *driver): driver(driver), id(id)
{
	input=driver->getInput();
	driver->addCodeListener(this);
	eRCInput::getInstance()->addDevice(id, this);
}

eRCDevice::~eRCDevice()
{
	driver->removeCodeListener(this);
	eRCInput::getInstance()->removeDevice(id.c_str());
}

eRCDriver::eRCDriver(eRCInput *input): input(input), enabled(1)
{
}

eRCDriver::~eRCDriver()
{
	for (std::list<eRCDevice*>::iterator i=listeners.begin(); i!=listeners.end(); ++i)
		delete *i;
}

void eRCShortDriver::keyPressed(int)
{
	uint16_t rccode;
	while (1)
	{
		if (read(handle, &rccode, 2)!=2)
			break;
		if (enabled && !input->islocked())
			for (std::list<eRCDevice*>::iterator i(listeners.begin()); i!=listeners.end(); ++i)
				(*i)->handleCode(rccode);
	}
}

eRCShortDriver::eRCShortDriver(const char *filename): eRCDriver(eRCInput::getInstance())
{
	handle=open(filename, O_RDONLY|O_NONBLOCK);
	if (handle<0)
	{
		eDebug("failed to open %s", filename);
		sn=0;
	} else
	{
		sn=eSocketNotifier::create(eApp, handle, eSocketNotifier::Read);
		CONNECT(sn->activated, eRCShortDriver::keyPressed);
	}
}

eRCShortDriver::~eRCShortDriver()
{
	if (handle>=0)
		close(handle);
}

void eRCInputEventDriver::keyPressed(int)
{
	struct input_event ev;
	while (1)
	{
		if (read(handle, &ev, sizeof(struct input_event))!=sizeof(struct input_event))
			break;
		if (enabled && !input->islocked())
			for (std::list<eRCDevice*>::iterator i(listeners.begin()); i!=listeners.end(); ++i)
				(*i)->handleCode((long)&ev);
	}
}

eRCInputEventDriver::eRCInputEventDriver(const char *filename): eRCDriver(eRCInput::getInstance())
{
	handle=open(filename, O_RDONLY|O_NONBLOCK);
	if (handle<0)
	{
		eDebug("failed to open %s", filename);
		sn=0;
	} else
	{
		sn=eSocketNotifier::create(eApp, handle, eSocketNotifier::Read);
		CONNECT(sn->activated, eRCInputEventDriver::keyPressed);
		memset(keyCaps, 0, sizeof(keyCaps));
		::ioctl(handle, EVIOCGBIT(EV_KEY, sizeof(keyCaps)), keyCaps);
		memset(evCaps, 0, sizeof(evCaps));
		::ioctl(handle, EVIOCGBIT(0, sizeof(evCaps)), evCaps);
	}
}

std::string eRCInputEventDriver::getDeviceName()
{
	char name[128]="";
	if (handle >= 0)
		::ioctl(handle, EVIOCGNAME(128), name);
#ifdef FORCE_ADVANCED_REMOTE
	if (!strcmp(name, "dreambox remote control (native)")) return "dreambox advanced remote control (native)";
#endif
	return name;
}

void eRCInputEventDriver::setExclusive(bool b)
{
	if (handle >= 0)
	{
		int grab = b;
		if (::ioctl(handle, EVIOCGRAB, grab) < 0)
			perror("EVIOCGRAB");
	}
}

bool eRCInputEventDriver::hasCap(unsigned char *caps, int bit)
{
	return (caps[bit / 8] & (1 << (bit % 8)));
}

bool eRCInputEventDriver::isKeyboard()
{
#ifdef VUPLUS_RC_WORKAROUND
	return(false);
#else
/*
 * 0000000000000000000000000000000000000000000000000000000000000000001000000000007ff800000000007fffebeffdfffeffffffffffffffffffffe Logitech USB Cordless Internet Pro
 * 0000000c000000004837fff072ff32dbf5c4447000000000000000000ff000100021f948b37cc0000677bfadd71dfed009ed680000044000000000010000002 Logitech USB Cordless Internet Pro
 * 00000000000000004837fff072ff32dbf5444460000000000000000ffff000100030f908b17c007ffff7bfad9415ffffebeffdfffeffffffffffffffffffffe Logitech K400 (uses unified receiver)
 * 0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000040000000 KEY_A
 * 0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000100000000000 KEY_Z
 * 0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000100000000000000000000000000000 KEY_POWER
 * 0000000000000000000000000000000000000000000000000000000000000000000000000000400000000000000000000000000000000000000000000000000 KEY_PROG3
 * 0000000000000000000000000000000000000000000000000000000000000000000800000000000000000000000000000000000000000000000000000000000 KEY_UWB
 * 0000000000000000000000000000000000000000002000000000000000000000000000000000000000000000000000000000000000000000000000000000000 BTN_GEAR_DOWN
 * 0000000000000000000000000000000000001000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000 KEY_VENDOR
 * 0000000000000000000000000010000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000 KEY_YELLOW
 * 4000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000 KEY_BRL_DOT10
 */

	/* Assume that a keyboard will have KEY_A and KEY_Z, but not all of these following esoteric
	 * keys: KEY_POWER, KEY_PROG3, KEY_UWB, BTN_GEAR_DOWN, KEY_VENDOR, KEY_YELLOW, KEY_BRL_DOT10.
	 */
	return hasCap(keyCaps, KEY_A) && hasCap(keyCaps, KEY_Z) &&
			!(
				hasCap(keyCaps, KEY_POWER) &&
				hasCap(keyCaps, KEY_PROG3) &&
				hasCap(keyCaps, KEY_UWB) &&
				hasCap(keyCaps, BTN_GEAR_DOWN) &&
				hasCap(keyCaps, KEY_VENDOR) &&
				hasCap(keyCaps, KEY_YELLOW) &&
				hasCap(keyCaps, KEY_BRL_DOT10)
			);
#endif
}

bool eRCInputEventDriver::isPointerDevice()
{
#ifdef VUPLUS_RC_WORKAROUND
	return(false);
#else
	return hasCap(evCaps, EV_REL) || hasCap(evCaps, EV_ABS);
#endif
}

eRCInputEventDriver::~eRCInputEventDriver()
{
	if (handle>=0)
		close(handle);
}

eRCConfig::eRCConfig()
{
	reload();
}

eRCConfig::~eRCConfig()
{
	save();
}

void eRCConfig::set( int delay, int repeat )
{
	rdelay = delay;
	rrate = repeat;
}

void eRCConfig::reload()
{
	rdelay=500;
	rrate=100;
}

void eRCConfig::save()
{
}

eRCInput *eRCInput::instance;

eRCInput::eRCInput()
{
	ASSERT( !instance);
	instance=this;
	locked = 0;
	keyboardMode = kmNone;
}

eRCInput::~eRCInput()
{
}

void eRCInput::close()
{
}

bool eRCInput::open()
{
	return false;
}

void eRCInput::lock()
{
	locked=1;
	for (std::map<std::string,eRCDevice*>::iterator i=devices.begin(); i != devices.end(); ++i)
		i->second->setExclusive(false);
}

void eRCInput::unlock()
{
	locked=0;
	for (std::map<std::string,eRCDevice*>::iterator i=devices.begin(); i != devices.end(); ++i)
		i->second->setExclusive(true);
}

void eRCInput::addDevice(const std::string &id, eRCDevice *dev)
{
	devices.insert(std::pair<std::string,eRCDevice*>(id, dev));
}

void eRCInput::removeDevice(const std::string &id)
{
	devices.erase(id);
}

eRCDevice *eRCInput::getDevice(const std::string &id)
{
	std::map<std::string,eRCDevice*>::iterator i=devices.find(id);
	if (i == devices.end())
	{
		eDebug("failed, possible choices are:");
		for (std::map<std::string,eRCDevice*>::iterator i=devices.begin(); i != devices.end(); ++i)
			eDebug("%s", i->first.c_str());
		return 0;
	}
	return i->second;
}

std::map<std::string,eRCDevice*,eRCInput::lstr> &eRCInput::getDevices()
{
	return devices;
}

eAutoInitP0<eRCInput> init_rcinput(eAutoInitNumbers::rc, "RC Input layer");
