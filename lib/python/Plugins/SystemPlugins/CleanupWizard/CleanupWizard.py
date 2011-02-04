from Screens.Wizard import wizardManager, WizardSummary
from Screens.WizardLanguage import WizardLanguage
from Screens.Rc import Rc
from Screens.Console import Console
from Screens.MessageBox import MessageBox
from Components.Console import Console
from Components.Ipkg import IpkgComponent
from Components.Pixmap import Pixmap, MovingPixmap, MultiPixmap
from Components.config import config, getConfigListEntry, ConfigSubsection, ConfigText, ConfigLocations, ConfigBoolean
from Tools.Directories import fileExists, resolveFilename, SCOPE_PLUGINS, SCOPE_SKIN_IMAGE
from os import system, statvfs, stat


def checkFreeSpaceAvailable():
	try:
		stat = statvfs('/')
	except OSError:
		return None
	return (stat.f_bfree * stat.f_bsize)/1024 #return free space in kiloBytes


class CleanupWizard(WizardLanguage, Rc):

	skin = """
		<screen name="CleanupWizard" position="0,0" size="720,576" title="Welcome..." flags="wfNoBorder" >
			<widget name="text" position="153,40" size="380,330" font="Regular;22" />
			<widget source="list" render="Listbox" position="43,300" size="460,220" scrollbarMode="showOnDemand" >
				<convert type="StringList" />
			</widget>
			<widget name="config" position="53,340" zPosition="1" size="440,180" transparent="1" scrollbarMode="showOnDemand" />
			<ePixmap pixmap="skin_default/buttons/button_red.png" position="40,225" zPosition="0" size="15,16" transparent="1" alphatest="on" />
			<widget name="languagetext" position="55,225" size="95,30" font="Regular;18" />
			<widget name="wizard" pixmap="skin_default/wizard.png" position="40,50" zPosition="10" size="110,174" alphatest="on" />
			<widget name="rc" pixmaps="skin_default/rc.png,skin_default/rcold.png" position="530,50" zPosition="10" size="154,500" alphatest="on" />
			<widget name="arrowdown" pixmap="skin_default/arrowdown.png" position="-100,-100" zPosition="11" size="37,70" alphatest="on" />
			<widget name="arrowdown2" pixmap="skin_default/arrowdown.png" position="-100,-100" zPosition="11" size="37,70" alphatest="on" />
			<widget name="arrowup" pixmap="skin_default/arrowup.png" position="-100,-100" zPosition="11" size="37,70" alphatest="on" />
			<widget name="arrowup2" pixmap="skin_default/arrowup.png" position="-100,-100" zPosition="11" size="37,70" alphatest="on" />
		</screen>"""

	def __init__(self, session):
		self.xmlfile = resolveFilename(SCOPE_PLUGINS, "SystemPlugins/CleanupWizard/cleanupwizard.xml")
		WizardLanguage.__init__(self, session, showSteps = False, showStepSlider = False)
		Rc.__init__(self)
		self.session = session
		self["wizard"] = Pixmap()
		self.selectedAction = None
		self.selectedPackage = None
		self.NextStep = None
		self.Text = None
		self.buildListRef = None
		self.RemoveRef = None
		self.excluded_extensions = ('-skins', '-streamproxy', '-frontprocessorupgrade', '-crashlogautosubmit', '-hotplug', '-webinterface', '-mediascanner', '-genuinedreambox', '-mediaplayer', '-pictureplayer', '-dvdplayer', '-dvdburn', '-videotune', '-videomode', '-softwaremanager', '-skinselector', '-satfinder' )
		self.Console = Console()
		self.installed_packetlist = []
		self.ipkg = IpkgComponent()
		self.ipkg.addCallback(self.ipkgCallback)

	def markDone(self):
		pass

	def listAction(self):
		list = []
		list.append((_("OK, remove some extensions"), "removeextensions"))
		list.append((_("Exit the cleanup wizard"), "end"))
		return list

	def listAgainAction(self):
		list = []
		list.append((_("OK, remove another extensions"), "removeextensions"))
		list.append((_("Exit the cleanup wizard"), "end"))
		return list

	def ActionSelectionMade(self, index):
		self.selectedAction = index
		self.ActionSelect(index)

	def ActionSelect(self, index):
		if index == 'end':
			self.NextStep = 'end'
		else:
			self.NextStep = 'removeextensions'

	def ActionSelectionMoved(self):
		self.ActionSelect(self.selection)

	def buildList(self,action):
		if self.NextStep is not 'end':
			if not self.Console:
				self.Console = Console()
			cmd = "opkg list_installed | grep enigma2"
			self.Console.ePopen(cmd, self.buildListInstalled_Finished)
			self.buildListRef = self.session.openWithCallback(self.buildListfinishedCB, MessageBox, _("Please wait while searching for removable packages..."), type = MessageBox.TYPE_INFO, enable_input = False)
		else:
			self.buildListfinishedCB(False)

	def buildListInstalled_Finished(self, result, retval, extra_args = None):
		if len(result):
			self.installed_packetlist = []
			for x in result.splitlines():
				split = x.split(' - ')
				if not any(split[0].strip().endswith(x) for x in self.excluded_extensions): #ignore some base plugins
					if split[0].strip() != 'enigma2':
						self.installed_packetlist.append((split[0].strip()))
		self.buildListRef.close(True)

	def buildListfinishedCB(self,data):
		self.buildListRef = None
		if data is True:
			self.currStep = self.getStepWithID(self.NextStep)
			self.afterAsyncCode()
		else:
			self.currStep = self.getStepWithID(self.NextStep)
			self.afterAsyncCode()

	def listInstalledPackages(self):
		list = []
		if self.installed_packetlist and len(self.installed_packetlist):
			for x in self.installed_packetlist:
				if x.startswith('enigma2-plugin-'):
					pluginname = x.replace("enigma2-plugin-","")
				elif x.startswith('enigma2-skin-'):
					pluginname = x.replace("enigma2-","")
				else:
					pluginname = x
				list.append( (pluginname,x) )
		return list

	def PackageSelectionMade(self, index):
		self.PackageSelect(index)

	def PackageSelectionMoved(self):
		self.PackageSelect(self.selection)

	def PackageSelect(self, package):
		self.selectedPackage = package

	def ipkgCallback(self, event, param):
		if event == IpkgComponent.EVENT_ERROR:
			freeSpace = checkFreeSpaceAvailable()
			txt_line1 = _("There was an error. The package:") + "\n" + str(self.selectedPackage) + "\n" + _("could not be removed") + "\n"
			txt_line2 = _("There are now ") + str(freeSpace) + " kB " + _("available") + "\n\n"
			txt_line3 = _("Please select an option below.")
			self.Text = txt_line1 + txt_line2 + txt_line3
			self.NextStep = 'StatusRemoveERROR'
			self.RemoveRef.close(True)
		elif event == IpkgComponent.EVENT_DONE:
			freeSpace = checkFreeSpaceAvailable()
			txt_line1 = _("The package:") + "\n" + str(self.selectedPackage) + "\n" + _("was removed successfully") + "\n"
			txt_line2 = _("There are now ") + str(freeSpace) + " kB " + _("available") + "\n\n"
			txt_line3 = _("Please select an option below.")
			self.Text = txt_line1 + txt_line2 + txt_line3
			self.NextStep = 'StatusRemoveOK'
			self.RemoveRef.close(True)
		pass

	def removeExtension(self,extension):
		if self.NextStep is not 'end':
			self.ipkg.startCmd(IpkgComponent.CMD_REMOVE, {'package': extension})
			self.RemoveRef = self.session.openWithCallback(self.removeExtensionFinishedCB, MessageBox, _("Please wait while removing selected package..."), type = MessageBox.TYPE_INFO, enable_input = False)
		else:
			self.buildListfinishedCB(False)

	def removeExtensionFinishedCB(self,data):
		self.RemoveRef = None
		if data is True:
			self.currStep = self.getStepWithID(self.NextStep)
			self.afterAsyncCode()
		else:
			self.currStep = self.getStepWithID(self.NextStep)
			self.afterAsyncCode()

