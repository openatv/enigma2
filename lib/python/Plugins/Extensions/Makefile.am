installdir = $(pkglibdir)/python/Plugins/Extensions

SUBDIRS = AtileHD CutListEditor DVDBurn FileCommander MediaPlayer MediaScanner PicturePlayer ProgrammlistenUpdater SocketMMI TuxboxPlugins StreamlinkWrapper YTDLWrapper YTDLPWrapper

if HAVE_LIBDDVD
SUBDIRS += DVDPlayer
endif

if VU7376
SUBDIRS += MiniTV QuadPip
endif

if GB7252
SUBDIRS += QuadPip
endif

if VUDUO4KLITE
SUBDIRS += QuadPip
endif

if VUUNO4K
SUBDIRS += QuadPip
endif

if VUUNO4KSE
SUBDIRS += MiniTV QuadPip
endif

if VU7376DUO
SUBDIRS += MiniTV QuadPip
endif

if S8100
SUBDIRS += MiniTV
endif

if DREAMNEXTGEN
SUBDIRS += QuadPip
endif

install_PYTHON = __init__.py
