#include <lib/gui/ewindow.h>
#include <lib/gui/ewidgetdesktop.h>

#include <lib/gui/ewindowstyle.h>

eWindow::eWindow(eWidgetDesktop *desktop): eWidget(0)
{
	m_child = new eWidget(this);
	desktop->addRootWidget(this, 0);
	
	m_style = new eWindowStyleSimple();
}

void eWindow::setTitle(const std::string &string)
{
	if (m_title == string)	
		return;
	m_title = string;
	event(evtTitleChanged);
}

int eWindow::event(int event, void *data, void *data2)
{
	switch (event)
	{
	case evtWillChangeSize:
	{
		const eSize &new_size = *static_cast<eSize*>(data);
		eDebug("eWindow::evtWillChangeSize to %d %d", new_size.width(), new_size.height());
		if (m_style)
			m_style->handleNewSize(this, new_size);
		break;
	}
	case evtPaint:
	{
		gPainter &painter = *static_cast<gPainter*>(data2);
		painter.setBackgroundColor(gColor(0x18));
		painter.clear();
		break;
	}
	default:
		break;
	}
	return eWidget::event(event, data, data2);
}

