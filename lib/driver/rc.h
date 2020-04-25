#ifndef __rc_h
#define __rc_h

#include <list>
#include <map>

#include <linux/input.h>

#include <lib/base/ebase.h>
#include <libsig_comp.h>
#include <string>

class eRCInput;
class eRCDriver;
class eRCKey;

#ifndef SWIG

/**
 * \brief A remote control.
 *
 * Handles one remote control. Gets codes from a \ref eRCDriver. Produces events in \ref eRCInput.
 */
class eRCDevice: public sigc::trackable
{
protected:
	eRCInput *input;
	eRCDriver *driver;
	std::string id;
public:
	/**
	 * \brief Constructs a new remote control.
	 *
	 * \param id The identifier of the RC, for use in settings.
	 * \param input The \ref eRCDriver where this remote gets its codes from.
	 */
	eRCDevice(std::string id, eRCDriver *input);
	virtual ~eRCDevice();
	/**
	 * \brief Handles a device specific code.
	 *
	 * Generates events in \ref eRCInput. code is highly device- and driver dependant.
	 * For Example, it might be 16bit codes with one bit make/break or special codes
	 * for repeat.
	 */
	virtual void handleCode(long code)=0;
	/**
	 * \brief Get user readable description.
	 * \result The description.
	 */
	virtual const char *getDescription() const=0;
	const std::string getIdentifier() const { return id; }
	/**
	 * \brief Get a description for a specific key.
	 * \param key The key to get the description for.
	 * \result User readable description of given key.
	 */
	virtual void setExclusive(bool b) { };
};

/**
 * Receives codes from one or more remote controls.
 */
class eRCDriver: public sigc::trackable
{
protected:
	std::list<eRCDevice*> listeners;
	eRCInput *input;
	int enabled;
public:
	/**
	 * \brief Constructs a driver.
	 *
	 * \param input The RCInput to bind this driver to.
	 */
	eRCDriver(eRCInput *input);
	/**
	 * \brief Get pointer to key-consumer.
	 */
	eRCInput *getInput() const { return input; }
	/**
	 * \brief Adds a code lister
	 */
	void addCodeListener(eRCDevice *dev)
	{
		listeners.push_back(dev);
	}
	void removeCodeListener(eRCDevice *dev)
	{
		listeners.remove(dev);
	}
	virtual ~eRCDriver();

	void enable(int en) { enabled=en; }
	virtual void setExclusive(bool) { }
	virtual bool isKeyboard() { return false; }
	virtual bool isPointerDevice() { return false; }
};

class eRCShortDriver: public eRCDriver
{
protected:
	int handle;
	ePtr<eSocketNotifier> sn;
	void keyPressed(int);
public:
	eRCShortDriver(const char *filename);
	~eRCShortDriver();
};

class eRCInputEventDriver: public eRCDriver
{
protected:
	bool m_remote_control;
	int handle;
	unsigned char evCaps[(EV_MAX / 8) + 1];
	unsigned char keyCaps[(KEY_MAX / 8) + 1];
	ePtr<eSocketNotifier> sn;
	void keyPressed(int);
public:
	std::string getDeviceName();
	eRCInputEventDriver(const char *filename);
	~eRCInputEventDriver();
	void setExclusive(bool b); // in exclusive mode data is not carried to console device
	bool isKeyboard();
	bool isPointerDevice();
	bool hasCap(unsigned char *caps, int bit);
};

class eRCKey
{
public:
	eRCDevice *producer;
	int code, flags;

	eRCKey(eRCDevice *producer, int code, int flags):
		producer(producer), code(code), flags(flags)
	{
	}
	enum
	{
			/* there are not really flags.. */
		flagMake=0,
		flagBreak=1,
		flagRepeat=2,
		flagLong=3,
			/* but this is. */
		flagAscii=4,
	};

	bool operator<(const eRCKey &r) const
	{
		if (r.producer == producer)
		{
			if (r.code == code)
			{
				if (r.flags < flags)
					return 1;
				else
					return 0;
			} else if (r.code < code)
				return 1;
			else
				return 0;
		} else if (r.producer < producer)
			return 1;
		else
			return 0;
	}
};

class eRCConfig
{
public:
	eRCConfig();
	~eRCConfig();
	void reload();
	void save();
	void set(int delay, int repeat);
	int rdelay, // keypress delay after first keypress to begin of repeat (in ms)
		rrate;		// repeat rate (in ms)
};

#endif

class eRCInput: public sigc::trackable
{
	int locked;
	static eRCInput *instance;
	int keyboardMode;
#ifdef SWIG
	eRCInput();
	~eRCInput();
public:
#else
public:
	struct lstr
	{
		bool operator()(const std::string &a, const std::string &b) const
		{
			return a<b;
		}
	};
protected:
	std::map<std::string,eRCDevice*,lstr> devices;
public:
	sigc::signal1<void, const eRCKey&> keyEvent;
	eRCInput();
	~eRCInput();

	void close();
	bool open();

	/* This is only relevant for "keyboard"-styled input devices,
	   i.e. not plain remote controls. It's up to the input device
	   driver to decide wheter an input device is a keyboard or
	   not.

	   kmNone will ignore all Ascii Characters sent from the
	   keyboard/console driver, only give normal keycodes to the
	   application.

	   kmAscii will filter out all keys which produce ascii characters,
	   and send them instead. Note that Modifiers like shift will still
	   be send. Control keys which produce escape codes are send using
	   normal keycodes.

	   kmAll will ignore all keycodes, and send everything as ascii,
	   including escape codes. Pretty much useless, since you should
	   lock the console and pass this as the console fd for making the
	   tc* stuff working.
	*/

	void keyPressed(const eRCKey &key)
	{
		/*emit*/ keyEvent(key);
	}

	void addDevice(const std::string &id, eRCDevice *dev);
	void removeDevice(const std::string &id);
	eRCDevice *getDevice(const std::string &id);
	std::map<std::string,eRCDevice*,lstr> &getDevices();

	eRCConfig config;
#endif
	enum { kmNone, kmAscii, kmAll };
	void setKeyboardMode(int mode) { keyboardMode = mode; }
	int  getKeyboardMode() { return keyboardMode; }
	static eRCInput *getInstance() { return instance; }
	void lock();
	void unlock();
	int islocked() { return locked; }
};

#endif
