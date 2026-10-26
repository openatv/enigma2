from os.path import basename

from Components.ActionMap import HelpableActionMap
from Components.config import ConfigSelection, config, configfile
from Components.Sources.StaticText import StaticText
from Screens.ChoiceBox import ChoiceBox
from Screens.InputBox import InputBox
from Screens.MessageBox import MessageBox
from Screens.Setup import Setup
from Tools.BoundFunction import boundFunction
from Tools.Conversions import NumberScaler
from Tools.Swap import swapManager

startswap = None


def SwapAutostart():
	global startswap
	if config.usage.swapautostart.value:
		startswap = StartSwap()
		startswap.start()


class StartSwap:
	def start(self):
		swapManager.scan(self.startSwap2)

	def startSwap2(self, entries, error=""):
		if error:
			print(f"[SwapManager] Autostart scan: {error}")
		self.entries = [x for x in entries if x["available"] and not x["active"] and not x["noauto"]]
		self.startNext()

	def startNext(self, error=""):
		if error:
			print(f"[SwapManager] Autostart: {error}")
		if self.entries:
			swapManager.setActive(self.entries.pop(0), True, self.startNext)


class Swap(Setup):
	protectionSections = ("configuration", "storage")

	def __init__(self, session):
		self.entries = []
		self.scanning = False
		self.closed = False
		Setup.__init__(self, session, setup=None)
		# The old Swap skin describes a single device. Use the standard Setup layout.
		self.skinName = ["SwapManagerSetup", "Setup"]
		self["key_red"].setText(_("Close"))
		self["key_yellow"] = StaticText(_("Create"))
		self["key_blue"] = StaticText()
		self["swapname_summary"] = StaticText()
		self["swapactive_summary"] = StaticText()
		self["fullUIActions"].setEnabled(False)
		self["swapActions"] = HelpableActionMap(self, ["OkCancelActions", "ColorActions", "MenuActions"], {
			"cancel": (self.keyCancel, _("Close the swap manager")),
			"red": (self.keyCancel, _("Close the swap manager")),
			"ok": (self.actDeact, _("Start or stop the selected swap")),
			"green": (self.actDeact, _("Start or stop the selected swap")),
			"yellow": (self.doCreateSwap, _("Create a swap file")),
			"blue": (self.deleteSwap, _("Delete the selected swap file")),
			"menu": (self.swapMenu, _("Refresh, add an existing swap file or change autostart"))
		}, prio=-1, description=_("Swap Manager"))
		self.onClose.append(self.screenClosed)
		self.onLayoutFinish.append(self.protectedCallback(self.updateSwap))

	def screenClosed(self):
		self.closed = True

	def createSetup(self):
		self.list = []
		scaler = NumberScaler()
		for entry in self.entries:
			status = _("Active") if entry["active"] else _("Inactive") if entry["available"] else _("Unavailable")
			size = scaler.scale(entry["size"], style="Iec")
			value = ConfigSelection(choices=[("status", f"{status} / {size}")])
			value.setReadOnly(True)
			description = _("Swap file") if entry["type"] == "file" else _("Swap partition")
			description += "\n" + _("Used: %s") % scaler.scale(entry["used"], style="Iec")
			if entry["active"]:
				description += "  " + _("Priority: %d") % entry["priority"]
			if entry["fstab"]:
				description += "\n" + _("Configured in /etc/fstab. Starting or stopping here only changes the current session.")
			self.list.append((entry["path"], value, description))
		self["config"].setList(self.list)
		self.setTitle(_("Swap Manager"))

	def currentSwap(self):
		index = self["config"].getCurrentIndex()
		return self.entries[index] if index is not None and 0 <= index < len(self.entries) else None

	def selectionChanged(self):
		Setup.selectionChanged(self)
		entry = self.currentSwap()
		if "swapActions" in self:
			ready = not self.scanning and not swapManager.busy
			canToggle = bool(ready and entry and (entry["active"] or entry["available"]))
			canDelete = bool(ready and entry and entry["type"] == "file" and entry["available"])
			self["key_green"].setText((_("Stop") if entry["active"] else _("Start")) if canToggle else _("Refresh") if ready else "")
			self["key_yellow"].setText(_("Create") if ready else "")
			self["key_blue"].setText(_("Delete") if canDelete else "")
			self["swapActions"].setEnabledAction("ok", canToggle)
			self["swapActions"].setEnabledAction("green", ready)
			self["swapActions"].setEnabledAction("blue", canDelete)
			self["swapActions"].setEnabledAction("yellow", ready)
			self["swapActions"].setEnabledAction("menu", ready)
			self["key_menu"].setText(_("MENU") if ready else "")
			self["swapname_summary"].setText(entry["path"] if entry else "")
			self["swapactive_summary"].setText(self.getCurrentValue())

	def updateSwap(self):
		if not self.closed and not self.scanning and not swapManager.busy:
			self.scanning = True
			entry = self.currentSwap()
			self.selectedPath = entry["path"] if entry else None
			self.selectionChanged()
			self.setFootnote(_("Scanning swap devices..."))
			swapManager.scan(self.scanFinished)

	def scanFinished(self, entries, error):
		if not self.closed:
			self.scanning = False
			self.entries = entries
			self.createSetup()
			for index, entry in enumerate(entries):
				if entry["path"] == self.selectedPath:
					self["config"].setCurrentIndex(index)
					break
			self.selectionChanged()
			self.setFootnote(error or (_("No swap files or partitions found. Use Create to add a swap file.") if not entries else ""))

	def operationFinished(self, error=""):
		if not self.closed:
			self.updateSwap()
			if error:
				self.session.open(MessageBox, error, type=MessageBox.TYPE_ERROR)

	def actDeact(self):
		entry = self.currentSwap()
		if entry and (entry["active"] or entry["available"]) and not self.scanning and not swapManager.busy:
			swapManager.setActive(entry, not entry["active"], self.operationFinished)
			self.selectionChanged()
			if swapManager.busy:
				self.setFootnote(_("Please wait. Stopping swap can take a while."))
		else:
			self.updateSwap()

	def deleteSwap(self):
		entry = self.currentSwap()
		if entry and entry["type"] == "file" and entry["available"] and not swapManager.busy:
			self.session.openWithCallback(boundFunction(self.deleteConfirmed, entry.copy()), MessageBox,
				_("Delete swap file '%s'?\nAn active file will be stopped first. Its swap entry in /etc/fstab will also be removed.") % entry["path"], type=MessageBox.TYPE_YESNO, default=False)

	def deleteConfirmed(self, entry, answer):
		if answer:
			swapManager.delete(entry, self.operationFinished)
			self.selectionChanged()
			if swapManager.busy:
				self.setFootnote(_("Please wait while the swap file is stopped and deleted."))

	def doCreateSwap(self):
		if not self.scanning and not swapManager.busy:
			locations = swapManager.getLocations()
			if locations:
				self.session.openWithCallback(self.createSelected, SwapCreate, locations)
			else:
				self.session.open(MessageBox, _("No writable ext2, ext3 or ext4 storage is available for a swap file."), type=MessageBox.TYPE_ERROR)

	def createSelected(self, selection=None):
		if selection:
			swapManager.create(selection[0], selection[1], self.operationFinished)
			self.selectionChanged()
			if swapManager.busy:
				self.setFootnote(_("Creating swap file. This can take several minutes."))

	def swapMenu(self):
		choices = [(_("Refresh"), "refresh"), (_("Add an existing swap file"), "add"), (_("Autostart"), "autostart")]
		self.session.openWithCallback(self.menuSelected, ChoiceBox, choiceList=choices, windowTitle=_("Swap Manager"))

	def menuSelected(self, answer):
		if answer:
			if answer[1] == "refresh":
				self.updateSwap()
			elif answer[1] == "add":
				self.session.openWithCallback(self.addFile, InputBox, title=_("Full path of the existing swap file"), text="/media/hdd/swapfile")
			elif answer[1] == "autostart":
				self.session.openWithCallback(lambda *args: self.updateSwap(), SwapAutostartSetup)

	def addFile(self, path):
		if path:
			try:
				swapManager.addFile(path)
			except (OSError, ValueError) as error:
				self.session.open(MessageBox, str(error), type=MessageBox.TYPE_ERROR)
			self.updateSwap()

	def keyCancel(self):
		if not swapManager.busy:
			self.close()


class SwapCreate(Setup):
	protectionSections = ("configuration", "storage")

	def __init__(self, session, locations):
		self.locations = locations
		choices = []
		for location in locations:
			name = location["name"]
			shortName = f"{name[:21]}..." if len(name) > 24 else name
			label = f'{name} (/)' if location["path"] == "/" else f'{basename(location["source"])}: {shortName}'
			choices.append((location["path"], label))
		self.location = ConfigSelection(choices=choices)
		self.size = ConfigSelection(default="256", choices=[(str(x), NumberScaler().scale(x * 1024 * 1024, style="Iec")) for x in (32, 64, 128, 256, 512, 1024, 1536, 2048, 4096, 8192)])
		Setup.__init__(self, session, setup=None)
		self["key_green"].setText(_("Create"))

	def createSetup(self):
		location = next(x for x in self.locations if x["path"] == self.location.value)
		description = "\n".join((location["name"], _("Device: %s") % location["source"], _("Mount point: %s") % location["path"], _("Free space: %s") % NumberScaler().scale(location["free"], style="Iec")))
		currentItem = self["config"].getCurrent()
		self.list = [
			(_("Storage device"), self.location, description),
			(_("Size"), self.size, _("The file is created inactive. Start it in the swap manager when needed."))
		]
		self["config"].setList(self.list)
		self.moveToItem(currentItem)
		self.setTitle(_("Create swap file"))
		self.selectionChanged()

	def keySave(self):
		location = next(x for x in self.locations if x["path"] == self.location.value)
		self.close((location, int(self.size.value)))


class SwapAutostartSetup(Setup):
	protectionSections = ("configuration", "storage")

	def __init__(self, session):
		Setup.__init__(self, session, setup=None)

	def createSetup(self):
		self.list = [(_("Enable Swap at startup"), config.usage.swapautostart, _("Start all available swap files and partitions when Enigma2 starts. Entries marked noauto in /etc/fstab are excluded. System autostart from /etc/fstab is independent of this setting."))]
		self["config"].setList(self.list)
		self.setTitle(_("Swap autostart"))

	def keySave(self):
		config.usage.swapautostart.save()
		configfile.save()
		self.close()
