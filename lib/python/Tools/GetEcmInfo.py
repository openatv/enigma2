from Components.config import config
import os

ECM_INFO = '/tmp/ecm.info'

old_ecm_mtime = None
data = None

class GetEcmInfo:
	def getEcmData(self):
		global old_ecm_mtime
		global data
		try:
			ecm_mtime = os.stat(ECM_INFO).st_mtime
		except:
			ecm_mtime = None
		if ecm_mtime != old_ecm_mtime:
			old_ecm_mtime = ecm_mtime
			data = self.getText()
		if data == None:
			return _("Free To Air"),'0','0','0'
		return data

	def getText(self):
		try:
			ecm = open(ECM_INFO, 'rb').readlines()
			info = {}
			for line in ecm:
				d = line.split(':', 1)
				if len(d) > 1:
					info[d[0].strip()] = d[1].strip()
			# info is dictionary
		except:
			ecm = None
			self.textvalue = _("Free To Air")
			decCI='0'
			provid='0'
			ecmpid='0'
			return self.textvalue,decCI,provid,ecmpid
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
				if info['response'] and 'CaID 0x' in ecm[0] and 'pid 0x' in ecm[0]:
					self.textvalue = self.textvalue + " (0.%ss)" % info['response']
					info['caid'] = ecm[0][ecm[0].find('CaID 0x')+7:ecm[0].find(',')]
					info['pid'] = ecm[0][ecm[0].find('pid 0x')+6:ecm[0].find(' =')]
					info['provid'] = info.get('prov', '0')[:4]
			else:
				source = info.get('source', None)
				if source:
					# MGcam
					info['caid'] = info['caid'][2:]
					info['pid'] = info['pid'][2:]
					info['provid'] = info['prov'][2:]
					time = " ?"
					for line in ecm:
						if line.find('msec') != -1:
							line = line.split(' ')
							if line[0]:
								time = " (%ss)" % (float(line[0])/1000)
								continue
					self.textvalue = source + time
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
