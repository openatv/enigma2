#
#  Coded by Vali, updated by Mirakels for openpli
#

from enigma import iServiceInformation
from Components.Converter.Converter import Converter
from Components.Element import cached
from Components.config import config
from Poll import Poll

class pliExpertInfo(Poll, Converter, object):
	SMART_LABEL = 0
	SMART_INFO_H = 1
	SMART_INFO_V = 2
	def __init__(self, type):
		Converter.__init__(self, type)
		Poll.__init__(self)
		self.type = {
				"ShowMe": self.SMART_LABEL,
				"ExpertInfo": self.SMART_INFO_H,
				"ExpertInfoVertical": self.SMART_INFO_V
			}[type]
		try:
			self.poll_interval = config.plugins.ValiKSSetup.pollTime.value*1000
		except:
			self.poll_interval = 30000
		self.poll_enabled = True
		self.ar_fec = ["Auto", "1/2", "2/3", "3/4", "5/6", "7/8", "3/5", "4/5", "8/9", "9/10","None","None","None","None","None"]
		self.ar_pol = ["H", "V", "CL", "CR", "na", "na", "na", "na", "na", "na", "na", "na"]
		self.idnames = ("0100,01FF,Seca,S","0500,05FF,Via,V","0600,06FF,Ideto,I","0900,09FF,NDS,Nd","0B00,0BFF,Conax,Co","0D00,0DFF,CryptoW,Cw","1700,17FF,BetaCr,B","1800,18FF,Nagra,N")

	@cached
	
	def getText(self):
		service = self.source.service
		info = service and service.info()
		if not info:
			return ""	
		Ret_Text = ""
		Sec_Text = ""
		decID = ""
		decCI = "0x000"
		decFrom = ""
		eMasTime = ""
		res = ""
		dccmd = ""
		searchIDs = []
		foundIDs = []
		xresol = info.getInfo(iServiceInformation.sVideoWidth)
		yresol = info.getInfo(iServiceInformation.sVideoHeight)
		feinfo = (service and service.frontendInfo())
		if (self.type == self.SMART_INFO_H): # HORIZONTAL
			sep = "  "
			sep2 = " - "
		elif (self.type == self.SMART_INFO_V): # VERTIKAL
			sep = "\n"
			sep2 = "\n"
		else:
			return ""	# unsupported orientation
		
		if (feinfo is not None) and (xresol > 0):
			if (yresol > 580):
				Ret_Text = "HD " 
			else:
				Ret_Text = "SD "
			Ret_Text += str(xresol) + "x" + str(yresol)
			frontendData = (feinfo and feinfo.getAll(True))
			if (frontendData is not None):
				if ((frontendData.get("tuner_type") == "DVB-S") or (frontendData.get("tuner_type") == "DVB-C")):
					frequency = (str((frontendData.get("frequency") / 1000)) + " MHz")
					symbolrate = (str((float(frontendData.get("symbol_rate")) / float(1000000))) + " MS/s")
					try:
						if (frontendData.get("tuner_type") == "DVB-S"):
							polarisation_i = frontendData.get("polarization")
						else:
							polarisation_i = 0
						fec_i = frontendData.get("fec_inner")
						Ret_Text += sep + frequency + " - " + self.ar_pol[polarisation_i] + sep2 + self.ar_fec[fec_i] + " - " + symbolrate 
					except:
						Ret_Text += sep + frequency + sep + symbolrate
					orb_pos = ""
					if (frontendData.get("tuner_type") == "DVB-S"):
						orbital_pos = int(frontendData["orbital_position"])
						if orbital_pos > 1800:
							orb_pos = str((float(3600 - orbital_pos)) / 10.0) + "W"
						elif orbital_pos > 0:
							orb_pos = str((float(orbital_pos)) / 10.0) + "E"
					Ret_Text += sep + "Pos: " + orb_pos
				elif (frontendData.get("tuner_type") == "DVB-T"):
					frequency = (str((frontendData.get("frequency") / 1000)) + " MHz")
					Ret_Text += sep + "Frequency:" + sep + frequency
			prvd = info.getInfoString(iServiceInformation.sProvider)
			Ret_Text = self.short(prvd) + sep + Ret_Text

		try:
			f = open("/tmp/ecm.info", "r")
			flines = f.readlines()
			f.close()
		except:
			Sec_Text = "secEmpty"
			flines = None

		if (flines is not None):
			ePid = ""
			decID = ""
			decFrom = ""
			eMasTime = ""
			eHops = ""
			for cell in flines:
				icell = cell.lower()
				cellmembers = cell.split()
				if ("caid" in icell):
					for x in range(len(cellmembers)):
						if ("caid" in cellmembers[x].lower()):
							if x<(len(cellmembers) - 1):
								if cellmembers[x+1] != "0x000":
									decID = cellmembers[x + 1]
									decID = decID.lstrip("0x")
									decID = decID.strip(",;.:-*_<>()[]{}")
									if (len(decID)<4):
										decID = "0" + decID
										decCI = decID
							break
				elif ("using:" in cell) or ("source:" in cell):
					for x in range(len(cellmembers)):
						if ("using:" in cellmembers[x]) or ("source:" in cellmembers[x]):
							if x < (len(cellmembers) - 1):
								if cellmembers[x + 1] != "fta":
									decFrom = cellmembers[x + 1]
							break
				elif ("ecm time:" in cell):
					for x in range(len(cellmembers)):
						if ("time:" in cellmembers[x]):
							if x < (len(cellmembers) - 1):
								eMasTime = str(cellmembers[x + 1])
							break
				elif ("address:" in cell):
					for x in range(len(cellmembers)):
						if ("address:" in cellmembers[x]):
							if x < (len(cellmembers) - 1):
								adrFrom = cellmembers[x + 1]
								if ("sci0" in adrFrom):
									decFrom = "Slot-1"
								elif ("sci1" in adrFrom):
									decFrom = "Slot-2"
								elif ("sci2" in adrFrom):
									decFrom = "Slot-3"
								else:
									decFrom = adrFrom
							break
				elif ("hops:" in cell):
					for x in range(len(cellmembers)):
						if ("hops:" in cellmembers[x]):
							if x<(len(cellmembers) - 1):
								eHops = str(cellmembers[x + 1])
							break
				elif ("pid:" in cell):
					for x in range(len(cellmembers)):
						if ("pid:" in cellmembers[x]):
							if x<(len(cellmembers) - 1):
								ePid = str(cellmembers[x + 1])
								ePid = ePid.lstrip("0x")
								if (len(ePid) == 3):
									ePid = "0" + ePid
								elif (len(ePid) == 2):
									ePid = "00" + ePid
								elif (len(ePid) == 1):
									ePid = "000" + ePid
								ePid = ePid.upper()
							break
			if decID != "":
				for idline in self.idnames:
					IDlist = idline.split(",")
					try:
						if (int(decID, 16) >= int(IDlist[0], 16)) and (int(decID, 16) <= int(IDlist[1], 16)):
							decID = IDlist[2] + ":" + decID.upper()
							break
					except:
						pass

			Sec_Text = self.short(decFrom) + sep + decID + sep + "pid: " + ePid + sep + eHops + " hops" + sep + eMasTime + " sec."

		try:
			searchIDs = (info.getInfoObject(iServiceInformation.sCAIDs))
			for oneID in searchIDs:
				for idline in self.idnames:
					IDlist = idline.split(",")
					if (oneID >= int(IDlist[0], 16)) and (oneID <= int(IDlist[1], 16)) and not(oneID == int(decCI, 16)):
						if not(IDlist[3] in foundIDs):
							foundIDs.append(IDlist[3]) #+ "(" +hex(oneID).lstrip("0x") + ")")
			res = " ".join(foundIDs)
		except:
			pass

		if (info.getInfo(iServiceInformation.sIsCrypted) == 1):
			Ret_Text += "\n" + self.short(res) + sep + Sec_Text

		return Ret_Text

	text = property(getText)

	def changed(self, what):
		Converter.changed(self, what)

	def short(self, langTxt):
		if (self.type == self.SMART_INFO_V and len(langTxt)>23):
			retT = langTxt[:20] + "..."
			return retT
		else:
			return langTxt
