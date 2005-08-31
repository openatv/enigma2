#ifndef __FB_H
#define __FB_H

#include <linux/fb.h>
#include <lib/base/eerror.h>

class fbClass
{
	int fd;
	unsigned int xRes, yRes, stride, bpp;
	int available;
	struct fb_var_screeninfo screeninfo, oldscreen;
	fb_cmap cmap;
	__u16 red[256], green[256], blue[256], trans[256];
	static fbClass *instance;
	int locked;
	
	int m_number_of_pages;
public:
	unsigned char *lfb;
	int showConsole(int state);
	int SetMode(unsigned int xRes, unsigned int yRes, unsigned int bpp);
	int Available() { return available; }
	
	int getNumPages() { return m_number_of_pages; }
	
	int setOffset(int off);
	int waitVSync();
	unsigned int Stride() { return stride; }
	fb_cmap *CMAP() { return &cmap; }

	fbClass(const char *fb="/dev/fb/0");
	~fbClass();
	
	static fbClass *getInstance();

				// low level gfx stuff
	int PutCMAP();

	int lock();
	void unlock();
	int islocked() { return locked; }
};

#endif
