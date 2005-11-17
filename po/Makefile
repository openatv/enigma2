#GETTEXT=./pygettext.py
GETTEXT=xgettext

LANGS := de en
LANGPO := $(foreach LANG, $(LANGS),$(LANG).po)
LANGMO := $(foreach LANG, $(LANGS),$(LANG).mo)

default: enigma2.pot $(LANGPO) merge $(LANGMO)

merge:
	msgmerge -U en.po enigma2.pot
	msgmerge -U de.po enigma2.pot

enigma2.pot:
	$(GETTEXT)	-d enigma2 -s -o enigma2.pot \
			../lib/python/Screens/ScanSetup.py \
			../lib/python/Screens/NetworkSetup.py


%.mo: %.po
	msgfmt $< -o $@

%.po:
	msginit -l $@ -o $@ -i enigma2.pot --no-translator
	
