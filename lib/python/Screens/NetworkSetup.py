from errno import ETIMEDOUT
from glob import glob
from os import rename, strerror, system, unlink
from os.path import exists
from process import ProcessList
from random import Random

from enigma import eConsoleAppContainer, eTimer

from Components.About import about
from Components.ActionMap import HelpableActionMap, HelpableNumberActionMap
from Components.config import ConfigIP, ConfigMacText, ConfigNumber, ConfigPassword, ConfigSelection, ConfigText, ConfigYesNo, NoSave, config, getConfigListEntry
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
from Screens.Processing import Processing
from Screens.Screen import Screen
from Screens.Setup import Setup
from Tools.Directories import SCOPE_SKINS, SCOPE_GUISKIN, SCOPE_PLUGINS, fileReadLines, fileReadXML, fileWriteLines, resolveFilename
from Tools.LoadPixmap import LoadPixmap

MODULE_NAME = __name__.split(".")[-1]
BASE_GROUP = "packagegroup-base"


class NetworkAdapterSelection(Screen):
	def __init__(self, session):
		Screen.__init__(self, session, enableHelp=True)
		self.setTitle(_("Network Settings"))
		self.wlan_errortext = _("No working wireless network adapter found.\nPlease verify that you have attached a compatible WLAN device and your network is configured correctly.")
		self.lan_errortext = _("No working local network adapter found.\nPlease verify that you have attached a network cable and your network is configured correctly.")
		self.oktext = _("Press OK on your remote control to continue.")
		self.edittext = _("Press OK to edit the settings.")
		self.defaulttext = _("Press yellow to set this interface as the default interface.")
		self.restartLanRef = None
		self["key_red"] = StaticText(_("Close"))
		self["key_green"] = StaticText(_("Select"))
		self["key_yellow"] = StaticText("")
		self["key_blue"] = StaticText("")
		self["introduction"] = StaticText(self.edittext)
		self["OkCancelActions"] = HelpableActionMap(self, ["OkCancelActions", "ColorActions"], {
			"cancel": (self.close, _("Exit network interface list")),
			"ok": (self.okbuttonClick, _("Select interface")),
			"red": (self.close, _("Exit network interface list")),
			"green": (self.okbuttonClick, _("Select interface")),
			"blue": (self.openNetworkWizard, _("Use the network wizard to configure selected network adapter"))
		}, prio=0, description=_("Network Adapter Actions"))
		self["DefaultInterfaceAction"] = HelpableActionMap(self, ["ColorActions"], {
			"yellow": (self.setDefaultInterface, [_("Set interface as the default Interface"), _("* Only available if more than one interface is active.")])
		}, prio=0, description=_("Network Adapter Actions"))
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
		if len(self.adapters) == 1:
			self.onFirstExecBegin.append(self.okbuttonClick)
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
		elif iNetwork.isWirelessInterface(iface):
			if active is True:
				interfacepng = LoadPixmap(resolveFilename(SCOPE_GUISKIN, "icons/network_wireless-active.png"))
			elif active is False:
				interfacepng = LoadPixmap(resolveFilename(SCOPE_GUISKIN, "icons/network_wireless-inactive.png"))
			else:
				interfacepng = LoadPixmap(resolveFilename(SCOPE_GUISKIN, "icons/network_wireless.png"))
		num_configured_if = len(iNetwork.getConfiguredAdapters())
		if num_configured_if >= 2:
			if default is True:
				defaultpng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_GUISKIN, "buttons/button_green.png"))
			elif default is False:
				defaultpng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_GUISKIN, "buttons/button_green_off.png"))
		if active is True:
			activepng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_GUISKIN, "icons/lock_on.png"))
		elif active is False:
			activepng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_GUISKIN, "icons/lock_error.png"))
		description = iNetwork.getFriendlyAdapterDescription(iface)
		return iface, name, description, interfacepng, defaultpng, activepng, divpng

	def updateList(self):
		self.list = []
		default_gw = None
		num_configured_if = len(iNetwork.getConfiguredAdapters())
		if num_configured_if >= 2:
			self["key_yellow"].setText(_("Default"))
			self["introduction"].setText(self.defaulttext)
			self["DefaultInterfaceAction"].setEnabled(True)
		else:
			self["key_yellow"].setText("")
			self["introduction"].setText(self.edittext)
			self["DefaultInterfaceAction"].setEnabled(False)
		if num_configured_if < 2 and exists("/etc/default_gw"):
			unlink("/etc/default_gw")
		if exists("/etc/default_gw"):
			fp = open("/etc/default_gw")
			result = fp.read()
			fp.close()
			default_gw = result
		for adapter in self.adapters:
			default_int = adapter[1] == default_gw
			active_int = iNetwork.getAdapterAttribute(adapter[1], "up")
			self.list.append(self.buildInterfaceList(adapter[1], _(adapter[0]), default_int, active_int))
		if exists(resolveFilename(SCOPE_PLUGINS, "SystemPlugins/NetworkWizard/networkwizard.xml")):
			self["key_blue"].setText(_("Network Wizard"))
		self["list"].setList(self.list)

	def setDefaultInterface(self):
		selection = self["list"].getCurrent()
		num_if = len(self.list)
		old_default_gw = None
		num_configured_if = len(iNetwork.getConfiguredAdapters())
		if exists("/etc/default_gw"):
			fp = open("/etc/default_gw")
			old_default_gw = fp.read()
			fp.close()
		if num_configured_if > 1 and (not old_default_gw or old_default_gw != selection[0]):
			fp = open("/etc/default_gw", "w+")
			fp.write(selection[0])
			fp.close()
			self.restartLan()
		elif old_default_gw and num_configured_if < 2:
			unlink("/etc/default_gw")
			self.restartLan()

	def okbuttonClick(self):
		selection = self["list"].getCurrent()
		if selection is not None:
			self.session.openWithCallback(self.AdapterSetupClosed, AdapterSetupConfiguration, selection[0])

	def AdapterSetupClosed(self, *ret):
		if len(self.adapters) == 1:
			self.close()
		else:
			self.updateList()

	def cleanup(self):
		iNetwork.stopLinkStateConsole()
		iNetwork.stopRestartConsole()
		iNetwork.stopGetInterfacesConsole()

	def restartLan(self):
		iNetwork.restartNetwork(self.restartLanDataAvail)
		self.restartLanRef = self.session.openWithCallback(self.restartfinishedCB, MessageBox, _("Please wait while we configure your network..."), type=MessageBox.TYPE_INFO, enable_input=False)

	def restartLanDataAvail(self, data):
		if data is True:
			iNetwork.getInterfaces(self.getInterfacesDataAvail)

	def getInterfacesDataAvail(self, data):
		if data is True:
			self.restartLanRef.close(True)

	def restartfinishedCB(self, data):
		if data is True:
			self.updateList()
			self.session.open(MessageBox, _("Finished configuring your network"), type=MessageBox.TYPE_INFO, timeout=10, default=False)

	def openNetworkWizard(self):
		if exists(resolveFilename(SCOPE_PLUGINS, "SystemPlugins/NetworkWizard/networkwizard.xml")):
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
		self.dnsInitial = iNetwork.getNameserverList()
		print(f"[NetworkSetup] DNSSettings: Initial DNS list: {str(self.dnsInitial)}.")
		self.dnsOptions = {
			"custom": [[0, 0, 0, 0]],
			"dhcp-router": [list(x[1]) for x in self.getNetworkRoutes()],
		}
		fileDom = fileReadXML(resolveFilename(SCOPE_SKINS, "dnsservers.xml"), source=MODULE_NAME)
		for dns in fileDom.findall("dnsserver"):
			if dns.get("key", ""):
				adresses = []
				ipv4s = dns.get("ipv4", "").split(",")
				for ipv4 in ipv4s:
					adresses.append([int(x) for x in ipv4.split(".")])
				ipv6s = dns.get("ipv6", "")
				if ipv6s:
					adresses.extend(ipv6s.split(","))
				self.dnsOptions[dns.get("key")] = adresses

		option = self.dnsCheck(self.dnsInitial, refresh=False)
		self.dnsServers = self.dnsOptions[option][:]
		self.entryAdded = False
		Setup.__init__(self, session=session, setup="DNS")
		self["key_yellow"] = StaticText(_("Add"))
		self["key_blue"] = StaticText("")
		dnsDescription = _("DNS (Dynamic Name Server) Actions")
		self["addAction"] = HelpableActionMap(self, ["DNSSettingsActions"], {
			"dnsAdd": (self.addDNSServer, _("Add a DNS entry"))
		}, prio=0, description=dnsDescription)
		self["removeAction"] = HelpableActionMap(self, ["DNSSettingsActions"], {
			"dnsRemove": (self.removeDNSServer, _("Remove a DNS entry"))
		}, prio=0, description=dnsDescription)
		self["removeAction"].setEnabled(False)
		self["moveUpAction"] = HelpableActionMap(self, ["DNSSettingsActions"], {
			"moveUp": (self.moveEntryUp, _("Move the current DNS entry up one line"))
		}, prio=0, description=dnsDescription)
		self["moveUpAction"].setEnabled(False)
		self["moveDownAction"] = HelpableActionMap(self, ["DNSSettingsActions"], {
			"moveDown": (self.moveEntryDown, _("Move the current DNS entry down one line"))
		}, prio=0, description=dnsDescription)
		self["moveDownAction"].setEnabled(False)

	def dnsCheck(self, dnsServers, refresh=True):
		def dnsRefresh(refresh):
			if refresh:
				for item in self["config"].getList():
					if item[1] == config.usage.dns:
						self["config"].invalidate(item)
						break

		for option in self.dnsOptions.keys():
			if dnsServers == self.dnsOptions[option]:
				if option != "custom":
					self.dnsOptions["custom"] = [[0, 0, 0, 0]]
				config.usage.dns.value = option
				dnsRefresh(refresh)
				return option
		option = "custom"
		self.dnsOptions[option] = dnsServers[:]
		config.usage.dns.value = option
		dnsRefresh(refresh)
		return option

	def createSetup(self):  # NOSONAR silence S2638
		Setup.createSetup(self)
		dnsList = self["config"].getList()
		if hasattr(self, "dnsStart"):
			del dnsList[self.dnsStart:]
		self.dnsStart = len(dnsList)
		items = [NoSave(ConfigIP(default=x)) for x in self.dnsServers if isinstance(x, list)] + [NoSave(ConfigText(default=x, fixed_size=False)) for x in self.dnsServers if isinstance(x, str)]
		entry = None
		for item, entry in enumerate(items, start=1):
			dnsList.append(getConfigListEntry(_("Name server %d") % item, entry, _("Enter DNS (Dynamic Name Server) %d's IP address.") % item))
		self.dnsLength = item if items else 0
		if self.entryAdded and entry:
			entry.default = [256, 256, 256, 256]  # This triggers a cancel confirmation for unedited new entries.
			self.entryAdded = False
		self["config"].setList(dnsList)

	def changedEntry(self):
		current = self["config"].getCurrent()[1]
		index = self["config"].getCurrentIndex()
		if current == config.usage.dns:
			self.dnsServers = self.dnsOptions[config.usage.dns.value][:]
		elif current not in (config.usage.dnsMode, config.usage.dnsSuffix) and self.dnsStart <= index < self.dnsStart + self.dnsLength:
			self.dnsServers[index - self.dnsStart] = current.value[:]
			option = self.dnsCheck(self.dnsServers, refresh=True)
		Setup.changedEntry(self)
		self.updateControls()

	def selectionChanged(self):
		Setup.selectionChanged(self)
		self.updateControls()

	def updateControls(self):
		index = self["config"].getCurrentIndex() - self.dnsStart
		if 0 <= index < self.dnsLength:
			self["key_blue"].setText(_("Delete") if self.dnsLength > 1 or self.dnsServers[0] != [0, 0, 0, 0] else "")
			self["removeAction"].setEnabled(self.dnsLength > 1 or self.dnsServers[0] != [0, 0, 0, 0])
			self["moveUpAction"].setEnabled(index > 0)
			self["moveDownAction"].setEnabled(index < self.dnsLength - 1)
		else:
			self["key_blue"].setText("")
			self["removeAction"].setEnabled(False)
			self["moveUpAction"].setEnabled(False)
			self["moveDownAction"].setEnabled(False)

	def keySave(self):
		iNetwork.clearNameservers()
		for dnsServer in self.dnsServers:
			iNetwork.addNameserver(dnsServer)
		print(f"[NetworkSetup] DNSSettings: Saved DNS list: {str(iNetwork.getNameserverList())}.")
		# iNetwork.saveNameserverConfig()
		iNetwork.writeNameserverConfig()
		Setup.keySave(self)

	def addDNSServer(self):
		self.entryAdded = True
		self.dnsServers = self.dnsServers + [[0, 0, 0, 0]]
		self.dnsCheck(self.dnsServers, refresh=False)
		self.createSetup()
		self["config"].setCurrentIndex(self.dnsStart + self.dnsLength - 1)

	def removeDNSServer(self):
		index = self["config"].getCurrentIndex() - self.dnsStart
		if self.dnsLength == 1:
			self.dnsServers = [[0, 0, 0, 0]]
		else:
			del self.dnsServers[index]
		self.dnsCheck(self.dnsServers, refresh=False)
		self.createSetup()
		if index == self.dnsLength:
			index -= 1
		self["config"].setCurrentIndex(self.dnsStart + index)

	def moveEntryUp(self):
		index = self["config"].getCurrentIndex() - self.dnsStart - 1
		self.dnsServers.insert(index, self.dnsServers.pop(index + 1))
		self.dnsCheck(self.dnsServers, refresh=False)
		self.createSetup()
		self["config"].setCurrentIndex(self.dnsStart + index)

	def moveEntryDown(self):
		index = self["config"].getCurrentIndex() - self.dnsStart + 1
		self.dnsServers.insert(index, self.dnsServers.pop(index - 1))
		self.dnsCheck(self.dnsServers, refresh=False)
		self.createSetup()
		self["config"].setCurrentIndex(self.dnsStart + index)

	def getNetworkRoutes(self):
		# # cat /proc/net/route
		# Iface   Destination     Gateway         Flags   RefCnt  Use     Metric  Mask            MTU     Window  IRTT
		# eth0    00000000        FE08A8C0        0003    0       0       0       00000000        0       0       0
		# eth0    0008A8C0        00000000        0001    0       0       0       00FFFFFF        0       0       0
		gateways = []
		lines = []
		lines = fileReadLines("/proc/net/route", lines, source=MODULE_NAME)
		headings = lines.pop(0)
		for line in lines:
			data = line.split()
			if data[1] == "00000000" and int(data[3]) & 0x03 and data[7] == "00000000":  # If int(flags) & 0x03 is True this is a gateway (0x02) and it is up (0x01).
				gateways.append((data[0], tuple(reversed([int(data[2][x:x + 2], 16) for x in range(0, len(data[2]), 2)]))))
		return gateways


class NameserverSetup(DNSSettings):
	def __init__(self, session):
		DNSSettings.__init__(self, session=session)


class NetworkMacSetup(ConfigListScreen, Screen):
	def __init__(self, session):
		Screen.__init__(self, session, enableHelp=True)
		self.setTitle(_("MAC Address Settings"))
		self.curMac = self.getmac("eth0")
		self.getConfigMac = NoSave(ConfigMacText(default=self.curMac))
		self["key_red"] = StaticText(_("Cancel"))
		self["key_green"] = StaticText(_("Save"))
		self["introduction"] = StaticText(_("Press OK to set the MAC address."))
		self["actions"] = HelpableActionMap(self, ["OkCancelActions", "ColorActions"], {
			"cancel": (self.cancel, _("Exit MAC address configuration")),
			"ok": (self.ok, _("Activate MAC address configuration")),
			"red": (self.cancel, _("Exit MAC address configuration")),
			"green": (self.ok, _("Activate MAC address configuration"))
		}, prio=0, description=_("MAC Address Actions"))
		self.list = []
		ConfigListScreen.__init__(self, self.list)
		self.createSetup()

	def getmac(self, iface):
		eth = about.getIfConfig(iface)
		return eth["hwaddr"]

	def createSetup(self):
		self.list = []
		self.list.append(getConfigListEntry(_("MAC-address"), self.getConfigMac))
		self["config"].list = self.list

	def ok(self):
		MAC = self.getConfigMac.value
		f = open("/etc/enigma2/hwmac", "w")
		f.write(MAC)
		f.close()
		self.restartLan()

	def run(self):
		self.ok()

	def cancel(self):
		self.close()

	def restartLan(self):
		iNetwork.restartNetwork(self.restartLanDataAvail)
		self.restartLanRef = self.session.openWithCallback(self.restartfinishedCB, MessageBox, _("Please wait while we configure your network..."), type=MessageBox.TYPE_INFO, enable_input=False)

	def restartLanDataAvail(self, data):
		if data is True:
			iNetwork.getInterfaces(self.getInterfacesDataAvail)

	def getInterfacesDataAvail(self, data):
		if data is True:
			self.restartLanRef.close(True)

	def restartfinishedCB(self, data):
		if data is True:
			self.session.openWithCallback(self.close, MessageBox, _("Finished configuring your network"), type=MessageBox.TYPE_INFO, timeout=10, default=False)


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

	def NameserverSetupClosed(self, *ret):
		iNetwork.loadNameserverConfig()
		nameserver = (iNetwork.getNameserverList() + [[0, 0, 0, 0]] * 2)[0:2]
		self.primaryDNS = NoSave(ConfigIP(default=nameserver[0]))
		self.secondaryDNS = NoSave(ConfigIP(default=nameserver[1]))
		self.createSetup()
		self.layoutFinished()

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
		self.restartLanRef = None
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

	def queryWirelessDevice(self, iface):
		try:
			from wifi.scan import Cell
			import errno
		except ImportError:
			return False
		else:
			from wifi.exceptions import InterfaceError
			try:
				system(f"ifconfig {self.iface} up")
				wlanresponse = list(Cell.all(iface))
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

	def ok(self):
		self.cleanup()
		if self["menulist"].getCurrent()[1] == "edit":
			if iNetwork.isWirelessInterface(self.iface):
				try:
					from Plugins.SystemPlugins.WirelessLan.plugin import WlanScan
				except ImportError:
					self.session.open(MessageBox, self.missingwlanplugintxt, type=MessageBox.TYPE_INFO, timeout=10)
				else:
					if self.queryWirelessDevice(self.iface):
						self.session.openWithCallback(self.AdapterSetupClosed, AdapterSetup, self.iface)
					else:
						self.showErrorMessage()	 # Display Wlan not available message.
			else:
				self.session.openWithCallback(self.AdapterSetupClosed, AdapterSetup, self.iface)
		if self["menulist"].getCurrent()[1] == "test":
			self.session.open(NetworkAdapterTest, self.iface)
		if self["menulist"].getCurrent()[1] == "dns":
			self.session.open(NameserverSetup)
		if self["menulist"].getCurrent()[1] == "mac":
			self.session.open(NetworkMacSetup)
		if self["menulist"].getCurrent()[1] == "scanwlan":
			try:
				from Plugins.SystemPlugins.WirelessLan.plugin import WlanScan
			except ImportError:
				self.session.open(MessageBox, self.missingwlanplugintxt, type=MessageBox.TYPE_INFO, timeout=10)
			else:
				if self.queryWirelessDevice(self.iface):
					self.session.openWithCallback(self.WlanScanClosed, WlanScan, self.iface)
				else:
					self.showErrorMessage()	 # Display Wlan not available message.
		if self["menulist"].getCurrent()[1] == "wlanstatus":
			try:
				from Plugins.SystemPlugins.WirelessLan.plugin import WlanStatus
			except ImportError:
				self.session.open(MessageBox, self.missingwlanplugintxt, type=MessageBox.TYPE_INFO, timeout=10)
			else:
				if self.queryWirelessDevice(self.iface):
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
		if self["menulist"].getCurrent()[1] == "mac":
			self["description"].setText("%s\n\n%s" % (_("Set the MAC address of your %s %s.") % getBoxDisplayName(), self.oktext))
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
			except:
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
		# Check which boxes support MAC change via the GUI.
		if BoxInfo.getItem("machinebuild") not in ("DUMMY",) and self.iface == "eth0":
			menu.append((_("Network MAC settings"), "mac"))
		return menu

	def AdapterSetupClosed(self, *ret):
		if ret is not None and len(ret):
			if ret[0] == "ok" and (iNetwork.isWirelessInterface(self.iface) and iNetwork.getAdapterAttribute(self.iface, "up") is True):
				try:
					from Plugins.SystemPlugins.WirelessLan.plugin import WlanStatus
				except ImportError:
					self.session.open(MessageBox, self.missingwlanplugintxt, type=MessageBox.TYPE_INFO, timeout=10)
				else:
					if self.queryWirelessDevice(self.iface):
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
			iNetwork.restartNetwork(self.restartLanDataAvail)
			self.restartLanRef = self.session.openWithCallback(self.restartfinishedCB, MessageBox, _("Please wait while your network is restarting..."), type=MessageBox.TYPE_INFO, enable_input=False)

	def restartLanDataAvail(self, data):
		if data is True:
			iNetwork.getInterfaces(self.getInterfacesDataAvail)

	def getInterfacesDataAvail(self, data):
		if data is True:
			self.restartLanRef.close(True)

	def restartfinishedCB(self, data):
		if data is True:
			self.updateStatusbar()
			self.session.open(MessageBox, _("Finished restarting your network"), type=MessageBox.TYPE_INFO, timeout=10, default=False)

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
			except:
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


class NetworkMountsMenu(Screen):
	def __init__(self, session):
		Screen.__init__(self, session, enableHelp=True)
		self.setTitle(_("Mount Settings"))
		self.onChangedEntry = []
		self.mainmenu = self.genMainMenu()
		self["menulist"] = MenuList(self.mainmenu)
		self["key_red"] = StaticText(_("Close"))
		self["introduction"] = StaticText()
		self["actions"] = HelpableActionMap(self, ["NavigationActions", "ColorActions", "OkCancelActions"], {
			"ok": (self.keyOk, _("Select menu entry")),
			"close": (self.close, _("Exit network adapter setup menu")),
			"red": (self.close, _("Exit network adapter setup menu")),
			"top": (self["menulist"].goTop, _("Move to first line / screen")),
			"pageUp": (self["menulist"].goPageUp, _("Move up a screen")),
			"up": (self["menulist"].goLineUp, _("Move up a line")),
			# "left": (self.left, _("Move up to first entry")),
			# "right": (self.right, _("Move down to last entry")),
			"down": (self["menulist"].goLineDown, _("Move down a line")),
			"pageDown": (self["menulist"].goPageDown, _("Move down a screen")),
			"bottom": (self["menulist"].goBottom, _("Move to last line / screen"))
		}, prio=0, description=_("Mount Menu Actions"))
		if self.selectionChanged not in self["menulist"].onSelectionChanged:
			self["menulist"].onSelectionChanged.append(self.selectionChanged)
		self.selectionChanged()

	def createSummary(self):
		from Screens.PluginBrowser import PluginBrowserSummary
		return PluginBrowserSummary

	def selectionChanged(self):
		item = self["menulist"].getCurrent()
		if item:
			if item[1][0] == "extendedSetup":
				self["introduction"].setText(_(item[1][1]))
			name = str(self["menulist"].getCurrent()[0])
			desc = self["introduction"].text
		else:
			name = ""
			desc = ""
		for cb in self.onChangedEntry:
			cb(name, desc)

	def keyOk(self):
		if self["menulist"].getCurrent()[1][0] == "extendedSetup":
			self.extended = self["menulist"].getCurrent()[1][2]
			self.extended(self.session)

	def genMainMenu(self):
		menu = []
		self.extended = None
		self.extendedSetup = None
		for plugin in plugins.getPlugins(PluginDescriptor.WHERE_NETWORKMOUNTS):
			callFnc = plugin.__call__["ifaceSupported"](self)
			if callFnc is not None:
				self.extended = callFnc
				menuEntryName = plugin.__call__["menuEntryName"](self) if "menuEntryName" in plugin.__call__ else _("Extended Setup...")
				menuEntryDescription = plugin.__call__["menuEntryDescription"](self) if "menuEntryDescription" in plugin.__call__ else _("Extended Networksetup Plugin...")
				self.extendedSetup = ("extendedSetup", menuEntryDescription, self.extended)
				menu.append((menuEntryName, self.extendedSetup))
		return menu


class NetworkDaemons():
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
