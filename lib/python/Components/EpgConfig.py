from time import mktime, time

from enigma import RT_HALIGN_CENTER, RT_HALIGN_LEFT, RT_HALIGN_RIGHT, RT_VALIGN_CENTER, RT_WRAP

from Components.config import config, ConfigClock, ConfigNumber, ConfigSelection, ConfigSelectionNumber, ConfigSubsection, ConfigYesNo, NoSave
from Components.SystemInfo import BoxInfo
from Tools.Directories import isPluginInstalled

# Action choice lists.
# Each entry is (value, label) or (value, label, helptext).

epgActions = [
	("", _("Do nothing")),
	("openIMDb", _("IMDb Search")),
	("openTMDb", _("TMDB Search")),
	("sortEPG", _("Sort")),
	("addEditTimer", _("Add Timer")),
	("openTimerList", _("Show Timer List")),
	("openEPGSearch", _("EPG Search")),
	("addEditAutoTimer", _("Add AutoTimer")),
	("openAutoTimerList", _("Show AutoTimer List")),
	("forward24Hours", _("+24 Hours")),
	("back24Hours", _("-24 Hours")),
	("prevPage", _("Previous Page")),
	("nextPage", _("Next Page")),
	("prevBouquet", _("Previous Bouquet")),
	("nextBouquet", _("Next Bouquet")),
	("toggleBouquetList", _("Bouquet List")),
	("enterDateTime", _("Goto Date/Time")),
	("openEventView", _("Event Info")),
	("openSingleEPG", _("Single EPG")),
	("showMovies", _("Recordings")),
]

verticalActions = epgActions + [
	("gotoPrimetime", _("Goto Prime Time")),
	("setBasetime", _("Set Base Time")),
]

okActions = [
	("zap", _("Zap")),
	("zapExit", _("Zap + Exit")),
	("openEventView", _("Event Info")),
]

recActions = [
	("addEditTimerMenu", _("Timer Menu")),
	("addEditTimer", _("Add Timer")),
	# ("addEditTimerSilent", _("Create Timer")),  # Not implemented yet.
	("addEditZapTimerSilent", _("Create Zap Timer")),
	("addEditAutoTimer", _("Add AutoTimer")),
]

infoActions = [
	("", _("Do nothing")),
	("openEventView", _("Event Info")),
	("openSingleEPG", _("Single EPG")),
]

channelUpActions = [
	("forward24Hours", _("+24 Hours")),
	("prevPage", _("Previous Page")),
	("nextBouquet", _("Next Bouquet")),
]

channelDownActions = [
	("back24Hours", _("-24 Hours")),
	("nextPage", _("Next Page")),
	("prevBouquet", _("Previous Bouquet")),
]


def upgradeConfig():
	if config.epgselection.migrationVersion.value < 1:
		oldKeys = []

		def getOldValue(name):
			value = config.content.stored_values
			found = True
			for n in name.split("."):
				value = value.get(n, None)
				if value is None:
					found = False
					break
			return value if found else None

		def upgrade(configItem, name, valuemap=None, mapper=None):
			oldKeys.append(name)
			value = getOldValue(name)
			if value is not None:
				newvalue = None
				if valuemap is not None:
					newvalue = valuemap.get(value, None)
				if newvalue is None and mapper is not None:
					newvalue = mapper(value)
				if newvalue is not None:
					print("[EpgConfig] upgrading %s, mapping value %s to %s" % (name, value, newvalue))
				else:
					print("[EpgConfig] upgrading %s, value %s" % (name, value))
					newvalue = value
				if newvalue is not None:
					configItem.saved_value = newvalue
					configItem.load()

		def upgradePrimetime(configItem, prefix):
			# The old keys store hour and minutes separately, each one only when changed (default 20:15).
			oldKeys.extend((f"epgselection.{prefix}_primetimehour", f"epgselection.{prefix}_primetimemins"))
			hour = getOldValue(f"epgselection.{prefix}_primetimehour")
			mins = getOldValue(f"epgselection.{prefix}_primetimemins")
			if hour is not None or mins is not None:
				print(f"[EpgConfig] upgrading epgselection.{prefix}_primetimehour/mins {hour}:{mins}")
				configItem.saved_value = f"{hour or 20}:{mins or 15}"
				configItem.load()

		print("[EpgConfig] Upgrading EPG settings from flat keys to subsections")

		okMap = {"Zap": "zap", "Zap + Exit": "zapExit"}
		infoMap = {"Channel Info": "openEventView", "Single EPG": "openSingleEPG"}
		# The old vertical OK button also had "Channel Info" (same as "openEventView").
		verticalOkMap = {"Channel Info": "openEventView", "Zap": "zap", "Zap + Exit": "zapExit"}
		# Old color button values -> new action IDs.
		colorMap = {
			"prevpage": "prevPage",
			"nextpage": "nextPage",
			"prevbouquet": "prevBouquet",
			"nextbouquet": "nextBouquet",
			"bouquetlist": "toggleBouquetList",
			"gotodatetime": "enterDateTime",
			"gotoprimetime": "gotoPrimetime",
			"setbasetime": "setBasetime",
			"24minus": "back24Hours",
			"24plus": "forward24Hours",
			"autotimer": "addEditAutoTimer",
			"timer": "addEditTimer",
			"imdb": "openIMDb",
			"tmdb": "openTMDb",
			"showmovies": "showMovies",
			"record": "addEditTimerMenu",
			"epgsearch": "openEPGSearch",
		}
		# Old servicetitle_mode values with a different order.
		titleModeMap = {
			"servicenumber+picon": "picon+servicenumber",
			"servicenumber+picon+servicename": "picon+servicenumber+servicename",
		}
		# graph_channelbtn ("24"/"page"/"bouquet") -> split into btn_channelup / btn_channeldown.
		channelUpMap = {"24": "forward24Hours", "page": "prevPage", "bouquet": "nextBouquet"}
		channelDownMap = {"24": "back24Hours", "page": "nextPage", "bouquet": "prevBouquet"}

		# infobar
		upgrade(config.epgselection.infobar.type_mode, "epgselection.infobar_type_mode")
		upgrade(config.epgselection.infobar.preview_mode, "epgselection.infobar_preview_mode")
		upgrade(config.epgselection.infobar.btn_ok, "epgselection.infobar_ok", okMap)
		upgrade(config.epgselection.infobar.btn_oklong, "epgselection.infobar_oklong", okMap)
		upgrade(config.epgselection.infobar.itemsperpage, "epgselection.infobar_itemsperpage")
		upgrade(config.epgselection.infobar.roundto, "epgselection.infobar_roundto")
		upgrade(config.epgselection.infobar.histminutes, "epgselection.infobar_histminutes")
		upgrade(config.epgselection.infobar.prevtimeperiod, "epgselection.infobar_prevtimeperiod")
		upgradePrimetime(config.epgselection.infobar.primetime, "infobar")
		upgrade(config.epgselection.infobar.servicetitle_mode, "epgselection.infobar_servicetitle_mode", titleModeMap)
		upgrade(config.epgselection.infobar.servfs, "epgselection.infobar_servfs")
		upgrade(config.epgselection.infobar.eventfs, "epgselection.infobar_eventfs")
		upgrade(config.epgselection.infobar.timelinefs, "epgselection.infobar_timelinefs")
		upgrade(config.epgselection.infobar.timeline24h, "epgselection.infobar_timeline24h")
		upgrade(config.epgselection.infobar.servicewidth, "epgselection.infobar_servicewidth")
		upgrade(config.epgselection.infobar.piconwidth, "epgselection.infobar_piconwidth")
		upgrade(config.epgselection.infobar.infowidth, "epgselection.infobar_infowidth")

		# single (formerly "enhanced")
		upgrade(config.epgselection.single.preview_mode, "epgselection.enhanced_preview_mode")
		upgrade(config.epgselection.single.btn_ok, "epgselection.enhanced_ok", okMap)
		upgrade(config.epgselection.single.btn_oklong, "epgselection.enhanced_oklong", okMap)
		upgrade(config.epgselection.single.eventfs, "epgselection.enhanced_eventfs")
		upgrade(config.epgselection.single.itemsperpage, "epgselection.enhanced_itemsperpage")

		# multi
		upgrade(config.epgselection.multi.showbouquet, "epgselection.multi_showbouquet")
		upgrade(config.epgselection.multi.preview_mode, "epgselection.multi_preview_mode")
		upgrade(config.epgselection.multi.btn_ok, "epgselection.multi_ok", okMap)
		upgrade(config.epgselection.multi.btn_oklong, "epgselection.multi_oklong", okMap)
		upgrade(config.epgselection.multi.eventfs, "epgselection.multi_eventfs")
		upgrade(config.epgselection.multi.itemsperpage, "epgselection.multi_itemsperpage")

		# grid (formerly "graph")
		upgrade(config.epgselection.grid.showbouquet, "epgselection.graph_showbouquet")
		upgrade(config.epgselection.grid.preview_mode, "epgselection.graph_preview_mode")
		upgrade(config.epgselection.grid.type_mode, "epgselection.graph_type_mode")
		# upgrade(config.epgselection.grid.highlight_current_events, "epgselection.graph_highlight_current_events")  # Not implemented yet.
		upgrade(config.epgselection.grid.btn_ok, "epgselection.graph_ok", okMap)
		upgrade(config.epgselection.grid.btn_oklong, "epgselection.graph_oklong", okMap)
		upgrade(config.epgselection.grid.btn_info, "epgselection.graph_info", infoMap)
		upgrade(config.epgselection.grid.btn_infolong, "epgselection.graph_infolong", infoMap)
		upgrade(config.epgselection.grid.roundto, "epgselection.graph_roundto")
		upgrade(config.epgselection.grid.histminutes, "epgselection.graph_histminutes")
		upgrade(config.epgselection.grid.prevtimeperiod, "epgselection.graph_prevtimeperiod")
		upgradePrimetime(config.epgselection.grid.primetime, "graph")
		upgrade(config.epgselection.grid.servicetitle_mode, "epgselection.graph_servicetitle_mode", titleModeMap)
		upgrade(config.epgselection.grid.servicename_alignment, "epgselection.graph_servicename_alignment")
		upgrade(config.epgselection.grid.event_alignment, "epgselection.graph_event_alignment")
		upgrade(config.epgselection.grid.servfs, "epgselection.graph_servfs")
		upgrade(config.epgselection.grid.eventfs, "epgselection.graph_eventfs")
		upgrade(config.epgselection.grid.timelinefs, "epgselection.graph_timelinefs")
		upgrade(config.epgselection.grid.timeline24h, "epgselection.graph_timeline24h")
		upgrade(config.epgselection.grid.itemsperpage, "epgselection.graph_itemsperpage")
		upgrade(config.epgselection.grid.pig, "epgselection.graph_pig")
		upgrade(config.epgselection.grid.servicewidth, "epgselection.graph_servicewidth")
		upgrade(config.epgselection.grid.piconwidth, "epgselection.graph_piconwidth")
		upgrade(config.epgselection.grid.infowidth, "epgselection.graph_infowidth")
		upgrade(config.epgselection.grid.rec_icon_height, "epgselection.graph_rec_icon_height")
		upgrade(config.epgselection.grid.startmode, "epgselection.graph_startmode")
		# graph_channelbtn is a single key that becomes two separate channel-direction keys
		upgrade(config.epgselection.grid.btn_channelup, "epgselection.graph_channelbtn", channelUpMap)
		upgrade(config.epgselection.grid.btn_channeldown, "epgselection.graph_channelbtn", channelDownMap)
		upgrade(config.epgselection.grid.btn_red, "epgselection.graph_red", colorMap)
		upgrade(config.epgselection.grid.btn_green, "epgselection.graph_green", colorMap)
		upgrade(config.epgselection.grid.btn_yellow, "epgselection.graph_yellow", colorMap)
		upgrade(config.epgselection.grid.btn_blue, "epgselection.graph_blue", colorMap)

		# vertical
		upgradePrimetime(config.epgselection.vertical.primetime, "vertical")
		upgrade(config.epgselection.vertical.itemsperpage, "epgselection.vertical_itemsperpage")
		upgrade(config.epgselection.vertical.eventfs, "epgselection.vertical_eventfs")
		upgrade(config.epgselection.vertical.preview_mode, "epgselection.vertical_preview_mode")
		upgrade(config.epgselection.vertical.pig, "epgselection.vertical_pig")
		upgrade(config.epgselection.vertical.eventmarker, "epgselection.vertical_eventmarker")
		upgrade(config.epgselection.vertical.showlines, "epgselection.vertical_showlines")
		upgrade(config.epgselection.vertical.startmode, "epgselection.vertical_startmode")
		upgrade(config.epgselection.vertical.channelbtn, "epgselection.vertical_channelbtn")
		upgrade(config.epgselection.vertical.channelbtn_invert, "epgselection.vertical_channelbtn_invert")
		upgrade(config.epgselection.vertical.updownbtn, "epgselection.vertical_updownbtn")
		upgrade(config.epgselection.vertical.btn_ok, "epgselection.vertical_ok", verticalOkMap)
		upgrade(config.epgselection.vertical.btn_oklong, "epgselection.vertical_oklong", verticalOkMap)
		upgrade(config.epgselection.vertical.btn_info, "epgselection.vertical_info", infoMap)
		upgrade(config.epgselection.vertical.btn_infolong, "epgselection.vertical_infolong", infoMap)
		upgrade(config.epgselection.vertical.btn_red, "epgselection.vertical_red", colorMap)
		upgrade(config.epgselection.vertical.btn_green, "epgselection.vertical_green", colorMap)
		upgrade(config.epgselection.vertical.btn_yellow, "epgselection.vertical_yellow", colorMap)
		upgrade(config.epgselection.vertical.btn_blue, "epgselection.vertical_blue", colorMap)

		# Remove the migrated old keys from the settings.
		storedValues = config.epgselection.content.stored_values
		for name in oldKeys:
			storedValues.pop(name.split(".", 1)[1], None)
		config.epgselection.migrationVersion.value = 1
		config.epgselection.migrationVersion.save()


def initEPGConfig():
	config.epgselection = ConfigSubsection()
	config.epgselection.migrationVersion = ConfigNumber(default=0)
	config.epgselection.sort = ConfigSelection(default="0", choices=[
		("0", _("Time")),
		("1", _("Alphanumeric")),
	])
	config.epgselection.overjump = ConfigYesNo(default=False)

	tmdb = isPluginInstalled("tmdb")

	serviceTitleChoices = [
		("servicename", _("Service name")),
		("picon", _("Picon")),
		("picon+servicename", _("Picon and service name")),
		("servicenumber+picon", _("Service number and picon")),
		("picon+servicenumber", _("Picon and service number")),
		("servicenumber+servicename", _("Service number and service name")),
		("picon+servicenumber+servicename", _("Picon, service number and service name")),
		("servicenumber+picon+servicename", _("Service number, picon and service name")),
	]

	singleBrowseModeChoices = [
		("currentservice", _("Select current service")),
		("lastepgservice", _("Select last browsed service")),
	]

	multiBrowseModeChoices = [
		("currentservice", _("Select current service")),
		("firstservice", _("Select first service in bouquet")),
		("lastepgservice", _("Select last browsed service")),
	]

	possibleAlignmentChoices = [
		(str(RT_HALIGN_LEFT | RT_VALIGN_CENTER), _("Left")),
		(str(RT_HALIGN_CENTER | RT_VALIGN_CENTER), _("Centered")),
		(str(RT_HALIGN_RIGHT | RT_VALIGN_CENTER), _("Right")),
		(str(RT_HALIGN_LEFT | RT_VALIGN_CENTER | RT_WRAP), _("Left, wrapped")),
		(str(RT_HALIGN_CENTER | RT_VALIGN_CENTER | RT_WRAP), _("Centered, wrapped")),
		(str(RT_HALIGN_RIGHT | RT_VALIGN_CENTER | RT_WRAP), _("Right, wrapped")),
	]

	# infobar

	config.epgselection.infobar = ConfigSubsection()

	config.epgselection.infobar.browse_mode = ConfigSelection(default="currentservice", choices=singleBrowseModeChoices)

	config.epgselection.infobar.type_mode = ConfigSelection(default="text", choices=[
		("text", _("Text")),
		("graphics", _("Multi EPG")),
		("single", _("Single EPG")),
	])

	if BoxInfo.getItem("NumVideoDecoders", 1) > 1:
		config.epgselection.infobar.preview_mode = ConfigSelection(default="1", choices=[
			("0", _("Disabled")),
			("1", _("Full screen")),
			("2", _("PiP")),
		])
	else:
		config.epgselection.infobar.preview_mode = ConfigSelection(default="1", choices=[
			("0", _("Disabled")),
			("1", _("Full screen")),
		])

	# 0 uses the item height or row count of the skin.
	choices = [(0, _("Use skin default"))] + [(i, _("%d") % i) for i in range(1, 5)]
	config.epgselection.infobar.itemsperpage = ConfigSelection(default=2, choices=choices)

	config.epgselection.infobar.roundto = ConfigSelection(default="15", choices=[
		("15", _("%d minutes") % 15),
		("30", _("%d minutes") % 30),
		("60", _("%d minutes") % 60),
	])

	# How many minutes of past EPG to show before "now".
	config.epgselection.infobar.histminutes = ConfigSelection(default="0", choices=[
		(str(x), _("%d minutes") % x) for x in range(0, 121, 15)
	])

	# Persisted start position for "previous time" navigation.
	config.epgselection.infobar.prevtime = ConfigClock(default=time())

	config.epgselection.infobar.prevtimeperiod = ConfigSelection(default="180", choices=[
		(str(x), _("%d minutes") % x) for x in (60, 90, 120, 150, 180, 210, 240, 270, 300)
	])

	# The old keys infobar_primetimehour/mins are migrated to this clock (default 20:15).
	config.epgselection.infobar.primetime = ConfigClock(default=mktime((2000, 1, 1, 20, 15, 0, 0, 0, -1)))

	config.epgselection.infobar.servicetitle_mode = ConfigSelection(default="picon+servicename", choices=serviceTitleChoices)

	config.epgselection.infobar.servfs = ConfigSelectionNumber(default=0, stepwidth=1, min=-8, max=10, wraparound=True)
	config.epgselection.infobar.eventfs = ConfigSelectionNumber(default=0, stepwidth=1, min=-8, max=10, wraparound=True)
	config.epgselection.infobar.timelinefs = ConfigSelectionNumber(default=0, stepwidth=1, min=-8, max=10, wraparound=True)
	config.epgselection.infobar.timeline24h = ConfigYesNo(default=True)
	config.epgselection.infobar.servicewidth = ConfigSelectionNumber(default=250, stepwidth=1, min=70, max=500, wraparound=True)
	config.epgselection.infobar.piconwidth = ConfigSelectionNumber(default=100, stepwidth=1, min=50, max=500, wraparound=True)
	config.epgselection.infobar.infowidth = ConfigSelectionNumber(default=25, stepwidth=25, min=0, max=150, wraparound=True)

	config.epgselection.infobar.btn_ok = ConfigSelection(choices=okActions, default="zap")
	config.epgselection.infobar.btn_oklong = ConfigSelection(choices=okActions, default="zapExit")
	config.epgselection.infobar.btn_epg = ConfigSelection(choices=infoActions, default="openSingleEPG")
	config.epgselection.infobar.btn_epglong = ConfigSelection(choices=infoActions, default="")
	config.epgselection.infobar.btn_info = ConfigSelection(choices=infoActions, default="openEventView")
	config.epgselection.infobar.btn_infolong = ConfigSelection(choices=infoActions, default="openSingleEPG")
	config.epgselection.infobar.btn_red = ConfigSelection(choices=epgActions, default="openTMDb" if tmdb else "openIMDb")
	config.epgselection.infobar.btn_redlong = ConfigSelection(choices=epgActions, default="sortEPG")
	config.epgselection.infobar.btn_green = ConfigSelection(choices=epgActions, default="addEditTimer")
	config.epgselection.infobar.btn_greenlong = ConfigSelection(choices=epgActions, default="openTimerList")
	config.epgselection.infobar.btn_yellow = ConfigSelection(choices=epgActions, default="openEPGSearch")
	config.epgselection.infobar.btn_yellowlong = ConfigSelection(choices=epgActions, default="")
	config.epgselection.infobar.btn_blue = ConfigSelection(choices=epgActions, default="addEditAutoTimer")
	config.epgselection.infobar.btn_bluelong = ConfigSelection(choices=epgActions, default="openAutoTimerList")
	config.epgselection.infobar.btn_rec = ConfigSelection(choices=recActions, default="addEditTimerMenu")
	config.epgselection.infobar.btn_reclong = ConfigSelection(choices=recActions, default="addEditZapTimerSilent")

	# single

	config.epgselection.single = ConfigSubsection()
	config.epgselection.single.browse_mode = ConfigSelection(default="currentservice", choices=singleBrowseModeChoices)
	config.epgselection.single.preview_mode = ConfigYesNo(default=True)
	config.epgselection.single.eventfs = ConfigSelectionNumber(default=0, stepwidth=1, min=-8, max=10, wraparound=True)
	# 0 uses the item height or row count of the skin.
	choices = [(0, _("Use skin default"))] + [(i, _("%d") % i) for i in range(1, 41)]
	config.epgselection.single.itemsperpage = ConfigSelection(default=16, choices=choices)
	config.epgselection.single.btn_ok = ConfigSelection(choices=okActions, default="zap")
	config.epgselection.single.btn_oklong = ConfigSelection(choices=okActions, default="zapExit")
	config.epgselection.single.btn_epg = ConfigSelection(choices=infoActions, default="openSingleEPG")
	config.epgselection.single.btn_epglong = ConfigSelection(choices=infoActions, default="")
	config.epgselection.single.btn_info = ConfigSelection(choices=infoActions, default="openEventView")
	config.epgselection.single.btn_infolong = ConfigSelection(choices=infoActions, default="openSingleEPG")
	config.epgselection.single.btn_red = ConfigSelection(choices=epgActions, default="openTMDb" if tmdb else "openIMDb")
	config.epgselection.single.btn_redlong = ConfigSelection(choices=epgActions, default="sortEPG")
	config.epgselection.single.btn_green = ConfigSelection(choices=epgActions, default="addEditTimer")
	config.epgselection.single.btn_greenlong = ConfigSelection(choices=epgActions, default="openTimerList")
	config.epgselection.single.btn_yellow = ConfigSelection(choices=epgActions, default="openEPGSearch")
	config.epgselection.single.btn_yellowlong = ConfigSelection(choices=epgActions, default="")
	config.epgselection.single.btn_blue = ConfigSelection(choices=epgActions, default="addEditAutoTimer")
	config.epgselection.single.btn_bluelong = ConfigSelection(choices=epgActions, default="openAutoTimerList")
	config.epgselection.single.btn_rec = ConfigSelection(choices=recActions, default="addEditTimerMenu")
	config.epgselection.single.btn_reclong = ConfigSelection(choices=recActions, default="addEditZapTimerSilent")

	# multi

	config.epgselection.multi = ConfigSubsection()
	config.epgselection.multi.showbouquet = ConfigYesNo(default=False)
	config.epgselection.multi.browse_mode = ConfigSelection(default="currentservice", choices=multiBrowseModeChoices)
	config.epgselection.multi.preview_mode = ConfigYesNo(default=True)
	config.epgselection.multi.eventfs = ConfigSelectionNumber(default=0, stepwidth=1, min=-8, max=10, wraparound=True)
	# 0 uses the item height or row count of the skin.
	choices = [(0, _("Use skin default"))] + [(i, _("%d") % i) for i in range(8, 41)]
	config.epgselection.multi.itemsperpage = ConfigSelection(default=16, choices=choices)
	# config.epgselection.multi.servicewidth = ConfigSelectionNumber(default=7, stepwidth=1, min=5, max=20, wraparound=True)  # Not implemented yet.
	config.epgselection.multi.btn_ok = ConfigSelection(choices=okActions, default="zap")
	config.epgselection.multi.btn_oklong = ConfigSelection(choices=okActions, default="zapExit")
	config.epgselection.multi.btn_epg = ConfigSelection(choices=infoActions, default="openSingleEPG")
	config.epgselection.multi.btn_epglong = ConfigSelection(choices=infoActions, default="")
	config.epgselection.multi.btn_info = ConfigSelection(choices=infoActions, default="openEventView")
	config.epgselection.multi.btn_infolong = ConfigSelection(choices=infoActions, default="openSingleEPG")
	config.epgselection.multi.btn_red = ConfigSelection(choices=epgActions, default="openTMDb" if tmdb else "openIMDb")
	config.epgselection.multi.btn_redlong = ConfigSelection(choices=epgActions, default="sortEPG")
	config.epgselection.multi.btn_green = ConfigSelection(choices=epgActions, default="addEditTimer")
	config.epgselection.multi.btn_greenlong = ConfigSelection(choices=epgActions, default="openTimerList")
	config.epgselection.multi.btn_yellow = ConfigSelection(choices=epgActions, default="openEPGSearch")
	config.epgselection.multi.btn_yellowlong = ConfigSelection(choices=epgActions, default="")
	config.epgselection.multi.btn_blue = ConfigSelection(choices=epgActions, default="addEditAutoTimer")
	config.epgselection.multi.btn_bluelong = ConfigSelection(choices=epgActions, default="openAutoTimerList")
	config.epgselection.multi.btn_rec = ConfigSelection(choices=recActions, default="addEditTimerMenu")
	config.epgselection.multi.btn_reclong = ConfigSelection(choices=recActions, default="addEditZapTimerSilent")

	# grid (formerly "graph")

	config.epgselection.grid = ConfigSubsection()
	config.epgselection.grid.showbouquet = ConfigYesNo(default=False)
	config.epgselection.grid.browse_mode = ConfigSelection(default="currentservice", choices=multiBrowseModeChoices)
	config.epgselection.grid.preview_mode = ConfigYesNo(default=True)
	config.epgselection.grid.type_mode = ConfigSelection(choices=[
		("graphics", _("Graphics")),
		("text", _("Text")),
	], default="text")
	# config.epgselection.grid.highlight_current_events = ConfigYesNo(default=True)  # Not implemented yet.
	config.epgselection.grid.roundto = ConfigSelection(default="15", choices=[
		("15", _("%d minutes") % 15),
		("30", _("%d minutes") % 30),
		("60", _("%d minutes") % 60),
	])

	# How many minutes of past EPG to show before "now".
	config.epgselection.grid.histminutes = ConfigSelection(default="0", choices=[
		(str(x), _("%d minutes") % x) for x in range(0, 121, 15)
	])

	# Persisted start position for "previous time" navigation.
	config.epgselection.grid.prevtime = ConfigClock(default=time())

	config.epgselection.grid.prevtimeperiod = ConfigSelection(default="180", choices=[
		(str(x), _("%d minutes") % x) for x in (60, 90, 120, 150, 180, 210, 240, 270, 300)
	])

	# The old keys graph_primetimehour/mins are migrated to this clock (default 20:15).
	config.epgselection.grid.primetime = ConfigClock(default=mktime((2000, 1, 1, 20, 15, 0, 0, 0, -1)))

	# Start position when opening the grid EPG.
	config.epgselection.grid.startmode = ConfigSelection(default="standard", choices=[
		("standard", _("Standard")),
		("primetime", _("Prime time")),
		("channel1", _("Channel 1")),
		("channel1+primetime", _("Channel 1 with prime time")),
	])

	config.epgselection.grid.servicetitle_mode = ConfigSelection(default="picon+servicename", choices=serviceTitleChoices)

	config.epgselection.grid.servicename_alignment = ConfigSelection(default=possibleAlignmentChoices[0][0], choices=possibleAlignmentChoices)
	# config.epgselection.grid.servicenumber_alignment = ConfigSelection(default=possibleAlignmentChoices[0][0], choices=possibleAlignmentChoices)  # Not implemented yet.
	config.epgselection.grid.event_alignment = ConfigSelection(default=possibleAlignmentChoices[0][0], choices=possibleAlignmentChoices)
	# config.epgselection.grid.timelinedate_alignment = ConfigSelection(default=possibleAlignmentChoices[0][0], choices=possibleAlignmentChoices)  # Not implemented yet.

	config.epgselection.grid.servfs = ConfigSelectionNumber(default=0, stepwidth=1, min=-8, max=10, wraparound=True)
	config.epgselection.grid.eventfs = ConfigSelectionNumber(default=0, stepwidth=1, min=-8, max=10, wraparound=True)
	config.epgselection.grid.timelinefs = ConfigSelectionNumber(default=0, stepwidth=1, min=-8, max=10, wraparound=True)
	config.epgselection.grid.timeline24h = ConfigYesNo(default=True)

	# 0 uses the item height or row count of the skin.
	choices = [(0, _("Use skin default"))] + [(i, _("%d") % i) for i in range(3, 21)]
	config.epgselection.grid.itemsperpage = ConfigSelection(default=8, choices=choices)

	config.epgselection.grid.pig = ConfigYesNo(default=False)
	config.epgselection.grid.heightswitch = NoSave(ConfigYesNo(default=False))
	config.epgselection.grid.servicewidth = ConfigSelectionNumber(default=250, stepwidth=1, min=70, max=500, wraparound=True)
	config.epgselection.grid.piconwidth = ConfigSelectionNumber(default=100, stepwidth=1, min=50, max=500, wraparound=True)
	config.epgselection.grid.infowidth = ConfigSelectionNumber(default=25, stepwidth=25, min=0, max=150, wraparound=True)
	config.epgselection.grid.rec_icon_height = ConfigSelection(choices=[
		("bottom", _("Bottom")),
		("top", _("Top")),
		("middle", _("Middle")),
		("hide", _("Hide")),
	], default="bottom")

	# Not implemented yet.
	# config.epgselection.grid.number_buttons_mode = ConfigSelection(choices=[
	# 	("paging", _("Standard")),
	# 	("service", _("Enter service number")),
	# ], default="paging")

	config.epgselection.grid.btn_ok = ConfigSelection(choices=okActions, default="zap")
	config.epgselection.grid.btn_oklong = ConfigSelection(choices=okActions, default="zapExit")
	config.epgselection.grid.btn_epg = ConfigSelection(choices=infoActions, default="openSingleEPG")
	config.epgselection.grid.btn_epglong = ConfigSelection(choices=infoActions, default="")
	config.epgselection.grid.btn_info = ConfigSelection(choices=infoActions, default="openEventView")
	config.epgselection.grid.btn_infolong = ConfigSelection(choices=infoActions, default="openSingleEPG")
	config.epgselection.grid.btn_rec = ConfigSelection(choices=recActions, default="addEditTimerMenu")
	config.epgselection.grid.btn_reclong = ConfigSelection(choices=recActions, default="addEditZapTimerSilent")
	# The old graph_channelbtn key is split into one key per direction.
	config.epgselection.grid.btn_channelup = ConfigSelection(choices=channelUpActions, default="forward24Hours")
	config.epgselection.grid.btn_channeldown = ConfigSelection(choices=channelDownActions, default="back24Hours")
	config.epgselection.grid.btn_red = ConfigSelection(choices=epgActions, default="openTMDb" if tmdb else "openIMDb")
	config.epgselection.grid.btn_redlong = ConfigSelection(choices=epgActions, default="sortEPG")
	config.epgselection.grid.btn_green = ConfigSelection(choices=epgActions, default="addEditTimer")
	config.epgselection.grid.btn_greenlong = ConfigSelection(choices=epgActions, default="openTimerList")
	config.epgselection.grid.btn_yellow = ConfigSelection(choices=epgActions, default="openEPGSearch")
	config.epgselection.grid.btn_yellowlong = ConfigSelection(choices=epgActions, default="")
	config.epgselection.grid.btn_blue = ConfigSelection(choices=epgActions, default="addEditAutoTimer")
	config.epgselection.grid.btn_bluelong = ConfigSelection(choices=epgActions, default="openAutoTimerList")

	# vertical

	config.epgselection.vertical = ConfigSubsection()

	# The old keys vertical_primetimehour/mins are migrated to this clock (default 20:15).
	config.epgselection.vertical.primetime = ConfigClock(default=mktime((2000, 1, 1, 20, 15, 0, 0, 0, -1)))
	config.epgselection.vertical.prevtime = ConfigClock(default=time())
	config.epgselection.vertical.itemsperpage = ConfigSelectionNumber(default=6, stepwidth=1, min=3, max=12, wraparound=True)
	config.epgselection.vertical.eventfs = ConfigSelectionNumber(default=0, stepwidth=1, min=-10, max=10, wraparound=True)
	config.epgselection.vertical.preview_mode = ConfigYesNo(default=True)
	config.epgselection.vertical.pig = ConfigYesNo(default=False)
	config.epgselection.vertical.eventmarker = ConfigYesNo(default=False)
	config.epgselection.vertical.showlines = ConfigYesNo(default=True)
	config.epgselection.vertical.startmode = ConfigSelection(default="standard", choices=[
		("standard", _("Standard")),
		("primetime", _("Prime time")),
		("channel1", _("Channel 1")),
		("channel1+primetime", _("Channel 1 with prime time")),
	])
	config.epgselection.vertical.channelbtn = ConfigSelection(default="page", choices=[
		("page", _("Previous/Next page")),
		("scroll", _("All up/down")),
		("24", _("-24h/+24 Hours")),
	])
	config.epgselection.vertical.channelbtn_invert = ConfigYesNo(default=False)
	config.epgselection.vertical.updownbtn = ConfigYesNo(default=True)
	# The old keys used the labels as values, see verticalOkMap.
	config.epgselection.vertical.btn_ok = ConfigSelection(choices=okActions, default="openEventView")
	config.epgselection.vertical.btn_oklong = ConfigSelection(choices=okActions, default="zapExit")
	config.epgselection.vertical.btn_info = ConfigSelection(choices=infoActions, default="openEventView")
	config.epgselection.vertical.btn_infolong = ConfigSelection(choices=infoActions, default="openSingleEPG")
	# The old values are migrated via colorMap.
	config.epgselection.vertical.btn_red = ConfigSelection(choices=verticalActions, default="openTMDb" if tmdb else "openIMDb")
	config.epgselection.vertical.btn_redlong = ConfigSelection(choices=verticalActions, default="sortEPG")
	config.epgselection.vertical.btn_green = ConfigSelection(choices=verticalActions, default="addEditTimer")
	config.epgselection.vertical.btn_greenlong = ConfigSelection(choices=verticalActions, default="openTimerList")
	config.epgselection.vertical.btn_yellow = ConfigSelection(choices=verticalActions, default="openEPGSearch")
	config.epgselection.vertical.btn_yellowlong = ConfigSelection(choices=verticalActions, default="")
	config.epgselection.vertical.btn_blue = ConfigSelection(choices=verticalActions, default="addEditAutoTimer")
	config.epgselection.vertical.btn_bluelong = ConfigSelection(choices=verticalActions, default="openAutoTimerList")

	# Old keys that are still read by plugins (EPGSearch) and skin renderers (MetrixHD, AX-Blue
	# and Multibox PrimeTime). They follow the new settings and are not saved.
	def addLegacyKey(name, element, source, convert=None):
		def sourceChanged(configElement):
			getattr(config.epgselection, name).value = convert(configElement.value) if convert else configElement.value

		setattr(config.epgselection, name, NoSave(element))
		element.saved_value = None  # Drop the old stored value from the settings.
		source.addNotifier(sourceChanged)

	addLegacyKey("graph_primetimehour", ConfigSelectionNumber(default=20, stepwidth=1, min=0, max=23, wraparound=True), config.epgselection.grid.primetime, lambda value: value[0])
	addLegacyKey("graph_primetimemins", ConfigSelectionNumber(default=15, stepwidth=1, min=0, max=59, wraparound=True), config.epgselection.grid.primetime, lambda value: value[1])
	addLegacyKey("enhanced_eventfs", ConfigSelectionNumber(default=0, stepwidth=1, min=-8, max=10, wraparound=True), config.epgselection.single.eventfs)
	addLegacyKey("enhanced_itemsperpage", ConfigSelectionNumber(default=16, stepwidth=1, min=0, max=40, wraparound=True), config.epgselection.single.itemsperpage)

	# Migrate the old flat keys to the subsections.
	upgradeConfig()


class EPGSettings:
	"""Unified per-type accessor for all EPG button and display config settings.

	Instantiate once per EPG screen with the current EPG type constant, then
	read button values by name without knowing which subsection holds them.

	Example::

		self._cfg = EPGSettings(self.type)
		if self._cfg.ok == "zapExit":
			self.zap()
		self._dispatchEpgAction(self._cfg.btn("red"))
		self._dispatchEpgAction(self._cfg.btn("blue", long=True))
	"""

	def __init__(self, epg_type):
		# Imported here to keep Components.EpgList out of the startup imports (UsageConfig).
		from Components.EpgList import EPG_TYPE_ENHANCED, EPG_TYPE_GRAPH, EPG_TYPE_INFOBAR, EPG_TYPE_INFOBARGRAPH, EPG_TYPE_MULTI, EPG_TYPE_SINGLE, EPG_TYPE_VERTICAL
		sections = {
			EPG_TYPE_GRAPH: "grid",
			EPG_TYPE_INFOBARGRAPH: "infobar",
			EPG_TYPE_INFOBAR: "infobar",
			EPG_TYPE_ENHANCED: "single",
			EPG_TYPE_MULTI: "multi",
			EPG_TYPE_VERTICAL: "vertical",
			EPG_TYPE_SINGLE: "single",
		}
		section = sections.get(epg_type)
		self._section = getattr(config.epgselection, section) if section else None
		self._type = epg_type

	@property
	def section(self):
		"""The raw config subsection for this EPG type (may be None for similar/unknown)."""
		return self._section

	def _get(self, attr, fallback=""):
		if self._section is None:
			return fallback
		cfg = getattr(self._section, attr, None)
		return cfg.value if cfg is not None else fallback

	@property
	def ok(self):
		"""Action for the OK button (short press). Default: "zap"."""
		return self._get("btn_ok", "zap")

	@property
	def oklong(self):
		"""Action for the OK button (long press). Default: "zapExit"."""
		return self._get("btn_oklong", "zapExit")

	@property
	def info(self):
		"""Action for the INFO button (short press). Default: "openEventView"."""
		return self._get("btn_info", "openEventView")

	@property
	def infolong(self):
		"""Action for the INFO button (long press). Default: "openSingleEPG"."""
		return self._get("btn_infolong", "openSingleEPG")

	@property
	def epg(self):
		"""Action for the EPG button (short press). Default: "openSingleEPG"."""
		return self._get("btn_epg", "openSingleEPG")

	@property
	def epglong(self):
		"""Action for the EPG button (long press). Default: ""."""
		return self._get("btn_epglong", "")

	@property
	def rec(self):
		"""Action for the record button (short press). Default: "addEditTimerMenu"."""
		return self._get("btn_rec", "addEditTimerMenu")

	@property
	def reclong(self):
		"""Action for the record button (long press). Default: "addEditZapTimerSilent"."""
		return self._get("btn_reclong", "addEditZapTimerSilent")

	def btn(self, color, long=False):
		"""Return the configured action for a color button.

		Args:
			color: "red", "green", "yellow", or "blue"
			long:  True for long-press variant

		Returns:
			action ID string (e.g. "openIMDb") or "" if not configured / unknown type.
		"""
		suffix = "long" if long else ""
		if long:
			defaults = {
				"red": "sortEPG",
				"green": "openTimerList",
				"blue": "openAutoTimerList",
			}
		else:
			defaults = {
				"red": "openIMDb",
				"green": "addEditTimer",
				"yellow": "openEPGSearch",
				"blue": "addEditAutoTimer",
			}
		return self._get(f"btn_{color}{suffix}", defaults.get(color, ""))

	@property
	def channelup(self):
		"""Action for channel-up button (grid/infobargraph only). Default: "prevPage"."""
		return self._get("btn_channelup", "prevPage")

	@property
	def channeldown(self):
		"""Action for channel-down button (grid/infobargraph only). Default: "nextPage"."""
		return self._get("btn_channeldown", "nextPage")

	@property
	def preview_mode(self):
		"""Preview mode value for this EPG type."""
		return self._get("preview_mode", "0")

	@property
	def primetime(self):
		"""Primetime as (hour, minute) from ConfigClock. Returns the default (20, 15) as fallback."""
		cfg = getattr(self._section, "primetime", None) if self._section is not None else None
		v = cfg.value if cfg is not None else None
		return (v[0], v[1]) if v else (20, 15)

	@property
	def itemsperpage(self):
		"""Items per page (0 = skin default). Returns integer."""
		return self._get("itemsperpage", 0)
