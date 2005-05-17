#ifndef __rc_h
#define __rc_h

#include <list>
#include <map>

#include <lib/base/ebase.h>
#include <libsig_comp.h>
#include <string>

class eRCInput;
class eRCDriver;
class eRCKey;

/**
 * \brief A remote control.
 *
 * Handles one remote control. Gets codes from a \ref eRCDriver. Produces events in \ref eRCInput.
 */
class eRCDevice: public Object
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
	~eRCDevice();
	/**
	 * \brief Handles a device specific code.
	 *
	 * Generates events in \ref eRCInput. code is highly device- and driver dependant.
	 * For Example, it might be 16bit codes with one bit make/break or special codes
	 * for repeat.
	 */
	virtual void handleCode(int code)=0;
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
};

/**
 * Receives codes from one or more remote controls.
 */
class eRCDriver: public Object
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
	~eRCDriver();
	
	void enable(int en) { enabled=en; }
};

class eRCShortDriver: public eRCDriver
{
protected:
	int handle;
	eSocketNotifier *sn;
	void keyPressed(int);
public:
	eRCShortDriver(const char *filename);
	~eRCShortDriver();
};

class eRCInputEventDriver: public eRCDriver
{
protected:
	int handle;
	eSocketNotifier *sn;
	void keyPressed(int);
public:
	std::string getDeviceName();
	eRCInputEventDriver(const char *filename);
	~eRCInputEventDriver();
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
		flagBreak=1,
		flagRepeat=2
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

class eRCInput: public Object
{
	int locked;	
	int handle;
	static eRCInput *instance;

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
	Signal1<void, const eRCKey&> keyEvent;
	eRCInput();
	~eRCInput();
	
	int lock();
	void unlock();
	int islocked() { return locked; }
	void close();
	bool open();

	void setFile(int handle);

	void keyPressed(const eRCKey &key)
	{
		/*emit*/ keyEvent(key);
	}
	
	void addDevice(const std::string &id, eRCDevice *dev);
	void removeDevice(const std::string &id);
	eRCDevice *getDevice(const std::string &id);
	std::map<std::string,eRCDevice*,lstr> &getDevices();
	
	static eRCInput *getInstance() { return instance; }
	
	eRCConfig config;
};

#endif
