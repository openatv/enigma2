#ifndef __lib_gui_evideo_h
#define __lib_gui_evideo_h

#include <lib/gui/elabel.h>

class eVideoWidget: public eLabel
{
	eSize m_fb_size;
	int m_state;
	eRect m_user_rect;
	int m_decoder;
	bool m_overscan;
	static ePtr<eTimer> fullsizeTimer;
	static int pendingFullsize;
	static int posFullsizeLeft;
	static int posFullsizeTop;
	static int posFullsizeWidth;
	static int posFullsizeHeight;

public:
	eVideoWidget(eWidget *parent);
	~eVideoWidget();
	void setDecoder(int target);
	void setOverscan(bool overscan);
	void setFBSize(eSize size);
	void setFullScreenPosition(eRect pos);
	static void setFullsize(bool force = false);
protected:
	int event(int event, void *data=0, void *data2=0);
	void updatePosition(int disable = 0);
	static void writeProc(const std::string &filename, int value);
	static void setPosition(int index, int left, int top, int width, int height);
};

#endif
