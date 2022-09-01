import subprocess
from Components.PluginComponent import plugins
from Screens.Console import Console
from Tools.Directories import shellquote, fileExists, resolveFilename, SCOPE_PLUGINS

from .unarchiver import ArchiverMenuScreen, ArchiverInfoScreen

ADDONINFO = (
	_("File Commander - ipk Addon"),
	_("install/unpack ipk Files"),
	"0.3"
)


class ipkMenuScreen(ArchiverMenuScreen):

	def __init__(self, session, sourcelist, targetlist):
		ArchiverMenuScreen.__init__(self, session, sourcelist, targetlist, addoninfo=ADDONINFO)
		self.list.append((_("Show contents of ipk file"), self.ID_SHOW))
		self.list.append((_("Install"), self.ID_INSTALL))

	def unpackModus(self, selectid):
		if selectid == self.ID_SHOW:
			# This is done in a subshell because using two
			# communicating Popen commands can deadlock on the
			# pipe output. Using communicate() avoids deadlock
			# on reading stdout and stderr from the pipe.
			fname = shellquote(self.sourceDir + self.filename)
			p = subprocess.Popen("ar -t %s > /dev/null 2>&1" % fname, shell=True)
			if p.wait():
				cmd = "tar -xOf %s ./data.tar.gz | tar -tzf -" % fname
			else:
				cmd = "ar -p %s data.tar.gz | tar -tzf -" % fname
			self.unpackPopen(cmd, ArchiverInfoScreen, ADDONINFO)
		elif selectid == self.ID_INSTALL:
			self.ulist = []
			if fileExists("/usr/bin/opkg"):
				self.session.openWithCallback(self.doCallBack, Console, title=_("Installing Plugin ..."), cmdlist=(("opkg", "install", self.sourceDir + self.filename),))

	def doCallBack(self):
		if self.filename.startswith("enigma2-plugin-"):
			plugins.readPluginList(resolveFilename(SCOPE_PLUGINS))
