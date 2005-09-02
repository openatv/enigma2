from config import *

import os

class Network:
	def __init__(self):
		pass
		
	def setIPAddress(self, ip):
		print ip
		#os.system("echo ifconfig eth0 %d.%d.%d.%d" % (ip[0], ip[1], ip[2], ip[3]))

	def setIPGateway(self, ip):
		os.system("echo route add default gw %d.%d.%d.%d" % (ip[0], ip[1], ip[2], ip[3]))

	def setIPNameserver(self, ip):
		resolvconf = file('/etc/resolv.conf', 'w')
		resolvconf.write("nameserver %d.%d.%d.%d" % (ip[0], ip[1], ip[2], ip[3]))
		resolvconf.close()
		
def InitNetwork():
	config.network = ConfigSubsection();
	config.network.ip = configElement("config.network.ip", configSequence, [192,168,1,45], (".") );
	config.network.gateway = configElement("config.network.gateway", configSequence, [192,168,1,3], (".") );
	config.network.dns = configElement("config.network.dns", configSequence, [192,168,1,3], (".") );

	iNetwork = Network()

	def setIPAddress(configElement):
		iNetwork.setIPAddress(configElement.value);

	def setIPGateway(configElement):
		iNetwork.setIPGateway(configElement.value);
		
	def setIPNameserver(configElement):
		iNetwork.setIPNameserver(configElement.value);


	# this will call the "setup-val" initial
	config.network.ip.addNotifier(setIPAddress);
	config.network.gateway.addNotifier(setIPGateway);
	config.network.dns.addNotifier(setIPNameserver);		
