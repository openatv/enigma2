#include <lib/base/externalvideo.h>
#include <lib/base/eerror.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <sys/un.h>
#include <unistd.h>
#include <string.h>
#include <errno.h>
#include <stdlib.h>

#define EXTERNAL_VIDEO_SOCKET "/var/run/video.socket"

eExternalVideo *eExternalVideo::getInstance()
{
	static eExternalVideo s_inst;
	return &s_inst;
}

eExternalVideo::eExternalVideo()
{
	m_fd = ::socket(AF_UNIX, SOCK_DGRAM | SOCK_CLOEXEC | SOCK_NONBLOCK, 0);
	if (m_fd < 0) {
		eWarning("[eExternalVideo] socket: %s", strerror(errno));
		return;
	}

	struct sockaddr_un sa;
	memset(&sa, 0, sizeof(sa));
	sa.sun_family = AF_UNIX;
	strncpy(sa.sun_path, EXTERNAL_VIDEO_SOCKET, sizeof(sa.sun_path) - 1);
	::unlink(EXTERNAL_VIDEO_SOCKET);
	if (::bind(m_fd, reinterpret_cast<struct sockaddr *>(&sa), sizeof(sa)) < 0) {
		eWarning("[eExternalVideo] bind %s: %s", EXTERNAL_VIDEO_SOCKET, strerror(errno));
		::close(m_fd);
		m_fd = -1;
		return;
	}
	::chmod(EXTERNAL_VIDEO_SOCKET, 0666);

	m_sn = eSocketNotifier::create(eApp, m_fd, eSocketNotifier::Read);
	CONNECT(m_sn->activated, eExternalVideo::readable);
}

/* the number after "key": in msg, def if missing */
static int jsonInt(const char *msg, const char *key, int def)
{
	const char *p = strstr(msg, key);
	if (!p)
		return def;
	p = strchr(p + strlen(key), ':');
	return p ? atoi(p + 1) : def;
}

void eExternalVideo::readable(int)
{
	char msg[512];
	ssize_t len;

	while ((len = ::recv(m_fd, msg, sizeof(msg) - 1, 0)) > 0) {
		msg[len] = 0;
		/* only the video track of a player */
		const char *vc = strstr(msg, "\"v_c\"");
		if (!vc)
			continue;
		int width = jsonInt(vc, "\"w\"", 0);
		int height = jsonInt(vc, "\"h\"", 0);
		int framerate = jsonInt(vc, "\"f\"", 0);
		int progressive = jsonInt(vc, "\"p\"", -1);
		eDebug("[eExternalVideo] %dx%d %d %d", width, height, framerate, progressive);
		videoChanged(width, height, framerate, progressive);
	}
}
