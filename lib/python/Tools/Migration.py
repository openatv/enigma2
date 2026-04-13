from Components.config import ConfigBoolean, ConfigSubsection, ConfigText, config


def migrateSettings():
	try:
		config.misc.migrationVersion = ConfigText("0")
		migrationVersion = int(config.misc.migrationVersion.value)
	except Exception:
		migrationVersion = 0
	if migrationVersion < 1:
		migrateMenuSort()
		migrateTimeshift()
	elif migrationVersion < 2:
		migrateFileCommander()
	config.misc.migrationVersion.value = "2"
	config.misc.migrationVersion.save()


def migrateMenuSort():  # This function needs to called in StartEnigma after init of config.usage.menu_sort_weight!
	'''
	Migrate the old menu.xml id's to the new key's.
	NOTE: This method can be removed at end of 2022 because it's only a temporary need.
	'''
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
	# Update menu number display setting.
	config.usage.menu_show_numbers = ConfigBoolean(default=False)
	if config.usage.menu_show_numbers.value and config.usage.menuEntryStyle.value == "text":
		config.usage.menu_show_numbers.value = config.usage.menu_show_numbers.default  # Remove the old setting.
		config.usage.menuEntryStyle.value = "number"  # Save the new setting.
		config.usage.menu_show_numbers.save()
		config.usage.menuEntryStyle.save()
	# Update menu sort order setting.
	config.usage.menu_sort_mode = ConfigText(default="user")
	oldValue = config.usage.menu_sort_mode.value
	if oldValue == "a_z":
		oldValue = "alpha"
	if oldValue != config.usage.menuSortOrder.value:
		config.usage.menu_sort_mode.value = config.usage.menu_sort_mode.default  # Remove the old setting.
		config.usage.menuSortOrder.value = "user"  # Save the new setting.
		config.usage.menu_sort_mode.save()
		config.usage.menuSortOrder.save()
	# Update menu sort hide / show / resorting dictionary setting.
	oldSettings = config.usage.menu_sort_weight.getSavedValue()
	if oldSettings:
		newSettings = oldSettings
		for key in menuMappings.keys():
			newSettings = newSettings.replace("'%s':" % key, "'%s':" % menuMappings[key])
		if newSettings != oldSettings:
			print(f"[Migration] migrateMenuSort: Value changed from '{oldSettings}' to '{newSettings}'.")
			try:
				config.usage.menu_sort_weight.value = eval(newSettings)  # Test and save the new settings.
				config.usage.menu_sort_weight.save()
			except Exception as err:
				print(f"[Migration] migrateMenuSort Error: {err}!")


def migrateTimeshift():
	# Update time shift settings.
	stringList = (
		("startdelay", "startDelay", "0"),
		("timeshiftCheckEvents", "checkEvents", "0"),
		("timeshiftCheckFreeSpace", "checkFreeSpace", "0"),
		("timeshiftMaxHours", "maxHours", "12"),
		("timeshiftMaxEvents", "maxEvents", "12")
	)
	booleanList = (
		("showinfobar", "showInfoBar", True),
		("showlivetvmsg", "showLiveTVMsg", True),
		("filesplitting", "fileSplitting", True),
		("stopwhilerecording", "stopWhileRecording", False),
	)
	try:
		for item in stringList:
			setattr(config.timeshift, item[0], ConfigText(default=item[2]))
			value = getattr(config.timeshift, item[0]).value
			default = getattr(config.timeshift, item[0]).default
			if value != default:
				getattr(config.timeshift, item[1]).value = value
				getattr(config.timeshift, item[0]).value = default
				getattr(config.timeshift, item[0]).save()
				getattr(config.timeshift, item[1]).save()
		for item in booleanList:
			setattr(config.timeshift, item[0], ConfigBoolean(default=item[2]))
			value = getattr(config.timeshift, item[0]).value
			default = getattr(config.timeshift, item[0]).default
			if value != default:
				getattr(config.timeshift, item[1]).value = value
				getattr(config.timeshift, item[0]).value = default
				getattr(config.timeshift, item[0]).save()
				getattr(config.timeshift, item[1]).save()
	except Exception as err:
		print(f"[Migration] migrateTimeshift Error: {err}!")


def migrateFileCommander():
	attributes = (
		("add_extensionmenu_entry", "addToExtensionMenu"),
		("add_mainmenu_entry", "addToMainMenu"),
		("bookmarks", "bookmarks"),
		("calculate_directorysize", None),
		("change_navbutton", None),
		("diashow", None),
		("editposition_lineend", "editLineEnd"),
		("extension", "extension"),
		("firstDirs", "directoriesFirst"),
		("hashes", None),
		("input_length", None),
		("my_extension", "myExtensions"),
		("path_default", "defaultPathLeft"),
		("pathDefault", "defaultPathLeft"),
		("path_left", None),
		("path_right", None),
		("savedir_left", "savePathLeft"),
		("savedir_right", "savePathRight"),
		("script_messagelen", "scriptMessageLength"),
		("script_priority_ionice", "scriptPriorityIONice"),
		("script_priority_nice", "scriptPriorityNice"),
		("showScriptCompleted_message", "showScriptCompletedMessage"),
		("showTaskCompleted_message", "showTaskCompletedMessage"),
		("sortDirs", "sortDirectories"),
		("sortFiles_left", "sortFilesLeft"),
		("sortFiles_right", "sortFilesRight"),
		("unknown_extension_as_text", "useViewerForUnknown")
	)
	config.plugins.FileCommander = ConfigSubsection()
	config.plugins.filecommander = ConfigSubsection()
	for old, new in attributes:
		setattr(config.plugins.filecommander, old, ConfigText(default=""))
		value = getattr(config.plugins.filecommander, old).value
		if value and new:
			if value == "True":
				value = True
			if value == "False":
				value = False
			if old == "bookmarks":
				value = [x for x in value[2:-2].split("', '")]
			getattr(config.plugins.FileCommander, new).value = value
		getattr(config.plugins.filecommander, old).value = ""
	config.plugins.filecommander.save()
	config.plugins.FileCommander.save()
