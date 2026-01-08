#ifndef __lib_gui_epixmap_h
#define __lib_gui_epixmap_h

#include <lib/gui/ewidget.h>
#include <vector>

class ePixmap : public eWidget {
	int m_alphatest;
	int m_scale;

public:
	ePixmap(eWidget* parent);
	~ePixmap();

	void setPixmap(gPixmap* pixmap);
	void setPixmap(ePtr<gPixmap>& pixmap);
	void setPixmapFromFile(const char* filename, bool autoDetect = false);
	void setAlphatest(int alphatest); /* 1 for alphatest, 2 for alphablend */
	void setScale(int scale); // DEPRECATED
	void setPixmapScale(int flags);
	void setPixmapScaleFlags(int flags) { setPixmapScale(flags); } // DEPRECATED

	void setAniPixmapFromFile(const char* filename, bool autostart = false);
	void startAnimation(bool once = false);
	void stopAnimation() { m_animTimer->stop(); }
	eSize getPixmapSize() const { return (m_pixmap) ? m_pixmap->size() : eSize(0, 0); }

protected:
	ePtr<gPixmap> m_pixmap;
	int event(int event, void* data = 0, void* data2 = 0);
	void checkSize();

	std::string getClassName() const override { return std::string("ePixmap"); }

private:
	std::vector<ePtr<gPixmap>> m_frames;
	std::vector<int> m_delays;
	int m_currentFrame = 0;
	bool m_playOnce = false;
	ePtr<eTimer> m_animTimer;
	void nextFrame();

	enum eLabelEvent {
		evtChangedPixmap = evtUserWidget,
	};
};

#endif
