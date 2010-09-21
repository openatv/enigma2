SUBDIRS = include lib main data po tools

installdir = $(pkglibdir)/python

install_PYTHON = \
	Navigation.py NavigationInstance.py RecordTimer.py SleepTimer.py ServiceReference.py \
	keyids.py keymapparser.py mytest.py skin.py timer.py tools.py GlobalActions.py \
	e2reactor.py

install-exec-hook:
		$(PYTHON) $(srcdir)/tools/genmetaindex.py $(DESTDIR)$(datadir)/meta/plugin_*.xml > $(DESTDIR)$(datadir)/meta/index-enigma2.xml

uninstall-hook:
	$(RM) $(DESTDIR)$(datadir)/meta/index-enigma2.xml
