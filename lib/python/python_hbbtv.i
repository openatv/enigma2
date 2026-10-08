%immutable eHbbtv::playServiceRequest;
%immutable eHbbtv::playStreamRequest;
%immutable eHbbtv::pauseStreamRequest;
%immutable eHbbtv::stopStreamRequest;
%immutable eHbbtv::nextServiceRequest;
%immutable eHbbtv::prevServiceRequest;
%immutable eHbbtv::setVolumeRequest;
%immutable eHbbtv::setVideoWindowRequest;
%immutable eHbbtv::unsetVideoWindowRequest;
%immutable eHbbtv::aitInvalidated;
%immutable eHbbtv::redButtonAppplicationReady;
%immutable eHbbtv::textApplicationReady;
%immutable eHbbtv::createApplicationRequest;
%immutable eHbbtv::show;
%immutable eHbbtv::hide;

/*
 * python_hbbtv.i is intentionally small, but it can be included before
 * enigma_python.i declares the generic PSignal typemaps.  Without these local
 * typemaps Python receives opaque PSignal* wrapper objects and signal.connect()
 * is not available.
 */
%typemap(out) PSignal0<void> {
	$1 = $input->get();
}

%typemap(out) PSignal1<void, const char *> {
	$1 = $input->get();
}

%typemap(out) PSignal1<void, int> {
	$1 = $input->get();
}

%typemap(out) PSignal4<void, int, int, int, int> {
	$1 = $input->get();
}

/*
 * Keep the native C++ method for ABI compatibility:
 *
 *   std::list<std::pair<std::string, std::string> > getApplicationIdsAndName();
 *
 * The Dream NPAPI/OIPF bridge may call that C++ ABI directly.
 * Python, however, needs an actually iterable object.  Without this override
 * SWIG returns an opaque std::list pointer object.
 */
%rename(_getApplicationIdsAndNameNative) eHbbtv::getApplicationIdsAndName;

%include <lib/hbbtv/oipfapplication.h>
%include <lib/hbbtv/hbbtv.h>

%extend eHbbtv {
	PyObject *getApplicationIdsAndName()
	{
		std::list<std::pair<std::string, std::string> > apps = $self->getApplicationIdsAndName();
		PyObject *list = PyList_New(0);
		if (!list)
			return NULL;

		for (std::list<std::pair<std::string, std::string> >::const_iterator it = apps.begin(); it != apps.end(); ++it)
		{
			PyObject *tuple = Py_BuildValue("(ss)", it->first.c_str(), it->second.c_str());
			if (!tuple)
			{
				Py_DECREF(list);
				return NULL;
			}
			PyList_Append(list, tuple);
			Py_DECREF(tuple);
		}
		return list;
	}
}
