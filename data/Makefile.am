SUBDIRS = countries fonts extensions keymaps skin_default rc_models

dist_pkgdata_DATA = \
	encoding.conf \
	keymap.xml \
	menu.xml \
	prev.png \
	black.mvi \
	rcpositions.xml \
	setup.xml \
	skin_default.xml \
	skin_subtitles.xml \
	skin.xml \
	startwizard.xml \
	userinterfacepositionerwizard.xml \
	freesat.t1 \
	freesat.t2 \
	unicable.xml \
	hd-testcard.mvi

if HAVE_TEXTLCD
dist_pkgdata_DATA += skin_text.xml
endif

if HAVE_COLORLCD
dist_pkgdata_DATA += skin_display96.xml
endif

if HAVE_COLORLCD220
SUBDIRS += lcd220
dist_pkgdata_DATA += skin_display220_picon.xml skin_display220_no_picon.xml
endif

if HAVE_BWLCD255
SUBDIRS += lcd255
dist_pkgdata_DATA += skin_display255_picon.xml skin_display255_no_picon.xml
endif
