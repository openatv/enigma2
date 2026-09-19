from os import W_OK, access, listdir, remove, rmdir, stat, statvfs
from os.path import exists, isdir, ismount, join, realpath
from re import compile, fullmatch, sub
from shlex import split
from tempfile import mkdtemp

from Components.ActionMap import HelpableActionMap
from Components.ChoiceList import ChoiceEntryComponent, ChoiceList
from Components.config import ConfigInteger, ConfigSelection
from Components.Console import Console
from Components.Harddisk import harddiskmanager
from Components.Label import Label
from Components.Sources.StaticText import StaticText
from Components.SystemInfo import BoxInfo, getBoxDisplayName
from Screens.Console import Console as ConsoleScreen
from Screens.LocationBox import DEFAULT_INHIBIT_DEVICES
from Screens.MessageBox import MessageBox
from Screens.Screen import Screen
from Screens.Setup import Setup
from Screens.Standby import QUIT_REBOOT, QUIT_RESTART, TryQuitMainloop
from Screens.VirtualKeyBoard import VirtualKeyBoard
from Tools.Directories import fileReadLines, fileReadLine, fileWriteLine, fileWriteLines
from Tools.MultiBoot import MultiBoot

MODULE_NAME = __name__.split(".")[-1]

ACTION_SELECT = 0
ACTION_CREATE = 1

MOUNT_DEVICE = 0
MOUNT_MOUNTPOINT = 1
MOUNT_FILESYSTEM = 2
MOUNT_OPTIONS = 3
MOUNT_DUMP = 4
MOUNT_FSCK_ORDER = 5
MAX_MOUNT = 6
MKFS_EXT4_FAST_OPTIONS = "-E nodiscard,lazy_itable_init=1,lazy_journal_init=1 -i 65536 -m 0"
MULTIBOOT_SWAP_SIZE_MIB = 512


def getDiskDevice(device):
	if not device:
		return None
	device = realpath(device) if exists(device) else device
	base = device.rsplit("/", 1)[-1]
	if base.startswith(("mmcblk", "nvme")):
		base = sub(r"p\d+$", "", base)
	elif base.startswith(("sd", "cf")):
		base = sub(r"\d+$", "", base)
	return f"/dev/{base}"


def canExpandNativeSlots():
	if not BoxInfo.getItem("HasNewNativeMultiboot") or not BoxInfo.getItem("canMultiBoot") or BoxInfo.getItem("HasKexecMultiboot") or BoxInfo.getItem("HasGPT") or BoxInfo.getItem("HasChkrootMultiboot") or BoxInfo.getItem("hasUBIMB"):
		return False
	for slotCode, slotData in MultiBoot.getBootSlots().items():
		cmdLines = slotData.get("cmdline", {})
		cmdLines = cmdLines.values() if isinstance(cmdLines, dict) else (cmdLines,)
		if slotCode.isdecimal() and slotData.get("startupfile") and any("root=" in cmdLine and "kernel=" in cmdLine for cmdLine in cmdLines if cmdLine):
			return True
	return False


def isAdditionalSlot(slotCode):
	slotData = MultiBoot.getBootSlots().get(slotCode, {})
	cmdLines = slotData.get("cmdline", {})
	cmdLines = cmdLines.values() if isinstance(cmdLines, dict) else (cmdLines,)
	if any("extra=true" in cmdLine for cmdLine in cmdLines if cmdLine):
		return True
	if not slotCode or not slotCode.isdecimal():
		return False
	if BoxInfo.getItem("HasGPT"):
		return getDiskDevice(slotData.get("device")) == "/dev/mmcblk1"
	if BoxInfo.getItem("HasKexecMultiboot"):
		return int(slotCode) >= 4
	if canExpandNativeSlots():
		bootDisk = getDiskDevice(MultiBoot.getBootDevice())
		rootDisk = getDiskDevice(slotData.get("device"))
		return bool(slotData.get("rootsubdir") and bootDisk and rootDisk and rootDisk != bootDisk)
	return False


def hasAdditionalSlots():
	return any(isAdditionalSlot(slotCode) for slotCode in MultiBoot.getBootSlots())


class MultiBootManager(Screen):
	# NOTE: This embedded skin will be affected by the Choicelist parameters and ChoiceList font in the current skin!  This screen should be skinned.
	# 	See Components/ChoiceList.py to see the hard coded defaults for which this embedded screen has been designed.
	skin = """
	<screen title="MultiBoot Manager" position="center,center" size="900,455">
		<widget name="slotlist" position="10,10" size="880,275" scrollbarMode="showOnDemand" />
		<widget name="description" position="10,e-160" size="880,100" font="Regular;20" valign="bottom" />
		<widget source="key_red" render="Label" position="10,e-50" size="140,40" backgroundColor="key_red" font="Regular;20" conditional="key_red" foregroundColor="key_text" halign="center" noWrap="1" valign="center">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="key_green" render="Label" position="160,e-50" size="140,40" backgroundColor="key_green" font="Regular;20" conditional="key_green" foregroundColor="key_text" halign="center" noWrap="1" valign="center">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="key_yellow" render="Label" position="310,e-50" size="140,40" backgroundColor="key_yellow" font="Regular;20" conditional="key_yellow" foregroundColor="key_text" halign="center" noWrap="1" valign="center">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="key_blue" render="Label" position="460,e-50" size="140,40" backgroundColor="key_blue" font="Regular;20" conditional="key_blue" foregroundColor="key_text" halign="center" noWrap="1" valign="center">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="key_info" render="Label" position="e-300,e-50" size="90,40" backgroundColor="key_back" font="Regular;20" conditional="key_info" foregroundColor="key_text" halign="center" noWrap="1" valign="center">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="key_text" render="Label" position="e-200,e-50" size="90,40" backgroundColor="key_back" font="Regular;20" conditional="key_text" foregroundColor="key_text" halign="center" noWrap="1" valign="center">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="key_help" render="Label" position="e-100,e-50" size="90,40" backgroundColor="key_back" font="Regular;20" conditional="key_help" foregroundColor="key_text" halign="center" noWrap="1" valign="center">
			<convert type="ConditionalShowHide" />
		</widget>
	</screen>"""

	def __init__(self, session, *args):
		Screen.__init__(self, session, enableHelp=True)
		self.setTitle(_("MultiBoot Manager"))
		self["slotlist"] = ChoiceList([ChoiceEntryComponent("", (_("Loading slot information, please wait..."), "Loading"))])
		self.defaultDescription = _("Press the UP/DOWN buttons to select a slot and press OK or GREEN to reboot to that slot. Press YELLOW to delete the selected image or hold YELLOW to permanently wipe it. A deleted image can be restored with BLUE, but a wiped image cannot. Press INFO to show or hide empty slots.")
		self["description"] = Label(self.defaultDescription)
		self["key_red"] = StaticText(_("Cancel"))
		self["key_green"] = StaticText(_("Reboot"))
		self["key_yellow"] = StaticText()
		self["key_blue"] = StaticText()
		self["key_info"] = StaticText()
		self["key_text"] = StaticText()
		actionDescription = _("MultiBoot Manager Actions")
		self["actions"] = HelpableActionMap(self, ["CancelActions", "NavigationActions"], {
			"cancel": (self.keyCancel, _("Cancel the slot selection and exit")),
			"close": (self.keyCloseRecursive, _("Cancel the slot selection and exit all menus")),
			"top": (self.keyTop, _("Move to first line / screen")),
			"pageUp": (self.keyPageUp, _("Move up a screen")),
			"up": (self.keyUp, _("Move up a line")),
			# "left": (self.keyUp, _("Move up a line")),
			# "right": (self.keyDown, _("Move down a line")),
			"down": (self.keyDown, _("Move down a line")),
			"pageDown": (self.keyPageDown, _("Move down a screen")),
			"bottom": (self.keyBottom, _("Move to last line / screen"))
		}, prio=0, description=actionDescription)
		self["restartActions"] = HelpableActionMap(self, ["OkSaveActions"], {
			"save": (self.keyReboot, _("Select the highlighted slot and reboot")),
			"ok": (self.keyReboot, _("Select the highlighted slot and reboot")),
		}, prio=0, description=actionDescription)
		self["restartActions"].setEnabled(False)
		self["emptyActions"] = HelpableActionMap(self, ["ColorActions"], {
			"yellow": (self.keyEmptySlot, _("Empty or Wipe the highlighted slot"))
		}, prio=0, description=actionDescription)
		self["emptyActions"].setEnabled(False)
		self["wipeActions"] = HelpableActionMap(self, ["ColorActions"], {
			"yellowlong": (self.keyWipeSlot, _("Permanently wipe the highlighted slot"))
		}, prio=0, description=actionDescription)
		self["wipeActions"].setEnabled(False)
		self["restoreActions"] = HelpableActionMap(self, ["ColorActions"], {
			"blue": (self.keyRestoreSlot, _("Restore the highlighted slot"))
		}, prio=0, description=actionDescription)
		self["restoreActions"].setEnabled(False)
		self["infoActions"] = HelpableActionMap(self, ["InfoActions"], {
			"info": (self.keyToggleEmptySlots, _("Show or hide empty slots"))
		}, prio=0, description=actionDescription)
		self["infoActions"].setEnabled(False)
		self["renameActions"] = HelpableActionMap(self, "VirtualKeyboardActions", {
			"showVirtualKeyboard": (self.keyRenameSlot, _("Rename the highlighted slot"))
		}, prio=0, description=actionDescription)
		self["renameActions"].setEnabled(False)
		if (BoxInfo.getItem("HasKexecMultiboot") or BoxInfo.getItem("HasGPT") or BoxInfo.getItem("HasChkrootMultiboot") or canExpandNativeSlots()) and not BoxInfo.getItem("hasUBIMB"):
			self["addActions"] = HelpableActionMap(self, ["ColorActions"], {
				"blue": (self.keyAddSlots, _("Add or change additional slots"))
			}, prio=0, description=actionDescription)
			self["addActions"].setEnabled(False)
		self.editSlotCode = None
		self.showEmptySlots = False
		self.emptySlotCount = 0
		self.onLayoutFinish.append(self.layoutFinished)
		self.initialize = True
		self.callLater(self.getSlotList)

	def layoutFinished(self):
		self["slotlist"].enableAutoNavigation(False)

	def getSlotList(self):
		current = self["slotlist"].getCurrent()
		currentData = current[0][1] if current and current[0] else None
		selectedSlot = currentData[:2] if isinstance(currentData, tuple) else None
		selectedIndex = self["slotlist"].getSelectedIndex()

		def getSlotListCallback(slotList):
			slots = []
			if slotList:
				slotCode, bootCode = MultiBoot.getCurrentSlotAndBootCodes()
				activeMsg = "  -  %s" % _("Active")
				slotMsg = _("Slot '%s' %s: %s%s")
				slotData = {}
				self.emptySlotCount = sum(1 for slotInfo in slotList.values() if slotInfo.get("status") == "empty")
				for slot in sorted(slotList.keys(), key=lambda x: (not x.isnumeric(), int(x) if x.isnumeric() else x)):
					slotInfo = slotList[slot]
					status = slotInfo.get("status") or "unknown"
					if not self.showEmptySlots and status == "empty":
						continue
					for boot in slotInfo.get("bootCodes") or [""]:
						if slotData.get(boot) is None:
							slotData[boot] = []
						active = activeMsg if boot == bootCode and slot == slotCode else ""
						device = slotInfo.get("device") or _("Unknown")
						slotType = "eMMC" if "mmcblk" in device else "MTD" if "mtd" in device else "UBI" if "ubi" in device else "USB"
						slotData[boot].append(ChoiceEntryComponent("none" if boot else "", (slotMsg % (slot, slotType, slotInfo.get("imagename") or _("Unknown"), active), (slot, boot, status, slotInfo.get("ubi", False), active != ""))))
				for bootCode in sorted(slotData.keys()):
					if bootCode == "":
						continue
					slots.append(ChoiceEntryComponent("", (MultiBoot.getBootCodeDescription(bootCode), None)))
					slots.extend(slotData[bootCode])
				if "" in slotData:
					slots.extend(slotData[""])
				if not slots:
					slots.append(ChoiceEntryComponent("", (_("No slot images found"), "Void")))
				if self.initialize:
					self.initialize = False
					index = 0
					for itemIndex, item in enumerate(slots):
						if isinstance(item[0][1], tuple) and item[0][1][4]:
							index = itemIndex
							break
				elif selectedSlot:
					index = min(selectedIndex, len(slots) - 1)
					for itemIndex, item in enumerate(slots):
						if isinstance(item[0][1], tuple) and item[0][1][:2] == selectedSlot:
							index = itemIndex
							break
				else:
					index = min(selectedIndex, len(slots) - 1)
			else:
				self.emptySlotCount = 0
				slots.append(ChoiceEntryComponent("", (_("No slot images found"), "Void")))
				index = 0
			self["key_info"].setText(_("INFO") if self.emptySlotCount else "")
			self["infoActions"].setEnabled(bool(self.emptySlotCount))
			self["slotlist"].setList(slots)
			self["slotlist"].moveToIndex(index)
			self.selectionChanged()

		MultiBoot.getSlotImageList(getSlotListCallback)

	def selectionChanged(self):
		self["wipeActions"].setEnabled(False)
		self["description"].setText(self.defaultDescription)
		if "addActions" in self:
			self["addActions"].setEnabled(False)
		slotCode = MultiBoot.getCurrentSlotCode()
		selection = self["slotlist"].getCurrent()
		current = selection[0] if selection else None
		if not current or not isinstance(current[1], tuple):
			self["key_green"].setText("")
			self["key_yellow"].setText("")
			self["key_blue"].setText("")
			self["key_text"].setText("")
			self["restartActions"].setEnabled(False)
			self["emptyActions"].setEnabled(False)
			self["restoreActions"].setEnabled(False)
			self["renameActions"].setEnabled(False)
			if "addActions" in self:
				self["addActions"].setEnabled(False)
			return
		slot = current[1][0]
		status = current[1][2]
		ubi = current[1][3]
		active = current[1][4]
		if BoxInfo.getItem("HasChkrootMultiboot") and slot == "1" and active and not BoxInfo.getItem("hasUBIMB"):
			additionalSlots = hasAdditionalSlots()
			description = _("Press the UP/DOWN buttons to select a slot, then press OK or GREEN to reboot into that slot. If available, YELLOW will disable MultiBoot, delete, or wipe the selected slot.")
			self["description"].setText("%s %s" % (description, _("Press BLUE to change the additional slots.") if additionalSlots else _("Press BLUE to add more slots.")))
			self["key_green"].setText(_("Reboot"))
			self["key_yellow"].setText(_("Disable"))
			self["key_blue"].setText(_("Change slots") if additionalSlots else _("Add slots"))
			self["restartActions"].setEnabled(True)
			self["emptyActions"].setEnabled(True)
			self["restoreActions"].setEnabled(False)
			self["addActions"].setEnabled(True)
		elif slot == slotCode or status in ("android", "androidlinuxse", "recovery"):
			self["key_green"].setText(_("Reboot"))
			self["key_yellow"].setText("")
			self["key_blue"].setText("")
			self["restartActions"].setEnabled(True)
			self["emptyActions"].setEnabled(False)
			self["restoreActions"].setEnabled(False)
		elif status == "hidden":
			self["key_green"].setText("")
			self["key_yellow"].setText("")
			self["key_blue"].setText(_("Restore"))
			self["restartActions"].setEnabled(False)
			self["emptyActions"].setEnabled(False)
			self["restoreActions"].setEnabled(True)
		elif status in ("empty", "unknown"):
			self["key_green"].setText("")
			self["key_yellow"].setText("")
			self["key_blue"].setText("")
			self["restartActions"].setEnabled(False)
			self["emptyActions"].setEnabled(False)
			self["restoreActions"].setEnabled(False)
		elif ubi:
			self["key_green"].setText(_("Reboot"))
			self["key_yellow"].setText(_("Wipe"))
			self["key_blue"].setText("")
			self["restartActions"].setEnabled(True)
			self["emptyActions"].setEnabled(True)
			self["wipeActions"].setEnabled(status == "active")
			self["restoreActions"].setEnabled(False)
		else:
			self["key_green"].setText(_("Reboot"))
			self["key_yellow"].setText(_("Delete"))
			self["key_blue"].setText("")
			self["restartActions"].setEnabled(True)
			self["emptyActions"].setEnabled(True)
			self["wipeActions"].setEnabled(status == "active")
			self["restoreActions"].setEnabled(False)
		if "addActions" in self and ((BoxInfo.getItem("HasKexecMultiboot") and slotCode == "R") or BoxInfo.getItem("HasGPT") or canExpandNativeSlots()):
			additionalSlots = hasAdditionalSlots()
			if status == "hidden" or (additionalSlots and isAdditionalSlot(slotCode)):
				self["addActions"].setEnabled(False)
			else:
				self["restoreActions"].setEnabled(False)
				self["addActions"].setEnabled(True)
				self["key_blue"].setText(_("Change slots") if additionalSlots else _("Add slots"))
		if status == "active" and slot.isdecimal():
			self["renameActions"].setEnabled(True)
			self["key_text"].setText("TEXT")
		else:
			self["renameActions"].setEnabled(False)
			self["key_text"].setText("")

	def keyCancel(self):
		self.close()

	def keyCloseRecursive(self):
		self.close(True)

	def keyToggleEmptySlots(self):
		if self.emptySlotCount:
			self.showEmptySlots = not self.showEmptySlots
			self.getSlotList()

	def keyTop(self):
		self["slotlist"].instance.moveSelection(self["slotlist"].instance.moveTop)
		while self["slotlist"].getCurrent()[0][1] is None:
			self["slotlist"].instance.moveSelection(self["slotlist"].instance.moveDown)
		self.selectionChanged()

	def keyPageUp(self):
		self["slotlist"].instance.moveSelection(self["slotlist"].instance.movePageUp)
		while self["slotlist"].getCurrent()[0][1] is None:
			self["slotlist"].instance.moveSelection(self["slotlist"].instance.moveDown)
		self.selectionChanged()

	def keyUp(self):
		self["slotlist"].instance.moveSelection(self["slotlist"].instance.moveUp)
		while self["slotlist"].getCurrent()[0][1] is None:
			self["slotlist"].instance.moveSelection(self["slotlist"].instance.moveUp)
		self.selectionChanged()

	def keyDown(self):
		self["slotlist"].instance.moveSelection(self["slotlist"].instance.moveDown)
		while self["slotlist"].getCurrent()[0][1] is None:
			self["slotlist"].instance.moveSelection(self["slotlist"].instance.moveDown)
		self.selectionChanged()

	def keyPageDown(self):
		self["slotlist"].instance.moveSelection(self["slotlist"].instance.movePageDown)
		while self["slotlist"].getCurrent()[0][1] is None:
			self["slotlist"].instance.moveSelection(self["slotlist"].instance.moveDown)
		self.selectionChanged()

	def keyBottom(self):
		self["slotlist"].instance.moveSelection(self["slotlist"].instance.moveEnd)
		while self["slotlist"].getCurrent()[0][1] is None:
			self["slotlist"].instance.moveSelection(self["slotlist"].instance.moveDown)
		self.selectionChanged()

	def keyReboot(self):
		def rebootCallback(result):
			current = self["slotlist"].getCurrent()[0]
			if result:
				print(f"[MultiBootManager] {current[0]} activation was not completely successful, status {result}!")
			else:
				print(f"[MultiBootManager] {current[0]} activated.")
				self.session.open(TryQuitMainloop, QUIT_REBOOT)

		current = self["slotlist"].getCurrent()[0]
		MultiBoot.activateSlot(current[1][0], current[1][1], rebootCallback)

	def keyEmptySlot(self):
		def keyDisableChkrootCallback(answer):
			def disableChkrootCallback(result):
				if result not in (0, 1):
					print(f"[MultiBootManager] Disable was not completely successful, status {result}!")
					self.session.open(MessageBox, _("Disabling Chkroot failed!"), MessageBox.TYPE_ERROR, timeout=5)
				else:
					self.session.open(TryQuitMainloop, QUIT_REBOOT)

			if answer:
				MultiBoot.wipeChkroot(disableChkrootCallback)

		def keyEmptySlotCallback(answer):
			def emptySlotCallback(result):
				current = self["slotlist"].getCurrent()[0]
				if result:
					print(f"[MultiBootManager] {current[0]} deletion was not completely successful, status {result}!")
				else:
					print(f"[MultiBootManager] {current[0]} marked as deleted.")
				self.getSlotList()

			if answer:
				current = self["slotlist"].getCurrent()[0]
				MultiBoot.emptySlot(current[1][0], emptySlotCallback)

		current = self["slotlist"].getCurrent()[0]
		slot = current[1][0]
		# currentTemp = current[1][4]  # This does not appear to be used!
		if BoxInfo.getItem("HasChkrootMultiboot") and slot == "1" and current and not BoxInfo.getItem("hasUBIMB"):
			self.session.openWithCallback(keyDisableChkrootCallback, MessageBox, _("Disable Chkroot Multiboot?"), windowTitle=self.getTitle())
		else:
			self.session.openWithCallback(keyEmptySlotCallback, MessageBox, f"{self["slotlist"].getCurrent()[0][0]}\n\n{_("Delete this slot?")}", windowTitle=self.getTitle())

	def keyWipeSlot(self):
		selection = self["slotlist"].getCurrent()
		current = selection[0] if selection else None
		if not current or not isinstance(current[1], tuple) or current[1][2] != "active" or current[1][0] == MultiBoot.getCurrentSlotCode():
			return
		slotName = current[0]
		slotCode = current[1][0]

		def keyWipeSlotCallback(answer):
			def wipeSlotCallback(result):
				if result:
					print(f"[MultiBootManager] {slotName} wipe was not completely successful, status {result}!")
				else:
					print(f"[MultiBootManager] {slotName} permanently wiped.")
				self.getSlotList()

			if answer:
				self["wipeActions"].setEnabled(False)
				MultiBoot.wipeSlot(slotCode, wipeSlotCallback)

		message = "%s\n\n%s" % (slotName, _("Permanently wipe this slot? All files in the slot will be deleted and cannot be restored."))
		self.session.openWithCallback(keyWipeSlotCallback, MessageBox, message, MessageBox.TYPE_YESNO, default=False, windowTitle=self.getTitle())

	def keyRestoreSlot(self):
		def keyRestoreSlotCallback(result):
			current = self["slotlist"].getCurrent()[0]
			if result:
				print(f"[MultiBootManager] {current[0]} restoration was not completely successful, status {result}!")
			else:
				print(f"[MultiBootManager] {current[0]} restored.")
			self.getSlotList()

		current = self["slotlist"].getCurrent()[0]
		MultiBoot.restoreSlot(current[1][0], keyRestoreSlotCallback)

	def keyRenameSlot(self):
		def renameSlotCallback(newName):
			def renameCallback(result):
				if result:
					print(f"[MultiBootManager] Rename of slot failed, status {result}!")
				self.getSlotList()

			slotCode = self.editSlotCode
			self.editSlotCode = None
			if newName is not None and slotCode is not None:
				MultiBoot.renameSlot(slotCode, newName.strip(), renameCallback)

		current = self["slotlist"].getCurrent()
		if current and current[0][1]:
			slotCode, _bootCode, status, _ubi, _current = current[0][1]
			if status in ("active",) and slotCode.isdecimal():
				editable = current[0][0].split(": ", 1)[-1].rsplit(" (", 1)[0]
				index = editable.rfind("  -  ")
				if index >= 0:
					editable = editable[:index]
				self.editSlotCode = slotCode
				self.session.openWithCallback(renameSlotCallback, VirtualKeyBoard, title=_("Rename slot '%s' (leave empty to reset):") % slotCode, text=editable)

	def keyAddSlots(self):
		if BoxInfo.getItem("HasGPT"):
			self.session.open(GPTSlotManager)
		elif BoxInfo.getItem("HasChkrootMultiboot") and not BoxInfo.getItem("hasUBIMB"):
			self.session.open(ChkrootSlotManager)
		elif canExpandNativeSlots():
			self.session.open(NativeSlotManager)
		elif BoxInfo.getItem("HasKexecMultiboot"):
			self.session.open(KexecSlotManager)


class KexecInit(Screen):
	skin = """
	<screen name="KexecInit" title="Kexec MultiBoot Manager" position="center,center" size="900,600" resolution="1280,720">
		<widget name="description" position="0,0" size="e,e-50" font="Regular;20" />
		<widget source="key_red" render="Label" position="0,e-40" size="180,40" backgroundColor="key_red" conditional="key_red" font="Regular;20" foregroundColor="key_text" halign="center" valign="center">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="key_green" render="Label" position="190,e-40" size="180,40" backgroundColor="key_green" conditional="key_green" font="Regular;20" foregroundColor="key_text" halign="center" valign="center">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="key_help" render="Label" position="e-80,e-40" size="80,40" backgroundColor="key_back" conditional="key_help" font="Regular;20" foregroundColor="key_text" halign="center" valign="center">
			<convert type="ConditionalShowHide" />
		</widget>
	</screen>"""

	def __init__(self, session, *args):
		Screen.__init__(self, session, enableHelp=True)
		self.setTitle(_("Kexec MultiBoot Manager"))
		self["key_red"] = StaticText()
		self["key_green"] = StaticText()
		self["description"] = Label()
		self["actions"] = HelpableActionMap(self, ["OkCancelActions"], {
			"ok": (self.close, _("Close the Kexec MultiBoot Manager")),
			"cancel": (self.close, _("Close the Kexec MultiBoot Manager"))
		}, prio=0, description=_("Kexec MultiBoot Actions"))
		if exists("/usr/bin/kernel_auto.bin") and exists("/usr/bin/STARTUP.cpio.gz"):
			self["key_red"].setText(_("Remove Files"))
			self["key_green"].setText(_("Initialize"))
			self.descriptionSuffix = _("The %s %s will reboot within 10 seconds, unless there are eMMC slots to restore. Restoring eMMC slots can take from 1 to 5 minutes per slot.") % getBoxDisplayName()
			self["description"].setText("%s\n\n%s" % (_("Press GREEN to enable MultiBoot!"), self.descriptionSuffix))
			self["kexecActions"] = HelpableActionMap(self, ["ColorActions"], {
				"red": (self.removeFiles, _("Remove the MultiBoot files")),
				"green": (self.rootInit, _("Start the Kexec initialization"))
			}, prio=0, description=_("Kexec MultiBoot Actions"))
		else:
			self.descriptionSuffix = ""
			self["description"].setText("%s: %s\n\n%s" % (_("NOTE"), _("Unable to initialize Kexec MultiBoot!"), _("Kexec MultiBoot files are missing.")))

	def rootInit(self):
		def rootInitCallback(*args, **kwargs):
			model = BoxInfo.getItem("model")
			for usbSlot in range(1, 4):
				if exists(f"/media/hdd/{model}/linuxrootfs{usbSlot}"):
					Console().ePopen(f"/bin/cp -R /media/hdd/{model}/linuxrootfs{usbSlot} . /")
			self.session.open(TryQuitMainloop, QUIT_REBOOT)

		self["actions"].setEnabled(False)  # This function takes time so disable the ActionMaps to avoid responding to multiple button presses.
		self["kexecActions"].setEnabled(False)
		self["description"].setText("%s\n\n%s" % (_("Kexec MultiBoot Initialization in progress!"), self.descriptionSuffix))
		mtdRootFs = BoxInfo.getItem("mtdrootfs")
		fileWriteLine("/STARTUP", f"kernel=/zImage root=/dev/{mtdRootFs} rootsubdir=linuxrootfs0", source=MODULE_NAME)
		fileWriteLine("/STARTUP_RECOVERY", f"kernel=/zImage root=/dev/{mtdRootFs} rootsubdir=linuxrootfs0", source=MODULE_NAME)
		fileWriteLine("/STARTUP_1", f"kernel=/linuxrootfs1/zImage root=/dev/{mtdRootFs} rootsubdir=linuxrootfs1", source=MODULE_NAME)
		fileWriteLine("/STARTUP_2", f"kernel=/linuxrootfs2/zImage root=/dev/{mtdRootFs} rootsubdir=linuxrootfs2", source=MODULE_NAME)
		fileWriteLine("/STARTUP_3", f"kernel=/linuxrootfs3/zImage root=/dev/{mtdRootFs} rootsubdir=linuxrootfs3", source=MODULE_NAME)
		mtdKernel = BoxInfo.getItem("mtdkernel")
		cmdList = []
		cmdList.append(f"/bin/dd if=/dev/{mtdKernel} of=/zImage")  # Backup old kernel.
		cmdList.append(f"/bin/dd if=/usr/bin/kernel_auto.bin of=/dev/{mtdKernel}")  # Create new kernel.
		cmdList.append("/bin/mv /usr/bin/STARTUP.cpio.gz /STARTUP.cpio.gz")  # Copy user root routine.
		Console().eBatch(cmdList, rootInitCallback, debug=True)

	def removeFiles(self):
		def removeFilesCallback(answer):
			if answer:
				for file in files:
					try:
						remove(file)
					except OSError as err:
						print("[MultiBootManager] Error %d: Unable to delete MultiBoot file '%s'.  (%s)" % (err.errno, file, err.strerror))
				self.close()

		files = ("/usr/bin/kernel_auto.bin", "/usr/bin/STARTUP.cpio.gz")
		self.session.openWithCallback(removeFilesCallback, MessageBox, "%s\n\n%s" % (_("Permanently remove the MultiBoot files?"), "\n".join(files)), simple=True)


class KexecSlotManager(Setup):
	def __init__(self, session):
		def getGreenHelpText():
			return {
				ACTION_SELECT: _("Select a device to use for the additional slots"),
				ACTION_CREATE: _("Create the additional slots on the selected device")
			}.get(self.green, _("Help text uninitialized"))

		self.kexecSlotManagerLocation = ConfigSelection(default=None, choices=[(None, _("<Select a device>"))])
		self.kexecSlotManagerSlots = ConfigInteger(default=1, limits=(1, 50))
		self.kexecSlotManagerDevice = None
		Setup.__init__(self, session=session, setup="KexecSlotManager")
		self.setTitle(_("Slot Manager"))
		self["fullUIActions"] = HelpableActionMap(self, ["CancelSaveActions"], {
			"cancel": (self.keyCancel, _("Cancel any changed settings and exit")),
			"close": (self.closeRecursive, _("Cancel any changed settings and exit all menus"))
		}, prio=0, description=_("Common Setup Actions"))  # Override the ConfigList "fullUIActions" action map so that we can control the GREEN button here.
		self["actions"] = HelpableActionMap(self, ["ColorActions"], {
			"green": (self.keyGreen, getGreenHelpText)
		}, prio=-1, description=_("Slot Manager Actions"))
		self.console = Console()
		self.freespace = 0
		self.deviceData = {}
		self.mountData = None
		self.green = ACTION_SELECT

	def layoutFinished(self):
		Setup.layoutFinished(self)
		self.readDevices()

	def selectionChanged(self):
		Setup.selectionChanged(self)
		self.updateStatus()

	def changedEntry(self):
		Setup.changedEntry(self)
		self.updateStatus()

	def keySelect(self):
		if self.getCurrentItem() == self.kexecSlotManagerLocation:
			self.showDeviceSelection()
		else:
			Setup.keySelect(self)

	def keyGreen(self):
		def restartCallback(answer):
			if answer is True:
				self.session.open(TryQuitMainloop, QUIT_REBOOT)
			else:
				self.close()

		def createSlots():
			startupRe = compile(r"^STARTUP_(\d+)$")
			try:
				for startupFile in listdir("/"):
					match = startupRe.match(startupFile)
					if match and int(match.group(1)) >= 4:
						remove(join("/", startupFile))
			except OSError as err:
				print(f"[KexecSlotManager] Error {err.errno}: Unable to remove obsolete additional STARTUP files.  ({err.strerror})")
				self.session.open(MessageBox, _("Unable to remove the obsolete additional STARTUP files."), MessageBox.TYPE_ERROR, timeout=10, windowTitle=self.getTitle())
				return
			model = BoxInfo.getItem("model")[2:]
			for slot in range(4, self.kexecSlotManagerSlots.value + 4):
				rootWait = ""
				if model == "duo4k":
					rootWait = " rootwait=40"
				if model == "duo4kse":
					rootWait = " rootwait=35"
				startupFileContent = "kernel=%s/linuxrootfs%d/zImage root=UUID=%s rootsubdir=%s/linuxrootfs%d%s" % (model, slot, self.kexecSlotManagerDevice, model, slot, rootWait)
				with open("/STARTUP_%d" % slot, "w") as fd:
					fd.write(startupFileContent)
			self.session.openWithCallback(restartCallback, MessageBox, _("Restart necessary, restart GUI now?"), MessageBox.TYPE_YESNO, windowTitle=self.getTitle())

		if self.kexecSlotManagerDevice:
			createSlots()
		else:
			self.showDeviceSelection()

	def showDeviceSelection(self):
		def readDevicesCallback():
			choiceList = [
				(_("Cancel"), "")
			]
			for deviceID, deviceData in self.deviceData.items():
				choiceList.append((f"{deviceData[1]} ({deviceData[0]})", deviceID))
			self.session.openWithCallback(self.deviceSelectionCallback, MessageBox, text=_("Please select the device or Cancel to cancel the selection."), list=choiceList, windowTitle=self.getTitle())

		self.readDevices(readDevicesCallback)

	def deviceSelectionCallback(self, deviceId):
		def getPathMountData(path):
			mounts = fileReadLines("/proc/mounts", [], source=MODULE_NAME)
			print(f"[KexecSlotManager] getPathMountData DEBUG: path={path}.")
			for mount in mounts:
				data = mount.split()
				if data[MOUNT_DEVICE] == path:
					status = stat(data[MOUNT_MOUNTPOINT])
					return (data[MOUNT_MOUNTPOINT], status, data)
			return None

		if deviceId:
			print(f"[KexecSlotManager] deviceSelectionCallback DEBUG: deviceId={deviceId}.")
			self.kexecSlotManagerDevice = deviceId
			locations = self.kexecSlotManagerLocation.getSelectionList()
			path = self.deviceData[deviceId][0]
			self.mountData = getPathMountData(path)
			if self.mountData:
				mountPoint = self.mountData[0]
				mountStat = self.mountData[1]
				print(f"[KexecSlotManager] deviceSelectionCallback DEBUG: mountData={str(self.mountData)}.")
				if not isdir(mountPoint):
					footnote = _("Directory '%s' does not exist!") % mountPoint
				elif mountStat.st_dev in DEFAULT_INHIBIT_DEVICES:
					footnote = _("Flash directory '%s' not allowed!") % mountPoint
				elif not access(mountPoint, W_OK):
					footnote = _("Directory '%s' not writable!") % mountPoint
				else:
					status = statvfs(mountPoint)
					self.freespace = status.f_bavail * status.f_bsize / 1024 / 1024 / 1024
					footnote = None
			else:
				footnote = _("No valid mount for '%s' found!") % path
			print(f"[KexecSlotManager] deviceSelectionCallback DEBUG: footnote={footnote}")
			if not footnote:
				if (path, path) not in locations:
					locations.append((path, path))
					self.kexecSlotManagerLocation.setSelectionList(default=None, choices=locations)
					self.kexecSlotManagerLocation.value = path
					maxSlots = int(self.freespace / 2)
					maxSlots = 50 if maxSlots > 50 else maxSlots
					self.kexecSlotManagerSlots.updateLimits([(1, maxSlots)])
					self.createSetup()
				self.kexecSlotManagerDevice = deviceId
			self.updateStatus(footnote)

	def readDevices(self, callback=None):
		def readDevicesCallback(output=None, retVal=None, extraArgs=None):
			def getDeviceID(deviceInfo):
				mode = "UUID="
				for token in deviceInfo:
					if token.startswith(mode):
						return token[len(mode):]
				return None

			print(f"[KexecSlotManager] readDevicesCallback DEBUG: retVal={retVal}, output='{output}'.")
			lines = [line for line in output.splitlines() if "UUID=\"" in line and ("/dev/sd" in line or "/dev/cf" in line) and "TYPE=\"ext" in line]
			self.deviceData = {}
			for (name, hdd) in harddiskmanager.HDDList():
				for line in lines:
					data = split(line.strip())
					if data and data[0][:-1].startswith(hdd.dev_path):
						deviceID = getDeviceID(data)
						if deviceID:
							self.deviceData[deviceID] = (data[0][:-1], name)
			self.updateStatus()
			if callback and callable(callback):
				callback()

		self.console.ePopen(["/sbin/blkid", "/sbin/blkid"], callback=readDevicesCallback)

	def updateStatus(self, footnote=None):
		self.green = ACTION_CREATE if self.kexecSlotManagerDevice else ACTION_SELECT
		self["key_green"].setText({
			ACTION_SELECT: _("Select Device"),
			ACTION_CREATE: _("Create Slots")
		}.get(self.green, _("Invalid")))


class GPTSlotManager(Setup):
	def __init__(self, session):
		def getGreenHelpText():
			return {
				ACTION_SELECT: _("Select a device to use for the additional slots"),
				ACTION_CREATE: _("Create the additional slots on the selected device")
			}.get(self.green, _("Help text uninitialized"))

		self.GPTSlotManagerLocation = ConfigSelection(default=None, choices=[(None, _("<Select a device>"))])
		self.GPTSlotManagerSlots = ConfigInteger(default=4, limits=(4, 4))
		self.GPTSlotManagerDevice = None
		Setup.__init__(self, session=session, setup="GPTSlotManager")
		self.setTitle(_("Slot Manager"))
		self["fullUIActions"] = HelpableActionMap(self, ["CancelSaveActions"], {
			"cancel": (self.keyCancel, _("Cancel any changed settings and exit")),
			"close": (self.closeRecursive, _("Cancel any changed settings and exit all menus"))
		}, prio=0, description=_("Common Setup Actions"))  # Override the ConfigList "fullUIActions" action map so that we can control the GREEN button here.
		self["actions"] = HelpableActionMap(self, ["ColorActions"], {
			"green": (self.keyGreen, getGreenHelpText)
		}, prio=-1, description=_("Slot Manager Actions"))
		self.console = Console()
		self.deviceData = {}
		self.green = ACTION_SELECT

	def partitionSizeGB(self, dev):
		try:
			base = dev.replace("/dev/", "")
			path = f"/sys/class/block/{base}/size"
			path = path if exists(path) else f"/sys/block/{base}/size"
			with open(path) as fd:
				blocks = int(fd.read().strip())
				return ceil((blocks * 512) / (1024 * 1024 * 1024))
		except Exception:
			return 0

	def emmcSlotCount(self):
		count = 0
		try:
			for entry in listdir("/dev/disk/by-partlabel"):
				if entry == "dreambox-rootfs" or (entry.startswith("dreambox-rootfs") and entry[len("dreambox-rootfs"):].isdigit()):
					if realpath(join("/dev/disk/by-partlabel", entry)).startswith("/dev/mmcblk0p"):
						count += 1
		except OSError:
			pass
		return count if count > 0 else 4

	def layoutFinished(self):
		Setup.layoutFinished(self)
		self.readDevices()

	def createSetup(self):
		self.list = []
		if self.GPTSlotManagerDevice:
			self.list.append((_("Number of Slots"), self.GPTSlotManagerSlots))
		Setup.createSetup(self, appendItems=self.list)

	def selectionChanged(self):
		Setup.selectionChanged(self)
		self.updateStatus()

	def changedEntry(self):
		Setup.changedEntry(self)
		self.updateStatus()

	def keySelect(self):
		if self.getCurrentItem() == self.GPTSlotManagerLocation:
			self.showDeviceSelection()
		else:
			Setup.keySelect(self)

	def keyGreen(self):
		def restartCallback(answer):
			if answer is True:
				self.session.open(TryQuitMainloop, QUIT_REBOOT)
			else:
				self.close()

		def createSlots():
			if not createStartupFiles():
				return
			update_bootconfig()
			formatDevice()

		def createStartupFiles():
			numSlots = self.GPTSlotManagerSlots.value
			offset = self.emmcSlotCount() + 1
			startupRe = compile(r"^STARTUP_(\d+)$")
			try:
				for startupFile in listdir("/data"):
					match = startupRe.match(startupFile)
					if match and int(match.group(1)) >= offset:
						remove(join("/data", startupFile))
			except OSError as err:
				print(f"[GPTSlotManager] Error {err.errno}: Unable to remove obsolete additional STARTUP files.  ({err.strerror})")
				self.session.open(MessageBox, _("Unable to remove the obsolete additional STARTUP files."), MessageBox.TYPE_ERROR, timeout=10, windowTitle=self.getTitle())
				return False
			for i in range(numSlots):
				content = f"root=/dev/mmcblk1p{i + 2} rootfstype=ext4 kernel=/kernel{i + 2}.img\n"
				path = join("/data", f"STARTUP_{i + offset}")
				if not fileWriteLine(path, content, source=MODULE_NAME):
					self.session.open(MessageBox, _("Unable to create the additional STARTUP files."), MessageBox.TYPE_ERROR, timeout=10, windowTitle=self.getTitle())
					return False
			return True

		def update_bootconfig():
			numSlots = self.GPTSlotManagerSlots.value
			offset = self.emmcSlotCount() + 1
			bootInfo = []
			for i in range(numSlots):
				bootInfo.append(f"[SDcard Slot {i + offset}]")
				bootInfo.append(f"cmd=fatload mmc 0:1 1080000 /kernel{i + 2}.img;bootm;")
				bootInfo.append("arg=${bootargs} logo=osd0,loaded,0x7f800000 vout=1080p50hz,enable hdmimode=1080p50hz fb_width=1280 fb_height=720 panel_type=lcd_4")

			bootConfig = "/data/bootconfig.txt"
			lines = fileReadLines(bootConfig, [], source=MODULE_NAME)
			newlines = []
			skipblock = False
			for line in lines:
				if line.strip().startswith("[SDcard Slot"):
					skipblock = True
				elif skipblock and line.strip().startswith("["):
					skipblock = False

				if not skipblock:
					newlines.append(line)
			lines = newlines

			for i in range(len(lines) - 1, -1, -1):
				if lines[i].strip().startswith("["):
					lines = lines[:i] + bootInfo + lines[i:]
					break

			if numSlots > 4:
				for idx, line in enumerate(lines):
					if line.startswith("fb_pos="):
						lines[idx] = "fb_pos=100,450"
					elif line.startswith("fb_size="):
						lines[idx] = "fb_size=1080,300"
					elif line.startswith("font_size="):
						lines[idx] = "font_size=2"

			recovery_index = None
			for i, line in enumerate(lines):
				if line.strip() == "[   Recovery   ]":
					recovery_index = i
					break
			if recovery_index is not None:
				del lines[recovery_index:recovery_index + 3]
			fileWriteLines(bootConfig, lines, source=MODULE_NAME)

		def formatDevice():
			TARGET = "mmcblk1"
			TARGET_DEVICE = f"/dev/{TARGET}"
			numSlots = self.GPTSlotManagerSlots.value

			if exists(TARGET_DEVICE):
				cmdlist = []
				cmdlist.append(f"for n in {TARGET_DEVICE}* ; do umount -lf $n > /dev/null 2>&1 ; done")
				cmdlist.append(f"/bin/touch /dev/nomount.{TARGET} > /dev/null 2>&1")
				for i in range(1, numSlots + 2):
					cmdlist.append(f"/bin/touch /dev/nomount.{TARGET}p{i} > /dev/null 2>&1")

				cmdlist.append(f"/usr/sbin/sgdisk -z {TARGET_DEVICE}")
				cmdlist.append(f"/usr/sbin/parted --script {TARGET_DEVICE} mklabel gpt")
				cmdlist.append(f"/usr/sbin/partprobe {TARGET_DEVICE}")
				cmdlist.append(f"/usr/sbin/parted --script {TARGET_DEVICE} mkpart DREAMCARD fat16 8192s 100MB")

				for i in range(numSlots):
					start = "100MB" if i == 0 else f"{int(i * 100 // numSlots)}%"
					end = f"{int((i + 1) * 100 // numSlots)}%"
					cmdlist.append(f"/usr/sbin/parted --script {TARGET_DEVICE} mkpart dreambox-rootfs ext4 {start} {end}")

				cmdlist.append(f"/usr/sbin/partprobe {TARGET_DEVICE}")
				cmdlist.append("sleep 2")
				cmdlist.append(f"/usr/sbin/mkfs.fat -F 16 -S 512 -v -n DREAMCARD {TARGET_DEVICE}p1")
				for i in range(2, 2 + numSlots):
					cmdlist.append(f"/sbin/mkfs.ext4 {MKFS_EXT4_FAST_OPTIONS} -F {TARGET_DEVICE}p{i}")
				self.session.openWithCallback(formatDeviceCallback, ConsoleScreen, title=self.getTitle(), cmdlist=cmdlist, closeOnSuccess=True)

		def formatDeviceCallback():
			self.session.openWithCallback(restartCallback, MessageBox, _("Restart necessary, restart GUI now?"), MessageBox.TYPE_YESNO, windowTitle=self.getTitle())

		if self.GPTSlotManagerDevice:
			createSlots()
		else:
			self.showDeviceSelection()

	def showDeviceSelection(self):
		def readDevicesCallback():
			choiceList = [(_("Cancel"), "")]
			for deviceData in self.deviceData.items():
				choiceList.append((f"{deviceData[1]} ({deviceData[0]})", 1))
			self.session.openWithCallback(self.deviceSelectionCallback, MessageBox, text=_("Please select the device or Cancel to cancel the selection."), list=choiceList, windowTitle=self.getTitle())

		self.readDevices(readDevicesCallback)

	def deviceSelectionCallback(self, selection):
		if selection:
			print(f"[GPTSlotManager] deviceSelectionCallback DEBUG: selection={selection}.")
			self.GPTSlotManagerDevice = selection
			locations = self.GPTSlotManagerLocation.getSelectionList()
			path = self.deviceData[selection][0]
			name = self.deviceData[selection][1]
			if (path, path) not in locations:
				locations.append((path, path))
				self.GPTSlotManagerLocation.setSelectionList(default=None, choices=locations)
				self.GPTSlotManagerLocation.value = path
			self.GPTSlotManagerDevice = selection
			self.updateStatus(f"Found SDCARD: {name}")
			devicePath = self.deviceData[selection][0]
			diskSize = self.partitionSizeGB(devicePath)
			print(f"[GPTSlotManager] devicePath={devicePath}, diskSize={diskSize}GB")

			if diskSize > 16:
				maxSlots = int(diskSize // 4)
				print(f"[GPTSlotManager] Setting maxSlots={maxSlots} for {diskSize}GB disk")
				self.GPTSlotManagerSlots.updateLimits([(4, maxSlots)])
			else:
				print(f"[GPTSlotManager] Disk size {diskSize}GB <= 16GB, limiting to 4 slots")
				self.GPTSlotManagerSlots.updateLimits([(4, 4)])
				self.GPTSlotManagerSlots.value = 4
			self.createSetup()

	def readDevices(self, callback=None):
		def readDevicesCallback():
			base = "mmcblk1"
			devbase = f"/dev/{base}"
			sysbase = f"/sys/block/{base}"
			self.deviceData = {}
			if not isdir(sysbase) or not exists(devbase):
				self.updateStatus()
				if callback and callable(callback):
					callback()
				return

			displayname = base
			for (name, hdd) in harddiskmanager.HDDList():
				if hdd.dev_path == devbase:
					displayname = name
					break

			self.deviceData[1] = (devbase, displayname)
			self.updateStatus()
			if callback and callable(callback):
				callback()

		readDevicesCallback()

	def updateStatus(self, footnote=None):
		self.green = ACTION_CREATE if self.GPTSlotManagerDevice else ACTION_SELECT
		self["key_green"].setText({
			ACTION_SELECT: _("Select Device"),
			ACTION_CREATE: _("Create Slots")
		}.get(self.green, _("Invalid")))


class ChkrootInit(Screen):
	skin = """
	<screen name="ChkrootInit" title="Chkroot MultiBoot Manager" position="center,center" size="900,600" resolution="1280,720">
		<widget name="description" position="0,0" size="e,e-50" font="Regular;20" />
		<widget source="key_red" render="Label" position="0,e-40" size="180,40" backgroundColor="key_red" conditional="key_red" font="Regular;20" foregroundColor="key_text" halign="center" valign="center">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="key_green" render="Label" position="190,e-40" size="180,40" backgroundColor="key_green" conditional="key_green" font="Regular;20" foregroundColor="key_text" halign="center" valign="center">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="key_help" render="Label" position="e-80,e-40" size="80,40" backgroundColor="key_back" conditional="key_help" font="Regular;20" foregroundColor="key_text" halign="center" valign="center">
			<convert type="ConditionalShowHide" />
		</widget>
	</screen>"""

	def __init__(self, session, *args):
		Screen.__init__(self, session, enableHelp=True)
		self.skinName = "KexecInit"
		self.setTitle(_("Chkroot MultiBoot Manager"))
		self["key_red"] = StaticText()
		self["key_green"] = StaticText()
		self["description"] = Label()
		self["actions"] = HelpableActionMap(self, ["OkCancelActions", "ColorActions"], {
			"ok": (self.close, _("Close the Chkroot MultiBoot Manager")),
			"cancel": (self.close, _("Close the Chkroot MultiBoot Manager")),
			"red": (self.disableChkroot, _("Disable the MultiBoot option")),
			"green": (self.ubimbInit if BoxInfo.getItem("hasUBIMB") else self.rootInit, _("Start the Chkroot initialization"))
		}, prio=-1, description=_("Chkroot Manager Actions"))
		self["key_red"].setText(_("Disable Chkroot"))
		self["key_green"].setText(_("Initialize"))
		self.descriptionSuffix = _("The %s %s will reboot within 1 seconds.") % getBoxDisplayName()
		self["description"].setText("%s\n\n%s" % (_("Press GREEN to enable MultiBoot!"), self.descriptionSuffix))

	def ubimbInit(self):
		self.session.open(UBISlotManager)

	def rootInit(self):
		def rootInitCallback(*args, **kwargs):
			self.session.open(TryQuitMainloop, QUIT_REBOOT)

		self["description"].setText("%s\n\n%s" % (_("Chkroot MultiBoot Initialization in progress!"), self.descriptionSuffix))
		device = "/dev/block/by-name/others"
		mountpoint = "/boot"
		mtdRootFs = BoxInfo.getItem("mtdrootfs")
		mtdKernel = BoxInfo.getItem("mtdkernel")
		machinebuild = BoxInfo.getItem("machinebuild")
		if machinebuild in ("dm900", "dm920", "dm820", "dm7080"):
			with open("/sys/block/mmcblk0/mmcblk0p1/size") as fd:
				sectors = int(fd.read().strip())
			if machinebuild in ("dm900", "dm920"):
				rootMap = [
					("mmcblk0p2", "linuxrootfs1"),
					("mmcblk0p2", "linuxrootfs1")
				]
				rootMap.append(("mmcblk0p3" if sectors < 2097152 else "mmcblk0p2", "linuxrootfs2"))
				rootMap.extend([
					("mmcblk0p3", "linuxrootfs3"),
					("mmcblk0p3", "linuxrootfs4"),
					("mmcblk0p3", "linuxrootfs5"),
					("mmcblk0p3", "linuxrootfs6")
				])
			else:
				rootMap = [
					("mmcblk0p1", "linuxrootfs1"),
					("mmcblk0p1", "linuxrootfs1")
				]
				rootMap.append(("mmcblk0p2" if sectors < 2097152 else "mmcblk0p1", "linuxrootfs2"))
				rootMap.extend([
					("mmcblk0p2", "linuxrootfs3"),
					("mmcblk0p2", "linuxrootfs4")
				])
		else:
			rootMap = [
				(mtdRootFs, "linuxrootfs1"),
				(mtdRootFs, "linuxrootfs1"),
				(mtdRootFs, "linuxrootfs2"),
				(mtdRootFs, "linuxrootfs3"),
				(mtdRootFs, "linuxrootfs4")
			]

		cmdList = [
			f"mkfs.vfat -F 32 -n CHKROOT {device}",
			f"mkdir -p {mountpoint}",
			f"mount {device} {mountpoint}",
		]

		for idx, (rootdev, subdir) in enumerate(rootMap):
			suffix = "" if idx == 0 else f"_{idx}"
			cmdList.append(f"echo 'kernel=/dev/{mtdKernel} root=/dev/{rootdev} rootsubdir={subdir}' > {mountpoint}/STARTUP{suffix}")

		cmdList.append(f"umount {mountpoint}")
		Console().eBatch(cmdList, rootInitCallback, debug=True)

	def disableChkroot(self):
		def disableChkrootCallback(answer):
			if answer:
				fileWriteLine("/etc/.disableChkroot", "disabled\n", source=MODULE_NAME)
				self.close()

		self.session.openWithCallback(disableChkrootCallback, MessageBox, _("Permanently disable the MultiBoot option?"), simple=True)


class ChkrootSlotManager(Setup):
	def __init__(self, session):
		def getGreenHelpText():
			return {
				ACTION_SELECT: _("Select a device to create multiboot slots"),
				ACTION_CREATE: _("Create slots for the selected device")
			}.get(self.green, _("Help text uninitialized"))

		self.ChkrootSlotManagerLocation = ConfigSelection(default=None, choices=[(None, _("<Select a device>"))])
		self.ChkrootSlotManagerSlots = ConfigInteger(default=10, limits=(1, 20))
		self.ChkrootSlotManagerDevice = None
		Setup.__init__(self, session=session, setup="ChkrootSlotManager")
		self.setTitle(_("Slot Manager"))
		self["fullUIActions"] = HelpableActionMap(self, ["CancelSaveActions"], {
			"cancel": (self.keyCancel, _("Cancel any changed settings and exit")),
			"close": (self.closeRecursive, _("Cancel any changed settings and exit all menus"))
		}, prio=0, description=_("Common Setup Actions"))  # Override the ConfigList "fullUIActions" action map so that we can control the GREEN button here.
		self["actions"] = HelpableActionMap(self, ["ColorActions"], {
			"green": (self.keyGreen, getGreenHelpText)
		}, prio=-1, description=_("Slot Manager Actions"))
		self.console = Console()
		self.deviceData = {}
		self.green = ACTION_SELECT

	def layoutFinished(self):
		Setup.layoutFinished(self)
		self.readDevices()

	def selectionChanged(self):
		Setup.selectionChanged(self)
		self.updateStatus()

	def changedEntry(self):
		Setup.changedEntry(self)
		self.updateStatus()

	def keySelect(self):
		if self.getCurrentItem() == self.ChkrootSlotManagerLocation:
			self.showDeviceSelection()
		else:
			Setup.keySelect(self)

	def keyGreen(self):
		if self.ChkrootSlotManagerDevice:
			self.createSlots()
		else:
			self.showDeviceSelection()

	def createSlots(self):
		if not self.ChkrootSlotManagerDevice:
			self.showDeviceSelection()
			return

		TARGET = self.deviceData[self.ChkrootSlotManagerDevice][0].split("/")[-1]
		TARGET_DEVICE = f"/dev/{TARGET}"
		PART_SUFFIX = "p" if "mmcblk" in TARGET else ""
		PART = lambda n: f"{TARGET_DEVICE}{PART_SUFFIX}{n}"  # noqa E731
		MOUNTPOINT = "/tmp/boot"
		symlinkPath = "/dev/block/by-name/others"
		if exists(symlinkPath):
			realDevice = realpath(symlinkPath)
			if realDevice == "/dev/mmcblk0boot1":
				try:
					with open("/sys/block/mmcblk0boot1/force_ro", "w") as fn:
						fn.write("0")
				except Exception:
					pass

			if exists(TARGET_DEVICE):
				cmdlist = []
				cmdlist.append(f"for n in {TARGET_DEVICE}* ; do umount -lf $n > /dev/null 2>&1 ; done")
				cmdlist.append(f"/usr/sbin/sgdisk -z {TARGET_DEVICE}")
				cmdlist.append(f"/bin/touch /dev/nomount.{TARGET} > /dev/null 2>&1")
				cmdlist.append(f"/usr/sbin/parted --script {TARGET_DEVICE} mklabel gpt")
				cmdlist.append(f"/usr/sbin/partprobe {TARGET_DEVICE}")
				cmdlist.append(f"/usr/sbin/parted --script {TARGET_DEVICE} unit MiB mkpart rootfs ext4 1MB -- -{MULTIBOOT_SWAP_SIZE_MIB}MiB")
				cmdlist.append(f"/usr/sbin/parted --script {TARGET_DEVICE} unit MiB mkpart swap linux-swap -- -{MULTIBOOT_SWAP_SIZE_MIB}MiB 100%")
				cmdlist.append(f"/usr/sbin/partprobe {TARGET_DEVICE}")
				cmdlist.append(f"/sbin/mkfs.ext4 -O ^64bit,^extent,^flex_bg,^huge_file,^dir_nlink,^extra_isize,^metadata_csum {MKFS_EXT4_FAST_OPTIONS} -F -L rootfs {PART(1)}")
				cmdlist.append(f"/sbin/mkswap -L swap {PART(2)}")
				cmdlist.append(f"/bin/mkdir -p {MOUNTPOINT}")
				cmdlist.append(f"/bin/umount {MOUNTPOINT} > /dev/null 2>&1")
				cmdlist.append(f"/bin/mount {realDevice} {MOUNTPOINT}")
				cmdlist.append(f"find {MOUNTPOINT} -maxdepth 1 -type f -name 'STARTUP_*' -exec grep -q 'extra=true' {{}} \\; -exec rm -f {{}} \\;")
				self.session.openWithCallback(self.formatDeviceCallback, ConsoleScreen, title=self.getTitle(), cmdlist=cmdlist)
		else:
			self.session.open(MessageBox, _("Startup device not found!"), MessageBox.TYPE_ERROR, timeout=5)
			self.close()

	def formatDeviceCallback(self):
		def closeStartUpCallback(answer):
			if answer:
				self.session.open(TryQuitMainloop, QUIT_RESTART)
		MOUNTPOINT = "/tmp/boot"
		mtdRootFs = BoxInfo.getItem("mtdrootfs")  # noqa F841
		mtdKernel = BoxInfo.getItem("mtdkernel")
		device = self.ChkrootSlotManagerDevice
		PART_SUFFIX = "p" if "mmcblk" in device else ""
		uuidRootFS = fileReadLine(f"/dev/uuid/{device}{PART_SUFFIX}1", default=None, source=MODULE_NAME)
		diskSize = self.partitionSizeGB(f"/dev/{device}")

		existingNumbers = []
		startupRe = compile(r"^STARTUP_(\d+)$")

		for fname in listdir(MOUNTPOINT):
			match = startupRe.match(fname)
			if match:
				existingNumbers.append(int(match.group(1)))

		startIndex = max(existingNumbers) + 1 if existingNumbers else 1
		maxSlots = min(diskSize, self.ChkrootSlotManagerSlots.value)
		remainingSlots = maxSlots - len(existingNumbers)
		endIndex = startIndex + remainingSlots - 1
		created = 0
		for i in range(startIndex, endIndex + 1):
			startupContent = f"kernel=/dev/{mtdKernel} root=UUID={uuidRootFS} rootsubdir=linuxrootfs{i} rootfstype=ext4 extra=true\n"
			with open(f"{MOUNTPOINT}/STARTUP_{i}", "w") as fd:
				fd.write(startupContent)
			created += 1
		Console().ePopen(["/bin/sync"])
		Console().ePopen(["/bin/umount", "/bin/umount", f"{MOUNTPOINT}"])
		self.session.openWithCallback(closeStartUpCallback, MessageBox, _("Slots have been extended by %d..\n") % created, type=MessageBox.TYPE_INFO, close_on_any_key=True, timeout=10)

	def showDeviceSelection(self):
		def readDevicesCallback():
			choiceList = [(_("Cancel"), None)]
			for device_id, (path, name) in self.deviceData.items():
				choiceList.append((f"{name} ({path})", device_id))
			self.session.openWithCallback(self.deviceSelectionCallback, MessageBox, text=_("Select target device for slot creation"), list=choiceList, windowTitle=self.getTitle())
		self.readDevices(readDevicesCallback)

	def deviceSelectionCallback(self, selection):
		if not selection:
			return

		print(f"[ChkrootSlotManager] deviceSelectionCallback: selected device ID = {selection}")
		self.ChkrootSlotManagerDevice = selection
		locations = self.ChkrootSlotManagerLocation.getSelectionList()
		path = self.deviceData[selection][0]
		name = self.deviceData[selection][1]  # noqa F841
		if (path, path) not in locations:
			locations.append((path, path))
			self.ChkrootSlotManagerLocation.setSelectionList(default=None, choices=locations)
			self.ChkrootSlotManagerLocation.value = path
			self.createSetup()
		self.updateStatus(f"Selected device: {self.deviceData[selection][1]}")

	def partitionSizeGB(self, dev):
		try:
			base = dev.replace("/dev/", "")
			path = f"/sys/class/block/{base}/size"
			path = path if exists(path) else f"/sys/block/{base}/size"
			with open(path) as fd:
				blocks = int(fd.read().strip())
				return ceil((blocks * 512) / (1024 * 1024 * 1024))
		except Exception:
			return 0

	def readDevices(self, callback=None):
		def readDevicesCallback(output=None, retVal=None, extraArgs=None):
			def getDeviceID(deviceInfo):
				mode = "UUID="
				for token in deviceInfo:
					if token.startswith(mode):
						return token[len(mode):]
				return None

			print(f"[ChkrootSlotManager] readDevicesCallback DEBUG: retVal={retVal}, output='{output}'.")
			mtdblack = BoxInfo.getItem("mtdblack") or ""
			blacklist = mtdblack.strip().split()

			self.deviceData = {}

			for (name, hdd) in harddiskmanager.HDDList():
				if any(hdd.dev_path.startswith(black) for black in blacklist) or hdd.dev_path.startswith("/dev/romblock"):
					continue

				deviceID = hdd.dev_path.split("/")[-1]
				self.deviceData[deviceID] = (hdd.dev_path, name)

			self.updateStatus()
			if callback and callable(callback):
				callback()

		self.console.ePopen(["/sbin/blkid", "/sbin/blkid"], callback=readDevicesCallback)

	def updateStatus(self, footnote=None):
		self.green = ACTION_CREATE if self.ChkrootSlotManagerDevice else ACTION_SELECT
		self["key_green"].setText({
			ACTION_SELECT: _("Select Device"),
			ACTION_CREATE: _("Create Slots")
		}.get(self.green, _("Invalid")))


class NativeSlotManager(Setup):
	def __init__(self, session):
		def getGreenHelpText():
			return {
				ACTION_SELECT: _("Select a device to create multiboot slots"),
				ACTION_CREATE: _("Create slots for the selected device")
			}.get(self.green, _("Help text uninitialized"))

		self.NativeSlotManagerLocation = ConfigSelection(default=None, choices=[(None, _("<Select a device>"))])
		self.NativeSlotManagerSlots = ConfigInteger(default=4, limits=(1, 50))
		self.NativeSlotManagerDevice = None
		self.slotPlan = []
		self.startupFilesToRemove = []
		self.rootDevice = None
		Setup.__init__(self, session=session, setup="NativeSlotManager")
		self.setTitle(_("Slot Manager"))
		self["fullUIActions"] = HelpableActionMap(self, ["CancelSaveActions"], {
			"cancel": (self.keyCancel, _("Cancel any changed settings and exit")),
			"close": (self.closeRecursive, _("Cancel any changed settings and exit all menus"))
		}, prio=0, description=_("Common Setup Actions"))
		self["actions"] = HelpableActionMap(self, ["ColorActions"], {
			"green": (self.keyGreen, getGreenHelpText)
		}, prio=-1, description=_("Slot Manager Actions"))
		self.console = Console()
		self.deviceData = {}
		self.green = ACTION_SELECT

	def layoutFinished(self):
		Setup.layoutFinished(self)
		self.readDevices()

	def selectionChanged(self):
		Setup.selectionChanged(self)
		self.updateStatus()

	def changedEntry(self):
		Setup.changedEntry(self)
		self.updateStatus()

	def keySelect(self):
		if self.getCurrentItem() == self.NativeSlotManagerLocation:
			self.showDeviceSelection()
		else:
			Setup.keySelect(self)

	def keyGreen(self):
		if self.NativeSlotManagerDevice:
			self.createSlots()
		else:
			self.showDeviceSelection()

	def createSlots(self):
		if not self.NativeSlotManagerDevice:
			self.showDeviceSelection()
			return
		error = self.prepareSlotPlan()
		if error:
			self.session.open(MessageBox, error, MessageBox.TYPE_ERROR, timeout=10, windowTitle=self.getTitle())
			return
		path, name = self.deviceData[self.NativeSlotManagerDevice]
		message = "%s\n\n%s\n\n%s" % (name, path, _("All data on the selected device will be erased. Create one shared data partition with %d additional MultiBoot slots, a 512 MiB swap partition and the internal slot 1 kernel?") % len(self.slotPlan))
		if self.startupFilesToRemove:
			message = "%s\n\n%s" % (message, _("%d obsolete manufacturer STARTUP files will be replaced or removed.") % len(self.startupFilesToRemove))
		self.session.openWithCallback(self.createSlotsCallback, MessageBox, message, MessageBox.TYPE_YESNO, default=False, windowTitle=self.getTitle())

	def createSlotsCallback(self, answer):
		if answer:
			self.formatDevice()

	def isSlotTargetValid(self, slotData):
		device = slotData.get("device")
		if not device or not exists(device):
			return False
		if slotData.get("rootsubdir"):
			return True
		devicePath = realpath(device)
		for mount in fileReadLines("/proc/mounts", default=[], source=MODULE_NAME):
			data = mount.split()
			if len(data) > MOUNT_MOUNTPOINT and data[MOUNT_MOUNTPOINT] == "/" and realpath(data[MOUNT_DEVICE]) == devicePath:
				return True
		inspectDir = mkdtemp(prefix="NativeSlotTarget_")
		try:
			Console().ePopen(["/bin/mount", "/bin/mount", "-o", "ro", device, inspectDir])
			return ismount(inspectDir)
		finally:
			if ismount(inspectDir):
				Console().ePopen(["/bin/umount", "/bin/umount", inspectDir])
			if not ismount(inspectDir):
				rmdir(inspectDir)

	def prepareSlotPlan(self):
		bootSlots = MultiBoot.getBootSlots()
		if isAdditionalSlot(MultiBoot.getCurrentSlotCode()):
			return _("Additional slots cannot be changed while the receiver is running from one of them.")
		startupDevice = MultiBoot.getBootDevice()
		if not startupDevice or not exists(startupDevice):
			return _("The manufacturer STARTUP device was not found.")

		self.slotPlan = []
		self.startupFilesToRemove = []
		validSlotNumbers = {int(slotCode) for slotCode, slotData in bootSlots.items() if slotCode.isdecimal() and self.isSlotTargetValid(slotData)}
		additionalSlotNumbers = {int(slotCode) for slotCode in bootSlots if slotCode.isdecimal() and isAdditionalSlot(slotCode)}
		manufacturerSlotNumbers = validSlotNumbers - additionalSlotNumbers
		if not manufacturerSlotNumbers:
			return _("No valid manufacturer MultiBoot slots were found.")

		inspectDir = mkdtemp(prefix="NativeSlotManager_")
		rawStartupFiles = {}
		try:
			Console().ePopen(["/bin/mount", "/bin/mount", startupDevice, inspectDir])
			if not ismount(inspectDir):
				return _("The manufacturer STARTUP device cannot be mounted for inspection.")
			startupRe = compile(r"^STARTUP_(?:LINUX_)?(\d+)(?:_|$)")
			for startupFile in listdir(inspectDir):
				match = startupRe.match(startupFile)
				if match:
					slotNumber = int(match.group(1))
					rawStartupFiles.setdefault(slotNumber, []).append(startupFile)
		finally:
			if ismount(inspectDir):
				Console().ePopen(["/bin/umount", "/bin/umount", inspectDir])
			if not ismount(inspectDir):
				rmdir(inspectDir)

		lastManufacturerSlot = max(manufacturerSlotNumbers)
		protectedSlotNumbers = manufacturerSlotNumbers | {slotNumber for slotNumber in rawStartupFiles if slotNumber <= lastManufacturerSlot}
		obsoleteSlotNumbers = sorted(set(rawStartupFiles) - protectedSlotNumbers)
		self.startupFilesToRemove = sorted(startupFile for slotNumber in obsoleteSlotNumbers for startupFile in rawStartupFiles[slotNumber])

		if 1 not in manufacturerSlotNumbers or "1" not in bootSlots:
			return _("Manufacturer slot 1 was not found and cannot be used as the shared kernel template.")
		sourceSlot = "1"
		slotData = bootSlots[sourceSlot]
		sourceRootSubdir = slotData.get("rootsubdir") or "linuxrootfs1"
		startupFiles = slotData.get("startupfile", {})
		cmdLines = slotData.get("cmdline", {})
		if not isinstance(startupFiles, dict) or not isinstance(cmdLines, dict):
			return _("Manufacturer slot 1 does not provide suitable STARTUP files.")
		modes = []
		for bootCode in slotData.get("bootCodes", [""]):
			startupFile = startupFiles.get(bootCode)
			cmdLine = cmdLines.get(bootCode)
			if startupFile and cmdLine and "root=" in cmdLine and "kernel=" in cmdLine:
				modes.append((bootCode, startupFile, cmdLine))
		if not modes:
			return _("Manufacturer slot 1 has no usable STARTUP command with a kernel device.")

		newSlotNumbers = obsoleteSlotNumbers[:self.NativeSlotManagerSlots.value]
		nextSlot = max(lastManufacturerSlot, max(rawStartupFiles, default=0)) + 1
		while len(newSlotNumbers) < self.NativeSlotManagerSlots.value:
			if nextSlot not in protectedSlotNumbers:
				newSlotNumbers.append(nextSlot)
			nextSlot += 1
		newSlotNumbers.sort()
		for newSlot in newSlotNumbers:
			rootSubdir = self.getRootSubdir(sourceRootSubdir, newSlot)
			if not rootSubdir:
				self.slotPlan = []
				return _("The root subdirectory in the manufacturer STARTUP file cannot be safely extended.")
			startupData = []
			for bootCode, startupFile, cmdLine in modes:
				newStartupFile = self.getStartupName(startupFile, sourceSlot, str(newSlot))
				if not newStartupFile:
					self.slotPlan = []
					return _("The manufacturer STARTUP filename '%s' cannot be safely extended.") % startupFile
				startupData.append((bootCode, newStartupFile, cmdLine))
			self.slotPlan.append((str(newSlot), rootSubdir, startupData))
		return None

	def getRootSubdir(self, rootSubdir, newSlot):
		match = compile(r"^(.*?)(\d+)$").match(rootSubdir)
		if not match:
			return None
		rootSubdir = f"{match.group(1)}{newSlot}"
		return rootSubdir if not rootSubdir.startswith("/") and ".." not in rootSubdir and fullmatch(r"[A-Za-z0-9._/-]+", rootSubdir) else None

	def getStartupName(self, startupFile, sourceSlot, newSlot):
		parts = startupFile.split("_")
		if len(parts) > 2 and parts[0] == "STARTUP" and parts[1] == "LINUX" and parts[2] == sourceSlot:
			parts[2] = newSlot
		elif len(parts) > 1 and parts[0] == "STARTUP" and parts[1] == sourceSlot:
			parts[1] = newSlot
		else:
			return None
		return "_".join(parts)

	def updateStartupContent(self, cmdLine, rootSubdir, rootDevice):
		content = cmdLine
		# Legacy manufacturer subdirboot initramfs images mount root directly and cannot resolve UUID= targets.
		content = sub(r"(?<![A-Za-z0-9_])root=[^\s'\"]+", f"root={rootDevice}", content, count=1)
		if not compile(r"(?<![A-Za-z0-9_])rootwait(?:=[^\s'\"]+)?(?=$|[\s'\"])").search(content):
			content = sub(r"((?<![A-Za-z0-9_])root=[^\s'\"]+)", r"\1 rootwait", content, count=1)
		if compile(r"(?<![A-Za-z0-9_])rootsubdir=[^\s'\"]+").search(content):
			content = sub(r"(?<![A-Za-z0-9_])rootsubdir=[^\s'\"]+", f"rootsubdir={rootSubdir}", content, count=1)
		else:
			content = sub(r"((?<![A-Za-z0-9_])root=[^\s'\"]+)", rf"\1 rootsubdir={rootSubdir}", content, count=1)
		content = sub(r"(?<![A-Za-z0-9_])userdataroot=[^\s'\"]+", f"userdataroot={rootDevice}", content, count=1)
		if "extra=true" not in content:
			content = sub(r"((?<![A-Za-z0-9_])rootsubdir=[^\s'\"]+)", r"\1 extra=true", content, count=1)
		return content

	def partitionPath(self, device, partition):
		return f"{device}{'p' if device[-1].isdigit() else ''}{partition}"

	def formatDevice(self):
		targetDevice = self.diskPath(self.deviceData[self.NativeSlotManagerDevice][0])
		target = targetDevice.rsplit("/", 1)[-1]
		if not fullmatch(r"(?:sd[a-z]+|mmcblk\d+)", target):
			self.session.open(MessageBox, _("The selected device is not a supported removable block device."), MessageBox.TYPE_ERROR, timeout=10, windowTitle=self.getTitle())
			return
		if not self.slotPlan:
			self.session.open(MessageBox, _("No additional slots have been planned."), MessageBox.TYPE_ERROR, timeout=10, windowTitle=self.getTitle())
			return

		mountPoint = "/tmp/NativeSlotManagerBoot"
		rootMountPoint = "/tmp/NativeSlotManagerRoot"
		startupDevice = MultiBoot.getBootDevice()
		if not startupDevice or not exists(startupDevice):
			self.session.open(MessageBox, _("Startup device not found!"), MessageBox.TYPE_ERROR, timeout=5)
			self.close()
			return

		cmdlist = []
		cmdlist.append(f"for n in {targetDevice}* ; do umount -lf $n > /dev/null 2>&1 ; done")
		cmdlist.append(f"/usr/sbin/sgdisk -z {targetDevice}")
		cmdlist.append(f"/bin/touch /dev/nomount.{target}")
		cmdlist.append(f"/usr/sbin/parted --script {targetDevice} mklabel gpt")
		cmdlist.append(f"/usr/sbin/parted --script {targetDevice} unit MiB mkpart userdata ext4 1MiB -- -{MULTIBOOT_SWAP_SIZE_MIB}MiB")
		cmdlist.append(f"/usr/sbin/parted --script {targetDevice} unit MiB mkpart swap linux-swap -- -{MULTIBOOT_SWAP_SIZE_MIB}MiB 100%")
		cmdlist.append(f"/usr/sbin/partprobe {targetDevice}")
		rootDevice = self.partitionPath(targetDevice, 1)
		swapDevice = self.partitionPath(targetDevice, 2)
		cmdlist.append(f"i=0; while {{ [ ! -b {rootDevice} ] || [ ! -b {swapDevice} ]; }} && [ $i -lt 10 ]; do /sbin/mdev -s > /dev/null 2>&1 || /bin/busybox mdev -s > /dev/null 2>&1 || true; /bin/sleep 1; i=$((i + 1)); done; [ -b {rootDevice} ] && [ -b {swapDevice} ]")
		cmdlist.append(f"/bin/touch /dev/nomount.{rootDevice.rsplit('/', 1)[-1]}")
		cmdlist.append(f"/bin/touch /dev/nomount.{swapDevice.rsplit('/', 1)[-1]}")
		self.rootDevice = rootDevice
		cmdlist.append(f"/sbin/mkfs.ext4 -O ^64bit,^extent,^flex_bg,^huge_file,^dir_nlink,^extra_isize,^metadata_csum {MKFS_EXT4_FAST_OPTIONS} -F -L rootfs {rootDevice}")
		cmdlist.append(f"/sbin/mkswap -L swap {swapDevice}")
		cmdlist.append(f"/bin/mkdir -p {mountPoint} {rootMountPoint}")
		cmdlist.append(f"/bin/umount {mountPoint} > /dev/null 2>&1")
		cmdlist.append(f"/bin/umount {rootMountPoint} > /dev/null 2>&1")
		cmdlist.append(f"/bin/mount {rootDevice} {rootMountPoint}")
		for _slotCode, rootSubdir, _startupData in self.slotPlan:
			cmdlist.append(f"/bin/mkdir -p {rootMountPoint}/{rootSubdir}")
		cmdlist.append(f"/bin/umount {rootMountPoint}")
		cmdlist.append(f"/bin/mount {realpath(startupDevice)} {mountPoint}")
		self.session.openWithCallback(self.formatDeviceCallback, ConsoleScreen, title=self.getTitle(), cmdlist=cmdlist)

	def formatDeviceCallback(self):
		def closeStartupCallback(answer):
			if answer:
				self.session.open(TryQuitMainloop, QUIT_RESTART)

		mountPoint = "/tmp/NativeSlotManagerBoot"
		created = 0
		failed = False
		for startupFile in self.startupFilesToRemove:
			path = join(mountPoint, startupFile)
			if exists(path):
				try:
					remove(path)
				except OSError as err:
					print(f"[NativeSlotManager] Error {err.errno}: Unable to remove obsolete STARTUP file '{path}'.  ({err.strerror})")
					failed = True
					break
		for _slotCode, rootSubdir, startupData in self.slotPlan:
			if failed:
				break
			for _bootCode, startupFile, cmdLine in startupData:
				content = self.updateStartupContent(cmdLine, rootSubdir, self.rootDevice)
				if not fileWriteLine(join(mountPoint, startupFile), content, source=MODULE_NAME):
					failed = True
					break
			if failed:
				break
			created += 1
		Console().ePopen(["/bin/sync"])
		Console().ePopen(["/bin/umount", "/bin/umount", mountPoint])
		if failed:
			self.session.open(MessageBox, _("Unable to create the new manufacturer STARTUP files."), MessageBox.TYPE_ERROR, timeout=10, windowTitle=self.getTitle())
			return
		self.session.openWithCallback(closeStartupCallback, MessageBox, _("%d additional slots have been created.\n") % created, type=MessageBox.TYPE_INFO, close_on_any_key=True, timeout=10)

	def showDeviceSelection(self):
		def readDevicesCallback():
			choiceList = [(_("Cancel"), None)]
			for deviceID, (path, name) in self.deviceData.items():
				choiceList.append((f"{name} ({path})", deviceID))
			self.session.openWithCallback(self.deviceSelectionCallback, MessageBox, text=_("Select target device for slot creation"), list=choiceList, windowTitle=self.getTitle())
		self.readDevices(readDevicesCallback)

	def deviceSelectionCallback(self, selection):
		if not selection:
			return
		print(f"[NativeSlotManager] Selected device ID '{selection}'.")
		self.NativeSlotManagerDevice = selection
		locations = self.NativeSlotManagerLocation.getSelectionList()
		path, name = self.deviceData[selection]
		if (path, path) not in locations:
			locations.append((path, path))
			self.NativeSlotManagerLocation.setSelectionList(default=None, choices=locations)
		self.NativeSlotManagerLocation.value = path

		deviceBytes = self.deviceSizeBytes(path)
		reservedBytes = (MULTIBOOT_SWAP_SIZE_MIB + 1) * 1024 * 1024
		bytesPerSlot = 2 * 1024 * 1024 * 1024
		maxSlots = min(50, max(0, int((deviceBytes - reservedBytes) // bytesPerSlot)))
		if maxSlots < 1:
			self.NativeSlotManagerDevice = None
			self.NativeSlotManagerLocation.value = None
			self.createSetup()
			self.updateStatus(_("The selected device is too small. At least 2561 MiB is required."))
			return
		self.NativeSlotManagerSlots.updateLimits([(1, maxSlots)])
		if self.NativeSlotManagerSlots.value > maxSlots:
			self.NativeSlotManagerSlots.value = maxSlots
		self.createSetup()
		self.updateStatus(_("Selected device: %s") % name)

	def deviceSizeBytes(self, device):
		if not device:
			return 0
		try:
			base = realpath(device).rsplit("/", 1)[-1] if exists(device) else device.rsplit("/", 1)[-1]
			path = f"/sys/class/block/{base}/size"
			path = path if exists(path) else f"/sys/block/{base}/size"
			with open(path) as fd:
				return int(fd.read().strip()) * 512
		except (OSError, ValueError):
			return 0

	def diskPath(self, device):
		return getDiskDevice(device)

	def getProtectedDevices(self):
		devices = {self.diskPath(MultiBoot.getBootDevice())}
		for slotCode, slotData in MultiBoot.getBootSlots().items():
			if not isAdditionalSlot(slotCode):
				devices.add(self.diskPath(slotData.get("device")))
				devices.add(self.diskPath(slotData.get("kernel")))
		for mount in fileReadLines("/proc/mounts", [], source=MODULE_NAME):
			data = mount.split()
			if len(data) > MOUNT_MOUNTPOINT and data[MOUNT_MOUNTPOINT] == "/":
				devices.add(self.diskPath(data[MOUNT_DEVICE]))
		return {device for device in devices if device}

	def readDevices(self, callback=None):
		def readDevicesCallback(output=None, retVal=None, extraArgs=None):
			print(f"[NativeSlotManager] readDevicesCallback DEBUG: retVal={retVal}, output='{output}'.")
			mtdblack = BoxInfo.getItem("mtdblack") or ""
			blacklist = {self.diskPath(device if device.startswith("/dev/") else f"/dev/{device}") for device in mtdblack.strip().split()}
			protectedDevices = self.getProtectedDevices()
			self.deviceData = {}
			for name, hdd in harddiskmanager.HDDList():
				diskPath = self.diskPath(hdd.dev_path)
				if not diskPath or diskPath in blacklist or diskPath in protectedDevices or hdd.dev_path.startswith("/dev/romblock"):
					continue
				deviceID = diskPath.rsplit("/", 1)[-1]
				self.deviceData[deviceID] = (diskPath, name)
			self.updateStatus()
			if callback and callable(callback):
				callback()
		self.console.ePopen(["/sbin/blkid", "/sbin/blkid"], callback=readDevicesCallback)

	def updateStatus(self, footnote=None):
		self.green = ACTION_CREATE if self.NativeSlotManagerDevice else ACTION_SELECT
		self["key_green"].setText({
			ACTION_SELECT: _("Select Device"),
			ACTION_CREATE: _("Create Slots")
		}.get(self.green, _("Invalid")))

class UBISlotManager(Setup):
	def __init__(self, session):
		def getGreenHelpText():
			return {
				ACTION_SELECT: _("Select a device to create multiboot slots"),
				ACTION_CREATE: _("Create slots for the selected device")
			}.get(self.green, _("Help text uninitialized"))

		self.UBISlotManagerLocation = ConfigSelection(default=None, choices=[(None, _("<Select a device>"))])
		self.UBISlotManagerSlots = ConfigInteger(default=10, limits=(1, 20))
		self.UBISlotManagerDevice = None
		Setup.__init__(self, session=session, setup="UBISlotManager")
		self.setTitle(_("Slot Manager"))
		self["fullUIActions"] = HelpableActionMap(self, ["CancelSaveActions"], {
			"cancel": (self.keyCancel, _("Cancel any changed settings and exit")),
			"close": (self.closeRecursive, _("Cancel any changed settings and exit all menus"))
		}, prio=0, description=_("Common Setup Actions"))  # Override the ConfigList "fullUIActions" action map so that we can control the GREEN button here.
		self["actions"] = HelpableActionMap(self, ["ColorActions"], {
			"green": (self.keyGreen, getGreenHelpText)
		}, prio=-1, description=_("Slot Manager Actions"))
		self.console = Console()
		self.deviceData = {}
		self.green = ACTION_SELECT

	def layoutFinished(self):
		Setup.layoutFinished(self)
		self.readDevices()

	def selectionChanged(self):
		Setup.selectionChanged(self)
		self.updateStatus()

	def changedEntry(self):
		Setup.changedEntry(self)
		self.updateStatus()

	def keySelect(self):
		if self.getCurrentItem() == self.UBISlotManagerLocation:
			self.showDeviceSelection()
		else:
			Setup.keySelect(self)

	def keyGreen(self):
		if self.UBISlotManagerDevice:
			self.createSlots()
		else:
			self.showDeviceSelection()

	def createSlots(self):
		if not self.UBISlotManagerDevice:
			self.showDeviceSelection()
			return

		TARGET = self.deviceData[self.UBISlotManagerDevice][0].split("/")[-1]
		TARGET_DEVICE = f"/dev/{TARGET}"
		PART_SUFFIX = "p" if "mmcblk" in TARGET else ""
		PART = lambda n: f"{TARGET_DEVICE}{PART_SUFFIX}{n}"  # noqa E731
		MOUNTPOINT = "/tmp/boot"

		if exists(TARGET_DEVICE):
			cmdlist = []
			cmdlist.append(f"for n in {TARGET_DEVICE}* ; do umount -lf $n > /dev/null 2>&1 ; done")
			cmdlist.append(f"/usr/sbin/sgdisk -z {TARGET_DEVICE}")
			cmdlist.append(f"/bin/touch /dev/nomount.{TARGET} > /dev/null 2>&1")
			cmdlist.append(f"/bin/touch /dev/nomount.{TARGET}1 > /dev/null 2>&1")
			cmdlist.append(f"/usr/sbin/parted --script {TARGET_DEVICE} mklabel gpt")
			cmdlist.append(f"/usr/sbin/partprobe {TARGET_DEVICE}")
			cmdlist.append(f"/usr/sbin/parted --script {TARGET_DEVICE} mkpart startup fat32 8192s 5MB")
			cmdlist.append(f"/usr/sbin/parted --script {TARGET_DEVICE} unit MiB mkpart rootfs ext4 5MiB -- -{MULTIBOOT_SWAP_SIZE_MIB}MiB")
			cmdlist.append(f"/usr/sbin/parted --script {TARGET_DEVICE} unit MiB mkpart swap linux-swap -- -{MULTIBOOT_SWAP_SIZE_MIB}MiB 100%")
			cmdlist.append(f"/usr/sbin/partprobe {TARGET_DEVICE}")
			cmdlist.append(f"/usr/sbin/mkfs.vfat -F 32 -n STARTUP {PART(1)}")
			cmdlist.append(f"/sbin/mkfs.ext4 -O ^64bit,^extent,^flex_bg,^huge_file,^dir_nlink,^extra_isize,^metadata_csum {MKFS_EXT4_FAST_OPTIONS} -F -L rootfs {PART(2)}")
			cmdlist.append(f"/sbin/mkswap -L swap {PART(3)}")
			cmdlist.append(f"/bin/mkdir -p {MOUNTPOINT}")
			cmdlist.append(f"/bin/umount {MOUNTPOINT} > /dev/null 2>&1")
			cmdlist.append(f"/bin/mount {PART(1)} {MOUNTPOINT}")
			self.session.openWithCallback(self.formatDeviceCallback, ConsoleScreen, title=self.getTitle(), cmdlist=cmdlist)

	def formatDeviceCallback(self):
		def closeStartUpCallback(answer):
			if answer:
				self.session.open(TryQuitMainloop, QUIT_REBOOT)
		MOUNTPOINT = "/tmp/boot"
		mtdRootFs = BoxInfo.getItem("mtdrootfs")  # noqa F841
		mtdKernel = BoxInfo.getItem("mtdkernel")
		device = self.UBISlotManagerDevice
		PART_SUFFIX = "p" if "mmcblk" in device else ""
		uuidRootFS = fileReadLine(f"/dev/uuid/{device}{PART_SUFFIX}2", default=None, source=MODULE_NAME)
		diskSize = self.partitionSizeGB(f"/dev/{device}")

		machinebuild = BoxInfo.getItem("machinebuild")
		rootfsName = "dreambox-rootfs" if machinebuild == "dm520" else "rootfs"
		startupContent = f"kernel=/dev/{mtdKernel} ubi.mtd=rootfs root=ubi0:{rootfsName} flash=1 rootfstype=ubifs\n"

		with open(f"{MOUNTPOINT}/STARTUP", "w") as fd:
			fd.write(startupContent)
		with open(f"{MOUNTPOINT}/STARTUP_FLASH", "w") as fd:
			fd.write(startupContent)
		count = min(diskSize, self.UBISlotManagerSlots.value)
		for i in range(1, count + 1):
			startupContent = f"kernel=/dev/{mtdKernel} root=UUID={uuidRootFS} rootsubdir=linuxrootfs{i} rootfstype=ext4\n"
			with open(f"{MOUNTPOINT}/STARTUP_{i}", "w") as fd:
				fd.write(startupContent)
		Console().ePopen(["/bin/sync"])
		Console().ePopen(["/bin/umount", "/bin/umount", f"{MOUNTPOINT}"])
		self.session.openWithCallback(closeStartUpCallback, MessageBox, _("%d slots have been created on the device.\n") % count, type=MessageBox.TYPE_INFO, close_on_any_key=True, timeout=10)

	def showDeviceSelection(self):
		def readDevicesCallback():
			choiceList = [(_("Cancel"), None)]
			for device_id, (path, name) in self.deviceData.items():
				choiceList.append((f"{name} ({path})", device_id))
			self.session.openWithCallback(self.deviceSelectionCallback, MessageBox, text=_("Select target device for slot creation"), list=choiceList, windowTitle=self.getTitle())
		self.readDevices(readDevicesCallback)

	def deviceSelectionCallback(self, selection):
		if not selection:
			return

		print(f"[UBISlotManager] deviceSelectionCallback: selected device ID = {selection}")
		self.UBISlotManagerDevice = selection
		locations = self.UBISlotManagerLocation.getSelectionList()
		path = self.deviceData[selection][0]
		name = self.deviceData[selection][1]  # noqa F841
		if (path, path) not in locations:
			locations.append((path, path))
			self.UBISlotManagerLocation.setSelectionList(default=None, choices=locations)
			self.UBISlotManagerLocation.value = path
			self.createSetup()
		self.updateStatus(f"Selected device: {self.deviceData[selection][1]}")

	def partitionSizeGB(self, dev):
		try:
			base = dev.replace("/dev/", "")
			path = f"/sys/class/block/{base}/size"
			path = path if exists(path) else f"/sys/block/{base}/size"
			with open(path) as fd:
				blocks = int(fd.read().strip())
				return ceil((blocks * 512) / (1024 * 1024 * 1024))
		except Exception:
			return 0

	def readDevices(self, callback=None):
		def readDevicesCallback(output=None, retVal=None, extraArgs=None):
			def getDeviceID(deviceInfo):
				mode = "UUID="
				for token in deviceInfo:
					if token.startswith(mode):
						return token[len(mode):]
				return None

			print(f"[UBISlotManager] readDevicesCallback DEBUG: retVal={retVal}, output='{output}'.")
			mtdblack = BoxInfo.getItem("mtdblack") or ""
			blacklist = mtdblack.strip().split()

			self.deviceData = {}

			for (name, hdd) in harddiskmanager.HDDList():
				if any(hdd.dev_path.startswith(black) for black in blacklist) or hdd.dev_path.startswith("/dev/romblock"):
					continue

				deviceID = hdd.dev_path.split("/")[-1]
				self.deviceData[deviceID] = (hdd.dev_path, name)

			self.updateStatus()
			if callback and callable(callback):
				callback()

		self.console.ePopen(["/sbin/blkid", "/sbin/blkid"], callback=readDevicesCallback)

	def updateStatus(self, footnote=None):
		self.green = ACTION_CREATE if self.UBISlotManagerDevice else ACTION_SELECT
		self["key_green"].setText({
			ACTION_SELECT: _("Select Device"),
			ACTION_CREATE: _("Create Slots")
		}.get(self.green, _("Invalid")))
