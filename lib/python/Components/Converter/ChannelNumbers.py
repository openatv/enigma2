from Components.NimManager import nimmanager


class ChannelNumbers:

	def __init__(self):
		pass

	def getChannelNumber(self, frequency, nim):

		f = int(self.getMHz(frequency))
		descr = self.getTunerDescription(nim)

		if "Europe" in descr:
			if "DVB-T" in descr:
				if 174 < f < 230: 	# III
					d = (f + 1) % 7
					return str(int(f - 174) / 7 + 5) + (d < 3 and "-" or d > 4 and "+" or "")
				elif 470 <= f < 863: 	# IV,V
					d = (f + 2) % 8
					return str(int(f - 470) / 8 + 21) + (d < 3.5 and "-" or d > 4.5 and "+" or "")

		elif "Australia" in descr:
			d = (f + 1) % 7
			ds = (d < 3 and "-" or d > 4 and "+" or "")
			if 174 < f < 202: 	# CH6-CH9
				return str(int(f - 174) / 7 + 6) + ds
			elif 202 <= f < 209: 	# CH9A
				return "9A" + ds
			elif 209 <= f < 230: 	# CH10-CH12
				return str(int(f - 209) / 7 + 10) + ds
			elif 526 < f < 820: 	# CH28-CH69
				d = (f - 1) % 7
				return str(int(f - 526) / 7 + 28) + (d < 3 and "-" or d > 4 and "+" or "")

		return ""

	def getMHz(self, frequency):
		if str(frequency).endswith('MHz'):
			return frequency.split()[0]
		return (frequency + 50000) / 100000 / 10.

	def getTunerDescription(self, nim):
		description = ""
		try:
			description = nimmanager.getTerrestrialDescription(nim)
		except:
			print "[ChannelNumber] nimmanager.getTerrestrialDescription(nim) failed, nim:", nim
		return description

	def supportedChannels(self, nim):
		descr = self.getTunerDescription(nim)
		if "Europe" in descr and "DVB-T" in descr:
			return True
		return False

	def channel2frequency(self, channel, nim):
		descr = self.getTunerDescription(nim)
		if "Europe" in descr and "DVB-T" in descr:
			if 5 <= channel <= 12:
				return (177500 + 7000 * (channel - 5)) * 1000
			elif 21 <= channel <= 69:
				return (474000 + 8000 * (channel - 21)) * 1000
		return 474000000


channelnumbers = ChannelNumbers()
