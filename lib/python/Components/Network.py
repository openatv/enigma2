from config import *

import os

class Network:
	def __init__(self):
		pass
		
	def updateNetworkConfig(self):
		# fixme restarting and updating the network too often. possible fix: check current config and execute only if changed :/
		# fixme using interfaces.tmp instead of interfaces for now
		fp = file('/etc/network/interfaces.tmp', 'w')
		fp.write("auto eth0\n")
		if (config.network.dhcp.value == "yes"):
			fp.write("iface eth0 inet dhcp\n")
		else:
			fp.write("iface eth0 inet static\n")
			fp.write("	address %d.%d.%d.%d\n" % tuple(config.network.ip.value))
			fp.write("	netmask %d.%d.%d.%d\n" % tuple(config.network.netmask.value))
			fp.write("	gateway %d.%d.%d.%d\n" % tuple(config.network.gateway.value))
		fp.close()

		import os
		os.system("/etc/init.d/networking restart")
		
	def setDHCP(self, useDHCP):
		if (useDHCP):
			print "Using DHCP"
			config.network.ip.enabled = False
			config.network.netmask.enabled = False
			config.network.gateway.enabled = False
			config.network.dns.enabled = False
		else:
			print "NOT using DHCP"
			config.network.ip.enabled = True
			config.network.netmask.enabled = True
			config.network.gateway.enabled = True
			config.network.dns.enabled = True
					
	def setIPNameserver(self, ip):
		resolvconf = file('/etc/resolv.conf', 'w')
		resolvconf.write("nameserver %d.%d.%d.%d" % tuple(ip))
		resolvconf.close()
		
	def setMACAddress(self, mac):
		os.system("echo ifconfig eth0 ether %02x:%02x:%02x:%02x:%02x:%02x" % tuple(mac))
		
def InitNetwork():
	config.network = ConfigSubsection()
	config.network.dhcp = configElement("config.network.dhcp", configSelection, 0, ("no", "yes"))
	config.network.ip = configElement("config.network.ip", configSequence, [192,168,1,45], (("."), 3))
	config.network.netmask = configElement("config.network.netmask", configSequence, [255,255,255,0], (("."), 3))	
	config.network.gateway = configElement("config.network.gateway", configSequence, [192,168,1,3], (("."), 3))
	config.network.dns = configElement("config.network.dns", configSequence, [192,168,1,3], (("."), 3))
	config.network.mac = configElement("config.network.mac", configSequence, [00,11,22,33,44,55], ((":"), 2))

	iNetwork = Network()

	def updateNetworkConfig(configElement):
		iNetwork.updateNetworkConfig()

	def setDHCP(configElement):
		iNetwork.setDHCP(configElement.value)

	def setIPNameserver(configElement):
		iNetwork.setIPNameserver(configElement.value)

	def setMACAddress(configElement):
		iNetwork.setMACAddress(configElement.value)

	# this will call the "setup-val" initial
	config.network.dhcp.addNotifier(setDHCP)
	config.network.ip.addNotifier(updateNetworkConfig)
	config.network.netmask.addNotifier(updateNetworkConfig)	
	config.network.gateway.addNotifier(updateNetworkConfig)
	config.network.dns.addNotifier(setIPNameserver)
	config.network.mac.addNotifier(setMACAddress)