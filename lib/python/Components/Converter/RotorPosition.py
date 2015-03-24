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
		if type == "WithText":
			self.type = self.WITH_TEXT
		if type == "TunerName":
			self.type = self.TUNER_NAME
		else:
			self.type = self.DEFAULT

	@cached
	def getText(self):
		(rotor, tuner) = self.isMotorizedTuner()
		if rotor:
			self.actualizeCfgLastRotorPosition()
			if self.type == self.WITH_TEXT:
				return _("Rotor: ") + orbpos(config.misc.lastrotorposition.value)
			if self.type == self.TUNER_NAME:
				active_tuner = self.getActiveTuner()
				if tuner != active_tuner:
					return _("%s:%s") % (chr(ord("A")+tuner), orbpos(config.misc.lastrotorposition.value))
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
			config.misc.lastrotorposition.value = eDVBSatelliteEquipmentControl.getInstance().getTargetOrbitalPosition()
			config.misc.lastrotorposition.save()

	def getActiveTuner(self):
		if not eDVBSatelliteEquipmentControl.getInstance().isRotorMoving():
			service = self.source.service
			feinfo = service and service.frontendInfo()
			tuner = feinfo and feinfo.getFrontendData()
			if tuner:
				return tuner.get("tuner_number")
		return ""