from os.path import basename, exists
from re import fullmatch, sub
from time import monotonic
from xml.etree.ElementTree import ParseError, parse

from enigma import eDVBDB, eServiceReference, eTimer, iServiceInformation

from Components.NimManager import nimmanager
from Screens.ServiceScan import ServiceScan
from Tools.Directories import SCOPE_CONFIG, SCOPE_SKINS, fileReadLines, fileWriteLines, resolveFilename


MODULE_NAME = __name__.split(".")[-1]


class DABScan(ServiceScan):
	"""DAB-over-DVB backend for the existing Enigma2 ServiceScan screen."""

	POLL_INTERVAL = 500
	FEED_TIMEOUT = 15000
	STABLE_POLLS = 3
	SUPPORTED_DECODERS = ("fedi2eti", "tsniv2ni", "ts2na12", "ts2na")

	def __init__(self, session):
		self.previousService = session.nav.getCurrentlyPlayingServiceOrGroup()
		self.serviceRestored = False
		self.feeds = []
		self.feedErrors = []
		self.knownFeeds = 0
		self.skippedDisabledFeeds = 0
		self.skippedUnavailableFeeds = 0
		self.skippedUnsupportedFeeds = 0
		self.feedIndex = 0
		self.failures = []
		self.committedServices = 0
		self.currentServices = []
		self.feedListOffset = 0
		self.lastSignature = None
		self.stablePolls = 0
		self.feedStarted = 0
		self.scanFinished = False
		ServiceScan.__init__(self, session, [])
		self.skinName = ["ServiceScan"]
		self.setImage("ServiceScan")
		self.setTitle(_("DAB+ Scan"))
		self.pollTimer = eTimer()
		self.pollTimer.callback.append(self.pollScan)
		self.onClose.append(self.cleanup)

	def runScan(self):
		if not self.loadFeeds():
			message = _("No supported DAB+ feeds are available for the satellite positions configured on this box.") if self.knownFeeds and not self.feedErrors else _("No valid DAB+ feeds configured. Check /etc/enigma2/dab.xml.")
			self.finishWithError(message)
			return
		if self.session.nav.RecordTimer.isRecording():
			self.finishWithError(_("A DAB+ scan cannot run while a recording is in progress."))
			return
		self["scan_state"].setText(_("Starting DAB+ scan..."))
		self.startFeed()

	def loadFeeds(self):
		self.feeds = []
		self.feedErrors = []
		self.knownFeeds = 0
		self.skippedDisabledFeeds = 0
		self.skippedUnavailableFeeds = 0
		self.skippedUnsupportedFeeds = 0
		configPath = resolveFilename(SCOPE_CONFIG, "dab.xml")
		packagePath = resolveFilename(SCOPE_SKINS, "dab.xml")
		xmlPath = configPath if exists(configPath) else packagePath
		try:
			root = parse(xmlPath).getroot()
			if root.tag != "dabFeeds":
				raise ValueError("invalid root element")
			definitions = [(node, None, None) for node in root.findall("feed")]
			for satellite in root.findall("satellite"):
				for transponder in satellite.findall("transponder"):
					definitions.extend((node, transponder, satellite) for node in transponder.findall("feed"))
			for node, transponder, satellite in definitions:
				self.knownFeeds += 1
				if self.feedAttribute(node, transponder, satellite, "enabled", "true").lower() in ("0", "false", "no", "off"):
					self.skippedDisabledFeeds += 1
					continue
				try:
					feed = self.parseFeed(node, transponder, satellite)
					if not nimmanager.getNimListForSat(feed["orbitalPosition"]):
						self.skippedUnavailableFeeds += 1
						continue
					if feed["decoder"] not in self.SUPPORTED_DECODERS:
						self.skippedUnsupportedFeeds += 1
						continue
					self.feeds.append(feed)
				except (TypeError, ValueError) as err:
					feedName = node.get("name") or node.get("id") or "unknown feed"
					self.feedErrors.append(f"{feedName}: {err}")
		except (OSError, ParseError, ValueError) as err:
			self.feedErrors.append(f"{xmlPath}: {err}")
		if self.knownFeeds:
			print("[DABScan] Feed definitions: %d known, %d selected, %d unavailable, %d unsupported, %d disabled." % (self.knownFeeds, len(self.feeds), self.skippedUnavailableFeeds, self.skippedUnsupportedFeeds, self.skippedDisabledFeeds))
		for error in self.feedErrors:
			print(f"[DABScan] {error}")
		return bool(self.feeds)

	def feedAttribute(self, node, transponder, satellite, attribute, default=None):
		for source in (node, transponder, satellite):
			if source is not None and source.get(attribute) is not None:
				return source.get(attribute)
		return default

	def parseFeed(self, node, transponder=None, satellite=None):
		def attribute(name, default=None):
			return self.feedAttribute(node, transponder, satellite, name, default)
		feedId = attribute("id", "feed")
		orbitalPosition = int(attribute("orbitalPosition", "-1"), 10)
		if orbitalPosition < 0 or orbitalPosition > 3599:
			raise ValueError("invalid orbital position")
		decoder = attribute("decoder", "fedi2eti").lower()
		generatedName = "userbouquet.dab_%s.radio" % sub("[^a-z0-9_]+", "_", feedId.lower()).strip("_")
		bouquetFile = attribute("bouquetFile", generatedName)
		if basename(bouquetFile) != bouquetFile or not fullmatch(r"userbouquet\.[A-Za-z0-9_.-]+\.radio", bouquetFile):
			raise ValueError(f"invalid bouquet file name '{bouquetFile}'")
		address = attribute("multicastAddress", "")
		if decoder == "fedi2eti" and not address:
			raise ValueError("missing multicast address")
		port = int(attribute("multicastPort", "0"), 10)
		if decoder == "fedi2eti" and (port < 1 or port > 65535):
			raise ValueError("invalid multicast port")
		return {
			"id": feedId,
			"name": attribute("name", feedId),
			"satellite": attribute("satellite", attribute("name", "")) if satellite is None else satellite.get("name", ""),
			"orbitalPosition": orbitalPosition,
			"decoder": decoder,
			"transport": attribute("transport", decoder),
			"parentServiceType": self.parseHex(node, transponder, satellite, "parentServiceType"),
			"parentSid": self.parseHex(node, transponder, satellite, "parentSid"),
			"tsid": self.parseHex(node, transponder, satellite, "tsid"),
			"onid": self.parseHex(node, transponder, satellite, "onid"),
			"namespace": self.parseHex(node, transponder, satellite, "namespace"),
			"pid": self.parseHex(node, transponder, satellite, "pid"),
			"ensembleId": self.parseHex(node, transponder, satellite, "ensembleId"),
			"address": address,
			"port": port,
			"bouquetFile": bouquetFile,
			"bouquetName": attribute("bouquetName", attribute("name", feedId))
		}

	def parseHex(self, node, transponder, satellite, attribute):
		value = self.feedAttribute(node, transponder, satellite, attribute)
		if value is None:
			raise ValueError(f"missing attribute '{attribute}'")
		return int(value, 16)

	def startFeed(self):
		if self.feedIndex >= len(self.feeds):
			self.finishScan()
			return
		feed = self.feeds[self.feedIndex]
		self.currentServices = []
		self.feedListOffset = len(self.serviceList)
		self.lastSignature = None
		self.stablePolls = 0
		self.feedStarted = monotonic()
		self["pass"].setText(_("Pass %d/%d") % (self.feedIndex + 1, len(self.feeds)))
		self["network"].setText(feed["name"])
		source = "%s:%d" % (feed["address"], feed["port"]) if feed["decoder"] == "fedi2eti" else feed["transport"]
		self["transponder"].setText(_("%s - PID 0x%04X - %s") % (feed["satellite"], feed["pid"], source))
		self.setScanState(_("Scanning DAB+ feed; waiting for live FIC data..."))
		self.updateProgress(0)
		seed = self.buildReference(feed, 0, feed["name"])
		print(f"[DABScan] Starting feed '{feed['name']}' with reference '{seed.toString()}'.")
		if self.session.nav.playService(seed, checkParentalControl=False, adjust=False):
			self.feedFailed(_("Unable to start the DAB+ feed"))
			return
		self.pollTimer.start(self.POLL_INTERVAL, False)

	def pollScan(self):
		if self.scanFinished or self.state != self.RUNNING:
			self.pollTimer.stop()
			return
		elapsed = int((monotonic() - self.feedStarted) * 1000)
		self.updateProgress(min(elapsed, self.FEED_TIMEOUT))
		raw = ""
		service = self.session.nav.getCurrentService()
		if service:
			info = service.info()
			if info:
				raw = info.getInfoString(iServiceInformation.sDABServiceList) or ""
		services = self.parseServiceList(raw)
		if services:
			signature = tuple((item["sid"], item["bitrate"], item["dabplus"], item["label"]) for item in services)
			if signature == self.lastSignature:
				self.stablePolls += 1
			else:
				self.lastSignature = signature
				self.stablePolls = 1
				self.currentServices = services
				self.showCurrentServices()
			self.setScanState(_("Scanning: %d services found; validating live result (%d/%d)...") % (self.foundServices, self.stablePolls, self.STABLE_POLLS))
			if self.stablePolls >= self.STABLE_POLLS:
				self.feedComplete()
				return
		else:
			self.lastSignature = None
			self.stablePolls = 0
		if elapsed >= self.FEED_TIMEOUT:
			self.feedFailed(_("Timeout waiting for FIC service data"))

	def parseServiceList(self, raw):
		services = []
		for line in raw.splitlines():
			fields = line.split("\t", 3)
			if len(fields) != 4:
				continue
			try:
				sid = int(fields[0], 16)
				bitrate = int(fields[1])
				dabplus = bool(int(fields[2]))
			except ValueError:
				continue
			label = self.cleanLabel(fields[3])
			if sid and label:
				services.append({"sid": sid, "bitrate": bitrate, "dabplus": dabplus, "label": label})
		return services

	def cleanLabel(self, label):
		return " ".join(label.replace("\r", " ").replace("\n", " ").split())[:63]

	def showCurrentServices(self):
		feed = self.feeds[self.feedIndex]
		del self.serviceList[self.feedListOffset:]
		for service in self.currentServices:
			reference = self.buildReference(feed, service["sid"], service["label"])
			codec = "DAB+" if service["dabplus"] else "DAB"
			name = f"{service['label']}  ({codec}, {service['bitrate']} kbit/s)"
			self.serviceList.append((name, reference.toString()))
		self.foundServices = self.committedServices + len(self.currentServices)
		self["servicelist"].setList(self.serviceList)
		self["servicelist"].goBottom()
		if self.currentServices:
			for callback in self.onServiceChanged:
				callback(self.currentServices[-1]["label"])

	def feedComplete(self):
		self.pollTimer.stop()
		feed = self.feeds[self.feedIndex]
		if self.writeBouquet(feed, self.currentServices):
			count = len(self.currentServices)
			self.committedServices += count
			self.foundServices = self.committedServices
			print(f"[DABScan] Wrote {count} services to '{feed['bouquetFile']}'.")
		else:
			self.failures.append(_("%s: bouquet could not be written") % feed["name"])
			del self.serviceList[self.feedListOffset:]
			self["servicelist"].setList(self.serviceList)
			self.foundServices = self.committedServices
		self.feedIndex += 1
		self.startFeed()

	def feedFailed(self, reason):
		self.pollTimer.stop()
		feed = self.feeds[self.feedIndex]
		message = f"{feed['name']}: {reason}"
		self.failures.append(message)
		del self.serviceList[self.feedListOffset:]
		self["servicelist"].setList(self.serviceList)
		self.foundServices = self.committedServices
		print(f"[DABScan] {message}; keeping the existing bouquet.")
		self.feedIndex += 1
		self.startFeed()

	def buildReference(self, feed, sid, name):
		target = "%s%%3a%d" % (feed["address"], feed["port"]) if feed["decoder"] == "fedi2eti" else feed["decoder"]
		text = "4115:0:%X:%X:%X:%X:%X:%X:%X:%X:dab%%3a//%s" % (
			feed["parentServiceType"], feed["parentSid"], feed["tsid"], feed["onid"],
			feed["namespace"], feed["pid"], sid, feed["ensembleId"], target)
		reference = eServiceReference(text)
		reference.setName(name)
		return reference

	def writeBouquet(self, feed, services):
		bouquetPath = resolveFilename(SCOPE_CONFIG, feed["bouquetFile"])
		lines = [f"#NAME {feed['bouquetName']}"]
		for service in services:
			reference = self.buildReference(feed, service["sid"], service["label"])
			lines.append(f"#SERVICE {reference.toString()}")
			lines.append(f"#DESCRIPTION {service['label']}")
		if not fileWriteLines(bouquetPath, list(lines), source=MODULE_NAME):
			return False

		masterPath = resolveFilename(SCOPE_CONFIG, "bouquets.radio")
		masterLines = fileReadLines(masterPath, default=[], source=MODULE_NAME) or []
		if not any(feed["bouquetFile"] in line for line in masterLines):
			masterLines.append(''.join((
				'#SERVICE 1:7:2:0:0:0:0:0:0:0:FROM BOUQUET "',
				feed["bouquetFile"], '" ORDER BY bouquet')))
			if not fileWriteLines(masterPath, list(masterLines), source=MODULE_NAME):
				return False
		return True

	def updateProgress(self, elapsed):
		total = len(self.feeds)
		if not total:
			return
		feedProgress = min(float(elapsed) / self.FEED_TIMEOUT, 0.95)
		progress = int(100 * (self.feedIndex + feedProgress) / total)
		self["scan_progress"].setValue(progress)
		for callback in self.onProgressChanged:
			callback(progress)

	def setScanState(self, text):
		self["scan_state"].setText(text)
		for callback in self.onStateChanged:
			callback(text)

	def finishScan(self):
		self.pollTimer.stop()
		self.scanFinished = True
		eDVBDB.getInstance().reloadBouquets()
		self.restoreService()
		self["scan_progress"].setValue(100)
		self["pass"].setText("")
		self["network"].setText(_("DAB+ Scan"))
		if self.failures:
			self["transponder"].setText(_("%d of %d feeds completed; failed feed bouquets were kept") % (len(self.feeds) - len(self.failures), len(self.feeds)))
		else:
			self["transponder"].setText(_("%d radio bouquets created") % len(self.feeds))
		if self.foundServices:
			self.state = self.DONE
			self.setScanState(_("Scanning completed, %d DAB+ services found.") % self.foundServices)
			self["servicelist"].setCurrentIndex(0)
			self["servicelist"].selectionEnabled(True)
			self["key_green"].setText(_("Select"))
			self["doneActions"].setEnabled(True)
		else:
			self.state = self.ERROR
			self.setScanState(_("DAB+ scan failed; existing bouquets were kept."))
		self["key_red"].setText(_("Close"))

	def finishWithError(self, message):
		self.scanFinished = True
		self.state = self.ERROR
		self.restoreService()
		self["pass"].setText("")
		self["network"].setText(_("DAB+ Scan"))
		self["transponder"].setText("")
		self.setScanState(message)
		self["key_red"].setText(_("Close"))

	def keySave(self):
		selected = self["servicelist"].getCurrent()
		if selected:
			self.session.nav.playService(eServiceReference(selected[1]), checkParentalControl=False, adjust=False)
		self.close(True)

	def keyCancel(self):
		self.pollTimer.stop()
		self.restoreService()
		self.close(False)

	def keyCloseRecursive(self):
		self.pollTimer.stop()
		self.restoreService()
		self.close(True)

	def restoreService(self):
		if self.serviceRestored:
			return
		self.serviceRestored = True
		if self.previousService:
			self.session.nav.playService(self.previousService, checkParentalControl=False, adjust=False)
		else:
			self.session.nav.stopService()

	def cleanup(self):
		self.pollTimer.stop()
		self.restoreService()
