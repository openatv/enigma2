from Components.Language import language
from Tools.Directories import resolveFilename, SCOPE_LANGUAGE, SCOPE_PLUGINS, SCOPE_SKIN_IMAGE #@UnresolvedImport
import gettext, os

lang = language.getLanguage()
os.environ["LANGUAGE"] = lang[:2]
gettext.bindtextdomain("enigma2", resolveFilename(SCOPE_LANGUAGE))
gettext.textdomain("enigma2")
gettext.bindtextdomain("Volume_adjust", "%s%s" % (resolveFilename(SCOPE_PLUGINS), "Extensions/Volume_adjust/locale/"))

def _(txt):
	t = gettext.dgettext("Volume_adjust", txt)
	if t == txt:
		t = gettext.gettext(txt)
	return t