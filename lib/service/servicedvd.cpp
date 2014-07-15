/* yes, it's dvd  */
#include <lib/base/eerror.h>
#include <lib/base/object.h>
#include <lib/base/ebase.h>
#include <lib/base/nconfig.h>
#include <string>
#include <lib/service/service.h>
#include <lib/base/init_num.h>
#include <lib/base/init.h>
#include <lib/gui/esubtitle.h>
#include <lib/gdi/gpixmap.h>

#include <byteswap.h>
#include <netinet/in.h>
#ifndef BYTE_ORDER
#error no byte order defined!
#endif

extern "C" {
#include <dreamdvd/ddvdlib.h>
}
#include "servicedvd.h"

// eServiceFactoryDVD

eServiceFactoryDVD::eServiceFactoryDVD()
{
	ePtr<eServiceCenter> sc;

	eServiceCenter::getPrivInstance(sc);
	if (sc)
	{
		std::list<std::string> extensions;
		extensions.push_back("iso");
		extensions.push_back("img");
		sc->addServiceFactory(eServiceFactoryDVD::id, this, extensions);
	}
}

eServiceFactoryDVD::~eServiceFactoryDVD()
{
	ePtr<eServiceCenter> sc;

	eServiceCenter::getPrivInstance(sc);
	if (sc)
		sc->removeServiceFactory(eServiceFactoryDVD::id);
}

DEFINE_REF(eServiceFactoryDVD)

	// iServiceHandler
RESULT eServiceFactoryDVD::play(const eServiceReference &ref, ePtr<iPlayableService> &ptr)
{
		// check resources...
	ptr = new eServiceDVD(ref);
	return 0;
}

RESULT eServiceFactoryDVD::record(const eServiceReference &/*ref*/, ePtr<iRecordableService> &ptr)
{
	ptr=0;
	return -1;
}

RESULT eServiceFactoryDVD::list(const eServiceReference &, ePtr<iListableService> &ptr)
{
	ptr=0;
	return -1;
}


RESULT eServiceFactoryDVD::info(const eServiceReference &/*ref*/, ePtr<iStaticServiceInformation> &ptr)
{
	ptr=0;
	return -1;
}

RESULT eServiceFactoryDVD::offlineOperations(const eServiceReference &, ePtr<iServiceOfflineOperations> &ptr)
{
	ptr = 0;
	return -1;
}

DEFINE_REF(eServiceDVDInfoContainer);

int eServiceDVDInfoContainer::getInteger(unsigned int index) const
{
	if (index >= integerValues.size()) return -1;
	return integerValues[index];
}

std::string eServiceDVDInfoContainer::getString(unsigned int index) const
{
	if (index >= stringValues.size()) return "";
	return stringValues[index];
}

void eServiceDVDInfoContainer::addInteger(int value)
{
	integerValues.push_back(value);
}

void eServiceDVDInfoContainer::addString(const char *value)
{
	stringValues.push_back(value);
}


// eServiceDVD

DEFINE_REF(eServiceDVD);

eServiceDVD::eServiceDVD(eServiceReference ref):
	m_ref(ref), m_ddvdconfig(ddvd_create()), m_subtitle_widget(0), m_state(stIdle),
	m_current_trick(0), m_pump(eApp, 1), m_width(-1), m_height(-1),
	m_aspect(-1), m_framerate(-1), m_progressive(-1)
{
	int aspect = DDVD_16_9;
	int policy = DDVD_PAN_SCAN;
	int policy2 = DDVD_PAN_SCAN;

	char tmp[255];
	ssize_t rd;

	m_sn = eSocketNotifier::create(eApp, ddvd_get_messagepipe_fd(m_ddvdconfig), eSocketNotifier::Read|eSocketNotifier::Priority|eSocketNotifier::Error|eSocketNotifier::Hungup);
	eDebug("SERVICEDVD construct!");
	// create handle
	ddvd_set_dvd_path(m_ddvdconfig, ref.path.c_str());
	ddvd_set_ac3thru(m_ddvdconfig, 0);

	std::string ddvd_language = eConfigManager::getConfigValue("config.osd.language");
	if (ddvd_language != "")
		ddvd_set_language(m_ddvdconfig, (ddvd_language.substr(0,2)).c_str());

	int fd = open("/proc/stb/video/aspect", O_RDONLY);
	if (fd > -1)
	{
		rd = read(fd, tmp, 255);
		if (rd > 2 && !strncmp(tmp, "4:3", 3))
			aspect = DDVD_4_3;
		else if (rd > 4 && !strncmp(tmp, "16:10", 5))
			aspect = DDVD_16_10;
		close(fd);
	}

 	fd = open("/proc/stb/video/policy", O_RDONLY);
	if (fd > -1)
	{
		rd = read(fd, tmp, 255);
		if (rd > 6 && !strncmp(tmp, "bestfit", 7))
			policy = DDVD_JUSTSCALE;
		else if (rd > 8 && !strncmp(tmp, "letterbox", 9))
			policy = DDVD_LETTERBOX;
		close(fd);
	}

#ifdef DDVD_SUPPORTS_16_10_SCALING
 	fd = open("/proc/stb/video/policy2", O_RDONLY);
	if (fd > -1)
	{
		rd = read(fd, tmp, 255);
		if (rd > 6 && !strncmp(tmp, "bestfit", 7))
			policy2 = DDVD_JUSTSCALE;
		else if (rd > 8 && !strncmp(tmp, "letterbox", 9))
			policy2 = DDVD_LETTERBOX;
		close(fd);
	}
	ddvd_set_video_ex(m_ddvdconfig, aspect, policy, policy2, DDVD_PAL /*unused*/);
#else
	ddvd_set_video(m_ddvdconfig, aspect, policy, DDVD_PAL /*unused*/);
#warning please update libdreamdvd for 16:10 scaling support!
#endif

	CONNECT(m_sn->activated, eServiceDVD::gotMessage);
	CONNECT(m_pump.recv_msg, eServiceDVD::gotThreadMessage);
	strcpy(m_ddvd_titlestring,"");
	m_cue_pts = 0;
	pause();
}

void eServiceDVD::gotThreadMessage(const int &msg)
{
	switch(msg)
	{
	case 1: // thread stopped
		m_state = stStopped;
		m_event(this, evStopped);
		break;
	}
}

void eServiceDVD::gotMessage(int /*what*/)
{
	switch(ddvd_get_next_message(m_ddvdconfig,1))
	{
		case DDVD_COLORTABLE_UPDATE:
		{
/*
			struct ddvd_color ctmp[4];
			ddvd_get_last_colortable(ddvdconfig, ctmp);
			int i=0;
			while (i < 4)
			{
				rd1[252+i]=ctmp[i].red;
				bl1[252+i]=ctmp[i].blue;
				gn1[252+i]=ctmp[i].green;
				tr1[252+i]=ctmp[i].trans;
				i++;
			}
			if(ioctl(fb, FBIOPUTCMAP, &colormap) == -1)
			{
				printf("Framebuffer: <FBIOPUTCMAP failed>\n");
				return 1;
			}
*/
			eDebug("no support for 8bpp framebuffer in dvdplayer yet!");
			break;
		}
		case DDVD_SCREEN_UPDATE:
			eDebug("DVD_SCREEN_UPDATE!");
			if (m_subtitle_widget) {
				int x1,x2,y1,y2;
				ddvd_get_last_blit_area(m_ddvdconfig, &x1, &x2, &y1, &y2);

				int x_offset = 0, y_offset = 0, width = 720, height = 576;

#ifdef DDVD_SUPPORTS_GET_BLIT_DESTINATION
				ddvd_get_blit_destination(m_ddvdconfig, &x_offset, &y_offset, &width, &height);
				eDebug("values got from ddvd: %d %d %d %d", x_offset, y_offset, width, height);
				y_offset = -y_offset;
				width -= x_offset * 2;
				height -= y_offset * 2;
#endif
				eRect dest(x_offset, y_offset, width, height);

				if (dest.width() && dest.height())
					m_subtitle_widget->setPixmap(m_pixmap, eRect(x1, y1, (x2-x1)+1, (y2-y1)+1), dest);
			}
			break;
		case DDVD_SHOWOSD_STATE_PLAY:
		{
			eDebug("DVD_SHOWOSD_STATE_PLAY!");
			m_current_trick = 0;
			m_event(this, evUser+1);
			break;
		}
		case DDVD_SHOWOSD_STATE_PAUSE:
		{
			eDebug("DVD_SHOWOSD_STATE_PAUSE!");
			m_event(this, evUser+2);
			break;
		}
		case DDVD_SHOWOSD_STATE_FFWD:
		{
			eDebug("DVD_SHOWOSD_STATE_FFWD!");
			m_event(this, evUser+3);
			break;
		}
		case DDVD_SHOWOSD_STATE_FBWD:
		{
			eDebug("DVD_SHOWOSD_STATE_FBWD!");
			m_event(this, evUser+4);
			break;
		}
		case DDVD_SHOWOSD_STRING:
		{
			eDebug("DVD_SHOWOSD_STRING!");
			m_event(this, evUser+5);
			break;
		}
		case DDVD_SHOWOSD_AUDIO:
		{
			eDebug("DVD_SHOWOSD_AUDIO!");
			m_event(this, evUser+6);
			break;
		}
		case DDVD_SHOWOSD_SUBTITLE:
		{
			eDebug("DVD_SHOWOSD_SUBTITLE!");
			m_event((iPlayableService*)this, evUpdatedInfo);
			m_event(this, evUser+7);
			break;
		}
		case DDVD_EOF_REACHED:
			eDebug("DVD_EOF_REACHED!");
			m_event(this, evEOF);
			break;
		case DDVD_SOF_REACHED:
			eDebug("DVD_SOF_REACHED!");
			m_event(this, evSOF);
			break;
		case DDVD_SHOWOSD_ANGLE:
		{
			int current, num;
			ddvd_get_angle_info(m_ddvdconfig, &current, &num);
			eDebug("DVD_ANGLE_INFO: %d / %d", current, num);
			m_event(this, evUser+13);
			break;
		}
		case DDVD_SHOWOSD_TIME:
		{
			static struct ddvd_time last_info;
			struct ddvd_time info;
//			eDebug("DVD_SHOWOSD_TIME!");
			ddvd_get_last_time(m_ddvdconfig, &info);
			if ( info.pos_chapter != last_info.pos_chapter )
				m_event(this, evUser+8); // chapterUpdated
			if ( info.pos_title != last_info.pos_title )
				m_event(this, evUser+9); // titleUpdated
			memcpy(&last_info, &info, sizeof(struct ddvd_time));
			break;
		}
		case DDVD_SHOWOSD_TITLESTRING:
		{
			ddvd_get_title_string(m_ddvdconfig, m_ddvd_titlestring);
			eDebug("DDVD_SHOWOSD_TITLESTRING: %s",m_ddvd_titlestring);
			loadCuesheet();
			if (!m_cue_pts)
				unpause();
			m_event(this, evStart);
			break;
		}
		case DDVD_MENU_OPENED:
			eDebug("DVD_MENU_OPENED!");
			m_state = stMenu;
			m_event(this, evSeekableStatusChanged);
			m_event(this, evUser+11);
			break;
		case DDVD_MENU_CLOSED:
			eDebug("DVD_MENU_CLOSED!");
			m_state = stRunning;
			m_event(this, evSeekableStatusChanged);
			m_event(this, evUser+12);
			break;
#ifdef DDVD_SUPPORTS_PICTURE_INFO
		case DDVD_SIZE_CHANGED:
		{
			int changed = m_width != -1 && m_height != -1 && m_aspect != -1;
			ddvd_get_last_size(m_ddvdconfig, &m_width, &m_height, &m_aspect);
			if (changed)
				m_event((iPlayableService*)this, evVideoSizeChanged);
			break;
		}
		case DDVD_PROGRESSIVE_CHANGED:
		{
			int changed = m_progressive != -1;
			ddvd_get_last_progressive(m_ddvdconfig, &m_progressive);
			if (changed)
				m_event((iPlayableService*)this, evVideoProgressiveChanged);
			break;
		}
		case DDVD_FRAMERATE_CHANGED:
		{
			int changed = m_framerate != -1;
			ddvd_get_last_framerate(m_ddvdconfig, &m_framerate);
			if (changed)
				m_event((iPlayableService*)this, evVideoFramerateChanged);
			break;
		}
#endif
		default:
			break;
	}
}

eServiceDVD::~eServiceDVD()
{
	eDebug("SERVICEDVD destruct!");
	kill();
	saveCuesheet();
	ddvd_close(m_ddvdconfig);
	disableSubtitles();
}

RESULT eServiceDVD::connectEvent(const Slot2<void,iPlayableService*,int> &event, ePtr<eConnection> &connection)
{
	connection = new eConnection((iPlayableService*)this, m_event.connect(event));
	return 0;
}

RESULT eServiceDVD::start()
{
	ASSERT(m_state == stIdle);
	m_state = stRunning;
	eDebug("eServiceDVD starting");
// 	m_event(this, evStart);
	return 0;
}

RESULT eServiceDVD::stop()
{
	ASSERT(m_state != stIdle);
	if (m_state == stStopped)
		return -1;
	eDebug("DVD: stop %s", m_ref.path.c_str());
	m_state = stStopped;
	ddvd_send_key(m_ddvdconfig, DDVD_KEY_EXIT);

	return 0;
}

RESULT eServiceDVD::setTarget(int /*target*/)
{
	return -1;
}

RESULT eServiceDVD::pause(ePtr<iPauseableService> &ptr)
{
	ptr=this;
	return 0;
}

RESULT eServiceDVD::seek(ePtr<iSeekableService> &ptr)
{
	ptr=this;
	return 0;
}

RESULT eServiceDVD::subtitle(ePtr<iSubtitleOutput> &ptr)
{
	ptr=this;
	return 0;
}

RESULT eServiceDVD::audioTracks(ePtr<iAudioTrackSelection> &ptr)
{
	ptr = this;
	return 0;
}

int eServiceDVD::getNumberOfTracks()
{
	int i = 0;
	ddvd_get_audio_count(m_ddvdconfig, &i);
	return i;
}

int eServiceDVD::getCurrentTrack()
{
	int audio_id,audio_type;
	uint16_t audio_lang;
	ddvd_get_last_audio(m_ddvdconfig, &audio_id, &audio_lang, &audio_type);
	return audio_id;
}

RESULT eServiceDVD::selectTrack(unsigned int i)
{
	ddvd_set_audio(m_ddvdconfig, i);
	return 0;
}

RESULT eServiceDVD::getTrackInfo(struct iAudioTrackInfo &info, unsigned int audio_id)
{
	int audio_type;
	uint16_t audio_lang;
	ddvd_get_audio_byid(m_ddvdconfig, audio_id, &audio_lang, &audio_type);
	char audio_string[3]={audio_lang >> 8, audio_lang, 0};
	info.m_pid = audio_id+1;
	info.m_language = audio_string;
	switch(audio_type)
	{
		case DDVD_MPEG:
			info.m_description = "MPEG";
			break;
		case DDVD_AC3:
			info.m_description = "AC3";
			break;
		case DDVD_DTS:
			info.m_description = "DTS";
			break;
		case DDVD_LPCM:
			info.m_description = "LPCM";
			break;
		default:
			info.m_description = "und";
	}
	return 0;
}

RESULT eServiceDVD::keys(ePtr<iServiceKeys> &ptr)
{
	ptr=this;
	return 0;
}

	// iPausableService
RESULT eServiceDVD::setSlowMotion(int ratio)
{
	eDebug("setSlowmode(%d)", ratio);
	// pass ratio as repeat factor.
	// ratio=2 means 1/2 speed
	// ratio=3 means 1/3 speed
	ddvd_send_key(m_ddvdconfig, ratio < 0 ? DDVD_KEY_SLOWBWD : DDVD_KEY_SLOWFWD);
	ddvd_send_key(m_ddvdconfig, ratio);
	return 0;
}

RESULT eServiceDVD::setFastForward(int trick)
{
	eDebug("setTrickmode(%d)", trick);
	ddvd_send_key(m_ddvdconfig, trick < 0 ? DDVD_KEY_FASTBWD : DDVD_KEY_FASTFWD);
	ddvd_send_key(m_ddvdconfig, trick);
	return 0;
}

RESULT eServiceDVD::pause()
{
	eDebug("set pause!\n");
	ddvd_send_key(m_ddvdconfig, DDVD_KEY_PAUSE);
	return 0;
}

RESULT eServiceDVD::unpause()
{
	eDebug("set unpause!\n");
	ddvd_send_key(m_ddvdconfig, DDVD_KEY_PLAY);
	return 0;
}

void eServiceDVD::thread()
{
	eDebug("eServiceDVD dvd thread started");
	hasStarted();
	ddvd_run(m_ddvdconfig);
}

void eServiceDVD::thread_finished()
{
	eDebug("eServiceDVD dvd thread finished");
	m_pump.send(1); // inform main thread
}

RESULT eServiceDVD::info(ePtr<iServiceInformation>&i)
{
	i = this;
	return 0;
}

RESULT eServiceDVD::getName(std::string &name)
{
	if ( m_ddvd_titlestring[0] != '\0' )
		name = m_ddvd_titlestring;
	else
		if ( !m_ref.name.empty() )
			name = m_ref.name;
		else
			name = m_ref.path;
	return 0;
}

int eServiceDVD::getInfo(int w)
{
	switch (w)
	{
		case sCurrentChapter:
		{
			struct ddvd_time info;
			ddvd_get_last_time(m_ddvdconfig, &info);
			return info.pos_chapter;
		}
		case sTotalChapters:
		{
			struct ddvd_time info;
			ddvd_get_last_time(m_ddvdconfig, &info);
			return info.end_chapter;
		}
		case sCurrentTitle:
		{
			struct ddvd_time info;
			ddvd_get_last_time(m_ddvdconfig, &info);
			return info.pos_title;
		}
		case sTotalTitles:
		{
			struct ddvd_time info;
			ddvd_get_last_time(m_ddvdconfig, &info);
			return info.end_title;
		}
		case sTXTPID:	// we abuse HAS_TELEXT icon in InfoBar to signalize subtitles status
		{
			int spu_id;
			uint16_t spu_lang;
			ddvd_get_last_spu(m_ddvdconfig, &spu_id, &spu_lang);
			return spu_id;
		}
		case sUser+6:
		case sUser+7:
		case sUser+8:
			return resIsPyObject;
#ifdef DDVD_SUPPORTS_PICTURE_INFO
		case sVideoWidth:
			return m_width;
		case sVideoHeight:
			return m_height;
		case sAspect:
			return m_aspect;
		case sProgressive:
			return m_progressive;
		case sFrameRate:
			return m_framerate;
#endif
		default:
			return resNA;
	}
}

std::string eServiceDVD::getInfoString(int w)
{
	switch(w)
	{
		case sServiceref:
			return m_ref.toString();
		default:
			eDebug("unhandled getInfoString(%d)", w);
	}
	return "";
}

ePtr<iServiceInfoContainer> eServiceDVD::getInfoObject(int w)
{
	eServiceDVDInfoContainer *container = new eServiceDVDInfoContainer;
	ePtr<iServiceInfoContainer> retval = container;
	eDebug("eServiceDVD::getInfoObject %d", w);
	switch (w)
	{
		case sUser + 6:
		{
			int audio_id,audio_type;
			uint16_t audio_lang;
			ddvd_get_last_audio(m_ddvdconfig, &audio_id, &audio_lang, &audio_type);
			char audio_string[3] = {audio_lang >> 8, audio_lang, 0};
			container->addInteger(audio_id + 1);
			container->addString(audio_string);
			switch (audio_type)
			{
			case DDVD_MPEG:
				container->addString("MPEG");
				break;
			case DDVD_AC3:
				container->addString("AC3");
				break;
			case DDVD_DTS:
				container->addString("DTS");
				break;
			case DDVD_LPCM:
				container->addString("LPCM");
				break;
			}
			break;
		}
		case sUser + 7:
		{
			int spu_id;
			uint16_t spu_lang;
			ddvd_get_last_spu(m_ddvdconfig, &spu_id, &spu_lang);
			char spu_string[3] = {spu_lang >> 8, spu_lang, 0};
			if (spu_id == -1)
			{
				container->addInteger(0);
				container->addString("");
			}
			else
			{
				container->addInteger(spu_id + 1);
				container->addString(spu_string);
			}
			break;
		}
		case sUser + 8:
		{
			int current, num;
			ddvd_get_angle_info(m_ddvdconfig, &current, &num);
			container->addInteger(current);
			container->addInteger(num);
			break;
		}
		default:
			eDebug("unhandled getInfoObject(%d)", w);
	}
	return retval;
}

RESULT eServiceDVD::enableSubtitles(iSubtitleUser *user, SubtitleTrack &track)
{
	eSize size = eSize(720, 576);

	if (m_subtitle_widget) m_subtitle_widget->destroy();
	m_subtitle_widget = user;

	int pid = -1;

	if (track.pid >= 0)
	{
		pid = track.pid - 1;

		ddvd_set_spu(m_ddvdconfig, pid);
		m_event(this, evUser+7);
	}

	eDebug("eServiceDVD::enableSubtitles %i", pid);

	if (!m_pixmap)
	{
		m_pixmap = new gPixmap(size, 32, 1); /* allocate accel surface (if possible) */
#ifdef DDVD_SUPPORTS_GET_BLIT_DESTINATION
		ddvd_set_lfb_ex(m_ddvdconfig, (unsigned char *)m_pixmap->surface->data, size.width(), size.height(), 4, size.width()*4, 1);
#else
		ddvd_set_lfb(m_ddvdconfig, (unsigned char *)m_pixmap->surface->data, size.width(), size.height(), 4, size.width()*4);
#warning please update libdreamdvd for fast scaling
#endif
		run(); // start the thread
	}

	return 0;
}

RESULT eServiceDVD::disableSubtitles()
{
	if (m_subtitle_widget) m_subtitle_widget->destroy();
	m_subtitle_widget = 0;
	return 0;
}

RESULT eServiceDVD::getSubtitleList(std::vector<struct SubtitleTrack> &subtitlelist)
{
	unsigned int spu_count = 0;
	ddvd_get_spu_count(m_ddvdconfig, &spu_count);

	for ( unsigned int spu_id = 0; spu_id < spu_count; spu_id++ )
	{
		struct SubtitleTrack track;
		uint16_t spu_lang;
		ddvd_get_spu_byid(m_ddvdconfig, spu_id, &spu_lang);
		char spu_string[3]={spu_lang >> 8, spu_lang, 0};

		track.type = 2;
		track.pid = spu_id + 1;
		track.page_number = 5;
		track.magazine_number = 0;
		track.language_code = spu_string;
		subtitlelist.push_back(track);
	}
	return 0;
}

RESULT eServiceDVD::getCachedSubtitle(struct SubtitleTrack &track)
{
	eDebug("eServiceDVD::getCachedSubtitle nyi");
	return -1;
}

RESULT eServiceDVD::getLength(pts_t &len)
{
// 	eDebug("eServiceDVD::getLength");
	struct ddvd_time info;
	ddvd_get_last_time(m_ddvdconfig, &info);
	len = info.end_hours * 3600;
	len += info.end_minutes * 60;
	len += info.end_seconds;
	len *= 90000;
	return 0;
}

RESULT eServiceDVD::seekTo(pts_t to)
{
	eDebug("eServiceDVD::seekTo(%lld)",to);
	if ( to > 0 )
	{
		eDebug("set_resume_pos: resume_info.title=%d, chapter=%d, block=%lu, audio_id=%d, audio_lock=%d, spu_id=%d, spu_lock=%d",m_resume_info.title,m_resume_info.chapter,m_resume_info.block,m_resume_info.audio_id, m_resume_info.audio_lock, m_resume_info.spu_id, m_resume_info.spu_lock);
		ddvd_set_resume_pos(m_ddvdconfig, m_resume_info);
	}
	return 0;
}

RESULT eServiceDVD::seekRelative(int direction, pts_t to)
{
	int seconds = to / 90000;
	seconds *= direction;
	eDebug("seekRelative %d %d", direction, seconds);
	ddvd_skip_seconds(m_ddvdconfig, seconds);
	return 0;
}

RESULT eServiceDVD::getPlayPosition(pts_t &pos)
{
	struct ddvd_time info;
	ddvd_get_last_time(m_ddvdconfig, &info);
	pos = info.pos_hours * 3600;
	pos += info.pos_minutes * 60;
	pos += info.pos_seconds;
// 	eDebug("getPlayPosition %lld", pos);
	pos *= 90000;
	return 0;
}

RESULT eServiceDVD::seekTitle(int title)
{
	eDebug("setTitle %d", title);
	ddvd_set_title(m_ddvdconfig, title);
	return 0;
}

RESULT eServiceDVD::seekChapter(int chapter)
{
	eDebug("setChapter %d", chapter);
	if ( chapter > 0 )
		ddvd_set_chapter(m_ddvdconfig, chapter);
	return 0;
}

RESULT eServiceDVD::setTrickmode(int /*trick*/)
{
	return -1;
}

RESULT eServiceDVD::isCurrentlySeekable()
{
	return m_state == stRunning ? 3 : 0;
}

RESULT eServiceDVD::keyPressed(int key)
{
	switch(key)
	{
	case iServiceKeys::keyLeft:
		ddvd_send_key(m_ddvdconfig, DDVD_KEY_LEFT);
		break;
	case iServiceKeys::keyRight:
		ddvd_send_key(m_ddvdconfig, DDVD_KEY_RIGHT);
		break;
	case iServiceKeys::keyUp:
		ddvd_send_key(m_ddvdconfig, DDVD_KEY_UP);
		break;
	case iServiceKeys::keyDown:
		ddvd_send_key(m_ddvdconfig, DDVD_KEY_DOWN);
		break;
	case iServiceKeys::keyOk:
		ddvd_send_key(m_ddvdconfig, DDVD_KEY_OK);
		break;
	case iServiceKeys::keyUser:
		ddvd_send_key(m_ddvdconfig, DDVD_KEY_AUDIO);
		break;
	case iServiceKeys::keyUser+1:
		ddvd_send_key(m_ddvdconfig, DDVD_KEY_SUBTITLE);
		break;
	case iServiceKeys::keyUser+2:
		ddvd_send_key(m_ddvdconfig, DDVD_KEY_AUDIOMENU);
		break;
	case iServiceKeys::keyUser+3:
		ddvd_send_key(m_ddvdconfig, DDVD_KEY_NEXT_CHAPTER);
		break;
	case iServiceKeys::keyUser+4:
		ddvd_send_key(m_ddvdconfig, DDVD_KEY_PREV_CHAPTER);
		break;
	case iServiceKeys::keyUser+5:
		ddvd_send_key(m_ddvdconfig, DDVD_KEY_NEXT_TITLE);
		break;
	case iServiceKeys::keyUser+6:
		ddvd_send_key(m_ddvdconfig, DDVD_KEY_PREV_TITLE);
		break;
	case iServiceKeys::keyUser+7:
		ddvd_send_key(m_ddvdconfig, DDVD_KEY_MENU);
		break;
	case iServiceKeys::keyUser+8:
		ddvd_send_key(m_ddvdconfig, DDVD_KEY_ANGLE);
		break;
	default:
		return -1;
	}
	return 0;
}

RESULT eServiceDVD::cueSheet(ePtr<iCueSheet> &ptr)
{
	if (m_cue_pts)
	{
		ptr = this;
		return 0;
	}
	ptr = 0;
	return -1;
}

PyObject *eServiceDVD::getCutList()
{
	ePyObject list = PyList_New(1);
	ePyObject tuple = PyTuple_New(2);
	PyTuple_SetItem(tuple, 0, PyLong_FromLongLong(m_cue_pts));
	PyTuple_SetItem(tuple, 1, PyInt_FromLong(3));
	PyList_SetItem(list, 0, tuple);
	return list;
}

void eServiceDVD::setCutList(ePyObject /*list*/)
{
}

void eServiceDVD::setCutListEnable(int /*enable*/)
{
}

void eServiceDVD::loadCuesheet()
{
	FILE* f;
	{
		std::string filename = m_ref.path;
		filename += "/dvd.cuts";
		f = fopen(filename.c_str(), "rb");
	}
	if (f == NULL)
	{
		char filename[128];
		if ( m_ddvd_titlestring[0] != '\0' )
			snprintf(filename, sizeof(filename), "/home/root/dvd-%s.cuts", m_ddvd_titlestring);
		else
		{
			struct stat st;
			if (stat(m_ref.path.c_str(), &st) == 0)
			{
				// DVD has no name and cannot be written. Use the mtime to generate something unique...
				snprintf(filename, 128, "/home/root/dvd-%x.cuts", st.st_mtime);
			}
			else
			{
				strcpy(filename, "/home/root/dvd-untitled.cuts");
			}
		}
		eDebug("eServiceDVD::loadCuesheet() filename=%s",filename);
		f = fopen(filename, "rb");
	}


	if (f)
	{
		unsigned long long where;
		unsigned int what;

		if (!fread(&where, sizeof(where), 1, f))
			return;
		if (!fread(&what, sizeof(what), 1, f))
			return;

		where = be64toh(where);
		what = ntohl(what);

		if (!fread(&m_resume_info, sizeof(struct ddvd_resume), 1, f))
			return;
		if (!fread(&what, sizeof(what), 1, f))
			return;

		what = ntohl(what);
		if (what != 4 )
			return;

 		m_cue_pts = where;

		fclose(f);
	} else
		eDebug("cutfile not found!");

	if (m_cue_pts)
	{
		m_event((iPlayableService*)this, evCuesheetChanged);
		eDebug("eServiceDVD::loadCuesheet() pts=%lld",m_cue_pts);
	}
}

void eServiceDVD::saveCuesheet()
{
	eDebug("eServiceDVD::saveCuesheet()");

	struct ddvd_resume resume_info;
	ddvd_get_resume_pos(m_ddvdconfig, &resume_info);

	if (resume_info.title)
	{
		struct ddvd_time info;
		ddvd_get_last_time(m_ddvdconfig, &info);
		pts_t pos;
		pos = info.pos_hours * 3600;
		pos += info.pos_minutes * 60;
		pos += info.pos_seconds;
		pos *= 90000;
		m_cue_pts = pos;
	 	eDebug("ddvd_get_resume_pos resume_info.title=%d, chapter=%d, block=%lu, audio_id=%d, audio_lock=%d, spu_id=%d, spu_lock=%d  (pts=%llu)",resume_info.title,resume_info.chapter,resume_info.block,resume_info.audio_id, resume_info.audio_lock, resume_info.spu_id, resume_info.spu_lock,m_cue_pts);
	}
	else
	{
		eDebug("we're in a menu or somewhere else funny. so save cuesheet with pts=0");
		m_cue_pts = 0;
	}

	FILE* f;
	{
		std::string filename = m_ref.path;
		filename += "/dvd.cuts";
		f = fopen(filename.c_str(), "wb");
	}
	if (f == NULL)
	{
		char filename[128];
		if ( m_ddvd_titlestring[0] != '\0' )
			snprintf(filename, sizeof(filename), "/home/root/dvd-%s.cuts", m_ddvd_titlestring);
		else
		{
			struct stat st;
			if (stat(m_ref.path.c_str(), &st) == 0)
			{
				// DVD has no name and cannot be written. Use the mtime to generate something unique...
				snprintf(filename, 128, "/home/root/dvd-%x.cuts", st.st_mtime);
			}
			else
			{
				strcpy(filename, "/home/root/dvd-untitled.cuts");
			}
		}
		eDebug("eServiceDVD::saveCuesheet() filename=%s",filename);
		f = fopen(filename, "wb");
	}

	if (f)
	{
		unsigned long long where;
		int what;

		where = htobe64(m_cue_pts);
		what = htonl(3);
		fwrite(&where, sizeof(where), 1, f);
		fwrite(&what, sizeof(what), 1, f);

		what = htonl(4);
		fwrite(&resume_info, sizeof(struct ddvd_resume), 1, f);
		fwrite(&what, sizeof(what), 1, f);

		fclose(f);
	}
}

eAutoInitPtr<eServiceFactoryDVD> init_eServiceFactoryDVD(eAutoInitNumbers::service+1, "eServiceFactoryDVD");

PyMODINIT_FUNC
initservicedvd(void)
{
	Py_InitModule("servicedvd", NULL);
}
