from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Components.ActionMap import ActionMap
from Components.ConfigList import ConfigListScreen
from Components.MenuList import MenuList
from Components.Sources.StaticText import StaticText
from Components.config import config, ConfigNumber, ConfigSelection, ConfigSelectionNumber, getConfigListEntry
from Plugins.Plugin import PluginDescriptor

from enigma import setAnimation_current, setAnimation_speed

from boxbranding import getBrandOEM

if not getBrandOEM() == 'gigablue':
	from enigma import setAnimation_current_listbox
	
# default = disabled
if getBrandOEM() == 'gigablue':
	g_default = {
		"current": 0,
		"speed"  : 20,
		}
else:
	g_default = {
		"current": 0,
		"speed"  : 20,
		"listbox": "0",
		}

g_max_speed = 30

g_animation_paused = False
g_orig_show = None
g_orig_doClose = None

config.misc.window_animation_default = ConfigNumber(default=g_default["current"])
config.misc.window_animation_speed = ConfigSelectionNumber(15, g_max_speed, 1, default=g_default["speed"])
if not getBrandOEM() == 'gigablue':
	config.misc.listbox_animation_default = ConfigSelection(default = g_default["listbox"], choices = [ ("0", _("Disable")), ("1", _("Enable")), ("2", _("Same behavior as current animation")) ])

class AnimationSetupConfig(ConfigListScreen, Screen):
	skin="""
		<screen position="center,center" size="600,140" title="Animation Setup">
			<widget name="config" position="0,0" size="600,100" scrollbarMode="showOnDemand" />
			<ePixmap pixmap="skin_default/buttons/red.png" position="0,100" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/green.png" position="140,100" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/yellow.png" position="280,100" size="140,40" alphatest="on" />
			<widget source="key_red" render="Label" position="0,100" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" foregroundColor="#ffffff" backgroundColor="#9f1313" transparent="1" />
			<widget source="key_green" render="Label" position="140,100" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" foregroundColor="#ffffff" backgroundColor="#1f771f" transparent="1" />
			<widget source="key_yellow" render="Label" position="280,100" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" foregroundColor="#ffffff" backgroundColor="#a08500" transparent="1" />
		</screen>
		"""

	def __init__(self, session):
		self.session = session
		self.entrylist = []

		Screen.__init__(self, session)
		ConfigListScreen.__init__(self, self.entrylist)

		self["actions"] = ActionMap(["OkCancelActions", "ColorActions",], {
			"ok"     : self.keyGreen,
			"green"  : self.keyGreen,
			"yellow" : self.keyYellow,
			"red"    : self.keyRed,
			"cancel" : self.keyRed,
		}, -2)
		self["key_red"]   = StaticText(_("Cancel"))
		self["key_green"] = StaticText(_("Save"))
		self["key_yellow"] = StaticText(_("Default"))

		self.makeConfigList()
		self.onLayoutFinish.append(self.layoutFinished)

	def layoutFinished(self):
		self.setTitle(_('Animation Setup'))

	def keyGreen(self):
		config.misc.window_animation_speed.save()
		setAnimation_speed(int(config.misc.window_animation_speed.value))
		config.misc.listbox_animation_default.save()
		if not getBrandOEM() == 'gigablue':
			setAnimation_current_listbox(int(config.misc.listbox_animation_default.value))
		self.close()

	def keyRed(self):
		config.misc.window_animation_speed.cancel()
		config.misc.listbox_animation_default.cancel()
		self.close()

	def keyYellow(self):
		global g_default
		config.misc.window_animation_speed.value = g_default["speed"]
		if not getBrandOEM() == 'gigablue':
			config.misc.listbox_animation_default.value = g_default["listbox"]
		self.makeConfigList()

	def keyLeft(self):
		ConfigListScreen.keyLeft(self)

	def keyRight(self):
		ConfigListScreen.keyRight(self)

	def makeConfigList(self):
		self.entrylist = []

		entrySpeed = getConfigListEntry(_("Animation Speed"), config.misc.window_animation_speed)
		self.entrylist.append(entrySpeed)
		if not getBrandOEM() == 'gigablue':
			entryMoveSelection = getConfigListEntry(_("Enable Focus Animation"), config.misc.listbox_animation_default)
			self.entrylist.append(entryMoveSelection)
		self["config"].list = self.entrylist
		self["config"].l.setList(self.entrylist)


class AnimationSetupScreen(Screen):
	if getBrandOEM() == 'gigablue':
		animationSetupItems = [
			{"idx":0, "name":_("Disable Animations")},
			{"idx":1, "name":_("Simple fade")},
			{"idx":2, "name":_("Simple zoom")},
			{"idx":3, "name":_("Grow drop")},
			{"idx":4, "name":_("Grow from left")},
			{"idx":5, "name":_("Extrude from left")},
			#{"idx":6, "name":_("Popup")},
			{"idx":7, "name":_("Slide drop")},
			{"idx":8, "name":_("Slide from left")},
			{"idx":9, "name":_("Slide left to right")},
			{"idx":10, "name":_("Slide right to left")},
			{"idx":11, "name":_("Slide top to bottom")},
			{"idx":12, "name":_("Zoom from left")},
			{"idx":13, "name":_("Zoom from right")},
			{"idx":14, "name":_("Stripes")},
		]
	else:
		animationSetupItems = [
			{"idx":0, "name":_("Disable Animations")},
			{"idx":1, "name":_("Simple fade")},
			{"idx":2, "name":_("Grow drop")},
			{"idx":3, "name":_("Grow from left")},
			{"idx":4, "name":_("Popup")},
			{"idx":5, "name":_("Slide drop")},
			{"idx":6, "name":_("Slide left to right")},
			{"idx":7, "name":_("Slide top to bottom")},
			{"idx":8, "name":_("Stripes")},
		]

	skin = """
		<screen name="AnimationSetup" position="center,center" size="680,400" title="Animation Setup">
			<ePixmap pixmap="skin_default/buttons/red.png" position="0,0" size="140,40" zPosition="1" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/green.png" position="140,0" size="140,40" zPosition="1" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/yellow.png" position="280,0" size="140,40" zPosition="1" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/blue.png" position="420,0" size="140,40" zPosition="1" alphatest="on" />

			<widget source="key_red" render="Label" position="0,0" zPosition="2" size="140,40" font="Regular;20" halign="center" valign="center" foregroundColor="#ffffff" backgroundColor="#9f1313" transparent="1" />
			<widget source="key_green" render="Label" position="140,0" zPosition="2" size="140,40" font="Regular;20" halign="center" valign="center" foregroundColor="#ffffff" backgroundColor="#1f771f" transparent="1" />
			<widget source="key_yellow" render="Label" position="280,0" zPosition="2" size="140,40" font="Regular;20" halign="center" valign="center" foregroundColor="#ffffff" backgroundColor="#a08500" transparent="1" />
			<widget source="key_blue" render="Label" position="420,0" zPosition="2" size="140,40" font="Regular;20" halign="center" valign="center" foregroundColor="#ffffff" backgroundColor="#18188b" transparent="1" />

			<widget name="list" position="10,60" size="660,364" scrollbarMode="showOnDemand" />
			<widget source="introduction" render="Label" position="0,370" size="560,40" zPosition="10" font="Regular;20" valign="center" backgroundColor="#25062748" transparent="1" />
		</screen>"""

	def __init__(self, session):

		self.skin = AnimationSetupScreen.skin
		Screen.__init__(self, session)

		self.animationList = []

		self["introduction"] = StaticText(_("* current animation"))
		self["key_red"] = StaticText(_("Cancel"))
		self["key_green"] = StaticText(_("Save"))
		self["key_yellow"] = StaticText(_("Settings"))
		self["key_blue"] = StaticText(_("Preview"))

		self["actions"] = ActionMap(["SetupActions", "ColorActions"],
			{
				"cancel": self.keyclose,
				"save": self.ok,
				"ok" : self.ok,
				"yellow": self.config,
				"blue": self.preview
			}, -3)

		self["list"] = MenuList(self.animationList)

		self.onLayoutFinish.append(self.layoutFinished)

	def layoutFinished(self):
		l = []
		for x in self.animationSetupItems:
			key = x.get("idx", 0)
			name = x.get("name", "??")
			if key == config.misc.window_animation_default.value:
				name = "* %s" % (name)
			l.append( (name, key) )

		self["list"].setList(l)

	def ok(self):
		current = self["list"].getCurrent()
		if current:
			key = current[1]
			config.misc.window_animation_default.value = key
			config.misc.window_animation_default.save()
			setAnimation_current(key)
			if not getBrandOEM() == 'gigablue':
				setAnimation_current_listbox(int(config.misc.listbox_animation_default.value))
		self.close()

	def keyclose(self):
		setAnimation_current(config.misc.window_animation_default.value)
		setAnimation_speed(int(config.misc.window_animation_speed.value))
		if not getBrandOEM() == 'gigablue':
			setAnimation_current_listbox(int(config.misc.listbox_animation_default.value))
		self.close()

	def config(self):
		self.session.open(AnimationSetupConfig)

	def preview(self):
		current = self["list"].getCurrent()
		if current:
			global g_animation_paused
			tmp = g_animation_paused
			g_animation_paused = False

			setAnimation_current(current[1])
			self.session.open(MessageBox, current[0], MessageBox.TYPE_INFO, timeout=3)
			g_animation_paused = tmp

def checkAttrib(self, paused):
	global g_animation_paused
	if g_animation_paused is paused and self.skinAttributes is not None:
		for (attr, value) in self.skinAttributes:
			if attr == "animationPaused" and value in ("1", "on"):
				return True
	return False

def screen_show(self):
	global g_animation_paused
	if g_animation_paused:
		setAnimation_current(0)

	g_orig_show(self)

	if checkAttrib(self, False):
		g_animation_paused = True

def screen_doClose(self):
	global g_animation_paused
	if checkAttrib(self, True):
		g_animation_paused = False
		setAnimation_current(config.misc.window_animation_default.value)
	g_orig_doClose(self)

def animationSetupMain(session, **kwargs):
	session.open(AnimationSetupScreen)

def startAnimationSetup(menuid):
	if menuid != "osd_menu":
		return []

	return [( _("Animations"), animationSetupMain, "animation_setup", 3)]

def sessionAnimationSetup(session, reason, **kwargs):
	setAnimation_current(config.misc.window_animation_default.value)
	setAnimation_speed(int(config.misc.window_animation_speed.value))
	if not getBrandOEM() == 'gigablue':
		setAnimation_current_listbox(int(config.misc.listbox_animation_default.value))

	global g_orig_show, g_orig_doClose
	if g_orig_show is None:
		g_orig_show = Screen.show
	if g_orig_doClose is None:
		g_orig_doClose = Screen.doClose
	Screen.show = screen_show
	Screen.doClose = screen_doClose

def Plugins(**kwargs):
	plugin_list = [
		PluginDescriptor(
			name = "Animations",
			description = "Setup UI animations",
			where = PluginDescriptor.WHERE_MENU,
			needsRestart = False,
			fnc = startAnimationSetup),
		PluginDescriptor(
			where = PluginDescriptor.WHERE_SESSIONSTART,
			needsRestart = False,
			fnc = sessionAnimationSetup),
	]
	return plugin_list;
