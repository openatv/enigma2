#ifndef __lib_nav_playlist_h
#define __lib_nav_playlist_h

#include <list>
#include <lib/base/object.h>
#include <lib/service/iservice.h>

class ePlaylist: public virtual iObject, public std::list<eServiceReference>
{
DECLARE_REF;
public:
	ePlaylist();
	std::list<eServiceReference>::iterator m_current;
};

#endif
