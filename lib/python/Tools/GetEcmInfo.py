from Components.config import config
import os
import time

ECM_INFO = '/tmp/ecm.info'
EMPTY_ECM_INFO = _("Free To Air"),'0','0','0'

old_ecm_time = time.time()
info = {}
data = EMPTY_ECM_INFO

class GetEcmInfo:
	def pollEcmData(self):
		global data
		global old_ecm_time
		global info
		if not os.path.isfile(ECM_INFO):
			data = EMPTY_ECM_INFO
			info = {}
			return
		try:
			ecm_time = os.stat(ECM_INFO).st_mtime
		except:
			ecm_time = old_ecm_time
		if ecm_time != old_ecm_time:
			oecmi1 = info.get('ecminterval1','')
			oecmi0 = info.get('ecminterval0','')
			info = {}
			info['ecminterval2'] = oecmi1
			info['ecminterval1'] = oecmi0
			old_ecm_time = ecm_time
			try:
				file = open(ECM_INFO, 'rb')
				ecm = file.readlines()
				file.close()
			except:
				ecm = ''
			for line in ecm:
				d = line.split(':', 1)
				if len(d) > 1:
					info[d[0].strip()] = d[1].strip()
			data = self.getText()
			return
		info['ecminterval0'] = int(time.time()-ecm_time+0.5)
		return

	def getEcmData(self):
		self.pollEcmData()
		return data

	def getInfo(self, member, ifempty = ''):
		self.pollEcmData()
		return str(info.get(member, ifempty))

	def getText(self):
		# info is dictionary
		using = info.get('using', '')
		protocol = info.get('protocol', '')
		if using or protocol:
			if config.usage.show_cryptoinfo.getValue() == '0':
				self.textvalue = ' '
			elif config.usage.show_cryptoinfo.getValue() == '1':
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
			elif config.usage.show_cryptoinfo.getValue() == '2':
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
						share = open('/tmp/share.info', 'rb').readlines()
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
				if ecm[1].startswith('SysID'):
					info['prov'] = ecm[1].strip()[6:]
				if 'response' in info:
					self.textvalue = self.textvalue + " (0.%ss)" % info['response']
				if 'CaID 0x' in ecm[0] and 'pid 0x' in ecm[0]:
					info['caid'] = ecm[0][ecm[0].find('CaID 0x')+7:ecm[0].find(',')]
					info['pid'] = ecm[0][ecm[0].find('pid 0x')+6:ecm[0].find(' =')]
					info['provid'] = info.get('prov', '0')[:4]
			else:
				source = info.get('source', None)
				if source:
					# MGcam
					eEnc  = ""
					eCaid = ""
					eSrc = ""
					eTime = "0"
					for line in ecm:
						line = line.strip()
						if line.find('ECM') != -1:
							linetmp = line.split(' ')
							eEnc = linetmp[1]
							eCaid = linetmp[5][2:-1]
							continue
						if line.find('source') != -1:
							linetmp = line.split(' ')
							try:
								eSrc = linetmp[4][:-1]
								continue
							except:
								eSrc = linetmp[1]
								continue
						if line.find('msec') != -1:
							linetmp = line.split(' ')
							eTime = linetmp[0]
							continue
					self.textvalue = "(%s %s %.3f @ %s)" % (eEnc,eCaid,(float(eTime)/1000),eSrc)
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
