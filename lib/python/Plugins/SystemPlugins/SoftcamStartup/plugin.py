from Plugins.Plugin import PluginDescriptor
from Components.config import config, ConfigSubsection, ConfigYesNo
from Tools.BoundFunction import boundFunction

config.misc.softcam_startup = ConfigSubsection()
config.misc.softcam_startup.extension_menu = ConfigYesNo(default = True)

def main(session, showExtentionMenuOption=False, **kwargs):
	import SoftcamStartup
	session.open(SoftcamStartup.SoftcamStartup, showExtentionMenuOption)

def menu(menuid, **kwargs):
	if menuid == "cam":
		return [(_("Softcam startup..."), boundFunction(main, showExtentionMenuOption=True), "softcam_startup", -1)]
	return []

def Plugins(**kwargs):
	name = _("Softcam startup")
	description = _("Configure the startup of your softcams")
	list = [(PluginDescriptor(name=name, description=description, where = PluginDescriptor.WHERE_MENU, fnc = menu))]
	if config.misc.softcam_startup.extension_menu.value:
		list.append(PluginDescriptor(name=name, description=description, where = PluginDescriptor.WHERE_EXTENSIONSMENU, fnc=main))
	return list
