#include <lib/base/eerror.h>
#include <lib/base/object.h>
#include <string>
#include <errno.h>
#include <lib/service/servicefs.h>
#include <lib/service/service.h>
#include <lib/base/init_num.h>
#include <lib/base/init.h>
#include <dirent.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <unistd.h>


class eServiceFSInformation: public iServiceInformation
{
	DECLARE_REF;
public:
	RESULT getName(const eServiceReference &ref, std::string &name);
};

DEFINE_REF(eServiceFSInformation);

RESULT eServiceFSInformation::getName(const eServiceReference &ref, std::string &name)
{
	name = ref.path;
}

// eServiceFactoryFS

eServiceFactoryFS::eServiceFactoryFS()
{
	ePtr<eServiceCenter> sc;
	
	eServiceCenter::getInstance(sc);
	if (sc)
		sc->addServiceFactory(eServiceFactoryFS::id, this);
	
	m_service_information = new eServiceFSInformation();
}

eServiceFactoryFS::~eServiceFactoryFS()
{
	ePtr<eServiceCenter> sc;
	
	eServiceCenter::getInstance(sc);
	if (sc)
		sc->removeServiceFactory(eServiceFactoryFS::id);
}

DEFINE_REF(eServiceFactoryFS)

	// iServiceHandler
RESULT eServiceFactoryFS::play(const eServiceReference &ref, ePtr<iPlayableService> &ptr)
{
	ptr=0;
	return -1;
}

RESULT eServiceFactoryFS::record(const eServiceReference &ref, ePtr<iRecordableService> &ptr)
{
	ptr=0;
	return -1;
}

RESULT eServiceFactoryFS::list(const eServiceReference &ref, ePtr<iListableService> &ptr)
{
	ptr = new eServiceFS(ref.path.c_str());
	return 0;
}

RESULT eServiceFactoryFS::info(const eServiceReference &ref, ePtr<iServiceInformation> &ptr)
{
	ptr = m_service_information;
	return 0;
}

// eServiceFS

DEFINE_REF(eServiceFS);

eServiceFS::eServiceFS(const char *path): path(path)
{
}

eServiceFS::~eServiceFS()
{
}

RESULT eServiceFS::getContent(std::list<eServiceReference> &list)
{
	DIR *d=opendir(path.c_str());
	if (!d)
		return -errno;
	while (dirent *e=readdir(d))
	{
		if (!(strcmp(e->d_name, ".") && strcmp(e->d_name, "..")))
			continue;
		
		std::string filename;
		
		filename = path;
		filename += e->d_name;
		
		struct stat s;
		if (::stat(filename.c_str(), &s) < 0)
			continue;
		
		if (S_ISDIR(s.st_mode))
			filename += "/";
		
		if (S_ISDIR(s.st_mode))
		{
			eServiceReference service(eServiceFactoryFS::id, 
				eServiceReference::isDirectory|
				eServiceReference::canDescent|eServiceReference::mustDescent|
				eServiceReference::shouldSort|eServiceReference::sort1,
				filename);
			service.data[0] = 1;
			list.push_back(service);
		} else
		{
			eServiceReference service(eServiceFactoryFS::id, 
				eServiceReference::isDirectory|
				eServiceReference::canDescent|eServiceReference::mustDescent|
				eServiceReference::shouldSort|eServiceReference::sort1,
				filename);
			service.data[0] = 0;
			list.push_back(service);
		}
	}
	return 0;
}

eAutoInitPtr<eServiceFactoryFS> init_eServiceFactoryFS(eAutoInitNumbers::service+1, "eServiceFactoryFS");
