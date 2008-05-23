/* yes, it's dvd  */
#include "servicedvd.h"
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

// eServiceFactoryDVD

eServiceFactoryDVD::eServiceFactoryDVD()
{
	ePtr<eServiceCenter> sc;
	
	eServiceCenter::getPrivInstance(sc);
	if (sc)
	{
		std::list<std::string> extensions;
		extensions.push_back("iso");
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
	ptr = new eServiceDVD(ref.path.c_str());
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

// eServiceDVD

DEFINE_REF(eServiceDVD);

eServiceDVD::eServiceDVD(const char *filename):
	m_filename(filename),
	m_ddvdconfig(ddvd_create()),
	m_pixmap(new gPixmap(eSize(720, 576), 32)),
	m_subtitle_widget(0),
	m_state(stIdle),
	m_current_trick(0),
	m_sn(eApp, ddvd_get_messagepipe_fd(m_ddvdconfig), eSocketNotifier::Read|eSocketNotifier::Priority|eSocketNotifier::Error|eSocketNotifier::Hungup),
	m_pump(eApp, 1)
{
	std::string aspect;
	eDebug("SERVICEDVD construct!");
	// create handle
	ddvd_set_dvd_path(m_ddvdconfig, filename);
	ddvd_set_ac3thru(m_ddvdconfig, 0);
	ddvd_set_language(m_ddvdconfig, "de");

	if (ePythonConfigQuery::getConfigValue("config.av.aspect", aspect) != 0)
		aspect = "16_9";
	if (aspect == "4_3_letterbox")
		ddvd_set_video(m_ddvdconfig, DDVD_4_3_LETTERBOX, DDVD_PAL);
	else if (aspect == "4_3_panscan")
		ddvd_set_video(m_ddvdconfig, DDVD_4_3_PAN_SCAN, DDVD_PAL);
	else
		ddvd_set_video(m_ddvdconfig, DDVD_16_9, DDVD_PAL);

	ddvd_set_lfb(m_ddvdconfig, (unsigned char *)m_pixmap->surface->data, 720, 576, 4, 720*4);
	CONNECT(m_sn.activated, eServiceDVD::gotMessage);
	CONNECT(m_pump.recv_msg, eServiceDVD::gotThreadMessage);
	strcpy(m_ddvd_titlestring,"");
	m_cue_pts = 0;
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
			if (m_subtitle_widget)
				m_subtitle_widget->setPixmap(m_pixmap, eRect(0, 0, 720, 576));
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
			eDebug("DVD_SHOWOSD_STRING!");
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
		default:
			break;
	}
}

eServiceDVD::~eServiceDVD()
{
	eDebug("SERVICEDVD destruct!");
	kill();
	ddvd_close(m_ddvdconfig);
}

RESULT eServiceDVD::connectEvent(const Slot2<void,iPlayableService*,int> &event, ePtr<eConnection> &connection)
{
	connection = new eConnection((iPlayableService*)this, m_event.connect(event));
	return 0;
}

RESULT eServiceDVD::start()
{
	assert(m_state == stIdle);
	m_state = stRunning;
	eDebug("eServiceDVD starting");
	run();
// 	m_event(this, evStart);
	return 0;
}

RESULT eServiceDVD::stop()
{
	assert(m_state != stIdle);
	if (m_state == stStopped)
		return -1;
	eDebug("DVD: stop %s", m_filename.c_str());
	m_state = stStopped;
	ddvd_send_key(m_ddvdconfig, DDVD_KEY_EXIT);
	struct ddvd_time info;
	ddvd_get_last_time(m_ddvdconfig, &info);
	if ( info.pos_chapter < info.end_chapter )
	{
		pts_t pos;
		pos = info.pos_hours * 3600;
		pos += info.pos_minutes * 60;
		pos += info.pos_seconds;
		pos *= 90000;
		pos += info.pos_title * 256;
		pos += info.pos_chapter;
		m_cue_pts = pos;
		eDebug("POS %llu\n", m_cue_pts);
	}
	saveCuesheet();
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

RESULT eServiceDVD::keys(ePtr<iServiceKeys> &ptr)
{
	ptr=this;
	return 0;
}

	// iPausableService
RESULT eServiceDVD::setSlowMotion(int /*ratio*/)
{
	return -1;
}

RESULT eServiceDVD::setFastForward(int trick)
{
	eDebug("setTrickmode(%d)", trick);
	while (m_current_trick > trick && m_current_trick != -64)
	{
		ddvd_send_key(m_ddvdconfig, DDVD_KEY_FBWD);
		if (m_current_trick == 0)
			m_current_trick = -2;
		else if (m_current_trick > 0)
		{
			m_current_trick /= 2;
			if (abs(m_current_trick) == 1)
				m_current_trick=0;
		}
		else
			m_current_trick *= 2;
	}
	while (m_current_trick < trick && m_current_trick != 64)
	{
		ddvd_send_key(m_ddvdconfig, DDVD_KEY_FFWD);
		if (m_current_trick == 0)
			m_current_trick = 2;
		else if (m_current_trick < 0)
		{
			m_current_trick /= 2;
			if (abs(m_current_trick) == 1)
				m_current_trick=0;
		}
		else
			m_current_trick *= 2;
	}
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
		name = m_filename;
	return 0;
}

int eServiceDVD::getInfo(int w)
{
	switch (w)
		{
		case sUser:
		case sArtist:
		case sAlbum:
			return resIsPyObject;  // then getInfoObject should be called
		case sComment:
		case sTracknumber:
		case sGenre:
			return resIsString;  // then getInfoString should be called
		case sUser+8:
		{
			struct ddvd_time info;
			ddvd_get_last_time(m_ddvdconfig, &info);
			return info.pos_chapter;
		}
		case sUser+80:
		{
			struct ddvd_time info;
			ddvd_get_last_time(m_ddvdconfig, &info);
			return info.end_chapter;
		}
		case sUser+9:
		{
			struct ddvd_time info;
			ddvd_get_last_time(m_ddvdconfig, &info);
			return info.pos_title;
		}
		case sUser+90:
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
		default:
			return resNA;
	}
}

std::string eServiceDVD::getInfoString(int w)
{
	switch(w)
	{
		case sUser+7: {
			int spu_id;
			uint16_t spu_lang;
			ddvd_get_last_spu(m_ddvdconfig, &spu_id, &spu_lang);
			unsigned char spu_string[3]={spu_lang >> 8, spu_lang, 0};
			char osd[100];
			if (spu_id == -1)
				sprintf(osd,"");
			else
				sprintf(osd,"%d - %s",spu_id+1,spu_string);
// 			lbo_changed=1;
			return osd;
			}
		case sUser+6:
			{
			int audio_id,audio_type;
			uint16_t audio_lang;
			ddvd_get_last_audio(m_ddvdconfig, &audio_id, &audio_lang, &audio_type);
			char audio_string[3]={audio_lang >> 8, audio_lang, 0};
			char audio_form[5];
			switch(audio_type)
			{
				case DDVD_MPEG:
					sprintf(audio_form,"MPEG");
					break;
				case DDVD_AC3:
					sprintf(audio_form,"AC3");
					break;
				case DDVD_DTS:
					sprintf(audio_form,"DTS");
					break;
				case DDVD_LPCM:
					sprintf(audio_form,"LPCM");
					break;
				default:
					sprintf(audio_form,"-");
			}
			char osd[100];
			sprintf(osd,"%d - %s (%s)",audio_id+1,audio_string,audio_form);
			return osd;
			}
		default:
			eDebug("unhandled getInfoString(%d)", w);
	}
	return "";
}

PyObject *eServiceDVD::getInfoObject(int w)
{
	switch(w)
	{
		default:
			eDebug("unhandled getInfoObject(%d)", w);
	}
	Py_RETURN_NONE;
}

RESULT eServiceDVD::enableSubtitles(eWidget *parent, SWIG_PYOBJECT(ePyObject) /*entry*/)
{
	if (m_subtitle_widget)
		delete m_subtitle_widget;
	m_subtitle_widget = new eSubtitleWidget(parent);
	m_subtitle_widget->resize(parent->size());
	m_subtitle_widget->setPixmap(m_pixmap, eRect(0, 0, 720, 576));
	m_subtitle_widget->setZPosition(-1);
	m_subtitle_widget->show();
	return 0;
}

RESULT eServiceDVD::disableSubtitles(eWidget */*parent*/)
{
	delete m_subtitle_widget;
	m_subtitle_widget = 0;
	return 0;
}

PyObject *eServiceDVD::getSubtitleList()
{
	eDebug("eServiceDVD::getSubtitleList nyi");
	Py_RETURN_NONE;
}

PyObject *eServiceDVD::getCachedSubtitle()
{
	eDebug("eServiceDVD::getCachedSubtitle nyi");
	Py_RETURN_NONE;
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
	struct ddvd_time info;
	to /= 90000;
	int cur;
	ddvd_get_last_time(m_ddvdconfig, &info);
	cur = info.pos_hours * 3600;
	cur += info.pos_minutes * 60;
	cur += info.pos_seconds;
	eDebug("seekTo %lld, cur %d, diff %lld", to, cur, to - cur);
	ddvd_skip_seconds(m_ddvdconfig, to - cur);
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
	return m_state == stRunning;
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
	eDebug("eServiceDVD::loadCuesheet()");
	char filename[128];
	if ( m_ddvd_titlestring[0] != '\0' )
		snprintf(filename, 128, "/home/root/dvd-%s.cuts", m_ddvd_titlestring);

	eDebug("eServiceDVD::loadCuesheet() filename=%s",filename);

	FILE *f = fopen(filename, "rb");

	if (f)
	{
		eDebug("loading cuts..");
		unsigned long long where;
		unsigned int what;

		if (!fread(&where, sizeof(where), 1, f))
			return;

		if (!fread(&what, sizeof(what), 1, f))
			return;
			
#if BYTE_ORDER == LITTLE_ENDIAN
		where = bswap_64(where);
#endif
		what = ntohl(what);

		m_cue_pts = where;
		fclose(f);
	} else
		eDebug("cutfile not found!");

	eDebug("eServiceDVD::loadCuesheet() pts=%lld",m_cue_pts);

	if (m_cue_pts)
		m_event((iPlayableService*)this, evCuesheetChanged);
}

void eServiceDVD::saveCuesheet()
{
	eDebug("eServiceDVD::saveCuesheet() pts=%lld",m_cue_pts);
	char filename[128];
	if ( m_ddvd_titlestring[0] != '\0' )
		snprintf(filename, 128, "/home/root/dvd-%s.cuts", m_ddvd_titlestring);
	
	FILE *f = fopen(filename, "wb");

	if (f)
	{
		unsigned long long where;
		int what;

		{
#if BYTE_ORDER == BIG_ENDIAN
			where = m_cue_pts;
#else
			where = bswap_64(m_cue_pts);
#endif
			what = 3;
			fwrite(&where, sizeof(where), 1, f);
			fwrite(&what, sizeof(what), 1, f);
		}
		fclose(f);
	}
}

eAutoInitPtr<eServiceFactoryDVD> init_eServiceFactoryDVD(eAutoInitNumbers::service+1, "eServiceFactoryDVD");

PyMODINIT_FUNC
initservicedvd(void)
{
	Py_InitModule("servicedvd", NULL);
}
