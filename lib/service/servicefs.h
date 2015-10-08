#ifndef __servicefs_h
#define __servicefs_h

#include <lib/service/iservice.h>

class eServiceFactoryFS: public iServiceHandler
{
	DECLARE_REF(eServiceFactoryFS);
public:
	eServiceFactoryFS();
	virtual ~eServiceFactoryFS();
	enum { id = eServiceReference::idFile };

		// iServiceHandler
	RESULT play(const eServiceReference &, ePtr<iPlayableService> &ptr);
	RESULT record(const eServiceReference &, ePtr<iRecordableService> &ptr);
	RESULT list(const eServiceReference &, ePtr<iListableService> &ptr);
	RESULT info(const eServiceReference &, ePtr<iStaticServiceInformation> &ptr);
	RESULT offlineOperations(const eServiceReference &, ePtr<iServiceOfflineOperations> &ptr);
private:
	ePtr<iStaticServiceInformation> m_service_information;
};

class eServiceFS: public iListableService
{
	DECLARE_REF(eServiceFS);
	std::string path;
	friend class eServiceFactoryFS;
	eServiceFS(const char *path, const char *additional_extensions=0);
	std::map<int, std::list<std::string> > m_additional_extensions;

	int m_list_valid;
	std::list<eServiceReference> m_list;
	int getServiceTypeForExtension(const char *str);
	int getServiceTypeForExtension(const std::string &str);
public:
	virtual ~eServiceFS();

	RESULT getContent(std::list<eServiceReference> &list, bool sorted=false);
	PyObject *getContent(const char *format, bool sorted=false);
	RESULT getNext(eServiceReference &ptr);
	int compareLessEqual(const eServiceReference &, const eServiceReference &);
	RESULT startEdit(ePtr<iMutableServiceList> &);
};

// Mainly a placekeeper for its service types

class eServiceReferenceFS: public eServiceReference
{
public:
	// Service types (data[ref_service_type])
	enum {
		invalid   = -1,
		file      = 0,
		directory = 1,
	};
	eServiceReferenceFS()
		: eServiceReference()
	{
	}
	eServiceReferenceFS(int type, int flags)
		: eServiceReference(type, flags)
	{
	}
	eServiceReferenceFS(int type, int flags, int data0)
		: eServiceReference(type, flags, data0)
	{
	}
	eServiceReferenceFS(int type, int flags, int data0, int data1)
		: eServiceReference(type, flags, data0, data1)
	{
	}
	eServiceReferenceFS(int type, int flags, int data0, int data1, int data2)
		: eServiceReference(type, flags, data0, data1, data2)
	{
	}
	eServiceReferenceFS(int type, int flags, int data0, int data1, int data2, int data3)
		: eServiceReference(type, flags, data0, data1, data2, data3)
	{
	}
	eServiceReferenceFS(int type, int flags, int data0, int data1, int data2, int data3, int data4)
		: eServiceReference(type, flags, data0, data1, data2, data3, data4)
	{
	}
	eServiceReferenceFS(int type, int flags, const std::string &path)
		: eServiceReference(type, flags, path)
	{
	}
#ifdef SWIG
	eServiceReferenceFS(const eServiceReferenceFS &ref);
#endif
};
#endif
