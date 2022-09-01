from Components.config import config
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

		self.list.append((_("Show contents of zip file"), 1))
		self.list.append((_("Unpack to current folder"), 2))
		self.list.append((_("Unpack to %s") % self.targetDir, 3))
		self.list.append((_("Unpack to %s") % config.usage.default_path.value, 4))

	def unpackModus(self, id):
		print("[UnzipMenuScreen] unpackModus %s" % id)
		if id == 1:
			cmd = ("unzip", "-l", self.sourceDir + self.filename)
			self.unpackPopen(cmd, UnpackInfoScreen, ADDONINFO)
		elif 2 <= id <= 4:
			cmd = ["unzip", "-o", self.sourceDir + self.filename, "-d"]
			if id == 2:
				cmd.append(self.sourceDir)
			elif id == 3:
				cmd.append(self.targetDir)
			elif id == 4:
				cmd.append(config.usage.default_path.value)
			self.unpackEConsoleApp(cmd)


class UnpackInfoScreen(ArchiverInfoScreen):

	def __init__(self, session, liste, sourceDir, filename, addoninfo=None):
		ArchiverInfoScreen.__init__(self, session, liste, sourceDir, filename, addoninfo)
		font = skin.fonts.get("FileList", ("Console", 20, 30))
		self.chooseMenuList.l.setFont(0, gFont('Console', int(font[1] * 0.85)))
