DOMAIN=enigma2
#GETTEXT=./pygettext.py
GETTEXT=xgettext

#MSGFMT = ./msgfmt.py
MSGFMT = msgfmt

LANGS := ar ca cs da de el en es fi fr fy hr hu is it lt nl no pl pt ru sv tr uk
LANGPO := $(foreach LANG, $(LANGS),$(LANG).po)
LANGMO := $(foreach LANG, $(LANGS),$(LANG).mo)

default: enigma2.pot $(LANGPO) merge $(LANGMO)
	for lang in $(LANGS); do \
		mkdir -p $$lang/LC_MESSAGES; \
		cp $$lang.mo $$lang/LC_MESSAGES/enigma2.mo; \
	done

merge:
	for lang in $(LANGS); do \
		msgmerge --no-location -s -N -U $$lang.po enigma2.pot; \
	done


# the TRANSLATORS: allows putting translation comments before the to-be-translated line.
enigma2.pot:
	$(GETTEXT) -L python --add-comments="TRANSLATORS:" -d enigma2 -s -o enigma2.pot ../lib/python/Screens/*.py ../lib/python/Components/*.py \
			../lib/python/Tools/*.py \
			../*.py \
			../lib/python/Plugins/*/*/*.py

	./xml2po.py	../data/ >> enigma2.pot
	./xml2po.py	../lib/python/Plugins/SystemPlugins/Videomode/ >> enigma2.pot
	./xml2po.py	../lib/python/Plugins/SystemPlugins/SoftwareManager/ >> enigma2.pot
	msguniq -o enigma2uniq.pot enigma2.pot
	$(RM) enigma2.pot
	mv enigma2uniq.pot enigma2.pot

.PHONY: enigma2.pot


%.mo: %.po
	$(MSGFMT) -o $@ $<

%.po:
	msginit -l $@ -o $@ -i enigma2.pot --no-translator

CLEANFILES = $(foreach LANG, $(LANGS),$(LANG).mo)

clean-local:
	$(RM) -r $(LANGS)

install-data-am: default
	for lang in $(LANGS); do \
		mkdir -p $(DESTDIR)$(DATADIR)/enigma2/po/$$lang/LC_MESSAGES; \
		cp $$lang.mo $(DESTDIR)$(DATADIR)/enigma2/po/$$lang/LC_MESSAGES/$(DOMAIN).mo; \
	done
