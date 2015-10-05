from Plugins.Plugin import PluginDescriptor
from Components.Harddisk import harddiskmanager
from twisted.internet.protocol import Protocol, Factory
import os

# globals
hotplugNotifier = []
audiocd = False

def AudiocdAdded():
	global audiocd
	if audiocd:
		return True
	else:
		return False

def processHotplugData(self, v):
	print "[Hotplug.plugin.py]:", v
	action = v.get("ACTION")
	device = v.get("DEVPATH")
	physdevpath = v.get("PHYSDEVPATH")
	media_state = v.get("X_E2_MEDIA_STATUS")
	global audiocd

	dev = device.split('/')[-1]

	if action == "add":
		error, blacklisted, removable, is_cdrom, partitions, medium_found = harddiskmanager.addHotplugPartition(dev, physdevpath)
	elif action == "remove":
		harddiskmanager.removeHotplugPartition(dev)
	elif action == "audiocdadd":
		audiocd = True
		media_state = "audiocd"
		error, blacklisted, removable, is_cdrom, partitions, medium_found = harddiskmanager.addHotplugAudiocd(dev, physdevpath)
		print "[Hotplug.plugin.py] AUDIO CD ADD"
	elif action == "audiocdremove":
		audiocd = False
		file = []
		# Removing the invalid playlist.e2pls If its still the audio cd's list
		# Default setting is to save last playlist on closing Mediaplayer.
		# If audio cd is removed after Mediaplayer was closed,
        # the playlist remains in if no other media was played.
		if os.path.isfile('/etc/enigma2/playlist.e2pls'):
			with open('/etc/enigma2/playlist.e2pls', 'r') as f:
				file = f.readline().strip()
		if file:
			if '.cda' in file:
				try:
					os.remove('/etc/enigma2/playlist.e2pls')
				except OSError:
					pass
		harddiskmanager.removeHotplugPartition(dev)
		print "[Hotplug.plugin.py] REMOVING AUDIOCD"
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

class Hotplug(Protocol):
	def connectionMade(self):
		print "[Hotplug.plugin.py] connection!"
		self.received = ""

	def dataReceived(self, data):
		self.received += data
		print "[Hotplug.plugin.py] complete", self.received

	def connectionLost(self, reason):
		print "[Hotplug.plugin.py] connection lost!"
		data = self.received.split('\0')[:-1]
		v = {}
		for x in data:
			i = x.find('=')
			var, val = x[:i], x[i+1:]
			v[var] = val
		processHotplugData(self, v)

def autostart(reason, **kwargs):
	if reason == 0:
		from twisted.internet import reactor
		try:
			os.remove("/tmp/hotplug.socket")
		except OSError:
			pass
		factory = Factory()
		factory.protocol = Hotplug
		reactor.listenUNIX("/tmp/hotplug.socket", factory)

def Plugins(**kwargs):
	return PluginDescriptor(name = "Hotplug", description = "listens to hotplug events", where = PluginDescriptor.WHERE_AUTOSTART, needsRestart = True, fnc = autostart)
