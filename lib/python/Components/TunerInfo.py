from GUIComponent import GUIComponent

from enigma import eLabel, eSlider, iFrontendInformation

from math import log

class TunerInfo(GUIComponent):
	SNR = 0
	AGC = 1
	BER = 2
	LOCK = 3
	
	SNR_PERCENTAGE = 0
	AGC_PERCENTAGE = 1
	BER_VALUE = 2
	SNR_BAR = 3
	AGC_BAR = 4
	BER_BAR = 5
	LOCK_STATE = 6
	SYNC_STATE = 7
	def __init__(self, type, servicefkt = None, frontendfkt = None):
		GUIComponent.__init__(self)
		self.instance = None
		self.message = None
		self.value = None
		
		self.servicefkt = servicefkt
		self.frontendfkt = frontendfkt
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
			return (long)(log(val)/log(2))
		return val*100/65535
	
	def update(self):
		if self.type == self.SNR_PERCENTAGE or self.type == self.SNR_BAR:
			value = self.getValue(self.SNR) * 100 / 65536
		elif self.type == self.AGC_PERCENTAGE or self.type == self.AGC_BAR:
			value = self.getValue(self.AGC) * 100 / 65536
		elif self.type == self.BER_VALUE or self.type == self.BER_BAR:
			value = self.getValue(self.BER)
		elif self.type == self.LOCK_STATE:
			value = self.getValue(self.LOCK)
		
		if self.type == self.SNR_PERCENTAGE or self.type == self.AGC_PERCENTAGE:
			self.setText("%d%%" % (value))
		elif self.type == self.BER_VALUE:
			self.setText("%d" % (value))
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
		if self.servicefkt is not None:
			service = self.servicefkt()
			if service is not None:
				feinfo = service.frontendInfo()
				if feinfo is not None:
					if what == self.SNR:
						return feinfo.getFrontendInfo(iFrontendInformation.signalPower)
					elif what == self.AGC:
						return feinfo.getFrontendInfo(iFrontendInformation.signalQuality)
					elif what == self.BER:
						return feinfo.getFrontendInfo(iFrontendInformation.bitErrorRate)
					elif what == self.LOCK:
						return feinfo.getFrontendInfo(iFrontendInformation.lockState)
		elif self.frontendfkt is not None:
			frontend = self.frontendfkt()
			if frontend:
				if what == self.SNR:
					return frontend.readFrontendData(iFrontendInformation.signalPower)
				elif what == self.AGC:
					return frontend.readFrontendData(iFrontendInformation.signalQuality)
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
		if self.message is not None:
			instance.setText(self.message)
		elif self.value is not None:
			instance.setValue(self.value)
