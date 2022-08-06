from __future__ import absolute_import
from Plugins.Plugin import PluginDescriptor
from os import stat
from .Vps import vps_timers
from .Vps_setup import VPS_Setup
from .Modifications import register_vps
from . import _
from boxbranding import getImageDistro

# Config
from Components.config import config, ConfigYesNo, ConfigSubsection, ConfigInteger, ConfigSelection

config.plugins.vps = ConfigSubsection()
config.plugins.vps.enabled = ConfigYesNo(default=True)
config.plugins.vps.do_PDC_check = ConfigYesNo(default=True)
config.plugins.vps.initial_time = ConfigInteger(default=10, limits=(0, 120))
config.plugins.vps.allow_wakeup = ConfigYesNo(default=False)
config.plugins.vps.allow_seeking_multiple_pdc = ConfigYesNo(default=True)
config.plugins.vps.vps_default = ConfigSelection(choices=[("no", _("No")), ("yes_safe", _("Yes (safe mode)")), ("yes", _("Yes"))], default="no")
config.plugins.vps.instanttimer = ConfigSelection(choices=[("no", _("No")), ("yes_safe", _("Yes (safe mode)")), ("yes", _("Yes")), ("ask", _("always ask"))], default="ask")
config.plugins.vps.infotext = ConfigInteger(default=0)

# 04 Feb 2021.  If we don't force-save this then
#   config.plugins.vps.enabled=False
# hangs around in the settings file even after you set it back to True.
# Something else seems to be wrong somewhere, but this is a quick and
# imple fix/workaround.
#
config.plugins.vps.enabled.save_forced = True


def autostart(reason, **kwargs):
	if reason == 0:
		if "session" in kwargs:
			session = kwargs["session"]
			vps_timers.session = session
			vps_timers.checkNextAfterEventAuto()
			vps_timers.checkTimer()

			try:
				from Plugins.Extensions.WebInterface.WebChilds.Toplevel import addExternalChild
				from Plugins.Extensions.WebInterface.WebChilds.Screenpage import ScreenPage
				from twisted.web import static
				from twisted.python import util
				from enigma import eEnv
			except ImportError as ie:
				pass
			else:
				if hasattr(static.File, 'render_GET'):
					class File(static.File):
						def render_POST(self, request):
							return self.render_GET(request)
				else:
					File = static.File

				root = File(eEnv.resolve("${libdir}/enigma2/python/Plugins/SystemPlugins/vps/web-data"))
				root.putChild("web", ScreenPage(session, util.sibpath(__file__, "web"), True))
				addExternalChild(("vpsplugin", root, "VPS-Plugin", "1", False))
		else:
			register_vps()

	elif reason == 1:
		vps_timers.shutdown()


def setup(session, **kwargs):
	session.openWithCallback(doneConfig, VPS_Setup)


def doneConfig(session, **kwargs):
	vps_timers.checkTimer()


def startSetup(menuid):
	if getImageDistro() in ('teamblue'):
		if menuid != "general_menu":
			return []
	elif getImageDistro() in ('openhdf'):
		if menuid != "record_menu":
			return []
	elif getImageDistro() in ('openvix'):
		if menuid != "rec":
			return []
	else:
		if menuid != "system":
			return []
	return [(_("VPS Settings"), setup, "vps", 50)]


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
