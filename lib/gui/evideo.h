#ifndef __lib_gui_evideo_h
#define __lib_gui_evideo_h

#include <lib/gui/elabel.h>

class eVideoWidget: public eLabel
{
	eSize m_fb_size;
	int m_state;
	eRect m_user_rect;
	int m_decoder;
public:
	eVideoWidget(eWidget *parent);
	~eVideoWidget();
	void setDecoder(int target);
	void setFBSize(eSize size);
protected:
	int event(int event, void *data=0, void *data2=0);
	void updatePosition(int disable = 0);
};

#endif
