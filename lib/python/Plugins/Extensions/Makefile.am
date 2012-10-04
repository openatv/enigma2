installdir = $(pkglibdir)/python/Plugins/Extensions

SUBDIRS = TuxboxPlugins CutListEditor PicturePlayer MediaScanner MediaPlayer GraphMultiEPG SocketMMI DVDBurn Modem StreamTV DLNABrowser DLNAServer GBAspectRatioSwitch

if HAVE_LIBDDVD
SUBDIRS += DVDPlayer
endif

install_PYTHON =	\
	__init__.py
