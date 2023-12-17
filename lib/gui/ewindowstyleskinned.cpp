#include <lib/base/eerror.h>
#include <lib/gdi/esize.h>
#include <lib/gui/ewindow.h>
#include <lib/gui/ewindowstyle.h>
#include <lib/gui/ewindowstyleskinned.h>

DEFINE_REF(eWindowStyleSkinned);

eWindowStyleSkinned::eWindowStyleSkinned()
{
	// TODO: initialize colors!!

	m_color[colForeground] = gRGB(0xFFFFFF);
	m_color[colScrollbarForeground] = gRGB(0xFFFFFF);
	m_color[colScrollbarBorder] = gRGB(0xFFFFFF);
	m_color[colWindowTitleForeground] = gRGB(0xFFFFFF);
	m_color[colSliderForeground] = gRGB(0xFFFFFF);
	m_color[colSliderBorder] = gRGB(0xFFFFFF);

	m_labelfnt = new gFont("Regular", 12);
	m_listboxfnt = new gFont("Regular", 20);
	m_entryfnt = new gFont("Regular", 20);
	m_valuefnt = new gFont(m_entryfnt->family, m_entryfnt->pointSize - m_entryfnt->pointSize/5);

}

void eWindowStyleSkinned::handleNewSize(eWindow *wnd, eSize &size, eSize &offset)
{
//	eDebug("[eWindowStyleSkinned] handle new size: %d x %d", size.width(), size.height());

	size = eSize(
			size.width() + m_border[bsWindow].m_border_left + m_border[bsWindow].m_border_right,
			size.height() + m_border[bsWindow].m_border_top + m_border[bsWindow].m_border_bottom
		);

	offset = eSize(-m_border[bsWindow].m_border_left, -m_border[bsWindow].m_border_top);

	eWidget *child = wnd->child();

	wnd->m_clip_region = eRect(ePoint(0, 0), size);

	child->move(ePoint(m_border[bsWindow].m_border_left, m_border[bsWindow].m_border_top));
	child->resize(eSize(size.width() - m_border[bsWindow].m_border_left - m_border[bsWindow].m_border_right, size.height() - m_border[bsWindow].m_border_top - m_border[bsWindow].m_border_bottom));
}

void eWindowStyleSkinned::paintWindowDecoration(eWindow *wnd, gPainter &painter, const std::string &title)
{
	drawBorder(painter, eRect(ePoint(0, 0), wnd->size()), m_border[bsWindow], bpAll, 0);

	if (m_fnt)
	{
		painter.setBackgroundColor(m_color[colWindowTitleBackground]);
		painter.setForegroundColor(m_color[colWindowTitleForeground]);
		painter.setFont(m_fnt);
		painter.renderText(eRect(m_title_offset.width(), m_title_offset.height(), wnd->size().width() - m_title_offset.width(), m_border[bsWindow].m_border_top - m_title_offset.height()), title);
	}
}

void eWindowStyleSkinned::paintBackground(gPainter &painter, const ePoint &offset, const eSize &size)
{
	painter.setBackgroundColor(m_color[colBackground]);
	painter.clear();
}

void eWindowStyleSkinned::setStyle(gPainter &painter, int what)
{
	switch (what)
	{
	case styleLabel:
		painter.setForegroundColor(m_color[colForeground]);
		break;
	case styleListboxSelected:
		painter.setForegroundColor(m_color[colListboxForegroundSelected]);
		painter.setBackgroundColor(m_color[colListboxBackgroundSelected]);
		break;
	case styleListboxNormal:
		painter.setForegroundColor(m_color[colListboxForeground]);
		painter.setBackgroundColor(m_color[colListboxBackground]);
		break;
	case styleListboxMarked:
		painter.setForegroundColor(m_color[colListboxForegroundMarked]);
		painter.setBackgroundColor(m_color[colListboxBackgroundMarked]);
		break;
	case styleListboxMarkedAndSelected:
		painter.setForegroundColor(m_color[colListboxForegroundMarkedSelected]);
		painter.setBackgroundColor(m_color[colListboxBackgroundMarkedSelected]);
		break;
	case styleScollbar:
		if (m_color[colScrollbarBackground].argb() != 0)
		{
			painter.setBackgroundColor(m_color[colScrollbarBackground]);
			painter.clear();
		}
		painter.setForegroundColor(m_color[colScrollbarForeground]);
		break;
	case styleScollbarBorder:
		painter.setForegroundColor(m_color[colScrollbarBorder]);
		break;
	case styleSlider:
		if (m_color[colSliderBackground].argb() != 0)
		{
			painter.setBackgroundColor(m_color[colSliderBackground]);
			painter.clear();
		}
		painter.setForegroundColor(m_color[colSliderForeground]);
		break;
	case styleSliderBorder:
		painter.setForegroundColor(m_color[colSliderBorder]);
		break;
	}

}

void eWindowStyleSkinned::drawFrame(gPainter &painter, const eRect &frame, int what)
{
	int bs;
	switch (what)
	{
	case frameButton:
		bs = bsButton;
		break;
	case frameListboxEntry:
		bs = bsListboxEntry;
		break;
	default:
		eWarning("[eWindowStyleSkinned] invalid frame style %d", what);
		return;
	}
	drawBorder(painter, frame, m_border[bs], bpAll, gPainter::BT_ALPHABLEND);
}

void eWindowStyleSkinned::drawBorder(gPainter &painter, const eRect &pos, struct borderSet &border, int what, int flags)
{
	int x = pos.left(), xm = pos.right();

	ePtr<gPixmap>
		&tl = border.m_pixmap[bpiTopLeft],
		&t  = border.m_pixmap[bpiTop],
		&tr = border.m_pixmap[bpiTopRight],
		&l  = border.m_pixmap[bpiLeft],
		&r  = border.m_pixmap[bpiRight],
		&bl = border.m_pixmap[bpiBottomLeft],
		&b  = border.m_pixmap[bpiBottom],
		&br = border.m_pixmap[bpiBottomRight];

	if (tl)
	{
		painter.blit(tl, ePoint(x, pos.top()), eRect(), flags);
		x += tl->size().width();
	}

	if (tr)
	{
		xm -= tr->size().width();
		painter.blit(tr, ePoint(xm, pos.top()), pos, flags);
	}

	if (t)
	{
		while (x < xm)
		{
			painter.blit(t, ePoint(x, pos.top()), eRect(x, pos.top(), xm - x, pos.height()), flags);
			x += t->size().width();
		}
	}

	x = pos.left();
	xm = pos.right();

	if (bl)
	{
		painter.blit(bl, ePoint(pos.left(), pos.bottom()-bl->size().height()), eRect(), flags);
		x += bl->size().width();
	}

	if (br)
	{
		xm -= br->size().width();
		painter.blit(br, ePoint(xm, pos.bottom()-br->size().height()), eRect(x, pos.bottom()-br->size().height(), pos.width() - x, bl->size().height()), flags);
	}

	if (b)
	{
		while (x < xm)
		{
			painter.blit(b, ePoint(x, pos.bottom()-b->size().height()), eRect(x, pos.bottom()-b->size().height(), xm - x, pos.height()), flags);
			x += b->size().width();
		}
	}

	int y = 0;
	if (tl)
		y = tl->size().height();

	y += pos.top();

	int ym = pos.bottom();
	if (bl)
		ym -= bl->size().height();

	if (l)
	{
		while (y < ym)
		{
			painter.blit(l, ePoint(pos.left(), y), eRect(pos.left(), y, pos.width(), ym - y), flags);
			y += l->size().height();
		}
	}

	y = 0;

	if (tr)
		y = tr->size().height();

	y += pos.top();

	ym = pos.bottom();
	if (br)
		ym -= br->size().height();

	if (r)
	{
		while (y < ym)
		{
			painter.blit(r, ePoint(pos.right() - r->size().width(), y), eRect(pos.right()-r->size().width(), y, r->size().width(), ym - y), flags);
			y += r->size().height();
		}
	}
}

RESULT eWindowStyleSkinned::getFont(int what, ePtr<gFont> &fnt)
{
	fnt = 0;
	switch (what)
	{
	case fontListbox:
		fnt = m_listboxfnt;
		break;
	case fontStatic:
		fnt = m_labelfnt;
		break;
	case fontEntry:
		fnt = m_entryfnt;
		break;
	case fontValue:
		fnt = m_valuefnt;
		break;
	case fontHeader:
		fnt = m_headerfnt ? m_headerfnt : m_entryfnt;
		break;
	case fontButton:
		fnt = new gFont("Regular", 20);
		break;
	case fontTitlebar:
		fnt = new gFont("Regular", 25);
		break;
	default:
		return -1;
	}
	return 0;
}

void eWindowStyleSkinned::setPixmap(int bs, int bp, ePtr<gPixmap> &ptr)
{
	setPixmap(bs, bp, *(ptr.operator->()));
}

void eWindowStyleSkinned::setPixmap(int bs, int bp, gPixmap &pixmap)
{
	if ((bs >= bsMax) || (bs < 0))
		return;

	int i = 0;
	for (int b = 1; b < bpMax; b <<= 1, ++i)
	{
		if (bp & b)
			m_border[bs].m_pixmap[i] = &pixmap;
	}

		/* recalc border sizes */
	m_border[bs].m_border_top = 0;
	m_border[bs].m_border_left = 0;
	m_border[bs].m_border_bottom = 0;
	m_border[bs].m_border_right = 0;

	for (int i = 0; i < 3; ++i)
		if (m_border[bs].m_pixmap[i])
			if (m_border[bs].m_border_top < m_border[bs].m_pixmap[i]->size().height())
				m_border[bs].m_border_top = m_border[bs].m_pixmap[i]->size().height();
	for (int i = 6; i < 9; ++i)
		if (m_border[bs].m_pixmap[i])
			if (m_border[bs].m_border_bottom < m_border[bs].m_pixmap[i]->size().height())
				m_border[bs].m_border_bottom = m_border[bs].m_pixmap[i]->size().height();

	if (m_border[bs].m_pixmap[3])
		m_border[bs].m_border_left = m_border[bs].m_pixmap[3]->size().width();
	else
		m_border[bs].m_border_left = 0;

	if (m_border[bs].m_pixmap[5])
		m_border[bs].m_border_right = m_border[bs].m_pixmap[5]->size().width();
	else
		m_border[bs].m_border_right = 0;

/*	eDebug("[eWindowStyleSkinned] recalced border size for %d: %d:%d %d:%d",
		bs,
		m_border[bs].m_border_left, m_border[bs].m_border_top,
		m_border[bs].m_border_right, m_border[bs].m_border_bottom);  */
}

void eWindowStyleSkinned::setColor(int what, const gRGB &col)
{
	if ((what < colMax) && (what >= 0))
		m_color[what] = col;
}

gRGB eWindowStyleSkinned::getColor(int what)
{
	if ((what < colMax) && (what >= 0))
		return m_color[what];
	return nullptr;
}

void eWindowStyleSkinned::setTitleOffset(const eSize &offset)
{
	m_title_offset = offset;
}

void eWindowStyleSkinned::setTitleFont(gFont *fnt)
{
	m_fnt = fnt;
}

void eWindowStyleSkinned::setLabelFont(gFont *fnt)
{
	m_labelfnt = fnt;
}

void eWindowStyleSkinned::setListboxFont(gFont *fnt)
{
	m_listboxfnt = fnt;
}

void eWindowStyleSkinned::setEntryFont(gFont *fnt)
{
	m_entryfnt = fnt;
}

void eWindowStyleSkinned::setValueFont(gFont *fnt)
{
	m_valuefnt = fnt;
}

void eWindowStyleSkinned::setHeaderFont(gFont *fnt)
{
	m_headerfnt = fnt;
}
