#include <lib/gdi/gmaindc.h>

gMainDC *gMainDC::m_instance;

ePtr<gMainDC> NewgMainDCPtr(void)
{
	ePtr<gMainDC> ptr;
	gMainDC::getInstance(ptr);
	return ptr;
}

gMainDC::gMainDC()
{
	ASSERT(m_instance == 0);
	m_instance = this;
}

gMainDC::gMainDC(gPixmap *pixmap) : gDC(pixmap)
{
	ASSERT(m_instance == 0);
	m_instance = this;
}

gMainDC::~gMainDC()
{
	m_instance = 0;
}

int gMainDC::getGraphicsLogicalWidth() const
{
	return m_pixmap ? m_pixmap->size().width() : 0;
}

int gMainDC::getGraphicsLogicalHeight() const
{
	return m_pixmap ? m_pixmap->size().height() : 0;
}

std::string gMainDC::getOSDAxis() const
{
	int width = getGraphicsLogicalWidth();
	int height = getGraphicsLogicalHeight();
	if (width <= 0 || height <= 0) {
		width = 720;
		height = 576;
	}
	return "0 0 " + std::to_string(width) + " " + std::to_string(height);
}
