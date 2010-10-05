from os import system, popen, path as os_path, listdir
from re import compile as re_compile, search as re_search
from socket import *
from enigma import eConsoleAppContainer
from Components.Console import Console
from Components.PluginComponent import plugins
from Components.About import about
from Plugins.Plugin import PluginDescriptor

class Network:
	def __init__(self):
		self.ifaces = {}
		self.configuredInterfaces = []
		self.configuredNetworkAdapters = []
		self.NetworkState = 0
		self.DnsState = 0
		self.nameservers = []
		self.ethtool_bin = "ethtool"
		self.container = eConsoleAppContainer()
		self.Console = Console()
		self.LinkConsole = Console()
		self.restartConsole = Console()
		self.deactivateConsole = Console()
		self.deactivateInterfaceConsole = Console()
		self.activateConsole = Console()
		self.resetNetworkConsole = Console()
		self.DnsConsole = Console()
		self.PingConsole = Console()
		self.config_ready = None
		self.friendlyNames = {}
		self.lan_interfaces = []
		self.wlan_interfaces = []
		self.getInterfaces()

	def onRemoteRootFS(self):
		fp = file('/proc/mounts', 'r')
		mounts = fp.readlines()
		fp.close()
		for line in mounts:
			parts = line.strip().split(' ')
			if parts[1] == '/' and (parts[2] == 'nfs' or parts[2] == 'smbfs'):
				return True
		return False

	def getInterfaces(self, callback = None):
		devicesPattern = re_compile('[a-z]+[0-9]+')
		self.configuredInterfaces = []
		fp = file('/proc/net/dev', 'r')
		result = fp.readlines()
		fp.close()
		for line in result:
			try:
				device = devicesPattern.search(line).group()
				if device in ('wifi0', 'wmaster0'):
					continue
				self.getDataForInterface(device, callback)
			except AttributeError:
				pass
		#print "self.ifaces:", self.ifaces
		#self.writeNetworkConfig()
		#print ord(' ')
		#for line in result:
		#	print ord(line[0])

	# helper function
	def regExpMatch(self, pattern, string):
		if string is None:
			return None
		try:
			return pattern.search(string).group()
		except AttributeError:
			None

	# helper function to convert ips from a sring to a list of ints
	def convertIP(self, ip):
		strIP = ip.split('.')
		ip = []
		for x in strIP:
			ip.append(int(x))
		return ip

	def getDataForInterface(self, iface,callback):
		#get ip out of ip addr, as avahi sometimes overrides it in ifconfig.
		if not self.Console:
			self.Console = Console()
		cmd = "ip -o addr"
		self.Console.ePopen(cmd, self.IPaddrFinished, [iface,callback])

	def IPaddrFinished(self, result, retval, extra_args):
		(iface, callback ) = extra_args
		data = { 'up': False, 'dhcp': False, 'preup' : False, 'postdown' : False }
		globalIPpattern = re_compile("scope global")
		ipRegexp = '[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}'
		netRegexp = '[0-9]{1,2}'
		macRegexp = '[0-9]{2}\:[0-9]{2}\:[0-9]{2}\:[a-z0-9]{2}\:[a-z0-9]{2}\:[a-z0-9]{2}'
		ipLinePattern = re_compile('inet ' + ipRegexp + '/')
		ipPattern = re_compile(ipRegexp)
		netmaskLinePattern = re_compile('/' + netRegexp)
		netmaskPattern = re_compile(netRegexp)
		bcastLinePattern = re_compile(' brd ' + ipRegexp)
		upPattern = re_compile('UP')
		macPattern = re_compile('[0-9]{2}\:[0-9]{2}\:[0-9]{2}\:[a-z0-9]{2}\:[a-z0-9]{2}\:[a-z0-9]{2}')
		macLinePattern = re_compile('link/ether ' + macRegexp)
		
		for line in result.splitlines():
			split = line.strip().split(' ',2)
			if (split[1][:-1] == iface):
				up = self.regExpMatch(upPattern, split[2])
				mac = self.regExpMatch(macPattern, self.regExpMatch(macLinePattern, split[2]))
				if up is not None:
					data['up'] = True
					if iface is not 'lo':
						self.configuredInterfaces.append(iface)
				if mac is not None:
					data['mac'] = mac
			if (split[1] == iface):
				if re_search(globalIPpattern, split[2]):
					ip = self.regExpMatch(ipPattern, self.regExpMatch(ipLinePattern, split[2]))
					netmask = self.calc_netmask(self.regExpMatch(netmaskPattern, self.regExpMatch(netmaskLinePattern, split[2])))
					bcast = self.regExpMatch(ipPattern, self.regExpMatch(bcastLinePattern, split[2]))
					if ip is not None:
						data['ip'] = self.convertIP(ip)
					if netmask is not None:
						data['netmask'] = self.convertIP(netmask)
					if bcast is not None:
						data['bcast'] = self.convertIP(bcast)
						
		if not data.has_key('ip'):
			data['dhcp'] = True
			data['ip'] = [0, 0, 0, 0]
			data['netmask'] = [0, 0, 0, 0]
			data['gateway'] = [0, 0, 0, 0]

		cmd = "route -n | grep  " + iface
		self.Console.ePopen(cmd,self.routeFinished, [iface, data, callback])

	def routeFinished(self, result, retval, extra_args):
		(iface, data, callback) = extra_args
		ipRegexp = '[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}'
		ipPattern = re_compile(ipRegexp)
		ipLinePattern = re_compile(ipRegexp)

		for line in result.splitlines():
			print line[0:7]
			if line[0:7] == "0.0.0.0":
				gateway = self.regExpMatch(ipPattern, line[16:31])
				if gateway is not None:
					data['gateway'] = self.convertIP(gateway)
					
		self.ifaces[iface] = data
		self.loadNetworkConfig(iface,callback)

	def writeNetworkConfig(self):
		self.configuredInterfaces = []
		fp = file('/etc/network/interfaces', 'w')
		fp.write("# automatically generated by enigma 2\n# do NOT change manually!\n\n")
		fp.write("auto lo\n")
		fp.write("iface lo inet loopback\n\n")
		for ifacename, iface in self.ifaces.items():
			if iface['up'] == True:
				fp.write("auto " + ifacename + "\n")
				self.configuredInterfaces.append(ifacename)
			if iface['dhcp'] == True:
				fp.write("iface "+ ifacename +" inet dhcp\n")
			if iface['dhcp'] == False:
				fp.write("iface "+ ifacename +" inet static\n")
				if iface.has_key('ip'):
					print tuple(iface['ip'])
					fp.write("	address %d.%d.%d.%d\n" % tuple(iface['ip']))
					fp.write("	netmask %d.%d.%d.%d\n" % tuple(iface['netmask']))
					if iface.has_key('gateway'):
						fp.write("	gateway %d.%d.%d.%d\n" % tuple(iface['gateway']))
			if iface.has_key("configStrings"):
				fp.write("\n" + iface["configStrings"] + "\n")
			if iface["preup"] is not False and not iface.has_key("configStrings"):
				fp.write(iface["preup"])
				fp.write(iface["postdown"])
			fp.write("\n")				
		fp.close()
		self.writeNameserverConfig()

	def writeNameserverConfig(self):
		fp = file('/etc/resolv.conf', 'w')
		for nameserver in self.nameservers:
			fp.write("nameserver %d.%d.%d.%d\n" % tuple(nameserver))
		fp.close()

	def loadNetworkConfig(self,iface,callback = None):
		interfaces = []
		# parse the interfaces-file
		try:
			fp = file('/etc/network/interfaces', 'r')
			interfaces = fp.readlines()
			fp.close()
		except:
			print "[Network.py] interfaces - opening failed"

		ifaces = {}
		currif = ""
		for i in interfaces:
			split = i.strip().split(' ')
			if (split[0] == "iface"):
				currif = split[1]
				ifaces[currif] = {}
				if (len(split) == 4 and split[3] == "dhcp"):
					ifaces[currif]["dhcp"] = True
				else:
					ifaces[currif]["dhcp"] = False
			if (currif == iface): #read information only for available interfaces
				if (split[0] == "address"):
					ifaces[currif]["address"] = map(int, split[1].split('.'))
					if self.ifaces[currif].has_key("ip"):
						if self.ifaces[currif]["ip"] != ifaces[currif]["address"] and ifaces[currif]["dhcp"] == False:
							self.ifaces[currif]["ip"] = map(int, split[1].split('.'))
				if (split[0] == "netmask"):
					ifaces[currif]["netmask"] = map(int, split[1].split('.'))
					if self.ifaces[currif].has_key("netmask"):
						if self.ifaces[currif]["netmask"] != ifaces[currif]["netmask"] and ifaces[currif]["dhcp"] == False:
							self.ifaces[currif]["netmask"] = map(int, split[1].split('.'))
				if (split[0] == "gateway"):
					ifaces[currif]["gateway"] = map(int, split[1].split('.'))
					if self.ifaces[currif].has_key("gateway"):
						if self.ifaces[currif]["gateway"] != ifaces[currif]["gateway"] and ifaces[currif]["dhcp"] == False:
							self.ifaces[currif]["gateway"] = map(int, split[1].split('.'))
				if (split[0] == "pre-up"):
					if self.ifaces[currif].has_key("preup"):
						self.ifaces[currif]["preup"] = i
				if (split[0] == "post-down"):
					if self.ifaces[currif].has_key("postdown"):
						self.ifaces[currif]["postdown"] = i

		for ifacename, iface in ifaces.items():
			if self.ifaces.has_key(ifacename):
				self.ifaces[ifacename]["dhcp"] = iface["dhcp"]
		if self.Console:
			if len(self.Console.appContainers) == 0:
				# save configured interfacelist
				self.configuredNetworkAdapters = self.configuredInterfaces
				# load ns only once	
				self.loadNameserverConfig()
				print "read configured interface:", ifaces
				print "self.ifaces after loading:", self.ifaces
				self.config_ready = True
				self.msgPlugins()
				if callback is not None:
					callback(True)

	def loadNameserverConfig(self):
		ipRegexp = "[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}"
		nameserverPattern = re_compile("nameserver +" + ipRegexp)
		ipPattern = re_compile(ipRegexp)

		resolv = []
		try:
			fp = file('/etc/resolv.conf', 'r')
			resolv = fp.readlines()
			fp.close()
			self.nameservers = []
		except:
			print "[Network.py] resolv.conf - opening failed"

		for line in resolv:
			if self.regExpMatch(nameserverPattern, line) is not None:
				ip = self.regExpMatch(ipPattern, line)
				if ip is not None:
					self.nameservers.append(self.convertIP(ip))

		print "nameservers:", self.nameservers

	def deactivateNetworkConfig(self, callback = None):
		if self.onRemoteRootFS():
			if callback is not None:
				callback(True)
			return
		self.deactivateConsole = Console()
		self.commands = []
		self.commands.append("/etc/init.d/avahi-daemon stop")
		for iface in self.ifaces.keys():
			cmd = "ip addr flush " + iface
			self.commands.append(cmd)		
		self.commands.append("/etc/init.d/networking stop")
		self.commands.append("killall -9 udhcpc")
		self.commands.append("rm /var/run/udhcpc*")
		self.deactivateConsole.eBatch(self.commands, self.deactivateNetworkFinished, callback, debug=True)
		
	def deactivateNetworkFinished(self,extra_args):
		callback = extra_args
		if len(self.deactivateConsole.appContainers) == 0:
			if callback is not None:
				callback(True)

	def activateNetworkConfig(self, callback = None):
		if self.onRemoteRootFS():
			if callback is not None:
				callback(True)
			return
		self.activateConsole = Console()
		self.commands = []
		self.commands.append("/etc/init.d/networking start")
		self.commands.append("/etc/init.d/avahi-daemon start")
		self.activateConsole.eBatch(self.commands, self.activateNetworkFinished, callback, debug=True)
		
	def activateNetworkFinished(self,extra_args):
		callback = extra_args
		if len(self.activateConsole.appContainers) == 0:
			if callback is not None:
				callback(True)

	def getConfiguredAdapters(self):
		return self.configuredNetworkAdapters

	def getNumberOfAdapters(self):
		return len(self.ifaces)

	def getFriendlyAdapterName(self, x):
		if x in self.friendlyNames.keys():
			return self.friendlyNames.get(x, x)
		else:
			self.friendlyNames[x] = self.getFriendlyAdapterNaming(x)
			return self.friendlyNames.get(x, x) # when we have no friendly name, use adapter name

	def getFriendlyAdapterNaming(self, iface):
		if iface.startswith('eth'):
			if iface not in self.lan_interfaces and len(self.lan_interfaces) == 0:
				self.lan_interfaces.append(iface)
				return _("LAN connection")
			elif iface not in self.lan_interfaces and len(self.lan_interfaces) >= 1:
				self.lan_interfaces.append(iface)
				return _("LAN connection") + " " + str(len(self.lan_interfaces))
		else:
			if iface not in self.wlan_interfaces and len(self.wlan_interfaces) == 0:
				self.wlan_interfaces.append(iface)
				return _("WLAN connection")
			elif iface not in self.wlan_interfaces and len(self.wlan_interfaces) >= 1:
				self.wlan_interfaces.append(iface)
				return _("WLAN connection") + " " + str(len(self.wlan_interfaces))

	def getFriendlyAdapterDescription(self, iface):
		if iface == 'eth0':
			return _("Internal LAN adapter.")
		else:
			classdir = "/sys/class/net/" + iface + "/device/"
			driverdir = "/sys/class/net/" + iface + "/device/driver/"
			if os_path.exists(classdir):
				files = listdir(classdir)
				if 'driver' in files:
					if os_path.realpath(driverdir).endswith('ath_pci'):
						return _("Atheros")+ " " + str(os_path.basename(os_path.realpath(driverdir))) + " " + _("WLAN adapter.") 
					elif os_path.realpath(driverdir).endswith('zd1211b'):
						return _("Zydas")+ " " + str(os_path.basename(os_path.realpath(driverdir))) + " " + _("WLAN adapter.") 
					elif os_path.realpath(driverdir).endswith('rt73'):
						return _("Ralink")+ " " + str(os_path.basename(os_path.realpath(driverdir))) + " " + _("WLAN adapter.") 
					elif os_path.realpath(driverdir).endswith('rt73usb'):
						return _("Ralink")+ " " + str(os_path.basename(os_path.realpath(driverdir))) + " " + _("WLAN adapter.") 
					else:
						return str(os_path.basename(os_path.realpath(driverdir))) + " " + _("WLAN adapter.") 
				else:
					return _("Unknown network adapter.")

	def getAdapterName(self, iface):
		return iface

	def getAdapterList(self):
		return self.ifaces.keys()

	def getAdapterAttribute(self, iface, attribute):
		if self.ifaces.has_key(iface):
			if self.ifaces[iface].has_key(attribute):
				return self.ifaces[iface][attribute]
		return None

	def setAdapterAttribute(self, iface, attribute, value):
		print "setting for adapter", iface, "attribute", attribute, " to value", value
		if self.ifaces.has_key(iface):
			self.ifaces[iface][attribute] = value

	def removeAdapterAttribute(self, iface, attribute):
		if self.ifaces.has_key(iface):
			if self.ifaces[iface].has_key(attribute):
				del self.ifaces[iface][attribute]

	def getNameserverList(self):
		if len(self.nameservers) == 0:
			return [[0, 0, 0, 0], [0, 0, 0, 0]]
		else: 
			return self.nameservers

	def clearNameservers(self):
		self.nameservers = []

	def addNameserver(self, nameserver):
		if nameserver not in self.nameservers:
			self.nameservers.append(nameserver)

	def removeNameserver(self, nameserver):
		if nameserver in self.nameservers:
			self.nameservers.remove(nameserver)

	def changeNameserver(self, oldnameserver, newnameserver):
		if oldnameserver in self.nameservers:
			for i in range(len(self.nameservers)):
				if self.nameservers[i] == oldnameserver:
					self.nameservers[i] = newnameserver

	def resetNetworkConfig(self, mode='lan', callback = None):
		if self.onRemoteRootFS():
			if callback is not None:
				callback(True)
			return
		self.resetNetworkConsole = Console()
		self.commands = []
		self.commands.append("/etc/init.d/avahi-daemon stop")
		for iface in self.ifaces.keys():
			cmd = "ip addr flush " + iface
			self.commands.append(cmd)		
		self.commands.append("/etc/init.d/networking stop")
		self.commands.append("killall -9 udhcpc")
		self.commands.append("rm /var/run/udhcpc*")
		self.resetNetworkConsole.eBatch(self.commands, self.resetNetworkFinishedCB, [mode, callback], debug=True)

	def resetNetworkFinishedCB(self, extra_args):
		(mode, callback) = extra_args
		if len(self.resetNetworkConsole.appContainers) == 0:
			self.writeDefaultNetworkConfig(mode, callback)

	def writeDefaultNetworkConfig(self,mode='lan', callback = None):
		fp = file('/etc/network/interfaces', 'w')
		fp.write("# automatically generated by enigma 2\n# do NOT change manually!\n\n")
		fp.write("auto lo\n")
		fp.write("iface lo inet loopback\n\n")
		if mode == 'wlan':
			fp.write("auto wlan0\n")
			fp.write("iface wlan0 inet dhcp\n")
		if mode == 'wlan-mpci':
			fp.write("auto ath0\n")
			fp.write("iface ath0 inet dhcp\n")
		if mode == 'lan':
			fp.write("auto eth0\n")
			fp.write("iface eth0 inet dhcp\n")
		fp.write("\n")
		fp.close()

		self.resetNetworkConsole = Console()
		self.commands = []
		if mode == 'wlan':
			self.commands.append("ifconfig eth0 down")
			self.commands.append("ifconfig ath0 down")
			self.commands.append("ifconfig wlan0 up")
		if mode == 'wlan-mpci':
			self.commands.append("ifconfig eth0 down")
			self.commands.append("ifconfig wlan0 down")
			self.commands.append("ifconfig ath0 up")		
		if mode == 'lan':			
			self.commands.append("ifconfig eth0 up")
			self.commands.append("ifconfig wlan0 down")
			self.commands.append("ifconfig ath0 down")
		self.commands.append("/etc/init.d/avahi-daemon start")	
		self.resetNetworkConsole.eBatch(self.commands, self.resetNetworkFinished, [mode,callback], debug=True)	

	def resetNetworkFinished(self,extra_args):
		(mode, callback) = extra_args
		if len(self.resetNetworkConsole.appContainers) == 0:
			if callback is not None:
				callback(True,mode)

	def checkNetworkState(self,statecallback):
		# www.dream-multimedia-tv.de, www.heise.de, www.google.de
		self.NetworkState = 0
		cmd1 = "ping -c 1 82.149.226.170"
		cmd2 = "ping -c 1 193.99.144.85"
		cmd3 = "ping -c 1 209.85.135.103"
		self.PingConsole = Console()
		self.PingConsole.ePopen(cmd1, self.checkNetworkStateFinished,statecallback)
		self.PingConsole.ePopen(cmd2, self.checkNetworkStateFinished,statecallback)
		self.PingConsole.ePopen(cmd3, self.checkNetworkStateFinished,statecallback)
		
	def checkNetworkStateFinished(self, result, retval,extra_args):
		(statecallback) = extra_args
		if self.PingConsole is not None:
			if retval == 0:
				self.PingConsole = None
				statecallback(self.NetworkState)
			else:
				self.NetworkState += 1
				if len(self.PingConsole.appContainers) == 0:
					statecallback(self.NetworkState)
		
	def restartNetwork(self,callback = None):
		if self.onRemoteRootFS():
			if callback is not None:
				callback(True)
			return
		self.restartConsole = Console()
		self.config_ready = False
		self.msgPlugins()
		self.commands = []
		self.commands.append("/etc/init.d/avahi-daemon stop")
		for iface in self.ifaces.keys():
			cmd = "ip addr flush " + iface
			self.commands.append(cmd)		
		self.commands.append("/etc/init.d/networking stop")
		self.commands.append("killall -9 udhcpc")
		self.commands.append("rm /var/run/udhcpc*")
		self.commands.append("/etc/init.d/networking start")
		self.commands.append("/etc/init.d/avahi-daemon start")
		self.restartConsole.eBatch(self.commands, self.restartNetworkFinished, callback, debug=True)
	
	def restartNetworkFinished(self,extra_args):
		( callback ) = extra_args
		if callback is not None:
			callback(True)

	def getLinkState(self,iface,callback):
		cmd = self.ethtool_bin + " " + iface
		self.LinkConsole = Console()
		self.LinkConsole.ePopen(cmd, self.getLinkStateFinished,callback)

	def getLinkStateFinished(self, result, retval,extra_args):
		(callback) = extra_args

		if self.LinkConsole is not None:
			if len(self.LinkConsole.appContainers) == 0:
				callback(result)
			
	def stopPingConsole(self):
		if self.PingConsole is not None:
			if len(self.PingConsole.appContainers):
				for name in self.PingConsole.appContainers.keys():
					self.PingConsole.kill(name)

	def stopLinkStateConsole(self):
		if self.LinkConsole is not None:
			if len(self.LinkConsole.appContainers):
				for name in self.LinkConsole.appContainers.keys():
					self.LinkConsole.kill(name)
					
	def stopDNSConsole(self):
		if self.DnsConsole is not None:
			if len(self.DnsConsole.appContainers):
				for name in self.DnsConsole.appContainers.keys():
					self.DnsConsole.kill(name)
					
	def stopRestartConsole(self):
		if self.restartConsole is not None:
			if len(self.restartConsole.appContainers):
				for name in self.restartConsole.appContainers.keys():
					self.restartConsole.kill(name)
					
	def stopGetInterfacesConsole(self):
		if self.Console is not None:
			if len(self.Console.appContainers):
				for name in self.Console.appContainers.keys():
					self.Console.kill(name)
					
	def stopDeactivateInterfaceConsole(self):
		if self.deactivateInterfaceConsole is not None:
			if len(self.deactivateInterfaceConsole.appContainers):
				for name in self.deactivateInterfaceConsole.appContainers.keys():
					self.deactivateInterfaceConsole.kill(name)
					
	def checkforInterface(self,iface):
		if self.getAdapterAttribute(iface, 'up') is True:
			return True
		else:
			ret=system("ifconfig " + iface + " up")
			system("ifconfig " + iface + " down")
			if ret == 0:
				return True
			else:
				return False

	def checkDNSLookup(self,statecallback):
		cmd1 = "nslookup www.dream-multimedia-tv.de"
		cmd2 = "nslookup www.heise.de"
		cmd3 = "nslookup www.google.de"
		self.DnsConsole = Console()
		self.DnsConsole.ePopen(cmd1, self.checkDNSLookupFinished,statecallback)
		self.DnsConsole.ePopen(cmd2, self.checkDNSLookupFinished,statecallback)
		self.DnsConsole.ePopen(cmd3, self.checkDNSLookupFinished,statecallback)
		
	def checkDNSLookupFinished(self, result, retval,extra_args):
		(statecallback) = extra_args
		if self.DnsConsole is not None:
			if retval == 0:
				self.DnsConsole = None
				statecallback(self.DnsState)
			else:
				self.DnsState += 1
				if len(self.DnsConsole.appContainers) == 0:
					statecallback(self.DnsState)

	def deactivateInterface(self,iface,callback = None):
		if self.onRemoteRootFS():
			if callback is not None:
				callback(True)
			return
		self.deactivateInterfaceConsole = Console()
		self.commands = []
		cmd1 = "ip addr flush " + iface
		cmd2 = "ifconfig " + iface + " down"
		self.commands.append(cmd1)
		self.commands.append(cmd2)
		self.deactivateInterfaceConsole.eBatch(self.commands, self.deactivateInterfaceFinished, callback, debug=True)

	def deactivateInterfaceFinished(self,extra_args):
		callback = extra_args
		if self.deactivateInterfaceConsole:
			if len(self.deactivateInterfaceConsole.appContainers) == 0:
				if callback is not None:
					callback(True)

	def detectWlanModule(self, iface = None):
		self.wlanmodule = None
		classdir = "/sys/class/net/" + iface + "/device/"
		driverdir = "/sys/class/net/" + iface + "/device/driver/"
		if os_path.exists(classdir):
			classfiles = listdir(classdir)
			driver_found = False
			nl80211_found = False
			for x in classfiles:
				if x == 'driver':
					driver_found = True
				if x.startswith('ieee80211:'):
					nl80211_found = True

			if driver_found and nl80211_found:
				#print about.getKernelVersionString()
				self.wlanmodule = "nl80211"
			else:
				if driver_found and not nl80211_found:
					driverfiles = listdir(driverdir)
					if os_path.realpath(driverdir).endswith('ath_pci'):
						if len(driverfiles) >= 1:
							self.wlanmodule = 'madwifi'
					if os_path.realpath(driverdir).endswith('rt73'):
						if len(driverfiles) == 2 or len(driverfiles) == 5:
							self.wlanmodule = 'ralink'					
					if os_path.realpath(driverdir).endswith('zd1211b'):
						if len(driverfiles) == 1 or len(driverfiles) == 5:
							self.wlanmodule = 'zydas'
			if self.wlanmodule is None:
				self.wlanmodule = "wext"
			print 'Using "%s" as wpa-supplicant driver' % (self.wlanmodule)
			return self.wlanmodule
	
	def calc_netmask(self,nmask):
		from struct import pack, unpack
		from socket import inet_ntoa, inet_aton
		mask = 1L<<31
		xnet = (1L<<32)-1
		cidr_range = range(0, 32)
		cidr = long(nmask)
		if cidr not in cidr_range:
			print 'cidr invalid: %d' % cidr
			return None
		else:
			nm = ((1L<<cidr)-1)<<(32-cidr)
			netmask = str(inet_ntoa(pack('>L', nm)))
			return netmask
	
	def msgPlugins(self):
		if self.config_ready is not None:
			for p in plugins.getPlugins(PluginDescriptor.WHERE_NETWORKCONFIG_READ):
				p(reason=self.config_ready)
	
iNetwork = Network()

def InitNetwork():
	pass
