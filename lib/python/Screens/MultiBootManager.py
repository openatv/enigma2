from Components.ActionMap import HelpableActionMap
from Components.ChoiceList import ChoiceEntryComponent, ChoiceList
from Components.Label import Label
from Components.Sources.StaticText import StaticText
from Screens.HelpMenu import HelpableScreen
from Screens.MessageBox import MessageBox
from Screens.Screen import Screen
from Screens.Standby import QUIT_REBOOT, TryQuitMainloop
from Tools.MultiBoot import MultiBoot


class MultiBootManager(Screen, HelpableScreen):
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
		<widget source="key_help" render="Label" position="e-100,e-50" size="90,40" backgroundColor="key_back" font="Regular;20" conditional="key_help" foregroundColor="key_text" halign="center" noWrap="1" valign="center">
			<convert type="ConditionalShowHide" />
		</widget>
	</screen>"""

	def __init__(self, session, *args):
		Screen.__init__(self, session)
		HelpableScreen.__init__(self)
		Screen.setTitle(self, _("MultiBoot Manager"))
		self["slotlist"] = ChoiceList([ChoiceEntryComponent("", (_("Loading slot information, please wait..."), "Loading"))])
		self["description"] = Label(_("Press the UP/DOWN buttons to select a slot and press OK or GREEN to reboot to that image. If available, YELLOW will either delete or wipe the image. A deleted image can be restored with the BLUE button. A wiped image is completely removed and cannot be restored!"))
		self["key_red"] = StaticText(_("Cancel"))
		self["key_green"] = StaticText(_("Reboot"))
		self["key_yellow"] = StaticText()
		self["key_blue"] = StaticText()
		self["actions"] = HelpableActionMap(self, ["CancelActions", "NavigationActions"], {
			"cancel": (self.cancel, _("Cancel the slot selection and exit")),
			"close": (self.closeRecursive, _("Cancel the slot selection and exit all menus")),
			"top": (self.keyTop, _("Move to first line / screen")),
			# "pageUp": (self.keyTop, _("Move up a screen")),
			"up": (self.keyUp, _("Move up a line")),
			# "left": (self.keyUp, _("Move up a line")),
			# "right": (self.keyDown, _("Move down a line")),
			"down": (self.keyDown, _("Move down a line")),
			# "pageDown": (self.keyBottom, _("Move down a screen")),
			"bottom": (self.keyBottom, _("Move to last line / screen"))
		}, prio=0, description=_("MultiBoot Manager Actions"))
		self["restartActions"] = HelpableActionMap(self, ["OkSaveActions"], {
			"save": (self.reboot, _("Select the highlighted slot and reboot")),
			"ok": (self.reboot, _("Select the highlighted slot and reboot")),
		}, prio=0, description=_("MultiBoot Manager Actions"))
		self["restartActions"].setEnabled(False)
		self["deleteActions"] = HelpableActionMap(self, ["ColorActions"], {
			"yellow": (self.deleteImage, _("Delete or Wipe the highlighted slot"))
		}, prio=0, description=_("MultiBoot Manager Actions"))
		self["deleteActions"].setEnabled(False)
		self["restoreActions"] = HelpableActionMap(self, ["ColorActions"], {
			"blue": (self.restoreImage, _("Restore the highlighted slot"))
		}, prio=0, description=_("MultiBoot Manager Actions"))
		self["restoreActions"].setEnabled(False)
		self.onLayoutFinish.append(self.layoutFinished)
		self.initialize = True
		self.callLater(self.getImagesList)

	def layoutFinished(self):
		self["slotlist"].instance.enableAutoNavigation(False)

	def getImagesList(self):
		MultiBoot.getSlotImageList(self.getSlotImageListCallback)

	def getSlotImageListCallback(self, slotImages):
		imageList = []
		if slotImages:
			slotCode, bootCode = MultiBoot.getCurrentSlotAndBootCodes()
			slotImageList = sorted(slotImages.keys())
			currentMsg = "  -  %s" % _("Current")
			slotMsg = _("Slot '%s': %s%s")
			imageLists = {}
			for slot in slotImageList:
				for boot in slotImages[slot]["bootCodes"]:
					if imageLists.get(boot) is None:
						imageLists[boot] = []
					current = currentMsg if boot == bootCode and slot == slotCode else ""
					imageLists[boot].append(ChoiceEntryComponent("none" if boot else "", (slotMsg % (slot, slotImages[slot]["imagename"], current), (slot, boot, slotImages[slot]["status"], slotImages[slot]["ubi"], current != ""))))
			for bootCode in sorted(imageLists.keys()):
				if bootCode == "":
					continue
				imageList.append(ChoiceEntryComponent("", (MultiBoot.getBootCodeDescription(bootCode), None)))
				imageList.extend(imageLists[bootCode])
			if "" in imageLists:
				imageList.extend(imageLists[""])
			if self.initialize:
				self.initialize = False
				for index, item in enumerate(imageList):
					if item[0][1] and item[0][1][4]:
						break
			else:
				index = self["slotlist"].getSelectedIndex()
		else:
			imageList.append(ChoiceEntryComponent("", (_("No slot images found"), "Void")))
			index = 0
		self["slotlist"].setList(imageList)
		self["slotlist"].moveToIndex(index)
		self.selectionChanged()

	def cancel(self):
		self.close()

	def closeRecursive(self):
		self.close(True)

	def deleteImage(self):
		self.session.openWithCallback(self.deleteImageAnswer, MessageBox, "%s\n\n%s" % (self["slotlist"].l.getCurrentSelection()[0][0], _("Are you sure you want to delete this image?")), simple=True, windowTitle=self.getTitle())

	def deleteImageAnswer(self, answer):
		if answer:
			currentSelected = self["slotlist"].l.getCurrentSelection()[0]
			MultiBoot.emptySlot(currentSelected[1][0], self.deleteImageCallback)

	def deleteImageCallback(self, result):
		currentSelected = self["slotlist"].l.getCurrentSelection()[0]
		if result:
			print("[MultiBootManager] %s deletion was not completely successful, status %d!" % (currentSelected[0], result))
		else:
			print("[MultiBootManager] %s marked as deleted." % currentSelected[0])
		self.getImagesList()

	def restoreImage(self):
		currentSelected = self["slotlist"].l.getCurrentSelection()[0]
		MultiBoot.restoreSlot(currentSelected[1][0], self.restoreImageCallback)

	def restoreImageCallback(self, result):
		currentSelected = self["slotlist"].l.getCurrentSelection()[0]
		if result:
			print("[MultiBootManager] %s restoration was not completely successful, status %d!" % (currentSelected[0], result))
		else:
			print("[MultiBootManager] %s restored." % currentSelected[0])
		self.getImagesList()

	def reboot(self):
		currentSelected = self["slotlist"].l.getCurrentSelection()[0]
		MultiBoot.activateSlot(currentSelected[1][0], currentSelected[1][1], self.rebootCallback)

	def rebootCallback(self, result):
		currentSelected = self["slotlist"].l.getCurrentSelection()[0]
		if result:
			print("[MultiBootManager] %s activation was not completely successful, status %d!" % (currentSelected[0], result))
		else:
			print("[MultiBootManager] %s activated." % currentSelected[0])
			self.session.open(TryQuitMainloop, QUIT_REBOOT)

	def selectionChanged(self):
		slotCode = MultiBoot.getCurrentSlotCode()
		currentSelected = self["slotlist"].l.getCurrentSelection()[0]
		slot = currentSelected[1][0]
		status = currentSelected[1][2]
		ubi = currentSelected[1][3]
		current = currentSelected[1][4]
		if slot == slotCode or status in ("android", "androidlinuxse", "recovery"):
			self["key_green"].setText(_("Reboot"))
			self["key_yellow"].setText("")
			self["key_blue"].setText("")
			self["restartActions"].setEnabled(True)
			self["deleteActions"].setEnabled(False)
			self["restoreActions"].setEnabled(False)
		elif status == "unknown":
			self["key_green"].setText("")
			self["key_yellow"].setText("")
			self["key_blue"].setText("")
			self["restartActions"].setEnabled(False)
			self["deleteActions"].setEnabled(False)
			self["restoreActions"].setEnabled(False)
		elif status == "empty":
			self["key_green"].setText("")
			self["key_yellow"].setText("")
			self["key_blue"].setText(_("Restore"))
			self["restartActions"].setEnabled(False)
			self["deleteActions"].setEnabled(False)
			self["restoreActions"].setEnabled(True)
		elif ubi:
			self["key_green"].setText(_("Reboot"))
			self["key_yellow"].setText(_("Wipe"))
			self["key_blue"].setText("")
			self["restartActions"].setEnabled(True)
			self["deleteActions"].setEnabled(True)
			self["restoreActions"].setEnabled(False)
		else:
			self["key_green"].setText(_("Reboot"))
			self["key_yellow"].setText(_("Delete"))
			self["key_blue"].setText("")
			self["restartActions"].setEnabled(True)
			self["deleteActions"].setEnabled(True)
			self["restoreActions"].setEnabled(False)

	def keyTop(self):
		self["slotlist"].instance.moveSelection(self["slotlist"].instance.moveTop)
		while self["slotlist"].l.getCurrentSelection()[0][1] is None:
			self["slotlist"].instance.moveSelection(self["slotlist"].instance.moveDown)
		self.selectionChanged()

	def keyUp(self):
		self["slotlist"].instance.moveSelection(self["slotlist"].instance.moveUp)
		while self["slotlist"].l.getCurrentSelection()[0][1] is None:
			self["slotlist"].instance.moveSelection(self["slotlist"].instance.moveUp)
		self.selectionChanged()

	def keyDown(self):
		self["slotlist"].instance.moveSelection(self["slotlist"].instance.moveDown)
		while self["slotlist"].l.getCurrentSelection()[0][1] is None:
			self["slotlist"].instance.moveSelection(self["slotlist"].instance.moveDown)
		self.selectionChanged()

	def keyBottom(self):
		self["slotlist"].instance.moveSelection(self["slotlist"].instance.moveEnd)
		while self["slotlist"].l.getCurrentSelection()[0][1] is None:
			self["slotlist"].instance.moveSelection(self["slotlist"].instance.moveUp)
		self.selectionChanged()
