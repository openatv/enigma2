#include <lib/service/service.h>
#include <lib/base/init_num.h>
#include <lib/base/init.h>

eServiceReference::eServiceReference(const eString &string)
{
	const char *c=string.c_str();
	int pathl=-1;
	
	if ( sscanf(c, "%d:%d:%x:%x:%x:%x:%x:%x:%x:%x:%n", &type, &flags, &data[0], &data[1], &data[2], &data[3], &data[4], &data[5], &data[6], &data[7], &pathl) < 8 )
	{
		memset( data, 0, sizeof(data) );
		eDebug("find old format eServiceReference string");
		sscanf(c, "%d:%d:%x:%x:%x:%x:%n", &type, &flags, &data[0], &data[1], &data[2], &data[3], &pathl);
	}

	if (pathl)
		path=c+pathl;
}

eString eServiceReference::toString() const
{
	eString ret;
	ret+=eString().sprintf("%d:", type);
	ret+=eString().sprintf("%d", flags);
	for (unsigned int i=0; i<sizeof(data)/sizeof(*data); ++i)
		ret+=":"+eString().sprintf("%x", data[i]);
	ret+=":"+path;
	return ret;
}


eServiceCenter *eServiceCenter::instance;

eServiceCenter::eServiceCenter()
{
	if (!instance)
		instance = this;
}

eServiceCenter::~eServiceCenter()
{
	if (instance == this)
		instance = 0;
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

RESULT eServiceCenter::addServiceFactory(int id, iServiceHandler *hnd)
{
	handler.insert(std::pair<int,ePtr<iServiceHandler> >(id, hnd));
	return 0;
}

RESULT eServiceCenter::removeServiceFactory(int id)
{
	handler.erase(id);
	return 0;
}

eAutoInitP0<eServiceCenter> init_eServiceCenter(eAutoInitNumbers::service, "eServiceCenter");
