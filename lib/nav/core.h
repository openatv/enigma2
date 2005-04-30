#ifndef __nav_core_h
#define __nav_core_h

#include <lib/base/object.h>
#include <lib/service/iservice.h>
#include <lib/nav/playlist.h>
#include <connection.h>

class eNavigation: public iObject, public Object
{
	DECLARE_REF(eNavigation);
private:
	ePtr<iPlayableService> m_runningService;
	
	ePtr<iRecordableService> m_recordingService;
	
	ePtr<iServiceHandler> m_servicehandler;
	Signal2<void,eNavigation*,int> m_event;
	ePtr<eConnection> m_service_event_conn;
	void serviceEvent(iPlayableService* service, int event);
	
	ePtr<ePlaylist> m_playlist;
public:
	enum
	{
		evStopService,  /** the "current" service was just stopped and likes to be deallocated (clear refs!) */
		evNewService,   /** a new "current" service was just started */
		evPlayFailed,   /** the next service (in playlist) or the one given in playService failed to play */
		evPlaylistDone, /** the last service in the playlist was just played */
		evUpdatedEventInfo /** the "currently running" event info was updated */
	};
	
	RESULT playService(const eServiceReference &service);
	RESULT enqueueService(const eServiceReference &service);
	RESULT connectEvent(const Slot2<void,eNavigation*,int> &event, ePtr<eConnection> &connection);
/*	int connectServiceEvent(const Slot1<void,iPlayableService*,int> &event, ePtr<eConnection> &connection); */
	RESULT getCurrentService(ePtr<iPlayableService> &service);
	RESULT getPlaylist(ePtr<ePlaylist> &playlist);
	RESULT stopService(void);
	
	RESULT recordService(const eServiceReference &service);
	RESULT endRecording();
	
	RESULT pause(int p);
	eNavigation(iServiceHandler *serviceHandler);
	virtual ~eNavigation();
};

#endif
