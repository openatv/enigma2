from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Screens.ChoiceBox import ChoiceBox
from Screens.Standby import TryQuitMainloop
from Screens.Console import Console
from Components.ActionMap import ActionMap
from Components.Sources.StaticText import StaticText
from Components.Sources.Progress import Progress
from Components.Sources.Boolean import Boolean
from Components.Label import Label
from Components.FileList import FileList
from Components.Task import Task, Job, job_manager, Condition
from Screens.TaskView import JobView
from Tools.Directories import fileExists
from Tools.HardwareInfo import HardwareInfo
from os import system
from enigma import eConsoleAppContainer, quitMainloop, eEnv
from Components.About import about

class md5Postcondition(Condition):
	def check(self, task):
		print "md5Postcondition::check", task.returncode
		return task.returncode == 0

	def getErrorMessage(self, task):
		if task.returncode == 1:
			return _("The md5sum validation failed, the file may be corrupted!")
		return "md5 error"

class md5verify(Task):
	def __init__(self, job, path, md5):
		Task.__init__(self, job, "md5sum")
		self.postconditions.append(md5Postcondition())
		self.weighting = 5
		self.cwd = path
		self.setTool("md5sum")
		self.args += ["-c", "-s"]
		self.initial_input = md5
	
	def writeInput(self, input):
		self.container.dataSent.append(self.md5ready)
		print "[writeInput]", input
		Task.writeInput(self, input)

	def md5ready(self, retval):
		self.container.sendEOF()

	def processOutput(self, data):
		print "[md5sum]",

class writeNAND(Task):
	def __init__(self, job, param, box):
		Task.__init__(self,job, ("Writing image file to NAND Flash"))
		self.setTool(eEnv.resolve("${libdir}/enigma2/python/Plugins/SystemPlugins/NFIFlash/writenfi-mipsel-2.6.18-r1"))
		if box == "dm7025":
			self.end = 256
		elif box[:5] == "dm800":
			self.end = 512
		self.args += param
		self.weighting = 95

	def processOutput(self, data):
		print "[writeNand] " + data
		if data == "." or data.endswith(" ."):
			self.progress += 1
		elif data.find("*** done!") > 0:
			print "data.found done"
			self.setProgress(self.end)
		else:
			self.output_line = data

class NFIFlash(Screen):
	skin = """
	<screen name="NFIFlash" position="center,center" size="610,410" title="Image flash utility" >
		<ePixmap pixmap="skin_default/buttons/red.png" position="0,0" size="140,40" alphatest="on" />
		<ePixmap pixmap="skin_default/buttons/green.png" position="140,0" size="140,40" alphatest="on" />
		<ePixmap pixmap="skin_default/buttons/yellow.png" position="280,0" size="140,40" alphatest="on" />
		<ePixmap pixmap="skin_default/buttons/blue.png" position="420,0" size="140,40" alphatest="on" />
		<widget source="key_red" render="Label" position="0,0" zPosition="1" size="140,40" font="Regular;20" valign="center" halign="center" backgroundColor="#9f1313" transparent="1" />
		<widget source="key_green" render="Label" position="140,0" zPosition="1" size="140,40" font="Regular;20" valign="center" halign="center" backgroundColor="#1f771f" transparent="1" />
		<widget source="key_yellow" render="Label" position="280,0" zPosition="1" size="140,40" font="Regular;20" valign="center" halign="center" backgroundColor="#a08500" transparent="1" />
		<widget source="key_blue" render="Label" position="420,0" zPosition="1" size="140,40" font="Regular;20" valign="center" halign="center" backgroundColor="#18188b" transparent="1" />
		<ePixmap pixmap="skin_default/border_menu_350.png" position="5,50" zPosition="1" size="350,300" transparent="1" alphatest="on" />
		<widget name="filelist" position="15,60" size="330,284" scrollbarMode="showOnDemand" />
		<widget source="infolabel" render="Label" position="360,50" size="240,300" font="Regular;13" />
		<widget source="status" render="Label" position="5,360" zPosition="10" size="600,50" halign="center" valign="center" font="Regular;22" transparent="1" shadowColor="black" shadowOffset="-1,-1" />
	</screen>"""

	def __init__(self, session, destdir=None):
		Screen.__init__(self, session)
		
		self.box = HardwareInfo().get_device_name()
		self.usbmountpoint = "/mnt/usb/"

		self["key_red"] = StaticText()
		self["key_green"] = StaticText()
		self["key_yellow"] = StaticText()
		self["key_blue"] = StaticText()
		self.filelist = FileList(self.usbmountpoint, matchingPattern = "^.*\.(nfi|NFI)", showDirectories = False, showMountpoints = False)
		self["filelist"] = self.filelist
		self["infolabel"] = StaticText()

		self["status"] = StaticText(_("Please select an NFI file and press green key to flash!") + '\n' + _("currently installed image: %s") % (about.getImageVersionString()))
		self.job = None

		self["shortcuts"] = ActionMap(["OkCancelActions", "ColorActions", "ShortcutActions", "DirectionActions"],
		{
			"ok": self.keyOk,
			"green": self.keyOk,
			"up": self.keyUp,
			"upRepeated": self.keyUp,
			"downRepeated": self.keyDown,
			"down": self.keyDown,
			"left": self.keyLeft,
			"yellow": self.reboot,
			"right": self.keyRight
		}, -1)
		self.md5sum = ""
		self.onShown.append(self.autostart)

	def autostart(self):
		self.onShown.remove(self.autostart)
		self.check_for_NFO()
		print "[[layoutFinished]]", len(self["filelist"].getFileList())
		if len(self["filelist"].getFileList()) == 1:
			print "==1"
			self.keyOk()

	def keyUp(self):
		self["filelist"].up()
		self.check_for_NFO()

	def keyDown(self):
		self["filelist"].down()
		self.check_for_NFO()
	
	def keyRight(self):
		self["filelist"].pageDown()
		self.check_for_NFO()

	def keyLeft(self):
		self["filelist"].pageUp()
		self.check_for_NFO()

	def keyOk(self):
		if self.job is None or self.job.status is not self.job.IN_PROGRESS:
			if self["filelist"].canDescent(): # isDir
				self["filelist"].descent()
				self.check_for_NFO()
			elif self["filelist"].getFilename():
				self.session.openWithCallback(self.queryCB, MessageBox, _("Shall the USB stick wizard proceed and program the image file %s into flash memory?" % self.nfifile.rsplit('/',1)[-1]), MessageBox.TYPE_YESNO)

	def check_for_NFO(self, nfifile=None):
		print "check_for_NFO", self["filelist"].getFilename(), self["filelist"].getCurrentDirectory()
		self["infolabel"].text = ""
		self["key_green"].text = ""

		if nfifile is None:
			if self["filelist"].getFilename() is None:
				return
			if self["filelist"].getCurrentDirectory() is not None:
				self.nfifile = self["filelist"].getCurrentDirectory()+self["filelist"].getFilename()
		else:
			self.nfifile = nfifile

		if self.nfifile.upper().endswith(".NFI"):
			self["key_green"].text = _("Flash")
			nfofilename = self.nfifile[0:-3]+"nfo"
			print nfofilename, fileExists(nfofilename)
			if fileExists(nfofilename):
				nfocontent = open(nfofilename, "r").read()
				print "nfocontent:", nfocontent
				self["infolabel"].text = nfocontent
				pos = nfocontent.find("MD5:")
				if pos > 0:
					self.md5sum = nfocontent[pos+5:pos+5+32] + "  " + self.nfifile
				else:
					self.md5sum = ""
			else:
				self["infolabel"].text = _("No details for this image file") + (self["filelist"].getFilename() or "")
				self.md5sum = ""

	def queryCB(self, answer):
		if answer == True:
			self.createJob()

	def createJob(self):
		self.job = Job("Image flashing job")
		self.job.afterEvent = "close"
		cwd = self["filelist"].getCurrentDirectory()
		md5verify(self.job, cwd, self.md5sum)
		writeNAND(self.job, [self.nfifile], self.box)
		self["key_blue"].text = ""
		self["key_yellow"].text = ""
		self["key_green"].text = ""
		job_manager.AddJob(self.job)
		self.session.openWithCallback(self.flashed, JobView, self.job, cancelable = False, backgroundable = False, afterEventChangeable = False)

	def flashed(self, bg):
		print "[flashed]"
		if self.job.status == self.job.FINISHED:
			self["status"].text = _("NFI image flashing completed. Press Yellow to Reboot!")
			filename = self.usbmountpoint+'enigma2settingsbackup.tar.gz'
			if fileExists(filename):
				import os.path, time
				date = time.ctime(os.path.getmtime(filename))
				self.session.openWithCallback(self.askRestoreCB, MessageBox, _("The wizard found a configuration backup. Do you want to restore your old settings from %s?") % date, MessageBox.TYPE_YESNO)
			else:
				self.unlockRebootButton()
		else:
			self["status"].text = _("Flashing failed")

	def askRestoreCB(self, ret):
		if ret:
			from Plugins.SystemPlugins.SoftwareManager.BackupRestore import getBackupFilename
			restorecmd = ["tar -xzvf " + self.usbmountpoint + getBackupFilename() + " -C /"]
			self.session.openWithCallback(self.unlockRebootButton, Console, title = _("Restore is running..."), cmdlist = restorecmd, closeOnSuccess = True)
		else:
			self.unlockRebootButton()

	def unlockRebootButton(self, retval = None):
		if self.job.status == self.job.FINISHED:
			self["key_yellow"].text = _("Reboot")

	def reboot(self, ret=None):
		if self.job.status == self.job.FINISHED:
			self["status"].text = ("rebooting...")
			from os import system
			system(eEnv.resolve("${libdir}/enigma2/python/Plugins/SystemPlugins/NFIFlash/kill_e2_reboot.sh"))
