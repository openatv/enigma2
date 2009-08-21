SUBDIRS = include lib main data po tools

installdir = $(pkglibdir)/python

install_PYTHON = \
	Navigation.py NavigationInstance.py RecordTimer.py SleepTimer.py ServiceReference.py \
	keyids.py keymapparser.py mytest.py skin.py timer.py tools.py GlobalActions.py \
	e2reactor.py

LANGS := $(shell cat $(srcdir)/po/LINGUAS)

install-exec-hook:
	for lang in $(LANGS); do \
		$(PYTHON) $(srcdir)/tools/genmetaindex.py $$lang $(DESTDIR)$(pkgdatadir)/meta/enigma2/plugin_*.xml > $(DESTDIR)$(pkgdatadir)/meta/enigma2/index_$$lang.xml; \
	done

uninstall-hook:
	$(RM) $(DESTDIR)$(pkgdatadir)/meta/enigma2/index_*.xml
