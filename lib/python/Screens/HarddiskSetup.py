from Screens.Screen import Screen
from Components.ActionMap import ActionMap
from Components.Harddisk import harddiskmanager
from Components.MenuList import MenuList
from Components.Label import Label
from Components.Pixmap import Pixmap
from Components.Task import job_manager
from Components.config import config
from Components.Sources.StaticText import StaticText
from Screens.MessageBox import MessageBox
from Tools.BoundFunction import boundFunction
import Screens.InfoBar

from enigma import eListboxPythonMultiContent, gFont
from Components.MultiContent import MultiContentEntryText

class HarddiskSetup(Screen):
	def __init__(self, session, hdd, action, text, question, menu_path=""):
		Screen.__init__(self, session)
		screentitle = text
		if config.usage.show_menupath.value == 'large':
			menu_path += screentitle
			title = menu_path
			self["menu_path_compressed"] = StaticText("")
		elif config.usage.show_menupath.value == 'small':
			title = screentitle
			self["menu_path_compressed"] = StaticText(menu_path + " >" if not menu_path.endswith(' / ') else menu_path[:-3] + " >" or "")
		else:
			title = screentitle
			self["menu_path_compressed"] = StaticText("")
		Screen.setTitle(self, title)

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
		print '[HarddiskSetup] answer:',answer
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
	def __init__(self, session, menu_path=""):
		Screen.__init__(self, session)
		screentitle = _("Initialize Devices")
		self.menu_path = menu_path
		if config.usage.show_menupath.value == 'large':
			self.menu_path += screentitle
			title = self.menu_path
			self["menu_path_compressed"] = StaticText("")
			self.menu_path += ' / '
		elif config.usage.show_menupath.value == 'small':
			title = screentitle
			condtext = ""
			if self.menu_path and not self.menu_path.endswith(' / '):
				condtext = self.menu_path + " >"
			elif self.menu_path:
				condtext = self.menu_path[:-3] + " >"
			self["menu_path_compressed"] = StaticText(condtext)
			self.menu_path += screentitle + ' / '
		else:
			title = screentitle
			self["menu_path_compressed"] = StaticText("")
		Screen.setTitle(self, title)

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
			 question=_("Do you really want to initialize this device?\nAll the data on the device will be lost!"), menu_path=self.menu_path)

	def okbuttonClick(self):
		selection = self["hddlist"].getCurrent()[0]
		if selection != 0:
			self.doIt(selection[1])
			self.close(True)
			
# This is actually just HarddiskSelection but with correct type
class HarddiskFsckSelection(HarddiskSelection):
	def __init__(self, session, menu_path=""):
		HarddiskSelection.__init__(self, session)
		screentitle = _("File system check")
		self.menu_path = menu_path
		if config.usage.show_menupath.value == 'large':
			self.menu_path += screentitle
			title = self.menu_path
			self["menu_path_compressed"] = StaticText("")
			self.menu_path += ' / '
		elif config.usage.show_menupath.value == 'small':
			title = screentitle
			condtext = ""
			if self.menu_path and not self.menu_path.endswith(' / '):
				condtext = self.menu_path + " >"
			elif self.menu_path:
				condtext = self.menu_path[:-3] + " >"
			self["menu_path_compressed"] = StaticText(condtext)
			self.menu_path += screentitle + ' / '
		else:
			title = screentitle
			self["menu_path_compressed"] = StaticText("")
		Screen.setTitle(self, title)
		self.skinName = "HarddiskSelection"

	def doIt(self, selection):
		self.session.openWithCallback(self.close, HarddiskSetup, selection,
			 action=selection.createCheckJob,
			 text=_("Check"),
			 question=_("Do you really want to check the file system?\nThis could take a long time!"), menu_path=self.menu_path)

class HarddiskConvertExt4Selection(HarddiskSelection):
	def __init__(self, session, menu_path=""):
		HarddiskSelection.__init__(self, session)
		screentitle = _("Convert file system")
		self.menu_path = menu_path
		if config.usage.show_menupath.value == 'large':
			self.menu_path += screentitle
			title = self.menu_path
			self["menu_path_compressed"] = StaticText("")
			self.menu_path += ' / '
		elif config.usage.show_menupath.value == 'small':
			title = screentitle
			condtext = ""
			if self.menu_path and not self.menu_path.endswith(' / '):
				condtext = self.menu_path + " >"
			elif self.menu_path:
				condtext = self.menu_path[:-3] + " >"
			self["menu_path_compressed"] = StaticText(condtext)
			self.menu_path += screentitle + ' / '
		else:
			title = screentitle
			self["menu_path_compressed"] = StaticText("")
		Screen.setTitle(self, title)
		self.skinName = "HarddiskSelection"

	def doIt(self, selection):
		self.session.openWithCallback(self.close, HarddiskSetup, selection,
			 action=selection.createExt4ConversionJob,
			 text=_("Convert ext3 to ext4"),
			 question=_("Do you really want to convert the file system?\nYou cannot go back!"), menu_path=self.menu_path)
