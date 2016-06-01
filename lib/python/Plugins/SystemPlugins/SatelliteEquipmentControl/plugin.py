from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Plugins.Plugin import PluginDescriptor

from Components.ConfigList import ConfigListScreen
from Components.ActionMap import ActionMap
from Components.config import config
from Components.NimManager import nimmanager as nimmgr

class SecParameterSetup(Screen, ConfigListScreen):
	skin = """
		<screen position="100,100" size="560,400" title="Satellite equipment setup" >
			<widget name="config" position="10,10" size="540,390" />
		</screen>"""
	def __init__(self, session):
		self.skin = SecParameterSetup.skin

		self["actions"] = ActionMap(["SetupActions", "MenuActions"],
		{
			"ok": self.keySave,
			"cancel": self.keyCancel,
			"menu": self.closeRecursive,
		}, -2)

		Screen.__init__(self, session)
		list = [
			(_("Delay after diseqc reset command"), config.sec.delay_after_diseqc_reset_cmd),
			(_("Delay after diseqc peripherial poweron command"), config.sec.delay_after_diseqc_peripherial_poweron_cmd),
			(_("Delay after continuous tone disable before diseqc"), config.sec.delay_after_continuous_tone_disable_before_diseqc),
			(_("Delay after final continuous tone change"), config.sec.delay_after_final_continuous_tone_change),
			(_("Delay after last voltage change"), config.sec.delay_after_final_voltage_change),
			(_("Delay between diseqc commands"), config.sec.delay_between_diseqc_repeats),
			(_("Delay after last diseqc command"), config.sec.delay_after_last_diseqc_command),
			(_("Delay after toneburst"), config.sec.delay_after_toneburst),
			(_("Delay after change voltage before switch command"), config.sec.delay_after_change_voltage_before_switch_command),
			(_("Delay after enable voltage before switch command"), config.sec.delay_after_enable_voltage_before_switch_command),
			(_("Delay between switch and motor command"), config.sec.delay_between_switch_and_motor_command),
			(_("Delay after set voltage before measure motor power"), config.sec.delay_after_voltage_change_before_measure_idle_inputpower),
			(_("Delay after enable voltage before motor command"), config.sec.delay_after_enable_voltage_before_motor_command),
			(_("Delay after motor stop command"), config.sec.delay_after_motor_stop_command),
			(_("Delay after voltage change before motor command"), config.sec.delay_after_voltage_change_before_motor_command),
			(_("Delay before sequence repeat"), config.sec.delay_before_sequence_repeat),
			(_("Motor running timeout"), config.sec.motor_running_timeout),
			(_("Motor command retries"), config.sec.motor_command_retries) ]
		ConfigListScreen.__init__(self, list)

session = None

def confirmed(answer):
	global session
	if answer:
		session.open(SecParameterSetup)

def SecSetupMain(Session, **kwargs):
	global session
	session = Session
	session.openWithCallback(confirmed, MessageBox, _("Please do not change any values unless you know what you are doing!"), MessageBox.TYPE_INFO)

def SecSetupStart(menuid):
	show = False

	# other menu than "scan"?
	if menuid != "scan":
		return [ ]

	# only show if DVB-S frontends are available
	for slot in nimmgr.nim_slots:
		if slot.canBeCompatible("DVB-S"):
			return [(_("Satellite equipment setup"), SecSetupMain, "satellite_equipment_setup", None)]

	return [ ]

def Plugins(**kwargs):
	if nimmgr.hasNimType("DVB-S"):
		return PluginDescriptor(name=_("Satellite equipment setup"), description=_("Setup your satellite equipment"), where = PluginDescriptor.WHERE_MENU, needsRestart = False, fnc=SecSetupStart)
	else:
		return []
