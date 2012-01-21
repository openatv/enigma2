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
				else:
					source = info.get('source', '')
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
		except:
			ecm = None
			self.textvalue = ""
			decCI='0'
			provid='0'
			ecmpid='0'
		return self.textvalue,decCI,provid,ecmpid
