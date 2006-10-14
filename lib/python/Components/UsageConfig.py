from config import ConfigSubsection, ConfigYesNo, config, ConfigSelection

def InitUsageConfig():
	config.usage = ConfigSubsection();
	config.usage.showdish = ConfigYesNo(default = False)
	config.usage.multibouquet = ConfigYesNo(default = False)
	config.usage.quickzap_bouquet_change = ConfigYesNo(default = False)
	config.usage.e1like_radio_mode = ConfigYesNo(default = False)
	config.usage.infobar_timeout = ConfigSelection(default = "5", choices = [
		("0", _("no timeout")), ("1", _("1 second")), ("2", _("2 seconds")), ("3", _("3 seconds")),
		("4", _("4 seconds")), ("5", _("5 seconds")), ("6", _("6 seconds")), ("7", _("7 seconds")),
		("8", _("8 seconds")), ("9", _("9 seconds")), ("10", _("10 seconds"))])
	config.usage.show_infobar_on_zap = ConfigYesNo(default = True)
	config.usage.show_infobar_on_skip = ConfigYesNo(default = True)
