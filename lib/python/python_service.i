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
				if (data)
				{
					transponderDataToDict(ret, data);
				}
			}
			return ret;
		}
		case iServiceInformation::sFileSize:
			return PyLong_FromLongLong(self->getFileSize());
		case iServiceInformation::sCAIDs:
		{
			ePyObject ret;
			std::vector<int> caids, ecmpids;
			self->getCaIds(caids, ecmpids);
			int cnt = caids.size();

			ret = PyList_New(cnt);

			for (unsigned int i = 0; i < cnt; i++)
			{
				PyList_SET_ITEM(ret, i, PyInt_FromLong(caids[i]));
			}
			return ret;
		}
		case iServiceInformation::sCAIDPIDs:
		{
			ePyObject ret;
			std::vector<int> caids, ecmpids;
			self->getCaIds(caids, ecmpids);
			int cnt = caids.size();

			ret = PyList_New(cnt);

			for (unsigned int i = 0; i < cnt; i++)
			{
				ePyObject tuple = PyTuple_New(2);
				PyTuple_SET_ITEM(tuple, 0, PyInt_FromLong(caids[i]));
				PyTuple_SET_ITEM(tuple, 1, PyInt_FromLong(ecmpids[i]));
				PyList_SET_ITEM(ret, i, tuple);
			}
			return ret;
		}
		case iServiceInformation::sUser + 6: /* DVD audio info */
		{
			ePyObject tuple = PyTuple_New(3);
			if (tuple)
			{
				ePtr<iServiceInfoContainer> info = self->getInfoObject(w);
				if (info)
				{
					PyTuple_SetItem(tuple, 0, PyInt_FromLong(info->getInteger(0)));
					PyTuple_SetItem(tuple, 1, PyString_FromString(info->getString(0).c_str()));
					PyTuple_SetItem(tuple, 2, PyString_FromString(info->getString(1).c_str()));
				}
			}
			return tuple;
		}
		case iServiceInformation::sUser + 7: /* DVD subtitle info */
		{
			ePyObject tuple = PyTuple_New(2);
			if (tuple)
			{
				ePtr<iServiceInfoContainer> info = self->getInfoObject(w);
				if (info)
				{
					PyTuple_SetItem(tuple, 0, PyInt_FromLong(info->getInteger(0)));
					PyTuple_SetItem(tuple, 1, PyString_FromString(info->getString(0).c_str()));
				}
			}
			return tuple;
		}
		case iServiceInformation::sUser + 8: /* DVD angle info */
		{
			ePyObject tuple = PyTuple_New(2);
			if (tuple)
			{
				ePtr<iServiceInfoContainer> info = self->getInfoObject(w);
				if (info)
				{
					PyTuple_SetItem(tuple, 0, PyInt_FromLong(info->getInteger(0)));
					PyTuple_SetItem(tuple, 1, PyInt_FromLong(info->getInteger(1)));
				}
			}
			return tuple;
		}
		default: /* servicemp3 objects, either buffer or double */
		{
			ePtr<iServiceInfoContainer> info = self->getInfoObject(w);
			if (info)
			{
				unsigned char *data;
				unsigned int size;
				data = info->getBuffer(size);
				if (data && size)
				{
					return PyBuffer_FromMemory(data, size);
				}
				else
				{
					return PyFloat_FromDouble(info->getDouble(0));
				}
			}
			break;
		}
	}
	Py_INCREF(Py_None);
	return Py_None;
}
};

%ignore iServiceInformation::getInfoObject;

%extend iStaticServiceInformation {
PyObject *getInfoObject(const eServiceReference &ref, int w)
{
	switch (w)
	{
		case iServiceInformation::sTransponderData:
		{
			ePyObject ret = PyDict_New();
			if (ret)
			{
				ePtr<iDVBTransponderData> data = self->getTransponderData(ref);
				if (data)
				{
					transponderDataToDict(ret, data);
				}
			}
			return ret;
		}
		case iServiceInformation::sFileSize:
			return PyLong_FromLongLong(self->getFileSize(ref));
	}
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
		if (data)
		{
			streamingDataToDict(ret, data);
		}
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
		if (data)
		{
			frontendDataToDict(ret, data);
		}
	}
	return ret;
}

PyObject *getFrontendStatus()
{
	ePyObject ret = PyDict_New();
	if (ret)
	{
		ePtr<iDVBFrontendStatus> status = self->getFrontendStatus();
		if (status)
		{
			frontendStatusToDict(ret, status);
		}
	}
	return ret;
}

PyObject *getTransponderData(bool original)
{
	ePyObject ret = PyDict_New();
	if (ret)
	{
		ePtr<iDVBTransponderData> data = self->getTransponderData(original);
		if (data)
		{
			transponderDataToDict(ret, data);
		}
	}
	return ret;
}

PyObject *getAll(bool original)
{
	ePyObject ret = PyDict_New();
	if (ret)
	{
		ePtr<iDVBFrontendData> data = self->getFrontendData();
		if (data)
		{
			frontendDataToDict(ret, data);
		}
		ePtr<iDVBFrontendStatus> status = self->getFrontendStatus();
		if (status)
		{
			frontendStatusToDict(ret, status);
		}
		ePtr<iDVBTransponderData> tpdata = self->getTransponderData(original);
		if (tpdata)
		{
			transponderDataToDict(ret, tpdata);
		}
	}
	return ret;
}
};

%ignore iFrontendInformation::getFrontendData;
%ignore iFrontendInformation::getFrontendStatus;
%ignore iFrontendInformation::getTransponderData;
%ignore iFrontendInformation::getAll;

%extend iStreamedService {
PyObject *getBufferCharge()
{
	ePyObject tuple = PyTuple_New(5);
	if (tuple)
	{
		ePtr<iStreamBufferInfo> info = self->getBufferCharge();
		if (info)
		{
			PyTuple_SET_ITEM(tuple, 0, PyInt_FromLong(info->getBufferPercentage()));
			PyTuple_SET_ITEM(tuple, 1, PyInt_FromLong(info->getAverageInputRate()));
			PyTuple_SET_ITEM(tuple, 2, PyInt_FromLong(info->getAverageOutputRate()));
			PyTuple_SET_ITEM(tuple, 3, PyInt_FromLong(info->getBufferSpace()));
			PyTuple_SET_ITEM(tuple, 4, PyInt_FromLong(info->getBufferSize()));
		}
	}
	return tuple;
}
};

%ignore iStreamedService::getBufferCharge;

%ignore iStreamData;
%ignore iServiceInfoContainer;
%ignore iDVBFrontendStatus;
%ignore iDVBTransponderData;
%ignore iDVBFrontendData;
%ignore iStreamBufferInfo;
