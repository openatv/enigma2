installdir = $(pkglibdir)/python/Plugins/Extensions

SUBDIRS = TuxboxPlugins \
	CutListEditor \
	PicturePlayer \
	MediaScanner \
	MediaPlayer \
	SocketMMI \
	DVDBurn \
	IniSHOUTcast \
	IniZapHistoryBrowser \
	IniGmailReader \
	FileCommander \
	IniWebcamViewer \
	RemoteIPTVClient

if HAVE_LIBDDVD
SUBDIRS += DVDPlayer
endif

install_PYTHON = __init__.py
