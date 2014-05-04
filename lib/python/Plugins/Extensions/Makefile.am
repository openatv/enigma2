installdir = $(pkglibdir)/python/Plugins/Extensions

SUBDIRS = TuxboxPlugins CutListEditor PicturePlayer MediaScanner MediaPlayer SocketMMI DVDBurn Modem \
	IniMyTube IniSHOUTcast IniLastFM IniZapHistoryBrowser AccuWeather GmailReader IniHbbTV IniAirPlayer FileCommander \
	IniEcasa IniWebcamViewer GoogleNews

if HAVE_LIBDDVD
SUBDIRS += DVDPlayer
endif

install_PYTHON = __init__.py
