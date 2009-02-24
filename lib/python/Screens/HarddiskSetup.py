from Screen import Screen
from Components.ActionMap import ActionMap
from Components.Harddisk import harddiskmanager			#global harddiskmanager
from Components.MenuList import MenuList
from Components.Label import Label
from Components.Pixmap import Pixmap
from Screens.MessageBox import MessageBox
from enigma import eTimer

class HarddiskWait(Screen):
	def doInit(self):
		self.timer.stop()
		result = self.hdd.initialize()
		self.close(result)

	def doCheck(self):
		self.timer.stop()
		result = self.hdd.check()
		self.close(result)

	def __init__(self, session, hdd, type):
		Screen.__init__(self, session)
		self.hdd = hdd
		self.timer = eTimer()
		if type == HarddiskSetup.HARDDISK_INITIALIZE:
			text = _("Initializing Harddisk...")
			self.timer.callback.append(self.doInit)
		else:
			text = _("Checking Filesystem...")
			self.timer.callback.append(self.doCheck)
		self["wait"] = Label(text)
		self.timer.start(100)

class HarddiskSetup(Screen):
	HARDDISK_INITIALIZE = 1
	HARDDISK_CHECK = 2

	def __init__(self, session, hdd, type = None):
		Screen.__init__(self, session)
		self.hdd = hdd

		if type not in (self.HARDDISK_INITIALIZE, self.HARDDISK_CHECK):
			self.type = self.HARDDISK_INITIALIZE
		else:
			self.type = type

		self["model"] = Label(_("Model: ") + hdd.model())
		self["capacity"] = Label(_("Capacity: ") + hdd.capacity())
		self["bus"] = Label(_("Bus: ") + hdd.bus())
		self["initialize"] = Pixmap()

		if self.type == self.HARDDISK_INITIALIZE:
			text = _("Initialize")
		else:
			text = _("Check")
		self["initializetext"] = Label(text)

		self["actions"] = ActionMap(["OkCancelActions"],
		{
			"ok": self.close,
			"cancel": self.close
		})
		
		self["shortcuts"] = ActionMap(["ShortcutActions"],
		{
			"red": self.hddQuestion
		})

	def hddReady(self, result):
		print "Result: " + str(result)
		if (result != 0):
			if self.type == self.HARDDISK_INITIALIZE:
				message = _("Unable to initialize harddisk.\nError: ")
			else:
				message = _("Unable to complete filesystem check.\nError: ")
			self.session.open(MessageBox, message + str(self.hdd.errorList[0 - result]), MessageBox.TYPE_ERROR)
		else:
			self.close()

	def hddQuestion(self):
		if self.type == self.HARDDISK_INITIALIZE:
			message = _("Do you really want to initialize the harddisk?\nAll data on the disk will be lost!")
		else:
			message = _("Do you really want to check the filesystem?\nThis could take lots of time!")
		self.session.openWithCallback(self.hddConfirmed, MessageBox, message)

	def hddConfirmed(self, confirmed):
		if not confirmed:
			return

		print "this will start either the initialize or the fsck now!"
		self.session.openWithCallback(self.hddReady, HarddiskWait, self.hdd, self.type)

class HarddiskSelection(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		
		if harddiskmanager.HDDCount() == 0:
			tlist = []
			tlist.append((_("no HDD found"), 0))
			self["hddlist"] = MenuList(tlist)
		else:			
			self["hddlist"] = MenuList(harddiskmanager.HDDList())
		
		self["actions"] = ActionMap(["OkCancelActions"],
		{
			"ok": self.okbuttonClick ,
			"cancel": self.close
		})

	def okbuttonClick(self):
		selection = self["hddlist"].getCurrent()
		if selection[1] != 0:
			self.session.open(HarddiskSetup, selection[1], HarddiskSetup.HARDDISK_INITIALIZE)

# This is actually just HarddiskSelection but with correct type
class HarddiskFsckSelection(HarddiskSelection):
	def __init__(self, session):
		HarddiskSelection.__init__(self, session)
		self.skinName = "HarddiskSelection"

	def okbuttonClick(self):
		selection = self["hddlist"].getCurrent()
		if selection[1] != 0:
			self.session.open(HarddiskSetup, selection[1], HarddiskSetup.HARDDISK_CHECK)
