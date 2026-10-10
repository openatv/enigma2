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

	def __init__(self, tokens):
		Converter.__init__(self, tokens)
		Poll.__init__(self)
		self.poll_interval = 30000
		self.poll_enabled = True
		self.type = {
			"ALL": self.ALL,
			"DATA": self.DATA,
			"ENCODER": self.ENCODER,
			"EXTRA_INFO": self.EXTRA_INFO,
			"INFO": self.INFO,
			"INFO_RESOLVE": self.INFO_RESOLVE,
			"INFO_RESOLVE_SHORT": self.INFO_RESOLVE_SHORT,
			"IP": self.IP,
			"NAME": self.NAME,
			"NUMBER": self.NUMBER,
			"REF": self.REF,
			"SHORT_ALL": self.SHORT_ALL
		}.get(tokens, self.UNKNOWN)
		self.streamServer = eStreamServer.getInstance()

	def changed(self, what):
		Converter.changed(self, (self.CHANGED_POLL,))

	def doSuspend(self, suspended):
		pass

	@cached
	def getBoolean(self):
		return bool(self.streamServer and self.streamServer.getConnectedClients())

	boolean = property(getBoolean)

	@cached
	def getText(self):
		text = ""
		if self.streamServer is not None:
			clients = []
			refs = []
			ips = []
			names = []
			encoders = []
			extraInfo = f"{_('ClientIP')}\t\t{_('Transcode')}\t{_('Channel')}\n\n"
			info = ""
			for client in self.streamServer.getConnectedClients():
				refs.append(client[1])
				serviceName = ServiceReference(client[1]).getServiceName() or "(unknown service)"
				names.append(serviceName)
				ip = client[0]
				ips.append(ip)
				transcoding = int(client[2]) != 0
				streamType = "T" if transcoding else "S"
				encoder = _("Yes") if transcoding else _("No")
				encoders.append(encoder)
				if self.type in (self.INFO_RESOLVE, self.INFO_RESOLVE_SHORT):
					try:
						ip = gethostbyaddr(ip)[0]
					except Exception:
						pass
					if self.type == self.INFO_RESOLVE_SHORT:
						ip = ip.partition(".")[0]
				info = f"{info}{streamType} {ip:8s} {serviceName}\n"
				clients.append((ip, serviceName, encoder))
				extraInfo = f"{extraInfo}{ip:8s}\t{encoder}\t{serviceName}\n"
			match self.type:
				case self.ALL:
					text = "\n".join(" ".join(x) for x in clients)
				case self.DATA:
					text = clients
				case self.ENCODER:
					text = f"{_('Transcoding')}: {' '.join(encoders)}"
				case self.EXTRA_INFO:
					text = extraInfo
				case self.INFO | self.INFO_RESOLVE | self.INFO_RESOLVE_SHORT:
					text = info
				case self.IP:
					text = " ".join(ips)
				case self.NAME:
					text = " ".join(names)
				case self.NUMBER:
					text = str(len(clients))
				case self.REF:
					text = " ".join(refs)
				case self.SHORT_ALL:
					text = _("Total clients streaming: %d ( %s )") % (len(clients), " ".join(names))
				case _:
					text = "(unknown)"
		return text

	text = property(getText)
