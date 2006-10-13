from config import ConfigSubsection, ConfigYesNo, config, ConfigSelection

def InitUsageConfig():
	config.usage = ConfigSubsection();
	config.usage.showdish = ConfigYesNo(default = False)
	config.usage.multibouquet = ConfigYesNo(default = False)
	config.usage.quickzap_bouquet_change = ConfigYesNo(default = False)
	config.usage.e1like_radio_mode = ConfigYesNo(default = False)
	config.usage.infobar_timeout = ConfigSelection(default = _("5 seconds"), choices = [
		_("no timeout"), _("1 second"), _("2 seconds"), _("3 seconds"), _("4 seconds"),
		_("5 seconds"), _("6 seconds"), _("7 seconds"), _("8 seconds"),
		_("9 seconds"), _("10 seconds")])
	config.usage.show_infobar_on_zap = ConfigYesNo(default = True)
	config.usage.show_infobar_on_skip = ConfigYesNo(default = True)
