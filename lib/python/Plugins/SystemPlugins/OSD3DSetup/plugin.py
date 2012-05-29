from Screens.Screen import Screen
from Components.ConfigList import ConfigListScreen
from Components.config import config, ConfigSubsection, ConfigInteger, ConfigSelection, ConfigSlider, getConfigListEntry

modelist = {"off": _("Off"), "auto": _("Auto"), "sidebyside": _("Side by Side"), "topandbottom": _("Top and Bottom")}
if config.misc.boxtype.value == 'gb800se' or config.misc.boxtype.value == 'gb800solo' or config.misc.boxtype.value == 'gb800ue':
	setmodelist = {"mode1": _("Mode 1"), "mode2": _("Mode 2")}

config.plugins.OSD3DSetup = ConfigSubsection()
config.plugins.OSD3DSetup.mode = ConfigSelection(choices = modelist, default = "auto")
config.plugins.OSD3DSetup.znorm = ConfigInteger(default = 0)
if config.misc.boxtype.value == 'gb800se' or config.misc.boxtype.value == 'gb800solo' or config.misc.boxtype.value == 'gb800ue':
	config.plugins.OSD3DSetup.setmode = ConfigSelection(choices = setmodelist, default = "mode1")

PROC_ET_3DMODE = "/proc/stb/fb/3dmode"
PROC_ET_ZNORM = "/proc/stb/fb/znorm"

PROC_DM_3DMODE = "/proc/stb/fb/primary/3d"
PROC_DM_ZNORM = "/proc/stb/fb/primary/zoffset"

class OSD3DSetupScreen(Screen, ConfigListScreen):
	skin = """
	<screen position="c-200,c-100" size="400,200" title="OSD 3D setup">
		<widget name="config" position="c-175,c-75" size="350,150" />
		<ePixmap pixmap="skin_default/buttons/green.png" position="c-145,e-45" zPosition="0" size="140,40" alphatest="on" />
		<ePixmap pixmap="skin_default/buttons/red.png" position="c+5,e-45" zPosition="0" size="140,40" alphatest="on" />
		<widget name="ok" position="c-145,e-45" size="140,40" valign="center" halign="center" zPosition="1" font="Regular;20" transparent="1" backgroundColor="green" />
		<widget name="cancel" position="c+5,e-45" size="140,40" valign="center" halign="center" zPosition="1" font="Regular;20" transparent="1" backgroundColor="red" />
	</screen>"""

	def __init__(self, session):
		self.skin = OSD3DSetupScreen.skin
		Screen.__init__(self, session)

		from Components.ActionMap import ActionMap
		from Components.Button import Button

		self["ok"] = Button(_("OK"))
		self["cancel"] = Button(_("Cancel"))

		self["actions"] = ActionMap(["SetupActions", "ColorActions", "MenuActions"],
		{
			"ok": self.keyGo,
			"save": self.keyGo,
			"cancel": self.keyCancel,
			"green": self.keyGo,
			"red": self.keyCancel,
			"menu": self.closeRecursive,
		}, -2)

		self.list = []
		ConfigListScreen.__init__(self, self.list, session = self.session)

		mode = config.plugins.OSD3DSetup.mode.value
		znorm = config.plugins.OSD3DSetup.znorm.value
		if config.misc.boxtype.value == 'gb800se' or config.misc.boxtype.value == 'gb800solo' or config.misc.boxtype.value == 'gb800ue':		
			setmode = config.plugins.OSD3DSetup.setmode.value

		self.mode = ConfigSelection(choices = modelist, default = mode)
		self.znorm = ConfigSlider(default = znorm + 50, increment = 1, limits = (0, 100))
		if config.misc.boxtype.value == 'gb800se' or config.misc.boxtype.value == 'gb800solo' or config.misc.boxtype.value == 'gb800ue':
			self.setmode = ConfigSelection(choices = setmodelist, default = setmode)
			self.list.append(getConfigListEntry(_("Setup mode"), self.setmode))
		self.list.append(getConfigListEntry(_("3d mode"), self.mode))
		self.list.append(getConfigListEntry(_("Depth"), self.znorm))
		
		self["config"].list = self.list
		self["config"].l.setList(self.list)

	def keyLeft(self):
		ConfigListScreen.keyLeft(self)
		self.setPreviewSettings()

	def keyRight(self):
		ConfigListScreen.keyRight(self)
		self.setPreviewSettings()

	def setPreviewSettings(self):
		applySettings(self.mode.value, int(self.znorm.value) - 50)

	def keyGo(self):
		config.plugins.OSD3DSetup.mode.value = self.mode.value
		config.plugins.OSD3DSetup.znorm.value = int(self.znorm.value) - 50
		if config.misc.boxtype.value == 'gb800se' or config.misc.boxtype.value == 'gb800solo' or config.misc.boxtype.value == 'gb800ue':
			config.plugins.OSD3DSetup.setmode.value = self.setmode.value
		config.plugins.OSD3DSetup.save()
		self.close()

	def keyCancel(self):
		setConfiguredSettings()
		self.close()

def applySettings(mode, znorm):
	path_mode = ""
	path_znorm = ""
	from os import path
	if path.exists(PROC_ET_3DMODE):
		path_mode = PROC_ET_3DMODE
		path_znorm = PROC_ET_ZNORM
	elif path.exists(PROC_DM_3DMODE):
		path_mode = PROC_DM_3DMODE
		path_znorm = PROC_DM_ZNORM
		if mode == 'sidebyside':
			mode = 'sbs'
		elif mode == 'topandbottom':
			mode = 'tab'
		else:
			mode = 'off'
	else:
		return
	try:
		file = open(path_mode, "w")
		file.write(mode)
		file.close()
		file = open(path_znorm, "w")
		file.write('%d' % znorm)
		file.close()
	except:
		return
		
def applySettings2(mode, znorm, setmode):
	try:
		if setmode == "mode1":
			file = open("/proc/stb/fb/3dmode", "w")
			file.write(mode)
			file.close()
			file = open("/proc/stb/fb/znorm", "w")
			file.write('%d' % znorm)
			file.close()
		elif setmode == "mode2":
			file = open("/proc/stb/fb/primary/3d","w")
			if mode == "sidebyside" :
				mode = "sbs"
			elif mode == "topandbottom":
				mode = "tab"
			file.write(mode)
			file.close()
			file = open("/proc/stb/fb/primary/zoffset","w")
			file.write('%d' % znorm)
			file.close()
	except:
		return		

def setConfiguredSettings():
	if config.misc.boxtype.value == 'gb800se' or config.misc.boxtype.value == 'gb800solo' or config.misc.boxtype.value == 'gb800ue':
		applySettings2(config.plugins.OSD3DSetup.mode.value, int(config.plugins.OSD3DSetup.znorm.value), config.plugins.OSD3DSetup.setmode.value)
	else:	
		applySettings(config.plugins.OSD3DSetup.mode.value, int(config.plugins.OSD3DSetup.znorm.value))

def main(session, **kwargs):
	session.open(OSD3DSetupScreen)

def startup(reason, **kwargs):
	setConfiguredSettings()

def Plugins(**kwargs):
	from os import path
	if path.exists(PROC_ET_3DMODE) or path.exists(PROC_DM_3DMODE):
		from Plugins.Plugin import PluginDescriptor
		return [PluginDescriptor(name = "OSD 3D setup", description = _("Adjust 3D settings"), where = PluginDescriptor.WHERE_PLUGINMENU, fnc = main),
					PluginDescriptor(name = "OSD 3D setup", description = "", where = PluginDescriptor.WHERE_SESSIONSTART, fnc = startup)]
	return []
