from Components.NimManager import nimmanager


# FIXME Do we need this ?
class ChannelNumbers:
	def __init__(self):
		pass

	def channel2frequency(self, channel, nim):
		frequency = 474000000
		description = self.getTunerDescription(nim)
		if "Europe" in description and "DVB-T" in description:
			if 5 <= channel <= 12:
				frequency = int((177500 + 7000 * (channel - 5)) * 1000)
			elif 21 <= channel <= 69:
				frequency = int((474000 + 8000 * (channel - 21)) * 1000)
		return frequency

	def getChannelNumber(self, frequency, nim):
		def getSign(offset, lower, upper):
			return "-" if offset < lower else "+" if offset > upper else ""

		channel = ""
		mhz = int(self.getMHz(frequency))
		description = self.getTunerDescription(nim)
		if "Europe" in description:
			if "DVB-T" in description:
				if 174 < mhz < 230:  # III
					channel = f"{(mhz - 174) // 7 + 5}{getSign((mhz + 1) % 7, 3, 4)}"
				elif 470 <= mhz < 863:  # IV,V
					channel = f"{(mhz - 470) // 8 + 21}{getSign((mhz + 2) % 8, 3.5, 4.5)}"
		elif "Australia" in description:
			sign = getSign((mhz + 1) % 7, 3, 4)
			if 174 < mhz < 202:  # CH6-CH9
				channel = f"{(mhz - 174) // 7 + 6}{sign}"
			elif 202 <= mhz < 209:  # CH9A
				channel = f"9A{sign}"
			elif 209 <= mhz < 230:  # CH10-CH12
				channel = f"{(mhz - 209) // 7 + 10}{sign}"
			elif 526 < mhz < 820:  # CH28-CH69
				channel = f"{(mhz - 526) // 7 + 28}{getSign((mhz - 1) % 7, 3, 4)}"
		return channel

	def getMHz(self, frequency):
		return frequency.split()[0] if str(frequency).endswith("MHz") else (frequency + 50000) / 100000 / 10.

	def getTunerDescription(self, nim):
		description = ""
		try:
			description = nimmanager.getTerrestrialDescription(nim)
		except Exception:
			print(f"[ChannelNumber] nimmanager.getTerrestrialDescription(nim) failed, nim: {nim}")
		return description

	def supportedChannels(self, nim):
		description = self.getTunerDescription(nim)
		return "Europe" in description and "DVB-T" in description


channelnumbers = ChannelNumbers()
