from Screens.Screen import Screen
from Components.ConfigList import ConfigListScreen
from Components.config import config, getConfigListEntry, ConfigSubsection, ConfigSelection, ConfigInteger
from Components.ActionMap import ActionMap,NumberActionMap
from Screens.MessageBox import MessageBox
from Components.Sources.StaticText import StaticText
from Plugins.Plugin import PluginDescriptor
from Plugins.SystemPlugins.FanControl.InstandbyOn import instandbyon
import NavigationInstance

class ManualFancontrol(Screen,ConfigListScreen):
	skin = """
			<screen name="ManualFancontrol" position="center,center" size="560,300" >
			<widget name="config" zPosition="2" position="5,50" size="550,200" scrollbarMode="showOnDemand" transparent="1" />
			<widget source="current" render="Label" position="150,270" zPosition="1" size="280,30" font="Regular;18" halign="left" valign="center" transparent="1" />
			<ePixmap pixmap="skin_default/buttons/red.png" position="0,0" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/green.png" position="140,0" size="140,40" alphatest="on" />
			<widget source="key_red" render="Label" position="0,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" transparent="1" />
			<widget source="key_green" render="Label" position="140,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" transparent="1" />
			</screen>"""

	def __init__(self,session):
		Screen.__init__(self,session)
		self.session = session
		Screen.setTitle(self, _("Fan Control"))
		self["shortcuts"] = ActionMap(["ShortcutActions", "SetupActions" ],
		{
			"ok": self.keySave,
			"cancel": self.keyCancel,
			"red": self.keyCancel,
			"green": self.keySave,
		}, -2)
		self.list = []
		ConfigListScreen.__init__(self, self.list,session = self.session)
		self["key_red"] = StaticText(_("Cancel"))
		self["key_green"] = StaticText(_("Save"))
		self["current"] = StaticText(" ")
		self.configSetup()
		self.oldfanoffmode = instandbyon.fanoffmode
		if instandbyon.fanoffmode is 'ON' :
			instandbyon.checkStatusLoopStop()

	def displayCurrentValue(self):
		currrent_val = self["config"].getCurrent()[0]+" : "+str(self["config"].getCurrent()[1].value)
		self["current"].setText(_(currrent_val))
		print currrent_val

	def selectionChanged(self):
		if self["config"].getCurrent() == self.pwmEntry:
			instandbyon.setPWM(self["config"].getCurrent()[1].value)

	def keyLeft(self):
		oldpwmvalue=config.plugins.manualfancontrols.pwmvalue.value
		ConfigListScreen.keyLeft(self)
		if self["config"].getCurrent() == self.pwmEntry and oldpwmvalue == 5:
			self.createSetup()
		else:
			self.displayCurrentValue()
		self.selectionChanged()

	def keyRight(self):
		oldpwmvalue=config.plugins.manualfancontrols.pwmvalue.value
		ConfigListScreen.keyRight(self)
		if self["config"].getCurrent() == self.pwmEntry and oldpwmvalue == 0:
			self.createSetup()
			while self["config"].getCurrent() != self.pwmEntry:
				self["config"].setCurrentIndex(self["config"].getCurrentIndex()+1)
		else:
			self.displayCurrentValue()
		self.selectionChanged()

	def createSetup(self):
		self.list = []
		if config.plugins.manualfancontrols.pwmvalue.value > 0:
			self.list.append( self.standbyEntry )
		self.list.append( self.pwmEntry )
		self.list.append( self.periodEntry )
		self["config"].list = self.list
		self["config"].l.setList(self.list)

	def configSetup(self):
		self.standbyEntry = getConfigListEntry(_("FanOFF InStanby"), config.plugins.manualfancontrols.standbymode)
		self.pwmEntry = getConfigListEntry(_("PWM value"), config.plugins.manualfancontrols.pwmvalue)
		self.periodEntry = getConfigListEntry(_("Status Check Period"), config.plugins.manualfancontrols.checkperiod)
		if not self.displayCurrentValue in self["config"].onSelectionChanged:
			self["config"].onSelectionChanged.append(self.displayCurrentValue)
		self.createSetup()

	def keySave(self):
		if instandbyon.fanoffmode is 'OFF' and config.plugins.manualfancontrols.pwmvalue.value == 0:
			print "<SimpleFancontrol> instandbyon.fanoffmode 'OFF' -> 'ON'"
			instandbyon.fanoffmode = 'ON'
			instandbyon.addRecordEventCB()
			instandbyon.checkStatusLoopStart()
		elif instandbyon.fanoffmode is 'ON' and config.plugins.manualfancontrols.pwmvalue.value != 0:
			print "<SimpleFancontrol> instandbyon.fanoffmode 'ON' -> 'OFF'"
			instandbyon.fanoffmode = 'OFF'
			instandbyon.removeRecordEventCB()
#			instandbyon.checkStatusLoopStop() # stopped at init
		elif self.oldfanoffmode is 'ON' :
			instandbyon.checkStatusLoopStart()
		instandbyon.checkStstus()
		ConfigListScreen.keySave(self)

	def cancelConfirm(self, result):
		if not result:
			return
		for x in self["config"].list:
			x[1].cancel()
		instandbyon.checkStstus()
		self.oldfanoffmode = instandbyon.fanoffmode
		if self.oldfanoffmode is 'ON' :
			instandbyon.checkStatusLoopStart()
		self.close()

	def keyCancel(self):
		if self["config"].isChanged():
			self.session.openWithCallback(self.cancelConfirm, MessageBox, _("Really close without saving settings?"))
		else:
			instandbyon.checkStstus()
			if self.oldfanoffmode is 'ON' :
				instandbyon.checkStatusLoopStart()
			self.close()

def main(session, **kwargs):
	session.open(ManualFancontrol)

def selSetup(menuid, **kwargs):
	if menuid != "system":
		return [ ]
	return [(_("Fan Control"), main, "fansetup_config", 70)]

def Plugins(**kwargs):
	from os import path
	if not path.exists("/usr/lib/enigma2/python/Plugins/Extensions/FanControl2/plugin.pyo"):
		return [PluginDescriptor(name=_("Fan Control"), description=_("setup Fancontol inStandby mode"), where = PluginDescriptor.WHERE_MENU, needsRestart = True, fnc=selSetup)]
	return []
