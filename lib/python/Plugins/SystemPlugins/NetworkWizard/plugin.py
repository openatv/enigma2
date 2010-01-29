from Screens.Screen import Screen
from Plugins.Plugin import PluginDescriptor
from Components.config import getConfigListEntry, config

def NetworkWizardMain(session, **kwargs):
	session.open(NetworkWizard)

def startSetup(menuid):
	if menuid != "system": 
		return [ ]

	return [(_("Network Wizard"), NetworkWizardMain, "nw_wizard", 40)]

def NetworkWizard(*args, **kwargs):
	from NetworkWizard import NetworkWizard
	return NetworkWizard(*args, **kwargs)

def Plugins(**kwargs):
	list = []
	if config.misc.firstrun.value:
		list.append(PluginDescriptor(name=_("Network Wizard"), where = PluginDescriptor.WHERE_WIZARD, fnc=(25, NetworkWizard)))
	return list
