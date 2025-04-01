# Based on a plugin from Sif Team.
# This version created by IanSav and the OpenATV team.

from os.path import join
from sys import maxsize

from enigma import eDVBDB, eServiceCenter, eServiceReference, eTimer

from Components.ActionMap import HelpableActionMap
from Components.config import ConfigSelection, ConfigSubsection, ConfigYesNo, config
from Components.PluginComponent import plugins
from Components.Sources.StaticText import StaticText
from Plugins.Plugin import PluginDescriptor
from Screens.Setup import Setup
from Tools.Directories import SCOPE_CONFIG, SCOPE_PLUGIN_ABSOLUTE, fileReadLines, fileReadXML, fileWriteLines, resolveFilename

MODULE_NAME = __name__.split(".")[-1]

config.plugins.LCNScanner = ConfigSubsection()
config.plugins.LCNScanner.showInPluginsList = ConfigYesNo(default=False)
config.plugins.LCNScanner.showInPluginsList.addNotifier(plugins.reloadPlugins, initial_call=False, immediate_feedback=False)


class LCNScanner:
	MODE_TV = "1:7:1:0:0:0:0:0:0:0:(type == 1) || (type == 17) || (type == 22) || (type == 25) || (type == 134) || (type == 195)"
	MODE_RADIO = "1:7:2:0:0:0:0:0:0:0:(type == 2) || (type == 10)"
	MODES = {
		"TV": (1, 17, 22, 25, 134, 195),
		"Radio": (2, 10)
	}

	OLDDB_NAMESPACE = 0
	OLDDB_ONID = 1
	OLDDB_TSID = 2
	OLDDB_SID = 3
	OLDDB_LCN = 4
	OLDDB_SIGNAL = 5

	DB_SID = 0
	DB_TSID = 1
	DB_ONID = 2
	DB_NAMESPACE = 3
	DB_SIGNAL = 4
	DB_LCN_BROADCAST = 5
	DB_LCN_SCANNED = 6
	DB_LCN_GUI = 7
	DB_PROVIDER = 8  # Max 255 characters.
	DB_PROVIDER_GUI = 9
	DB_SERVICENAME = 10  # Max 255 characters.
	DB_SERVICENAME_GUI = 11

	LCNS_MEDIUM = 0
	LCNS_TRIPLET = 1
	LCNS_SERVICEREFERENCE = 2
	LCNS_SIGNAL = 3
	LCNS_LCN_BROADCAST = 4
	LCNS_LCN_SCANNED = 5
	LCNS_LCN_GUI = 6
	LCNS_PROVIDER = 7
	LCNS_PROVIDER_GUI = 8
	LCNS_SERVICENAME = 9
	LCNS_SERVICENAME_GUI = 10

	SERVICE_PROVIDER = 0
	SERVICE_SERVICEREFERENCE = 1
	SERVICE_NAME = 2

	def __init__(self):
		# This code is not currently needed but is being kept in case needs change.
		# def readBouquet(mode):
		# 	bouquetList = {}
		# 	bouquets = fileReadLines(join(self.configPath, f"bouquets.{mode}"), default=[], source=MODULE_NAME)
		# 	for bouquet in bouquets:
		# 		if bouquet[:8] != "#SERVICE":
		# 			continue
		# 		data = bouquet.strip().split(":")[-1]
		# 		bouquetFile = None
		# 		if data[:13] == "FROM BOUQUET ":
		# 			endPos = data.find(" ", 13)
		# 			bouquetFile = data if endPos == -1 else data[13:endPos].strip("\"")
		# 		else:
		# 			bouquetFile = data
		# 		if bouquetFile:
		# 			bouquetLines = fileReadLines(join(self.configPath, bouquetFile), default=[], source=MODULE_NAME)
		# 			for bouquetLine in bouquetLines:
		# 				if bouquetLine[:6] == "#NAME ":
		# 					bouquetList[bouquetFile] = bouquetLine[6:]
		# 					break
		# 	return bouquetList

		self.configPath = resolveFilename(SCOPE_CONFIG)
		# This code is not currently needed but is being kept in case needs change.
		# bouquetTV = readBouquet("tv")
		# bouquetRadio = readBouquet("radio")
		# cableBouquetTV = bouquetTV if "userbouquet.cable_lcn.tv" in bouquetTV else bouquetTV | {"userbouquet.cable_lcn.tv": "Cable TV LCN"}
		# cableBouquetRadio = bouquetRadio if "userbouquet.cable_lcn.radio" in bouquetRadio else bouquetRadio | {"userbouquet.cable_lcn.radio": "Cable Radio LCN"}
		# satelliteBouquetTV = bouquetTV if "userbouquet.satellite_lcn.tv" in bouquetTV else bouquetTV | {"userbouquet.satellite_lcn.tv": "Satellite TV LCN"}
		# satelliteBouquetRadio = bouquetRadio if "userbouquet.satellite_lcn.radio" in bouquetRadio else bouquetRadio | {"userbouquet.satellite_lcn.radio": "Satellite Radio LCN"}
		# terrestrialBouquetTV = bouquetTV if "userbouquet.terrestrial_lcn.tv" in bouquetTV else bouquetTV | {"userbouquet.terrestrial_lcn.tv": "Terrestrial TV LCN"}
		# terrestrialBouquetRadio = bouquetRadio if "userbouquet.terrestrial_lcn.radio" in bouquetRadio else bouquetRadio | {"userbouquet.terrestrial_lcn.radio": "Terrestrial Radio LCN"}
		self.ruleList = {}
		self.rulesDom = fileReadXML(resolveFilename(SCOPE_PLUGIN_ABSOLUTE, "rules.xml"), default="<rulesxml />", source=MODULE_NAME)
		if self.rulesDom is not None:
			rulesIndex = 1
			for rules in self.rulesDom.findall("rules"):
				name = rules.get("name")
				if name:
					self.ruleList[name] = name
				else:
					name = f"Rules{rulesIndex}"
					rules.set("name", name)
					self.ruleList[name] = name
					rulesIndex += 1
		# This code is not currently needed but is being kept in case needs change.
		# config.plugins.LCNScanner.cableBouquetTV = ConfigSelection(default="userbouquet.cable_lcn.tv", choices=cableBouquetTV)
		# config.plugins.LCNScanner.cableBouquetRadio = ConfigSelection(default="userbouquet.cable_lcn.radio", choices=cableBouquetRadio)
		# config.plugins.LCNScanner.satelliteBouquetTV = ConfigSelection(default="userbouquet.satellite_lcn.tv", choices=satelliteBouquetTV)
		# config.plugins.LCNScanner.satelliteBouquetRadio = ConfigSelection(default="userbouquet.satellite_lcn.radio", choices=satelliteBouquetRadio)
		# config.plugins.LCNScanner.terrestrialBouquetTV = ConfigSelection(default="userbouquet.terrestrial_lcn.tv", choices=terrestrialBouquetTV)
		# config.plugins.LCNScanner.terrestrialBouquetRadio = ConfigSelection(default="userbouquet.terrestrial_lcn.radio", choices=terrestrialBouquetRadio)
		config.plugins.LCNScanner.rules = ConfigSelection(default="Default", choices=self.ruleList)
		config.plugins.LCNScanner.useSpacerLines = ConfigYesNo(default=False)
		config.plugins.LCNScanner.addServiceNames = ConfigYesNo(default=False)
		config.plugins.LCNScanner.useDescriptionLines = ConfigYesNo(default=False)

	def lcnScan(self, callback=None):
		def getModes(element):
			mode = element.get("mode", "All")
			match mode:
				case "All" | "Both":
					modes = ("TV", "Radio")
				case "TV":
					modes = ("TV",)
				case "Radio":
					modes = ("Radio",)
				case _:
					print(f"[LCNScanner] Error: Invalid mode '{mode}' specified, 'All' assumed!  (Only 'All', 'Both', 'Radio' or 'TV' permitted.)")
					modes = ("TV", "Radio")
			return modes

		def loadLCNs():
			print("[LCNScanner] Loading 'lcndb' file.")
			lcndb = []
			for lcn in fileReadLines(join(self.configPath, "lcndb"), default=[], source=MODULE_NAME):
				if lcn not in lcndb:
					lcndb.append(lcn)
				else:
					print(f"[LCNScanner] Error: Duplicated line detected in lcndb!  ({lcn}).")
			# for lcn in lcndb:
			# 	print(f"[LCNScanner] loadLCNs DEBUG: LCN '{lcn}'.")
			return lcndb

		def loadServices(mode):
			print(f"[LCNScanner] Loading {mode} services.")
			services = {}
			serviceHandler = eServiceCenter.getInstance()
			match mode:
				case "TV":
					providerQuery = f"{self.MODE_TV} FROM PROVIDERS ORDER BY name"
				case "Radio":
					providerQuery = f"{self.MODE_RADIO} FROM PROVIDERS ORDER BY name"
			providers = serviceHandler.list(eServiceReference(providerQuery))
			if providers:
				for serviceQuery, providerName in providers.getContent("SN", True):
					serviceList = serviceHandler.list(eServiceReference(serviceQuery))
					for serviceReference, serviceName in serviceList.getContent("SN", True):
						services[":".join(serviceReference.split(":")[3:7])] = (providerName, serviceReference, serviceName)
			# for service in sorted(services.keys()):
			# 	print(f"[LCNScanner] loadServices DEBUG: Service '{service}' -> {services[service]}.")
			return services

		def matchLCNsAndServices(mode, lcndb, services, duplicate, renumbers):
			print(f"[LCNScanner] Matching LCN entries with {mode} services.")
			lcns = []
			try:
				version = int(lcndb[0][9:]) if lcndb[0].startswith("#VERSION ") else 1
			except Exception:
				version = 1
			match version:
				case 1:
					for line in lcndb:
						line = line.strip()
						if len(line) != 38:
							continue
						item = line.split(":")
						if len(item) != 6:
							continue
						match item[self.OLDDB_NAMESPACE][:4].upper():
							case "DDDD":
								medium = "A"
							case "EEEE":
								medium = "T"
							case "FFFF":
								medium = "C"
							case _:
								medium = "S"
						service = f"{item[self.OLDDB_SID].lstrip("0")}:{item[self.OLDDB_TSID].lstrip("0")}:{item[self.OLDDB_ONID].lstrip("0")}:{item[self.OLDDB_NAMESPACE].lstrip("0")}".upper()
						lcns.append([
							medium,
							service,
							services[service][self.SERVICE_SERVICEREFERENCE] if service in services else "",
							int(item[self.OLDDB_SIGNAL]),
							int(item[self.OLDDB_LCN]),
							0,
							0,
							services[service][self.SERVICE_PROVIDER] if service in services else "",
							"",
							services[service][self.SERVICE_NAME] if service in services else "",
							""
						])
				case 2:
					for line in lcndb:
						if line.startswith("#"):
							continue
						item = line.split(":")
						match item[self.DB_NAMESPACE][:4]:
							case "DDDD":
								medium = "A"
							case "EEEE":
								medium = "T"
							case "FFFF":
								medium = "C"
							case _:
								medium = "S"
						service = f"{item[self.DB_SID]}:{item[self.DB_TSID]}:{item[self.DB_ONID]}:{item[self.DB_NAMESPACE]}"
						lcns.append([
							medium,
							service,
							services[service][self.SERVICE_SERVICEREFERENCE] if service in services else "",
							int(item[self.DB_SIGNAL]),
							int(item[self.DB_LCN_BROADCAST]),
							int(item[self.DB_LCN_SCANNED]),
							int(item[self.DB_LCN_GUI]),
							services[service][self.SERVICE_PROVIDER] if service in services else "",
							item[self.DB_PROVIDER_GUI],
							services[service][self.SERVICE_NAME] if service in services else "",
							item[self.DB_SERVICENAME_GUI]
						])
				case _:
					print("[LCNScanner] Error: LCN db file format unrecognized!")
			scannerLCN = duplicate[mode][0]
			scannerLast = duplicate[mode][1]
			cableCache = {}  # Cache to check for unique cable LCNs.
			satelliteCache = {}  # Cache to check for unique satellite LCNs.
			terrestrialCache = {}  # Cache to check for unique terrestrial LCNs.
			cableLCNs = {}  # Dictionary for available and unique cable LCNs.
			satelliteLCNs = {}  # Dictionary for available and unique satellite LCNs.
			terrestrialLCNs = {}  # Dictionary for available and unique terrestrial LCNs.
			for data in lcns:
				service = data[self.LCNS_TRIPLET]
				serviceReference = data[self.LCNS_SERVICEREFERENCE].split(":")
				lcn = data[self.LCNS_LCN_BROADCAST]
				match data[self.LCNS_MEDIUM]:
					case "C":
						lcnCache = cableCache
						serviceLCNs = cableLCNs
					case "S":
						lcnCache = satelliteCache
						serviceLCNs = satelliteLCNs
					case "A" | "T":
						lcnCache = terrestrialCache
						serviceLCNs = terrestrialLCNs
				if service in services:  # Check if the service represented by this LCN entry is still a valid service.
					if lcn in lcnCache:  # Check if the LCN already exists.
						if data[self.LCNS_TRIPLET] == lcnCache[lcn][self.LCNS_TRIPLET] and data[self.LCNS_SIGNAL] > lcnCache[lcn][self.LCNS_SIGNAL]:
							data[self.LCNS_LCN_SCANNED] = data[self.LCNS_LCN_BROADCAST]
							lcnCache[lcn] = data  # Replace the existing weaker signal with the stronger one.
						elif scannerLCN > scannerLast:  # Check if there is no more space for duplicates.
							print(f"[LCNScanner] Warning: Duplicate LCN {lcn} found for servine '{data[self.LCNS_SERVICEREFERENCE]}' but duplicate LCN range exhausted!")
						else:  # Allocate a new LCN from the duplicate pool.
							print(f"[LCNScanner] Duplicate LCN found, renumbering {lcn} to {scannerLCN}.")
							lcn = scannerLCN
							data[self.LCNS_LCN_SCANNED] = lcn
							lcnCache[lcn] = data
							scannerLCN += 1
					else:
						data[self.LCNS_LCN_SCANNED] = data[self.LCNS_LCN_BROADCAST]
						lcnCache[lcn] = data
				elif len(serviceReference) > 2 and serviceReference[2] in self.MODES[mode]:  # Skip all LCN entries of the same type that are not a valid service.
					print(f"[LCNScanner] Service '{service}' with LCN {lcn} not a valid {mode} service!")
					continue
				else:
					continue
				for renumber in renumbers[mode]:  # Process the LCN renumbering rules.
					if renumber[0][0] <= lcn <= renumber[0][1]:
						try:
							startingLCN = lcn
							lcn = int(eval(renumber[1].replace("LCN", str(lcn))))
							print(f"[LCNScanner] LCN {startingLCN} is renumbered to {lcn} via rule range {renumber[0][0]}-{renumber[0][1]} and formula='{renumber[1]}'.")
							if lcn in lcnCache:
								print(f"[LCNScanner] Renumbered LCN {startingLCN} is now a duplicated LCN {lcn}, renumbering {startingLCN} to {scannerLCN}.")
								data[self.LCNS_LCN_SCANNED] = scannerLCN
								scannerLCN += 1
							else:
								data[self.LCNS_LCN_SCANNED] = lcn
						except ValueError as err:
							print(f"[LCNScanner] Error: LCN renumber formula '{renumber[1]}' is invalid!  ({err})")
				serviceLCNs[lcn] = tuple(data)
			# for lcn in sorted(cableLCNs.keys()):
			# 	print(f"[LCNScanner] matchLCNsAndServices DEBUG: Cable LCN '{lcn}' -> {cableLCNs[lcn]}.")
			# for lcn in sorted(satelliteLCNs.keys()):
			# 	print(f"[LCNScanner] matchLCNsAndServices DEBUG: Satellite LCN '{lcn}' -> {satelliteLCNs[lcn]}.")
			# for lcn in sorted(terrestrialLCNs.keys()):
			# 	print(f"[LCNScanner] matchLCNsAndServices DEBUG: Terrestrial LCN '{lcn}' -> {terrestrialLCNs[lcn]}.")
			return (cableLCNs, satelliteLCNs, terrestrialLCNs)

		def writeBouquet(mode, medium, serviceLCNs, markers):
			def insertMarker(mode, lcn):
				if lcn in markers[mode]:
					bouquet.append(f"#SERVICE 1:64:0:0:0:0:0:0:0:0::{markers[mode][lcn]}")
					if useDescriptionLines:
						bouquet.append(f"#DESCRIPTION {markers[mode][lcn]}")
				return bouquet

			useDescriptionLines = config.plugins.LCNScanner.useDescriptionLines.value if config.plugins.LCNScanner.addServiceNames.value else False
			bouquet = []
			bouquet.append(f"#NAME {medium} {mode} LCN")
			bouquet.append(f"#SERVICE 1:64:0:0:0:0:0:0:0:0::{medium} {mode} LCN")
			if useDescriptionLines:
				bouquet.append(f"#DESCRIPTION {medium} {mode} LCN")
			index = 0
			useSpacerLines = config.plugins.LCNScanner.useSpacerLines.value
			for lcn in sorted(serviceLCNs.keys()):
				index += 1
				while lcn > index:
					bouquet = insertMarker(mode, index)
					if useSpacerLines:
						bouquet.append("#SERVICE 1:832:D:0:0:0:0:0:0:0:")
					index += 1
				bouquet = insertMarker(mode, index)
				name = serviceLCNs[lcn][self.LCNS_SERVICENAME]
				serviceName = f":{name}" if config.plugins.LCNScanner.addServiceNames.value else ""
				bouquet.append(f"#SERVICE {serviceLCNs[lcn][self.LCNS_SERVICEREFERENCE]}{serviceName}")
				if useDescriptionLines:
					bouquet.append(f"#DESCRIPTION {name}")
			# Save bouquet and, if required, add this bouquet to the list of bouquets.
			extension = mode.lower()
			# This code is not currently needed but is being kept in case needs change.
			# bouquetName = getattr(config.plugins.LCNScanner, f"{medium.lower()}Bouquet{mode}", f"userbouquet.{medium.lower()}_lcn.{mode}").value
			bouquetName = f"userbouquet.{medium.lower()}_lcn.{extension}"
			bouquetsPath = join(self.configPath, bouquetName)
			if fileWriteLines(bouquetsPath, bouquet, source=MODULE_NAME):
				print(f"[LCNScanner] Bouquet '{bouquetsPath}' saved.")
			else:
				print(f"[LCNScanner] Error: Bouquet '{bouquetsPath}' could not be saved!")
			bouquetsPath = join(self.configPath, f"bouquets.{extension}")
			bouquets = fileReadLines(bouquetsPath, default=[], source=MODULE_NAME)
			for bouquet in bouquets:
				if bouquet.find(bouquetName) != -1:
					print(f"[LCNScanner] Bouquet '{bouquetName}' is already in '{bouquetsPath}'.")
					break
			else:
				bouquets.append(f"#SERVICE 1:7:2:0:0:0:0:0:0:0:FROM BOUQUET \"{bouquetName}\" ORDER BY bouquet")
				if fileWriteLines(bouquetsPath, bouquets, source=MODULE_NAME):
					print(f"[LCNScanner] Bouquet '{bouquetName}' added to '{bouquetsPath}'.")
				else:
					print(f"[LCNScanner] Error: Bouquet '{bouquetName}' could not be added to '{bouquetsPath}'!")

		def buildLCNs(serviceLCNs):
			lcndb = []
			for lcn in sorted(serviceLCNs.keys()):
				data = []
				# This code is not currently supported but is being kept in case this changes.
				# for field in (self.LCNS_TRIPLET, self.LCNS_SIGNAL, self.LCNS_LCN_BROADCAST, self.LCNS_LCN_SCANNED, self.LCNS_LCN_GUI, self.LCNS_PROVIDER, self.LCNS_PROVIDER_GUI, self.LCNS_SERVICENAME, self.LCNS_SERVICENAME_GUI):
				for field in (self.LCNS_TRIPLET, self.LCNS_SIGNAL, self.LCNS_LCN_BROADCAST, self.LCNS_LCN_SCANNED, self.LCNS_LCN_GUI):
					data.append(str(serviceLCNs[lcn][field]))
				data.extend(["", "", "", ""])  # This keeps the record length as defined while all the fields are not available.
				lcndb.append(":".join(data))
			return lcndb

		print("[LCNScanner] LCN scan started.")
		duplicate = {
			"TV": [99000, maxsize],
			"Radio": [99000, maxsize]
		}
		renumbers = {
			"TV": [],
			"Radio": []
		}
		markers = {
			"TV": {},
			"Radio": {}
		}
		rules = config.plugins.LCNScanner.rules.value if config.plugins.LCNScanner.rules.value in self.ruleList.keys() else self.ruleList[0][0]
		dom = self.rulesDom.findall(f".//rules[@name='{rules}']/rule[@type='duplicate']")
		if dom is not None:
			for element in dom:
				modes = getModes(element)
				for mode in modes:
					lcnRange = element.get("range", "99000-99999")
					rangeMsg = "starting with 99000"
					markerMsg = ""
					try:
						duplicate[mode] = [int(x) for x in lcnRange.split("-", 1)]
						if len(duplicate[mode]) == 1:
							duplicate[mode].append(maxsize)
							rangeMsg = f"starting with {duplicate[mode][0]}"
						else:
							rangeMsg = f"within the range {duplicate[mode][0]} to {duplicate[mode][1]}"
						marker = element.text
						if marker:
							markers[mode][duplicate[mode][0]] = marker
							markerMsg = f" with a preceding marker of '{marker}'"
					except ValueError as err:
						print(f"[LCNScanner] Error: Duplicate range '{lcnRange}' is invalid!  ({err})")
					print(f"[LCNScanner] Duplicated LCNs for {mode} will be allocated new numbers {rangeMsg}{markerMsg}.")
		dom = self.rulesDom.findall(f".//rules[@name='{rules}']/rule[@type='renumber']")
		if dom is not None:
			for element in dom:
				modes = getModes(element)
				for mode in modes:
					lcnRange = element.get("range")
					try:
						lcnRange = [int(x) for x in lcnRange.split("-", 1)]
						if len(lcnRange) != 2:
							raise ValueError("Range format is a pair of numbers separated by a hyphen: <LOWER_LIMIT>-<HIGHER_LIMIT>")
						renumbers[mode].append((lcnRange, element.text))
						print(f"[LCNScanner] LCNs for {mode} in the range {lcnRange[0]} to {lcnRange[1]} will be renumbered with the formula '{element.text}'.")
					except ValueError as err:
						print(f"[LCNScanner] Error: Renumber range '{lcnRange}' is invalid!  ({err})")
		dom = self.rulesDom.findall(f".//rules[@name='{rules}']/rule[@type='marker']")
		if dom is not None:
			for element in dom:
				modes = getModes(element)
				for mode in modes:
					lcn = element.get("position")
					if lcn:
						try:
							lcn = int(lcn)
							markers[mode][lcn] = element.text
							print(f"[LCNScanner] Marker '{element.text}' will be added before {mode} LCN {lcn}.")
						except ValueError as err:
							print(f"[LCNScanner] Error: Invalid marker LCN '{lcn}' specified!  ({err})")
		# The actual scanning process starts here.
		lcndb = loadLCNs()
		lcns = []
		for mode in ("TV", "Radio"):
			services = loadServices(mode)
			cableLCNs, satelliteLCNs, terrestrialLCNs = matchLCNsAndServices(mode, lcndb, services, duplicate, renumbers)
			if cableLCNs or satelliteLCNs or terrestrialLCNs:
				if cableLCNs:
					writeBouquet(mode, "Cable", cableLCNs, markers)
					lcns += buildLCNs(cableLCNs)
				if satelliteLCNs:
					writeBouquet(mode, "Satellite", satelliteLCNs, markers)
					lcns += buildLCNs(satelliteLCNs)
				if terrestrialLCNs:
					writeBouquet(mode, "Terrestrial", terrestrialLCNs, markers)
					lcns += buildLCNs(terrestrialLCNs)
			else:
				print("[LCNScanner] Error: No valid entries found in the LCN database! Run a service scan.")
		if lcns:
			# This code is not currently supported but is being kept in case this changes.
			# lcns.insert(0,"#SID:TSID:ONID:NAMESPACE:SIGNAL:LCN_BROADCAST:LCN_SCANNED:LCN_GUI:PROVIDER:PROVIDER_GUI:SERVICENAME:SERVICENAME_GUI")
			lcns.insert(0, "#VERSION 2")
			if fileWriteLines(join(self.configPath, "lcndb"), lcns, source=MODULE_NAME):
				print("[LCNScanner] The 'lcndb' file has been updated.")
			else:
				print("[LCNScanner] Error: The 'lcndb' file could not be updated!")
			eDVBDB.getInstance().reloadServicelist()
		eDVBDB.getInstance().reloadBouquets()
		print("[LCNScanner] LCN scan finished.")
		if callback and callable(callback):
			callback()


class LCNScannerSetup(LCNScanner, Setup):
	def __init__(self, session):
		LCNScanner.__init__(self)
		Setup.__init__(self, session=session, setup="LCNScanner", plugin="SystemPlugins/LCNScanner")
		self["scanActions"] = HelpableActionMap(self, "ColorActions", {
			"yellow": (self.keyScan, _("Scan for terrestrial LCNs and create LCN bouquets"))
		}, prio=0, description=_("LCN Scanner Actions"))
		lines = fileReadLines(resolveFilename(SCOPE_CONFIG, "lcndb"), default=[], source=MODULE_NAME)
		if len(lines) > 1:
			self["scanActions"].setEnabled(True)
			self["key_yellow"] = StaticText(_("Scan"))
		else:
			self["scanActions"].setEnabled(False)
			self["key_yellow"] = StaticText("")

	def keyScan(self):
		def performScan():
			def keyScanCallback():
				def clearFootnote():
					self["scanActions"].setEnabled(True)
					self["key_yellow"].setText(_("Scan"))
					self.setFootnote("")

				self.timer = eTimer()
				self.timer.callback.append(clearFootnote)
				self.timer.startLongTimer(2)

			self.lcnScan(callback=keyScanCallback)

		self["scanActions"].setEnabled(False)
		self["key_yellow"].setText("")
		self.setFootnote(_("Please wait while LCN bouquets are created/updated..."))
		self.timer = eTimer()
		self.timer.callback.append(performScan)
		self.timer.start(0, True)  # Yield to the idle loop to allow a screen update.

	def keySave(self):
		if hasattr(self, "timer"):
			self.timer.stop()
		Setup.keySave(self)


def main(session, **kwargs):
	session.open(LCNScannerSetup)


def menu(menuid, **kwargs):
	return [("LCN Scanner", main, "LCNScanner", None)] if menuid == "scan" else []


def Plugins(**kwargs):
	pluginList = []
	description = _("LCN Scanner plugin for DVB-C/T/T2 services")
	pluginList.append(PluginDescriptor(where=[PluginDescriptor.WHERE_MENU], description=description, needsRestart=False, fnc=menu))
	if config.plugins.LCNScanner.showInPluginsList.value:
		pluginList.append(PluginDescriptor(name=_("LCN Scanner"), where=[PluginDescriptor.WHERE_PLUGINMENU], description=description, icon="LCNScanner.png", fnc=main))
	return pluginList
