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

