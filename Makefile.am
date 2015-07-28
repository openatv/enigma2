SUBDIRS = include lib main data po tools

ACLOCAL_AMFLAGS = -I m4

installdir = $(pkglibdir)/python
install_PYTHON = \
	Navigation.py NavigationInstance.py RecordTimer.py ServiceReference.py \
	keyids.py keymapparser.py mytest.py skin.py timer.py GlobalActions.py \
	e2reactor.py

pkgconfigdir = $(libdir)/pkgconfig
pkgconfig_DATA = enigma2.pc

metadir = $(datadir)/meta
meta_DATA = index-enigma2.xml
CLEANFILES = index-enigma2.xml

EXTRA_DIST = lamedb

index-enigma2.xml: $(top_srcdir)/tools/genmetaindex.py $(top_srcdir)/lib/python/Plugins/*/*/meta/plugin_*.xml
	$(AM_V_GEN)$(PYTHON) $^ > $@
