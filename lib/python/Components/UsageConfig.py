from config import ConfigSubsection, ConfigYesNo, config

def InitUsageConfig():
	config.usage = ConfigSubsection();
	config.usage.showdish = ConfigYesNo(default = False)
	config.usage.multibouquet = ConfigYesNo(default = False)
	config.usage.quickzap_bouquet_change = ConfigYesNo(default = False)
	config.usage.e1like_radio_mode = ConfigYesNo(default = False)
