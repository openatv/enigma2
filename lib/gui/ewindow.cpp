#include <lib/gui/ewindow.h>
#include <lib/gui/ewidgetdesktop.h>

#include <lib/gui/ewindowstyle.h>
#include <lib/gui/ewindowstyleskinned.h>

#include <lib/gdi/epng.h>

eWindow::eWindow(eWidgetDesktop *desktop, int z): eWidget(0)
{
	m_flags = 0;
	m_desktop = desktop;
		/* ask style manager for current style */
	ePtr<eWindowStyleManager> mgr;
	eWindowStyleManager::getInstance(mgr);

	ePtr<eWindowStyle> style;
	if (mgr)
		mgr->getStyle(desktop->getStyleID(), style);

		/* when there is either no style manager or no style, revert to simple style. */
	if (!style)
		style = new eWindowStyleSimple();

	setStyle(style);

	setZPosition(z); /* must be done before addRootWidget */

		/* we are the parent for the child window. */
		/* as we are in the constructor, this is thread safe. */
	m_child = this;
	m_child = new eWidget(this);
	desktop->addRootWidget(this);
}

eWindow::~eWindow()
{
	m_desktop->removeRootWidget(this);
	m_child->destruct();
}

void eWindow::setTitle(const std::string &string)
{
	if (m_title == string)
		return;
	m_title = string;
	event(evtTitleChanged);
}

std::string eWindow::getTitle() const
{
	return m_title;
}

void eWindow::setBackgroundColor(const gRGB &col)
{
		/* set background color for child, too */
	eWidget::setBackgroundColor(col);
	m_child->setBackgroundColor(col);
}

void eWindow::setFlag(int flags)
{
	m_flags |= flags;
}

void eWindow::clearFlag(int flags)
{
	m_flags &= ~flags;
}

int eWindow::event(int event, void *data, void *data2)
{
	switch (event)
	{
	case evtWillChangeSize:
	{
		eSize &new_size = *static_cast<eSize*>(data);
		eSize &offset = *static_cast<eSize*>(data2);
		if (!(m_flags & wfNoBorder))
		{
			ePtr<eWindowStyle> style;
			if (!getStyle(style))
			{
//			eDebug("[eWindow] evtWillChangeSize to %d %d", new_size.width(), new_size.height());
				style->handleNewSize(this, new_size, offset);
			}
		} else
			m_child->resize(new_size);
		break;
	}
	case evtPaint:
	{
		if (!(m_flags & wfNoBorder))
		{
			ePtr<eWindowStyle> style;
			if (!getStyle(style))
			{
				gPainter &painter = *static_cast<gPainter*>(data2);
				style->paintWindowDecoration(this, painter, m_title);
			}
		}
		return 0;
	}
	case evtTitleChanged:
			/* m_visible_region contains, in contrast to m_visible_with_childs,
			   only the decoration. though repainting the whole decoration is bad,
			   repainting the whole window is even worse. */
		invalidate(m_visible_region);
		break;
	default:
		break;
	}
	return eWidget::event(event, data, data2);
}

