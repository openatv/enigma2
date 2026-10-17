#ifndef __lib_base_externalvideo_h
#define __lib_base_externalvideo_h

#include <lib/python/connections.h>

#ifndef SWIG
#include <lib/base/ebase.h>
#endif

/* Video of players that run outside the services (exteplayer3, gstplayer
 * started by a plugin): they send a datagram to EXTERNAL_VIDEO_SOCKET when
 * the video changes, e.g. {"v_c":{"w":1920,"h":1080,"f":25000,"p":1}}. */
#ifdef SWIG
class eExternalVideo
#else
class eExternalVideo : public sigc::trackable
#endif
{
	eExternalVideo();
#ifndef SWIG
	int m_fd = -1;
	ePtr<eSocketNotifier> m_sn;

	void readable(int what);
#endif

public:
	/* width, height, frame rate in 1/1000 Hz, progressive (-1 unknown) */
	PSignal4<void, int, int, int, int> videoChanged;

	static eExternalVideo *getInstance();
};

#endif /* __lib_base_externalvideo_h */
