from Plugins.Plugin import PluginDescriptor
from twisted.internet.protocol import Protocol, Factory
from twisted.internet import reactor
from Components.Harddisk import harddiskmanager

DEVICEDB =  \
	{ "/devices/pci0000:00/0000:00:14.2/usb1/1-1/1-1:1.0/host0/target0:0:0/0:0:0:0": "CF Slot",
	  "/devices/pci0000:00/0000:00:14.2/usb1/1-1/1-1:1.0/host0/target1:0:0/0:0:0:0": "SD Slot"
	}

class Hotplug(Protocol):
	def getUserfriendlyDeviceName(self, phys):
		return DEVICEDB.get(phys, "USB Storage")

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

		dev = device.split('/')[-1]

		if action == "add":
			print "Medium found in", self.getUserfriendlyDeviceName(dev)
			harddiskmanager.addHotplugPartition(dev, self.getUserfriendlyDeviceName(physdevpath))
		elif action == "remove":
			harddiskmanager.removeHotplugPartition(dev)

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
