#ifndef __FB_H
#define __FB_H

#include <lib/base/eerror.h>
#include <linux/fb.h>
#if defined(__sh__)
	#include <linux/stmfb.h>
#endif

#ifndef FB_DEV
# define FB_DEV "/dev/fb0"
#endif

class fbClass
{
	int fbFd;
	int xRes, yRes, stride, bpp;
#if defined(__sh__)
	struct stmfbio_output_configuration outcfg;
	struct stmfbio_outputinfo outinfo;
	struct stmfbio_planeinfo planemode;
	struct stmfbio_var_screeninfo_ex infoex;

	int xResSc, yResSc;
	int topDiff, leftDiff, rightDiff, bottomDiff;
#endif
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
	fbClass(const char *fb=FB_DEV);
	~fbClass();
public:
#else
public:
	unsigned char *lfb;
#if not defined(__sh__)
	void enableManualBlit();
	void disableManualBlit();
	int showConsole(int state);
#endif
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

	fbClass(const char *fb=FB_DEV);
	~fbClass();

			// low level gfx stuff
	int PutCMAP();
#endif
	static fbClass *getInstance();
#if defined(__sh__)
	void clearFBblit();
	int getFBdiff(int ret);
	void setFBdiff(int top, int right, int left, int bottom);
#endif

	int lock();
	void unlock();
	int islocked() { return locked; }
};

#endif
