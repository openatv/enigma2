SUBDIRS = lib main data po tools

installdir = $(pkglibdir)/python

install_PYTHON = \
	Navigation.py NavigationInstance.py RecordTimer.py SleepTimer.py ServiceReference.py \
	keyids.py keymapparser.py mytest.py skin.py timer.py tools.py GlobalActions.py \
	e2reactor.py

LANGS := ar ca cs da de el en es fi fr fy hr hu is it lt lv nl no pl pt ru sv sk sl sr tr uk

install-exec-hook:
	for lang in ${LANGS}; do \
		python $(srcdir)/tools/genmetaindex.py $$lang $(DESTDIR)$(pkgdatadir)/meta/enigma2/plugin_*.xml > $(DESTDIR)$(pkgdatadir)/meta/enigma2/index_$$lang.xml; \
		done;
