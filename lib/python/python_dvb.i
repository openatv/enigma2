%{
#include <lib/python/swig.h>
#include <lib/python/python_helpers.h>
%}

%extend iDVBFrontend {
void getFrontendStatus(PyObject *dest)
{
	ePyObject ret = dest;
	ePtr<iDVBFrontendStatus> status;
	self->getFrontendStatus(status);
	if (status)
	{
		frontendStatusToDict(ret, status);
	}
}

void getTransponderData(PyObject *dest, bool original)
{
	ePyObject ret = dest;
	ePtr<iDVBTransponderData> data;
	self->getTransponderData(data, original);
	if (data)
	{
		transponderDataToDict(ret, data);
	}
}

void getFrontendData(PyObject *dest)
{
	ePyObject ret = dest;
	ePtr<iDVBFrontendData> data;
	self->getFrontendData(data);
	if (data)
	{
		frontendDataToDict(ret, data);
	}
}
};

%ignore iDVBFrontend::getFrontendStatus;
%ignore iDVBFrontend::getTransponderData;
%ignore iDVBFrontend::getFrontendData;

%ignore iDVBFrontendStatus;
%ignore iDVBTransponderData;
%ignore iDVBFrontendData;
