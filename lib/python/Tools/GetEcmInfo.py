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
			return '','0','0','0'
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
			using = info.get('using', '')
			if using:
				# CCcam
				if using == 'fta':
					self.textvalue = _("FTA")
				elif using == 'emu':
					self.textvalue = "EMU (%ss)" % (info.get('ecm time', '?'))
				else:
					hops = info.get('hops', None)
					if hops and hops != '0':
						hops = ' @' + hops
					else:
						hops = ''
					self.textvalue = info.get('address', '?') + hops + " (%ss)" % info.get('ecm time', '?')
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
		except:
			ecm = None
			self.textvalue = ""
			decCI='0'
			provid='0'
			ecmpid='0'
		return self.textvalue,decCI,provid,ecmpid
