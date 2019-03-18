from Screens.Screen import Screen
from Components.About import about
from Components.ActionMap import ActionMap
from Components.config import config
from Components.AVSwitch import AVSwitch
from Components.SystemInfo import SystemInfo
from Components.Sources.StaticText import StaticText
from GlobalActions import globalActionMap
from enigma import eDVBVolumecontrol, eTimer, eDVBLocalTimeHandler, eServiceReference
from boxbranding import getMachineBrand, getMachineName, getBoxType
from Tools import Notifications
from time import localtime, time
import Screens.InfoBar
from os import path
from gettext import dgettext

inStandby = None
powerKey = None

QUIT_SHUTDOWN = 1
QUIT_REBOOT = 2
QUIT_RESTART = 3
QUIT_UPGRADE_FP = 4
QUIT_ERROR_RESTART = 5
QUIT_FACTORY_RESET = 40
QUIT_RESTORE_BACKUP = 41
QUIT_UPGRADE_PROGRAM = 42
QUIT_IMAGE_RESTORE = 43
QUIT_UPGRADE_MICOM = 44

class Standby2(Screen):
	def Power(self):
		print "[Standby] leave standby"
		self.videoOn()
		# restart last played service
		# unmute adc
		self.leaveMute()
		# kill me
		self.close(True)

	def deepStandby(self):
		saveAllowSuspend = Standby2.ALLOW_SUSPEND
		Standby2.ALLOW_SUSPEND = True
		powerKey.shutdown()
		Standby2.ALLOW_SUSPEND = saveAllowSuspend

	def setMute(self):
		if eDVBVolumecontrol.getInstance().isMuted():
			self.wasMuted = 1
			print "[Standby] mute already active"
		else:
			self.wasMuted = 0
			eDVBVolumecontrol.getInstance().volumeToggleMute()

	def leaveMute(self):
		if self.wasMuted == 0:
			eDVBVolumecontrol.getInstance().volumeToggleMute()

	def videoOff(self):
		# set input to vcr scart
		if SystemInfo["ScartSwitch"]:
			self.avswitch.setInput("SCART")
		else:
			self.avswitch.setInput("AUX")

		if path.exists("/proc/stb/hdmi/output"):
			open("/proc/stb/hdmi/output", "w").write("off")

	def videoOn(self):
		# set input to encoder
		self.avswitch.setInput("ENCODER")

		if path.exists("/proc/stb/hdmi/output"):
			open("/proc/stb/hdmi/output", "w").write("on")

	def __init__(self, session):
		Screen.__init__(self, session)
		self.skinName = "Standby"
		self.avswitch = AVSwitch()

		print "[Standby] enter standby"
		if getBoxType() in ('ini-7012', 'ini-7012au'):
			if path.exists("/proc/stb/lcd/symbol_scrambled"):
				open("/proc/stb/lcd/symbol_scrambled", "w").write("0")

			if path.exists("/proc/stb/lcd/symbol_1080p"):
				open("/proc/stb/lcd/symbol_1080p", "w").write("0")

			if path.exists("/proc/stb/lcd/symbol_1080i"):
				open("/proc/stb/lcd/symbol_1080i", "w").write("0")

			if path.exists("/proc/stb/lcd/symbol_720p"):
				open("/proc/stb/lcd/symbol_720p", "w").write("0")

			if path.exists("/proc/stb/lcd/symbol_576i"):
				open("/proc/stb/lcd/symbol_576i", "w").write("0")

			if path.exists("/proc/stb/lcd/symbol_576p"):
				open("/proc/stb/lcd/symbol_576p", "w").write("0")

			if path.exists("/proc/stb/lcd/symbol_hd"):
				open("/proc/stb/lcd/symbol_hd", "w").write("0")

			if path.exists("/proc/stb/lcd/symbol_dolby_audio"):
				open("/proc/stb/lcd/symbol_dolby_audio", "w").write("0")

			if path.exists("/proc/stb/lcd/symbol_mp3"):
				open("/proc/stb/lcd/symbol_mp3", "w").write("0")

		self["actions"] = ActionMap(["StandbyActions"], {
			"power": self.Power,
			"discrete_on": self.Power,
			"deepstandby": self.deepStandby,
		}, -1)

		globalActionMap.setEnabled(False)

		from Screens.InfoBar import InfoBar
		self.infoBarInstance = InfoBar.instance
		self.standbyStopServiceTimer = eTimer()
		self.standbyStopServiceTimer.callback.append(self.stopService)
		self.timeHandler = None

		# mute adc
		self.setMute()

		self.paused_service = None

		self.prev_running_service = self.session.nav.getCurrentlyPlayingServiceOrGroup()
		service = self.prev_running_service and self.prev_running_service.toString()
		if service:
			if service.rsplit(":", 1)[1].startswith("/"):
				self.paused_service = True
				self.infoBarInstance.pauseService()
		if not self.paused_service:
			self.timeHandler =  eDVBLocalTimeHandler.getInstance()
			if self.timeHandler.ready():
				if self.session.nav.getCurrentlyPlayingServiceOrGroup():
					self.stopService()
				else:
					self.standbyStopServiceTimer.startLongTimer(5)
				self.timeHandler = None
			else:
				self.timeHandler.m_timeUpdated.get().append(self.stopService)

		if self.session.pipshown:
			self.infoBarInstance and hasattr(self.infoBarInstance, "showPiP") and self.infoBarInstance.showPiP()

		self.videoOff()
		self.onFirstExecBegin.append(self.__onFirstExecBegin)
		self.onClose.append(self.__onClose)

	def __onClose(self):
		global inStandby
		inStandby = None
		self.standbyStopServiceTimer.stop()
		self.timeHandler and self.timeHandler.m_timeUpdated.get().remove(self.stopService)
		if self.paused_service:
			self.infoBarInstance.unPauseService()
		elif self.prev_running_service:
			service = self.prev_running_service.toString()
			if config.servicelist.startupservice_onstandby.value:
				self.session.nav.playService(eServiceReference(config.servicelist.startupservice.value))
				from Screens.InfoBar import InfoBar
				InfoBar.instance and InfoBar.instance.servicelist.correctChannelNumber()
			else:
				self.session.nav.playService(self.prev_running_service)
		self.session.screen["Standby"].boolean = False
		globalActionMap.setEnabled(True)

	def __onFirstExecBegin(self):
		global inStandby
		inStandby = self
		self.session.screen["Standby"].boolean = True
		config.misc.standbyCounter.value += 1

	def createSummary(self):
		return StandbySummary

	def stopService(self):
		self.session.nav.stopService()

class Standby(Standby2):
	def __init__(self, session, menu_path=""):
		screentitle = _("Standby")
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
		if Screens.InfoBar.InfoBar and Screens.InfoBar.InfoBar.instance and Screens.InfoBar.InfoBar.ptsGetTimeshiftStatus(Screens.InfoBar.InfoBar.instance):
			self.skin = """<screen position="0,0" size="0,0"/>"""
			Screen.__init__(self, session)
			self.onFirstExecBegin.append(self.showMessageBox)
			self.onShow.append(self.close)
		else:
			Standby2.__init__(self, session)
		Screen.setTitle(self, title)

	def showMessageBox(self):
		Screens.InfoBar.InfoBar.checkTimeshiftRunning(Screens.InfoBar.InfoBar.instance, self.showMessageBoxcallback)

	def showMessageBoxcallback(self, answer):
		if answer:
			self.onClose.append(self.doStandby)

	def doStandby(self):
		Notifications.AddNotification(Screens.Standby.Standby2)

class StandbySummary(Screen):
	skin = """
	<screen position="0,0" size="132,64">
		<widget source="global.CurrentTime" render="Label" position="0,0" size="132,64" font="Regular;40" halign="center">
			<convert type="ClockToText" />
		</widget>
		<widget source="session.RecordState" render="FixedLabel" text=" " position="0,0" size="132,64" zPosition="1" >
			<convert type="ConfigEntryTest">config.usage.blinking_display_clock_during_recording,True,CheckSourceBoolean</convert>
			<convert type="ConditionalShowHide">Blink</convert>
		</widget>
	</screen>"""

from enigma import quitMainloop, iRecordableService
from Screens.MessageBox import MessageBox
from time import time
from Components.Task import job_manager

class QuitMainloopScreen(Screen):
	def __init__(self, session, retvalue=1):
		self.skin = """<screen name="QuitMainloopScreen" position="fill" flags="wfNoBorder">
				<ePixmap pixmap="icons/input_info.png" position="c-27,c-60" size="53,53" alphatest="on" />
				<widget name="text" position="center,c+5" size="720,100" font="Regular;22" halign="center" />
			</screen>"""
		Screen.__init__(self, session)
		from Components.Label import Label

		text = {
			QUIT_SHUTDOWN: _("Your %s %s is shutting down.") % (getMachineBrand(), getMachineName()),
			QUIT_REBOOT: _("Your %s %s is rebooting.") % (getMachineBrand(), getMachineName()),
			QUIT_RESTART: _("The user interface of your %s %s is restarting.") % (getMachineBrand(), getMachineName()),
			QUIT_UPGRADE_FP: _("Your front processor will be upgraded.\nPlease wait until your %s %s reboots.\nThis may take a few minutes.") % (getMachineBrand(), getMachineName()),
			QUIT_ERROR_RESTART: _("The user interface of your %s %s is restarting\ndue to an error.") % (getMachineBrand(), getMachineName()),
			QUIT_FACTORY_RESET: _("Resetting settings to factory defaults.\nYour %s %s will restart now.") % (getMachineBrand(), getMachineName()),
			QUIT_RESTORE_BACKUP: _("Restoring settings from backup.\nYour %s %s will restart now.") % (getMachineBrand(), getMachineName()),
			QUIT_UPGRADE_PROGRAM: _("Upgrade in progress.\nPlease wait until your %s %s reboots.\nThis may take a few minutes.") % (getMachineBrand(), getMachineName()),
			QUIT_IMAGE_RESTORE: _("Reflash in progress.\nPlease wait until your %s %s reboots.\nThis may take a few minutes.") % (getMachineBrand(), getMachineName()),
			QUIT_UPGRADE_MICOM: _("Your front panel will be upgraded.\nThis may take a few minutes.")
		}.get(retvalue)
		self["text"] = Label(text)

		import os
		text2 = {
			QUIT_SHUTDOWN: _("Shutting down"),
			QUIT_REBOOT: _("Rebooting"),
			QUIT_RESTART: _("GUI restarting"),
			QUIT_UPGRADE_FP: _("Front processor upgrade"),
			QUIT_ERROR_RESTART: _("GUI restarting"),
			QUIT_FACTORY_RESET: _("Factory reset"),
			QUIT_RESTORE_BACKUP: _("Restoring settings"),
			QUIT_UPGRADE_PROGRAM: _("Upgrading"),
			QUIT_IMAGE_RESTORE: _("Reflashing"),
			QUIT_UPGRADE_MICOM: _("Front panel upgrade")
		}.get(retvalue)
		cmd = "echo " + text2 + " > /dev/dbox/oled0"
		os.system(cmd)

class QuitMainloopScreenSummary(Screen):
	skin = """
	<screen name="QuitMainloopScreenSummary" position="0,0" size="132,64">
		<eLabel text="TEST" position="0,0" size="132,64" font="Regular;40" halign="center"/>
	</screen>"""

inTryQuitMainloop = False

class TryQuitMainloop(MessageBox):
	def __init__(self, session, retvalue=1, timeout=-1, default_yes=True):
		self.retval = retvalue
		self.ptsmainloopvalue = retvalue
		recordings = session.nav.getRecordings()
		jobs = []
		for job in job_manager.getPendingJobs():
			if job.name != dgettext('vix', 'SoftcamCheck'):
				jobs.append(job)

		inTimeshift = Screens.InfoBar.InfoBar and Screens.InfoBar.InfoBar.instance and Screens.InfoBar.InfoBar.ptsGetTimeshiftStatus(Screens.InfoBar.InfoBar.instance)
		self.connected = False
		reason = ""
		next_rec_time = -1
		if not recordings:
			next_rec_time = session.nav.RecordTimer.getNextRecordingTime()
		if len(jobs):
			reason = (ngettext("%d job is running in the background!", "%d jobs are running in the background!", len(jobs)) % len(jobs)) + '\n'
			if len(jobs) == 1:
				job = jobs[0]
				reason += "%s: %s (%d%%)\n" % (job.getStatustext(), job.name, int(100 * job.progress / float(job.end)))
			else:
				reason += (_("%d jobs are running in the background!") % len(jobs)) + '\n'
		if inTimeshift:
			reason = _("You seem to be in timeshift or saving timeshift!") + '\n'
		if recordings or (next_rec_time > 0 and (next_rec_time - time()) < 360):
			default_yes = False
			reason = _("Recording(s) are in progress or coming up soon, or you are saving timeshift!") + '\n'

		if reason and inStandby:
			session.nav.record_event.append(self.getRecordEvent)
			self.skinName = ""
		elif reason and not inStandby:
			text = {
				QUIT_SHUTDOWN: _("Really shutdown now?"),
				QUIT_REBOOT: _("Really reboot now?"),
				QUIT_RESTART: _("Really restart now?"),
				QUIT_UPGRADE_FP: _("Really upgrade the front processor and reboot now?"),
				QUIT_FACTORY_RESET: _("Really do a factory reset and reboot now?"),
				QUIT_RESTORE_BACKUP: _("Really restore settings and reboot now?"),
				QUIT_UPGRADE_PROGRAM: _("Really upgrade your %s %s and reboot now?") % (getMachineBrand(), getMachineName()),
				QUIT_IMAGE_RESTORE: _("Really reflash your %s %s and reboot now?") % (getMachineBrand(), getMachineName()),
				QUIT_UPGRADE_MICOM: _("Really upgrade the front panel and reboot now?")
			}.get(retvalue)
			if text:
				MessageBox.__init__(self, session, reason + text, type=MessageBox.TYPE_YESNO, timeout=timeout, default=default_yes)
				self.skinName = "MessageBoxSimple"
				session.nav.record_event.append(self.getRecordEvent)
				self.connected = True
				self.onShow.append(self.__onShow)
				self.onHide.append(self.__onHide)
				return
		self.skin = """<screen position="1310,0" size="0,0"/>"""
		Screen.__init__(self, session)
		self.close(True)

	def getRecordEvent(self, recservice, event):
		if event == iRecordableService.evEnd and config.timeshift.isRecording.value:
			return
		else:
			if event == iRecordableService.evEnd:
				recordings = self.session.nav.getRecordings()
				if not recordings:  # no more recordings exist
					rec_time = self.session.nav.RecordTimer.getNextRecordingTime()
					if rec_time > 0 and (rec_time - time()) < 360:
						self.initTimeout(360)  # wait for next starting timer
						self.startTimer()
					else:
						self.close(True)  # immediate shutdown
			elif event == iRecordableService.evStart:
				self.stopTimer()

	def close(self, value):
		if self.connected:
			self.connected = False
			self.session.nav.record_event.remove(self.getRecordEvent)
		if value:
			self.hide()
			if self.retval == 1:
				config.misc.DeepStandby.value = True
			self.session.nav.stopService()
			self.quitScreen = self.session.instantiateDialog(QuitMainloopScreen, retvalue=self.retval)
			self.quitScreen.show()
			quitMainloop(self.retval)
			if getBoxType() == "vusolo4k":  #workaround for white display flash
				f = open("/proc/stb/fp/oled_brightness", "w")
				f.write("0")
				f.close()
		else:
			MessageBox.close(self, True)

	def __onShow(self):
		global inTryQuitMainloop
		inTryQuitMainloop = True

	def __onHide(self):
		global inTryQuitMainloop
		inTryQuitMainloop = False
