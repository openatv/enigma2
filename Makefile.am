SUBDIRS = include lib main data po tools

installdir = $(pkglibdir)/python

install_PYTHON = \
	Navigation.py NavigationInstance.py RecordTimer.py SleepTimer.py ServiceReference.py \
	keyids.py keymapparser.py mytest.py skin.py timer.py GlobalActions.py \
	e2reactor.py

LANGS := $(shell cat $(srcdir)/po/LINGUAS)

install-exec-hook:
	for lang in $(LANGS); do \
		$(PYTHON) $(srcdir)/tools/genmetaindex.py $$lang $(DESTDIR)$(datadir)/meta/plugin_*.xml > $(DESTDIR)$(datadir)/meta/index-enigma2_$$lang.xml; \
	done

uninstall-hook:
	$(RM) $(DESTDIR)$(datadir)/meta/index-enigma2_*.xml
