import Netlink
import enigma
import os

class NetlinkReader():
	def __init__(self):
		from twisted.internet import reactor
		self.nls = Netlink.NetlinkSocket()
		reactor.addReader(self)
	def fileno(self):
		return self.nls.fileno()
	def doRead(self):
		for event in self.nls.parse():
			try:
				subsystem = event['SUBSYSTEM']
				if subsystem == 'input':
					devname = event['DEVNAME']
					action = event['ACTION']
					if action == 'add':
						print "New input device detected:", devname
						enigma.addInputDevice(os.path.join('/dev', devname))
					elif action == 'remove':
						print "Removed input device:", devname
						enigma.removeInputDevice(os.path.join('/dev', devname))
				elif subsystem == 'net':
					from Network import iNetwork
					iNetwork.hotplug(event)
			except KeyError:
				# Ignore "not found"
				pass
	def connectionLost(self, failure):
		# Ignore...
		print "connectionLost?", failure
		self.nls.close()
	def logPrefix(self):
		return 'NetlinkReader'

reader = NetlinkReader()
