from Plugins.Plugin import PluginDescriptor
from twisted.internet.protocol import Protocol, Factory
from twisted.internet import reactor
from Components.Harddisk import harddiskmanager

hotplugNotifier = [ ]

class Hotplug(Protocol):
	def connectionMade(self):
		self.received = ""

	def dataReceived(self, data):
		self.received += data

	def connectionLost(self, reason):
		data = self.received.split('\0')[:-1]

		v = {}

		for x in data:
			i = x.find('=')
			var, val = x[:i], x[i+1:]
			v[var] = val

		print "hotplug:", v

		action = v.get("ACTION")
		device = v.get("DEVPATH")
		physdevpath = v.get("PHYSDEVPATH")
		media_state = v.get("X_E2_MEDIA_STATUS")

		dev = device.split('/')[-1]

		if action is not None and action == "add":
			harddiskmanager.addHotplugPartition(dev, physdevpath)
		elif action is not None and action == "remove":
			harddiskmanager.removeHotplugPartition(dev)
		elif media_state is not None:
			if media_state == '1':
				harddiskmanager.removeHotplugPartition(dev)
				harddiskmanager.addHotplugPartition(dev, physdevpath)
			elif media_state == '0':
				harddiskmanager.removeHotplugPartition(dev)
		
		for callback in hotplugNotifier:
			try:
				callback(dev, action or media_state)
			except AttributeError:
				hotplugNotifier.remove(callback)

def autostart(reason, **kwargs):
	if reason == 0:
		print "starting hotplug handler"
		factory = Factory()
		factory.protocol = Hotplug

		try:
			import os
			os.remove("/tmp/hotplug.socket")
		except OSError:
			pass

		reactor.listenUNIX("/tmp/hotplug.socket", factory)

def Plugins(**kwargs):
	return PluginDescriptor(name = "Hotplug", description = "listens to hotplug events", where = PluginDescriptor.WHERE_AUTOSTART, fnc = autostart)
