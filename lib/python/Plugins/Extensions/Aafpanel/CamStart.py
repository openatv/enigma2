from Components.config import config, ConfigSubsection, ConfigText, ConfigSelection, ConfigYesNo
from enigma import *
import os
import datetime

config.softcam = ConfigSubsection()
config.softcam.actCam = ConfigText(visible_width = 200)
config.softcam.restartRunning = ConfigYesNo(default=True)
config.softcam.restartAttempts =  ConfigSelection(
                    [
                    ("0", _("0 (disabled)")),
                    ("1", _("1")),
                    ("3", _("3")),
                    ("5", _("5 (default)")),
                    ("10", _("10")),
                    ], "5")
config.softcam.restartTime = ConfigSelection(
                    [
                    ("5", _("5")),
                    ("10", _("10 (default)")),
                    ("20", _("20")),
                    ("30", _("30")),
                    ("60", _("60")),
                    ("120", _("120")),
                    ("240", _("240")),
                    ], "10")
config.softcam.camstartMode =  ConfigSelection(
                    [
                    ("0", _("Python Camstarter (default)")),
                    ("1", _("Init.d")),
                    ], "0")

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

class CamStart:

	def __init__(self, session):
		self.count = 0
		self.timerTime = 2
		self.session = session
		self.timer = eTimer()
		self.timer.timeout.get().append(self.timerEvent)
		self.service = None

	def startTimer(self):
		if self.timer.isActive():
			# Disable Timer?
			pass
		else:
			self.timer.startLongTimer(self.timerTime)

	def StopTimer(self, result):
		if result:
			self.timer.stop()
			self.service = None

	def timerEvent(self):
		if config.softcam.restartAttempts.getValue() == "0":
			return
		self.timerTime = int(config.softcam.restartTime.getValue())
		emuDir = "/etc/"
		self.emuList = []
		self.mlist = []
		self.emuDirlist = []
		self.emuBin = []
		self.emuStart = []
		self.emuDirlist = os.listdir(emuDir)
		cam_name = config.softcam.actCam.getValue()
		if cam_name == "no CAM active" or cam_name == "":
			self.timer.stop()
			self.service = None
			print "[CAMSTARTER] No Cam to Start, Exit"
		else:
			self.count += 1
			print '[CAMSTARTER] Start/Check: ' + str(self.count)
			#// check emu dir for config files
			for x in self.emuDirlist:
				#// if file contains the string "emu" (then this is a emu config file)
				if x.find("emu") > -1:
					self.emuList.append(emuDir + x)
					em = open(emuDir + x)
					#// read the emu config file
					for line in em.readlines():
						line1 = line
						#// emuname
						if line.find("emuname") > -1:
							line = line.split("=")
							self.mlist.append(line[1].strip())
						#// binname
						line = line1
						if line.find("binname") > -1:
							line = line.split("=")
							self.emuBin.append(line[1].strip())
						#// startcam
						line = line1
						if line.find("startcam") > -1:
							line = line.split("=")
							self.emuStart.append(line[1].strip())

			camrunning = 0
			camfound = 0
			tel = 0
			for x in self.mlist:
				#print '[CAMSTARTER] searching active cam: ' + x
				if x == cam_name:
					camfound = 1
					cam_bin = self.emuBin[tel]
					p = command('pidof %s |wc -w' % cam_bin)
					#print '[CAMSTARTER] binname : ' + cam_bin
					import time
					time.sleep(2)
					#print '[CAMSTARTER] cam pid found: ' + str(p)
					if p != '':
						if int(p) > 0:
							actcam = self.mlist[tel]
							print datetime.datetime.now()
							print '[CAMSTARTER] CAM is Running, active cam: ' + actcam
							if cam_bin.find('camd3')>-1 and self.count == 1:
								print '[CAMSTARTER] stop ' + cam_bin
								os.system('killall -9 '  + cam_bin)
							camrunning = 1
						break
				else:
					tel +=1
			try:
				#// CAM IS NOT RUNNING SO START
				if camrunning == 0:
					#// AND CAM IN LIST
					if camfound == 1:
						start = self.emuStart[tel]
						print "[CAMSTARTER] no CAM active, starting " + start
						os.system("echo Start attempts: " + str(self.count) + " > " + "/tmp/camstarter.txt")
						self.container = eConsoleAppContainer()
						self.container.execute(start)
				else:
					# If Cam is running don't check anymore
					if config.softcam.restartRunning.getValue():
						print "[CAMSTARTER] Cam is running, exit camstarter"
						self.count = 0
						return
					if camfound == 0:
						print "[CAMSTARTER] No Cam found to start"
			except:
				pass

			if self.count < int(config.softcam.restartAttempts.getValue()):
				self.startTimer()
			else:
				self.count = 0

timerInstance = None
