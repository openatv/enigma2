LANGS = de
LANGMO = $(LANGS:=.mo)
LANGPO = $(LANGS:=.po)

EXTRA_DIST = $(LANGPO)

.po.mo:
	$(MSGFMT) -o $@ $<

BUILT_SOURCES = $(LANGMO)

dist-hook: $(LANGPO)

install-data-local: $(LANGMO)
	for lang in $(LANGS); do \
		$(mkinstalldirs) $(DESTDIR)$(pkglibdir)/python/Plugins/SystemPlugins/VideoClippingSetup/locale/$$lang/LC_MESSAGES; \
		$(INSTALL_DATA) $$lang.mo $(DESTDIR)$(pkglibdir)/python/Plugins/SystemPlugins/VideoClippingSetup/locale/$$lang/LC_MESSAGES/VideoClippingSetup.mo; \
	done
