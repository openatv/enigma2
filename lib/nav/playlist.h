#ifndef __lib_nav_playlist_h
#define __lib_nav_playlist_h

#include <list>
#include <lib/base/object.h>
#include <lib/service/iservice.h>

class ePlaylist: public iObject, public std::list<eServiceReference>
{
DECLARE_REF;
public:
	ePlaylist();
	virtual ~ePlaylist();
	std::list<eServiceReference>::iterator m_current;
};

#endif
