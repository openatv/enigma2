#include <lib/base/eerror.h>
#include <lib/base/estring.h>
#include <lib/python/python.h>
#include <lib/service/service.h>
#include <lib/base/init_num.h>
#include <lib/base/init.h>
#include <lib/python/python.h>

static std::string encode(const std::string s)
{
	int len = s.size();
	std::string res;
	int i;
	for (i=0; i<len; ++i)
	{
		unsigned char c = s[i];
		if ((c == ':') || (c < 32) || (c == '%'))
		{
			res += "%";
			char hex[8];
			snprintf(hex, 8, "%02x", c);
			res += hex;
		} else
			res += c;
	}
	return res;
}

static std::string decode(const std::string s)
{
	int len = s.size();
	std::string res;
	int i;
	for (i=0; i<len; ++i)
	{
		unsigned char c = s[i];
		if (c != '%')
			res += c;
		else
		{
			i += 2;
			if (i >= len)
				break;
			char t[3] = {s[i - 1], s[i], 0};
			unsigned char r = strtoul(t, 0, 0x10);
			if (r)
				res += r;
		}
	}
	return res;
}


eServiceReference::eServiceReference(const std::string &string)
{
	const char *c=string.c_str();
	int pathl=0;

	if (!string.length())
		type = idInvalid;
	else if ( sscanf(c, "%d:%d:%x:%x:%x:%x:%x:%x:%x:%x:%n", &type, &flags, &data[0], &data[1], &data[2], &data[3], &data[4], &data[5], &data[6], &data[7], &pathl) < 8 )
	{
		memset( data, 0, sizeof(data) );
		eDebug("find old format eServiceReference string");
		if ( sscanf(c, "%d:%d:%x:%x:%x:%x:%n", &type, &flags, &data[0], &data[1], &data[2], &data[3], &pathl) < 2 )
			type = idInvalid;
	}

	if (pathl)
	{
		const char *pathstr = c+pathl;
		const char *namestr = strchr(pathstr, ':');
		if (namestr)
		{
			if (pathstr != namestr)
				path.assign(pathstr, namestr-pathstr);
			if (*(namestr+1))
				name=namestr+1;
		}
		else
			path=pathstr;
	}
	
	path = decode(path);
	name = decode(name);
}

std::string eServiceReference::toString() const
{
	std::string ret;
	ret += getNum(type);
	ret += ":";
	ret += getNum(flags);
	for (unsigned int i=0; i<sizeof(data)/sizeof(*data); ++i)
		ret+=":"+ getNum(data[i], 0x10);
	ret+=":"+encode(path); /* we absolutely have a problem when the path contains a ':' (for example: http://). we need an encoding here. */
	if (name.length())
		ret+=":"+encode(name);
	return ret;
}

std::string eServiceReference::toCompareString() const
{
	std::string ret;
	ret += getNum(type);
	ret += ":0";
	for (unsigned int i=0; i<sizeof(data)/sizeof(*data); ++i)
		ret+=":"+getNum(data[i], 0x10);
	ret+=":"+encode(path);
	return ret;
}

eServiceCenter *eServiceCenter::instance;

eServiceCenter::eServiceCenter()
{
	if (!instance)
	{
		eDebug("settings instance.");
		instance = this;
	}
}

eServiceCenter::~eServiceCenter()
{
	if (instance == this)
	{
		eDebug("clear instance");
		instance = 0;
	}
}

DEFINE_REF(eServiceCenter);

RESULT eServiceCenter::play(const eServiceReference &ref, ePtr<iPlayableService> &ptr)
{
	std::map<int,ePtr<iServiceHandler> >::iterator i = handler.find(ref.type);
	if (i == handler.end())
	{
		ptr = 0;
		return -1;
	}
	return i->second->play(ref, ptr);
}

RESULT eServiceCenter::record(const eServiceReference &ref, ePtr<iRecordableService> &ptr)
{
	std::map<int,ePtr<iServiceHandler> >::iterator i = handler.find(ref.type);
	if (i == handler.end())
	{
		ptr = 0;
		return -1;
	}
	return i->second->record(ref, ptr);
}

RESULT eServiceCenter::list(const eServiceReference &ref, ePtr<iListableService> &ptr)
{
	std::map<int,ePtr<iServiceHandler> >::iterator i = handler.find(ref.type);
	if (i == handler.end())
	{
		ptr = 0;
		return -1;
	}
	return i->second->list(ref, ptr);
}

RESULT eServiceCenter::info(const eServiceReference &ref, ePtr<iStaticServiceInformation> &ptr)
{
	std::map<int,ePtr<iServiceHandler> >::iterator i = handler.find(ref.type);
	if (i == handler.end())
	{
		ptr = 0;
		return -1;
	}
	return i->second->info(ref, ptr);
}

RESULT eServiceCenter::offlineOperations(const eServiceReference &ref, ePtr<iServiceOfflineOperations> &ptr)
{
	std::map<int,ePtr<iServiceHandler> >::iterator i = handler.find(ref.type);
	if (i == handler.end())
	{
		ptr = 0;
		return -1;
	}
	return i->second->offlineOperations(ref, ptr);
}

RESULT eServiceCenter::addServiceFactory(int id, iServiceHandler *hnd, std::list<std::string> &extensions)
{
	handler.insert(std::pair<int,ePtr<iServiceHandler> >(id, hnd));
	this->extensions[id]=extensions;
	return 0;
}

RESULT eServiceCenter::removeServiceFactory(int id)
{
	handler.erase(id);
	extensions.erase(id);
	return 0;
}

RESULT eServiceCenter::addFactoryExtension(int id, const char *extension)
{
	std::map<int, std::list<std::string> >::iterator it = extensions.find(id);
	if (it == extensions.end())
		return -1;
	it->second.push_back(extension);
	return 0;
}

RESULT eServiceCenter::removeFactoryExtension(int id, const char *extension)
{
	std::map<int, std::list<std::string> >::iterator it = extensions.find(id);
	if (it == extensions.end())
		return -1;
	it->second.remove(extension);
	return 0;
}


int eServiceCenter::getServiceTypeForExtension(const char *str)
{
	for (std::map<int, std::list<std::string> >::iterator sit(extensions.begin()); sit != extensions.end(); ++sit)
	{
		for (std::list<std::string>::iterator eit(sit->second.begin()); eit != sit->second.end(); ++eit)
		{
			if (*eit == str)
				return sit->first;
		}
	}
	return -1;
}

int eServiceCenter::getServiceTypeForExtension(const std::string &str)
{
	return getServiceTypeForExtension(str.c_str());
}

	/* default handlers */
RESULT iServiceHandler::info(const eServiceReference &, ePtr<iStaticServiceInformation> &ptr)
{
	ptr = 0;
	return -1;
}

#include <lib/service/event.h>

RESULT iStaticServiceInformation::getEvent(const eServiceReference &ref, ePtr<eServiceEvent> &evt, time_t start_time)
{
	evt = 0;
	return -1;
}

int iStaticServiceInformation::getLength(const eServiceReference &ref)
{
	return -1;
}

int iStaticServiceInformation::isPlayable(const eServiceReference &ref, const eServiceReference &ignore, bool simulate)
{
	return 0;
}

RESULT iServiceInformation::getEvent(ePtr<eServiceEvent> &evt, int m_nownext)
{
	evt = 0;
	return -1;
}

int iStaticServiceInformation::getInfo(const eServiceReference &ref, int w)
{
	return -1;
}

std::string iStaticServiceInformation::getInfoString(const eServiceReference &ref, int w)
{
	return "";
}

PyObject *iStaticServiceInformation::getInfoObject(const eServiceReference &ref, int w)
{
	Py_RETURN_NONE;
}

int iServiceInformation::getInfo(int w)
{
	return -1;
}

std::string iServiceInformation::getInfoString(int w)
{
	return "";
}

PyObject* iServiceInformation::getInfoObject(int w)
{
	Py_RETURN_NONE;
}

int iStaticServiceInformation::setInfo(const eServiceReference &ref, int w, int v)
{
	return -1;
}

int iStaticServiceInformation::setInfoString(const eServiceReference &ref, int w, const char *v)
{
	return -1;
}

int iServiceInformation::setInfo(int w, int v)
{
	return -1;
}

int iServiceInformation::setInfoString(int w, const char *v)
{
	return -1;
}

eAutoInitPtr<eServiceCenter> init_eServiceCenter(eAutoInitNumbers::service, "eServiceCenter");
