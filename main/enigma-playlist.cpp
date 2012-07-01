#include <stdio.h>
#include <libsig_comp.h>
#include <lib/base/ebase.h>
#include <lib/base/eerror.h>
#include <lib/base/init.h>
#include <lib/base/init_num.h>

#include <lib/dvb/dvb.h>
#include <lib/dvb/db.h>
#include <lib/dvb/isection.h>
#include <lib/dvb/esection.h>
#include <dvbsi++/program_map_section.h>
#include <lib/dvb/scan.h>
#include <unistd.h>

#include <lib/service/iservice.h>
#include <lib/nav/core.h>

class eMain: public eApplication, public Object
{
	eInit init;
	
	ePtr<eDVBResourceManager> m_mgr;
	ePtr<iDVBChannel> m_channel;
	ePtr<eDVBDB> m_dvbdb;

	ePtr<iPlayableService> m_playservice;
	ePtr<eNavigation> m_nav;
	ePtr<eConnection> m_conn_event;
	ePtr<iServiceInformation> m_serviceInformation;
public:
	eMain()
	{
		init.setRunlevel(eAutoInitNumbers::main);
		m_dvbdb = new eDVBDB();
		m_mgr = new eDVBResourceManager();
		m_mgr->setChannelList(m_dvbdb);
		
		ePtr<eServiceCenter> service_center;
		eServiceCenter::getInstance(service_center);

		assert(service_center);
		m_nav = new eNavigation(service_center);
#if 0
		if (service_center)
		{
			eServiceReference ref("2:0:1:0:0:0:0:0:0:0:/");
			ePtr<iListableService> lst;
			if (service_center->list(ref, lst))
				eDebug("no list available!");
			else
			{
				std::list<eServiceReference> list;
				if (lst->getContent(list))
					eDebug("list itself SUCKED AROUND!!!");
				else
					for (std::list<eServiceReference>::const_iterator i(list.begin());
						i != list.end(); ++i)
						eDebug("%s", i->toString().c_str());
			}
		}
#endif		
		m_nav->connectEvent(slot(*this, &eMain::event), m_conn_event);
		
//		eServiceReference ref("1:0:1:6de2:44d:1:c00000:0:0:0:");
		eServiceReference ref("4097:47:0:0:0:0:0:0:0:0:/sine_60s_100.mp3");
		eServiceReference ref1("4097:47:0:0:0:0:0:0:0:0:/sine_60s_100.mp31");
		eServiceReference ref2("4097:47:0:0:0:0:0:0:0:0:/sine_60s_100.mp32");
		
		if (m_nav->enqueueService(ref))
			eDebug("play sucked around!");
		else
			eDebug("play r00lz!");

		m_nav->enqueueService(ref1);
		m_nav->enqueueService(ref2);
		m_nav->enqueueService(ref1);
	}
	
	void event(eNavigation *nav, int ev)
	{
		assert(nav);
		
		ePtr<ePlaylist> playlist;
		nav->getPlaylist(playlist);
		if (playlist)
		{
			eDebug("PLAYLIST:");
			ePlaylist::iterator i;
			for (i=playlist->begin(); i != playlist->end(); ++i)
				eDebug("%s %s", i == playlist->m_current ? "-->" : "   ", i->toString().c_str());
		}
		
		switch (ev)
		{
		case eNavigation::evStopService:
				/* very important: the old service should be deallocated, so clear *all* references to it */
			m_serviceInformation = 0;
			eDebug("STOP service!");
			break;
		case eNavigation::evNewService:
		{
			ePtr<iPlayableService> service;
			nav->getCurrentService(service);
			if (!service)
			{
				eDebug("no running service!");
				break;
			}
			if (service->getIServiceInformation(m_serviceInformation))
			{
				eDebug("failed to get iserviceinformation");
				break;
			}
			std::string name;
			m_serviceInformation->getName(name);
			eDebug("NEW running service: %s", name.c_str());
			break;
		}
		case eNavigation::evPlayFailed:
			eDebug("play failed!");
			break;
		case eNavigation::evPlaylistDone:
			eDebug("playlist done");
			quit();
			break;
		default:
			eDebug("Navigation event %d", ev);
			break;
		}
	}
	
	~eMain()
	{
	}
};

#ifdef OBJECT_DEBUG
int object_total_remaining;

void object_dump()
{
	printf("%d items left\n", object_total_remaining);
}
#endif

int main()
{
#ifdef OBJECT_DEBUG
	atexit(object_dump);
#endif

	eMain app;
	int res = app.exec();
	eDebug("after exec");
	return res;
}

