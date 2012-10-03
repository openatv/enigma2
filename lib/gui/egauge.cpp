#include <lib/gui/egauge.h>
#include <math.h>


eGauge::eGauge(eWidget *parent)
	:eWidget(parent), m_have_border_color(false)
{

}

void eGauge::setBorderColor(const gRGB &color)
{
	m_border_color=color;
	m_have_border_color=true;
	invalidate();
}

int eGauge::event(int event, void *data, void *data2)
{
	switch (event)
	{
	case evtPaint:
	{
		ePtr<eWindowStyle> style;

		eSize s(size());

		gPainter &painter = *(gPainter*)data2;

		gRGB pal[256];
		pal[0] = 0;
		pal[1] = 0xff0000;
		pal[2] = 0xffFFff;
		pal[3] = 0x00ff00;
	
		for (int a=0; a<0x10; ++a)
			pal[a | 0x10] = (0x111111 * a) | 0xFF;
		painter.setPalette(pal, 0, 256);

		if (m_have_border_color) {
			painter.setBackgroundColor(gColor(1));
			painter.setForegroundColor(gColor(1));
		} else  {
			painter.setBackgroundColor(gColor(2));
			painter.setForegroundColor(gColor(2));
		}

		painter.line(ePoint(basex, basey), ePoint(endx, endy));
		painter.line(ePoint(basex, (basey -1)), ePoint(endx, endy));
		painter.line(ePoint(basex, (basey +1)), ePoint(endx, endy));
		painter.line(ePoint((basex -1), basey), ePoint(endx, endy));
		painter.line(ePoint((basex +1), basey), ePoint(endx, endy));
		if(basex < endx)
			painter.line(ePoint(basex, basey), ePoint((endx -1), endy));
		if(basex > endx)
			painter.line(ePoint(basex, basey), ePoint((endx +1), endy));
		if(basey > endy)
			painter.line(ePoint(basex, basey), ePoint(endx, (endy -1)));
		if(basey < endy)
			painter.line(ePoint(basex, basey), ePoint(endx, (endy +1)));


		return 0;
	}
	case evtChangedGauge:
	{
		
		int mystart = 0;
		int perc = m_value;

		basex = size().width() >> 1;
		basey = size().height() >> 1;
		double angle = (double) mystart + (double) perc * (double)(360 - (mystart<<1)) / 100.0;
		double rads  = angle*M_PI/180;
		
		endx = basex + (int) (sin(rads) * (double)(size().width())/2.0);
		endy = basey - (int) (cos(rads) * (double)(size().height())/2.0);

		invalidate();
		
		return 0;
	}
	default:
		return eWidget::event(event, data, data2);
	}
}

void eGauge::setValue(int value)
{
	m_value = value;
	event(evtChangedGauge);
}
