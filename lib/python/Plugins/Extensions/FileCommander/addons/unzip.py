from enigma import gFont
from .unarchiver import ArchiverMenuScreen, ArchiverInfoScreen
import skin

ADDONINFO = (
	_("File Commander - unzip Addon"),
	_("unpack zip Files"),
	"0.3"
)


class UnzipMenuScreen(ArchiverMenuScreen):

	def __init__(self, session, sourcelist, targetlist):
		ArchiverMenuScreen.__init__(self, session, sourcelist, targetlist, addoninfo=ADDONINFO)
		self.initList(_("Show contents of zip file"))

	def unpackModus(self, selectid):
		print("[UnzipMenuScreen] unpackModus %s" % selectid)
		if selectid == self.ID_SHOW:
			cmd = ("unzip", "-l", self.sourceDir + self.filename)
			self.unpackPopen(cmd, UnpackInfoScreen, ADDONINFO)
		else:
			cmd = ["unzip", "-o", self.sourceDir + self.filename, "-d"]
			cmd.append(self.getPathBySelectId(selectid))
			self.unpackEConsoleApp(cmd)


class UnpackInfoScreen(ArchiverInfoScreen):

	def __init__(self, session, liste, sourceDir, filename, addoninfo=None):
		ArchiverInfoScreen.__init__(self, session, liste, sourceDir, filename, addoninfo)
		font = skin.fonts.get("FileList", ("Console", 20, 30))
		self.chooseMenuList.l.setFont(0, gFont('Console', int(font[1] * 0.85)))
