from Components.config import config, ConfigYesNo, ConfigSubsection, ConfigInteger, ConfigSelection
from Plugins.Plugin import PluginDescriptor
from .Vps import vps_timers
from .Vps_setup import VPS_Setup
from .Modifications import register_vps

config.plugins.vps = ConfigSubsection()
config.plugins.vps.enabled = ConfigYesNo(default=True)
config.plugins.vps.do_PDC_check = ConfigYesNo(default=True)
config.plugins.vps.initial_time = ConfigInteger(default=10, limits=(0, 120))
config.plugins.vps.allow_wakeup = ConfigYesNo(default=False)
config.plugins.vps.allow_seeking_multiple_pdc = ConfigYesNo(default=True)
config.plugins.vps.vps_default = ConfigSelection(choices=[("no", _("No")), ("yes_safe", _("Yes (safe mode)")), ("yes", _("Yes"))], default="no")
config.plugins.vps.instanttimer = ConfigSelection(choices=[("no", _("No")), ("yes_safe", _("Yes (safe mode)")), ("yes", _("Yes")), ("ask", _("Always ask"))], default="ask")
config.plugins.vps.infotext = ConfigInteger(default=0)

# 04 Feb 2021.  If we don't force-save this then
#   config.plugins.vps.enabled=False
# hangs around in the settings file even after you set it back to True.
# Something else seems to be wrong somewhere, but this is a quick and
# imple fix/workaround.
#
config.plugins.vps.enabled.save_forced = True

vps_already_registered = False


def autostart(reason, **kwargs):
	global vps_already_registered
	if reason == 0:
		if "session" in kwargs:
			session = kwargs["session"]
			vps_timers.session = session
			vps_timers.checkNextAfterEventAuto()
			vps_timers.checkTimer()
		elif not vps_already_registered:
			register_vps()
			vps_already_registered = True

	elif reason == 1:
		vps_timers.shutdown()


def setup(session, **kwargs):
	session.openWithCallback(setupCallback, VPS_Setup)


def setupCallback(result=None):
	if result is None:
		vps_timers.checkTimer()


def startSetup(menuid):
	if menuid != "timermenu":
		return []
	return [(_("VPS Settings"), setup, "vps", 90)]


def getNextWakeup():
	return vps_timers.NextWakeup()


def Plugins(**kwargs):
	return [
		PluginDescriptor(
			name="VPS",
			where=[
				PluginDescriptor.WHERE_AUTOSTART,
				PluginDescriptor.WHERE_SESSIONSTART
			],
			fnc=autostart,
			wakeupfnc=getNextWakeup,
			needsRestart=True
		),
		PluginDescriptor(
			name=_("VPS Settings"),
			where=PluginDescriptor.WHERE_MENU,
			fnc=startSetup,
			needsRestart=True
		),
	]
