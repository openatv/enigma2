%module enigma
%{
#define SWIG_COMPILE
#include <lib/base/smartptr.h>
#include <lib/base/eerror.h>
#include <lib/base/econfig.h>
#include <lib/service/iservice.h>
#include <lib/service/service.h>

#include <lib/gui/ewidget.h>
#include <lib/gui/elabel.h>
#include <lib/gui/ebutton.h>
#include <lib/gui/ewindow.h>
#include <lib/gui/ewidgetdesktop.h>
#include <lib/gui/eslider.h>
#include <lib/python/connections.h>
%}

#define DEBUG
%include "stl.i"
%include <lib/base/object.h>
%include <lib/base/eerror.h>
%include <lib/base/econfig.h>
%include <lib/base/smartptr.h>
%include <lib/service/iservice.h>
%include <lib/service/service.h>
%template(eServiceCenterPtr) ePtr<eServiceCenter>;

%immutable eButton::selected;

%include <lib/gdi/epoint.h>
%include <lib/gdi/erect.h>
%include <lib/gdi/esize.h>
%include <lib/gdi/region.h>
%include <lib/gui/ewidget.h>
%include <lib/gui/elabel.h>
%include <lib/gui/ebutton.h>
%include <lib/gui/ewindow.h>
%include <lib/gui/eslider.h>
%include <lib/gui/ewidgetdesktop.h>

template<class R> class PSignal0
{
public:
	PyObject *get();
};

template<class R, class P0> class PSignal1
{
public:
	PyObject *get();
};

template<class R, class P0, class P1> class PSignal2
{
public:
	PyObject *get();
};

%template(PSignal1VI) PSignal1<void,int>;

%typemap(out) PSignal1VI {
	$1 = $input->get();
}

%template(PSignal0V) PSignal0<void>;

%typemap(out) PSignal0V {
	$1 = $input->get();
}

