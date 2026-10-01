from time import mktime, time

from enigma import RT_HALIGN_CENTER, RT_HALIGN_LEFT, RT_HALIGN_RIGHT, RT_VALIGN_CENTER, RT_WRAP

from Components.config import config, ConfigClock, ConfigNumber, ConfigSelection, ConfigSelectionNumber, ConfigSubsection, ConfigYesNo, NoSave
from Components.EpgList import EPG_TYPE_ENHANCED, EPG_TYPE_GRAPH, EPG_TYPE_INFOBAR, EPG_TYPE_INFOBARGRAPH, EPG_TYPE_MULTI, EPG_TYPE_SINGLE, EPG_TYPE_VERTICAL
from Components.SystemInfo import BoxInfo
from Tools.Directories import isPluginInstalled

# Action choice lists.
# TODO Step 2: Move these to Screens/EpgSelectionBase.py and import from there.
# Each entry is (value, label) or (value, label, helptext).

epgActions = [
	("", _("Do nothing")),
	("openIMDb", _("IMDb Search")),
	("openTMDb", _("TMDb Search")),
	("sortEPG", _("Sort")),
	("addEditTimer", _("Add Timer")),
	("openTimerList", _("Show Timer List")),
	("openEPGSearch", _("EPG Search")),
	("addEditAutoTimer", _("Add AutoTimer")),
	("openAutoTimerList", _("AutoTimer List")),
	("forward24Hours", _("+24 hours")),
	("back24Hours", _("-24 hours")),
	("openEventView", _("Event Info")),
	("openSingleEPG", _("Single EPG")),
	("showMovies", _("Recordings")),
]

okActions = [
	("zap", _("Zap")),
	("zapExit", _("Zap + Exit")),
	("openEventView", _("Event Info")),
]

recActions = [
	("addEditTimerMenu", _("Timer Menu")),
	("addEditTimer", _("Add Timer")),
	("addEditTimerSilent", _("Create Timer")),
	("addEditZapTimerSilent", _("Create Zap Timer")),
	("addEditAutoTimer", _("Add AutoTimer")),
]

infoActions = [
	("", _("Do nothing")),
	("openEventView", _("Event Info")),
	("openSingleEPG", _("Single EPG")),
	("switchToSingleEPG", _("Switch to Single EPG")),
	("switchToGridEPG", _("Switch to Grid EPG")),
	("switchToMultiEPG", _("Switch to Multi EPG")),
]

channelUpActions = [
	("forward24Hours", _("+24 hours")),
	("prevPage", _("Page up")),
]

channelDownActions = [
	("back24Hours", _("-24 hours")),
	("nextPage", _("Page down")),
]


def upgradeConfig():
	if config.epgselection.migrationVersion.value < 1:
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

		print("[EpgConfig] Upgrading EPG settings from flat ATV keys to subsection structure")

		okMap = {"Zap": "zap", "Zap + Exit": "zapExit"}
		infoMap = {"Channel Info": "openEventView", "Single EPG": "openSingleEPG"}
		# Old ATV vertical ok had one more choice "Channel Info" (same as "openEventView")
		verticalOkMap = {"Channel Info": "openEventView", "Zap": "zap", "Zap + Exit": "zapExit"}
		# Old ATV color button string values → new epgActions IDs.
		# Note: "prevpage"/"nextpage"/"prevbouquet"/"nextbouquet"/"bouquetlist"/"gotodatetime"
		# have no equivalent in the new epgActions list → will fall back to configured default.
		colorMap = {
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
		# Old ATV servicetitle_mode choices where ordering differed from new schema.
		titleModeMap = {
			"servicenumber+picon": "picon+servicenumber",
			"servicenumber+picon+servicename": "picon+servicenumber+servicename",
		}
		# graph_channelbtn ("24"/"page"/"bouquet") → split into btn_channelup / btn_channeldown.
		# "bouquet" has no equivalent in channelUpActions/channelDownActions → falls to default.
		channelUpMap = {"24": "forward24Hours", "page": "prevPage"}
		channelDownMap = {"24": "back24Hours", "page": "nextPage"}

		# infobar
		upgrade(config.epgselection.infobar.type_mode, "epgselection.infobar_type_mode")
		upgrade(config.epgselection.infobar.preview_mode, "epgselection.infobar_preview_mode")
		upgrade(config.epgselection.infobar.btn_ok, "epgselection.infobar_ok", okMap)
		upgrade(config.epgselection.infobar.btn_oklong, "epgselection.infobar_oklong", okMap)
		upgrade(config.epgselection.infobar.itemsperpage, "epgselection.infobar_itemsperpage")
		upgrade(config.epgselection.infobar.roundto, "epgselection.infobar_roundto")
		upgrade(config.epgselection.infobar.histminutes, "epgselection.infobar_histminutes")
		upgrade(config.epgselection.infobar.prevtimeperiod, "epgselection.infobar_prevtimeperiod")
		# Old key was an integer hour (e.g. "20"); ConfigClock needs "HH:MM" format.
		upgrade(config.epgselection.infobar.primetime, "epgselection.infobar_primetimehour", mapper=lambda v: f"{v}:{getOldValue('epgselection.infobar_primetimemins') or 15}")
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
		# graph_channel1 was True/False; browse_mode is a string choice
		upgrade(config.epgselection.grid.browse_mode, "epgselection.graph_channel1", {"True": "firstservice", "False": "currentservice"})
		upgrade(config.epgselection.grid.preview_mode, "epgselection.graph_preview_mode")
		upgrade(config.epgselection.grid.type_mode, "epgselection.graph_type_mode")
		upgrade(config.epgselection.grid.highlight_current_events, "epgselection.graph_highlight_current_events")
		upgrade(config.epgselection.grid.btn_ok, "epgselection.graph_ok", okMap)
		upgrade(config.epgselection.grid.btn_oklong, "epgselection.graph_oklong", okMap)
		upgrade(config.epgselection.grid.btn_info, "epgselection.graph_info", infoMap)
		upgrade(config.epgselection.grid.btn_infolong, "epgselection.graph_infolong", infoMap)
		upgrade(config.epgselection.grid.roundto, "epgselection.graph_roundto")
		upgrade(config.epgselection.grid.histminutes, "epgselection.graph_histminutes")
		upgrade(config.epgselection.grid.prevtimeperiod, "epgselection.graph_prevtimeperiod")
		upgrade(config.epgselection.grid.primetime, "epgselection.graph_primetimehour", mapper=lambda v: f"{v}:{getOldValue('epgselection.graph_primetimemins') or 15}")
		upgrade(config.epgselection.grid.servicetitle_mode, "epgselection.graph_servicetitle_mode", titleModeMap)
		upgrade(config.epgselection.grid.servicename_alignment, "epgselection.graph_servicename_alignment")
		upgrade(config.epgselection.grid.event_alignment, "epgselection.graph_event_alignment")
		# servicenumber_alignment and timelinedate_alignment are new (from OpenViX), no old key
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
		upgrade(config.epgselection.vertical.primetime, "epgselection.vertical_primetimehour", mapper=lambda v: f"{v}:{getOldValue('epgselection.vertical_primetimemins') or 15}")
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

	# OpenViX uses 8 choices (full set). ATV old had 5 choices with slightly different labels.
	# The full set is used here; migration maps old ordering variants to new keys.
	serviceTitleChoices = [
		("servicename", _("Service Name")),
		("picon", _("Picon")),
		("picon+servicename", _("Picon and Service Name")),
		("servicenumber+picon", _("Service Number and Picon")),
		("picon+servicenumber", _("Picon and Service Number")),
		("servicenumber+servicename", _("Service Number and Service Name")),
		("picon+servicenumber+servicename", _("Picon, Service Number and Service Name")),
		("servicenumber+picon+servicename", _("Service Number, Picon and Service Name")),
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
		(str(RT_HALIGN_LEFT | RT_VALIGN_CENTER), _("left")),
		(str(RT_HALIGN_CENTER | RT_VALIGN_CENTER), _("centered")),
		(str(RT_HALIGN_RIGHT | RT_VALIGN_CENTER), _("right")),
		(str(RT_HALIGN_LEFT | RT_VALIGN_CENTER | RT_WRAP), _("left, wrapped")),
		(str(RT_HALIGN_CENTER | RT_VALIGN_CENTER | RT_WRAP), _("centered, wrapped")),
		(str(RT_HALIGN_RIGHT | RT_VALIGN_CENTER | RT_WRAP), _("right, wrapped")),
	]

	# ─── infobar ───────────────────────────────────────────────────────────────

	config.epgselection.infobar = ConfigSubsection()

	# ATV old had no browse_mode for infobar – new from OpenViX.
	config.epgselection.infobar.browse_mode = ConfigSelection(default="currentservice", choices=singleBrowseModeChoices)

	# ATV old labels: "Text" / "Multi EPG" / "Single EPG". OpenViX labels differ slightly.
	# ATV old default: "text". OpenViX default: "graphics". Using OpenViX default.
	config.epgselection.infobar.type_mode = ConfigSelection(default="graphics", choices=[
		("text", _("Text Grid EPG")),
		("graphics", _("Graphics Grid EPG")),
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

	# ATV old: ConfigSelectionNumber(default=2, min=1, max=4) – no skin-default option.
	choices = [(0, _("Use skin default"))] + [(i, _("%d") % i) for i in range(1, 5)]
	config.epgselection.infobar.itemsperpage = ConfigSelection(default=2, choices=choices)

	config.epgselection.infobar.roundto = ConfigSelection(default="15", choices=[
		("15", _("%d minutes") % 15),
		("30", _("%d minutes") % 30),
		("60", _("%d minutes") % 60),
	])

	# ATV-specific: how many minutes of past EPG to show before "now".
	config.epgselection.infobar.histminutes = ConfigSelection(default="0", choices=[
		(str(x), _("%d minutes") % x) for x in range(0, 121, 15)
	])

	# ATV-specific: persisted start position for "previous time" navigation.
	config.epgselection.infobar.prevtime = ConfigClock(default=time())

	config.epgselection.infobar.prevtimeperiod = ConfigSelection(default="180", choices=[
		(str(x), _("%d minutes") % x) for x in (60, 90, 120, 150, 180, 210, 240, 270, 300)
	])

	# ATV old stored primetime as two ints (infobar_primetimehour + infobar_primetimemins).
	# Now unified to ConfigClock. Migration converts old hour value by appending ":00".
	# OpenViX default: (20, 0). ATV old: hour=20, mins=15. Using OpenViX default.
	config.epgselection.infobar.primetime = ConfigClock(default=mktime((2000, 1, 1, 20, 15, 0, 0, 0, -1)))

	# ATV old default: "picon+servicename". OpenViX default: "servicename".
	# Keeping ATV default for a better visual experience on existing installs.
	config.epgselection.infobar.servicetitle_mode = ConfigSelection(default="picon+servicename", choices=serviceTitleChoices)

	config.epgselection.infobar.servfs = ConfigSelectionNumber(default=0, stepwidth=1, min=-8, max=10, wraparound=True)
	config.epgselection.infobar.eventfs = ConfigSelectionNumber(default=0, stepwidth=1, min=-8, max=10, wraparound=True)
	config.epgselection.infobar.timelinefs = ConfigSelectionNumber(default=0, stepwidth=1, min=-8, max=10, wraparound=True)
	config.epgselection.infobar.timeline24h = ConfigYesNo(default=True)
	config.epgselection.infobar.servicewidth = ConfigSelectionNumber(default=250, stepwidth=1, min=70, max=500, wraparound=True)
	config.epgselection.infobar.piconwidth = ConfigSelectionNumber(default=100, stepwidth=1, min=50, max=500, wraparound=True)
	# ATV old infowidth default: 25. OpenViX default: 50. Using OpenViX default.
	config.epgselection.infobar.infowidth = ConfigSelectionNumber(default=50, stepwidth=25, min=0, max=150, wraparound=True)

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

	# ─── single ────────────────────────────────────────────────────────────────

	config.epgselection.single = ConfigSubsection()
	config.epgselection.single.browse_mode = ConfigSelection(default="lastepgservice", choices=singleBrowseModeChoices)
	config.epgselection.single.preview_mode = ConfigYesNo(default=True)
	config.epgselection.single.eventfs = ConfigSelectionNumber(default=0, stepwidth=1, min=-8, max=10, wraparound=True)
	# ATV old: ConfigSelectionNumber(default=16, min=8, max=40) – no skin-default option.
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

	# ─── multi ─────────────────────────────────────────────────────────────────

	config.epgselection.multi = ConfigSubsection()
	config.epgselection.multi.showbouquet = ConfigYesNo(default=False)
	config.epgselection.multi.browse_mode = ConfigSelection(default="currentservice", choices=multiBrowseModeChoices)
	config.epgselection.multi.preview_mode = ConfigYesNo(default=True)
	config.epgselection.multi.eventfs = ConfigSelectionNumber(default=0, stepwidth=1, min=-8, max=10, wraparound=True)
	# ATV old: ConfigSelectionNumber(default=16, min=8, max=40) – no skin-default option.
	choices = [(0, _("Use skin default"))] + [(i, _("%d") % i) for i in range(8, 41)]
	config.epgselection.multi.itemsperpage = ConfigSelection(default=16, choices=choices)
	config.epgselection.multi.servicewidth = ConfigSelectionNumber(default=7, stepwidth=1, min=5, max=20, wraparound=True)
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

	# ─── grid (formerly "graph") ───────────────────────────────────────────────

	config.epgselection.grid = ConfigSubsection()
	config.epgselection.grid.showbouquet = ConfigYesNo(default=False)
	# ATV old had no grid browse_mode (used graph_channel1 True/False instead). New from OpenViX.
	config.epgselection.grid.browse_mode = ConfigSelection(default="currentservice", choices=multiBrowseModeChoices)
	config.epgselection.grid.preview_mode = ConfigYesNo(default=True)
	config.epgselection.grid.type_mode = ConfigSelection(choices=[
		("graphics", _("Graphics")),
		("text", _("Text")),
	], default="graphics")
	config.epgselection.grid.highlight_current_events = ConfigYesNo(default=True)
	config.epgselection.grid.roundto = ConfigSelection(default="15", choices=[
		("15", _("%d minutes") % 15),
		("30", _("%d minutes") % 30),
		("60", _("%d minutes") % 60),
	])

	# ATV-specific: how many minutes of past EPG to show before "now".
	config.epgselection.grid.histminutes = ConfigSelection(default="0", choices=[
		(str(x), _("%d minutes") % x) for x in range(0, 121, 15)
	])

	# ATV-specific: persisted start position for "previous time" navigation.
	config.epgselection.grid.prevtime = ConfigClock(default=time())

	config.epgselection.grid.prevtimeperiod = ConfigSelection(default="180", choices=[
		(str(x), _("%d minutes") % x) for x in (60, 90, 120, 150, 180, 210, 240, 270, 300)
	])

	# ATV old stored primetime as two ints (graph_primetimehour + graph_primetimemins).
	# Now unified to ConfigClock. Migration converts old hour value by appending ":00".
	# OpenViX default: (20, 0). ATV old: hour=20, mins=15. Using OpenViX default.
	config.epgselection.grid.primetime = ConfigClock(default=mktime((2000, 1, 1, 20, 15, 0, 0, 0, -1)))

	# ATV-specific: start position mode when opening grid EPG. OpenViX does not have this.
	config.epgselection.grid.startmode = ConfigSelection(default="standard", choices=[
		("standard", _("Standard")),
		("primetime", _("Prime time")),
		("channel1", _("Channel 1")),
		("channel1+primetime", _("Channel 1 with prime time")),
	])

	# ATV old default: "picon+servicename". OpenViX default: "servicename".
	config.epgselection.grid.servicetitle_mode = ConfigSelection(default="picon+servicename", choices=serviceTitleChoices)

	config.epgselection.grid.servicename_alignment = ConfigSelection(default=possibleAlignmentChoices[0][0], choices=possibleAlignmentChoices)
	# ATV old had no graph_servicenumber_alignment – new from OpenViX, no migration.
	config.epgselection.grid.servicenumber_alignment = ConfigSelection(default=possibleAlignmentChoices[0][0], choices=possibleAlignmentChoices)
	config.epgselection.grid.event_alignment = ConfigSelection(default=possibleAlignmentChoices[0][0], choices=possibleAlignmentChoices)
	# ATV old had no graph_timelinedate_alignment – new from OpenViX, no migration.
	config.epgselection.grid.timelinedate_alignment = ConfigSelection(default=possibleAlignmentChoices[0][0], choices=possibleAlignmentChoices)

	config.epgselection.grid.servfs = ConfigSelectionNumber(default=0, stepwidth=1, min=-8, max=10, wraparound=True)
	config.epgselection.grid.eventfs = ConfigSelectionNumber(default=0, stepwidth=1, min=-8, max=10, wraparound=True)
	config.epgselection.grid.timelinefs = ConfigSelectionNumber(default=0, stepwidth=1, min=-8, max=10, wraparound=True)
	config.epgselection.grid.timeline24h = ConfigYesNo(default=True)

	# ATV old: ConfigSelectionNumber(default=8, min=3, max=20) – no skin-default option.
	choices = [(0, _("Use skin default"))] + [(i, _("%d") % i) for i in range(3, 21)]
	config.epgselection.grid.itemsperpage = ConfigSelection(default=8, choices=choices)

	# ATV old default: False. OpenViX default: True. Using OpenViX default.
	config.epgselection.grid.pig = ConfigYesNo(default=True)
	config.epgselection.grid.heightswitch = NoSave(ConfigYesNo(default=False))
	config.epgselection.grid.servicewidth = ConfigSelectionNumber(default=250, stepwidth=1, min=70, max=500, wraparound=True)
	config.epgselection.grid.piconwidth = ConfigSelectionNumber(default=100, stepwidth=1, min=50, max=500, wraparound=True)
	# ATV old infowidth default: 25. OpenViX default: 50. Using OpenViX default.
	config.epgselection.grid.infowidth = ConfigSelectionNumber(default=50, stepwidth=25, min=0, max=150, wraparound=True)
	config.epgselection.grid.rec_icon_height = ConfigSelection(choices=[
		("bottom", _("bottom")),
		("top", _("top")),
		("middle", _("middle")),
		("hide", _("hide")),
	], default="bottom")

	# ATV old had no number_buttons_mode – new from OpenViX, no migration.
	config.epgselection.grid.number_buttons_mode = ConfigSelection(choices=[
		("paging", _("Standard")),
		("service", _("Enter service number")),
	], default="paging")

	config.epgselection.grid.btn_ok = ConfigSelection(choices=okActions, default="zap")
	config.epgselection.grid.btn_oklong = ConfigSelection(choices=okActions, default="zapExit")
	config.epgselection.grid.btn_epg = ConfigSelection(choices=infoActions, default="openSingleEPG")
	config.epgselection.grid.btn_epglong = ConfigSelection(choices=infoActions, default="")
	config.epgselection.grid.btn_info = ConfigSelection(choices=infoActions, default="openEventView")
	config.epgselection.grid.btn_infolong = ConfigSelection(choices=infoActions, default="openSingleEPG")
	config.epgselection.grid.btn_rec = ConfigSelection(choices=recActions, default="addEditTimerMenu")
	config.epgselection.grid.btn_reclong = ConfigSelection(choices=recActions, default="addEditZapTimerSilent")
	# ATV old: single graph_channelbtn key → now split into direction-specific keys.
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

	# ─── vertical (ATV-specific, full section) ─────────────────────────────────
	# OpenViX only defines vertical.primetime and vertical.prevtime.
	# enigma2-jb supports a full vertical EPG; all settings are ATV-specific.

	config.epgselection.vertical = ConfigSubsection()

	# ATV old stored as two ints (vertical_primetimehour + vertical_primetimemins).
	# Migration converts old hour value by appending ":00".
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
	# Old ATV choices used string labels ("Channel Info"/"Zap"/"Zap + Exit") as values.
	# Migration maps these to the new action IDs via verticalOkMap.
	config.epgselection.vertical.btn_ok = ConfigSelection(choices=okActions, default="openEventView")
	config.epgselection.vertical.btn_oklong = ConfigSelection(choices=okActions, default="zapExit")
	config.epgselection.vertical.btn_info = ConfigSelection(choices=infoActions, default="openEventView")
	config.epgselection.vertical.btn_infolong = ConfigSelection(choices=infoActions, default="openSingleEPG")
	# Old ATV vertical had graph_red/green/yellow/blue with old-style string values.
	# Migration maps via colorMap; unmapped values (prevpage etc.) fall to default.
	config.epgselection.vertical.btn_red = ConfigSelection(choices=epgActions, default="openTMDb" if tmdb else "openIMDb")
	config.epgselection.vertical.btn_green = ConfigSelection(choices=epgActions, default="addEditTimer")
	config.epgselection.vertical.btn_yellow = ConfigSelection(choices=epgActions, default="openEPGSearch")
	config.epgselection.vertical.btn_blue = ConfigSelection(choices=epgActions, default="addEditAutoTimer")

	# Run migration from flat ATV keys to new subsection structure.
	upgradeConfig()

	# Backwards-compatibility aliases so plugins referencing old flat keys still work.
	config.epgselection.enhanced_eventfs = config.epgselection.single.eventfs
	config.epgselection.enhanced_itemsperpage = config.epgselection.single.itemsperpage


# ─── Settings mapping: old flat key → new subsection key ───────────────────────
#
# Use this table to find and replace all usages in EpgSelection.py and Setup screens.
#
# OLD KEY                                  NEW KEY
# ──────────────────────────────────────── ─────────────────────────────────────
# config.epgselection.sort                 config.epgselection.sort                 (unchanged)
# config.epgselection.overjump             config.epgselection.overjump             (unchanged)
#
# INFOBAR
# config.epgselection.infobar_type_mode    config.epgselection.infobar.type_mode
# config.epgselection.infobar_preview_mode config.epgselection.infobar.preview_mode
# config.epgselection.infobar_ok           config.epgselection.infobar.btn_ok
# config.epgselection.infobar_oklong       config.epgselection.infobar.btn_oklong
# config.epgselection.infobar_itemsperpage config.epgselection.infobar.itemsperpage
# config.epgselection.infobar_roundto      config.epgselection.infobar.roundto
# config.epgselection.infobar_histminutes  config.epgselection.infobar.histminutes
# config.epgselection.infobar_prevtime     config.epgselection.infobar.prevtime
# config.epgselection.infobar_prevtimeperiod config.epgselection.infobar.prevtimeperiod
# config.epgselection.infobar_primetimehour  } → config.epgselection.infobar.primetime
# config.epgselection.infobar_primetimemins  }
# config.epgselection.infobar_servicetitle_mode config.epgselection.infobar.servicetitle_mode
# config.epgselection.infobar_servfs       config.epgselection.infobar.servfs
# config.epgselection.infobar_eventfs      config.epgselection.infobar.eventfs
# config.epgselection.infobar_timelinefs   config.epgselection.infobar.timelinefs
# config.epgselection.infobar_timeline24h  config.epgselection.infobar.timeline24h
# config.epgselection.infobar_servicewidth config.epgselection.infobar.servicewidth
# config.epgselection.infobar_piconwidth   config.epgselection.infobar.piconwidth
# config.epgselection.infobar_infowidth    config.epgselection.infobar.infowidth
# (no old key)                             config.epgselection.infobar.browse_mode      NEW
# (no old key)                             config.epgselection.infobar.btn_epg          NEW
# (no old key)                             config.epgselection.infobar.btn_epglong      NEW
# (no old key)                             config.epgselection.infobar.btn_info         NEW
# (no old key)                             config.epgselection.infobar.btn_infolong     NEW
# (no old key)                             config.epgselection.infobar.btn_red          NEW
# (no old key)                             config.epgselection.infobar.btn_redlong      NEW
# (no old key)                             config.epgselection.infobar.btn_green        NEW
# (no old key)                             config.epgselection.infobar.btn_greenlong    NEW
# (no old key)                             config.epgselection.infobar.btn_yellow       NEW
# (no old key)                             config.epgselection.infobar.btn_yellowlong   NEW
# (no old key)                             config.epgselection.infobar.btn_blue         NEW
# (no old key)                             config.epgselection.infobar.btn_bluelong     NEW
# (no old key)                             config.epgselection.infobar.btn_rec          NEW
# (no old key)                             config.epgselection.infobar.btn_reclong      NEW
#
# SINGLE (formerly "enhanced")
# config.epgselection.enhanced_preview_mode config.epgselection.single.preview_mode
# config.epgselection.enhanced_ok          config.epgselection.single.btn_ok
# config.epgselection.enhanced_oklong      config.epgselection.single.btn_oklong
# config.epgselection.enhanced_eventfs     config.epgselection.single.eventfs
# config.epgselection.enhanced_itemsperpage config.epgselection.single.itemsperpage
# (no old key)                             config.epgselection.single.browse_mode      NEW
# (no old key)                             config.epgselection.single.btn_epg          NEW
# (no old key)                             config.epgselection.single.btn_epglong      NEW
# (no old key)                             config.epgselection.single.btn_info         NEW
# (no old key)                             config.epgselection.single.btn_infolong     NEW
# (no old key)                             config.epgselection.single.btn_red          NEW
# (no old key)                             config.epgselection.single.btn_redlong      NEW
# (no old key)                             config.epgselection.single.btn_green        NEW
# (no old key)                             config.epgselection.single.btn_greenlong    NEW
# (no old key)                             config.epgselection.single.btn_yellow       NEW
# (no old key)                             config.epgselection.single.btn_yellowlong   NEW
# (no old key)                             config.epgselection.single.btn_blue         NEW
# (no old key)                             config.epgselection.single.btn_bluelong     NEW
# (no old key)                             config.epgselection.single.btn_rec          NEW
# (no old key)                             config.epgselection.single.btn_reclong      NEW
#
# MULTI
# config.epgselection.multi_showbouquet    config.epgselection.multi.showbouquet
# config.epgselection.multi_preview_mode   config.epgselection.multi.preview_mode
# config.epgselection.multi_ok             config.epgselection.multi.btn_ok
# config.epgselection.multi_oklong         config.epgselection.multi.btn_oklong
# config.epgselection.multi_eventfs        config.epgselection.multi.eventfs
# config.epgselection.multi_itemsperpage   config.epgselection.multi.itemsperpage
# (no old key)                             config.epgselection.multi.browse_mode       NEW
# (no old key)                             config.epgselection.multi.servicewidth      NEW
# (no old key)                             config.epgselection.multi.btn_epg           NEW
# (no old key)                             config.epgselection.multi.btn_epglong       NEW
# (no old key)                             config.epgselection.multi.btn_info          NEW
# (no old key)                             config.epgselection.multi.btn_infolong      NEW
# (no old key)                             config.epgselection.multi.btn_red           NEW
# (no old key)                             config.epgselection.multi.btn_redlong       NEW
# (no old key)                             config.epgselection.multi.btn_green         NEW
# (no old key)                             config.epgselection.multi.btn_greenlong     NEW
# (no old key)                             config.epgselection.multi.btn_yellow        NEW
# (no old key)                             config.epgselection.multi.btn_yellowlong    NEW
# (no old key)                             config.epgselection.multi.btn_blue          NEW
# (no old key)                             config.epgselection.multi.btn_bluelong      NEW
# (no old key)                             config.epgselection.multi.btn_rec           NEW
# (no old key)                             config.epgselection.multi.btn_reclong       NEW
#
# GRID (formerly "graph")
# config.epgselection.graph_showbouquet    config.epgselection.grid.showbouquet
# config.epgselection.graph_channel1       config.epgselection.grid.browse_mode        (True→"firstservice", False→"currentservice")
# config.epgselection.graph_preview_mode   config.epgselection.grid.preview_mode
# config.epgselection.graph_type_mode      config.epgselection.grid.type_mode
# config.epgselection.graph_highlight_current_events config.epgselection.grid.highlight_current_events
# config.epgselection.graph_roundto        config.epgselection.grid.roundto
# config.epgselection.graph_histminutes    config.epgselection.grid.histminutes
# config.epgselection.graph_prevtime       config.epgselection.grid.prevtime
# config.epgselection.graph_prevtimeperiod config.epgselection.grid.prevtimeperiod
# config.epgselection.graph_primetimehour  } → config.epgselection.grid.primetime
# config.epgselection.graph_primetimemins  }
# config.epgselection.graph_startmode      config.epgselection.grid.startmode
# config.epgselection.graph_servicetitle_mode config.epgselection.grid.servicetitle_mode
# config.epgselection.graph_servicename_alignment config.epgselection.grid.servicename_alignment
# config.epgselection.graph_event_alignment config.epgselection.grid.event_alignment
# config.epgselection.graph_servfs         config.epgselection.grid.servfs
# config.epgselection.graph_eventfs        config.epgselection.grid.eventfs
# config.epgselection.graph_timelinefs     config.epgselection.grid.timelinefs
# config.epgselection.graph_timeline24h    config.epgselection.grid.timeline24h
# config.epgselection.graph_itemsperpage   config.epgselection.grid.itemsperpage
# config.epgselection.graph_pig            config.epgselection.grid.pig
# config.epgselection.graph_servicewidth   config.epgselection.grid.servicewidth
# config.epgselection.graph_piconwidth     config.epgselection.grid.piconwidth
# config.epgselection.graph_infowidth      config.epgselection.grid.infowidth
# config.epgselection.graph_rec_icon_height config.epgselection.grid.rec_icon_height
# config.epgselection.graph_ok             config.epgselection.grid.btn_ok
# config.epgselection.graph_oklong         config.epgselection.grid.btn_oklong
# config.epgselection.graph_info           config.epgselection.grid.btn_info
# config.epgselection.graph_infolong       config.epgselection.grid.btn_infolong
# config.epgselection.graph_channelbtn     config.epgselection.grid.btn_channelup / .btn_channeldown  (split)
# config.epgselection.graph_red            config.epgselection.grid.btn_red
# config.epgselection.graph_green          config.epgselection.grid.btn_green
# config.epgselection.graph_yellow         config.epgselection.grid.btn_yellow
# config.epgselection.graph_blue           config.epgselection.grid.btn_blue
# (no old key)                             config.epgselection.grid.servicenumber_alignment  NEW
# (no old key)                             config.epgselection.grid.timelinedate_alignment   NEW
# (no old key)                             config.epgselection.grid.number_buttons_mode      NEW
# (no old key)                             config.epgselection.grid.btn_epg          NEW
# (no old key)                             config.epgselection.grid.btn_epglong      NEW
# (no old key)                             config.epgselection.grid.btn_redlong      NEW
# (no old key)                             config.epgselection.grid.btn_greenlong    NEW
# (no old key)                             config.epgselection.grid.btn_yellowlong   NEW
# (no old key)                             config.epgselection.grid.btn_blue         NEW (was btn only via colorMap)
# (no old key)                             config.epgselection.grid.btn_bluelong     NEW
# (no old key)                             config.epgselection.grid.btn_rec          NEW
# (no old key)                             config.epgselection.grid.btn_reclong      NEW
#
# VERTICAL (all ATV-specific; subsection keys just drop the "vertical_" prefix)
# config.epgselection.vertical_primetimehour } → config.epgselection.vertical.primetime
# config.epgselection.vertical_primetimemins }
# config.epgselection.vertical_prevtime      config.epgselection.vertical.prevtime
# config.epgselection.vertical_itemsperpage  config.epgselection.vertical.itemsperpage
# config.epgselection.vertical_eventfs       config.epgselection.vertical.eventfs
# config.epgselection.vertical_preview_mode  config.epgselection.vertical.preview_mode
# config.epgselection.vertical_pig           config.epgselection.vertical.pig
# config.epgselection.vertical_eventmarker   config.epgselection.vertical.eventmarker
# config.epgselection.vertical_showlines     config.epgselection.vertical.showlines
# config.epgselection.vertical_startmode     config.epgselection.vertical.startmode
# config.epgselection.vertical_channelbtn    config.epgselection.vertical.channelbtn
# config.epgselection.vertical_channelbtn_invert config.epgselection.vertical.channelbtn_invert
# config.epgselection.vertical_updownbtn     config.epgselection.vertical.updownbtn
# config.epgselection.vertical_ok            config.epgselection.vertical.btn_ok
# config.epgselection.vertical_oklong        config.epgselection.vertical.btn_oklong
# config.epgselection.vertical_info          config.epgselection.vertical.btn_info
# config.epgselection.vertical_infolong      config.epgselection.vertical.btn_infolong
# config.epgselection.vertical_red           config.epgselection.vertical.btn_red
# config.epgselection.vertical_green         config.epgselection.vertical.btn_green
# config.epgselection.vertical_yellow        config.epgselection.vertical.btn_yellow
# config.epgselection.vertical_blue          config.epgselection.vertical.btn_blue


# ═══════════════════════════════════════════════════════════════════════════════
# EPGSettings — per-type unified config accessor
# ═══════════════════════════════════════════════════════════════════════════════
#
# Usage in EPGSelectionNEW.py (or any EPG screen):
#
#   from Components.EpgConfig import EPGSettings
#   self._cfg = EPGSettings(self.type)
#
#   action = self._cfg.ok           # value string, e.g. "zap"
#   action = self._cfg.oklong       # e.g. "zapExit"
#   action = self._cfg.btn("red")   # e.g. "openIMDb"
#   action = self._cfg.btn("red", long=True)   # e.g. "sortEPG"
#   action = self._cfg.info         # e.g. "openEventView"
#   action = self._cfg.infolong     # e.g. "openSingleEPG"
#   action = self._cfg.epg          # e.g. "openSingleEPG"
#   action = self._cfg.rec          # e.g. "addEditTimerMenu"
#
# ───────────────────────────────────────────────────────────────────────────────
# SETTINGS REFERENCE — Status, Behavior Changes, Open Items
# ───────────────────────────────────────────────────────────────────────────────
#
# CHANGED vs. old openATV flat schema:
# ─────────────────────────────────────
# itemsperpage (all types):
#   OLD: integer only (5 = 5 rows, always divided by this value).
#   NEW: 0 = "use skin default" (EpgListNEW skips division when value == 0),
#        integers 1+ work as before.
#   IMPACT: First-time users get skin default; existing users migrated to old value.
#
# primetime (grid, infobar, vertical):
#   OLD: two separate ConfigSelectionNumber items (hour + minute as ints).
#   NEW: single ConfigClock; .value returns [hour, minute] list.
#   ACCESS: pt = config.epgselection.grid.primetime.value; pt[0] = hour, pt[1] = minute.
#   MIGRATION: hour string "20" → ConfigClock saved_value "20:00" (appends ":00").
#
# graph_channelbtn (grid only):
#   OLD: single choice "page"/"24"/"bouquet"; controlled both channel+/- together.
#   NEW: split into btn_channelup ("forward24Hours"/"prevPage")
#              and btn_channeldown ("back24Hours"/"nextPage").
#   NOTE: "bouquet" option removed — no equivalent in channelUpActions.
#         Users who had "bouquet" fall back to default (prevPage/nextPage).
#
# Button values (ok, info, color buttons):
#   OLD: human-readable strings "Zap", "Zap + Exit", "Channel Info", "Single EPG",
#        "imdb", "timer", "autotimer", "epgsearch", "showmovies", "record",
#        "24plus", "24minus", "tmdb".
#   NEW: action ID strings "zap", "zapExit", "openEventView", "openSingleEPG",
#        "openIMDb", "addEditTimer", "addEditAutoTimer", "openEPGSearch",
#        "showMovies", "addEditTimerMenu", "forward24Hours", "back24Hours",
#        "openTMDb".
#   MIGRATION: handled in upgradeConfig() via colorMap / okMap / infoMap.
#   LOST (no mapping): "prevpage", "nextpage", "prevbouquet", "nextbouquet",
#        "bouquetlist", "gotodatetime" from old color buttons (non-standard ATV
#        extensions) — these will fall back to the configured default on first run.
#
# servicetitle_mode (grid, infobar):
#   OLD: "servicenumber+picon" and "servicenumber+picon+servicename" had
#        reversed ordering in the ATV label vs. value.
#   NEW: ordering is consistent (picon always before servicenumber in value).
#   MIGRATION: titleModeMap corrects the two affected variants.
#
# ─────────────────────────────────────
# NEW settings (not in old openATV, now configurable):
# ─────────────────────────────────────
# browse_mode (infobar, single, multi):
#   Determines which service is pre-selected when the EPG opens.
#   "currentservice" = currently playing service (old hard-coded behavior).
#   "lastepgservice" = remember last browsed service across sessions.
#   STATUS: Config key exists but EPGSelectionNEW.onCreate() does NOT yet use it.
#   TODO: Implement browse_mode logic in onCreate() for each EPG type.
#
# btn_epg / btn_epglong (all types):
#   Configurable action for the EPG button (old: always opened SingleEPG).
#   STATUS: Config key exists. EPGSelectionNEW.epgButtonPressed() does NOT yet
#   dispatch from btn_epg — it still calls OpenSingleEPG() directly.
#   TODO: dispatch via EPGSettings.epg in epgButtonPressed().
#
# btn_info / btn_infolong (single, multi, infobar — NEW for these types):
#   Old code only had configurable info for graph and vertical.
#   Single/multi/infobar now also have btn_info / btn_infolong.
#   STATUS: Config key exists. EPGSelectionNEW._getInfoConfig() only handles
#   grid and vertical — single/multi/infobar still use the default infoKeyPressed().
#   TODO: Extend _getInfoConfig() (or EPGSettings.info) to cover all types.
#
# btn_red/green/yellow/blue + long variants (single, multi, infobar — NEW):
#   Old code had hardcoded behavior for non-graph/non-vertical types
#   (red=IMDb, green=AddTimer, yellow=EPGSearch, blue=AddAutoTimer).
#   Now all types have configurable color buttons.
#   STATUS: Config keys exist. EPGSelectionNEW._dispatchEpgAction() and
#   _getColorConfig() only handle grid and vertical.
#   TODO: Extend _dispatchEpgAction()/_getColorConfig() to single/multi/infobar
#   so color buttons become configurable for those types too.
#
# btn_rec / btn_reclong (all types):
#   Old code had hard-coded record (short=AddTimer, long=ZapTimer).
#   Now the record button behavior is configurable per type via recActions.
#   STATUS: Config key exists. EPGSelectionNEW recButtonPressed / recButtonPressedLong
#   do NOT yet dispatch from btn_rec/btn_reclong.
#   TODO: Implement rec button dispatch in EPGSelectionNEW.
#
# ─────────────────────────────────────
# OPENVIX-ONLY settings (in config, not yet implemented in openATV code):
# ─────────────────────────────────────
# grid.highlight_current_events:
#   OpenViX highlights currently-airing events with a special color.
#   EpgListNEW.py does NOT implement this — no equivalent rendering code.
#   TODO: Add highlight logic in EpgListNEW.buildGraphEntry() if desired.
#
# grid.number_buttons_mode:
#   OpenViX lets the user choose whether number keys navigate by page or
#   jump to a service by number. EPGSelectionNEW.keyNumberGlobal() always
#   uses the "page/time" navigation (key 2=prevPage, 8=nextPage, etc.).
#   TODO: Branch on grid.number_buttons_mode.value in keyNumberGlobal().
#
# grid.servicenumber_alignment:
#   EpgListNEW.buildGraphEntry() does not yet read this key; it hard-codes
#   RT_HALIGN_CENTER | RT_VALIGN_CENTER for the channel number.
#   TODO: Apply servicenumber_alignment in buildGraphEntry().
#
# grid.timelinedate_alignment:
#   TimelineText.setEntries() in EpgListNEW does not yet read this key.
#   TODO: Apply timelinedate_alignment in setEntries().
#
# infoActions "switchToSingleEPG" / "switchToGridEPG" / "switchToMultiEPG":
#   These can be assigned to btn_info/btn_epg but the switch logic
#   (close with a specific return type and reopen in another EPG mode) is
#   not implemented in EPGSelectionNEW.
#   TODO: Handle these in the close/reopen flow.
#
# ─────────────────────────────────────
# STILL OPEN / TODOs summary:
# ─────────────────────────────────────
# 1. browse_mode — implement in EPGSelectionNEW.onCreate()
# 2. btn_epg dispatch — implement in EPGSelectionNEW.epgButtonPressed()
# 3. btn_info for single/multi/infobar — extend _getInfoConfig()
# 4. Color buttons for single/multi/infobar — extend _dispatchEpgAction()
# 5. btn_rec / btn_reclong — implement dispatch in EPGSelectionNEW
# 6. grid.highlight_current_events — implement in EpgListNEW
# 7. grid.number_buttons_mode — implement in EPGSelectionNEW.keyNumberGlobal()
# 8. grid.servicenumber_alignment — apply in EpgListNEW.buildGraphEntry()
# 9. grid.timelinedate_alignment — apply in EpgListNEW (TimelineText)
# 10. switchToXxxEPG infoActions — implement close/reopen in EPGSelectionNEW
# 11. Move action lists (epgActions, okActions, …) to EpgSelectionBase.py
#     and import from there (currently duplicated inline in EpgConfig.py)


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

	# Maps EPG type constant → config subsection object (set after initEPGConfig runs)
	_TYPE_SECTION = {
		EPG_TYPE_GRAPH: lambda: config.epgselection.grid,
		EPG_TYPE_INFOBARGRAPH: lambda: config.epgselection.infobar,
		EPG_TYPE_INFOBAR: lambda: config.epgselection.infobar,
		EPG_TYPE_ENHANCED: lambda: config.epgselection.single,
		EPG_TYPE_MULTI: lambda: config.epgselection.multi,
		EPG_TYPE_VERTICAL: lambda: config.epgselection.vertical,
		EPG_TYPE_SINGLE: lambda: config.epgselection.single,
	}

	def __init__(self, epg_type):
		factory = self._TYPE_SECTION.get(epg_type)
		self._section = factory() if factory else None
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

	# ── ok / oklong ─────────────────────────────────────────────────────────
	@property
	def ok(self):
		"""Action for the OK button (short press). Default: "zap"."""
		return self._get("btn_ok", "zap")

	@property
	def oklong(self):
		"""Action for the OK button (long press). Default: "zapExit"."""
		return self._get("btn_oklong", "zapExit")

	# ── info / infolong ──────────────────────────────────────────────────────
	@property
	def info(self):
		"""Action for the INFO button (short press). Default: "openEventView"."""
		return self._get("btn_info", "openEventView")

	@property
	def infolong(self):
		"""Action for the INFO button (long press). Default: "openSingleEPG"."""
		return self._get("btn_infolong", "openSingleEPG")

	# ── epg / epglong ────────────────────────────────────────────────────────
	@property
	def epg(self):
		"""Action for the EPG button (short press). Default: "openSingleEPG"."""
		return self._get("btn_epg", "openSingleEPG")

	@property
	def epglong(self):
		"""Action for the EPG button (long press). Default: ""."""
		return self._get("btn_epglong", "")

	# ── rec / reclong ────────────────────────────────────────────────────────
	@property
	def rec(self):
		"""Action for the record button (short press). Default: "addEditTimerMenu"."""
		return self._get("btn_rec", "addEditTimerMenu")

	@property
	def reclong(self):
		"""Action for the record button (long press). Default: "addEditZapTimerSilent"."""
		return self._get("btn_reclong", "addEditZapTimerSilent")

	# ── color buttons ────────────────────────────────────────────────────────
	def btn(self, color, long=False):
		"""Return the configured action for a color button.

		Args:
			color: "red", "green", "yellow", or "blue"
			long:  True for long-press variant

		Returns:
			action ID string (e.g. "openIMDb") or "" if not configured / unknown type.
		"""
		suffix = "long" if long else ""
		defaults = {
			"red": "openIMDb",
			"green": "addEditTimer",
			"yellow": "openEPGSearch",
			"blue": "addEditAutoTimer",
		}
		return self._get(f"btn_{color}{suffix}", defaults.get(color, ""))

	# ── channel+/- (grid only) ───────────────────────────────────────────────
	@property
	def channelup(self):
		"""Action for channel-up button (grid/infobargraph only). Default: "prevPage"."""
		return self._get("btn_channelup", "prevPage")

	@property
	def channeldown(self):
		"""Action for channel-down button (grid/infobargraph only). Default: "nextPage"."""
		return self._get("btn_channeldown", "nextPage")

	# ── preview mode ─────────────────────────────────────────────────────────
	@property
	def preview_mode(self):
		"""Preview mode value for this EPG type."""
		return self._get("preview_mode", "0")

	# ── primetime ────────────────────────────────────────────────────────────
	@property
	def primetime(self):
		"""Primetime as (hour, minute) from ConfigClock. Returns (20, 0) as fallback."""
		if self._section is None:
			return (20, 0)
		cfg = getattr(self._section, "primetime", None)
		if cfg is None:
			return (20, 0)
		v = cfg.value
		return (v[0], v[1]) if v else (20, 0)

	# ── itemsperpage ─────────────────────────────────────────────────────────
	@property
	def itemsperpage(self):
		"""Items per page (0 = skin default). Returns integer."""
		return self._get("itemsperpage", 0)
