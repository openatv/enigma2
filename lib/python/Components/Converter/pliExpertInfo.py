#
#  Coded by Vali, updated by Mirakels for openpli
#

from enigma import iServiceInformation
from Components.Converter.Converter import Converter
from Components.Element import cached
from Components.config import config
from Tools.Transponder import ConvertToHumanReadable
from Poll import Poll

ECM_INFO = '/tmp/ecm.info'

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
		self.idnames = (
			( "0x100", "0x1FF","Seca"   ,"S" ),
			( "0x500", "0x5FF","Via"    ,"V" ),
			( "0x600", "0x6FF","Ideto"  ,"I" ),
			( "0x900", "0x9FF","NDS"    ,"Nd"),
			( "0xB00", "0xBFF","Conax"  ,"Co"),
			( "0xD00", "0xDFF","CryptoW","Cw"),
			("0x1700","0x17FF","Beta"   ,"B" ),
			("0x1800","0x18FF","Nagra"  ,"N" ))
	@cached
	
	def getText(self):
		service = self.source.service
		info = service and service.info()
		if not info:
			return ""	

		Ret_Text = ""
		Sec_Text = ""

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
		
		prvd = info.getInfoString(iServiceInformation.sProvider)
		Ret_Text = self.short(prvd)

		frontendDataOrg = (feinfo and feinfo.getAll(True))
		if (frontendDataOrg is not None):
			frontendData = ConvertToHumanReadable(frontendDataOrg)
			if ((frontendDataOrg.get("tuner_type") == "DVB-S") or (frontendDataOrg.get("tuner_type") == "DVB-C")):
				frequency = (str((frontendData.get("frequency") / 1000)))
				symbolrate = (str((frontendData.get("symbol_rate") / 1000)))
				fec_inner = frontendData.get("fec_inner")
				if (frontendDataOrg.get("tuner_type") == "DVB-S"):
					Ret_Text += sep + frontendData.get("system")
					Ret_Text += sep + frequency + frontendData.get("polarization")[:1]
					Ret_Text += sep + symbolrate
					Ret_Text += sep + frontendData.get("modulation") + "-" + fec_inner
					orbital_pos = int(frontendData["orbital_position"])
					if orbital_pos > 1800:
						orb_pos = str((float(3600 - orbital_pos)) / 10.0) + "W"
					elif orbital_pos > 0:
						orb_pos = str((float(orbital_pos)) / 10.0) + "E"
					Ret_Text += sep + orb_pos
				else:
					Ret_Text += sep + "DVB-C " + frequency + " MHz" + sep + fec_inner + sep + symbolrate
			elif (frontendDataOrg.get("tuner_type") == "DVB-T"):
				frequency = (str((frontendData.get("frequency") / 1000)))
				Ret_Text += sep + "DVB-T" + sep + "Frequency:" + sep + frequency + " MHz"

		if (feinfo is not None) and (xresol > 0):
			if (yresol > 580):
				Ret_Text += sep + "HD "
			else:
				Ret_Text += sep + "SD "
			Ret_Text += str(xresol) + "x" + str(yresol)

		if (info.getInfo(iServiceInformation.sIsCrypted) == 1):
			
			try:
				ecm = open(ECM_INFO, 'rb').readlines()
	                        ecminfo = {}
				for line in ecm:
					d = line.split(':', 1)
					if len(d) > 1:
						ecminfo[d[0].strip()] = d[1].strip()
				
				using = ecminfo.get('using', '')
				if using:
					# CCcam
					if using == 'fta':
						Sec_Text = _("FTA")
					elif using == 'emu':
						Sec_Text = "EMU (%ss)" % (ecminfo.get('ecm time', '?'))
					else:
						hops = ecminfo.get('hops', None)
						if hops and hops != '0':
							hops = ' @' + hops
						else:
							hops = ''
						Sec_Text = ecminfo.get('address', '?') + hops + " (%ss)" % ecminfo.get('ecm time', '?')
				else:
					decode = ecminfo.get('decode', None)
					if decode:
						# gbox (untested)
						if ecminfo['decode'] == 'Network':
							cardid = 'id:' + ecminfo.get('prov', '')
							try:
								share = open('/tmp/share.info', 'rb').readlines()
								for line in share:
									if cardid in line:
										Sec_Text = line.strip()
										break
								else:
									Sec_Text = cardid
							except:
								Sec_Text = decode
						else:
							Sec_Text = decode
					else:
						source = ecminfo.get('source', '')
						if source:
							# MGcam
							eEnc  = ""
							eCaid = ""
							eSrc = ""
							eTime = ""
							for line in ecm:
								line = line.strip() 
								if line.find('ECM') != -1:
									line = line.split(' ')
									eEnc = line[1]
									eCaid = line[5][2:-1]
									continue
								if line.find('source') != -1:
									line = line.split(' ')
									eSrc = line[4][:-1]
									continue
								if line.find('msec') != -1:
									line = line.split(' ')
									eTime = line[0]
									continue
							Sec_Text = "(%s %s %.3f @ %s)" % (eEnc,eCaid,(float(eTime)/1000),eSrc)
						else:
							reader = ecminfo.get('reader', '')
							if reader:
								#Oscam
								hops = ecminfo.get('hops', None)
								if hops and hops != '0':
									hops = ' @' + hops
								else:
									hops = ''
								Sec_Text = reader + hops + " (%ss)" % ecminfo.get('ecm time', '?')
							else:
								Sec_Text = ""
	
				pid = ecminfo.get('pid', None)
				decCI = ecminfo.get('caid', None)
				decCIfull=""
				if decCI != "":
					for idline in self.idnames:
						try:
							if decCI.upper() >= idline[0].upper() and decCI.upper() <= idline[1].upper():
								decCIfull = idline[2] + ":" + decCI
								break
						except:
							pass
			
				Sec_Text += sep + decCIfull + sep + "pid:" + pid
	
				res = ""			
				try:
					searchIDs = (info.getInfoObject(iServiceInformation.sCAIDs))
					for idline in self.idnames:
						color = "\c007?7?7?"
						for oneID in searchIDs:
							if (oneID >= int(idline[0], 16)) and (oneID <= int(idline[1], 16)):
								color="\c00????00"
								if oneID == int(decCI,16):
									color="\c0000??00"
									break
						res += color + idline[3] + " "
				except:
					pass
		
				Ret_Text += "\n" + res + "\c00?????? " + Sec_Text
			except:
				Ret_Text += "\n\c007?7?7?S V I Nd Co Cw B N" + "\c00?????? No expert cryptinfo available" 
				pass
		else:
			Ret_Text += "\n\c007?7?7?S V I Nd Co Cw B N" + "\c00?????? FTA"

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
