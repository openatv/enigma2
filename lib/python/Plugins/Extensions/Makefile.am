installdir = $(pkglibdir)/python/Plugins/Extensions

SUBDIRS = TuxboxPlugins CutListEditor PicturePlayer MediaScanner MediaPlayer SocketMMI DVDBurn Modem \
	IniMyTube IPTVStreams MovieBrowser MP3Browser IniSHOUTcast IniLastFM IniZapHistoryBrowser AccuWeather GmailReader IniHbbTV AirPlayer

if HAVE_LIBDDVD
SUBDIRS += DVDPlayer
endif

install_PYTHON =	\
	__init__.py
