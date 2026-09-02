from __future__ import annotations

from dataclasses import dataclass
from ipaddress import ip_address

from os import rename
from os.path import exists
from re import IGNORECASE, compile

from enigma import eTimer, gRGB

from skin import parseColor
from Components.ActionMap import HelpableActionMap
from Components.config import ConfigIP, ConfigNumber, ConfigPassword, ConfigSelection, ConfigText, ConfigYesNo, NoSave, ReadOnly, config, getConfigListEntry
from Components.Console import Console
from Components.Label import Label
from Components.NetworkManager import Adapter, Connection, Encryption, VpnInfo, WiFiConfig, networkManager, encryptionLabels, wpaCliBin
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
from Tools.Directories import SCOPE_SKINS, fileReadLine, fileReadLines, fileReadXML, fileWriteLines, resolveFilename
from Tools.ServiceAction import ServiceAction

MODULE_NAME = __name__.split(".")[-1]

# Bitmask describing what a screen just changed about an adapter/connection,
# passed to applyAdapterChange() below. Only used here - networkManager.save()
# itself is a plain writer and doesn't need to know any of this. A caller ORs
# together every bit that applies (e.g. general settings changed AND the
# adapter ends up disabled in the same Save); applyAdapterChange() alone
# decides the resulting action and its ordering, so callers never have to
# work out priority between bits themselves.
CHANGE_NONE = 0				# Nothing that needs activating changed.
CHANGE_GENERAL = 1 << 0			# IP/Gateway/DNS/link speed/... changed.
CHANGE_ADAPTER_ENABLED = 1 << 1  # Adapter/connection was just enabled.
CHANGE_ADAPTER_DISABLED = 1 << 2  # Adapter/connection was just disabled.


def ip4Str(addr: list) -> str:
	joined = ".".join(str(x) for x in addr)
	return "" if joined == "0.0.0.0" else joined


def applyAdapterChange(interface: str, change: int, callback):
	def done(*_args):
		Processing.instance.hideProgress()
		callback()

	def doneNotify(*_args):
		networkManager.notifyNetworkPlugins(True, interface=interface)
		done(*_args)

	if change == CHANGE_NONE:
		if callable(callback):
			callback()
		return

	networkManager.notifyNetworkPlugins(False, interface=interface)
	Processing.instance.setDescription(_("Please wait..."))
	Processing.instance.showProgress(endless=True)
	if change & CHANGE_ADAPTER_DISABLED:
		def afterDown(*_args):
			networkManager.save()
			doneNotify(*_args)

		adapter = networkManager.adapters.get(interface)
		if adapter and adapter.isWiFi:
			ServiceAction.wlanDeactivate(interface, afterDown)
		else:
			ServiceAction.ifdown(interface, afterDown)
	elif change & CHANGE_GENERAL:
		networkManager.save()
		networkManager.restartNetwork(interface=interface, callback=done)
	elif change & CHANGE_ADAPTER_ENABLED:
		networkManager.save()
		ServiceAction.ifup(interface, doneNotify)
	else:
		done()


def scanResultToConnection(scanResult: ScanResult, iface: str) -> Connection:
	return Connection(adapter=iface, name=scanResult.ssid, dhcp=True, enabled=True, priority=0, wifi=WiFiConfig(ssid=scanResult.ssid, encryption=scanResult.encryption))


class NetworkOverview(Screen):
	"""Adapters (top list) and Saved Wi-Fi Networks for the selected adapter (bottom list)."""

	OVERVIEW_TEMPLATE_HEADER = 0
	OVERVIEW_TEMPLATE_ROW = 1
	OVERVIEW_COLOR_CONNECTED = gRGB(0x0000CC00).argb()  # Green – Connected.
	OVERVIEW_COLOR_NO_LINK = gRGB(0x00CC0000).argb()   # Red – LAN without link.
	OVERVIEW_COLOR_IDLE = gRGB(0x00808080).argb()  # Gray – Disabled / Not associated / Saved connection.
	OVERVIEW_COLOR_CONNECTED_SELECTED = gRGB(0x0000CC00).argb()  # Green – Connected, row selected.
	OVERVIEW_COLOR_NO_LINK_SELECTED = gRGB(0x00CC0000).argb()   # Red – LAN without link, row selected.
	OVERVIEW_COLOR_IDLE_SELECTED = gRGB(0x00808080).argb()  # Gray – Disabled / Not Associated / Saved connection, row selected.

	skin = """
	<screen name="NetworkOverview" title="Network Overview" position="center,center" size="1070,540" resolution="1280,720">
		<widget source="adapterList" render="Listbox" position="10,10" size="e-20,250">
			<template name="Default" colors="#0000CC00,#00CC0000,#00CCCCCC,#00003300,#00330000,#00333333" fonts="Regular;25,enigma2icons;38,Regular;24,Regular;18,enigma2icons;20" itemHeight="50">
				<rowtemplate>
					<text index="AdapterName" position="0,0" size="240,50" font="0" foregroundColor="gray" padding="5,0" verticalAlignment="center" />
					<text index="StatusText" position="280,0" size="170,50" font="0" foregroundColor="gray" padding="5,0" verticalAlignment="center" />
					<text index="MAC" position="450,0" size="170,50" font="0" foregroundColor="gray" padding="5,0" verticalAlignment="center" />
					<text index="IPAddress" position="620,0" size="150,50" font="0" foregroundColor="gray" padding="5,0" verticalAlignment="center" />
					<text index="Gateway" position="770,0" size="140,50" font="0" foregroundColor="gray" padding="5,0" verticalAlignment="center" />
					<text index="Speed" position="910,0" size="140,50" font="0" foregroundColor="gray" padding="5,0" verticalAlignment="center" />
				</rowtemplate>
				<rowtemplate>
					<text index="AdapterGlyph" position="0,6" size="48,38" font="1" horizontalAlignment="center" padding="5,0" verticalAlignment="center" />
					<text index="AdapterName" position="60,0" size="180,28" font="2" padding="5,0" verticalAlignment="center" />
					<text index="AdapterType" position="60,28" size="180,22" font="3" padding="5,0" verticalAlignment="center" />
					<text index="InternetGlyph" position="240,15" size="40,20" font="4" horizontalAlignment="center" padding="5,0" verticalAlignment="center" />
					<text index="StatusText" position="280,0" size="170,50" font="3" foregroundColor="+StatusColor" foregroundColorSelected="+StatusColorSelected" padding="5,0" verticalAlignment="center" />
					<text index="MAC" position="450,0" size="170,50" font="3" padding="5,0" verticalAlignment="center" />
					<text index="IPAddress" position="620,0" size="150,50" font="3" padding="5,0" verticalAlignment="center" />
					<text index="Gateway" position="770,0" size="140,50" font="3" padding="5,0" verticalAlignment="center" />
					<text index="Speed" position="910,0" size="140,50" font="3" padding="5,0" verticalAlignment="center" />
				</rowtemplate>
			</template>
		</widget>
		<widget source="savedLabel" render="Label" position="10,270" size="e-20,25" foregroundColor="gray" padding="10,0" verticalAlignment="center" widgetBorderColor="gray" widgetBorderWidth="1">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="savedList" render="Listbox" position="10,305" size="e-20,175">
			<template name="Default" colors="#0000CC00,#00CC0000,#00CCCCCC,#00003300,#00330000,#00333333" fonts="Regular;25,Regular;20" itemHeight="35">
				<rowtemplate>
					<text index="SSID" position="0,0" size="280,35" font="0" foregroundColor="gray" padding="5,0" verticalAlignment="center" />
					<text index="StatusText" position="280,0" size="170,35" font="0" foregroundColor="gray" padding="5,0" verticalAlignment="center" />
					<text index="BSSID" position="450,0" size="210,35" font="0" foregroundColor="gray" padding="5,0" verticalAlignment="center" />
					<text index="Frequency" position="660,0" size="120,35" font="0" foregroundColor="gray" padding="5,0" verticalAlignment="center" />
					<text index="Channel" position="780,0" size="120,35" font="0" foregroundColor="gray" padding="5,0" verticalAlignment="center" />
					<text index="Encryption" position="900,0" size="150,35" font="0" foregroundColor="gray" padding="5,0" verticalAlignment="center" />
				</rowtemplate>
				<rowtemplate>
					<text index="SSID" position="0,0" size="280,35" font="1" padding="5,0" verticalAlignment="center" />
					<text index="StatusText" position="280,0" size="170,35" font="1" foregroundColor="+StatusColor" foregroundColorSelected="+StatusColorSelected" padding="5,0" verticalAlignment="center" />
					<text index="BSSID" position="450,0" size="210,35" font="1" padding="5,0" verticalAlignment="center" />
					<text index="Frequency" position="660,0" size="120,35" font="1" padding="5,0" verticalAlignment="center" />
					<text index="Channel" position="780,0" size="120,35" font="1" padding="5,0" verticalAlignment="center" />
					<text index="Encryption" position="900,0" size="150,35" font="1" padding="5,0" verticalAlignment="center" />
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
		def greeHelp():
			return self.helpTextGreen

		def doClose():
			networkManager.onAdaptersChanged.remove(self.refreshAdapters)

		Screen.__init__(self, session, enableHelp=True)
		self.setTitle(_("Network Overview"))
		self["savedLabel"] = StaticText("")
		self["key_red"] = StaticText(_("Close"))
		self["key_green"] = StaticText("")
		self["key_yellow"] = StaticText("")
		self["key_blue"] = StaticText("")
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
			"StatusColor": 7,
			"StatusColorSelected": 8
		}
		self.indexSaved = 9
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
			"green": (self.keyGreen, greeHelp),
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
		self.internetChecked = False
		self.helpTextGreen = ""
		self.onLayoutFinish.append(self.layoutFinished)
		self.onShown.append(self.checkInternet)
		self.onClose.append(doClose)

	def layoutFinished(self):
		self["adapterList"].enableAutoNavigation(False)
		self["adapterList"].setLockFirstRow(True)
		self.markHeaderNotSelectable("adapterList")
		self["savedList"].enableAutoNavigation(False)
		self["savedList"].setLockFirstRow(True)
		self.markHeaderNotSelectable("savedList")
		networkManager.onAdaptersChanged.append(self.refreshAdapters)
		self.buildAdapters()
		self.setListFocus("adapterList")

	def buildAdapters(self):
		rows = self.buildAdapterRows()
		hasRows = bool(rows)
		self["adapterList"].setList(rows)
		if hasRows:
			self["adapterList"].index = 1
		self.buildSaved()
		text = _("Add Wi-Fi") if any(x.isWiFi for x in networkManager.adapters.values()) else ""
		self["key_yellow"].setText(text)
		self["actions"].setEnabledAction("yellow", text != "")

	def buildAdapterRows(self) -> list[tuple]:
		def buildOverviewAdapterRow(adapter: Adapter) -> tuple:
			"""Row for the adapter listbox. Same template for LAN and Wi-Fi. No per-type extra line."""
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
				speed = f"{netInfo.bitrateBps // 1000000} Mbps" if netInfo.bitrateBps else "—"
			else:
				speed = formatNetworkSpeed(netInfo.speed) if netInfo.speed > 0 else "—"
			internet = adapter.adapterEnabled and adapter.hasInternet
			inetGlyph = "\uEA68" if internet else ""  # Glyph is Cloud.
			return (
				self.OVERVIEW_TEMPLATE_ROW,
				"\uE9FE" if adapter.isWiFi else "\uEA5A",                         # AdapterGlyph (Glyphs are Wi-fi and Settings_ethernet).
				adapter.name,                                                     # AdapterName.
				_("Wi-Fi Adapter") if adapter.isWiFi else _("Ethernet Adapter"),  # AdapterType.
				statusText,                                                       # StatusText.
				statusColor,                                                      # StatusColor.
				statusColorSelected,                                              # StatusColorSelected.
				adapter.mac.upper(),                                              # MAC.
				ip4Str(netInfo.ip) or "—",                                        # IPAddress.
				ip4Str(netInfo.gateway) or "—",                                   # Gateway.
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
			inetGlyph = "\uEA69" if vpn.up and vpn.link else ""  # Cloud Locked.
			return (
				self.OVERVIEW_TEMPLATE_ROW,
				"\uE9AF",               # AdapterGlyph (Glyph is Vpn_key).
				vpn.name,               # AdapterName.
				_("VPN"),               # AdapterType.
				statusText,             # StatusText.
				statusColor,            # StatusColor.
				statusColorSelected,    # StatusColorSelected.
				vpn.mac.upper(),        # MAC.
				ip4Str(vpn.ip) or "—",  # IPAddress.
				"—",                    # Gateway.
				"—",                    # Speed.
				inetGlyph,              # InternetGlyph.
				None,                   # -> indexAdapter.
			)

		def buildOverviewAdapterHeaderRow() -> tuple:
			return (
				self.OVERVIEW_TEMPLATE_HEADER,
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

		connected, noLink, idle, connectedSelected, noLinkSelected, idleSelected = self.overviewColors("adapterList")
		rows = [buildOverviewAdapterRow(networkManager.adapters[iface]) for iface in sorted(networkManager.adapters.keys())]
		rows += [buildOverviewVpnRow(networkManager.vpnInterfaces[iface]) for iface in sorted(networkManager.vpnInterfaces.keys())]
		if rows:
			rows.insert(0, buildOverviewAdapterHeaderRow())
		return rows

	def overviewColors(self, sourceName: str) -> tuple:
		defaultColors = (self.OVERVIEW_COLOR_CONNECTED, self.OVERVIEW_COLOR_NO_LINK, self.OVERVIEW_COLOR_IDLE, self.OVERVIEW_COLOR_CONNECTED_SELECTED, self.OVERVIEW_COLOR_NO_LINK_SELECTED, self.OVERVIEW_COLOR_IDLE_SELECTED)
		colors = self[sourceName].additionalTemplateAttributes.get("colors")
		if not colors:
			return defaultColors
		parts = [parseColor(part.strip()).argb() for part in colors.split(",")]
		if len(parts) == 3:
			parts += parts
		if len(parts) != 6:
			print(f"[{MODULE_NAME}] Error: Template 'colors' must have 3 or 6 entries (connected, noLink, idle[, connectedSelected, noLinkSelected, idleSelectedected]), got {len(parts)}!")
			return defaultColors
		return tuple(parts)

	def buildSaved(self, preserveSelection: bool = False):
		adapter = self.currentAdapter()
		connections, rows = self.buildSavedRows(adapter)
		if adapter is None or not adapter.isWiFi:
			self["savedList"].setList([])
			self["savedLabel"].setText("")
		else:
			if preserveSelection and len(rows) == self["savedList"].count():
				oldRows = self["savedList"].getList()
				for index, (oldRow, newRow) in enumerate(zip(oldRows, rows)):
					if oldRow != newRow:
						self["savedList"].updateEntry(index, newRow)
			else:
				hasRows = bool(rows)
				self["savedList"].setList(rows)
				if hasRows:
					self["savedList"].index = 1
			self["savedLabel"].setText(f"{_("Saved Wi-Fi Networks")} · {adapter.name} · {len(connections)}")
		if self.currentList == "savedList" and not self["savedList"].count():
			self.setListFocus("adapterList")
		else:
			self.updateButtons()

	def buildSavedRows(self, adapter: Adapter | None) -> tuple[list[Connection], list[tuple]]:
		def buildOverviewSavedRow(conn: Connection, adapter: Adapter) -> tuple:
			"""Row for the saved Wi-Fi listbox. BSSID/frequency/channel are only known
			while this connection is the one currently associated in wpa_supplicant.conf.
			Doesn't persist for saved networks that aren't connected right now."""
			ssid = conn.wifi.ssid
			netInfo = adapter.netInfo
			isLive = netInfo.link and netInfo.ssid == ssid
			if isLive:
				statusText, statusColor, statusColorSelected = _("Connected"), connected, connectedSelected
			elif conn.enabled:
				statusText, statusColor, statusColorSelected = _("Not Connected"), idle, idleSelected
			else:
				statusText, statusColor, statusColorSelected = _("Disabled"), idle, idleSelected
			return (
				self.OVERVIEW_TEMPLATE_ROW,
				ssid,                                                                        # SSID.
				netInfo.bssid.upper() if isLive and netInfo.bssid else "—",                  # BSSID.
				f"{netInfo.freqMhz / 1000:.2f} GHz" if isLive and netInfo.freqMhz else "—",  # Frequency.
				str(netInfo.channel) if isLive and netInfo.channel else "—",                 # Channel.
				encryptionLabels.get(conn.wifi.encryption, lambda: "")(),                    # Encryption.
				statusText,                                                                  # StatusText.
				statusColor,                                                                 # StatusColor.
				statusColorSelected,                                                         # StatusColorSelected.
				conn,                                                                        # -> indexSaved.
			)

		def buildOverviewSavedHeaderRow() -> tuple:
			"""First row of the saved Wi-Fi listbox, rendered via <rowtemplate> #0.
			Column titles are not selectable (see isOverviewRowSelectable). All
			texts are a static gray in the skin.  Unlike the data row's StatusText
			this one doesn't need a real StatusColor."""
			return (
				self.OVERVIEW_TEMPLATE_HEADER,
				_("SSID"),        # SSID.
				_("BSSID"),       # BSSID.
				_("Frequency"),   # Frequency.
				_("Channel"),     # Channel.
				_("Encryption"),  # Encryption.
				_("Status"),      # StatusText.
				None,             # StatusColor.
				None,             # StatusColorSelected.
				None,             # -> indexSaved.
			)

		connected, noLink, idle, connectedSelected, noLinkSelected, idleSelected = self.overviewColors("savedList")
		if adapter is None or not adapter.isWiFi:
			return [], []
		connections = self.overviewWiFiConnections(adapter)
		rows = [buildOverviewSavedRow(x, adapter) for x in connections]
		if rows:
			rows.insert(0, buildOverviewSavedHeaderRow())
		return connections, rows

	def setListFocus(self, listName: str):
		self.currentList = listName
		self["adapterList"].selectionEnabled(listName == "adapterList")
		self["savedList"].selectionEnabled(listName == "savedList")
		self.updateButtons()

	def updateButtons(self):
		infoText = ""
		greenText = ""
		blueText = ""
		adapter = self.currentAdapter()
		if adapter:
			if self.currentList == "adapterList":
				infoText = _("INFO")
				greenText = _("Deactivate") if adapter.adapterEnabled else _("Activate")
				self.helpTextGreen = _("Deactivate network adapter") if adapter.adapterEnabled else _("Activate network adapter")
			else:
				conn = self.currentSaved()
				if conn:
					greenText = _("Disable") if conn.enabled else _("Enable")
					self.helpTextGreen = _("Disable saved Wi-Fi network") if conn.enabled else _("Enable saved Wi-Fi network")
					if conn.enabled and not self.isConnectionLive(conn, adapter):
						blueText = _("Connect")
		self["key_info"].setText(infoText)
		self["key_green"].setText(greenText)
		self["key_blue"].setText(blueText)
		self["actions"].setEnabledAction("info", infoText != "")
		self["actions"].setEnabledAction("green", greenText != "")
		self["actions"].setEnabledAction("blue", blueText != "")
		self["actions"].setEnabledAction("first", self.currentList == "savedList")
		self["actions"].setEnabledAction("left", self.currentList == "savedList")
		self["actions"].setEnabledAction("right", self.currentList == "adapterList" and self["savedList"].count())
		self["actions"].setEnabledAction("last", self.currentList == "adapterList" and self["savedList"].count())

	def isConnectionLive(self, conn: Connection, adapter: Adapter) -> bool:
		"""True if saved entry is the Wi-Fi connection the adapter is currently
		associated with, same check as buildOverviewConnectionRow()'s isLive."""
		return adapter.netInfo.link and adapter.netInfo.ssid == conn.wifi.ssid

	def currentAdapter(self) -> Adapter | None:
		entry = self["adapterList"].getCurrent()
		return entry[self.indexAdapter] if entry else None

	def currentSaved(self) -> Connection | None:
		entry = None
		if self.currentList == "savedList":
			entry = self["savedList"].getCurrent()
		return entry[self.indexSaved] if entry else None

	def checkInternet(self):
		def checkInternetCallback():
			self.internetChecked = True
			self.refreshAdapters()

		if not self.internetChecked:
			networkManager.checkConnectionInternet(callback=checkInternetCallback)

	def refreshAdapters(self):
		if "adapterList" in self:
			oldGateways = {x[self.indexAdapter].name: x[self.indexAdapter].netInfo.gateway for x in self["adapterList"].getList() if x[self.indexAdapter] is not None}
			newGateways = {name: adapter.netInfo.gateway for name, adapter in networkManager.adapters.items()}
			if oldGateways != newGateways:
				self.internetChecked = False
				self.checkInternet()
				return
			oldRows = self["adapterList"].getList()
			newRows = self.buildAdapterRows()
			if len(oldRows) != len(newRows):
				adapterIndex = self["adapterList"].getCurrentIndex() if self["adapterList"].count() else -1
				savedIndex = self["savedList"].getCurrentIndex() if self["savedList"].count() else -1
				self.buildAdapters()
				try:
					if adapterIndex != -1:
						self["adapterList"].setCurrentIndex(adapterIndex)
				except Exception:
					pass
				if self.currentList == "savedList":
					try:
						if savedIndex != -1:
							self["savedList"].setCurrentIndex(savedIndex)
					except Exception:
						pass
			else:
				for index, (oldRow, newRow) in enumerate(zip(oldRows, newRows)):
					if oldRow != newRow:
						self["adapterList"].updateEntry(index, newRow)
				self.buildSaved(preserveSelection=True)

	def keyOK(self):
		adapter = self.currentAdapter()
		if adapter is None:
			return
		conn = self.currentSaved()
		if conn is None:
			self.openAdapterSetup(adapter)
		else:
			self.openSetup(conn, adapter)

	def keyCloseRecursive(self):
		self.close(True)

	def keyMenu(self):
		def showContextMenu(conn: Connection | None, adapter: Adapter):
			if conn is None:
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
					(_("Disable Network") if conn.enabled else _("Enable network"), "toggleSaved"),
				]
				menu.append((_("Delete Network"), "delete"))
				title = _("Saved Wi-Fi Network '%s' Context Menu") % self.connLabel(conn, adapter)
			if adapter.isWiFi:
				menu.append((_("Scan Wi-Fi Networks"), "scan"))
				menu.append((_("Add Wi-Fi Manually"), "addManual"))
			self.session.openWithCallback(lambda choice: self.contextCb(choice, conn, adapter), ChoiceBox, windowTitle=title, choiceList=menu)

		adapter = self.currentAdapter()
		if adapter:
			showContextMenu(self.currentSaved(), adapter)

	def keyInfo(self):
		if self.currentList == "adapterList":
			adapter = self.currentAdapter()
			if adapter:
				self.session.open(NetworkInformation, adapter, self.currentSaved())

	def keyGreen(self):
		adapter = self.currentAdapter()
		if adapter:
			if self.currentList == "adapterList":
				self.toggleAdapter(adapter)
			else:
				conn = self.currentSaved()
				if conn:
					self.toggleSaved(conn, adapter)

	def keyYellow(self):
		if networkManager.adapters:
			wifiAdapters = [x for x in networkManager.adapters.values() if x.isWiFi]
			if wifiAdapters:
				adapter = self.currentAdapter()
				preselected = adapter if adapter is not None and adapter.isWiFi else None
				NetworkWiFiAddFlow.start(self.session, adapter=preselected, callback=lambda *_: self.buildAdapters())

	def keyBlue(self):
		conn = self.currentSaved()
		adapter = self.currentAdapter()
		if adapter and conn and conn.enabled and not self.isConnectionLive(conn, adapter):
			self.session.openWithCallback(lambda *_: self.refreshAdapters(), NetworkWiFiActivator, conn, adapter)

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

	def markHeaderNotSelectable(self, sourceName: str):
		def isOverviewRowSelectable(kind, *_):
			return kind != self.OVERVIEW_TEMPLATE_HEADER

		self[sourceName].master.content.setSelectableFunc(isOverviewRowSelectable)

	def overviewWiFiConnections(self, adapter: Adapter) -> list[Connection]:
		return [conn for conn in networkManager.getConnections(adapter.name) if conn.wifi and conn.wifi.ssid]

	def connLabel(self, conn: Connection, adapter: Adapter) -> str:
		encShort = {
			Encryption.NONE: "open",
			Encryption.WEP: "WEP",
			Encryption.WPA: "WPA",
			Encryption.WPA2: "WPA2",
			Encryption.WPA3: "WPA3"
		}
		if conn.isWiFi and conn.wifi and conn.wifi.ssid:
			result = f"{conn.adapter}  │  {conn.wifi.ssid}  [{encShort.get(conn.wifi.encryption, conn.wifi.encryption)}]"
		else:
			mode = "DHCP" if conn.dhcp else conn.ipStr()
			result = f"{conn.adapter}  │  {mode}"
		return result

	def contextCb(self, choice, conn: Connection | None, adapter: Adapter):
		def openWiFiManual(adapter: Adapter):
			conn = Connection(adapter=adapter.name, name=_("New Wi-Fi"), dhcp=True, enabled=False, wifi=WiFiConfig())
			self.session.openWithCallback(self.setupClosed, NetworkWiFi, conn, adapter)

		def confirmDelete(conn: Connection, adapter: Adapter):
			def doDelete(confirmed: bool, conn: Connection, adapter: Adapter):
				if confirmed:
					if conn.isWiFi and conn.wifi:
						networkManager.removeConnection(adapter.name, conn.wifi.ssid)
					else:
						networkManager.connections[adapter.name] = [x for x in networkManager.getConnections(adapter.name) if x is not conn]
					networkManager.save()
					if conn.isWiFi:
						self.buildAdapters()
					else:
						applyAdapterChange(adapter.name, CHANGE_GENERAL, self.buildAdapters)

			self.session.openWithCallback(lambda confirmed: doDelete(confirmed, conn, adapter), MessageBox, _("Confirm the deletion of '%s'?") % self.connLabel(conn, adapter), type=MessageBox.TYPE_YESNO)

		def restartAdapter(adapter: Adapter):
			def done():
				Processing.instance.hideProgress()
				self.buildAdapters()

			Processing.instance.setDescription(_("Restarting adapter..."))
			Processing.instance.showProgress(endless=True)
			networkManager.restartNetwork(interface=adapter.name, callback=done)

		def restartNetwork():
			def done():
				Processing.instance.hideProgress()
				self.buildAdapters()

			Processing.instance.setDescription(_("Restarting saved Wi-Fi network..."))
			Processing.instance.showProgress(endless=True)
			networkManager.restartNetwork(interface="all", callback=done)

		def openWiFiScan(iface: str):
			def wifiScanDone(result: ScanResult | None, adapter: Adapter):
				if result is True:
					self.keyCloseRecursive()
				elif result:
					self.session.openWithCallback(self.setupClosed, NetworkWiFi, scanResultToConnection(result, adapter.name), adapter)

			adapter = networkManager.getAdapter(iface)
			if adapter is not None and adapter.isWiFi:
				self.session.openWithCallback(lambda result: wifiScanDone(result, adapter), NetworkWiFiScan, adapter)

		if choice:
			match choice[1]:
				case "adapterSetup":
					self.openAdapterSetup(adapter)
				case "addManual":
					openWiFiManual(adapter)
				case "delete":
					confirmDelete(conn, adapter)
				case "restartAdapter":
					restartAdapter(adapter)
				case "restartNetwork":
					restartNetwork()
				case "scan":
					openWiFiScan(adapter.name)
				case "setup":
					self.openSetup(conn, adapter)
				case "test":
					self.session.open(NetworkTest, adapter.name)
				case "toggleAdapter":
					self.toggleAdapter(adapter)
				case "toggleSaved":
					self.toggleSaved(conn, adapter)

	def openAdapterSetup(self, adapter: Adapter):
		self.session.openWithCallback(self.setupClosed, NetworkAdapterSetup, adapter)

	def openSetup(self, conn: Connection, adapter: Adapter):
		self.session.openWithCallback(self.setupClosed, NetworkWiFi, conn, adapter)

	def setupClosed(self, *result):
		if len(result) == 1 and isinstance(result[0], tuple):
			recursive, saved = result[0][0], result[0][1]
		else:
			recursive = bool(result[0]) if result else False
			saved = False
		if saved:
			self.buildAdapters()
		elif recursive:
			self.keyCloseRecursive()

	def toggleAdapter(self, adapter: Adapter):
		def done():
			self.refreshAdapters()
			self.session.showInfo(_("Network adapter enabled.") if adapter.adapterEnabled else _("Network adapter disabled."))

		adapter.adapterEnabled = not adapter.adapterEnabled
		change = CHANGE_ADAPTER_ENABLED if adapter.adapterEnabled else CHANGE_ADAPTER_DISABLED
		applyAdapterChange(adapter.name, change, done)

	def toggleSaved(self, conn: Connection, adapter: Adapter):
		def done(*_args):
			self.refreshAdapters()
			self.session.showInfo(_("Saved Wi-Fi network connection enabled.") if conn.enabled else _("Saved Wi-Fi network connection disabled."))

		if conn.enabled:
			wasLive = self.isConnectionLive(conn, adapter)
			conn.enabled = False
			networkManager.save()
			if wasLive and conn.wifi and conn.wifi.wpaId is not None:
				Console().ePopen((wpaCliBin, wpaCliBin, "-i", adapter.name, "disable_network", str(conn.wifi.wpaId)), callback=done)
			else:
				done()
		else:
			conn.enabled = True
			networkManager.save()
			done()

	def activateWiFiConnection(self, conn: Connection, adapter: Adapter):
		for connection in networkManager.getConnections(adapter.name):
			connection.enabled = (connection is conn)
		adapter.adapterEnabled = True
		networkManager.save()
		self.refreshAdapters()
		self.session.openWithCallback(lambda *_: self.refreshAdapters(), NetworkWiFiActivator, conn, adapter)


class NetworkAdapterSetup(Setup):
	def __init__(self, session, adapter: Adapter):
		self.adapter = adapter
		self.conn = networkManager.getBaseConnection(adapter.name)
		self.buildConfigObjects()
		self.hasWakeOnLan = adapter.name == "eth0" and BoxInfo.getItem("wol") and BoxInfo.getItem("WakeOnLAN")
		Setup.__init__(self, session=session, setup="NetworkAdapter")
		self.setTitle(_("Network Adapter '%s' Settings") % adapter.name)
		self["key_info"] = StaticText(_("INFO"))
		self["infoActions"] = HelpableActionMap(self, ["InfoActions"], {
			"info": (self.keyShowInfo, _("Show network adapter connection information"))
		}, prio=0, description=_("Network Overview Actions"))

	def keyShowInfo(self):
		self.session.open(NetworkInformation, self.adapter, self.conn)

	def buildConfigObjects(self):
		adapter = self.adapter
		conn = self.conn
		self.cfgEnabled = NoSave(ConfigYesNo(default=adapter.adapterEnabled))
		self.cfgIpMode = NoSave(ConfigSelection(
			default=conn.ipMode,
			choices=[
				(0, _("IPv4 only")),
				(1, _("IPv6 only")),
				(2, _("IPv4 and IPv6")),
			]
		))
		self.cfgDhcp = NoSave(ConfigYesNo(default=conn.dhcp))
		self.cfgIp = NoSave(ConfigIP(default=conn.ip))
		self.cfgNetmask = NoSave(ConfigIP(default=conn.netmask))
		self.cfgGateway = NoSave(ConfigIP(default=conn.gateway))
		currentMetric = adapter.metric
		self.hasMetric = currentMetric is not None and len(networkManager.adapters) > 1
		self.cfgMetric = NoSave(ConfigSelection(choices=networkManager.ROUTE_METRIC_CHOICES, default=currentMetric if currentMetric is not None else (600 if adapter.isWiFi else 100)))
		hasOwn = bool(conn.dnsServers)
		self.cfgDnsOverride = NoSave(ConfigYesNo(default=hasOwn))
		dnsV4 = [x for x in conn.dnsServers if isinstance(x, list)]
		dnsV6 = [x for x in conn.dnsServers if isinstance(x, str)]
		self.cfgDns1v4 = NoSave(ConfigIP(default=dnsV4[0] if len(dnsV4) > 0 else [0, 0, 0, 0]))
		self.cfgDns2v4 = NoSave(ConfigIP(default=dnsV4[1] if len(dnsV4) > 1 else [0, 0, 0, 0]))
		self.cfgDns1v6 = NoSave(ConfigText(default=dnsV6[0] if len(dnsV6) > 0 else "", fixed_size=False))
		self.cfgDns2v6 = NoSave(ConfigText(default=dnsV6[1] if len(dnsV6) > 1 else "", fixed_size=False))
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
		self.cfgWakeOnWiFi = NoSave(ConfigYesNo(default=conn.wakeOnWiFi and adapter.adapterEnabled))
		self.cfgWowOnly = NoSave(ConfigYesNo(default=conn.wakeOnWiFi and not adapter.adapterEnabled))

	def keySave(self):
		adapter = self.adapter
		conn = self.conn
		wasEnabled = adapter.adapterEnabled
		wasGeneral = (conn.dhcp, conn.ipMode, list(conn.ip), list(conn.netmask), list(conn.gateway), list(conn.dnsServers))
		wasLinkSpeed = networkManager.getLinkSpeed(adapter.name)
		wasMetric = adapter.metric if self.hasMetric else None
		adapter.adapterEnabled = self.cfgEnabled.value
		conn.dhcp = self.cfgDhcp.value
		conn.ipMode = self.cfgIpMode.value
		if not conn.dhcp:
			conn.ip = list(self.cfgIp.value)
			conn.netmask = list(self.cfgNetmask.value)
			conn.gateway = list(self.cfgGateway.value)
		if not self.cfgDnsOverride.value:
			conn.dnsServers = []
		else:
			servers = []
			for cfgV4 in (self.cfgDns1v4, self.cfgDns2v4):
				ipValue = list(cfgV4.value)
				if ipValue != [0, 0, 0, 0]:
					servers.append(ipValue)
			for cfgV6 in (self.cfgDns1v6, self.cfgDns2v6):
				textValue = cfgV6.value.strip()
				if textValue:
					servers.append(textValue)
			conn.dnsServers = servers
		# Apply Wake-on-WiFi (Broadcom).
		if adapter.isWiFi and adapter.canWakeOnWiFi:
			conn.wakeOnWiFi = self.cfgWakeOnWiFi.value if adapter.adapterEnabled else self.cfgWowOnly.value
			cmds = networkManager.setWakeOnWiFiCommands(adapter.name, conn.wakeOnWiFi)
			if cmds:
				Console().eBatch(cmds, lambda result: None, debug=False)
		# Apply forced link speed (LAN adapters only).
		if not adapter.isWiFi:
			networkManager.setLinkSpeed(adapter.name, self.cfgLinkSpeed.value)
		if self.hasMetric and self.cfgMetric.value != wasMetric:
			if adapter.isWiFi:
				networkManager.setRouteMetrics(wlanMetric=self.cfgMetric.value)
			else:
				networkManager.setRouteMetrics(lanMetric=self.cfgMetric.value)
		nowGeneral = (conn.dhcp, conn.ipMode, list(conn.ip), list(conn.netmask), list(conn.gateway), list(conn.dnsServers))
		change = CHANGE_NONE
		if nowGeneral != wasGeneral or self.cfgLinkSpeed.value != wasLinkSpeed:
			change |= CHANGE_GENERAL
		if adapter.adapterEnabled != wasEnabled:
			change |= CHANGE_ADAPTER_ENABLED if adapter.adapterEnabled else CHANGE_ADAPTER_DISABLED
		applyAdapterChange(adapter.name, change, lambda: self.close((False, True)))

		if self.hasWakeOnLan:
			config.network.wol.save()


class NetworkWiFi(Setup):
	"""Setup screen for one Wi-Fi profile (SSID)."""

	ENCRYPTION_CHOICES = [
		(Encryption.NONE, _("None")),
		(Encryption.WEP, "WEP"),
		(Encryption.WPA, "WPA"),
		(Encryption.WPA2, "WPA2"),
	]

	def __init__(self, session, conn: Connection, adapter: Adapter):
		self.conn = conn
		self.adapter = adapter
		self.buildConfigObjects()
		Setup.__init__(self, session=session, setup="NetworkWiFi")
		self.setTitle(_("Saved Wi-Fi Network '%s' Settings") % conn.adapter)
		self["key_info"] = StaticText(_("INFO"))
		self["infoActions"] = HelpableActionMap(self, ["InfoActions"], {
			"info": (self.keyShowInfo, _("Show network adapter connection information"))
		}, prio=0, description=_("Network Overview Actions"))

	def keyShowInfo(self):
		self.session.open(NetworkInformation, self.adapter, self.conn)

	def buildConfigObjects(self):
		def rankLabel(rank, total):
			if rank == 1 and total > 1:
				return _("1. (Highest)")
			if rank == total and total > 1:
				return _("%s. (Lowest)") % rank
			return f"{rank}."
		conn = self.conn
		adapter = self.adapter
		self.cfgEnabled = NoSave(ConfigYesNo(default=conn.enabled))
		wifiConnections = [x for x in networkManager.getConnections(adapter.name) if x.isWiFi and x.wifi and x.wifi.ssid]
		if not any(x is conn for x in wifiConnections):
			wifiConnections = wifiConnections + [conn]
		self.hasMultiplePriorities = len(wifiConnections) > 1
		if self.hasMultiplePriorities:
			self.wifiConnsSorted = sorted(wifiConnections, key=lambda wifiConn: wifiConn.priority, reverse=True)
			currentRank = next((idx + 1 for idx, x in enumerate(self.wifiConnsSorted) if x is conn), 1)
			rankChoices = [(x + 1, rankLabel(x + 1, len(wifiConnections))) for x in range(len(wifiConnections))]
			self.cfgPriority = NoSave(ConfigSelection(choices=rankChoices, default=currentRank))
		else:
			self.wifiConnsSorted = []
			self.cfgPriority = NoSave(ConfigNumber(default=conn.priority))
		wifi = conn.wifi
		self.cfgSsid = NoSave(ConfigText(default=wifi.ssid, fixed_size=False))
		self.cfgHidden = NoSave(ConfigYesNo(default=wifi.hidden))
		self.cfgEncryption = NoSave(ConfigSelection(choices=self.ENCRYPTION_CHOICES, default=wifi.encryption))
		self.cfgKey = NoSave(ConfigPassword(default=wifi.key, fixed_size=False))

	def keySave(self):
		conn = self.conn
		adapter = self.adapter
		conn.enabled = self.cfgEnabled.value
		if self.hasMultiplePriorities:
			chosenRank = self.cfgPriority.value
			others = [x for x in self.wifiConnsSorted if x is not conn]
			newOrder = others[:chosenRank - 1] + [conn] + others[chosenRank - 1:]
			for idx, wifiConnection in enumerate(newOrder):
				wifiConnection.priority = (len(newOrder) - idx) * 10
		else:
			conn.priority = int(self.cfgPriority.value)
		wifi = conn.wifi
		wifi.ssid = self.cfgSsid.value.strip()
		wifi.hidden = self.cfgHidden.value
		wifi.encryption = self.cfgEncryption.value
		if wifi.encryption != Encryption.NONE:
			wifi.key = self.cfgKey.value
		conns = networkManager.getConnections(adapter.name)
		if not any(x is conn for x in conns):
			conns.append(conn)
		wasEnabled = adapter.adapterEnabled
		if conn.enabled:
			adapter.adapterEnabled = True
		networkManager.saveWpaSupplicant(adapter.name)
		if not wasEnabled and adapter.adapterEnabled:
			networkManager.save()
		if conn.enabled:
			self.session.openWithCallback(self.wifiConnectionVerified, NetworkWiFiActivator, conn, adapter)
		else:
			self.close((False, True))

	def wifiConnectionVerified(self, ip=""):
		if ip:
			self.close((False, True, ip))
		else:
			self.session.openWithCallback(self.wifiRetryChoice, MessageBox, _("Could not verify the saved Wi-Fi network.\n\nDo you want to change the settings again?"), type=MessageBox.TYPE_YESNO)

	def wifiRetryChoice(self, retry):
		if not retry:
			self.close((False, True, ""))


class NetworkInformation(InformationNetwork):
	def __init__(self, session, adapter, conn):
		InformationNetwork.__init__(self, session)
		self.adapter = adapter
		self.conn = conn

	def displayInformation(self):
		InformationNetwork.displayInformation(self, selectedAdapter=self.adapter)


@dataclass
class ScanResult:
	ssid: str = ""
	bssid: str = ""
	frequency: str = ""
	channel: int = 0
	signalDbm: int = -100
	signalPct: int = 0
	encryption: Encryption = Encryption.NONE
	encDetails: str = ""

	@property
	def signalBars(self) -> int:
		if self.signalPct >= 80:
			result = 4
		elif self.signalPct >= 60:
			result = 3
		elif self.signalPct >= 35:
			result = 2
		elif self.signalPct >= 10:
			result = 1
		else:
			result = 0
		return result

	@property
	def encLabel(self) -> str:
		return {
			Encryption.NONE: _("None"),
			Encryption.WEP: "WEP",
			Encryption.WPA: "WPA",
			Encryption.WPA2: "WPA2",
			Encryption.WPA3: "WPA3",
		}.get(self.encryption, self.encryption.upper())


class NetworkWiFiScan(Screen):
	"""Runs iwlist scan and shows results sorted by signal strength."""

	skin = """
	<screen name="NetworkWiFiScan" title="Wi-Fi Scan" position="center,center" size="940,455" resolution="1280,720">
		<widget source="list" render="Listbox" position="10,10" size="e-20,e-105">
			<template name="Default" fonts="Regular;22,Regular;20,enigma2icons;20" itemHeight="35">
				<mode name="default">
					<panel position="0,0" size="e,e" layout="horizontal">
						<text index="Name" position="left" size="450,35" flags="scroll" font="0" padding="5,0" verticalAlignment="center" />
						<text index="Glyph" position="left" size="30,35" font="2" horizontalAlignment="center" padding="5,0" verticalAlignment="center" />
						<text index="Percentage" position="left" size="60,35" font="1" horizontalAlignment="right" padding="5,0" verticalAlignment="center" />
						<text index="dBm" position="left" size="90,35" font="1" horizontalAlignment="right" padding="5,0" verticalAlignment="center" />
						<text index="Encryption" position="left" size="100,35" font="1" horizontalAlignment="center" padding="5,0" verticalAlignment="center" />
						<text index="Channel" position="left" size="80,35" font="1" horizontalAlignment="center" padding="5,0" verticalAlignment="center" />
						<text index="Frequency" position="right" size="110,35" font="1" horizontalAlignment="right" padding="5,0" verticalAlignment="center" />
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

	STRENGTH_GLYPHS = ["", "\uEA66", "\uEA67", "\uEA64", "\uEA65"]

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
		self["actions"] = HelpableActionMap(self, ["OkCancelActions", "ColorActions"], {
			"ok": (self.keySelect, _("Configure the selected Wi-Fi network")),
			"cancel": (self.keyClose, _("Close the screen")),
			"close": (self.closeRecursive, _("Close the screen and exit all menus")),
			"red": (self.keyClose, _("Close the screen")),
			"green": (self.keySelect, _("Configure the selected Wi-Fi network")),
			"yellow": (self.keyStartScan, _("Rescan for available Wi-Fi networks"))
		}, prio=0, description=_("Wi-Fi Scan Actions"))
		self.console = Console()
		self.scanning = False
		self.accessPoints: dict[str, ScanResult] = {}
		self.onLayoutFinish.append(self.keyStartScan)

	def keySelect(self):
		current = self["list"].getCurrent()
		if current:
			self.close(current[-1])

	def keyClose(self):
		if self.console:
			self.console.killAll()
		self.close(None)

	def closeRecursive(self):
		if self.console:
			self.console.killAll()
		self.close(True)

	def keyStartScan(self):
		def finishScan(results, parser):
			self.scanning = False
			if isinstance(results, bytes):
				results = results.decode("UTF-8", errors="replace")
			for accessPoint in parser(results or ""):
				self.accessPoints[accessPoint.bssid] = accessPoint
			if self.accessPoints:
				accessPointList = []
				for accessPoint in sorted(self.accessPoints.values(), key=lambda ap: -ap.signalPct):
					accessPointList.append((
						f"{accessPoint.ssid}  ({accessPoint.bssid})",                # Name.
						accessPoint.ssid,                                            # SSID.
						accessPoint.bssid,                                           # BSSID.
						self.STRENGTH_GLYPHS[min(accessPoint.signalBars, 4)],        # Glyph.
						f"{accessPoint.signalPct}%  ({accessPoint.signalDbm} dBm)",  # Strength.
						f"{accessPoint.signalPct}%",                                 # Percent.
						f"{accessPoint.signalDbm} dBm",                              # dBM.
						accessPoint.encLabel,                                        # Encryption.
						f"Ch-{accessPoint.channel}  ({accessPoint.frequency})",      # ChannelFrequency.
						f"Ch-{accessPoint.channel}",                                 # Channel.
						accessPoint.frequency,                                       # Frequency.
						accessPoint                                                  # AccessPoint data record.
					))
				self["list"].setList(accessPointList)
				count = len(self.accessPoints)
				self["description"].setText(ngettext("%d network found.", "%d networks found.", count) % count)
			else:
				self["list"].setList([])
				self["description"].setText(_("No networks found."))

		def scanViaIwlist(results=None, retVal=0, extraArgs=None):
			self.console.ePopen(("/sbin/iwlist", "/sbin/iwlist", self.adapter, "scanning"), callback=lambda r, rv, ea=None: finishScan(r, self.parseIwlist))

		def scanViaWpaCli():
			def scanResultsCallback(results, retVal, extraArgs=None):
				finishScan(results, self.parseWpaCliScanResults)

			def triggerScanCallback(results=None, retVal=0, extraArgs=None):
				self.scanTimer = eTimer()
				self.scanTimer.callback.append(lambda: self.console.ePopen((wpaCliBin, wpaCliBin, "-i", self.adapter, "scan_results"), callback=scanResultsCallback))
				self.scanTimer.start(3000, True)

			self.console.ePopen((wpaCliBin, wpaCliBin, "-i", self.adapter, "scan"), callback=triggerScanCallback)

		def ifUpCallback(results=None, retVal=0, extraArgs=None):
			if networkManager.wpaSupplicantRunning(self.adapter):
				scanViaWpaCli()
			elif self.adapterObj.isBroadcomWl:
				self.console.ePopen(("/usr/bin/wl", "/usr/bin/wl", "up"), callback=scanViaIwlist)
			else:
				scanViaIwlist()

		if not self.scanning:
			self.scanning = True
			self["description"].setText(_("Scanning..."))
			if self.adapterObj.netInfo.up:
				ifUpCallback()
			else:
				self.console.ePopen(("/sbin/ifconfig", "/sbin/ifconfig", self.adapter, "up"), callback=ifUpCallback)

	def parseIwlist(self, raw: str) -> list[ScanResult]:
		results: list[ScanResult] = []
		current: ScanResult | None = None
		reCell = compile(r"Cell \d+ - Address:\s*([0-9A-Fa-f:]{17})")
		reSsid = compile(r"ESSID:\"(.*?)\"")
		reFreq = compile(r"Frequency:([\d.]+ \w+Hz).*?Channel:?\s*(\d+)?")
		reQuality = compile(r"Quality=(\d+)/(\d+)\s+Signal level=(-?\d+) dBm")
		reEncOn = compile(r"Encryption key:on")
		reEncOff = compile(r"Encryption key:off")
		reIeWpa1 = compile(r"IE:.*WPA Version 1", IGNORECASE)
		reIeWpa2 = compile(r"IE:.*WPA2|IE:.*RSN", IGNORECASE)
		for line in raw.splitlines():
			line = line.strip()
			match = reCell.search(line)
			if match:
				current = ScanResult(bssid=match.group(1))
				results.append(current)
				continue
			if current is None:
				continue
			match = reSsid.search(line)
			if match:
				current.ssid = match.group(1)
			match = reFreq.search(line)
			if match:
				current.frequency = match.group(1)
				if match.group(2):
					current.channel = int(match.group(2))
			match = reQuality.search(line)
			if match:
				qVal, qMax = int(match.group(1)), int(match.group(2))
				current.signalPct = int(qVal * 100 / qMax) if qMax else 0
				current.signalDbm = int(match.group(3))
			if reIeWpa2.search(line):
				current.encryption = Encryption.WPA2
				current.encDetails = line
			elif reIeWpa1.search(line):
				if current.encryption == Encryption.NONE:
					current.encryption = Encryption.WPA
					current.encDetails = line
			elif reEncOn.search(line):
				if current.encryption == Encryption.NONE:
					current.encryption = Encryption.WEP
			elif reEncOff.search(line):
				current.encryption = Encryption.NONE
		return sorted((x for x in results if x.ssid), key=lambda x: -x.signalPct)

	@staticmethod
	def channelFromFreq(freqMhz: int) -> int:
		if freqMhz == 2484:
			return 14
		if 2412 <= freqMhz <= 2472:
			return (freqMhz - 2407) // 5
		if 5000 <= freqMhz <= 5900:
			return (freqMhz - 5000) // 5
		return 0

	def parseWpaCliScanResults(self, raw: str) -> list[ScanResult]:
		results: list[ScanResult] = []
		reBssid = compile(r"^[0-9A-Fa-f]{2}(:[0-9A-Fa-f]{2}){5}$")
		for line in raw.splitlines():
			fields = line.strip().split("\t")
			if len(fields) < 5 or not reBssid.match(fields[0]):
				continue
			bssid, freqStr, signalStr, flags, ssid = fields[0], fields[1], fields[2], fields[3], fields[4]
			if not ssid:
				continue
			try:
				freqMhz = int(freqStr)
				signalDbm = int(signalStr)
			except ValueError:
				continue
			if "WPA2" in flags or "RSN" in flags:
				encryption = Encryption.WPA2
			elif "WPA" in flags:
				encryption = Encryption.WPA
			elif "WEP" in flags:
				encryption = Encryption.WEP
			else:
				encryption = Encryption.NONE
			results.append(ScanResult(
				ssid=ssid,
				bssid=bssid,
				frequency=f"{freqMhz / 1000:.3f} GHz",
				channel=self.channelFromFreq(freqMhz),
				signalDbm=signalDbm,
				signalPct=max(0, min(100, 2 * (signalDbm + 100))),
				encryption=encryption,
				encDetails=flags,
			))
		return sorted(results, key=lambda x: -x.signalPct)


class NetworkWiFiActivator(Screen):
	"""Runs ifup + wpa_supplicant (scoped to this one adapter, via
	wlanactivator script) and polls for an IP address, so the user
	gets feedback if the connection attempt fails or times out."""

	skin = """
	<screen name="NetworkWiFiActivator" title="Wi-Fi Activator" position="center,center" size="700,220" resolution="1280,720">
		<widget name="status" position="10,10" size="e-20,e-80" font="Regular;20" horizontalAlignment="center" verticalAlignment="center" />
		<widget source="key_red" render="Label" position="10,e-50" size="180,40" backgroundColor="key_red" font="Regular;20" foregroundColor="key_text" horizontalAlignment="center" wrap="off" verticalAlignment="center">
			<convert type="ConditionalShowHide" />
		</widget>
	</screen>"""

	def __init__(self, session, conn: Connection, adapter: Adapter):
		Screen.__init__(self, session, enableHelp=True)
		self.conn = conn
		self.adapter = adapter
		self.ssid = conn.wifi.ssid if conn.wifi else adapter.name
		self.serviceAction = None
		self.pollTimer = None
		self.closeTimer = None
		self.pollCount = 0
		self.setTitle(_("Connecting To '%s'") % adapter.name)
		self["status"] = Label()
		self["key_red"] = StaticText("")
		self["actions"] = HelpableActionMap(self, ["OkCancelActions", "ColorActions"], {
			"cancel": (self.keyClose, _("Close the screen")),
			"red": (self.keyClose, _("Close the screen")),
		}, prio=0, description=_("Wi-Fi Activation Actions"))
		self.pollIntervalMs = 1500
		self.pollMaxAttempts = 20
		self.onLayoutFinish.append(self.start)
		# print(f"[{MODULE_NAME}] DEBUG __init__: iface='{adapter.name}' ssid='{self.ssid!r}'.")

	def keyClose(self):
		self.close("")

	def showCloseButton(self):
		self["key_red"].setText(_("Close"))

	def setStatus(self, text: str):
		self["status"].setText(f"{self.ssid}  ({self.adapter.name})\n\n{text}")

	def start(self):
		def connectedCb(retval: int):
			# print(f"[{MODULE_NAME}] DEBUG connectedCb: iface='{self.adapter.name}' retval='{retval}'.")
			if retval != 0:
				self.setStatus(self.diagnoseFailure())
				self.showCloseButton()
				return
			self.beginPolling()

		self.setStatus(_("Connecting..."))
		networkId = self.conn.wifi.wpaId if self.conn.wifi else None
		# print(f"[{MODULE_NAME}] DEBUG start: dispatching wlanActivate for iface='{self.adapter.name}' networkId='{networkId}'.")
		self.serviceAction = ServiceAction.wlanActivate(self.adapter.name, connectedCb, networkId=networkId)

	def beginPolling(self):
		self.pollCount = 0
		self.setStatus(_("Waiting for IP address..."))
		self.pollTimer = eTimer()
		self.pollTimer.callback.append(self.checkIp)
		self.pollTimer.start(self.pollIntervalMs, True)

	def checkIp(self):
		# iface = self.adapter.name
		self.pollCount += 1
		networkManager.applyNetinfo()
		netInfo = self.adapter.netInfo
		ip = ip4Str(netInfo.ip)
		# print(f"[{MODULE_NAME}] DEBUG checkIp: iface='{iface}' attempt={self.pollCount}/{self.pollMaxAttempts} link='{netInfo.link}' ip='{ip!r}'.")
		if netInfo.link and ip:
			self.pollTimer.stop()
			self.setStatus(_("Connected.\nIP address is '%s'.") % ip)
			self.scheduleClose(5000, ip)
		elif self.pollCount >= self.pollMaxAttempts:
			self.pollTimer.stop()
			self.setStatus(self.diagnoseFailure())
			self.showCloseButton()
		else:
			self.pollTimer.start(self.pollIntervalMs, True)

	def diagnoseFailure(self) -> str:
		"""Best-effort explanation of *why* the connection attempt failed, based on
		wpa_supplicant's association state (wpa_cli status). Distinguishes a
		missing/unreachable AP, a wrong key, and DHCP-only failures instead of a
		single generic "failed" message. The SSID/adapter is already shown by
		setStatus()'s header, so these messages don't repeat it."""
		interface = self.adapter.name
		running = networkManager.wpaSupplicantRunning(interface)
		# print(f"[{MODULE_NAME}] DEBUG diagnoseFailure: iface='{interface}' wpaSupplicantRunning='{running}'.")
		if not running:
			reason = _("Could not connect.\nWi-Fi driver (wpa_supplicant) did not start, check the Wi-Fi settings.")
		else:
			state = networkManager.getWiFiStatus(interface).get("wpa_state", "")
			# print(f"[{MODULE_NAME}] DEBUG diagnoseFailure: iface='{interface}' wpa_state='{state!r}'.")
			if state == "COMPLETED":
				reason = _("Connected, but no IP address was received.\nCheck the router's DHCP settings.")
			elif state in ("4WAY_HANDSHAKE", "GROUP_HANDSHAKE"):
				reason = _("Could not connect.\nWrong Wi-Fi password?")
			elif state in ("SCANNING", "DISCONNECTED", "INACTIVE", ""):
				reason = _("Access point not found.\nCheck it is in range and the SSID is correct.")
			else:
				reason = _("Could not connect (status '%s').") % state
		return f"{reason}\n{_("Saved Wi-Fi network will be retried automatically at next boot.")}"

	def scheduleClose(self, delayMs: int, ip: str):
		def doClose():
			# print(f"[{MODULE_NAME}] DEBUG scheduleClose: firing close() now for iface='{self.adapter.name}' ip='{ip!r}'.")
			self.close(ip)

		# print(f"[{MODULE_NAME}] DEBUG scheduleClose: iface='{self.adapter.name}' delayMs='{delayMs}' ip='{ip!r}'.")
		self.closeTimer = eTimer()
		self.closeTimer.callback.append(doClose)
		self.closeTimer.start(delayMs, True)

	def close(self, *args, **kwargs):
		# print(f"[{MODULE_NAME}] DEBUG close: iface='{self.adapter.name}' args='{args}'.")
		return Screen.close(self, *args, **kwargs)


class NetworkWiFiAddFlow:
	"""Stateless coordinator. Call NetworkWiFiAddFlow.start() to begin
	the work flow of adding the adaptor and the saved network connection."""

	@staticmethod
	def start(session, adapter: Adapter | None = None, callback=None):
		if adapter is not None:
			NetworkWiFiAddFlow.openScan(session, adapter, callback)
		else:
			wifiAdapters = [x for x in networkManager.adapters.values() if x.isWiFi]
			if not wifiAdapters:
				session.showWarning(_("Warning: No Wi-Fi adapter found!"))
			elif len(wifiAdapters) == 1:
				NetworkWiFiAddFlow.openScan(session, wifiAdapters[0], callback)
			else:
				NetworkWiFiAddFlow.pickAdapter(session, wifiAdapters, callback)

	@staticmethod
	def openScan(session, adapter: Adapter, callback):
		def scanned(result: ScanResult | None):
			def setupDone(*result):
				ip = ""
				if len(result) == 1 and isinstance(result[0], tuple):
					saved = bool(result[0][1]) if len(result[0]) > 1 else False
					ip = result[0][2] if len(result[0]) > 2 else ""
				else:
					saved = bool(result[0]) if result else False
				if saved:
					conns = networkManager.getConnections(adapter.name)
					if not any(x.wifi and x.wifi.ssid == (conn.wifi.ssid if conn.wifi else "") for x in conns):
						conns.append(conn)
						networkManager.saveWpaSupplicant(adapter.name)
				if callback:
					callback(ip)

			if result is None or result is True:
				if callback:
					callback()
				return
			existing = next((x for x in networkManager.getConnections(adapter.name) if x.wifi and x.wifi.ssid == result.ssid), None)
			conn = existing if existing is not None else scanResultToConnection(result, adapter.name)

			session.openWithCallback(setupDone, NetworkWiFi, conn, adapter)

		session.openWithCallback(scanned, NetworkWiFiScan, adapter)

	@staticmethod
	def pickAdapter(session, adapters: list[Adapter], callback):
		def chosen(adapter):
			if not adapter:
				if callback:
					callback()
				return
			NetworkWiFiAddFlow.openScan(session, adapter, callback)

		choices = [(x.name, x) for x in adapters]
		session.openWithCallback(chosen, MessageBox, _("Select Wi-Fi adapter"), type=MessageBox.TYPE_YESNO, list=choices)


class NetworkTest(Screen):
	"""Sequential network adapter tests displayed as a simple list."""

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
		self.interface = interface
		self.rows: list[tuple] = []
		self.generation = 0
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
		self["actions"] = HelpableActionMap(self, ["OkCancelActions", "ColorActions"], {
			"cancel": (self.close, _("Close network test")),
			"red": (self.close, _("Close network test")),
			"green": (self.keyRestart, _("Restart test")),
		}, prio=0, description=_("Network Test Actions"))
		self.onLayoutFinish.append(self.layoutFinished)

	def layoutFinished(self):
		self["list"].master.content.setSelectableFunc(lambda *_: False)
		self["list"].enableAutoNavigation(False)
		self.start()

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

		def pingRow(row: int, host: str, okText: str, failText: str, detail: str, nextFn):
			def done(exitCode: int):
				ok = exitCode == 0
				if not hasattr(self, "generation") or self.generation != gen:
					return
				setRow(row, self.STATE_OK if ok else self.STATE_FAIL, okText if ok else failText, detail)
				nextFn()

			setRow(row, self.STATE_BUSY, _("Pinging..."), detail)
			gen = self.generation
			ServiceAction.ping(self.interface, host, done)

		def testDns():
			def done(exitCode: int):
				ok = exitCode == 0
				if not hasattr(self, "generation") or self.generation != gen:
					return
				setRow(self.ROW_DNS, self.STATE_OK if ok else self.STATE_FAIL, _("Available") if ok else _("Unavailable"), "Found Google")

			setRow(self.ROW_DNS, self.STATE_BUSY, _("Resolving..."), "google.com")
			gen = self.generation
			ServiceAction.resolve("google.com", done)

		def testInternet():
			pingRow(self.ROW_INTERNET, "1.1.1.1", reachableText, unreachableText, "Cloudflare accessible", testDns)

		def testGateway():
			gateway = ip4Str(net.gateway) if net.gateway else ""
			if not gateway:
				setRow(self.ROW_GATEWAY, self.STATE_SKIP, _("No gateway"), "")
				setRow(self.ROW_INTERNET, self.STATE_SKIP, notAvailableText, "")
				testDns()
			else:
				pingRow(self.ROW_GATEWAY, gateway, reachableText, unreachableText, gateway, testInternet)

		def testIp():
			ip = net.ip or []
			ipStr = ".".join(str(x) for x in ip) if ip else ""
			if ipStr and ipStr != "0.0.0.0":
				conn = networkManager.activeConnection(self.interface)
				hint = "DHCP" if (conn and conn.dhcp) else _("Static")
				setRow(self.ROW_IP, self.STATE_OK, ipStr, hint)
			else:
				setRow(self.ROW_IP, self.STATE_FAIL, _("No IP address"), "")
			testGateway()

		def testLink():
			if adapter.isWiFi:
				ssid = net.ssid or ""
				if ssid:
					sig = f"{net.signal} dBm" if net.signal else ""
					setRow(self.ROW_LINK, self.STATE_OK, _("Associated"), f"{ssid}  {sig}".strip())
				else:
					setRow(self.ROW_LINK, self.STATE_FAIL, _("Not associated"), "")
			else:
				if net.link:
					setRow(self.ROW_LINK, self.STATE_OK, _("Connected"), formatNetworkSpeed(net.speed) if net.speed > 0 else "")
				else:
					setRow(self.ROW_LINK, self.STATE_FAIL, _("Disconnected"), "")
			testIp()

		self.setTitle(_("Network Test For '%s'") % self.interface)
		adapter = networkManager.adapters.get(self.interface)
		adapterName = networkManager.getFriendlyAdapterName(self.interface)
		net = networkManager.getNetInfo(self.interface)
		isWiFi = adapter.isWiFi if adapter else False
		labels = [
			_("Adapter"),
			_("Wi-Fi link") if isWiFi else _("LAN link"),
			_("IP address"),
			_("Gateway"),
			"Internet",
			"DNS",
		]
		glyph, color = self.STATES[self.STATE_BUSY]
		self.rows = [(glyph, label, "", "", color) for label in labels]
		reachableText = _("Reachable")
		unreachableText = _("Unreachable")
		notAvailableText = _("N/A")
		self["list"].setList(list(self.rows))
		if adapter:
			setRow(self.ROW_ADAPTER, self.STATE_OK, self.interface, adapterName)
			testLink()
		else:
			setRow(self.ROW_ADAPTER, self.STATE_FAIL, _("Not found"), "")
			setRow(self.ROW_LINK, self.STATE_SKIP, notAvailableText, "")
			setRow(self.ROW_IP, self.STATE_SKIP, notAvailableText, "")
			testGateway()


class DNSSettings(Setup):
	"""Global system DNS configuration. Uses networkManager in NetworkManager.py."""

	def __init__(self, session):
		def defaultGateway() -> list[int]:
			result = [0, 0, 0, 0]
			for interface in sorted(networkManager.adapters.keys()):
				if networkManager.adapters[interface].netInfo.up:
					connection = networkManager.activeConnection(interface)
					if connection:
						result = list(connection.gateway)
						break
			return result

		dnsInitial = list(networkManager.nameserverConfig.servers)
		self.dnsOptions = {}
		self.dnsServersV4 = []
		self.dnsServersV6 = []
		self.dnsServerItems = []
		self.dnsServerGroups = []
		if BoxInfo and BoxInfo.getItem("DNSCrypt"):
			self.dnsOptions["dnscrypt"] = {"v4": [[127, 0, 0, 1]], "v6": []}
		fileDom = fileReadXML(resolveFilename(SCOPE_SKINS, "dnsservers.xml"), source=MODULE_NAME)
		if fileDom is not None:
			for dns in fileDom.findall("dnsserver"):
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
		for addr in dnsInitial:
			if isinstance(addr, list) and len(addr) == 4 and v4pos < 2:
				self.dnsOptions["custom"]["v4"][v4pos] = addr
				self.dnsOptions["dhcp-router"]["v4"][v4pos] = addr
				v4pos += 1
			elif isinstance(addr, str):
				try:
					if ip_address(addr).version == 6 and v6pos < 2:
						self.dnsOptions["custom"]["v6"][v6pos] = addr
						self.dnsOptions["dhcp-router"]["v6"][v6pos] = addr
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

	def createSetup(self):  # noqa
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
				self.dnsServerItems.append(getConfigListEntry(
					name,
					entry,
					_("Enter DNS (Dynamic Name Server) %d's IP address.") % item
				))
				self.dnsServerGroups.append(group)
		Setup.createSetup(self, appendItems=self.dnsServerItems)

	def groupIndex(self, index: int) -> int:
		return self.dnsServerGroups[:index].count(self.dnsServerGroups[index])

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

	def moveItem(self, direction: int):
		current = self["config"].getCurrent()
		if current not in self.dnsServerItems:
			return
		index = self.dnsServerItems.index(current)
		group = self.dnsServerGroups[index]
		servers = self.dnsServersV4 if group == "v4" else self.dnsServersV6
		groupIdx = self.groupIndex(index)
		otherIdx = groupIdx + direction
		if 0 <= otherIdx < len(servers):
			servers[groupIdx], servers[otherIdx] = servers[otherIdx], servers[groupIdx]
			self.createSetup()

	def keyMoveItemUp(self):
		self.moveItem(-1)

	def keyMoveItemDown(self):
		self.moveItem(1)

	def keySave(self):
		if self.hostname.isChanged:
			fileWriteLines("/etc/hostname", [self.hostname.value, ""], source=MODULE_NAME)

		servers: list = []
		if config.usage.dns.value == "dnscrypt":
			servers = [[127, 0, 0, 1]]
		elif config.usage.dns.value == "custom":
			for item in self.dnsServerItems:
				val = item[1].value
				if val:
					servers.append(val)
		else:
			for val in self.dnsServersV4 + self.dnsServersV6:
				if val:
					servers.append(val)
		networkManager.setNameservers(servers)
		networkManager.save()
		if config.usage.dns.value == "dnscrypt":
			self.writeDnsCryptToml()
		hasChanges = False
		for notifier in self.onSave:
			notifier()
		for item in self["config"].list:
			if len(item) > 1 and item[1].isChanged():
				hasChanges = True
				break
		if hasChanges:
			self.saveAll()
		self.close()

	def writeDnsCryptToml(self):  # DNSCrypt TOML helpers.
		def insertSectionKey(lines, sectionName, key, rhs, anchorKeys, foundSet):
			def findSectionRange(lines, sectionName):
				start = None
				result = None
				for index, line in enumerate(lines):
					lineStripped = line.strip()
					if lineStripped.startswith("[") and lineStripped.endswith("]"):
						name = lineStripped.strip()[1:-1].strip()
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

		def tomlBool(val):
			return "true" if bool(val) else "false"

		def tomlInt(val, default=0):
			try:
				result = str(int(val))
			except Exception:
				result = str(int(default))
			return result

		def tomlStr(val):
			return f"\"{str(val).replace("\\", "\\\\").replace('"', '\\"')}\""

		def replaceKeyLine(line, key, newRhs, foundSet):
			lineStripped = line.lstrip()
			indent = line[:len(line) - len(lineStripped)]
			result = line
			if lineStripped.startswith((f"{key} ", f"{key}=", f"#{key} ", f"#{key}=")):
				foundSet.add(key)
				result = f"{indent}{key} = {newRhs}"
			return result

		tomlPath = "/etc/dnscrypt-proxy/dnscrypt-proxy.toml"
		oldLines = fileReadLines(tomlPath, default=[], source=MODULE_NAME)
		if oldLines:
			found = set()
			newLines = []
			currentSection = None
			for line in oldLines:
				lineStripped = line.strip()
				if lineStripped.startswith("[") and lineStripped.endswith("]"):
					currentSection = lineStripped.strip()[1:-1].strip()
					newLines.append(line)
					continue
				if currentSection is None:
					line = replaceKeyLine(line, "ipv4_servers", tomlBool(config.usage.dnsMode.value != 3), found)
					line = replaceKeyLine(line, "ipv6_servers", tomlBool(config.usage.dnsMode.value != 2), found)
					line = replaceKeyLine(line, "dnscrypt_servers", tomlBool(config.usage.DNSCryptProtocol.value), found)
					line = replaceKeyLine(line, "doh_servers", tomlBool(config.usage.DNSCryptDoH.value), found)
					line = replaceKeyLine(line, "odoh_servers", tomlBool(config.usage.DNSCryptODoH.value), found)
					line = replaceKeyLine(line, "require_dnssec", tomlBool(config.usage.DNSCryptDNSSEC.value), found)
					line = replaceKeyLine(line, "require_nolog", tomlBool(config.usage.DNSCryptNoLog.value), found)
					line = replaceKeyLine(line, "require_nofilter", tomlBool(config.usage.DNSCryptNoFilter.value), found)
					line = replaceKeyLine(line, "cache", tomlBool(config.usage.DNSCryptCache.value), found)
					newLines.append(line)
					continue
				if currentSection == "monitoring_ui":
					for attribute, key, value in [
						("DNSCryptUI", "enabled", tomlBool(config.usage.DNSCryptUI.value)),
						(None, "listen_address", tomlStr(f"0.0.0.0:{tomlInt(config.usage.DNSCryptPort.value, 9012)}")),
						("DNSCryptUsername", "username", tomlStr(config.usage.DNSCryptUsername.value.strip())),
						("DNSCryptPassword", "password", tomlStr(config.usage.DNSCryptPassword.value.strip())),
						("DNSCryptPrivacy", "privacy_level", tomlInt(config.usage.DNSCryptPrivacy.value, 1)),
					]:
						tmpFound = set()
						replacement = replaceKeyLine(line, key, value, tmpFound)
						if key in tmpFound:
							found.add(f"monitoring_ui.{key}")
							line = replacement
				newLines.append(line)
			insertSectionKey(newLines, "monitoring_ui", "enabled", tomlBool(config.usage.DNSCryptUI.value), ["enabled"], found)
			insertSectionKey(newLines, "monitoring_ui", "listen_address", tomlStr(f"0.0.0.0:{tomlInt(config.usage.DNSCryptPort.value, 9012)}"), ["enabled", "listen_address"], found)
			insertSectionKey(newLines, "monitoring_ui", "username", tomlStr(config.usage.DNSCryptUsername.value.strip()), ["listen_address", "username"], found)
			insertSectionKey(newLines, "monitoring_ui", "password", tomlStr(config.usage.DNSCryptPassword.value.strip()), ["username", "password"], found)
			insertSectionKey(newLines, "monitoring_ui", "privacy_level", tomlInt(config.usage.DNSCryptPrivacy.value, 1), ["password", "privacy_level"], found)
			tmpPath = f"{tomlPath}.tmp"
			fileWriteLines(tmpPath, newLines)
			if exists(tmpPath):
				rename(tmpPath, tomlPath)
