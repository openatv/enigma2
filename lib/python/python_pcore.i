%extend pNavigation {
PyObject *getRecordings(bool simulate, pNavigation::RecordType type=pNavigation::isAnyRecording)
{
	std::vector<ePtr<iRecordableService> > recordings;
	self->getRecordings(recordings, simulate, type);
	ePyObject result = PyList_New(recordings.size());
	for (unsigned int i = 0; i < recordings.size(); i++)
		PyList_SET_ITEM(result, i, NEW_iRecordableServicePtr(recordings[i])); 
	return result;
}
PyObject *getRecordingsServicesOnly(pNavigation::RecordType type=pNavigation::isAnyRecording)
{
	std::vector<eServiceReference> services;
	self->getRecordingsServicesOnly(services, type);
	ePyObject result = PyList_New(services.size());
	for (unsigned int i = 0; i < services.size(); i++)
		PyList_SET_ITEM(result, i, PyString_FromString(services[i].toString().c_str()));
	return result;
}
PyObject *getRecordingsTypesOnly(pNavigation::RecordType type=pNavigation::isAnyRecording)
{
	std::vector<pNavigation::RecordType> returnedTypes;
	self->getRecordingsTypesOnly(returnedTypes, type);
	ePyObject result = PyList_New(returnedTypes.size());
	for (unsigned int i = 0; i < returnedTypes.size(); i++)
		PyList_SET_ITEM(result, i, PyInt_FromLong(int(returnedTypes[i])));
	return result;
}
PyObject *getRecordingsServicesAndTypes(pNavigation::RecordType type=pNavigation::isAnyRecording)
{
	std::vector<pNavigation::RecordType> returnedTypes;
	std::vector<eServiceReference> services;
	self->getRecordingsTypesOnly(returnedTypes, type);
	self->getRecordingsServicesOnly(services, type);
	ePyObject l = PyList_New(0);
	for (unsigned int i = 0; i < services.size(); i++)
	{
		ePyObject tuple = PyTuple_New(2);
		PyTuple_SET_ITEM(tuple, 0, PyString_FromString(services[i].toString().c_str()));
		PyTuple_SET_ITEM(tuple, 1, PyInt_FromLong(int(returnedTypes[i])));
		PyList_Append(l, tuple);
		Py_DECREF(tuple);
	}
	return l;
}
};

%ignore pNavigation::getRecordings;
%ignore pNavigation::getRecordingsServicesOnly;
%ignore pNavigation::getRecordingsTypesOnly;
