from traceback import format_stack

from Components.Console import Console
from Components.Harddisk import getProcMounts
from Components.NetworkManager import networkManager
from Tools.ServiceAction import ServiceAction


class NetworkCompat:
	"""Plugin-facing iNetwork shim, backed by the singleton NetworkManager."""

	def __init__(self):
		self._pending = []

	# ------------------------------------------------------------------
	# Passthroughs – also needed internally by NetworkManager/new screens,
	# so the real implementation lives there.
	# ------------------------------------------------------------------

	def activateInterface(self, iface: str, callback=None):
		networkManager.activateInterface(iface, callback)

	def restartNetwork(self, callback=None):
		networkManager.restartNetwork(callback=callback)

	def getFriendlyAdapterName(self, iface: str) -> str:
		return networkManager.getFriendlyAdapterName(iface)

	# ------------------------------------------------------------------
	# Plugin-only shims
	# ------------------------------------------------------------------

	def getAdapterName(self, iface: str) -> str:
		return networkManager.getFriendlyAdapterName(iface)

	def getAdapterAttribute(self, iface: str, attr: str):
		adapter = networkManager.getAdapter(iface)
		if adapter is None:
			return None
		net = adapter.netInfo
		conn = networkManager.getActiveConnection(iface)
		attrMap = {
			"up": lambda: net.up,
			"ip": lambda: net.ip,
			"netmask": lambda: net.netmask,
			"gateway": lambda: net.gateway,
			"bcast": lambda: net.bcast,
			"mac": lambda: adapter.mac,
			"dhcp": lambda: (conn.dhcp if conn else True),
			"preup": lambda: (conn.extraLines[0] if conn and conn.extraLines else False),
			"predown": lambda: (conn.extraLines[-1] if conn and len(conn.extraLines) > 1 else False),
			"ipv6": lambda: (conn.ipMode in (1, 2) if conn else False),
		}
		getter = attrMap.get(attr)
		return getter() if getter else None

	def setAdapterAttribute(self, iface: str, attr: str, value):
		conn = networkManager.getActiveConnection(iface)
		if conn is None:
			return
		if attr == "dhcp":
			conn.dhcp = value
		elif attr == "ip":
			conn.ip = value
		elif attr == "netmask":
			conn.netmask = value
		elif attr == "gateway":
			conn.gateway = value
		elif attr == "up":
			conn.enabled = value
		elif attr == "ipv6":
			conn.ipMode = 2 if value else 0

	def getConfiguredAdapters(self) -> list[str]:
		return [
			iface for iface in networkManager.adapters
			if any(x.enabled for x in networkManager.getConnections(iface))
		]

	def getInstalledAdapters(self) -> list[str]:
		return list(networkManager.adapters.keys())

	def getAdapterList(self) -> list[str]:
		return self.getInstalledAdapters()

	def getNumberOfAdapters(self) -> int:
		return len(networkManager.adapters)

	def getInterfaces(self, callback=None):
		networkManager.load()
		if callback:
			callback(True)

	def deactivateInterface(self, ifaces, callback=None):
		if isinstance(ifaces, str):
			ifaces = [ifaces]
		wlanIfaces = [x for x in ifaces if networkManager.getAdapter(x) and networkManager.getAdapter(x).isWiFi]
		lanIfaces = [x for x in ifaces if x not in wlanIfaces]
		total = (1 if lanIfaces else 0) + len(wlanIfaces)
		if total == 0:
			if callback:
				callback(True)
			return
		done = [0]

		def _oneDone(*_args):
			done[0] += 1
			if done[0] >= total and callback:
				callback(True)

		if lanIfaces:
			self._pending.append(ServiceAction.ifdown(lanIfaces, _oneDone))
		for iface in wlanIfaces:
			self._pending.append(ServiceAction.wlanDeactivate(iface, _oneDone))

	def checkNetworkState(self, callback):
		try:
			pingTargets = ["1.1.1.1", "8.8.8.8", "9.9.9.9"]
			results = []

			def _pingDone(out, retval, extra):
				results.append(retval == 0)
				if len(results) == len(pingTargets):
					callback(sum(results))

			for target in pingTargets:
				Console().ePopen(f"/bin/ping -c 1 -W 2 {target}", _pingDone)
		except Exception:
			callback(0)

	def getNameserverList(self) -> list:
		return list(networkManager.nameserverConfig.servers)

	def clearNameservers(self):
		networkManager.nameserverConfig.servers = []

	def addNameserver(self, nameserver):
		if nameserver not in networkManager.nameserverConfig.servers:
			networkManager.nameserverConfig.servers.append(nameserver)

	def removeNameserver(self, nameserver):
		if nameserver in networkManager.nameserverConfig.servers:
			networkManager.nameserverConfig.servers.remove(nameserver)

	def changeNameserver(self, oldNameserver, newNameserver):
		servers = networkManager.nameserverConfig.servers
		if oldNameserver in servers:
			servers[servers.index(oldNameserver)] = newNameserver

	def onRemoteRootFS(self) -> bool:
		try:
			for parts in getProcMounts():
				if parts[1] == "/" and parts[2] == "nfs":
					return True
		except Exception:
			pass
		return False

	# NetworkBrowser calls these unconditionally after restartNetwork()/getInterfaces() –
	# there is no Console-based process left to stop.
	def stopRestartConsole(self):
		pass

	def stopGetInterfacesConsole(self):
		pass

	@property
	def ifaces(self) -> dict:
		result = {}
		ns = list(networkManager.nameserverConfig.servers)
		for iface, adapter in networkManager.adapters.items():
			net = adapter.netInfo
			conn = networkManager.activeConnection(iface)
			result[iface] = {
				"up": net.up,
				"ip": list(net.ip),
				"netmask": list(net.netmask),
				"gateway": list(net.gateway),
				"mac": adapter.mac,
				"dhcp": conn.dhcp if conn else True,
				"dns-nameservers": ns,
			}
		return result

	@ifaces.setter
	def ifaces(self, value):
		pass  # old callers do iNetwork.ifaces = {} before getInterfaces(); ignore

	# ------------------------------------------------------------------
	# Debug: log the caller's stack trace for every attribute that isn't
	# implemented above, so unknown legacy accesses show up in the log.
	# ------------------------------------------------------------------

	def __getattr__(self, name):
		stack = "".join(format_stack(limit=6)[:-1])
		print(f"[Network] Error: Undefined iNetwork attribute '{name}'!\nAccess stack:\n{stack}")
		raise AttributeError(name)


iNetwork = NetworkCompat()


__all__ = ["iNetwork"]
