%extend pNavigation {
PyObject *getRecordings(bool simulate)
{
	std::vector<ePtr<iRecordableService> > recordings;
	self->getRecordings(recordings, simulate);
	ePyObject result = PyList_New(recordings.size());
	for (unsigned int i = 0; i < recordings.size(); i++)
		PyList_SET_ITEM(result, i, NEW_iRecordableServicePtr(recordings[i])); 
	return result;
}
};

%ignore pNavigation::getRecordings;
