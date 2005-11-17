#GETTEXT=./pygettext.py
GETTEXT=xgettext

#MSGFMT = ./msgfmt.py
MSGFMT = msgfmt

LANGS := de en
LANGPO := $(foreach LANG, $(LANGS),$(LANG).po)
LANGMO := $(foreach LANG, $(LANGS),$(LANG).mo)

default: enigma2.pot $(LANGPO) merge $(LANGMO)
	-mkdir -p de/LC_MESSAGES
	cp de.mo de/LC_MESSAGES/enigma2.mo

	-mkdir -p en/LC_MESSAGES
	cp en.mo en/LC_MESSAGES/enigma2.mo

merge:
	msgmerge -U de.po enigma2.pot

enigma2.pot:
	$(GETTEXT)	-d enigma2 -s -o enigma2.pot \
			../lib/python/Screens/ScanSetup.py \
			../lib/python/Screens/NetworkSetup.py \
			../lib/python/Screens/Satconfig.py \
			../lib/python/Screens/EventView.py \
			../lib/python/Screens/Ci.py \
			../lib/python/Screens/About.py \
			../lib/python/Screens/HarddiskSetup.py \
			../lib/python/Screens/InfoBar.py \
			../lib/python/Components/SetupDevices.py \
			../lib/python/Components/Language.py 
			


%.mo: %.po
	$(MSGFMT) -o $@ $<

%.po:
	msginit -l $@ -o $@ -i enigma2.pot --no-translator
	

clean:
	rm *.mo *.pot
