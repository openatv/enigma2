#include <lib/gui/ewindow.h>
#include <lib/gui/ewidgetdesktop.h>

#include <lib/gui/ewindowstyle.h>

eWindow::eWindow(eWidgetDesktop *desktop): eWidget(0)
{
	setStyle(new eWindowStyleSimple());

		/* we are the parent for the child window. */
		/* as we are in the constructor, this is thread safe. */
	m_child = this;
	m_child = new eWidget(this);
	desktop->addRootWidget(this, 0);
}

eWindow::~eWindow()
{
	getDesktop()->removeRootWidget(this);
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
		ePtr<eWindowStyle> style;
		if (!getStyle(style))
		{
			const eSize &new_size = *static_cast<eSize*>(data);
//			eDebug("eWindow::evtWillChangeSize to %d %d", new_size.width(), new_size.height());
			style->handleNewSize(this, new_size);
		}
		break;
	}
	case evtPaint:
	{
		ePtr<eWindowStyle> style;
		if (!getStyle(style))
		{
			gPainter &painter = *static_cast<gPainter*>(data2);
			style->paintWindowDecoration(this, painter, m_title);
		} else
			eDebug("no style :(");
		return 0;
	}
	default:
		break;
	}
	return eWidget::event(event, data, data2);
}

