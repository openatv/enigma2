from Components.Converter.Converter import Converter
from enigma import eTimer
from Components.Element import cached
import os

ECM_INFO = '/tmp/ecm.info'

class CryptoInfo(Converter, object):
	def __init__(self, type):
		Converter.__init__(self, type)
		# type is ignored, expected to be "verboseInfo"
		self.active = False
		self.visible = True
		self.textvalue = ""
		self.clock_timer = eTimer()
		self.clock_timer.callback.append(self.poll)
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
				else:
					self.textvalue = "%s @%s (%ss)" % (info.get('address', '?'), info.get('hops', '-'), info.get('ecm time', '?'))
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
					self.textvalue = ""
		except:
			ecm = None
			self.textvalue = ""
		return self.textvalue

	text = property(getText)
