#include <lib/python/python_helpers.h>

void PutToDict(ePyObject &dict, const char *key, long value)
{
	ePyObject item = PyInt_FromLong(value);
	if (item)
	{
		if (PyDict_SetItemString(dict, key, item))
			eDebug("put %s to dict failed", key);
		Py_DECREF(item);
	}
	else
		eDebug("could not create PyObject for %s", key);
}

void PutToDict(ePyObject &dict, const char *key, ePyObject item)
{
	if (item)
	{
		if (PyDict_SetItemString(dict, key, item))
			eDebug("put %s to dict failed", key);
		Py_DECREF(item);
	}
	else
		eDebug("invalid PyObject for %s", key);
}

void PutToDict(ePyObject &dict, const char *key, const char *value)
{
	ePyObject item = PyString_FromString(value);
	if (item)
	{
		if (PyDict_SetItemString(dict, key, item))
			eDebug("put %s to dict failed", key);
		Py_DECREF(item);
	}
	else
		eDebug("could not create PyObject for %s", key);
}

static PyObject *createTuple(int pid, const char *type)
{
	PyObject *r = PyTuple_New(2);
	PyTuple_SET_ITEM(r, 0, PyInt_FromLong(pid));
	PyTuple_SET_ITEM(r, 1, PyString_FromString(type));
	return r;
}

static inline void PyList_AppendSteal(PyObject *list, PyObject *item)
{
	PyList_Append(list, item);
	Py_DECREF(item);
}

void frontendDataToDict(ePyObject &dest, ePtr<iDVBFrontendData> data)
{
	if (dest && PyDict_Check(dest))
	{
		PutToDict(dest, "tuner_number", data->getNumber());
		PutToDict(dest, "tuner_type", data->getTypeDescription().c_str());
	}
}

void frontendStatusToDict(ePyObject &dest, ePtr<iDVBFrontendStatus> status)
{
	if (dest && PyDict_Check(dest))
	{
		PutToDict(dest, "tuner_state", status->getStateDescription().c_str());
		PutToDict(dest, "tuner_locked", status->getLocked());
		PutToDict(dest, "tuner_synced", status->getSynced());
		PutToDict(dest, "tuner_bit_error_rate", status->getBER());
		PutToDict(dest, "tuner_signal_quality", status->getSNR());
		int snrdb = status->getSNRdB();
		if (snrdb >= 0) PutToDict(dest, "tuner_signal_quality_db", snrdb);
		PutToDict(dest, "tuner_signal_power", status->getSignalPower());
	}
}

void transponderDataToDict(ePyObject &dest, ePtr<iDVBTransponderData> data)
{
	if (dest && PyDict_Check(dest))
	{
		int value;
		PutToDict(dest, "tuner_type", data->getTunerType().c_str());
		PutToDict(dest, "frequency", data->getFrequency());
		value = data->getSymbolRate();
		if (value > 0) PutToDict(dest, "symbol_rate", value);
		value = data->getOrbitalPosition();
		if (value >= 0) PutToDict(dest, "orbital_position", value);
		value = data->getInversion();
		if (value >= 0) PutToDict(dest, "inversion", value);
		value = data->getFecInner();
		if (value >= 0) PutToDict(dest, "fec_inner", value);
		value = data->getModulation();
		if (value >= 0) PutToDict(dest, "modulation", value);
		value = data->getPolarization();
		if (value >= 0) PutToDict(dest, "polarization", value);
		value = data->getRolloff();
		if (value >= 0) PutToDict(dest, "rolloff", value);
		value = data->getPilot();
		if (value >= 0) PutToDict(dest, "pilot", value);
		value = data->getSystem();
		if (value >= 0) PutToDict(dest, "system", value);

		/* additional terrestrial fields */
		value = data->getBandwidth();
		if (value >= 0) PutToDict(dest, "bandwidth", value);
		value = data->getCodeRateLp();
		if (value >= 0) PutToDict(dest, "code_rate_lp", value);
		value = data->getCodeRateHp();
		if (value >= 0) PutToDict(dest, "code_rate_hp", value);
		value = data->getConstellation();
		if (value >= 0) PutToDict(dest, "constellation", value);
		value = data->getTransmissionMode();
		if (value >= 0) PutToDict(dest, "transmission_mode", value);
		value = data->getGuardInterval();
		if (value >= 0) PutToDict(dest, "guard_interval", value);
		value = data->getHierarchyInformation();
		if (value >= 0) PutToDict(dest, "hierarchy_information", value);
		value = data->getPlpId();
		if (value >= 0) PutToDict(dest, "plp_id", value);
	}
}

void streamingDataToDict(ePyObject &dest, ePtr<iStreamData> data)
{
	if (dest && PyDict_Check(dest))
	{
		int pmt, pcr, txt, adapter, demux;
		std::vector<int> video, audio, subtitle;
		unsigned int i;
		ePyObject l = PyList_New(0);
		PyList_AppendSteal(l, createTuple(0, "pat"));

		data->getPmtPid(pmt);
		if (pmt != -1)
			PyList_AppendSteal(l, createTuple(pmt, "pmt"));

		data->getVideoPids(video);
		for (i = 0; i < video.size(); i++)
		{
			PyList_AppendSteal(l, createTuple(video[i], "video"));
		}
		data->getAudioPids(audio);
		for (i = 0; i < audio.size(); i++)
		{
			PyList_AppendSteal(l, createTuple(audio[i], "audio"));
		}
		data->getSubtitlePids(subtitle);
		for (i = 0; i < subtitle.size(); i++)
		{
			PyList_AppendSteal(l, createTuple(subtitle[i], "subtitle"));
		}

		data->getPcrPid(pcr);
		PyList_AppendSteal(l, createTuple(pcr, "pcr"));

		data->getTxtPid(txt);
		if (txt != -1)
			PyList_AppendSteal(l, createTuple(txt, "text"));

		PutToDict(dest, "pids", l);

		data->getAdapterId(adapter);
		PutToDict(dest, "adapter", adapter);
		data->getDemuxId(demux);
		PutToDict(dest, "demux", demux);
	}
}
