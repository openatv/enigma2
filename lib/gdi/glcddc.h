#ifndef DISABLE_LCD

#ifndef __glcddc_h
#define __glcddc_h

#include "grc.h"

class eLCD;

class gLCDDC: public gPixmapDC
{
	eLCD *lcd;
	static gLCDDC *instance;
	int update;
	void exec(gOpcode *opcode);
public:
	gLCDDC(eLCD *lcd);
	~gLCDDC();
	void setUpdate(int update);
	static gLCDDC *getInstance();
};


#endif

#endif //DISABLE_LCD
