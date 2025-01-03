import netifaces as ni
from os import listdir, remove, system as os_system
from os.path import basename, exists, isdir, realpath
from re import compile
from socket import inet_ntoa, gethostbyname, gethostname
from struct import pack

from enigma import eTimer

from Components.config import config
from Components.Console import Console
from Components.Harddisk import harddiskmanager
from Components.PluginComponent import plugins
from Components.SystemInfo import BoxInfo
from Plugins.Plugin import PluginDescriptor
from Tools.Directories import fileReadLines, fileWriteLines

MODULE_NAME = __name__.split(".")[-1]


class Network:
	def __init__(self):
		self.networkInterfaceFile = "/etc/network/interfaces"
		self.networkProgram = "/sbin/ifconfig"
		self.onlyWoWifaces = {}
		self.pingProgram = "/bin/ping"
		self.pingCheckList = ("1.1.1.1", "8.8.8.8", "9.9.9.9", "64.6.64.6")  # Cloudflare DNS, Google DNS, Quad9 DNS, Verisign DNS.
		self.pingCount = 1  # Each ping takes about 1 second to process.
		self.pingTestsPassed = 0
		self.dnsProgram = "/usr/bin/nslookup"
		self.dnsCheckList = ("www.cloudflare.com", "www.google.com", "www.microsoft.com", "www.akamai.com", "www.ebay.com", "www.amazon.com")  # To be discussed!
		self.dnsTestsPassed = 0
		self.resolvFile = "/etc/resolv.conf"
		self.nameserverFile = "/etc/enigma2/nameserversdns.conf"
		self.ifaces = {}  # Don't rename this!
		self.configuredNetworkAdapters = []
		self.nameservers = []
		self.ethtool_bin = "/usr/sbin/ethtool"
		self.console = Console()
		self.linkConsole = Console()
		self.restartConsole = Console()
		self.deactivateInterfaceConsole = Console()
		self.activateInterfaceConsole = Console()
		self.resetNetworkConsole = Console()
		self.dnsConsole = Console()
		self.pingConsole = Console()
		self.config_ready = None
		self.friendlyNames = {}
		self.lan_interfaces = []
		self.wlan_interfaces = []
		self.remoteRootFS = None
		self.getInterfaces()

	def getInstalledAdapters(self):  # Find all the non-blacklisted network interfaces available in /sys/class/net.
		return [x for x in listdir("/sys/class/net") if not self.isBlacklisted(x)]

	def isBlacklisted(self, iface):  # Function to determine if the interface is in a blacklist.
		return iface in ("lo", "wifi0", "wmaster0", "sit0", "tap0", "tun0", "wg0", "sys0", "p2p0", "tunl0", "ip6tnl0", "ip_vti0", "ip6_vti0")

	def onRemoteRootFS(self):
		if self.remoteRootFS is None:
			from Components.Harddisk import getProcMounts
			for parts in getProcMounts():
				if parts[1] == "/" and parts[2] == "nfs":
					self.remoteRootFS = True
					break
			else:
				self.remoteRootFS = False
		return self.remoteRootFS

	def getInterfaces(self, callback=None):  # Find and learn about all network interfaces.
		self.configuredInterfaces = []
		for interface in self.getInstalledAdapters():
			self.getAddrInet(interface, callback)
			# self.getConnectionInfo(interface, callback)

	def getNumberOfAdapters(self):  # Count the number of available network interfaces.
		return len(self.ifaces)

	def regExpMatch(self, pattern, string):  # Helper function.
		result = None
		if string:
			try:
				result = pattern.search(string).group()
			except AttributeError:
				result = None
		return result

	# Function to convert IPs from a string to a list of integers. If
	# noneOnError is True then return None if a valid IP address is
	# not found else return [0, 0, 0, 0].
	#
	def convertIP(self, ip, noneOnError=False):
		try:
			data = [int(x) for x in ip.split(".")]
		except ValueError:
			data = None if noneOnError else [0, 0, 0, 0]
		return data if data and len(data) == 4 else None

	def loadNetworkConfig(self, iface, callback=None):  # Parse the interfaces file.
		interfaces = {}
		interface = ""
		lines = fileReadLines(self.networkInterfaceFile, default=[], source=MODULE_NAME)
		if len(lines) > 3:
			lines = lines[2:]  # Remove the header
		enabled = False
		for line in lines:
			if line.startswith(f"auto {iface}"):
				enabled = True
				break
		newlines = []
		for line in lines:
			if line and line[0] == "#" and "inet6 dhcp" not in line:
				newlines.append(line[1:])
			else:
				newlines.append(line)
		for line in newlines:
			data = line.strip().split(" ")
			if data[0] == "iface":
				interface = data[1]
				if interface not in interfaces:
					interfaces[interface] = {}
					interfaces[interface]["ipv6"] = False
				if data[2] == "inet6":
					interfaces[interface]["ipv6"] = True
				else:
					interfaces[interface]["dhcp"] = len(data) == 4 and data[3] == "dhcp"
			if interface == iface:  # Read information only for available interfaces.
				if data[0] == "address":
					interfaces[interface]["address"] = list(map(int, data[1].split(".")))
					if "ip" in self.ifaces[interface] and self.ifaces[interface]["ip"] != interfaces[interface]["address"] and interfaces[interface]["dhcp"] is False:
						self.ifaces[interface]["ip"] = interfaces[interface]["address"][:]
				if data[0] == "netmask":
					interfaces[interface]["netmask"] = list(map(int, data[1].split(".")))
					if "netmask" in self.ifaces[interface] and self.ifaces[interface]["netmask"] != interfaces[interface]["netmask"] and interfaces[interface]["dhcp"] is False:
						self.ifaces[interface]["netmask"] = interfaces[interface]["netmask"][:]
				if data[0] == "gateway":
					interfaces[interface]["gateway"] = list(map(int, data[1].split(".")))
					if "gateway" in self.ifaces[interface] and self.ifaces[interface]["gateway"] != interfaces[interface]["gateway"] and interfaces[interface]["dhcp"] is False:
						self.ifaces[interface]["gateway"] = interfaces[interface]["gateway"][:]
				if data[0] == "pre-up" and "preup" in self.ifaces[interface]:
					self.ifaces[interface]["preup"] = line
				if data[0] in ("pre-down", "post-down"):
					if "predown" in self.ifaces[interface]:
						self.ifaces[interface]["predown"] = line

		self.ifaces[iface]["up"] = enabled
		print(f"[Network] DEBUG: Interfaces={interfaces}")
		for name, item in list(interfaces.items()):
			if name in self.ifaces:
				self.ifaces[name]["dhcp"] = item["dhcp"]
				self.ifaces[name]["ipv6"] = item["ipv6"]

		print(f"[Network] DEBUG: '{iface}' InterfaceData={self.ifaces[iface]}")
		if self.console and len(self.console.appContainers) == 0:
			self.configuredNetworkAdapters = self.configuredInterfaces  # Save configured interface list.
			self.loadNameserverConfig()  # Load name servers only once.
			if config.usage.dns.value.lower() not in ("dhcp-router"):
				self.writeNameserverConfig()
				# print(f"read configured interface: {interfaces}")
				# print(f"self.ifaces after loading: {self.ifaces}")
			self.config_ready = True
			self.msgPlugins()
			if callback and callable(callback):
				callback(True)

	def getAddrInet(self, iface, callback):
		data = {"up": False, "dhcp": False, "preup": False, "predown": False}
		try:
			data["up"] = int(open("/sys/class/net/%s/flags" % iface).read().strip(), 16) & 1 == 1
			if data["up"]:
				self.configuredInterfaces.append(iface)
			nit = ni.ifaddresses(iface)
			data["ip"] = self.convertIP(nit[ni.AF_INET][0]["addr"])  # IPv4 address.
			data["netmask"] = self.convertIP(nit[ni.AF_INET][0]["netmask"])
			data["bcast"] = self.convertIP(nit[ni.AF_INET][0]["broadcast"])
			data["mac"] = nit[ni.AF_LINK][0]["addr"]  # MAC address.
			data["gateway"] = self.convertIP(ni.gateways()["default"][ni.AF_INET][0])  # Default gateway address.
		except:
			data["dhcp"] = True
			data["ip"] = [0, 0, 0, 0]
			data["netmask"] = [0, 0, 0, 0]
			data["gateway"] = [0, 0, 0, 0]
		self.ifaces[iface] = data
		self.loadNetworkConfig(iface, callback)

	def routeFinished(self, result, retval, extra_args):
		(iface, data, callback) = extra_args
		ipRegexp = r"[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}"
		ipPattern = compile(ipRegexp)
		ipLinePattern = compile(ipRegexp)
		for line in result.splitlines():
			print("[Network] %s" % line[0:7])
			if line[0:7] == "0.0.0.0":
				gateway = self.regExpMatch(ipPattern, line[16:31])
				if gateway:
					data["gateway"] = self.convertIP(gateway)
		self.ifaces[iface] = data
		self.loadNetworkConfig(iface, callback)

	def writeNetworkConfig(self):
		self.configuredInterfaces = []
		lines = ["# Automatically generated by Enigma2."]
		lines.append("# Do NOT change manually!")
		lines.append("")
		lines.append("auto lo")
		lines.append("iface lo inet loopback")
		lines.append("")
		print(f"[Network] writeNetworkConfig DEBUG: onlyWoWifaces = {self.onlyWoWifaces}")
		for ifacename, iface in sorted(self.ifaces.items()):
			print(f"[Network] writeNetworkConfig {ifacename} = {str(iface)}")
			if "dns-nameservers" in iface and iface["dns-nameservers"]:
				dns = []
				for nameserver in iface["dns-nameservers"].split()[1:]:
					dns.append((self.convertIP(nameserver)))
				if dns:
					self.nameservers = dns
			WoW = False
			if ifacename in self.onlyWoWifaces:
				WoW = self.onlyWoWifaces[ifacename]
			enabled = iface["up"] is True
			enabledComment = "" if enabled else "# "
			if WoW is False:
				lines.append(f"{enabledComment}auto {ifacename}")
				self.configuredInterfaces.append(ifacename)
				self.onlyWoWifaces[ifacename] = False
			elif WoW is True:
				self.onlyWoWifaces[ifacename] = True
				lines.append(f"# Only WakeOnWiFi {ifacename}")
			comment = "" if "ipv6" in iface and iface["ipv6"] and enabled else "# "
			lines.append(f"{comment}iface {ifacename} inet6 dhcp")
			if iface["dhcp"]:
				lines.append(f"{enabledComment}iface {ifacename} inet dhcp")
			if not iface["dhcp"]:
				lines.append(f"{enabledComment}iface {ifacename} inet static")
				lines.append(f"{enabledComment}  hostname $(hostname)")
				if "ip" in iface:
					dummy = ".".join([str(x) for x in iface["ip"]])
					lines.append(f"{enabledComment}	address {dummy}")
					dummy = ".".join([str(x) for x in iface["netmask"]])
					lines.append(f"{enabledComment}	netmask {dummy}")
					# lines.append(f"	address {".".join([str(x) for x in iface["ip"]])}")
					# lines.append(f"	netmask {".".join([str(x) for x in iface["netmask"]])}")
					if "gateway" in iface:
						dummy = ".".join([str(x) for x in iface["gateway"]])
						lines.append(f"{enabledComment}	gateway {dummy}")
						# lines.append(f"	gateway {".".join([str(x) for x in iface["gateway"]])}")
			if "configStrings" in iface:
				configStrings = iface["configStrings"]
				if not enabled:
					configStrings = configStrings.split("\n")
					configStrings = [f"{enabledComment}{x}" for x in configStrings]
					configStrings = "\n".join(configStrings)
				lines.append(configStrings)
			if iface["preup"] is not False and "configStrings" not in iface:
				lines.append(f"{enabledComment}{iface["preup"]}")
			if iface["predown"] is not False and "configStrings" not in iface:
				lines.append(f"{enabledComment}{iface["predown"]}")
			lines.append("")
		fileWriteLines(self.networkInterfaceFile, lines, source=MODULE_NAME)
		self.configuredNetworkAdapters = self.configuredInterfaces
		self.writeNameserverConfig()

	def writeNameserverConfig(self):
		# try:
		# Console().ePopen("/bin/rm -f '%s'" % self.resolvFile)
		linesV4 = ["nameserver %d.%d.%d.%d" % tuple(nameserver) for nameserver in self.nameservers if isinstance(nameserver, list)]
		# linesV4 = [f"nameserver {".".join([str(x) for x in nameserver])}" for nameserver in self.nameservers if isinstance(nameserver, list)]
		linesV6 = [f"nameserver {nameserver}" for nameserver in self.nameservers if isinstance(nameserver, str)]
		match config.usage.dnsMode.value:
			case 0:
				lines = linesV4 + linesV6
			case 1:
				lines = linesV6 + linesV4
			case 2:
				lines = linesV4
			case 3:
				lines = linesV6
		suffix = [f"domain {config.usage.dnsSuffix.value}"] if config.usage.dnsSuffix.value else []
		rotate = ["options rotate"] if config.usage.dnsRotate.value else []
		fileWriteLines(self.resolvFile, rotate + suffix + lines, source=MODULE_NAME)
		if config.usage.dns.value != "dhcp-router":
			fileWriteLines(self.nameserverFile, lines, source=MODULE_NAME)
		elif exists(self.nameserverFile):
			remove(self.nameserverFile)
		# self.restartNetwork()
		# except:
		# 	print("[Network] resolv.conf or nameserversdns.conf - writing failed")

	def loadNameserverConfig(self):
		ipRegExpV4 = r"[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}"
		ipRegExpV6 = r"(^|(?<=[^\w:.]))(([0-9a-fA-F]{0,4}:){1,7}[0-9a-fA-F]{0,4})(?=$|(?![\w:.]))"
		ipPatternV4 = compile(ipRegExpV4)
		nameserverPatternV4 = compile(f"nameserver +{ipRegExpV4}")
		nameserverPatternV6 = compile(f"nameserver +{ipRegExpV6}")
		self.nameservers = []
		fileName = self.resolvFile if config.usage.dns.value == "dhcp-router" else self.nameserverFile
		for line in fileReadLines(fileName, default=[], source=MODULE_NAME):
			if line == "options rotate":
				config.usage.dnsRotate.value = True
			elif line.startswith("domain "):
				config.usage.dnsSuffix.value = line.replace("domain ", "")
			elif self.regExpMatch(nameserverPatternV4, line) is not None:
				ip = self.regExpMatch(ipPatternV4, line)
				if ip:
					self.nameservers.append(self.convertIP(ip))
			elif self.regExpMatch(nameserverPatternV6, line) is not None:
				self.nameservers.append(line.replace("nameserver ", ""))
		print(f"[Network] DEBUG: Nameservers: {self.nameservers}.")

	def getConfiguredAdapters(self):
		return self.configuredNetworkAdapters

	def getFriendlyAdapterName(self, x):
		if x in list(self.friendlyNames.keys()):
			return self.friendlyNames.get(x, x)
		self.friendlyNames[x] = self.getFriendlyAdapterNaming(x)
		return self.friendlyNames.get(x, x)  # When we have no friendly name use the adapter name.

	def getFriendlyAdapterNaming(self, iface):
		name = None
		if self.isWirelessInterface(iface):
			if iface not in self.wlan_interfaces:
				name = _("WLAN connection")
				if self.wlan_interfaces:
					name += " " + str(len(self.wlan_interfaces) + 1)
				self.wlan_interfaces.append(iface)
		else:
			if iface not in self.lan_interfaces:
				if BoxInfo.getItem("machinebuild") == "et10000" and iface == "eth1":
					name = _("VLAN connection")
				else:
					name = _("LAN connection")
				if self.lan_interfaces and BoxInfo.getItem("machinebuild") != "et10000" and iface != "eth1":
					name += " " + str(len(self.lan_interfaces) + 1)
				self.lan_interfaces.append(iface)
		return name

	def getFriendlyAdapterDescription(self, iface):
		if not self.isWirelessInterface(iface):
			return _("Ethernet network interface")
		moduledir = self.getWlanModuleDir(iface)
		if moduledir:
			name = basename(realpath(moduledir))
			if name in ("ath_pci", "ath5k", "ar6k_wlan"):
				name = "Atheros"
			elif name in ("rt73", "rt73usb", "rt3070sta"):
				name = "Ralink"
			elif name == "zd1211b":
				name = "Zydas"
			elif name == "r871x_usb_drv":
				name = "Realtek"
			elif name == "brcm-systemport":
				name = "Broadcom"
			elif name == "wlan":
				name = name.upper()
		else:
			name = _("Unknown")
		return "%s %s" % (name, _("wireless network interface"))

	def getAdapterName(self, iface):
		return iface

	def getAdapterList(self):
		return list(self.ifaces.keys())

	def getAdapterAttribute(self, iface, attribute):
		if iface in self.ifaces and attribute in self.ifaces[iface]:
			return self.ifaces[iface][attribute]
		return None

	def setAdapterAttribute(self, iface, attribute, value):
		# print "setting for adapter", iface, "attribute", attribute, " to value", value
		if iface in self.ifaces:
			self.ifaces[iface][attribute] = value

	def removeAdapterAttribute(self, iface, attribute):
		if iface in self.ifaces:
			if attribute in self.ifaces[iface]:
				del self.ifaces[iface][attribute]

	def getNameserverList(self):
		return [[0, 0, 0, 0], [0, 0, 0, 0]] if len(self.nameservers) == 0 else self.nameservers

	def clearNameservers(self):
		self.nameservers = []

	def addNameserver(self, nameserver):
		if nameserver not in self.nameservers:
			self.nameservers.append(nameserver)

	def removeNameserver(self, nameserver):
		if nameserver in self.nameservers:
			self.nameservers.remove(nameserver)

	def changeNameserver(self, oldNameserver, newNameserver):
		if oldNameserver in self.nameservers:
			for pos, nameserver in enumerate(self.nameservers):
				if self.nameservers[pos] == oldNameserver:
					self.nameservers[pos] = newNameserver

	def resetNetworkConfig(self, mode="lan", callback=None):
		self.resetNetworkConsole = Console()
		self.commands = []
		self.commands.append("/etc/init.d/avahi-daemon stop")
		for iface in self.ifaces.keys():
			if iface != "eth0" or not self.onRemoteRootFS():
				self.commands.append("ip addr flush dev %s scope global" % iface)
		self.commands.append("/etc/init.d/networking stop")
		self.commands.append("killall -9 udhcpc")
		self.commands.append("rm /var/run/udhcpc*")
		self.resetNetworkConsole.eBatch(self.commands, self.resetNetworkFinishedCB, [mode, callback], debug=True)

	def resetNetworkFinishedCB(self, extra_args):
		(mode, callback) = extra_args
		if len(self.resetNetworkConsole.appContainers) == 0:
			self.writeDefaultNetworkConfig(mode, callback)

	def writeDefaultNetworkConfig(self, mode="lan", callback=None):
		lines = []
		lines.append("# Automatically generated by Enigma2.\n# Do NOT change manually!")
		lines.append("")
		lines.append("auto lo")
		lines.append("iface lo inet loopback")
		lines.append("")
		dev = ""
		if mode == "wlan":
			dev = "wlan0"
		if mode == "wlan-mpci":
			dev = "ath0"
		if mode == "lan":
			dev = "eth0"
		if dev:
			lines.append("auto %s" % dev)
			lines.append("iface %s inet dhcp" % dev)
		lines.append("")
		fileWriteLines(self.networkInterfaceFile, lines, source=MODULE_NAME)
		self.resetNetworkConsole = Console()
		self.commands = []
		if mode == "wlan":
			self.commands.append("%s eth0 down" % self.networkProgram)
			self.commands.append("%s ath0 down" % self.networkProgram)
			self.commands.append("%s wlan0 up" % self.networkProgram)
		if mode == "wlan-mpci":
			self.commands.append("%s eth0 down" % self.networkProgram)
			self.commands.append("%s wlan0 down" % self.networkProgram)
			self.commands.append("%s ath0 up" % self.networkProgram)
		if mode == "lan":
			self.commands.append("%s eth0 up" % self.networkProgram)
			self.commands.append("%s wlan0 down" % self.networkProgram)
			self.commands.append("%s ath0 down" % self.networkProgram)
		self.commands.append("/etc/init.d/avahi-daemon start")
		self.resetNetworkConsole.eBatch(self.commands, self.resetNetworkFinished, [mode, callback], debug=True)

	def resetNetworkFinished(self, extra_args):
		(mode, callback) = extra_args
		if len(self.resetNetworkConsole.appContainers) == 0 and callback is not None:
			callback(True, mode)

	# Internet connectivity (ping) test methods.
	#
	def checkNetworkState(self, callback):  # Legacy method for testing Internet connectivity.
		self.checkInternetConnectivity(callback, pingList=None)

	def checkInternetConnectivity(self, callback, pingList=None):
		if pingList is None:
			pingList = self.pingCheckList
		self.pingTestsPassed = 0
		self.pingConsole = Console()
		for target in pingList:
			self.pingConsole.ePopen((self.pingProgram, self.pingProgram, "-c", str(self.pingCount), target), self.checkInternetConnectivityFinished, extra_args=callback)

	def checkInternetConnectivityFinished(self, result, retVal, extraArgs):
		callback = extraArgs
		# print("[Network] DEBUG: Ping results:\n%s" % result)
		if self.pingConsole is not None:
			if retVal == 0:
				self.pingConsole = None
				callback(self.pingTestsPassed)
			else:
				self.pingTestsPassed += 1
				if not self.pingConsole.appContainers:
					callback(self.pingTestsPassed)

	# DNS lookup (nslookup) test methods.
	#
	def checkDNSLookup(self, callback, dnsList=None):
		if dnsList is None:
			dnsList = self.dnsCheckList
		self.dnsTestsPassed = 0
		self.dnsConsole = Console()
		for target in dnsList:
			self.dnsConsole.ePopen((self.dnsProgram, self.dnsProgram, target), self.checkDNSLookupFinished, callback)

	def checkDNSLookupFinished(self, result, retVal, extraArgs):
		callback = extraArgs
		# print("[Network] DEBUG: DNS results:\n%s" % result)
		if self.dnsConsole is not None:
			if retVal == 0:
				self.dnsConsole = None
				callback(self.dnsTestsPassed)
			else:
				self.dnsTestsPassed += 1
				if not self.dnsConsole.appContainers:
					callback(self.dnsTestsPassed)

	def restartNetwork(self, callback=None):
		self.restartConsole = Console()
		self.config_ready = False
		self.msgPlugins()
		self.commands = []
		self.commands.append("/etc/init.d/avahi-daemon stop")
		for iface in self.ifaces.keys():
			if iface != "eth0" or not self.onRemoteRootFS():
				self.commands.append(("/sbin/ifdown", "/sbin/ifdown", iface))
				self.commands.append("ip addr flush dev %s scope global" % iface)
		self.commands.append("/etc/init.d/networking stop")
		self.commands.append("killall -9 udhcpc")
		self.commands.append("rm /var/run/udhcpc*")
		self.commands.append("/etc/init.d/networking start")
		self.commands.append("/etc/init.d/avahi-daemon start")
		self.restartConsole.eBatch(self.commands, self.restartNetworkFinished, callback, debug=True)

	def restartNetworkFinished(self, extra_args):
		(callback) = extra_args
		if callback is not None:
			try:
				callback(True)
			except:
				pass

	def getLinkState(self, iface, callback):
		cmd = "%s %s" % (self.ethtool_bin, iface)
		self.linkConsole = Console()
		self.linkConsole.ePopen(cmd, self.getLinkStateFinished, callback)

	def getLinkStateFinished(self, result, retval, extra_args):
		(callback) = extra_args
		if isinstance(result, bytes):
			result = result.decode()
		if self.linkConsole is not None and len(self.linkConsole.appContainers) == 0:
			callback(result)

	def stopPingConsole(self):
		if self.pingConsole is not None and len(self.pingConsole.appContainers):
			for name in list(self.pingConsole.appContainers.keys()):
				self.pingConsole.kill(name)

	def stopLinkStateConsole(self):
		if self.linkConsole is not None and len(self.linkConsole.appContainers):
			for name in list(self.linkConsole.appContainers.keys()):
				self.linkConsole.kill(name)

	def stopDNSConsole(self):
		if self.dnsConsole is not None and len(self.dnsConsole.appContainers):
			for name in list(self.dnsConsole.appContainers.keys()):
				self.dnsConsole.kill(name)

	def stopRestartConsole(self):
		if self.restartConsole is not None and len(self.restartConsole.appContainers):
			for name in list(self.restartConsole.appContainers.keys()):
				self.restartConsole.kill(name)

	def stopGetInterfacesConsole(self):
		if self.console is not None and len(self.console.appContainers):
			for name in list(self.console.appContainers.keys()):
				self.console.kill(name)

	def stopDeactivateInterfaceConsole(self):
		if self.deactivateInterfaceConsole is not None:
			self.deactivateInterfaceConsole.killAll()
			self.deactivateInterfaceConsole = None

	def stopActivateInterfaceConsole(self):
		if self.activateInterfaceConsole is not None:
			self.activateInterfaceConsole.killAll()
			self.activateInterfaceConsole = None

	def checkforInterface(self, iface):
		if self.getAdapterAttribute(iface, "up") is True:
			return True
		else:
			ret = os_system("ifconfig %s up" % iface)
			os_system("ifconfig %s down" % iface)
			return ret == 0

	def deactivateInterface(self, ifaces, callback=None):
		def buildCommands(iface):
			commands.append("ifdown %s" % iface)
			commands.append("ip addr flush dev %s scope global" % iface)
			# The wpa_supplicant sometimes doesn't quit properly on SIGTERM.
			if exists("/var/run/wpa_supplicant/%s" % iface):
				commands.append("wpa_cli -i%s terminate" % iface)

		self.config_ready = False
		self.msgPlugins()
		commands = []
		if not self.deactivateInterfaceConsole:
			self.deactivateInterfaceConsole = Console()
		if isinstance(ifaces, (list, tuple)):
			for iface in ifaces:
				if iface != "eth0" or not self.onRemoteRootFS():
					buildCommands(iface)
		else:
			if ifaces == "eth0" and self.onRemoteRootFS():
				if callback is not None:
					callback(True)
				return
			buildCommands(ifaces)
		self.deactivateInterfaceConsole.eBatch(commands, self.deactivateInterfaceFinished, (ifaces, callback), debug=True)

	def deactivateInterfaceFinished(self, extra_args):
		def checkCommandResult(iface):
			if self.deactivateInterfaceConsole and "ifdown %s" % iface in self.deactivateInterfaceConsole.appResults:
				result = str(self.deactivateInterfaceConsole.appResults.get("ifdown %s" % iface)).strip("\n")
				if result == "ifdown: interface %s not configured" % iface:
					return False
				else:
					return True

		(ifaces, callback) = extra_args
		# The ifdown command sometimes can't get the interface down.
		if isinstance(ifaces, (list, tuple)):
			for iface in ifaces:
				if checkCommandResult(iface) is False:
					Console().ePopen(("ifconfig %s down" % iface))
		else:
			if checkCommandResult(ifaces) is False:
				Console().ePopen(("ifconfig %s down" % ifaces))
		if self.deactivateInterfaceConsole:
			if len(self.deactivateInterfaceConsole.appContainers) == 0 and callback is not None:
				callback(True)

	def activateInterface(self, iface, callback=None):
		if self.config_ready:
			self.config_ready = False
			self.msgPlugins()
		if iface == "eth0" and self.onRemoteRootFS():
			if callback is not None:
				callback(True)
			return
		if not self.activateInterfaceConsole:
			self.activateInterfaceConsole = Console()
		commands = ["/sbin/ifup %s" % iface]
		self.activateInterfaceConsole.eBatch(commands, self.activateInterfaceFinished, callback, debug=True)

	def activateInterfaceFinished(self, extra_args):
		callback = extra_args
		if self.activateInterfaceConsole:
			if len(self.activateInterfaceConsole.appContainers) == 0:
				if callback is not None:
					try:
						callback(True)
					except:
						pass

	def sysfsPath(self, iface):
		return "/sys/class/net/%s" % iface

	def isWirelessInterface(self, iface):
		if iface in self.wlan_interfaces:
			return True
		if isdir("%s/wireless" % self.sysfsPath(iface)):
			return True
		if not exists("/proc/net/wireless"):
			return False
		# The r871x_usb_drv on kernel 2.6.12 is not identifiable over /sys/class/net/"ifacename"/wireless so look also inside /proc/net/wireless.
		device = compile("[a-z]{2,}[0-9]*:")
		ifnames = []
		fp = open("/proc/net/wireless")
		for line in fp:
			try:
				ifnames.append(device.search(line).group()[:-1])
			except AttributeError:
				pass
		fp.close()
		return True if iface in ifnames else False

	def canWakeOnWiFi(self, iface):
		if self.sysfsPath(iface) == "/sys/class/net/wlan3" and exists("/tmp/bcm/%s" % iface):
			return True

	def getWlanModuleDir(self, iface=None):
		if self.sysfsPath(iface) == "/sys/class/net/wlan3" and exists("/tmp/bcm/%s" % iface):
			devicedir = "%s/device" % self.sysfsPath("sys0")
		else:
			devicedir = "%s/device" % self.sysfsPath(iface)
		moduledir = "%s/driver/module" % devicedir
		if isdir(moduledir):
			return moduledir
		# Identification is not possible over default module directory.
		try:
			for x in listdir(devicedir):
				# The rt3070 on kernel 2.6.18 registers wireless devices as usb_device (e.g. 1-1.3:1.0) and identification is only possible over /sys/class/net/"ifacename"/device/1-xxx.
				if x.startswith("1-"):
					moduledir = "%s/%s/driver/module" % (devicedir, x)
					if isdir(moduledir):
						return moduledir
			# The rt73, zd1211b, r871x_usb_drv on kernel 2.6.12 can be identified over /sys/class/net/"ifacename"/device/driver, so also look here.
			moduledir = "%s/driver" % devicedir
			if isdir(moduledir):
				return moduledir
		except:
			pass
		return None

	def detectWlanModule(self, iface=None):
		if not self.isWirelessInterface(iface):
			return None
		devicedir = "%s/device" % self.sysfsPath(iface)
		if isdir("%s/ieee80211" % devicedir):
			return "nl80211"
		moduledir = self.getWlanModuleDir(iface)
		if moduledir:
			module = basename(realpath(moduledir))
			if module in ("brcm-systemport",):
				return "brcm-wl"
			if module in ("ath_pci", "ath5k"):
				return "madwifi"
			if module in ("rt73", "rt73"):
				return "ralink"
			if module == "zd1211b":
				return "zydas"
		return "wext"

	def calcNetmask(self, nmask):
		mask = 1 << 31
		xnet = (1 << 32) - 1
		cidrRange = range(0, 32)
		cidr = int(nmask)
		if cidr not in cidrRange:
			print("[Network] cidr invalid: %d!" % cidr)
			return None
		else:
			nm = ((1 << cidr) - 1) << (32 - cidr)
			netmask = str(inet_ntoa(pack(">L", nm)))
			return netmask

	def msgPlugins(self):
		if self.config_ready is not None:
			for p in plugins.getPlugins(PluginDescriptor.WHERE_NETWORKCONFIG_READ):
				p(reason=self.config_ready)

	def hotplug(self, event):
		interface = event["INTERFACE"]
		if self.isBlacklisted(interface):
			return
		action = event["ACTION"]
		if action == "add":
			print("[Network] Add new interface: '%s'." % interface)
			self.getAddrInet(interface, None)
		elif action == "remove":
			print("[Network] Removed interface: '%s'." % interface)
			try:
				del self.ifaces[interface]
			except KeyError:
				pass

	def getInterfacesNameserverList(self, iface):
		result = []
		nameservers = self.getAdapterAttribute(iface, "dns-nameservers")
		if nameservers:
			ipRegexp = r"[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}"
			ipPattern = compile(ipRegexp)
			for x in nameservers.split()[1:]:
				ip = self.regExpMatch(ipPattern, x)
				if ip:
					result.append([int(n) for n in ip.split(".")])
		if len(self.nameservers) and not result:  # Also use global name server if we got none from the interface.
			result.extend(self.nameservers)
		return result


iNetwork = Network()


class NetworkCheck:
	def __init__(self):
		self.Timer = eTimer()
		self.Timer.callback.append(self.startCheckNetwork)

	def startCheckNetwork(self):
		self.Timer.stop()
		if self.Retry > 0:
			try:
				if gethostbyname(gethostname()) != "127.0.0.1":
					print("[Network] NetworkCheck: Done.")
					harddiskmanager.enumerateNetworkMounts(refresh=True)
					return
				self.Retry = self.Retry - 1
				self.Timer.start(1000, True)
			except Exception as err:
				print("[Network] NetworkCheck: Error %s!" % str(err))

	def Start(self):
		self.Retry = 10
		self.Timer.start(1000, True)


def InitNetwork():
	global networkCheck
	networkCheck = NetworkCheck()
	networkCheck.Start()
