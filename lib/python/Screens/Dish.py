# -*- coding: utf-8 -*-
from Screen import Screen
from Components.BlinkingPixmap import BlinkingPixmapConditional
from Components.Pixmap import Pixmap
from Components.config import config, ConfigInteger
from Components.Sources.Boolean import Boolean
from Components.Label import Label
from Components.ProgressBar import ProgressBar
from Components.ServiceEventTracker import ServiceEventTracker
from enigma import eDVBSatelliteEquipmentControl, eTimer, eComponentScan, iPlayableService
from enigma import eServiceCenter, iServiceInformation
from ServiceReference import ServiceReference

INVALID_POSITION = 9999
config.misc.lastrotorposition = ConfigInteger(INVALID_POSITION)

class Dish(Screen):
	STATE_HIDDEN = 0
	STATE_SHOWN  = 1
	skin = """
		<screen name="Dish" flags="wfNoBorder" position="86,100" size="130,200" title="Dish" zPosition="1" backgroundColor="#11396D" >
			<widget name="Dishpixmap" position="0,0"  size="130,160" zPosition="-1" pixmap="skin_default/icons/dish.png" transparent="1" alphatest="on" />
			<widget name="turnTime"   position="5,0"   size="120,20" zPosition="1" font="Regular;20" halign="right" shadowColor="black" shadowOffset="-2,-2" transparent="1" />
			<widget name="From"       position="5,164"  size="50,17" zPosition="1" font="Regular;17" halign="left"  shadowColor="black" shadowOffset="-2,-1" transparent="1"  />
			<widget name="posFrom"    position="57,160" size="70,20" zPosition="1" font="Regular;20" halign="left"  shadowColor="black" shadowOffset="-2,-2" transparent="1" />
			<widget name="Goto"       position="5,184"  size="50,17" zPosition="1" font="Regular;17" halign="left"  shadowColor="black" shadowOffset="-2,-1" transparent="1" />
			<widget name="posGoto"    position="57,180" size="70,20" zPosition="1" font="Regular;20" halign="left"  shadowColor="black" shadowOffset="-2,-2" transparent="1" />
		</screen>"""

	def __init__(self, session):
		self.skin = Dish.skin
		Screen.__init__(self, session)

		self["Dishpixmap"] = Pixmap()
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

		self.rotor_pos = self.cur_orbpos = config.misc.lastrotorposition.value
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
		if not self.showdish:
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

	def getTurnTime(self, start, end, pol=0):
		mrt = abs(start - end) if start and end else 0
		if mrt > 0:
			if (mrt > 1800):
				mrt = 3600 - mrt
			if (mrt % 10):
				mrt += 10
			#mrt = (mrt * 2000) / 10000 + 3	# 0.5° per second
			if pol in (1, 3):	# vertical
				mrt = (mrt * 1000) / 10000 + 3	# 1.0° per second
			else:	# horizontal
				mrt = (mrt * 667) / 10000 + 3	# 1.5° per second
		return mrt

	def OrbToStr(self, orbpos):
		if orbpos == INVALID_POSITION:
			return "N/A"
		if orbpos > 1800:
			orbpos = 3600 - orbpos
			return "%d.%d°W" % (orbpos/10, orbpos%10)
		return "%d.%d°E" % (orbpos/10, orbpos%10)

	def FormatTurnTime(self, time):
		t = abs(time)
		return "%s%02d:%02d:%02d" % (time < 0 and "- " or "", t/3600%24, t/60%60, t%60)
