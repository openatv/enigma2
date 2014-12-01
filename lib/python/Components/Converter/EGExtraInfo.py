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
			f = open('/tmp/ecm.info', 'rb')
			ecm = f.readlines()
			f.close()
			info = {}
			for line in ecm:
				d = line.split(':', 1)
				if len(d) > 1:
					info[d[0].strip()] = d[1].strip()
			# 1st values
			data['caid'] = '0x00'
			data['pid'] = ''
			data['provider'] = ''
			data['using'] = ''
			data['decode'] = ''
			data['source'] = ''
			data['reader'] = ''
			data['address'] = ''
			data['address_from'] = ''
			data['hops'] = '0'
			data['ecm_time'] = '0'

			data['caid'] = info.get('caid', '0')
			data['provider'] = info.get('provider', '')
			if data['provider'] == '':
				data['provider'] = info.get('prov', ' ')

			data['using'] = info.get('using', '')
			data['reader'] = info.get('reader', '')
			## CCcam
			if data['using']:
				data['using'] = info.get('using', '')
				data['decode'] = info.get('decode', '')
				data['source'] = info.get('source', '')
				data['reader'] = info.get('reader', '')
				data['address'] = info.get('address', 'Unknown')
				data['address_from'] = info.get('from', 'Unknown')
				data['hops'] = info.get('hops', '0')
				data['ecm_time'] = info.get('ecm time', '?')
			elif data['reader']:
				data['caid'] = info.get('caid', '')
				data['pid'] = info.get('pid', '')
				data['provider'] = info.get('prov', '')
				data['reader'] = info.get('reader', '')
				data['address'] = info.get('from', 'Unknown')
				data['hops'] = info.get('hops', '0')
				data['ecm_time'] = info.get('ecm time', '?')
			else:
				data['decode'] = info.get('decode', '')
				if data['decode']:
					# gbox (untested)
					if data['decode'] == 'Network':
						cardid = 'id:' + info.get('prov', '')
						try:
							f = open('/tmp/share.info', 'rb')
							share = f.readlines()
							f.close()
							for line in share:
								if cardid in line:
									data['address'] = line.strip()
									break
							else:
								data['address'] = cardid
						except:
							data['address'] = data['decode']
					else:
						# adddess = slot or emu
						data['address'] = data['decode']

					if ecm[1].startswith('SysID'):
						data['provider'] = ecm[1].strip()[6:]
					if 'CaID 0x' in ecm[0] and 'pid 0x' in ecm[0]:
						data['ecm_time'] = info.get('response', '?')
						data['caid'] = ecm[0][ecm[0].find('CaID 0x') + 7:ecm[0].find(',')]
						data['pid'] = ecm[0][ecm[0].find('pid 0x') + 6:ecm[0].find(' =')]
						data['provider'] = info.get('prov', '0')[:4]
				else:
					source = info.get('source', None)
					if source:
						print "Found Source"
						#wicardd
						if 'CaID 0x' in ecm[0] and 'pid 0x' in ecm[0]:
							data['caid'] = ecm[0][ecm[0].find('CaID 0x') + 7:ecm[0].find(',')]
							data['pid'] = ecm[0][ecm[0].find('pid 0x') + 6:ecm[0].find(' =')]
							data['provider'] = info.get('prov', '0')[2:]
						# MGcam
						else:
							data['caid'] = info['caid'][2:]
							data['pid'] = info['pid'][2:]
							data['provider'] = info['prov'][2:]
						time = " ?"
						for line in ecm:
							if line.find('msec') != -1:
								line = line.split(' ')
								if line[0]:
									time = " (%ss)" % (float(line[0]) / 1000)
									continue
						data['address'] = source
						data['ecm_time'] = time
					else:
						reader = info.get('reader', '')
						if reader:
							hops = info.get('hops', None)
							if hops and hops != '0':
								hops = ' @' + hops
							else:
								hops = ''
							data['hops'] = hops
							data['ecm_time'] = info.get('ecm time', '?')
							data['address'] = reader
						else:
							data['hops'] = ""
							data['ecm_time'] = ""
							data['address'] = ""
		except:
			data['caid'] = '0x00'
			data['provider'] = ''
			data['pid'] = ''
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
			f = open("/etc/egami/.emuname", 'r')
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
				return "Address: %s   Hops: %s   Ecm time: %ss" % (data['address'], data['hops'], data['ecm_time'])
			elif data['decode'] == "slot-1" or data['decode'] == "slot-2" or data['decode'] == "Network":
				return "Decode: %s   Ecm time: %s Pid: %s" % (data['address'], data['ecm_time'], data['pid'])
			elif data['address']:
				return "Address: %s   Ecm time: %s Pid: %s" % (data['address'], data['ecm_time'], data['pid'])

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
			elif data['decode']:
				if data['decode'] == 'Network':
					return 'Netowrk'
				elif data['decode'] == 'slot-1' or data['decode'] == 'slot-2':
					return 'Card'
			elif data['address']:
				if data['address'][:3] == "net":
					return 'Network'
				elif data['address'][:3] == "emu":
					return 'Emulator'
				else:
					return 'Fta'
			return ""

		elif self.type == "CryptoBar":
			data = self.GetEcmInfo()
			res = ""
			available_caids = info.getInfoObject(iServiceInformation.sCAIDs)	
			for caid_entry in self.caid_data:
				if int(data['caid'], 16) >= int(caid_entry[0], 16) and int(data['caid'], 16) <= int(caid_entry[1], 16):
					color = "\c0000??00"
				else:
					color = "\c007?7?7?"
					try:
						for caid in available_caids:
							if caid >= int(caid_entry[0], 16) and caid <= int(caid_entry[1], 16):
								color = "\c00????00"
					except:
						pass

				if res:
					res += " "
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

		current_caid = data['caid']

		available_caids = info.getInfoObject(iServiceInformation.sCAIDs)

		for caid_entry in self.caid_data:
			if caid_entry[3] == request_caid:
				if(request_selected):
					if int(current_caid, 16) >= int(caid_entry[0], 16) and int(current_caid, 16) <= int(caid_entry[1], 16):
						return True
				else:  # request available
					try:
						for caid in available_caids:
							if caid >= int(caid_entry[0], 16) and caid <= int(caid_entry[1], 16):
								return True
					except:
						pass

		return False

	boolean = property(getBool)
