from Components.config import config, ConfigSubsection, ConfigText, configfile
from Components.MultiContent import MultiContentEntryText, MultiContentEntryPixmapAlphaTest
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
    file.close
  # if one or last line then remove linefeed
  if text[-1:] == '\n': text = text[:-1]
  comandline = text
  os.system("rm /tmp/command.txt")
  return comandline

class EMUlist(MenuList):
	def __init__(self, list=[], enableWrapAround = False):
		MenuList.__init__(self, list, enableWrapAround, eListboxPythonMultiContent)
		Schriftart = 22
		self.l.setFont(0, gFont("Regular", Schriftart))
		self.l.setItemHeight(24)

	def moveSelection(self,idx=0):
		if self.instance is not None:
			self.instance.moveSelectionTo(idx)

SOFTCAM_SKIN = """<screen name="SoftcamPanel" position="center,center" size="500,450" title="Softcam Panel">
	<eLabel font="Regular;22" position="10,10" size="185,25" text="Softcam Selection:" />
	<widget font="Regular;18" name="camcount" position="420,10" size="60,25" />
	<widget name="Mlist" position="200,10" size="200,25" />
	<widget font="Regular;22" name="enigma2" position="10,10" size="185,25" />
	<eLabel backgroundColor="red" position="10,60" size="120,3" zPosition="0" />
	<eLabel backgroundColor="green" position="130,60" size="120,3" zPosition="0" />
	<eLabel backgroundColor="yellow" position="250,60" size="120,3" zPosition="0" />
	<eLabel backgroundColor="blue" position="370,60" size="120,3" zPosition="0" />
	<widget font="Regular;16" halign="center" name="key_red" position="10,62" size="120,35" transparent="1" valign="center" zPosition="2" />
	<widget font="Regular;16" halign="center" name="key_green" position="130,62" size="120,35" transparent="1" valign="center" zPosition="2" />
	<widget font="Regular;16" halign="center" name="key_yellow" position="250,62" size="120,35" transparent="1" valign="center" zPosition="2" />
	<widget font="Regular;16" halign="center" name="key_blue" position="370,62" size="120,35" transparent="1" valign="center" zPosition="2" />
	<eLabel backgroundColor="#56C856" position="0,99" size="500,1" zPosition="0" />
	<widget font="Regular;22" name="actifcam" position="10,100" size="480,32" />
	<eLabel backgroundColor="#56C856" position="0,133" size="500,1" zPosition="0" />
	<widget font="Regular;16" name="ecminfo" position="10,140" size="480,300" />
	<widget name="emulist" position="160,160" size="190,245" scrollbarMode="showOnDemand" />
</screen>"""

config.softcam = ConfigSubsection()
config.softcam.actCam = ConfigText(visible_width = 200)

REFRESH = 0
CCCAMINFO = 1
OSCAMINFO = 2

class SoftcamPanel(Screen):
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
		self["Mlist"] = MenuList(self.mlist)
		#// set the label text
		self["key_green"] = Label(_("Restart"))
		self["key_red"] = Label(_("Stop"))
		self["key_yellow"] = Label(_("Refresh"))
		self.partyfeed = os.path.exists("/etc/opkg/3rd-party-feed.conf")
		if self.partyfeed:
			self["key_blue"]= Label(_("Install"))
		else:
			self["key_blue"]= Label(_("Exit"))
		self["ecminfo"] = Label(_("No ECM info"))
		self["camcount"] = Label("(0/0)")
		self["actifcam"] = Label(_("no CAM active"))
		self["enigma2"] = Label("")
		self["emulist"] = EMUlist([0,(eListboxPythonMultiContent.TYPE_TEXT, 0, 0,250, 30, 0, RT_HALIGN_LEFT|RT_VALIGN_CENTER, "EMU not found")])

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
					#// emuname
					line = line1
					if line.find("startcam") > -1:
						line = line.split("=")
						self.emuStart.append(line[1].strip())
						#print  '[SOFTCAM] startcam: ' + line[1].strip()

					#// stopcam
					line = line1
					if line.find("stopcam") > -1:
						line = line.split("=")
						self.emuStop.append(line[1].strip())
						#print  '[SOFTCAM] stopcam: ' + line[1].strip()

					#// Restart GUI
					line = line1
					if line.find("restartgui") > -1:
						self.emuRgui[count] = 1
						#print  '[SOFTCAM] emuname: ' + line[1].strip()

					#// binname
					line = line1
					if line.find("binname") > -1:
						line = line.split("=")
						self.emuBin.append(line[1].strip())
						#print  '[SOFTCAM] binname: ' + line[1].strip()
					#// startcam
				em.close()
				count += 1
				self["camcount"].setText("(1/" + str(count) + ")")

		self.maxcount = count
		self.ReadMenu()

		self["emulist"].hide()
		self["Mlist"].show()
		self["ecminfo"].show()
		self.focus = "ml"

		self.read_shareinfo()
		self.Timer = eTimer()
		self.Timer.callback.append(self.layoutFinished)
		self.Timer.start(2000, True)
		#// get the remote buttons
		self["actions"] = ActionMap(["OkCancelActions", "DirectionActions", "ColorActions"],
		{
			"cancel": self.Exit,
			"left": self.left,
			"right": self.right,
			"up": self.up,
			"down": self.down,
			"ok": self.ok,
			"blue": self.Blue,
			"red": self.Red,
			"green": self.Green,
			"yellow": self.Yellow,
		}, -1)
		#// update screen
		self.onLayoutFinish.append(self.layoutFinished)

	def setWindowTitle(self):
		self.setTitle(_("Softcam Panel V1.0"))

	def ReadMenu(self):
		self.whichCam()
		self.fileresultlist = []
		for x in self.emuDirlist:
			#// if file contains the string "emu" (then this is a emu config file)
			if x.find("emu") > -1:
				self.emuList.append(emuDir + x)
				em = open(emuDir + x)
				self.emuRgui.append(0)
				#// read the emu config file
				for line in em.readlines():
					farbwahl = 16777215  # weiss
					line1 = line
					#// emuname
					line = line1
					if line.find("emuname") > -1:
						line = line.split("=")
						self.mlist.append(line[1].strip())
						name = line[1].strip()
						print "current CAM" + self.curcam
						if self.curcam == name:
							farbwahl = 65280  # print in green
						entry = [[name],(eListboxPythonMultiContent.TYPE_TEXT, 0, 0,250, 30, 0, RT_HALIGN_LEFT|RT_VALIGN_CENTER, name, farbwahl)]
						print "adding to feedlist: " + str(entry), farbwahl
						self.fileresultlist.append(entry)
				em.close()
		self["emulist"].l.setList(self.fileresultlist)
		camIndex = self["Mlist"].getSelectedIndex()
		self["emulist"].moveSelection(0)

	def whichCam(self):
			#// check for active cam
			self.curcam = ""
			for x in self.emuBin:
				p = command('pidof ' + x + ' |wc -w')
				if not p.isdigit(): p=0
				if int(p) > 0:
					self.curcam = x
					break

	def layoutFinished(self):
		self.Timer.stop()
		if not Check_Softcam():
			self.Exit()
		#// check for active cam
		try:
			global oldcamIndex
			oldcamIndex = 0
			tel = 0
			camrunning = 0
			for x in self.emuBin:
				print '[SOFTCAM] searching active cam: ' + x
				p = command('pidof ' + x + ' |wc -w')
				if not p.isdigit(): p=0
				if int(p) > 0:
					oldcamIndex = tel
					if self.first == 0: # Only update first time or when refresh button was pressed
						self["Mlist"].moveToIndex(tel)
						self["emulist"].moveToIndex(tel)
						actcam = self.mlist[tel]

					self["camcount"].setText("(" + str(tel + 1) + "/" + str(count) + ")")
					self["key_green"].setText(_("Restart"))
					self.Save_Settings(actcam)
					self["actifcam"].setText(_("active CAM: ") + actcam )
					print  '[SOFTCAM] set active cam to: ' + actcam
					self.Label_restart_Enigma2(tel)
					camrunning = 1
					if actcam.upper().startswith('CCCAM'):
						self.YellowAction = CCCAMINFO
						self["key_yellow"].setText(_("CCcamInfo"))
					elif actcam.upper().startswith('OSCAM'):
						self.YellowAction = OSCAMINFO
						self["key_yellow"].setText(_("OscamInfo"))
					else:
						self.YellowAction = REFRESH
						self["key_yellow"].setText(_("Refresh"))
					break
				else:
					tel +=1
			#// CAM IS NOT RUNNING
			if camrunning == 0:
				actcam = _("no CAM active")
				self["actifcam"].setText(actcam )
				self["key_green"].setText(_("Start"))
				self.YellowAction = REFRESH
				self["key_yellow"].setText(_("Refresh"))
				if os.path.exists('/tmp/ecm.info') is True:
					os.system("rm /tmp/ecm.info")
				if os.path.exists('/tmp/ecm0.info') is True:
					os.system("rm /tmp/ecm0.info")
				self.Save_Settings(actcam)
				self.Label_restart_Enigma2(tel)
			self.first = 1
		except:
			pass
		
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

	def up(self):
		print "you pressed up"
		self.Timer.stop()
		self["emulist"].show()
		self["Mlist"].hide()
		self["ecminfo"].hide()
		self.focus = "em"
		print "Count=" + str(count)
		curentIndex = self["Mlist"].getSelectedIndex()
		print "CurentIndex=" + str(curentIndex)
		if count > 0 and curentIndex >0:
			self["emulist"].up()
			self["Mlist"].up()
			camIndex = self["Mlist"].getSelectedIndex()
			#camIndex = self["emulist"].getSelectedIndex()
			self["camcount"].setText("(" + str(camIndex + 1 )+ "/" + str(count) + ")")
			self.Label_restart_Enigma2(camIndex)

	def down(self):
		print "you pressed down"
		self.Timer.stop()
		self["emulist"].show()
		self["Mlist"].hide()
		self["ecminfo"].hide()
		self.focus = "em"
		print "Count=" + str(count)
		curentIndex = self["Mlist"].getSelectedIndex()
		if count > 0 and (curentIndex + 1)  < count:
			self["emulist"].down()
			self["Mlist"].down()
			camIndex = self["Mlist"].getSelectedIndex()
			#camIndex = self["emulist"].getSelectedIndex()
			self["camcount"].setText("(" + str(camIndex + 1 )+ "/" + str(count) + ")")
			self.Label_restart_Enigma2(camIndex)

	def ShowEmuList(self):
		self["emulist"].hide()
		self["Mlist"].show()
		self["ecminfo"].show()
		self.focus = "ml"

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
			self.ShowEmuList()
			self.first = 0
			self.layoutFinished()

	def Green(self):
		#// Start the CAM when pressing the GREEN button
		self.ShowEmuList()
		self.Timer.stop()
		self.Startcam()
		self.Timer.start(2000, True)		#reset timer


	def left(self):
		#// Go to the previous CAM in list
		self["emulist"].hide()
		self["Mlist"].show()
		self["ecminfo"].show()
		self.focus = "ml"
		curentIndex = self["Mlist"].getSelectedIndex()
		if count > 0 and curentIndex >0:
			global camIndex
			self["Mlist"].up()
			self["emulist"].up()
			camIndex = self["Mlist"].getSelectedIndex()
			self["camcount"].setText("(" + str(camIndex + 1 )+ "/" + str(count) + ")")
			self.Label_restart_Enigma2(camIndex)

	def right(self):
		#// Go to the next CAM in list
		self["emulist"].hide()
		self["Mlist"].show()
		self["ecminfo"].show()
		self.focus = "ml" # which list is active
		curentIndex = self["Mlist"].getSelectedIndex()
		if count > 0 and (curentIndex + 1)  < count:
			global camIndex
			self["Mlist"].down()
			self["emulist"].down()
			camIndex = self["Mlist"].getSelectedIndex()
			#	camIndex = self["Mlist"].getSelectedIndex()
			self["camcount"].setText("(" + str(camIndex + 1 )+ "/" + str(count) + ")")
			self.Label_restart_Enigma2(camIndex)

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
		self.ShowEmuList()
		self.Timer.stop()
		self.Startcam()
		if self.YellowAction == REFRESH:
			self.Yellow()
		self.Timer.start(2000, True)		#reset timer

	def Stopcam(self):
		#// Stopping the CAM
		self.ShowEmuList()
		global oldcamIndex
		oldcam = self.emuBin[oldcamIndex]
		import time
		self.container = eConsoleAppContainer()

		if config.softcam.camstartMode.getValue() == "0" or not fileExists('/etc/init.d/softcam'):
			print  '[SOFTCAM] Python stop cam: ' + oldcam
			self.container.execute(self.emuStop[oldcamIndex])
		
			# check if incubus_watch runs
			p = command('pidof incubus_watch |wc -w')
			if not p.isdigit(): p=0
			if int(p) > 0:
				# stop incubus_watch
				print '[SOFTCAM] stop incubus_watch'
				self.container = eConsoleAppContainer()
				self.container.execute('killall -9 incubus_watch')
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
		else:
			print  '[SOFTCAM] init.d stop cam: ' + oldcam
			self.container.execute('/etc/init.d/softcam stop')

		if os.path.exists('/tmp/ecm.info') is True:
			os.system("rm /tmp/ecm.info")
		actcam = _("no CAM active")
		self["actifcam"].setText(actcam)
		self["key_green"].setText(_("Start"))
		self["ecminfo"].setText(_("No ECM info"))
		self.Save_Settings(actcam)

	def Startcam(self):
		#// Starting the CAM
		print "count=",count
		try:
			if count > 0:
				if config.softcam.camstartMode.getValue() == "0":
					self.Stopcam()
				global camIndex
				camIndex = self["Mlist"].getSelectedIndex()
				print "camindex", camIndex
				actcam = self.mlist[camIndex]
				#print  '[SOFTCAM ml] start cam: ' + actcam
				self["actifcam"].setText(_("active CAM: ") + actcam)
				emustart = self.emuStart[camIndex][self.emuStart[camIndex].find(self.emuBin[camIndex]):]
				print emustart
				self.Save_Settings(actcam)
				start = self.emuStart[camIndex]
				if config.softcam.camstartMode.getValue() == "0":
					print  '[SOFTCAM] Python start cam: ' + actcam
					import time
					time.sleep (1) # was 5sec
					if self.emuRgui[camIndex] == 0:
						kk = start.find(';')
						if kk >-1:
							print "[SOFTCAM] starting two cam's"
							emu1 = start[0:kk]
							emu2 = start[kk+1:]
							print "[SOFTCAM] starting cam 1 " + emu1
							self.container = eConsoleAppContainer()
							self.container.execute(emu1)
							time.sleep (5)
							print "[SOFTCAM] starting cam 2 " + emu2
							self.container = eConsoleAppContainer()
							self.container.execute(emu2)
						else:
							self.container = eConsoleAppContainer()
							self.container.execute(start)
					else:
						self.session.open(MessageBox, "Prepairing " + actcam + " to start\n\n" + "Restarting Enigma2", MessageBox.TYPE_WARNING)
						TryQuitMainloop(self.session, 2)
				else:
					print  '[SOFTCAM] init.d start cam: ' + actcam
					self.createInitdscript("/usr/bin/" + self.emuBin[camIndex], self.emuStart[camIndex], self.emuStop[camIndex])

				self["key_green"].setText(_("Restart"))
				self.ReadMenu()
		except:
			pass

	def Save_Settings(self, cam_name):
		#// Save Came Name to Settings file
		config.softcam.actCam.setValue(cam_name)
		config.softcam.save()
		configfile.save()

	def Label_restart_Enigma2(self, index):
		#// Display warning when Enigma2 restarts with Cam
		if self.emuRgui[index] == 0:
			self["enigma2"].setText("")
		else:
			self["enigma2"].setText("Enigma2 restarts with cam")

	def read_startconfig(self, item):
		Adir = "/var/etc/autostart/start-config"
		be = []
		if os.path.exists(Adir) is True:
			f = open( Adir, "r" )
			be = f.readlines()
			f.close
			for line in be:
				if line.find(item) > -1:
					k = line.split("=")
					if k[1][:-1] == "y":
						return True
						break
	def isCamrunning(self, cam):
		p = command('pidof ' + cam + ' |wc -w')
		if not p.isdigit(): p=0
		if int(p) > 0:
			return True
		else:
			return False

	def createInitdscript(self, emubin, start, stop):
		Adir = "/etc/init.d/softcam"
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
		f.close

		self.container = eConsoleAppContainer()
		# Set execute rights
		os.chmod(Adir,0755)
		# Create symbolic link for startup
		if not os.path.exists("/etc/rc2.d/S20softcam"):
			self.container.execute('update-rc.d -f softcam defaults')
		# Wait a few seconds
		import time
		time.sleep (3) 

		# Start cam
		if self.isCamrunning(emubin):
			self.container.execute('/etc/init.d/softcam restart')
		else:
			self.container.execute('/etc/init.d/softcam start')

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
							MultiContentEntryPixmapAlphaTest(pos = (545, 2), size = (48, 48), png = 4), # index 4 is the status pixmap
							MultiContentEntryPixmapAlphaTest(pos = (5, 50), size = (510, 2), png = 5), # index 4 is the div pixmap
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
				statuspng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_CURRENT_PLUGIN, "Extensions/Aafpanel/pics/upgrade.png"))
				self.statuslist.append(( _("Package list update"), '', _("Trying to download a new updatelist. Please wait..." ),'', statuspng, divpng ))
				self['list'].setList(self.statuslist)
			if status == 'list':
				statuspng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_CURRENT_PLUGIN, "Extensions/Aafpanel/pics/upgrade.png"))
				self.statuslist.append(( _("Package list"), '', _("Getting Softcam list. Please wait..." ),'', statuspng, divpng ))
				self['list'].setList(self.statuslist)
			elif status == 'error':
				statuspng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_CURRENT_PLUGIN, "Extensions/Aafpanel/pics/remove.png"))
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
		print answer
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
		installedpng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_CURRENT_PLUGIN, "Extensions/Aafpanel/pics/installed.png"))
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