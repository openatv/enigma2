from Components.config import config
import os
import time

ECM_INFO = '/tmp/ecm.info'
EMPTY_ECM_INFO = ' ','0','0','0'

old_ecm_time = time.time()
info = {}
ecm = ''
data = EMPTY_ECM_INFO

class GetEcmInfo:
	def __init__(self):
		pass

	def pollEcmData(self):
		global data
		global old_ecm_time
		global info
		global ecm
		try:
			ecm_time = os.stat(ECM_INFO).st_mtime
		except:
			ecm_time = old_ecm_time
			data = EMPTY_ECM_INFO
			info = {}
			ecm = ''
		if ecm_time != old_ecm_time:
			oecmi1 = info.get('ecminterval1','')
			oecmi0 = info.get('ecminterval0','')
			info = {'ecminterval2': oecmi1, 'ecminterval1': oecmi0}
			old_ecm_time = ecm_time
			try:
				file = open(ECM_INFO, 'rb')
				ecm = file.readlines()
				file.close()
			except:
				ecm = ''
			info['caid'] = "0"
			info['eCaid'] = ""
			info['eEnc'] = ""
			info['eSrc'] = ""
			info['eTime'] = "0"
			info['pid'] = "0"
			info['prov'] = ""
			info['provid'] = "0"
			# print 'ECM DATA:',ecm
			for line in ecm:
				# print 'ECM LINE:',line
				d = line.split(':', 1)
				if len(d) > 1:
					info[d[0].strip()] = d[1].strip()
				mgcam = line.strip()
				if 'ECM' in line:
					linetmp = mgcam.split(' ')
					info['eEnc'] = linetmp[1]
					try:			
						info['eCaid'] = linetmp[5][2:-1]
					except:
						info['eCaid'] = ""
					continue
				if 'source' in line:
					linetmp = mgcam.split(' ')
					try:
						info['eSrc'] = linetmp[4][:-1]
						continue
					except:
						info['eSrc'] = linetmp[1]
						continue
				if 'msec' in line:
					linetmp = line.split(' ')
					info['eTime'] = linetmp[0]
					continue
				if 'SysID' in line:
					info['prov'] = line.strip()[6:]
					continue
				if 'CaID 0x' in line and 'pid 0x' in line:
					info['caid'] = line[line.find('CaID 0x')+7:line.find(',')]
					info['pid'] = line[line.find('pid 0x')+6:line.find(' =')]
					info['provid'] = info.get('prov', '0')[:4]
			data = self.getText()
			return True
		else:
			info['ecminterval0'] = int(time.time()-ecm_time+0.5)

	def getEcm(self):
		return (self.pollEcmData(), ecm)

	def getEcmData(self):
		self.pollEcmData()
		return data

	def getInfo(self, member, ifempty = ''):
		self.pollEcmData()
		return str(info.get(member, ifempty))

	def getText(self):
		global ecm
		# info is dictionary
		using = info.get('using', '')
		protocol = info.get('protocol', '')
		if using or protocol:
			if config.usage.show_cryptoinfo.value == '0':
				self.textvalue = ' '
			elif config.usage.show_cryptoinfo.value == '1':
				# CCcam
				if using == 'fta':
					self.textvalue = _("Free To Air")
				elif using == 'emu':
					self.textvalue = "EMU (%ss)" % (info.get('ecm time', '?'))
				else:
					if info.get('address', None):
						address = info.get('address', '')
					elif info.get('from', None):
						address = info.get('from', '')
					else:
						address = ''
					hops = info.get('hops', None)
					if hops and hops != '0':
						hops = ' @' + hops
					else:
						hops = ''
					self.textvalue = address + hops + " (%ss)" % info.get('ecm time', '?')
			elif config.usage.show_cryptoinfo.value == '2':
				# CCcam
				if using == 'fta':
					self.textvalue = _("Free To Air")
				else:
					address = _('Server:') + ' '
					if info.get('address', None):
						address += info.get('address', '')
					elif info.get('from', None):
						address += info.get('from', '')

					protocol = _('Protocol:') + ' '
					if info.get('protocol', None):
						protocol += info.get('protocol', '')

					hops = _('Hops:') + ' '
					if info.get('hops', None):
						hops += info.get('hops', '')

					ecm = _('Ecm:') + ' '
					if info.get('ecm time', None):
						ecm += info.get('ecm time', '')
					self.textvalue = address + '\n' + protocol + '  ' + hops + '  ' + ecm
		else:
			decode = info.get('decode', None)
			if decode:
				# gbox (untested)
				if info['decode'] == 'Network':
					cardid = 'id:' + info.get('prov', '')
					try:
						file = open('/tmp/share.info', 'rb')
						share = file.readlines()
						file.close()
						for line in share:
							if cardid in line:
								self.textvalue = line.strip()
								break
						else:
							self.textvalue = cardid
					except:
						self.textvalue = decode
				else:
					self.textvalue = decode
				if 'response' in info:
					self.textvalue += " (0.%ss)" % info['response']
			else:
				source = info.get('source', None)
				if source:
					# MGcam
					self.textvalue = "%s %s %.3f @ %s" % (info['eEnc'],info['eCaid'],(float(info['eTime'])/1000),info['eSrc'])
				else:
					reader = info.get('reader', '')
					if reader:
						hops = info.get('hops', None)
						if hops and hops != '0':
							hops = ' @' + hops
						else:
							hops = ''
						self.textvalue = reader + hops + " (%ss)" % info.get('ecm time', '?')
					else:
						self.textvalue = ""
		decCI = info.get('caid', '0')
		provid = info.get('provid', '0')
		if provid == '0':
			provid = info.get('prov', '0')
		ecmpid = info.get('pid', '0')
		return self.textvalue,decCI,provid,ecmpid
