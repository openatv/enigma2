# -*- coding: utf-8 -*-
from Converter import Converter
from Components.Element import cached
from Components.config import config
from Tools.Transponder import orbpos
from Components.NimManager import nimmanager
from enigma import eDVBSatelliteEquipmentControl

class RotorPosition(Converter, object):
	DEFAULT = 0
	WITH_TEXT = 1
	TUNER_NAME = 2

	def __init__(self, type):
		Converter.__init__(self, type)
		self.LastRotorPos = config.misc.lastrotorposition.value
		config.misc.lastrotorposition.addNotifier(self.forceChanged, initial_call=False)
		config.misc.showrotorposition.addNotifier(self.show_hide, initial_call=False)

	@cached
	def getText(self):
		if config.misc.showrotorposition.value != "no":
			self.LastRotorPos = config.misc.lastrotorposition.value
			(rotor, tuner) = self.isMotorizedTuner()
			if rotor:
				self.actualizeCfgLastRotorPosition()
				if config.misc.showrotorposition.value == "withtext":
					return _("Rotor: ") + orbpos(config.misc.lastrotorposition.value)
				if config.misc.showrotorposition.value == "tunername":
					active_tuner = self.getActiveTuner()
					if tuner != active_tuner:
						return _("%s:%s") % ("\c0000?0?0" + chr(ord("A")+ tuner), "\c00?0?0?0" + orbpos(config.misc.lastrotorposition.value))
					return ""
				return orbpos(config.misc.lastrotorposition.value)
		return ""

	text = property(getText)

	def isMotorizedTuner(self):
		for x in nimmanager.nim_slots:
			for sat in nimmanager.getRotorSatListForNim(x.slot):
				if sat[0]:
					return (True, x.slot)
		return (False, None)

	def actualizeCfgLastRotorPosition(self):
		if eDVBSatelliteEquipmentControl.getInstance().isRotorMoving():
			current_pos = eDVBSatelliteEquipmentControl.getInstance().getTargetOrbitalPosition()
			if current_pos != config.misc.lastrotorposition.value:
				self.LastRotorPos = config.misc.lastrotorposition.value = current_pos
				config.misc.lastrotorposition.save()

	def getActiveTuner(self):
		if not eDVBSatelliteEquipmentControl.getInstance().isRotorMoving():
			service = self.source.service
			feinfo = service and service.frontendInfo()
			tuner = feinfo and feinfo.getAll(True)
			if tuner:
				num = tuner.get("tuner_number")
				orb_pos = tuner.get("orbital_position")
				if isinstance(num, int) and orb_pos:
					satList = nimmanager.getRotorSatListForNim(num)
					for sat in satList:
						if sat[0] == orb_pos:
							return num
		return ""

	def forceChanged(self, configElement=None):
		if self.LastRotorPos != config.misc.lastrotorposition.value:
			Converter.changed(self, (self.CHANGED_ALL,))

	def show_hide(self, configElement=None):
		Converter.changed(self, (self.CHANGED_ALL,))
