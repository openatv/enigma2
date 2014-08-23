#ifndef __FB_H
#define __FB_H

#include <lib/base/eerror.h>
#include <linux/fb.h>

class fbClass
{
	int fbFd;
	int xRes, yRes, stride, bpp;
	int available;
	struct fb_var_screeninfo screeninfo;
	fb_cmap cmap;
	uint16_t red[256], green[256], blue[256], trans[256];
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
	int Available() { return available; }

	int getNumPages() { return m_number_of_pages; }

	unsigned long getPhysAddr() { return m_phys_mem; }

	int setOffset(int off);
	int waitVSync();
	void blit();
	unsigned int Stride() { return stride; }
	fb_cmap *CMAP() { return &cmap; }

	fbClass(const char *fb="/dev/fb0");
	~fbClass();

			// low level gfx stuff
	int PutCMAP();
#endif
	static fbClass *getInstance();

	int lock();
	void unlock();
	int islocked() { return locked; }
};

#endif
