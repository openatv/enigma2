from Screens.MessageBox import MessageBox
from Screens.Setup import Setup
from Plugins.Plugin import PluginDescriptor

from Components.NimManager import nimmanager as nimmgr


class SecParameterSettings(Setup):
	def __init__(self, session):
		Setup.__init__(self, session=session, setup="SecParameterSettings", plugin="SystemPlugins/SatelliteEquipmentControl")


session = None


def confirmed(answer):
	global session
	if answer:
		session.open(SecParameterSettings)


def SecSetupMain(Session, **kwargs):
	global session
	session = Session
	session.openWithCallback(confirmed, MessageBox, _("Please do not change any values unless you know what you are doing!"), MessageBox.TYPE_INFO)


def SecSetupStart(menuid):
	show = False  # noqa F841

	# other menu than "scan"?
	if menuid != "scan":
		return []

	# only show if DVB-S frontends are available
	for slot in nimmgr.nim_slots:
		if slot.canBeCompatible("DVB-S"):
			return [(_("Satellite equipment setup"), SecSetupMain, "satellite_equipment_setup", None)]

	return []


def Plugins(**kwargs):
	if nimmgr.hasNimType("DVB-S"):
		return PluginDescriptor(name=_("Satellite equipment setup"), description=_("Setup your satellite equipment"), where=PluginDescriptor.WHERE_MENU, needsRestart=False, fnc=SecSetupStart)
	else:
		return []
