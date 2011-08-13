%{
#include <lib/python/swig.h>
#include <lib/python/python_helpers.h>
%}

%extend iDVBFrontend {
void getFrontendStatus(ePyObject dest)
{
	ePtr<iDVBFrontendStatus> status;
	self->getFrontendStatus(status);
	frontendStatusToDict(dest, status);
}

void getTransponderData(ePyObject dest, bool original)
{
	ePtr<iDVBTransponderData> data;
	self->getTransponderData(data, original);
	transponderDataToDict(dest, data);
}

void getFrontendData(ePyObject dest)
{
	ePtr<iDVBFrontendData> data;
	self->getFrontendData(data);
	frontendDataToDict(dest, data);
}
};

%ignore iDVBFrontend::getFrontendStatus;
%ignore iDVBFrontend::getTransponderData;
%ignore iDVBFrontend::getFrontendData;

%ignore iDVBFrontendStatus;
%ignore iDVBTransponderData;
%ignore iDVBFrontendData;
