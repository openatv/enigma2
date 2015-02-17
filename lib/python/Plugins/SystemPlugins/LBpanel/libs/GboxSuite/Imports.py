# 2014.10.12 15:52:37 CEST
from enigma import eListbox, eListboxPythonMultiContent, gFont, loadPNG, RT_HALIGN_LEFT, RT_VALIGN_CENTER
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Components.ActionMap import ActionMap, NumberActionMap
from Components.ScrollLabel import ScrollLabel
from Components.GUIComponent import GUIComponent
from Components.MenuList import MenuList
from Components.Input import Input
from Components.Label import Label
from Plugins.Plugin import PluginDescriptor
from Tools.Directories import *
from Components.config import config, ConfigSelection, ConfigText, ConfigSelection, ConfigElement, ConfigSubsection, getConfigListEntry
config.plugins.gs = ConfigSubsection()
config.plugins.gs.infoDir = ConfigSelection(default='/var/tmp', choices=[('/var/tmp', _('/var/tmp')),
 ('/var/keys', _('/var/keys')),
 ('/usr/keys', _('/usr/keys')),
 ('/usr/gbox', _('/usr/gbox')),
 ('/var/gbox', _('/var/gbox')),
 ('/tmp/gb2', _('/tmp/gb2'))])
config.plugins.gs.configDir = ConfigSelection(default='/var/keys', choices=[('/var/keys', _('/var/keys')),
 ('/usr/keys', _('/usr/keys')),
 ('/usr/gbox', _('/usr/gbox')),
 ('/var/gbox', _('/var/gbox')),
 ('/usr/keys0', _('/usr/keys0')),
 ('/usr/keys/gb2', _('/usr/keys/gb2'))])
providerTable = {}
RT_HALIGN_LEFT = 0
RT_HALIGN_RIGHT = 1
RT_HALIGN_CENTER = 2
RT_HALIGN_BLOCK = 4
RT_VALIGN_TOP = 0
RT_VALIGN_CENTER = 8
RT_VALIGN_CENTER_TEXT = 6
RT_VALIGN_BOTTOM = 16

