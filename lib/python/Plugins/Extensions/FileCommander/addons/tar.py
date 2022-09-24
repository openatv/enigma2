
from .unarchiver import ArchiverMenuScreen, ArchiverInfoScreen

ADDONINFO = (
	_("File Commander - tar Addon"),
	_("unpack tar/compressed tar Files"),
	"0.3"
)


class TarMenuScreen(ArchiverMenuScreen):

	def __init__(self, session, sourcelist, targetlist):
		ArchiverMenuScreen.__init__(self, session, sourcelist, targetlist, addoninfo=ADDONINFO)
		self.initList(_("Show contents of tar or compressed tar file"))

	def unpackModus(self, selectid):
		print("[TarMenuScreen] unpackModus %s" % selectid)
		if selectid == self.ID_SHOW:
			cmd = ("tar", "-tf", self.sourceDir + self.filename)
			self.unpackPopen(cmd, ArchiverInfoScreen, ADDONINFO)
		else:
			cmd = ["tar", "-xvf", self.sourceDir + self.filename, "-C"]
			cmd.append(self.getPathBySelectId(selectid))
			self.unpackEConsoleApp(cmd)
