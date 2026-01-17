from errno import ETIMEDOUT
from ipaddress import ip_address
from json import dumps, loads
from glob import glob
from os import rename, strerror, system
from os.path import exists
from process import ProcessList
from random import Random
from urllib.request import Request, urlopen

from enigma import eConsoleAppContainer, eTimer

from Components.About import about
from Components.ActionMap import HelpableActionMap, HelpableNumberActionMap
from Components.config import ConfigIP, ConfigMacText, ConfigNumber, ConfigPassword, ConfigSelection, ConfigText, ConfigYesNo, NoSave, ReadOnly, config, getConfigListEntry
from Components.ConfigList import ConfigListScreen
from Components.Console import Console
from Components.Label import Label, MultiColorLabel
from Components.MenuList import MenuList
from Components.Network import iNetwork
from Components.Pixmap import Pixmap, MultiPixmap
from Components.ScrollLabel import ScrollLabel
from Components.SystemInfo import BoxInfo, getBoxDisplayName
from Components.PluginComponent import plugins
from Components.FileList import MultiFileSelectList
from Components.Opkg import OpkgComponent
from Components.Sources.Boolean import Boolean
from Components.Sources.List import List
from Components.Sources.StaticText import StaticText
from Plugins.Plugin import PluginDescriptor
from Screens.MessageBox import MessageBox
from Screens.RestartNetwork import RestartNetworkNew
from Screens.Processing import Processing
from Screens.Screen import Screen
from Screens.Setup import Setup
from Tools.Directories import SCOPE_SKINS, SCOPE_GUISKIN, SCOPE_PLUGINS, fileReadLines, fileReadXML, fileWriteLine, fileWriteLines, resolveFilename
from Tools.LoadPixmap import LoadPixmap

MODULE_NAME = __name__.split(".")[-1]
BASE_GROUP = "packagegroup-base"


def queryWirelessDevice(iface):
	try:
		from wifi.scan import Cell
		import errno
	except ImportError:
		return False
	else:
		from wifi.exceptions import InterfaceError
		try:
			system(f"ifconfig {iface} up")
			wlanresponse = list(Cell.all(iface))  # noqa F841
		except InterfaceError as ie:
			print(f"[NetworkSetup] queryWirelessDevice InterfaceError: {str(ie)}")
			return False
		except OSError as xxx_todo_changeme:
			(error_no, error_str) = xxx_todo_changeme.args
			if error_no in (errno.EOPNOTSUPP, errno.ENODEV, errno.EPERM):
				return False
			else:
				print(f"[NetworkSetup] queryWirelessDevice OSError: {error_no} '{error_str}'")
				return True
		else:
			return True


class NetworkAdapterSelection(Screen):
	def __init__(self, session):
		Screen.__init__(self, session, enableHelp=True)
		self.setTitle(_("Network Settings"))
		self.wlan_errortext = _("No working wireless network adapter found.\nPlease verify that you have attached a compatible WLAN device and your network is configured correctly.")
		self.lan_errortext = _("No working local network adapter found.\nPlease verify that you have attached a network cable and your network is configured correctly.")
		self.oktext = _("Press OK on your remote control to continue.")
		self.edittext = _("Press OK to edit the settings.")
		self["key_red"] = StaticText(_("Close"))
		self["key_green"] = StaticText(_("Select"))
		self["key_yellow"] = StaticText(_("Network Restart"))
		self["key_blue"] = StaticText(_(""))
		self["introduction"] = StaticText(self.edittext)
		self["OkCancelActions"] = HelpableActionMap(self, ["OkCancelActions", "ColorActions", "MenuActions"], {
			"cancel": (self.close, _("Exit network interface list")),
			"ok": (self.okbuttonClick, _("Select interface")),
			"red": (self.close, _("Exit network interface list")),
			"green": (self.okbuttonClick, _("Select interface")),
			"yellow": (self.restartLanAsk, _("Restart network to with current setup")),
			"menu": (self.menubuttonClick, _("Select interface"))
		}, prio=0, description=_("Network Adapter Actions"))

		if exists(resolveFilename(SCOPE_PLUGINS, "SystemPlugins/NetworkWizard/networkwizard.xml")):
			self["wizardActions"] = HelpableActionMap(self, ["ColorActions"], {
				"blue": (self.openNetworkWizard, _("Use the network wizard to configure selected network adapter"))
			}, prio=0, description=_("Network Adapter Actions"))
			self["key_blue"].setText(_("Network Wizard"))

		self.adapters = [(iNetwork.getFriendlyAdapterName(x), x) for x in iNetwork.getAdapterList()]
		if not self.adapters:
			self.adapters = [(iNetwork.getFriendlyAdapterName(x), x) for x in iNetwork.getConfiguredAdapters()]
		if len(self.adapters) == 0:
			self.adapters = [(iNetwork.getFriendlyAdapterName(x), x) for x in iNetwork.getInstalledAdapters()]
		self.onChangedEntry = []
		self.list = []
		self["list"] = List(self.list)
		self.updateList()
		if self.selectionChanged not in self["list"].onSelectionChanged:
			self["list"].onSelectionChanged.append(self.selectionChanged)
		self.onClose.append(self.cleanup)

	def createSummary(self):
		from Screens.PluginBrowser import PluginBrowserSummary
		return PluginBrowserSummary

	def selectionChanged(self):
		item = self["list"].getCurrent()
		if item:
			name = item[0]
			desc = item[1]
		else:
			name = ""
			desc = ""
		for cb in self.onChangedEntry:
			cb(name, desc)

	def buildInterfaceList(self, iface, name, default, active):
		divpng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_GUISKIN, "div-h.png"))
		defaultpng = None
		activepng = None
		description = None
		interfacepng = None
		if not iNetwork.isWirelessInterface(iface):
			if active is True:
				interfacepng = LoadPixmap(resolveFilename(SCOPE_GUISKIN, "icons/network_wired-active.png"))
			elif active is False:
				interfacepng = LoadPixmap(resolveFilename(SCOPE_GUISKIN, "icons/network_wired-inactive.png"))
			else:
				interfacepng = LoadPixmap(resolveFilename(SCOPE_GUISKIN, "icons/network_wired.png"))
		else:
			if active is True:
				interfacepng = LoadPixmap(resolveFilename(SCOPE_GUISKIN, "icons/network_wireless-active.png"))
			elif active is False:
				interfacepng = LoadPixmap(resolveFilename(SCOPE_GUISKIN, "icons/network_wireless-inactive.png"))
			else:
				interfacepng = LoadPixmap(resolveFilename(SCOPE_GUISKIN, "icons/network_wireless.png"))
		if active is True:
			activepng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_GUISKIN, "icons/lock_on.png"))
		elif active is False:
			activepng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_GUISKIN, "icons/lock_error.png"))
		description = iNetwork.getFriendlyAdapterDescription(iface)
		return iface, name, description, interfacepng, defaultpng, activepng, divpng

	def updateList(self):
		self.list = []
		for adapter in self.adapters:
			active_int = iNetwork.getAdapterAttribute(adapter[1], "up")
			self.list.append(self.buildInterfaceList(adapter[1], _(adapter[0]), 0, active_int))
		self["list"].setList(self.list)

	def menubuttonClick(self):
		selection = self["list"].getCurrent()
		if selection:
			self.session.openWithCallback(self.AdapterSetupClosed, AdapterSetupConfiguration, selection[0])

	def okbuttonClick(self):
		selection = self["list"].getCurrent()
		if selection:
			if iNetwork.isWirelessInterface(selection[0]):
				try:
					from Plugins.SystemPlugins.WirelessLan.plugin import WlanScan  # noqa F401
					if queryWirelessDevice(selection[0]):
						self.session.openWithCallback(self.AdapterSetupClosed, AdapterSetup, selection[0])
				except ImportError:
					self.session.open(MessageBox, _("No working wireless network interface found.\n Please verify that you have attached a compatible WLAN device or enable your local network interface."), type=MessageBox.TYPE_INFO, timeout=10)
			else:
				self.session.openWithCallback(self.AdapterSetupClosed, AdapterSetup, selection[0])

	def AdapterSetupClosed(self, *ret):
		if len(self.adapters) == 1:
			self.close()
		else:
			self.updateList()

	def cleanup(self):
		iNetwork.stopLinkStateConsole()
		iNetwork.stopRestartConsole()

	def restartLanAsk(self):
		self.session.openWithCallback(self.restartLan, MessageBox, _("Are you sure you want to restart your network interfaces?"))

	def restartLan(self, ret=False):
		if ret:
			def restartfinishedCB():
				self.updateList()
				self.session.open(MessageBox, _("Finished configuring your network"), type=MessageBox.TYPE_INFO, timeout=10, default=False)
			RestartNetworkNew.start(callback=restartfinishedCB)

	def openNetworkWizard(self):
		try:
			from Plugins.SystemPlugins.NetworkWizard.NetworkWizard import NetworkWizard
		except ImportError:
			self.session.open(MessageBox, _("The network wizard extension is not installed!\nPlease install it."), type=MessageBox.TYPE_INFO, timeout=10)
		else:
			selection = self["list"].getCurrent()
			if selection is not None:
				self.session.openWithCallback(self.AdapterSetupClosed, NetworkWizard, selection[0])


class DNSSettings(Setup):
	def __init__(self, session):
		self.dnsInitial = iNetwork.loadResolveConfig()
		print(f"[NetworkSetup] DNSSettings: Initial DNS list: {self.dnsInitial}.")
		self.dnsOptions = {}
		if BoxInfo.getItem("DNSCrypt"):
			self.dnsOptions["dnscrypt"] = [[127, 0, 0, 1]]
		fileDom = fileReadXML(resolveFilename(SCOPE_SKINS, "dnsservers.xml"), source=MODULE_NAME)
		for dns in fileDom.findall("dnsserver"):
			if key := dns.get("key", ""):
				addresses = []
				ipv4s = dns.get("ipv4", "")
				if ipv4s:
					for ipv4 in [x.strip() for x in ipv4s.split(",")]:
						addresses.append([int(x) for x in ipv4.split(".")])
				ipv6s = dns.get("ipv6", "")
				if ipv6s:
					addresses.extend([x.strip() for x in ipv6s.split(",")])
				self.dnsOptions[key] = addresses
		dnsSource = config.usage.dns.value
		self.dnsOptions["custom"] = [self.defaultGW(), [0, 0, 0, 0], "", ""]
		self.dnsOptions["dhcp-router"] = [self.defaultGW(), [0, 0, 0, 0], "", ""]
		if dnsSource not in self.dnsOptions:
			config.usage.dns.value = "custom"

		self.dnsServerItems = []
		v4pos = 0
		v6pos = 2
		for addr in self.dnsInitial:
			if isinstance(addr, list) and len(addr) == 4:
				self.dnsOptions["custom"][v4pos] = addr
				self.dnsOptions["dhcp-router"][v4pos] = addr
				v4pos += 1
			if isinstance(addr, str) and ip_address(addr).version == 6:
				self.dnsOptions["custom"][v6pos] = addr
				self.dnsOptions["dhcp-router"][v6pos] = addr
				v6pos += 1

		Setup.__init__(self, session=session, setup="DNS")

	def defaultGW(self):
		ifaces = sorted(iNetwork.ifaces.keys())
		for iface in ifaces:
			if iNetwork.getAdapterAttribute(iface, "up"):
				return iNetwork.getAdapterAttribute(iface, "gateway")
		return [0, 0, 0, 0]

	def createSetup(self):  # NOSONAR silence S2638
		if config.usage.dns.value != "dnscrypt":
			self.dnsServers = self.dnsOptions[config.usage.dns.value][:]
			v4 = config.usage.dnsMode.value != 3
			v6 = config.usage.dnsMode.value != 2
			self.dnsServerItems = []
			if config.usage.dns.value == "custom":
				items = []
				if v4:
					items.append(NoSave(ConfigIP(self.dnsServers[0])))
					items.append(NoSave(ConfigIP(self.dnsServers[1])))
				if v6:
					items.append(NoSave(ConfigText(default=self.dnsServers[2], fixed_size=False)))
					items.append(NoSave(ConfigText(default=self.dnsServers[3], fixed_size=False)))
			else:
				items = []
				for addr in self.dnsServers:
					if v4 and isinstance(addr, list) and len(addr) == 4:
						items.append(ReadOnly(NoSave(ConfigIP(default=addr))))
					elif v6 and isinstance(addr, str):
						items.append(ReadOnly(NoSave(ConfigText(default=addr, fixed_size=False))))
			entry = None
			for item, entry in enumerate(items, start=1):
				name = _("Name server %d") % item
				if config.usage.dns.value != "custom":
					name = (name, 0)
				self.dnsServerItems.append(getConfigListEntry(name, entry, _("Enter DNS (Dynamic Name Server) %d's IP address.") % item))
		else:
			self.dnsServerItems = []
		Setup.createSetup(self, appendItems=self.dnsServerItems)

	def changedEntry(self):
		if config.usage.dns.value == "custom":
			current = self["config"].getCurrent()
			if current in self.dnsServerItems:
				idx = self.dnsServerItems.index(current)
				if config.usage.dnsMode.value == 3:  # IPV6 only
					idx += 2
				value = current[1].value
				self.dnsServers[idx] = value
		return Setup.changedEntry(self)

	def keySave(self):
		iNetwork.clearNameservers()
		if config.usage.dns.value == "dnscrypt":
			iNetwork.addNameserver([127, 0, 0, 1])
		elif config.usage.dns.value != "custom":
			for value in self.dnsServers:
				iNetwork.addNameserver(value)
		else:
			for item in self.dnsServerItems:
				value = item[1].value
				if value:
					iNetwork.addNameserver(value)
		print(f"[NetworkSetup] DNSSettings: Saved DNS list: {str(iNetwork.getNameserverList())}.")
		iNetwork.writeNameserverConfig()
		if config.usage.dns.value == "dnscrypt":
			self.writeDNSCryptToml()
		hasChanges = False
		for notifier in self.onSave:
			notifier()
		for item in self["config"].list:
			if len(item) > 1 and item[1].isChanged():
				hasChanges = True
				break

		if hasChanges:
			self.saveAll()
			RestartNetworkNew.start(callback=self.close)
		else:
			self.close()

	def tomlBool(self, val):
		return "true" if bool(val) else "false"

	def tomlStr(self, val):
		s = str(val).replace("\\", "\\\\").replace('"', '\\"')
		return f'"{s}"'

	def tomlInt(self, val, default=0):
		try:
			return str(int(val))
		except Exception:
			return str(int(default))

	def replaceKeyLine(self, line, key, new_rhs, foundSet):
		ls = line.lstrip()
		indent = line[:len(line) - len(ls)]
		if ls.startswith(f"{key} ") or ls.startswith(f"{key}=") or ls.startswith(f"#{key} ") or ls.startswith(f"#{key}="):
			foundSet.add(key)
			return f"{indent}{key} = {new_rhs}"
		return line

	def insertGlobalKey(self, lines, key, rhs, anchorKeys, foundSet):
		def findGlobalEnd(lines):
			for i, line in enumerate(lines):
				s = line.lstrip()
				if s.startswith("[") and s.rstrip().endswith("]") and not s.startswith("#"):
					return i
			return len(lines)

		if key in foundSet:
			return
		endGlobal = findGlobalEnd(lines)
		insertAt = None
		for i in range(endGlobal):
			s = lines[i].lstrip()
			for a in anchorKeys:
				if s.startswith(f"{a} ") or s.startswith(f"{a}=") or s.startswith(f"#{a} ") or s.startswith(f"#{a}="):
					insertAt = i + 1
		if insertAt is None:
			insertAt = endGlobal
		lines.insert(insertAt, f"{key} = {rhs}")
		foundSet.add(key)

	def findSectionRange(self, lines, sectionName):
		start = None
		for i, line in enumerate(lines):
			s = line.lstrip()
			if s.startswith("[") and s.rstrip().endswith("]") and not s.startswith("#"):
				name = s.strip()[1:-1].strip()
				if start is None and name == sectionName:
					start = i + 1
					continue
				if start is not None:
					return (start, i)
		if start is not None:
			return (start, len(lines))
		return (None, None)

	def insertSectionKey(self, lines, sectionName, key, rhs, anchorKeys, foundSet):
		foundToken = f"{sectionName}.{key}"
		if foundToken in foundSet:
			return
		start, end = self.findSectionRange(lines, sectionName)
		if start is None:
			return
		insertAt = None
		for i in range(start, end):
			s = lines[i].lstrip()
			for a in anchorKeys:
				if s.startswith(f"{a} ") or s.startswith(f"{a}=") or s.startswith(f"#{a} ") or s.startswith(f"#{a}="):
					insertAt = i + 1
		if insertAt is None:
			insertAt = end
		lines.insert(insertAt, f"{key} = {rhs}")
		foundSet.add(foundToken)

	def writeDNSCryptToml(self):
		tomlPath = "/etc/dnscrypt-proxy/dnscrypt-proxy.toml"
		oldLines = fileReadLines(tomlPath, source=MODULE_NAME)
		if not oldLines:
			print("[NetworkSetup] DNSSettings: DNSCrypt config file is missing, cannot write settings.")
			return
		found = set()
		newLines = []
		currentSection = None
		for line in oldLines:
			ls = line.lstrip()
			if ls.startswith("[") and ls.rstrip().endswith("]") and not ls.startswith("#"):
				currentSection = ls.strip()[1:-1].strip()
				newLines.append(line)
				continue
			if currentSection is None:
				line = self.replaceKeyLine(line, "ipv4_servers", self.tomlBool(config.usage.dnsMode.value != 3), found)
				line = self.replaceKeyLine(line, "ipv6_servers", self.tomlBool(config.usage.dnsMode.value != 2), found)
				line = self.replaceKeyLine(line, "dnscrypt_servers", self.tomlBool(config.usage.DNSCryptProtocol.value), found)
				line = self.replaceKeyLine(line, "doh_servers", self.tomlBool(config.usage.DNSCryptDoH.value), found)
				line = self.replaceKeyLine(line, "odoh_servers", self.tomlBool(config.usage.DNSCryptODoH.value), found)
				line = self.replaceKeyLine(line, "require_dnssec", self.tomlBool(config.usage.DNSCryptDNSSEC.value), found)
				line = self.replaceKeyLine(line, "require_nolog", self.tomlBool(config.usage.DNSCryptNoLog.value), found)
				line = self.replaceKeyLine(line, "require_nofilter", self.tomlBool(config.usage.DNSCryptNoFilter.value), found)
				line = self.replaceKeyLine(line, "cache", self.tomlBool(config.usage.DNSCryptCache.value), found)
				newLines.append(line)
				continue
			if currentSection == "monitoring_ui":
				tmpFound = set()
				line2 = self.replaceKeyLine(line, "enabled", self.tomlBool(config.usage.DNSCryptUI.value), tmpFound)
				if "enabled" in tmpFound:
					found.add("monitoring_ui.enabled")
					line = line2
				listenValue = self.tomlStr(f"0.0.0.0:{self.tomlInt(config.usage.DNSCryptPort.value, default=9012)}")
				tmpFound.clear()
				line2 = self.replaceKeyLine(line, "listen_address", listenValue, tmpFound)
				if "listen_address" in tmpFound:
					found.add("monitoring_ui.listen_address")
					line = line2
				tmpFound.clear()
				line2 = self.replaceKeyLine(line, "username", self.tomlStr(config.usage.DNSCryptUsername.value.strip()), tmpFound)
				if "username" in tmpFound:
					found.add("monitoring_ui.username")
					line = line2
				tmpFound.clear()
				line2 = self.replaceKeyLine(line, "password", self.tomlStr(config.usage.DNSCryptPassword.value.strip()), tmpFound)
				if "password" in tmpFound:
					found.add("monitoring_ui.password")
					line = line2
				tmpFound.clear()
				line2 = self.replaceKeyLine(line, "privacy_level", self.tomlInt(config.usage.DNSCryptPrivacy.value, default=1), tmpFound)
				if "privacy_level" in tmpFound:
					found.add("monitoring_ui.privacy_level")
					line = line2
				newLines.append(line)
				continue
			newLines.append(line)
		self.insertSectionKey(newLines, "monitoring_ui", "enabled", self.tomlBool(config.usage.DNSCryptUI.value), anchorKeys=["enabled"], foundSet=found)
		self.insertSectionKey(newLines, "monitoring_ui", "listen_address", self.tomlStr(f"0.0.0.0:{self.tomlInt(config.usage.DNSCryptPort.value, default=9012)}"), anchorKeys=["enabled", "listen_address"], foundSet=found)
		self.insertSectionKey(newLines, "monitoring_ui", "username", self.tomlStr(config.usage.DNSCryptUsername.value.strip()), anchorKeys=["listen_address", "username"], foundSet=found)
		self.insertSectionKey(newLines, "monitoring_ui", "password", self.tomlStr(config.usage.DNSCryptPassword.value.strip()), anchorKeys=["username", "password"], foundSet=found)
		self.insertSectionKey(newLines, "monitoring_ui", "privacy_level", self.tomlInt(config.usage.DNSCryptPrivacy.value, default=1), anchorKeys=["password", "privacy_level"], foundSet=found)
		tmpPath = f"{tomlPath}.tmp"
		fileWriteLines(tmpPath, newLines)
		if exists(tmpPath):
			rename(tmpPath, tomlPath)


class NameserverSetup(DNSSettings):
	def __init__(self, session):
		DNSSettings.__init__(self, session=session)


class AdapterSetup(ConfigListScreen, Screen):
	def __init__(self, session, networkinfo, essid=None):
		Screen.__init__(self, session, enableHelp=True)
		self.setTitle(_("Adapter Settings"))
		if isinstance(networkinfo, (list, tuple)):
			self.iface = networkinfo[0]
			self.essid = networkinfo[1]
		else:
			self.iface = networkinfo
			self.essid = essid
		macAddr = about.getIfConfig(self.iface).get("hwaddr", "") if self.iface == "eth0" else ""
		self.getConfigMac = NoSave(ConfigMacText(default=macAddr)) if macAddr else None
		self.extended = None
		self.applyConfigRef = None
		self.finished_cb = None
		self.oktext = _("Press OK on your remote control to continue.")
		self.oldInterfaceState = iNetwork.getAdapterAttribute(self.iface, "up")
		self.createConfig()
		self["actions"] = HelpableActionMap(self, ["OkCancelActions", "ColorActions"], {
			"cancel": (self.keyCancel, _("Exit network adapter configuration")),
			"ok": (self.keySave, _("Activate network adapter configuration")),
			"red": (self.keyCancel, _("Exit network adapter configuration")),
			"green": (self.keySave, _("Activate network adapter configuration"))
		}, prio=0, description=_("Network Adapter Actions"))
		self.list = []
		ConfigListScreen.__init__(self, self.list, session=session)
		self.createSetup()
		self.onLayoutFinish.append(self.layoutFinished)
		self.onClose.append(self.cleanup)
		self["DNS1text"] = StaticText(_("Primary DNS"))
		self["DNS2text"] = StaticText(_("Secondary DNS"))
		self["DNS1"] = StaticText()
		self["DNS2"] = StaticText()
		self["introduction"] = StaticText(_("Current settings:"))
		self["IPtext"] = StaticText(_("IP address"))
		self["Netmasktext"] = StaticText(_("Netmask"))
		self["Gatewaytext"] = StaticText(_("Gateway"))
		self["IP"] = StaticText()
		self["Mask"] = StaticText()
		self["Gateway"] = StaticText()
		self["Adaptertext"] = StaticText(_("Network:"))
		self["Adapter"] = StaticText()
		self["introduction2"] = StaticText(_("Press OK to activate the settings."))
		self["key_red"] = StaticText(_("Cancel"))
		self["key_green"] = StaticText(_("Save"))
		self["key_blue"] = StaticText()
		self["VKeyIcon"] = Boolean(False)
		self["HelpWindow"] = Pixmap()
		self["HelpWindow"].hide()

	def layoutFinished(self):
		self["DNS1"].setText(self.primaryDNS.getText())
		self["DNS2"].setText(self.secondaryDNS.getText())
		if self.ipConfigEntry.getText() is not None:
			if self.ipConfigEntry.getText() == "0.0.0.0":
				self["IP"].setText(_("N/A"))
			else:
				self["IP"].setText(self.ipConfigEntry.getText())
		else:
			self["IP"].setText(_("N/A"))
		if self.netmaskConfigEntry.getText() is not None:
			if self.netmaskConfigEntry.getText() == "0.0.0.0":
				self["Mask"].setText(_("N/A"))
			else:
				self["Mask"].setText(self.netmaskConfigEntry.getText())
		else:
			self["IP"].setText(_("N/A"))
		if iNetwork.getAdapterAttribute(self.iface, "gateway"):
			if self.gatewayConfigEntry.getText() == "0.0.0.0":
				self["Gatewaytext"].setText(_("Gateway"))
				self["Gateway"].setText(_("N/A"))
			else:
				self["Gatewaytext"].setText(_("Gateway"))
				self["Gateway"].setText(self.gatewayConfigEntry.getText())
		else:
			self["Gateway"].setText("")
			self["Gatewaytext"].setText("")
		self["Adapter"].setText(iNetwork.getFriendlyAdapterName(self.iface))

	def createConfig(self):
		self.InterfaceEntry = None
		self.dhcpEntry = None
		self.gatewayEntry = None
		self.DNSConfigEntry = None
		self.hiddenSSID = None
		self.wlanSSID = None
		self.encryption = None
		self.encryptionType = None
		self.encryptionKey = None
		self.encryptionlist = None
		self.weplist = None
		self.wsconfig = None
		self.default = None
		self.primaryDNSEntry = None
		self.secondaryDNSEntry = None
		self.onlyWakeOnWiFi = False
		self.WakeOnWiFiEntry = False
		self.ipTypeEntry = None
		if iNetwork.isWirelessInterface(self.iface):
			driver = iNetwork.detectWlanModule(self.iface)
			if driver in ("brcm-wl", ):
				from Plugins.SystemPlugins.WirelessLan.Wlan import brcmWLConfig
				self.ws = brcmWLConfig()
			else:
				from Plugins.SystemPlugins.WirelessLan.Wlan import wpaSupplicant
				self.ws = wpaSupplicant()
			self.encryptionlist = []
			self.encryptionlist.append(("Unencrypted", _("Unencrypted")))
			self.encryptionlist.append(("WEP", _("WEP")))
			self.encryptionlist.append(("WPA", _("WPA")))
			if not exists(f"/tmp/bcm/{self.iface}"):
				self.encryptionlist.append(("WPA/WPA2", _("WPA or WPA2")))
			self.encryptionlist.append(("WPA2", _("WPA2")))
			self.weplist = []
			self.weplist.append("ASCII")
			self.weplist.append("HEX")
			self.wsconfig = self.ws.loadConfig(self.iface)
			if self.essid is None:
				self.essid = self.wsconfig["ssid"]
			if iNetwork.canWakeOnWiFi(self.iface):
				iface_file = "/etc/network/interfaces"
				default_v = False
				if exists(iface_file):
					with open(iface_file) as f:
						output = f.read()
					search_str = f"#only WakeOnWiFi {self.iface}"
					if output.find(search_str) >= 0:
						default_v = True
				self.onlyWakeOnWiFi = NoSave(ConfigYesNo(default=default_v))
			config.plugins.wlan.hiddenessid = NoSave(ConfigYesNo(default=self.wsconfig["hiddenessid"]))
			config.plugins.wlan.essid = NoSave(ConfigText(default=self.essid, visible_width=50, fixed_size=False))
			config.plugins.wlan.encryption = NoSave(ConfigSelection(self.encryptionlist, default=self.wsconfig["encryption"]))
			config.plugins.wlan.wepkeytype = NoSave(ConfigSelection(self.weplist, default=self.wsconfig["wepkeytype"]))
			config.plugins.wlan.psk = NoSave(ConfigPassword(default=self.wsconfig["key"], visible_width=50, fixed_size=False))
		self.activateInterfaceEntry = NoSave(ConfigYesNo(default=iNetwork.getAdapterAttribute(self.iface, "up") or False))
		self.dhcpConfigEntry = NoSave(ConfigYesNo(default=iNetwork.getAdapterAttribute(self.iface, "dhcp") or False))
		self.ipConfigEntry = NoSave(ConfigIP(default=iNetwork.getAdapterAttribute(self.iface, "ip")) or [0, 0, 0, 0])
		self.netmaskConfigEntry = NoSave(ConfigIP(default=iNetwork.getAdapterAttribute(self.iface, "netmask") or [255, 0, 0, 0]))
		if iNetwork.getAdapterAttribute(self.iface, "gateway"):
			self.dhcpdefault = True
		else:
			self.dhcpdefault = False
		self.hasGatewayConfigEntry = NoSave(ConfigYesNo(default=self.dhcpdefault or False))
		self.gatewayConfigEntry = NoSave(ConfigIP(default=iNetwork.getAdapterAttribute(self.iface, "gateway") or [0, 0, 0, 0]))
		nameserver = (iNetwork.getNameserverList() + [[0, 0, 0, 0]] * 2)[0:2]
		self.primaryDNS = NoSave(ConfigIP(default=nameserver[0]))
		self.secondaryDNS = NoSave(ConfigIP(default=nameserver[1]))
		self.ipTypeConfigEntry = NoSave(ConfigYesNo(default=iNetwork.getAdapterAttribute(self.iface, "ipv6") or False))

	def createSetup(self):
		if BoxInfo.getItem("WakeOnLAN"):
			self.wolstartvalue = config.network.wol.value
		self.list = []
		self.InterfaceEntry = getConfigListEntry(_("Use interface"), self.activateInterfaceEntry)
		self.list.append(self.InterfaceEntry)
		if self.onlyWakeOnWiFi:
			self.WakeOnWiFiEntry = getConfigListEntry(_("Use only for Wake on WLan (WoW)"), self.onlyWakeOnWiFi)
			self.list.append(self.WakeOnWiFiEntry)
		if self.activateInterfaceEntry.value or (self.onlyWakeOnWiFi and self.onlyWakeOnWiFi.value):
			self.ipTypeEntry = getConfigListEntry(_("Enable IPv6"), self.ipTypeConfigEntry)
			self.list.append(self.ipTypeEntry)
			self.dhcpEntry = getConfigListEntry(_("Use DHCP"), self.dhcpConfigEntry)
			self.list.append(self.dhcpEntry)
			if not self.dhcpConfigEntry.value:
				self.list.append(getConfigListEntry(_("IP address"), self.ipConfigEntry))
				self.list.append(getConfigListEntry(_("Netmask"), self.netmaskConfigEntry))
				self.gatewayEntry = getConfigListEntry(_("Use a gateway"), self.hasGatewayConfigEntry)
				self.list.append(self.gatewayEntry)
				if self.hasGatewayConfigEntry.value:
					self.list.append(getConfigListEntry(_("Gateway"), self.gatewayConfigEntry))
			if self.getConfigMac:
				self.list.append(getConfigListEntry(_("MAC-address"), self.getConfigMac))
			havewol = False
			if BoxInfo.getItem("WakeOnLAN") and BoxInfo.getItem("machinebuild") not in ("et10000", "gb800seplus", "gb800ueplus", "gbultrase", "gbultraue", "gbultraueh", "gbipbox", "gbquad", "gbx1", "gbx2", "gbx3", "gbx3h"):
				havewol = True
			if BoxInfo.getItem("machinebuild") in ("et10000", "vuultimo4k", "vuduo4kse") and self.iface == "eth0":
				havewol = False
			if havewol and self.onlyWakeOnWiFi is not True:
				self.list.append(getConfigListEntry(_("Enable Wake On LAN"), config.network.wol))
			self.extended = None
			self.configStrings = None
			for p in plugins.getPlugins(PluginDescriptor.WHERE_NETWORKSETUP):
				callFnc = p.__call__["ifaceSupported"](self.iface)
				if callFnc is not None:
					if "WlanPluginEntry" in p.__call__:  # Internally used only for WLAN Plugin.
						self.extended = callFnc
						if "configStrings" in p.__call__:
							self.configStrings = p.__call__["configStrings"]
						isExistBcmWifi = exists(f"/tmp/bcm/{self.iface}")
						if not isExistBcmWifi:
							self.hiddenSSID = getConfigListEntry(_("Hidden network"), config.plugins.wlan.hiddenessid)
							self.list.append(self.hiddenSSID)
						self.wlanSSID = getConfigListEntry(_("Network name (SSID)"), config.plugins.wlan.essid)
						self.list.append(self.wlanSSID)
						self.encryption = getConfigListEntry(_("Encryption"), config.plugins.wlan.encryption)
						self.list.append(self.encryption)
						if not isExistBcmWifi:
							self.encryptionType = getConfigListEntry(_("Encryption key type"), config.plugins.wlan.wepkeytype)
						self.encryptionKey = getConfigListEntry(_("Encryption key"), config.plugins.wlan.psk)
						if config.plugins.wlan.encryption.value != "Unencrypted":
							if config.plugins.wlan.encryption.value == "WEP":
								if not isExistBcmWifi:
									self.list.append(self.encryptionType)
							self.list.append(self.encryptionKey)
		self["config"].list = self.list

	def newConfig(self):
		if self["config"].getCurrent() in (self.InterfaceEntry, self.dhcpEntry, self.gatewayEntry, self.DNSConfigEntry, self.primaryDNSEntry, self.secondaryDNSEntry, self.ipTypeEntry):
			self.createSetup()
		if self["config"].getCurrent() == self.WakeOnWiFiEntry:
			iNetwork.onlyWoWifaces[self.iface] = self.onlyWakeOnWiFi.value
			open(BoxInfo.getItem("WakeOnLAN"), "w").write(BoxInfo.getItem("WakeOnLANType")[self.onlyWakeOnWiFi.value])
			self.createSetup()
		if iNetwork.isWirelessInterface(self.iface):
			if self["config"].getCurrent() == self.encryption:
				self.createSetup()

	def keyLeft(self):
		ConfigListScreen.keyLeft(self)
		self.newConfig()

	def keyRight(self):
		ConfigListScreen.keyRight(self)
		self.newConfig()

	def keySave(self):
		self.hideInputHelp()
		if self["config"].isChanged() or (BoxInfo.getItem("WakeOnLAN") and self.wolstartvalue != config.network.wol.value):
			self.session.openWithCallback(self.keySaveConfirm, MessageBox, ("%s\n\n%s" % (_("Are you sure you want to activate this network configuration?"), self.oktext)))
		else:
			if self.finished_cb:
				self.finished_cb()
			else:
				self.close("cancel")
		config.network.save()

	def keySaveConfirm(self, ret=False):
		if ret is True:
			num_configured_if = len(iNetwork.getConfiguredAdapters())
			if num_configured_if >= 1:
				if self.iface in iNetwork.getConfiguredAdapters() or (self.iface in iNetwork.onlyWoWifaces and iNetwork.onlyWoWifaces[self.iface] is True):
					self.applyConfig(True)
				else:
					self.session.openWithCallback(self.secondIfaceFoundCB, MessageBox, _("A second configured interface has been found.\n\nDo you want to disable the second network interface?"), default=True)
			else:
				self.applyConfig(True)
		else:
			self.keyCancel()

	def secondIfaceFoundCB(self, data):
		if data is False:
			self.applyConfig(True)
		else:
			configuredInterfaces = iNetwork.getConfiguredAdapters()
			for interface in configuredInterfaces:
				if interface == self.iface:
					continue
				iNetwork.setAdapterAttribute(interface, "up", False)
			iNetwork.deactivateInterface(configuredInterfaces, self.deactivateSecondInterfaceCB)

	def deactivateSecondInterfaceCB(self, data):
		if data is True:
			self.applyConfig(True)

	def applyConfig(self, ret=False):
		if ret is True:
			if self.getConfigMac and self.getConfigMac.isChanged():
				fileWriteLine("/etc/enigma2/hwmac", self.getConfigMac.value, source=MODULE_NAME)

			self.applyConfigRef = None
			iNetwork.setAdapterAttribute(self.iface, "ipv6", self.ipTypeConfigEntry.value)
			iNetwork.setAdapterAttribute(self.iface, "up", self.activateInterfaceEntry.value)
			iNetwork.setAdapterAttribute(self.iface, "dhcp", self.dhcpConfigEntry.value)
			iNetwork.setAdapterAttribute(self.iface, "ip", self.ipConfigEntry.value)
			iNetwork.setAdapterAttribute(self.iface, "netmask", self.netmaskConfigEntry.value)
			if self.hasGatewayConfigEntry.value:
				iNetwork.setAdapterAttribute(self.iface, "gateway", self.gatewayConfigEntry.value)
			else:
				iNetwork.removeAdapterAttribute(self.iface, "gateway")
			if self.extended is not None and self.configStrings is not None:
				iNetwork.setAdapterAttribute(self.iface, "configStrings", self.configStrings(self.iface))
				self.ws.writeConfig(self.iface)
			if self.activateInterfaceEntry.value is False and not (self.onlyWakeOnWiFi and self.onlyWakeOnWiFi.value is True):
				iNetwork.deactivateInterface(self.iface, self.deactivateInterfaceCB)
				iNetwork.writeNetworkConfig()
				self.applyConfigRef = self.session.openWithCallback(self.applyConfigfinishedCB, MessageBox, _("Please wait for activation of your network configuration..."), type=MessageBox.TYPE_INFO, enable_input=False)
			else:
				if self.oldInterfaceState is False:
					iNetwork.activateInterface(self.iface, self.deactivateInterfaceCB)
				else:
					iNetwork.deactivateInterface(self.iface, self.activateInterfaceCB)
				iNetwork.writeNetworkConfig()
				self.applyConfigRef = self.session.openWithCallback(self.applyConfigfinishedCB, MessageBox, _("Please wait for activation of your network configuration..."), type=MessageBox.TYPE_INFO, enable_input=False)
		else:
			self.keyCancel()

	def deactivateInterfaceCB(self, data):
		if data is True:
			self.applyConfigDataAvail(True)

	def activateInterfaceCB(self, data):
		if data is True:
			iNetwork.activateInterface(self.iface, self.applyConfigDataAvail)

	def applyConfigDataAvail(self, data):
		if data is True:
			iNetwork.getInterfaces(self.getInterfacesDataAvail)

	def getInterfacesDataAvail(self, data):
		if data is True:
			self.applyConfigRef.close(True)

	def applyConfigfinishedCB(self, data):
		if data is True:
			if self.finished_cb:
				self.session.openWithCallback(lambda x: self.finished_cb(), MessageBox, _("Your network configuration has been activated."), type=MessageBox.TYPE_INFO, timeout=10)
			else:
				self.session.openWithCallback(self.ConfigfinishedCB, MessageBox, _("Your network configuration has been activated."), type=MessageBox.TYPE_INFO, timeout=10)

	def ConfigfinishedCB(self, data):
		if data is not None and data is True:
			self.close("ok")

	def keyCancelConfirm(self, result):
		if not result:
			return
		if BoxInfo.getItem("WakeOnLAN"):
			config.network.wol.setValue(self.wolstartvalue)
		if self.oldInterfaceState is False:
			iNetwork.deactivateInterface(self.iface, self.keyCancelCB)
		else:
			self.close("cancel")

	def keyCancel(self):
		self.hideInputHelp()
		if self["config"].isChanged() or (BoxInfo.getItem("WakeOnLAN") and self.wolstartvalue != config.network.wol.value):
			self.session.openWithCallback(self.keyCancelConfirm, MessageBox, _("Really close without saving settings?"), default=False)
		else:
			self.close("cancel")

	def keyCancelCB(self, data):
		if data is not None and data is True:
			self.close("cancel")

	def runAsync(self, finished_cb):
		self.finished_cb = finished_cb
		self.keySave()

	def cleanup(self):
		iNetwork.stopLinkStateConsole()

	def hideInputHelp(self):
		current = self["config"].getCurrent()
		if current == self.wlanSSID:
			if current[1].help_window.instance is not None:
				current[1].help_window.instance.hide()
		elif current == self.encryptionKey and config.plugins.wlan.encryption.value != "Unencrypted":
			if current[1].help_window.instance is not None:
				current[1].help_window.instance.hide()

	def makeLineDnsNameservers(self, nameservers=[]):
		line = ""
		entry = " ".join([("%d.%d.%d.%d" % tuple(x)) for x in nameservers if x != [0, 0, 0, 0]])
		if len(entry):
			line = f"{line}\tdns-nameservers {entry}\n"
		return line


class AdapterSetupConfiguration(Screen):
	def __init__(self, session, iface):
		Screen.__init__(self, session, enableHelp=True)
		self.setTitle(_("Network Settings"))
		self.iface = iface
		self.LinkState = None
		self.onChangedEntry = []
		self.mainmenu = ""
		self["menulist"] = MenuList(self.mainmenu)
		self["key_red"] = StaticText(_("Close"))
		self["description"] = StaticText()
		self["IFtext"] = StaticText()
		self["IF"] = StaticText()
		self["Statustext"] = StaticText()
		self["statuspic"] = MultiPixmap()
		self["statuspic"].hide()
		self.oktext = _("Press OK on your remote control to continue.")
		self.reboottext = _("Your STB will restart after pressing OK on your remote control.")
		self.errortext = _("No working wireless network interface found.\n Please verify that you have attached a compatible WLAN device or enable your local network interface.")
		self.missingwlanplugintxt = _("The wireless LAN plugin is not installed!\nPlease install it.")
		self["actions"] = HelpableActionMap(self, ["NavigationActions", "ColorActions", "OkCancelActions"], {
			"cancel": (self.close, _("Exit network adapter setup menu")),
			"ok": (self.ok, _("Select menu entry")),
			"red": (self.close, _("Exit network adapter setup menu")),
			"top": (self["menulist"].goTop, _("Move to first line / screen")),
			"pageUp": (self["menulist"].goPageUp, _("Move up a screen")),
			"up": (self["menulist"].goLineUp, _("Move up a line")),
			# "left": (self.left, _("Move up to first entry")),
			# "right": (self.right, _("Move down to last entry")),
			"down": (self["menulist"].goLineDown, _("Move down a line")),
			"pageDown": (self["menulist"].goPageDown, _("Move down a screen")),
			"bottom": (self["menulist"].goBottom, _("Move to last line / screen"))
		}, prio=-2, description=_("Network Adapter Setting Actions"))
		self.updateStatusbar()
		self.onClose.append(self.cleanup)
		if self.selectionChanged not in self["menulist"].onSelectionChanged:
			self["menulist"].onSelectionChanged.append(self.selectionChanged)
		self.selectionChanged()

	def ok(self):
		self.cleanup()
		if self["menulist"].getCurrent()[1] == "edit":
			if iNetwork.isWirelessInterface(self.iface):
				try:
					from Plugins.SystemPlugins.WirelessLan.plugin import WlanScan  # noqa F401
				except ImportError:
					self.session.open(MessageBox, self.missingwlanplugintxt, type=MessageBox.TYPE_INFO, timeout=10)
				else:
					if queryWirelessDevice(self.iface):
						self.session.openWithCallback(self.AdapterSetupClosed, AdapterSetup, self.iface)
					else:
						self.showErrorMessage()	 # Display Wlan not available message.
			else:
				self.session.openWithCallback(self.AdapterSetupClosed, AdapterSetup, self.iface)
		if self["menulist"].getCurrent()[1] == "test":
			self.session.open(NetworkAdapterTest, self.iface)
		if self["menulist"].getCurrent()[1] == "dns":
			self.session.open(NameserverSetup)
		if self["menulist"].getCurrent()[1] == "scanwlan":
			try:
				from Plugins.SystemPlugins.WirelessLan.plugin import WlanScan
			except ImportError:
				self.session.open(MessageBox, self.missingwlanplugintxt, type=MessageBox.TYPE_INFO, timeout=10)
			else:
				if queryWirelessDevice(self.iface):
					self.session.openWithCallback(self.WlanScanClosed, WlanScan, self.iface)
				else:
					self.showErrorMessage()	 # Display Wlan not available message.
		if self["menulist"].getCurrent()[1] == "wlanstatus":
			try:
				from Plugins.SystemPlugins.WirelessLan.plugin import WlanStatus
			except ImportError:
				self.session.open(MessageBox, self.missingwlanplugintxt, type=MessageBox.TYPE_INFO, timeout=10)
			else:
				if queryWirelessDevice(self.iface):
					self.session.openWithCallback(self.WlanStatusClosed, WlanStatus, self.iface)
				else:
					self.showErrorMessage()	 # Display Wlan not available message.
		if self["menulist"].getCurrent()[1] == "lanrestart":
			self.session.openWithCallback(self.restartLan, MessageBox, "%s\n\n%s" % (_("Are you sure you want to restart your network interfaces?"), self.oktext))
		if self["menulist"].getCurrent()[1] == "openwizard":
			from Plugins.SystemPlugins.NetworkWizard.NetworkWizard import NetworkWizard
			self.session.openWithCallback(self.AdapterSetupClosed, NetworkWizard, self.iface)
		if self["menulist"].getCurrent()[1][0] == "extendedSetup":
			self.extended = self["menulist"].getCurrent()[1][2]
			self.extended(self.session, self.iface)

	def createSummary(self):
		from Screens.PluginBrowser import PluginBrowserSummary
		return PluginBrowserSummary

	def selectionChanged(self):
		if self["menulist"].getCurrent()[1] == "edit":
			self["description"].setText("%s\n\n%s" % (_("Edit the network configuration of your %s %s.") % getBoxDisplayName(), self.oktext))
		if self["menulist"].getCurrent()[1] == "test":
			self["description"].setText("%s\n\n%s" % (_("Test the network configuration of your %s %s.") % getBoxDisplayName(), self.oktext))
		if self["menulist"].getCurrent()[1] == "dns":
			self["description"].setText("%s\n\n%s" % (_("Edit the DNS configuration of your %s %s.") % getBoxDisplayName(), self.oktext))
		if self["menulist"].getCurrent()[1] == "scanwlan":
			self["description"].setText("%s\n\n%s" % (_("Scan your network for wireless access points and connect to them using your selected wireless device."), self.oktext))
		if self["menulist"].getCurrent()[1] == "wlanstatus":
			self["description"].setText("%s\n\n%s" % (_("Shows the state of your wireless LAN connection."), self.oktext))
		if self["menulist"].getCurrent()[1] == "lanrestart":
			self["description"].setText("%s\n\n%s" % (_("Restart your network connection and interfaces."), self.oktext))
		if self["menulist"].getCurrent()[1] == "openwizard":
			self["description"].setText("%s\n\n%s" % (_("Use the network wizard to configure your Network."), self.oktext))
		if self["menulist"].getCurrent()[1][0] == "extendedSetup":
			self["description"].setText("%s\n\n%s" % (_(self["menulist"].getCurrent()[1][1]), self.oktext))
		item = self["menulist"].getCurrent()
		if item:
			name = str(self["menulist"].getCurrent()[0])
			desc = self["description"].text
		else:
			name = ""
			desc = ""
		for cb in self.onChangedEntry:
			cb(name, desc)

	def updateStatusbar(self, data=None):
		self.mainmenu = self.genMainMenu()
		self["menulist"].l.setList(self.mainmenu)
		self["IFtext"].setText(_("Network:"))
		self["IF"].setText(iNetwork.getFriendlyAdapterName(self.iface))
		self["Statustext"].setText(_("Link:"))
		if iNetwork.isWirelessInterface(self.iface):
			try:
				from Plugins.SystemPlugins.WirelessLan.Wlan import iStatus
			except Exception:
				self["statuspic"].setPixmapNum(1)
				self["statuspic"].show()
			else:
				iStatus.getDataForInterface(self.iface, self.getInfoCB)
		else:
			iNetwork.getLinkState(self.iface, self.dataAvail)

	def doNothing(self):
		pass

	def genMainMenu(self):
		menu = [
			(_("Adapter Settings"), "edit"),
			(_("Nameserver settings"), "dns"),
			(_("Network test"), "test"),
			(_("Restart Network"), "lanrestart")
		]
		self.extended = None
		self.extendedSetup = None
		for p in plugins.getPlugins(PluginDescriptor.WHERE_NETWORKSETUP):
			callFnc = p.__call__["ifaceSupported"](self.iface)
			if callFnc is not None:
				self.extended = callFnc
				if "WlanPluginEntry" in p.__call__:  # Internally used only for WLAN Plugin.
					menu.append((_("Scan wireless networks"), "scanwlan"))
					if iNetwork.getAdapterAttribute(self.iface, "up"):
						menu.append((_("Show WLAN status"), "wlanstatus"))
				else:
					menuEntryName = p.__call__["menuEntryName"](self.iface) if "menuEntryName" in p.__call__ else _("Extended Setup...")
					menuEntryDescription = p.__call__["menuEntryDescription"](self.iface) if "menuEntryDescription" in p.__call__ else _("Extended Networksetup Plugin...")
					self.extendedSetup = ("extendedSetup", menuEntryDescription, self.extended)
					menu.append((menuEntryName, self.extendedSetup))
		if exists(resolveFilename(SCOPE_PLUGINS, "SystemPlugins/NetworkWizard/networkwizard.xml")):
			menu.append((_("Network Wizard"), "openwizard"))
		return menu

	def AdapterSetupClosed(self, *ret):
		if ret is not None and len(ret):
			if ret[0] == "ok" and (iNetwork.isWirelessInterface(self.iface) and iNetwork.getAdapterAttribute(self.iface, "up") is True):
				try:
					from Plugins.SystemPlugins.WirelessLan.plugin import WlanStatus
				except ImportError:
					self.session.open(MessageBox, self.missingwlanplugintxt, type=MessageBox.TYPE_INFO, timeout=10)
				else:
					if queryWirelessDevice(self.iface):
						self.session.openWithCallback(self.WlanStatusClosed, WlanStatus, self.iface)
					else:
						self.showErrorMessage()  # Display Wlan not available message.
			else:
				self.updateStatusbar()
		else:
			self.updateStatusbar()

	def WlanStatusClosed(self, *ret):
		if ret is not None and len(ret):
			from Plugins.SystemPlugins.WirelessLan.Wlan import iStatus
			iStatus.stopWlanConsole()
			self.updateStatusbar()
			if iNetwork.getAdapterAttribute(self.iface, "up") is True and self.iface in iNetwork.onlyWoWifaces and iNetwork.onlyWoWifaces[self.iface] is True:
				iNetwork.deactivateInterface(self.iface, self.deactivateInterfaceCB)

	def deactivateInterfaceCB(self, data):
		iNetwork.getInterfaces()

	def WlanScanClosed(self, *ret):
		if ret[0] is not None:
			self.session.openWithCallback(self.AdapterSetupClosed, AdapterSetup, self.iface, ret[0])
		else:
			from Plugins.SystemPlugins.WirelessLan.Wlan import iStatus
			iStatus.stopWlanConsole()
			self.updateStatusbar()

	def restartLan(self, ret=False):
		if ret is True:
			def restartfinishedCB():
				self.updateStatusbar()
				self.session.open(MessageBox, _("Finished configuring your network"), type=MessageBox.TYPE_INFO, timeout=10, default=False)
			RestartNetworkNew.start(callback=restartfinishedCB)

	def dataAvail(self, data):
		self.LinkState = None
		for line in data.splitlines():
			line = line.strip()
			if "Link detected:" in line:
				self.LinkState = "yes" in line
		if self.LinkState:
			iNetwork.checkNetworkState(self.checkNetworkCB)
		else:
			self["statuspic"].setPixmapNum(1)
			self["statuspic"].show()

	def showErrorMessage(self):
		self.session.open(MessageBox, self.errortext, type=MessageBox.TYPE_INFO, timeout=10)

	def cleanup(self):
		iNetwork.stopLinkStateConsole()
		iNetwork.stopDeactivateInterfaceConsole()
		iNetwork.stopActivateInterfaceConsole()
		iNetwork.stopPingConsole()
		try:
			from Plugins.SystemPlugins.WirelessLan.Wlan import iStatus
		except ImportError:
			pass
		else:
			iStatus.stopWlanConsole()

	def getInfoCB(self, data, status):
		self.LinkState = None
		if data is not None:
			if data is True:
				if status is not None:
					if status[self.iface]["essid"] == "off" or status[self.iface]["accesspoint"] == "Not-Associated" or status[self.iface]["accesspoint"] is False:
						self.LinkState = False
						self["statuspic"].setPixmapNum(1)
						self["statuspic"].show()
					else:
						self.LinkState = True
						iNetwork.checkNetworkState(self.checkNetworkCB)

	def checkNetworkCB(self, data):
		if iNetwork.getAdapterAttribute(self.iface, "up") is True:
			if self.LinkState is True:
				self["statuspic"].setPixmapNum(0 if data <= 2 else 1)
				self["statuspic"].show()
			else:
				self["statuspic"].setPixmapNum(1)
				self["statuspic"].show()
		else:
			self["statuspic"].setPixmapNum(1)
			self["statuspic"].show()


class NetworkAdapterTest(Screen):
	def __init__(self, session, iface):
		Screen.__init__(self, session)
		self.setTitle(_("Network Test"))
		self.iface = iface
		self.oldInterfaceState = iNetwork.getAdapterAttribute(self.iface, "up")
		self.setLabels()
		self.onClose.append(self.cleanup)
		self.onHide.append(self.cleanup)
		self["updown_actions"] = HelpableNumberActionMap(self, ["WizardActions", "ShortcutActions"], {
			"ok": self.KeyOK,
			"blue": self.KeyOK,
			"up": lambda: self.updownhandler("up"),
			"down": lambda: self.updownhandler("down")
		}, prio=-2, description=_("Network Adapter Text Actions"))
		self["updown_actions"].setEnabled(False)
		self["shortcuts"] = HelpableActionMap(self, ["ShortcutActions", "WizardActions"], {
			"red": self.cancel,
			"back": self.cancel
		}, prio=-2, description=_("Network Adapter Text Actions"))
		self["infoshortcuts"] = HelpableActionMap(self, ["ShortcutActions", "WizardActions"], {
			"red": self.closeInfo,
			"back": self.closeInfo
		}, prio=-2, description=_("Network Adapter Text Actions"))
		self["infoshortcuts"].setEnabled(False)
		self["shortcutsgreen"] = HelpableActionMap(self, ["ShortcutActions"], {
			"green": self.KeyGreen
		}, prio=-2, description=_("Network Adapter Text Actions"))
		self["shortcutsgreen_restart"] = HelpableActionMap(self, ["ShortcutActions"], {
			"green": self.KeyGreenRestart
		}, prio=-2, description=_("Network Adapter Text Actions"))
		self["shortcutsgreen_restart"].setEnabled(False)
		self["shortcutsyellow"] = HelpableActionMap(self, ["ShortcutActions"], {
			"yellow": self.KeyYellow,
		}, prio=-2, description=_("Network Adapter Text Actions"))
		self.onClose.append(self.delTimer)
		self.onLayoutFinish.append(self.layoutFinished)
		self.steptimer = False
		self.nextstep = 0
		self.activebutton = 0
		self.nextStepTimer = eTimer()
		self.nextStepTimer.callback.append(self.nextStepTimerFire)

	def cancel(self):
		if self.oldInterfaceState is False:
			iNetwork.setAdapterAttribute(self.iface, "up", self.oldInterfaceState)
			iNetwork.deactivateInterface(self.iface)
		self.close()

	def closeInfo(self):
		self["shortcuts"].setEnabled(True)
		self["infoshortcuts"].setEnabled(False)
		self["InfoText"].hide()
		self["InfoTextBorder"].hide()
		self["key_red"].setText(_("Close"))

	def delTimer(self):
		del self.steptimer
		del self.nextStepTimer

	def nextStepTimerFire(self):
		self.nextStepTimer.stop()
		self.steptimer = False
		self.runTest()

	def updownhandler(self, direction):
		if direction == "up":
			if self.activebutton >= 2:
				self.activebutton -= 1
			else:
				self.activebutton = 6
			self.setActiveButton(self.activebutton)
		if direction == "down":
			if self.activebutton <= 5:
				self.activebutton += 1
			else:
				self.activebutton = 1
			self.setActiveButton(self.activebutton)

	def setActiveButton(self, button):
		if button == 1:
			self["EditSettingsButton"].setPixmapNum(0)
			self["EditSettings_Text"].setForegroundColorNum(0)
			self["NetworkInfo"].setPixmapNum(0)
			self["NetworkInfo_Text"].setForegroundColorNum(1)
			self["AdapterInfo"].setPixmapNum(1)  # Active.
			self["AdapterInfo_Text"].setForegroundColorNum(2)  # Active.
		if button == 2:
			self["AdapterInfo_Text"].setForegroundColorNum(1)
			self["AdapterInfo"].setPixmapNum(0)
			self["DhcpInfo"].setPixmapNum(0)
			self["DhcpInfo_Text"].setForegroundColorNum(1)
			self["NetworkInfo"].setPixmapNum(1)  # Active.
			self["NetworkInfo_Text"].setForegroundColorNum(2)  # Active.
		if button == 3:
			self["NetworkInfo"].setPixmapNum(0)
			self["NetworkInfo_Text"].setForegroundColorNum(1)
			self["IPInfo"].setPixmapNum(0)
			self["IPInfo_Text"].setForegroundColorNum(1)
			self["DhcpInfo"].setPixmapNum(1)  # Active.
			self["DhcpInfo_Text"].setForegroundColorNum(2)  # Active.
		if button == 4:
			self["DhcpInfo"].setPixmapNum(0)
			self["DhcpInfo_Text"].setForegroundColorNum(1)
			self["DNSInfo"].setPixmapNum(0)
			self["DNSInfo_Text"].setForegroundColorNum(1)
			self["IPInfo"].setPixmapNum(1)  # Active.
			self["IPInfo_Text"].setForegroundColorNum(2)  # Active.
		if button == 5:
			self["IPInfo"].setPixmapNum(0)
			self["IPInfo_Text"].setForegroundColorNum(1)
			self["EditSettingsButton"].setPixmapNum(0)
			self["EditSettings_Text"].setForegroundColorNum(0)
			self["DNSInfo"].setPixmapNum(1)  # Active.
			self["DNSInfo_Text"].setForegroundColorNum(2)  # Active.
		if button == 6:
			self["DNSInfo"].setPixmapNum(0)
			self["DNSInfo_Text"].setForegroundColorNum(1)
			self["EditSettingsButton"].setPixmapNum(1)  # Active.
			self["EditSettings_Text"].setForegroundColorNum(2)  # Active.
			self["AdapterInfo"].setPixmapNum(0)
			self["AdapterInfo_Text"].setForegroundColorNum(1)

	def runTest(self):
		next = self.nextstep
		if next == 0:
			self.doStep1()
		elif next == 1:
			self.doStep2()
		elif next == 2:
			self.doStep3()
		elif next == 3:
			self.doStep4()
		elif next == 4:
			self.doStep5()
		elif next == 5:
			self.doStep6()
		self.nextstep += 1

	def doStep1(self):
		self.steptimer = True
		self.nextStepTimer.start(300)
		self["key_yellow"].setText(_("Stop test"))

	def doStep2(self):
		self["Adapter"].setText(iNetwork.getFriendlyAdapterName(self.iface))
		self["Adapter"].setForegroundColorNum(2)
		self["Adaptertext"].setForegroundColorNum(1)
		self["AdapterInfo_Text"].setForegroundColorNum(1)
		self["AdapterInfo_OK"].show()
		self.steptimer = True
		self.nextStepTimer.start(300)

	def doStep3(self):
		self["Networktext"].setForegroundColorNum(1)
		self["Network"].setText(_("Please wait..."))
		self.getLinkState(self.iface)
		self["NetworkInfo_Text"].setForegroundColorNum(1)
		self.steptimer = True
		self.nextStepTimer.start(1000)

	def doStep4(self):
		self["Dhcptext"].setForegroundColorNum(1)
		if iNetwork.getAdapterAttribute(self.iface, "dhcp") is True:
			self["Dhcp"].setForegroundColorNum(2)
			self["Dhcp"].setText(_("enabled"))
			self["DhcpInfo_Check"].setPixmapNum(0)
		else:
			self["Dhcp"].setForegroundColorNum(1)
			self["Dhcp"].setText(_("disabled"))
			self["DhcpInfo_Check"].setPixmapNum(1)
		self["DhcpInfo_Check"].show()
		self["DhcpInfo_Text"].setForegroundColorNum(1)
		self.steptimer = True
		self.nextStepTimer.start(1000)

	def doStep5(self):
		self["IPtext"].setForegroundColorNum(1)
		self["IP"].setText(_("Please wait..."))
		iNetwork.checkNetworkState(self.NetworkStatedataAvail)

	def doStep6(self):
		self.steptimer = False
		self.nextStepTimer.stop()
		self["DNStext"].setForegroundColorNum(1)
		self["DNS"].setText(_("Please wait..."))
		iNetwork.checkDNSLookup(self.DNSLookupdataAvail)

	def KeyGreen(self):
		self["shortcutsgreen"].setEnabled(False)
		self["shortcutsyellow"].setEnabled(True)
		self["updown_actions"].setEnabled(False)
		self["key_yellow"].setText("")
		self["key_green"].setText("")
		self.steptimer = True
		self.nextStepTimer.start(1000)

	def KeyGreenRestart(self):
		self.nextstep = 0
		self.layoutFinished()
		self["Adapter"].setText("")
		self["Network"].setText("")
		self["Dhcp"].setText("")
		self["IP"].setText("")
		self["DNS"].setText("")
		self["AdapterInfo_Text"].setForegroundColorNum(0)
		self["NetworkInfo_Text"].setForegroundColorNum(0)
		self["DhcpInfo_Text"].setForegroundColorNum(0)
		self["IPInfo_Text"].setForegroundColorNum(0)
		self["DNSInfo_Text"].setForegroundColorNum(0)
		self["shortcutsgreen_restart"].setEnabled(False)
		self["shortcutsgreen"].setEnabled(False)
		self["shortcutsyellow"].setEnabled(True)
		self["updown_actions"].setEnabled(False)
		self["key_yellow"].setText("")
		self["key_green"].setText("")
		self.steptimer = True
		self.nextStepTimer.start(1000)

	def KeyOK(self):
		self["infoshortcuts"].setEnabled(True)
		self["shortcuts"].setEnabled(False)
		if self.activebutton == 1:  # Adapter check.
			self["InfoText"].setText(_("This test detects your configured LAN adapter."))
			self["InfoTextBorder"].show()
			self["InfoText"].show()
			self["key_red"].setText(_("Back"))
		if self.activebutton == 2:  # LAN check.
			self["InfoText"].setText(_("This test checks whether a network cable is connected to your LAN adapter.\nIf you get a \"disconnected\" message:\n- verify that a network cable is attached\n- verify that the cable is not broken"))
			self["InfoTextBorder"].show()
			self["InfoText"].show()
			self["key_red"].setText(_("Back"))
		if self.activebutton == 3:  # DHCP check.
			self["InfoText"].setText(_("This test checks whether your LAN adapter is set up for automatic IP address configuration with DHCP.\nIf you get a \"disabled\" message:\n - then your LAN adapter is configured for manual IP setup\n- verify that you have entered correct IP information in the adapter setup dialog.\nIf you get an \"enabled\" message:\n-verify that you have a configured and working DHCP server in your network."))
			self["InfoTextBorder"].show()
			self["InfoText"].show()
			self["key_red"].setText(_("Back"))
		if self.activebutton == 4:  # IP check.
			self["InfoText"].setText(_("This test checks whether a valid IP address is found for your LAN adapter.\nIf you get a \"unconfirmed\" message:\n- no valid IP address was found\n- please check your DHCP, cabling and adapter setup"))
			self["InfoTextBorder"].show()
			self["InfoText"].show()
			self["key_red"].setText(_("Back"))
		if self.activebutton == 5:  # DNS check.
			self["InfoText"].setText(_("This test checks for configured DNS.\nIf you get an \"unconfirmed\" message:\n- please check your DHCP, cabling and adapter setup\n- if you configured your nameservers manually please verify your entries in the \"Nameserver\" configuration"))
			self["InfoTextBorder"].show()
			self["InfoText"].show()
			self["key_red"].setText(_("Back"))
		if self.activebutton == 6:  # Edit settings.
			self.session.open(AdapterSetup, self.iface)

	def KeyYellow(self):
		self.nextstep = 0
		self["shortcutsgreen_restart"].setEnabled(True)
		self["shortcutsgreen"].setEnabled(False)
		self["shortcutsyellow"].setEnabled(False)
		self["key_green"].setText(_("Restart test"))
		self["key_yellow"].setText("")
		self.steptimer = False
		self.nextStepTimer.stop()

	def layoutFinished(self):
		self.setTitle("%s %s" % (_("Network Test:"), iNetwork.getFriendlyAdapterName(self.iface)))
		self["shortcutsyellow"].setEnabled(False)
		self["AdapterInfo_OK"].hide()
		self["NetworkInfo_Check"].hide()
		self["DhcpInfo_Check"].hide()
		self["IPInfo_Check"].hide()
		self["DNSInfo_Check"].hide()
		self["EditSettings_Text"].hide()
		self["EditSettingsButton"].hide()
		self["InfoText"].hide()
		self["InfoTextBorder"].hide()
		self["key_yellow"].setText("")

	def setLabels(self):
		self["Adaptertext"] = MultiColorLabel(_("LAN adapter"))
		self["Adapter"] = MultiColorLabel()
		self["AdapterInfo"] = MultiPixmap()
		self["AdapterInfo_Text"] = MultiColorLabel(_("Show info"))
		self["AdapterInfo_OK"] = Pixmap()
		if self.iface in iNetwork.wlan_interfaces:
			self["Networktext"] = MultiColorLabel(_("Wireless network"))
		else:
			self["Networktext"] = MultiColorLabel(_("Local network"))
		self["Network"] = MultiColorLabel()
		self["NetworkInfo"] = MultiPixmap()
		self["NetworkInfo_Text"] = MultiColorLabel(_("Show info"))
		self["NetworkInfo_Check"] = MultiPixmap()
		self["Dhcptext"] = MultiColorLabel(_("DHCP"))
		self["Dhcp"] = MultiColorLabel()
		self["DhcpInfo"] = MultiPixmap()
		self["DhcpInfo_Text"] = MultiColorLabel(_("Show info"))
		self["DhcpInfo_Check"] = MultiPixmap()
		self["IPtext"] = MultiColorLabel(_("IP address"))
		self["IP"] = MultiColorLabel()
		self["IPInfo"] = MultiPixmap()
		self["IPInfo_Text"] = MultiColorLabel(_("Show info"))
		self["IPInfo_Check"] = MultiPixmap()
		self["DNStext"] = MultiColorLabel(_("Nameserver"))
		self["DNS"] = MultiColorLabel()
		self["DNSInfo"] = MultiPixmap()
		self["DNSInfo_Text"] = MultiColorLabel(_("Show info"))
		self["DNSInfo_Check"] = MultiPixmap()
		self["EditSettings_Text"] = MultiColorLabel(_("Edit settings"))
		self["EditSettingsButton"] = MultiPixmap()
		self["key_red"] = StaticText(_("Close"))
		self["key_green"] = StaticText(_("Start test"))
		self["key_yellow"] = StaticText(_("Stop test"))
		self["InfoTextBorder"] = Pixmap()
		self["InfoText"] = Label()

	def getLinkState(self, iface):
		if iface in iNetwork.wlan_interfaces:
			try:
				from Plugins.SystemPlugins.WirelessLan.Wlan import iStatus
			except Exception:
				self["Network"].setForegroundColorNum(1)
				self["Network"].setText(_("disconnected"))
				self["NetworkInfo_Check"].setPixmapNum(1)
				self["NetworkInfo_Check"].show()
			else:
				iStatus.getDataForInterface(self.iface, self.getInfoCB)
		else:
			iNetwork.getLinkState(iface, self.LinkStatedataAvail)

	def LinkStatedataAvail(self, data):
		for item in data.splitlines():
			if "Link detected:" in item:
				if "yes" in item:
					self["Network"].setForegroundColorNum(2)
					self["Network"].setText(_("connected"))
					self["NetworkInfo_Check"].setPixmapNum(0)
				else:
					self["Network"].setForegroundColorNum(1)
					self["Network"].setText(_("disconnected"))
					self["NetworkInfo_Check"].setPixmapNum(1)
				break
		else:
			self["Network"].setText(_("unknown"))
		self["NetworkInfo_Check"].show()

	def NetworkStatedataAvail(self, data):
		if "IP" in self:
			if data <= 2:
				self["IP"].setForegroundColorNum(2)
				self["IP"].setText(_("confirmed"))
				self["IPInfo_Check"].setPixmapNum(0)
			else:
				self["IP"].setForegroundColorNum(1)
				self["IP"].setText(_("unconfirmed"))
				self["IPInfo_Check"].setPixmapNum(1)
			self["IPInfo_Check"].show()
			self["IPInfo_Text"].setForegroundColorNum(1)
			self.steptimer = True
			self.nextStepTimer.start(300)

	def DNSLookupdataAvail(self, data):
		if "DNS" in self:
			if data <= 2:
				self["DNS"].setForegroundColorNum(2)
				self["DNS"].setText(_("confirmed"))
				self["DNSInfo_Check"].setPixmapNum(0)
			else:
				self["DNS"].setForegroundColorNum(1)
				self["DNS"].setText(_("unconfirmed"))
				self["DNSInfo_Check"].setPixmapNum(1)
			self["DNSInfo_Check"].show()
			self["DNSInfo_Text"].setForegroundColorNum(1)
			self["EditSettings_Text"].show()
			self["EditSettingsButton"].setPixmapNum(1)
			self["EditSettings_Text"].setForegroundColorNum(2)  # Active.
			self["EditSettingsButton"].show()
			self["key_yellow"].setText("")
			self["key_green"].setText(_("Restart test"))
			self["shortcutsgreen"].setEnabled(False)
			self["shortcutsgreen_restart"].setEnabled(True)
			self["shortcutsyellow"].setEnabled(False)
			self["updown_actions"].setEnabled(True)
			self.activebutton = 6

	def getInfoCB(self, data, status):
		if data is not None:
			if data is True:
				if status is not None:
					if status[self.iface]["essid"] == "off" or status[self.iface]["accesspoint"] == "Not-Associated" or status[self.iface]["accesspoint"] is False:
						self["Network"].setForegroundColorNum(1)
						self["Network"].setText(_("disconnected"))
						self["NetworkInfo_Check"].setPixmapNum(1)
						self["NetworkInfo_Check"].show()
					else:
						self["Network"].setForegroundColorNum(2)
						self["Network"].setText(_("connected"))
						self["NetworkInfo_Check"].setPixmapNum(0)
						self["NetworkInfo_Check"].show()

	def cleanup(self):
		iNetwork.stopLinkStateConsole()
		iNetwork.stopDNSConsole()
		try:
			from Plugins.SystemPlugins.WirelessLan.Wlan import iStatus
		except ImportError:
			pass
		else:
			iStatus.stopWlanConsole()


class NetworkDaemons:
	def __init__(self):
		fileDom = fileReadXML(resolveFilename(SCOPE_SKINS, "networkdaemons.xml"), source=MODULE_NAME)
		self.__daemons = []
		for daemon in fileDom.findall("daemon"):
			daemondict = {}
			for key in ("key", "title", "installcheck", "package", "autostart", "autostartservice", "autostartprio", "running", "startservice", "logpath"):
				daemondict[key] = daemon.get(key, "")
			if daemondict["key"] and daemondict["title"]:
				daemondict["isinstalled"] = daemondict["installcheck"] == "" or exists(daemondict["installcheck"])
				daemondict["isservice"] = daemondict["startservice"] != ""
				self.__daemons.append(daemondict)

	def getDaemons(self):
		return self.__daemons


class NetworkServicesSetup(Setup, NetworkDaemons):
	def __init__(self, session):
		NetworkDaemons.__init__(self)
		self.serviceItems = []
		self.serviceIsRunning = {}
		Setup.__init__(self, session, "NetworkServicesSetup")
		self["key_yellow"] = StaticText()
		self["key_blue"] = StaticText()
		self["startStopActions"] = HelpableActionMap(self, ["ColorActions"], {
			"yellow": (self.toggleStartStop, _("Start or Stop service"))
		}, prio=0, description=_("Network Setup Actions"))
		self["showLogActions"] = HelpableActionMap(self, ["ColorActions"], {
			"blue": (self.showLog, _("Show Log"))
		}, prio=0, description=_("Network Setup Actions"))
		self.console = Console()
		self.opkgComponent = OpkgComponent()
		self.opkgComponent.addCallback(self.opkgCallback)

	def getRunningStatus(self):
		self.serviceIsRunning = {}
		processlist = ProcessList()
		for daemon in self.getDaemons():
			if daemon["isservice"]:
				self.serviceIsRunning[daemon["key"]] = False
				for runningService in daemon["running"].split(","):
					if str(processlist.named(runningService)).strip("[]"):
						self.serviceIsRunning[daemon["key"]] = True
						break

	def getService(self, daemon):
		choices = []
		checkFile = daemon["installcheck"]
		autoStartCheck = daemon["autostart"]
		title = daemon["title"]
		if checkFile:
			if exists(checkFile):
				choices.append((2, _("Uninstall")))
				if not autoStartCheck:
					choices.append((3, _("Installed")))
					default = 3
			else:
				choices.append((2, _("Not Installed")))
				choices.append((3, _("Install")))
				default = 2
				autoStartCheck = False
		if autoStartCheck:
			default = 0 if glob(autoStartCheck) else 1
			if default == 0:
				choices.append((0, _("Enabled")))
				choices.append((1, _("Disable")))
			else:
				choices.append((0, _("Enable")))
				choices.append((1, _("Disabled")))

		cfg = ConfigSelection(default=default, choices=choices)
		return (title, cfg, _("Select the action for '%s'") % title, daemon)

	def createSetup(self):  # NOSONAR silence S2638
		if not self.serviceItems:
			for daemon in self.getDaemons():
				self.serviceItems.append(self.getService(daemon))
			self.getRunningStatus()
		Setup.createSetup(self, appendItems=self.serviceItems)

	def selectionChanged(self):
		current = self["config"].getCurrent()
		if current:
			daemon = current[3]
			isInstalled = daemon["isinstalled"]
			isRunning = self.serviceIsRunning.get(daemon["key"], None)
			if isInstalled and isRunning is not None:
				cmd = _("Stop") if isRunning else _("Start")
				self["key_yellow"].setText(cmd)
				self["startStopActions"].setEnabled(True)
			else:
				self["key_yellow"].setText("")
				self["startStopActions"].setEnabled(False)
			logPath = daemon["logpath"] and isInstalled
			self["key_blue"].setText(_("Show Log") if logPath else "")
			self["showLogActions"].setEnabled(logPath != "")

			Setup.selectionChanged(self)
			installed = _("Installed") if isInstalled else _("Not Installed")
			if isRunning is not None:
				running = _("Running") if isRunning else _("Not running")
				footnote = f"{_('Current Status:')} {installed} / {running}"
			else:
				footnote = f"{_('Current Status:')} {installed}"
			self.setFootnote(footnote)

	def toggleStartStop(self):
		def toggleStartStopCallback(result=None, retval=None, extra_args=None):
			self.getRunningStatus()
			self.selectionChanged()
			Processing.instance.hideProgress()

		current = self["config"].getCurrent()
		if current:
			daemon = current[3]
			if daemon["isservice"]:
				isRunning = self.serviceIsRunning.get(daemon["key"], None)
				service = daemon["startservice"]
				cmd = "stop" if isRunning else "start"
				self.showProgress()
				commands = [f"/etc/init.d/{service} {cmd}"]
				if daemon["key"] == "sambas":
					commands = [f"/etc/init.d/wsdd {cmd}"]
					if isRunning:
						commands.append("killall nmbd")
						commands.append("killall smbd")
				self.showProgress()
				self.console.eBatch(commands, toggleStartStopCallback, debug=True)

	def showLog(self):
		current = self["config"].getCurrent()
		if current:
			self.session.open(NetworkLogScreen, title=_("Log"), logPath=current[3]["logpath"])

	def showProgress(self, text=""):
		Processing.instance.setDescription(text or _("Please wait..."))
		Processing.instance.showProgress(endless=True)

	def opkgCallback(self, event, parameter):
		def configureCallback(result=None, retval=None, extra_args=None):
			Processing.instance.hideProgress()
			Setup.keySave(self)
		if event == self.opkgComponent.EVENT_REMOVE_DONE and self.installPackages:
			self.showProgress(_("Installing Service"))
			self.opkgComponent.runCommand(self.opkgComponent.CMD_REFRESH_INSTALL, {"arguments": self.installPackages})
		elif event in (self.opkgComponent.EVENT_REMOVE_DONE, self.opkgComponent.EVENT_INSTALL_DONE):
			if self.cmdList:
				self.showProgress(_("Configuring Service"))
				self.console.eBatch(self.cmdList, configureCallback, debug=True)
			else:
				configureCallback()

	def keySave(self):
		self.installPackages = []
		self.removePackages = []
		self.cmdList = []
		for item in self["config"].list:
			if len(item) > 1 and item[1].isChanged():
				daemon = item[3]
				if item[1].value == 2:  # remove
					self.removePackages.append(daemon["package"])
				elif item[1].value == 3:  # install
					self.installPackages.append(daemon["package"])
				elif item[1].value == 0:  # autostart on
					autostartprio = daemon["autostartprio"]
					cmd = f"defaults {autostartprio}" if autostartprio else "defaults"
					autostartservice = daemon["autostartservice"]
					self.cmdList.append(f"update-rc.d -f {autostartservice} {cmd}")
				elif item[1].value == 1:  # autostart off
					autostartservice = daemon["autostartservice"]
					self.cmdList.append(f"update-rc.d -f {autostartservice} remove")
			item[1].cancel()

		if self.removePackages:
			self.showProgress(_("Removing Service"))
			args = {
				"arguments": self.removePackages,
				"options": {"remove": ["--force-remove", "--autoremove"]}
			}
			self.opkgComponent.runCommand(self.opkgComponent.CMD_REMOVE, args)
		elif self.installPackages:
			self.opkgCallback(self.opkgComponent.EVENT_REMOVE_DONE, "")
		elif self.cmdList:
			self.opkgCallback(self.opkgComponent.EVENT_INSTALL_DONE, "")
		else:
			Setup.keySave(self)


class NetworkInadynSetup(Setup):
	def __init__(self, session):
		self.ina_user = NoSave(ConfigText(fixed_size=False))
		self.ina_pass = NoSave(ConfigText(fixed_size=False))
		self.ina_alias = NoSave(ConfigText(fixed_size=False))
		self.ina_period = NoSave(ConfigNumber())
		self.ina_sysactive = NoSave(ConfigYesNo(default=False))
		choices = [(x, x) for x in ("dyndns@dyndns.org", "statdns@dyndns.org", "custom@dyndns.org", "default@no-ip.com")]
		self.ina_system = NoSave(ConfigSelection(default="dyndns@dyndns.org", choices=choices))
		Setup.__init__(self, session, "NetworkInadynSetup")

	def changedEntry(self):
		pass  # No actions needed

	def createSetup(self):  # NOSONAR silence S2638
		inadynItems = []
		lines = fileReadLines("/etc/inadyn.conf", source=MODULE_NAME)
		if lines:
			for line in lines:
				if line.startswith("username "):
					line = line[9:]
					self.ina_user.value = line
					ina_user1 = getConfigListEntry("%s:" % _("Username"), self.ina_user)
					inadynItems.append(ina_user1)
				elif line.startswith("password "):
					line = line[9:]
					self.ina_pass.value = line
					ina_pass1 = getConfigListEntry("%s:" % _("Password"), self.ina_pass)
					inadynItems.append(ina_pass1)
				elif line.startswith("alias "):
					line = line[6:]
					self.ina_alias.value = line
					ina_alias1 = getConfigListEntry("%s:" % _("Alias"), self.ina_alias)
					inadynItems.append(ina_alias1)
				elif line.startswith("update_period_sec "):
					line = line[18:]
					line = (int(line) // 60)
					self.ina_period.value = line
					ina_period1 = getConfigListEntry("%s:" % _("Time update in minutes"), self.ina_period)
					inadynItems.append(ina_period1)
				elif line.startswith("dyndns_system ") or line.startswith("#dyndns_system "):
					if not line.startswith("#"):
						self.ina_sysactive.value = True
						line = line[14:]
					else:
						self.ina_sysactive.value = False
						line = line[15:]
					ina_sysactive1 = getConfigListEntry("%s:" % _("Set system"), self.ina_sysactive)
					inadynItems.append(ina_sysactive1)
					self.ina_value = line
					ina_system1 = getConfigListEntry("%s:" % _("System"), self.ina_system)
					inadynItems.append(ina_system1)
		Setup.createSetup(self, appendItems=inadynItems)
		self.setTitle(_("Inadyn Settings"))

	def keySave(self):
		oldLines = fileReadLines("/etc/inadyn.conf", source=MODULE_NAME)
		if oldLines:
			newLines = []
			for line in oldLines:
				if line.startswith("username "):
					line = f"username {self.ina_user.value.strip()}"
				elif line.startswith("password "):
					line = f"password {self.ina_pass.value.strip()}"
				elif line.startswith("alias "):
					line = f"alias {self.ina_alias.value.strip()}"
				elif line.startswith("update_period_sec "):
					strview = self.ina_period.value * 60
					line = f"update_period_sec {str(strview)}"
				elif line.startswith("dyndns_system ") or line.startswith("#dyndns_system "):
					line = f"{'' if self.ina_sysactive.value else '#'}dyndns_system {self.ina_system.value.strip()}"
				newLines.append(line)
			fileWriteLines("/etc/inadyn.conf.tmp", newLines)
		else:
			self.session.open(MessageBox, _("Sorry Inadyn Config is Missing"), MessageBox.TYPE_INFO)
			self.close()
		if exists("/etc/inadyn.conf.tmp"):
			rename("/etc/inadyn.conf.tmp", "/etc/inadyn.conf")
		self.close()


class NetworkuShareSetup(Setup):
	def __init__(self, session):
		self.ushare_user = NoSave(ConfigText(default=BoxInfo.getItem("machinebuild"), fixed_size=False))
		self.ushare_iface = NoSave(ConfigText(fixed_size=False))
		self.ushare_port = NoSave(ConfigNumber())
		self.ushare_telnetport = NoSave(ConfigNumber())
		self.ushare_web = NoSave(ConfigYesNo(default=True))
		self.ushare_telnet = NoSave(ConfigYesNo(default=True))
		self.ushare_xbox = NoSave(ConfigYesNo(default=True))
		self.ushare_ps3 = NoSave(ConfigYesNo(default=True))
		choices = [(x, x) for x in ("dyndns@dyndns.org", "statdns@dyndns.org", "custom@dyndns.org", "default@no-ip.com")]
		self.ushare_system = NoSave(ConfigSelection(default="dyndns@dyndns.org", choices=choices))
		self.selectedFiles = []
		Setup.__init__(self, session, "NetworkuShareSetup")
		self["key_yellow"] = StaticText(_("Shares"))
		self["selectSharesActions"] = HelpableActionMap(self, ["ColorActions"], {
			"yellow": (self.selectShares, _("Select Shares"))
		}, prio=0, description=_("Network Setup Actions"))

	def changedEntry(self):
		pass  # No actions needed

	def createSetup(self):  # NOSONAR silence S2638
		ushareItems = []
		lines = fileReadLines("/etc/ushare.conf", source=MODULE_NAME)
		if lines:
			for line in lines:
				line = line.strip()
				if line.startswith("USHARE_NAME="):
					line = line[12:]
					self.ushare_user.value = line
					ushare_user1 = getConfigListEntry("%s:" % _("uShare Name"), self.ushare_user)
					ushareItems.append(ushare_user1)
				elif line.startswith("USHARE_IFACE="):
					line = line[13:]
					self.ushare_iface.value = line
					ushare_iface1 = getConfigListEntry("%s:" % _("Interface"), self.ushare_iface)
					ushareItems.append(ushare_iface1)
				elif line.startswith("USHARE_PORT="):
					line = line[12:]
					self.ushare_port.value = line
					ushare_port1 = getConfigListEntry("%s:" % _("uShare Port"), self.ushare_port)
					ushareItems.append(ushare_port1)
				elif line.startswith("USHARE_TELNET_PORT="):
					line = line[19:]
					self.ushare_telnetport.value = line
					ushare_telnetport1 = getConfigListEntry("%s:" % _("Telnet Port"), self.ushare_telnetport)
					ushareItems.append(ushare_telnetport1)
				elif line.startswith("ENABLE_WEB="):
					self.ushare_web.value = line.endswith("yes")
					ushare_web1 = getConfigListEntry("%s:" % _("Web Interface"), self.ushare_web)
					ushareItems.append(ushare_web1)
				elif line.startswith("ENABLE_TELNET="):
					self.ushare_telnet.value = line.endswith("yes")
					ushare_telnet1 = getConfigListEntry("%s:" % _("Telnet Interface"), self.ushare_telnet)
					ushareItems.append(ushare_telnet1)
				elif line.startswith("ENABLE_XBOX="):
					self.ushare_xbox.value = line.endswith("yes")
					ushare_xbox1 = getConfigListEntry("%s:" % _("XBox 360 support"), self.ushare_xbox)
					ushareItems.append(ushare_xbox1)
				elif line.startswith("ENABLE_DLNA="):
					self.ushare_ps3.value = line.endswith("yes")
					ushare_ps31 = getConfigListEntry("%s:" % _("DLNA support"), self.ushare_ps3)
					ushareItems.append(ushare_ps31)
				elif line.startswith("USHARE_DIR="):
					line = line[11:]
					self.selectedFiles = [str(n) for n in line.split(", ")]
		Setup.createSetup(self, appendItems=ushareItems)
		self.setTitle(_("uShare Settings"))

	def keySave(self):
		def getYesNo(configItem):
			return "yes" if configItem.value else "no"
		oldLines = fileReadLines("/etc/ushare.conf", source=MODULE_NAME)
		if oldLines:
			newLines = []
			for line in oldLines:
				if line.startswith("USHARE_NAME="):
					line = f"USHARE_NAME={self.ushare_user.value.strip()}"
				elif line.startswith("USHARE_IFACE="):
					line = f"USHARE_IFACE={self.ushare_iface.value.strip()}"
				elif line.startswith("USHARE_PORT="):
					line = f"USHARE_PORT={str(self.ushare_port.value)}"
				elif line.startswith("USHARE_TELNET_PORT="):
					line = f"USHARE_TELNET_PORT={str(self.ushare_telnetport.value)}"
				elif line.startswith("USHARE_DIR="):
					line = ("USHARE_DIR=%s" % ", ".join(self.selectedFiles))
				elif line.startswith("ENABLE_WEB="):
					line = f"ENABLE_WEB={getYesNo(self.ushare_web.value)}"
				elif line.startswith("ENABLE_TELNET="):
					line = f"ENABLE_TELNET={getYesNo(self.ushare_telnet.value)}"
				elif line.startswith("ENABLE_XBOX="):
					line = f"ENABLE_XBOX={getYesNo(self.ushare_xbox.value)}"
				elif line.startswith("ENABLE_DLNA="):
					line = f"ENABLE_DLNA={getYesNo(self.ushare_ps3.value)}"
				newLines.append(line)
			fileWriteLines("/etc/ushare.conf.tmp", newLines)
		else:
			self.session.open(MessageBox, _("Sorry uShare Config is Missing"), MessageBox.TYPE_INFO)
			self.close()
		if exists("/etc/ushare.conf.tmp"):
			rename("/etc/ushare.conf.tmp", "/etc/ushare.conf")
		self.close()

	def selectShares(self):
		def selectSharesCallBack(selectedFiles):
			if selectedFiles:
				self.selectedFiles = selectedFiles
		self.session.openWithCallback(selectSharesCallBack, uShareSelection, self.selectedFiles)


class uShareSelection(Screen):
	def __init__(self, session, selectedFiles):
		Screen.__init__(self, session)
		self.setTitle(_("Select Folders"))
		self["key_red"] = StaticText(_("Cancel"))
		self["key_green"] = StaticText(_("Save"))
		self["key_yellow"] = StaticText()
		self.selectedFiles = selectedFiles
		defaultDir = "/media/"
		self.filelist = MultiFileSelectList(self.selectedFiles, defaultDir, showFiles=False)
		self["checkList"] = self.filelist
		self["actions"] = HelpableActionMap(self, ["NavigationActions", "OkCancelActions", "ColorActions"], {
			"ok": self.keyOk,
			"cancel": self.exit,
			"red": self.exit,
			"green": self.keyGreen,
			"yellow": self.keyYellow,
			"top": (self["checkList"].goTop, _("Move to first line / screen")),
			"pageUp": (self["checkList"].goPageUp, _("Move up a screen")),
			"up": (self["checkList"].goLineUp, _("Move up a line")),
			# "left": (self.left, _("Move up to first entry")),
			# "right": (self.right, _("Move down to last entry")),
			"down": (self["checkList"].goLineDown, _("Move down a line")),
			"pageDown": (self["checkList"].goPageDown, _("Move down a screen")),
			"bottom": (self["checkList"].goBottom, _("Move to last line / screen"))
		}, prio=-1, description=_("uShare Selection Actions"))
		if self.selectionChanged not in self["checkList"].onSelectionChanged:
			self["checkList"].onSelectionChanged.append(self.selectionChanged)
		self.onLayoutFinish.append(self.layoutFinished)

	def layoutFinished(self):
		idx = 0
		self["checkList"].moveToIndex(idx)
		self.selectionChanged()

	def selectionChanged(self):
		current = self["checkList"].getCurrent()[0]
		self["key_yellow"].setText(_("Deselect") if current[2] is True else _("Select"))

	def keyYellow(self):
		self["checkList"].changeSelectionState()
		self.selectedFiles = self["checkList"].getSelectedList()

	def keyGreen(self):
		self.selectedFiles = self["checkList"].getSelectedList()
		self.close(self.selectedFiles)

	def exit(self):
		self.close(None)

	def keyOk(self):
		if self.filelist.canDescent():
			self.filelist.descent()


class NetworkMiniDLNASetup(Setup):
	def __init__(self, session):
		self.selectedFiles = []
		self.minidlna_name = NoSave(ConfigText(default=BoxInfo.getItem("machinebuild"), fixed_size=False))
		self.minidlna_iface = NoSave(ConfigText(fixed_size=False))
		self.minidlna_port = NoSave(ConfigNumber())
		self.minidlna_serialno = NoSave(ConfigNumber())
		self.minidlna_web = NoSave(ConfigYesNo(default=True))
		self.minidlna_inotify = NoSave(ConfigYesNo(default=True))
		self.minidlna_tivo = NoSave(ConfigYesNo(default=True))
		self.minidlna_strictdlna = NoSave(ConfigYesNo(default=True))
		Setup.__init__(self, session, "NetworkMiniDLNASetup")
		self["key_yellow"] = StaticText(_("Shares"))
		self["selectSharesActions"] = HelpableActionMap(self, ["ColorActions"], {
			"yellow": (self.selectShares, _("Select Shares"))
		}, prio=0, description=_("Network Setup Actions"))

	def changedEntry(self):
		pass  # No actions needed

	def createSetup(self):  # NOSONAR silence S2638
		minidlnaItems = []
		lines = fileReadLines("/etc/minidlna.conf", source=MODULE_NAME)
		if lines:
			for line in lines:
				line = line.strip()
				if line.startswith("friendly_name="):
					line = line[14:]
					self.minidlna_name.value = line
					minidlna_name1 = getConfigListEntry("%s:" % _("Name"), self.minidlna_name)
					minidlnaItems.append(minidlna_name1)
				elif line.startswith("network_interface="):
					line = line[18:]
					self.minidlna_iface.value = line
					minidlna_iface1 = getConfigListEntry("%s:" % _("Interface"), self.minidlna_iface)
					minidlnaItems.append(minidlna_iface1)
				elif line.startswith("port="):
					line = line[5:]
					self.minidlna_port.value = line
					minidlna_port1 = getConfigListEntry("%s:" % _("Port"), self.minidlna_port)
					minidlnaItems.append(minidlna_port1)
				elif line.startswith("serial="):
					line = line[7:]
					self.minidlna_serialno.value = line
					minidlna_serialno1 = getConfigListEntry("%s:" % _("Serial No"), self.minidlna_serialno)
					minidlnaItems.append(minidlna_serialno1)
				elif line.startswith("inotify="):
					self.minidlna_inotify.value = line[8:] != "no"
					minidlna_inotify1 = getConfigListEntry("%s:" % _("Inotify Monitoring"), self.minidlna_inotify)
					minidlnaItems.append(minidlna_inotify1)
				elif line.startswith("enable_tivo="):
					self.minidlna_tivo.value = line[12:] != "no"
					minidlna_tivo1 = getConfigListEntry("%s:" % _("TiVo support"), self.minidlna_tivo)
					minidlnaItems.append(minidlna_tivo1)
				elif line.startswith("strict_dlna="):
					self.minidlna_strictdlna.value = line[12:] != "no"
					minidlna_strictdlna1 = getConfigListEntry("%s:" % _("Strict DLNA"), self.minidlna_strictdlna)
					minidlnaItems.append(minidlna_strictdlna1)
				elif line.startswith("media_dir="):
					line = line[11:]
					self.selectedFiles = [str(n) for n in line.split(", ")]

		Setup.createSetup(self, appendItems=minidlnaItems)
		self.setTitle(_("MiniDLNA Settings"))

	def keySave(self):
		def getYesNo(configItem):
			return "yes" if configItem.value else "no"
		oldLines = fileReadLines("/etc/minidlna.conf", [], source=MODULE_NAME)
		if oldLines:
			newLines = []
			for line in oldLines:
				line = line.replace("\n", "")
				if line.startswith("friendly_name="):
					line = f"friendly_name={self.minidlna_name.value.strip()}"
				elif line.startswith("network_interface="):
					line = f"network_interface={self.minidlna_iface.value.strip()}"
				elif line.startswith("port="):
					line = f"port={str(self.minidlna_port.value)}"
				elif line.startswith("serial="):
					line = f"serial={str(self.minidlna_serialno.value)}"
				elif line.startswith("media_dir="):
					line = "media_dir=%s" % ", ".join(self.selectedFiles)
				elif line.startswith("inotify="):
					line = f"inotify={getYesNo(self.minidlna_inotify)}"
				elif line.startswith("enable_tivo="):
					line = f"enable_tivo={getYesNo(self.minidlna_tivo)}"
				elif line.startswith("strict_dlna="):
					line = f"strict_dlna={getYesNo(self.minidlna_strictdlna)}"
				newLines.append(line)
			fileWriteLines("/etc/minidlna.conf.tmp", newLines, source=MODULE_NAME)
		else:
			self.session.open(MessageBox, _("Sorry MiniDLNA Config is Missing"), MessageBox.TYPE_INFO)
			self.close()
		if exists("/etc/minidlna.conf.tmp"):
			rename("/etc/minidlna.conf.tmp", "/etc/minidlna.conf")
		self.close()

	def selectShares(self):
		def selectSharesCallBack(selectedFiles):
			if selectedFiles:
				self.selectedFiles = selectedFiles
		self.session.openWithCallback(selectSharesCallBack, uShareSelection, self.selectedFiles)


class NetworkSambaSetup(Setup):
	def __init__(self, session):
		Setup.__init__(self, session=session, setup="NetworkSamba")


class NetworkPassword(Setup):
	def __init__(self, session):
		config.network.password = NoSave(ConfigPassword(default=""))
		Setup.__init__(self, session=session, setup="Password")
		self["key_yellow"] = StaticText(_("Random Password"))
		self["passwordActions"] = HelpableActionMap(self, ["ColorActions"], {
			"yellow": (self.randomPassword, _("Create a randomly generated password"))
		}, prio=0, description=_("Password Actions"))
		self.user = "root"
		self.counter = 0
		self.timer = eTimer()
		self.timer.callback.append(self.appClosed)
		self.language = "C.UTF-8"  # This is a complete hack to negate all the plugins that inappropriately change the language!

	def keySave(self):
		password = config.network.password.value
		if not password:
			print("[NetworkSetup] NetworkPassword: Error: The new password may not be blank!")
			self.session.open(MessageBox, _("Error: The new password may not be blank!"), MessageBox.TYPE_ERROR, windowTitle=self.getTitle())
			return
		# print(f"[NetworkSetup] NetworkPassword: Changing the password for '{self.user}' to '{password}'.")
		print(f"[NetworkSetup] NetworkPassword: Changing the password for '{self.user}'.")
		self.container = eConsoleAppContainer()
		self.container.dataAvail.append(self.dataAvail)
		self.container.appClosed.append(self.appClosed)
		status = self.container.execute(*("/usr/bin/passwd", "/usr/bin/passwd", self.user))
		if status:  # If status is -1 code is already/still running, is status is -3 code can not be started!
			self.session.open(MessageBox, _("Error %d: Unable to start 'passwd' command!") % status, MessageBox.TYPE_ERROR, windowTitle=self.getTitle())
			Setup.keySave(self)
		else:
			self.timer.start(3000)

	def randomPassword(self):
		from string import ascii_letters, digits
		passwdChars = ascii_letters + digits
		passwdLength = 10
		config.network.password.value = "".join(Random().sample(passwdChars, passwdLength))
		self["config"].invalidateCurrent()

	def dataAvail(self, data):
		data = data.decode("UTF-8", "ignore")
		# print(f"[NetworkSetup] DEBUG NetworkPassword: data='{data}'.")
		if data.endswith("password: "):
			self.container.write(f"{config.network.password.value}\n")
			self.counter += 1

	def appClosed(self, retVal=ETIMEDOUT):
		self.timer.stop()
		if retVal:
			if retVal == ETIMEDOUT:
				self.container.kill()
			print(f"[NetworkSetup] NetworkPassword: Error {retVal}: Unable to change password!  ({strerror(retVal)})")
			self.session.open(MessageBox, _("Error %d: Unable to change password!  (%s)") % (retVal, strerror(retVal)), MessageBox.TYPE_ERROR, windowTitle=self.getTitle())
		elif self.counter == 2:
			print("[NetworkSetup] NetworkPassword: Password changed.")
			self.session.open(MessageBox, _("Password changed."), MessageBox.TYPE_INFO, timeout=5, windowTitle=self.getTitle())
			Setup.keySave(self)
		else:
			print("[NetworkSetup] NetworkPassword: Error: Unexpected program interaction!")
			self.session.open(MessageBox, _("Error: Interaction failure, unable to change password!"), MessageBox.TYPE_ERROR, windowTitle=self.getTitle())
		del self.container.dataAvail[:]
		del self.container.appClosed[:]
		del self.container


# TODO "NetworkInadynLog" skin?
#
class NetworkLogScreen(Screen):
	def __init__(self, session, title=None, skinName="NetworkInadynLog", logPath="", tailLog=True):
		Screen.__init__(self, session)
		self.setTitle(title if title else _("Network Log"))
		self.skinName = [skinName, "NetworkLogScreen"]
		self.logPath = logPath
		self.tailLog = tailLog
		# self["log"] = ScrollLabel()  # This would make a better widget name.
		self["infotext"] = ScrollLabel()
		self["actions"] = HelpableActionMap(self, ["OkCancelActions", "NavigationActions"], {
			"cancel": (self.keyCancel, _("Close the screen")),
			"close": (self.closeRecursive, _("Close the screen and exit all menus")),
			"ok": (self.keyCancel, _("Close the screen")),
			"top": (self["infotext"].goTop, _("Move to first line / screen")),
			"pageUp": (self["infotext"].goPageUp, _("Move up a screen")),
			"up": (self["infotext"].goLineUp, _("Move up a line")),
			"down": (self["infotext"].goLineDown, _("Move down a line")),
			"pageDown": (self["infotext"].goPageDown, _("Move down a screen")),
			"bottom": (self["infotext"].goBottom, _("Move to last line / screen"))
		}, prio=0, description=_("Network Log Actions"))
		self.console = Console()
		if self.tailLog:
			self.console.ePopen(["/usr/bin/tail", "/usr/bin/tail", logPath], self.showLog)  # Should the number of lines be specified?  10 lines is probably less than one screen worth!
		else:
			self.showLog()

	def keyCancel(self):
		self.console.killAll()
		self.close()

	def closeRecursive(self):
		self.console.killAll()
		self.close(True)

	def showLog(self, data=None, retVal=None, extraArgs=None):
		lines = []
		if self.tailLog:
			lines = [x.rstrip() for x in data.split("\n")]
		elif self.logPath and exists(self.logPath):
			lines = fileReadLines(self.logPath, [], source=MODULE_NAME)
		self["infotext"].setText("\n".join(lines))


class NetworkZeroTierSetup(Setup):
	ZEROTIERCLI = "/usr/sbin/zerotier-cli"
	ZEROTIERSECRET = "/var/lib/zerotier-one/authtoken.secret"
	ZEROTIERAPI = "http://127.0.0.1:9993"

	def __init__(self, session):
		self.cachedToken = None
		self.lastInfo = None
		self.joined = False
		Setup.__init__(self, session=session, setup="NetworkZeroTier")
		self["key_yellow"] = StaticText("")
		self["key_blue"] = StaticText(_("Refresh"))
		self["zerotierActions"] = HelpableActionMap(self, ["ColorActions"], {
			"yellow": (self.toggleJoinLeave, _("Join or leave the configured ZeroTier network")),
			"blue": (self.refreshInfo, _("Refresh ZeroTier status information"))
		}, prio=0, description=_("ZeroTier Actions"))
		self.setJoinLeaveButton()

	def changedEntry(self):
		current = self["config"].getCurrent()
		if current and len(current) > 1 and current[1] is config.network.ZeroTierNetworkId:
			self.createSetup()
			self.setJoinLeaveButton()
		return Setup.changedEntry(self)

	def refreshInfo(self):
		self.createSetup()
		self["config"].invalidateCurrent()
		self.setJoinLeaveButton()

	def readAuthToken(self):
		if self.cachedToken:
			return self.cachedToken
		with open(self.ZEROTIERSECRET, encoding="utf-8", errors="ignore") as fd:
			token = fd.read().strip()
			self.cachedToken = token if token else None
			return self.cachedToken

	def apiRequest(self, method, path, payload=None, timeout=2):
		token = self.readAuthToken()
		url = f"{self.ZEROTIERAPI}{path}"
		headers = {"X-ZT1-Auth": token}

		data = None
		if payload is not None:
			data = dumps(payload).encode("utf-8")
			headers["Content-Type"] = "application/json"

		req = Request(url, data=data, headers=headers, method=method)
		try:
			with urlopen(req, timeout=timeout) as resp:
				body = resp.read().decode("utf-8", "ignore").strip()
				return loads(body) if body else None
		except Exception:
			pass

	def getserviceStatus(self):
		data = self.apiRequest("GET", "/status")
		return {
			"online": bool(data.get("online", False)) if isinstance(data, dict) else False,
			"version": str(data.get("version", "")) if isinstance(data, dict) else "",
			"address": str(data.get("address", "")) if isinstance(data, dict) else ""
		}

	def getMemberships(self):
		data = self.apiRequest("GET", "/network")
		return data if isinstance(data, list) else []

	def isJoined(self, nwid, memberships=None):
		memberships = memberships if memberships is not None else self.getMemberships()
		for m in memberships:
			if isinstance(m, dict) and str(m.get("id", "")).lower() == nwid.lower():
				return True
		return False

	def setJoinLeaveButton(self):
		nwid = str(config.network.ZeroTierNetworkId.value or "").strip()
		if not nwid:
			self["key_yellow"].setText("")
			self["zerotierActions"].setEnabled(False)
			return

		self["zerotierActions"].setEnabled(True)
		self["key_yellow"].setText(_("Leave") if self.joined else _("Join"))

	def toggleJoinLeave(self):
		nwid = str(config.network.ZeroTierNetworkId.value or "").strip()
		if not nwid:
			return

		memberships = self.getMemberships()
		self.joined = self.isJoined(nwid, memberships)

		if self.joined:
			self.zerotierCli(nwid, "leave")
		else:
			self.zerotierCli(nwid, "join")
		self.refreshInfo()

	def createSetup(self):  # NOSONAR silence S2638
		nwid = str(config.network.ZeroTierNetworkId.value or "").strip()
		if not nwid:
			self.lastInfo = None
			Setup.createSetup(self, appendItems=[])

		items = []
		serviceOnline = False
		serviceVersion = ""
		name = ""
		status = ""
		ipv4 = ""
		ipv6 = ""
		serviceStatus = self.getserviceStatus()
		serviceOnline = serviceStatus.get("online", False)
		serviceVersion = serviceStatus.get("version", "")
		memberships = self.getMemberships()
		entry = next((n for n in memberships if str(n.get("nwid") or n.get("id") or "").lower() == nwid.lower()), None)
		self.joined = entry is not None

		if self.joined:
			name = str(entry.get("name", "") or "")
			status = str(entry.get("status", "") or "")
			ips = entry.get("assignedAddresses", []) or []
			ipv4 = next((ip.split("/", 1)[0] for ip in ips if "." in ip), "")
			ipv6 = next((ip.split("/", 1)[0] for ip in ips if ":" in ip), "")
		self.lastInfo = {
			"serviceOnline": serviceOnline,
			"serviceVersion": serviceVersion,
			"joined": self.joined,
			"name": name,
			"status": status,
			"ipv4": ipv4,
			"ipv6": ipv6
		}

		items.append(getConfigListEntry((_("Joined"), 0), ReadOnly(NoSave(ConfigText(default=_("Yes") if self.joined else _("No"), fixed_size=False)))))
		items.append(getConfigListEntry((_("Service online"), 0), ReadOnly(NoSave(ConfigText(default=_("Yes") if serviceOnline else _("No"), fixed_size=False)))))
		if serviceVersion:
			items.append(getConfigListEntry((_("Version"), 0), ReadOnly(NoSave(ConfigText(default=serviceVersion, fixed_size=False)))))

		if self.joined:
			if name:
				items.append(getConfigListEntry((_("Name"), 0), ReadOnly(NoSave(ConfigText(default=name, fixed_size=False)))))
			if status:
				items.append(getConfigListEntry((_("Status"), 0), ReadOnly(NoSave(ConfigText(default=status, fixed_size=False)))))
			items.append(getConfigListEntry((_("Tunnel IPv4"), 0), ReadOnly(NoSave(ConfigText(default=ipv4 or _("N/A"), fixed_size=False)))))
			items.append(getConfigListEntry((_("Tunnel IPv6"), 0), ReadOnly(NoSave(ConfigText(default=ipv6 or _("N/A"), fixed_size=False)))))
		else:
			items.append(getConfigListEntry((_("Info"), 0), ReadOnly(NoSave(ConfigText(default=_("Not joined. Press Yellow to join."), fixed_size=False)))))
		Setup.createSetup(self, appendItems=items)

	def zerotierCli(self, nwid, option):
		if not nwid:
			return False
		background = " "
		if option == "leave":
			background = "&"
			ztIface = next((a for a in iNetwork.getAdapterList() if a.startswith("zt")), "")
			if ztIface:
				Console().ePopen(f"ip link del dev {ztIface}")
		Console().ePopen([self.ZEROTIERCLI, self.ZEROTIERCLI, option, nwid, background])
