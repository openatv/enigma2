DOMAIN=enigma2
#GETTEXT=./pygettext.py
GETTEXT=xgettext

#MSGFMT = ./msgfmt.py
MSGFMT = msgfmt

LANGS := de en ar nl es is it da sv no fr fi tr ca
LANGPO := $(foreach LANG, $(LANGS),$(LANG).po)
LANGMO := $(foreach LANG, $(LANGS),$(LANG).mo)

default: enigma2.pot $(LANGPO) merge $(LANGMO)
	for lang in $(LANGS); do \
		mkdir -p $$lang/LC_MESSAGES; \
		cp $$lang.mo $$lang/LC_MESSAGES/enigma2.mo; \
	done

merge:
	for lang in $(LANGS); do \
		msgmerge -N -U $$lang.po enigma2.pot; \
	done

enigma2.pot:
	$(GETTEXT)	-d enigma2 -s -o enigma2.pot \
			../lib/python/Screens/ScanSetup.py \
			../lib/python/Screens/NetworkSetup.py \
			../lib/python/Screens/Satconfig.py \
			../lib/python/Screens/EventView.py \
			../lib/python/Screens/Ci.py \
			../lib/python/Screens/EpgSelection.py \
			../lib/python/Screens/LanguageSelection.py \
			../lib/python/Screens/About.py \
			../lib/python/Screens/Setup.py \
			../lib/python/Screens/HarddiskSetup.py \
			../lib/python/Screens/MovieSelection.py \
			../lib/python/Screens/InfoBar.py \
			../lib/python/Screens/TimerEdit.py \
			../lib/python/Screens/TimerEntry.py \
			../lib/python/Screens/TimeDateInput.py \
			../lib/python/Screens/Wizard.py \
			../lib/python/Screens/ServiceScan.py \
			../lib/python/Screens/InfoBarGenerics.py \
			../lib/python/Screens/ChannelSelection.py \
			../lib/python/Screens/PluginBrowser.py \
			../lib/python/Screens/Console.py \
			../lib/python/Screens/MediaPlayer.py \
			../lib/python/Screens/PiPSetup.py \
			../lib/python/Screens/SubservicesQuickzap.py \
			../lib/python/Components/DiskInfo.py \
			../lib/python/Components/ServiceScan.py \
			../lib/python/Components/Lcd.py \
			../lib/python/Components/SetupDevices.py \
			../lib/python/Components/Language.py \
			../lib/python/Components/NimManager.py \
			../lib/python/Components/TimerList.py \
			../lib/python/Components/EventInfo.py \
			../lib/python/Components/Network.py \
			../lib/python/Components/RecordingConfig.py \
			../lib/python/Plugins/SystemPlugins/PositionerSetup/plugin.py \
			../lib/python/Plugins/SystemPlugins/SoftwareUpdate/plugin.py \
			../lib/python/Plugins/SystemPlugins/FrontprocessorUpgrade/plugin.py \
			../lib/python/Plugins/SystemPlugins/ConfigurationBackup/plugin.py \
			../lib/python/Tools/FuzzyDate.py \
			../RecordTimer.py
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
