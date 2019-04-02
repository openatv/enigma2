#!/usr/bin/env python
# -*- coding: iso-8859-1 -*-

from Components.config import config
from Plugins.Extensions.FileCommander.addons.unarchiver import ArchiverMenuScreen, ArchiverInfoScreen

pname = _("File Commander - tar Addon")
pdesc = _("unpack tar/compressed tar Files")
pversion = "0.2-r1"

class TarMenuScreen(ArchiverMenuScreen):

	def __init__(self, session, sourcelist, targetlist):
		super(TarMenuScreen, self).__init__(session, sourcelist, targetlist)

		self.list.append((_("Show contents of tar or compressed tar file"), 1))
		self.list.append((_("Unpack to current folder"), 2))
		self.list.append((_("Unpack to %s") % self.targetDir, 3))
		self.list.append((_("Unpack to %s") % config.usage.default_path.value, 4))

		self.pname = pname
		self.pdesc = pdesc
		self.pversion = pversion

	def unpackModus(self, id):
		print "[TarMenuScreen] unpackModus", id
		if id == 1:
			cmd = ("tar", "-tf", self.sourceDir + self.filename)
			self.unpackPopen(cmd, UnpackInfoScreen)
		elif 2 <= id <= 4:
			cmd = ["tar", "-xvf", self.sourceDir + self.filename, "-C"]
			if id == 2:
				cmd.append(self.sourceDir)
			elif id == 3:
				cmd.append(self.targetDir)
			elif id == 4:
				cmd.append(config.usage.default_path.value)
			self.unpackEConsoleApp(cmd)

class UnpackInfoScreen(ArchiverInfoScreen):

	def __init__(self, session, list, sourceDir, filename):
		super(UnpackInfoScreen, self).__init__(session, list, sourceDir, filename)
		self.pname = pname
		self.pdesc = pdesc
		self.pversion = pversion
