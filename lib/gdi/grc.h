#ifndef __grc_h
#define __grc_h

/*
	gPainter ist die high-level version. die highlevel daten werden zu low level opcodes ueber
	die gRC-queue geschickt und landen beim gDC der hardwarespezifisch ist, meist aber auf einen
	gPixmap aufsetzt (und damit unbeschleunigt ist).
*/

// for debugging use:
//#define SYNC_PAINT
#undef SYNC_PAINT

#include <pthread.h>
#include <stack>
#include <list>

#include <string>
#include <lib/base/elock.h>
#include <lib/base/message.h>
#include <lib/gdi/erect.h>
#include <lib/gdi/gpixmap.h>
#include <lib/gdi/region.h>
#include <lib/gdi/gfont.h>
#include <lib/gdi/compositing.h>

class eTextPara;

class gDC;
struct gOpcode
{
	enum Opcode
	{
		renderText,
		renderPara,
		setFont,

		fill, fillRegion, clear,
		blit,

		setPalette,
		mergePalette,

		line,

		setBackgroundColor,
		setForegroundColor,

		setBackgroundColorRGB,
		setForegroundColorRGB,

		setOffset,

		setClip, addClip, popClip,

		flush,

		waitVSync,
		flip,
		notify,

		enableSpinner, disableSpinner, incrementSpinner,

		shutdown,

		setCompositing,
		sendShow,
		sendHide,
#ifdef USE_LIBVUGLES2
		sendShowItem,
		setFlush,
		setView,
#endif
	} opcode;

	gDC *dc;
	union para
	{
		struct pfillRect
		{
			eRect area;
		} *fill;

		struct pfillRegion
		{
			gRegion region;
		} *fillRegion;

		struct prenderText
		{
			eRect area;
			char *text;
			int flags;
			int border;
			gRGB bordercolor;
		} *renderText;

		struct prenderPara
		{
			ePoint offset;
			eTextPara *textpara;
		} *renderPara;

		struct psetFont
		{
			gFont *font;
		} *setFont;

		struct psetPalette
		{
			gPalette *palette;
		} *setPalette;

		struct pblit
		{
			gPixmap *pixmap;
			int flags;
			eRect position;
			eRect clip;
		} *blit;

		struct pmergePalette
		{
			gPixmap *target;
		} *mergePalette;

		struct pline
		{
			ePoint start, end;
		} *line;

		struct psetClip
		{
			gRegion region;
		} *clip;

		struct psetColor
		{
			gColor color;
		} *setColor;

		struct psetColorRGB
		{
			gRGB color;
		} *setColorRGB;

		struct psetOffset
		{
			ePoint value;
			int rel;
		} *setOffset;

		gCompositingData *setCompositing;

		struct psetShowHideInfo
		{
			ePoint point;
			eSize size;
		} *setShowHideInfo;
#ifdef USE_LIBVUGLES2
		struct psetShowItemInfo
		{
			long dir;
			ePoint point;
			eSize size;
		} *setShowItemInfo;
		
		struct psetFlush
		{
			bool enable;
		} *setFlush;
		
		struct psetViewInfo
		{
			eSize size;
		} *setViewInfo;
#endif
	} parm;
};

#define MAXSIZE 2048

		/* gRC is the singleton which controls the fifo and dispatches commands */
class gRC: public iObject, public sigc::trackable
{
	DECLARE_REF(gRC);
	friend class gPainter;
	static gRC *instance;

#ifndef SYNC_PAINT
	static void *thread_wrapper(void *ptr);
	pthread_t the_thread;
	pthread_mutex_t mutex;
	pthread_cond_t cond;
#endif
	void *thread();

	gOpcode queue[MAXSIZE];
	int rp, wp;

	eFixedMessagePump<int> m_notify_pump;
	void recv_notify(const int &i);

	ePtr<gDC> m_spinner_dc;
	int m_spinner_enabled;

	int m_spinneronoff;

	void enableSpinner();
	void disableSpinner();

	ePtr<gCompositingData> m_compositing;

	int m_prev_idle_count;
public:
	gRC();
	virtual ~gRC();

	void submit(const gOpcode &o);

#ifdef CONFIG_ION
	void lock();
	void unlock();
#endif

	sigc::signal0<void> notify;

	void setSpinnerDC(gDC *dc) { m_spinner_dc = dc; }
	void setSpinnerOnOff(int onoff) { m_spinneronoff = onoff; }

	static gRC *getInstance();
};

	/* gPainter is the user frontend, which in turn sends commands through gRC */
class gPainter
{
	ePtr<gDC> m_dc;
	ePtr<gRC> m_rc;
	friend class gRC;

	gOpcode *beginptr;
	void begin(const eRect &rect);
	void end();
public:
	gPainter(gDC *dc, eRect rect=eRect());
	virtual ~gPainter();

	void setBackgroundColor(const gColor &color);
	void setForegroundColor(const gColor &color);

	void setBackgroundColor(const gRGB &color);
	void setForegroundColor(const gRGB &color);

	void setFont(gFont *font);
		/* flags only THESE: */
	enum
	{
			// todo, make mask. you cannot align both right AND center AND block ;)
		RT_HALIGN_BIDI = 0,  /* default */
		RT_HALIGN_LEFT = 1,
		RT_HALIGN_RIGHT = 2,
		RT_HALIGN_CENTER = 4,
		RT_HALIGN_BLOCK = 8,

		RT_VALIGN_TOP = 0,  /* default */
		RT_VALIGN_CENTER = 16,
		RT_VALIGN_BOTTOM = 32,

		RT_WRAP = 64
	};
	void renderText(const eRect &position, const std::string &string, int flags=0, gRGB bordercolor=gRGB(), int border=0);

	void renderPara(eTextPara *para, ePoint offset=ePoint(0, 0));

	void fill(const eRect &area);
	void fill(const gRegion &area);

	void clear();

	enum
	{
		BT_ALPHATEST = 1,
		BT_ALPHABLEND = 2,
		BT_SCALE = 4, /* will be automatically set by blitScale */
		BT_KEEP_ASPECT_RATIO = 8,
		BT_FIXRATIO = 8
	};

	void blit(gPixmap *pixmap, ePoint pos, const eRect &clip=eRect(), int flags=0);
	void blitScale(gPixmap *pixmap, const eRect &pos, const eRect &clip=eRect(), int flags=0, int aflags = BT_SCALE);

	void setPalette(gRGB *colors, int start=0, int len=256);
	void setPalette(gPixmap *source);
	void mergePalette(gPixmap *target);

	void line(ePoint start, ePoint end);

	void setOffset(ePoint abs);
	void moveOffset(ePoint rel);
	void resetOffset();

	void resetClip(const gRegion &clip);
	void clip(const gRegion &clip);
	void clippop();

	void waitVSync();
	void flip();
	void notify();
	void setCompositing(gCompositingData *comp);

	void flush();
	void sendShow(ePoint point, eSize size);
	void sendHide(ePoint point, eSize size);
#ifdef USE_LIBVUGLES2
	void sendShowItem(long dir, ePoint point, eSize size);
	void setFlush(bool val);
	void setView(eSize size);
#endif
};

class gDC: public iObject
{
	DECLARE_REF(gDC);
protected:
	ePtr<gPixmap> m_pixmap;

	gColor m_foreground_color, m_background_color;
	gRGB m_foreground_color_rgb, m_background_color_rgb;
	ePtr<gFont> m_current_font;
	ePoint m_current_offset;

	std::stack<gRegion> m_clip_stack;
	gRegion m_current_clip;

	ePtr<gPixmap> m_spinner_saved, m_spinner_temp;
	ePtr<gPixmap> *m_spinner_pic;
	eRect m_spinner_pos;
	int m_spinner_num, m_spinner_i;
public:
	virtual void exec(const gOpcode *opcode);
	gDC(gPixmap *pixmap);
	gDC();
	virtual ~gDC();
	gRegion &getClip() { return m_current_clip; }
	int getPixmap(ePtr<gPixmap> &pm) { pm = m_pixmap; return 0; }
	gRGB getRGB(gColor col);
	virtual eSize size() { return m_pixmap->size(); }
	virtual int islocked() const { return 0; }

	virtual void enableSpinner();
	virtual void disableSpinner();
	virtual void incrementSpinner();
	virtual void setSpinner(eRect pos, ePtr<gPixmap> *pic, int len);
};

#endif
