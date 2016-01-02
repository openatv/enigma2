SUBDIRS = countries fonts extensions keymaps skin_default

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
	freesat.t1 \
	freesat.t2 \
	timezone.xml \
	unicable.xml

if GBIPBOX
SUBDIRS += gbipbox
else
dist_pkgdata_DATA += startwizard.xml
endif

if HAVE_TEXTLCD
dist_pkgdata_DATA += skin_text.xml
endif

if HAVE_COLORLCD220
SUBDIRS += lcd220 lcd_skin220
endif

if HAVE_COLORLCD400
SUBDIRS += lcd400 lcd_skin400
endif

if HAVE_BWLCD255
SUBDIRS += vfd255
endif

if HAVE_TEXTLCD
SUBDIRS += displaytext
endif

skin_display.xml: $(srcdir)/skin_display_default.xml
	test -f $(srcdir)/skin_display_$(BOXTYPE).xml && cp $(srcdir)/skin_display_$(BOXTYPE).xml skin_display.xml || cp $(srcdir)/skin_display_default.xml skin_display.xml
