from Screen import Screen
from Components.ActionMap import ActionMap
from Components.Harddisk import harddiskmanager
from Components.MenuList import MenuList
from Components.Label import Label
from Components.Pixmap import Pixmap
from Screens.MessageBox import MessageBox

class HarddiskSetup(Screen):
	def __init__(self, session, hdd, action, text, question):
		Screen.__init__(self, session)
		self.action = action
		self.question = question
		self["model"] = Label(_("Model: ") + hdd.model())
		self["capacity"] = Label(_("Capacity: ") + hdd.capacity())
		self["bus"] = Label(_("Bus: ") + hdd.bus())
		self["initialize"] = Pixmap()
		self["initializetext"] = Label(text)
		self["actions"] = ActionMap(["OkCancelActions"],
		{
			"ok": self.hddQuestion,
			"cancel": self.close
		})
		self["shortcuts"] = ActionMap(["ShortcutActions"],
		{
			"red": self.hddQuestion
		})

	def hddQuestion(self):
		message = self.question + "\n" + _("You can continue watching TV etc. while this is running.")
		self.session.openWithCallback(self.hddConfirmed, MessageBox, message)

	def hddConfirmed(self, confirmed):
		if not confirmed:
			return
		from Components.Task import job_manager
		try:
			job = self.action()
			job_manager.AddJob(job, onSuccess=job_manager.popupTaskView)
			from TaskView import JobView
			self.session.open(JobView, job, afterEventChangeable=False)
		except Exception, ex:
			self.session.open(MessageBox, str(ex), type=MessageBox.TYPE_ERROR, timeout=10)
		self.close()

class HarddiskSelection(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		self.skinName = "HarddiskSelection" # For derived classes
		if harddiskmanager.HDDCount() == 0:
			tlist = []
			tlist.append((_("no storage devices found"), 0))
			self["hddlist"] = MenuList(tlist)
		else:
			self["hddlist"] = MenuList(harddiskmanager.HDDList())
		self["actions"] = ActionMap(["OkCancelActions"],
		{
			"ok": self.okbuttonClick,
			"cancel": self.close
		})

	def doIt(self, selection):
		self.session.openWithCallback(self.close, HarddiskSetup, selection,
			 action=selection.createInitializeJob,
			 text=_("Initialize"),
			 question=_("Do you really want to initialize the device?\nAll data on the disk will be lost!"))

	def okbuttonClick(self):
		selection = self["hddlist"].getCurrent()
		if selection[1] != 0:
			self.doIt(selection[1])

# This is actually just HarddiskSelection but with correct type
class HarddiskFsckSelection(HarddiskSelection):
	def doIt(self, selection):
		self.session.openWithCallback(self.close, HarddiskSetup, selection,
			 action=selection.createCheckJob,
			 text=_("Check"),
			 question=_("Do you really want to check the filesystem?\nThis could take lots of time!"))

class HarddiskConvertExt4Selection(HarddiskSelection):
	def doIt(self, selection):
		self.session.openWithCallback(self.close, HarddiskSetup, selection,
			 action=selection.createExt4ConversionJob,
			 text=_("Convert ext3 to ext4"),
			 question=_("Do you really want to convert the filesystem?\nYou cannot go back!"))
