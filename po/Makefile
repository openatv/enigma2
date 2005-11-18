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
#	msgmerge -N -U enigma2.pot menu.pot
#	msgmerge -N -U enigma2.pot setup.pot
	msguniq -o enigma2uniq.pot enigma2.pot
	rm enigma2.pot
	mv enigma2uniq.pot enigma2.pot
	msgmerge -N -U de.po enigma2.pot

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
			../lib/python/Screens/TimerEdit.py \
			../lib/python/Components/SetupDevices.py \
			../lib/python/Components/Language.py \
			../lib/python/Components/EventInfo.py \
			../lib/python/Components/Network.py 
	./xml2po.py	../data/ >> enigma2.pot


%.mo: %.po
	$(MSGFMT) -o $@ $<

%.po:
	msginit -l $@ -o $@ -i enigma2.pot --no-translator
	

clean:
	rm *.mo *.pot
