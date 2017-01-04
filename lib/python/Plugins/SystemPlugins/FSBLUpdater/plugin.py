from Components.config import config, ConfigBoolean
from Screens.ChoiceBox import ChoiceBox
from Plugins.Plugin import PluginDescriptor
from Tools.HardwareInfo import HardwareInfo

from FSBLUpdater import FSBLUpdater

from Tools.Log import Log
from Tools import Notifications


config.misc.fsbl_update_never = ConfigBoolean(default=False)

class FSBLUpdateHandler(object):
	def __init__(self):
		self._boxtype = HardwareInfo().get_device_name()
		self._session = None

	def check(self, session):
		if config.misc.fsbl_update_never.value:
			return
		self._session = session
		if FSBLUpdater.isUpdateRequired(self._boxtype):
			Log.w("FSBL Update required!")
			choices = [
				(_("Yes"), "yes"),
				(_("No"), "no"),
				(_("Don't ask again!"), "never")
			]
			txt = _("DO NOT POWER OFF YOUR DEVICE WHILE UPDATING!\nUpdate now?")
			Notifications.AddNotificationWithCallback(self._startFSBLUpdater, ChoiceBox, list=choices, title = txt, windowTitle=_("Bootloader update required!"))
		else:
			Log.i("No FSBL update required!")

	def _startFSBLUpdater(self, answer):
		if not answer:
			return
		Log.i(answer)
		answer = answer[1]
		if answer == "yes":
			self._session.open(FSBLUpdater, HardwareInfo().get_device_name())
		elif answer == "never":
			config.misc.fsbl_update_never.value = True
			config.misc.fsbl_update_never.save()

global updateHandler
updateHandler = None
def sessionstart(session, *args, **kwargs):
	global updateHandler
	updateHandler = FSBLUpdateHandler()
	updateHandler.check(session)

def Plugins(path, **kwargs):
	global plugin_path
	plugin_path = path
	return [
		PluginDescriptor(
			name=_("FSBL Update Check"),
			where = PluginDescriptor.WHERE_SESSIONSTART,
			fnc=sessionstart,)]