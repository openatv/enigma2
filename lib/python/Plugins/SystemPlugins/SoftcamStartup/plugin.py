from Plugins.Plugin import PluginDescriptor
from Components.config import config, ConfigSubsection, ConfigYesNo
from Tools.BoundFunction import boundFunction
import os

config.misc.softcam_startup = ConfigSubsection()
config.misc.softcam_startup.extension_menu = ConfigYesNo(default = True)

CamInstalled = False
for cam in os.listdir("/etc/init.d"):
	if cam.startswith('softcam.') and not cam.endswith('None'):
		CamInstalled = True
	elif cam.startswith('cardserver.') and not cam.endswith('None'):
		CamInstalled = True
	else:
		pass

def main(session, showExtentionMenuOption=False, **kwargs):
	import SoftcamStartup
	session.open(SoftcamStartup.SoftcamStartup, showExtentionMenuOption)

def menu(menuid, **kwargs):
	if menuid == "cam" and CamInstalled:
		return [(_("Softcam startup..."), boundFunction(main, showExtentionMenuOption=True), "softcam_startup", -1)]
	return []

def Plugins(**kwargs):
	name = _("Softcam startup")
	description = _("Configure the startup of your softcams")
	list = [(PluginDescriptor(name=name, description=description, where = PluginDescriptor.WHERE_MENU, fnc = menu))]
	if config.misc.softcam_startup.extension_menu.value:
		list.append(PluginDescriptor(name=name, description=description, where = PluginDescriptor.WHERE_EXTENSIONSMENU, fnc=main))
	return list
