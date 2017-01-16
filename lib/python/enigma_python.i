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
#include <lib/base/eenv.h>
#include <lib/base/eerror.h>
#include <lib/base/etpm.h>
#include <lib/base/message.h>
#include <lib/base/e2avahi.h>
#include <lib/driver/rc.h>
#include <lib/driver/rcinput_swig.h>
#include <lib/service/event.h>
#include <lib/service/iservice.h>
#include <lib/service/service.h>
#include <lib/service/servicedvb.h>
#include <lib/gdi/fb.h>
#include <lib/gdi/font.h>
#include <lib/gdi/gpixmap.h>
#include <lib/gdi/gfbdc.h>
#include <lib/gdi/grc.h>
#include <lib/gdi/gmaindc.h>
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
#include <lib/gui/epositiongauge.h>
#include <lib/gui/egauge.h>
#include <lib/gui/evideo.h>
#include <lib/gui/ecanvas.h>
#include <lib/python/connections.h>
#include <lib/python/pythonconfig.h>
#include <lib/gui/elistbox.h>
#include <lib/gui/elistboxcontent.h>
#include <lib/gui/esubtitle.h>
#include <lib/service/listboxservice.h>
#include <lib/nav/core.h>
#include <lib/actions/action.h>
#include <lib/gdi/gfont.h>
#include <lib/gdi/epng.h>
#include <lib/dvb/db.h>
#include <lib/dvb/frontendparms.h>
#include <lib/dvb/idvb.h>
#include <lib/dvb/dvb.h>
#include <lib/dvb/frontend.h>
#include <lib/dvb/volume.h>
#include <lib/dvb/sec.h>
#include <lib/dvb/epgcache.h>
#include <lib/dvb/dvbtime.h>
#include <lib/dvb/pmt.h>
#include <lib/dvb/cahandler.h>
#include <lib/dvb/fastscan.h>
#include <lib/dvb/cablescan.h>
#include <lib/dvb/encoder.h>
#include <lib/dvb/streamserver.h>
#include <lib/components/scan.h>
#include <lib/components/file_eraser.h>
#include <lib/components/tuxtxtapp.h>
#include <lib/driver/avswitch.h>
#include <lib/driver/hdmi_cec.h>
#include <lib/driver/rfmod.h>
#include <lib/driver/misc_options.h>
#include <lib/driver/etimezone.h>
#include <lib/gdi/lcd.h>
#include <lib/mmi/mmi_ui.h>
#include <lib/dvb_ci/dvbci.h>
#include <lib/dvb_ci/dvbci_ui.h>
#include <lib/python/python.h>
#include <lib/python/python_helpers.h>
#include <lib/gdi/picload.h>
%}

%feature("ref")   iObject "$this->AddRef(); /* eDebug(\"AddRef (%s:%d)!\", __FILE__, __LINE__); */ "
%feature("unref") iObject "$this->Release(); /* eDebug(\"Release! %s:%d\", __FILE__, __LINE__); */ "

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
   "$result = t_output_helper($result, ((*$1) ? SWIG_NewPointerObj((void*)($1), $1_descriptor, 1) : (delete $1, Py_INCREF(Py_None), Py_None)));"
%enddef


#define DEBUG
typedef long time_t;
%include "typemaps.i"
%include "std_string.i"
%include <lib/python/swig.h>
%include <lib/base/object.h>
%include <lib/base/eenv.h>
%include <lib/base/eerror.h>

%include <lib/python/python_dvb.i>
%include <lib/python/python_service.i>
%include <lib/python/python_pmt.i>
%include <lib/python/python_pcore.i>

%immutable eSocketNotifier::activated;
%include <lib/base/ebase.h>
%include <lib/base/smartptr.h>
%include <lib/service/event.h>
%include <lib/service/iservice.h>
%include <lib/service/service.h>
%include <lib/base/e2avahi.h>

// TODO: embed these...
%immutable ePicLoad::PictureData;
%immutable eButton::selected;
%immutable eInput::changed;
%immutable eComponentScan::statusChanged;
%immutable eComponentScan::newService;
%immutable eFastScan::scanProgress;
%immutable eFastScan::scanCompleted;
%immutable eCableScan::scanProgress;
%immutable eCableScan::scanCompleted;
%immutable pNavigation::m_event;
%immutable pNavigation::m_record_event;
%immutable eListbox::selectionChanged;
%immutable eDVBCI_UI::ciStateChanged;
%immutable eSocket_UI::socketStateChanged;
%immutable eDVBResourceManager::frontendUseMaskChanged;
%immutable eAVSwitch::vcr_sb_notifier;
%immutable eHdmiCEC::messageReceived;
%immutable eHdmiCEC::addressChanged;
%immutable ePythonMessagePump::recv_msg;
%immutable eDVBLocalTimeHandler::m_timeUpdated;
%immutable iCryptoInfo::clientname;
%immutable iCryptoInfo::clientinfo;
%immutable iCryptoInfo::verboseinfo;
%immutable iCryptoInfo::usedcaid;
%immutable iCryptoInfo::decodetime;
%immutable iCryptoInfo::usedcardid;
%immutable eTuxtxtApp::appClosed;
%immutable iDVBChannel::receivedTsidOnid;
%include <lib/base/message.h>
%include <lib/base/etpm.h>
%include <lib/driver/rc.h>
%include <lib/driver/rcinput_swig.h>
%include <lib/gdi/fb.h>
%include <lib/gdi/font.h>
%include <lib/gdi/gpixmap.h>
%include <lib/gdi/gfbdc.h>
%include <lib/gdi/gmaindc.h>
%include <lib/gdi/epoint.h>
%include <lib/gdi/erect.h>
%include <lib/gdi/esize.h>
%include <lib/gui/ewidget.h>
%include <lib/gui/elabel.h>
%include <lib/gui/einput.h>
%include <lib/gui/einputstring.h>
%include <lib/gui/einputnumber.h>
%include <lib/gui/epixmap.h>
%include <lib/gui/ecanvas.h>
%include <lib/gui/ebutton.h>
%include <lib/gui/ewindow.h>
%include <lib/gui/eslider.h>
%include <lib/gui/epositiongauge.h>
%include <lib/gui/egauge.h>
%include <lib/gui/ewidgetdesktop.h>
%include <lib/gui/elistbox.h>
%include <lib/gui/elistboxcontent.h>
%include <lib/gui/ewindowstyle.h>
%include <lib/gui/ewindowstyleskinned.h>
%include <lib/gui/ewidgetanimation.h>
%include <lib/gui/evideo.h>
%include <lib/gui/esubtitle.h>
%include <lib/service/listboxservice.h>
%include <lib/nav/core.h>
%include <lib/actions/action.h>
%include <lib/gdi/gfont.h>
%include <lib/gdi/epng.h>
%include <lib/dvb/volume.h>
%include <lib/dvb/sec.h>
%include <lib/dvb/epgcache.h>
%include <lib/dvb/frontendparms.h>
%include <lib/dvb/dvbtime.h>
%include <lib/dvb/idvb.h>
%include <lib/dvb/dvb.h>
%include <lib/dvb/frontend.h>
%include <lib/dvb/pmt.h>
%include <lib/dvb/cahandler.h>
%include <lib/dvb/fastscan.h>
%include <lib/dvb/cablescan.h>
%include <lib/components/scan.h>
%include <lib/components/file_eraser.h>
%include <lib/components/tuxtxtapp.h>
%include <lib/driver/avswitch.h>
%include <lib/driver/hdmi_cec.h>
%include <lib/driver/rfmod.h>
%include <lib/driver/misc_options.h>
%include <lib/driver/etimezone.h>
%include <lib/gdi/lcd.h>
%include <lib/mmi/mmi_ui.h>
%include <lib/dvb_ci/dvbci.h>
%include <lib/dvb_ci/dvbci_ui.h>
%include <lib/dvb/db.h>
%include <lib/python/python.h>
%include <lib/python/pythonconfig.h>
%include <lib/gdi/picload.h>
%include <lib/dvb/streamserver.h>
/**************  eptr  **************/

/**************  signals  **************/

template<class R> class PSignal0
{
public:
	PyObject *get();
};

%template(PSignal0V) PSignal0<void>;

%typemap(out) PSignal0V {
	$1 = $input->get();
}

template<class R, class P0> class PSignal1
{
public:
	PyObject *get();
};

%template(PSignal1VI) PSignal1<void,int>;
%template(PSignal1VS) PSignal1<void,const char *c>;

%typemap(out) PSignal1VI {
	$1 = $input->get();
}

%typemap(out) PSignal1VS {
	$1 = $input->get();
}

%template(PSignal1VoidICECMessage) PSignal1<void,ePtr<iCECMessage>&>;

%typemap(out) PSignal1VoidICECMessage {
	$1 = $input->get();
}

template<class R, class P0, class P1> class PSignal2
{
public:
	PyObject *get();
};

%template(PSignal2VoidIRecordableServiceInt) PSignal2<void,ePtr<iRecordableService>&,int>;

%typemap(out) PSignal2VoidIRecordableServiceInt {
	$1 = $input->get();
}

%template(PSignal2VII) PSignal2<void,int,int>;

%typemap(out) PSignal2VII {
	$1 = $input->get();
}

%{
RESULT SwigFromPython(ePtr<gPixmap> &result, PyObject *obj)
{	
	ePtr<gPixmap> *res;

	res = 0;
	result = 0;
#ifndef SWIGTYPE_p_ePtrT_gPixmap_t
#define SWIGTYPE_p_ePtrT_gPixmap_t SWIGTYPE_p_ePtrTgPixmap_t
#endif
	if (SWIG_Python_ConvertPtr(obj, (void **)&res, SWIGTYPE_p_ePtrT_gPixmap_t, SWIG_POINTER_EXCEPTION | 0))
		return -1;
	if (!res)
		return -1;
	result = *res;
	return 0;
}
PyObject *New_eServiceReference(const eServiceReference &ref)
{
    eServiceReference *result = new eServiceReference(ref);
    return SWIG_NewPointerObj((void*)(result), SWIGTYPE_p_eServiceReference, 1);
}
PyObject *New_iRecordableServicePtr(const ePtr<iRecordableService> &ptr)
{
    ePtr<iRecordableService> *result = new ePtr<iRecordableService>(ptr);
#ifndef SWIGTYPE_p_ePtrT_iRecordableService_t
#define SWIGTYPE_p_ePtrT_iRecordableService_t SWIGTYPE_p_ePtrTiRecordableService_t
#endif
    return SWIG_NewPointerObj((void*)(result), SWIGTYPE_p_ePtrT_iRecordableService_t, 1);
}
PyObject *New_iCECMessagePtr(const ePtr<iCECMessage> &ptr)
{
    ePtr<iCECMessage> *result = new ePtr<iCECMessage>(ptr);
#ifndef SWIGTYPE_p_ePtrT_iCECMessage_t
#define SWIGTYPE_p_ePtrT_iCECMessage_t SWIGTYPE_p_ePtrTiCECMessage_t
#endif
    return SWIG_NewPointerObj((void*)(result), SWIGTYPE_p_ePtrT_iCECMessage_t, 1);
}
%}

/* needed for service groups */

PyObject *getBestPlayableServiceReference(const eServiceReference &bouquet_ref, const eServiceReference &ignore, bool simulate=false);
%{
PyObject *getBestPlayableServiceReference(const eServiceReference &bouquet_ref, const eServiceReference &ignore, bool simulate=false)
{
	eStaticServiceDVBBouquetInformation info;
	if (info.isPlayable(bouquet_ref, ignore, simulate))
		return New_eServiceReference(info.getPlayableService());
	Py_INCREF(Py_None);
	return Py_None;
}
%}

void setTunerTypePriorityOrder(int);
%{
void setTunerTypePriorityOrder(int order)
{
	eDVBFrontend::setTypePriorityOrder(order);
}
%}

void setPreferredTuner(int);
%{
void setPreferredTuner(int index)
{
	eDVBFrontend::setPreferredFrontend(index);
}
%}

void setSpinnerOnOff(int);
%{
void setSpinnerOnOff(int onoff)
{
	gRC *rc = gRC::getInstance();
	if (rc) rc->setSpinnerOnOff(onoff);
}
%}

void setEnableTtCachingOnOff(int);
%{
void setEnableTtCachingOnOff(int onoff)
{
	eTuxtxtApp *tt = eTuxtxtApp::getInstance();
	if (tt) tt->setEnableTtCachingOnOff(onoff);
}
%}

int getUsedEncoderCount();
%{
int getUsedEncoderCount()
{
	eEncoder *encoders = eEncoder::getInstance();
	if (encoders) return encoders->getUsedEncoderCount();
	return 0;
}
%}

int getLinkedSlotID(int);
%{
int getLinkedSlotID(int fe)
{
        eFBCTunerManager *mgr = eFBCTunerManager::getInstance();
        if (mgr) return mgr->getLinkedSlotID(fe);
        return -1;
}
%}

bool isFBCLink(int);
%{
bool isFBCLink(int fe)
{
        eFBCTunerManager *mgr = eFBCTunerManager::getInstance();
        if (mgr) return mgr->isFBCLink(fe);
        return false;
}
%}

/************** temp *****************/

	/* need a better place for this, i agree. */
%{
extern void runMainloop();
extern void quitMainloop(int exit_code);
extern eApplication *getApplication();
extern int getPrevAsciiCode();
extern void addFont(const char *filename, const char *alias, int scale_factor, int is_replacement, int renderflags = 0);
extern const char *getEnigmaVersionString();
extern const char *getGStreamerVersionString();
extern void dump_malloc_stats(void);
#ifndef HAVE_OSDANIMATION
extern void setAnimation_current(int a);
extern void setAnimation_speed(int speed);
#endif
%}

extern void addFont(const char *filename, const char *alias, int scale_factor, int is_replacement, int renderflags = 0);
extern int getPrevAsciiCode();
extern void runMainloop();
extern void quitMainloop(int exit_code);
extern eApplication *getApplication();
extern const char *getEnigmaVersionString();
extern const char *getGStreamerVersionString();
extern void dump_malloc_stats(void);
#ifndef HAVE_OSDANIMATION
extern void setAnimation_current(int a);
extern void setAnimation_speed(int speed);
#endif

%include <lib/python/python_console.i>
%include <lib/python/python_base.i>
