from config import ConfigSubsection, ConfigYesNo, config, ConfigSelection
from enigma import Misc_Options
import os

def InitUsageConfig():
	config.usage = ConfigSubsection();
	config.usage.showdish = ConfigYesNo(default = False)
	config.usage.multibouquet = ConfigYesNo(default = False)
	config.usage.quickzap_bouquet_change = ConfigYesNo(default = False)
	config.usage.e1like_radio_mode = ConfigYesNo(default = False)
	config.usage.infobar_timeout = ConfigSelection(default = "5", choices = [
		("0", _("no timeout")), ("1", "1 " + _("second")), ("2", "2 " + _("seconds")), ("3", "3 " + _("seconds")),
		("4", "4 " + _("seconds")), ("5", "5 " + _("seconds")), ("6", "6 " + _("seconds")), ("7", "7 " + _("seconds")),
		("8", "8 " + _("seconds")), ("9", "9 " + _("seconds")), ("10", "10 " + _("seconds"))])
	config.usage.show_infobar_on_zap = ConfigYesNo(default = True)
	config.usage.show_infobar_on_skip = ConfigYesNo(default = True)
	config.usage.show_infobar_on_event_change = ConfigYesNo(default = True)
	config.usage.hdd_standby = ConfigSelection(default = "120", choices = [
		("0", _("no standby")), ("2", "10 " + _("seconds")), ("6", "30 " + _("seconds")),
		("12", "1 " + _("minute")), ("24", "2 " + _("minutes")),
		("60", "5 " + _("minutes")), ("120", "10 " + _("minutes")), ("240", "20 " + _("minutes")),
		("241", "30 " + _("minutes")), ("242", "1 " + _("hour")), ("244", "2 " + _("hours")),
		("248", "4 " + _("hours")) ])
	config.usage.output_12V = ConfigSelection(default = "do not change", choices = [
		("do not change", _("do not change")), ("off", _("off")), ("on", _("on")) ])

	def setHDDStandby(configElement):
		os.system("hdparm -S" + configElement.value + " /dev/ide/host0/bus0/target0/lun0/disc")
	config.usage.hdd_standby.addNotifier(setHDDStandby)

	def set12VOutput(configElement):
		if configElement.value == "on":
			Misc_Options.getInstance().set_12V_output(1)
		elif configElement.value == "off":
			Misc_Options.getInstance().set_12V_output(0)
	config.usage.output_12V.addNotifier(set12VOutput)
