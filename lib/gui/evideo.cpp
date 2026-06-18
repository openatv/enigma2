#include <lib/base/cfile.h>
#include <lib/gui/evideo.h>
#include <lib/gui/ewidgetdesktop.h>
#include <unistd.h>
#include <fcntl.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>

ePtr<eTimer> eVideoWidget::fullsizeTimer;
int eVideoWidget::pendingFullsize = 0;
int eVideoWidget::posFullsizeLeft = 0;
int eVideoWidget::posFullsizeTop = 0;
int eVideoWidget::posFullsizeWidth = 0;
int eVideoWidget::posFullsizeHeight = 0;

eVideoWidget::eVideoWidget(eWidget *parent)
	:eLabel(parent), m_fb_size(720, 576), m_state(0), m_decoder(1)
{
	if (!fullsizeTimer)
	{
		fullsizeTimer = eTimer::create(eApp);
		fullsizeTimer->timeout.connect(sigc::bind(sigc::ptr_fun(&eVideoWidget::setFullsize), false));
	}
	parent->setPositionNotifyChild(1);
}

int eVideoWidget::event(int event, void *data, void *data2)
{
	switch (event)
	{
	case evtChangedPosition:
	case evtParentChangedPosition:
		m_state &= ~1;
		updatePosition(!isVisible());
		break;
	case evtChangedSize:
		m_state |= 2;
		updatePosition(!isVisible());
		break;
	case evtParentVisibilityChanged:
		updatePosition(!isVisible());
		break;
	}
	return eLabel::event(event, data, data2);
}

eVideoWidget::~eVideoWidget()
{
	updatePosition(1);
}

void eVideoWidget::setFBSize(eSize size)
{
	m_fb_size = size;
}

static inline bool aml_has_axis()
{
#ifdef DREAMNEXTGEN
	return access("/sys/class/video/axis", W_OK) == 0;
#else
	return false;
#endif
}

// robust desktop size: device_resolution → display/mode → fb0 (fix triple height)
static inline void aml_get_desktop_size(int &dw, int &dh)
{
	dw = 1920; dh = 1080;

	// 1) /sys/class/video/device_resolution e.g. "1920x1080" or "1920x1080p60hz"
	{
		int fd = open("/sys/class/video/device_resolution", O_RDONLY);
		if (fd >= 0)
		{
			char buf[64] = {0};
			int n = read(fd, buf, sizeof(buf)-1); close(fd);
			if (n > 0)
			{
				char *x = strchr(buf, 'x');
				if (x)
				{
					*x = 0;
					int W = atoi(buf);
					char *p = x + 1;
					while (*p && (*p < '0' || *p > '9')) ++p; // skip non-digits (handles "...p60hz")
					int H = atoi(p);
					if (W > 0 && H > 0) { dw = W; dh = H; return; }
				}
			}
		}
	}

	// 2) /sys/class/display/mode e.g. "1080p60hz"
	{
		int fd = open("/sys/class/display/mode", O_RDONLY);
		if (fd >= 0)
		{
			char buf[32] = {0};
			int n = read(fd, buf, sizeof(buf)-1); close(fd);
			if (n > 0)
			{
				if (!strncmp(buf, "480", 3))  { dw = 720;  dh = 480;  return; }
				if (!strncmp(buf, "576", 3))  { dw = 720;  dh = 576;  return; }
				if (!strncmp(buf, "720", 3))  { dw = 1280; dh = 720;  return; }
				if (!strncmp(buf, "1080",4))  { dw = 1920; dh = 1080; return; }
				if (!strncmp(buf, "2160",4))  { dw = 3840; dh = 2160; return; }
				if (!strncmp(buf, "4320",4))  { dw = 7680; dh = 4320; return; }
			}
		}
	}

	// 3) /sys/class/graphics/fb0/virtual_size e.g. "1920,3240" → fix 3240 (1080*3)
	{
		int fd = open("/sys/class/graphics/fb0/virtual_size", O_RDONLY);
		if (fd >= 0)
		{
			char buf[64] = {0};
			int n = read(fd, buf, sizeof(buf)-1); close(fd);
			if (n > 0)
			{
				int W = 0, H = 0;
				if (sscanf(buf, "%d,%d", &W, &H) == 2 && W > 0 && H > 0)
				{
					if (H >= 2*576 && (H % 3) == 0) H /= 3; // common triple-buffer height
					dw = W; dh = H;
				}
			}
		}
	}
}

// write axis with L,T,W,H (converted to L T R B)
static inline void aml_write_axis(const char *path, int L, int T, int W, int H)
{
	int R = L + (W > 0 ? W : 1) - 1;
	int B = T + (H > 0 ? H : 1) - 1;
	char buf[64];
	int fd = open(path, O_WRONLY | O_TRUNC);
	if (fd >= 0)
	{
		int n = snprintf(buf, sizeof(buf), "%d %d %d %d", L, T, R, B);
		if (n > 0) (void)write(fd, buf, n);
		close(fd);
	}
}

// helper: enable/disable planes (0 = main, 1 = PiP)
static inline void aml_enable_plane(int index, bool enable)
{
	const char *path = (index == 0)
		? "/sys/class/video/disable_video"
		: "/sys/class/video/disable_videopip";
	int fd = open(path, O_WRONLY | O_TRUNC);
	if (fd >= 0) {
		const char *v = enable ? "0" : "1"; // 0 = enabled, 1 = disabled
		(void)write(fd, v, 1);
		close(fd);
	}
}

void eVideoWidget::setFullScreenPosition(eRect pos)
{
	posFullsizeLeft = pos.left();
	posFullsizeTop = pos.top();
	posFullsizeWidth = pos.width();
	posFullsizeHeight = pos.height();

	// Apply immediately, scaling for AML so "full screen" really fills the desktop.
	if (aml_has_axis())
	{
		int dw, dh; aml_get_desktop_size(dw, dh);
		int L = posFullsizeLeft   * dw / (m_fb_size.width()  ? m_fb_size.width()  : 720);
		int T = posFullsizeTop    * dh / (m_fb_size.height() ? m_fb_size.height() : 576);
		int W = posFullsizeWidth  * dw / (m_fb_size.width()  ? m_fb_size.width()  : 720);
		int H = posFullsizeHeight * dh / (m_fb_size.height() ? m_fb_size.height() : 576);
		setPosition(0, L, T, W, H);
	}
	else
	{
		setPosition(0, posFullsizeLeft, posFullsizeTop, posFullsizeWidth, posFullsizeHeight);
	}
}

void eVideoWidget::writeProc(const std::string &filename, int value)
{
	CFile f(filename.c_str(), "w");
	if (f)
		fprintf(f, "%08x\n", value);
}

void eVideoWidget::setPosition(int index, int left, int top, int width, int height)
{
	if (aml_has_axis())
	{
		// index 0 = main, 1 = PiP
		const char *path = (index == 0) ? "/sys/class/video/axis"
		                                : "/sys/class/video/axis_pip";
		aml_write_axis(path, left, top, width, height);
		return;
	}

	// default: legacy /proc interface
	char filenamebase[128];
	snprintf(filenamebase, sizeof(filenamebase), "/proc/stb/vmpeg/%d/dst_", index);
	std::string filename = filenamebase;
	writeProc(filename + std::string("left"), left);
	writeProc(filename + std::string("top"), top);
	writeProc(filename + std::string("width"), width);
	writeProc(filename + std::string("height"), height);
	writeProc(filename + std::string("apply"), 1);
}

void eVideoWidget::setFullsize(bool force)
{
	// AML: only make MAIN fullscreen, don't touch PiP here
	if (aml_has_axis())
	{
		// main plane (decoder 0)
		if (force || (pendingFullsize & (1 << 0)))
		{
			int dw, dh; aml_get_desktop_size(dw, dh);
			aml_enable_plane(0, true);
			aml_write_axis("/sys/class/video/axis", 0, 0, dw, dh);
			pendingFullsize &= ~(1 << 0);
		}

		// PiP: clear pending without resizing (UI controls it explicitly)
		if (force || (pendingFullsize & (1 << 1)))
			pendingFullsize &= ~(1 << 1);

		return;
	}

	// Legacy path unchanged
	for (int decoder = 0; decoder < 2; ++decoder)
	{
		if (force || (pendingFullsize & (1 << decoder)))
		{
			eVideoWidget::setPosition(decoder,
				posFullsizeLeft, posFullsizeTop,
				posFullsizeWidth, posFullsizeHeight);
			pendingFullsize &= ~(1 << decoder);
		}
	}
}

void eVideoWidget::restoreFullsize()
{
	if (aml_has_axis())
		setFullsize(true);
}

void eVideoWidget::updatePosition(int disable)
{
	int left = 0, top = 0, width = 0, height = 0;
	if (!disable)
		m_state |= 4;

	if (disable && !(m_state & 4))
	{
		return;
	}

	if ((m_state & 2) != 2)
	{
		return;
	}

	eRect pos(0,0,0,0);
	if (!disable)
		pos = eRect(getAbsolutePosition(), size());
	else
		m_state &= ~4;

	if (!disable && m_state & 8 && pos == m_user_rect)
	{
		return;
	}

	if (!(m_state & 1))
	{
		m_user_rect = pos;
		m_state |= 1;
	}

	if (aml_has_axis())
	{
		// On AML, /sys/class/video/axis{,_pip} expect real desktop pixels.
		// Scale from the widget's FB space (usually 720x576) to desktop size.
		int dw, dh; aml_get_desktop_size(dw, dh);
		if (dw <= 0) dw = 1920;
		if (dh <= 0) dh = 1080;
		left   = pos.left()   * dw / m_fb_size.width();
		top    = pos.top()    * dh / m_fb_size.height();
		width  = pos.width()  * dw / m_fb_size.width();
		height = pos.height() * dh / m_fb_size.height();
	}
	else
	{
		// Legacy SoCs keep using the 720x576 destination space.
		left   = pos.left()   * 720 / m_fb_size.width();
		top    = pos.top()    * 576 / m_fb_size.height();
		width  = pos.width()  * 720 / m_fb_size.width();
		height = pos.height() * 576 / m_fb_size.height();
	}

	if (!disable)
	{
		setPosition(m_decoder, left, top, width, height);
		pendingFullsize &= ~(1 << m_decoder);
		m_state |= 8;
	}
	else
	{
		m_state &= ~8;
		pendingFullsize |= (1 << m_decoder);
		fullsizeTimer->start(100, true);
	}
}

void eVideoWidget::setDecoder(int decoder)
{
	m_decoder = decoder;
}

void eVideoWidget::setOverscan(bool overscan)
{
	m_overscan = overscan;
}
