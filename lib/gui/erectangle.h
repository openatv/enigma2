#ifndef __lib_gui_erectangle_h
#define __lib_gui_erectangle_h

#include <lib/gui/ewidget.h>

class eRectangle : public eWidget {
public:
	eRectangle(eWidget* parent);

protected:
	std::string getClassName() const override { return std::string("eRectangle"); }
};

#endif
