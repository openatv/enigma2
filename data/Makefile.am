SUBDIRS = fonts keymaps

dist_pkgdata_DATA = \
	encoding.conf \
	keymap.xml \
	keytranslation.xml \
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
	distro-logo.png \
	groupedservices


if HAVE_TEXTLCD
if HAVE_7SEGMENT
SUBDIRS += 7segment
else
if SPARK
SUBDIRS += displaydualtext
else
SUBDIRS += displaytext
endif
endif
endif

if HAVE_COLORLCD3
SUBDIRS += display128dm
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

if HAVE_COLORLCD390
SUBDIRS += display390
endif

if HAVE_COLORLCD400
SUBDIRS += display400
endif

if HAVE_COLORLCD480
SUBDIRS += display480
endif

if HAVE_COLORLCD720
SUBDIRS += display720
endif

if HAVE_COLORLCD800
SUBDIRS += display800
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

if HAVE_GRAUTEC8000
SUBDIRS += grautec8000
endif

if HAVE_GRAUTEC70X0
SUBDIRS += grautec70x0
endif

