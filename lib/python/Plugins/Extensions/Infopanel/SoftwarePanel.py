from Plugins.Plugin import PluginDescriptor
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.Pixmap import Pixmap
from Components.Sources.List import List
from Components.Sources.StaticText import StaticText
from Components.Ipkg import IpkgComponent
from Components.MultiContent import MultiContentEntryText, MultiContentEntryPixmapAlphaBlend
from Tools.LoadPixmap import LoadPixmap
from enigma import ePixmap
from Tools.Directories import resolveFilename, SCOPE_CURRENT_PLUGIN, SCOPE_CURRENT_SKIN, SCOPE_METADIR
import os
from boxbranding import getMachineBrand, getMachineName

class SoftwarePanel(Screen):

	def __init__(self, session, *args):
		Screen.__init__(self, session)
		Screen.setTitle(self, _("Software Panel"))
		skin = """
		<screen name="SoftwarePanel" position="center,center" size="650,605" title="Software Panel">
			<widget name="a_off" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/Infopanel/icons/aoff.png" position="10,10" zPosition="1" size="36,97" alphatest="on" />
			<widget name="a_red" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/Infopanel/icons/ared.png" position="10,10" zPosition="1" size="36,97" alphatest="on" />
			<widget name="a_yellow" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/Infopanel/icons/ayellow.png" position="10,10" zPosition="1" size="36,97" alphatest="on" />
			<widget name="a_green" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/Infopanel/icons/agreen.png" position="10,10" zPosition="1" size="36,97" alphatest="on" />
			<widget name="feedstatusRED" position="60,14" size="200,30" zPosition="1" font="Regular;25" halign="left" transparent="1" />
			<widget name="feedstatusYELLOW" position="60,46" size="200,30" zPosition="1" font="Regular;25" halign="left" transparent="1" />
			<widget name="feedstatusGREEN" position="60,78" size="200,30" zPosition="1" font="Regular;25" halign="left" transparent="1" />
			<widget name="packagetext" position="180,50" size="350,30" zPosition="1" font="Regular;25" halign="right" transparent="1" />
			<widget name="packagenr" position="511,50" size="50,30" zPosition="1" font="Regular;25" halign="right" transparent="1" />
			<widget source="list" render="Listbox" position="10,120" size="630,365" scrollbarMode="showOnDemand">
				<convert type="TemplatedMultiContent">
					{"template": [
							MultiContentEntryText(pos = (5, 1), size = (540, 28), font=0, flags = RT_HALIGN_LEFT, text = 0), # index 0 is the name
							MultiContentEntryText(pos = (5, 26), size = (540, 20), font=1, flags = RT_HALIGN_LEFT, text = 2), # index 2 is the description
							MultiContentEntryPixmapAlphaBlend(pos = (545, 2), size = (48, 48), png = 4), # index 4 is the status pixmap
							MultiContentEntryPixmapAlphaBlend(pos = (5, 50), size = (610, 2), png = 5), # index 4 is the div pixmap
						],
					"fonts": [gFont("Regular", 22),gFont("Regular", 14)],
					"itemHeight": 52
					}
				</convert>
			</widget>
			<ePixmap pixmap="skin_default/buttons/red.png" position=" 30,570" size="35,27" alphatest="blend" />
			<widget name="key_green_pic" pixmap="skin_default/buttons/green.png" position="290,570" size="35,27" alphatest="blend" />
			<widget name="key_red" position=" 80,573" size="200,26" zPosition="1" font="Regular;22" halign="left" transparent="1" />
			<widget name="key_green" position="340,573" size="200,26" zPosition="1" font="Regular;22" halign="left" transparent="1" />
		</screen> """
		self.skin = skin
		self.list = []
		self.statuslist = []
		self["list"] = List(self.list)
		self['a_off'] = Pixmap()
		self['a_red'] = Pixmap()
		self['a_yellow'] = Pixmap()
		self['a_green'] = Pixmap()
		self['key_green_pic'] = Pixmap()
		self['key_red_pic'] = Pixmap()
		self['key_red'] = Label(_("Cancel"))
		self['key_green'] = Label(_("Update"))
		self['packagetext'] = Label(_("Updates Available:"))
		self['packagenr'] = Label("0")
		self['feedstatusRED'] = Label("<  " + _("feed status"))
		self['feedstatusYELLOW'] = Label("<  " + _("feed status"))
		self['feedstatusGREEN'] = Label("<  " + _("feed status"))
		self['key_green'].hide()
		self['key_green_pic'].hide()
		self.update = False
		self.packages = 0
		self.ipkg = IpkgComponent()
		self.ipkg.addCallback(self.ipkgCallback)
		self["actions"] = ActionMap(["OkCancelActions", "DirectionActions", "ColorActions", "SetupActions"],
		{
			"cancel": self.Exit,
			"green": self.Green,
			"red": self.Exit,
		}, -2)

		self.onLayoutFinish.append(self.layoutFinished)

	def Exit(self):
		self.ipkg.stop()
		self.close()

	def Green(self):
		if self.packages > 0:
			if self.packages <= 200:
				from Plugins.SystemPlugins.SoftwareManager.plugin import UpdatePlugin
				self.session.open(UpdatePlugin)
				self.close()
			else:
				print "DO NOT UPDATE !!!"
				message = _("There are to many update packages !!\n\n"
				"There is a risk that your %s %s will not\n"
				"boot after online-update, or will show disfunction in running Image.\n\n"
				"You need to flash new !!\n\n"
				"Do you want to flash-online ?") % (getMachineBrand(), getMachineName())
				self.session.openWithCallback(self.checkPackagesCallback, MessageBox, message, default = True)

	def checkPackagesCallback(self, ret):
		print ret
		if ret:
			from Plugins.SystemPlugins.SoftwareManager.Flash_online import FlashOnline
			self.session.open(FlashOnline)
		self.close()

	def layoutFinished(self):
		self.checkTraficLight()
		self.rebuildList()

	def UpdatePackageNr(self):
		self.packages = len(self.list)
		print self.packages
		print"packagenr" + str(self.packages)
		self["packagenr"].setText(str(self.packages))
		if self.packages == 0:
			self['key_green'].hide()
			self['key_green_pic'].hide()
		else:
			self['key_green'].show()
			self['key_green_pic'].show()

	def checkTraficLight(self):
		print"checkTraficLight"
		from urllib import urlopen
		import socket
		self['a_red'].hide()
		self['a_yellow'].hide()
		self['a_green'].hide()
		self['feedstatusRED'].hide()
		self['feedstatusYELLOW'].hide()
		self['feedstatusGREEN'].hide()
		currentTimeoutDefault = socket.getdefaulttimeout()
		socket.setdefaulttimeout(3)
		try:
			urlopenATV = "http://ampel.mynonpublic.com/Ampel/index.php"
			d = urlopen(urlopenATV)
			tmpStatus = d.read()
			if 'rot.png' in tmpStatus:
				self['a_off'].hide()
				self['a_red'].show()
				self['feedstatusRED'].show()
			elif 'gelb.png' in tmpStatus:
				self['a_off'].hide()
				self['a_yellow'].show()
				self['feedstatusYELLOW'].show()
			elif 'gruen.png' in tmpStatus:
				self['a_off'].hide()
				self['a_green'].show()
				self['feedstatusGREEN'].show()
		except:
			self['a_off'].show()
		socket.setdefaulttimeout(currentTimeoutDefault)

	def setStatus(self,status = None):
		if status:
			self.statuslist = []
			divpng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_CURRENT_SKIN, "skin_default/div-h.png"))
			if status == 'update':
				statuspng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_CURRENT_PLUGIN, "SystemPlugins/SoftwareManager/upgrade.png"))
				self.statuslist.append(( _("Package list update"), '', _("Trying to download a new updatelist. Please wait..." ),'',statuspng, divpng ))
			elif status == 'error':
				statuspng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_CURRENT_PLUGIN, "SystemPlugins/SoftwareManager/remove.png"))
				self.statuslist.append(( _("Error"), '', _("There was an error downloading the updatelist. Please try again." ),'',statuspng, divpng ))
			elif status == 'noupdate':
				statuspng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_CURRENT_PLUGIN, "SystemPlugins/SoftwareManager/installed.png"))
				self.statuslist.append(( _("Nothing to upgrade"), '', _("There are no updates available." ),'',statuspng, divpng ))

			self['list'].setList(self.statuslist)

	def rebuildList(self):
		self.setStatus('update')
		self.ipkg.startCmd(IpkgComponent.CMD_UPDATE)

	def ipkgCallback(self, event, param):
		if event == IpkgComponent.EVENT_ERROR:
			self.setStatus('error')
		elif event == IpkgComponent.EVENT_DONE:
			if self.update == False:
				self.update = True
				self.ipkg.startCmd(IpkgComponent.CMD_UPGRADE_LIST)
			else:
				self.buildPacketList()
		pass
	
	def buildEntryComponent(self, name, version, description, state):
		divpng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_CURRENT_SKIN, "skin_default/div-h.png"))
		if not description:
			description = "No description available."
		if state == 'installed':
			installedpng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_CURRENT_PLUGIN, "SystemPlugins/SoftwareManager/installed.png"))
			return((name, version, _(description), state, installedpng, divpng))	
		elif state == 'upgradeable':
			upgradeablepng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_CURRENT_PLUGIN, "SystemPlugins/SoftwareManager/upgradeable.png"))
			return((name, version, _(description), state, upgradeablepng, divpng))	
		else:
			installablepng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_CURRENT_PLUGIN, "SystemPlugins/SoftwareManager/installable.png"))
			return((name, version, _(description), state, installablepng, divpng))

	def buildPacketList(self):
		self.list = []
		fetchedList = self.ipkg.getFetchedList()
		excludeList = self.ipkg.getExcludeList()

		if len(fetchedList) > 0:
			for x in fetchedList:
				try:
					self.list.append(self.buildEntryComponent(x[0], x[1], x[2], "upgradeable"))
				except:
					print "[SOFTWAREPANEL] " + x[0] + " no valid architecture, ignoring !!"
#					self.list.append(self.buildEntryComponent(x[0], '', 'no valid architecture, ignoring !!', "installable"))
#			if len(excludeList) > 0:
#				for x in excludeList:
#					try:
#						self.list.append(self.buildEntryComponent(x[0], x[1], x[2], "installable"))
#					except:
#						self.list.append(self.buildEntryComponent(x[0], '', 'no valid architecture, ignoring !!', "installable"))

			self['list'].setList(self.list)

		elif len(fetchedList) == 0:
			self.setStatus('noupdate')
		else:
			self.setStatus('error')

		self.UpdatePackageNr()