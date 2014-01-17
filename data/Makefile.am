SUBDIRS = fonts extensions keymaps rc_models

dist_pkgdata_DATA = \
	encoding.conf \
	keymap.xml \
	keymap.ntr \
	keymap.u80 \
	menu.xml \
	black.mvi \
	rcpositions.xml \
	setup.xml \
	skin_subtitles.xml \
	startwizard.xml \
	userinterfacepositionerwizard.xml \
	videowizard.xml \
	freesat.t1 \
	freesat.t2 \
	unicable.xml \
	hd-testcard.mvi \
	distro-logo.png

if HAVE_TEXTLCD
SUBDIRS += displaytext
endif

if HAVE_COLORLCD2
SUBDIRS += display96
endif

if HAVE_COLORLCD1
SUBDIRS += display128
endif

if HAVE_COLORLCD220
SUBDIRS += display220
endif

if HAVE_COLORLCD400
SUBDIRS += display400
endif

if HAVE_BWLCD255
SUBDIRS += display255
endif

if HAVE_BWLCD140
SUBDIRS += display140
endif
