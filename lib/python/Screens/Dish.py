# -*- coding: utf-8 -*-
from Screens.Screen import Screen
from Components.BlinkingPixmap import BlinkingPixmapConditional
from Components.Pixmap import Pixmap
from Components.config import config, ConfigInteger
from Components.Label import Label
from Components.ServiceEventTracker import ServiceEventTracker
from Components.Sources.Boolean import Boolean
from enigma import eDVBSatelliteEquipmentControl, eTimer, iPlayableService, eServiceCenter, iServiceInformation
from Components.NimManager import nimmanager
from Components.Sources.FrontendStatus import FrontendStatus
from ServiceReference import ServiceReference

INVALID_POSITION = 9999
config.misc.lastrotorposition = ConfigInteger(INVALID_POSITION)

class Dish(Screen):
	STATE_HIDDEN = 0
	STATE_SHOWN  = 1
	def __init__(self, session):
		Screen.__init__(self, session)
		self["Dishpixmap"] = BlinkingPixmapConditional()
		self["Dishpixmap"].onVisibilityChange.append(self.DishpixmapVisibilityChanged)
		self["turnTime"] = Label("")
		self["posFrom"] = Label("")
		self["posGoto"] = Label("")
		self["From"] = Label(_("From :"))
		self["Goto"] = Label(_("Goto :"))
		self["Tuner"] = Label(_("Tuner :"))
		self["tunerName"] = Label("")
		self["turnSpeed"] = Label("")

		self.updateRotorSatList()
		self.rotorTimer = eTimer()
		self.rotorTimer.callback.append(self.updateRotorMovingState)
		self.turnTimer = eTimer()
		self.turnTimer.callback.append(self.turnTimerLoop)
		self.timeoutTimer = eTimer()
		self.timeoutTimer.callback.append(self.testIsTuned)

		self.showdish = config.usage.showdish.value
		config.usage.showdish.addNotifier(self.configChanged)
		self.configChanged(config.usage.showdish)

		self.rotor_pos = self.cur_orbpos = config.misc.lastrotorposition.value
		config.misc.lastrotorposition.addNotifier(self.rotorPositionChanged)
		self.turn_time = self.total_time = self.pmt_timeout = self.close_timeout = None
		self.cur_polar = 0
		self.__state = self.STATE_HIDDEN

		self.onShow.append(self.__onShow)
		self.onHide.append(self.__onHide)

		self.__event_tracker = ServiceEventTracker(screen=self,
			eventmap= {
				iPlayableService.evStart: self.__serviceStarted,
				iPlayableService.evTunedIn: self.__serviceTunedIn,
			})

	def updateRotorSatList(self):
		self.available_sat = []
		for x in nimmanager.nim_slots:
			for sat in nimmanager.getRotorSatListForNim(x.slot):
				if sat[0] not in self.available_sat:
					self.available_sat.append(sat[0])

	def updateRotorMovingState(self):
		moving = eDVBSatelliteEquipmentControl.getInstance().isRotorMoving()
		if moving:
			if self.cur_orbpos != INVALID_POSITION and self.cur_orbpos != config.misc.lastrotorposition.value:
				config.misc.lastrotorposition.value = self.cur_orbpos
				config.misc.lastrotorposition.save()
			if self.__state == self.STATE_HIDDEN:
				self.show()

	def turnTimerLoop(self):
		if self.total_time:
			self.turn_time -= 1
			self["turnTime"].setText(self.FormatTurnTime(self.turn_time))
			self.close_timeout -=1
			if self.close_timeout < 0:
				print "[Dish] timeout!"
				self.__toHide()

	def __onShow(self):
		self.__state = self.STATE_SHOWN

		prev_rotor_pos = self.rotor_pos
		self.rotor_pos = self.cur_orbpos
		self.total_time = self.getTurnTime(prev_rotor_pos, self.rotor_pos, self.cur_polar)
		self.turn_time = self.total_time
		self.close_timeout = round(self.total_time * 1.25) # aded 25%

		self["posFrom"].setText(self.OrbToStr(prev_rotor_pos))
		self["posGoto"].setText(self.OrbToStr(self.rotor_pos))
		self["tunerName"].setText(self.getTunerName())
		if self.total_time == 0:
			self["turnTime"].setText("")
			self["turnSpeed"].setText("")
		else:
			self["turnTime"].setText(self.FormatTurnTime(self.turn_time))
			self["turnSpeed"].setText(str(self.getTurningSpeed(self.cur_polar)) + chr(176) + _("/s"))

		self.turnTimer.start(1000, False)

	def __onHide(self):
		self.__state = self.STATE_HIDDEN
		self.turnTimer.stop()
		self.updateRotorSatList()

	def __serviceStarted(self):
		if self.__state == self.STATE_SHOWN:
			self.hide()
		if self.showdish == "off":
			return

		service = self.session.nav.getCurrentService()
		info = service and service.info()
		data = info and info.getInfoObject(iServiceInformation.sTransponderData)
		if not data or data == -1:
			return

		tuner_type = data.get("tuner_type")
		if tuner_type and "DVB-S" in tuner_type:
			cur_orbpos = data.get("orbital_position", INVALID_POSITION)
			if cur_orbpos in self.available_sat:
				self.cur_orbpos = cur_orbpos
				self.cur_polar  = data.get("polarization", 0)
				self.rotorTimer.start(500, False)

	def __toHide(self):
		self.rotorTimer.stop()
		self.timeoutTimer.stop()
		if self.__state == self.STATE_SHOWN:
			self.hide()

	def __serviceTunedIn(self):
		if self.close_timeout is not None:
			self.pmt_timeout = self.close_timeout
			self.timeoutTimer.start(500, False)

	def testIsTuned(self):
		if self.pmt_timeout >= 0:
			service = self.session.nav.getCurrentService()
			info = service and service.info()
			pmt = info and info.getInfo(iServiceInformation.sPMTPID)
			if pmt >= 0:
				print "[Dish] tuned, closing..."
				self.__toHide()
			else:
				self.pmt_timeout -= 0.5
		else:
			self.__toHide()
			print "[Dish] tuning failed"

	def dishState(self):
		return self.__state

	def configChanged(self, configElement):
		self.showdish = configElement.value
		if configElement.value == "off":
			self["Dishpixmap"].setConnect(lambda: False)
		else:
			self["Dishpixmap"].setConnect(eDVBSatelliteEquipmentControl.getInstance().isRotorMoving)

	def DishpixmapVisibilityChanged(self, state):
		if self.showdish == "flashing":
			if state:
				self["Dishpixmap"].show() # show dish picture
			else:
				self["Dishpixmap"].hide() # hide dish picture
		else:
			self["Dishpixmap"].show() # show dish picture

	def rotorPositionChanged(self, configElement=None):
		if self.cur_orbpos != config.misc.lastrotorposition.value != INVALID_POSITION:
			self.rotor_pos = self.cur_orbpos = config.misc.lastrotorposition.value

	def getTurnTime(self, start, end, pol=0):
		mrt = abs(start - end) if start and end else 0
		if mrt > 0:
			if mrt > 1800:
				mrt = 3600 - mrt
			if mrt % 10:
				mrt += 10
			mrt = round((mrt * 1000 / self.getTurningSpeed(pol) ) / 10000) + 3
		return mrt

	def getTurningSpeed(self, pol=0):
		tuner = self.getCurrentTuner()
		if tuner is not None:
			nimConfig = nimmanager.getNimConfig(tuner)
			if nimConfig.configMode.value == "simple":
				if "positioner" in nimConfig.diseqcMode.value:
					nim = config.Nims[tuner]
					if pol in (1, 3): # vertical
						return nim.turningspeedV.float
					return nim.turningspeedH.float
			elif nimConfig.configMode.value == "advanced":
				if self.cur_orbpos != INVALID_POSITION:
					satlist = nimConfig.advanced.sat.keys()
					if self.cur_orbpos in satlist:
						currSat = nimConfig.advanced.sat[self.cur_orbpos]
						lnbnum = int(currSat.lnb.value)
						currLnb = lnbnum and nimConfig.advanced.lnb[lnbnum]
						diseqcmode = currLnb and currLnb.diseqcMode.value or ""
						if diseqcmode == "1_2":
							if pol in (1, 3): # vertical
								return currLnb.turningspeedV.float
							return currLnb.turningspeedH.float
		if pol in (1, 3):
			return 1.0
		return 1.5

	def getCurrentTuner(self):
		service = self.session.nav.getCurrentService()
		feinfo = service and service.frontendInfo()
		tuner = feinfo and feinfo.getFrontendData()
		if tuner is not None:
			return tuner.get("tuner_number")
		return None

	def getTunerName(self):
		nr = self.getCurrentTuner()
		if nr is not None:
			nims = nimmanager.nimList()
			if nr < len(nims) and nr >= 0:
				return "".join(nims[nr].split(':')[:1])
			print "[Dish.py] bug hunting nr: %s\n" %nr
			print "[Dish.py] bug hunting nims:\n"
			print nims
			raise
#			return " ".join((_("Tuner"),str(nr)))
		return ""

	def OrbToStr(self, orbpos):
		if orbpos == INVALID_POSITION:
			return "N/A"
		if orbpos > 1800:
			orbpos = 3600 - orbpos
			return "%d.%d°W" % (orbpos/10, orbpos%10)
		return "%d.%d°E" % (orbpos/10, orbpos%10)

	def FormatTurnTime(self, time):
		t = abs(time)
		return "%s%02d:%02d" % (time < 0 and "- " or "", t/60%60, t%60)

class Dishpip(Dish, Screen):
	STATE_HIDDEN = 0
	STATE_SHOWN  = 1
	def __init__(self, session):
		Screen.__init__(self, session)
		self["Dishpixmap"] = Boolean(fixed=True, poll=1500)
		self["turnTime"] = Label("")
		self["posFrom"] = Label("")
		self["posGoto"] = Label("")
		self["From"] = Label(_("From :"))
		self["Goto"] = Label(_("Goto :"))
		self["tunerName"] = Label("")
		self["turnSpeed"] = Label("")
		self.updateRotorSatList()
		self.frontend = None
		self["Frontend"] = FrontendStatus(service_source = lambda: self.frontend, update_interval=1000)
		self.rotorTimer = eTimer()
		self.rotorTimer.timeout.get().append(self.updateRotorMovingState)
		self.turnTimer = eTimer()
		self.turnTimer.callback.append(self.turnTimerLoop)
		self.timeoutTimer = eTimer()
		self.timeoutTimer.callback.append(self.__toHide)
		self.rotor_pos = self.cur_orbpos = config.misc.lastrotorposition.value
		config.misc.lastrotorposition.addNotifier(self.RotorpositionChange)
		self.turn_time = self.total_time = None
		self.close_timeout = self.moving_timeout = self.cur_polar = 0
		self.__state = self.STATE_HIDDEN

		self.onShow.append(self.__onShow)
		self.onHide.append(self.__onHide)

	def RotorpositionChange(self, configElement=None):
		if self.cur_orbpos != config.misc.lastrotorposition.value != INVALID_POSITION:
			self.rotor_pos = self.cur_orbpos = config.misc.lastrotorposition.value

	def getRotorMovingState(self):
		return eDVBSatelliteEquipmentControl.getInstance().isRotorMoving()

	def updateRotorMovingState(self):
		moving = self.getRotorMovingState()
		if moving:
			if self.__state == self.STATE_HIDDEN:
				self.rotorTimer.stop()
				self.moving_timeout = 0
				self.show()
				if self.cur_orbpos != INVALID_POSITION and self.cur_orbpos != config.misc.lastrotorposition.value:
					config.misc.lastrotorposition.value = self.cur_orbpos
					config.misc.lastrotorposition.save()
		self.moving_timeout -= 1
		if not self.rotorTimer.isActive() and self.moving_timeout > 0:
			self.rotorTimer.start(1000, True)

	def turnTimerLoop(self):
		if self.total_time:
			self.turn_time -= 1
			self["turnTime"].setText(self.FormatTurnTime(self.turn_time))
			self.close_timeout -=1
			if self.close_timeout <= 3:
				self.__toHide()
			#elif not self.getRotorMovingState():
			#	self.turnTimer.stop()
			#	self.timeoutTimer.start(10000, True)
		else:
			if not self.getRotorMovingState():
				self.turnTimer.stop()
				self.timeoutTimer.start(3000, True)

	def startPiPService(self, ref=None):
		if self.__state == self.STATE_SHOWN:
			self.__toHide()
		if not config.usage.showdish.value or ref is None:
			return
		info = eServiceCenter.getInstance().info(ref)
		data = info and info.getInfoObject(ref, iServiceInformation.sTransponderData)
		if not data or data == -1:
			return
		tuner_type = data.get("tuner_type")
		if tuner_type and "DVB-S" in tuner_type:
			cur_orbpos = data.get("orbital_position", INVALID_POSITION)
			if cur_orbpos in self.available_sat:
				self.cur_orbpos = cur_orbpos
				self.cur_polar  = data.get("polarization", 0)
				self.moving_timeout = 3
				if not self.rotorTimer.isActive():
					self.rotorTimer.start(500, True)

	def __onShow(self):
		self.__state = self.STATE_SHOWN
		prev_rotor_pos = self.rotor_pos
		self.rotor_pos = self.cur_orbpos
		self.total_time = self.getTurnTime(prev_rotor_pos, self.rotor_pos, self.cur_polar)
		self.turn_time = self.total_time
		self.close_timeout = round(self.total_time * 1.25) # aded 25%
		self["posFrom"].setText(self.OrbToStr(prev_rotor_pos))
		self["posGoto"].setText(self.OrbToStr(self.rotor_pos))
		self["tunerName"].setText(self.getTunerName())
		if self.total_time == 0:
			self["turnTime"].setText("")
			self["turnSpeed"].setText("")
		else:
			self["turnTime"].setText(self.FormatTurnTime(self.turn_time))
			self["turnSpeed"].setText(str(self.getTurningSpeed(self.cur_polar)) + chr(176) + _("/s"))
		self.turnTimer.start(1000, False)

	def __onHide(self):
		self.__state = self.STATE_HIDDEN
		self.updateRotorSatList()

	def setHide(self):
		self.__toHide()

	def __toHide(self):
		self.rotorTimer.stop()
		self.turnTimer.stop()
		self.timeoutTimer.stop()
		self.close_timeout = self.moving_timeout = 0
		self.frontend = None
		if self.__state == self.STATE_SHOWN:
			self.hide()

	def getCurrentTuner(self):
		if hasattr(self.session, 'pipshown') and self.session.pipshown:
			service = self.session.pip.pipservice
			if service is False or service is None:
				return None
			self.frontend = service
			feinfo = service and service.frontendInfo()
			tuner = feinfo and feinfo.getFrontendData()
			if tuner is not None:
				return tuner.get("tuner_number")
		return None
