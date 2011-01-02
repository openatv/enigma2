#ifndef __lib_driver_rcsdl_h
#define __lib_driver_rcsdl_h

#include <lib/driver/rc.h>

#include <SDL.h>

class eSDLInputDevice : public eRCDevice
{
private:
	bool m_escape;
	unsigned int m_unicode;
	int translateKey(SDLKey key);

public:
	eSDLInputDevice(eRCDriver *driver);
	~eSDLInputDevice();

	virtual void handleCode(long arg);
	virtual const char *getDescription() const;
};

class eSDLInputDriver : public eRCDriver
{
private:
	static eSDLInputDriver *instance;

public:
	eSDLInputDriver();
	~eSDLInputDriver();

	static eSDLInputDriver *getInstance() { return instance; }

	void keyPressed(const SDL_KeyboardEvent *key);
};

#endif
