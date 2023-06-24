%extend eDVBServicePMTHandler {
PyObject *eDVBServicePMTHandler::getCaIds(bool pair)
{
	ePyObject ret;
	std::vector<int> caids, ecmpids;
	std::vector<std::string> databytes;
	self->getCaIds(caids, ecmpids, databytes);
	unsigned int cnt = caids.size();

	ret = PyList_New(cnt);

	for (unsigned int i = 0; i < cnt; i++)
	{
		if (pair)
		{
			ePyObject tuple = PyTuple_New(3);
			PyTuple_SET_ITEM(tuple, 0, PyLong_FromLong(caids[i]));
			PyTuple_SET_ITEM(tuple, 1, PyLong_FromLong(ecmpids[i]));
			PyTuple_SET_ITEM(tuple, 2, PyString_FromString(databytes[i].c_str()));
			PyList_SET_ITEM(ret, i, tuple);
		}
		else
		{
			PyList_SET_ITEM(ret, i, PyLong_FromLong(caids[i]));
		}
	}

	return ret;
}
};

%ignore eDVBServicePMTHandler::getCaIds;
