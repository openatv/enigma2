from config import *

import os

class Network:
	def __init__(self):
		pass
		
	def setDHCP(self, useDHCP):
		if (useDHCP):
			print "Using DHCP"
			config.network.ip.enabled = False
			config.network.gateway.enabled = False
			config.network.dns.enabled = False
		else:
			print "NOT using DHCP"
			config.network.ip.enabled = True
			config.network.gateway.enabled = True
			config.network.dns.enabled = True
					
	def setIPAddress(self, ip):
		print ip
		os.system("echo ifconfig eth0 %d.%d.%d.%d" % (ip[0], ip[1], ip[2], ip[3]))

	def setIPGateway(self, ip):
		os.system("echo route add default gw %d.%d.%d.%d" % (ip[0], ip[1], ip[2], ip[3]))

	def setIPNameserver(self, ip):
		resolvconf = file('/etc/resolv.conf', 'w')
		resolvconf.write("nameserver %d.%d.%d.%d" % (ip[0], ip[1], ip[2], ip[3]))
		resolvconf.close()
		
	def setMACAddress(self, mac):
		os.system("echo ifconfig eth0 ether %02x:%02x:%02x:%02x:%02x:%02x" % (mac[0], mac[1], mac[2], mac[3], mac[4], mac[5]))
		
def InitNetwork():
	config.network = ConfigSubsection()
	config.network.dhcp = configElement("config.network.dhcp", configBoolean, 0, ("no", "yes"))
	config.network.ip = configElement("config.network.ip", configSequence, [192,168,1,45], (("."), 3))
	config.network.gateway = configElement("config.network.gateway", configSequence, [192,168,1,3], (("."), 3))
	config.network.dns = configElement("config.network.dns", configSequence, [192,168,1,3], (("."), 3))
	config.network.mac = configElement("config.network.mac", configSequence, [00,11,22,33,44,55], ((":"), 2))

	iNetwork = Network()

	def setDHCP(configElement):
		iNetwork.setDHCP(configElement.value)

	def setIPAddress(configElement):
		iNetwork.setIPAddress(configElement.value)

	def setIPGateway(configElement):
		iNetwork.setIPGateway(configElement.value)
		
	def setIPNameserver(configElement):
		iNetwork.setIPNameserver(configElement.value)

	def setMACAddress(configElement):
		iNetwork.setMACAddress(configElement.value)

	# this will call the "setup-val" initial
	config.network.dhcp.addNotifier(setDHCP)
	config.network.ip.addNotifier(setIPAddress)
	config.network.gateway.addNotifier(setIPGateway)
	config.network.dns.addNotifier(setIPNameserver)
	config.network.mac.addNotifier(setMACAddress)