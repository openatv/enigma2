from socket import gethostbyaddr
from enigma import eStreamServer
from Components.Converter.Converter import Converter
from Components.Converter.Poll import Poll
from Components.Element import cached
from ServiceReference import ServiceReference


class ClientsStreaming(Converter, Poll):
	UNKNOWN = -1
	REF = 0
	IP = 1
	NAME = 2
	ENCODER = 3
	NUMBER = 4
	SHORT_ALL = 5
	ALL = 6
	INFO = 7
	INFO_RESOLVE = 8
	INFO_RESOLVE_SHORT = 9
	EXTRA_INFO = 10
	DATA = 11

	def __init__(self, type):
		Converter.__init__(self, type)
		Poll.__init__(self)
		self.poll_interval = 30000
		self.poll_enabled = True

		self.type = {
			"REF": self.REF,
			"IP": self.IP,
			"NAME": self.NAME,
			"ENCODER": self.ENCODER,
			"NUMBER": self.NUMBER,
			"SHORT_ALL": self.SHORT_ALL,
			"ALL": self.ALL,
			"INFO": self.INFO,
			"INFO_RESOLVE": self.INFO_RESOLVE,
			"INFO_RESOLVE_SHORT": self.INFO_RESOLVE_SHORT,
			"EXTRA_INFO": self.EXTRA_INFO,
			"DATA": self.DATA,
		}.get(type, self.UNKNOWN)

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
		extrainfo = f'{_("ClientIP")}\t\t{_("Transcode")}\t{_("Channel")}\n\n'
		info = ""

		for x in self.streamServer.getConnectedClients():
			refs.append((x[1]))
			servicename = ServiceReference(x[1]).getServiceName() or "(unknown service)"
			service_name = servicename
			names.append((service_name))
			ip = x[0]

			ips.append((ip))

			if int(x[2]) == 0:
				strtype = "S"
				encoder = _("No")
			else:
				strtype = "T"
				encoder = _("Yes")

			encoders.append((encoder))

			if self.type == self.INFO_RESOLVE or self.type == self.INFO_RESOLVE_SHORT:
				try:
					raw = gethostbyaddr(ip)
					ip = raw[0]
				except Exception:
					pass

				if self.type == self.INFO_RESOLVE_SHORT:
					ip, sep, tail = ip.partition(".")

			info = f"{info}{strtype} {ip:8s} {service_name}\n"

			clients.append((ip, service_name, encoder))

			extrainfo = f"{extrainfo}{ip:8s}\t{encoder}\t{service_name}\n"

		if self.type == self.REF:
			return " ".join(refs)
		elif self.type == self.IP:
			return " ".join(ips)
		elif self.type == self.NAME:
			return " ".join(names)
		elif self.type == self.ENCODER:
			return f"{_("Transcoding")}: {" ".join(encoders)}"
		elif self.type == self.NUMBER:
			return str(len(clients))
		elif self.type == self.EXTRA_INFO:
			return extrainfo
		elif self.type == self.SHORT_ALL:
			return _("Total clients streaming: %d ( %s )") % (len(clients), " ".join(names))
		elif self.type == self.ALL:
			return "\n".join(" ".join(elems) for elems in clients)
		elif self.type == self.INFO or self.type == self.INFO_RESOLVE or self.type == self.INFO_RESOLVE_SHORT:
			return info
		elif self.type == self.DATA:
			return clients
		else:
			return "(unknown)"

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
