#ifndef __lib_gui_epositiongauge_h
#define __lib_gui_epositiongauge_h

#include <lib/gui/ewidget.h>
#include <set>

typedef long long pts_t;

enum { CUT_TYPE_NONE = -1, CUT_TYPE_IN, CUT_TYPE_OUT, CUT_TYPE_MARK, CUT_TYPE_LAST };

class ePixmap;

class ePositionGauge: public eWidget
{
public:
	ePositionGauge(eWidget *parent);
	~ePositionGauge();
	void setLength(const pts_t &len);
	void setPosition(const pts_t &pos);

	void setInColor(const gRGB &color); /* foreground? */
	void setPointer(int which, gPixmap *pixmap, const ePoint &center);
	void setPointer(int which, ePtr<gPixmap> &pixmap, const ePoint &center);

	void setInOutList(SWIG_PYOBJECT(ePyObject) list);
	void setForegroundColor(const gRGB &col);
	void setCutMark(const pts_t &where, int what);

	void enableSeekPointer(int enable);
	void setSeekPosition(const pts_t &pos);

#ifndef SWIG
protected:
	int event(int event, void *data=0, void *data2=0);
private:
	void updatePosition();
	enum ePositionGaugeEvent
	{
		evtChangedPosition = evtUserWidget
	};
	ePixmap *m_point_widget, *m_seek_point_widget;
	ePoint m_point_center, m_seek_point_center;

	pts_t m_position, m_length, m_seek_position;
	int m_pos, m_seek_pos;

	pts_t m_cut_where;
	int m_cut_what;

		/* TODO: this is duplicated code from lib/service/servicedvb.h */
	struct cueEntry
	{
		pts_t where;
		unsigned int what;

		bool operator < (const struct cueEntry &o) const
		{
			return where < o.where;
		}
		cueEntry(const pts_t &where, unsigned int what) :
			where(where), what(what)
		{
		}
	};

	std::multiset<cueEntry> m_cue_entries;
	int scale(const pts_t &val);

	int m_have_foreground_color;
	gRGB m_foreground_color;
#endif
};

#endif
