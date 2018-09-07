#include <lib/driver/rcinput.h>

#include <lib/base/eerror.h>

#include <sys/ioctl.h>
#include <linux/input.h>
#include <linux/kd.h>
#include <sys/stat.h>
#include <fcntl.h>

#include <lib/base/ebase.h>
#include <lib/base/init.h>
#include <lib/base/init_num.h>
#include <lib/driver/input_fake.h>

static bool bflag;

void eRCDeviceInputDev::handleCode(long rccode)
{
	struct input_event *ev = (struct input_event *)rccode;

#if WETEKRC
/*
	eDebug("[eRCDeviceInputDev] ==> BEFORE check for evtype: %x %x %x", ev->value, ev->code, ev->type);
	eDebug("[eRCDeviceInputDev] ==> BEFORE check for evtype:-->BackspaceFLAG %d", bflag);
*/
	if (ev->code == KEY_BACKSPACE && ev->value == 1 ) {
		bflag = !bflag;
	}
/*
	eDebug("[eRCDeviceInputDev] ==> BEFORE check for evtype after check for evvalue:-->BackspaceFLAG %d", bflag);
*/
#endif

	if (ev->type != EV_KEY)
		return;
		
	eDebug("[eRCDeviceInputDev] %x %x %x", ev->value, ev->code, ev->type);

	int km = iskeyboard ? input->getKeyboardMode() : eRCInput::kmNone;

	switch (ev->code)
	{
		case KEY_LEFTSHIFT:
		case KEY_RIGHTSHIFT:
			shiftState = ev->value;
			break;
		case KEY_CAPSLOCK:
			if (ev->value == 1)
				capsState = !capsState;
			break;
	}

	if (km == eRCInput::kmAll)
		return;

	if (km == eRCInput::kmAscii)
	{
		bool ignore = false;
		bool ascii = (ev->code > 0 && ev->code < 61);

		switch (ev->code)
		{
			case KEY_LEFTCTRL:
			case KEY_RIGHTCTRL:
			case KEY_LEFTSHIFT:
			case KEY_RIGHTSHIFT:
			case KEY_LEFTALT:
			case KEY_RIGHTALT:
			case KEY_CAPSLOCK:
				ignore = true;
				break;
			case KEY_RESERVED:
			case KEY_ESC:
			case KEY_TAB:
			case KEY_BACKSPACE:
/*
				bflag = !bflag;
				eDebug("[eRCDeviceInputDev] --> AFTER flip BackspaceFLAG %d", bflag);
*/
			case KEY_ENTER:
			case KEY_INSERT:
			case KEY_DELETE:
			case KEY_MUTE:
				ascii = false;
			default:
				break;
		}

		if (ignore)
			return;

		if (ascii)
		{
			if (ev->value)
			{
				if (consoleFd >= 0)
				{
					struct kbentry ke;
					/* off course caps is not the same as shift, but this will have to do for now */
					ke.kb_table = (shiftState || capsState) ? K_SHIFTTAB : K_NORMTAB;
					ke.kb_index = ev->code;
					::ioctl(consoleFd, KDGKBENT, &ke);
					if (ke.kb_value)
						input->keyPressed(eRCKey(this, ke.kb_value & 0xff, eRCKey::flagAscii)); /* emit */
				}
			}
			return;
		}
	}

#if TIVIARRC
	if (ev->code == KEY_EPG) {
		ev->code = KEY_INFO;
	}
	else if (ev->code == KEY_MEDIA) {
		ev->code = KEY_EPG;
	}
	else if (ev->code == KEY_INFO) {
		ev->code = KEY_BACK;
	}
	else if (ev->code == KEY_PREVIOUS) {
		ev->code = KEY_SUBTITLE;
	}
	else if (ev->code == KEY_NEXT) {
		ev->code = KEY_TEXT;
	}
	else if (ev->code == KEY_BACK) {
		ev->code = KEY_MEDIA;
	}
	else if (ev->code == KEY_PLAYPAUSE) {
		ev->code = KEY_PLAY;
	}
	else if (ev->code == KEY_RECORD) {
		ev->code = KEY_PREVIOUS;
	}
	else if (ev->code == KEY_STOP) {
		ev->code = KEY_PAUSE;
	}
	else if (ev->code == KEY_PROGRAM) {
		ev->code = KEY_STOP;
	}
	else if (ev->code == KEY_BOOKMARKS) {
		ev->code = KEY_RECORD;
	}
	else if (ev->code == KEY_SLEEP) {
		ev->code = KEY_NEXT;
	}
	else if (ev->code == KEY_TEXT) {
		ev->code = KEY_PAGEUP;
	}
	else if (ev->code == KEY_SUBTITLE) {
		ev->code = KEY_PAGEDOWN;
	}
	else if (ev->code == KEY_LIST) {
		ev->code = KEY_F3;
	}
	else if (ev->code ==  KEY_RADIO) {
		ev->code =  KEY_MODE;
	}
	else if (ev->code == KEY_AUDIO) {
		ev->code = KEY_TV;
	}
	else if (ev->code == KEY_HELP) {
		ev->code = KEY_SLEEP;
	}
	else if (ev->code == KEY_TV) {
		ev->code = KEY_VMODE;
	}
#endif

#if WETEKRC
/*
	eDebug("[eRCDeviceInputDev] -->BackspaceFLAG %d", bflag);
	eDebug("[eRCDeviceInputDev] -->before change %x %x %x", ev->value, ev->code, ev->type);
*/
/* default is with NO numerc keys !!!*/
	if (bflag) {
		if (ev->code == KEY_1) {
			ev->code = KEY_RED;
		}
		if (ev->code == KEY_2) {
			ev->code = KEY_GREEN;
		}
		if (ev->code == KEY_3) {
			ev->code = KEY_YELLOW;
		}
		if (ev->code == KEY_4) {
			ev->code = KEY_BLUE;
		}
		if (ev->code == KEY_5) {
			ev->code = KEY_PREVIOUS;
		}
		if (ev->code == KEY_6) {
			ev->code = KEY_NEXT;
		}
		if (ev->code == KEY_7) {
			ev->code = KEY_REWIND;
		}
		if (ev->code == KEY_8) {
			ev->code = KEY_STOP;
		}
		if (ev->code == KEY_9) {
			ev->code = KEY_FASTFORWARD;
		}
		if (ev->code == KEY_0) {
			ev->code = KEY_PLAYPAUSE;
		}
	}
/*
	eDebug("[eRCDeviceInputDev] -->BackspaceFLAG %d", bflag);
	eDebug("[eRCDeviceInputDev] -->after change %x %x %x", ev->value, ev->code, ev->type);
*/
#endif

#if KEY_F6_TO_KEY_FAVORITES
	if (ev->code == KEY_F6) {
		ev->code = KEY_FAVORITES;
	}
#endif

#if KEY_HELP_TO_KEY_AUDIO
	if (ev->code == KEY_HELP) {
		ev->code = KEY_AUDIO;
	}
#endif


#if KEY_WWW_TO_KEY_FILE
	if (ev->code == KEY_WWW) {
		ev->code = KEY_FILE;
	}
#endif

#if KEY_CONTEXT_MENU_TO_KEY_BACK
	if (ev->code == KEY_CONTEXT_MENU) {
		ev->code = KEY_BACK;
	}
#endif

#if KEY_VIDEO_TO_KEY_ANGLE
	if (ev->code == KEY_VIDEO) {
		ev->code = KEY_ANGLE;
	}
#endif

#if KEY_F7_TO_KEY_MENU
	if (ev->code == KEY_F7) {
		ev->code = KEY_MENU;
	}
#endif

#if KEY_F1_TO_KEY_MEDIA
	if (ev->code == KEY_F1) {
		ev->code = KEY_MEDIA;
	}
#endif

#if KEY_HOME_TO_KEY_INFO
	if (ev->code == KEY_HOME) {
		ev->code = KEY_INFO;
	}
#endif

#if KEY_BACK_TO_KEY_EXIT
	if (ev->code == KEY_BACK) {
		ev->code = KEY_EXIT;
	}
#endif

#if KEY_F2_TO_KEY_EPG
	if (ev->code == KEY_F2) {
		ev->code = KEY_EPG;
	}
#endif

#if KEY_ENTER_TO_KEY_OK
	if (ev->code == KEY_ENTER) {
		ev->code = KEY_OK;
	}
#endif

#if KEY_BOOKMARKS_TO_KEY_MEDIA
	if (ev->code == KEY_BOOKMARKS)
	{
		/* formuler and triplex remote send wrong keycode */
		ev->code = KEY_MEDIA;
	}
#endif

#if KEY_VIDEO_TO_KEY_FAVORITES
	if (ev->code == KEY_VIDEO)
	{
		/* formuler rcu fav key send key_media change this to  KEY_FAVORITES */
		ev->code = KEY_FAVORITES;
	}
#endif

#if KEY_FAV_TO_KEY_PVR
	if (ev->code == KEY_FAVORITES)
	{
		/* tomcat remote dont have a PVR Key. Correct this, so we do not have to place hacks in the keymaps. */
		ev->code = KEY_PVR;
	}
#endif

#if KEY_LAST_TO_KEY_PVR
	if (ev->code == KEY_LAST)
	{
		/* xwidowx Remote rc has a Funktion key, which sends KEY_LAST events but we need a KEY_PVR. Correct this, so we do not have to place hacks in the keymaps. */
		ev->code = KEY_PVR;
	}
#endif

#if KEY_LAST_TO_KEY_BACK
	if (ev->code == KEY_LAST)
	{
		/* sf108 Remote rc has a Funktion key, which sends KEY_LAST events but we need a KEY_BACK. Correct this, so we do not have to place hacks in the keymaps. */
		ev->code = KEY_BACK;
	}
#endif

#if KEY_MEDIA_TO_KEY_LIST
	if (ev->code == KEY_MEDIA)
	{
		/* entwodia Remote rc has a Funktion key, which sends KEY_MEDIA events but we need a KEY_LIST. Correct this, so we do not have to place hacks in the keymaps. */
		ev->code = KEY_LIST;
	}
#endif

#if KEY_F1_TO_KEY_F2
	if (ev->code == KEY_F1)
	{
		/* ET7X00 Remote rc has a Funktion key, which sends KEY_F1 events but we need a KEY_F2. Correct this, so we do not have to place hacks in the keymaps. */
		ev->code = KEY_F2;
	}
#endif

#if KEY_INFO_TO_KEY_EPG
	if (ev->code == KEY_INFO)
	{
		/* vu Remote rc has a EPG key, which sends KEY_INFO events but we need a KEY_EPG. Correct this, so we do not have to place hacks in the keymaps. */
		ev->code = KEY_EPG;
	}
#endif

#if KEY_HELP_TO_KEY_INFO
	if (ev->code == KEY_HELP)
	{
		/* vu Remote rc has a HELP key, which sends KEY_HELP events but we need a KEY_INFO. Correct this, so we do not have to place hacks in the keymaps. */
		ev->code = KEY_INFO;
	}
#endif

#if KEY_MODE_TO_KEY_AUDIO
	if (ev->code == KEY_MODE)
	{
		/* ebox Remote rc has a AV key, which sends KEY_MODE events. Correct this, so we do not have to place hacks in the keymaps. */
		ev->code = KEY_AUDIO;
	}
#endif

#if KEY_VIDEO_IS_KEY_SCREEN
	if (ev->code == KEY_VIDEO)
	{
		/* Blackbox Remote rc has a KEY_PIP key, which sends KEY_VIDEO events. Correct this, so we do not have to place hacks in the keymaps. */
		ev->code = KEY_SCREEN;
	}
#endif

#if KEY_ARCHIVE_TO_KEY_DIRECTORY
	if (ev->code == KEY_ARCHIVE)
	{
		/* Blackbox Remote rc has a KEY_PLUGIN key, which sends KEY_ARCHIVE events. Correct this, so we do not have to place hacks in the keymaps. */
		ev->code = KEY_DIRECTORY;
	}
#endif

#if KEY_TIME_TO_KEY_SLOW
	if (ev->code == KEY_TIME)
	{
		/* Blackbox Remote rc has a KEY_PLUGIN key, which sends KEY_TIME events. Correct this, so we do not have to place hacks in the keymaps. */
		ev->code = KEY_SLOW;
	}
#endif
	
#if KEY_TEXT_TO_KEY_AUDIO
	if (ev->code == KEY_AUDIO)
	{
		/* AZBOX rc has a KEY aux key, which sends KEY_TEXT events. Correct this, so we do not have to place hacks in the keymaps. */
		ev->code = KEY_TEXT;
	}
	else if (ev->code == KEY_AUDIO)
	{
		/* AZBOX rc has a KEY Check key, which sends KEY_AUDIO events. Correct this, so we do not have to place hacks in the keymaps. */
		ev->code = KEY_TEXT;
	}
#endif

#if KEY_CONTEXT_MENU_TO_KEY_AUX
	if (ev->code == KEY_CONTEXT_MENU)
	{
		/* Gigablue New Remote rc has a KEY_HDMI-IN, which sends KEY_CONTEXT_MENU events. Correct this, so we do not have to place hacks in the keymaps. */
		ev->code = KEY_AUX;
	}
#endif

#if KEY_F2_TO_KEY_F6
	if (ev->code == KEY_F2)
	{
		/* Gigablue New Remote rc has a KEY_PIP key, which sends KEY_F2 events. Correct this, so we do not have to place hacks in the keymaps. */
		ev->code = KEY_F6;
	}
#endif

#if KEY_F1_TO_KEY_F6
	if (ev->code == KEY_F1)
	{
		ev->code = KEY_F6;
	}
#endif

#if KEY_F2_TO_KEY_AUX
	if (ev->code == KEY_F2)
	{
		ev->code = KEY_AUX;
	}
#endif

#if KEY_F3_TO_KEY_LIST
	if (ev->code == KEY_F3)
	{
		/* Xtrend New Remote rc has a KEY_F3 key, which sends KEY_LIST events. Correct this, so we do not have to place hacks in the keymaps. */
		ev->code = KEY_LIST;
	}
#endif

#if KEY_TV_TO_KEY_MODE
	if (ev->code == KEY_TV)
	{
		/* AZBOX rc has a KEY_MODE key, which sends KEY_TV events. Correct this, so we do not have to place hacks in the keymaps. */
		ev->code = KEY_MODE;
	}
#endif

#if KEY_VIDEO_TO_KEY_EPG
	if (ev->code == KEY_VIDEO)
	{
		/* AZBOX rc has a KEY_EPG key, which sends KEY_VIDEO events. Correct this, so we do not have to place hacks in the keymaps. */
		ev->code = KEY_EPG;
	}
#endif

#if KEY_VIDEO_TO_KEY_SUBTITLE
	if (ev->code == KEY_VIDEO)
	{
		/* AZBOX rc has a KEY_SUBTITLE key, which sends KEY_VIDEO events. Correct this, so we do not have to place hacks in the keymaps. */
		ev->code = KEY_SUBTITLE;
	}
#endif

#if KEY_TV_TO_KEY_STOP
	if (ev->code == KEY_TV)
	{
		/* AZBOX rc has a KEY_STOP key, which sends KEY_TV events. Correct this, so we do not have to place hacks in the keymaps. */
		ev->code = KEY_STOP;
	}
#endif

#if KEY_RADIO_TO_KEY_RECORD
	if (ev->code == KEY_RADIO)
	{
		/* AZBOX rc has a KEY_RECORD key, which sends KEY_RADIO events. Correct this, so we do not have to place hacks in the keymaps. */
		ev->code = KEY_RECORD;
	}
#endif

#if KEY_HOME_TO_KEY_OPEN
	if (ev->code == KEY_HOME)
	{
		/* AZBOX rc has no radio/tv/pvr key, we use KEY_HOME which sends KEY_OPEN events. Correct this, so we do not have to place hacks in the keymaps. */
		ev->code = KEY_OPEN;
	}
#endif

#if KEY_HOME_TO_KEY_HOMEPAGE
	if (ev->code == KEY_HOME)
	{
		/* DAGS map HOME Key to show Mediaportal */
		ev->code = KEY_HOMEPAGE;
	}
#endif

#if KEY_MEDIA_TO_KEY_KEY_F2
	if (ev->code == KEY_MEDIA)
	{
		/* DAGS map Media to F2 to show MediaCenter */
		ev->code = KEY_F2;
	}
#endif

#if KEY_TV_TO_KEY_VIDEO
	if (ev->code == KEY_TV)
	{
		/* Venton HD1 rc has a no KEY_VIDEO key, which sends KEY_TV events. Correct this, so we do not have to place hacks in the keymaps. */
		ev->code = KEY_VIDEO;
	}
#endif

#if KEY_BOOKMARKS_TO_KEY_DIRECTORY
	if (ev->code == KEY_BOOKMARKS)
	{
		/* Venton ini2 remote has a KEY_BOOKMARKS key we need KEY_DIRECTORY. Correct this, so we do not have to place hacks in the keymaps. */
		ev->code = KEY_DIRECTORY;
	}
#endif

#if KEY_MEDIA_TO_KEY_BOOKMARKS
	if (ev->code == KEY_MEDIA)
	{
		/* Venton ini2 remote has a KEY_MEDIA key we need KEY_Bookmark. Correct this, so we do not have to place hacks in the keymaps. */
		ev->code = KEY_BOOKMARKS;
	}
#endif

#if KEY_MEDIA_TO_KEY_OPEN
	if (ev->code == KEY_MEDIA)
	{
		/* Venton ini2 remote has a KEY_MEDIA key we need KEY_OPEN. Correct this, so we do not have to place hacks in the keymaps. */
		ev->code = KEY_OPEN;
	}
#endif

#if KEY_SEARCH_TO_KEY_WWW
	if (ev->code == KEY_SEARCH)
	{
		/* Venton rc has a a Key WWW and send KEY_SEARCH. Correct this, so we do not have to place hacks in the keymaps. */
		ev->code = KEY_WWW;
	}
#endif

#if KEY_POWER2_TO_KEY_WWW
	if (ev->code == KEY_POWER2)
	{
		/* Venton rc has a a Key WWW and send KEY_POWER2. Correct this, so we do not have to place hacks in the keymaps. */
		ev->code = KEY_WWW;
	}
#endif

#if KEY_DIRECTORY_TO_KEY_FILE
	if (ev->code == KEY_DIRECTORY)
	{
		/* Venton rc has a a KEY_DIRECTORY and send KEY_FILE. Correct this, so we do not have to place hacks in the keymaps. */
		ev->code = KEY_FILE;
	}
#endif

#if KEY_OPTION_TO_KEY_PC
	if (ev->code == KEY_OPTION)
	{
		/* Venton rc has a a Key LAN and send KEY_OPTION. Correct this, so we do not have to place hacks in the keymaps. */
		ev->code = KEY_PC;
	}
#endif

#if KEY_VIDEO_TO_KEY_MODE
	if (ev->code == KEY_VIDEO)
	{
		/* Venton rc has a a Key Format and send KEY_Video. Correct this, so we do not have to place hacks in the keymaps. */
		ev->code = KEY_MODE;
	}
#endif
	

#if KEY_GUIDE_TO_KEY_EPG
	if (ev->code == KEY_HELP)
	{
		/* GB800 rc has a KEY_GUIDE key, which sends KEY_HELP events. Correct this, so we do not have to place hacks in the keymaps. */
		ev->code = KEY_EPG;
	}
#endif

#if KEY_SCREEN_TO_KEY_MODE
	if (ev->code == KEY_SCREEN)
	{
		/* GB800 rc has a KEY_ASPECT key, which sends KEY_SCREEN events. Correct this, so we do not have to place hacks in the keymaps. */
		ev->code = KEY_MODE;
	}
#endif

#if KEY_PLAY_IS_KEY_PLAYPAUSE
	if (ev->code == KEY_PLAY)
	{
		/* sogno rc has a KEY_PLAYPAUSE  key, which sends KEY_PLAY events. Correct this, so we do not have to place hacks in the keymaps. */
		ev->code = KEY_PLAYPAUSE;
	}
#endif

#if KEY_PLAY_ACTUALLY_IS_KEY_PLAYPAUSE
	if (ev->code == KEY_PLAY)
	{
		if ((id == "dreambox advanced remote control (native)")  || (id == "bcm7325 remote control"))
		{
			/* 8k rc has a KEY_PLAYPAUSE key, which sends KEY_PLAY events. Correct this, so we do not have to place hacks in the keymaps. */
			ev->code = KEY_PLAYPAUSE;
		}
	}
#endif

#if KEY_F1_TO_KEY_PC
	if (ev->code == KEY_F1)
	{
		/* Technomate , which sends KEY_F1 events. Correct this, so we do not have to place hacks in the keymaps. */
		ev->code = KEY_PC;
	}
#endif

#if KEY_F5_TO_KEY_ANGLE
	if (ev->code == KEY_F5)
	{
		/* Technomate , which sends KEY_F5 events. Correct this, so we do not have to place hacks in the keymaps. */
		ev->code = KEY_ANGLE;
	}
#endif

#if KEY_DOT_TO_KEY_HOMEPAGE
	if (ev->code == KEY_DOT)
	{
		/* Technomate , which sends KEY_DOT events. Correct this, so we do not have to place hacks in the keymaps. */
		ev->code = KEY_HOMEPAGE;
	}
#endif

#if KEY_SCREEN_TO_KEY_ANGLE
	if (ev->code == KEY_SCREEN)
	{
		/* MixOs , which sends KEY_SCREEN events. Correct this, so we do not have to place hacks in the keymaps. */
		ev->code = KEY_ANGLE;
	}
#endif

#if KEY_ZOOM_TO_KEY_SCREEN
	if (ev->code == KEY_ZOOM)
	{
		/* Venton rc has a a Key LAN and send KEY_OPTION. Correct this, so we do not have to place hacks in the keymaps. */
		ev->code = KEY_SCREEN;
	}
#endif

#if KEY_TIME_TO_KEY_SLEEP
	if (ev->code == KEY_SLEEP)
	{
		/* MixOs , which sends KEY_SLEEP events. Correct this, so we do not have to place hacks in the keymaps. */
		ev->code = KEY_PROGRAM;
	}
#endif

#if KEY_LIST_TO_KEY_PVR
	if (ev->code == KEY_LIST)
	{
		/* HDx , which sends KEY_LIST events. Correct this, so we do not have to place hacks in the keymaps. */
		ev->code = KEY_PVR;
	}
#endif

#if KEY_BOOKMARKS_IS_KEY_DIRECTORY
	if (ev->code == KEY_BOOKMARKS)
	{
		/* Beyonwiz U4 RCU workaround to open pluginbrowser */
		ev->code = KEY_DIRECTORY;
	}
#endif

#if KEY_VIDEO_TO_KEY_BOOKMARKS
	if (ev->code == KEY_VIDEO)
	{
		/* Axas Ultra have two keys open Movie folder , use Media key to open Mediaportal */
		ev->code = KEY_BOOKMARKS;
	}
#endif

	switch (ev->value)
	{
		case 0:
			input->keyPressed(eRCKey(this, ev->code, eRCKey::flagBreak)); /*emit*/
			break;
		case 1:
			input->keyPressed(eRCKey(this, ev->code, 0)); /*emit*/
			break;
		case 2:
			input->keyPressed(eRCKey(this, ev->code, eRCKey::flagRepeat)); /*emit*/
			break;
	}
}

eRCDeviceInputDev::eRCDeviceInputDev(eRCInputEventDriver *driver, int consolefd)
	:	eRCDevice(driver->getDeviceName(), driver), iskeyboard(driver->isKeyboard()),
		ismouse(driver->isPointerDevice()),
		consoleFd(consolefd), shiftState(false), capsState(false)
{
	setExclusive(true);
	eDebug("[eRCDeviceInputDev] device \"%s\" is a %s", id.c_str(), iskeyboard ? "keyboard" : (ismouse ? "mouse" : "remotecontrol"));
}

void eRCDeviceInputDev::setExclusive(bool b)
{
	if (!iskeyboard && !ismouse)
		driver->setExclusive(b);
}

const char *eRCDeviceInputDev::getDescription() const
{
	return id.c_str();
}

class eInputDeviceInit
{
	struct element
	{
		public:
			char* filename;
			eRCInputEventDriver* driver;
			eRCDeviceInputDev* device;
			element(const char* fn, eRCInputEventDriver* drv, eRCDeviceInputDev* dev):
				filename(strdup(fn)),
				driver(drv),
				device(dev)
			{
			}
			~element()
			{
				delete device;
				delete driver;
				free(filename);
			}
		private:
			element(const element& other); /* no copy */
	};
	typedef std::vector<element*> itemlist;
	std::vector<element*> items;
	int consoleFd;

public:
	eInputDeviceInit()
	{
#if WORKAROUND_KODI_INPUT
		addAll();
#else
		int i = 0;
		consoleFd = ::open("/dev/tty0", O_RDWR);
		while (1)
		{
			char filename[32];
			sprintf(filename, "/dev/input/event%d", i);
			if (::access(filename, R_OK) < 0)
				break;
			add(filename);
			++i;
		}
		eDebug("[eInputDeviceInit] Found %d input devices.", i);
#endif
	}

	~eInputDeviceInit()
	{
		for (itemlist::iterator it = items.begin(); it != items.end(); ++it)
			delete *it;

		if (consoleFd >= 0)
			::close(consoleFd);
	}

	void add(const char* filename)
	{
		eDebug("[eInputDeviceInit] adding device %s", filename);
		eRCInputEventDriver *p = new eRCInputEventDriver(filename);
		items.push_back(new element(filename, p, new eRCDeviceInputDev(p, consoleFd)));
	}

	void remove(const char* filename)
	{
		for (itemlist::iterator it = items.begin(); it != items.end(); ++it)
		{
			if (strcmp((*it)->filename, filename) == 0)
			{
				delete *it;
				items.erase(it);
				return;
			}
		}
		eDebug("[eInputDeviceInit] Remove '%s', not found", filename);
	}

	void addAll(void)
	{
		int i = 0;
		if (consoleFd < 0)
		{
			consoleFd = ::open("/dev/tty0", O_RDWR);
			printf("consoleFd %d\n", consoleFd);
		}
		while (1)
		{
			char filename[32];
			sprintf(filename, "/dev/input/event%d", i);
			if (::access(filename, R_OK) < 0)
				break;
			add(filename);
			++i;
		}
		eDebug("[eInputDeviceInit] Found %d input devices.", i);
	}

	void removeAll(void)
	{
		int size = items.size();
		for (itemlist::iterator it = items.begin(); it != items.end(); ++it)
		{
			delete *it;
		}
		items.clear();
	}
};

eAutoInitP0<eInputDeviceInit> init_rcinputdev(eAutoInitNumbers::rc+1, "input device driver");

void addInputDevice(const char* filename)
{
	init_rcinputdev->add(filename);
}

void removeInputDevice(const char* filename)
{
	init_rcinputdev->remove(filename);
}

void addAllInputDevices(void)
{
	init_rcinputdev->addAll();
}

void removeAllInputDevices(void)
{
	init_rcinputdev->removeAll();
}
