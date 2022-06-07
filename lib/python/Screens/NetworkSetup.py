from errno import ETIMEDOUT
from glob import glob
from os import remove, rename, strerror, system, unlink
from os.path import exists
from random import Random
import sys
import time

from enigma import eConsoleAppContainer, eTimer

from Components.About import about, getVersionString
from Components.ActionMap import HelpableActionMap, HelpableNumberActionMap
from Components.config import ConfigIP, ConfigLocations, ConfigMacText, ConfigNumber, ConfigPassword, ConfigSelection, ConfigSubsection, ConfigText, ConfigYesNo, NoSave, config, getConfigListEntry
from Components.ConfigList import ConfigListScreen
from Components.Console import Console
from Components.Input import Input
from Components.Label import Label, MultiColorLabel
from Components.MenuList import MenuList
from Components.Network import iNetwork
from Components.Pixmap import Pixmap, MultiPixmap
from Components.ScrollLabel import ScrollLabel
from Components.SystemInfo import BoxInfo
from Components.PluginComponent import plugins
from Components.FileList import MultiFileSelectList
from Components.Sources.Boolean import Boolean
from Components.Sources.List import List
from Components.Sources.StaticText import StaticText
from Plugins.Plugin import PluginDescriptor
from Screens.HelpMenu import HelpableScreen
from Screens.InputBox import InputBox
from Screens.MessageBox import MessageBox
from Screens.Screen import Screen
from Screens.Setup import Setup
from Screens.Standby import TryQuitMainloop
from Tools.Directories import SCOPE_GUISKIN, SCOPE_PLUGINS, fileExists, fileReadLines, resolveFilename
from Tools.LoadPixmap import LoadPixmap

MODULE_NAME = __name__.split(".")[-1]
BASE_GROUP = "packagegroup-base" if float(getVersionString()) >= 4.0 else "task-base"

BRAND = BoxInfo.getItem("displaybrand")
MODEL = BoxInfo.getItem("displaymodel")

class NetworkAdapterSelection(Screen, HelpableScreen):
	def __init__(self, session):
		Screen.__init__(self, session)
		HelpableScreen.__init__(self)
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
		if not self.selectionChanged in self["list"].onSelectionChanged:
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
			if active == True:
				interfacepng = LoadPixmap(resolveFilename(SCOPE_GUISKIN, "icons/network_wired-active.png"))
			elif active == False:
				interfacepng = LoadPixmap(resolveFilename(SCOPE_GUISKIN, "icons/network_wired-inactive.png"))
			else:
				interfacepng = LoadPixmap(resolveFilename(SCOPE_GUISKIN, "icons/network_wired.png"))
		elif iNetwork.isWirelessInterface(iface):
			if active == True:
				interfacepng = LoadPixmap(resolveFilename(SCOPE_GUISKIN, "icons/network_wireless-active.png"))
			elif active == False:
				interfacepng = LoadPixmap(resolveFilename(SCOPE_GUISKIN, "icons/network_wireless-inactive.png"))
			else:
				interfacepng = LoadPixmap(resolveFilename(SCOPE_GUISKIN, "icons/network_wireless.png"))

		num_configured_if = len(iNetwork.getConfiguredAdapters())
		if num_configured_if >= 2:
			if default == True:
				defaultpng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_GUISKIN, "buttons/button_green.png"))
			elif default == False:
				defaultpng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_GUISKIN, "buttons/button_green_off.png"))
		if active == True:
			activepng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_GUISKIN, "icons/lock_on.png"))
		elif active == False:
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
			fp = open("/etc/default_gw", "r")
			result = fp.read()
			fp.close()
			default_gw = result

		for x in self.adapters:
			if x[1] == default_gw:
				default_int = True
			else:
				default_int = False
			if iNetwork.getAdapterAttribute(x[1], "up") == True:
				active_int = True
			else:
				active_int = False
			self.list.append(self.buildInterfaceList(x[1], _(x[0]), default_int, active_int))

		if exists(resolveFilename(SCOPE_PLUGINS, "SystemPlugins/NetworkWizard/networkwizard.xml")):
			self["key_blue"].setText(_("Network Wizard"))
		self["list"].setList(self.list)

	def setDefaultInterface(self):
		selection = self["list"].getCurrent()
		num_if = len(self.list)
		old_default_gw = None
		num_configured_if = len(iNetwork.getConfiguredAdapters())
		if exists("/etc/default_gw"):
			fp = open("/etc/default_gw", "r")
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
		if selection != None:
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
		if data == True:
			iNetwork.getInterfaces(self.getInterfacesDataAvail)

	def getInterfacesDataAvail(self, data):
		if data == True:
			self.restartLanRef.close(True)

	def restartfinishedCB(self, data):
		if data == True:
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
				if selection != None:
					self.session.openWithCallback(self.AdapterSetupClosed, NetworkWizard, selection[0])


class DNSSettings(Setup):
	def __init__(self, session):
		self.dnsInitial = iNetwork.getNameserverList()
		print("[NetworkSetup] DNSSettings: Initial DNS list: %s." % str(self.dnsInitial))
		self.dnsOptions = {
			"custom": [[0, 0, 0, 0]],
			"dhcp-router": [list(x[1]) for x in self.getNetworkRoutes()],
			"google": [[8, 8, 8, 8], [8, 8, 4, 4]],
			"cloudflare": [[1, 1, 1, 1], [1, 0, 0, 1]],
			"opendns-familyshield": [[208, 67, 222, 123], [208, 67, 220, 123]],
			"opendns-home": [[208, 67, 222, 222], [208, 67, 220, 220]]
		}
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

	def createSetup(self):
		Setup.createSetup(self)
		dnsList = self["config"].getList()
		self.dnsStart = len(dnsList)
		for item, entry in enumerate([NoSave(ConfigIP(default=x)) for x in self.dnsServers], start=1):
			dnsList.append(getConfigListEntry(_("Name server %d") % item, entry, _("Enter DNS (Dynamic Name Server) %d's IP address.") % item))
		self.dnsLength = item
		if self.entryAdded:
			entry.default = [256, 256, 256, 256]  # This triggers a cancel confirmation for unedited new entries.
			self.entryAdded = False
		self["config"].setList(dnsList)

	def changedEntry(self):
		current = self["config"].getCurrent()[1]
		index = self["config"].getCurrentIndex()
		if current == config.usage.dns:
			self.dnsServers = self.dnsOptions[config.usage.dns.value][:]
		elif self.dnsStart <= index < self.dnsStart + self.dnsLength:
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
		print("[NetworkSetup] DNSSettings: Saved DNS list: %s." % str(iNetwork.getNameserverList()))
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


class NetworkMacSetup(Screen, ConfigListScreen, HelpableScreen):
	def __init__(self, session):
		Screen.__init__(self, session)
		HelpableScreen.__init__(self)
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
		if data == True:
			iNetwork.getInterfaces(self.getInterfacesDataAvail)

	def getInterfacesDataAvail(self, data):
		if data == True:
			self.restartLanRef.close(True)

	def restartfinishedCB(self, data):
		if data == True:
			self.session.openWithCallback(self.close, MessageBox, _("Finished configuring your network"), type=MessageBox.TYPE_INFO, timeout=10, default=False)


class AdapterSetup(Screen, ConfigListScreen, HelpableScreen):
	def __init__(self, session, networkinfo, essid=None):
		Screen.__init__(self, session)
		HelpableScreen.__init__(self)
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
		if self.ipConfigEntry.getText() != None:
			if self.ipConfigEntry.getText() == "0.0.0.0":
				self["IP"].setText(_("N/A"))
			else:
				self["IP"].setText(self.ipConfigEntry.getText())
		else:
			self["IP"].setText(_("N/A"))
		if self.netmaskConfigEntry.getText() != None:
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
			if not exists("/tmp/bcm/%s" % self.iface):
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
					with open(iface_file, "r") as f:
						output = f.read()
					search_str = "#only WakeOnWiFi %s" % self.iface
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
			if BoxInfo.getItem("WakeOnLAN") and not BoxInfo.getItem("model") in ("et10000", "gb800seplus", "gb800ueplus", "gbultrase", "gbultraue", "gbultraueh", "gbipbox", "gbquad", "gbx1", "gbx2", "gbx3", "gbx3h"):
				havewol = True
			if BoxInfo.getItem("model") in ("et10000", "vuultimo4k", "vuduo4kse") and self.iface == "eth0":
				havewol = False
			if havewol and self.onlyWakeOnWiFi != True:
				self.list.append(getConfigListEntry(_("Enable Wake On LAN"), config.network.wol))

			self.extended = None
			self.configStrings = None
			for p in plugins.getPlugins(PluginDescriptor.WHERE_NETWORKSETUP):
				callFnc = p.__call__["ifaceSupported"](self.iface)
				if callFnc != None:
					if "WlanPluginEntry" in p.__call__:  # Internally used only for WLAN Plugin.
						self.extended = callFnc
						if "configStrings" in p.__call__:
							self.configStrings = p.__call__["configStrings"]

						isExistBcmWifi = exists("/tmp/bcm/%s" % self.iface)
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
		if self["config"].getCurrent() == self.InterfaceEntry:
			self.createSetup()
		if self["config"].getCurrent() == self.dhcpEntry:
			self.createSetup()
		if self["config"].getCurrent() == self.gatewayEntry:
			self.createSetup()
		if self["config"].getCurrent() == self.DNSConfigEntry:
			self.createSetup()
		if self["config"].getCurrent() == self.primaryDNSEntry:
			self.createSetup()
		if self["config"].getCurrent() == self.secondaryDNSEntry:
			self.createSetup()
		if self["config"].getCurrent() == self.WakeOnWiFiEntry:
			iNetwork.onlyWoWifaces[self.iface] = self.onlyWakeOnWiFi.value
			open(BoxInfo.getItem("WakeOnLAN"), "w").write(self.onlyWakeOnWiFi.value and "enable" or "disable")
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
		if ret == True:
			num_configured_if = len(iNetwork.getConfiguredAdapters())
			if num_configured_if >= 1:
				if self.iface in iNetwork.getConfiguredAdapters() or (self.iface in iNetwork.onlyWoWifaces and iNetwork.onlyWoWifaces[self.iface] == True):
					self.applyConfig(True)
				else:
					self.session.openWithCallback(self.secondIfaceFoundCB, MessageBox, _("A second configured interface has been found.\n\nDo you want to disable the second network interface?"), default=True)
			else:
				self.applyConfig(True)
		else:
			self.keyCancel()

	def secondIfaceFoundCB(self, data):
		if data == False:
			self.applyConfig(True)
		else:
			configuredInterfaces = iNetwork.getConfiguredAdapters()
			for interface in configuredInterfaces:
				if interface == self.iface:
					continue
				iNetwork.setAdapterAttribute(interface, "up", False)
			iNetwork.deactivateInterface(configuredInterfaces, self.deactivateSecondInterfaceCB)

	def deactivateSecondInterfaceCB(self, data):
		if data == True:
			self.applyConfig(True)

	def applyConfig(self, ret=False):
		if ret == True:
			self.applyConfigRef = None
			iNetwork.setAdapterAttribute(self.iface, "up", self.activateInterfaceEntry.value)
			iNetwork.setAdapterAttribute(self.iface, "dhcp", self.dhcpConfigEntry.value)
			iNetwork.setAdapterAttribute(self.iface, "ip", self.ipConfigEntry.value)
			iNetwork.setAdapterAttribute(self.iface, "netmask", self.netmaskConfigEntry.value)
			if self.hasGatewayConfigEntry.value:
				iNetwork.setAdapterAttribute(self.iface, "gateway", self.gatewayConfigEntry.value)
			else:
				iNetwork.removeAdapterAttribute(self.iface, "gateway")

			if self.extended != None and self.configStrings != None:
				iNetwork.setAdapterAttribute(self.iface, "configStrings", self.configStrings(self.iface))
				self.ws.writeConfig(self.iface)

			if self.activateInterfaceEntry.value == False and not (self.onlyWakeOnWiFi and self.onlyWakeOnWiFi.value == True):
				iNetwork.deactivateInterface(self.iface, self.deactivateInterfaceCB)
				iNetwork.writeNetworkConfig()
				self.applyConfigRef = self.session.openWithCallback(self.applyConfigfinishedCB, MessageBox, _("Please wait for activation of your network configuration..."), type=MessageBox.TYPE_INFO, enable_input=False)
			else:
				if self.oldInterfaceState == False:
					iNetwork.activateInterface(self.iface, self.deactivateInterfaceCB)
				else:
					iNetwork.deactivateInterface(self.iface, self.activateInterfaceCB)
				iNetwork.writeNetworkConfig()
				self.applyConfigRef = self.session.openWithCallback(self.applyConfigfinishedCB, MessageBox, _("Please wait for activation of your network configuration..."), type=MessageBox.TYPE_INFO, enable_input=False)
		else:
			self.keyCancel()

	def deactivateInterfaceCB(self, data):
		if data == True:
			self.applyConfigDataAvail(True)

	def activateInterfaceCB(self, data):
		if data == True:
			iNetwork.activateInterface(self.iface, self.applyConfigDataAvail)

	def applyConfigDataAvail(self, data):
		if data == True:
			iNetwork.getInterfaces(self.getInterfacesDataAvail)

	def getInterfacesDataAvail(self, data):
		if data == True:
			self.applyConfigRef.close(True)

	def applyConfigfinishedCB(self, data):
		if data == True:
			if self.finished_cb:
				self.session.openWithCallback(lambda x: self.finished_cb(), MessageBox, _("Your network configuration has been activated."), type=MessageBox.TYPE_INFO, timeout=10)
			else:
				self.session.openWithCallback(self.ConfigfinishedCB, MessageBox, _("Your network configuration has been activated."), type=MessageBox.TYPE_INFO, timeout=10)

	def ConfigfinishedCB(self, data):
		if data != None:
			if data == True:
				self.close("ok")

	def keyCancelConfirm(self, result):
		if not result:
			return
		if BoxInfo.getItem("WakeOnLAN"):
			config.network.wol.setValue(self.wolstartvalue)
		if self.oldInterfaceState == False:
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
		if data != None:
			if data == True:
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
			if current[1].help_window.instance != None:
				current[1].help_window.instance.hide()
		elif current == self.encryptionKey and config.plugins.wlan.encryption.value != "Unencrypted":
			if current[1].help_window.instance != None:
				current[1].help_window.instance.hide()

	def makeLineDnsNameservers(self, nameservers=[]):
		line = ""
		entry = " ".join([("%d.%d.%d.%d" % tuple(x)) for x in nameservers if x != [0, 0, 0, 0]])
		if len(entry):
			line += "\tdns-nameservers %s\n" % entry
		return line


class AdapterSetupConfiguration(Screen, HelpableScreen):
	def __init__(self, session, iface):
		Screen.__init__(self, session)
		HelpableScreen.__init__(self)
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
		self["WizardActions"] = HelpableActionMap(self, "WizardActions", {
			"up": (self.up, _("move up to previous entry")),
			"down": (self.down, _("move down to next entry")),
			"left": (self.left, _("move up to first entry")),
			"right": (self.right, _("move down to last entry")),
		}, prio=0, description=_("Network Adapter Setting Actions"))
		self["OkCancelActions"] = HelpableActionMap(self, ["OkCancelActions"], {
			"cancel": (self.close, _("Exit network adapter setup menu")),
			"ok": (self.ok, _("Select menu entry")),
			"red": (self.close, _("Exit network adapter setup menu"))
		}, prio=0, description=_("Network Adapter Setting Actions"))
		self["actions"] = HelpableNumberActionMap(self, ["WizardActions", "ShortcutActions"], {
			"ok": self.ok,
			"back": self.close,
			"up": self.up,
			"down": self.down,
			"red": self.close,
			"left": self.left,
			"right": self.right,
		}, prio=-2, description=_("Network Adapter Setting Actions"))
		self.updateStatusbar()
		self.onClose.append(self.cleanup)
		if not self.selectionChanged in self["menulist"].onSelectionChanged:
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
				system("ifconfig %s up" % self.iface)
				wlanresponse = list(Cell.all(iface))
			except InterfaceError as ie:
				print("[NetworkSetup] queryWirelessDevice InterfaceError: %s" % str(ie))
				return False
			except OSError as xxx_todo_changeme:
				(error_no, error_str) = xxx_todo_changeme.args
				if error_no in (errno.EOPNOTSUPP, errno.ENODEV, errno.EPERM):
					return False
				else:
					print("[NetworkSetup] queryWirelessDevice OSError: %s '%s'" % (error_no, error_str))
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

	def up(self):
		self["menulist"].up()

	def down(self):
		self["menulist"].down()

	def left(self):
		self["menulist"].pageUp()

	def right(self):
		self["menulist"].pageDown()

	def createSummary(self):
		from Screens.PluginBrowser import PluginBrowserSummary
		return PluginBrowserSummary

	def selectionChanged(self):
		if self["menulist"].getCurrent()[1] == "edit":
			self["description"].setText("%s\n\n%s" % (_("Edit the network configuration of your %s %s.") % (BRAND, MODEL), self.oktext))
		if self["menulist"].getCurrent()[1] == "test":
			self["description"].setText("%s\n\n%s" % (_("Test the network configuration of your %s %s.") % (BRAND, MODEL), self.oktext))
		if self["menulist"].getCurrent()[1] == "dns":
			self["description"].setText("%s\n\n%s" % (_("Edit the DNS configuration of your %s %s.") % (BRAND, MODEL), self.oktext))
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
			self["description"].setText("%s\n\n%s" % (_("Set the MAC address of your %s %s.") % (BRAND, MODEL), self.oktext))
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
		menu = [(_("Adapter Settings"), "edit"), (_("Nameserver settings"), "dns"), (_("Network test"), "test"), (_("Restart Network"), "lanrestart")]

		self.extended = None
		self.extendedSetup = None
		for p in plugins.getPlugins(PluginDescriptor.WHERE_NETWORKSETUP):
			callFnc = p.__call__["ifaceSupported"](self.iface)
			if callFnc != None:
				self.extended = callFnc
				if "WlanPluginEntry" in p.__call__:  # Internally used only for WLAN Plugin.
					menu.append((_("Scan wireless networks"), "scanwlan"))
					if iNetwork.getAdapterAttribute(self.iface, "up"):
						menu.append((_("Show WLAN status"), "wlanstatus"))
				else:
					if "menuEntryName" in p.__call__:
						menuEntryName = p.__call__["menuEntryName"](self.iface)
					else:
						menuEntryName = _("Extended Setup...")
					if "menuEntryDescription" in p.__call__:
						menuEntryDescription = p.__call__["menuEntryDescription"](self.iface)
					else:
						menuEntryDescription = _("Extended Networksetup Plugin...")
					self.extendedSetup = ("extendedSetup", menuEntryDescription, self.extended)
					menu.append((menuEntryName, self.extendedSetup))

		if exists(resolveFilename(SCOPE_PLUGINS, "SystemPlugins/NetworkWizard/networkwizard.xml")):
			menu.append((_("Network Wizard"), "openwizard"))
		# Check which boxes support MAC change via the GUI.
		if BoxInfo.getItem("model") not in ("DUMMY",) and self.iface == "eth0":
			menu.append((_("Network MAC settings"), "mac"))

		return menu

	def AdapterSetupClosed(self, *ret):
		if ret != None and len(ret):
			if ret[0] == "ok" and (iNetwork.isWirelessInterface(self.iface) and iNetwork.getAdapterAttribute(self.iface, "up") == True):
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
		if ret != None and len(ret):
			from Plugins.SystemPlugins.WirelessLan.Wlan import iStatus
			iStatus.stopWlanConsole()
			self.updateStatusbar()
			if iNetwork.getAdapterAttribute(self.iface, "up") == True and self.iface in iNetwork.onlyWoWifaces and iNetwork.onlyWoWifaces[self.iface] == True:
				iNetwork.deactivateInterface(self.iface, self.deactivateInterfaceCB)

	def deactivateInterfaceCB(self, data):
		iNetwork.getInterfaces()

	def WlanScanClosed(self, *ret):
		if ret[0] != None:
			self.session.openWithCallback(self.AdapterSetupClosed, AdapterSetup, self.iface, ret[0])
		else:
			from Plugins.SystemPlugins.WirelessLan.Wlan import iStatus
			iStatus.stopWlanConsole()
			self.updateStatusbar()

	def restartLan(self, ret=False):
		if ret == True:
			iNetwork.restartNetwork(self.restartLanDataAvail)
			self.restartLanRef = self.session.openWithCallback(self.restartfinishedCB, MessageBox, _("Please wait while your network is restarting..."), type=MessageBox.TYPE_INFO, enable_input=False)

	def restartLanDataAvail(self, data):
		if data == True:
			iNetwork.getInterfaces(self.getInterfacesDataAvail)

	def getInterfacesDataAvail(self, data):
		if data == True:
			self.restartLanRef.close(True)

	def restartfinishedCB(self, data):
		if data == True:
			self.updateStatusbar()
			self.session.open(MessageBox, _("Finished restarting your network"), type=MessageBox.TYPE_INFO, timeout=10, default=False)

	def dataAvail(self, data):
		self.LinkState = None
		for line in data.splitlines():
			line = line.strip()
			if "Link detected:" in line:
				if "yes" in line:
					self.LinkState = True
				else:
					self.LinkState = False
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
		if data != None:
			if data == True:
				if status != None:
					if status[self.iface]["essid"] == "off" or status[self.iface]["accesspoint"] == "Not-Associated" or status[self.iface]["accesspoint"] == False:
						self.LinkState = False
						self["statuspic"].setPixmapNum(1)
						self["statuspic"].show()
					else:
						self.LinkState = True
						iNetwork.checkNetworkState(self.checkNetworkCB)

	def checkNetworkCB(self, data):
		if iNetwork.getAdapterAttribute(self.iface, "up") == True:
			if self.LinkState == True:
				if data <= 2:
					self["statuspic"].setPixmapNum(0)
				else:
					self["statuspic"].setPixmapNum(1)
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
		if self.oldInterfaceState == False:
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
		if iNetwork.getAdapterAttribute(self.iface, "dhcp") == True:
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
			self["InfoText"].setText(_("This test checks whether your LAN adapter is set up for automatic IP address configuration with DHCP.\nIf you get a \"disabled\" message:\n - then your LAN adapter is configured for manual IP setup\n- verify thay you have entered correct IP informations in the adapter setup dialog.\nIf you get an \"enabled\" message:\n-verify that you have a configured and working DHCP server in your network."))
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
		if data != None:
			if data == True:
				if status != None:
					if status[self.iface]["essid"] == "off" or status[self.iface]["accesspoint"] == "Not-Associated" or status[self.iface]["accesspoint"] == False:
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


class NetworkMountsMenu(Screen, HelpableScreen):
	def __init__(self, session):
		Screen.__init__(self, session)
		HelpableScreen.__init__(self)
		self.setTitle(_("Mount Settings"))
		self.onChangedEntry = []
		self.mainmenu = self.genMainMenu()
		self["menulist"] = MenuList(self.mainmenu)
		self["key_red"] = StaticText(_("Close"))
		self["introduction"] = StaticText()

		self["WizardActions"] = HelpableActionMap(self, "WizardActions",
			{
			"up": (self.up, _("move up to previous entry")),
			"down": (self.down, _("move down to next entry")),
			"left": (self.left, _("move up to first entry")),
			"right": (self.right, _("move down to last entry")),
			})

		self["OkCancelActions"] = HelpableActionMap(self, "OkCancelActions",
			{
			"cancel": (self.close, _("exit mounts setup menu")),
			"ok": (self.ok, _("select menu entry")),
			})

		self["ColorActions"] = HelpableActionMap(self, "ColorActions",
			{
			"red": (self.close, _("exit networkadapter setup menu")),
			})

		self["actions"] = HelpableNumberActionMap(self, ["WizardActions", "ShortcutActions"], {
			"ok": self.ok,
			"back": self.close,
			"up": self.up,
			"down": self.down,
			"red": self.close,
			"left": self.left,
			"right": self.right
		}, prio=-2, description=_("Mount Actions"))

		if not self.selectionChanged in self["menulist"].onSelectionChanged:
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

	def ok(self):
		if self["menulist"].getCurrent()[1][0] == "extendedSetup":
			self.extended = self["menulist"].getCurrent()[1][2]
			self.extended(self.session)

	def up(self):
		self["menulist"].up()

	def down(self):
		self["menulist"].down()

	def left(self):
		self["menulist"].pageUp()

	def right(self):
		self["menulist"].pageDown()

	def genMainMenu(self):
		menu = []
		self.extended = None
		self.extendedSetup = None
		for p in plugins.getPlugins(PluginDescriptor.WHERE_NETWORKMOUNTS):
			callFnc = p.__call__["ifaceSupported"](self)
			if callFnc != None:
				self.extended = callFnc
				if "menuEntryName" in p.__call__:
					menuEntryName = p.__call__["menuEntryName"](self)
				else:
					menuEntryName = _("Extended Setup...")
				if "menuEntryDescription" in p.__call__:
					menuEntryDescription = p.__call__["menuEntryDescription"](self)
				else:
					menuEntryDescription = _("Extended Networksetup Plugin...")
				self.extendedSetup = ("extendedSetup", menuEntryDescription, self.extended)
				menu.append((menuEntryName, self.extendedSetup))
		return menu


class NetworkBaseScreen(Screen, HelpableScreen):
	def __init__(self, session, showLog=False):
		Screen.__init__(self, session)
		HelpableScreen.__init__(self)
		self.service_name = ""
		self.Console = Console()
		self["key_red"] = StaticText(_("Remove Service"))
		self["key_green"] = StaticText(_("Start"))
		self["key_yellow"] = StaticText(_("Autostart"))
		self["key_blue"] = StaticText(_("Show Log") if showLog else "")

	def InstallCheck(self):
		if self.service_name:
			self.Console.ePopen("/usr/bin/opkg list_installed %s" % self.service_name, self.checkNetworkState)

	def checkNetworkState(self, str, retval, extra_args):
		if "Collected errors" in str:
			self.session.openWithCallback(self.close, MessageBox, _("A background update check is in progress, please wait a few minutes and try again."), type=MessageBox.TYPE_INFO, timeout=10, close_on_any_key=True)
		elif not str:
			self.feedscheck = self.session.open(MessageBox, _("Please wait whilst feeds state is checked."), MessageBox.TYPE_INFO, enable_input=False)
			self.feedscheck.setTitle(_("Checking Feeds"))
			cmd1 = "opkg update"
			self.CheckConsole = Console()
			self.CheckConsole.ePopen(cmd1, self.checkNetworkStateFinished)
		else:
			self.updateService()

	def checkNetworkStateFinished(self, result, retval, extra_args=None):
		if "bad address" in result:
			self.session.openWithCallback(self.InstallPackageFailed, MessageBox, _("Your %s %s is not connected to the internet, please check your network settings and try again.") % (BRAND, MODEL), type=MessageBox.TYPE_INFO, timeout=10, close_on_any_key=True)
		elif ("wget returned 1" or "wget returned 255" or "404 Not Found") in result:
			self.session.openWithCallback(self.InstallPackageFailed, MessageBox, _("Sorry feeds are down for maintenance, please try again later."), type=MessageBox.TYPE_INFO, timeout=10, close_on_any_key=True)
		else:
			self.session.openWithCallback(self.InstallPackage, MessageBox, _("Your %s %s will be restarted after the installation of service\nReady to install '%s'?") % (BRAND, MODEL, self.service_name), MessageBox.TYPE_YESNO)

	def InstallPackage(self, val):
		if val:
			self.doInstall(self.installComplete, self.service_name)
		else:
			self.feedscheck.close()
			self.close()

	def InstallPackageFailed(self, val):
		self.feedscheck.close()
		self.close()

	def installComplete(self, result=None, retval=None, extra_args=None):
		self.message.close()
		self.feedscheck.close()
		self.updateService()

	def doInstall(self, callback, pkgname):
		self.message = self.session.open(MessageBox, _("Please wait..."), MessageBox.TYPE_INFO, enable_input=False)
		self.message.setTitle(_("Installing Service"))
		self.Console.ePopen("/usr/bin/opkg install %s" % pkgname, callback)

	def RemovePackage(self, val):
		if val:
			self.doRemove(self.removeComplete, self.service_name)

	def doRemove(self, callback, pkgname):
		self.message = self.session.open(MessageBox, _("Please wait..."), MessageBox.TYPE_INFO, enable_input=False)
		self.message.setTitle(_("Removing Service"))
		self.Console.ePopen("/usr/bin/opkg remove %s --force-remove --autoremove" % pkgname, callback)

	def removeComplete(self, result=None, retval=None, extra_args=None):
		self.message.close()
		self.close()

	def UninstallCheck(self):
		self.Console.ePopen("/usr/bin/opkg list_installed %s" % self.service_name, self.RemovedataAvail)

	def RemovedataAvail(self, str, retval, extra_args):
		if str:
			self.session.openWithCallback(self.RemovePackage, MessageBox, _("Ready to remove '%s'?") % self.service_name, MessageBox.TYPE_YESNO)
		else:
			self.updateService()

	def updateService(self, result=None, retval=None, extra_args=None):
		pass

	def createSummary(self):
		return NetworkServicesSummary


class NetworkAfp(NetworkBaseScreen):
	def __init__(self, session):
		NetworkBaseScreen.__init__(self, session)
		self.setTitle(_("AFP Settings"))
		self.skinName = "NetworkAfp"
		self.onChangedEntry = []
		self["lab1"] = Label(_("Autostart:"))
		self["labactive"] = Label(_(_("Disabled")))
		self["lab2"] = Label(_("Current Status:"))
		self["labstop"] = Label(_("Stopped"))
		self["labrun"] = Label(_("Running"))
		self["status_summary"] = StaticText()
		self["autostartstatus_summary"] = StaticText()
		self.my_afp_active = False
		self.my_afp_run = False
		self["actions"] = HelpableActionMap(self, ["WizardActions", "ColorActions"], {
			"ok": self.close,
			"back": self.close,
			"red": self.UninstallCheck,
			"green": self.AfpStartStop,
			"yellow": self.activateAfp
		}, prio=0, description=_("AFP Actions"))
		self.service_name = "%s-appletalk netatalk" % BASE_GROUP
		self.onLayoutFinish.append(self.InstallCheck)

	def installComplete(self, result=None, retval=None, extra_args=None):
		self.session.open(TryQuitMainloop, 2)

	def RemovedataAvail(self, str, retval, extra_args):
		if str:
			self.session.openWithCallback(self.RemovePackage, MessageBox, _("Your %s %s will be restarted after the removal of service\nDo you want to remove now?") % (BRAND, MODEL), MessageBox.TYPE_YESNO, widowTitle=_("Ready to remove '%s'?") % self.service_name)
		else:
			self.updateService()

	def removeComplete(self, result=None, retval=None, extra_args=None):
		self.session.open(TryQuitMainloop, 2)

	def AfpStartStop(self):
		if not self.my_afp_run:
			self.Console.ePopen("/etc/init.d/atalk start", self.StartStopCallback)
		elif self.my_afp_run:
			self.Console.ePopen("/etc/init.d/atalk stop", self.StartStopCallback)

	def StartStopCallback(self, result=None, retval=None, extra_args=None):
		time.sleep(3)
		self.updateService()

	def activateAfp(self):
		if fileExists("/etc/rc2.d/S20atalk"):
			self.Console.ePopen("update-rc.d -f atalk remove", self.StartStopCallback)
		else:
			self.Console.ePopen("update-rc.d -f atalk defaults", self.StartStopCallback)

	def updateService(self, result=None, retval=None, extra_args=None):
		import process
		p = process.ProcessList()
		afp_process = str(p.named("afpd")).strip("[]")
		self["labrun"].hide()
		self["labstop"].hide()
		self["labactive"].setText(_("Disabled"))
		self.my_afp_active = False
		self.my_afp_run = False
		if fileExists("/etc/rc2.d/S20atalk"):
			self["labactive"].setText(_("Enabled"))
			self["labactive"].show()
			self.my_afp_active = True
		if afp_process:
			self.my_afp_run = True
		if self.my_afp_run:
			self["labstop"].hide()
			self["labactive"].show()
			self["labrun"].show()
			self["key_green"].setText(_("Stop"))
			status_summary = "%s %s" % (self["lab2"].text, self["labrun"].text)
		else:
			self["labrun"].hide()
			self["labstop"].show()
			self["labactive"].show()
			self["key_green"].setText(_("Start"))
			status_summary = "%s %s" % (self["lab2"].text, self["labstop"].text)
		title = _("AFP Settings")
		autostartstatus_summary = "%s %s" % (self["lab1"].text, self["labactive"].text)

		for cb in self.onChangedEntry:
			cb(title, status_summary, autostartstatus_summary)


class NetworkSABnzbd(NetworkBaseScreen):
	def __init__(self, session):
		NetworkBaseScreen.__init__(self, session)
		self.setTitle(_("SABnzbd Settings"))
		self.skinName = "NetworkSABnzbd"
		self.onChangedEntry = []
		self["lab1"] = Label(_("Autostart:"))
		self["labactive"] = Label(_(_("Disabled")))
		self["lab2"] = Label(_("Current Status:"))
		self["labstop"] = Label(_("Stopped"))
		self["labrun"] = Label(_("Running"))
		self["status_summary"] = StaticText()
		self["autostartstatus_summary"] = StaticText()
		self.my_sabnzbd_active = False
		self.my_sabnzbd_run = False
		self["actions"] = HelpableActionMap(self, ["WizardActions", "ColorActions"], {
			"ok": self.close,
			"back": self.close,
			"red": self.UninstallCheck,
			"green": self.SABnzbStartStop,
			"yellow": self.activateSABnzbd
		}, prio=0, description=_("SABnzbd Actions"))
		self.service_name = ("sabnzbd3" if sys.version_info[0] >= 3 else "sabnzbd")
		self.onLayoutFinish.append(self.InstallCheck)

	def checkNetworkStateFinished(self, result, retval, extra_args=None):
		if (float(getVersionString()) < 3.0 and result.find("mipsel/Packages.gz, wget returned 1") != -1) or (float(getVersionString()) >= 3.0 and result.find("mips32el/Packages.gz, wget returned 1") != -1):
			self.session.openWithCallback(self.InstallPackageFailed, MessageBox, _("Sorry feeds are down for maintenance, please try again later."), type=MessageBox.TYPE_INFO, timeout=10, close_on_any_key=True)
		elif result.find("bad address") != -1:
			self.session.openWithCallback(self.InstallPackageFailed, MessageBox, _("Your %s %s is not connected to the internet, please check your network settings and try again.") % (BRAND, MODEL), type=MessageBox.TYPE_INFO, timeout=10, close_on_any_key=True)
		else:
			self.session.openWithCallback(self.InstallPackage, MessageBox, _("Ready to install '%s'?") % self.service_name, MessageBox.TYPE_YESNO)

	def SABnzbStartStop(self):
		if not self.my_sabnzbd_run:
			self.Console.ePopen("/etc/init.d/sabnzbd start")
			time.sleep(3)
			self.updateService()
		elif self.my_sabnzbd_run:
			self.Console.ePopen("/etc/init.d/sabnzbd stop")
			time.sleep(3)
			self.updateService()

	def activateSABnzbd(self):
		if fileExists("/etc/rc2.d/S20sabnzbd"):
			self.Console.ePopen("update-rc.d -f sabnzbd remove")
		else:
			self.Console.ePopen("update-rc.d -f sabnzbd defaults")
		time.sleep(3)
		self.updateService()

	def updateService(self, result=None, retval=None, extra_args=None):
		import process
		p = process.ProcessList()
		sabnzbd_processpy = str(p.named("SABnzbd.py")).strip("[]")
		sabnzbd_processpyc = str(p.named("SABnzbd.pyc")).strip("[]")
		self["labrun"].hide()
		self["labstop"].hide()
		self["labactive"].setText(_("Disabled"))
		self.my_sabnzbd_active = False
		self.my_sabnzbd_run = False
		if fileExists("/etc/rc2.d/S20sabnzbd"):
			self["labactive"].setText(_("Enabled"))
			self["labactive"].show()
			self.my_sabnzbd_active = True
		if sabnzbd_processpy or sabnzbd_processpyc:
			self.my_sabnzbd_run = True
		if self.my_sabnzbd_run:
			self["labstop"].hide()
			self["labactive"].show()
			self["labrun"].show()
			self["key_green"].setText(_("Stop"))
			status_summary = "%s %s" % (self["lab2"].text, self["labrun"].text)
		else:
			self["labrun"].hide()
			self["labstop"].show()
			self["labactive"].show()
			self["key_green"].setText(_("Start"))
			status_summary = "%s %s" % (self["lab2"].text, self["labstop"].text)
		title = _("SABnzbd Settings")
		autostartstatus_summary = "%s %s" % (self["lab1"].text, self["labactive"].text)
		for cb in self.onChangedEntry:
			cb(title, status_summary, autostartstatus_summary)


class NetworkFtp(NetworkBaseScreen):
	def __init__(self, session):
		NetworkBaseScreen.__init__(self, session)
		self.setTitle(_("FTP Settings"))
		self.skinName = "NetworkSamba"
		self.onChangedEntry = []
		self["lab1"] = Label(_("Autostart:"))
		self["labactive"] = Label(_(_("Disabled")))
		self["lab2"] = Label(_("Current Status:"))
		self["labstop"] = Label(_("Stopped"))
		self["labrun"] = Label(_("Running"))
		self["key_red"].setText("")
		self.my_ftp_active = False
		self.my_ftp_run = False
		self["actions"] = HelpableActionMap(self, ["WizardActions", "ColorActions"], {
			"ok": self.close,
			"back": self.close,
			"green": self.FtpStartStop,
			"yellow": self.activateFtp
		}, prio=0, description=_("FTP Actions"))
		self.onLayoutFinish.append(self.updateService)

	def createSummary(self):
		return NetworkServicesSummary

	def FtpStartStop(self):
		commands = []
		if not self.my_ftp_run:
			commands.append("/etc/init.d/vsftpd start")
		elif self.my_ftp_run:
			commands.append("/etc/init.d/vsftpd stop")
		self.Console.eBatch(commands, self.StartStopCallback, debug=True)

	def StartStopCallback(self, result=None, retval=None, extra_args=None):
		time.sleep(3)
		self.updateService()

	def activateFtp(self):
		commands = []
		if len(glob("/etc/rc2.d/S*0vsftpd")):
		# if fileExists("/etc/rc2.d/S20vsftpd"):
			commands.append("update-rc.d -f vsftpd remove")
		else:
			commands.append("update-rc.d -f vsftpd defaults")
		self.Console.eBatch(commands, self.StartStopCallback, debug=True)

	def updateService(self):
		import process
		p = process.ProcessList()
		ftp_process = str(p.named("vsftpd")).strip("[]")
		self["labrun"].hide()
		self["labstop"].hide()
		self["labactive"].setText(_("Disabled"))
		self.my_ftp_active = False
		if len(glob("/etc/rc2.d/S*0vsftpd")):
		# if fileExists("/etc/rc2.d/S20vsftpd"):
			self["labactive"].setText(_("Enabled"))
			self["labactive"].show()
			self.my_ftp_active = True

		self.my_ftp_run = False
		if ftp_process:
			self.my_ftp_run = True
		if self.my_ftp_run:
			self["labstop"].hide()
			self["labactive"].show()
			self["labrun"].show()
			self["key_green"].setText(_("Stop"))
			status_summary = "%s %s" % (self["lab2"].text, self["labrun"].text)
		else:
			self["labrun"].hide()
			self["labstop"].show()
			self["labactive"].show()
			self["key_green"].setText(_("Start"))
			status_summary = "%s %s" % (self["lab2"].text, self["labstop"].text)
		title = _("FTP Settings")
		autostartstatus_summary = "%s %s" % (self["lab1"].text, self["labactive"].text)

		for cb in self.onChangedEntry:
			cb(title, status_summary, autostartstatus_summary)


class NetworkNfs(NetworkBaseScreen):
	def __init__(self, session):
		NetworkBaseScreen.__init__(self, session)
		self.setTitle(_("NFS Settings"))
		self.skinName = "NetworkNfs"
		self.onChangedEntry = []
		self["lab1"] = Label(_("Autostart:"))
		self["labactive"] = Label(_(_("Disabled")))
		self["lab2"] = Label(_("Current Status:"))
		self["labstop"] = Label(_("Stopped"))
		self["labrun"] = Label(_("Running"))
		self.my_nfs_active = False
		self.my_nfs_run = False
		self["actions"] = HelpableActionMap(self, ["WizardActions", "ColorActions"], {
			"ok": self.close,
			"back": self.close,
			"red": self.UninstallCheck,
			"green": self.NfsStartStop,
			"yellow": self.Nfsset
		}, prio=0, description=_("NFS Actions"))
		self.service_name = "%s-nfs" % BASE_GROUP
		self.onLayoutFinish.append(self.InstallCheck)

	def installComplete(self, result=None, retval=None, extra_args=None):
		self.session.open(TryQuitMainloop, 2)

	def RemovedataAvail(self, str, retval, extra_args):
		if str:
			self.session.openWithCallback(self.RemovePackage, MessageBox, _("Your %s %s will be restarted after the removal of service\nDo you want to remove now?") % (BRAND, MODEL), MessageBox.TYPE_YESNO, windowTitle=_("Ready to remove '%s'?") % self.service_name)
		else:
			self.updateService()

	def removeComplete(self, result=None, retval=None, extra_args=None):
		self.session.open(TryQuitMainloop, 2)

	def NfsStartStop(self):
		if not self.my_nfs_run:
			self.Console.ePopen("/etc/init.d/nfsserver start", self.StartStopCallback)
		elif self.my_nfs_run:
			self.Console.ePopen("/etc/init.d/nfsserver stop", self.StartStopCallback)

	def StartStopCallback(self, result=None, retval=None, extra_args=None):
		time.sleep(3)
		self.updateService()

	def Nfsset(self):
		if fileExists("/etc/rc2.d/S11nfsserver") or fileExists("/etc/rc2.d/S13nfsserver") or fileExists("/etc/rc2.d/S20nfsserver"):
			self.Console.ePopen("update-rc.d -f nfsserver remove", self.StartStopCallback)
		else:
			self.Console.ePopen("update-rc.d -f nfsserver defaults 13", self.StartStopCallback)

	def updateService(self):
		import process
		p = process.ProcessList()
		nfs_process = str(p.named("nfsd")).strip("[]")
		self["labrun"].hide()
		self["labstop"].hide()
		self["labactive"].setText(_("Disabled"))
		self.my_nfs_active = False
		self.my_nfs_run = False
		if fileExists("/etc/rc2.d/S13nfsserver"):
			self["labactive"].setText(_("Enabled"))
			self["labactive"].show()
			self.my_nfs_active = True
		if nfs_process:
			self.my_nfs_run = True
		if self.my_nfs_run:
			self["labstop"].hide()
			self["labrun"].show()
			self["key_green"].setText(_("Stop"))
			status_summary = "%s %s" % (self["lab2"].text, self["labrun"].text)
		else:
			self["labstop"].show()
			self["labrun"].hide()
			self["key_green"].setText(_("Start"))
			status_summary = "%s %s" % (self["lab2"].text, self["labstop"].text)
		title = _("NFS Settings")
		autostartstatus_summary = "%s %s" % (self["lab1"].text, self["labactive"].text)

		for cb in self.onChangedEntry:
			cb(title, status_summary, autostartstatus_summary)


class NetworkOpenvpn(NetworkBaseScreen):
	def __init__(self, session):
		NetworkBaseScreen.__init__(self, session, showLog=True)
		self.setTitle(_("OpenVPN Settings"))
		self.skinName = "NetworkOpenvpn"
		self.onChangedEntry = []
		self["lab1"] = Label(_("Autostart:"))
		self["labactive"] = Label(_(_("Disabled")))
		self["lab2"] = Label(_("Current Status:"))
		self["labstop"] = Label(_("Stopped"))
		self["labrun"] = Label(_("Running"))
		self["labconfig"] = Label(_("Config file name (ok to change):"))
		self["labconfigfilename"] = Label(_("default"))
		self.config_file = ""
		self.my_vpn_active = False
		self.my_vpn_run = False
		self["actions"] = HelpableActionMap(self, ["WizardActions", "ColorActions"], {
			"ok": self.inputconfig,
			"back": self.close,
			"red": self.UninstallCheck,
			"green": self.VpnStartStop,
			"yellow": self.activateVpn,
			"blue": self.Vpnshowlog
		}, prio=0, description=_("OpenVPN Actions"))
		self.service_name = "openvpn"
		self.onLayoutFinish.append(self.InstallCheck)

	def Vpnshowlog(self):
		self.session.open(NetworkLogScreen, title=_("OpenVpn Log"), logPath="/etc/openvpn/openvpn.log")

	def VpnStartStop(self):
		if not self.my_vpn_run:
			self.Console.ePopen("/etc/init.d/openvpn start %s" % self.config_file, self.StartStopCallback)
		elif self.my_vpn_run:
			self.Console.ePopen("/etc/init.d/openvpn stop", self.StartStopCallback)

	def StartStopCallback(self, result=None, retval=None, extra_args=None):
		time.sleep(3)
		self.updateService()

	def activateVpn(self):
		if fileExists("/etc/rc2.d/S20openvpn"):
			self.Console.ePopen("update-rc.d -f openvpn remove", self.StartStopCallback)
		else:
			self.Console.ePopen("update-rc.d -f openvpn defaults", self.StartStopCallback)

	def updateService(self):
		import process
		p = process.ProcessList()
		openvpn_process = str(p.named("openvpn")).strip("[]")
		self["labrun"].hide()
		self["labstop"].hide()
		self["labactive"].setText(_("Disabled"))
		self.my_Vpn_active = False
		self.my_vpn_run = False
		if fileExists("/etc/rc2.d/S20openvpn"):
			self["labactive"].setText(_("Enabled"))
			self["labactive"].show()
			self.my_Vpn_active = True
		if openvpn_process:
			self.my_vpn_run = True
		if self.my_vpn_run:
			self["labstop"].hide()
			self["labrun"].show()
			self["key_green"].setText(_("Stop"))
			status_summary = "%s %s" % (self["lab2"].text, self["labrun"].text)
		else:
			self["labstop"].show()
			self["labrun"].hide()
			self["key_green"].setText(_("Start"))
			status_summary = "%s %s" % (self["lab2"].text, self["labstop"].text)
		title = _("OpenVPN Settings")
		autostartstatus_summary = "%s %s" % (self["lab1"].text, self["labactive"].text)
		self["labconfig"].show()
		for cb in self.onChangedEntry:
			cb(title, status_summary, autostartstatus_summary)

	def inputconfig(self):
		self.session.openWithCallback(self.askForWord, InputBox, title=_("Input config file name:"), text=" " * 20, maxSize=20, type=Input.TEXT)

	def askForWord(self, word):
		if word is None:
			pass
		else:
			self.config_file = _(word)
			self["labconfigfilename"].setText(self.config_file)


class NetworkSamba(NetworkBaseScreen):
	def __init__(self, session):
		NetworkBaseScreen.__init__(self, session, showLog=True)
		self.setTitle(_("Samba Setup"))
		self.skinName = "NetworkSamba"
		self.onChangedEntry = []
		self["lab1"] = Label(_("Autostart:"))
		self["labactive"] = Label(_(_("Disabled")))
		self["lab2"] = Label(_("Current Status:"))
		self["labstop"] = Label(_("Stopped"))
		self["labrun"] = Label(_("Running"))
		self.my_Samba_active = False
		self.my_Samba_run = False
		self["actions"] = HelpableActionMap(self, ["WizardActions", "ColorActions"], {
			"ok": self.close,
			"back": self.close,
			"red": self.UninstallCheck,
			"green": self.SambaStartStop,
			"yellow": self.activateSamba,
			"blue": self.Sambashowlog
		}, prio=0, description=_("Samba Actions"))
		self.service_name = "%s-smbfs-server" % BASE_GROUP
		self.onLayoutFinish.append(self.InstallCheck)

	def QuestionCallback(self, val):
		if val:
			self.session.openWithCallback(self.InstallPackage, MessageBox, _("Do you want to also install samba client ?\nThis allows you to mount your windows shares on this device."), MessageBox.TYPE_YESNO)
		else:
			self.feedscheck.close()
			self.close()

	def InstallPackage(self, val):
		if val:
			self.service_name = "%s %s-smbfs-client" % (self.service_name, BASE_GROUP)
		self.doInstall(self.installComplete, self.service_name)

	def installComplete(self, result=None, retval=None, extra_args=None):
		self.session.open(TryQuitMainloop, 2)

	def UninstallCheck(self):
		self.service_name = "%s %s-smbfs-client" % (self.service_name, BASE_GROUP)
		self.Console.ePopen("/usr/bin/opkg list_installed %s" % self.service_name, self.RemovedataAvail)

	def RemovedataAvail(self, str, retval, extra_args):
		if str:
			self.session.openWithCallback(self.RemovePackage, MessageBox, _("Your %s %s will be restarted after the removal of service.\nDo you want to remove now?") % (BRAND, MODEL), MessageBox.TYPE_YESNO, windowTitle=_("Ready to remove '%s'?") % self.service_name)
		else:
			self.updateService()

	def Sambashowlog(self):
		self.session.open(NetworkLogScreen, title=_("Samba Log"), logPath="/var/log/samba/log.smbd")

	def SambaStartStop(self):
		commands = []
		if not self.my_Samba_run:
			commands.append("/etc/init.d/samba start")
		elif self.my_Samba_run:
			commands.append("/etc/init.d/samba stop")
			commands.append("killall nmbd")
			commands.append("killall smbd")
		self.Console.eBatch(commands, self.StartStopCallback, debug=True)

	def StartStopCallback(self, result=None, retval=None, extra_args=None):
		time.sleep(3)
		self.updateService()

	def activateSamba(self):
		commands = []
		if fileExists("/etc/rc2.d/S20samba"):
			commands.append("update-rc.d -f samba remove")
		else:
			commands.append("update-rc.d -f samba defaults")
		self.Console.eBatch(commands, self.StartStopCallback, debug=True)

	def updateService(self):
		import process
		p = process.ProcessList()
		samba_process = str(p.named("smbd")).strip("[]")
		self["labrun"].hide()
		self["labstop"].hide()
		self["labactive"].setText(_("Disabled"))
		self.my_Samba_active = False
		if fileExists("/etc/rc2.d/S20samba"):
			self["labactive"].setText(_("Enabled"))
			self["labactive"].show()
			self.my_Samba_active = True

		self.my_Samba_run = False
		if samba_process:
			self.my_Samba_run = True
		if self.my_Samba_run:
			self["labstop"].hide()
			self["labactive"].show()
			self["labrun"].show()
			self["key_green"].setText(_("Stop"))
			status_summary = "%s %s" % (self["lab2"].text, self["labrun"].text)
		else:
			self["labrun"].hide()
			self["labstop"].show()
			self["labactive"].show()
			self["key_green"].setText(_("Start"))
			status_summary = "%s %s" % (self["lab2"].text, self["labstop"].text)
		title = _("Samba Setup")
		autostartstatus_summary = "%s %s" % (self["lab1"].text, self["labactive"].text)

		for cb in self.onChangedEntry:
			cb(title, status_summary, autostartstatus_summary)


class NetworkTelnet(NetworkBaseScreen):
	def __init__(self, session):
		NetworkBaseScreen.__init__(self, session)
		self.setTitle(_("Telnet Settings"))
		self.skinName = "NetworkSamba"
		self.onChangedEntry = []
		self["lab1"] = Label(_("Autostart:"))
		self["labactive"] = Label(_(_("Disabled")))
		self["lab2"] = Label(_("Current Status:"))
		self["labstop"] = Label(_("Stopped"))
		self["labrun"] = Label(_("Running"))
		self.my_telnet_active = False
		self.my_telnet_run = False
		self["actions"] = HelpableActionMap(self, ["WizardActions", "ColorActions"], {
			"ok": self.close,
			"back": self.close,
			"green": self.TelnetStartStop,
			"yellow": self.activateTelnet
		}, prio=0, description=_("Telnet Actions"))

	def createSummary(self):
		return NetworkServicesSummary

	def TelnetStartStop(self):
		commands = []
		if fileExists("/etc/init.d/telnetd.busybox"):
			if self.my_telnet_run:
				commands.append("/etc/init.d/telnetd.busybox stop")
			else:
				commands.append("/bin/su -l -c \"/etc/init.d/telnetd.busybox start\"")
			self.Console.eBatch(commands, self.StartStopCallback, debug=True)

	def StartStopCallback(self, result=None, retval=None, extra_args=None):
		time.sleep(3)
		self.updateService()

	def activateTelnet(self):
		commands = []
		if fileExists("/etc/init.d/telnetd.busybox"):
			if fileExists("/etc/rc2.d/S20telnetd.busybox"):
				commands.append("update-rc.d -f telnetd.busybox remove")
			else:
				commands.append("update-rc.d -f telnetd.busybox defaults")
		self.Console.eBatch(commands, self.StartStopCallback, debug=True)

	def updateService(self):
		import process
		p = process.ProcessList()
		telnet_process = str(p.named("telnetd")).strip("[]")
		self["labrun"].hide()
		self["labstop"].hide()
		self["labactive"].setText(_("Disabled"))
		self.my_telnet_active = False
		self.my_telnet_run = False
		if fileExists("/etc/rc2.d/S20telnetd.busybox"):
			self["labactive"].setText(_("Enabled"))
			self["labactive"].show()
			self.my_telnet_active = True

		if telnet_process:
			self.my_telnet_run = True
		if self.my_telnet_run:
			self["labstop"].hide()
			self["labactive"].show()
			self["labrun"].show()
			self["key_green"].setText(_("Stop"))
			status_summary = "%s %s" % (self["lab2"].text, self["labrun"].text)
		else:
			self["labrun"].hide()
			self["labstop"].show()
			self["labactive"].show()
			self["key_green"].setText(_("Start"))
			status_summary = "%s %s" % (self["lab2"].text, self["labstop"].text)
		title = _("Telnet Settings")
		autostartstatus_summary = "%s %s" % (self["lab1"].text, self["labactive"].text)

		for cb in self.onChangedEntry:
			cb(title, status_summary, autostartstatus_summary)


class NetworkInadyn(NetworkBaseScreen):
	def __init__(self, session):
		NetworkBaseScreen.__init__(self, session, showLog=True)
		self.setTitle(_("Inadyn Settings"))
		self.onChangedEntry = []
		self["autostart"] = Label(_("Autostart:"))
		self["labactive"] = Label(_(_("Active")))
		self["labdisabled"] = Label(_(_("Disabled")))
		self["status"] = Label(_("Current Status:"))
		self["labstop"] = Label(_("Stopped"))
		self["labrun"] = Label(_("Running"))
		self["time"] = Label(_("Time Update in Minutes:"))
		self["labtime"] = Label()
		self["username"] = Label("%s:" % _("Username"))
		self["labuser"] = Label()
		self["password"] = Label("%s:" % _("Password"))
		self["labpass"] = Label()
		self["alias"] = Label("%s:" % _("Alias"))
		self["labalias"] = Label()
		self["sactive"] = Pixmap()
		self["sinactive"] = Pixmap()
		self["system"] = Label("%s:" % _("System"))
		self["labsys"] = Label()
		self["actions"] = HelpableActionMap(self, ["WizardActions", "ColorActions", "SetupActions"], {
			"ok": self.setupinadyn,
			"back": self.close,
			"menu": self.setupinadyn,
			"red": self.UninstallCheck,
			"green": self.InadynStartStop,
			"yellow": self.autostart,
			"blue": self.inaLog
		}, prio=0, description=_("Inadyn Actions"))
		self.service_name = "inadyn-mt"
		self.onLayoutFinish.append(self.InstallCheck)

	def InadynStartStop(self):
		if not self.my_inadyn_run:
			self.Console.ePopen("/etc/init.d/inadyn-mt start", self.StartStopCallback)
		elif self.my_inadyn_run:
			self.Console.ePopen("/etc/init.d/inadyn-mt stop", self.StartStopCallback)

	def StartStopCallback(self, result=None, retval=None, extra_args=None):
		time.sleep(3)
		self.updateService()

	def autostart(self):
		if fileExists("/etc/rc2.d/S20inadyn-mt"):
			self.Console.ePopen("update-rc.d -f inadyn-mt remove", self.StartStopCallback)
		else:
			self.Console.ePopen("update-rc.d -f inadyn-mt defaults", self.StartStopCallback)

	def updateService(self):
		import process
		p = process.ProcessList()
		inadyn_process = str(p.named("inadyn-mt")).strip("[]")
		self["labrun"].hide()
		self["labstop"].hide()
		self["labactive"].hide()
		self["labdisabled"].hide()
		self["sactive"].hide()
		self.my_inadyn_active = False
		self.my_inadyn_run = False
		if fileExists("/etc/rc2.d/S20inadyn-mt"):
			self["labdisabled"].hide()
			self["labactive"].show()
			self.my_inadyn_active = True
			autostartstatus_summary = "%s %s" % (self["autostart"].text, self["labactive"].text)
		else:
			self["labactive"].hide()
			self["labdisabled"].show()
			autostartstatus_summary = "%s %s" % (self["autostart"].text, self["labdisabled"].text)
		if inadyn_process:
			self.my_inadyn_run = True
		if self.my_inadyn_run:
			self["labstop"].hide()
			self["labrun"].show()
			self["key_green"].setText(_("Stop"))
			status_summary = "%s %s" % (self["status"].text, self["labrun"].text)
		else:
			self["labstop"].show()
			self["labrun"].hide()
			self["key_green"].setText(_("Start"))
			status_summary = "%s %s" % (self["status"].text, self["labstop"].text)

		# self.my_nabina_state = False
		if fileExists("/etc/inadyn.conf"):
			f = open("/etc/inadyn.conf", "r")
			for line in f.readlines():
				line = line.strip()
				if line.startswith("username "):
					line = line[9:]
					self["labuser"].setText(line)
				elif line.startswith("password "):
					line = line[9:]
					self["labpass"].setText(line)
				elif line.startswith("alias "):
					line = line[6:]
					self["labalias"].setText(line)
				elif line.startswith("update_period_sec "):
					line = line[18:]
					line = (int(line) // 60)
					self["labtime"].setText(str(line))
				elif line.startswith("dyndns_system ") or line.startswith("#dyndns_system "):
					if line.startswith("#"):
						line = line[15:]
						self["sactive"].hide()
					else:
						line = line[14:]
						self["sactive"].show()
					self["labsys"].setText(line)
			f.close()
		title = _("Inadyn Settings")

		for cb in self.onChangedEntry:
			cb(title, status_summary, autostartstatus_summary)

	def setupinadyn(self):
		self.session.openWithCallback(self.updateService, NetworkInadynSetup)

	def inaLog(self):
		self.session.open(NetworkLogScreen, title=_("Inadyn Log"), logPath="/var/log/inadyn.log", tailLog=False)


class NetworkInadynSetup(Screen, ConfigListScreen):
	def __init__(self, session):
		Screen.__init__(self, session)
		self.onChangedEntry = []
		self.list = []
		ConfigListScreen.__init__(self, self.list, session=session, on_change=self.selectionChanged)
		self.setTitle(_("Inadyn Settings"))
		self["key_red"] = Label(_("Save"))
		self["actions"] = HelpableActionMap(self, ["WizardActions", "ColorActions", "VirtualKeyboardActions"], {
			"red": self.saveIna,
			"back": self.close,
			"showVirtualKeyboard": self.KeyText
		}, prio=0, description=_("Inadyn Setting Actions"))
		self["HelpWindow"] = Pixmap()
		self["HelpWindow"].hide()
		self.updateList()
		if not self.selectionChanged in self["config"].onSelectionChanged:
			self["config"].onSelectionChanged.append(self.selectionChanged)

	def createSummary(self):
		from Screens.PluginBrowser import PluginBrowserSummary
		return PluginBrowserSummary

	def selectionChanged(self):
		item = self["config"].getCurrent()
		if item:
			name = str(item[0])
			desc = str(item[1].value)
		else:
			name = ""
			desc = ""
		for cb in self.onChangedEntry:
			cb(name, desc)

	def updateList(self):
		self.ina_user = NoSave(ConfigText(fixed_size=False))
		self.ina_pass = NoSave(ConfigText(fixed_size=False))
		self.ina_alias = NoSave(ConfigText(fixed_size=False))
		self.ina_period = NoSave(ConfigNumber())
		self.ina_sysactive = NoSave(ConfigYesNo(default=False))
		self.ina_system = NoSave(ConfigSelection(default="dyndns@dyndns.org", choices=[("dyndns@dyndns.org", "dyndns@dyndns.org"), ("statdns@dyndns.org", "statdns@dyndns.org"), ("custom@dyndns.org", "custom@dyndns.org"), ("default@no-ip.com", "default@no-ip.com")]))

		if fileExists("/etc/inadyn.conf"):
			f = open("/etc/inadyn.conf", "r")
			for line in f.readlines():
				line = line.strip()
				if line.startswith("username "):
					line = line[9:]
					self.ina_user.value = line
					ina_user1 = getConfigListEntry("%s:" % _("Username"), self.ina_user)
					self.list.append(ina_user1)
				elif line.startswith("password "):
					line = line[9:]
					self.ina_pass.value = line
					ina_pass1 = getConfigListEntry("%s:" % _("Password"), self.ina_pass)
					self.list.append(ina_pass1)
				elif line.startswith("alias "):
					line = line[6:]
					self.ina_alias.value = line
					ina_alias1 = getConfigListEntry("%s:" % _("Alias"), self.ina_alias)
					self.list.append(ina_alias1)
				elif line.startswith("update_period_sec "):
					line = line[18:]
					line = (int(line) // 60)
					self.ina_period.value = line
					ina_period1 = getConfigListEntry("%s:" % _("Time update in minutes"), self.ina_period)
					self.list.append(ina_period1)
				elif line.startswith("dyndns_system ") or line.startswith("#dyndns_system "):
					if not line.startswith("#"):
						self.ina_sysactive.value = True
						line = line[14:]
					else:
						self.ina_sysactive.value = False
						line = line[15:]
					ina_sysactive1 = getConfigListEntry("%s:" % _("Set system"), self.ina_sysactive)
					self.list.append(ina_sysactive1)
					self.ina_value = line
					ina_system1 = getConfigListEntry("%s:" % _("System"), self.ina_system)
					self.list.append(ina_system1)

			f.close()
		self["config"].list = self.list

	def KeyText(self):
		sel = self["config"].getCurrent()
		if sel:
			if isinstance(self["config"].getCurrent()[1], ConfigText) or isinstance(self["config"].getCurrent()[1], ConfigPassword):
				if self["config"].getCurrent()[1].help_window.instance != None:
					self["config"].getCurrent()[1].help_window.hide()
			self.vkvar = sel[0]
			if self.vkvar == "%s:" % _("Username") or self.vkvar == "%s:" % _("Password") or self.vkvar == "%s:" % _("Alias") or self.vkvar == "%s:" % _("System"):
				from Screens.VirtualKeyBoard import VirtualKeyBoard
				self.session.openWithCallback(self.VirtualKeyBoardCallback, VirtualKeyBoard, title=self["config"].getCurrent()[0], text=self["config"].getCurrent()[1].value)

	def VirtualKeyBoardCallback(self, callback=None):
		if callback != None and len(callback):
			self["config"].getCurrent()[1].setValue(callback)
			self["config"].invalidate(self["config"].getCurrent())

	def saveIna(self):
		if fileExists("/etc/inadyn.conf"):
			inme = open("/etc/inadyn.conf", "r")
			out = open("/etc/inadyn.conf.tmp", "w")
			for line in inme.readlines():
				line = line.replace("\n", "")
				if line.startswith("username "):
					line = ("username %s" % self.ina_user.value.strip())
				elif line.startswith("password "):
					line = ("password %s" % self.ina_pass.value.strip())
				elif line.startswith("alias "):
					line = ("alias %s" % self.ina_alias.value.strip())
				elif line.startswith("update_period_sec "):
					strview = (self.ina_period.value * 60)
					strview = str(strview)
					line = ("update_period_sec %s" % strview)
				elif line.startswith("dyndns_system ") or line.startswith("#dyndns_system "):
					if self.ina_sysactive.value:
						line = ("dyndns_system %s" % self.ina_system.value.strip())
					else:
						line = ("#dyndns_system %s" % self.ina_system.value.strip())
				out.write(("%s\n" % line))
			out.close()
			inme.close()
		else:
			self.session.open(MessageBox, _("Sorry Inadyn Config is Missing"), MessageBox.TYPE_INFO)
			self.close()
		if fileExists("/etc/inadyn.conf.tmp"):
			rename("/etc/inadyn.conf.tmp", "/etc/inadyn.conf")
		self.myStop()

	def myStop(self):
		self.close()


config.networkushare = ConfigSubsection()
config.networkushare.mediafolders = NoSave(ConfigLocations(default=None))


class NetworkuShare(NetworkBaseScreen):
	def __init__(self, session):
		NetworkBaseScreen.__init__(self, session, showLog=True)
		self.setTitle(_("uShare Settings"))
		self.onChangedEntry = []
		self["autostart"] = Label(_("Autostart:"))
		self["labactive"] = Label(_(_("Active")))
		self["labdisabled"] = Label(_(_("Disabled")))
		self["status"] = Label(_("Current Status:"))
		self["labstop"] = Label(_("Stopped"))
		self["labrun"] = Label(_("Running"))
		self["username"] = Label("%s:" % _("uShare Name"))
		self["labuser"] = Label()
		self["iface"] = Label("%s:" % _("Interface"))
		self["labiface"] = Label()
		self["port"] = Label("%s:" % _("uShare Port"))
		self["labport"] = Label()
		self["telnetport"] = Label("%s:" % _("Telnet Port"))
		self["labtelnetport"] = Label()
		self["sharedir"] = Label("%s:" % _("Share Folders"))
		self["labsharedir"] = Label()
		self["web"] = Label("%s:" % _("Web Interface"))
		self["webactive"] = Pixmap()
		self["webinactive"] = Pixmap()
		self["telnet"] = Label("%s:" % _("Telnet Interface"))
		self["telnetactive"] = Pixmap()
		self["telnetinactive"] = Pixmap()
		self["xbox"] = Label("%s:" % _("XBox 360 support"))
		self["xboxactive"] = Pixmap()
		self["xboxinactive"] = Pixmap()
		self["dlna"] = Label("%s:" % _("DLNA support"))
		self["dlnaactive"] = Pixmap()
		self["dlnainactive"] = Pixmap()
		self["actions"] = HelpableActionMap(self, ["WizardActions", "ColorActions", "SetupActions"], {
			"ok": self.setupushare,
			"back": self.close,
			"menu": self.setupushare,
			"red": self.UninstallCheck,
			"green": self.uShareStartStop,
			"yellow": self.autostart,
			"blue": self.ushareLog
		}, prio=0, description=_("uShare Actions"))
		self.service_name = "ushare"
		self.onLayoutFinish.append(self.InstallCheck)

	def uShareStartStop(self):
		if not self.my_ushare_run:
			self.Console.ePopen("/etc/init.d/ushare start >> /tmp/uShare.log", self.StartStopCallback)
		elif self.my_ushare_run:
			self.Console.ePopen("/etc/init.d/ushare stop >> /tmp/uShare.log", self.StartStopCallback)

	def StartStopCallback(self, result=None, retval=None, extra_args=None):
		time.sleep(3)
		self.updateService()

	def autostart(self):
		if fileExists("/etc/rc2.d/S20ushare"):
			self.Console.ePopen("update-rc.d -f ushare remove", self.StartStopCallback)
		else:
			self.Console.ePopen("update-rc.d -f ushare defaults", self.StartStopCallback)

	def updateService(self):
		import process
		p = process.ProcessList()
		ushare_process = str(p.named("ushare")).strip("[]")
		self["labrun"].hide()
		self["labstop"].hide()
		self["labactive"].hide()
		self["labdisabled"].hide()
		self.my_ushare_active = False
		self.my_ushare_run = False
		if not fileExists("/tmp/uShare.log"):
			f = open("/tmp/uShare.log", "w")
			f.write("")
			f.close()
		if fileExists("/etc/rc2.d/S20ushare"):
			self["labdisabled"].hide()
			self["labactive"].show()
			self.my_ushare_active = True
			autostartstatus_summary = "%s %s" % (self["autostart"].text, self["labactive"].text)
		else:
			self["labactive"].hide()
			self["labdisabled"].show()
			autostartstatus_summary = "%s %s" % (self["autostart"].text, self["labdisabled"].text)
		if ushare_process:
			self.my_ushare_run = True
		if self.my_ushare_run:
			self["labstop"].hide()
			self["labrun"].show()
			self["key_green"].setText(_("Stop"))
			status_summary = "%s %s" % (self["status"].text, self["labstop"].text)
		else:
			self["labstop"].show()
			self["labrun"].hide()
			self["key_green"].setText(_("Start"))
			status_summary = "%s %s" % (self["status"].text, self["labstop"].text)

		if fileExists("/etc/ushare.conf"):
			f = open("/etc/ushare.conf", "r")
			for line in f.readlines():
				line = line.strip()
				if line.startswith("USHARE_NAME="):
					line = line[12:]
					self["labuser"].setText(line)
				elif line.startswith("USHARE_IFACE="):
					line = line[13:]
					self["labiface"].setText(line)
				elif line.startswith("USHARE_PORT="):
					line = line[12:]
					self["labport"].setText(line)
				elif line.startswith("USHARE_TELNET_PORT="):
					line = line[19:]
					self["labtelnetport"].setText(line)
				elif line.startswith("USHARE_DIR="):
					line = line[11:]
					self.mediafolders = line
					self["labsharedir"].setText(line)
				elif line.startswith("ENABLE_WEB="):
					if line[11:] == "no":
						self["webactive"].hide()
						self["webinactive"].show()
					else:
						self["webactive"].show()
						self["webinactive"].hide()
				elif line.startswith("ENABLE_TELNET="):
					if line[14:] == "no":
						self["telnetactive"].hide()
						self["telnetinactive"].show()
					else:
						self["telnetactive"].show()
						self["telnetinactive"].hide()
				elif line.startswith("ENABLE_XBOX="):
					if line[12:] == "no":
						self["xboxactive"].hide()
						self["xboxinactive"].show()
					else:
						self["xboxactive"].show()
						self["xboxinactive"].hide()
				elif line.startswith("ENABLE_DLNA="):
					if line[12:] == "no":
						self["dlnaactive"].hide()
						self["dlnainactive"].show()
					else:
						self["dlnaactive"].show()
						self["dlnainactive"].hide()
			f.close()
		title = _("uShare Settings")

		for cb in self.onChangedEntry:
			cb(title, status_summary, autostartstatus_summary)

	def setupushare(self):
		self.session.openWithCallback(self.updateService, NetworkuShareSetup)

	def ushareLog(self):
		self.session.open(NetworkLogScreen, title=_("uShare Log"), logPath="/tmp/uShare.log")


class NetworkuShareSetup(Screen, ConfigListScreen):
	def __init__(self, session):
		Screen.__init__(self, session)
		self.onChangedEntry = []
		self.list = []
		ConfigListScreen.__init__(self, self.list, session=session, on_change=self.selectionChanged)
		self.setTitle(_("uShare Settings"))
		self["key_red"] = Label(_("Save"))
		self["key_green"] = Label(_("Shares"))
		self["actions"] = HelpableActionMap(self, ["WizardActions", "ColorActions", "VirtualKeyboardActions"], {
			"red": self.saveuShare,
			"green": self.selectfolders,
			"back": self.close,
			"showVirtualKeyboard": self.KeyText
		}, prio=0, description=_("uShare Setting Actions"))
		self["HelpWindow"] = Pixmap()
		self["HelpWindow"].hide()
		self.updateList()
		if not self.selectionChanged in self["config"].onSelectionChanged:
			self["config"].onSelectionChanged.append(self.selectionChanged)

	def createSummary(self):
		from Screens.PluginBrowser import PluginBrowserSummary
		return PluginBrowserSummary

	def selectionChanged(self):
		item = self["config"].getCurrent()
		if item:
			name = str(item[0])
			desc = str(item[1].value)
		else:
			name = ""
			desc = ""
		for cb in self.onChangedEntry:
			cb(name, desc)

	def updateList(self, ret=None):
		self.list = []
		self.ushare_user = NoSave(ConfigText(default=BoxInfo.getItem("model"), fixed_size=False))
		self.ushare_iface = NoSave(ConfigText(fixed_size=False))
		self.ushare_port = NoSave(ConfigNumber())
		self.ushare_telnetport = NoSave(ConfigNumber())
		self.ushare_web = NoSave(ConfigYesNo(default=True))
		self.ushare_telnet = NoSave(ConfigYesNo(default=True))
		self.ushare_xbox = NoSave(ConfigYesNo(default=True))
		self.ushare_ps3 = NoSave(ConfigYesNo(default=True))
		self.ushare_system = NoSave(ConfigSelection(default="dyndns@dyndns.org", choices=[("dyndns@dyndns.org", "dyndns@dyndns.org"), ("statdns@dyndns.org", "statdns@dyndns.org"), ("custom@dyndns.org", "custom@dyndns.org")]))

		if fileExists("/etc/ushare.conf"):
			f = open("/etc/ushare.conf", "r")
			for line in f.readlines():
				line = line.strip()
				if line.startswith("USHARE_NAME="):
					line = line[12:]
					self.ushare_user.value = line
					ushare_user1 = getConfigListEntry("%s:" % _("uShare Name"), self.ushare_user)
					self.list.append(ushare_user1)
				elif line.startswith("USHARE_IFACE="):
					line = line[13:]
					self.ushare_iface.value = line
					ushare_iface1 = getConfigListEntry("%s:" % _("Interface"), self.ushare_iface)
					self.list.append(ushare_iface1)
				elif line.startswith("USHARE_PORT="):
					line = line[12:]
					self.ushare_port.value = line
					ushare_port1 = getConfigListEntry("%s:" % _("uShare Port"), self.ushare_port)
					self.list.append(ushare_port1)
				elif line.startswith("USHARE_TELNET_PORT="):
					line = line[19:]
					self.ushare_telnetport.value = line
					ushare_telnetport1 = getConfigListEntry("%s:" % _("Telnet Port"), self.ushare_telnetport)
					self.list.append(ushare_telnetport1)
				elif line.startswith("ENABLE_WEB="):
					if line[11:] == "no":
						self.ushare_web.value = False
					else:
						self.ushare_web.value = True
					ushare_web1 = getConfigListEntry("%s:" % _("Web Interface"), self.ushare_web)
					self.list.append(ushare_web1)
				elif line.startswith("ENABLE_TELNET="):
					if line[14:] == "no":
						self.ushare_telnet.value = False
					else:
						self.ushare_telnet.value = True
					ushare_telnet1 = getConfigListEntry("%s:" % _("Telnet Interface"), self.ushare_telnet)
					self.list.append(ushare_telnet1)
				elif line.startswith("ENABLE_XBOX="):
					if line[12:] == "no":
						self.ushare_xbox.value = False
					else:
						self.ushare_xbox.value = True
					ushare_xbox1 = getConfigListEntry("%s:" % _("XBox 360 support"), self.ushare_xbox)
					self.list.append(ushare_xbox1)
				elif line.startswith("ENABLE_DLNA="):
					if line[12:] == "no":
						self.ushare_ps3.value = False
					else:
						self.ushare_ps3.value = True
					ushare_ps31 = getConfigListEntry("%s:" % _("DLNA support"), self.ushare_ps3)
					self.list.append(ushare_ps31)
			f.close()
		self["config"].list = self.list

	def KeyText(self):
		sel = self["config"].getCurrent()
		if sel:
			if isinstance(self["config"].getCurrent()[1], ConfigText) or isinstance(self["config"].getCurrent()[1], ConfigPassword):
				if self["config"].getCurrent()[1].help_window.instance != None:
					self["config"].getCurrent()[1].help_window.hide()
			self.vkvar = sel[0]
			if self.vkvar == "%s:" % _("uShare Name") or self.vkvar == "%s:" % _("Share Folders"):
				from Screens.VirtualKeyBoard import VirtualKeyBoard
				self.session.openWithCallback(self.VirtualKeyBoardCallback, VirtualKeyBoard, title=self["config"].getCurrent()[0], text=self["config"].getCurrent()[1].value)

	def VirtualKeyBoardCallback(self, callback=None):
		if callback != None and len(callback):
			self["config"].getCurrent()[1].setValue(callback)
			self["config"].invalidate(self["config"].getCurrent())

	def saveuShare(self):
		if fileExists("/etc/ushare.conf"):
			inme = open("/etc/ushare.conf", "r")
			out = open("/etc/ushare.conf.tmp", "w")
			for line in inme.readlines():
				line = line.replace("\n", "")
				if line.startswith("USHARE_NAME="):
					line = ("USHARE_NAME=%s" % self.ushare_user.value.strip())
				elif line.startswith("USHARE_IFACE="):
					line = ("USHARE_IFACE=%s" % self.ushare_iface.value.strip())
				elif line.startswith("USHARE_PORT="):
					line = ("USHARE_PORT=%s" % str(self.ushare_port.value))
				elif line.startswith("USHARE_TELNET_PORT="):
					line = ("USHARE_TELNET_PORT=%s" % str(self.ushare_telnetport.value))
				elif line.startswith("USHARE_DIR="):
					line = ("USHARE_DIR=%s" % ", ".join(config.networkushare.mediafolders.value))
				elif line.startswith("ENABLE_WEB="):
					if not self.ushare_web.value:
						line = "ENABLE_WEB=no"
					else:
						line = "ENABLE_WEB=yes"
				elif line.startswith("ENABLE_TELNET="):
					if not self.ushare_telnet.value:
						line = "ENABLE_TELNET=no"
					else:
						line = "ENABLE_TELNET=yes"
				elif line.startswith("ENABLE_XBOX="):
					if not self.ushare_xbox.value:
						line = "ENABLE_XBOX=no"
					else:
						line = "ENABLE_XBOX=yes"
				elif line.startswith("ENABLE_DLNA="):
					if not self.ushare_ps3.value:
						line = "ENABLE_DLNA=no"
					else:
						line = "ENABLE_DLNA=yes"
				out.write(("%s\n" % line))
			out.close()
			inme.close()
		else:
			open("/tmp/uShare.log", "a").write("%s\n" % _("Sorry uShare Config is Missing"))
			self.session.open(MessageBox, _("Sorry uShare Config is Missing"), MessageBox.TYPE_INFO)
			self.close()
		if fileExists("/etc/ushare.conf.tmp"):
			rename("/etc/ushare.conf.tmp", "/etc/ushare.conf")
		self.myStop()

	def myStop(self):
		self.close()

	def selectfolders(self):
		try:
			self["config"].getCurrent()[1].help_window.hide()
		except:
			pass
		self.session.openWithCallback(self.updateList, uShareSelection)


class uShareSelection(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		self.setTitle(_("Select Folders"))
		self["key_red"] = StaticText(_("Cancel"))
		self["key_green"] = StaticText(_("Save"))
		self["key_yellow"] = StaticText()
		if fileExists("/etc/ushare.conf"):
			f = open("/etc/ushare.conf", "r")
			for line in f.readlines():
				line = line.strip()
				if line.startswith("USHARE_DIR="):
					line = line[11:]
					self.mediafolders = line
		self.selectedFiles = [str(n) for n in self.mediafolders.split(", ")]
		defaultDir = "/media/"
		self.filelist = MultiFileSelectList(self.selectedFiles, defaultDir, showFiles=False)
		self["checkList"] = self.filelist
		self["actions"] = HelpableActionMap(self, ["DirectionActions", "OkCancelActions", "ShortcutActions"], {
			"cancel": self.exit,
			"red": self.exit,
			"yellow": self.changeSelectionState,
			"green": self.saveSelection,
			"ok": self.okClicked,
			"left": self.left,
			"right": self.right,
			"down": self.down,
			"up": self.up
		}, prio=-1, description=_("uShare Selection Actions"))
		if not self.selectionChanged in self["checkList"].onSelectionChanged:
			self["checkList"].onSelectionChanged.append(self.selectionChanged)
		self.onLayoutFinish.append(self.layoutFinished)

	def layoutFinished(self):
		idx = 0
		self["checkList"].moveToIndex(idx)
		self.selectionChanged()

	def selectionChanged(self):
		current = self["checkList"].getCurrent()[0]
		if current[2] == True:
			self["key_yellow"].setText(_("Deselect"))
		else:
			self["key_yellow"].setText(_("Select"))

	def up(self):
		self["checkList"].up()

	def down(self):
		self["checkList"].down()

	def left(self):
		self["checkList"].pageUp()

	def right(self):
		self["checkList"].pageDown()

	def changeSelectionState(self):
		self["checkList"].changeSelectionState()
		self.selectedFiles = self["checkList"].getSelectedList()

	def saveSelection(self):
		self.selectedFiles = self["checkList"].getSelectedList()
		config.networkushare.mediafolders.value = self.selectedFiles
		self.close(None)

	def exit(self):
		self.close(None)

	def okClicked(self):
		if self.filelist.canDescent():
			self.filelist.descent()


config.networkminidlna = ConfigSubsection()
config.networkminidlna.mediafolders = NoSave(ConfigLocations(default=None))


class NetworkMiniDLNA(NetworkBaseScreen):
	def __init__(self, session):
		NetworkBaseScreen.__init__(self, session, showLog=True)
		self.setTitle(_("MiniDLNA Settings"))
		self.onChangedEntry = []
		self["autostart"] = Label(_("Autostart:"))
		self["labactive"] = Label(_(_("Active")))
		self["labdisabled"] = Label(_(_("Disabled")))
		self["status"] = Label(_("Current Status:"))
		self["labstop"] = Label(_("Stopped"))
		self["labrun"] = Label(_("Running"))
		self["username"] = Label("%s:" % _("Name"))
		self["labuser"] = Label()
		self["iface"] = Label("%s:" % _("Interface"))
		self["labiface"] = Label()
		self["port"] = Label("%s:" % _("Port"))
		self["labport"] = Label()
		self["serialno"] = Label("%s:" % _("Serial No"))
		self["labserialno"] = Label()
		self["sharedir"] = Label("%s:" % _("Share Folders"))
		self["labsharedir"] = Label()
		self["inotify"] = Label("%s:" % _("Inotify Monitoring"))
		self["inotifyactive"] = Pixmap()
		self["inotifyinactive"] = Pixmap()
		self["tivo"] = Label("%s:" % _("TiVo support"))
		self["tivoactive"] = Pixmap()
		self["tivoinactive"] = Pixmap()
		self["dlna"] = Label("%s:" % _("Strict DLNA"))
		self["dlnaactive"] = Pixmap()
		self["dlnainactive"] = Pixmap()
		self["actions"] = HelpableActionMap(self, ["WizardActions", "ColorActions", "SetupActions"], {
			"ok": self.setupminidlna,
			"back": self.close,
			"menu": self.setupminidlna,
			"red": self.UninstallCheck,
			"green": self.MiniDLNAStartStop,
			"yellow": self.autostart,
			"blue": self.minidlnaLog
		}, prio=0, description=_("Mini DLNA Actions"))
		self.service_name = "minidlna"
		self.onLayoutFinish.append(self.InstallCheck)

	def MiniDLNAStartStop(self):
		if not self.my_minidlna_run:
			self.Console.ePopen("/etc/init.d/minidlna start", self.StartStopCallback)
		elif self.my_minidlna_run:
			self.Console.ePopen("/etc/init.d/minidlna stop", self.StartStopCallback)

	def StartStopCallback(self, result=None, retval=None, extra_args=None):
		time.sleep(3)
		self.updateService()

	def autostart(self):
		if fileExists("/etc/rc2.d/S20minidlna"):
			self.Console.ePopen("update-rc.d -f minidlna remove", self.StartStopCallback)
		else:
			self.Console.ePopen("update-rc.d -f minidlna defaults", self.StartStopCallback)

	def updateService(self):
		import process
		p = process.ProcessList()
		minidlna_process = str(p.named("minidlnad")).strip("[]")
		self["labrun"].hide()
		self["labstop"].hide()
		self["labactive"].hide()
		self["labdisabled"].hide()
		self.my_minidlna_active = False
		self.my_minidlna_run = False
		if fileExists("/etc/rc2.d/S20minidlna"):
			self["labdisabled"].hide()
			self["labactive"].show()
			self.my_minidlna_active = True
			autostartstatus_summary = "%s %s" % (self["autostart"].text, self["labactive"].text)
		else:
			self["labactive"].hide()
			self["labdisabled"].show()
			autostartstatus_summary = "%s %s" % (self["autostart"].text, self["labdisabled"].text)
		if minidlna_process:
			self.my_minidlna_run = True
		if self.my_minidlna_run:
			self["labstop"].hide()
			self["labrun"].show()
			self["key_green"].setText(_("Stop"))
			status_summary = "%s %s" % (self["status"].text, self["labstop"].text)
		else:
			self["labstop"].show()
			self["labrun"].hide()
			self["key_green"].setText(_("Start"))
			status_summary = "%s %s" % (self["status"].text, self["labstop"].text)

		if fileExists("/etc/minidlna.conf"):
			f = open("/etc/minidlna.conf", "r")
			for line in f.readlines():
				line = line.strip()
				if line.startswith("friendly_name="):
					line = line[14:]
					self["labuser"].setText(line)
				elif line.startswith("network_interface="):
					line = line[18:]
					self["labiface"].setText(line)
				elif line.startswith("port="):
					line = line[5:]
					self["labport"].setText(line)
				elif line.startswith("serial="):
					line = line[7:]
					self["labserialno"].setText(line)
				elif line.startswith("media_dir="):
					line = line[10:]
					self.mediafolders = line
					self["labsharedir"].setText(line)
				elif line.startswith("inotify="):
					if line[8:] == "no":
						self["inotifyactive"].hide()
						self["inotifyinactive"].show()
					else:
						self["inotifyactive"].show()
						self["inotifyinactive"].hide()
				elif line.startswith("enable_tivo="):
					if line[12:] == "no":
						self["tivoactive"].hide()
						self["tivoinactive"].show()
					else:
						self["tivoactive"].show()
						self["tivoinactive"].hide()
				elif line.startswith("strict_dlna="):
					if line[12:] == "no":
						self["dlnaactive"].hide()
						self["dlnainactive"].show()
					else:
						self["dlnaactive"].show()
						self["dlnainactive"].hide()
			f.close()
		title = _("MiniDLNA Settings")

		for cb in self.onChangedEntry:
			cb(title, status_summary, autostartstatus_summary)

	def setupminidlna(self):
		self.session.openWithCallback(self.updateService, NetworkMiniDLNASetup)

	def minidlnaLog(self):
		self.session.open(NetworkLogScreen, title=_("MiniDLNA Log"), logPath="/var/volatile/log/minidlna.log")


class NetworkMiniDLNASetup(Screen, ConfigListScreen):
	def __init__(self, session):
		Screen.__init__(self, session)
		self.onChangedEntry = []
		self.list = []
		ConfigListScreen.__init__(self, self.list, session=session, on_change=self.selectionChanged)
		self.setTitle(_("MiniDLNA Settings"))
		self.skinName = "NetworkuShareSetup"
		self["key_red"] = Label(_("Save"))
		self["key_green"] = Label(_("Shares"))
		self["actions"] = HelpableActionMap(self, ["WizardActions", "ColorActions", "VirtualKeyboardActions"], {
			"red": self.saveMinidlna,
			"green": self.selectfolders,
			"back": self.close,
			"showVirtualKeyboard": self.KeyText
		}, prio=0, description=_("Mini DLNA Setting Actions"))
		self["HelpWindow"] = Pixmap()
		self["HelpWindow"].hide()
		self.updateList()
		if not self.selectionChanged in self["config"].onSelectionChanged:
			self["config"].onSelectionChanged.append(self.selectionChanged)

	def createSummary(self):
		from Screens.PluginBrowser import PluginBrowserSummary
		return PluginBrowserSummary

	def selectionChanged(self):
		item = self["config"].getCurrent()
		if item:
			name = str(item[0])
			desc = str(item[1].value)
		else:
			name = ""
			desc = ""
		for cb in self.onChangedEntry:
			cb(name, desc)

	def updateList(self, ret=None):
		self.list = []
		self.minidlna_name = NoSave(ConfigText(default=BoxInfo.getItem("model"), fixed_size=False))
		self.minidlna_iface = NoSave(ConfigText(fixed_size=False))
		self.minidlna_port = NoSave(ConfigNumber())
		self.minidlna_serialno = NoSave(ConfigNumber())
		self.minidlna_web = NoSave(ConfigYesNo(default=True))
		self.minidlna_inotify = NoSave(ConfigYesNo(default=True))
		self.minidlna_tivo = NoSave(ConfigYesNo(default=True))
		self.minidlna_strictdlna = NoSave(ConfigYesNo(default=True))
		if fileExists("/etc/minidlna.conf"):
			f = open("/etc/minidlna.conf", "r")
			for line in f.readlines():
				line = line.strip()
				if line.startswith("friendly_name="):
					line = line[14:]
					self.minidlna_name.value = line
					minidlna_name1 = getConfigListEntry("%s:" % _("Name"), self.minidlna_name)
					self.list.append(minidlna_name1)
				elif line.startswith("network_interface="):
					line = line[18:]
					self.minidlna_iface.value = line
					minidlna_iface1 = getConfigListEntry("%s:" % _("Interface"), self.minidlna_iface)
					self.list.append(minidlna_iface1)
				elif line.startswith("port="):
					line = line[5:]
					self.minidlna_port.value = line
					minidlna_port1 = getConfigListEntry("%s:" % _("Port"), self.minidlna_port)
					self.list.append(minidlna_port1)
				elif line.startswith("serial="):
					line = line[7:]
					self.minidlna_serialno.value = line
					minidlna_serialno1 = getConfigListEntry("%s:" % _("Serial No"), self.minidlna_serialno)
					self.list.append(minidlna_serialno1)
				elif line.startswith("inotify="):
					self.minidlna_inotify.value = line[8:] != "no"
					minidlna_inotify1 = getConfigListEntry("%s:" % _("Inotify Monitoring"), self.minidlna_inotify)
					self.list.append(minidlna_inotify1)
				elif line.startswith("enable_tivo="):
					self.minidlna_tivo.value = line[12:] != "no"
					minidlna_tivo1 = getConfigListEntry("%s:" % _("TiVo support"), self.minidlna_tivo)
					self.list.append(minidlna_tivo1)
				elif line.startswith("strict_dlna="):
					self.minidlna_strictdlna.value = line[12:] != "no"
					minidlna_strictdlna1 = getConfigListEntry("%s:" % _("Strict DLNA"), self.minidlna_strictdlna)
					self.list.append(minidlna_strictdlna1)
			f.close()
		self["config"].list = self.list

	def KeyText(self):
		sel = self["config"].getCurrent()
		if sel:
			if isinstance(self["config"].getCurrent()[1], ConfigText) or isinstance(self["config"].getCurrent()[1], ConfigPassword):
				if self["config"].getCurrent()[1].help_window.instance != None:
					self["config"].getCurrent()[1].help_window.hide()
			self.vkvar = sel[0]
			if self.vkvar == "%s:" % _("Name") or self.vkvar == "%s:" % _("Share Folders"):
				from Screens.VirtualKeyBoard import VirtualKeyBoard
				self.session.openWithCallback(self.VirtualKeyBoardCallback, VirtualKeyBoard, title=self["config"].getCurrent()[0], text=self["config"].getCurrent()[1].value)

	def VirtualKeyBoardCallback(self, callback=None):
		if callback != None and len(callback):
			self["config"].getCurrent()[1].setValue(callback)
			self["config"].invalidate(self["config"].getCurrent())

	def saveMinidlna(self):
		if fileExists("/etc/minidlna.conf"):
			inme = open("/etc/minidlna.conf", "r")
			out = open("/etc/minidlna.conf.tmp", "w")
			for line in inme.readlines():
				line = line.replace("\n", "")
				if line.startswith("friendly_name="):
					line = ("friendly_name=%s" % self.minidlna_name.value.strip())
				elif line.startswith("network_interface="):
					line = ("network_interface=%s" % self.minidlna_iface.value.strip())
				elif line.startswith("port="):
					line = ("port=%s" % str(self.minidlna_port.value))
				elif line.startswith("serial="):
					line = ("serial=%s" % str(self.minidlna_serialno.value))
				elif line.startswith("media_dir="):
					line = ("media_dir=%s" % ", ".join(config.networkminidlna.mediafolders.value))
				elif line.startswith("inotify="):
					line = "inotify=yes" if self.minidlna_inotify.value else "inotify=no"
				elif line.startswith("enable_tivo="):
					line = "enable_tivo=yes" if self.minidlna_tivo.value else "enable_tivo=no"
				elif line.startswith("strict_dlna="):
					line = "strict_dlna=yes" if self.minidlna_strictdlna.value else "strict_dlna=no"
				out.write(("%s\n" % line))
			out.close()
			inme.close()
		else:
			self.session.open(MessageBox, _("Sorry MiniDLNA Config is Missing"), MessageBox.TYPE_INFO)
			self.close()
		if fileExists("/etc/minidlna.conf.tmp"):
			rename("/etc/minidlna.conf.tmp", "/etc/minidlna.conf")
		self.myStop()

	def myStop(self):
		self.close()

	def selectfolders(self):
		try:
			self["config"].getCurrent()[1].help_window.hide()
		except:
			pass
		self.session.openWithCallback(self.updateList, MiniDLNASelection)


class MiniDLNASelection(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		self.setTitle(_("Select Folders"))
		self.skinName = "uShareSelection"
		self["key_red"] = StaticText(_("Cancel"))
		self["key_green"] = StaticText(_("Save"))
		self["key_yellow"] = StaticText()

		if fileExists("/etc/minidlna.conf"):
			f = open("/etc/minidlna.conf", "r")
			for line in f.readlines():
				line = line.strip()
				if line.startswith("media_dir="):
					line = line[11:]
					self.mediafolders = line
		self.selectedFiles = [str(n) for n in self.mediafolders.split(", ")]
		defaultDir = "/media/"
		self.filelist = MultiFileSelectList(self.selectedFiles, defaultDir, showFiles=False)
		self["checkList"] = self.filelist
		self["actions"] = HelpableActionMap(self, ["DirectionActions", "OkCancelActions", "ShortcutActions"], {
			"cancel": self.exit,
			"red": self.exit,
			"yellow": self.changeSelectionState,
			"green": self.saveSelection,
			"ok": self.okClicked,
			"left": self.left,
			"right": self.right,
			"down": self.down,
			"up": self.up
		}, prio=-1, description=_("Mini DLNA Setting Actions"))
		if not self.selectionChanged in self["checkList"].onSelectionChanged:
			self["checkList"].onSelectionChanged.append(self.selectionChanged)
		self.onLayoutFinish.append(self.layoutFinished)

	def layoutFinished(self):
		idx = 0
		self["checkList"].moveToIndex(idx)
		self.selectionChanged()

	def selectionChanged(self):
		current = self["checkList"].getCurrent()[0]
		if current[2] == True:
			self["key_yellow"].setText(_("Deselect"))
		else:
			self["key_yellow"].setText(_("Select"))

	def up(self):
		self["checkList"].up()

	def down(self):
		self["checkList"].down()

	def left(self):
		self["checkList"].pageUp()

	def right(self):
		self["checkList"].pageDown()

	def changeSelectionState(self):
		self["checkList"].changeSelectionState()
		self.selectedFiles = self["checkList"].getSelectedList()

	def saveSelection(self):
		self.selectedFiles = self["checkList"].getSelectedList()
		config.networkminidlna.mediafolders.value = self.selectedFiles
		self.close(None)

	def exit(self):
		self.close(None)

	def okClicked(self):
		if self.filelist.canDescent():
			self.filelist.descent()


class NetworkServicesSummary(Screen):
	def __init__(self, session, parent):
		Screen.__init__(self, session, parent=parent)
		self["title"] = StaticText("")
		self["status_summary"] = StaticText("")
		self["autostartstatus_summary"] = StaticText("")
		self.onShow.append(self.addWatcher)
		self.onHide.append(self.removeWatcher)

	def addWatcher(self):
		self.parent.onChangedEntry.append(self.selectionChanged)
		self.parent.updateService()

	def removeWatcher(self):
		self.parent.onChangedEntry.remove(self.selectionChanged)

	def selectionChanged(self, title, status_summary, autostartstatus_summary):
		self["title"].text = title
		self["status_summary"].text = status_summary
		self["autostartstatus_summary"].text = autostartstatus_summary


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
			self.session.open(MessageBox, _("Error: The new password may not be blank!"), MessageBox.TYPE_ERROR)
			return
		# print("[NetworkSetup] NetworkPassword: Changing the password for '%s' to '%s'." % (self.user, password))
		print("[NetworkSetup] NetworkPassword: Changing the password for '%s'." % self.user)
		self.container = eConsoleAppContainer()
		self.container.dataAvail.append(self.dataAvail)
		self.container.appClosed.append(self.appClosed)
		status = self.container.execute(*("/usr/bin/passwd", "/usr/bin/passwd", self.user))
		if status:  # If status is -1 code is already/still running, is status is -3 code can not be started!
			self.session.open(MessageBox, _("Error %d: Unable to start 'passwd' command!") % status, MessageBox.TYPE_ERROR)
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
		# print("[NetworkSetup] DEBUG NetworkPassword: data='%s'." % data)
		if data.endswith("password: "):
			self.container.write("%s\n" % config.network.password.value)
			self.counter += 1

	def appClosed(self, retVal=ETIMEDOUT):
		self.timer.stop()
		if retVal:
			if retVal == ETIMEDOUT:
				self.container.kill()
			print("[NetworkSetup] NetworkPassword: Error %d: Unable to change password!  (%s)" % (retVal, strerror(retVal)))
			self.session.open(MessageBox, _("Error %d: Unable to change password!  (%s)") % (retVal, strerror(retVal)), MessageBox.TYPE_ERROR)
		elif self.counter == 2:
			print("[NetworkSetup] NetworkPassword: Password changed.")
			self.session.open(MessageBox, _("Password changed."), MessageBox.TYPE_INFO, timeout=5)
			Setup.keySave(self)
		else:
			print("[NetworkSetup] NetworkPassword: Error: Unexpected program interaction!")
			self.session.open(MessageBox, _("Error: Interaction failure, unable to change password!"), MessageBox.TYPE_ERROR)
		del self.container.dataAvail[:]
		del self.container.appClosed[:]
		del self.container


class NetworkSATPI(NetworkBaseScreen):
	def __init__(self, session):
		NetworkBaseScreen.__init__(self, session)
		self.setTitle(_("SATPI Settings"))
		self.skinName = "NetworkSATPI"
		self.onChangedEntry = []
		self["lab1"] = Label(_("Autostart:"))
		self["labactive"] = Label(_(_("Disabled")))
		self["lab2"] = Label(_("Current Status:"))
		self["labstop"] = Label(_("Stopped"))
		self["labrun"] = Label(_("Running"))
		self["status_summary"] = StaticText()
		self["autostartstatus_summary"] = StaticText()
		self.my_satpi_active = False
		self.my_satpi_run = False
		self["actions"] = HelpableActionMap(self, ["WizardActions", "ColorActions"], {
			"ok": self.close,
			"back": self.close,
			"red": self.UninstallCheck,
			"green": self.SATPIStartStop,
			"yellow": self.activateSATPI
		}, prio=0, description=_("SATPI Setting Actions"))
		self.service_name = "satpi"
		self.onLayoutFinish.append(self.InstallCheck)

	def checkNetworkStateFinished(self, result, retval, extra_args=None):
		if (float(getVersionString()) < 3.0 and result.find("mipsel/Packages.gz, wget returned 1") != -1) or (float(getVersionString()) >= 3.0 and result.find("mips32el/Packages.gz, wget returned 1") != -1):
			self.session.openWithCallback(self.InstallPackageFailed, MessageBox, _("Sorry feeds are down for maintenance, please try again later."), type=MessageBox.TYPE_INFO, timeout=10, close_on_any_key=True)
		elif result.find("bad address") != -1:
			self.session.openWithCallback(self.InstallPackageFailed, MessageBox, _("Your %s %s is not connected to the internet, please check your network settings and try again.") % (BRAND, MODEL), type=MessageBox.TYPE_INFO, timeout=10, close_on_any_key=True)
		else:
			self.session.openWithCallback(self.InstallPackage, MessageBox, _("Ready to install '%s'?") % self.service_name, MessageBox.TYPE_YESNO)

	def removeComplete(self, result=None, retval=None, extra_args=None):
		self.message.close()
		self.updateService()

	def createSummary(self):
		return NetworkServicesSummary

	def SATPIStartStop(self):
		if not self.my_satpi_run:
			self.Console.ePopen("/etc/init.d/satpi start")
			time.sleep(3)
			self.updateService()
		elif self.my_satpi_run:
			self.Console.ePopen("/etc/init.d/satpi stop")
			time.sleep(3)
			self.updateService()

	def activateSATPI(self):
		if fileExists("/etc/rc2.d/S80satpi"):
			self.Console.ePopen("update-rc.d -f satpi remove")
		else:
			self.Console.ePopen("update-rc.d -f satpi defaults 80")
		time.sleep(3)
		self.updateService()

	def updateService(self, result=None, retval=None, extra_args=None):
		import process
		p = process.ProcessList()
		satpi_process = str(p.named("satpi")).strip("[]")
		self["labrun"].hide()
		self["labstop"].hide()
		self["labactive"].setText(_("Disabled"))
		self.my_satpi_active = False
		self.my_satpi_run = False
		if fileExists("/etc/rc2.d/S80satpi"):
			self["labactive"].setText(_("Enabled"))
			self["labactive"].show()
			self.my_satpi_active = True
		if satpi_process:
			self.my_satpi_run = True
		if self.my_satpi_run:
			self["labstop"].hide()
			self["labactive"].show()
			self["labrun"].show()
			self["key_green"].setText(_("Stop"))
			status_summary = "%s %s" % (self["lab2"].text, self["labrun"].text)
		else:
			self["labrun"].hide()
			self["labstop"].show()
			self["labactive"].show()
			self["key_green"].setText(_("Start"))
			status_summary = "%s %s" % (self["lab2"].text, self["labstop"].text)
		title = _("SATPI Settings")
		autostartstatus_summary = "%s %s" % (self["lab1"].text, self["labactive"].text)
		for cb in self.onChangedEntry:
			cb(title, status_summary, autostartstatus_summary)


# TODO "NetworkInadynLog" skin?
#
class NetworkLogScreen(Screen):
	def __init__(self, session, title="", skinName="NetworkInadynLog", logPath="", tailLog=True):
		Screen.__init__(self, session)
		self.setTitle(title)
		self.skinName = [skinName, "NetworkLogScreen"]
		self.tailLog = tailLog
		self.console = Console()
		self["infotext"] = ScrollLabel("")
		self["actions"] = HelpableActionMap(self, ["CancelSaveActions", "OkActions", "NavigationActions"], {
			"cancel": (self.keyCancel, _("Close the screen")),
			"close": (self.closeRecursive, _("Close the screen and exit all menus")),
			"ok": (self.keyCancel, _("Close the screen")),
			"top": (self["infotext"].moveTop, _("Move to first line / screen")),
			"pageUp": (self["infotext"].pageUp, _("Move up a screen")),
			"left": (self["infotext"].pageUp, _("Move up a screen")),
			"right": (self["infotext"].pageDown, _("Move down a screen")),
			"up": (self["infotext"].moveUp, _("Move up a line")),
			"down": (self["infotext"].moveDown, _("Move down a line")),
			"pageDown": (self["infotext"].pageDown, _("Move down a screen")),
			"bottom": (self["infotext"].moveBottom, _("Move to last line / screen"))
		}, prio=0, description=_("Network Log Actions"))
		strview = ""
		self.logfile = logPath
		if self.tailLog:
			self.console.ePopen(["/usr/bin/tail", "/usr/bin/tail", logPath], self.showLog)
		else:
			self.showLog()

	def showLog(self, data=None, retVal=None, extraArgs=None):
		strview = ""
		if self.tailLog:
			strview = data
		elif self.logfile:
			if fileExists(self.logfile):
				f = open(self.logfile, "r")
				for line in f.readlines():
					strview += line
				f.close()
		self["infotext"].setText(strview)

	def keyCancel(self):
		self.console.killAll()
		self.close()

	def closeRecursive(self):
		self.console.killAll()
		self.close(True)
