from dataclasses import dataclass
from ipaddress import ip_address
from os import rename
from os.path import exists
from re import compile

from enigma import eTimer, gRGB

from skin import parseColor
from Components.ActionMap import HelpableActionMap
from Components.config import ConfigIP, ConfigNumber, ConfigPassword, ConfigSelection, ConfigText, ConfigYesNo, NoSave, ReadOnly, config, getConfigListEntry
from Components.Console import Console
from Components.Label import Label
from Components.NetworkManager import Adapter, Connection, Encryption, VpnInfo, WiFiConfig, encryptionLabels, iwBin, networkManager, wpaCliBin
from Components.Sources.List import List
from Components.Sources.StaticText import StaticText
from Components.SystemInfo import BoxInfo
from Screens.ChoiceBox import ChoiceBox
from Screens.Information import InformationNetwork
from Screens.MessageBox import MessageBox
from Screens.Processing import Processing
from Screens.Screen import Screen
from Screens.Setup import Setup
from Tools.Conversions import formatNetworkSpeed
from Tools.Directories import SCOPE_SKINS, fileReadLine, fileReadLines, fileReadXML, fileWriteLine, fileWriteLines, resolveFilename
from Tools.ServiceAction import ServiceAction

MODULE_NAME = __name__.split(".")[-1]

# Bitmask describing what a screen just changed about an adapter/connection,
# passed to applyAdapterChange() below. Only used here - networkManager.save()
# itself is a plain writer and doesn't need to know any of this. A caller ORs
# together every bit that applies (e.g. general settings changed AND the
# adapter ends up disabled in the same Save); applyAdapterChange() alone
# decides the resulting action and its ordering, so callers never have to
# work out priority between bits themselves.
#
CHANGE_NONE = 0  # Nothing that needs activating changed.
CHANGE_GENERAL = 1 << 0  # IP/Gateway/DNS/link speed/... changed.
CHANGE_ADAPTER_ENABLED = 1 << 1  # Adapter/connection was just enabled.
CHANGE_ADAPTER_DISABLED = 1 << 2  # Adapter/connection was just disabled.


def ip4Str(ipAddress: list) -> str:
	joined = ".".join(str(x) for x in ipAddress)
	return "" if joined == "0.0.0.0" else joined


def applyAdapterChange(interface: str, change: int, callback):
	def afterDownCallback(*args):
		networkManager.save()
		afterUpCallback(*args)

	def afterRestartCallback(*args):
		Processing.instance.hideProgress()
		callback()

	def afterUpCallback(*args):
		networkManager.notifyNetworkPlugins(True, interface=interface)
		afterRestartCallback(*args)

	if change == CHANGE_NONE:
		if callable(callback):
			callback()
	else:
		networkManager.notifyNetworkPlugins(False, interface=interface)
		Processing.instance.setDescription(_("Please wait..."))
		Processing.instance.showProgress(endless=True)
		if change & CHANGE_ADAPTER_DISABLED:
			adapter = networkManager.adapters.get(interface)
			if adapter and adapter.isWiFi:
				ServiceAction.wlanDeactivate(interface, afterDownCallback)
			else:
				ServiceAction.ifdown(interface, afterDownCallback)
		elif change & CHANGE_GENERAL:
			networkManager.save()
			networkManager.restartNetwork(interface=interface, callback=afterRestartCallback)
		elif change & CHANGE_ADAPTER_ENABLED:
			networkManager.save()
			ServiceAction.ifup(interface, afterUpCallback)
		else:
			afterRestartCallback()


def scanResultToConnection(scanResult, adapter):
	return Connection(adapter=adapter, name=scanResult.ssid, dhcp=True, enabled=True, priority=0, wifi=WiFiConfig(ssid=scanResult.ssid, encryption=scanResult.encryption))


# Adapters (top list) and Saved Wi-Fi Networks for the selected adapter (bottom list).
#
class NetworkOverview(Screen):
	skin = """
	<screen name="NetworkOverview" title="Network Overview" position="center,center" size="1100,540" resolution="1280,720">
		<widget source="adapterList" render="Listbox" position="10,10" size="e-20,250">
			<template name="Default" colors="#0000CC00,#00CC0000,#00CCCCCC,#00003300,#00330000,#00333333" fonts="Regular;25,enigma2icons;38,Regular;24,Regular;18,enigma2icons;20" itemHeight="50">
				<rowtemplate>
					<text index="AdapterName" position="0,0" size="250,50" font="0" foregroundColor="gray" padding="5,0" verticalAlignment="center" />
					<text index="StatusText" position="270,0" size="170,50" font="0" foregroundColor="gray" padding="5,0" verticalAlignment="center" />
					<text index="MAC" position="440,0" size="180,50" font="0" foregroundColor="gray" padding="5,0" verticalAlignment="center" />
					<text index="IPAddress" position="620,0" size="160,50" font="0" foregroundColor="gray" padding="5,0" verticalAlignment="center" />
					<text index="Gateway" position="780,0" size="160,50" font="0" foregroundColor="gray" padding="5,0" verticalAlignment="center" />
					<text index="Speed" position="940,0" size="140,50" font="0" foregroundColor="gray" padding="5,0" verticalAlignment="center" />
				</rowtemplate>
				<rowtemplate>
					<text index="AdapterGlyph" position="0,6" size="48,38" font="1" horizontalAlignment="center" padding="5,0" verticalAlignment="center" />
					<text index="AdapterName" position="60,0" size="170,28" font="2" padding="5,0" verticalAlignment="center" />
					<text index="AdapterType" position="60,28" size="170,22" font="3" padding="5,0" verticalAlignment="center" />
					<text index="InternetGlyph" position="230,15" size="40,20" font="4" horizontalAlignment="center" padding="5,0" verticalAlignment="center" />
					<text index="StatusText" position="270,0" size="170,50" font="3" foregroundColor="+StatusColor" foregroundColorSelected="+StatusColorSelected" padding="5,0" verticalAlignment="center" />
					<text index="MAC" position="440,0" size="180,50" font="3" padding="5,0" verticalAlignment="center" />
					<text index="IPAddress" position="620,0" size="160,50" font="3" padding="5,0" verticalAlignment="center" />
					<text index="Gateway" position="780,0" size="160,50" font="3" padding="5,0" verticalAlignment="center" />
					<text index="Speed" position="940,0" size="140,50" font="3" padding="5,0" verticalAlignment="center" />
				</rowtemplate>
			</template>
		</widget>
		<widget source="savedLabel" render="Label" position="10,270" size="e-20,25" foregroundColor="gray" padding="10,0" verticalAlignment="center" widgetBorderColor="gray" widgetBorderWidth="1">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="savedList" render="Listbox" position="10,305" size="e-20,175">
			<template name="Default" colors="#0000CC00,#00CC0000,#00CCCCCC,#00003300,#00330000,#00333333" fonts="Regular;25,Regular;20,enigma2icons;25" itemHeight="35">
				<rowtemplate>
					<text index="SSID" position="0,0" size="270,35" font="0" foregroundColor="gray" padding="5,0" verticalAlignment="center" />
					<text index="StatusText" position="270,0" size="80,35" font="0" foregroundColor="gray" padding="5,0" verticalAlignment="center" />
					<text index="BSSID" position="350,0" size="210,35" font="0" foregroundColor="gray" padding="5,0" verticalAlignment="center" />
					<text index="Frequency" position="560,0" size="140,35" font="0" foregroundColor="gray" padding="5,0" verticalAlignment="center" />
					<text index="Channel" position="700,0" size="120,35" font="0" foregroundColor="gray" padding="5,0" verticalAlignment="center" />
					<text index="Encryption" position="820,0" size="260,35" font="0" foregroundColor="gray" padding="5,0" verticalAlignment="center" />
				</rowtemplate>
				<rowtemplate>
					<text index="SSID" position="0,0" size="270,35" font="1" padding="5,0" verticalAlignment="center" />
					<text index="StatusGlyph" position="270,0" size="80,35" font="2" foregroundColor="+StatusColor" foregroundColorSelected="+StatusColorSelected" padding="5,0" verticalAlignment="center" />
					<text index="BSSID" position="350,0" size="210,35" font="1" padding="5,0" verticalAlignment="center" />
					<text index="Frequency" position="560,0" size="140,35" font="1" padding="5,0" verticalAlignment="center" />
					<text index="Channel" position="700,0" size="120,35" font="1" padding="5,0" verticalAlignment="center" />
					<text index="Encryption" position="820,0" size="260,35" font="1" padding="5,0" verticalAlignment="center" />
				</rowtemplate>
			</template>
		</widget>
		<widget source="key_red" render="Label" position="10,e-50" size="180,40" backgroundColor="key_red" font="Regular;20" foregroundColor="key_text" horizontalAlignment="center" wrap="off" verticalAlignment="center">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="key_green" render="Label" position="200,e-50" size="180,40" backgroundColor="key_green" font="Regular;20" foregroundColor="key_text" horizontalAlignment="center" wrap="off" verticalAlignment="center">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="key_yellow" render="Label" position="390,e-50" size="180,40" backgroundColor="key_yellow" font="Regular;20" foregroundColor="key_text" horizontalAlignment="center" wrap="off" verticalAlignment="center">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="key_blue" render="Label" position="580,e-50" size="180,40" backgroundColor="key_blue" font="Regular;20" foregroundColor="key_text" horizontalAlignment="center" wrap="off" verticalAlignment="center">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="key_menu" render="Label" position="e-300,e-50" size="90,40" backgroundColor="key_back" font="Regular;20" foregroundColor="key_text" horizontalAlignment="center" wrap="off" verticalAlignment="center">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="key_info" render="Label" position="e-200,e-50" size="90,40" backgroundColor="key_back" font="Regular;20" foregroundColor="key_text" horizontalAlignment="center" wrap="off" verticalAlignment="center">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="key_help" render="Label" position="e-100,e-50" size="90,40" backgroundColor="key_back" font="Regular;20" foregroundColor="key_text" horizontalAlignment="center" wrap="off" verticalAlignment="center">
			<convert type="ConditionalShowHide" />
		</widget>
	</screen>
	"""

	def __init__(self, session):
		def greenHelp():
			if self.currentList == "adapterList":
				helpText = _("Deactivate network adapter") if self.getCurrentAdapter().adapterEnabled else _("Activate network adapter")
			else:
				helpText = _("Disable saved Wi-Fi network") if self.getCurrentSaved().enabled else _("Enable saved Wi-Fi network")
			return helpText

		def doClose():
			networkManager.onAdaptersChanged.remove(self.refreshAdapters)

		Screen.__init__(self, session, enableHelp=True)
		self.setTitle(_("Network Overview"))
		self["savedLabel"] = StaticText()
		self["key_red"] = StaticText(_("Close"))
		self["key_green"] = StaticText()
		self["key_yellow"] = StaticText()
		self["key_blue"] = StaticText()
		self["key_menu"] = StaticText(_("MENU"))
		self["key_info"] = StaticText(_("INFO"))
		indexNames = {
			"Reserved_for_rowTemplate": 0,
			"AdapterGlyph": 1,
			"AdapterName": 2,
			"AdapterType": 3,
			"StatusText": 4,
			"StatusColor": 5,
			"StatusColorSelected": 6,
			"MAC": 7,
			"IPAddress": 8,
			"Gateway": 9,
			"Speed": 10,
			"InternetGlyph": 11
		}
		self.indexAdapter = 12
		self["adapterList"] = List([], indexNames=indexNames)
		indexNames = {
			"Reserved_for_rowTemplate": 0,
			"SSID": 1,
			"BSSID": 2,
			"Frequency": 3,
			"Channel": 4,
			"Encryption": 5,
			"StatusText": 6,
			"StatusGlyph": 7,
			"StatusColor": 8,
			"StatusColorSelected": 9
		}
		self.indexSaved = 10
		self["savedList"] = List([], indexNames=indexNames)
		self.currentList = "adapterList"
		self["adapterList"].onSelectionChanged.append(self.buildSaved)
		self["savedList"].onSelectionChanged.append(self.updateButtons)
		self["actions"] = HelpableActionMap(self, ["OkCancelActions", "MenuActions", "InfoActions", "ColorActions", "NavigationActions"], {
			"ok": (self.keyOK, _("Open the Network Adapter Settings for the selected item")),
			"cancel": (self.close, _("Close the screen")),
			"close": (self.keyCloseRecursive, _("Close the screen and exit all menus")),
			"menu": (self.keyMenu, _("Open the Context Menu for the selected item")),
			"info": (self.keyInfo, _("Show the Network Information for the selected adapter")),
			"red": (self.close, _("Close the screen")),
			"green": (self.keyGreen, greenHelp),
			"yellow": (self.keyYellow, _("Add a new Saved Wi-Fi Network")),
			"blue": (self.keyBlue, _("Connect to the selected Saved Wi-Fi Network")),
			"top": (self.keyTop, _("Move to first line / screen")),
			"pageUp": (self.keyPageUp, _("Move up a screen")),
			"up": (self.keyUp, _("Move up a line")),
			"first": (self.keyLeft, _("Move to the Adapter list")),
			"left": (self.keyLeft, _("Move to the Adapter list")),
			"right": (self.keyRight, _("Move to the Saved Wi-Fi Networks list")),
			"last": (self.keyRight, _("Move to the Saved Wi-Fi Networks list")),
			"down": (self.keyDown, _("Move down a line")),
			"pageDown": (self.keyPageDown, _("Move down a screen")),
			"bottom": (self.keyBottom, _("Move to last line / screen"))
		}, prio=0, description=_("Network Overview Actions"))
		self.overviewTemplateHeader = 0
		self.overviewTemplateRow = 1
		# defaultColors definitions:
		#	Index	Color	Meaning
		#	-----	-----	-------
		# 	0	Green	Connected.
		# 	1	Red	LAN without link.
		# 	2	Gray	Disabled / Not associated / Saved connection.
		# 	3	Green	Connected, row selected.
		# 	4	Red	LAN without link, row selected.
		# 	5	Gray	Disabled / Not Associated / Saved connection, row selected.
		self.defaultColors = (gRGB(0x0000CC00).argb(), gRGB(0x00CC0000).argb(), gRGB(0x00808080).argb(), gRGB(0x0000CC00).argb(), gRGB(0x00CC0000).argb(), gRGB(0x00808080).argb())
		self.encryptionShortText = {
			Encryption.NONE: "open",
			Encryption.WEP: "WEP",
			Encryption.WPA: "WPA",
			Encryption.WPA2: "WPA2",
			Encryption.WPA3: "WPA3",
			Encryption.WPA2_WPA3: "WPA2/WPA3",
			Encryption.WPA2_ENTERPRISE: "WPA2 Enterprise",
			Encryption.WPA3_ENTERPRISE: "WPA3 Enterprise",
			Encryption.WPA2_WPA3_ENTERPRISE: "WPA2/WPA3 Enterprise"
		}
		self.internetChecked = False
		self.onLayoutFinish.append(self.layoutFinished)
		self.onShown.append(self.checkInternet)
		self.onClose.append(doClose)

	def getCurrentAdapter(self) -> Adapter | None:
		entry = self["adapterList"].getCurrent()
		return entry[self.indexAdapter] if entry else None

	def getCurrentSaved(self) -> Connection | None:
		entry = self["savedList"].getCurrent() if self.currentList == "savedList" else None
		return entry[self.indexSaved] if entry else None

	def layoutFinished(self):
		def markHeaderNotSelectable(listName: str):
			def isOverviewRowSelectable(kind, *_):
				return kind != self.overviewTemplateHeader

			self[listName].master.content.setSelectableFunc(isOverviewRowSelectable)

		self["adapterList"].enableAutoNavigation(False)
		self["adapterList"].setLockFirstRow(True)
		markHeaderNotSelectable("adapterList")
		self["savedList"].enableAutoNavigation(False)
		self["savedList"].setLockFirstRow(True)
		markHeaderNotSelectable("savedList")
		networkManager.onAdaptersChanged.append(self.refreshAdapters)
		self.buildAdapters()
		self.setListFocus("adapterList")

	def checkInternet(self):
		def checkInternetCallback():
			self.internetChecked = True
			if "adapterList" in self:  # This callback comes from a another thread and this screen may close before it uses the callback.
				self.refreshAdapters()

		if not self.internetChecked:
			networkManager.checkConnectionInternet(callback=checkInternetCallback)

	def refreshAdapters(self):
		oldGateways = {x[self.indexAdapter].name: x[self.indexAdapter].netInfo.gateway for x in self["adapterList"].getList() if x[self.indexAdapter] is not None}
		newGateways = {name: adapter.netInfo.gateway for name, adapter in networkManager.getAdapters().items()}
		if oldGateways != newGateways:
			self.internetChecked = False
			self.checkInternet()
		else:
			oldRows = self["adapterList"].getList()
			newRows = self.buildAdapterRows()
			if len(oldRows) != len(newRows):
				adapterIndex = self["adapterList"].getCurrentIndex() if self["adapterList"].count() > 1 else -1
				count = self["savedList"].count()
				savedIndex = self["savedList"].getCurrentIndex() if count and count > 1 else -1
				self.buildAdapters()
				try:
					if adapterIndex != -1:
						self["adapterList"].setCurrentIndex(adapterIndex)
					if self.currentList == "savedList" and savedIndex != -1:
						self["savedList"].setCurrentIndex(savedIndex)
				except Exception:
					pass
			else:
				for index, (oldRow, newRow) in enumerate(zip(oldRows, newRows)):
					if oldRow != newRow:
						self["adapterList"].updateEntry(index, newRow)
				self.buildSaved(preserveSelection=True)

	def buildAdapters(self):
		self["adapterList"].setList(self.buildAdapterRows())
		if self["adapterList"].count() > 1:
			self["adapterList"].index = 1
		self.buildSaved()
		if any(x.isWiFi for x in networkManager.getAdapters().values()):
			self["key_yellow"].setText(_("Add Wi-Fi"))
			self["actions"].setEnabledAction("yellow", True)
		else:
			self["key_yellow"].setText("")
			self["actions"].setEnabledAction("yellow", False)

	def buildAdapterRows(self) -> list[tuple]:
		# Row for the adapter listbox. Same template for LAN and Wi-Fi. No per-type extra line.
		#
		def buildOverviewAdapterRow(adapter: Adapter) -> tuple:
			netInfo = adapter.netInfo
			if not adapter.adapterEnabled:
				statusText, statusColor, statusColorSelected = _("Deactivated"), idle, idleSelected
			elif netInfo.link:
				statusText, statusColor, statusColorSelected = _("Connected"), connected, connectedSelected
			elif adapter.isWiFi:
				statusText, statusColor, statusColorSelected = _("Not Connected"), idle, idleSelected
			else:
				statusText, statusColor, statusColorSelected = _("Cable Unplugged"), noLink, noLinkSelected
			if adapter.isWiFi:
				speed = f"{netInfo.bitrateBps // 1000000} Mbps" if netInfo.bitrateBps else "-"
			else:
				speed = formatNetworkSpeed(netInfo.speed) if netInfo.speed > 0 else "-"
			internet = adapter.adapterEnabled and adapter.hasInternet
			inetGlyph = "\uEA68" if internet else ""  # Glyph is Cloud.
			return (
				self.overviewTemplateRow,
				"\uE9FE" if adapter.isWiFi else "\uEA5A",                         # AdapterGlyph (Glyphs are Wi-fi and Settings Ethernet).
				adapter.name,                                                     # AdapterName.
				_("Wi-Fi Adapter") if adapter.isWiFi else _("Ethernet Adapter"),  # AdapterType.
				statusText,                                                       # StatusText.
				statusColor,                                                      # StatusColor.
				statusColorSelected,                                              # StatusColorSelected.
				adapter.mac.upper(),                                              # MAC.
				ip4Str(netInfo.ip) or "-",                                        # IPAddress.
				ip4Str(netInfo.gateway) or "-",                                   # Gateway.
				speed,                                                            # Speed.
				inetGlyph,                                                        # InternetGlyph.
				adapter,                                                          # -> indexAdapter.
			)

		def buildOverviewVpnRow(vpn: VpnInfo) -> tuple:
			if vpn.up and vpn.link:
				statusText, statusColor, statusColorSelected = _("Connected"), connected, connectedSelected
			elif vpn.up:
				statusText, statusColor, statusColorSelected = _("Up"), idle, idleSelected
			else:
				statusText, statusColor, statusColorSelected = _("Down"), noLink, noLinkSelected
			inetGlyph = "\uEA69" if vpn.up and vpn.link else ""  # Glyph is Cloud Locked.
			return (
				self.overviewTemplateRow,
				"\uE9AF",               # AdapterGlyph (Glyph is Vpn Key).
				vpn.name,               # AdapterName.
				_("VPN"),               # AdapterType.
				statusText,             # StatusText.
				statusColor,            # StatusColor.
				statusColorSelected,    # StatusColorSelected.
				vpn.mac.upper(),        # MAC.
				ip4Str(vpn.ip) or "-",  # IPAddress.
				"-",                    # Gateway.
				"-",                    # Speed.
				inetGlyph,              # InternetGlyph.
				None,                   # -> indexAdapter.
			)

		def buildOverviewAdapterHeaderRow() -> tuple:
			return (
				self.overviewTemplateHeader,
				None,              # AdapterGlyph.
				_("Adapter"),      # AdapterName.
				None,              # AdapterType.
				_("Status"),       # StatusText.
				None,              # StatusColor.
				None,              # StatusColorSelected.
				_("MAC Address"),  # MAC.
				_("IP Address"),   # IPAddress.
				_("Gateway"),      # Gateway.
				_("Speed"),        # Speed.
				None,              # InternetGlyph.
				None,              # -> indexAdapter.
			)

		connected, noLink, idle, connectedSelected, noLinkSelected, idleSelected = self.getOverviewColors("adapterList")
		adapters = networkManager.getAdapters()
		rows = [buildOverviewAdapterRow(adapters[iface]) for iface in sorted(adapters.keys())]
		rows += [buildOverviewVpnRow(networkManager.vpnInterfaces[iface]) for iface in sorted(networkManager.vpnInterfaces.keys())]
		if rows:
			rows.insert(0, buildOverviewAdapterHeaderRow())
		return rows

	def getOverviewColors(self, listName: str) -> tuple:
		colors = self[listName].additionalTemplateAttributes.get("colors")
		if colors:
			parts = [parseColor(part.strip()).argb() for part in colors.split(",")]
			count = len(parts)
			match count:
				case 3:
					colors = tuple(parts + parts)
				case 6:
					colors = tuple(parts)
				case _:
					print(f"[{MODULE_NAME}] Error: Template 'colors' must have 3 or 6 entries (connected, noLink, idle[, connectedSelected, noLinkSelected, idleSelectedected]), got {count}!")
					colors = self.defaultColors
		else:
			colors = self.defaultColors
		return colors

	def buildSaved(self, preserveSelection: bool = False):
		adapter = self.getCurrentAdapter()
		if adapter is None or not adapter.isWiFi:
			self["savedLabel"].setText("")
			self["savedList"].setList([])
			self.setListFocus("adapterList")
		else:
			connections, rows = self.buildSavedRows(adapter)
			self["savedLabel"].setText(f"{_("Saved Wi-Fi Networks")} · {adapter.name} · {len(connections)}")
			if preserveSelection and len(rows) == self["savedList"].count():
				oldRows = self["savedList"].getList()
				for index, (oldRow, newRow) in enumerate(zip(oldRows, rows)):
					if oldRow != newRow:
						self["savedList"].updateEntry(index, newRow)
			else:
				self["savedList"].setList(rows)
				if self["savedList"].count() > 1:
					self["savedList"].index = 1
			self.updateButtons()

	def buildSavedRows(self, adapter: Adapter | None) -> tuple[list[Connection], list[tuple]]:
		# Row for the saved Wi-Fi listbox. BSSID/frequency/channel are only known
		# while this connection is the one currently associated in wpa_supplicant.conf.
		# Doesn't persist for saved networks that aren't connected right now.
		#
		def buildOverviewSavedRow(conn: Connection, adapter: Adapter) -> tuple:
			ssid = conn.wifi.ssid
			netInfo = adapter.netInfo
			isLive = netInfo.link and netInfo.ssid == ssid
			if isLive:
				statusText, statusGlyph, statusColor, statusColorSelected = _("Connected"), "\uEA77", connected, connectedSelected  # Glyph is Signal Wifi 4 Bar.
			elif conn.enabled:
				statusText, statusGlyph, statusColor, statusColorSelected = _("Not Connected"), "\uEA78", idle, idleSelected  # Glyph is Signal Wifi Bad.
			else:
				statusText, statusGlyph, statusColor, statusColorSelected = _("Disabled"), "\uEA79", idle, idleSelected  # Glyph is Signal Wifi Off.
			return (
				self.overviewTemplateRow,
				ssid,                                                                        # SSID.
				netInfo.bssid.upper() if isLive and netInfo.bssid else "-",                  # BSSID.
				f"{netInfo.freqMhz / 1000:.2f} GHz" if isLive and netInfo.freqMhz else "-",  # Frequency.
				str(netInfo.channel) if isLive and netInfo.channel else "-",                 # Channel.
				encryptionLabels.get(conn.wifi.encryption, lambda: "")(),                    # Encryption.
				statusText,                                                                  # StatusText.
				statusGlyph,                                                                 # StatusGlyph.
				statusColor,                                                                 # StatusColor.
				statusColorSelected,                                                         # StatusColorSelected.
				conn,                                                                        # -> indexSaved.
			)

		# First row of the saved Wi-Fi listbox, rendered via <rowtemplate> #0.
		# Column titles are not selectable (see isOverviewRowSelectable). All
		# texts are a static gray in the skin. Unlike the data row's StatusText
		# this one doesn't need a real StatusColor.
		#
		def buildOverviewSavedHeaderRow() -> tuple:
			return (
				self.overviewTemplateHeader,
				_("SSID"),        # SSID.
				_("BSSID"),       # BSSID.
				_("Frequency"),   # Frequency.
				_("Channel"),     # Channel.
				_("Encryption"),  # Encryption.
				_("Status"),      # StatusText.
				None,             # StatusGlyph.
				None,             # StatusColor.
				None,             # StatusColorSelected.
				None,             # -> indexSaved.
			)

		connected, noLink, idle, connectedSelected, noLinkSelected, idleSelected = self.getOverviewColors("savedList")
		if adapter is None or not adapter.isWiFi:
			connections = []
			rows = []
		else:
			connections = [x for x in networkManager.getConnections(adapter.name) if x.wifi and x.wifi.ssid]
			rows = [buildOverviewSavedRow(x, adapter) for x in connections]
			if rows:
				rows.insert(0, buildOverviewSavedHeaderRow())
		return connections, rows

	def setListFocus(self, listName: str):
		if listName == "adapterList":
			self["actions"].setEnabledAction("first", False)
			self["actions"].setEnabledAction("left", False)
			self["key_info"].setText(_("INFO"))
			self["actions"].setEnabledAction("info", True)
			self["adapterList"].selectionEnabled(True)
			self["savedList"].selectionEnabled(False)
		else:
			self["actions"].setEnabledAction("first", True)
			self["actions"].setEnabledAction("left", True)
			self["key_info"].setText("")
			self["actions"].setEnabledAction("info", False)
			self["actions"].setEnabledAction("right", False)
			self["actions"].setEnabledAction("last", False)
			self["adapterList"].selectionEnabled(False)
			self["savedList"].selectionEnabled(True)
		self.currentList = listName
		self.updateButtons()

	def updateButtons(self):
		greenText = ""
		blueText = ""
		if adapter := self.getCurrentAdapter():
			if self.currentList == "adapterList":
				greenText = _("Deactivate") if adapter.adapterEnabled else _("Activate")
				valid = self["savedList"].count() > 1
				self["actions"].setEnabledAction("right", valid)
				self["actions"].setEnabledAction("last", valid)
			else:
				if connection := self.getCurrentSaved():
					greenText = _("Disable") if connection.enabled else _("Enable")
					if connection.enabled and not self.isConnectionLive(adapter, connection):
						blueText = _("Connect")
		self["key_green"].setText(greenText)
		self["key_blue"].setText(blueText)
		self["actions"].setEnabledAction("green", greenText != "")
		self["actions"].setEnabledAction("blue", blueText != "")

	# True if saved entry is the Wi-Fi connection the adapter is currently
	# associated with, same check as buildOverviewConnectionRow()'s isLive.
	#
	def isConnectionLive(self, adapter: Adapter, conn: Connection) -> bool:
		return adapter.netInfo.link and adapter.netInfo.ssid == conn.wifi.ssid

	def keyOK(self):
		if adapter := self.getCurrentAdapter():
			if connection := self.getCurrentSaved():
				self.openWiFiSetup(adapter, connection)
			else:
				self.openAdapterSetup(adapter)

	def openWiFiSetup(self, adapter: Adapter, connection: Connection):
		self.session.openWithCallback(self.setupClosed, NetworkWiFiSetup, adapter, connection)

	def openAdapterSetup(self, adapter: Adapter):
		self.session.openWithCallback(self.setupClosed, NetworkAdapterSetup, adapter)

	def setupClosed(self, *result):
		if len(result) == 1 and isinstance(result[0], tuple):
			closeRecursive, saved = result[0][0], result[0][1]
		else:
			closeRecursive = bool(result[0]) if result else False
			saved = False
		if saved:
			self.buildAdapters()
		elif closeRecursive:
			self.keyCloseRecursive()

	def keyCloseRecursive(self):
		self.close(True)

	def keyMenu(self):
		def showContextMenu(adapter: Adapter, connection: Connection | None):
			if connection is None:
				menu = [
					(_("Adapter Settings"), "adapterSetup"),
					(_("Disable Adapter") if adapter.adapterEnabled else _("Enable adapter"), "toggleAdapter"),
					(_("Network Test"), "test"),
					(_("Restart Adapter"), "restartAdapter"),
					(_("Restart Network"), "restartNetwork"),
				]
				title = _("Adapter '%s' Context Menu") % adapter.name
			else:
				menu = [
					(_("Settings"), "setup"),
					(_("Disable Network") if connection.enabled else _("Enable network"), "toggleSaved"),
				]
				menu.append((_("Delete Network"), "delete"))
				title = _("Saved Wi-Fi Network '%s' Context Menu") % self.connectionLabel(adapter, connection)
			if adapter.isWiFi:
				menu.append((_("Scan Wi-Fi Networks"), "scan"))
				menu.append((_("Add Wi-Fi Manually"), "addManual"))
			self.session.openWithCallback(lambda choice: self.keyMenuContextCallback(choice, adapter, connection), ChoiceBox, choiceList=menu, windowTitle=title)

		showContextMenu(self.getCurrentAdapter(), self.getCurrentSaved())

	def connectionLabel(self, adapter: Adapter, connection: Connection) -> str:
		if connection.isWiFi and connection.wifi and connection.wifi.ssid:
			result = f"{connection.adapter}  │  {connection.wifi.ssid}  [{self.encryptionShortText.get(connection.wifi.encryption, connection.wifi.encryption)}]"
		else:
			result = f"{connection.adapter}  │  {"DHCP" if connection.dhcp else connection.ipStr()}"
		return result

	def keyMenuContextCallback(self, choice, adapter: Adapter, connection: Connection | None):
		def openWiFiManual(adapter: Adapter):
			connection = Connection(adapter=adapter.name, name=_("New Wi-Fi"), dhcp=True, enabled=False, wifi=WiFiConfig())
			self.session.openWithCallback(self.setupClosed, NetworkWiFiSetup, adapter, connection)

		def confirmDelete(adapter: Adapter, connection: Connection):
			def confirmDeleteCallback(confirmed: bool, adapter: Adapter, connection: Connection):
				if confirmed:
					if connection.isWiFi and connection.wifi:
						networkManager.removeConnection(adapter.name, connection.wifi.ssid)
					else:
						networkManager.connections[adapter.name] = [x for x in networkManager.getConnections(adapter.name) if x is not connection]
					networkManager.save()
					if connection.isWiFi:
						self.buildAdapters()
					else:
						applyAdapterChange(adapter.name, CHANGE_GENERAL, self.buildAdapters)

			connectionLabel = self.connectionLabel(adapter, connection)
			self.session.openWithCallback(lambda confirmed: confirmDeleteCallback(confirmed, adapter, connection), MessageBox, _("Confirm the deletion of '%s'?") % connectionLabel, type=MessageBox.TYPE_YESNO, windowTitle=_("Saved Wi-Fi Network '%s' Context Menu") % connectionLabel)

		def restartAdapter(adapter: Adapter):
			def restartAdapterCallback():
				Processing.instance.hideProgress()
				self.buildAdapters()

			Processing.instance.setDescription(_("Restarting adapter..."))
			Processing.instance.showProgress(endless=True)
			networkManager.restartNetwork(interface=adapter.name, callback=restartAdapterCallback)

		def restartNetwork():
			def restartNetworkCallback():
				Processing.instance.hideProgress()
				self.buildAdapters()

			Processing.instance.setDescription(_("Restarting network..."))
			Processing.instance.showProgress(endless=True)
			networkManager.restartNetwork(interface="all", callback=restartNetworkCallback)

		def openWiFiScan(adapter: str):
			def wifiScanDone(result: ScanResult | None, adapter: Adapter):
				if result is True:
					self.keyCloseRecursive()
				elif result:
					self.session.openWithCallback(self.setupClosed, NetworkWiFiSetup, adapter, scanResultToConnection(result, adapter.name))

			adapter = networkManager.getAdapter(adapter)
			if adapter and adapter.isWiFi:
				self.session.openWithCallback(lambda result: wifiScanDone(result, adapter), NetworkWiFiScan, adapter)

		if choice:
			match choice[1]:
				case "adapterSetup":
					self.openAdapterSetup(adapter)
				case "addManual":
					openWiFiManual(adapter)
				case "delete":
					confirmDelete(adapter, connection)
				case "restartAdapter":
					restartAdapter(adapter)
				case "restartNetwork":
					restartNetwork()
				case "scan":
					openWiFiScan(adapter.name)
				case "setup":
					self.openWiFiSetup(adapter, connection)
				case "test":
					self.session.open(NetworkTest, adapter.name)
				case "toggleAdapter":
					self.toggleAdapter(adapter)
				case "toggleSaved":
					self.toggleSaved(adapter, connection)

	def keyInfo(self):
		if adapter := self.getCurrentAdapter():
			self.session.open(NetworkInformation, adapter)

	def keyGreen(self):
		if adapter := self.getCurrentAdapter():
			if self.currentList == "adapterList":
				self.toggleAdapter(adapter)
			elif connection := self.getCurrentSaved():
				self.toggleSaved(adapter, connection)

	def toggleAdapter(self, adapter: Adapter):
		def toggleAdapterCallback():
			self.refreshAdapters()
			self.session.showInfo(_("Network adapter enabled.") if adapter.adapterEnabled else _("Network adapter disabled."))

		adapter.adapterEnabled = not adapter.adapterEnabled
		change = CHANGE_ADAPTER_ENABLED if adapter.adapterEnabled else CHANGE_ADAPTER_DISABLED
		applyAdapterChange(adapter.name, change, toggleAdapterCallback)

	def toggleSaved(self, adapter: Adapter, connection: Connection):
		def toggleSavedCallback(*_args):
			self.refreshAdapters()
			self.session.showInfo(_("Saved Wi-Fi network connection enabled.") if connection.enabled else _("Saved Wi-Fi network connection disabled."))

		if connection.enabled:
			wasLive = self.isConnectionLive(adapter, connection)
			connection.enabled = False
			networkManager.save()
			if wasLive and connection.wifi and connection.wifi.wpaId is not None:
				Console().ePopen((wpaCliBin, wpaCliBin, "-i", adapter.name, "disable_network", str(connection.wifi.wpaId)), callback=toggleSavedCallback)
			else:
				toggleSavedCallback()
		else:
			connection.enabled = True
			networkManager.save()
			toggleSavedCallback()

	def keyYellow(self):
		adapter = self.getCurrentAdapter()
		preselected = adapter if adapter and adapter.isWiFi else None
		NetworkWiFiAddFlow.start(self.session, adapter=preselected, callback=lambda *_: self.buildAdapters())

	def keyBlue(self):
		adapter = self.getCurrentAdapter()
		connection = self.getCurrentSaved()
		if adapter and connection and connection.enabled and not self.isConnectionLive(adapter, connection):
			self.session.openWithCallback(lambda *_: self.refreshAdapters(), NetworkWiFiActivator, adapter, connection)

	def keyTop(self):
		self[self.currentList].goTop()

	def keyPageUp(self):
		self[self.currentList].goPageUp()

	def keyUp(self):
		self[self.currentList].goLineUp()

	def keyLeft(self):
		self.setListFocus("adapterList")

	def keyRight(self):
		self.setListFocus("savedList")

	def keyDown(self):
		self[self.currentList].goLineDown()

	def keyPageDown(self):
		self[self.currentList].goPageDown()

	def keyBottom(self):
		self[self.currentList].goBottom()


class NetworkAdapterSetup(Setup):
	def __init__(self, session, adapter: Adapter):
		self.adapter = adapter
		self.connection = networkManager.getBaseConnection(adapter.name)
		self.buildConfigObjects()
		self.hasWakeOnLan = adapter.name == "eth0" and BoxInfo.getItem("wol") and BoxInfo.getItem("WakeOnLAN")
		Setup.__init__(self, session=session, setup="NetworkAdapter")
		self.setTitle(_("Network Adapter '%s' Settings") % adapter.name)
		self["key_info"] = StaticText(_("INFO"))
		self["infoActions"] = HelpableActionMap(self, ["InfoActions"], {
			"info": (self.keyShowInfo, _("Show network adapter connection information"))
		}, prio=0, description=_("Network Overview Actions"))

	def buildConfigObjects(self):
		adapter = self.adapter
		connection = self.connection
		self.cfgEnabled = NoSave(ConfigYesNo(default=adapter.adapterEnabled))
		self.cfgIpMode = NoSave(ConfigSelection(default=connection.ipMode, choices=[
			(0, _("IPv4 only")),
			(1, _("IPv6 only")),
			(2, _("IPv4 and IPv6")),
		]))
		self.cfgDhcp = NoSave(ConfigYesNo(default=connection.dhcp))
		self.cfgIp = NoSave(ConfigIP(default=connection.ip))
		self.cfgNetmask = NoSave(ConfigIP(default=connection.netmask))
		self.cfgGateway = NoSave(ConfigIP(default=connection.gateway))
		currentMetric = adapter.metric
		self.hasMetric = currentMetric is not None and len(networkManager.getAdapters()) > 1
		self.cfgMetric = NoSave(ConfigSelection(choices=networkManager.ROUTE_METRIC_CHOICES, default=currentMetric if currentMetric is not None else (600 if adapter.isWiFi else 100)))
		hasOwn = bool(connection.dnsServers)
		self.cfgDnsOverride = NoSave(ConfigYesNo(default=hasOwn))
		dnsV4 = [x for x in connection.dnsServers if isinstance(x, list)]
		dnsV6 = [x for x in connection.dnsServers if isinstance(x, str)]
		self.cfgDNS1v4 = NoSave(ConfigIP(default=dnsV4[0] if len(dnsV4) > 0 else [0, 0, 0, 0]))
		self.cfgDNS2v4 = NoSave(ConfigIP(default=dnsV4[1] if len(dnsV4) > 1 else [0, 0, 0, 0]))
		self.cfgDNS1v6 = NoSave(ConfigText(default=dnsV6[0] if len(dnsV6) > 0 else "", fixed_size=False))
		self.cfgDNS2v6 = NoSave(ConfigText(default=dnsV6[1] if len(dnsV6) > 1 else "", fixed_size=False))
		if not adapter.isWiFi:
			linkSpeedChoices = networkManager.getSupportedLinkSpeeds(adapter.name)
			currentLinkSpeed = networkManager.getLinkSpeed(adapter.name)
			if currentLinkSpeed not in dict(linkSpeedChoices):
				currentLinkSpeed = "auto"
			self._hasLinkSpeedChoices = len(linkSpeedChoices) > 1
			self.cfgLinkSpeed = NoSave(ConfigSelection(choices=linkSpeedChoices, default=currentLinkSpeed))
		else:
			self._hasLinkSpeedChoices = False
			self.cfgLinkSpeed = NoSave(ConfigSelection(choices=[("auto", _("Auto"))], default="auto"))
		# Wake-on-WiFi (Broadcom wlan3 only).
		# cfgWakeOnWiFi: WoW while normally active (activate=True).
		# cfgWowOnly:    WoW only, no normal connection (activate=False).
		self.cfgWakeOnWiFi = NoSave(ConfigYesNo(default=connection.wakeOnWiFi and adapter.adapterEnabled))
		self.cfgWowOnly = NoSave(ConfigYesNo(default=connection.wakeOnWiFi and not adapter.adapterEnabled))

	def keyShowInfo(self):
		self.session.open(NetworkInformation, self.adapter)

	def keySave(self):
		adapter = self.adapter
		connection = self.connection
		wasEnabled = adapter.adapterEnabled
		wasGeneral = (connection.dhcp, connection.ipMode, connection.ip, connection.netmask, connection.gateway, connection.dnsServers)
		wasLinkSpeed = networkManager.getLinkSpeed(adapter.name)
		wasMetric = adapter.metric if self.hasMetric else None
		adapter.adapterEnabled = self.cfgEnabled.value
		connection.dhcp = self.cfgDhcp.value
		connection.ipMode = self.cfgIpMode.value
		if not connection.dhcp:
			connection.ip = self.cfgIp.value
			connection.netmask = self.cfgNetmask.value
			connection.gateway = self.cfgGateway.value
		if not self.cfgDnsOverride.value:
			connection.dnsServers = []
		else:
			servers = []
			for cfgV4 in (self.cfgDNS1v4, self.cfgDNS2v4):
				ipAddress = cfgV4.value
				if ipAddress != [0, 0, 0, 0]:
					servers.append(ipAddress)
			for cfgV6 in (self.cfgDNS1v6, self.cfgDNS2v6):
				ipAddress = cfgV6.value.strip()
				if ipAddress:
					servers.append(ipAddress)
			connection.dnsServers = servers
		if adapter.isWiFi and adapter.canWakeOnWiFi:  # Apply Wake-on-WiFi (Broadcom).
			connection.wakeOnWiFi = self.cfgWakeOnWiFi.value if adapter.adapterEnabled else self.cfgWowOnly.value
			commands = networkManager.setWakeOnWiFiCommands(adapter.name, connection.wakeOnWiFi)
			if commands:
				Console().eBatch(commands, lambda result: None, debug=False)
		if not adapter.isWiFi:  # Apply forced link speed (LAN adapters only).
			networkManager.setLinkSpeed(adapter.name, self.cfgLinkSpeed.value)
		if self.hasMetric and self.cfgMetric.value != wasMetric:
			if adapter.isWiFi:
				networkManager.setRouteMetrics(wlanMetric=self.cfgMetric.value)
			else:
				networkManager.setRouteMetrics(lanMetric=self.cfgMetric.value)
		nowGeneral = (connection.dhcp, connection.ipMode, connection.ip, connection.netmask, connection.gateway, connection.dnsServers)
		change = CHANGE_NONE
		if nowGeneral != wasGeneral or self.cfgLinkSpeed.value != wasLinkSpeed:
			change |= CHANGE_GENERAL
		if adapter.adapterEnabled != wasEnabled:
			change |= CHANGE_ADAPTER_ENABLED if adapter.adapterEnabled else CHANGE_ADAPTER_DISABLED
		applyAdapterChange(adapter.name, change, lambda: self.close((False, True)))
		if self.hasWakeOnLan:
			config.network.wol.save()


# Setup screen for one Wi-Fi profile (SSID).
#
class NetworkWiFiSetup(Setup):
	def __init__(self, session, adapter: Adapter, connection: Connection):
		self.connection = connection
		self.adapter = adapter
		self.buildConfigObjects()
		Setup.__init__(self, session=session, setup="NetworkWiFi")
		self.setTitle(_("Saved Wi-Fi Network '%s' Settings") % connection.adapter)
		self["key_info"] = StaticText(_("INFO"))
		self["infoActions"] = HelpableActionMap(self, ["InfoActions"], {
			"info": (self.keyShowInfo, _("Show network adapter connection information"))
		}, prio=0, description=_("Network Overview Actions"))

	def buildConfigObjects(self):
		def rankLabel(rank, total):
			if rank == 1 and total > 1:
				return _("1. (Highest)")
			if rank == total and total > 1:
				return _("%s. (Lowest)") % rank
			return f"{rank}."

		connection = self.connection
		adapter = self.adapter
		self.cfgEnabled = NoSave(ConfigYesNo(default=connection.enabled))
		wifiConnections = [x for x in networkManager.getConnections(adapter.name) if x.isWiFi and x.wifi and x.wifi.ssid]
		if not any(x is connection for x in wifiConnections):
			wifiConnections = wifiConnections + [connection]
		self.hasMultiplePriorities = len(wifiConnections) > 1
		if self.hasMultiplePriorities:
			self.wifiConnsSorted = sorted(wifiConnections, key=lambda wifiConn: wifiConn.priority, reverse=True)
			currentRank = next((index + 1 for index, x in enumerate(self.wifiConnsSorted) if x is connection), 1)
			rankChoices = [(x + 1, rankLabel(x + 1, len(wifiConnections))) for x in range(len(wifiConnections))]
			self.cfgPriority = NoSave(ConfigSelection(default=currentRank, choices=rankChoices))
		else:
			self.wifiConnsSorted = []
			self.cfgPriority = NoSave(ConfigNumber(default=connection.priority))
		wifi = connection.wifi
		self.cfgSsid = NoSave(ConfigText(default=wifi.ssid, fixed_size=False))
		self.cfgHidden = NoSave(ConfigYesNo(default=wifi.hidden))
		encryptionChoices = [  # A hand written configuration may carry a value this screen does not offer.
			(Encryption.NONE, _("None")),
			(Encryption.WEP, "WEP"),
			(Encryption.WPA, "WPA"),
			(Encryption.WPA2, "WPA2"),
			(Encryption.WPA2_WPA3, "WPA2/WPA3"),
			(Encryption.WPA3, "WPA3"),
		]
		if wifi.encryption not in [x[0] for x in encryptionChoices]:
			encryptionChoices.append((wifi.encryption, encryptionLabels.get(wifi.encryption, lambda: str(wifi.encryption))()))
		self.cfgEncryption = NoSave(ConfigSelection(default=wifi.encryption, choices=encryptionChoices))
		self.cfgKey = NoSave(ConfigPassword(default=wifi.key, fixed_size=False))

	def keyShowInfo(self):
		self.session.open(NetworkInformation, self.adapter)

	def keySave(self):
		def wifiConnectionVerifiedCallback(ipAddress=""):
			def wifiRetryCallback(retry):
				if not retry:
					self.close((False, True, ""))

			if ipAddress:
				self.close((False, True, ipAddress))
			else:
				self.session.openWithCallback(wifiRetryCallback, MessageBox, _("Could not verify the saved Wi-Fi network.\n\nDo you want to change the settings again?"), type=MessageBox.TYPE_YESNO)

		connection = self.connection
		adapter = self.adapter
		connection.enabled = self.cfgEnabled.value
		if self.hasMultiplePriorities:
			chosenRank = self.cfgPriority.value
			others = [x for x in self.wifiConnsSorted if x is not connection]
			newOrder = others[:chosenRank - 1] + [connection] + others[chosenRank - 1:]
			for index, wifiConnection in enumerate(newOrder):
				wifiConnection.priority = (len(newOrder) - index) * 10
		else:
			connection.priority = int(self.cfgPriority.value)
		wifi = connection.wifi
		wifi.ssid = self.cfgSsid.value.strip()
		wifi.hidden = self.cfgHidden.value
		wifi.encryption = self.cfgEncryption.value
		if wifi.encryption != Encryption.NONE:
			wifi.key = self.cfgKey.value
		connections = networkManager.getConnections(adapter.name)
		if not any(x is connection for x in connections):
			connections.append(connection)
		wasEnabled = adapter.adapterEnabled
		if connection.enabled:
			adapter.adapterEnabled = True
		networkManager.saveWpaSupplicant(adapter.name)
		if not wasEnabled and adapter.adapterEnabled:
			networkManager.save()
		if connection.enabled:
			self.session.openWithCallback(wifiConnectionVerifiedCallback, NetworkWiFiActivator, adapter, connection)
		else:
			self.close((False, True))


class NetworkInformation(InformationNetwork):
	def __init__(self, session, adapter):
		InformationNetwork.__init__(self, session)
		self.adapter = adapter

	def displayInformation(self):
		InformationNetwork.displayInformation(self, selectedAdapter=self.adapter)


@dataclass
class ScanResult:
	ssid: str = ""
	bssid: str = ""
	frequency: str = ""
	channel: int = 0
	signalDbm: int | None = None  # None when the driver only reports a relative level, integer otherwise.
	signalPct: int = 0
	encryption: Encryption = Encryption.NONE
	encDetails: str = ""

	@property
	def signalGlyphs(self) -> str:
		if self.signalPct >= 80:
			result = "\uEA65"  # Glyph is Android Wifi 4 Bar.
		elif self.signalPct >= 60:
			result = "\uEA64"  # Glyph is Android Wifi 3 Bar.
		elif self.signalPct >= 35:
			result = "\uEA67"  # Glyph is Wifi 3 Bar.
		elif self.signalPct >= 10:
			result = "\uEA66"  # Glyph is Wifi 1 Bar.
		else:
			result = ""
		return result

	@property
	def signalDbmText(self) -> str:
		return f"{self.signalDbm} dBm" if self.signalDbm is not None else "-"

	@property
	def signalText(self) -> str:
		return f"{self.signalPct}%  ({self.signalDbmText})" if self.signalDbm is not None else f"{self.signalPct}%"

	@property
	def encLabel(self) -> str:
		return {
			Encryption.NONE: _("None"),
			Encryption.WEP: "WEP",
			Encryption.WPA: "WPA",
			Encryption.WPA2: "WPA2",
			Encryption.WPA3: "WPA3",
			Encryption.WPA2_WPA3: "WPA2/WPA3",
			Encryption.WPA2_ENTERPRISE: "WPA2 Enterprise",
			Encryption.WPA3_ENTERPRISE: "WPA3 Enterprise",
			Encryption.WPA2_WPA3_ENTERPRISE: "WPA2/WPA3 Enterprise",
		}.get(self.encryption, self.encryption.upper())


# Runs iw scan and shows results sorted by signal strength.
#
class NetworkWiFiScan(Screen):
	skin = """
	<screen name="NetworkWiFiScan" title="Wi-Fi Scan" position="center,center" size="1120,455" resolution="1280,720">
		<widget source="list" render="Listbox" position="10,10" size="e-20,e-105">
			<template name="Default" fonts="Regular;22,Regular;20,enigma2icons;20" itemHeight="35">
				<mode name="default">
					<panel position="0,0" size="e,e" layout="horizontal">
						<text index="Name" position="left" size="450,35" flags="scroll" font="0" padding="5,0" verticalAlignment="center" />
						<text index="Glyph" position="left" size="30,35" font="2" horizontalAlignment="center" padding="5,0" verticalAlignment="center" />
						<text index="Percentage" position="left" size="65,35" font="1" horizontalAlignment="right" padding="5,0" verticalAlignment="center" />
						<text index="dBm" position="left" size="100,35" font="1" horizontalAlignment="right" padding="5,0" verticalAlignment="center" />
						<text index="Encryption" position="left" size="245,35" font="1" horizontalAlignment="center" padding="5,0" verticalAlignment="center" />
						<text index="Channel" position="left" size="80,35" font="1" horizontalAlignment="center" padding="5,0" verticalAlignment="center" />
						<text index="Frequency" position="right" size="130,35" font="1" horizontalAlignment="right" padding="5,0" verticalAlignment="center" />
					</panel>
				</mode>
			</template>
		</widget>
		<widget name="description" position="10,e-85" size="e-20,25" padding="5,0" verticalAlignment="center" widgetBorderColor="gray" widgetBorderWidth="1" />
		<widget source="key_red" render="Label" position="10,e-50" size="180,40" backgroundColor="key_red" font="Regular;20" foregroundColor="key_text" horizontalAlignment="center" wrap="off" verticalAlignment="center">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="key_green" render="Label" position="200,e-50" size="180,40" backgroundColor="key_green" font="Regular;20" foregroundColor="key_text" horizontalAlignment="center" wrap="off" verticalAlignment="center">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="key_yellow" render="Label" position="390,e-50" size="180,40" backgroundColor="key_yellow" font="Regular;20" foregroundColor="key_text" horizontalAlignment="center" wrap="off" verticalAlignment="center">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="key_help" render="Label" position="e-100,e-50" size="90,40" backgroundColor="key_back" font="Regular;20" foregroundColor="key_text" horizontalAlignment="center" verticalAlignment="center">
			<convert type="ConditionalShowHide" />
		</widget>
	</screen>"""

	def __init__(self, session, adapter: Adapter):
		Screen.__init__(self, session, enableHelp=True)
		self.adapterObj = adapter
		self.adapter = adapter.name
		self.setTitle(_("Wi-Fi Scan On '%s'") % self.adapter)
		indexNames = {
			"Name": 0,
			"SSID": 1,
			"BSSID": 2,
			"Glyph": 3,
			"Strength": 4,
			"Percentage": 5,
			"dBm": 6,
			"Encryption": 7,
			"ChannelFrequency": 8,
			"Channel": 9,
			"Frequency": 10
		}
		self["list"] = List([], indexNames=indexNames)
		self["description"] = Label()
		self["key_red"] = StaticText(_("Close"))
		self["key_green"] = StaticText(_("Select"))
		self["key_yellow"] = StaticText(_("Rescan"))
		self["actions"] = HelpableActionMap(self, ["OkCancelActions", "ColorActions", "NavigationActions"], {
			"ok": (self.keySelect, _("Configure the selected Wi-Fi network")),
			"cancel": (self.keyClose, _("Close the screen")),
			"close": (self.closeRecursive, _("Close the screen and exit all menus")),
			"red": (self.keyClose, _("Close the screen")),
			"green": (self.keySelect, _("Configure the selected Wi-Fi network")),
			"yellow": (self.keyStartScan, _("Rescan for available Wi-Fi networks")),
			"top": (self["list"].goTop, _("Move to first line / screen")),
			"pageUp": (self["list"].goPageUp, _("Move up a screen")),
			"up": (self["list"].goLineUp, _("Move up a line")),
			"down": (self["list"].goLineDown, _("Move down a line")),
			"pageDown": (self["list"].goPageDown, _("Move down a screen")),
			"bottom": (self["list"].goBottom, _("Move to last line / screen"))
		}, prio=0, description=_("Wi-Fi Scan Actions"))
		# AKM suite types under the 00-0F-AC organisation identifier (IEEE 802.11).
		self.akmPSKTypes = {2, 4, 6, 19, 20}  # PSK, FT-PSK, PSK-SHA256, FT-PSK-SHA384, PSK-SHA384.
		self.akmSAETypes = {8, 9, 24, 25}  # SAE, FT-SAE, SAE-EXT-KEY, FT-SAE-EXT-KEY - all of them are WPA3-Personal.
		self.akmEAPTypes = {1, 3}  # 802.1X, FT-802.1X - WPA2-Enterprise.
		self.akmEAPsha256Types = {5, 11, 12, 13}  # 802.1X-SHA256, Suite-B, Suite-B-192, FT-802.1X-SHA384 - WPA3-Enterprise.
		# Verdicts that carry more detail than a bare RSN element, never overwritten by the generic branches.
		self.enterpriseEncryptions = (Encryption.WPA2_ENTERPRISE, Encryption.WPA3_ENTERPRISE, Encryption.WPA2_WPA3_ENTERPRISE)
		self.console = Console()
		self.scanning = False
		self.accessPoints: dict[str, ScanResult] = {}
		self.onLayoutFinish.append(self.layoutFinished)

	def layoutFinished(self):
		self["list"].enableAutoNavigation(False)
		self.keyStartScan()

	def keySelect(self):
		current = self["list"].getCurrent()
		if current:
			accessPoint = current[-1]
			if accessPoint.encryption in self.enterpriseEncryptions:
				self.session.open(MessageBox, _("'%s' uses enterprise authentication (802.1X). Networks like this cannot be set up here, they have to be configured manually in wpa_supplicant.conf.") % accessPoint.ssid, type=MessageBox.TYPE_INFO)
			else:
				self.close(accessPoint)

	def keyClose(self):
		if self.console:
			self.console.killAll()
		self.close(None)

	def closeRecursive(self):
		if self.console:
			self.console.killAll()
		self.close(True)

	def keyStartScan(self):
		def ifUpCallback(results=None, retVal=0, extraArgs=None):
			def iwScanCallback(results=None, retVal=0, extraArgs=None):
				self.console.ePopen((iwBin, iwBin, "dev", self.adapter, "scan"), callback=lambda results, rv, ea=None: scanFinishedCallback(results, self.parseIwScan))

			def scanFinishedCallback(results, parser):
				self.scanning = False
				if isinstance(results, bytes):
					results = results.decode("UTF-8", errors="replace")
				for accessPoint in parser(results or ""):
					self.accessPoints[accessPoint.bssid] = accessPoint
				if self.accessPoints:
					accessPointList = []
					for accessPoint in sorted(self.accessPoints.values(), key=lambda ap: -ap.signalPct):
						accessPointList.append((
							f"{accessPoint.ssid}  ({accessPoint.bssid})",            # Name.
							accessPoint.ssid,                                        # SSID.
							accessPoint.bssid,                                       # BSSID.
							accessPoint.signalGlyphs,                                # Glyph.
							accessPoint.signalText,                                  # Strength.
							f"{accessPoint.signalPct}%",                             # Percent.
							accessPoint.signalDbmText,                               # dBM.
							accessPoint.encLabel,                                    # Encryption.
							f"Ch-{accessPoint.channel}  ({accessPoint.frequency})",  # ChannelFrequency.
							f"Ch-{accessPoint.channel}",                             # Channel.
							accessPoint.frequency,                                   # Frequency.
							accessPoint                                              # AccessPoint data record.
						))
					self["list"].setList(accessPointList)
					count = len(self.accessPoints)
					self["description"].setText(ngettext("%d network found.", "%d networks found.", count) % count)
				else:
					self["list"].setList([])
					self["description"].setText(_("No networks found."))

			if not networkManager.wpaSupplicantRunning(self.adapter) and self.adapterObj.isBroadcomWl:
				self.console.ePopen(("/usr/bin/wl", "/usr/bin/wl", "up"), callback=iwScanCallback)
			else:
				iwScanCallback()

		if not self.scanning:
			self.scanning = True
			self["description"].setText(_("Scanning..."))
			if self.adapterObj.netInfo.up:
				ifUpCallback()
			else:
				self.console.ePopen(("/sbin/ifconfig", "/sbin/ifconfig", self.adapter, "up"), callback=ifUpCallback)

	@staticmethod
	def channelFromFreq(freqMhz: int) -> int:
		if freqMhz == 2484:
			return 14
		if 2412 <= freqMhz <= 2472:
			return (freqMhz - 2407) // 5
		if 5000 <= freqMhz <= 5900:
			return (freqMhz - 5000) // 5
		return 0

	def parseIwScan(self, raw: str) -> list[ScanResult]:
		# Unlike iwlist (wireless-tools), iw is nl80211-native and knows AKM suites by name,
		# SAE/WPA3 included, so no raw RSN element byte-parsing is needed here. A suite is
		# either a recognised name (e.g. "SAE", "PSK", "IEEE 802.1X/SHA-256") or, on an iw
		# build too old to know it, an "00-0f-ac:N" OUI/number fallback - suiteNumbers()
		# below picks up the latter, the plain substring checks the former.
		#
		def suiteNumbers(suiteText: str) -> set[int]:
			return {int(n) for n in compile(r":(\d+)\b").findall(suiteText)}

		def finalizeEncryption(accessPoint: ScanResult, rsnSuites: str, wpaSeen: bool, hasPrivacy: bool):
			if rsnSuites:
				numbers = suiteNumbers(rsnSuites)
				upper = rsnSuites.upper()
				isSae = bool(numbers & self.akmSAETypes) or "SAE" in upper
				isPsk = bool(numbers & self.akmPSKTypes) or "PSK" in upper
				if isSae:
					accessPoint.encryption = Encryption.WPA2_WPA3 if isPsk else Encryption.WPA3
				elif numbers:  # Numeric OUI suites let sha256/plain EAP be told apart precisely.
					sha256 = bool(numbers & self.akmEAPsha256Types)
					plain = bool(numbers & self.akmEAPTypes)
					if sha256 or plain:
						accessPoint.encryption = Encryption.WPA2_WPA3_ENTERPRISE if sha256 and plain else (Encryption.WPA3_ENTERPRISE if sha256 else Encryption.WPA2_ENTERPRISE)
					else:
						accessPoint.encryption = Encryption.WPA2
				elif "802.1X" in upper:
					sha256 = "SHA-256" in upper or "SUITE-B" in upper or "SHA-384" in upper
					accessPoint.encryption = Encryption.WPA3_ENTERPRISE if sha256 else Encryption.WPA2_ENTERPRISE
				else:
					accessPoint.encryption = Encryption.WPA2
				accessPoint.encDetails = rsnSuites
			elif wpaSeen:
				accessPoint.encryption = Encryption.WPA
			elif hasPrivacy:
				accessPoint.encryption = Encryption.WEP
			else:
				accessPoint.encryption = Encryption.NONE

		results: list[ScanResult] = []
		current: ScanResult | None = None
		reBss = compile(r"^BSS\s+([0-9A-Fa-f:]{17})")
		reSsid = compile(r"^SSID:\s*(.*)$")
		reFreq = compile(r"^freq:\s*(\d+)")
		reSignal = compile(r"^signal:\s*(-?\d+(?:\.\d+)?)\s*dBm")
		reDsChannel = compile(r"DS Parameter set:\s*channel\s*(\d+)")
		reAuthSuites = compile(r"Authentication suites:\s*(.+)")
		hasPrivacy = wpaSeen = inRsn = False
		rsnSuites = ""
		for line in raw.splitlines():
			line = line.strip()
			if match := reBss.match(line):
				if current is not None:
					finalizeEncryption(current, rsnSuites, wpaSeen, hasPrivacy)
				current = ScanResult(bssid=match.group(1).lower())
				results.append(current)
				hasPrivacy = wpaSeen = inRsn = False
				rsnSuites = ""
				continue
			if current is None:
				continue
			if match := reSsid.match(line):
				current.ssid = match.group(1)
			elif match := reFreq.match(line):
				freqMhz = int(match.group(1))
				current.frequency = f"{freqMhz / 1000:.3f} GHz"
				current.channel = self.channelFromFreq(freqMhz)
			elif match := reSignal.match(line):
				current.signalDbm = round(float(match.group(1)))
				current.signalPct = max(0, min(100, 2 * (current.signalDbm + 100)))
			elif match := reDsChannel.search(line):
				current.channel = int(match.group(1))
			elif line.startswith("capability:"):
				hasPrivacy = "Privacy" in line
			elif line.startswith("RSN:"):
				inRsn = True
			elif line.startswith("WPA:"):
				inRsn = False
				wpaSeen = True
			elif line.startswith("*"):
				if inRsn and (match := reAuthSuites.search(line)):
					rsnSuites = match.group(1)
			else:  # Any other top-level field ends the RSN/WPA information element block.
				inRsn = False
		if current is not None:
			finalizeEncryption(current, rsnSuites, wpaSeen, hasPrivacy)
		return sorted((x for x in results if x.ssid), key=lambda x: -x.signalPct)


# Runs ifup + wpa_supplicant (scoped to this one adapter, via
# wlanactivator script) and polls for an IP address, so the user
# gets feedback if the connection attempt fails or times out.
#
class NetworkWiFiActivator(Screen):
	skin = """
	<screen name="NetworkWiFiActivator" title="Wi-Fi Activator" position="center,center" size="700,220" resolution="1280,720">
		<widget name="status" position="10,10" size="e-20,e-80" font="Regular;20" horizontalAlignment="center" verticalAlignment="center" />
		<widget source="key_red" render="Label" position="10,e-50" size="180,40" backgroundColor="key_red" font="Regular;20" foregroundColor="key_text" horizontalAlignment="center" wrap="off" verticalAlignment="center">
			<convert type="ConditionalShowHide" />
		</widget>
	</screen>"""

	def __init__(self, session, adapter: Adapter, connection: Connection):
		Screen.__init__(self, session, enableHelp=True)
		self.connection = connection
		self.adapter = adapter
		self.setTitle(_("Connecting To '%s'") % adapter.name)
		self["status"] = Label()
		self["key_red"] = StaticText()  # IanSav: Why hide the close button if it is never disabled?
		self["actions"] = HelpableActionMap(self, ["OkCancelActions", "ColorActions"], {
			"cancel": (self.keyClose, _("Close the screen")),
			"red": (self.keyClose, _("Close the screen")),
		}, prio=0, description=_("Wi-Fi Activation Actions"))
		self.pollTimer = eTimer()
		self.closeTimer = eTimer()
		self.pollInterval = 1500
		self.pollMaxAttempts = 20
		self.ssid = connection.wifi.ssid if connection.wifi else adapter.name
		self.pollCount = 0
		self.onLayoutFinish.append(self.start)

	def keyClose(self):
		self.close("")

	def start(self):
		def startCallback(retval: int):
			if retval:
				self.setStatus(self.diagnoseFailure())
				self["key_red"].setText(_("Close"))
			else:
				self.beginPolling()

		self.setStatus(_("Connecting..."))
		networkId = self.connection.wifi.wpaId if self.connection.wifi else None
		ServiceAction.wlanActivate(self.adapter.name, startCallback, networkId=networkId)

	def setStatus(self, text: str):
		self["status"].setText(f"{self.ssid}  ({self.adapter.name})\n\n{text}")

	def beginPolling(self):
		self.pollCount = 0
		self.setStatus(_("Waiting for IP address..."))
		self.pollTimer.callback.append(self.checkIp)
		self.pollTimer.start(self.pollInterval, True)

	def checkIp(self):
		def delayedCloseCallback():
			self.closeTimer.stop()
			self.close(ip)

		self.pollTimer.stop()
		self.pollCount += 1
		networkManager.applyNetinfo()
		netInfo = self.adapter.netInfo
		ip = ip4Str(netInfo.ip)
		if netInfo.link and ip:
			self.setStatus(_("Connected.\nIP address is '%s'.") % ip)
			self.closeTimer.callback.append(delayedCloseCallback)
			self.closeTimer.start(5000, True)
		elif self.pollCount >= self.pollMaxAttempts:
			self.setStatus(self.diagnoseFailure())
			self["key_red"].setText(_("Close"))
		else:
			self.pollTimer.start(self.pollInterval, True)

	# Best-effort explanation of *why* the connection attempt failed, based on
	# wpa_supplicant's association state (wpa_cli status). Distinguishes a
	# missing/unreachable AP, a wrong key, and DHCP-only failures instead of a
	# single generic "failed" message. The SSID/adapter is already shown by
	# setStatus()'s header, so these messages don't repeat it.
	#
	def diagnoseFailure(self) -> str:
		interface = self.adapter.name
		if networkManager.wpaSupplicantRunning(interface):
			status = networkManager.getWiFiStatus(interface).get("wpa_state", "")
			match status:
				case "COMPLETED":
					reason = _("Connected, but no IP address was received.\nCheck the router's DHCP settings.")
				case "4WAY_HANDSHAKE" | "GROUP_HANDSHAKE":
					reason = _("Could not connect.\nWrong Wi-Fi password?")
				case "" | "DISCONNECTED" | "INACTIVE" | "SCANNING":
					reason = _("Access point not found.\nCheck it is in range and the SSID is correct.")
				case _:
					reason = _("Could not connect (status '%s').") % status
		else:
			reason = _("Could not connect.\nWi-Fi driver (wpa_supplicant) did not start, check the Wi-Fi settings.")
		return f"{reason}\n{_("Saved Wi-Fi network will be retried automatically at next boot.")}"


# Stateless coordinator. Call NetworkWiFiAddFlow.start() to begin
# the work flow of adding the adaptor and the saved network connection.
#
class NetworkWiFiAddFlow:
	@staticmethod
	def start(session, adapter: Adapter | None = None, callback=None):
		if adapter is not None:
			NetworkWiFiAddFlow.openScan(session, adapter, callback)
		else:
			wifiAdapters = [x for x in networkManager.getAdapters().values() if x.isWiFi]
			match len(wifiAdapters):
				case 0:
					session.showWarning(_("Warning: No Wi-Fi adapter found!"))
				case 1:
					NetworkWiFiAddFlow.openScan(session, wifiAdapters[0], callback)
				case _:
					NetworkWiFiAddFlow.pickAdapter(session, wifiAdapters, callback)

	@staticmethod
	def openScan(session, adapter: Adapter, callback):
		def openScanCallback(result: ScanResult | None):
			def setupCallback(*result):
				ip = ""
				if len(result) == 1 and isinstance(result[0], tuple):
					saved = bool(result[0][1]) if len(result[0]) > 1 else False
					ip = result[0][2] if len(result[0]) > 2 else ""
				else:
					saved = bool(result[0]) if result else False
				if saved:
					connections = networkManager.getConnections(adapter.name)
					if not any(x.wifi and x.wifi.ssid == (connection.wifi.ssid if connection.wifi else "") for x in connections):
						connections.append(connection)
						networkManager.saveWpaSupplicant(adapter.name)
				if callback and callable(callback):
					callback(ip)

			if result is None or result is True:
				if callback and callable(callback):
					callback()
			else:
				existing = next((x for x in networkManager.getConnections(adapter.name) if x.wifi and x.wifi.ssid == result.ssid), None)
				connection = existing if existing is not None else scanResultToConnection(result, adapter.name)
				session.openWithCallback(setupCallback, NetworkWiFiSetup, adapter, connection)

		session.openWithCallback(openScanCallback, NetworkWiFiScan, adapter)

	@staticmethod
	def pickAdapter(session, adapters: list[Adapter], callback):
		def pickAdapterCallback(adapter):
			if not adapter:
				if callback and callable(callback):
					callback()
				return
			NetworkWiFiAddFlow.openScan(session, adapter, callback)

		choices = [(_("Adapter '%s'") % x.name, x) for x in adapters]
		session.openWithCallback(pickAdapterCallback, MessageBox, _("Select Wi-Fi adapter:"), type=MessageBox.TYPE_YESNO, list=choices, windowTitle=_("Network Overview"))


# Sequential network adapter tests displayed as a simple list.
#
class NetworkTest(Screen):
	skin = """
	<screen name="NetworkTest" title="Network Test" position="center,center" size="830,280" resolution="1280,720">
		<widget source="list" render="Listbox" position="10,10" size="e-20,e-60" scrollbarMode="showNever" selection="false">
			<template name="Default" fonts="enigma2icons;25,Regular;25" itemHeight="35">
				<mode name="default">
					<text index="Glyph" position="0,0" size="35,35" font="0" foregroundColor="+Color" foregroundColorSelected="+Color" horizontalAlignment="center" padding="5,0" verticalAlignment="center" />
					<text index="Label" position="60,0" size="200,35" font="1" padding="5,0" verticalAlignment="center" />
					<text index="Result" position="260,0" size="250,35" font="1" foregroundColor="+Color" foregroundColorSelected="+Color" padding="5,0" verticalAlignment="center" />
					<text index="Detail" position="510,0" size="300,35" font="1" padding="5,0" verticalAlignment="center" />
				</mode>
			</template>
		</widget>
		<widget source="key_red" render="Label" position="10,e-50" size="180,40" backgroundColor="key_red" font="Regular;20" foregroundColor="key_text" horizontalAlignment="center" wrap="off" verticalAlignment="center">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="key_green" render="Label" position="200,e-50" size="180,40" backgroundColor="key_green" font="Regular;20" foregroundColor="key_text" horizontalAlignment="center" wrap="off" verticalAlignment="center">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="key_help" render="Label" position="e-100,e-50" size="90,40" backgroundColor="key_back" font="Regular;20" foregroundColor="key_text" horizontalAlignment="center" wrap="off" verticalAlignment="center">
			<convert type="ConditionalShowHide" />
		</widget>
	</screen>"""

	ROW_ADAPTER = 0
	ROW_LINK = 1
	ROW_IP = 2
	ROW_GATEWAY = 3
	ROW_INTERNET = 4
	ROW_DNS = 5
	INDEX_GLYPH = 0
	INDEX_LABEL = 1
	INDEX_RESULT = 2
	INDEX_DETAIL = 3
	INDEX_COLOR = 4
	STATE_OK = "ok"
	STATE_FAIL = "fail"
	STATE_SKIP = "skip"
	STATE_BUSY = "busy"
	STATES = {  # State -> (Glyph, Color)
		STATE_OK: ("\uE914", gRGB(0x0000CC00).argb()),  # Check_circle, Green.
		STATE_FAIL: ("\uE918", gRGB(0x00CC0000).argb()),  # Cancel, Red.
		STATE_SKIP: ("\uE92B", gRGB(0x00808080).argb()),  # Do_not_disturb_on, Gray.
		STATE_BUSY: ("\uE9F8", gRGB(0x00808080).argb()),  # Hourglass_empty, Gray.
	}

	def __init__(self, session, interface: str):
		Screen.__init__(self, session, enableHelp=True)
		self.setTitle(_("Network Test For '%s'") % interface)
		self.interface = interface
		self["key_red"] = StaticText(_("Close"))
		self["key_green"] = StaticText(_("Retest"))
		indexNames = {
			"Glyph": self.INDEX_GLYPH,
			"Label": self.INDEX_LABEL,
			"Result": self.INDEX_RESULT,
			"Detail": self.INDEX_DETAIL,
			"Color": self.INDEX_COLOR,
		}
		self["list"] = List([], indexNames=indexNames)
		self["actions"] = HelpableActionMap(self, ["CancelActions", "ColorActions"], {
			"cancel": (self.close, _("Close network test")),
			"close": (self.keyCloseRecursive, _("Close network test and exit all menus")),
			"red": (self.close, _("Close network test")),
			"green": (self.keyRestart, _("Restart test")),
		}, prio=0, description=_("Network Test Actions"))
		self.adapter = networkManager.adapters.get(interface)
		self.adapterName = networkManager.getFriendlyAdapterName(interface)
		self.netInfo = networkManager.getNetInfo(interface)
		self.isWiFi = self.adapter.isWiFi if self.adapter else False
		self.labels = [
			_("Adapter"),
			_("Wi-Fi link") if self.isWiFi else _("LAN link"),
			_("IP address"),
			_("Gateway"),
			"Internet",
			"DNS",
		]
		self.reachableText = _("Reachable")
		self.unreachableText = _("Unreachable")
		self.notAvailableText = _("N/A")
		self.rows: list[tuple] = []
		self.generation = 0
		self.onLayoutFinish.append(self.layoutFinished)

	def layoutFinished(self):
		self["list"].enableAutoNavigation(False)
		self["list"].selectionEnabled(False)
		self.start()

	def keyCloseRecursive(self):
		self.close(True)

	def keyRestart(self):
		self.generation += 1
		self.start()

	def start(self):
		def setRow(idx: int, state: str, result: str, detail: str):
			glyph, color = self.STATES[state]
			row = list(self.rows[idx])
			row[self.INDEX_GLYPH], row[self.INDEX_RESULT], row[self.INDEX_DETAIL], row[self.INDEX_COLOR] = glyph, result, detail, color
			self.rows[idx] = tuple(row)
			self["list"].setList(list(self.rows))

		def testLinkAndIP():
			if self.isWiFi:
				ssid = self.netInfo.ssid or ""
				if ssid:
					signal = f"{self.netInfo.signal} dBm" if self.netInfo.signal else ""
					setRow(self.ROW_LINK, self.STATE_OK, _("Associated"), f"{ssid}  {signal}".strip())
				else:
					setRow(self.ROW_LINK, self.STATE_FAIL, _("Not associated"), "")
			else:
				if self.netInfo.link:
					setRow(self.ROW_LINK, self.STATE_OK, _("Connected"), formatNetworkSpeed(self.netInfo.speed) if self.netInfo.speed > 0 else "")
				else:
					setRow(self.ROW_LINK, self.STATE_FAIL, _("Disconnected"), "")
			ipAddress = self.netInfo.ip or []
			ipAddressText = ".".join(str(x) for x in ipAddress) if ipAddress else ""
			if ipAddressText and ipAddressText != "0.0.0.0":
				connection = networkManager.activeConnection(self.interface)
				setRow(self.ROW_IP, self.STATE_OK, ipAddressText, "DHCP" if (connection and connection.dhcp) else _("Static"))
			else:
				setRow(self.ROW_IP, self.STATE_FAIL, _("No IP address"), "")
			testGateway()

		def testGateway():
			gateway = ip4Str(self.netInfo.gateway) if self.netInfo.gateway else ""
			if gateway:
				pingRow(self.ROW_GATEWAY, gateway, self.reachableText, self.unreachableText, gateway, testInternet)
			else:
				setRow(self.ROW_GATEWAY, self.STATE_SKIP, _("No gateway"), "")
				setRow(self.ROW_INTERNET, self.STATE_SKIP, self.notAvailableText, "")
				testDNS()

		def pingRow(row: int, host: str, okText: str, failText: str, detail: str, nextFunction):
			def pingRowCallback(exitCode: int):
				statusOk = exitCode == 0
				if hasattr(self, "generation") and self.generation == generation:
					setRow(row, self.STATE_OK if statusOk else self.STATE_FAIL, okText if statusOk else failText, detail)
					nextFunction()

			setRow(row, self.STATE_BUSY, _("Pinging..."), detail)
			generation = self.generation
			ServiceAction.ping(self.interface, host, pingRowCallback)

		def testInternet():
			pingRow(self.ROW_INTERNET, "1.1.1.1", self.reachableText, self.unreachableText, "Cloudflare accessible", testDNS)

		def testDNS():
			def testDNSCallback(exitCode: int):
				statusOk = exitCode == 0
				if hasattr(self, "generation") and self.generation == generation:
					setRow(self.ROW_DNS, self.STATE_OK if statusOk else self.STATE_FAIL, _("Available") if statusOk else _("Unavailable"), "Found Google")

			setRow(self.ROW_DNS, self.STATE_BUSY, _("Resolving..."), "google.com")
			generation = self.generation
			ServiceAction.resolve("google.com", testDNSCallback)

		glyph, color = self.STATES[self.STATE_BUSY]
		self.rows = [(glyph, x, "", "", color) for x in self.labels]
		self["list"].setList(self.rows)
		if self.adapter:
			setRow(self.ROW_ADAPTER, self.STATE_OK, self.interface, self.adapterName)
			testLinkAndIP()
		else:
			setRow(self.ROW_ADAPTER, self.STATE_FAIL, _("Not found"), "")
			setRow(self.ROW_LINK, self.STATE_SKIP, self.notAvailableText, "")
			setRow(self.ROW_IP, self.STATE_SKIP, self.notAvailableText, "")
			testGateway()


class DNSSettings(Setup):
	def __init__(self, session):
		def defaultGateway() -> list[int]:
			result = [0, 0, 0, 0]
			for interface in sorted(networkManager.adapters.keys()):
				if networkManager.adapters[interface].netInfo.up:
					connection = networkManager.activeConnection(interface)
					if connection:
						result = connection.gateway
						break
			return result

		dnsInitial = networkManager.nameserverConfig.servers
		self.dnsOptions = {}
		self.dnsServersV4 = []
		self.dnsServersV6 = []
		self.dnsServerItems = []
		self.dnsServerGroups = []
		if BoxInfo and BoxInfo.getItem("DNSCrypt"):
			self.dnsOptions["dnscrypt"] = {"v4": [[127, 0, 0, 1]], "v6": []}
		dnsDom = fileReadXML(resolveFilename(SCOPE_SKINS, "dnsservers.xml"), default=None, source=MODULE_NAME)
		if dnsDom is not None:
			for dns in dnsDom.findall("dnsserver"):
				key = dns.get("key", "")
				if not key:
					continue
				v4 = [[int(x) for x in ipv4.split(".")] for ipv4 in [x.strip() for x in (dns.get("ipv4", "") or "").split(",") if x.strip()]]
				v6 = [x.strip() for x in (dns.get("ipv6", "") or "").split(",") if x.strip()]
				if v4 or v6:
					self.dnsOptions[key] = {"v4": v4, "v6": v6}
		gateway = defaultGateway()
		self.dnsOptions["custom"] = {"v4": [gateway, [0, 0, 0, 0]], "v6": ["", ""]}
		self.dnsOptions["dhcp-router"] = {"v4": [gateway, [0, 0, 0, 0]], "v6": ["", ""]}
		if config.usage.dns.value not in self.dnsOptions:
			config.usage.dns.value = "custom"
		v4pos = 0
		v6pos = 0
		for dnsAddress in dnsInitial:
			if isinstance(dnsAddress, list) and len(dnsAddress) == 4 and v4pos < 2:
				self.dnsOptions["custom"]["v4"][v4pos] = dnsAddress
				self.dnsOptions["dhcp-router"]["v4"][v4pos] = dnsAddress
				v4pos += 1
			elif isinstance(dnsAddress, str):
				try:
					if ip_address(dnsAddress).version == 6 and v6pos < 2:
						self.dnsOptions["custom"]["v6"][v6pos] = dnsAddress
						self.dnsOptions["dhcp-router"]["v6"][v6pos] = dnsAddress
						v6pos += 1
				except ValueError:
					pass
		hostname = fileReadLine("/etc/hostname", default="", source=MODULE_NAME)
		self.hostname = NoSave(ConfigText(default=hostname, fixed_size=False))
		Setup.__init__(self, session=session, setup="DNS")
		self["key_yellow"] = StaticText()
		self["key_blue"] = StaticText()
		self["moveActions"] = HelpableActionMap(self, ["ColorActions"], {
			"yellow": (self.keyMoveItemUp, _("Move item up")),
			"blue": (self.keyMoveItemDown, _("Move item down")),
		}, prio=0, description=_("DNS Settings Actions"))

	def createSetup(self):  # This method replaces the method of the same name in the parent Setup class.
		self.dnsServerItems = []
		self.dnsServerGroups = []
		if config.usage.dns.value != "dnscrypt":
			current = self.dnsOptions[config.usage.dns.value]
			self.dnsServersV4 = current["v4"][:]
			self.dnsServersV6 = current["v6"][:]
			v4 = config.usage.dnsMode.value != 3
			v6 = config.usage.dnsMode.value != 2
			isCustom = config.usage.dns.value == "custom"
			entries = []
			if v4:
				for addr in self.dnsServersV4:
					entry = NoSave(ConfigIP(addr)) if isCustom else ReadOnly(NoSave(ConfigIP(default=addr)))
					entries.append(("v4", entry))
			if v6:
				for addr in self.dnsServersV6:
					entry = NoSave(ConfigText(default=addr, fixed_size=False)) if isCustom else ReadOnly(NoSave(ConfigText(default=addr, fixed_size=False)))
					entries.append(("v6", entry))
			for item, (group, entry) in enumerate(entries, start=1):
				name = _("Name server %d") % item
				if not isCustom:
					name = (name, 0)
				self.dnsServerItems.append(getConfigListEntry(name, entry, _("Enter DNS (Dynamic Name Server) %d's IP address.") % item))
				self.dnsServerGroups.append(group)
		Setup.createSetup(self, appendItems=self.dnsServerItems)

	def changedEntry(self):
		if config.usage.dns.value == "custom":
			current = self["config"].getCurrent()
			if current in self.dnsServerItems:
				index = self.dnsServerItems.index(current)
				group = self.dnsServerGroups[index]
				servers = self.dnsServersV4 if group == "v4" else self.dnsServersV6
				servers[self.groupIndex(index)] = current[1].value
		result = Setup.changedEntry(self)
		current = self["config"].getCurrent()
		canMove = current in self.dnsServerItems and config.usage.dns.value not in ("dnscrypt", "dhcp-router")
		self["moveActions"].setEnabled(canMove)
		self["key_yellow"].setText(_("Move Up") if canMove else "")
		self["key_blue"].setText(_("Move Down") if canMove else "")
		return result

	def groupIndex(self, index: int) -> int:
		return self.dnsServerGroups[:index].count(self.dnsServerGroups[index])

	def keySave(self):  # This method replaces the method of the same name in the parent Setup class.
		if self.hostname.isChanged:
			fileWriteLine("/etc/hostname", f"{self.hostname.value}\n", source=MODULE_NAME)
		servers: list = []
		match config.usage.dns.value:
			case "dnscrypt":
				servers = [[127, 0, 0, 1]]
				self.writeDnsCryptToml()
			case "custom":
				for item in self.dnsServerItems:
					value = item[1].value
					if value:
						servers.append(value)
			case _:
				for value in self.dnsServersV4 + self.dnsServersV6:
					if value:
						servers.append(value)
		networkManager.setNameservers(servers)
		networkManager.save()
		Setup.keySave(self)

	def writeDnsCryptToml(self):  # DNSCrypt TOML helpers.
		def replaceKeyLine(line, key, value, foundSet):
			lineStripped = line.lstrip()
			indent = line[:len(line) - len(lineStripped)]
			result = line
			if lineStripped.startswith((f"{key} ", f"{key}=", f"#{key} ", f"#{key}=")):
				foundSet.add(key)
				result = f"{indent}{key} = {value}"
			return result

		def tomlBoolean(value):
			return "true" if bool(value) else "false"

		def tomlString(val):
			return f"\"{str(val).replace("\\", "\\\\").replace("\"", "\\\"")}\""

		def tomlInteger(val, default=0):
			try:
				result = str(int(val))
			except Exception:
				result = str(int(default))
			return result

		def insertSectionKey(lines, sectionName, key, rhs, anchorKeys, foundSet):
			def findSectionRange(lines, sectionName):
				start = None
				result = None
				for index, line in enumerate(lines):
					lineStripped = line.strip()
					if lineStripped.startswith("[") and lineStripped.endswith("]"):
						name = lineStripped[1:-1].strip()
						if start is None and name == sectionName:
							start = index + 1
							continue
						if start is not None:
							result = (start, index)
							break
				if result is None:
					result = (start, len(lines)) if start is not None else (None, None)
				return result

			token = f"{sectionName}.{key}"
			if token not in foundSet:
				start, end = findSectionRange(lines, sectionName)
				if start is not None:
					insertAt = None
					for index in range(start, end):
						lineStripped = lines[index].lstrip()
						for anchor in anchorKeys:
							if lineStripped.startswith((f"{anchor} ", f"{anchor}=", f"#{anchor} ", f"#{anchor}=")):
								insertAt = index + 1
					lines.insert(insertAt if insertAt is not None else end, f"{key} = {rhs}")
					foundSet.add(token)

		tomlPath = "/etc/dnscrypt-proxy/dnscrypt-proxy.toml"
		oldLines = fileReadLines(tomlPath, default=[], source=MODULE_NAME)
		if oldLines:
			found = set()
			newLines = []
			currentSection = None
			for line in oldLines:
				lineStripped = line.strip()
				if lineStripped.startswith("[") and lineStripped.endswith("]"):
					currentSection = lineStripped[1:-1].strip()
					newLines.append(line)
					continue
				if currentSection is None:
					line = replaceKeyLine(line, "ipv4_servers", tomlBoolean(config.usage.dnsMode.value != 3), found)
					line = replaceKeyLine(line, "ipv6_servers", tomlBoolean(config.usage.dnsMode.value != 2), found)
					line = replaceKeyLine(line, "dnscrypt_servers", tomlBoolean(config.usage.DNSCryptProtocol.value), found)
					line = replaceKeyLine(line, "doh_servers", tomlBoolean(config.usage.DNSCryptDoH.value), found)
					line = replaceKeyLine(line, "odoh_servers", tomlBoolean(config.usage.DNSCryptODoH.value), found)
					line = replaceKeyLine(line, "require_dnssec", tomlBoolean(config.usage.DNSCryptDNSSEC.value), found)
					line = replaceKeyLine(line, "require_nolog", tomlBoolean(config.usage.DNSCryptNoLog.value), found)
					line = replaceKeyLine(line, "require_nofilter", tomlBoolean(config.usage.DNSCryptNoFilter.value), found)
					line = replaceKeyLine(line, "cache", tomlBoolean(config.usage.DNSCryptCache.value), found)
					newLines.append(line)
					continue
				if currentSection == "monitoring_ui":
					for attribute, key, value in [
						("DNSCryptUI", "enabled", tomlBoolean(config.usage.DNSCryptUI.value)),
						(None, "listen_address", tomlString(f"0.0.0.0:{tomlInteger(config.usage.DNSCryptPort.value, 9012)}")),
						("DNSCryptUsername", "username", tomlString(config.usage.DNSCryptUsername.value.strip())),
						("DNSCryptPassword", "password", tomlString(config.usage.DNSCryptPassword.value.strip())),
						("DNSCryptPrivacy", "privacy_level", tomlInteger(config.usage.DNSCryptPrivacy.value, 1)),
					]:
						tmpFound = set()
						replacement = replaceKeyLine(line, key, value, tmpFound)
						if key in tmpFound:
							found.add(f"monitoring_ui.{key}")
							line = replacement
				newLines.append(line)
			insertSectionKey(newLines, "monitoring_ui", "enabled", tomlBoolean(config.usage.DNSCryptUI.value), ["enabled"], found)
			insertSectionKey(newLines, "monitoring_ui", "listen_address", tomlString(f"0.0.0.0:{tomlInteger(config.usage.DNSCryptPort.value, 9012)}"), ["enabled", "listen_address"], found)
			insertSectionKey(newLines, "monitoring_ui", "username", tomlString(config.usage.DNSCryptUsername.value.strip()), ["listen_address", "username"], found)
			insertSectionKey(newLines, "monitoring_ui", "password", tomlString(config.usage.DNSCryptPassword.value.strip()), ["username", "password"], found)
			insertSectionKey(newLines, "monitoring_ui", "privacy_level", tomlInteger(config.usage.DNSCryptPrivacy.value, 1), ["password", "privacy_level"], found)
			tmpPath = f"{tomlPath}.tmp"
			fileWriteLines(tmpPath, newLines)
			if exists(tmpPath):
				rename(tmpPath, tomlPath)

	def keyMoveItemUp(self):
		self.moveItem(-1)

	def keyMoveItemDown(self):
		self.moveItem(1)

	def moveItem(self, direction: int):
		current = self["config"].getCurrent()
		if current in self.dnsServerItems:
			index = self.dnsServerItems.index(current)
			group = self.dnsServerGroups[index]
			servers = self.dnsServersV4 if group == "v4" else self.dnsServersV6
			groupIdx = self.groupIndex(index)
			otherIdx = groupIdx + direction
			if 0 <= otherIdx < len(servers):
				servers[groupIdx], servers[otherIdx] = servers[otherIdx], servers[groupIdx]
				self.createSetup()
