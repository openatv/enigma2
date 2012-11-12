from Components.Language import language
from Tools.Directories import resolveFilename, SCOPE_LANGUAGE, SCOPE_PLUGINS
import gettext, os

lang = language.getLanguage()
os.environ["LANGUAGE"] = lang[:2]
gettext.bindtextdomain("enigma2", resolveFilename(SCOPE_LANGUAGE))
gettext.textdomain("enigma2")
gettext.bindtextdomain("Infopanel", "%s%s" % (resolveFilename(SCOPE_PLUGINS), "Extensions/Infopanel/locale/"))

def _(txt):
	t = gettext.dgettext("Infopanel", txt)
	if t == txt:
		t = gettext.gettext(txt)
	return t
