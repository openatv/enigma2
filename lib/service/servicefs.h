#ifndef __servicefs_h
#define __servicefs_h

#include <lib/service/iservice.h>

class eServiceFactoryFS: public iServiceHandler
{
DECLARE_REF;
public:
	eServiceFactoryFS();
	virtual ~eServiceFactoryFS();
	enum { id = 0x2 };

		// iServiceHandler
	RESULT play(const eServiceReference &, ePtr<iPlayableService> &ptr);
	RESULT record(const eServiceReference &, ePtr<iRecordableService> &ptr);
	RESULT list(const eServiceReference &, ePtr<iListableService> &ptr);
};

class eServiceFS: public iListableService
{
DECLARE_REF;
private:
	eString path;
	friend class eServiceFactoryFS;
	eServiceFS(const char *path);
public:
	virtual ~eServiceFS();
	
	RESULT getContent(std::list<eServiceReference> &list);
};

#endif
