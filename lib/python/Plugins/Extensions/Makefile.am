installdir = $(pkglibdir)/python/Plugins/Extensions

SUBDIRS = TuxboxPlugins CutListEditor PicturePlayer MediaScanner MediaPlayer SocketMMI DVDBurn Infopanel Volume_adjust ProgrammlistenUpdater AtileHD

if HAVE_LIBDDVD
SUBDIRS += DVDPlayer
endif

if VUSOLO4K
SUBDIRS += MiniTV QuadPip
endif

if VUULTIMO4K
SUBDIRS += MiniTV QuadPip
endif

if GB7252
SUBDIRS += QuadPip
endif

if VUUNO4K
SUBDIRS += QuadPip
endif

if VUUNO4KSE
SUBDIRS += MiniTV QuadPip
endif

if VUDUO4K
SUBDIRS += MiniTV QuadPip
endif

if S8100
SUBDIRS += MiniTV
endif

if HAVE_KODI
SUBDIRS +=  StartKodi
endif

install_PYTHON = __init__.py
