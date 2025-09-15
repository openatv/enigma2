#ifndef __lib_gui_erectangle_h
#define __lib_gui_erectangle_h

#include <lib/gui/ewidget.h>

class eRectangle : public eWidget {
public:
	eRectangle(eWidget* parent);


protected:
	int event(int event, void* data = 0, void* data2 = 0);

	std::string getClassName() const override { return std::string("eRectangle"); }
};

#endif
