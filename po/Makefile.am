dist_noinst_SCRIPTS = xml2po.py

LANGS = ar bg ca cs da de el en en_GB es et fa fi fr fy he hr hu is it ku lt lv nl no nb pl pt pt_BR ro ru sv sk sl sr th tr uk
LANGMO = $(LANGS:=.mo)
LANGPO = $(LANGS:=.po)

EXTRA_DIST = $(LANGPO)

# the TRANSLATORS: allows putting translation comments before the to-be-translated line.
enigma2-py.pot: $(top_srcdir)/*.py $(top_srcdir)/lib/python/*/*.py $(top_srcdir)/lib/python/*/*/*.py $(top_srcdir)/lib/python/Plugins/*/*/*.py
	$(XGETTEXT) --no-wrap -L Python --from-code=UTF-8 -kpgettext:1c,2 --add-comments="TRANSLATORS:" -d @PACKAGE_NAME@ -s -o $@ $^

enigma2-xml.pot: $(srcdir)/xml2po.py $(top_srcdir)/data/*.xml $(top_srcdir)/lib/python/Plugins/SystemPlugins/*/*.xml
	$(PYTHON) $^ > $@

enigma2.pot: enigma2-py.pot enigma2-xml.pot
	sed --in-place enigma2-py.pot --expression=s/CHARSET/UTF-8/
	sed --in-place enigma2-xml.pot --expression=s/CHARSET/UTF-8/
	cat $^ | $(MSGUNIQ) --no-wrap --no-location -o $@ -

%.po: enigma2.pot
	if [ -f $@ ]; then \
		$(MSGMERGE) --backup=none --no-wrap --no-location -s -U $@ $< && touch $@; \
	else \
		$(MSGINIT) -l $@ -o $@ -i $< --no-translator; \
	fi

.po.mo:
	$(MSGFMT) -o $@ $<

BUILT_SOURCES = $(LANGMO)
CLEANFILES = $(LANGMO) enigma2-py.pot enigma2-xml.pot enigma2.pot

dist-hook: $(LANGPO)

install-data-local: $(LANGMO)
	for lang in $(LANGS); do \
		$(mkinstalldirs) $(DESTDIR)$(pkgdatadir)/po/$$lang/LC_MESSAGES; \
		$(INSTALL_DATA) $$lang.po $(DESTDIR)$(pkgdatadir)/po/@PACKAGE_NAME@-$$lang.po; \
		$(INSTALL_DATA) $$lang.mo $(DESTDIR)$(pkgdatadir)/po/$$lang/LC_MESSAGES/@PACKAGE_NAME@.mo; \
		$(INSTALL_DATA) $$lang.po $(DESTDIR)$(pkgdatadir)/po/$$lang.po; \
	done

uninstall-local:
	for lang in $(LANGS); do \
		$(RM) $(DESTDIR)$(pkgdatadir)/po/@PACKAGE_NAME@-$$lang.po; \
		$(RM) $(DESTDIR)$(pkgdatadir)/po/$$lang/LC_MESSAGES/@PACKAGE_NAME@.mo; \
	done
