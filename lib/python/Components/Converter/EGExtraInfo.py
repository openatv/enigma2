# Based on PliExtraInfo
# Recoded for Black Pole by meo.
# Recodded for EGAMI

from enigma import iServiceInformation
from Components.Converter.Converter import Converter
from Components.Element import cached
from Poll import Poll


class EGExtraInfo(Poll, Converter, object):
	def __init__(self, type):
		Converter.__init__(self, type)
		Poll.__init__(self)

		self.type = type
		self.poll_interval = 1000
		self.poll_enabled = True
		self.caid_data = (
			("0x1700", "0x17ff", "Beta",    "B" ),
			( "0x600",  "0x6ff", "Irdeto",  "I" ),
			( "0x100",  "0x1ff", "Seca",    "S" ),
			( "0x500",  "0x5ff", "Via",     "V" ),
			("0x1800", "0x18ff", "Nagra",   "N" ),
			("0x4ae0", "0x4ae1", "Dre",     "D" ),
			( "0xd00",  "0xdff", "CryptoW", "CW"),
			( "0x900",  "0x9ff", "NDS",     "ND"),
			( "0xb00",  "0xbff", "Conax",   "CO"),
			("0x2600", "0x2600", "Biss",    "BI")
		)

	def GetEcmInfo(self):
		data = {}
		try:
			ecm = open('/tmp/ecm.info', 'rb').readlines()
			info = {}
			for line in ecm:
				d = line.split(':', 1)
				if len(d) > 1:
					info[d[0].strip()] = d[1].strip()
			
			data['caid'] = info.get('caid', '0')
			data['provider'] = info.get('provider', '')
			if data['provider'] == '':
				data['provider'] = info.get('prov', ' ')
			data['using'] = info.get('using', '')
			data['decode'] = info.get('decode', '')
			data['source'] = info.get('source', '')
			data['reader'] = info.get('reader', '')
			data['address'] = info.get('address', 'Unknown')
			data['address_from'] = info.get('from', 'Unknown')
			data['hops'] = info.get('hops', '0')
			data['ecm_time'] = info.get('ecm time', '?')
		except:
			data['caid'] = '0x00'
			data['provider'] = ''
			data['using'] = ''
			data['decode'] = ''
			data['source'] = ''
			data['reader'] = ''
			data['address'] = ''
			data['address_from'] = ''
			data['hops'] = '0'
			data['ecm_time'] = '0'
			
		return data
	
	def get_caName(self):
		try:
			f = open("/etc/egami/.emuname",'r')
 			name = f.readline().strip()
 			f.close()
		except:
			name = "Common Interface"
		return name
		
	@cached
	def getText(self):
		service = self.source.service
		if service is None:
			return ""
		info = service and service.info()
		is_crypted = info.getInfo(iServiceInformation.sIsCrypted)
		
		if self.type == "CamName":
			return self.get_caName()
		
		elif self.type == "NetInfo":
			if is_crypted != 1:
				return ''
			data = self.GetEcmInfo()
			if data['using']:
				return "Address: %s   Hops: %s   Ecm time: %ss" % (data['address'], data['hops'], data['ecm_time'])
			elif data['reader']:
				return "Address: %s   Hops: %s   Ecm time: %ss" % (data['address_from'], data['hops'], data['ecm_time'])
				
		elif self.type == "EcmInfo":
			if is_crypted != 1:
				return ''
			data = self.GetEcmInfo()
			return "CaId: %s     Provider: %s" % (data['caid'], data['provider'])
			
		elif self.type == "E-C-N":
			if is_crypted != 1:
				return 'Fta'
			data = self.GetEcmInfo()
			if data['using']:
				if data['using'] == "fta":
					return 'Fta'
				elif data['using'] == 'emu':
					return "Emulator"
				elif data['using'] == 'sci':
					return "Card"
				else:
					return "Network"
			elif data['reader']:
				pos = data['address_from'].find('.')
				if pos > 1:
					return "Network"
				else:
					return "Card"
			return ""
		
		elif self.type == "CryptoBar":
			data = self.GetEcmInfo()
			res = ""
			available_caids = info.getInfoObject(iServiceInformation.sCAIDs)	
			for caid_entry in self.caid_data:
				if int(data['caid'], 16) >= int(caid_entry[0], 16) and int(data['caid'], 16) <= int(caid_entry[1], 16):
					color="\c0000??00"
				else:
					color = "\c007?7?7?"
					try:
						for caid in available_caids:
							if caid >= int(caid_entry[0], 16) and caid <= int(caid_entry[1], 16):
								color="\c00????00"
					except:
						pass

				if res: res += " "
				res += color + caid_entry[3]
		
			res += "\c00??????"
			return res
				
		return ""
			
	text = property(getText)

	@cached
	def getBool(self):
		service = self.source.service
		info = service and service.info()

		if not info:
			return False

		if self.type == "CryptoCaidSecaAvailable":
			request_caid = "S"
			request_selected = False
		elif self.type == "CryptoCaidViaAvailable":
			request_caid = "V"
			request_selected = False
		elif self.type == "CryptoCaidIrdetoAvailable":
			request_caid = "I"
			request_selected = False
		elif self.type == "CryptoCaidNDSAvailable":
			request_caid = "ND"
			request_selected = False
		elif self.type == "CryptoCaidConaxAvailable":
			request_caid = "CO"
			request_selected = False
		elif self.type == "CryptoCaidCryptoWAvailable":
			request_caid = "CW"
			request_selected = False
		elif self.type == "CryptoCaidBetaAvailable":
			request_caid = "B"
			request_selected = False
		elif self.type == "CryptoCaidNagraAvailable":
			request_caid = "N"
			request_selected = False
		elif self.type == "CryptoCaidBissAvailable":
			request_caid = "BI"
			request_selected = False
		elif self.type == "CryptoCaidDreAvailable":
			request_caid = "D"
			request_selected = False
		elif self.type == "CryptoCaidSecaSelected":
			request_caid = "S"
			request_selected = True
		elif self.type == "CryptoCaidViaSelected":
			request_caid = "V"
			request_selected = True
		elif self.type == "CryptoCaidIrdetoSelected":
			request_caid = "I"
			request_selected = True
		elif self.type == "CryptoCaidNDSSelected":
			request_caid = "ND"
			request_selected = True
		elif self.type == "CryptoCaidConaxSelected":
			request_caid = "CO"
			request_selected = True
		elif self.type == "CryptoCaidCryptoWSelected":
			request_caid = "CW"
			request_selected = True
		elif self.type == "CryptoCaidBetaSelected":
			request_caid = "B"
			request_selected = True
		elif self.type == "CryptoCaidNagraSelected":
			request_caid = "N"
			request_selected = True
		elif self.type == "CryptoCaidBissSelected":
			request_caid = "BI"
			request_selected = True
		elif self.type == "CryptoCaidDreSelected":
			request_caid = "D"
			request_selected = True
		else:
			return False

		if info.getInfo(iServiceInformation.sIsCrypted) != 1:
			return False

		data = self.GetEcmInfo()

		if data is None:
			return False

		current_caid	= data['caid']

		available_caids = info.getInfoObject(iServiceInformation.sCAIDs)

		for caid_entry in self.caid_data:
			if caid_entry[3] == request_caid:
				if(request_selected):
					if int(current_caid, 16) >= int(caid_entry[0], 16) and int(current_caid, 16) <= int(caid_entry[1], 16):
						return True
				else: # request available
					try:
						for caid in available_caids:
							if caid >= int(caid_entry[0], 16) and caid <= int(caid_entry[1], 16):
								return True
					except:
						pass

		return False

	boolean = property(getBool)
	
	