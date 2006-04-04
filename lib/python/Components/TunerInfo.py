from GUIComponent import GUIComponent

from enigma import eLabel, eSlider, iFrontendStatusInformation

from math import log

class TunerInfo(GUIComponent):
	SNR_PERCENTAGE = 0
	AGC_PERCENTAGE = 1
	BER_VALUE = 2
	SNR_BAR = 3
	AGC_BAR = 4
	BER_BAR = 5
	LOCK_STATE = 6
	SYNC_STATE = 7
	def __init__(self, type, servicefkt):
		GUIComponent.__init__(self)
		self.instance = None
		self.message = None
		self.value = None
		
		self.servicefkt = servicefkt
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
		service = self.servicefkt()
		value = 0
		if service is not None:
			feinfo = service.frontendStatusInfo()
			if feinfo is not None:
				if self.type == self.SNR_PERCENTAGE or self.type == self.SNR_BAR:
					value = feinfo.getFrontendInfo(iFrontendStatusInformation.signalPower) * 100 / 65536
				elif self.type == self.AGC_PERCENTAGE or self.type == self.AGC_BAR:
					value = feinfo.getFrontendInfo(iFrontendStatusInformation.signalQuality) * 100 / 65536
				elif self.type == self.BER_VALUE or self.type == self.BER_BAR:
					value = feinfo.getFrontendInfo(iFrontendStatusInformation.bitErrorRate)
				elif self.type == self.LOCK_STATE:
					value = feinfo.getFrontendInfo(iFrontendStatusInformation.LockState)
		
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
				
	def createWidget(self, parent):
		if self.SNR_PERCENTAGE <= self.type <= self.BER_VALUE or self.type == self.LOCK_STATE:
			return eLabel(parent)
		elif self.SNR_BAR <= self.type <= self.BER_BAR:
			self.g = eSlider(parent)
			self.g.setRange(0, 100)
			return self.g
		
	def GUIcreate(self, parent):
		self.instance = self.createWidget(parent)
		if self.message is not None:
			self.instance.setText(self.message)
		elif self.value is not None:
			self.instance.setValue(self.value)	

	def GUIdelete(self):
		self.removeWidget(self.instance)
		self.instance = None
	
	def removeWidget(self, instance):
		pass