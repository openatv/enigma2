from Components.Converter.Converter import Converter
from enigma import eTimer
from Components.Element import cached
from Components.config import config
import os

ECM_INFO = '/tmp/ecm.info'

class CryptoInfo(Converter, object):
	def __init__(self, type):
		Converter.__init__(self, type)
		# type is ignored, expected to be "verboseInfo"
		self.active = False
		self.visible = config.usage.show_cryptoinfo.value
		self.textvalue = ""
		self.clock_timer = eTimer()
		self.clock_timer.callback.append(self.poll)
		if self.visible:
			self.clock_timer.start(1000)
		self.ecm_mtime = None

	def destroy(self):
		self.clock_timer.callback.remove(self.poll)
		Converter.destroy(self)

	def poll(self):
		try:
			ecm_mtime = os.stat(ECM_INFO).st_mtime
		except:
			ecm_mtime = None
		if ecm_mtime != self.ecm_mtime:
			self.ecm_mtime = ecm_mtime
			self.changed((self.CHANGED_POLL,))

	def doSuspend(self, suspended):
		if suspended:
			self.clock_timer.stop()
		else:
			self.clock_timer.start(1000)
			self.poll()

	@cached
	def getText(self):
		if not self.visible:
			return ''
		# file changed.
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
		except:
			ecm = None
			self.textvalue = ""
		return self.textvalue

	text = property(getText)
