from Converter import Converter
from Poll import Poll
from Components.Element import cached
from enigma import eStreamServer
from ServiceReference import ServiceReference

class ClientsStreaming(Converter, Poll, object):
	REF = 0
	IP = 1
	NAME = 2
	ENCODER = 3
	NUMBEP = 4
	SHORT_ALL = 5
	ALL = 6

	def __init__(self, type):
		Converter.__init__(self, type)
		Poll.__init__(self)
		self.poll_interval = 30000
		self.poll_enabled = True
		if type == "REF":
			self.type = self.REF
		elif type == "IP":
			self.type = self.IP
		elif type == "NAME":
			self.type = self.NAME
		elif type == "ENCODER":
			self.type = self.ENCODER
		elif type == "NUMBEP":
			self.type = self.NUMBEP
		elif type == "SHORT_ALL":
			self.type = self.SHORT_ALL
		else:
			self.type = self.ALL
		self.streamServer = eStreamServer.getInstance()

	@cached
	def getText(self):
		if self.streamServer is None:
			return ""
		clients = []
		refs = []
		ips = []
		names = []
		encoders = []
		for x in self.streamServer.getConnectedClients():
			refs.append((x[1]))
			servicename = ServiceReference(x[1]).getServiceName() or ""
			service_name = servicename.replace('\xc2\x86', '').replace('\xc2\x87', '')
			names.append((service_name))
			if '::ffff:' in x[0]:
				ip = 'ipv6'
				ips.append((ip))
			else:
				ip = x[0]#[7:]
				ips.append((ip))
			if int(x[2]) == 0:
				encoder = _('NO')
			else:
				encoder = _('YES')
			encoders.append((encoder))
			clients.append((ip, service_name, encoder))
		if not clients:
			return ""
		if self.type == self.REF:
			return ' '.join(refs)
		elif self.type == self.IP:
			return ' '.join(ips)
		elif self.type  == self.NAME:
			return ' '.join(names)
		elif self.type == self.ENCODER:
			return _("Transcoding: ") + ' '.join(encoders)
		elif self.type == self.NUMBEP:
			return str(len(clients))
		elif self.type == self.SHORT_ALL:
			return _("Total clients streaming: %d (%s)") % (len(clients), ' '.join(names))
		else:
			return '\n'.join(' '.join(elems) for elems in clients)
		return ""

	text = property(getText)

	@cached
	def getBoolean(self):
		if self.streamServer is None:
			return False
		return self.streamServer.getConnectedClients() and True or False

	boolean = property(getBoolean)

	def changed(self, what):
		Converter.changed(self, (self.CHANGED_POLL,))

	def doSuspend(self, suspended):
		pass

