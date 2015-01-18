from datasource import datasource

class lamedb(datasource):
	def __init__(self, filename = "lamedb"):
		datasource.__init__(self)
		self.setFilename(filename)

	def setFilename(self, filename):
		self.filename = filename

	def getName(self):
		return "lamedb"

	def getCapabilities(self):
		return [("read file", self.read), ("print all", self.printAll)]

	def read(self):
		inputfile = open(self.filename, "r")
		lines = inputfile.readlines()
		inputfile.close()

		versionstring = lines[0].split('/')
		version = int(versionstring[1])
		if 3 > version or 4 < version:
			print "unsupported lamedb version"
			return

		transpondersreading = False
		sats = {}
		transponders = {}
		for line in lines:
			if line.strip() == "transponders":
				transpondersreading = True
				continue
			if line.strip() == "services":
				transpondersreading = False
				continue
			if transpondersreading:
				if ord(line[0]) == 9:
					transponder = line.strip().split(' ')[1].split(':')
					sat = transponder[4]
					if not sats.has_key(sat):
						sats[sat] = []
					sats[sat].append((transponder, tsid, onid))
					tsid = None
					onid = None
				elif line.strip() != "/" and line.strip() != "end":
					data = line.strip().split(":")
					tsid = str(int(data[1], 16))
					onid = str(int(data[2], 16))
		satlist = sats.keys()
		satlist.sort()

		for sat in satlist:
			print sat
			self.addSat(sat, sat)
			transponders = sats[sat]
			transponders.sort(key = lambda a: a[0])
			for transpondertuple in transponders:
				transponder = transpondertuple[0]
				tsid = transpondertuple[1]
				onid = transpondertuple[2]
				print transponder, tsid, onid
				tmp_transponder = {"frequency": transponder[0], "symbol_rate": transponder[1], "polarization": transponder[2], "fec": transponder[3]}
				if version == 3:
					if len(transponder) > 6:
						tmp_transponder["system"] = transponder[6]
						tmp_transponder["modulation"] = transponder[7]
				elif version == 4:
					if len(transponder) > 7:
						tmp_transponder["system"] = transponder[7]
						tmp_transponder["modulation"] = transponder[8]
				if tsid != "1" or onid != "1":
					tmp_transponder["tsid"] = transponder[0]
					tmp_transponder["onid"] = transponder[0]
				self.addTransponder(sat, tmp_transponder)
