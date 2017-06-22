from config import config, ConfigSubsection, ConfigYesNo, ConfigText, ConfigSelection, ConfigIP, ConfigInteger, ConfigSubList, ConfigClock
from SystemInfo import SystemInfo

def InitClientMode():
	config.clientmode = ConfigSubsection()
	config.clientmode.enabled = ConfigYesNo(default = False)
	def clientModeChanged(configElement):
		SystemInfo["ClientModeEnabled"] = configElement.value == True
		SystemInfo["ClientModeDisabled"] = configElement.value != True
	config.clientmode.enabled.addNotifier(clientModeChanged, immediate_feedback = True, initial_call = True)
	config.clientmode.serverAddressType = ConfigSelection(default = "ip", choices = [("ip", _("IP")), ("domain", _("Domain"))])
	config.clientmode.serverIP = ConfigIP( default = [0,0,0,0], auto_jump=True)
	config.clientmode.serverDomain = ConfigText(default = "", fixed_size = False)
	config.clientmode.serverStreamingPort = ConfigInteger(default = 8001, limits=(1,65535))
	config.clientmode.serverFTPusername = ConfigText(default = "root", fixed_size = False)
	config.clientmode.serverFTPpassword = ConfigText(default = "", fixed_size = False)
	config.clientmode.serverFTPPort = ConfigInteger(default = 21, limits=(1,65535))
	config.clientmode.passive = ConfigYesNo(False)
	config.clientmode.enableSchedule = ConfigYesNo(False)
	config.clientmode.scheduleRepeatInterval = ConfigSelection(default = "360", choices = [("60", _("Every hour")), ("120", _("Every 2 hours")), ("180", _("Every 3 hours")), ("360", _("Every 6 hours")), ("720", _("Every 12 hours")), ("daily", _("Daily"))])
	config.clientmode.scheduletime = ConfigClock(default = 0) # 1:00
	# to reinstate normal mode settings
	config.clientmode.nim_cache = ConfigText(default = "", fixed_size = False)
	config.clientmode.remote_fallback_enabled_cache = ConfigYesNo(default = False)
	config.clientmode.remote_fallback_cache = ConfigText(default = "", fixed_size = False)
	config.clientmode.timer_sanity_check_enabled_cache = ConfigYesNo(default = True)
