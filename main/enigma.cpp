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
#include <lib/dvb_si/pmt.h>
#include <lib/dvb/scan.h>
#include <unistd.h>

#include <lib/service/iservice.h>

class eMain: public eApplication, public Object
{
	eInit init;
	
	ePtr<eDVBResourceManager> m_mgr;
	ePtr<iDVBChannel> m_channel;
	ePtr<eDVBDB> m_dvbdb;

	ePtr<iPlayableService> m_playservice;
public:
	eMain()
	{
		init.setRunlevel(eAutoInitNumbers::main);
		m_dvbdb = new eDVBDB();
		m_mgr = new eDVBResourceManager();
		m_mgr->setChannelList(m_dvbdb);
		
		ePtr<eServiceCenter> service_center;
		eServiceCenter::getInstance(service_center);

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
		
		eServiceReference ref("1:0:1:6de2:44d:1:c00000:0:0:0:");
		
		if (service_center)
		{
			if (service_center->play(ref, m_playservice))
				eDebug("play sucked around!");
			else
				eDebug("play r00lz!");
		} else
			eDebug("no service center: no play.");
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
	return app.exec();
}
