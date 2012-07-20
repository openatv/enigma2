# -*- coding: utf-8 -*-
from Components.Language import language
from Tools.Directories import resolveFilename, SCOPE_PLUGINS
import gettext

def localeInit():
	gettext.bindtextdomain("DeviceManager", resolveFilename(SCOPE_PLUGINS, "SystemPlugins/DeviceManager/locale"))

def _(txt):
	t = gettext.dgettext("DeviceManager", txt)
	if t == txt:
		print "[DeviceManager] fallback to default translation for:", txt
		t = gettext.gettext(txt)
	return t

localeInit()
language.addCallback(localeInit)