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

#include <lib/gdi/gpixmap.h>

#include <lib/gui/ewidget.h>
#include <lib/gui/elabel.h>
#include <lib/gui/einput.h>
#include <lib/gui/einputstring.h>
#include <lib/gui/einputnumber.h>
#include <lib/gui/epixmap.h>
#include <lib/gui/ebutton.h>
#include <lib/gui/ewindow.h>
#include <lib/gui/ewidgetdesktop.h>
#include <lib/gui/ewindowstyle.h>
#include <lib/gui/ewindowstyleskinned.h>
#include <lib/gui/ewidgetanimation.h>
#include <lib/gui/eslider.h>
#include <lib/python/connections.h>
#include <lib/gui/elistbox.h>
#include <lib/gui/elistboxcontent.h>
#include <lib/service/listboxservice.h>
#include <lib/components/scan.h>
#include <lib/nav/pcore.h>
#include <lib/actions/action.h>
#include <lib/gdi/gfont.h>
#include <lib/gdi/epng.h>
#include <lib/dvb/volume.h>
#include <lib/driver/avswitch.h>
#include <lib/driver/rfmod.h>

extern void runMainloop();
extern void quitMainloop();
extern void setLCD(const char *c);
extern void setLCDClock(const char *c);

extern PSignal1<void,int> &keyPressedSignal();
%}

%feature("ref")   iObject "$this->AddRef(); eDebug(\"AddRef (%s:%d)!\", __FILE__, __LINE__); "
%feature("unref") iObject "$this->Release(); eDebug(\"Release! %s:%d\", __FILE__, __LINE__); "


/* this magic allows smartpointer to be used as OUTPUT arguments, i.e. call-by-reference-styled return value. */

%define %typemap_output_simple(Type)
 %typemap(in,numinputs=0) Type *OUTPUT ($*1_ltype temp),
              Type &OUTPUT ($*1_ltype temp)
   "$1 = new Type;";
 %fragment("t_out_helper"{Type},"header",
     fragment="t_output_helper") {}
 %typemap(argout,fragment="t_out_helper"{Type}) Type *OUTPUT, Type &OUTPUT
   "$result = t_output_helper($result, (SWIG_NewPointerObj((void*)($1), $1_descriptor, 1)));"
%enddef

%define %typemap_output_ptr(Type)
 %typemap(in,numinputs=0) Type *OUTPUT ($*1_ltype temp),
              Type &OUTPUT ($*1_ltype temp)
   "$1 = new Type;";
 %fragment("t_out_helper"{Type},"header",
     fragment="t_output_helper") {}
 %typemap(argout,fragment="t_out_helper"{Type}) Type *OUTPUT, Type &OUTPUT
		// generate None if smartpointer is NULL
   "$result = t_output_helper($result, ((*$1) ? SWIG_NewPointerObj((void*)($1), $1_descriptor, 1) : (Py_INCREF(Py_None), Py_None)));"
%enddef


#define DEBUG
%include "typemaps.i"
%include "stl.i"
%include <lib/python/swig.h>
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
%immutable eInput::changed;
%immutable eComponentScan::statusChanged;
%immutable pNavigation::m_event;

%include <lib/gdi/epoint.h>
%include <lib/gdi/erect.h>
%include <lib/gdi/esize.h>
%include <lib/gdi/region.h>
%include <lib/gui/ewidget.h>
%include <lib/gui/elabel.h>
%include <lib/gui/einput.h>
%include <lib/gui/einputstring.h>
%include <lib/gui/einputnumber.h>
%include <lib/gui/epixmap.h>
%include <lib/gui/ebutton.h>
%include <lib/gui/ewindow.h>
%include <lib/gui/eslider.h>
%include <lib/gui/ewidgetdesktop.h>
%include <lib/gui/elistbox.h>
%include <lib/gui/elistboxcontent.h>
%include <lib/gui/ewindowstyle.h>
%include <lib/gui/ewindowstyleskinned.h>
%include <lib/gui/ewidgetanimation.h>
%include <lib/service/listboxservice.h>
%include <lib/components/scan.h>
%include <lib/nav/pcore.h>
%include <lib/actions/action.h>
%include <lib/gdi/gfont.h>
%include <lib/gdi/epng.h>
%include <lib/dvb/volume.h>
%include <lib/driver/avswitch.h>
%include <lib/driver/rfmod.h>

%include <lib/gdi/gpixmap.h>
/**************  eptr  **************/

%template(eActionMapPtr) ePtr<eActionMap>;
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
void setLCD(const char*);
void setLCDClock(const char*);
%immutable keyPressed;
PSignal1<void,int> &keyPressedSignal();

