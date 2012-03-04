/*
  eEITSave E2
  (c) 2010 by Dr. Best  <dr.best@dreambox-tools.info>
*/

using namespace std;
#include <lib/dvb/dvb.h>
#include <lib/dvb/epgcache.h>
#include <fcntl.h>

static void SaveEIT(const char *ref, const char *filename, int  eit_event_id, time_t begTime, time_t endTime)
{
	eEPGCache::getInstance()->Lock();
	const eit_event_struct *event = 0;
	eServiceReference mref = eServiceReference(ref);
	std::string sref = ref;
	if ( eit_event_id != -1 )
	{
		eDebug("[EITSave] query epg event id %d, %s", eit_event_id, sref.c_str());
		eEPGCache::getInstance()->lookupEventId(mref, eit_event_id, event);
	}
	
	if ( !event && (begTime != -1 && endTime != -1) )
	{
		time_t queryTime = begTime + ((endTime-begTime)/2);
		tm beg, end, query;
		localtime_r(&begTime, &beg);
		localtime_r(&endTime, &end);
		localtime_r(&queryTime, &query);
		eDebug("[EITSave] query stime %d:%d:%d, etime %d:%d:%d, qtime %d:%d:%d",
			beg.tm_hour, beg.tm_min, beg.tm_sec,
			end.tm_hour, end.tm_min, end.tm_sec,
			query.tm_hour, query.tm_min, query.tm_sec);
		eEPGCache::getInstance()->lookupEventTime(mref, queryTime, event);
	}
	if ( event )
	{
		eDebug("[EITSave] found event.. store to disc");
		std::string fname = filename;
		int fd = open(fname.c_str(), O_CREAT|O_WRONLY, 0777);
		if (fd>-1)
		{
			int evLen=HILO(event->descriptors_loop_length)+12/*EIT_LOOP_SIZE*/;
			int wr = ::write( fd, (unsigned char*)event, evLen );
			if ( wr != evLen )
				eDebug("eit write error (%m)");
			::close(fd);
		}
	}
	else
		eDebug("[EITSave] no event found...");
	eEPGCache::getInstance()->Unlock();
}

extern "C" {


static PyObject *
SaveEIT(PyObject *self, PyObject *args)
{
	char* var1;
	char* var2;
	int var3;
	time_t var4;
	time_t var5;
	if (PyTuple_Size(args) != 5 || !PyArg_ParseTuple(args, "ssiii", &var1, &var2, &var3, &var4, &var5))
		Py_RETURN_NONE;
	else
		SaveEIT(var1,var2, var3, var4, var5);
	Py_RETURN_NONE;
}


static PyMethodDef module_methods[] = {
	{"SaveEIT", (PyCFunction)SaveEIT,  METH_VARARGS,
	 "SaveEIT"
	},
	{NULL, NULL, 0, NULL} 
};

PyMODINIT_FUNC
initeitsave(void)
{
	Py_InitModule3("eitsave", module_methods,
		"EIT Saver");
}
};

