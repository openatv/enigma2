#ifndef __glcddc_h
#define __glcddc_h

#include "grc.h"
#include <lib/gdi/lcd.h>

class gLCDDC: public gDC
{
	eLCD *lcd;
	static gLCDDC *instance;
	int update;
	void exec(const gOpcode *opcode);
	gUnmanagedSurface surface;
public:
	gLCDDC();
	~gLCDDC();
	void setUpdate(int update);
	static int getInstance(ePtr<gLCDDC> &ptr) { if (!instance) return -1; ptr = instance; return 0; }
	int islocked() const { return lcd->islocked(); }
};

#endif
