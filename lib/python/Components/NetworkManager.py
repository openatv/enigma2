from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from json import JSONDecodeError, loads
from os import chmod, listdir, makedirs, remove, rmdir
from os.path import basename, exists, isdir, ismount, realpath
from pickle import dump as pickleDump, load as pickleLoad
from re import compile, match
from shutil import copy2
from socket import AF_UNIX, SOCK_STREAM, gethostbyname, gethostname, socket
from subprocess import DEVNULL, check_output
from uuid import uuid4
from collections.abc import Callable
from twisted.internet import reactor

from enigma import e2avahi_set_debug, eNetworkServiceBrowser, eTimer

from Components.config import config
from Components.Console import Console
from Components.Harddisk import harddiskmanager
from Components.PluginComponent import plugins
from Components.SystemInfo import BoxInfo
from Plugins.Plugin import PluginDescriptor
from Tools.Directories import fileReadLine, fileReadLines, fileReadXML, fileWriteLine, fileWriteLines
from Tools.ServiceAction import ServiceAction

interfacesFile = "/etc/network/interfaces"
resolvFile = "/etc/resolv.conf"
nameserverFile = "/etc/enigma2/nameserversdns.conf"
wpaSupplicantDir = "/etc"
sysfsNet = "/sys/class/net"
procNetWireless = "/proc/net/wireless"
ifconfigBin = "/sbin/ifconfig"
ifupBin = "/sbin/ifup"
ifdownBin = "/sbin/ifdown"
wpaSupplicantBin = "/usr/sbin/wpa_supplicant"
wpaCliBin = "/usr/sbin/wpa_cli"
socketDaemonPath = "/var/run/daemon.socket"
netEventSocketPath = "/var/run/daemon_net.socket"
netinfoPath = "/var/run/netinfo"
netscanPath = "/var/run/netscan"
netrestarterBin = "/usr/sbin/netrestarter"

MODULE_NAME = __name__.split(".")[-1]


class Encryption(StrEnum):
	NONE = "none"
	WEP = "wep"
	WPA = "wpa"
	WPA2 = "wpa2"
	WPA_WPA2 = "wpa+wpa2"  # Legacy combined mode stored as wpa2 in wpa_supplicant.
	WPA3 = "wpa3"
	WPA2_WPA3 = "wpa2+wpa3"  # WPA3 transition mode, the access point offers PSK and SAE side by side.
	WPA2_ENTERPRISE = "wpa2-eap"
	WPA3_ENTERPRISE = "wpa3-eap"
	WPA2_WPA3_ENTERPRISE = "wpa2+wpa3-eap"  # Same transition idea, 802.1X alongside 802.1X-SHA256.


# Deferred via lambda so translation happens at display time, not import time.
encryptionLabels = {
	Encryption.NONE: lambda: _("None"),
	Encryption.WEP: lambda: "WEP",
	Encryption.WPA: lambda: "WPA",
	Encryption.WPA2: lambda: "WPA2",
	Encryption.WPA_WPA2: lambda: "WPA/WPA2",
	Encryption.WPA3: lambda: "WPA3",
	Encryption.WPA2_WPA3: lambda: "WPA2/WPA3",
	Encryption.WPA2_ENTERPRISE: lambda: "WPA2 Enterprise",
	Encryption.WPA3_ENTERPRISE: lambda: "WPA3 Enterprise",
	Encryption.WPA2_WPA3_ENTERPRISE: lambda: "WPA2/WPA3 Enterprise"
}

# Driver-API identifiers.
apiNl80211 = "nl80211"
apiWext = "wext"
apiMadwifi = "madwifi"
apiRalink = "ralink"
apiZydas = "zydas"


# Central access point for all network configuration.
class NetworkManager:
	ADAPTER_BLACKLIST = frozenset((
		"atml0",
		"bnep0",
		"ip6_vti0",
		"ip6tnl0",
		"ip_vti0",
		"lo",
		"p2p0",
		"sit0",
		"sys0",
		"tap0",
		"tun0",
		"tunl0",
		"usb0",
		"wg0",
		"wifi0",
		"wmaster0"
	))

	ROUTE_METRIC_FILE = "/etc/default/e2-route-metric"
	ROUTE_METRIC_CHOICES = [(x, str(x)) for x in range(100, 901, 100)]
	NETINFO_UPDATE_DEBOUNCE_MS = 250
	LINKSPEED_BITS = {
		"10baseT/Half": (0x01, "10 Mbps Half Duplex"),
		"10baseT/Full": (0x02, "10 Mbps Full Duplex"),
		"100baseT/Half": (0x04, "100 Mbps Half Duplex"),
		"100baseT/Full": (0x08, "100 Mbps Full Duplex"),
		"1000baseT/Half": (0x10, "1000 Mbps Half Duplex"),
		"1000baseT/Full": (0x20, "1000 Mbps Full Duplex"),
	}

	def __init__(self):
		self._debug = config.crash.debugNetwork.value
		e2avahi_set_debug(self._debug)
		self.adapters: dict[str, Adapter] = {}
		self.connections: dict[str, list[Connection]] = {}
		self.vpnInterfaces: dict[str, VpnInfo] = {}
		self.nameserverConfig = NameserverConfig()
		self.interfacesFile = InterfacesFile()
		self.nsFiles = NameserverFiles()
		self.pendingRestart = None
		self.networkCheck = None
		self.onAdaptersChanged: list[Callable] = []
		self.netinfoUpdateTimer = eTimer()
		self.netinfoUpdateTimer.callback.append(self.onNetinfoUpdateDebounced)
		self.load()
		self._eventReader = NetEventReader(self)

	def log(self, msg: str):
		if self._debug:
			print(f"[{MODULE_NAME}] {msg}")

	def startNetworkCheck(self):
		self.networkCheck = NetworkCheck()
		self.networkCheck.start()

	def load(self):
		self.log("load: Starting full configuration/state load.")
		self.discoverAdapters()
		self.loadInterfacesFile()
		self.loadWpaSupplicantFiles()
		self.nsFiles.load(self.nameserverConfig)
		self.applyNetinfo()
		self.log(f"load: Done, adapters={sorted(self.adapters.keys())}.")

	def discoverAdapters(self):
		def isBroadcomWl(interface: str, module: str) -> bool:
			return exists(f"/tmp/bcm/{interface}") or module in ("brcm-systemport", "brcmfmac", "brcmsmac")

		def detectDriverApi(interface: str, module: str) -> str:
			driver = apiNl80211
			if isBroadcomWl(interface, module):
				driver = apiWext
			elif isdir(f"{sysfsNet}/{interface}/device/ieee80211"):
				driver = apiNl80211
			elif module in ("ath_pci", "ath5k", "ar6k_wlan"):
				driver = apiMadwifi
			elif module in ("rt73", "rt73usb", "rt3070sta", "rt2800usb"):
				driver = apiRalink
			elif module == "zd1211b":
				driver = apiZydas
			elif exists(procNetWireless):
				try:
					if f"{interface}:" in open(procNetWireless).read():
						driver = apiWext
				except OSError:
					driver = apiNl80211
			return driver

		def isBlacklisted(interface: str) -> bool:
			return interface in self.ADAPTER_BLACKLIST or interface in vpnNames

		def detectModule(interface: str) -> str:
			devDir = f"{sysfsNet}/{interface}/device"
			modLink = f"{devDir}/driver/module"
			if isdir(modLink):
				return basename(realpath(modLink))
			try:
				for entry in listdir(devDir):
					if entry.startswith("1-"):
						deep = f"{devDir}/{entry}/driver/module"
						if isdir(deep):
							return basename(realpath(deep))
				fallback = f"{devDir}/driver"
				if isdir(fallback):
					return basename(realpath(fallback))
			except OSError:
				pass
			return ""

		def canWakeOnWiFi(interface: str) -> bool:
			return interface == "wlan3" and bool(BoxInfo.getItem("wwol"))

		vpnNames = {name for name, data in readNetinfoInterfaces().items() if data.get("type") == "vpn"}
		try:
			names = [x for x in listdir(sysfsNet) if not isBlacklisted(x)]
		except OSError:
			names = []

		def isWireless(interface: str) -> bool:
			if isWirelessName(interface):
				return True
			if isdir(f"{sysfsNet}/{interface}/wireless"):
				return True
			if exists(procNetWireless):
				try:
					return f"{interface}:" in open(procNetWireless).read()
				except OSError:
					pass
			return False

		for name in names:
			isWiFi = isWireless(name)
			module = detectModule(name)
			api = detectDriverApi(name, module)
			existing = self.adapters.get(name)
			adapter = Adapter(
				name=name,
				isWiFi=isWiFi,
				module=module,
				driverApi=api,
				isBroadcomWl=isBroadcomWl(name, module),
				canWakeOnWiFi=canWakeOnWiFi(name),
				mac=fileReadLine(f"{sysfsNet}/{name}/address", default=""),
				netInfo=existing.netInfo if existing else NetInfo(),
			)
			netInfo = adapter.netInfo
			try:
				flags = int(open(f"{sysfsNet}/{name}/flags").read().strip(), 16)
				netInfo.up = bool(flags & 1)
			except OSError:
				pass
			self.adapters[name] = adapter
			self.log(f"discoverAdapters: {name} isWiFi={isWiFi} module={module} driverApi={api} up={netInfo.up}.")

	def loadInterfacesFile(self):
		self.interfacesFile.load()
		parsed, autoIfaces, wakeOnWiFiIfaces = self.interfacesFile.parse()
		self.log(f"loadInterfacesFile: autoIfaces={sorted(autoIfaces)} wakeOnWiFiIfaces={sorted(wakeOnWiFiIfaces)}.")
		for interface, conns in parsed.items():
			if interface not in self.adapters:
				self.adapters[interface] = Adapter(
					name=interface,
					isWiFi=isWirelessName(interface),
					driverApi=apiNl80211,
				)
			self.connections[interface] = conns
			self.adapters[interface].adapterEnabled = interface in autoIfaces
			if interface in wakeOnWiFiIfaces:
				for conn in conns:
					conn.wakeOnWiFi = True
			self.log(f"loadInterfacesFile: {interface} adapterEnabled={self.adapters[interface].adapterEnabled} connections={len(conns)}.")
		for interface, adapter in self.adapters.items():
			if not self.connections.get(interface):
				self.connections[interface] = [Connection(
					adapter=interface,
					name=interface,
					dhcp=True,
					wifi=WiFiConfig() if adapter.isWiFi else None,
				)]

	def loadWpaSupplicantFiles(self):
		for interface, adapter in self.adapters.items():
			if not adapter.isWiFi:
				continue
			wpf = WpaSupplicantFile(interface)
			if not wpf.exists():
				self.log(f"loadWpaSupplicantFiles: {interface} No '{wpf.path}'.")
				continue
			for wifi in wpf.parse():
				self.log(f"loadWpaSupplicantFiles: {interface} SSID={wifi.ssid!r} disabled={wifi.disabled} encryption={wifi.encryption}.")
				self.mergeWiFiConfig(interface, wifi)

	def mergeWiFiConfig(self, interface: str, wifi: WiFiConfig):
		conns = self.getConnections(interface)
		bySsid = {x.wifi.ssid: x for x in conns if x.wifi and x.wifi.ssid}
		if wifi.ssid in bySsid:
			conn = bySsid[wifi.ssid]
			conn.wifi = wifi
			conn.enabled = not wifi.disabled
			conn.priority = wifi.priority
		else:
			conns.append(Connection(
				adapter=interface,
				name=wifi.ssid,
				dhcp=True,
				enabled=not wifi.disabled,
				priority=wifi.priority,
				wifi=wifi,
			))

	def saveWpaSupplicant(self, onlyIface: str | None = None) -> bool:
		ok = True
		interfaces = [onlyIface] if onlyIface else list(self.adapters.keys())
		for interface in interfaces:
			adapter = self.adapters.get(interface)
			if not adapter or not adapter.isWiFi:
				continue
			conns = self.getConnections(interface)
			for conn in conns:
				if conn.wifi is not None and conn.wifi.ssid:
					conn.wifi.disabled = not conn.enabled
					conn.wifi.priority = conn.priority
			wifiConfigs = [x.wifi for x in conns if x.wifi is not None and x.wifi.ssid]
			if not wifiConfigs:
				continue
			self.log(f"saveWpaSupplicant: {interface} writing {len(wifiConfigs)} wifi config(s): {", ".join(f"{x.ssid!r}(disabled={x.disabled})" for x in wifiConfigs)}.")
			wpf = WpaSupplicantFile(interface)
			wpf.ensureDir()
			ok = wpf.save(wifiConfigs) and ok
			self.reconfigureWifi(interface)
		return ok

	def reconfigureWifi(self, interface: str) -> None:
		if not self.wpaSupplicantRunning(interface):
			return
		self.log(f"reconfigureWifi: {interface}.")
		Console().ePopen(f"{wpaCliBin} -i{interface} reconfigure 2>/dev/null; true")

	def save(self) -> bool:
		def buildWiFiConfigStrings(adapter: Adapter) -> list[str]:
			interface = adapter.name
			api = adapter.driverApi
			driverFlags = f"-D {api}" if api != apiNl80211 else ""
			return [
				f"pre-up {ifconfigBin} {interface} up || true",
				f"pre-up {wpaSupplicantBin} -i{interface} -c{adapter.wpaConfPath} -B {driverFlags} -P{adapter.wpaPidPath} || true",
				f"pre-down {wpaCliBin} -i{interface} terminate 2>/dev/null; true",
			]

		self.log("save: Starting.")
		ok = True
		for interface, adapter in self.adapters.items():
			if not adapter.isWiFi:
				continue
			cs = buildWiFiConfigStrings(adapter)
			for conn in self.getConnections(interface):
				if conn.wifi:
					conn.extraLines = list(cs)

		connMap = {}
		for interface, adapter in self.adapters.items():
			conns = self.getConnections(interface)
			if adapter.isWiFi:
				baseConn = self.getBaseConnection(interface)
				wowOnly = baseConn.wakeOnWiFi and not adapter.adapterEnabled
				baseConn.enabled = adapter.adapterEnabled or wowOnly
				baseConn.extraLines = buildWiFiConfigStrings(adapter)
				connMap[interface] = [baseConn]
			else:
				for conn in conns:
					conn.enabled = adapter.adapterEnabled
				connMap[interface] = conns
		adapterEnabledMap = {interface: adapter.adapterEnabled for interface, adapter in self.adapters.items()}
		self.log(f"save: adapterEnabledMap={adapterEnabledMap}.")
		ok = self.interfacesFile.save(connMap, adapterEnabledMap) and ok
		ok = self.saveWpaSupplicant() and ok

		anyDhcp = any(conn.dhcp for conns in connMap.values() for conn in conns if conn.enabled)
		self.nsFiles.save(self.nameserverConfig, anyDhcp)
		self.log(f"save: Done, status={ok}.")
		return ok

	def activateCommands(self, interface: str) -> list[str]:
		adapter = self.adapters.get(interface)
		if not adapter:
			return []
		conn = self.activeConnection(interface)
		if not conn:
			return [f"{ifupBin} {interface}"]
		if adapter.isWiFi:
			return WiFiRuntime(adapter).commandsActivate(conn)
		return [f"{ifupBin} {interface}"]

	def deactivateCommands(self, interface: str) -> list[str]:
		adapter = self.adapters.get(interface)
		if adapter and adapter.isWiFi:
			return WiFiRuntime(adapter).commandsDeactivate()
		return [
			f"{ifdownBin} {interface} 2>/dev/null; true",
			f"ip addr flush dev {interface} scope global 2>/dev/null; true",
		]

	def restartNetwork(self, interface: str = "", callback: Callable | None = None):
		self.log(f"restartNetwork: interface={interface or "all"}.")

		def done(retval: int = 0):
			self.log(f"restartNetwork: {interface or "all"} done, returned {retval}.")
			self.discoverAdapters()
			self.loadInterfacesFile()
			self.loadWpaSupplicantFiles()
			self.applyNetinfo()
			self.notifyNetworkPlugins(True, interface=interface)
			if callback:
				callback()
		self.pendingRestart = ServiceAction.netrestart(done, iface=interface)

	def getAdapter(self, interface: str) -> Adapter | None:
		return self.adapters.get(interface)

	def getNetInfo(self, interface: str) -> NetInfo:
		adapter = self.adapters.get(interface)
		return adapter.netInfo if adapter else NetInfo()

	def getConnections(self, interface: str) -> list[Connection]:
		return self.connections.setdefault(interface, [])

	def activeConnection(self, interface: str) -> Connection | None:
		enabled = [x for x in self.getConnections(interface) if x.enabled]
		return max(enabled, key=lambda conn: conn.priority, default=None)

	def getBaseConnection(self, interface: str) -> Connection:
		conns = self.getConnections(interface)
		if not conns:
			adapter = self.adapters.get(interface)
			isWiFi = adapter.isWiFi if adapter else isWirelessName(interface)
			base = Connection(adapter=interface, name=interface, dhcp=True, wifi=WiFiConfig() if isWiFi else None)
			conns.append(base)
			return base
		base = next((x for x in conns if not (x.wifi and x.wifi.ssid)), None)
		if base is None:
			adapter = self.adapters.get(interface)
			isWiFi = adapter.isWiFi if adapter else isWirelessName(interface)
			base = Connection(adapter=interface, name=interface, dhcp=True, wifi=WiFiConfig() if isWiFi else None)
			conns.append(base)
		return base

	def getActiveConnection(self, interface: str) -> Connection | None:
		return self.activeConnection(interface)

	def getWiFiConnections(self, interface: str) -> list[Connection]:
		return [x for x in self.getConnections(interface) if x.isWiFi]

	def addConnection(self, conn: Connection):
		self.getConnections(conn.adapter).append(conn)

	def removeConnection(self, interface: str, ssid: str) -> bool:
		conns = self.connections.get(interface)
		if not conns:
			self.log(f"removeConnection: {interface} not found.")
			return False
		before = len(conns)
		self.connections[interface] = [x for x in conns if not (x.wifi and x.wifi.ssid == ssid)]
		removed = len(self.connections[interface]) < before
		self.log(f"removeConnection: {interface} SSID='{ssid!r}', removed={removed}.")
		return removed

	def setNameservers(self, servers: list):
		self.nameserverConfig.servers = list(servers)

	# Returns a human-readable adapter label.
	def getFriendlyAdapterName(self, interface: str) -> str:
		adapter = self.adapters.get(interface)
		if adapter is None:
			return interface
		wifiAdapters = sorted(name for name, other in self.adapters.items() if other.isWiFi)
		lanAdapters = sorted(name for name, other in self.adapters.items() if not other.isWiFi)
		if adapter.isWiFi:
			idx = wifiAdapters.index(interface) if interface in wifiAdapters else 0
			return f"{_("Wi-Fi connection")} {idx + 1 if idx else ""}"
		idx = lanAdapters.index(interface) if interface in lanAdapters else 0
		return f"{_("LAN connection")} {idx + 1 if idx else ""}"

	# Compatibility shim – returns a short adapter description.
	def getFriendlyAdapterDescription(self, interface: str) -> str:
		adapter = self.adapters.get(interface)
		if adapter is None:
			return interface
		if adapter.isWiFi:
			return f"{adapter.module or 'Unknown'} {_('wireless network interface')}"
		return _("Ethernet network interface")

	def notifyNetworkPlugins(self, reason: bool, interface: str = ""):
		self.log(f"notifyNetworkPlugins: reason={reason} interface={interface!r} states={", ".join(f"{other}(up={adapter.netInfo.up}, ip={adapter.netInfo.ip})" for other, adapter in self.adapters.items())}.")
		if interface:
			otherAdapterUp = any(
				adapter.netInfo.up and any(octet != 0 for octet in adapter.netInfo.ip)
				for other, adapter in self.adapters.items() if other != interface
			)
			if otherAdapterUp:
				self.log(f"notifyNetworkPlugins: {interface} changed but another adapter is still up -> skipped.")
				return
		try:
			notified = [str(plugin) for plugin in plugins.getPlugins(PluginDescriptor.WHERE_NETWORKCONFIG_READ)]
			self.log(f"notifyNetworkPlugins: Calling {notified} with reason={reason}.")
			for plugin in plugins.getPlugins(PluginDescriptor.WHERE_NETWORKCONFIG_READ):
				plugin(reason=reason)
		except Exception as err:
			self.log(f"notifyNetworkPlugins: Error '{err}'!")

	def activateInterface(self, interface, callback=None):
		adapter = self.adapters.get(interface)
		if adapter and not adapter.isWiFi:
			def lanUp(retval: int):
				self.log(f"activateInterface: {interface} (LAN) ifup returned {retval}.")
				self.notifyNetworkPlugins(True)
				if callback:
					callback(retval == 0)
			self.log(f"activateInterface: {interface} (LAN) ifup.")
			self.pendingRestart = ServiceAction.ifup(interface, lanUp)
			return

		def wlanUp(retval: bool = True):
			self.log(f"activateInterface: {interface} (Wi-Fi) done.")
			self.notifyNetworkPlugins(True)
			if callback:
				callback(True)
		try:
			cmds = self.activateCommands(interface)
			self.log(f"activateInterface: {interface} (Wi-Fi) commands='{cmds}'.")
			Console().eBatch(cmds, lambda result: wlanUp(), debug=True)
		except Exception as err:
			self.log(f"activateInterface: {interface} (Wi-Fi) failed '{err}'!")
			if callback:
				callback(False)

	def getWiFiNetworkList(self, interface: str) -> list[str]:
		return [f"{wpaCliBin} -i{interface} list_networks"]

	def wpaSupplicantRunning(self, interface: str) -> bool:
		adapter = self.adapters.get(interface)
		running = exists(adapter.wpaCtrlPath) if adapter else False
		self.log(f"wpaSupplicantRunning: {interface} = {running}.")
		return running

	def getWiFiStatus(self, interface: str) -> dict:
		"""Parsed `wpa_cli status` (wpa_state, bssid, …) – used to explain *why* a
		Wi-Fi connection attempt failed (wrong key, AP not found, DHCP only, …).
		Empty dict if wpa_supplicant isn't reachable."""
		result = {}
		try:
			out = check_output([wpaCliBin, "-i", interface, "status"], stderr=DEVNULL, timeout=2).decode(errors="replace")
			for line in out.splitlines():
				key, sep, val = line.partition("=")
				if sep:
					result[key.strip()] = val.strip()
		except Exception as err:
			self.log(f"getWiFiStatus: {interface} wpa_cli failed '{err}'!")
		self.log(f"getWiFiStatus: {interface} = {result}.")
		return result

	def setBgscan(self, interface: str, bgscan: str):
		for conn in self.getWiFiConnections(interface):
			if conn.wifi:
				conn.wifi.bgscan = bgscan

	def getRoamingMode(self, interface: str) -> str:
		conn = self.getActiveConnection(interface)
		return conn.wifi.bgscan if (conn and conn.wifi) else ""

	def setRoamingMode(self, interface: str, mode: str):
		presets = {"auto": "simple:30:-70:3600", "fast": "simple:10:-65:300", "off": ""}
		self.setBgscan(interface, presets.get(mode, mode))

	# ------------------------------------------------------------------
	# Wake-on-WiFi
	# ------------------------------------------------------------------

	def setWakeOnWiFiCommands(self, interface: str, enable: bool) -> list[str]:
		adapter = self.adapters.get(interface)
		if adapter is None or not adapter.canWakeOnWiFi:
			return []
		self.getBaseConnection(interface).wakeOnWiFi = enable
		cmds: list[str] = []
		if enable:
			cmds.append(f"wl -i {interface} wowl 0x100")
			cmds.append(f"wl -i {interface} wowl_activate")
		else:
			cmds.append(f"wl -i {interface} wowl 0")
		procPath = BoxInfo.getItem("WakeOnLAN") or ""
		if procPath and exists(procPath):
			cmds.append(f"echo '{'enable' if enable else 'disable'}' > {procPath}")
		self.updateWowPreup(adapter, enable)
		return cmds

	def updateWowPreup(self, adapter: Adapter, enable: bool):
		baseConn = self.getBaseConnection(adapter.name)
		interface = adapter.name
		baseConn.extraLines = [x for x in baseConn.extraLines if "wowl" not in x]
		if enable:
			baseConn.extraLines.insert(0, f"pre-up wl -i {interface} wowl_activate || true")
			baseConn.extraLines.insert(0, f"pre-up wl -i {interface} wowl 0x100 || true")

	def getWakeOnWiFi(self, interface: str) -> bool:
		if interface not in self.adapters:
			return False
		return self.getBaseConnection(interface).wakeOnWiFi

	def getSupportedLinkSpeeds(self, interface: str) -> list[tuple[str, str]]:
		choices = [("auto", _("Auto"))]
		adapter = self.adapters.get(interface)
		if adapter is None or adapter.isWiFi:
			return choices
		mask = adapter.netInfo.linkSupported
		for _ethtoolMode, (bits, label) in self.LINKSPEED_BITS.items():
			if mask & bits:
				choices.append((f"{bits:#04x}", label))
		return choices

	@staticmethod
	def getLinkSpeed(interface: str) -> str:
		return fileReadLine(f"/etc/enigma2/{interface}_linkspeed", default="auto") or "auto"

	@staticmethod
	def setLinkSpeed(interface: str, value: str) -> None:
		path = f"/etc/enigma2/{interface}_linkspeed"
		if value == "auto":
			try:
				remove(path)
			except OSError:
				pass
		else:
			fileWriteLine(path, value)

	@staticmethod
	def parseMetricValue(raw: str) -> int | None:
		value = raw.split("#", 1)[0].strip().strip('"').strip("'")
		try:
			return int(value)
		except ValueError:
			return None

	@classmethod
	def getRouteMetrics(cls) -> tuple[int | None, int | None]:
		"""Returns (lanMetric, wlanMetric), or (None, None) if
		ROUTE_METRIC_FILE doesn't exist."""
		if not exists(cls.ROUTE_METRIC_FILE):
			return None, None
		lan = wlan = None
		for line in fileReadLines(cls.ROUTE_METRIC_FILE, default=[], source=MODULE_NAME):
			stripped = line.strip()
			if stripped.startswith("LAN_METRIC="):
				lan = cls.parseMetricValue(stripped.split("=", 1)[1])
			elif stripped.startswith("WLAN_METRIC="):
				wlan = cls.parseMetricValue(stripped.split("=", 1)[1])
		return lan, wlan

	@classmethod
	def setRouteMetrics(cls, lanMetric: int | None = None, wlanMetric: int | None = None) -> None:
		"""Rewrites only the LAN_METRIC/WLAN_METRIC lines in ROUTE_METRIC_FILE,
		leaving every other line untouched. No-op if the file doesn't exist."""
		if exists(cls.ROUTE_METRIC_FILE):
			newLines = []
			for line in fileReadLines(cls.ROUTE_METRIC_FILE, default=[], source=MODULE_NAME):
				stripped = line.strip()
				if lanMetric is not None and stripped.startswith("LAN_METRIC="):
					newLines.append(f"LAN_METRIC={lanMetric}")
				elif wlanMetric is not None and stripped.startswith("WLAN_METRIC="):
					newLines.append(f"WLAN_METRIC={wlanMetric}")
				else:
					newLines.append(line)
			fileWriteLines(cls.ROUTE_METRIC_FILE, newLines, source=MODULE_NAME)

	# ------------------------------------------------------------------
	# Event handlers (called by NetEventReader)
	# ------------------------------------------------------------------

	def notifyAdaptersChanged(self):
		for cb in self.onAdaptersChanged:
			try:
				cb()
			except Exception:
				pass

	def applyNetinfo(self):
		interfaces = readNetinfoInterfaces()
		self.vpnInterfaces = {
			interface: VpnInfo(
				name=interface,
				up=data.get("up", False),
				running=data.get("running", False),
				mac=data.get("mac", ""),
				rxBytes=data.get("rx_bytes", 0),
				txBytes=data.get("tx_bytes", 0),
				mtu=data.get("mtu", 0),
				ip=parseIp4(data.get("ip4", "")) if data.get("ip4") else [0, 0, 0, 0],
				netmask=parseIp4(data.get("mask", "")) if data.get("mask") else [0, 0, 0, 0],
				prefix=data.get("prefix4", 0),
				bcast=parseIp4(data.get("brd", "")) if data.get("brd") else [0, 0, 0, 0],
				link=data.get("link", False),
			)
			for interface, data in interfaces.items() if data.get("type") == "vpn"
		}
		for interface, data in interfaces.items():
			adapter = self.adapters.get(interface)
			if adapter is None:
				continue
			netInfo = adapter.netInfo
			netInfo.up = data.get("up", False)
			# Always assign, with an empty default when absent — "only assign
			# if truthy" left stale values in place after a restart.
			ip4 = data.get("ip4", "")
			netInfo.ip = parseIp4(ip4) if ip4 else [0, 0, 0, 0]
			mask = data.get("mask", "")
			netInfo.netmask = parseIp4(mask) if mask else [0, 0, 0, 0]
			gw = data.get("gw", "")
			netInfo.gateway = parseIp4(gw) if gw else [0, 0, 0, 0]
			netInfo.isDefaultGateway = bool(data.get("defgw", False))
			brd = data.get("brd", "")
			netInfo.bcast = parseIp4(brd) if brd else [0, 0, 0, 0]
			netInfo.driver = data.get("driver", "")
			netInfo.hwId = data.get("hw_id", "")
			netInfo.bus = data.get("bus", "")
			netInfo.rxBytes = data.get("rx_bytes", 0)
			netInfo.txBytes = data.get("tx_bytes", 0)
			netInfo.mtu = data.get("mtu", 0)
			netInfo.ip6 = data.get("ip6", [])
			if adapter.isWiFi:
				netInfo.ssid = data.get("ssid", "")
				netInfo.link = netInfo.up and bool(netInfo.ssid)  # link = up and associated to AP
				netInfo.bssid = data.get("bssid", "")
				netInfo.freqMhz = data.get("freq_mhz", 0)
				netInfo.channel = data.get("channel", 0)
				netInfo.bitrateBps = data.get("bitrate_bps", 0)
				netInfo.signal = data.get("signal_dbm", 0)
			else:
				netInfo.link = netInfo.up and data.get("link", False)
				netInfo.speed = data.get("speed", -1)
				netInfo.duplex = data.get("duplex", "")
				netInfo.port = data.get("port", "")
				netInfo.transceiver = data.get("transceiver", "")
				netInfo.autoneg = data.get("autoneg", False)
				netInfo.linkSupported = data.get("link_supported", 0)

	def onNetinfoUpdate(self):
		self.log("onNetinfoUpdate: Started.")
		self.netinfoUpdateTimer.start(self.NETINFO_UPDATE_DEBOUNCE_MS, True)

	def onNetinfoUpdateDebounced(self):
		self.log("onNetinfoUpdate: De-bounced.")
		self.applyNetinfo()
		self.notifyAdaptersChanged()

	def onLinkChange(self, interface: str, up: bool, running: bool):
		self.log(f"onLinkChange: {interface} up={up} running={running}.")
		adapter = self.adapters.get(interface)
		if adapter:
			netInfo = adapter.netInfo
			netInfo.up = up
			if adapter.isWiFi:
				if not running or not up:
					netInfo.link = False
					netInfo.ssid = ""
				return
			netInfo.link = up and running
			self.showToast(interface, running)
		self.notifyAdaptersChanged()

	def showToast(self, interface: str, up: bool):
		from Screens.Toast import Toast
		text = _("Network cable connected (%s)") % interface if up else _("Network cable disconnected (%s)") % interface
		icon = "\uF003" if up else "\uF004"
		Toast.instance.showToast(text=text, toasttype=Toast.TYPE_INFO, timeout=4, customIcon=icon)

	def onIpChange(self, interface: str, ipPrefix: str):
		self.log(f"onIpChange: {interface} ipPrefix={ipPrefix}.")
		adapter = self.adapters.get(interface)
		if adapter:
			adapter.netInfo.ip = parseIp4(ipPrefix.split("/")[0])
		self.notifyAdaptersChanged()

	# Pings 8.8.8.8 (fallback 1.1.1.1) per adapter with link, writes the
	# result to Adapter.hasInternet, then calls callback() once.
	def checkConnectionInternet(self, callback: Callable[[], None]):
		for adapter in self.adapters.values():
			adapter.hasInternet = False
		candidates = [
			interface
			for interface, adapter in self.adapters.items()
			if adapter.netInfo.link and adapter.netInfo.isDefaultGateway and self.activeConnection(interface) is not None
		]
		self.log(f"checkConnectionInternet: candidates={candidates}.")
		if not candidates:
			callback()
			return

		remaining = [len(candidates)]

		def onResult(interface: str, ok: bool):
			self.adapters[interface].hasInternet = ok
			remaining[0] -= 1
			if remaining[0] == 0:
				results = {interface: self.adapters[interface].hasInternet for interface in candidates}
				self.log(f"checkConnectionInternet: results={results}.")
				callback()

		def fallbackDone(interface: str, exitCode: int):
			onResult(interface, exitCode == 0)

		def primaryDone(interface: str, exitCode: int):
			if exitCode == 0:
				onResult(interface, True)
			else:
				ServiceAction.ping(interface, "1.1.1.1", lambda ec, iface=interface: fallbackDone(interface, ec))

		for interface in candidates:
			ServiceAction.ping(interface, "8.8.8.8", lambda ec, iface=interface: primaryDone(interface, ec))

	def onIfaceAdd(self, interface: str):
		self.log(f"onIfaceAdd: {interface}.")
		if interface not in self.adapters:
			self.discoverAdapters()
			self.loadInterfacesFile()
			self.loadWpaSupplicantFiles()
		self.notifyAdaptersChanged()

	def onIfaceRemove(self, interface: str):
		self.log(f"onIfaceRemove: {interface}.")
		self.adapters.pop(interface, None)
		self.notifyAdaptersChanged()

	def onScanTrigger(self, interface: str):
		self.log(f"onScanTrigger: {interface}.")
		pass  # placeholder: trigger wpa_cli scan when Wi-Fi comes up


# Wi-Fi-specific parameters for one Connection.
@dataclass
class WiFiConfig:
	ssid: str = ""
	hidden: bool = False
	encryption: Encryption = Encryption.NONE
	key: str = ""
	wepKeyType: str = "ASCII"  # "ASCII" | "HEX".
	wpaId: int | None = None
	priority: int = 0  # Wpa_supplicant priority (higher = preferred), synced from Connection.priority on save.
	disabled: bool = False  # Wpa_supplicant disabled=1.
	# Background scan – enables auto-roaming between known networks.
	# 	Format: "simple:<shortInterval>:<signalThreshold>:<longInterval>"
	# 	Set to "" to disable.
	bgscan: str = "simple:30:-70:3600"

	@property
	def needsKey(self) -> bool:
		return self.encryption != Encryption.NONE


# Logical network configuration attached to one physical Adapter.
@dataclass
class Connection:
	adapter: str = ""
	name: str = ""
	enabled: bool = False  # False -> Every line of this connection's stanza in /etc/network/interfaces is commented out with "# " (see serializeConnection()), not just "auto <iface>".
	priority: int = 0  # Higher = preferred, also wpa_supplicant priority.
	dhcp: bool = True
	ip: list[int] = field(default_factory=lambda: [0, 0, 0, 0])
	netmask: list[int] = field(default_factory=lambda: [255, 255, 255, 0])
	gateway: list[int] = field(default_factory=lambda: [0, 0, 0, 0])
	ipMode: int = 0  # 0=IPv4 only, 1=IPv6 only, 2=IPv4+IPv6.
	ipv6Dhcp: bool = True
	dnsServers: list = field(default_factory=list)  # [int,int,int,int] | "::addr".
	extraLines: list[str] = field(default_factory=list)
	wifi: WiFiConfig | None = None
	wakeOnWiFi: bool = False

	@property
	def isWiFi(self) -> bool:
		return self.wifi is not None

	def ipStr(self) -> str:
		return ".".join(str(x) for x in self.ip)

	def netmaskStr(self) -> str:
		return ".".join(str(x) for x in self.netmask)

	def gatewayStr(self) -> str:
		return ".".join(str(x) for x in self.gateway)


@dataclass
class NetInfo:
	up: bool = False
	link: bool = False  # Physical link (cable/Wi-Fi association).
	ip: list[int] = field(default_factory=lambda: [0, 0, 0, 0])
	netmask: list[int] = field(default_factory=lambda: [0, 0, 0, 0])
	gateway: list[int] = field(default_factory=lambda: [0, 0, 0, 0])
	isDefaultGateway: bool = False  # True on the one interface currently owning the system's default route.
	bcast: list[int] = field(default_factory=lambda: [0, 0, 0, 0])
	ip6: list = field(default_factory=list)  # [{"addr": "…", "prefix": 64}, …].
	speed: int = -1  # LAN only, Mbps; -1 = unknown.
	duplex: str = ""  # LAN only: "full" | "half" | "".
	port: str = ""  # LAN only: "TP" | "MII" | "FIBRE" | ….
	transceiver: str = ""  # LAN only: "internal" | "external".
	autoneg: bool = False  # LAN only.
	linkSupported: int = 0  # LAN only, ETHTOOL SUPPORTED_* bitmask from socketdaemon.
	ssid: str = ""  # Wi-Fi only.
	bssid: str = ""  # Wi-Fi only, AP MAC address.
	freqMhz: int = 0  # Wi-Fi only, channel frequency in MHz.
	channel: int = 0  # Wi-Fi only, channel number.
	bitrateBps: int = 0  # Wi-Fi only, TX bitrate in bps.
	signal: int = 0  # Wi-Fi only, dBm.
	driver: str = ""  # Kernel module name (e.g. "r8168", "mt76x2u").
	hwId: str = ""  # "VVVV:DDDD" PCI or USB vendor:product hex.
	bus: str = ""  # Physical bus from socketdaemon (e.g. "usb", "pci", "platform").
	rxBytes: int = 0  # Received data counter from /proc/net/dev.
	txBytes: int = 0  # Transmitted data counter from /proc/net/dev.
	mtu: int = 0


@dataclass
class VpnInfo:
	name: str
	up: bool = False
	running: bool = False
	mac: str = ""
	rxBytes: int = 0
	txBytes: int = 0
	mtu: int = 0
	ip: list[int] = field(default_factory=lambda: [0, 0, 0, 0])
	netmask: list[int] = field(default_factory=lambda: [0, 0, 0, 0])
	prefix: int = 0
	bcast: list[int] = field(default_factory=lambda: [0, 0, 0, 0])
	link: bool = False


@dataclass
class Adapter:
	name: str
	mac: str = ""
	isWiFi: bool = False
	module: str = ""
	driverApi: str = apiNl80211
	isBroadcomWl: bool = False  # Has the vendor "wl" tool available (needed to kick iwlist scans alive).
	canWakeOnWiFi: bool = False
	adapterEnabled: bool = False  # False -> Every line of this adapter's stanza in /etc/network/interfaces is commented out with "# " (see serializeConnection()), not just "auto <iface>".
	netInfo: NetInfo = field(default_factory=NetInfo)
	hasInternet: bool | None = None  # None = Not checked (yet) by NetworkManager.checkConnectionInternet().

	@property
	def wpaConfPath(self) -> str:
		return f"{wpaSupplicantDir}/wpa_supplicant.{self.name}.conf"

	@property
	def wpaPidPath(self) -> str:
		return f"/var/run/wpa_supplicant-{self.name}.pid"

	@property
	def wpaCtrlPath(self) -> str:
		return f"/var/run/wpa_supplicant/{self.name}"

	@property
	def metric(self) -> int | None:
		"""LAN_METRIC or WLAN_METRIC (depending on this adapter's type) from
		e2-route-metric, clamped to NetworkManager.ROUTE_METRIC_CHOICES. None
		if the daemon config file doesn't exist."""
		lanMetric, wlanMetric = networkManager.getRouteMetrics()
		if lanMetric is None:
			return None
		value = wlanMetric if self.isWiFi else lanMetric
		if value not in dict(NetworkManager.ROUTE_METRIC_CHOICES):
			value = 600 if self.isWiFi else 100
		return value


@dataclass
class NameserverConfig:

	mode: str = "dhcp-router"
	servers: list = field(default_factory=list)
	rotate: bool = False
	suffix: str = ""
	ipMode: int = 0  # 0=IPv4 + IPv6, 1=IPv6 + IPv4, 2=IPv4 only, 3=IPv6 only.


class InterfacesFile:
	_header = [
		"# Automatically generated by Enigma2.",
		"# Do NOT change manually!",
	]
	_stanzaKw = frozenset(("auto", "allow-auto", "allow-hotplug", "iface"))

	def __init__(self, path: str = interfacesFile):
		self.path = path
		self.writePath = path
		self.raw: list[str] = []
		self.load()

	def load(self):
		self.raw = fileReadLines(self.path, default=[], source=MODULE_NAME)

	def parse(self) -> tuple[dict[str, list[Connection]], set[str], set[str]]:
		result: dict[str, list[Connection]] = {}
		autoIfaces: set = set()
		wakeOnWiFiIfaces: set = set()
		current: Connection | None = None
		disabled = False
		inetSet: set[int] = set()  # Id(conn) for connections that have had inet (IPv4) stanza set.
		for raw in self.raw:
			line = raw.strip()
			if line.startswith("#"):
				inner = line[1:].strip()
				tokens_inner = inner.split()
				first = tokens_inner[0] if tokens_inner else ""
				if first in self._stanzaKw:
					line = inner
					disabled = True
				elif len(tokens_inner) >= 3 and tokens_inner[0] == "Only" and tokens_inner[1] == "WakeOnWiFi":
					wakeOnWiFiIfaces.add(tokens_inner[2])
					continue
				else:
					disabled = False
					continue
			else:
				disabled = False
			tokens = line.split()
			if not tokens:
				continue
			kw = tokens[0]
			if kw in ("auto", "allow-auto", "allow-hotplug") and len(tokens) >= 2:
				if not disabled:
					for iface in tokens[1:]:
						autoIfaces.add(iface)
				continue
			if kw == "iface" and len(tokens) >= 4:
				iface = tokens[1]
				inet = tokens[2]
				mode = tokens[3]
				if iface == "lo":
					current = None
					continue
				if inet == "inet6":
					# A commented-out "# iface ... inet6 dhcp" means IPv6 is not
					# configured. Treat it as absent instead of upgrading ipMode,
					# otherwise a disabled ipv6 stanza would come back enabled.
					if disabled:
						continue
					# IPv6 stanza, update the existing Connection for this iface,
					# do NOT create a second one.
					existing = result.get(iface, [])
					if existing:
						# 0 (IPv4 only) -> 2 (both), 1 (IPv6 placeholder) stays 1.
						existing[-1].ipMode = 2 if existing[-1].ipMode == 0 else existing[-1].ipMode
						existing[-1].ipv6Dhcp = mode == "dhcp"
						current = existing[-1]
					# If no inet stanza seen yet, create a placeholder Connection
					# (inet stanza may follow later in the file – rare but valid).
					else:
						conn = Connection(
							adapter=iface,
							name=iface,
							dhcp=True,
							ipMode=1,
							ipv6Dhcp=mode == "dhcp",
							enabled=not disabled,
							wifi=WiFiConfig() if isWirelessName(iface) else None,
						)
						result.setdefault(iface, []).append(conn)
						current = conn
					continue
				# Inet (IPv4) stanza – this is the primary Connection record.
				existing = result.get(iface, [])
				if existing and id(existing[-1]) not in inetSet:
					# Update the inet6-only placeholder with IPv4 data -> now both.
					conn = existing[-1]
					conn.ipMode = 2
				else:
					# No existing connection, or existing one already has inet data
					# (second block for the same iface) -> create a new Connection.
					conn = Connection(
						adapter=iface,
						name=iface,
						dhcp=True,
						ipMode=0,
						ipv6Dhcp=False,
						enabled=not disabled,
						wifi=WiFiConfig() if isWirelessName(iface) else None,
					)
					result.setdefault(iface, []).append(conn)
				conn.dhcp = mode == "dhcp"
				conn.enabled = not disabled
				inetSet.add(id(conn))
				current = conn
				continue
			if current is None:
				continue
			if kw == "address" and len(tokens) >= 2:
				current.ip = parseIp4(tokens[1])
			elif kw == "netmask" and len(tokens) >= 2:
				current.netmask = parseIp4(tokens[1])
			elif kw == "gateway" and len(tokens) >= 2:
				current.gateway = parseIp4(tokens[1])
			elif kw == "dns-nameservers":
				for tok in tokens[1:]:
					ip = parseIp4(tok)
					if ip:
						current.dnsServers.append(ip)
			elif kw in ("pre-up", "pre-down", "post-up", "post-down", "up", "down"):
				current.extraLines.append(raw.strip())
		return result, autoIfaces, wakeOnWiFiIfaces

	def serialize(self, connectionsByAdapter: dict[str, list[Connection]], adapterEnabledMap: dict[str, bool] | None = None) -> list[str]:
		lines: list[str] = list(self._header)
		lines.append("")
		lines.append("auto lo")
		lines.append("iface lo inet loopback")
		lines.append("")
		for interface in sorted(connectionsByAdapter):
			adapterEnabled = (adapterEnabledMap or {}).get(interface, False)
			for connection in connectionsByAdapter[interface]:
				lines.extend(serializeConnection(connection, adapterEnabled))
				lines.append("")
		return lines

	def save(self, connectionsByAdapter: dict[str, list[Connection]], adapterEnabledMap: dict[str, bool] | None = None) -> bool:
		lines = self.serialize(connectionsByAdapter, adapterEnabledMap)
		if exists(self.writePath):
			try:
				copy2(self.writePath, self.writePath + ".bak")
			except OSError as err:
				print(f"[{MODULE_NAME}] Error {err.errno}: Cannot backup '{self.writePath}'!  ({err.strerror})")

		status = fileWriteLines(self.writePath, lines, source=MODULE_NAME)
		if status:
			self.raw = lines
		return bool(status)


def serializeConnection(conn: Connection, adapterEnabled: bool) -> list[str]:
	lines: list[str] = []
	connectionPrefix = "" if conn.enabled else "# "
	lines.append(f"# Only WakeOnWiFi {conn.adapter}" if conn.wakeOnWiFi else f"{"" if adapterEnabled else "# "}auto {conn.adapter}")
	hasIpv4 = conn.ipMode in (0, 2)
	hasIpv6 = conn.ipMode in (1, 2)
	lines.append(f"iface {conn.adapter} inet6 dhcp" if hasIpv6 and conn.enabled else f"# iface {conn.adapter} inet6 dhcp")
	if hasIpv4:
		if conn.dhcp:
			lines.append(f"{connectionPrefix}iface {conn.adapter} inet dhcp")
		else:
			lines.append(f"{connectionPrefix}iface {conn.adapter} inet static")
			lines.append(f"{connectionPrefix}\thostname $(hostname)")
			lines.append(f"{connectionPrefix}\taddress {conn.ipStr()}")
			lines.append(f"{connectionPrefix}\tnetmask {conn.netmaskStr()}")
			if conn.gateway != [0, 0, 0, 0]:
				lines.append(f"{connectionPrefix}\tgateway {conn.gatewayStr()}")
	else:
		lines.append(f"# iface {conn.adapter} inet dhcp")
	if conn.dnsServers:
		serversText = " ".join(".".join(str(octet) for octet in x) if isinstance(x, list) else x for x in conn.dnsServers)
		lines.append(f"{connectionPrefix}\tdns-nameservers {serversText}")
	for extra in conn.extraLines:
		lines.append(f"{connectionPrefix}\t{extra}")
	return lines


class WpaSupplicantFile:
	WPA_DEFAULT_HEADER = [
		"ctrl_interface=/var/run/wpa_supplicant",
		"update_config=1",
		"",
	]

	def __init__(self, iface: str):
		self.iface = iface
		self.path = f"{wpaSupplicantDir}/wpa_supplicant.{iface}.conf"
		self.writePath = self.path
		self.raw = fileReadLines(self.path, default=[], source=MODULE_NAME)
		self.header: list[str] = self.extractHeader()

	def exists(self) -> bool:
		return exists(self.path)

	def extractHeader(self) -> list[str]:
		header: list[str] = []
		for line in self.raw:
			if line.strip().startswith("network"):
				break
			header.append(line)
		return header

	def parse(self) -> list[WiFiConfig]:
		configs: list[WiFiConfig] = []
		current: dict[str, str] | None = None
		depth = 0
		blockId = 0
		for line in self.raw:
			stripped = line.strip()
			if stripped.startswith("#"):
				continue
			if stripped.startswith("network") and "{" in stripped:
				current = {}
				depth = stripped.count("{") - stripped.count("}")
				continue
			if current is None:
				continue
			depth += stripped.count("{") - stripped.count("}")
			if "=" in stripped and depth > 0:
				key, sep, value = stripped.partition("=")
				current[key.strip()] = value.strip().strip('"')
			if depth <= 0 and current is not None:
				wifi = wpaDictToWiFiConfig(current, blockId)
				if wifi.ssid:
					configs.append(wifi)
				blockId += 1
				current = None
				depth = 0
		return configs

	def serialize(self, configs: list[WiFiConfig]) -> list[str]:
		header = self.header if self.header else list(self.WPA_DEFAULT_HEADER)
		lines: list[str] = list(header)
		if lines and lines[-1].strip():
			lines.append("")
		for wifi in configs:
			lines.extend(wifiConfigToWpaBlock(wifi))
			lines.append("")
		return lines

	def save(self, configs: list[WiFiConfig]) -> bool:
		if exists(self.writePath):
			try:
				copy2(self.writePath, self.writePath + ".bak")
			except OSError as err:
				print(f"[{MODULE_NAME}] Error {err.errno}: Cannot backup '{self.writePath}'!  ({err.strerror})")

		return bool(fileWriteLines(self.writePath, self.serialize(configs), source=MODULE_NAME))

	def ensureDir(self):
		makedirs(wpaSupplicantDir, exist_ok=True)


def wpaDictToWiFiConfig(fields: dict[str, str], blockId: int) -> WiFiConfig:
	keyMgmt = fields.get("key_mgmt", "NONE").upper()
	proto = fields.get("proto", "").upper()
	pairwise = fields.get("pairwise", "").upper()
	if keyMgmt == "NONE":
		enc = Encryption.NONE if not fields.get("wep_key0") else Encryption.WEP
	elif "SAE" in keyMgmt:
		enc = Encryption.WPA2_WPA3 if "WPA-PSK" in keyMgmt else Encryption.WPA3
	elif "EAP" in keyMgmt:
		sha256 = "EAP-SHA256" in keyMgmt
		plain = "EAP" in keyMgmt.replace("EAP-SHA256", "")
		if sha256 and plain:
			enc = Encryption.WPA2_WPA3_ENTERPRISE
		elif sha256:
			enc = Encryption.WPA3_ENTERPRISE
		else:
			enc = Encryption.WPA2_ENTERPRISE
	elif "WPA" in keyMgmt:
		enc = Encryption.WPA2 if ("CCMP" in pairwise or "WPA2" in proto or "RSN" in proto) else Encryption.WPA
	else:
		enc = Encryption.NONE
	try:
		priority = int(fields.get("priority", "0"))
	except ValueError:
		priority = 0
	return WiFiConfig(
		ssid=fields.get("ssid", ""),
		hidden=fields.get("scan_ssid", "0") == "1",
		encryption=enc,
		key=fields.get("psk", fields.get("wep_key0", "")),
		bgscan=fields.get("bgscan", "simple:30:-70:3600"),
		wpaId=blockId,
		priority=priority,
		disabled=fields.get("disabled", "0") == "1"
	)


def wifiConfigToWpaBlock(wifi: WiFiConfig) -> list[str]:
	lines = ["network={"]
	lines.append(f'\tssid="{wifi.ssid}"')
	if wifi.hidden:
		lines.append("\tscan_ssid=1")
	lines.append(f"\tpriority={wifi.priority}")
	if wifi.bgscan:
		lines.append(f'\tbgscan="{wifi.bgscan}"')
	match wifi.encryption:
		case Encryption.NONE:
			lines.append("\tkey_mgmt=NONE")
		case Encryption.WEP:
			lines.append("\tkey_mgmt=NONE")
			lines.append(f"\twep_key0={wifi.key}" if wifi.wepKeyType == "HEX" else f"\twep_key0=\"{wifi.key}\"")
			lines.append("\twep_tx_keyidx=0")
		case Encryption.WPA:
			lines.append("\tkey_mgmt=WPA-PSK")
			lines.append("\tproto=WPA")
			lines.append(f'\tpsk="{wifi.key}"')
		case Encryption.WPA2 | Encryption.WPA_WPA2:
			lines.append("\tkey_mgmt=WPA-PSK")
			lines.append("\tproto=RSN")
			lines.append(f'\tpsk="{wifi.key}"')
		case Encryption.WPA3:
			lines.append("\tkey_mgmt=SAE")
			lines.append("\tproto=RSN")
			lines.append("\tieee80211w=2")  # WPA3 requires protected management frames.
			lines.append(f'\tpsk="{wifi.key}"')
		case Encryption.WPA2_WPA3:
			lines.append("\tkey_mgmt=SAE WPA-PSK")  # Prefer SAE, fall back to PSK where the driver cannot do it.
			lines.append("\tproto=RSN")
			lines.append("\tieee80211w=1")
			lines.append(f'\tpsk="{wifi.key}"')
		case Encryption.WPA2_ENTERPRISE:  # 802.1X needs credentials this profile does not carry yet.
			lines.append("\tkey_mgmt=WPA-EAP")
			lines.append("\tproto=RSN")
		case Encryption.WPA3_ENTERPRISE:
			lines.append("\tkey_mgmt=WPA-EAP-SHA256")
			lines.append("\tproto=RSN")
			lines.append("\tieee80211w=2")
		case Encryption.WPA2_WPA3_ENTERPRISE:
			lines.append("\tkey_mgmt=WPA-EAP WPA-EAP-SHA256")
			lines.append("\tproto=RSN")
			lines.append("\tieee80211w=1")
	if wifi.disabled:
		lines.append("\tdisabled=1")
	lines.append("}")
	return lines


class NameserverFiles:
	RE_NS4 = compile(r"nameserver\s+(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})")
	RE_NS6 = compile(r"nameserver\s+(([0-9a-fA-F]{0,4}:){1,7}[0-9a-fA-F]{0,4})")

	def load(self, ns: NameserverConfig):
		path = resolvFile if ns.mode == "dhcp-router" else nameserverFile
		ns.servers = self.parse(path)

	def parse(self, path: str) -> list:
		servers: list = []
		for line in fileReadLines(path, default=[], source=MODULE_NAME):
			m4 = self.RE_NS4.match(line.strip())
			if m4:
				servers.append([int(x) for x in m4.group(1).split(".")])
				continue
			m6 = self.RE_NS6.match(line.strip())
			if m6:
				servers.append(m6.group(1))
		return servers

	def save(self, ns: NameserverConfig, anyDhcpActive: bool):
		def build(ns: NameserverConfig) -> list[str]:
			v4 = ["nameserver " + ".".join(str(octet) for octet in x) for x in ns.servers if isinstance(x, list) and x != [0, 0, 0, 0]]
			v6 = [f"nameserver {x}" for x in ns.servers if isinstance(x, str) and x]
			match ns.ipMode:
				case 0:
					nsLines = v4 + v6
				case 1:
					nsLines = v6 + v4
				case 2:
					nsLines = v4
				case _:
					nsLines = v6
			prefix: list[str] = []
			if ns.rotate:
				prefix.append("options rotate")
			if ns.suffix:
				prefix.append(f"domain {ns.suffix}")
			return prefix + nsLines

		lines = build(ns)
		if not anyDhcpActive:
			fileWriteLines(resolvFile, lines, source=MODULE_NAME)
		if ns.mode != "dhcp-router":
			fileWriteLines(nameserverFile, lines, source=MODULE_NAME)
		elif exists(nameserverFile):
			try:
				remove(nameserverFile)
			except OSError:
				pass


class WiFiRuntime:
	def __init__(self, adapter: Adapter):
		self.adapter = adapter

	@property
	def _iface(self) -> str:
		return self.adapter.name

	def commandsActivate(self, conn: Connection) -> list[str]:
		iface = self.adapter.name
		cmds: list[str] = []
		cmds.extend(self.commandsDeactivate())
		cmds.append(f"{ifconfigBin} {iface} up || true")
		if conn.wifi and conn.wifi.encryption != Encryption.NONE:
			cmds.append(f"{wpaSupplicantBin} -B -D {self.adapter.driverApi} -i{iface} -c{self.adapter.wpaConfPath} -P{self.adapter.wpaPidPath} || true")
		elif conn.wifi:
			ssid = conn.wifi.ssid.replace("\\", "\\\\").replace('"', '\\"').replace("$", "\\$").replace("`", "\\`")
			cmds.append(f'iwconfig {iface} essid "{ssid}" || true')
		cmds.append(f"{ifupBin} {iface}")
		return cmds

	def commandsDeactivate(self) -> list[str]:
		iface = self.adapter.name
		return [
			f"{wpaCliBin} -i{iface} terminate 2>/dev/null; true",
			f"{ifdownBin} {iface} 2>/dev/null; true",
			f"ip addr flush dev {iface} scope global 2>/dev/null; true",
		]

	def statusCommands(self) -> list[str]:
		return [f"iwconfig {self.adapter.name}"]


def readNetinfoInterfaces() -> dict:
	"""Raw "interfaces" dictionary from socketdaemon's /var/run/netinfo, {} if missing/invalid."""
	try:
		with open(netinfoPath, encoding="utf-8") as fd:
			info = loads(fd.read())
	except (OSError, JSONDecodeError):
		return {}
	return info.get("interfaces", {})


def isWirelessName(iface: str) -> bool:
	return bool(match(r"(wlan|ath|ra|wl)\d+", iface))


def parseIp4(text: str) -> list[int]:
	try:
		parts = [int(x) for x in text.split(".")]
		if len(parts) != 4 and not all(0 <= x <= 255 for x in parts):
			parts = [0, 0, 0, 0]
	except (ValueError, AttributeError):
		parts = [0, 0, 0, 0]
	return parts


class NetEventReader:
	def __init__(self, manager: NetworkManager):
		self.manager = manager
		self.sock = None
		self.buffer = b""
		self.retryTimer = None
		self.connect()

	def fileno(self) -> int:
		return self.sock.fileno() if self.sock else -1

	def doRead(self):
		try:
			data = self.sock.recv(4096)
		except OSError:
			data = b""
		if data:
			self.buffer += data
			while b"\n" in self.buffer:
				line, self.buffer = self.buffer.split(b"\n", 1)
				self.dispatch(line.decode("ascii", errors="replace").strip())
		else:
			self.disconnect()

	def connectionLost(self, failure=None):
		self.disconnect()

	def logPrefix(self) -> str:
		return "NetEventReader"

	def connect(self):
		try:
			sock = socket(AF_UNIX, SOCK_STREAM)
			sock.connect(netEventSocketPath)
			sock.setblocking(False)
			self.sock = sock
			reactor.addReader(self)
			print(f"[{MODULE_NAME}] NetEventReader connected to '{netEventSocketPath}'.")
		except OSError:
			self.scheduleRetry()

	def disconnect(self):
		if self.sock:
			try:
				reactor.removeReader(self)
			except Exception:
				pass
			try:
				self.sock.close()
			except OSError:
				pass
			self.sock = None
		self.scheduleRetry()

	def scheduleRetry(self):
		if self.retryTimer is not None:
			return
		self.retryTimer = eTimer()
		self.retryTimer.callback.append(self.retry)
		self.retryTimer.start(5000, True)

	def retry(self):
		self.retryTimer = None
		self.connect()

	def dispatch(self, line: str):
		if not line:
			return
		self.manager.log(f"NetEventReader: Received {line!r}.")
		parts = line.split(",")
		evt = parts[0]
		if evt == "UPDATE":
			self.manager.onNetinfoUpdate()
		elif evt == "LINK" and len(parts) == 4:
			self.manager.onLinkChange(parts[1], parts[2] == "up", parts[3] == "up")
		elif evt == "IP" and len(parts) == 3:
			self.manager.onIpChange(parts[1], parts[2])
		elif evt == "IFACE_ADD" and len(parts) == 2:
			self.manager.onIfaceAdd(parts[1])
		elif evt == "IFACE_REMOVE" and len(parts) == 2:
			self.manager.onIfaceRemove(parts[1])
		elif evt == "SCAN_TRIGGER" and len(parts) == 2:
			self.manager.onScanTrigger(parts[1])


class NetworkMountRepository:
	READ_MODE_WRAPPERS = ("autofs", "fstab", "enigma2")
	WRITE_MODES = ("autofs", "fstab")
	NORMALIZE_MODE = {
		"enigma2": "fstab",
		"old_enigma2": "fstab"
	}
	PROTOCOLS = ("nfs", "cifs")
	READ_XML = False
	AUTOMOUNTS_PATH = "/etc/enigma2/automounts.xml"
	AUTO_NETWORK_PATH = "/etc/auto.network"
	FSTAB_PATH = "/etc/fstab"
	MOUNT_BIN = "/bin/mount"
	DISABLED_PREFIX = "#DISABLED# "

	def parseFstabLine(self, line):
		line = line.strip()
		if not line:
			return None
		enabled = True
		if line.startswith(self.DISABLED_PREFIX):
			enabled = False
			line = line[len(self.DISABLED_PREFIX):].strip()
		elif line.startswith("#"):
			return None
		fields = line.split()
		if len(fields) < 4:
			return None
		device, mountpoint, fstype, options = fields[0], fields[1], fields[2], fields[3]
		if fstype in ("nfs", "nfs4") and ":" in device:
			protocol = "nfs"
			server, remotePath = device.split(":", 1)
			remotePath = remotePath.lstrip("/")
		elif fstype == "cifs" and device.startswith("//") and "/" in device[2:]:
			protocol = "cifs"
			server, remotePath = device[2:].split("/", 1)
		else:
			return None
		if not server or not remotePath:
			return None
		shareName = mountpoint.rstrip("/").rsplit("/", 1)[-1] or remotePath.rstrip("/").rsplit("/", 1)[-1] or "MEDIA"
		return {
			"id": f"fstab:{protocol}:{server}:{remotePath}",
			"mode": "fstab",
			"protocol": protocol,
			"enabled": enabled,
			"hddReplacement": mountpoint.rstrip("/") == "/media/hdd",
			"shareName": shareName,
			"server": server,
			"remotePath": remotePath,
			"unmanaged": True,
			**self.splitOptions(options, protocol),
		}

	def parseAutoNetworkLine(self, line):
		line = line.strip()
		if not line:
			return None
		enabled = True
		if line.startswith(self.DISABLED_PREFIX):
			enabled = False
			line = line[len(self.DISABLED_PREFIX):].strip()
		elif line.startswith("#"):
			return None
		fields = line.split(None, 2)
		if len(fields) < 3 or not fields[1].startswith("-fstype="):
			return None
		shareName, location = fields[0], fields[2]
		typeAndOptions = fields[1][len("-fstype="):].split(",")
		fstype, options = typeAndOptions[0], ",".join(typeAndOptions[1:])
		if fstype == "nfs" and ":" in location:
			protocol = "nfs"
			server, remotePath = location.split(":", 1)
			remotePath = remotePath.lstrip("/")
		elif fstype == "cifs" and location.startswith("://") and "/" in location[3:]:
			protocol = "cifs"
			server, remotePath = location[3:].split("/", 1)
		else:
			return None
		if not server or not remotePath:
			return None
		return {
			"id": f"autofs:{protocol}:{server}:{remotePath}",
			"mode": "autofs",
			"protocol": protocol,
			"enabled": enabled,
			"hddReplacement": False,
			"shareName": shareName,
			"server": server,
			"remotePath": remotePath,
			"unmanaged": True,
			**self.splitOptions(options, protocol),
		}

	def load(self):
		def readMode(node, wrapperMode):
			def readMount(node, wrapperMode, protocol):
				def text(tag, default=""):
					child = node.find(tag)
					return child.text if child is not None and child.text is not None else default

				mode = self.NORMALIZE_MODE.get(wrapperMode, wrapperMode)
				server = text("ip", "192.168.0.0")
				remotePath = text("sharedir", "/media/hdd/" if wrapperMode in ("autofs", "fstab") else "/exports/")
				shareName = text("shareName", "MEDIA")
				mount = {
					"id": f"{mode}:{protocol}:{server}:{remotePath}",
					"mode": mode,
					"protocol": protocol,
					"enabled": text("enabled", "False") in ("True", "true", "1"),
					"hddReplacement": text("hdd_replacement", "False") in ("True", "true", "1"),
					"shareName": shareName,
					"server": server,
					"remotePath": remotePath,
					"unmanaged": True,
					**self.splitOptions(text("options", "rw,nolock,tcp,utf8" if protocol == "nfs" else "rw,utf8"), protocol),
				}
				if protocol == "cifs":
					mount["username"] = text("username", "guest")
					mount["password"] = text("password")
				return mount

			mounts = []
			for protocol in self.PROTOCOLS:
				for protoNode in node.findall(protocol):
					for mountNode in protoNode.findall("mount"):
						mounts.append(readMount(mountNode, wrapperMode, protocol))
			return mounts

		def mergeUnmanaged(mounts, path, parseLine):
			known = {(mount["mode"], mount["protocol"], mount["server"], mount["remotePath"].lstrip("/")) for mount in mounts}
			for line in fileReadLines(path, default=[], source=MODULE_NAME):
				extra = parseLine(line)
				if extra is None:
					continue
				key = (extra["mode"], extra["protocol"], extra["server"], extra["remotePath"].lstrip("/"))
				if key not in known:
					mounts.append(extra)
					known.add(key)

		mounts = []
		if self.READ_XML:
			root = fileReadXML(self.AUTOMOUNTS_PATH, default="<mountmanager />", source=MODULE_NAME)
			if root is not None:
				for wrapperMode in self.READ_MODE_WRAPPERS:
					for modeNode in root.findall(wrapperMode):
						mounts += readMode(modeNode, wrapperMode)
				mounts += readMode(root, "old_enigma2")
		mergeUnmanaged(mounts, self.FSTAB_PATH, self.parseFstabLine)
		mergeUnmanaged(mounts, self.AUTO_NETWORK_PATH, self.parseAutoNetworkLine)
		return mounts

	def save(self, mounts):
		def writeMountFiles(effective):
			autoNetworkLines = [line for line in fileReadLines(self.AUTO_NETWORK_PATH, default=[], source=MODULE_NAME)
				if self.parseAutoNetworkLine(line) is None]
			fstabLines = [line for line in fileReadLines(self.FSTAB_PATH, default=[], source=MODULE_NAME)
				if self.parseFstabLine(line) is None]
			for mount, mode in effective:
				prefix = "" if mount.get("enabled") else self.DISABLED_PREFIX
				protocol = mount.get("protocol") or "nfs"
				server = mount.get("server") or ""
				remotePath = mount.get("remotePath") or ""
				shareName = mount.get("shareName") or ""
				if mode == "autofs":
					if protocol == "nfs":
						autoNetworkLines.append(f"{prefix}{shareName} -fstype=nfs,{self.buildNfsOptions(mount)} {server}:/{remotePath}")
					else:
						username = (mount.get("username") or "").replace(" ", "\\ ")
						password = (mount.get("password") or "").replace(" ", "\\ ")
						autoNetworkLines.append(f"{prefix}{shareName} -fstype=cifs,user={username},pass={password},{self.buildCifsOptions(mount)} ://{server}/{remotePath}")
				elif mode == "fstab":
					path = self.mountPointFor(mount)
					if protocol == "nfs":
						fstabLines.append(f"{prefix}{server}:/{remotePath}\t{path}\tnfs\t_netdev,{self.buildNfsOptions(mount)}\t0 0")
					else:
						username = mount.get("username") or ""
						password = mount.get("password") or ""
						fstabLines.append(f"{prefix}//{server}/{remotePath}\t{path}\tcifs\tuser={username},pass={password},_netdev,{self.buildCifsOptions(mount)}\t0 0")

			# print("[{MODULE_NAME}] NetworkMountRepository autoNetworkLines:", autoNetworkLines)
			# print("[{MODULE_NAME}] NetworkMountRepository fstabLines:", fstabLines)
			fileWriteLines(self.AUTO_NETWORK_PATH, autoNetworkLines, source=MODULE_NAME)
			fileWriteLines(self.FSTAB_PATH, fstabLines, source=MODULE_NAME)

		effective = []
		for mount in mounts:
			mode = mount.get("mode")
			if mode not in self.WRITE_MODES:
				mode = "fstab"
			effective.append((mount, mode))
		writeMountFiles(effective)

	NFS_RESERVED_OPTION_KEYS = frozenset(("ro", "rw", "nolock", "lock", "proto", "nfsvers", "rsize", "wsize", "timeo", "soft", "hard"))
	CIFS_RESERVED_OPTION_KEYS = frozenset(("user", "username", "pass", "password", "ro", "rw", "vers", "iocharset"))
	ALWAYS_IMPLIED_OPTION_KEYS = frozenset(("proto", "_netdev"))

	@classmethod
	def splitOptions(cls, rawOptions, protocol):
		tokens = [token.strip() for token in (rawOptions or "").split(",") if token.strip()]
		extra = []
		if protocol == "nfs":
			fields = {"accessMode": "rw", "nfsLocking": True, "nfsVersion": "", "nfsRsize": "0", "nfsWsize": "0", "nfsTimeo": 0, "nfsSoft": False}
			for token in tokens:
				parts = token.split("=", 1)
				key = parts[0].strip().lower()
				value = parts[1].strip() if len(parts) > 1 else ""
				if key == "ro":
					fields["accessMode"] = "ro"
				elif key == "rw":
					fields["accessMode"] = "rw"
				elif key == "nolock":
					fields["nfsLocking"] = False
				elif key == "lock":
					fields["nfsLocking"] = True
				elif key == "nfsvers":
					fields["nfsVersion"] = value
				elif key == "rsize":
					fields["nfsRsize"] = value
				elif key == "wsize":
					fields["nfsWsize"] = value
				elif key == "timeo":
					fields["nfsTimeo"] = int(value) if value.isdigit() else 0
				elif key == "soft":
					fields["nfsSoft"] = True
				elif key == "hard":
					fields["nfsSoft"] = False
				elif key in cls.ALWAYS_IMPLIED_OPTION_KEYS:
					pass
				else:
					extra.append(token)
		else:
			fields = {"username": "", "password": "", "accessMode": "rw", "smbVersion": "", "smbCharset": "utf8"}
			for token in tokens:
				parts = token.split("=", 1)
				key = parts[0].strip().lower()
				value = parts[1].strip() if len(parts) > 1 else ""
				if key in ("user", "username"):
					fields["username"] = value
				elif key in ("pass", "password"):
					fields["password"] = value
				elif key == "ro":
					fields["accessMode"] = "ro"
				elif key == "rw":
					fields["accessMode"] = "rw"
				elif key == "vers":
					fields["smbVersion"] = value
				elif key == "iocharset":
					fields["smbCharset"] = value
				elif key == "utf8" and not value:
					# Bare "utf8" token - legacy stand-in for iocharset=utf8
					# used by the old plugin's default options string.
					fields["smbCharset"] = "utf8"
				elif key in cls.ALWAYS_IMPLIED_OPTION_KEYS:
					pass
				else:
					extra.append(token)
		fields["options"] = ",".join(extra)
		return fields

	@classmethod
	def validateExtraOptions(cls, rawOptions, protocol):
		reserved = cls.NFS_RESERVED_OPTION_KEYS if protocol == "nfs" else cls.CIFS_RESERVED_OPTION_KEYS
		seen = set()
		for token in (rawOptions or "").split(","):
			token = token.strip()
			if not token:
				continue
			key = token.split("=", 1)[0].strip().lower()
			if key in reserved:
				return _("'%s' is already set by a dedicated setting above, remove it from 'Mount options'.") % token
			if key in seen:
				return _("'%s' is listed more than once in 'Mount options'.") % token
			seen.add(key)
		return None

	@staticmethod
	def buildCifsOptions(mount):
		parts = ["ro" if mount.get("accessMode") == "ro" else "rw"]
		version = mount.get("smbVersion") or ""
		if version and version != "auto":
			parts.append(f"vers={version}")
		parts.append(f"iocharset={mount.get('smbCharset') or 'utf8'}")
		extra = (mount.get("options") or "").strip()
		if extra:
			parts.append(extra)
		return ",".join(parts)

	def buildNfsOptions(self, mount):
		parts = ["ro" if mount.get("accessMode") == "ro" else "rw"]
		if not mount.get("nfsLocking", True):
			parts.append("nolock")
		parts.append("proto=tcp")
		version = mount.get("nfsVersion") or ""
		if version and version != "auto":
			parts.append(f"nfsvers={version}")
		rsize = mount.get("nfsRsize") or "0"
		if str(rsize) != "0":
			parts.append(f"rsize={rsize}")
		wsize = mount.get("nfsWsize") or "0"
		if str(wsize) != "0":
			parts.append(f"wsize={wsize}")
		timeo = mount.get("nfsTimeo") or 0
		if timeo:
			parts.append(f"timeo={timeo}")
		if mount.get("nfsSoft"):
			parts.append("soft")
		extra = (mount.get("options") or "").strip()
		if extra:
			parts.append(extra)
		return ",".join(parts)

	def newId(self):
		return f"mount-{uuid4().hex[:12]}"

	def mountPointFor(self, mount):
		shareName = mount.get("shareName") or mount.get("id", "")
		if mount.get("mode") == "autofs":
			return f"/media/autofs/{shareName}"
		if mount.get("hddReplacement"):
			return "/media/hdd"
		return f"/media/net/{shareName}"

	def isMounted(self, mount):
		mountPoint = self.mountPointFor(mount)
		if mount.get("mode") == "autofs":
			return exists(mountPoint)

		try:
			with open("/proc/self/mountinfo") as procFile:
				for line in procFile:
					fields = line.split(" ")
					if len(fields) > 4 and fields[4] == mountPoint:
						return True
		except OSError:
			pass
		return False

	def ensureMountPoint(self, mount):
		if mount.get("mode") == "fstab":
			mountPoint = self.mountPointFor(mount)
			if not exists(mountPoint):
				print(f"[{MODULE_NAME}] ensureMountPoint create dir '{mountPoint}'")
				makedirs(mountPoint, exist_ok=True)

	def buildMountCommand(self, mount):
		mountPoint = self.mountPointFor(mount)
		self.ensureMountPoint(mount)
		protocol = mount.get("protocol") or "nfs"
		server = mount.get("server") or ""
		remotePath = mount.get("remotePath") or ""
		if protocol == "nfs":
			source = f"{server}:/{remotePath}"
			options = self.buildNfsOptions(mount)
		else:
			username = mount.get("username") or ""
			password = mount.get("password") or ""
			source = f"//{server}/{remotePath}"
			options = f"user={username},pass={password},{self.buildCifsOptions(mount)}"
		return (self.MOUNT_BIN, self.MOUNT_BIN, "-t", protocol, source, mountPoint, "-o", options), mountPoint

	@staticmethod
	def credentialsPath(hostname):
		return f"/etc/enigma2/{hostname.strip()}.cache"

	def credentialsGet(self, hostname):
		if not hostname:
			return {}
		try:
			with open(self.credentialsPath(hostname), "rb") as fd:
				data = pickleLoad(fd)
		except Exception:
			return {}
		if not isinstance(data, dict):
			return {}
		username = data.get("username", "")
		password = data.get("password", "")
		return {"username": username, "password": password} if username or password else {}

	def credentialsSave(self, hostname, username, password):
		if not hostname:
			return
		path = self.credentialsPath(hostname)
		try:
			with open(path, "wb") as fd:
				pickleDump({"username": username, "password": password}, fd, -1)
			chmod(path, 0o600)  # contains a plaintext password
		except OSError as err:
			print(f"[{MODULE_NAME}] Error {err.errno}: Error writing '{path}'!  ({err.strerror})")

	def credentialsClear(self, hostname):
		if not hostname:
			return
		try:
			remove(self.credentialsPath(hostname))
		except OSError:
			pass


class NetworkCheck:
	MOUNT_BIN = "/bin/mount"

	def __init__(self):
		self.timer = eTimer()
		self.timer.callback.append(self.check)
		self.retry = 0
		self.console = Console()

	def start(self):
		self.retry = 10
		self.timer.start(1000, True)

	def check(self):
		self.timer.stop()
		if self.retry <= 0:
			return
		try:
			if gethostbyname(gethostname()) != "127.0.0.1":
				print("[{MODULE_NAME}] NetworkCheck: Done.")
				self.mountPendingShares()
				return
			self.retry -= 1
			self.timer.start(1000, True)
		except Exception as err:
			print(f"[{MODULE_NAME}] NetworkCheck: Error {err}!")

	def mountPendingShares(self):
		repository = NetworkMountRepository()
		mounts = repository.load()
		known = {mount.get("shareName") for mount in mounts if mount.get("mode") == "fstab" and not mount.get("hddReplacement")}
		self.removeOrphanedMountPoints(known)

		pending = False
		for mount in mounts:
			if mount.get("mode") == "fstab" and mount.get("enabled") and not repository.isMounted(mount):
				pending = True
				repository.ensureMountPoint(mount)

		if not pending:
			harddiskmanager.enumerateNetworkMounts(refresh=True)
			return

		def done(data, retVal, extra=None):
			if retVal:
				print(f"[{MODULE_NAME}] NetworkCheck: The 'mount -a' finished with errors, retVal='{retVal}', output='{data!r}'!")
			harddiskmanager.enumerateNetworkMounts(refresh=True)

		self.console.ePopen((self.MOUNT_BIN, self.MOUNT_BIN, "-a"), done)

	def removeOrphanedMountPoints(self, knownShareNames):
		base = "/media/net"
		if isdir(base):
			for name in listdir(base):
				if name not in knownShareNames:
					path = f"{base}/{name}"
					if not isdir(path) or ismount(path):
						continue
					try:
						rmdir(path)
						print(f"[{MODULE_NAME}] NetworkCheck: Removed orphaned mount point '{path!r}'.")
					except OSError as err:
						print(f"[{MODULE_NAME}] NetworkCheck Error: Could not remove orphaned mount point '{path!r}'!  ({err})")


class AvahiProvider:
	def __init__(self):
		self.typeToProtocol = {"_smb._tcp": "smb", "_nfs._tcp": "nfs"}
		self.serviceTypes = tuple(self.typeToProtocol)
		self.browser = None
		self.started = False
		self.onObservation: list[Callable] = []
		self.onSnapshot: list[Callable] = []

	def start(self):
		if not self.started:
			self.browser = eNetworkServiceBrowser()
			for serviceType in self.serviceTypes:
				self.browser.addServiceType(serviceType)
			self.browser.changed.get().append(self.changed)
			self.browser.start()
			self.started = True

	def stop(self):
		if self.started:
			self.browser.changed.get().remove(self.changed)
			self.browser.stop()
			self.browser = None
			self.started = False

	def changed(self):
		addresses = set()
		for entry in self.browser.getServices():
			self.dispatch(entry)
			addresses.update(entry["addresses"] or [])
		for callback in self.onSnapshot:
			callback(addresses)

	def dispatch(self, entry: dict):
		networkManager.log(f"AvahiProvider: found {entry["name"]} / {entry["hostname"]}")
		hostname = entry["hostname"]
		if hostname.lower().endswith(".local."):
			hostname = hostname[:-len(".local.")]
		elif hostname.lower().endswith(".local"):
			hostname = hostname[:-len(".local")]
		observation = {
			"source": "avahi",
			"protocol": self.typeToProtocol.get(entry["type"], entry["type"]),
			"name": entry["name"],
			"hostname": hostname,
			"addresses": entry["addresses"],
			"addressFamily": entry["protocol"],
			"port": entry["port"],
			"interface": entry["interface"],
			"domain": entry["domain"],
			"txt": entry["txt"],
		}
		for callback in self.onObservation:
			callback(observation)


class NetscanProvider:
	PORTS = {445: "smb", 2049: "nfs"}
	MIN_RESCAN_MS = 1000

	def __init__(self):
		self.started = False
		self.onObservation: list[Callable] = []
		self.rescanTimer = eTimer()
		self.rescanTimer.callback.append(self.onRescanTimerDone)
		self.rescanOk = None
		self.rescanCallback = None

	def start(self):
		self.started = True
		self.dispatchAll()

	def stop(self):
		self.started = False

	@staticmethod
	def defaultRouteCidr() -> str | None:
		for iface in readNetinfoInterfaces().values():
			if iface.get("defgw") and iface.get("ip4") and iface.get("prefix4") is not None:
				return f"{iface['ip4']}/{iface['prefix4']}"
		return None

	def rescan(self, callback: Callable | None = None):
		cidr = self.defaultRouteCidr()
		if not cidr:
			networkManager.log("NetscanProvider: rescan: no default-route interface with an IPv4 address.")
			if callback:
				callback(False)
			return

		def done(exitCode):
			self.rescanOk = exitCode == 0
			self.finishRescan()

		self.rescanOk = None
		self.rescanCallback = callback
		self.rescanTimer.start(self.MIN_RESCAN_MS, True)
		ServiceAction.netscan(cidr, list(self.PORTS), done)

	def onRescanTimerDone(self):
		self.finishRescan()

	def finishRescan(self):
		if self.rescanTimer.isActive() or self.rescanOk is None:
			return
		if self.rescanOk:
			self.dispatchAll()
		callback = self.rescanCallback
		if callback:
			callback(self.rescanOk)

	def dispatchAll(self):
		try:
			with open(netscanPath, encoding="utf-8") as fd:
				info = loads(fd.read())
		except (OSError, JSONDecodeError):
			info = {}
		for entry in info.get("scan", []):
			self.dispatch(entry)

	def dispatch(self, entry: dict):
		protocol = self.PORTS.get(entry.get("port"))
		if protocol:
			observation = {
				"source": "netscan",
				"protocol": protocol,
				"address": entry.get("address"),
				"hostname": entry.get("hostname") or "",
			}
			for callback in self.onObservation:
				callback(observation)


class DiscoveryManager:
	DEFAULT_RUN_MS = 30000

	def __init__(self):
		self.started = False
		self.hosts = {}
		self.onChanged: list[Callable] = []
		self.avahi = AvahiProvider()
		self.netscan = NetscanProvider()
		self.avahi.onObservation.append(self.onAvahiObservation)
		self.avahi.onSnapshot.append(self.onAvahiSnapshot)
		self.netscan.onObservation.append(self.onNetscanObservation)
		self.stopTimer = eTimer()
		self.stopTimer.callback.append(self.stop)

	def start(self, runMs: int | None = DEFAULT_RUN_MS):
		self.started = True
		self.avahi.start()
		self.netscan.start()
		self.notify()
		self.stopTimer.stop()
		if runMs:
			self.stopTimer.start(runMs, True)

	def stop(self):
		self.stopTimer.stop()
		if self.started:
			self.avahi.stop()
			self.netscan.stop()
			self.started = False

	def rescan(self, callback: Callable | None = None):
		before = {address for address, host in self.hosts.items() if host["source"] == "netscan"}
		seen = set()

		def onObservationDuringRescan(observation):
			address = observation.get("address")
			if address:
				seen.add(address)

		self.netscan.onObservation.append(onObservationDuringRescan)

		def done(ok):
			self.netscan.onObservation.remove(onObservationDuringRescan)
			if ok:
				for address in before - seen:
					host = self.hosts.get(address)
					if host and host["source"] == "netscan":
						del self.hosts[address]
				self.notify()
			if callback:
				callback(ok)

		self.netscan.rescan(done)

	@staticmethod
	def newHost(address, source):
		return {"address": address, "hostname": "", "hostnameSource": None, "protocols": set(), "source": source, "avahiShares": {}}

	@staticmethod
	def parseAvahiShareName(name):
		if name.endswith("]") and "[" in name:
			return name[name.rindex("[") + 1:-1]
		return name

	def onAvahiObservation(self, observation):
		protocol = observation.get("protocol")
		hostname = observation.get("hostname") or ""
		name = observation.get("name") or ""
		changed = False
		for address in observation.get("addresses") or []:
			host = self.hosts.get(address)
			if host is None:
				host = self.hosts[address] = self.newHost(address, "avahi")
				changed = True
			if host["source"] != "avahi":
				host["source"] = "avahi"
				changed = True
			if hostname and host["hostnameSource"] != "netscan" and (host["hostname"] != hostname or host["hostnameSource"] != "avahi"):
				host["hostname"] = hostname
				host["hostnameSource"] = "avahi"
				changed = True
			if protocol:
				if protocol not in host["protocols"]:
					host["protocols"].add(protocol)
					changed = True
				if protocol in ("nfs", "smb") and name:
					share = {"protocol": protocol, "name": self.parseAvahiShareName(name), "fullName": name}
					if host["avahiShares"].get(name) != share:
						host["avahiShares"][name] = share
						changed = True
		if changed:
			self.notify()

	def onAvahiSnapshot(self, addresses):
		stale = [address for address, host in self.hosts.items() if host["source"] == "avahi" and address not in addresses]
		for address in stale:
			del self.hosts[address]
		if stale:
			self.notify()

	def onNetscanObservation(self, observation):
		if self.started:
			address = observation.get("address")
			if address:
				host = self.hosts.setdefault(address, self.newHost(address, "netscan"))
				if host["source"] != "avahi":
					host["source"] = "netscan"
				hostname = observation.get("hostname")
				if hostname:
					host["hostname"] = hostname
					host["hostnameSource"] = "netscan"
				host["protocols"].add(observation["protocol"])

	def notify(self):
		for callback in self.onChanged:
			callback()


discoveryManager = DiscoveryManager()
networkManager = NetworkManager()
