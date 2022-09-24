from os.path import splitext

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
		self.initList()

	def unpackModus(self, selectid):
		print("[GunzipMenuScreen] unpackModus %s" % selectid)
		pathName = self.sourceDir + self.filename
		if selectid == self.ID_CURRENTDIR:
			cmd = ("gunzip", pathName)
		elif selectid in (self.ID_TARGETDIR, self.ID_DEFAULTDIR):
			baseName, ext = splitext(self.filename)
			if ext != ".gz":
				return
			dest = self.getPathBySelectId(id)
			dest += baseName
			cmd = "gunzip -c %s > %s && rm %s" % (shellquote(pathName), shellquote(dest), shellquote(pathName))
		self.unpackEConsoleApp(cmd)
