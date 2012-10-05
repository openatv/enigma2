#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""
Quick'n'easy switching of aspect ratio setting via configurable remote control keys (Enigma2)
© 2007 schaumkeks <schaumkeks@yahoo.de>
This is free software. You are allowed to modify and use it as long as you leave the copyright.
"""

from Plugins.Plugin import PluginDescriptor
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Components.Label import Label
from Components.ActionMap import ActionMap
from Components.config import config, getConfigListEntry, ConfigSubsection, ConfigSubDict, ConfigEnableDisable, ConfigYesNo, ConfigSelection
from Components.ConfigList import ConfigListScreen
from Components.AVSwitch import AVSwitch
from GlobalActions import globalActionMap
from Tools import Notifications
import keymapparser
import os.path

ASPECT = ["4_3_letterbox", "4_3_panscan", "16_9", "16_9_always", "16_10_letterbox", "16_10_panscan", "16_9_letterbox"]
ASPECTMSG = {
		"4_3_letterbox": _("4:3 Letterbox"),
		"4_3_panscan": _("4:3 PanScan"), 
		"16_9": _("16:9"), 
		"16_9_always": _("16:9 always"),
		"16_10_letterbox": _("16:10 Letterbox"),
		"16_10_panscan": _("16:10 PanScan"), 
		"16_9_letterbox": _("16:9 Letterbox")}

PACKAGE_PATH = os.path.dirname(str((globals())["__file__"]))
KEYMAPPINGS = {'aspect': os.path.join(PACKAGE_PATH, 'keymap-aspect.xml')}

config.plugins.GBAspectRatioSwitch = ConfigSubsection()
config.plugins.GBAspectRatioSwitch.enabled = ConfigEnableDisable(default = True)
config.plugins.GBAspectRatioSwitch.keymap = ConfigSelection({'aspect': _('ASPECT key')})
config.plugins.GBAspectRatioSwitch.showmsg = ConfigEnableDisable(default = True)
config.plugins.GBAspectRatioSwitch.modes = ConfigSubDict()
for aspect in ASPECT:
	config.plugins.GBAspectRatioSwitch.modes[aspect] = ConfigYesNo(default = True)

aspect_ratio_switch = None

class GBAspectRatioSwitchSetup(ConfigListScreen, Screen):
	skin = """
		<screen position="100,100" size="550,400" title="GBAspectRatioSwitch Setup">
			<widget name="config" position="0,0" size="550,300" scrollbarMode="showOnDemand" />
			<widget name="label" position="50,300" size="450,60" font="Regular;18" halign="center" />
			<widget name="buttonred" position="10,360" size="100,40" backgroundColor="red" valign="center" halign="center" zPosition="2" foregroundColor="white" font="Regular;18"/>
			<widget name="buttongreen" position="120,360" size="100,40" backgroundColor="green" valign="center" halign="center" zPosition="2" foregroundColor="white" font="Regular;18"/> 
		</screen>"""

	def __init__(self, session, args=None):
		Screen.__init__(self, session)
		
		self.list = []
		self.list.append(getConfigListEntry(_("Quick switching via remote control"), config.plugins.GBAspectRatioSwitch.enabled))
		self.list.append(getConfigListEntry(_("Key mapping"), config.plugins.GBAspectRatioSwitch.keymap))
		self.list.append(getConfigListEntry(_("Show current mode"), config.plugins.GBAspectRatioSwitch.showmsg))
		for aspect in ASPECT:
			self.list.append(getConfigListEntry(_("Include %s") % ASPECTMSG[aspect], config.plugins.GBAspectRatioSwitch.modes[aspect]))
		ConfigListScreen.__init__(self, self.list)

		self["label"] = Label(_("ENABLE DISABLE PLUGIN IF U WANT IT"))
		self["buttonred"] = Label(_("Cancel"))
		self["buttongreen"] = Label(_("OK"))

		self["actions"] = ActionMap(["SetupActions"],
		{
			#"green": self.save,
			#"red": self.cancel,
			"save": self.save,
			"ok": self.save,
			"cancel": self.cancel
		}, -2)

	def save(self):
		global aspect_ratio_switch
		
		if len([modeconf for modeconf in config.plugins.GBAspectRatioSwitch.modes.values() if modeconf.value]) < 2:
			self.session.open(MessageBox, _("You have to include at least %d aspect ratio modes!") % 2, MessageBox.TYPE_ERROR)
			return

		if config.plugins.GBAspectRatioSwitch.enabled.isChanged():
			if config.plugins.GBAspectRatioSwitch.enabled.value:
				aspect_ratio_switch = GBAspectRatioSwitch()
				aspect_ratio_switch.enable()
			elif aspect_ratio_switch is not None:
				aspect_ratio_switch.disable()
		elif aspect_ratio_switch is not None:
			#TODO: if aspects changed (no isChanged() on ConfigSubDict?)
			aspect_ratio_switch.reload_enabledaspects()
			if config.plugins.GBAspectRatioSwitch.keymap.isChanged():
				aspect_ratio_switch.change_keymap(config.plugins.GBAspectRatioSwitch.keymap.value)

		for x in self["config"].list:
			x[1].save()
		
		self.close()

	def cancel(self):
		for x in self["config"].list:
			x[1].cancel()
		self.close()

class GBAspectRatioSwitch:

	def __init__(self):
		self.reload_enabledaspects()

	def change_keymap(self, keymap):
		if keymap not in KEYMAPPINGS:
			return
		self.unload_keymap()
		try:
			keymapparser.readKeymap(KEYMAPPINGS[keymap])
		except IOError, (errno, strerror):
			config.plugins.GBAspectRatioSwitch.enabled.setValue(False)
			self.disable()
			Notifications.AddPopup(text=_("Changing keymap failed (%s).") % strerror, type=MessageBox.TYPE_ERROR, timeout=10, id='GBAspectRatioSwitch')
			return
		global globalActionMap
		globalActionMap.actions['switchAspectUp'] = self.switchAspectRatioUp
		globalActionMap.actions['switchAspectDown'] = self.switchAspectRatioDown

	def unload_keymap(self):
		for keymap in KEYMAPPINGS.values():
			keymapparser.removeKeymap(keymap)
		
		global globalActionMap
		if 'switchAspectUp' in globalActionMap.actions:
			del globalActionMap.actions['switchAspectUp']
		if 'switchAspectDown' in globalActionMap.actions:
			del globalActionMap.actions['switchAspectDown']

	def reload_enabledaspects(self):
		self.enabledaspects = []
		for aspectnum, aspect in enumerate(ASPECT):
			if config.plugins.GBAspectRatioSwitch.modes[aspect].value:
				self.enabledaspects.append(aspectnum)
		#print 'AspectRatioSwitch: Aspect modes in cycle:',self.enabledaspects

	def enable(self):
		self.change_keymap(config.plugins.GBAspectRatioSwitch.keymap.value)
		self.reload_enabledaspects()
	
	def disable(self):
		global aspect_ratio_switch
		self.unload_keymap()
		aspect_ratio_switch = None

	def switchAspectRatioUp(self):
		self.switchAspectRatio(+1)
		
	def switchAspectRatioDown(self):
		self.switchAspectRatio(-1)

	def switchAspectRatio(self, direction=1):
		if len(self.enabledaspects) < 2:
			return
		iAVSwitch = AVSwitch()
		aspectnum = iAVSwitch.getAspectRatioSetting()
		try:
			localaspectnum = self.enabledaspects.index(aspectnum)
		except ValueError:
			localaspectnum = 0
		newaspectnum = self.enabledaspects[(localaspectnum + direction) % len(self.enabledaspects)]
		iAVSwitch.setAspectRatio(newaspectnum)
		config.av.aspectratio.setValue(ASPECT[newaspectnum])
		if config.plugins.GBAspectRatioSwitch.showmsg.value:
			Notifications.AddPopup(text=ASPECTMSG[ASPECT[newaspectnum]], type=MessageBox.TYPE_INFO, timeout=2, id='GBAspectRatioSwitch')
		#print 'AspectRatioSwitch: Changed aspect ratio from %d - %s to %d - %s' % (aspectnum, ASPECT[aspectnum], newaspectnum, ASPECT[newaspectnum])

def autostart(reason, **kwargs):

	global aspect_ratio_switch
	
	if reason == 0: # startup
		#print "AspectRatioSwitch: startup"
		if config.plugins.GBAspectRatioSwitch.enabled.value and aspect_ratio_switch is None:
			aspect_ratio_switch = GBAspectRatioSwitch()
			aspect_ratio_switch.enable()
	elif reason == 1:
		#print "AspectRatioSwitch: shutdown"
		if aspect_ratio_switch is not None:
			aspect_ratio_switch.disable()

def main(session, **kwargs):
	session.open(GBAspectRatioSwitchSetup)

def Plugins(**kwargs):
 	return [
		PluginDescriptor(
			name="GBAspectRatioSwitch",
			description=_("Quick switching of aspect ratio setting"),
			where = PluginDescriptor.WHERE_PLUGINMENU,
			#icon='plugin.png',
			fnc=main),
		PluginDescriptor(
			where = [PluginDescriptor.WHERE_SESSIONSTART,PluginDescriptor.WHERE_AUTOSTART],
			fnc = autostart)]
