from Screens.Screen import Screen
from Components.ActionMap import ActionMap
from Components.Harddisk import harddiskmanager
from Components.MenuList import MenuList
from Components.Label import Label
from Components.Pixmap import Pixmap
from Components.Task import job_manager
from Screens.MessageBox import MessageBox
from Tools.BoundFunction import boundFunction
import Screens.InfoBar

from enigma import eListboxPythonMultiContent, gFont
from Components.MultiContent import MultiContentEntryText

class HarddiskSetup(Screen):
	def __init__(self, session, hdd, action, text, question):
		Screen.__init__(self, session)
		self.action = action
		self.question = question
		self.curentservice = None
		self["model"] = Label(_("Model: ") + hdd.model())
		self["capacity"] = Label(_("Capacity: ") + hdd.capacity())
		self["bus"] = Label(_("Bus: ") + hdd.bus())
		self["key_red"] = Label(text)
		self["key_green"] = Label()
		self["key_yellow"] = Label()
		self["key_blue"] = Label()
		self["actions"] = ActionMap(["OkCancelActions"],
		{
			"ok": self.hddQuestion,
			"cancel": self.close
		})
		self["shortcuts"] = ActionMap(["ShortcutActions"],
		{
			"red": self.hddQuestion
		})

	def hddQuestion(self, answer=False):
		print 'answer:',answer
		if Screens.InfoBar.InfoBar.instance.timeshiftEnabled():
			message = self.question + "\n" + _("You seem to be in time shift. In order to proceed, time shift needs to stop.")
			message += '\n' + _("Do you want to continue?")
			self.session.openWithCallback(self.stopTimeshift, MessageBox, message)
		else:
			message = self.question + "\n" + _("You can continue watching while this is running.")
			self.session.openWithCallback(self.hddConfirmed, MessageBox, message)

	def stopTimeshift(self, confirmed):
		if confirmed:
			self.curentservice = self.session.nav.getCurrentlyPlayingServiceReference()
			self.session.nav.stopService()
			Screens.InfoBar.InfoBar.instance.stopTimeshiftcheckTimeshiftRunningCallback(True)
			self.hddConfirmed(True)

	def hddConfirmed(self, confirmed):
		if not confirmed:
			return
		try:
			job_manager.AddJob(self.action())
			for job in job_manager.getPendingJobs():
				if job.name in (_("Initializing storage device..."), _("Checking file system..."),_("Converting ext3 to ext4...")):
					self.showJobView(job)
					break
		except Exception, ex:
			self.session.open(MessageBox, str(ex), type=MessageBox.TYPE_ERROR, timeout=10)

		if self.curentservice:
			self.session.nav.playService(self.curentservice)
		self.close()

	def showJobView(self, job):
		from Screens.TaskView import JobView
		job_manager.in_background = False
		self.session.openWithCallback(self.JobViewCB, JobView, job, cancelable=False, afterEventChangeable=False, afterEvent="close")

	def JobViewCB(self, in_background):
		job_manager.in_background = in_background

class HarddiskMenuList(MenuList):
	def __init__(self, list, enableWrapAround = False):
		MenuList.__init__(self, list, enableWrapAround, eListboxPythonMultiContent)
		self.l.setFont(0, gFont("Regular", 22))
		self.l.setFont(1, gFont("Regular", 14))
		self.l.setItemHeight(50)
	
def SubHarddiskMenuEntryComponent(name, item):
	return [
		_(item),
		MultiContentEntryText(pos=(20, 10), size=(540, 50), font=0, text = _(name)),
	]
	
class HarddiskSelection(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		Screen.setTitle(self, _("Initialization"))
		self.skinName = "HarddiskSelection" # For derived classes
		
		menu = []
		if harddiskmanager.HDDCount() == 0:
			menu.append(SubHarddiskMenuEntryComponent((_("no storage devices found")), 0))
		else:
			for x in harddiskmanager.HDDList():
				menu.append(SubHarddiskMenuEntryComponent(x[0], x))

		self["hddlist"] = HarddiskMenuList(menu)
		
		self["key_red"] = Label(_("Exit"))
		self["key_green"] = Label(_("Select"))
		self["key_yellow"] = Label()
		self["key_blue"] = Label()
		self["actions"] = ActionMap(["SetupActions"],
		{
			"save" : self.okbuttonClick,
			"ok": self.okbuttonClick,
			"cancel": self.close,
			"red": self.close
		})

	def doIt(self, selection):
		self.session.openWithCallback(self.close, HarddiskSetup, selection,
			 action=selection.createInitializeJob,
			 text=_("Initialize"),
			 question=_("Do you really want to initialize the device?\nAll data on the disk will be lost!"))

	def okbuttonClick(self):
		selection = self["hddlist"].getCurrent()[0]
		if selection != 0:
			self.doIt(selection[1])
			self.close(True)
			
# This is actually just HarddiskSelection but with correct type
class HarddiskFsckSelection(HarddiskSelection):
	def __init__(self, session):
		HarddiskSelection.__init__(self, session)
		Screen.setTitle(self, _("File system check"))
		self.skinName = "HarddiskSelection"

	def doIt(self, selection):
		self.session.openWithCallback(self.close, HarddiskSetup, selection,
			 action=selection.createCheckJob,
			 text=_("Check"),
			 question=_("Do you really want to check the file system?\nThis could take a long time!"))

class HarddiskConvertExt4Selection(HarddiskSelection):
	def __init__(self, session):
		HarddiskSelection.__init__(self, session)
		Screen.setTitle(self, _("Convert file system"))
		self.skinName = "HarddiskSelection"

	def doIt(self, selection):
		self.session.openWithCallback(self.close, HarddiskSetup, selection,
			 action=selection.createExt4ConversionJob,
			 text=_("Convert ext3 to ext4"),
			 question=_("Do you really want to convert the file system?\nYou cannot go back!"))
