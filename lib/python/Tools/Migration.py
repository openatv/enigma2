from Components.config import ConfigBoolean, ConfigText, ConfigSelectionNumber, ConfigYesNo, config

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
	migrateTimeshift()


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


def migrateTimeshift():
	# Time shift settings
	try:
		config.timeshift.startdelay = ConfigText(default="0")
		if config.timeshift.startdelay.value != "0":
			config.timeshift.startDelay.value = int(config.timeshift.startdelay.value)
			config.timeshift.startDelay.save()
			config.timeshift.startdelay.value = "0"
			config.timeshift.startdelay.save()

		config.timeshift.timeshiftCheckEvents = ConfigText(default="0")
		if config.timeshift.timeshiftCheckEvents.value != "0":
			config.timeshift.checkEvents.value = int(config.timeshift.timeshiftCheckEvents.value)
			config.timeshift.checkEvents.save()
			config.timeshift.timeshiftCheckEvents.value = "0"
			config.timeshift.timeshiftCheckEvents.save()

		config.timeshift.timeshiftCheckFreeSpace = ConfigText(default="0")
		if config.timeshift.timeshiftCheckFreeSpace.value != "0":
			config.timeshift.checkFreeSpace.value = int(config.timeshift.timeshiftCheckFreeSpace.value)
			config.timeshift.checkFreeSpace.save()
			config.timeshift.timeshiftCheckFreeSpace.value = "0"
			config.timeshift.timeshiftCheckFreeSpace.save()

		config.timeshift.timeshiftMaxHours = ConfigSelectionNumber(min=1, max=999, stepwidth=1, default=12, wraparound=True)
		if config.timeshift.timeshiftMaxHours.value != 12:
			config.timeshift.maxHours.value = config.timeshift.timeshiftMaxHours.value
			config.timeshift.maxHours.save()
			config.timeshift.timeshiftMaxHours.value = 12
			config.timeshift.timeshiftMaxHours.save()

		config.timeshift.timeshiftMaxEvents = ConfigSelectionNumber(min=1, max=999, stepwidth=1, default=12, wraparound=True)
		if config.timeshift.timeshiftMaxEvents.value != 12:
			config.timeshift.maxEvents.value = config.timeshift.timeshiftMaxEvents.value
			config.timeshift.maxEvents.save()
			config.timeshift.timeshiftMaxEvents.value = 12
			config.timeshift.timeshiftMaxEvents.save()

		config.timeshift.showinfobar = ConfigYesNo(default=True)
		if not config.timeshift.showinfobar.value:
			config.timeshift.showInfoBar.value = config.timeshift.showinfobar.value
			config.timeshift.showInfoBar.save()
			config.timeshift.showinfobar.value = True
			config.timeshift.showinfobar.save()

		config.timeshift.showlivetvmsg = ConfigYesNo(default=True)
		if not config.timeshift.showlivetvmsg.value:
			config.timeshift.showLiveTVMsg.value = config.timeshift.showlivetvmsg.value
			config.timeshift.showLiveTVMsg.save()
			config.timeshift.showlivetvmsg.value = True
			config.timeshift.showlivetvmsg.save()

		config.timeshift.filesplitting = ConfigYesNo(default=True)
		if not config.timeshift.filesplitting.value:
			config.timeshift.fileSplitting.value = config.timeshift.filesplitting.value
			config.timeshift.fileSplitting.save()
			config.timeshift.filesplitting.value = True
			config.timeshift.filesplitting.save()

		config.timeshift.stopwhilerecording = ConfigYesNo(default=False)
		if config.timeshift.stopwhilerecording.value:
			config.timeshift.stopWhileRecording.value = config.timeshift.stopwhilerecording.value
			config.timeshift.stopWhileRecording.save()
			config.timeshift.stopwhilerecording.value = False
			config.timeshift.stopwhilerecording.save()
	except Exception as err:
		print("[Migration] migrateTimeshift Error: %s!" % str(err))
