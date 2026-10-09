from Components.Converter.Converter import Converter
from Components.Converter.Poll import Poll
from Components.Element import cached
from Components.config import config
from Tools.GetEcmInfo import GetEcmInfo


class CryptoInfo(Poll, Converter):
	def __init__(self, tokens):
		Converter.__init__(self, tokens)
		Poll.__init__(self)
		self.type = tokens
		self.active = False  # TODO what's this
		self.visible = config.usage.show_cryptoinfo.value > 0
		self.textvalue = ""  # TODO what's this
		self.ecmdata = GetEcmInfo()

		def ShowCryptoInfo(configElement):
			if configElement.value > 0:
				self.poll_interval = 1000
				self.poll_enabled = True
			else:
				self.poll_enabled = False

		config.usage.show_cryptoinfo.addNotifier(ShowCryptoInfo)

	@cached
	def getText(self):
		if config.usage.show_cryptoinfo.value < 1:
			self.visible = False
			data = ""
		else:
			self.visible = True
			data = self.ecmdata.getEcmData()[0] if self.type == "VerboseInfo" else self.ecmdata.getInfo(self.type)
		return data

	text = property(getText)
