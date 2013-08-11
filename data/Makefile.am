SUBDIRS = countries fonts extensions keymaps skin_default rc_models

dist_pkgdata_DATA = \
	encoding.conf \
	keymap.xml \
	menu.xml \
	prev.png \
	radio.mvi \
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
dist_pkgdata_DATA += skin_text.xml
endif

if HAVE_COLORLCD220
SUBDIRS += lcd220 lcd_skin220
endif

skin_display.xml: skin_display_default.xml
	test -f skin_display_$(BOXTYPE).xml && cp skin_display_$(BOXTYPE).xml skin_display.xml || cp skin_display_default.xml skin_display.xml
