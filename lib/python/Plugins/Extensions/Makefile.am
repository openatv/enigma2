installdir = $(pkglibdir)/python/Plugins/Extensions

SUBDIRS = GraphMultiEPG TuxboxPlugins CutListEditor PicturePlayer MediaScanner MediaPlayer SocketMMI DVDBurn Modem Aafpanel vuWebBrowser Volume_adjust

if HAVE_LIBDDVD
SUBDIRS += DVDPlayer
endif

if VUPLUS
SUBDIRS += GenuineVuplus
endif

if VUUNO
SUBDIRS += WebBrowser
endif

if VUULTIMO
SUBDIRS += WebBrowser
endif

install_PYTHON =	\
	__init__.py
