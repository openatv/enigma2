from Components.config import config, ConfigSubsection, ConfigText, configfile, getConfigListEntry, ConfigSelection
from Components.ConfigList import ConfigListScreen
from Components.MultiContent import MultiContentEntryText, MultiContentEntryPixmapAlphaBlend
from Components.MenuList import MenuList
from Components.Label import Label
from Screens.Screen import Screen
from Components.ActionMap import ActionMap
from Components.Sources.List import List
from Components.Sources.StaticText import StaticText
from Tools.LoadPixmap import LoadPixmap
from Tools.Directories import resolveFilename, SCOPE_CURRENT_PLUGIN, SCOPE_CURRENT_SKIN, fileExists
from Screens.MessageBox import MessageBox
from Screens.Console import Console
from enigma import *
import os
from Screens.CCcamInfo import CCcamInfoMain
from Screens.OScamInfo import OscamInfoMenu

def Check_Softcam():
	found = False
	for x in os.listdir('/etc'):
		if x.find('.emu') > -1:
			found = True
			break;
	return found

def command(comandline, strip=1):
	comandline = comandline + " >/tmp/command.txt"
	os.system(comandline)
	text = ""
	if os.path.exists("/tmp/command.txt") is True:
		file = open("/tmp/command.txt", "r")
		if strip == 1:
			for line in file:
				text = text + line.strip() + '\n'
		else:
			for line in file:
				text = text + line
				if text[-1:] != '\n': text = text + "\n"
		file.close()
	# if one or last line then remove linefeed
	if text[-1:] == '\n': text = text[:-1]
	comandline = text
	os.system("rm /tmp/command.txt")
	return comandline

#class EMUlist(MenuList):
#	def __init__(self, list=[], enableWrapAround = False):
#		MenuList.__init__(self, list, enableWrapAround, eListboxPythonMultiContent)
#		Schriftart = 22
#		self.l.setFont(0, gFont("Regular", Schriftart))
#		self.l.setItemHeight(24)

#	def moveSelection(self,idx=0):
#		if self.instance is not None:
#			self.instance.moveSelectionTo(idx)

SOFTCAM_SKIN = """<screen name="SoftcamPanel" position="center,center" size="500,450" title="Softcam Panel">
	<eLabel font="Regular;22" position="10,10" size="185,25" text="Softcam Selection:" />
	<widget font="Regular;18" name="camcount" position="420,10" size="60,25" />
	<widget name="config" position="10,100" size="400,100" />
	<eLabel backgroundColor="red" position="10,60" size="120,3" zPosition="0" />
	<eLabel backgroundColor="green" position="130,60" size="120,3" zPosition="0" />
	<eLabel backgroundColor="yellow" position="250,60" size="120,3" zPosition="0" />
	<eLabel backgroundColor="blue" position="370,60" size="120,3" zPosition="0" />
	<widget font="Regular;16" halign="center" name="key_red" position="10,62" size="120,35" transparent="1" valign="center" zPosition="2" />
	<widget font="Regular;16" halign="center" name="key_green" position="130,62" size="120,35" transparent="1" valign="center" zPosition="2" />
	<widget font="Regular;16" halign="center" name="key_yellow" position="250,62" size="120,35" transparent="1" valign="center" zPosition="2" />
	<widget font="Regular;16" halign="center" name="key_blue" position="370,62" size="120,35" transparent="1" valign="center" zPosition="2" />
	<eLabel backgroundColor="#56C856" position="0,199" size="500,1" zPosition="0" />
	<widget font="Regular;16" name="actifcam" position="10,205" size="220,32" />
	<widget font="Regular;16" name="actifcam2" position="250,205" size="220,32" />
	<eLabel backgroundColor="#56C856" position="0,225" size="500,1" zPosition="0" />
	<widget font="Regular;16" name="ecminfo" position="10,235" size="480,300" />
</screen>"""


REFRESH = 0
CCCAMINFO = 1
OSCAMINFO = 2

class SoftcamPanel(ConfigListScreen, Screen):
	def __init__(self, session):
		global emuDir
		emuDir = "/etc/"
		self.service = None
		Screen.__init__(self, session)

		self.skin = SOFTCAM_SKIN
		self.onShown.append(self.setWindowTitle)
		self.partyfeed = None
		self.YellowAction = REFRESH

		self.mlist = []
		self["key_green"] = Label(_("Restart"))
		self["key_red"] = Label(_("Stop"))
		self["key_yellow"] = Label(_("Refresh"))
		self.partyfeed = os.path.exists("/etc/opkg/3rdparty-feed.conf") or os.path.exists("/etc/opkg/3rd-party-feed.conf")
		if self.partyfeed:
			self["key_blue"]= Label(_("Install"))
		else:
			self["key_blue"]= Label(_("Exit"))
		self["ecminfo"] = Label(_("No ECM info"))
		self["actifcam"] = Label(_("no CAM 1 active"))
		self["actifcam2"] = Label(_("no CAM 2 active"))

		#// create listings
		self.emuDirlist = []
		self.emuList = []
		self.emuBin = []
		self.emuStart = []
		self.emuStop = []
		self.emuRgui = []
		self.emuDirlist = os.listdir(emuDir)
		self.ecmtel = 0
		self.first = 0
		global count
		count = 0
		#// check emu dir for config files
		print "************ go in the emuloop ************"
		for x in self.emuDirlist:
			#// if file contains the string "emu" (then this is a emu config file)
			if x.find("emu") > -1:
				self.emuList.append(emuDir + x)
				em = open(emuDir + x)
				self.emuRgui.append(0)
				#// read the emu config file
				for line in em.readlines():
					line1 = line
					#// startcam
					line = line1
					if line.find("startcam") > -1:
						line = line.split("=")
						self.emuStart.append(line[1].strip())

					#// stopcam
					line = line1
					if line.find("stopcam") > -1:
						line = line.split("=")
						self.emuStop.append(line[1].strip())

					#// Restart GUI
					line = line1
					if line.find("restartgui") > -1:
						self.emuRgui[count] = 1

					#// binname
					line = line1
					if line.find("binname") > -1:
						line = line.split("=")
						self.emuBin.append(line[1].strip())
					
				em.close()
				count += 1

		self.maxcount = count
		
		self.onChangedEntry = [ ]
		self.list = []
		ConfigListScreen.__init__(self, self.list, session = self.session, on_change = self.changedEntry)
		self.ReadMenu()
		self.createSetup()
		self["ecminfo"].show()

		self.read_shareinfo()
		self.Timer = eTimer()
		self.Timer.callback.append(self.layoutFinished)
		self.Timer.start(2000, True)
		#// get the remote buttons
		self["actions"] = ActionMap(["OkCancelActions", "DirectionActions", "ColorActions"],
		{
			"cancel": self.Exit,
			"ok": self.ok,
			"blue": self.Blue,
			"red": self.Red,
			"green": self.Green,
			"yellow": self.Yellow,
		}, -1)
		#// update screen
		self.onLayoutFinish.append(self.layoutFinished)

	def setWindowTitle(self):
		self.setTitle(_("Softcam Panel V2.0"))

	def ReadMenu(self):
		self.whichCam()
		
		for x in self.emuDirlist:
			#// if file contains the string "emu" (then this is a emu config file)
			if x.find("emu") > -1:
				self.emuList.append(emuDir + x)
				em = open(emuDir + x)
				self.emuRgui.append(0)
				#// read the emu config file
				for line in em.readlines():
					line1 = line
					#// emuname
					line = line1
					if line.find("emuname") > -1:
						line = line.split("=")
						self.mlist.append(line[1].strip())
						name = line[1].strip()
				em.close()

		emusel = [_('no cam')]
		for x in self.mlist:
			emusel.append(x)
		self.cam1sel = ConfigSelection(emusel)
		self.cam2sel = ConfigSelection(emusel)
		self.setYellowKey(self.curcam)

	def whichCam(self):
		#// check for active cam 1
		cam = config.softcam.actCam.value
		self.curcam = None
		self.curcamIndex = None
		if cam in self.mlist:
			index = self.mlist.index(cam)
			x = self.emuBin[index]
			if self.isCamrunning(x):
				self.curcam = x
				self.curcamIndex = index

		#// check for active cam 2		
		cam = config.softcam.actCam2.value
		self.curcam2 = None
		self.curcam2Index = None
		if cam in self.mlist:
			index = self.mlist.index(cam)
			x = self.emuBin[index]
			if self.isCamrunning(x):
				self.curcam2 = x
				self.curcam2Index = index

		if not self.curcam and not self.curcam2 and self.mlist:
			print "[SOFTCAMPANEL] try to find a running cam"
			for cam in self.emuBin:
				index = self.emuBin.index(cam)
				if self.isCamrunning(cam):
					self.curcam = cam
					self.curcamIndex = index
					camname = self.mlist[index]
					print"[SOFTCAMPANEL] found %s running" % camname
					self.Save_Settings(camname)
					break

	def createSetup(self):
		self.editListEntry = None
		self.list = []
		self.list.append(getConfigListEntry(_("Select Cam 1"), self.cam1sel))
		if len(self.emuStart) > 1:
			self["actifcam2"].show()
			if self.cam1sel.value != _('no cam') or config.softcam.actCam.value != _("no CAM 1 active"):
				self.list.append(getConfigListEntry(_("Select Cam 2"), self.cam2sel))
				if self.cam2sel.value != _('no cam'):
					self.list.append(getConfigListEntry(_("Wait time before start Cam 2"), config.softcam.waittime))
		else:
			self["actifcam2"].hide()
			self.cam2sel.setValue(_('no cam'))

		self["config"].list = self.list
		self["config"].setList(self.list)

	def setYellowKey(self, cam):
		if cam == None or cam == _('no cam'):
			self.YellowAction = REFRESH
			self["key_yellow"].setText(_("Refresh"))
			return
		if cam.upper().startswith('CCCAM'):
			self.YellowAction = CCCAMINFO
			self["key_yellow"].setText(_("CCcamInfo"))
		elif cam.upper().startswith('OSCAM'):
			self.YellowAction = OSCAMINFO
			self["key_yellow"].setText(_("OscamInfo"))
		else:
			self.YellowAction = REFRESH
			self["key_yellow"].setText(_("Refresh"))

	def selectionChanged(self):
		#self["status"].setText(self["config"].getCurrent()[0])
		pass

	def changedEntry(self):
		for x in self.onChangedEntry:
			x()
		self.selectionChanged()
		self.createSetup()

	def getCurrentEntry(self):
		return self["config"].getCurrent()[0]

	def getCurrentValue(self):
		return str(self["config"].getCurrent()[1].getText())

	def getCurrentDescription(self):
		return self["config"].getCurrent() and len(self["config"].getCurrent()) > 2 and self["config"].getCurrent()[2] or ""

	def layoutFinished(self):
		self.Timer.stop()
		if not Check_Softcam():
			self.Exit()
		#// check for active cam
		try:
			self.whichCam()
			global oldcamIndex, oldcam2Index
			oldcamIndex = -1
			oldcam2Index = -1
			tel = 0

			if self.curcam:
				oldcamIndex = self.curcamIndex
				actcam = self.mlist[oldcamIndex]
				if self.first == 0:
					self.cam1sel.setValue(actcam)		
				self["key_green"].setText(_("Restart"))
				self["actifcam"].setText(_("active CAM 1: ") + actcam )
				print '[SOFTCAM] set active cam 1 to: ' + actcam
			else:
				actcam = _("no CAM 1 active")
				self["actifcam"].setText(actcam)
		
			if self.curcam2:
				oldcam2Index = self.curcam2Index
				actcam = self.mlist[oldcam2Index]
				if self.first == 0:
					self.cam2sel.setValue(actcam)
				self["actifcam2"].setText(_("active CAM 2: ") + actcam )
				print '[SOFTCAM] set active cam 2 to: ' + actcam
			else:
				actcam2 = _("no CAM 2 active")
				self["actifcam2"].setText(actcam2)

			if self.first == 0: # Only update first time or when refresh button was pressed
				self.createSetup()
				self.first = 1

			#// CAM IS NOT RUNNING
			if not self.curcam and not self.curcam2:
				self["key_green"].setText(_("Start"))
				self.YellowAction = REFRESH
				self["key_yellow"].setText(_("Refresh"))
				if os.path.exists('/tmp/ecm.info') is True:
					os.system("rm /tmp/ecm.info")
				if os.path.exists('/tmp/ecm0.info') is True:
					os.system("rm /tmp/ecm0.info")

		except:
			pass

		if self["config"].getCurrent()[0] == _("Select Cam 1"):
			self.setYellowKey(self.curcam)
		else:
			self.setYellowKey(self.curcam2)
		
		#// read ecm.info
		ecmi = ""
		if os.path.exists('/tmp/ecm.info') is True:
			ecmi = self.read_ecm('/tmp/ecm.info')
		elif os.path.exists('/tmp/ecm1.info') is True:
			ecmi = self.read_ecm('/tmp/ecm1.info')
		else:
			ecmi = _("No ECM info")
		ecmold = self["ecminfo"].getText()
		if ecmold == ecmi:
			self.ecmtel += 1
			if self.ecmtel > 5:
				ecmi = _("No new ECM info")
		else:
			self.ecmtel = 0
		self["ecminfo"].setText(ecmi)
		self.Timer.start(2000, True)		#reset timer

	def read_shareinfo(self):
		#// read share.info and put in list
		self.shareinfo =[]
		if os.path.exists('/tmp/share.info') is True:
			s = open('/tmp/share.info')
			for x in s.readlines():
				self.shareinfo.append(x)
			s.close()

	def read_ecm(self, ecmpath):
		#// read ecm.info and check for share.info
		ecmi2 = ''
		Caid = ''
		Prov = ''
		f = open(ecmpath)
		for line in f.readlines():
			line= line.replace('=', '')
			line= line.replace(' ', '', 1)
			#// search CaID
			if line.find('ECM on CaID') > -1:
				k = line.find('ECM on CaID') + 14
				Caid = line[k:k+4]
			#// search Boxid
			if line.find('prov:') > -1:
				tmpprov = line.split(':')
				Prov = tmpprov[1].strip()
				#// search peer in share.info only if share.info exists
				if Caid <> '' and Prov <> '' and len(self.shareinfo) > 0 :
					for x in self.shareinfo:
						cel = x.split(' ')
						#// search Boxid and Caid
						if cel[5][0:4] == Caid and cel[9][3:7] == Prov:
							line = 'Peer: ' + Prov + ' - ' + cel[3] + ' - ' + cel[8] + '\n'
							break
			ecmi2 = ecmi2 + line
		f.close()
		return ecmi2


	def Red(self):
		#// Stopping the CAM when pressing the RED button
		self.Timer.stop()
		self.Stopcam()
		self.Timer.start(2000, True)		#reset timer

	def Yellow(self):
		if self.YellowAction == CCCAMINFO:
			self.Timer.stop()
			self.session.openWithCallback(self.ShowSoftcamCallback, CCcamInfoMain)
		elif self.YellowAction == OSCAMINFO:
			self.Timer.stop()
			self.session.openWithCallback(self.ShowSoftcamCallback, OscamInfoMenu)
		else:
			self.first = 0
			self.layoutFinished()

	def Green(self):
		#// Start the CAM when pressing the GREEN button
		self.Timer.stop()
		self.Startcam()
		self.Timer.start(2000, True)		#reset timer

	def Exit(self):
		self.Timer.stop()
		self.close()
		
	def Blue(self):
		if not self.partyfeed:
			self.Exit()
		else:
			self.Timer.stop()
			self.session.openWithCallback(self.ShowSoftcamCallback, ShowSoftcamPackages)

	def ShowSoftcamCallback(self):
		self.Timer.start(2000, True)

	def ok(self):
		#// Exit Softcam when pressing the OK button
		self.Timer.stop()
		self.Startcam()
		if self.YellowAction == REFRESH:
			self.Yellow()
		self.Timer.start(2000, True)		#reset timer

	def Stopcam(self):
		#// Stopping the CAM
		global oldcamIndex, oldcam2Index
		if oldcamIndex >= 0:
			oldcam = self.emuBin[oldcamIndex]
		else:
			oldcam = None
		if oldcam2Index >= 0:
			oldcam2 = self.emuBin[oldcam2Index]
		else:
			oldcam2 = None
		import time
		self.container = eConsoleAppContainer()

		if config.softcam.camstartMode.value == "0" or not fileExists('/etc/init.d/softcam'):
			if oldcam:
				print '[SOFTCAM] Python stop cam 1: ' + oldcam
				self.container.execute(self.emuStop[oldcamIndex])

				time.sleep(1) # was 5sec
				t = 0
				while t < 5:
					p = command('pidof %s |wc -w' % oldcam )
					if not p.isdigit(): p=0
					if int(p) > 0:
						self.container = eConsoleAppContainer()
						self.container.execute('killall -9 ' + oldcam)
						t += 1
						time.sleep(1)
					else:
						t = 5

			if oldcam2:
				print '[SOFTCAM] Python stop cam 2: ' + oldcam2
				self.container.execute(self.emuStop[oldcam2Index])

				time.sleep(1) # was 5sec
				t = 0
				while t < 5:
					p = command('pidof %s |wc -w' % oldcam2 )
					if not p.isdigit(): p=0
					if int(p) > 0:
						self.container = eConsoleAppContainer()
						self.container.execute('killall -9 ' + oldcam2)
						t += 1
						time.sleep(1)
					else:
						t = 5

		else:
			self.container.execute('/etc/init.d/softcam.cam1 stop')
			self.container.execute('/etc/init.d/softcam.cam2 stop')

		if os.path.exists('/tmp/ecm.info') is True:
			os.system("rm /tmp/ecm.info")
		actcam = _("no CAM 1 active")
		actcam2 = _("no CAM 2 active")
		self["actifcam"].setText(actcam)
		self["actifcam2"].setText(actcam2)
		self["key_green"].setText(_("Start"))
		self["ecminfo"].setText(_("No ECM info"))
		self.Save_Settings(actcam)
		self.Save_Settings2(actcam2)

	def Startcam(self):
		#// Starting the CAM
		try:
			if count > 0:
				if self.cam1sel.value == self.cam2sel.value:
					self.session.openWithCallback(self.doNothing, MessageBox, _("No Cam started !!\n\nCam 1 must be different from Cam 2"), MessageBox.TYPE_ERROR, simple=True)
					return
				if config.softcam.camstartMode.value == "0":
					self.Stopcam()

				self.camIndex = self.cam1sel.getIndex() -1
				self.cam2Index = self.cam2sel.getIndex() - 1
				if self.camIndex >= 0:
					actcam = self.cam1sel.value
					self["actifcam"].setText(_("active CAM 1: ") + actcam)
					self.Save_Settings(actcam)
					start = self.emuStart[self.camIndex]
					if self.checkBinName(self.emuBin[self.camIndex], start):
						self.session.openWithCallback(self.startcam2, MessageBox, actcam + _(" Not Started !!\n\nCam binname must be in the start command line\nCheck your emu config file"), MessageBox.TYPE_ERROR, simple=True)
						return
					if config.softcam.camstartMode.value == "0":
						print '[SOFTCAM] Python start cam 1: ' + actcam
						self.session.openWithCallback(self.waitTime, MessageBox, _("Starting Cam 1: ") + actcam, MessageBox.TYPE_WARNING, timeout=5, simple=True)
						self.container = eConsoleAppContainer()
						self.container.execute(start)
					else:
						# Create INIT.D start
						self.session.openWithCallback(self.doNothing, MessageBox, _("Creating start scripts and starting the cam"), MessageBox.TYPE_WARNING, timeout=10, simple=True)
						self.Save_Settings2(self.cam2sel.value)

						camname1 = self.emuBin[self.camIndex]
						camname2 = self.emuBin[self.cam2Index]
						self.deleteInit()
						camname = "/usr/bin/" + camname1
						startcmd = self.emuStart[self.camIndex]
						stopcmd = self.emuStop[self.camIndex]							
						self.createInitdscript("cam1", camname, startcmd, stopcmd)
						if self.cam2Index >= 0:
							camname = "/usr/bin/" + camname2
							startcmd = self.emuStart[self.cam2Index]
							stopcmd = self.emuStop[self.cam2Index]							
							self.createInitdscript("cam2", camname, startcmd, stopcmd, config.softcam.waittime.value)

					self["key_green"].setText(_("Restart"))

		except:
			pass

	def waitTime(self, ret):
		if self.cam2Index >= 0:
			if config.softcam.waittime.value == '0':
				self.startcam2(None)
			else:
				self.session.openWithCallback(self.startcam2, MessageBox, _("Waiting..."), MessageBox.TYPE_WARNING, timeout=int(config.softcam.waittime.value), simple=True)

	def doNothing(self, ret):
		pass

	def startcam2(self, ret):
		camIndex = self.cam2Index
		if camIndex >= 0:
			actcam = self.cam2sel.value
			self["actifcam2"].setText(_("active CAM 2: ") + actcam)
			self.Save_Settings2(actcam)
			start = self.emuStart[camIndex]
			if self.checkBinName(self.emuBin[self.cam2Index], start):
					self.session.open(MessageBox, actcam + _(" Not Started !!\n\nCam binname must be in the start command line\nCheck your emu config file"), MessageBox.TYPE_ERROR, simple=True)
					return
			print '[SOFTCAM] Python start cam 2: ' + actcam
			self.session.open(MessageBox, _("Starting Cam 2: ") + actcam, MessageBox.TYPE_WARNING, timeout=5, simple=True)
			self.container = eConsoleAppContainer()
			self.container.execute(start)

	def Save_Settings(self, cam_name):
		#// Save Came Name to Settings file
		config.softcam.actCam.setValue(cam_name)
		config.softcam.save()
		configfile.save()

	def Save_Settings2(self, cam_name):
		#// Save Came Name to Settings file
		config.softcam.actCam2.setValue(cam_name)
		config.softcam.save()
		configfile.save()

	def isCamrunning(self, cam):
		p = command('pidof ' + cam + ' |wc -w')
		if not p.isdigit(): p=0
		if int(p) > 0:
			return True
		else:
			return False

	def checkBinName(self, binname, start):
		print "[CHECKBINNAME] bin=%s ,start=%s" %(binname,start)
		if start.find(binname + ' ') > -1:
			print "[CHECKBINNAME] OK"
			return False
		else:
			if start[start.rfind('/')+1:] == binname:
				print "[CHECKBINNAME] OK"
				return False
			else:
				print "[CHECKBINNAME] ERROR"
				return True

	def createInitdscript(self, camname, emubin, start, stop, wait=None):
		Adir = "/etc/init.d/softcam." + camname
		softcamfile = []
		softcamfile.append('#!/bin/sh')
		softcamfile.append('DAEMON=%s' % emubin)
		softcamfile.append('STARTCAM="%s"' % start)
		softcamfile.append('STOPCAM="%s"' % stop)
		softcamfile.append('DESC="Softcam"')
		softcamfile.append('')
		softcamfile.append('test -f $DAEMON || exit 0')
		softcamfile.append('set -e')
		softcamfile.append('')
		softcamfile.append('case "$1" in')
		softcamfile.append('	start)')
		softcamfile.append('		echo -n "starting $DESC: $DAEMON... "')
		if wait:
			softcamfile.append('		sleep ' + wait)
		softcamfile.append('		$STARTCAM')
		softcamfile.append('		echo "done."')
		softcamfile.append('		;;')
		softcamfile.append('	stop)')
		softcamfile.append('		echo -n "stopping $DESC: $DAEMON... "')
		softcamfile.append('		$STOPCAM')
		softcamfile.append('		echo "done."')
		softcamfile.append('		;;')
		softcamfile.append('	restart)')
		softcamfile.append('		echo "restarting $DESC: $DAEMON... "')
		softcamfile.append('		$0 stop')
		softcamfile.append('		echo "wait..."')
		softcamfile.append('		sleep 5')
		softcamfile.append('		$0 start')
		softcamfile.append('		echo "done."')
		softcamfile.append('		;;')
		softcamfile.append('	*)')
		softcamfile.append('		echo "Usage: $0 {start|stop|restart}"')
		softcamfile.append('		exit 1')
		softcamfile.append('		;;')
		softcamfile.append('esac')
		softcamfile.append('')
		softcamfile.append('exit 0')

		f = open( Adir, "w" )
		for x in softcamfile:
			f.writelines(x + '\n')
		f.close()

		self.container = eConsoleAppContainer()
		# Set execute rights
		os.chmod(Adir,0755)
		# Create symbolic link for startup
		if not os.path.exists("/etc/rc2.d/S20softcam." + camname):
			self.container.execute('update-rc.d -f softcam.' + camname + ' defaults')
		# Wait a few seconds
		import time
		time.sleep (3) 

		# Start cam
		if self.isCamrunning(emubin):
			self.container.execute('/etc/init.d/softcam.' + camname + ' restart')
		else:
			self.container.execute('/etc/init.d/softcam.' + camname + ' start')

	def deleteInit(self):
		if os.path.exists("/etc/rc2.d/S20softcam.cam1"):
			print "Delete Symbolink link"
			self.container = eConsoleAppContainer()
			self.container.execute('update-rc.d -f softcam.cam1 defaults')
		if os.path.exists("/etc/init.d/softcam.cam1"):
			print "Delete softcam init script cam1"
			os.system("rm /etc/init.d/softcam.cam1")
			
		if os.path.exists("/etc/rc2.d/S20softcam.cam2"):
			print "Delete Symbolink link"
			self.container = eConsoleAppContainer()
			self.container.execute('update-rc.d -f softcam.cam2 defaults')
		if os.path.exists("/etc/init.d/softcam.cam2"):
			print "Delete softcam init script cam2"
			os.system("rm /etc/init.d/softcam.cam2")

class ShowSoftcamPackages(Screen):
	skin = """
		<screen name="ShowSoftcamPackages" position="center,center" size="630,500" title="Install Softcams" >
			<ePixmap pixmap="skin_default/buttons/red.png" position="0,0" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/green.png" position="140,0" size="140,40" alphatest="on" />
			<widget source="key_red" render="Label" position="0,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" transparent="1" />
			<widget source="key_green" render="Label" position="140,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" transparent="1" />
			<widget source="key_ok" render="Label" position="240,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" transparent="1" />
			<widget source="list" render="Listbox" position="5,50" size="620,420" scrollbarMode="showOnDemand">
				<convert type="TemplatedMultiContent">
					{"template": [
							MultiContentEntryText(pos = (5, 1), size = (540, 28), font=0, flags = RT_HALIGN_LEFT, text = 0), # index 0 is the name
							MultiContentEntryText(pos = (5, 26), size = (540, 20), font=1, flags = RT_HALIGN_LEFT, text = 2), # index 2 is the description
							MultiContentEntryPixmapAlphaBlend(pos = (545, 2), size = (48, 48), png = 4), # index 4 is the status pixmap
							MultiContentEntryPixmapAlphaBlend(pos = (5, 50), size = (510, 2), png = 5), # index 4 is the div pixmap
						],
					"fonts": [gFont("Regular", 22),gFont("Regular", 14)],
					"itemHeight": 52
					}
				</convert>
			</widget>
		</screen>"""
	
	def __init__(self, session, args = None):
		Screen.__init__(self, session)
		self.session = session
		
		self["actions"] = ActionMap(["OkCancelActions", "DirectionActions", "ColorActions"],
		{
			"red": self.exit,
			"ok": self.go,
			"cancel": self.exit,
			"green": self.startupdateList,
		}, -1)
		
		self.list = []
		self.statuslist = []
		self["list"] = List(self.list)
		self["key_red"] = StaticText(_("Close"))
		self["key_green"] = StaticText(_("Reload"))
		self["key_ok"] = StaticText(_("Install"))

		self.oktext = _("\nPress OK on your remote control to continue.")
		self.onShown.append(self.setWindowTitle)
		self.setStatus('list')
		self.Timer1 = eTimer()
		self.Timer1.callback.append(self.rebuildList)
		self.Timer1.start(1000, True)
		self.Timer2 = eTimer()
		self.Timer2.callback.append(self.updateList)

	def go(self, returnValue = None):
		cur = self["list"].getCurrent()
		if cur:
			status = cur[3]
			self.package = cur[2]
			if status == "installable":
				self.session.openWithCallback(self.runInstall, MessageBox, _("Do you want to install the package:\n") + self.package + "\n" + self.oktext)

	def runInstall(self, result):
		if result:
			self.session.openWithCallback(self.runInstallCont, Console, cmdlist = ['opkg install ' + self.package], closeOnSuccess = True)

	def runInstallCont(self):
			ret = command('opkg list-installed | grep ' + self.package + ' | cut -d " " -f1')

			if ret != self.package:
				self.session.open(MessageBox, _("Install Failed !!"), MessageBox.TYPE_ERROR, timeout = 10)
			else:
				self.session.open(MessageBox, _("Install Finished."), MessageBox.TYPE_INFO, timeout = 10)
				self.setStatus('list')
				self.Timer1.start(1000, True)

	def UpgradeReboot(self, result):
		if result is None:
			return
		
	def exit(self):
		self.close()
			
	def setWindowTitle(self):
		self.setTitle(_("Install Softcams"))

	def setStatus(self,status = None):
		if status:
			self.statuslist = []
			divpng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_CURRENT_SKIN, "skin_default/div-h.png"))
			if status == 'update':
				statuspng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_CURRENT_PLUGIN, "Extensions/Infopanel/icons/upgrade.png"))
				self.statuslist.append(( _("Package list update"), '', _("Trying to download a new updatelist. Please wait..." ),'', statuspng, divpng ))
				self['list'].setList(self.statuslist)
			if status == 'list':
				statuspng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_CURRENT_PLUGIN, "Extensions/Infopanel/icons/upgrade.png"))
				self.statuslist.append(( _("Package list"), '', _("Getting Softcam list. Please wait..." ),'', statuspng, divpng ))
				self['list'].setList(self.statuslist)
			elif status == 'error':
				statuspng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_CURRENT_PLUGIN, "Extensions/Infopanel/icons/remove.png"))
				self.statuslist.append(( _("Error"), '', _("There was an error downloading the updatelist. Please try again." ),'', statuspng, divpng ))
				self['list'].setList(self.statuslist)				

	def startupdateList(self):
		self.setStatus('update')
		self.Timer2.start(1000, True)

	def updateList(self):
		self.container = eConsoleAppContainer()
		self.container.appClosed.append(self.doneupdateList)
		self.setStatus('list')
		self.container.execute('opkg update')

	def doneupdateList(self, answer):
		self.container.appClosed.remove(self.doneupdateList)
		self.Timer1.start(1000, True)

	def rebuildList(self):
		self.list = []
		self.Flist = []
		self.Elist = []
		t = command('opkg list | grep "enigma2-plugin-softcams-"')
		self.Flist = t.split('\n')
		tt = command('opkg list-installed | grep "enigma2-plugin-softcams-"')
		self.Elist = tt.split('\n')

		if len(self.Flist) > 0:
			self.buildPacketList()
		else:
			self.setStatus('error')

	def buildEntryComponent(self, name, version, description, state):
		divpng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_CURRENT_SKIN, "skin_default/div-h.png"))
		if not description:
			description = ""
		installedpng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_CURRENT_PLUGIN, "Extensions/Infopanel/icons/installed.png"))
		return((name, version, _(description), state, installedpng, divpng))

	def buildPacketList(self):
		fetchedList = self.Flist
		excludeList = self.Elist

		if len(fetchedList) > 0:
			for x in fetchedList:
				x_installed = False
				Fx = x.split(' - ')
				try:
					if Fx[0].find('-softcams-') > -1:
						for exc in excludeList:
							Ex = exc.split(' - ')
							if Fx[0] == Ex[0]:
								x_installed = True
								break
						if x_installed == False:
							self.list.append(self.buildEntryComponent(Fx[2], Fx[1], Fx[0], "installable"))
				except:
					pass

			self['list'].setList(self.list)
	
		else:
			self.setStatus('error')