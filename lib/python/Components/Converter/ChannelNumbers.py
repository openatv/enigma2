from Components.NimManager import nimmanager

class ChannelNumbers:

	def getChannelNumber(self, frequency, region):

		f = self.getMHz(frequency)
		reg = nimmanager.getTerrestrialDescription(region)

		if "Europe" in reg:
			if "DVB-T" in reg:
				if 174 < f < 230: 	# III
					d = (f + 1) % 7
					return str(int(f - 174)/7 + 5) + (d < 3 and "-" or d > 4 and "+" or "")
				elif 470 <= f < 863: 	# IV,V
					d = (f + 2) % 8
					return str(int(f - 470) / 8 + 21) + (d < 3.5 and "-" or d > 4.5 and "+" or "")

		elif "Australia" in reg:
			d = (f + 1) % 7
			ds = (d < 3 and "-" or d > 4 and "+" or "")
			if 174 < f < 202: 	# CH6-CH9
				return str(int(f - 174)/7 + 6) + ds
			elif 202 <= f < 209: 	# CH9A
				return "9A" + ds
			elif 209 <= f < 230: 	# CH10-CH12
				return str(int(f - 209)/7 + 6 - 1) + ds
			elif 526 < f < 820: 	# CH28-CH69
				return str(int(f - 526)/7 + 28) + ds

		return ""

	def getMHz(self, frequency):
		return (frequency+50000)/100000/10.

channelnumbers = ChannelNumbers()
