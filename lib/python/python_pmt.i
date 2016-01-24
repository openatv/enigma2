%extend eDVBServicePMTHandler {
PyObject *eDVBServicePMTHandler::getCaIds(bool pair)
{
	ePyObject ret;
	std::vector<int> caids, ecmpids;
	self->getCaIds(caids, ecmpids);
	unsigned int cnt = caids.size();

	ret = PyList_New(cnt);

	for (unsigned int i = 0; i < cnt; i++)
	{
		if (pair)
		{
			ePyObject tuple = PyTuple_New(2);
			PyTuple_SET_ITEM(tuple, 0, PyInt_FromLong(caids[i]));
			PyTuple_SET_ITEM(tuple, 1, PyInt_FromLong(ecmpids[i]));
			PyList_SET_ITEM(ret, i, tuple);
		}
		else
		{
			PyList_SET_ITEM(ret, i, PyInt_FromLong(caids[i]));
		}
	}

	return ret;
}
};

%ignore eDVBServicePMTHandler::getCaIds;
