from config import config, ConfigYesNo, ConfigIP, NoSave, ConfigSubsection, ConfigMAC

import os
from socket import *

class Network:
	def __init__(self):
		pass
		
	def writeNetworkConfig(self):
		# fixme restarting and updating the network too often. possible fix: check current config and execute only if changed :/
		# fixme using interfaces.tmp instead of interfaces for now
		fp = file('/etc/network/interfaces', 'w')
		fp.write("auto lo\n")
		fp.write("iface lo inet loopback\n\n")
		fp.write("auto eth0\n")
		if config.network.dhcp.value:
			fp.write("iface eth0 inet dhcp\n")
		else:
			fp.write("iface eth0 inet static\n")
			fp.write("	address %d.%d.%d.%d\n" % tuple(config.network.ip.value))
			fp.write("	netmask %d.%d.%d.%d\n" % tuple(config.network.netmask.value))
			fp.write("	gateway %d.%d.%d.%d\n" % tuple(config.network.gateway.value))
			fp2 = file('/etc/resolv.conf', 'w')
			fp2.write("nameserver %d.%d.%d.%d\n" % tuple(config.network.dns.value))
			fp2.close()
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
			fp = file('/etc/resolv.conf', 'r')
			resolv = fp.readlines()
			fp.close()
		except:
			print "[Network.py] loading network files failed"
			
		try:
			for i in resolv:
				split = i.strip().split(' ')
				if (split[0] == "nameserver"):
					config.network.dns.value = map(int, split[1].split('.'))
		except:
			print "[Network.py] resolv.conf parsing failed"
		
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
			print "[Network.py] parsing network failed"

	def deactivateNetworkConfig(self):
		os.system("ip addr flush eth0")
		os.system("/etc/init.d/networking stop")
		os.system("killall -9 udhcpc")
		os.system("rm /var/run/udhcpc*")

	def activateNetworkConfig(self):
		os.system("/etc/init.d/networking start")
		config.network.ip.value = self.getCurrentIP()
		config.network.ip.save()
		
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
	config.network = ConfigSubsection()
	config.network.dhcp = NoSave(ConfigYesNo(default=True))
	config.network.ip = NoSave(ConfigIP(default=iNetwork.getCurrentIP()))
	config.network.netmask = NoSave(ConfigIP(default=[255,255,255,0]))
	config.network.gateway = NoSave(ConfigIP(default=[192,168,1,3]))
	config.network.dns = NoSave(ConfigIP(default=[192,168,1,3]))
	config.network.mac = NoSave(ConfigMAC(default=[00,11,22,33,44,55]))

	iNetwork.loadNetworkConfig()
	
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
