
from Components.config import config
from .unarchiver import ArchiverMenuScreen, ArchiverInfoScreen


ADDONINFO = (
	_("File Commander - tar Addon"),
	_("unpack tar/compressed tar Files"),
	"0.3"
)


class TarMenuScreen(ArchiverMenuScreen):

	def __init__(self, session, sourcelist, targetlist):
		ArchiverMenuScreen.__init__(self, session, sourcelist, targetlist, addoninfo=ADDONINFO)
		self.list.append((_("Show contents of tar or compressed tar file"), 1))
		self.list.append((_("Unpack to current folder"), 2))
		self.list.append((_("Unpack to %s") % self.targetDir, 3))
		self.list.append((_("Unpack to %s") % config.usage.default_path.value, 4))

	def unpackModus(self, id):
		print("[TarMenuScreen] unpackModus %s" % id)
		if id == 1:
			cmd = ("tar", "-tf", self.sourceDir + self.filename)
			self.unpackPopen(cmd, ArchiverInfoScreen, ADDONINFO)
		elif 2 <= id <= 4:
			cmd = ["tar", "-xvf", self.sourceDir + self.filename, "-C"]
			if id == 2:
				cmd.append(self.sourceDir)
			elif id == 3:
				cmd.append(self.targetDir)
			elif id == 4:
				cmd.append(config.usage.default_path.value)
			self.unpackEConsoleApp(cmd)
