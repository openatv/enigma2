# -*- coding: utf-8 -*-
from Screens.Screen import Screen
from Components.BlinkingPixmap import BlinkingPixmapConditional
from Components.config import config, ConfigInteger
from Components.Label import Label
from Components.ServiceEventTracker import ServiceEventTracker
from enigma import eDVBSatelliteEquipmentControl, eTimer, iPlayableService
from enigma import eServiceCenter, iServiceInformation

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
		self["From"] = Label (_("From :"))
		self["Goto"] = Label (_("Goto :"))

		self.rotorTimer = eTimer()
		self.rotorTimer.callback.append(self.updateRotorMovingState)
		self.turnTimer = eTimer()
		self.turnTimer.callback.append(self.turnTimerLoop)
		self.showTimer = eTimer()
		self.showTimer.callback.append(self.hide)

		config.usage.showdish.addNotifier(self.configChanged)
		self.configChanged(config.usage.showdish)

		self.rotor_pos = self.cur_orbpos = config.misc.lastrotorposition.getValue()
		self.turn_time = self.total_time = None
		self.cur_polar = 0
		self.__state = self.STATE_HIDDEN

		self.onShow.append(self.__onShow)
		self.onHide.append(self.__onHide)

		self.__event_tracker = ServiceEventTracker(screen=self,
			eventmap= {
				iPlayableService.evStart: self.__serviceStarted,
				iPlayableService.evTunedIn: self.__serviceTuneEnd,
				iPlayableService.evTuneFailed: self.__serviceTuneEnd,
			})

	def updateRotorMovingState(self):
		moving = eDVBSatelliteEquipmentControl.getInstance().isRotorMoving()
		#if not moving:
		if moving:
			if self.__state == self.STATE_HIDDEN:
				self.show()
			#self.rotorTimer.start(500, True)
		else:
			if self.__state == self.STATE_SHOWN:
				#self.rotorTimer.stop()
				self.hide()

	def turnTimerLoop(self):
		self.turn_time -= 1
		self["turnTime"].setText(self.FormatTurnTime(self.turn_time))

	def __onShow(self):
		self.__state = self.STATE_SHOWN

		prev_rotor_pos = self.rotor_pos
		self.rotor_pos = self.cur_orbpos
		self.total_time = self.getTurnTime(prev_rotor_pos, self.rotor_pos, self.cur_polar)
		self.turn_time = self.total_time

		self["posFrom"].setText(self.OrbToStr(prev_rotor_pos))
		self["posGoto"].setText(self.OrbToStr(self.rotor_pos))
		self["turnTime"].setText(self.FormatTurnTime(self.turn_time))

		self.turnTimer.start(1000, False)

	def __onHide(self):
		self.__state = self.STATE_HIDDEN
		self.turnTimer.stop()

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
		if tuner_type and tuner_type.find("DVB-S") != -1:
			self.cur_orbpos = data.get("orbital_position", INVALID_POSITION)
			if self.cur_orbpos != INVALID_POSITION:
				config.misc.lastrotorposition.value = self.cur_orbpos
				config.misc.lastrotorposition.save()
			self.cur_polar  = data.get("polarization", 0)
			self.rotorTimer.start(500, False)

	def __serviceTuneEnd(self):
		self.rotorTimer.stop()
		if self.__state == self.STATE_SHOWN:
			#self.showTimer.start(25000, True)
			self.hide()

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

	def getTurnTime(self, start, end, pol=0):
		mrt = abs(start - end) if start and end else 0
		if mrt > 0:
			if (mrt > 1800):
				mrt = 3600 - mrt
			if (mrt % 10):
				mrt += 10
			( turningspeedH, turningspeedV ) = self.getTurningSpeed()
			if pol in (1, 3):	# vertical
				mrt = (mrt * 1000 / turningspeedV ) / 10000
			else:			# horizontal
				mrt = (mrt * 1000 / turningspeedH ) / 10000
		return mrt + 3

	def getTurningSpeed(self):
		tuner_number = self.currentTunerInfo().get("tuner_number")
		nim = config.Nims[tuner_number]
		return (nim.turningspeedH.float, nim.turningspeedV.float)

	def currentTunerInfo(self):
		service = self.session.nav.getCurrentService()
		feinfo = service and service.frontendInfo()
		return feinfo and feinfo.getFrontendData()

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
