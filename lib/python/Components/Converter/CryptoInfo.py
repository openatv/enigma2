from Components.Converter.Converter import Converter
from Components.Element import cached
from Components.config import config
from Tools.GetEcmInfo import GetEcmInfo 
from Poll import Poll


class CryptoInfo(Poll, Converter, object):
	def __init__(self, type):
		Converter.__init__(self, type)
		Poll.__init__(self)

		self.active = False
		self.visible = config.usage.show_cryptoinfo.value
		self.textvalue = ""
		self.poll_interval = 1000
		self.poll_enabled = True
		self.ecmdata = GetEcmInfo()
		
	@cached
	def getText(self):
		if not config.usage.show_cryptoinfo.value:
			self.visible = False
			return ''
		self.visible = True
		data = self.ecmdata.getEcmData()
		return data[0]
	text = property(getText)
