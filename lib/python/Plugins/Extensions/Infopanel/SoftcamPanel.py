from Components.config import config, ConfigSubsection, ConfigText, configfile, getConfigListEntry, ConfigSelection
from Components.ConfigList import ConfigListScreen
from Components.MultiContent import MultiContentEntryText, MultiContentEntryPixmapAlphaBlend
from Components.MenuList import MenuList
from Components.Label import Label
from Screens.Screen import Screen
from Components.ActionMap import ActionMap
from Components.Sources.List import List
from Components.Sources.StaticText import StaticText
from Tools.LoadPixmap import LoadPixmap
from Tools.Directories import resolveFilename, SCOPE_CURRENT_PLUGIN, SCOPE_CURRENT_SKIN, fileExists
from Screens.MessageBox import MessageBox
from Screens.Console import Console
from enigma import *
import os

def command(comandline, strip=1):
	comandline = comandline + " >/tmp/command.txt"
	os.system(comandline)
	text = ""
	if os.path.exists("/tmp/command.txt") is True:
		file = open("/tmp/command.txt", "r")
		if strip == 1:
			for line in file:
				text = text + line.strip() + '\n'
		else:
			for line in file:
				text = text + line
				if text[-1:] != '\n': text = text + "\n"
		file.close()
	# if one or last line then remove linefeed
	if text[-1:] == '\n': text = text[:-1]
	comandline = text
	os.system("rm /tmp/command.txt")
	return comandline

class ShowSoftcamPackages(Screen):
	skin = """
		<screen name="ShowSoftcamPackages" position="center,center" size="630,500" title="Install Softcams" >
			<ePixmap pixmap="skin_default/buttons/red.png" position="0,0" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/green.png" position="140,0" size="140,40" alphatest="on" />
			<widget source="key_red" render="Label" position="0,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" transparent="1" />
			<widget source="key_green" render="Label" position="140,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" transparent="1" />
			<widget source="key_ok" render="Label" position="240,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" transparent="1" />
			<widget source="list" render="Listbox" position="5,50" size="620,420" scrollbarMode="showOnDemand">
				<convert type="TemplatedMultiContent">
					{"template": [
							MultiContentEntryText(pos = (5, 1), size = (540, 28), font=0, flags = RT_HALIGN_LEFT, text = 0), # index 0 is the name
							MultiContentEntryText(pos = (5, 26), size = (540, 20), font=1, flags = RT_HALIGN_LEFT, text = 2), # index 2 is the description
							MultiContentEntryPixmapAlphaBlend(pos = (545, 2), size = (48, 48), png = 4), # index 4 is the status pixmap
							MultiContentEntryPixmapAlphaBlend(pos = (5, 50), size = (510, 2), png = 5), # index 4 is the div pixmap
						],
					"fonts": [gFont("Regular", 22),gFont("Regular", 14)],
					"itemHeight": 52
					}
				</convert>
			</widget>
		</screen>"""
	
	def __init__(self, session, args = None):
		Screen.__init__(self, session)
		self.session = session
		
		self["actions"] = ActionMap(["OkCancelActions", "DirectionActions", "ColorActions"],
		{
			"red": self.exit,
			"ok": self.go,
			"cancel": self.exit,
			"green": self.startupdateList,
		}, -1)
		
		self.list = []
		self.statuslist = []
		self["list"] = List(self.list)
		self["key_red"] = StaticText(_("Close"))
		self["key_green"] = StaticText(_("Reload"))
		self["key_ok"] = StaticText(_("Install"))

		self.oktext = _("\nPress OK on your remote control to continue.")
		self.onShown.append(self.setWindowTitle)
		self.setStatus('list')
		self.Timer1 = eTimer()
		self.Timer1.callback.append(self.rebuildList)
		self.Timer1.start(1000, True)
		self.Timer2 = eTimer()
		self.Timer2.callback.append(self.updateList)

	def go(self, returnValue = None):
		cur = self["list"].getCurrent()
		if cur:
			status = cur[3]
			self.package = cur[2]
			if status == "installable":
				self.session.openWithCallback(self.runInstall, MessageBox, _("Do you want to install the package:\n") + self.package + "\n" + self.oktext)

	def runInstall(self, result):
		if result:
			self.session.openWithCallback(self.runInstallCont, Console, cmdlist = ['opkg install ' + self.package], closeOnSuccess = True)

	def runInstallCont(self):
			ret = command('opkg list-installed | grep ' + self.package + ' | cut -d " " -f1')

			if ret != self.package:
				self.session.open(MessageBox, _("Install Failed !!"), MessageBox.TYPE_ERROR, timeout = 10)
			else:
				self.session.open(MessageBox, _("Install Finished."), MessageBox.TYPE_INFO, timeout = 10)
				self.setStatus('list')
				self.Timer1.start(1000, True)

	def UpgradeReboot(self, result):
		if result is None:
			return
		
	def exit(self):
		self.close()
			
	def setWindowTitle(self):
		self.setTitle(_("Install Softcams"))

	def setStatus(self,status = None):
		if status:
			self.statuslist = []
			divpng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_CURRENT_SKIN, "skin_default/div-h.png"))
			if status == 'update':
				statuspng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_CURRENT_PLUGIN, "Extensions/Infopanel/icons/upgrade.png"))
				self.statuslist.append(( _("Package list update"), '', _("Trying to download a new updatelist. Please wait..." ),'', statuspng, divpng ))
				self['list'].setList(self.statuslist)
			if status == 'list':
				statuspng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_CURRENT_PLUGIN, "Extensions/Infopanel/icons/upgrade.png"))
				self.statuslist.append(( _("Package list"), '', _("Getting Softcam list. Please wait..." ),'', statuspng, divpng ))
				self['list'].setList(self.statuslist)
			elif status == 'error':
				statuspng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_CURRENT_PLUGIN, "Extensions/Infopanel/icons/remove.png"))
				self.statuslist.append(( _("Error"), '', _("There was an error downloading the updatelist. Please try again." ),'', statuspng, divpng ))
				self['list'].setList(self.statuslist)				

	def startupdateList(self):
		self.setStatus('update')
		self.Timer2.start(1000, True)

	def updateList(self):
		self.container = eConsoleAppContainer()
		self.container.appClosed.append(self.doneupdateList)
		self.setStatus('list')
		self.container.execute('opkg update')

	def doneupdateList(self, answer):
		self.container.appClosed.remove(self.doneupdateList)
		self.Timer1.start(1000, True)

	def rebuildList(self):
		self.list = []
		self.Flist = []
		self.Elist = []
		t = command('opkg list | grep "enigma2-plugin-softcams-"')
		self.Flist = t.split('\n')
		tt = command('opkg list-installed | grep "enigma2-plugin-softcams-"')
		self.Elist = tt.split('\n')

		if len(self.Flist) > 0:
			self.buildPacketList()
		else:
			self.setStatus('error')

	def buildEntryComponent(self, name, version, description, state):
		divpng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_CURRENT_SKIN, "skin_default/div-h.png"))
		if not description:
			description = ""
		installedpng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_CURRENT_PLUGIN, "Extensions/Infopanel/icons/installed.png"))
		return((name, version, _(description), state, installedpng, divpng))

	def buildPacketList(self):
		fetchedList = self.Flist
		excludeList = self.Elist

		if len(fetchedList) > 0:
			for x in fetchedList:
				x_installed = False
				Fx = x.split(' - ')
				try:
					if Fx[0].find('-softcams-') > -1:
						for exc in excludeList:
							Ex = exc.split(' - ')
							if Fx[0] == Ex[0]:
								x_installed = True
								break
						if x_installed == False:
							self.list.append(self.buildEntryComponent(Fx[2], Fx[1], Fx[0], "installable"))
				except:
					pass

			self['list'].setList(self.list)
	
		else:
			self.setStatus('error')
