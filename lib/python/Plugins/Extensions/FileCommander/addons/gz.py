from os.path import splitext

from Components.config import config
from Tools.Directories import shellquote
from .unarchiver import ArchiverMenuScreen

ADDONINFO = (
	_("File Commander - gzip Addon"),
	_("unpack gzip Files"),
	"0.3"
)


class GunzipMenuScreen(ArchiverMenuScreen):

	def __init__(self, session, sourcelist, targetlist):
		ArchiverMenuScreen.__init__(self, session, sourcelist, targetlist, addoninfo=ADDONINFO)

		self.list.append((_("Unpack to current folder"), 1))
		self.list.append((_("Unpack to %s") % self.targetDir, 2))
		self.list.append((_("Unpack to %s") % config.usage.default_path.value, 3))

	def unpackModus(self, id):
		print("[GunzipMenuScreen] unpackModus %s" % id)
		pathName = self.sourceDir + self.filename
		if id == 1:
			cmd = ("gunzip", pathName)
		elif id in (2, 3):
			baseName, ext = splitext(self.filename)
			if ext != ".gz":
				return
			if id == 2:
				dest = self.targetDir
			elif id == 3:
				dest = config.usage.default_path.value
			dest += baseName
			cmd = "gunzip -c %s > %s && rm %s" % (shellquote(pathName), shellquote(dest), shellquote(pathName))
		self.unpackEConsoleApp(cmd)
