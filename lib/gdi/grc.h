#ifndef __grc_h
#define __grc_h

/*
	gPainter ist die high-level version. die highlevel daten werden zu low level opcodes ueber
	die gRC-queue geschickt und landen beim gDC der hardwarespezifisch ist, meist aber auf einen
	gPixmap aufsetzt (und damit unbeschleunigt ist).
*/

#include <pthread.h>
#include <stack>
#include <list>

#include <string>
#include <lib/base/ringbuffer.h>
#include <lib/base/elock.h>
#include <lib/gdi/erect.h>
#include <lib/gdi/gpixmap.h>
#include <lib/gdi/region.h>

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
		
		setOffset,
		
		setClip, addClip, popClip,
		
		end,shutdown
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
			std::string text;
			int flags;
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
			ePoint position;
			int flags;
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
		
		struct psetOffset
		{
			ePoint value;
			int rel;
		} *setOffset;
	} parm;

	int flags;
};

		/* gRC is the singleton which controls the fifo and dispatches commands */
class gRC: public iObject
{
DECLARE_REF;
private:
	static gRC *instance;
	
	static void *thread_wrapper(void *ptr);
	pthread_t the_thread;
	void *thread();

	queueRingBuffer<gOpcode> queue;
public:
	eLock queuelock;
	gRC();
	virtual ~gRC();

	void submit(const gOpcode &o)
	{
		static int collected=0;
		queue.enqueue(o);
		collected++;
//		if (o.opcode==gOpcode::end||o.opcode==gOpcode::shutdown)
		{
			queuelock.unlock(collected);
#ifdef SYNC_PAINT
			thread();
#endif
			collected=0;
		}
	}

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

	void setFont(gFont *font);
	void renderText(const eRect &position, const std::string &string, int flags=0);
	void renderPara(eTextPara *para, ePoint offset=ePoint(0, 0));

	void fill(const eRect &area);
	void fill(const gRegion &area);
	
	void clear();
	
	void blit(gPixmap *pixmap, ePoint pos, const eRect &what=eRect(), int flags=0);

	void setPalette(gRGB *colors, int start=0, int len=256);
	void mergePalette(gPixmap *target);
	
	void line(ePoint start, ePoint end);

	void setOffset(ePoint abs);
	void moveOffset(ePoint rel);
	void resetOffset();
	
	void resetClip(const gRegion &clip);
	void clip(const gRegion &clip);
	void clippop();

	void flush();
};

class gDC: public iObject
{
DECLARE_REF;
protected:
	ePtr<gPixmap> m_pixmap;

	gColor m_foreground_color, m_background_color;
	ePtr<gFont> m_current_font;
	ePoint m_current_offset;
	
	std::stack<gRegion> m_clip_stack;
	gRegion m_current_clip;
	
public:
	virtual void exec(gOpcode *opcode);
	gDC(gPixmap *pixmap);
	gDC();
	virtual ~gDC();
	gRegion &getClip() { return m_current_clip; }
	int getPixmap(ePtr<gPixmap> &pm) { pm = m_pixmap; return 0; }
	gRGB getRGB(gColor col);
	virtual eSize getSize() { return m_pixmap->getSize(); }
};

#endif
