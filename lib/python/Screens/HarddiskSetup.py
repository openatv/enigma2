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

	def __init__(self, session, hdd):
		Screen.__init__(self, session)
		self.hdd = hdd
		self["wait"] = Label(_("Initializing Harddisk..."));
		self.timer = eTimer()
		self.timer.timeout.get().append(self.doInit)
		self.timer.start(100)

class HarddiskSetup(Screen):
	def __init__(self, session, hdd):
		Screen.__init__(self, session)
		self.hdd = hdd
		
		self["model"] = Label(_("Model: ") + hdd.model())
		self["capacity"] = Label(_("Capacity: ") + hdd.capacity())
		self["bus"] = Label(_("Bus: ") + hdd.bus())
		self["initialize"] = Pixmap()
		self["initializetext"] = Label(_("Initialize"))

		self["actions"] = ActionMap(["OkCancelActions"],
		{
			"ok": self.close,
			"cancel": self.close
		})
		
		self["shortcuts"] = ActionMap(["ShortcutActions"],
		{
			"red": self.hddInitialize
		})

	def hddReady(self, result):
		print "Result: " + str(result)
		if (result != 0):
			self.session.open(MessageBox, _("Unable to initialize harddisk.\nPlease refer to the user manual.\nError: ") + str(self.hdd.errorList[0 - result]), MessageBox.TYPE_ERROR)
		else:
			self.close()

	def hddInitialize(self):
		self.session.openWithCallback(self.hddInitConfirmed, MessageBox, _("Do you really want to initialize the harddisk?\nAll data on the disk will be lost!"))

	def hddInitConfirmed(self, confirmed):
		if not confirmed:
			return

		print "this will start the initialize now!"
		self.session.openWithCallback(self.hddReady, HarddiskWait, self.hdd)
			
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
			self.session.open(HarddiskSetup, selection[1])
