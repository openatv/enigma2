%{
#include <lib/python/swig.h>
#include <lib/python/python_helpers.h>
%}

%extend iServiceInformation {
PyObject *getInfoObject(int w)
{
	switch (w)
	{
		case iServiceInformation::sTransponderData:
		{
			ePyObject ret = PyDict_New();
			if (ret)
			{
				ePtr<iDVBTransponderData> data = self->getTransponderData();
				transponderDataToDict(ret, data);
			}
			return ret;
		}
		case iServiceInformation::sFileSize:
			return PyLong_FromLongLong(self->getFileSize());
	}
	Py_INCREF(Py_None);
	return Py_None;
}
};

%ignore iServiceInformation::getInfoObject;

%extend iStaticServiceInformation {
PyObject *getInfoObject(const eServiceReference &ref, int w)
{
	Py_INCREF(Py_None);
	return Py_None;
}
};

%ignore iStaticServiceInformation::getInfoObject;

%extend iStreamableService {
PyObject *getStreamingData()
{
	ePyObject ret = PyDict_New();
	if (ret)
	{
		ePtr<iStreamData> data = self->getStreamingData();
		streamingDataToDict(ret, data);
	}
	return ret;
}
};

%ignore iStreamableService::getStreamingData;

%extend iFrontendInformation {
PyObject *getFrontendData()
{
	ePyObject ret = PyDict_New();
	if (ret)
	{
		ePtr<iDVBFrontendData> data = self->getFrontendData();
		frontendDataToDict(ret, data);
	}
	return ret;
}

PyObject *getFrontendStatus()
{
	ePyObject ret = PyDict_New();
	if (ret)
	{
		ePtr<iDVBFrontendStatus> status = self->getFrontendStatus();
		frontendStatusToDict(ret, status);
	}
	return ret;
}

PyObject *getTransponderData(bool original)
{
	ePyObject ret = PyDict_New();
	if (ret)
	{
		ePtr<iDVBTransponderData> data = self->getTransponderData(original);
		transponderDataToDict(ret, data);
	}
	return ret;
}

PyObject *getAll(bool original)
{
	ePyObject ret = PyDict_New();
	if (ret)
	{
		ePtr<iDVBFrontendData> data = self->getFrontendData();
		frontendDataToDict(ret, data);
		ePtr<iDVBFrontendStatus> status = self->getFrontendStatus();
		frontendStatusToDict(ret, status);
		ePtr<iDVBTransponderData> tpdata = self->getTransponderData(original);
		transponderDataToDict(ret, tpdata);
	}
	return ret;
}
};

%ignore iFrontendInformation::getFrontendData;
%ignore iFrontendInformation::getFrontendStatus;
%ignore iFrontendInformation::getTransponderData;
%ignore iFrontendInformation::getAll;

%ignore iStreamData;
%ignore iDVBFrontendStatus;
%ignore iDVBTransponderData;
%ignore iDVBFrontendData;
