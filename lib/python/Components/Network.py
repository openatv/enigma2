from config import *

import os
from socket import *

class Network:
	def __init__(self):
		pass
		
	def writeNetworkConfig(self):
		# fixme restarting and updating the network too often. possible fix: check current config and execute only if changed :/
		# fixme using interfaces.tmp instead of interfaces for now
		fp = file('/etc/network/interfaces', 'w')
		fp.write("auto eth0\n")
		if (config.network.dhcp.value == _("yes")):
			fp.write("iface eth0 inet dhcp\n")
		else:
			fp.write("iface eth0 inet static\n")
			fp.write("	address %d.%d.%d.%d\n" % tuple(config.network.ip.value))
			fp.write("	netmask %d.%d.%d.%d\n" % tuple(config.network.netmask.value))
			fp.write("	gateway %d.%d.%d.%d\n" % tuple(config.network.gateway.value))
		fp.close()

	def loadNetworkConfig(self):
		try:
			# parse the interfaces-file
			fp = file('/etc/network/interfaces', 'r')
			interfaces = fp.readlines()
			fp.close()
			
			ifaces = {}
			currif = ""
			for i in interfaces:
				split = i.strip().split(' ')
				if (split[0] == "iface"):
					currif = split[1]
					ifaces[currif] = {}
					if (len(split) == 4 and split[3] == "dhcp"):
						ifaces[currif]["dhcp"] = "yes"
					else:
						ifaces[currif]["dhcp"] = "no"
				if (currif != ""):
					if (split[0] == "address"):
						ifaces[currif]["address"] = map(int, split[1].split('.'))
					if (split[0] == "netmask"):
						ifaces[currif]["netmask"] = map(int, split[1].split('.'))
					if (split[0] == "gateway"):
						ifaces[currif]["gateway"] = map(int, split[1].split('.'))									
			
			# parse the resolv.conf-file
			fp = file('/etc/network/interfaces', 'r')
			resolv = fp.readlines()
			fp.close()
		except:
			pass
			
		try:
			for i in resolv:
				split = i.strip().split(' ')
				if (split[0] == "nameserver"):
					config.network.nameserver.value = map(int, split[1].split('.'))
		except:
			pass
		
		try:
			# set this config
			if (ifaces.has_key("eth0")):
				if (ifaces["eth0"]["dhcp"] == "yes"):
					config.network.dhcp.value = 1
				else:
					config.network.dhcp.value = 0
				if (ifaces["eth0"].has_key("address")): config.network.ip.value = ifaces["eth0"]["address"]
				if (ifaces["eth0"].has_key("netmask")): config.network.netmask.value = ifaces["eth0"]["netmask"]
				if (ifaces["eth0"].has_key("gateway")): config.network.gateway.value = ifaces["eth0"]["gateway"]
		except:
			pass

	def activateNetworkConfig(self):
		import os
		os.system("/etc/init.d/networking restart")
		config.network.ip.value = self.getCurrentIP()
		
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
		return
		resolvconf = file('/etc/resolv.conf', 'w')
		resolvconf.write("nameserver %d.%d.%d.%d" % tuple(ip))
		resolvconf.close()
		
	def setMACAddress(self, mac):
		#os.system("echo ifconfig eth0 ether %02x:%02x:%02x:%02x:%02x:%02x" % tuple(mac))
		pass
		
	def setIPAddress(self, ip):
		pass
		#os.system("echo ifconfig eth0 %d.%d.%d.%d" % tuple(ip))
		#self.writeNetworkConfig()

	def setGateway(self, ip):
		pass
		#os.system("echo route add default gw %d.%d.%d.%d" % tuple(ip))
		#self.writeNetworkConfig()
		
	def setNetmask(self, ip):
		pass
		#os.system("echo ifconfig eth0 netmask %d.%d.%d.%d" % tuple(ip))		
		#self.writeNetworkConfig()		

	def getCurrentIP(self):
		ipstr = [0,0,0,0]
		for x in os.popen("ifconfig eth0 | grep 'inet addr:'", "r").readline().split(' '):
			if x.split(':')[0] == "addr":
				ipstr = x.split(':')[1].split('.')
		ip = []
		for x in ipstr:
			ip.append(int(x))
		print "[Network.py] got ip " + str(ip)
		return ip

iNetwork = Network()

def InitNetwork():
	ip = iNetwork.getCurrentIP()

		
	config.network = ConfigSubsection()
	config.network.dhcp = configElement_nonSave("config.network.dhcp", configSelection, 1, (_("no"), _("yes")))
	config.network.ip = configElement_nonSave("config.network.ip", configSequence, ip, configsequencearg.get("IP"))
	config.network.netmask = configElement_nonSave("config.network.netmask", configSequence, [255,255,255,0], configsequencearg.get("IP"))
	config.network.gateway = configElement_nonSave("config.network.gateway", configSequence, [192,168,1,3], configsequencearg.get("IP"))
	config.network.dns = configElement_nonSave("config.network.dns", configSequence, [192,168,1,3], configsequencearg.get("IP"))
	config.network.mac = configElement_nonSave("config.network.mac", configSequence, [00,11,22,33,44,55], configsequencearg.get("MAC"))

	iNetwork.loadNetworkConfig()
	
	#FIXME using this till other concept for this is implemented
	#config.network.activate = configElement("config.network.activate", configSelection, 0, ("yes, sir", "you are my hero"))
	#config.network.activate = configElement("config.network.activate", configSelection, 0, ("yes", "you are my hero"))


	def writeNetworkConfig(configElement):
		iNetwork.writeNetworkConfig()
		
	def setIPAddress(configElement):
		iNetwork.setIPAddress(configElement.value)

	def setGateway(configElement):
		iNetwork.setGateway(configElement.value)

	def setNetmask(configElement):
		iNetwork.setNetmask(configElement.value)		

	def setDHCP(configElement):
		iNetwork.setDHCP(configElement.value)

	def setIPNameserver(configElement):
		iNetwork.setIPNameserver(configElement.value)

	def setMACAddress(configElement):
		iNetwork.setMACAddress(configElement.value)


	# this will call the "setup-val" initial
	config.network.dhcp.addNotifier(setDHCP)
	config.network.ip.addNotifier(setIPAddress)
	config.network.netmask.addNotifier(setNetmask)	
	config.network.gateway.addNotifier(setGateway)
	config.network.dns.addNotifier(setIPNameserver)
	config.network.mac.addNotifier(setMACAddress)
