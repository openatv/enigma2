from Components.config import ConfigBoolean, ConfigText, config

menuMappings = {
	"info_screen": "information",
	"timer_menu": "timermenu",
	"setup_selection": "setup",
	"rec_setup": "rec",
	"epg_menu": "epg",
	"display_selection": "display",
	"osd_setup": "osd_menu",
	"service_searching_selection": "scan",
	"cam_setup": "cam",
	"extended_selection": "extended",
	"hardisk_selection": "harddisk",
	"network_menu": "network",
	"system_selection": "system",
	"standby_restart_list": "shutdown"
}


def migrateSettings():
	migrateMenuSort()


def migrateMenuSort():  # This function needs to called in StartEnigma after init of config.usage.menu_sort_weight!
	'''
	Migrate the old menu.xml id's to the new key's.
	NOTE: This method can be removed at end of 2022 because it's only a temporary need.
	'''

	# Update menu number display setting...
	config.usage.menu_show_numbers = ConfigBoolean(False)
	if config.usage.menu_show_numbers.value and config.usage.menuEntryStyle.value == "text":
		config.usage.menu_show_numbers.value = False  # Remove the old setting.
		config.usage.menu_show_numbers.save()
		config.usage.menuEntryStyle.value = "number"  # Save the new setting.
		config.usage.menuEntryStyle.save()

	# Update menu sort order setting...
	config.usage.menu_sort_mode = ConfigText("user")
	oldValue = config.usage.menu_sort_mode.value
	if oldValue == "a_z":
		oldValue = "alpha"
	if oldValue != config.usage.menuSortOrder.value:
		config.usage.menu_sort_mode.value = "user"  # Remove the old setting.
		config.usage.menu_sort_mode.save()
		config.usage.menuSortOrder.value = "user"  # Save the new setting.
		config.usage.menuSortOrder.save()

	# Update menu sort hide / show / resorting dictionary setting...
	oldSettings = config.usage.menu_sort_weight.getSavedValue()
	if oldSettings:
		newSettings = oldSettings
		for key in menuMappings.keys():
			newSettings = newSettings.replace("'%s':" % key, "'%s':" % menuMappings[key])
		if newSettings != oldSettings:
			print("[Migration] migrateMenuSort: Value changed from '%s' to '%s'." % (oldSettings, newSettings))
			try:
				config.usage.menu_sort_weight.value = eval(newSettings)  # Test and save the new settings.
				config.usage.menu_sort_weight.save()
			except Exception as err:
				print("[Migration] migrateMenuSort Error: %s!" % str(err))
