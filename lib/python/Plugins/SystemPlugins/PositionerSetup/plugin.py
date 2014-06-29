from enigma import eTimer, eDVBSatelliteEquipmentControl, eDVBResourceManager, \
	eDVBDiseqcCommand, eDVBFrontendParametersSatellite, eDVBFrontendParameters,\
	iDVBFrontend

from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Plugins.Plugin import PluginDescriptor

from Components.Label import Label
from Components.Button import Button
from Components.ConfigList import ConfigList
from Components.ConfigList import ConfigListScreen
from Components.TunerInfo import TunerInfo
from Components.ActionMap import NumberActionMap, ActionMap
from Components.NimManager import nimmanager
from Components.MenuList import MenuList
from Components.ScrollLabel import ScrollLabel
from Components.config import config, ConfigSatlist, ConfigNothing, ConfigSelection, \
	 ConfigSubsection, ConfigInteger, ConfigFloat, KEY_LEFT, KEY_RIGHT, KEY_0, getConfigListEntry
from Components.TuneTest import Tuner
from Tools.Transponder import ConvertToHumanReadable

from time import sleep
from operator import mul as mul
from random import SystemRandom as SystemRandom
from threading import Thread as Thread
from threading import Event as Event

import log
import rotor_calc

class PositionerSetup(Screen):

	@staticmethod
	def satposition2metric(position):
		if position > 1800:
			position = 3600 - position
			orientation = "west"
		else:
			orientation = "east"
		return (position, orientation)

	@staticmethod
	def orbital2metric(position, orientation):
		if orientation == "west":
			position = 360 - position
		if orientation == "south":
			position = - position
		return position

	@staticmethod
	def longitude2orbital(position):
		if position >= 180:
			return 360 - position, "west"
		else:
			return position, "east"

	@staticmethod
	def latitude2orbital(position):
		if position >= 0:
			return position, "north"
		else:
			return -position, "south"

	UPDATE_INTERVAL = 50					# milliseconds
	STATUS_MSG_TIMEOUT = 2					# seconds
	LOG_SIZE = 16 * 1024					# log buffer size

	def __init__(self, session, feid):
		self.session = session
		Screen.__init__(self, session)
		self.feid = feid
		self.oldref = None
		log.open(self.LOG_SIZE)
		if config.Nims[self.feid].configMode.value == 'advanced':
			self.advanced = True
			self.advancedconfig = config.Nims[self.feid].advanced
			self.advancedsats = self.advancedconfig.sat
			self.availablesats = map(lambda x: x[0], nimmanager.getRotorSatListForNim(self.feid))
		else:
			self.advanced = False

		cur = { }
		if not self.openFrontend():
			self.oldref = session.nav.getCurrentlyPlayingServiceReference()
			service = session.nav.getCurrentService()
			feInfo = service and service.frontendInfo()
			if feInfo:
				cur = feInfo.getTransponderData(True)
			del feInfo
			del service
			session.nav.stopService() # try to disable foreground service
			if not self.openFrontend():
				if session.pipshown: # try to disable pip
					service = self.session.pip.pipservice
					feInfo = service and service.frontendInfo()
					if feInfo:
						cur = feInfo.getTransponderData(True)
					del feInfo
					del service
					from Screens.InfoBar import InfoBar
					InfoBar.instance and hasattr(InfoBar.instance, "showPiP") and InfoBar.instance.showPiP()
				if not self.openFrontend():
					self.frontend = None # in normal case this should not happen
					if hasattr(self, 'raw_channel'):
						del self.raw_channel

		self.frontendStatus = { }
		self.diseqc = Diseqc(self.frontend)
		# True means we dont like that the normal sec stuff sends commands to the rotor!
		self.tuner = Tuner(self.frontend, ignore_rotor = True)

		tp = ( cur.get("frequency", 0) / 1000,
			cur.get("symbol_rate", 0) / 1000,
			cur.get("polarization", eDVBFrontendParametersSatellite.Polarisation_Horizontal),
			cur.get("fec_inner", eDVBFrontendParametersSatellite.FEC_Auto),
			cur.get("inversion", eDVBFrontendParametersSatellite.Inversion_Unknown),
			cur.get("orbital_position", 0),
			cur.get("system", eDVBFrontendParametersSatellite.System_DVB_S),
			cur.get("modulation", eDVBFrontendParametersSatellite.Modulation_QPSK),
			cur.get("rolloff", eDVBFrontendParametersSatellite.RollOff_alpha_0_35),
			cur.get("pilot", eDVBFrontendParametersSatellite.Pilot_Unknown))

		self.tuner.tune(tp)
		self.isMoving = False
		self.stopOnLock = False

		self.red = Button("")
		self["key_red"] = self.red
		self.green = Button("")
		self["key_green"] = self.green
		self.yellow = Button("")
		self["key_yellow"] = self.yellow
		self.blue = Button("")
		self["key_blue"] = self.blue

		self.list = []
		self["list"] = ConfigList(self.list)

		self["snr_db"] = TunerInfo(TunerInfo.SNR_DB, statusDict = self.frontendStatus)
		self["snr_percentage"] = TunerInfo(TunerInfo.SNR_PERCENTAGE, statusDict = self.frontendStatus)
		self["ber_value"] = TunerInfo(TunerInfo.BER_VALUE, statusDict = self.frontendStatus)
		self["snr_bar"] = TunerInfo(TunerInfo.SNR_BAR, statusDict = self.frontendStatus)
		self["ber_bar"] = TunerInfo(TunerInfo.BER_BAR, statusDict = self.frontendStatus)
		self["lock_state"] = TunerInfo(TunerInfo.LOCK_STATE, statusDict = self.frontendStatus)

		self["frequency_value"] = Label("")
		self["symbolrate_value"] = Label("")
		self["fec_value"] = Label("")
		self["polarisation"] = Label("")
		self["status_bar"] = Label("")
		self.statusMsgTimeoutTicks = 0
		self.statusMsgBlinking = False
		self.statusMsgBlinkCount = 0
		self.statusMsgBlinkRate = 500 / self.UPDATE_INTERVAL	# milliseconds
		self.tuningChangedTo(tp)

		self["actions"] = NumberActionMap(["DirectionActions", "OkCancelActions", "ColorActions", "TimerEditActions", "InputActions"],
		{
			"ok": self.keyOK,
			"cancel": self.keyCancel,
			"up": self.keyUp,
			"down": self.keyDown,
			"left": self.keyLeft,
			"right": self.keyRight,
			"red": self.redKey,
			"green": self.greenKey,
			"yellow": self.yellowKey,
			"blue": self.blueKey,
			"log": self.showLog,
			"1": self.keyNumberGlobal,
			"2": self.keyNumberGlobal,
			"3": self.keyNumberGlobal,
			"4": self.keyNumberGlobal,
			"5": self.keyNumberGlobal,
			"6": self.keyNumberGlobal,
			"7": self.keyNumberGlobal,
			"8": self.keyNumberGlobal,
			"9": self.keyNumberGlobal,
			"0": self.keyNumberGlobal
		}, -1)

		self.updateColors("tune")

		self.statusTimer = eTimer()
		self.statusTimer.callback.append(self.updateStatus)
		self.collectingStatistics = False
		self.statusTimer.start(self.UPDATE_INTERVAL, True)
		self.dataAvailable = Event()
		self.onClose.append(self.__onClose)

		self.createConfig()
		self.createSetup()

	def __onClose(self):
		self.statusTimer.stop()
		log.close();
		self.session.nav.playService(self.oldref)

	def restartPrevService(self, yesno):
		if yesno:
			if self.frontend:
				self.frontend = None
				del self.raw_channel
		else:
			self.oldref=None
		self.close(None)

	def keyCancel(self):
		if self.oldref:
			self.session.openWithCallback(self.restartPrevService, MessageBox, _("Zap back to service before positioner setup?"), MessageBox.TYPE_YESNO)
		else:
			self.restartPrevService(False)

	def openFrontend(self):
		res_mgr = eDVBResourceManager.getInstance()
		if res_mgr:
			self.raw_channel = res_mgr.allocateRawChannel(self.feid)
			if self.raw_channel:
				self.frontend = self.raw_channel.getFrontend()
				if self.frontend:
					return True
				else:
					print "getFrontend failed"
			else:
				print "getRawChannel failed"
		else:
			print "getResourceManager instance failed"
		return False

	def setLNB(self, lnb):
		try:
			self.sitelon = lnb.longitude.float
			self.longitudeOrientation = lnb.longitudeOrientation.value
			self.sitelat = lnb.latitude.float
			self.latitudeOrientation = lnb.latitudeOrientation.value
			self.tuningstepsize = lnb.tuningstepsize.float
			self.rotorPositions = lnb.rotorPositions.value
			self.turningspeedH = lnb.turningspeedH.float
			self.turningspeedV = lnb.turningspeedV.float
		except: # some reasonable defaults from NimManager
			self.sitelon = 5.1
			self.longitudeOrientation = 'east'
			self.sitelat = 50.767
			self.latitudeOrientation = 'north'
			self.tuningstepsize = 0.36
			self.rotorPositions = 99
			self.turningspeedH = 2.3
			self.turningspeedV = 1.7
		self.sitelat = PositionerSetup.orbital2metric(self.sitelat, self.latitudeOrientation)
		self.sitelon = PositionerSetup.orbital2metric(self.sitelon, self.longitudeOrientation)

	def getLNBfromConfig(self, orb_pos):
		lnb = None
		if orb_pos in self.availablesats:
			lnbnum = int(self.advancedsats[orb_pos].lnb.value)
			if not lnbnum:
				for allsats in range(3601, 3607):
					lnbnum = int(self.advancedsats[allsats].lnb.value)
					if lnbnum:
						break
			if lnbnum:
				self.printMsg(_("Using LNB %d") % lnbnum)
				lnb = self.advancedconfig.lnb[lnbnum]
		if not lnb:
			self.logMsg(_("Warning: no LNB; using factory defaults."), timeout = 4)
		return lnb

	def createConfig(self):
		rotorposition = 1
		orb_pos = 0
		self.printMsg(_("Using tuner %s") % chr(0x41 + self.feid))
		if not self.advanced:
			self.printMsg(_("Configuration mode: %s") % _("simple"))
			nim = config.Nims[self.feid]
			self.sitelon = nim.longitude.float
			self.longitudeOrientation = nim.longitudeOrientation.value
			self.sitelat = nim.latitude.float
			self.latitudeOrientation = nim.latitudeOrientation.value
			self.sitelat = PositionerSetup.orbital2metric(self.sitelat, self.latitudeOrientation)
			self.sitelon = PositionerSetup.orbital2metric(self.sitelon, self.longitudeOrientation)
			self.tuningstepsize = nim.tuningstepsize.float
			self.rotorPositions = nim.rotorPositions.value
			self.turningspeedH = nim.turningspeedH.float
			self.turningspeedV = nim.turningspeedV.float
		else:	# it is advanced
			self.printMsg(_("Configuration mode: %s") % _("advanced"))
			fe_data = { }
			self.frontend.getFrontendData(fe_data)
			self.frontend.getTransponderData(fe_data, True)
			orb_pos = fe_data.get("orbital_position", None)
			if orb_pos in self.availablesats:
				rotorposition = int(self.advancedsats[orb_pos].rotorposition.value)
			self.setLNB(self.getLNBfromConfig(orb_pos))
		self.positioner_tune = ConfigNothing()
		self.positioner_move = ConfigNothing()
		self.positioner_finemove = ConfigNothing()
		self.positioner_limits = ConfigNothing()
		self.positioner_storage = ConfigInteger(default = rotorposition, limits = (1, self.rotorPositions))
		self.allocatedIndices = []
		m = PositionerSetup.satposition2metric(orb_pos)
		self.orbitalposition = ConfigFloat(default = [int(m[0] / 10), m[0] % 10], limits = [(0,180),(0,9)])
		self.orientation = ConfigSelection([("east", _("East")), ("west", _("West"))], m[1])

	def createSetup(self):
		self.list.append((_("Tune and focus"), self.positioner_tune, "tune"))
		self.list.append((_("Movement"), self.positioner_move, "move"))
		self.list.append((_("Fine movement"), self.positioner_finemove, "finemove"))
		self.list.append((_("Set limits"), self.positioner_limits, "limits"))
		self.list.append((_("Memory index"), self.positioner_storage, "storage"))
		self.list.append((_("Goto"), self.orbitalposition, "goto"))
		self.list.append((" ", self.orientation, "goto"))
		self["list"].l.setList(self.list)

	def keyOK(self):
		pass

	def getCurrentConfigPath(self):
		return self["list"].getCurrent()[2]

	def keyUp(self):
		if not self.isMoving:
			self["list"].instance.moveSelection(self["list"].instance.moveUp)
			self.updateColors(self.getCurrentConfigPath())

	def keyDown(self):
		if not self.isMoving:
			self["list"].instance.moveSelection(self["list"].instance.moveDown)
			self.updateColors(self.getCurrentConfigPath())

	def keyNumberGlobal(self, number):
		self["list"].handleKey(KEY_0 + number)

	def keyLeft(self):
		self["list"].handleKey(KEY_LEFT)

	def keyRight(self):
		self["list"].handleKey(KEY_RIGHT)

	def updateColors(self, entry):
		if entry == "tune":
			self.red.setText(_("Tune"))
			self.green.setText(_("Auto focus"))
			self.yellow.setText(_("Calibrate"))
			self.blue.setText(_("Calculate"))
		elif entry == "move":
			if self.isMoving:
				self.red.setText(_("Stop"))
				self.green.setText(_("Stop"))
				self.yellow.setText(_("Stop"))
				self.blue.setText(_("Stop"))
			else:
				self.red.setText(_("Move west"))
				self.green.setText(_("Search west"))
				self.yellow.setText(_("Search east"))
				self.blue.setText(_("Move east"))
		elif entry == "finemove":
			self.red.setText("")
			self.green.setText(_("Step west"))
			self.yellow.setText(_("Step east"))
			self.blue.setText("")
		elif entry == "limits":
			self.red.setText(_("Limits off"))
			self.green.setText(_("Limit west"))
			self.yellow.setText(_("Limit east"))
			self.blue.setText(_("Limits on"))
		elif entry == "storage":
			self.red.setText("")
			self.green.setText(_("Store position"))
			self.yellow.setText(_("Goto position"))
			if self.advanced:
				self.blue.setText(_("Allocate"))
			else:
				self.blue.setText("")
		elif entry == "goto":
			self.red.setText("")
			self.green.setText(_("Goto 0"))
			self.yellow.setText(_("Goto X"))
			self.blue.setText("")
		else:
			self.red.setText("")
			self.green.setText("")
			self.yellow.setText("")
			self.blue.setText("")

	def printMsg(self, msg):
		print msg
		print>>log, msg

	def stopMoving(self):
		self.printMsg(_("Stop"))
		self.diseqccommand("stop")
		self.isMoving = False
		self.stopOnLock = False
		self.statusMsg(_("Stopped"), timeout = self.STATUS_MSG_TIMEOUT)

	def redKey(self):
		entry = self.getCurrentConfigPath()
		if entry == "move":
			if self.isMoving:
				self.stopMoving()
			else:
				self.printMsg(_("Move west"))
				self.diseqccommand("moveWest", 0)
				self.isMoving = True
				self.statusMsg(_("Moving west ..."), blinking = True)
			self.updateColors("move")
		elif entry == "limits":
			self.printMsg(_("Limits off"))
			self.diseqccommand("limitOff")
			self.statusMsg(_("Limits cancelled"), timeout = self.STATUS_MSG_TIMEOUT)
		elif entry == "tune":
			fe_data = { }
			self.frontend.getFrontendData(fe_data)
			self.frontend.getTransponderData(fe_data, True)
			feparm = self.tuner.lastparm.getDVBS()
			fe_data["orbital_position"] = feparm.orbital_position
			self.statusTimer.stop()
			self.session.openWithCallback(self.tune, TunerScreen, self.feid, fe_data)

	def greenKey(self):
		entry = self.getCurrentConfigPath()
		if entry == "tune":
			# Auto focus
			self.printMsg(_("Auto focus"))
			print>>log, (_("Site latitude") + "      : %5.1f %s") % PositionerSetup.latitude2orbital(self.sitelat)
			print>>log, (_("Site longitude") + "     : %5.1f %s") % PositionerSetup.longitude2orbital(self.sitelon)
			Thread(target = self.autofocus).start()
		elif entry == "move":
			if self.isMoving:
				self.stopMoving()
			else:
				self.printMsg(_("Search west"))
				self.isMoving = True
				self.stopOnLock = True
				self.diseqccommand("moveWest", 0)
				self.statusMsg(_("Searching west ..."), blinking = True)
			self.updateColors("move")
		elif entry == "finemove":
			self.printMsg(_("Step west"))
			self.diseqccommand("moveWest", 0xFF) # one step
			self.statusMsg(_("Stepped west"), timeout = self.STATUS_MSG_TIMEOUT)
		elif entry == "storage":
			self.printMsg(_("Store at index"))
			index = int(self.positioner_storage.value)
			self.diseqccommand("store", index)
			self.statusMsg((_("Position stored at index") + " %2d") % index, timeout = self.STATUS_MSG_TIMEOUT)
		elif entry == "limits":
			self.printMsg(_("Limit west"))
			self.diseqccommand("limitWest")
			self.statusMsg(_("West limit set"), timeout = self.STATUS_MSG_TIMEOUT)
		elif entry == "goto":
			self.printMsg(_("Goto 0"))
			self.diseqccommand("moveTo", 0)
			self.statusMsg(_("Moved to position 0"), timeout = self.STATUS_MSG_TIMEOUT)

	def yellowKey(self):
		entry = self.getCurrentConfigPath()
		if entry == "move":
			if self.isMoving:
				self.stopMoving()
			else:
				self.printMsg(_("Move east"))
				self.isMoving = True
				self.stopOnLock = True
				self.diseqccommand("moveEast", 0)
				self.statusMsg(_("Searching east ..."), blinking = True)
			self.updateColors("move")
		elif entry == "finemove":
			self.printMsg(_("Step east"))
			self.diseqccommand("moveEast", 0xFF) # one step
			self.statusMsg(_("Stepped east"), timeout = self.STATUS_MSG_TIMEOUT)
		elif entry == "storage":
			self.printMsg(_("Goto index position"))
			index = int(self.positioner_storage.value)
			self.diseqccommand("moveTo", index)
			self.statusMsg((_("Moved to position at index") + " %2d") % index, timeout = self.STATUS_MSG_TIMEOUT)
		elif entry == "limits":
			self.printMsg(_("Limit east"))
			self.diseqccommand("limitEast")
			self.statusMsg(_("East limit set"), timeout = self.STATUS_MSG_TIMEOUT)
		elif entry == "goto":
			self.printMsg(_("Move to position X"))
			satlon = self.orbitalposition.float
			position = ("%5.1f %s") % (satlon, self.orientation.value)
			print>>log, (_("Satellite longitude:") + " %s") % position
			satlon = PositionerSetup.orbital2metric(satlon, self.orientation.value)
			self.statusMsg((_("Moving to position") + " %s") % position, timeout = self.STATUS_MSG_TIMEOUT)
			self.gotoX(satlon)
		elif entry == "tune":
			# Start USALS calibration
			self.printMsg(_("USALS calibration"))
			print>>log, (_("Site latitude") + "      : %5.1f %s") % PositionerSetup.latitude2orbital(self.sitelat)
			print>>log, (_("Site longitude") + "     : %5.1f %s") % PositionerSetup.longitude2orbital(self.sitelon)
			Thread(target = self.gotoXcalibration).start()

	def blueKey(self):
		entry = self.getCurrentConfigPath()
		if entry == "move":
			if self.isMoving:
				self.stopMoving()
			else:
				self.printMsg(_("Move east"))
				self.diseqccommand("moveEast", 0)
				self.isMoving = True
				self.statusMsg(_("Moving east ..."), blinking = True)
			self.updateColors("move")
		elif entry == "limits":
			self.printMsg(_("Limits on"))
			self.diseqccommand("limitOn")
			self.statusMsg(_("Limits enabled"), timeout = self.STATUS_MSG_TIMEOUT)
		elif entry == "tune":
			# Start (re-)calculate
			self.session.openWithCallback(self.recalcConfirmed, MessageBox, _("This will (re-)calculate all positions of your rotor and may remove previously memorised positions and fine-tuning!\nAre you sure?"), MessageBox.TYPE_YESNO, default = False, timeout = 10)
		elif entry == "storage":
			if self.advanced:
				self.printMsg(_("Allocate unused memory index"))
				while(True):
					if not len(self.allocatedIndices):
						for sat in self.availablesats:
							current_index = int(self.advancedsats[sat].rotorposition.value)
							if current_index not in self.allocatedIndices:
								self.allocatedIndices.append(current_index)
						if len(self.allocatedIndices) == self.rotorPositions:
							self.statusMsg(_("No free index available"), timeout = self.STATUS_MSG_TIMEOUT)
							break
					index = 1
					if len(self.allocatedIndices):
						for i in sorted(self.allocatedIndices):
							if i != index:
								break
							index += 1
					if index <= self.rotorPositions:
						self.positioner_storage.value = index
						self["list"].invalidateCurrent()
						self.allocatedIndices.append(index)
						self.statusMsg((_("Index allocated:") + " %2d") % index, timeout = self.STATUS_MSG_TIMEOUT)
						break
					else:
						self.allocatedIndices = []

	def recalcConfirmed(self, yesno):
		if yesno:
			self.printMsg(_("Calculate all positions"))
			print>>log, (_("Site latitude") + "      : %5.1f %s") % PositionerSetup.latitude2orbital(self.sitelat)
			print>>log, (_("Site longitude") + "     : %5.1f %s") % PositionerSetup.longitude2orbital(self.sitelon)
			lon = self.sitelon
			if lon >= 180:
				lon -= 360
			if lon < -30:	# americas, make unsigned binary west positive polarity
				lon = -lon
			lon = int(round(lon)) & 0xFF
			lat = int(round(self.sitelat)) & 0xFF
			index = int(self.positioner_storage.value) & 0xFF
			self.diseqccommand("calc", (((index << 8) | lon) << 8) | lat)
			self.statusMsg(_("Calculation complete"), timeout = self.STATUS_MSG_TIMEOUT)

	def showLog(self):
		self.session.open(PositionerSetupLog)

	def diseqccommand(self, cmd, param = 0):
		print>>log, "Diseqc(%s, %X)" % (cmd, param)
		self.diseqc.command(cmd, param)
		self.tuner.retune()

	def tune(self, transponder):
		# re-start the update timer
		self.statusTimer.start(self.UPDATE_INTERVAL, True)
		if transponder is not None:
			self.tuner.tune(transponder)
			self.tuningChangedTo(transponder)
		feparm = self.tuner.lastparm.getDVBS()
		orb_pos = feparm.orbital_position
		m = PositionerSetup.satposition2metric(orb_pos)
		self.orbitalposition.value = [int(m[0] / 10), m[0] % 10]
		self.orientation.value = m[1]
		if self.advanced:
			if orb_pos in self.availablesats:
				rotorposition = int(self.advancedsats[orb_pos].rotorposition.value)
				self.positioner_storage.value = rotorposition
				self.allocatedIndices = []
			self.setLNB(self.getLNBfromConfig(orb_pos))

	def isLocked(self):
		return self.frontendStatus.get("tuner_locked", 0) == 1

	def statusMsg(self, msg, blinking = False, timeout = 0):			# timeout in seconds
		self.statusMsgBlinking = blinking
		if not blinking:
			self["status_bar"].visible = True
		self["status_bar"].setText(msg)
		self.statusMsgTimeoutTicks = (timeout * 1000 + self.UPDATE_INTERVAL / 2) / self.UPDATE_INTERVAL

	def updateStatus(self):
		self.statusTimer.start(self.UPDATE_INTERVAL, True)
		if self.frontend:
			self.frontend.getFrontendStatus(self.frontendStatus)
		self["snr_db"].update()
		self["snr_percentage"].update()
		self["ber_value"].update()
		self["snr_bar"].update()
		self["ber_bar"].update()
		self["lock_state"].update()
		if self.statusMsgBlinking:
			self.statusMsgBlinkCount += 1
			if self.statusMsgBlinkCount == self.statusMsgBlinkRate:
				self.statusMsgBlinkCount = 0
				self["status_bar"].visible = not self["status_bar"].visible
		if self.statusMsgTimeoutTicks > 0:
			self.statusMsgTimeoutTicks -= 1
			if self.statusMsgTimeoutTicks == 0:
				self["status_bar"].setText("")
				self.statusMsgBlinking = False
				self["status_bar"].visible = True
		if self.isLocked() and self.isMoving and self.stopOnLock:
			self.stopMoving()
			self.updateColors(self.getCurrentConfigPath())
		if self.collectingStatistics:
			self.low_rate_adapter_count += 1
			if self.low_rate_adapter_count == self.MAX_LOW_RATE_ADAPTER_COUNT:
				self.low_rate_adapter_count = 0
				self.snr_percentage += self["snr_percentage"].getValue(TunerInfo.SNR)
				self.lock_count += self["lock_state"].getValue(TunerInfo.LOCK)
				self.stat_count += 1
				if self.stat_count == self.max_count:
					self.collectingStatistics = False
					count = float(self.stat_count)
					self.lock_count /= count
					self.snr_percentage *= 100.0 / 0x10000 / count
					self.dataAvailable.set()

	def tuningChangedTo(self, tp):

		def setLowRateAdapterCount(symbolrate):
			# change the measurement time and update interval in case of low symbol rate,
			# since more time is needed for the front end in that case.
			# It is an heuristic determination without any pretence. For symbol rates
			# of 5000 the interval is multiplied by 3 until 15000 which is seen
			# as a high symbol rate. Linear interpolation elsewhere.
			return max(int(round((3 - 1) * (symbolrate - 15000) / (5000 - 15000) + 1)), 1)

		self.symbolrate = tp[1]
		self.polarisation = tp[2]
		self.MAX_LOW_RATE_ADAPTER_COUNT = setLowRateAdapterCount(self.symbolrate)
		transponderdata = ConvertToHumanReadable(self.tuner.getTransponderData(), "DVB-S")
		frequency = transponderdata.get("frequency")
		if frequency:
			frequency_text = str(frequency / 1000)
		else:
			frequency_text = ""
		self["frequency_value"].setText(frequency_text)
		symbolrate = transponderdata.get("symbol_rate")
		if symbolrate:
			symbolrate_text = str(symbolrate / 1000)
		else:
			symbolrate_text = ""
		self["symbolrate_value"].setText(symbolrate_text)
		fec_inner = transponderdata.get("fec_inner")
		if fec_inner:
			fec_text = str(fec_inner)
		else:
			fec_text = ""
		self["fec_value"].setText(fec_text)
		polarisation = transponderdata.get("polarization")
		if polarisation:
			polarisation_text = str(polarisation)
		else:
			polarisation_text = ""
		self["polarisation"].setText(polarisation_text)

	@staticmethod
	def rotorCmd2Step(rotorCmd, stepsize):
		return round(float(rotorCmd & 0xFFF) / 0x10 / stepsize) * (1 - ((rotorCmd & 0x1000) >> 11))

	@staticmethod
	def gotoXcalc(satlon, sitelat, sitelon):
		def azimuth2Rotorcode(angle):
			gotoXtable = (0x00, 0x02, 0x03, 0x05, 0x06, 0x08, 0x0A, 0x0B, 0x0D, 0x0E)
			a = int(round(abs(angle) * 10.0))
			return ((a / 10) << 4) + gotoXtable[a % 10]

		satHourAngle = rotor_calc.calcSatHourangle(satlon, sitelat, sitelon)
		if sitelat >= 0: # Northern Hemisphere
			rotorCmd = azimuth2Rotorcode(180 - satHourAngle)
			if satHourAngle <= 180: # the east
				rotorCmd |= 0xE000
			else:					# west
				rotorCmd |= 0xD000
		else: # Southern Hemisphere
			if satHourAngle <= 180: # the east
				rotorCmd = azimuth2Rotorcode(satHourAngle) | 0xD000
			else: # west
				rotorCmd = azimuth2Rotorcode(360 - satHourAngle) | 0xE000
		return rotorCmd

	def gotoX(self, satlon):
		rotorCmd = PositionerSetup.gotoXcalc(satlon, self.sitelat, self.sitelon)
		self.diseqccommand("gotoX", rotorCmd)
		x = PositionerSetup.rotorCmd2Step(rotorCmd, self.tuningstepsize)
		print>>log, (_("Rotor step position:") + " %4d") % x
		return x

	def getTurningspeed(self):
		if self.polarisation == eDVBFrontendParametersSatellite.Polarisation_Horizontal:
			turningspeed = self.turningspeedH
		else:
			turningspeed = self.turningspeedV
		return max(turningspeed, 0.1)

	TURNING_START_STOP_DELAY = 1.600	# seconds
	MAX_SEARCH_ANGLE = 12.0				# degrees
	MAX_FOCUS_ANGLE = 6.0				# degrees
	LOCK_LIMIT = 0.1					# ratio
	MEASURING_TIME = 2.500				# seconds

	def measure(self, time = MEASURING_TIME):	# time in seconds
		self.snr_percentage = 0.0
		self.lock_count = 0.0
		self.stat_count = 0
		self.low_rate_adapter_count = 0
		self.max_count = max(int((time * 1000 + self.UPDATE_INTERVAL / 2)/ self.UPDATE_INTERVAL), 1)
		self.collectingStatistics = True
		self.dataAvailable.clear()
		self.dataAvailable.wait()

	def logMsg(self, msg, timeout = 0):
		self.statusMsg(msg, timeout = timeout)
		self.printMsg(msg)

	def sync(self):
		self.lock_count = 0.0
		n = 0
		while self.lock_count < (1 - self.LOCK_LIMIT) and n < 5:
			self.measure(time = 0.500)
			n += 1
		if self.lock_count < (1 - self.LOCK_LIMIT):
			return False
		return True

	randomGenerator = None
	def randomBool(self):
		if self.randomGenerator is None:
			self.randomGenerator = SystemRandom()
		return self.randomGenerator.random() >= 0.5

	def gotoXcalibration(self):

		def move(x):
			z = self.gotoX(x + satlon)
			time = int(abs(x - prev_pos) / turningspeed + 2 * self.TURNING_START_STOP_DELAY)
			sleep(time * self.MAX_LOW_RATE_ADAPTER_COUNT)
			return z

		def reportlevels(pos, level, lock):
			print>>log, (_("Signal quality") + " %5.1f" + chr(176) + "   : %6.2f") % (pos, level)
			print>>log, (_("Lock ratio") + "     %5.1f" + chr(176) + "   : %6.2f") % (pos, lock)

		def optimise(readings):
			xi = readings.keys()
			yi = map(lambda (x, y) : x, readings.values())
			x0 = sum(map(mul, xi, yi)) / sum(yi)
			xm = xi[yi.index(max(yi))]
			return (x0, xm)

		def toGeopos(x):
			if x < 0:
				return _("W")
			else:
				return _("E")

		def toGeoposEx(x):
			if x < 0:
				return _("west")
			else:
				return _("east")

		self.logMsg(_("GotoX calibration"))
		satlon = self.orbitalposition.float
		print>>log, (_("Satellite longitude:") + " %5.1f" + chr(176) + " %s") % (satlon, self.orientation.value)
		satlon = PositionerSetup.orbital2metric(satlon, self.orientation.value)
		prev_pos = 0.0						# previous relative position w.r.t. satlon
		turningspeed = self.getTurningspeed()

		x = 0.0								# relative position w.r.t. satlon
		dir = 1
		if self.randomBool():
			dir = -dir
		while abs(x) < self.MAX_SEARCH_ANGLE:
			if self.sync():
				break
			x += (1.0 * dir)						# one degree east/west
			self.statusMsg((_("Searching") + " " + toGeoposEx(dir) + " %2d" + chr(176)) % abs(x), blinking = True)
			move(x)
			prev_pos = x
		else:
			x = 0.0
			dir = -dir
			while abs(x) < self.MAX_SEARCH_ANGLE:
				x += (1.0 * dir)					# one degree east/west
				self.statusMsg((_("Searching") + " " + toGeoposEx(dir) + " %2d" + chr(176)) % abs(x), blinking = True)
				move(x)
				prev_pos = x
				if self.sync():
					break
			else:
				msg = _("Cannot find any signal ..., aborting !")
				self.printMsg(msg)
				self.statusMsg("")
				self.session.open(MessageBox, msg, MessageBox.TYPE_ERROR, timeout = 5)
				return
		x = round(x / self.tuningstepsize) * self.tuningstepsize
		move(x)
		prev_pos = x
		measurements = {}
		self.measure()
		print>>log, (_("Initial signal quality") + " %5.1f" + chr(176) + ": %6.2f") % (x, self.snr_percentage)
		print>>log, (_("Initial lock ratio") + "     %5.1f" + chr(176) + ": %6.2f") % (x, self.lock_count)
		measurements[x] = (self.snr_percentage, self.lock_count)

		start_pos = x
		x = 0.0
		dir = 1
		if self.randomBool():
			dir = -dir
		while x < self.MAX_FOCUS_ANGLE:
			x += self.tuningstepsize * dir					# one step east/west
			self.statusMsg((_("Moving") + " " + toGeoposEx(dir) + " %5.1f" + chr(176)) % abs(x + start_pos), blinking = True)
			move(x + start_pos)
			prev_pos = x + start_pos
			self.measure()
			measurements[x + start_pos] = (self.snr_percentage, self.lock_count)
			reportlevels(x + start_pos, self.snr_percentage, self.lock_count)
			if self.lock_count < self.LOCK_LIMIT:
				break
		else:
			msg = _("Cannot determine") + " " + toGeoposEx(dir) + " " + _("limit ..., aborting !")
			self.printMsg(msg)
			self.statusMsg("")
			self.session.open(MessageBox, msg, MessageBox.TYPE_ERROR, timeout = 5)
			return
		x = 0.0
		dir = -dir
		self.statusMsg((_("Moving") + " " + toGeoposEx(dir) + " %5.1f" + chr(176)) % abs(start_pos), blinking = True)
		move(start_pos)
		prev_pos = start_pos
		if not self.sync():
			msg = _("Sync failure moving back to origin !")
			self.printMsg(msg)
			self.statusMsg("")
			self.session.open(MessageBox, msg, MessageBox.TYPE_ERROR, timeout = 5)
			return
		while abs(x) < self.MAX_FOCUS_ANGLE:
			x += self.tuningstepsize * dir					# one step west/east
			self.statusMsg((_("Moving") + " " + toGeoposEx(dir) + " %5.1f" + chr(176)) % abs(x + start_pos), blinking = True)
			move(x + start_pos)
			prev_pos = x + start_pos
			self.measure()
			measurements[x + start_pos] = (self.snr_percentage, self.lock_count)
			reportlevels(x + start_pos, self.snr_percentage, self.lock_count)
			if self.lock_count < self.LOCK_LIMIT:
				break
		else:
			msg = _("Cannot determine") + " " + toGeoposEx(dir) + " " + _("limit ..., aborting !")
			self.printMsg(msg)
			self.statusMsg("")
			self.session.open(MessageBox, msg, MessageBox.TYPE_ERROR, timeout = 5)
			return
		(x0, xm) = optimise(measurements)
		x = move(x0)
		if satlon > 180:
			satlon -= 360
		x0 += satlon
		xm += satlon
		print>>log, (_("Weighted position") + "     : %5.1f" + chr(176) + " %s") % (abs(x0), toGeopos(x0))
		print>>log, (_("Strongest position") + "    : %5.1f" + chr(176) + " %s") % (abs(xm), toGeopos(xm))
		self.logMsg((_("Final position at") + " %5.1f" + chr(176) + " %s / %d; " + _("offset is") + " %4.1f" + chr(176)) % (abs(x0), toGeopos(x0), x, x0 - satlon), timeout = 10)

	def autofocus(self):

		def move(x):
			if x > 0:
				self.diseqccommand("moveEast", (-x) & 0xFF)
			elif x < 0:
				self.diseqccommand("moveWest", x & 0xFF)
			if x != 0:
				time = int(abs(x) * self.tuningstepsize / turningspeed + 2 * self.TURNING_START_STOP_DELAY)
				sleep(time * self.MAX_LOW_RATE_ADAPTER_COUNT)

		def reportlevels(pos, level, lock):
			print>>log, (_("Signal quality") + " [%2d]   : %6.2f") % (pos, level)
			print>>log, (_("Lock ratio") + " [%2d]       : %6.2f") % (pos, lock)

		def optimise(readings):
			xi = readings.keys()
			yi = map(lambda (x, y) : x, readings.values())
			x0 = int(round(sum(map(mul, xi, yi)) / sum(yi)))
			xm = xi[yi.index(max(yi))]
			return (x0, xm)

		def toGeoposEx(x):
			if x < 0:
				return _("west")
			else:
				return _("east")

		self.logMsg(_("Auto focus commencing ..."))
		turningspeed = self.getTurningspeed()
		measurements = {}
		maxsteps = max(min(round(self.MAX_FOCUS_ANGLE / self.tuningstepsize), 0x1F), 3)
		self.measure()
		print>>log, (_("Initial signal quality:") + " %6.2f") % self.snr_percentage
		print>>log, (_("Initial lock ratio") + "    : %6.2f") % self.lock_count
		if self.lock_count < 1 - self.LOCK_LIMIT:
			msg = _("There is no signal to lock on !")
			self.printMsg(msg)
			self.statusMsg("")
			self.session.open(MessageBox, msg, MessageBox.TYPE_ERROR, timeout = 5)
			return
		print>>log, _("Signal OK, proceeding")
		x = 0
		dir = 1
		if self.randomBool():
			dir = -dir
		measurements[x] = (self.snr_percentage, self.lock_count)
		nsteps = 0
		while nsteps < maxsteps:
			x += dir
			self.statusMsg((_("Moving") + " " + toGeoposEx(dir) + " %2d") % abs(x), blinking = True)
			move(dir) 		# one step
			self.measure()
			measurements[x] = (self.snr_percentage, self.lock_count)
			reportlevels(x, self.snr_percentage, self.lock_count)
			if self.lock_count < self.LOCK_LIMIT:
				break
			nsteps += 1
		else:
			msg = _("Cannot determine") + " " + toGeoposEx(dir) + " " + _("limit ..., aborting !")
			self.printMsg(msg)
			self.statusMsg("")
			self.session.open(MessageBox, msg, MessageBox.TYPE_ERROR, timeout = 5)
			return
		dir = -dir
		self.statusMsg(_("Moving") + " " + toGeoposEx(dir) + "  0", blinking = True)
		move(-x)
		if not self.sync():
			msg = _("Sync failure moving back to origin !")
			self.printMsg(msg)
			self.statusMsg("")
			self.session.open(MessageBox, msg, MessageBox.TYPE_ERROR, timeout = 5)
			return
		x = 0
		nsteps = 0
		while nsteps < maxsteps:
			x += dir
			self.statusMsg((_("Moving") + " " + toGeoposEx(dir) + " %2d") % abs(x), blinking = True)
			move(dir) 		# one step
			self.measure()
			measurements[x] = (self.snr_percentage, self.lock_count)
			reportlevels(x, self.snr_percentage, self.lock_count)
			if self.lock_count < self.LOCK_LIMIT:
				break
			nsteps += 1
		else:
			msg = _("Cannot determine") + " " + toGeoposEx(dir) + " " + _("limit ..., aborting !")
			self.printMsg(msg)
			self.statusMsg("")
			self.session.open(MessageBox, msg, MessageBox.TYPE_ERROR, timeout = 5)
			return
		(x0, xm) = optimise(measurements)
		print>>log, (_("Weighted position") + "     : %2d") % x0
		print>>log, (_("Strongest position") + "    : %2d") % xm
		self.logMsg((_("Final position at index") + " %2d (%5.1f" + chr(176) + ")") % (x0, x0 * self.tuningstepsize), timeout = 6)
		move(x0 - x)

class Diseqc:
	def __init__(self, frontend):
		self.frontend = frontend

	def command(self, what, param = 0):
		if self.frontend:
			cmd = eDVBDiseqcCommand()
			if what == "moveWest":
				string = 'E03169' + ("%02X" % param)
			elif what == "moveEast":
				string = 'E03168' + ("%02X" % param)
			elif what == "moveTo":
				string = 'E0316B' + ("%02X" % param)
			elif what == "store":
				string = 'E0316A' + ("%02X" % param)
			elif what == "gotoX":
				string = 'E0316E' + ("%04X" % param)
			elif what == "calc":
				string = 'E0316F' + ("%06X" % param)
			elif what == "limitOn":
				string = 'E0316A00'
			elif what == "limitOff":
				string = 'E03163'
			elif what == "limitEast":
				string = 'E03166'
			elif what == "limitWest":
				string = 'E03167'
			else:
				string = 'E03160' #positioner stop

			print "diseqc command:",
			print string
			cmd.setCommandString(string)
			self.frontend.setTone(iDVBFrontend.toneOff)
			sleep(0.015) # wait 15msec after disable tone
			self.frontend.sendDiseqc(cmd)
			if string == 'E03160': #positioner stop
				sleep(0.050)
				self.frontend.sendDiseqc(cmd) # send 2nd time

class PositionerSetupLog(Screen):
	skin = """
<screen position="center,center" size="560,400" title="Positioner Setup Log" >
	<ePixmap name="red"    position="0,0"   zPosition="2" size="140,40" pixmap="skin_default/buttons/red.png" transparent="1" alphatest="on" />
	<ePixmap name="green"  position="140,0" zPosition="2" size="140,40" pixmap="skin_default/buttons/green.png" transparent="1" alphatest="on" />
	<ePixmap name="yellow" position="280,0" zPosition="2" size="140,40" pixmap="skin_default/buttons/yellow.png" transparent="1" alphatest="on" />
	<ePixmap name="blue"   position="420,0" zPosition="2" size="140,40" pixmap="skin_default/buttons/blue.png" transparent="1" alphatest="on" />

	<widget name="key_red" position="0,0" size="140,40" valign="center" halign="center" zPosition="4"  foregroundColor="white" font="Regular;20" transparent="1" shadowColor="background" shadowOffset="-2,-2" />
	<widget name="key_green" position="140,0" size="140,40" valign="center" halign="center" zPosition="4"  foregroundColor="white" font="Regular;20" transparent="1" shadowColor="background" shadowOffset="-2,-2" />
	<widget name="key_yellow" position="280,0" size="140,40" valign="center" halign="center" zPosition="4"  foregroundColor="white" font="Regular;20" transparent="1" shadowColor="background" shadowOffset="-2,-2" />
	<widget name="key_blue" position="420,0" size="140,40" valign="center" halign="center" zPosition="4"  foregroundColor="white" font="Regular;20" transparent="1" shadowColor="background" shadowOffset="-2,-2" />

	<ePixmap alphatest="on" pixmap="skin_default/icons/clock.png" position="480,383" size="14,14" zPosition="3"/>
	<widget font="Regular;18" halign="left" position="505,380" render="Label" size="55,20" source="global.CurrentTime" transparent="1" valign="center" zPosition="3">
		<convert type="ClockToText">Default</convert>
	</widget>
	<widget name="list" font="Console;16" position="10,40" size="540,340" />
</screen>"""
	def __init__(self, session):
		self.session = session
		Screen.__init__(self, session)
		self["key_red"] = Button(_("Clear"))
		self["key_green"] = Button()
		self["key_yellow"] = Button()
		self["key_blue"] = Button(_("Save"))
		self["list"] = ScrollLabel(log.getvalue())
		self["actions"] = ActionMap(["DirectionActions", "OkCancelActions", "ColorActions"],
		{
			"red": self.clear,
			"green": self.cancel,
			"yellow": self.cancel,
			"save": self.save,
			"blue": self.save,
			"cancel": self.cancel,
			"ok": self.cancel,
			"left": self["list"].pageUp,
			"right": self["list"].pageDown,
			"up": self["list"].pageUp,
			"down": self["list"].pageDown,
			"pageUp": self["list"].pageUp,
			"pageDown": self["list"].pageDown
		}, -2)

	def save(self):
		try:
			f = open('/tmp/positionersetup.log', 'w')
			f.write(log.getvalue())
			f.close()
		except Exception, e:
			self["list"].setText(_("Failed to write /tmp/positionersetup.log: ") + str(e))
		self.close(True)

	def cancel(self):
		self.close(False)

	def clear(self):
		log.logfile.reset()
		log.logfile.truncate()
		self.close(False)

class TunerScreen(ConfigListScreen, Screen):
	skin = """
		<screen position="90,100" size="520,400" title="Tune">
			<widget name="config" position="20,10" size="460,350" scrollbarMode="showOnDemand" />
			<widget name="introduction" position="20,360" size="350,30" font="Regular;23" />
		</screen>"""

	def __init__(self, session, feid, fe_data):
		self.feid = feid
		self.fe_data = fe_data
		Screen.__init__(self, session)
		ConfigListScreen.__init__(self, None)
		self.createConfig(fe_data)
		self.initialSetup()
		self.createSetup()
		self.tuning.sat.addNotifier(self.tuningSatChanged)
		self.tuning.type.addNotifier(self.tuningTypeChanged)
		self.scan_sat.system.addNotifier(self.systemChanged)

		self["actions"] = NumberActionMap(["SetupActions"],
		{
			"ok": self.keyGo,
			"cancel": self.keyCancel,
		}, -2)

	def createConfig(self, frontendData):
		satlist = nimmanager.getRotorSatListForNim(self.feid)
		orb_pos = self.fe_data.get("orbital_position", None)
		orb_pos_str = str(orb_pos)
		self.tuning = ConfigSubsection()
		self.tuning.type = ConfigSelection(
				default = "manual_transponder",
				choices = { "manual_transponder" : _("Manual transponder"),
							"predefined_transponder" : _("Predefined transponder") } )
		self.tuning.sat = ConfigSatlist(list = satlist)
		if orb_pos is not None:
			for sat in satlist:
				if sat[0] == orb_pos and self.tuning.sat.value != orb_pos_str:
					self.tuning.sat.value = orb_pos_str
		self.updateTransponders()

		defaultSat = {
			"orbpos": 192,
			"system": eDVBFrontendParametersSatellite.System_DVB_S,
			"frequency": 11836,
			"inversion": eDVBFrontendParametersSatellite.Inversion_Unknown,
			"symbolrate": 27500,
			"polarization": eDVBFrontendParametersSatellite.Polarisation_Horizontal,
			"fec": eDVBFrontendParametersSatellite.FEC_Auto,
			"fec_s2": eDVBFrontendParametersSatellite.FEC_9_10,
			"modulation": eDVBFrontendParametersSatellite.Modulation_QPSK }
		if frontendData is not None:
			ttype = frontendData.get("tuner_type", "UNKNOWN")
			defaultSat["system"] = frontendData.get("system", eDVBFrontendParametersSatellite.System_DVB_S)
			defaultSat["frequency"] = frontendData.get("frequency", 0) / 1000
			defaultSat["inversion"] = frontendData.get("inversion", eDVBFrontendParametersSatellite.Inversion_Unknown)
			defaultSat["symbolrate"] = frontendData.get("symbol_rate", 0) / 1000
			defaultSat["polarization"] = frontendData.get("polarization", eDVBFrontendParametersSatellite.Polarisation_Horizontal)
			if defaultSat["system"] == eDVBFrontendParametersSatellite.System_DVB_S2:
				defaultSat["fec_s2"] = frontendData.get("fec_inner", eDVBFrontendParametersSatellite.FEC_Auto)
				defaultSat["rolloff"] = frontendData.get("rolloff", eDVBFrontendParametersSatellite.RollOff_alpha_0_35)
				defaultSat["pilot"] = frontendData.get("pilot", eDVBFrontendParametersSatellite.Pilot_Unknown)
			else:
				defaultSat["fec"] = frontendData.get("fec_inner", eDVBFrontendParametersSatellite.FEC_Auto)
			defaultSat["modulation"] = frontendData.get("modulation", eDVBFrontendParametersSatellite.Modulation_QPSK)
			defaultSat["orbpos"] = frontendData.get("orbital_position", 0)

		self.scan_sat = ConfigSubsection()
		self.scan_sat.system = ConfigSelection(default = defaultSat["system"], choices = [
			(eDVBFrontendParametersSatellite.System_DVB_S, _("DVB-S")),
			(eDVBFrontendParametersSatellite.System_DVB_S2, _("DVB-S2"))])
		self.scan_sat.frequency = ConfigInteger(default = defaultSat["frequency"], limits = (1, 99999))
		self.scan_sat.inversion = ConfigSelection(default = defaultSat["inversion"], choices = [
			(eDVBFrontendParametersSatellite.Inversion_Off, _("Off")),
			(eDVBFrontendParametersSatellite.Inversion_On, _("On")),
			(eDVBFrontendParametersSatellite.Inversion_Unknown, _("Auto"))])
		self.scan_sat.symbolrate = ConfigInteger(default = defaultSat["symbolrate"], limits = (1, 99999))
		self.scan_sat.polarization = ConfigSelection(default = defaultSat["polarization"], choices = [
			(eDVBFrontendParametersSatellite.Polarisation_Horizontal, _("horizontal")),
			(eDVBFrontendParametersSatellite.Polarisation_Vertical, _("vertical")),
			(eDVBFrontendParametersSatellite.Polarisation_CircularLeft, _("circular left")),
			(eDVBFrontendParametersSatellite.Polarisation_CircularRight, _("circular right"))])
		self.scan_sat.fec = ConfigSelection(default = defaultSat["fec"], choices = [
			(eDVBFrontendParametersSatellite.FEC_Auto, _("Auto")),
			(eDVBFrontendParametersSatellite.FEC_1_2, "1/2"),
			(eDVBFrontendParametersSatellite.FEC_2_3, "2/3"),
			(eDVBFrontendParametersSatellite.FEC_3_4, "3/4"),
			(eDVBFrontendParametersSatellite.FEC_5_6, "5/6"),
			(eDVBFrontendParametersSatellite.FEC_7_8, "7/8"),
			(eDVBFrontendParametersSatellite.FEC_None, _("None"))])
		self.scan_sat.fec_s2 = ConfigSelection(default = defaultSat["fec_s2"], choices = [
			(eDVBFrontendParametersSatellite.FEC_1_2, "1/2"),
			(eDVBFrontendParametersSatellite.FEC_2_3, "2/3"),
			(eDVBFrontendParametersSatellite.FEC_3_4, "3/4"),
			(eDVBFrontendParametersSatellite.FEC_3_5, "3/5"),
			(eDVBFrontendParametersSatellite.FEC_4_5, "4/5"),
			(eDVBFrontendParametersSatellite.FEC_5_6, "5/6"),
			(eDVBFrontendParametersSatellite.FEC_7_8, "7/8"),
			(eDVBFrontendParametersSatellite.FEC_8_9, "8/9"),
			(eDVBFrontendParametersSatellite.FEC_9_10, "9/10")])
		self.scan_sat.modulation = ConfigSelection(default = defaultSat["modulation"], choices = [
			(eDVBFrontendParametersSatellite.Modulation_QPSK, "QPSK"),
			(eDVBFrontendParametersSatellite.Modulation_8PSK, "8PSK")])
		self.scan_sat.rolloff = ConfigSelection(default = defaultSat.get("rolloff", eDVBFrontendParametersSatellite.RollOff_alpha_0_35), choices = [
			(eDVBFrontendParametersSatellite.RollOff_alpha_0_35, "0.35"),
			(eDVBFrontendParametersSatellite.RollOff_alpha_0_25, "0.25"),
			(eDVBFrontendParametersSatellite.RollOff_alpha_0_20, "0.20"),
			(eDVBFrontendParametersSatellite.RollOff_auto, _("Auto"))])
		self.scan_sat.pilot = ConfigSelection(default = defaultSat.get("pilot", eDVBFrontendParametersSatellite.Pilot_Unknown), choices = [
			(eDVBFrontendParametersSatellite.Pilot_Off, _("Off")),
			(eDVBFrontendParametersSatellite.Pilot_On, _("On")),
			(eDVBFrontendParametersSatellite.Pilot_Unknown, _("Auto"))])

	def initialSetup(self):
		currtp = self.transponderToString([None, self.scan_sat.frequency.value, self.scan_sat.symbolrate.value, self.scan_sat.polarization.value])
		if currtp in self.tuning.transponder.choices:
			self.tuning.type.value = "predefined_transponder"
		else:
			self.tuning.type.value = "manual_transponder"

	def createSetup(self):
		self.list = []
		self.list.append(getConfigListEntry(_('Tune'), self.tuning.type))
		self.list.append(getConfigListEntry(_('Satellite'), self.tuning.sat))
		nim = nimmanager.nim_slots[self.feid]

		if self.tuning.type.value == "manual_transponder":
			if nim.isCompatible("DVB-S2"):
				self.list.append(getConfigListEntry(_('System'), self.scan_sat.system))
			else:
				# downgrade to dvb-s, in case a -s2 config was active
				self.scan_sat.system.value = eDVBFrontendParametersSatellite.System_DVB_S
			self.list.append(getConfigListEntry(_('Frequency'), self.scan_sat.frequency))
			self.list.append(getConfigListEntry(_("Polarisation"), self.scan_sat.polarization))
			self.list.append(getConfigListEntry(_('Symbol rate'), self.scan_sat.symbolrate))
			if self.scan_sat.system.value == eDVBFrontendParametersSatellite.System_DVB_S:
				self.list.append(getConfigListEntry(_("FEC"), self.scan_sat.fec))
				self.list.append(getConfigListEntry(_('Inversion'), self.scan_sat.inversion))
			elif self.scan_sat.system.value == eDVBFrontendParametersSatellite.System_DVB_S2:
				self.list.append(getConfigListEntry(_("FEC"), self.scan_sat.fec_s2))
				self.list.append(getConfigListEntry(_('Inversion'), self.scan_sat.inversion))
				self.modulationEntry = getConfigListEntry(_('Modulation'), self.scan_sat.modulation)
				self.list.append(self.modulationEntry)
				self.list.append(getConfigListEntry(_('Roll-off'), self.scan_sat.rolloff))
				self.list.append(getConfigListEntry(_('Pilot'), self.scan_sat.pilot))
		else: # "predefined_transponder"
			self.list.append(getConfigListEntry(_("Transponder"), self.tuning.transponder))
			currtp = self.transponderToString([None, self.scan_sat.frequency.value, self.scan_sat.symbolrate.value, self.scan_sat.polarization.value])
			self.tuning.transponder.setValue(currtp)
		self["config"].list = self.list
		self["config"].l.setList(self.list)

	def tuningSatChanged(self, *parm):
		self.updateTransponders()
		self.createSetup()

	def tuningTypeChanged(self, *parm):
		self.createSetup()

	def systemChanged(self, *parm):
		self.createSetup()

	def transponderToString(self, tr, scale = 1):
		if tr[3] == 0:
			pol = "H"
		elif tr[3] == 1:
			pol = "V"
		elif tr[3] == 2:
			pol = "CL"
		elif tr[3] == 3:
			pol = "CR"
		else:
			pol = "??"
		return str(tr[1] / scale) + "," + pol + "," + str(tr[2] / scale)

	def updateTransponders(self):
		if len(self.tuning.sat.choices):
			transponderlist = nimmanager.getTransponders(int(self.tuning.sat.value))
			tps = []
			for transponder in transponderlist:
				tps.append(self.transponderToString(transponder, scale = 1000))
			self.tuning.transponder = ConfigSelection(choices = tps)

	def keyLeft(self):
		ConfigListScreen.keyLeft(self)

	def keyRight(self):
		ConfigListScreen.keyRight(self)

	def keyGo(self):
		returnvalue = (0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
		satpos = int(self.tuning.sat.value)
		if self.tuning.type.value == "manual_transponder":
			if self.scan_sat.system.value == eDVBFrontendParametersSatellite.System_DVB_S2:
				fec = self.scan_sat.fec_s2.value
			else:
				fec = self.scan_sat.fec.value
			returnvalue = (
				self.scan_sat.frequency.value,
				self.scan_sat.symbolrate.value,
				self.scan_sat.polarization.value,
				fec,
				self.scan_sat.inversion.value,
				satpos,
				self.scan_sat.system.value,
				self.scan_sat.modulation.value,
				self.scan_sat.rolloff.value,
				self.scan_sat.pilot.value)
		elif self.tuning.type.value == "predefined_transponder":
			transponder = nimmanager.getTransponders(satpos)[self.tuning.transponder.index]
			returnvalue = (transponder[1] / 1000, transponder[2] / 1000,
				transponder[3], transponder[4], 2, satpos, transponder[5], transponder[6], transponder[8], transponder[9])
		self.close(returnvalue)

	def keyCancel(self):
		self.close(None)

class RotorNimSelection(Screen):
	skin = """
		<screen position="140,165" size="400,130" title="select Slot">
			<widget name="nimlist" position="20,10" size="360,100" />
		</screen>"""

	def __init__(self, session):
		Screen.__init__(self, session)

		nimlist = nimmanager.getNimListOfType("DVB-S")
		nimMenuList = []
		for x in nimlist:
			if len(nimmanager.getRotorSatListForNim(x)) != 0:
				nimMenuList.append((nimmanager.nim_slots[x].friendly_full_description, x))

		self["nimlist"] = MenuList(nimMenuList)

		self["actions"] = ActionMap(["OkCancelActions"],
		{
			"ok": self.okbuttonClick ,
			"cancel": self.close
		}, -1)

	def okbuttonClick(self):
		selection = self["nimlist"].getCurrent()
		self.session.open(PositionerSetup, selection[1])

def PositionerMain(session, **kwargs):
	nimList = nimmanager.getNimListOfType("DVB-S")
	if len(nimList) == 0:
		session.open(MessageBox, _("No positioner capable frontend found."), MessageBox.TYPE_ERROR)
	else:
		if session.nav.RecordTimer.isRecording():
			session.open(MessageBox, _("A recording is currently running. Please stop the recording before trying to configure the positioner."), MessageBox.TYPE_ERROR)
		else:
			usableNims = []
			for x in nimList:
				configured_rotor_sats = nimmanager.getRotorSatListForNim(x)
				if len(configured_rotor_sats) != 0:
					usableNims.append(x)
			if len(usableNims) == 1:
				session.open(PositionerSetup, usableNims[0])
			elif len(usableNims) > 1:
				session.open(RotorNimSelection)
			else:
				session.open(MessageBox, _("No tuner is configured for use with a diseqc positioner!"), MessageBox.TYPE_ERROR)

def PositionerSetupStart(menuid, **kwargs):
	if menuid == "scan":
		return [(_("Positioner setup"), PositionerMain, "positioner_setup", None)]
	else:
		return []

def Plugins(**kwargs):
	if (nimmanager.hasNimType("DVB-S")):
		return PluginDescriptor(name=_("Positioner setup"), description = _("Setup your positioner"), where = PluginDescriptor.WHERE_MENU, needsRestart = False, fnc = PositionerSetupStart)
	else:
		return []
