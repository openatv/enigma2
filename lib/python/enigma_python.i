%module enigma
%{
#define SWIG_COMPILE
#include <lib/base/smartptr.h>
#include <lib/base/eerror.h>
#include <lib/base/econfig.h>
#include <lib/service/iservice.h>
#include <lib/service/service.h>
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
%template(iPlayableServicePtr) ePtr<iPlayableService>;
%template(iPauseableServicePtr) ePtr<iPauseableService>;
%template(iRecordableServicePtr) ePtr<iRecordableService>;
%template(iListableServicePtr) ePtr<iListableService>;
