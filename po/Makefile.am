DOMAIN=enigma2
#GETTEXT=./pygettext.py
GETTEXT=xgettext

#MSGFMT = ./msgfmt.py
MSGFMT = msgfmt

LANGS := de en ar nl es is it da sv no fr fi tr ca cs hr hu
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
	msguniq -o enigma2uniq.pot enigma2.pot
	$(RM) enigma2.pot
	mv enigma2uniq.pot enigma2.pot

.PHONY: enigma2.pot


%.mo: %.po
	$(MSGFMT) -o $@ $<

%.po:
	msginit -l $@ -o $@ -i enigma2.pot --no-translator

clean:
	$(RM) *.mo *.pot

install-data-am: default
	for lang in $(LANGS); do \
		mkdir -p $(DESTDIR)$(DATADIR)/enigma2/po/$$lang/LC_MESSAGES; \
		cp $$lang.mo $(DESTDIR)$(DATADIR)/enigma2/po/$$lang/LC_MESSAGES/$(DOMAIN).mo; \
	done
