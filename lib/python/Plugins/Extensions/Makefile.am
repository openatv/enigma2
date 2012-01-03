installdir = $(pkglibdir)/python/Plugins/Extensions

SUBDIRS = TuxboxPlugins CutListEditor PicturePlayer MediaScanner MediaPlayer SocketMMI DVDBurn Modem

if HAVE_LIBDDVD
SUBDIRS += DVDPlayer
endif

if VUUNO
SUBDIRS += WebBrowser
endif

if VUULTIMO
SUBDIRS += WebBrowser
endif

install_PYTHON =	\
	__init__.py
