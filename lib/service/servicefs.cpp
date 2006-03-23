#include <lib/base/eerror.h>
#include <lib/base/object.h>
#include <string>
#include <errno.h>
#include <lib/service/servicefs.h>
#include <lib/service/service.h>
#include <lib/service/servicedvb.h>
#include <lib/base/init_num.h>
#include <lib/base/init.h>
#include <dirent.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <unistd.h>

class eStaticServiceFSInformation: public iStaticServiceInformation
{
	DECLARE_REF(eStaticServiceFSInformation);
public:
	RESULT getName(const eServiceReference &ref, std::string &name);
	int getLength(const eServiceReference &ref) { return -1; }
};

DEFINE_REF(eStaticServiceFSInformation);

RESULT eStaticServiceFSInformation::getName(const eServiceReference &ref, std::string &name)
{
	name = ref.path;
	return 0;
}

// eServiceFactoryFS

eServiceFactoryFS::eServiceFactoryFS()
{
	ePtr<eServiceCenter> sc;
	
	eServiceCenter::getPrivInstance(sc);
	if (sc)
		sc->addServiceFactory(eServiceFactoryFS::id, this);
	
	m_service_information = new eStaticServiceFSInformation();
}

eServiceFactoryFS::~eServiceFactoryFS()
{
	ePtr<eServiceCenter> sc;
	
	eServiceCenter::getPrivInstance(sc);
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

RESULT eServiceFactoryFS::info(const eServiceReference &ref, ePtr<iStaticServiceInformation> &ptr)
{
	ptr = m_service_information;
	return 0;
}

RESULT eServiceFactoryFS::offlineOperations(const eServiceReference &, ePtr<iServiceOfflineOperations> &ptr)
{
	ptr = 0;
	return -1;
}

// eServiceFS

DEFINE_REF(eServiceFS);

eServiceFS::eServiceFS(const char *path): path(path)
{
	m_list_valid = 0;
}

eServiceFS::~eServiceFS()
{
}

RESULT eServiceFS::getContent(std::list<eServiceReference> &list, bool sorted)
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
			size_t e = filename.rfind('.');
			std::string extension = (e != std::string::npos) ? filename.substr(e) : "";
			int type = -1;
			
			if (extension == ".ts")
				type = eServiceFactoryDVB::id;
			else if (extension == ".mp3" || extension == ".ogg" || extension == ".avi")
				type = 4097;
			else if (extension == ".ogg")
				type = 4097;
			else if (extension == ".mpg")
				type = 4097;
			else if (extension == ".vob")
				type = 4097;
			
			if (type != -1)
			{
				eServiceReference service(type,
					0,
					filename);
				service.data[0] = 0;
				list.push_back(service);
			}
		}
	}
	closedir(d);

	if (sorted)
		list.sort(iListableServiceCompare(this));

	return 0;
}

RESULT eServiceFS::getContent(PyObject *list, bool sorted)
{
	if (!list || !PyList_Check(list))
		return -1;

	std::list<eServiceReference> tmplist;

	getContent(tmplist, sorted);

	if (sorted)
		tmplist.sort(iListableServiceCompare(this));

	for (std::list<eServiceReference>::iterator it(tmplist.begin());
		it != tmplist.end(); ++it)
	{
		PyObject *refobj = New_eServiceReference(*it);
		PyList_Append(list, refobj);
		Py_DECREF(refobj);
	}

	return 0;
}

RESULT eServiceFS::getNext(eServiceReference &ptr)
{
	if (!m_list_valid)
	{
		m_list_valid = 1;
		int res = getContent(m_list);
		if (res)
			return res;
	}
	
	if (!m_list.size())
	{
		ptr = eServiceReference();
		return -ERANGE;
	}
	
	ptr = m_list.front();
	m_list.pop_front();
	return 0;
}

int eServiceFS::compareLessEqual(const eServiceReference &a, const eServiceReference &b)
{
		/* directories first */
	if ((a.flags & ~b.flags) & eServiceReference::isDirectory)
		return 1;
	else if ((~a.flags & b.flags) & eServiceReference::isDirectory)
		return 0;
		/* sort by filename */
	else
		return a.path < b.path;
}

RESULT eServiceFS::startEdit(ePtr<iMutableServiceList> &res)
{
	res = 0;
	return -1;
}

eAutoInitPtr<eServiceFactoryFS> init_eServiceFactoryFS(eAutoInitNumbers::service+1, "eServiceFactoryFS");
