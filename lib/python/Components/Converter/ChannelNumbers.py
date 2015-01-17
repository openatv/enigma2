from Components.NimManager import nimmanager

class ChannelNumbers:

	def __init__(self):
		pass

# TODO: Need to figure out a sensible way of dealing with the Australian
#       requirement to support a +/- 125kHz optional offset for each channel

	def getChannelNumber(self, frequency, nim):
#		print "getChannelNumber", frequency
		res = None
		f = self.getMHz(frequency)
#		d = (f + 1.5) % 7
#		ds = (d < 4.0 and "-" or d > 4.0 and "+" or "")
		if 174 < f < 202:	 # CH6-CH9
			res = str(int(f - 174) / 7 + 6)
		elif 202 <= f < 209:	 # CH9A
			res = "9A"
		elif 209 <= f < 230:	 # CH10-CH12
			res = str(int(f - 209) / 7 + 10)
		elif 526 < f < 820:	 # CH28-CH69
#			d = (f - 0.5) % 7
#			ds = (d < 4.0 and "-" or d > 4.0 and "+" or "")
			res = str(int(f - 526) / 7 + 28)
#		print "converts to channel", res
		return res

	def getMHz(self, frequency):
		if str(frequency).lower().endswith('mhz'):
			return float(frequency.split()[0])
		return (frequency + 50000) / 100000 / 10.

	def getTunerDescription(self, nim):
		description = ""
		try:
			description = nimmanager.getTerrestrialDescription(nim)
		except:
			print "[ChannelNumber] nimmanager.getTerrestrialDescription(nim) failed, nim:", nim
		return description

	def supportedChannels(self, nim):
		return True

	def channel2frequency(self, channel, nim):
#		print "channel2frequency", channel
		res = 205500000
		if channel != "9A":
			ch = int(channel)
			if 6 <= ch <= 9:
				res = (177500 + 7000 * (ch - 6)) * 1000
			elif 10 <= ch <= 12:
				res = (212500 + 7000 * (ch - 10)) * 1000
			elif 28 <= ch <= 69:
				res = (529500 + 7000 * (ch - 28)) * 1000
#		print "converts to", res
		return res

channelnumbers = ChannelNumbers()
