SUBDIRS = countries fonts extensions keymaps skin_default rc_models

dist_pkgdata_DATA = \
	encoding.conf \
	keymap.xml \
	keymap.ntr \
	keymap.u80 \
	menu.xml \
	radio.mvi \
	prev.png \
	black.mvi \
	rcpositions.xml \
	setup.xml \
	skin_default.xml \
	skin_subtitles.xml \
	skin.xml \
	startwizard.xml \
	freesat.t1 \
	freesat.t2 \
	unicable.xml

if HAVE_TEXTLCD
dist_pkgdata_DATA += skin_text.xml skin_text_clock.xml
else
if HAVE_DISPLAY96
dist_pkgdata_DATA += skin_display96.xml
else
if HAVE_DISPLAY128
dist_pkgdata_DATA += skin_display128.xml
else
if HAVE_DISPLAYDM
dist_pkgdata_DATA += skin_display.xml
else
SUBDIRS += lcd
dist_pkgdata_DATA += skin_display_picon.xml skin_display_no_picon.xml
endif
endif
endif
endif
