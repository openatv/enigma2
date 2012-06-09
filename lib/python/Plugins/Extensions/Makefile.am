installdir = $(pkglibdir)/python/Plugins/Extensions

SUBDIRS = GraphMultiEPG TuxboxPlugins CutListEditor PicturePlayer MediaScanner MediaPlayer SocketMMI DVDBurn Modem Aafpanel vuWebBrowser Volume_adjust StreamTV DLNABrowser

if HAVE_LIBDDVD
SUBDIRS += DVDPlayer
endif

if VUPLUS
SUBDIRS += VuplusEvent
endif

install_PYTHON =	\
	__init__.py
