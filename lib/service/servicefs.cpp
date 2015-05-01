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
	{
		std::list<std::string> extensions;
		sc->addServiceFactory(eServiceFactoryFS::id, this, extensions);
	}

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
	ptr = new eServiceFS(ref.path.c_str(), ref.getName().empty() ? (const char*)0 : ref.getName().c_str());
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

eServiceFS::eServiceFS(const char *path, const char *additional_extensions): path(path)
{
	m_list_valid = 0;
	if (additional_extensions)
	{
		size_t slen=strlen(additional_extensions);
		char buf[slen+1];
		char *tmp=0, *cmds = buf;
		memcpy(buf, additional_extensions, slen+1);

		// strip spaces at beginning
		while(cmds[0] == ' ')
		{
			++cmds;
			--slen;
		}

		// strip spaces at the end
		while(slen && cmds[slen-1] == ' ')
		{
			cmds[slen-1] = 0;
			--slen;
		}

		if (slen)
		{
			if (*cmds)
			{
				int id;
				char buf2[17]; /* additional extention string is 16 characters + null-termination */
				while(1)
				{
					tmp = strchr(cmds, ' ');
					if (tmp)
						*tmp = 0;
					if (strstr(cmds, "0x"))
					{
						if (sscanf(cmds, "0x%x:%16s", &id, buf2) == 2)
							m_additional_extensions[id].push_back(buf2);
						else
							eDebug("[eServiceFS] parse additional_extension (%s) failed", cmds);
					}
					else
					{
						if (sscanf(cmds, "%d:%16s", &id, buf2) == 2)
							m_additional_extensions[id].push_back(buf2);
						else
							eDebug("[eServiceFS] parse additional_extension (%s) failed", cmds);
					}
					if (!tmp)
						break;
					cmds = tmp+1;
					while (*cmds && *cmds == ' ')
						++cmds;
				}
			}
		}
	}
}

eServiceFS::~eServiceFS()
{
}

int lower(char c)
{
	return std::tolower(static_cast<unsigned char>(c));
}

RESULT eServiceFS::getContent(std::list<eServiceReference> &list, bool sorted)
{
	DIR *d=opendir(path.c_str());
	if (!d)
		return -errno;

	ePtr<eServiceCenter> sc;
	eServiceCenter::getPrivInstance(sc);

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

		if (S_ISDIR(s.st_mode) || S_ISLNK(s.st_mode))
		{
			filename += "/";
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
			if (e != std::string::npos && e+1 < filename.length())
			{
				std::string extension = filename.substr(e+1);
				std::transform(extension.begin(), extension.end(), extension.begin(), lower);
				int type = getServiceTypeForExtension(extension);

				if (type == -1)
				{
					type = sc->getServiceTypeForExtension(extension);
				}

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
	}
	closedir(d);

	if (sorted)
		list.sort(iListableServiceCompare(this));

	return 0;
}

//   The first argument of this function is a format string to specify the order and
//   the content of the returned list
//   useable format options are
//   R = Service Reference (as swig object .. this is very slow)
//   S = Service Reference (as python string object .. same as ref.toString())
//   C = Service Reference (as python string object .. same as ref.toCompareString())
//   N = Service Name (as python string object)
//   when exactly one return value per service is selected in the format string,
//   then each value is directly a list entry
//   when more than one value is returned per service, then the list is a list of
//   python tuples
//   unknown format string chars are returned as python None values !
PyObject *eServiceFS::getContent(const char* format, bool sorted)
{
	ePyObject ret;
	std::list<eServiceReference> tmplist;
	int retcount=1;

	if (!format || !(retcount=strlen(format)))
		format = "R"; // just return service reference swig object ...

	if (!getContent(tmplist, sorted))
	{
		int services=tmplist.size();
		ePtr<iStaticServiceInformation> sptr;
		eServiceCenterPtr service_center;

		if (strchr(format, 'N'))
			eServiceCenter::getPrivInstance(service_center);

		ret = PyList_New(services);
		std::list<eServiceReference>::iterator it(tmplist.begin());

		for (int cnt=0; cnt < services; ++cnt)
		{
			eServiceReference &ref=*it++;
			ePyObject tuple = retcount > 1 ? PyTuple_New(retcount) : ePyObject();
			for (int i=0; i < retcount; ++i)
			{
				ePyObject tmp;
				switch(format[i])
				{
				case 'R':  // service reference (swig)object
					tmp = NEW_eServiceReference(ref);
					break;
				case 'C':  // service reference compare string
					tmp = PyString_FromString(ref.toCompareString().c_str());
					break;
				case 'S':  // service reference string
					tmp = PyString_FromString(ref.toString().c_str());
					break;
				case 'N':  // service name
					if (service_center)
					{
						service_center->info(ref, sptr);
						if (sptr)
						{
							std::string name;
							sptr->getName(ref, name);
							if (name.length())
								tmp = PyString_FromString(name.c_str());
						}
					}
					if (!tmp)
						tmp = PyString_FromString("<n/a>");
					break;
				default:
					if (tuple)
					{
						tmp = Py_None;
						Py_INCREF(Py_None);
					}
					break;
				}
				if (tmp)
				{
					if (tuple)
						PyTuple_SET_ITEM(tuple, i, tmp);
					else
						PyList_SET_ITEM(ret, cnt, tmp);
				}
			}
			if (tuple)
				PyList_SET_ITEM(ret, cnt, tuple);
		}
	}
	return ret ? (PyObject*)ret : (PyObject*)PyList_New(0);
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

	if (m_list.empty())
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

int eServiceFS::getServiceTypeForExtension(const char *str)
{
	for (std::map<int, std::list<std::string> >::iterator sit(m_additional_extensions.begin()); sit != m_additional_extensions.end(); ++sit)
	{
		for (std::list<std::string>::iterator eit(sit->second.begin()); eit != sit->second.end(); ++eit)
		{
			if (*eit == str)
				return sit->first;
		}
	}
	return -1;
}

int eServiceFS::getServiceTypeForExtension(const std::string &str)
{
	for (std::map<int, std::list<std::string> >::iterator sit(m_additional_extensions.begin()); sit != m_additional_extensions.end(); ++sit)
	{
		for (std::list<std::string>::iterator eit(sit->second.begin()); eit != sit->second.end(); ++eit)
		{
			if (*eit == str)
				return sit->first;
		}
	}
	return -1;
}

eAutoInitPtr<eServiceFactoryFS> init_eServiceFactoryFS(eAutoInitNumbers::service+1, "eServiceFactoryFS");
