/*
  NOTE: you have two options when adding classes so that
  they are callable *from* python.
  
   - either you %include the header file
   - or you re-declare it
   
  In both cases, you must #include the required
  header file (i.e. the header file itself), otherwise
  enigma_python_wrap.cxx won't build.
  
	In case you import the whole header file,
	please make sure that no unimportant stuff
	is wrapped, as this makes the wrapper stuff
	much more complex and it can probably break 
	very easily because of missing typemaps etc.
	
	you could make use of dizzy macros to ensure
	that some stuff is left out when parsed as SWIG
	definitions, but be sure to not modify the binary 
	representation. DON'T USE #ifdef SWIG_COMPILE
	for leaving out stuff (unless you *really* know
	what you are doing,of course!). you WILL break it.
		
	The better way (with more work) is to re-declare
	the class. It won't be compiled, so you can
	leave out stuff as you like.



Oh, things like "operator= is private in this context" etc.
is usually caused by not marking PSignals as immutable. 
*/

%define RefCount(...)
%typemap(newfree) __VA_ARGS__ * { eDebug("adding ref"); $1->AddRef(); }
%extend __VA_ARGS__  { ~__VA_ARGS__() { eDebug("removing ref!"); self->Release(); } }
%ignore __VA_ARGS__::~__VA_ARGS__();
%enddef

%module enigma
%{
#define SWIG_COMPILE
#include <lib/base/ebase.h>
#include <lib/base/smartptr.h>
#include <lib/base/eerror.h>
#include <lib/base/econfig.h>
#include <lib/service/iservice.h>
#include <lib/service/service.h>
#include <lib/service/event.h>

#include <lib/gui/ewidget.h>
#include <lib/gui/elabel.h>
#include <lib/gui/ebutton.h>
#include <lib/gui/ewindow.h>
#include <lib/gui/ewidgetdesktop.h>
#include <lib/gui/eslider.h>
#include <lib/python/connections.h>
#include <lib/gui/elistbox.h>
#include <lib/gui/elistboxcontent.h>
#include <lib/service/listboxservice.h>
#include <lib/components/scan.h>
#include <lib/nav/pcore.h>
#include <lib/actions/action.h>

extern void runMainloop();
extern void quitMainloop();

extern PSignal1<void,int> &keyPressedSignal();
%}

RefCount(eListboxPythonStringContent)
RefCount(eListboxServiceContent)
RefCount(eComponentScan)

#define DEBUG
%include "typemaps.i"
%include "stl.i"
%include <lib/base/object.h>
%include <lib/base/eerror.h>
%include <lib/base/econfig.h>
%include <lib/base/smartptr.h>
%include <lib/service/iservice.h>
%include <lib/service/service.h>
%template(eServiceCenterPtr) ePtr<eServiceCenter>;
%include <lib/service/event.h>


// TODO: embed these...
%immutable eButton::selected;
%immutable eComponentScan::statusChanged;
%immutable pNavigation::m_event;

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
%include <lib/gui/elistbox.h>
%include <lib/gui/elistboxcontent.h>
%include <lib/service/listboxservice.h>
%include <lib/components/scan.h>
%include <lib/nav/pcore.h>
%include <lib/actions/action.h>

/**************  eptr  **************/

%template(eActionMapPtr) ePtr<eActionMap>;
RefCount(eActionMap)
%apply eActionMapPtr OUTPUT { eActionMapPtr &ptr }
%apply eActionMap* *OUTPUT { eActionMap **ptr }

/**************  signals  **************/

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


/**************  base  **************/

%immutable eTimer::timeout;

class eTimer
{
public:
	eTimer(eMainloop *context = eApp);
	PSignal0<void> timeout;

	void start(long msec, bool singleShot=false);
	void stop();
	void changeInterval(long msek);
};

/**************  debug  **************/

void runMainloop();
void quitMainloop();
%immutable keyPressed;
PSignal1<void,int> &keyPressedSignal();
