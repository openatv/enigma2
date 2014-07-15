from Screens.Screen import Screen
from Plugins.Plugin import PluginDescriptor

def main(session, **kwargs):
	pass

def main1(session, **kwargs):
	pass

def Plugins(**kwargs):
	return [
		PluginDescriptor(
						name = "IceTV",
						description = _("IceTV"),
						where = PluginDescriptor.WHERE_EXTENSIONSMENU,
						fnc = main),
		PluginDescriptor(
						name = "IceTV",
						description = _("IceTV"),
						icon = "IceTV_icon.png",
						where = PluginDescriptor.WHERE_PLUGINMENU,
						fnc = main1)]
