# -*- coding: utf8 -*-
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Screens.ChoiceBox import ChoiceBox
from Screens.Standby import TryQuitMainloop
from Components.ActionMap import ActionMap
from Components.Sources.StaticText import StaticText
from Components.Sources.Progress import Progress
from Components.Sources.Boolean import Boolean
from Components.Label import Label
from Components.FileList import FileList
from Components.Task import Task, Job, JobManager
from Tools.Directories import fileExists
from Tools.HardwareInfo import HardwareInfo
from os import system
from enigma import eConsoleAppContainer
import re

class writeNAND(Task):
	def __init__(self,job,param,box):
		Task.__init__(self,job, _("Writing image file to NAND Flash"))
		self.setTool("/usr/lib/enigma2/python/Plugins/SystemPlugins/NFIFlash/mywritenand")
		if box == "dm7025":
			self.end = 256
		elif box[:5] == "dm800":
			self.end = 512
		if box == "dm8000":
			self.setTool("/usr/lib/enigma2/python/Plugins/SystemPlugins/NFIFlash/dm8000_writenand")
		self.args += param
		self.weighting = 1	

	def processOutput(self, data):
		print "[writeNand] " + data
		if data == "." or data.endswith(" ."):
			self.progress += 1
		elif data.find("*** done!") > 0:
			print "data.found done"
			self.setProgress(self.end)
		else:
			self.output_line = data

class NFISummary(Screen):
	skin = """
	<screen position="0,0" size="132,64">
		<widget source="title" render="Label" position="2,0" size="120,14" valign="center" font="Regular;12" />
		<widget source="content" render="Label" position="2,14" size="120,34" font="Regular;12" transparent="1" zPosition="1"  />
		<widget source="job_progresslabel" render="Label" position="66,50" size="60,14" font="Regular;12" transparent="1" halign="right" zPosition="0" />
		<widget source="job_progressbar" render="Progress" position="2,50" size="66,14" borderWidth="1" />
	</screen>"""

	def __init__(self, session, parent):
		Screen.__init__(self, session, parent)
		self["title"] = StaticText(_("Image flash utility"))
		self["content"] = StaticText(_("Please select .NFI flash image file from medium"))
		self["job_progressbar"] = Progress()
		self["job_progresslabel"] = StaticText("")

	def setText(self, text):
		self["content"].setText(text)

class NFIFlash(Screen):
	skin = """
		<screen name="NFIFlash" position="90,95" size="560,420" title="Image flash utility">
			<ePixmap pixmap="skin_default/buttons/green.png" position="140,0" zPosition="0" size="140,40" transparent="1" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/yellow.png" position="280,0" zPosition="0" size="140,40" transparent="1" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/blue.png" position="420,0" zPosition="0" size="140,40" transparent="1" alphatest="on" />
			<widget source="key_green" render="Label" position="140,0" zPosition="1" size="140,40" font="Regular;20" valign="center" halign="center" backgroundColor="#1f771f" transparent="1" />
			<widget source="key_yellow" render="Label" position="280,0" zPosition="1" size="140,40" font="Regular;20" valign="center" halign="center" backgroundColor="#a08500" transparent="1" />
			<widget source="key_blue" render="Label" position="420,0" zPosition="1" size="140,40" font="Regular;20" valign="center" halign="center" backgroundColor="#18188b" transparent="1" />
			<widget source="listlabel" render="Label" position="16,44" size="200,21" valign="center" font="Regular;18" />
			<widget name="filelist" position="0,68" size="260,260" scrollbarMode="showOnDemand" />
			<widget source="infolabel" render="Label" position="270,44" size="280,284" font="Regular;16" />
			<widget source="job_progressbar" render="Progress" position="10,374" size="540,26" borderWidth="1" backgroundColor="#254f7497" />
			<widget source="job_progresslabel" render="Label" position="180,378" zPosition="2" font="Regular;18" halign="center" transparent="1" size="200,22" foregroundColor="#000000" />
			<widget source="statusbar" render="Label" position="10,404" size="540,16" font="Regular;16" foregroundColor="#cccccc" />
		</screen>"""

	def __init__(self, session, cancelable = True, close_on_finish = False):
		self.skin = NFIFlash.skin
		Screen.__init__(self, session)
		
		self["job_progressbar"] = Progress()
		self["job_progresslabel"] = StaticText("")
		
		self["finished"] = Boolean()

		self["infolabel"] = StaticText("")
		self["statusbar"] = StaticText(_("Please select .NFI flash image file from medium"))
		self["listlabel"] = StaticText(_("select .NFI flash file")+":")
		
		self["key_green"] = StaticText()
		self["key_yellow"] = StaticText()
		self["key_blue"] = StaticText()

		self["actions"] = ActionMap(["OkCancelActions", "ColorActions", "DirectionActions"],
		{
			"green": self.ok,
			"yellow": self.reboot,
			"ok": self.ok,
			"left": self.left,
			"right": self.right,
			"up": self.up,
			"down": self.down
		}, -1)

		currDir = "/media/usb/"
		self.filelist = FileList(currDir, matchingPattern = "^.*\.(nfi|NFI)")
		self["filelist"] = self.filelist
		self.nfifile = ""
		self.md5sum = ""
		self.job = None
		self.box = HardwareInfo().get_device_name()

	def closeCB(self):
		if ( self.job is None or self.job.status is not self.job.IN_PROGRESS ) and not self.no_autostart:
			self.close()
		#else:
			#if self.cancelable:
				#self.cancel()

	def up(self):
		self["filelist"].up()
		self.check_for_NFO()

	def down(self):
		self["filelist"].down()
		self.check_for_NFO()
	
	def right(self):
		self["filelist"].pageDown()
		self.check_for_NFO()

	def left(self):
		self["filelist"].pageUp()
		self.check_for_NFO()

	def check_for_NFO(self):
		self.session.summary.setText(self["filelist"].getFilename())
		if self["filelist"].getFilename() is None:
			return
		if self["filelist"].getCurrentDirectory() is not None:
			self.nfifile = self["filelist"].getCurrentDirectory()+self["filelist"].getFilename()

		if self.nfifile.upper().endswith(".NFI"):
			self["key_green"].text = _("Flash")
			nfofilename = self.nfifile[0:-3]+"nfo"
			if fileExists(nfofilename):
				nfocontent = open(nfofilename, "r").read()
				self["infolabel"].text = nfocontent
				pos = nfocontent.find("md5sum")
				if pos > 0:
					self.md5sum = nfofilename
				else:
					self.md5sum = ""
			else:
				self["infolabel"].text = _("No details for this image file") + ":\n" + self["filelist"].getFilename()
				self.md5sum = ""
		else:
			self["infolabel"].text = ""
			self["key_green"].text = ""

	def ok(self):
		if self.job is None or self.job.status is not self.job.IN_PROGRESS:
			if self["filelist"].canDescent(): # isDir
				self["filelist"].descent()
				self.session.summary.setText(self["filelist"].getFilename())
				self.check_for_NFO()
			else:
				self.queryFlash()
	
	def queryFlash(self):
		fd = open(self.nfifile, 'r')
		print fd
		sign = fd.read(11)
		print sign
		if sign.find("NFI1" + self.box + "\0") == 0:
			if self.md5sum != "":
				self["statusbar"].text = _("Please wait for md5 signature verification...")
				self.session.summary.setText(_("Please wait for md5 signature verification..."))
				self.container = eConsoleAppContainer()
				self.container.setCWD(self["filelist"].getCurrentDirectory())
				self.container.appClosed.get().append(self.md5finished)
				self.container.execute("md5sum -cs " + self.md5sum)
			else:
				self.session.openWithCallback(self.queryCB, MessageBox, _("This .NFI file does not have a md5sum signature and is not guaranteed to work. Do you really want to burn this image to flash memory?"), MessageBox.TYPE_YESNO)
		else:
			self.session.open(MessageBox, (_("This .NFI file does not contain a valid %s image!") % (self.box.upper())), MessageBox.TYPE_ERROR)
			
	def md5finished(self, retval):
		if retval==0:
			self.session.openWithCallback(self.queryCB, MessageBox, _("This .NFI file has a valid md5 signature. Continue programming this image to flash memory?"), MessageBox.TYPE_YESNO)
		else:
			self.session.openWithCallback(self.queryCB, MessageBox, _("The md5sum validation failed, the file may be corrupted! Are you sure that you want to burn this image to flash memory? You are doing this at your own risk!"), MessageBox.TYPE_YESNO)

	def queryCB(self, answer):
		if answer == True:
			self.createJob()
		else:
			self["statusbar"].text = _("Please select .NFI flash image file from medium")

	def createJob(self):
		self.job = Job("Image flashing job")
		param = [self.nfifile]
		writeNAND(self.job,param,self.box)
		#writeNAND2(self.job,param)
		#writeNAND3(self.job,param)
		self.job.state_changed.append(self.update_job)
		self.job.end = 540
		self.cwd = self["filelist"].getCurrentDirectory()
		self["job_progressbar"].range = self.job.end
		self.startJob()

	def startJob(self):
		self["key_blue"].text = ""
		self["key_yellow"].text = ""
		self["key_green"].text = ""
		#self["progress0"].show()
		#self["progress1"].show()

		self.job.start(self.jobcb)

	def update_job(self):
		j = self.job
		#print "[job state_changed]"
		if j.status == j.IN_PROGRESS:
			self.session.summary["job_progressbar"].value = j.progress
			self.session.summary["job_progressbar"].range = j.end
			self.session.summary["job_progresslabel"].text = "%.2f%%" % (100*j.progress/float(j.end))
			self["job_progressbar"].range = j.end
			self["job_progressbar"].value = j.progress
			#print "[update_job] j.progress=%f, j.getProgress()=%f, j.end=%d, text=%f" % (j.progress, j.getProgress(), j.end,  (100*j.progress/float(j.end)))
			self["job_progresslabel"].text = "%.2f%%" % (100*j.progress/float(j.end))
			self.session.summary.setText(j.tasks[j.current_task].name)
			self["statusbar"].text = (j.tasks[j.current_task].name)

		elif j.status == j.FINISHED:
			self["statusbar"].text = _("Writing NFI image file to flash completed")
			self.session.summary.setText(_("NFI image flashing completed. Press Yellow to Reboot!"))
			self["key_yellow"].text = _("Reboot")

		elif j.status == j.FAILED:
			self["statusbar"].text = j.tasks[j.current_task].name + " " + _("failed")
			self.session.open(MessageBox, (_("Flashing failed") + ":\n" + j.tasks[j.current_task].name + ":\n" + j.tasks[j.current_task].output_line), MessageBox.TYPE_ERROR)

	def jobcb(self, jobref, fasel, blubber):
		print "[jobcb] %s %s %s" % (jobref, fasel, blubber)
		self["key_green"].text = _("Flash")

	def reboot(self):
		if self.job.status == self.job.FINISHED:
			self["statusbar"].text = _("rebooting...")
			TryQuitMainloop(self.session,2)
			
	def createSummary(self):
		return NFISummary
