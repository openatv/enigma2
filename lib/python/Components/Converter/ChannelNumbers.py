from Components.NimManager import nimmanager
import Tools.Transponder

class ChannelNumbers:

	def __init__(self):
		pass

	def getChannelNumber(self, frequency, nim):
		return Tools.Transponder.getChannelNumber(frequency, nim)

	def getMHz(self, frequency):
		return Tools.Transponder.getMHz(frequency)

	def getTunerDescription(self, nim):
		return Tools.Transponder.getTunerDescription(nim)

	def supportedChannels(self, nim):
		return Tools.Transponder.supportedChannels(nim)

	def channel2frequency(self, channel, nim):
		return Tools.Transponder.channel2frequency(channel, nim)

channelnumbers = ChannelNumbers()
