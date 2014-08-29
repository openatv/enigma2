#ifndef __FB_H
#define __FB_H

#include <lib/base/eerror.h>
#include <linux/fb.h>

// #define DEBUG_FB

class fbClass
{
	int fbFd;
	int xRes, yRes, stride, bpp;
	int available;
	struct fb_var_screeninfo screeninfo;
	fb_cmap cmap;
	__u16 red[256], green[256], blue[256], trans[256];
	static fbClass *instance;
	int locked;

	int m_manual_blit;
	int m_number_of_pages;
	int m_phys_mem;
#ifdef SWIG
	fbClass(const char *fb="/dev/fb0");
	~fbClass();
public:
#else
public:
	unsigned char *lfb;
	void enableManualBlit();
	void disableManualBlit();
	int showConsole(int state);
	int SetMode(int xRes, int yRes, int bpp);
	void getMode(int &xres, int &yres, int &bpp);
	int Available() {
#ifdef DEBUG_FB
		eDebug("[fbClass] %s", __FUNCTION__);
#endif
		return available;
	}
	
	int getNumPages() {
#ifdef DEBUG_FB
		eDebug("[fbClass] %s", __FUNCTION__);
#endif
		return m_number_of_pages;
	}
	
	unsigned long getPhysAddr() {
#ifdef DEBUG_FB
		eDebug("[fbClass] %s", __FUNCTION__);
#endif
		return m_phys_mem;
	}
	
	int setOffset(int off);
	int waitVSync();
	void blit();
	unsigned int Stride() {
#ifdef DEBUG_FB
		eDebug("[fbClass] %s", __FUNCTION__);
#endif
		return stride;
	}
	fb_cmap *CMAP() {
#ifdef DEBUG_FB
		eDebug("[fbClass] %s", __FUNCTION__);
#endif
		return &cmap;
	}

	fbClass(const char *fb="/dev/fb0");
	~fbClass();
	
			// low level gfx stuff
	int PutCMAP();
#endif
	static fbClass *getInstance();

	int lock();
	void unlock();
	int islocked() {
#ifdef DEBUG_FB
		eDebug("[fbClass] %s", __FUNCTION__);
#endif
		return locked;
	}
};

#endif
