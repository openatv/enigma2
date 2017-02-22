from GUIComponent import GUIComponent

from enigma import eLabel, eSlider, iFrontendInformation

from math import log

class TunerInfo(GUIComponent):
	SNR = 0
	SNR_DB = 1
	AGC = 2
	BER = 3
	SNR_PERCENTAGE = 0
	AGC_PERCENTAGE = 2
	BER_VALUE = 3
	SNR_BAR = 4
	AGC_BAR = 5
	BER_BAR = 6
	LOCK_STATE = 7
	SYNC_STATE = 8
	LOCK = 9

	def __init__(self, type, servicefkt = None, frontendfkt = None, statusDict = None):
		GUIComponent.__init__(self)
		self.instance = None
		self.message = None
		self.value = None
		self.servicefkt = servicefkt
		self.frontendfkt = frontendfkt
		self.statusDict = statusDict
		self.type = type
		self.update()

	def setText(self, text):
		self.message = text
		if self.instance:
			self.instance.setText(self.message)

	def setValue(self, value):
		self.value = value
		if self.instance:
			self.instance.setValue(self.value)

	def calc(self,val):
		if not val:
			return 0
		if val < 2500:
			return long(log(val)/log(2))
		return val*100/65535

	def update(self):
		if self.type == self.SNR_DB:
			value = self.getValue(self.SNR_DB)
		elif self.type == self.SNR_PERCENTAGE or self.type == self.SNR_BAR:
			value = self.getValue(self.SNR) * 100 / 65535
		elif self.type == self.AGC_PERCENTAGE or self.type == self.AGC_BAR:
			value = self.getValue(self.AGC) * 100 / 65535
		elif self.type == self.BER_VALUE or self.type == self.BER_BAR:
			value = self.getValue(self.BER)
		elif self.type == self.LOCK_STATE:
			value = self.getValue(self.LOCK)

		if self.type == self.SNR_DB:
			if value is not None and value != 0x12345678:
				self.setText("%3.02f dB" % (value / 100.0))
			else:
				self.setText("")
		elif self.type == self.SNR_PERCENTAGE or self.type == self.AGC_PERCENTAGE:
			self.setText("%d%%" % value)
		elif self.type == self.BER_VALUE:
			self.setText("%d" % value)
		elif self.type == self.SNR_BAR or self.type == self.AGC_BAR:
			self.setValue(value)
		elif self.type == self.BER_BAR:
			self.setValue(self.calc(value))
		elif self.type == self.LOCK_STATE:
			if value == 1:
				self.setText(_("locked"))
			else:
				self.setText(_("not locked"))

	def getValue(self, what):
		if self.statusDict:
			if what == self.SNR_DB:
				return self.statusDict.get("tuner_signal_quality_db", 0x12345678)
			elif what == self.SNR:
				return self.statusDict.get("tuner_signal_quality", 0)
			elif what == self.AGC:
				return self.statusDict.get("tuner_signal_power", 0)
			elif what == self.BER:
				return self.statusDict.get("tuner_bit_error_rate", 0)
			elif what == self.LOCK:
				return self.statusDict.get("tuner_locked", 0)
		elif self.servicefkt:
			service = self.servicefkt()
			if service is not None:
				feinfo = service.frontendInfo()
				if feinfo is not None:
					if what == self.SNR_DB:
						return feinfo.getFrontendInfo(iFrontendInformation.signalQualitydB)
					elif what == self.SNR:
						return feinfo.getFrontendInfo(iFrontendInformation.signalQuality)
					elif what == self.AGC:
						return feinfo.getFrontendInfo(iFrontendInformation.signalPower)
					elif what == self.BER:
						return feinfo.getFrontendInfo(iFrontendInformation.bitErrorRate)
					elif what == self.LOCK:
						return feinfo.getFrontendInfo(iFrontendInformation.lockState)
		elif self.frontendfkt:
			frontend = self.frontendfkt()
			if frontend:
				if what == self.SNR_DB:
					return frontend.readFrontendData(iFrontendInformation.signalQualitydB)
				elif what == self.SNR:
					return frontend.readFrontendData(iFrontendInformation.signalQuality)
				elif what == self.AGC:
					return frontend.readFrontendData(iFrontendInformation.signalPower)
				elif what == self.BER:
					return frontend.readFrontendData(iFrontendInformation.bitErrorRate)
				elif what == self.LOCK:
					return frontend.readFrontendData(iFrontendInformation.lockState)
		return 0

	def createWidget(self, parent):
		if self.SNR_PERCENTAGE <= self.type <= self.BER_VALUE or self.type == self.LOCK_STATE:
			return eLabel(parent)
		elif self.SNR_BAR <= self.type <= self.BER_BAR:
			self.g = eSlider(parent)
			self.g.setRange(0, 100)
			return self.g

	def postWidgetCreate(self, instance):
		if instance is None:
			return
		if self.message is not None:
			instance.setText(self.message)
		elif self.value is not None:
			instance.setValue(self.value)
