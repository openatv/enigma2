SUBDIRS = fonts keymaps

dist_pkgdata_DATA = \
	encoding.conf \
	keymap.xml \
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
	timezone.xml \
	unicable.xml \
	hd-testcard.mvi \
	distro-logo.png

if HAVE_TEXTLCD
SUBDIRS += displaytext
endif

if HAVE_COLORLCD
SUBDIRS += display96
endif

if HAVE_COLORLCD128
SUBDIRS += display128
endif

if HAVE_COLORLCD220
SUBDIRS += display220
endif

if HAVE_COLORLCD400
SUBDIRS += display400
endif

if HAVE_COLORLCD720
SUBDIRS += display720
endif

if HAVE_BWLCD255
SUBDIRS += vfd255
endif

if HAVE_BWLCD140
SUBDIRS += vfd140
endif

if HAVE_BWLCD128
SUBDIRS += vfd128
endif
