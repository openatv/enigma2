from Components.ActionMap import HelpableActionMap
from Components.Opkg import OpkgComponent
from Components.Sources.List import List
from Components.Sources.StaticText import StaticText
from Screens.MessageBox import MessageBox
from Screens.Screen import Screen
from Tools.Directories import resolveFilename, SCOPE_GUISKIN
from Tools.LoadPixmap import LoadPixmap


class ShowSoftcamPackages(Screen):
	skin = """
	<screen name="ShowSoftcamPackages" position="center,center" size="630,500" resolution="1280,720">
		<widget source="list" render="Listbox" position="10,10" size="620,420" enableWrapAround="1" scrollbarMode="showOnDemand">
			<convert type="TemplatedMultiContent">
				{
				"template":
					[
						MultiContentEntryText(pos = (5, 1), size = (540, 28), font=0, flags = RT_HALIGN_LEFT, text = 0), # index 0 is the name
						MultiContentEntryText(pos = (5, 26), size = (540, 20), font=1, flags = RT_HALIGN_LEFT, text = 2), # index 2 is the description
						MultiContentEntryPixmapAlphaBlend(pos = (545, 2), size = (48, 48), png = 4), # index 3 is the status pixmap
						MultiContentEntryPixmapAlphaBlend(pos = (5, 50), size = (510, 2), png = 5), # index 4 is the div pixmap
					],
				"fonts": [gFont("Regular", 22),gFont("Regular", 14)],
				"itemHeight": 52
				}
			</convert>
		</widget>
		<widget source="key_red" render="Label" position="10,e-50" size="140,40" backgroundColor="key_red" font="Regular;20" foregroundColor="key_text" halign="center" valign="center">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="key_green" render="Label" position="160,e-50" size="140,40" backgroundColor="key_green" font="Regular;20" foregroundColor="key_text" halign="center" valign="center">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="key_yellow" render="Label" position="310,e-50" size="140,40" backgroundColor="key_yellow" font="Regular;20" foregroundColor="key_text" halign="center" valign="center">
			<convert type="ConditionalShowHide" />
		</widget>
	</screen>"""

	def __init__(self, session, args=None):
		Screen.__init__(self, session)
		self.setTitle(_("Install Softcams"))

		self["actions"] = HelpableActionMap(self, ["OkCancelActions", "NavigationActions", "ColorActions"], {
			"cancel": (self.keyCancel, _("Stop the update, if running, then exit")),
			"ok": (self.keyOk, _("Install/Remove plugin")),
			"green": (self.keyOk, _("Install/Remove plugin")),
			"top": (self.top, _("Move to first line / screen")),
			"pageUp": (self.pageUp, _("Move up a page / screen")),
			"up": (self.pageUp, _("Move up a page / screen")),
			# "first": (self.top, _("Move to first line")),
			# "last": (self.bottom, _("Move to last line")),
			"down": (self.pageDown, _("Move down a page / screen")),
			"pageDown": (self.pageDown, _("Move down a page / screen")),
			"bottom": (self.bottom, _("Move to last line / screen")),
			"yellow": (self.keyRefresh, _("Refresh the update-able package list"))
		}, prio=0, description=_("Software Update Actions"))

		self["list"] = List([])
		self["list"].onSelectionChanged.append(self.selectionChanged)
		self["key_red"] = StaticText(_("Close"))
		self["key_yellow"] = StaticText(_("Reload"))
		self["key_green"] = StaticText(_("Install"))
		self.installpackage = None
		self.opkg = OpkgComponent()
		self.opkg.addCallback(self.opkgCallback)
		self.onLayoutFinish.append(self.layoutFinished)

	def opkgCallback(self, event, parameter):
		if event == OpkgComponent.EVENT_DONE:
			if self.opkg.currentCommand == OpkgComponent.CMD_UPDATE:
				self.rebuildList()
			elif self.opkg.currentCommand == OpkgComponent.CMD_LIST:
				self.Flist = self.opkg.getFetchedList()
				self.opkg.startCmd(OpkgComponent.CMD_LIST_INSTALLED, args={"package": "enigma2-plugin-softcams-*"})
			elif self.opkg.currentCommand == OpkgComponent.CMD_LIST_INSTALLED:
				self.Elist = self.opkg.getFetchedList()
				if len(self.Flist) > 0:
					self.buildPacketList()
				else:
					self.setStatus('error')
			elif self.opkg.currentCommand == OpkgComponent.CMD_INSTALL:
				self.session.open(MessageBox, _("Install Finished."), MessageBox.TYPE_INFO, timeout=5)
				self.rebuildList()
			elif self.opkg.currentCommand == OpkgComponent.CMD_REMOVE:
				self.session.open(MessageBox, _("Remove Finished."), MessageBox.TYPE_INFO, timeout=5)
				self.rebuildList()
		elif event == OpkgComponent.EVENT_ERROR:
			if self.opkg.currentCommand == OpkgComponent.CMD_INSTALL:
				self.session.open(MessageBox, _("Install Failed !!"), MessageBox.TYPE_ERROR, timeout=10)
			elif self.opkg.currentCommand == OpkgComponent.CMD_REMOVE:
				self.session.open(MessageBox, _("Remove Failed !!"), MessageBox.TYPE_ERROR, timeout=10)
			else:
				self.setStatus("error")

	def layoutFinished(self):
		self.rebuildList()

	def selectionChanged(self):
		cur = self["list"].getCurrent()
		if cur and len(cur) > 3:
			self["key_green"].text = _("Install") if cur[3] == "installable" else _("Remove")

	def keyOk(self, returnValue=None):
		cur = self["list"].getCurrent()
		if cur:
			self.installpackage = cur[0]
			if cur[3] == "installable":
				self.session.openWithCallback(self.runInstall, MessageBox, "%s%s - %s\n\n%s" % (_("Do you want to install the package:\n"), cur[0], cur[1], _("Press OK on your remote control to continue.")))
			else:
				self.session.openWithCallback(self.runUnInstall, MessageBox, "%s%s - %s\n\n%s" % (_("Do you want to remove the package:\n"), cur[0], cur[1], _("Press OK on your remote control to continue.")))

	def runInstall(self, result):
		if result and self.installpackage:
			self.opkg.startCmd(OpkgComponent.CMD_INSTALL, {"package": self.installpackage})

	def runUnInstall(self, result):
		if result and self.installpackage:
			self.opkg.startCmd(OpkgComponent.CMD_REMOVE, {"package": self.installpackage})

	def keyCancel(self):
		if self.opkg.isRunning():
			self.opkg.stop()
		self.opkg.removeCallback(self.opkgCallback)
		self.close()

	def setStatus(self, status=None):
		if status:
			image = "upgrade"
			if status == "update":
				name = _("Package list update")
				description = _("Downloading latest update list.  Please wait...")
			elif status == "list":
				name = _("Package list")
				description = _("Getting Softcam list. Please wait...")
			elif status == "error":
				image = "remove"
				name = _("Download error")
				description = _("There was an error downloading the update list.  Please try again.")
			imagePath = resolveFilename(SCOPE_GUISKIN, "icons/%s.png" % image)
			divPng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_GUISKIN, "div-h.png"))
			statusPng = LoadPixmap(cached=True, path=imagePath)
			self['list'].setList([(name, "", description, "", statusPng, divPng)])

	def keyRefresh(self):
		self.setStatus("update")
		self.opkg.startCmd(OpkgComponent.CMD_UPDATE)

	def rebuildList(self):
		self.Flist = []
		self.Elist = []
		self.setStatus("list")
		self.opkg.startCmd(OpkgComponent.CMD_LIST, args={"package": "enigma2-plugin-softcams-*"})

	def buildPacketList(self):
		plist = []
		excludeList = [x[0] for x in self.Elist]
		divpng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_GUISKIN, "div-h.png"))
		installedpng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_GUISKIN, "icons/installed.png"))
		installablepng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_GUISKIN, "icons/installable.png"))

		if len(self.Flist) > 0:
			for x in self.Flist:
				if len(x) > 1:
					state = "installable" if x[0] not in excludeList else "installed"
					image = installablepng if x[0] not in excludeList else installedpng
					name = x[0]
					version = x[1]
					description = ""
					if len(x) > 2:
						description = x[2]
					plist.append((name, version, _(description), state, image, divpng))
			self['list'].setList(plist)
		else:
			self.setStatus('error')

	def top(self):
		self["list"].top()

	def pageUp(self):
		self["list"].pageUp()

	def up(self):
		self["list"].up()

	def down(self):
		self["list"].down()

	def pageDown(self):
		self["list"].pageDown()

	def bottom(self):
		self["list"].bottom()
