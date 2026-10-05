from json import load
from os import W_OK, access, listdir, major, makedirs, minor, mkdir, remove, sep, stat, statvfs, unlink, walk
from os.path import basename, dirname, exists, isdir, isfile, islink, ismount, join, getsize, realpath
from queue import Empty, Queue
from shutil import rmtree
from threading import BoundedSemaphore, Event, Thread
from time import monotonic, time
from urllib.request import Request, urlopen
from zipfile import ZipFile

from enigma import eEPGCache, eTimer, fbClass

from Components.ActionMap import HelpableActionMap
from Components.ChoiceList import ChoiceEntryComponent, ChoiceList
from Components.config import config
from Components.Console import Console
from Components.Label import Label
from Components.ProgressBar import ProgressBar
from Components.SystemInfo import BoxInfo, getBoxDisplayName
from Components.Sources.StaticText import StaticText
from Screens.BackupRestore import BackupScreen
from Screens.MessageBox import MessageBox
from Screens.MultiBootManager import MultiBootManager
from Screens.Screen import Screen
from Tools.Downloader import DownloadWithProgress, USER_AGENTS
from Tools.MultiBoot import MultiBoot

UMOUNT = "/bin/umount"
OFGWRITE = "/usr/bin/ofgwrite"

FEED_DISTRIBUTION = 0
FEED_JSON_URL = 1

USER_AGENT = {"User-Agent": USER_AGENTS.CHROME}


def checkImageFiles(files):
	return sum(f.endswith((".nfi", ".tar.xz")) for f in files) == 1 or sum(("kernel" in f and f.endswith(".bin")) or f in {"zImage", "uImage", "root_cfe_auto.bin", "root_cfe_auto.jffs2", "oe_kernel.bin", "oe_rootfs.bin", "e2jffs2.img", "rootfs.ubi", "rootfs.bin", "rootfs.tar.bz2", "rootfs-one.tar.bz2", "rootfs-two.tar.bz2"} for f in files) >= 2


def isSmallBoxBootstrapImage(image):
	# This archive only boots the mandatory native setup from a USB stick.  A
	# running SmallBox image must use the full companion Multiboot archive.
	return BoxInfo.getItem("SmallBoxWizard") and str(image).split("?", 1)[0].lower().endswith("_usb.zip")


def isNewNativeAdditionalSlot(slotCode, slotData):
	if not slotCode or not slotCode.isdecimal() or BoxInfo.getItem("HasKexecMultiboot") or BoxInfo.getItem("HasGPT") or BoxInfo.getItem("HasChkrootMultiboot") or BoxInfo.getItem("hasUBIMB"):
		return False
	cmdLines = slotData.get("cmdline", {})
	cmdLines = cmdLines.values() if isinstance(cmdLines, dict) else (cmdLines,)
	return any("extra=true" in cmdLine for cmdLine in cmdLines if cmdLine)


class LocalImageScan:
	# A stuck network mount must neither block E2 nor create unlimited workers.
	workerSlots = BoundedSemaphore(2)
	TIMEOUT = 30

	def __init__(self, modelNames, hasMMC, smallBox, backups):
		self.modelNames = tuple(name for name in modelNames if name)
		self.hasMMC = hasMMC
		self.smallBox = smallBox
		self.backups = backups
		self.cancelled = Event()
		self.results = Queue()
		self.deadline = monotonic() + self.TIMEOUT
		self.images = {}
		self.errors = False

	def stopped(self):
		return self.cancelled.is_set() or monotonic() >= self.deadline

	def start(self):
		if not self.workerSlots.acquire(blocking=False):
			return False
		try:
			Thread(target=self.run, name="FlashManagerLocalImages", daemon=True).start()
		except Exception as err:
			self.workerSlots.release()
			print(f"[FlashManager] Unable to start local image search: {err}")
			return False
		return True

	def readDirectory(self, path):
		if self.stopped():
			return []
		try:
			return listdir(path)
		except FileNotFoundError:
			return []  # A device may have been removed while scanning.
		except OSError as err:
			self.errors = True
			print(f"[FlashManager] Unable to search '{path}': {err}")
			return []

	def scanDirectory(self, path, names):
		for name in names:
			if self.stopped():
				return
			if name.startswith(".") or not name.lower().endswith(".zip") or not any(model in name for model in self.modelNames):
				continue
			if ("backup" in name.lower()) != self.backups or (self.smallBox and name.lower().endswith("_usb.zip")):
				continue
			image = join(path, name)
			try:
				if not isfile(image) or self.stopped():
					continue
				with ZipFile(image, mode="r") as archive:
					files = archive.namelist()
				if not self.stopped() and checkImageFiles([entry.rsplit("/", 1)[-1] for entry in files]):
					self.images[image] = {"link": image, "name": name}
			except Exception as err:
				print(f"[FlashManager] Unable to read image archive '{image}': {err}")

	def scanMedia(self, media):
		if self.stopped() or (self.hasMMC and "/mmc" in media) or not isdir(media):
			return
		names = self.readDirectory(media)
		self.scanDirectory(media, names)
		for folder in ("images", "downloaded_images", "imagebackups"):
			if self.stopped():
				return
			if folder in names:
				path = join(media, folder)
				if not islink(path) and not ismount(path) and isdir(path):
					self.scanDirectory(path, self.readDirectory(path))

	def run(self):
		try:
			for name in self.readDirectory("/media"):
				if self.stopped():
					return
				self.scanMedia(join("/media", name))
			for name in self.readDirectory("/media/net"):
				if self.stopped():
					return
				self.scanMedia(join("/media/net", name))
		except Exception as err:
			self.errors = True
			print(f"[FlashManager] Local image search failed: {err}")
		finally:
			if not self.stopped():
				self.results.put((self.images, self.errors))
			self.workerSlots.release()


class FlashManager(Screen):
	skin = """
	<screen name="FlashManager" title="Flash Manager" position="center,center" size="900,485" resolution="1280,720">
		<widget name="list" position="0,0" size="e,400" scrollbarMode="showOnDemand" />
		<widget source="description" render="Label" position="10,e-75" size="e-20,25" font="Regular;20" conditional="description" halign="center" transparent="1" valign="center" />
		<widget source="key_red" render="Label" position="0,e-40" size="180,40" backgroundColor="key_red" conditional="key_red" font="Regular;20" foregroundColor="key_text" halign="center" valign="center">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="key_green" render="Label" position="190,e-40" size="180,40" backgroundColor="key_green" conditional="key_green" font="Regular;20" foregroundColor="key_text" halign="center" valign="center">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="key_yellow" render="Label" position="380,e-40" size="180,40" backgroundColor="key_yellow" conditional="key_yellow" font="Regular;20" foregroundColor="key_text" halign="center" valign="center">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="key_blue" render="Label" position="570,e-40" size="180,40" backgroundColor="key_blue" conditional="key_blue" font="Regular;20" foregroundColor="key_text" halign="center" valign="center">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="key_help" render="Label" position="e-80,e-40" size="80,40" backgroundColor="key_back" conditional="key_help" font="Regular;20" foregroundColor="key_text" halign="center" valign="center">
			<convert type="ConditionalShowHide" />
		</widget>
	</screen>"""

	def __init__(self, session):
		Screen.__init__(self, session, enableHelp=True)
		self.skinName = ["FlashManager", "FlashOnline"]
		self.imageFeed = "OpenATV"
		self.setTitle(_("Flash Manager - %s Images") % self.imageFeed)
		self.imagesList = {}
		self.imagesListLoaded = False
		self.localImageTypes = {_("Downloaded images"): False, _("Backup images"): True}
		self.localImages = {}
		self.localImageErrors = {}
		self.localScan = None
		self.localScanCategory = None
		self.localScanTimer = eTimer()
		self.localScanTimer.callback.append(self.pollLocalImages)
		self.onClose.append(self.stopLocalScan)
		self.expanded = []
		self.setIndex = None
		self["actions"] = HelpableActionMap(self, ["OkCancelActions", "ColorActions", "NavigationActions"], {
			"cancel": (self.keyCancel, _("Cancel the image selection and exit")),
			"close": (self.keyCloseRecursive, _("Cancel the image selection and exit all menus")),
			"ok": (self.keyOk, _("Select the highlighted image and proceed to the slot selection")),
			"red": (self.keyCancel, _("Cancel the image selection and exit")),
			"green": (self.keyOk, _("Select the highlighted image and proceed to the slot selection")),
			"yellow": (self.keyDistribution, _("Select a distribution from where images are to be obtained")),
			"top": (self.keyTop, _("Move to first line / screen")),
			"pageUp": (self.keyPageUp, _("Move up a screen")),
			"up": (self.keyUp, _("Move up a line")),
			"down": (self.keyDown, _("Move down a line")),
			"pageDown": (self.keyPageDown, _("Move down a screen")),
			"bottom": (self.keyBottom, _("Move to last line / screen"))
		}, prio=-1, description=_("Flash Manager Actions"))
		self["deleteActions"] = HelpableActionMap(self, ["ColorActions"], {
			"blue": (self.keyDeleteImage, _("Delete the selected locally stored image")),
		}, prio=-1, description=_("Flash Manager Actions"))
		self["deleteActions"].setEnabled(False)
		self["downloadActions"] = HelpableActionMap(self, ["ColorActions"], {
			"blue": (self.keyDownloadImage, _("Download the selected image")),
		}, prio=-1, description=_("Flash Manager Actions"))
		self["downloadActions"].setEnabled(False)

		self["key_red"] = StaticText(_("Cancel"))
		self["key_green"] = StaticText()
		self["key_yellow"] = StaticText(_("Distribution"))
		self["key_blue"] = StaticText()
		self["description"] = StaticText()
		self["list"] = ChoiceList(list=[ChoiceEntryComponent("", ((_("Retrieving image list, please wait...")), "Loading"))])
		self.feedUrls = [
			("OpenATV", "https://images.mynonpublic.com/openatv/json/%s" % BoxInfo.getItem("BoxName"))
		]
		self.callLater(self.getImagesList)

	def getImagesList(self):
		if not self.imagesListLoaded:
			feedURL = next((feed[FEED_JSON_URL] for feed in self.feedUrls if feed[FEED_DISTRIBUTION] == self.imageFeed), self.feedUrls[0][FEED_JSON_URL])
			try:
				req = Request(feedURL, None, USER_AGENT)
				with urlopen(req, timeout=10) as response:
					self.imagesList = dict(load(response))
				if BoxInfo.getItem("SmallBoxWizard"):
					self.imagesList = {
						category: {
							image: data for image, data in images.items()
							if not isSmallBoxBootstrapImage(data.get("name", image))
						} for category, images in self.imagesList.items()
					}
					self.imagesList = {category: images for category, images in self.imagesList.items() if images}
			except Exception:
				print("[FlashManager] getImagesList Error: Unable to load json data from URL '%s'!" % feedURL)
				self.imagesList = {}
			self.imagesListLoaded = True
		self.startLocalImages()
		self.updateImagesList()

	def startLocalImages(self):
		if self.localScan is not None or self.imageFeed != "OpenATV":
			return
		for category in self.expanded:
			if category in self.localImageTypes and category not in self.localImages:
				scan = LocalImageScan(
					[BoxInfo.getItem(key) for key in ("BoxName", "machinebuild", "model")],
					BoxInfo.getItem("HasMMC"), BoxInfo.getItem("SmallBoxWizard"), self.localImageTypes[category])
				if scan.start():
					self.localScan = scan
					self.localScanCategory = category
					self.localScanTimer.start(250)
					return
				self.localImages[category] = {}
				self.localImageErrors[category] = _("Unable to start the local image search. Please try again later.")
				self.session.showError(self.localImageErrors[category])

	def stopLocalScan(self):
		self.localScanTimer.stop()
		if self.localScan is not None:
			self.localScan.cancelled.set()
		self.localScan = None
		self.localScanCategory = None

	def pollLocalImages(self):
		scan = self.localScan
		if scan is None:
			return
		try:
			images, errors = scan.results.get_nowait()
			message = _("Some image locations could not be read. Check your storage devices.") if errors else None
		except Empty:
			if monotonic() < scan.deadline:
				return
			images = {}
			message = _("The local image search timed out. Check your storage devices.")
		category = self.localScanCategory
		self.stopLocalScan()
		self.localImages[category] = images
		if message:
			self.localImageErrors[category] = message
			self.session.showError(message)
		self.startLocalImages()
		self.updateImagesList()

	def reloadImagesList(self, recursive=False):
		if recursive:
			self.close(True)
			return
		self.stopLocalScan()
		self.imagesList = {}
		self.imagesListLoaded = False
		self.localImages.clear()
		self.localImageErrors.clear()
		self.getImagesList()

	def updateImagesList(self):
		current = self["list"].getCurrent()
		selected = current[0] if current else None
		index = self["list"].getSelectedIndex() or 0
		categories = dict(self.imagesList)
		if self.imageFeed == "OpenATV":
			categories.update({category: self.localImages.get(category, {}) for category in self.localImageTypes})
		imageList = []
		for category in sorted(categories, reverse=True):
			images = categories[category]
			local = self.imageFeed == "OpenATV" and category in self.localImageTypes
			if not images and not local:
				continue
			if category in self.expanded:
				imageList.append(ChoiceEntryComponent("expanded", (category, "Expanded")))
				for image in sorted(images, key=lambda image: basename(image), reverse=True):
					imageList.append(ChoiceEntryComponent("verticalline", (images[image]["name"], images[image]["link"])))
				if local:
					message = self.localImageErrors.get(category)
					if category not in self.localImages:
						message = _("Searching for local images, please wait...")
					elif not images and not message:
						message = _("No local images found.")
					if message:
						imageList.append(ChoiceEntryComponent("verticalline", (message, "Loading")))
			else:
				imageList.append(ChoiceEntryComponent("expandable", (category, "Expanded")))
		if not imageList:
			# Preserve the fallback for distributions without matching images.
			self.session.showError(_("Error: Cannot find any images!"))
			self.keyDistributionCallback("OpenATV")
			return
		self["list"].setList(imageList)
		if self.setIndex is not None:
			index = self.setIndex
			self.setIndex = None
		else:
			index = next((position for position, entry in enumerate(imageList) if entry[0] == selected), index)
		self["list"].moveToIndex(max(0, min(index, len(imageList) - 1)))
		self.selectionChanged()

	def keyCancel(self):
		self.close()

	def keyCloseRecursive(self):
		self.close(True)

	def keyOk(self):
		currentSelection = self["list"].getCurrent()
		if not currentSelection:
			return
		if currentSelection[0][1] == "Expanded":
			category = currentSelection[0][0]
			if category in self.expanded:
				self.expanded.remove(category)
				if category == self.localScanCategory:
					self.stopLocalScan()
			else:
				self.expanded.append(category)
				# Explicitly reopening a local category also refreshes removable media.
				self.localImages.pop(category, None)
				self.localImageErrors.pop(category, None)
			self.getImagesList()
		elif currentSelection[0][1] != "Loading":
			self.stopLocalScan()
			self.session.openWithCallback(self.reloadImagesList, FlashImage, currentSelection[0][0], currentSelection[0][1])

	def keyTop(self):
		self["list"].instance.goTop()
		self.selectionChanged()

	def keyPageUp(self):
		self["list"].instance.goPageUp()
		self.selectionChanged()

	def keyUp(self):
		self["list"].instance.goLineUp()
		self.selectionChanged()

	def keyDown(self):
		self["list"].instance.goLineDown()
		self.selectionChanged()

	def keyPageDown(self):
		self["list"].instance.goPageDown()
		self.selectionChanged()

	def keyBottom(self):
		self["list"].instance.goBottom()
		self.selectionChanged()

	def keyDistribution(self):
		self.feedUrls = [["OpenATV", "https://images.mynonpublic.com/openatv/json/%s" % BoxInfo.getItem("BoxName")]]
		distributionList = []
		default = 0
		machine = BoxInfo.getItem("machinebuild")
		try:
			req = Request("https://raw.githubusercontent.com/OpenATV/FlashImage/gh-pages/%s.json" % machine, None, USER_AGENT)
			responseList = load(urlopen(req, timeout=5))
			self.feedUrls = self.feedUrls + responseList
		except Exception as err:
			print("[FlashManager] Error: getavailable Distribution List for '%s'! (%s)" % (machine, err))
		for index, distribution in enumerate([feed[FEED_DISTRIBUTION] for feed in self.feedUrls]):
			distributionList.append((distribution, distribution))
			if distribution == self.imageFeed:
				default = index
		self.session.openWithCallback(self.keyDistributionCallback, MessageBox, _("Please select a distribution from which you would like to flash an image:"), list=distributionList, default=default, windowTitle=_("Flash Manager - Distributions"))

	def keyDistributionCallback(self, distribution):
		if distribution:
			self.stopLocalScan()
			self.imageFeed = distribution
			# TRANSLATORS: The variable is the name of a distribution.  E.g. "OpenATV".
			self.setTitle(_("Flash Manager - %s Images") % self.imageFeed)
			self.expanded = []
			self.setIndex = 0
			self.reloadImagesList()

	def keyDeleteImage(self):
		selection = self["list"].getCurrent()
		if not selection or selection[0][1] in ("Loading", "Expanded") or "://" in selection[0][1]:
			return
		currentSelectionImage, imagePath = selection[0]

		def keyDeleteImageCallback(result):
			if result:
				try:
					unlink(imagePath)
					unpacked = f"{imagePath[:-4]}.unzipped"
					if isdir(unpacked) and not islink(unpacked) and not ismount(unpacked):
						rmtree(unpacked)
					self.setIndex = self["list"].getSelectedIndex()
					self.reloadImagesList()
				except OSError as err:
					self.session.showError(_("Error %d: Unable to delete downloaded image '%s'!  (%s)") % (err.errno, imagePath, err.strerror))

		self.session.openWithCallback(keyDeleteImageCallback, MessageBox, _("Do you really want to delete '%s'?") % currentSelectionImage, MessageBox.TYPE_YESNO, default=False)

	def keyDownloadImage(self):
		currentSelection = self["list"].getCurrent()
		if currentSelection and "://" in currentSelection[0][1]:
			self.stopLocalScan()
			self.session.openWithCallback(self.reloadImagesList, FlashImage, currentSelection[0][0], currentSelection[0][1], True)

	def selectionChanged(self):
		selection = self["list"].getCurrent()
		currentSelection = selection[0] if selection else ("", "Loading")
		canDownload = False
		canDelete = False
		if currentSelection[1] == "Loading":
			self["key_green"].setText("")
			self["description"].setText("")
		else:
			if currentSelection[1] == "Expanded":
				self["key_green"].setText(_("Collapse") if currentSelection[0] in self.expanded else _("Expand"))
				self["description"].setText("")
			else:
				self["key_green"].setText(_("Flash Image"))
				self["description"].setText(_("Location: %s") % currentSelection[1][:currentSelection[1].rfind(sep) + 1])
				canDownload = "://" in currentSelection[1]
				canDelete = not canDownload
		if canDownload:
			self["key_blue"].setText(_("Download Image"))
		elif canDelete:
			self["key_blue"].setText(_("Delete Image"))
		else:
			self["key_blue"].setText("")
		self["downloadActions"].setEnabled(canDownload)
		self["deleteActions"].setEnabled(canDelete)


class FlashImage(Screen):
	skin = """
	<screen name="FlashImage" title="Flash Image" position="center,center" size="720,225" resolution="1280,720">
		<widget name="header" position="0,0" size="e,50" font="Regular;35" valign="center" />
		<widget name="info" position="0,60" size="e,130" font="Regular;25" valign="center" />
		<widget name="progress" position="0,e-25" size="e,25" />
	</screen>"""

	def __init__(self, session, imageName, source, downloadOnly=False):
		Screen.__init__(self, session, enableHelp=True)
		self.imageName = imageName
		self.source = source
		self.setTitle(_("Flash Image"))
		self.containerBackup = None
		self.containerOFGWrite = None
		self.getImageList = None
		self.downloader = None
		self.downloadOnly = downloadOnly
		self["header"] = Label(_("Backup Settings"))
		self["info"] = Label(_("Save settings and EPG data."))
		self["summary_header"] = StaticText(self["header"].getText())
		self["progress"] = ProgressBar()
		self["progress"].setRange((0, 100))
		self["progress"].setValue(0)
		self["actions"] = HelpableActionMap(self, ["OkCancelActions"], {
			"cancel": (self.keyCancel, _("Cancel the flash process")),
			"close": (self.keyCloseRecursive, _("Cancel the flash process and exit all menus")),
			"ok": (self.keyOK, _("Continue with the flash process"))
		}, prio=-1, description=_("Image Flash Actions"))
		self.hide()
		self.callLater(self.confirmation)
		self.backupBasePath = config.plugins.configurationbackup.backuplocation.value if not exists("/media/hdd/") else "/media/hdd/"

	def keyCancel(self, reply=None):
		if self.containerOFGWrite or self.getImageList:
			return 0
		if self.downloader:
			self.downloader.stop()
		self.close()

	def keyCloseRecursive(self):
		self.close(True)

	def keyOK(self):
		fbClass.getInstance().unlock()
		if self["header"].text == _("Flashing image successful"):
			if MultiBoot.canMultiBoot():
				self.session.openWithCallback(self.keyCancel, MultiBootManager)
			else:
				self.close()
		else:
			return 0

	def confirmation(self):
		if MultiBoot.canMultiBoot() and not self.downloadOnly:
			self.getImageList = MultiBoot.getSlotImageList(self.getImageListCallback)
		else:
			self.checkMedia(True)

	def getImageListCallback(self, imageDictionary):
		self.getImageList = None
		currentSlotCode = MultiBoot.getCurrentSlotCode()
		print("[FlashManager] Current image slot is '%s'." % currentSlotCode)
		choices = []
		default = 0
		currentMsg = "  -  %s" % _("Current")
		slotMsg = _("Slot '%s' %s: %s%s")
		for index, slotCode in enumerate(sorted(imageDictionary.keys(), key=lambda x: (not x.isnumeric(), int(x) if x.isnumeric() else x))):
			print("[FlashManager] Image Slot '%s': %s." % (slotCode, str(imageDictionary[slotCode])))
			slotType = "eMMC" if "mmcblk" in imageDictionary[slotCode]["device"] else "USB"
			current = ""
			if slotCode == currentSlotCode:
				current = currentMsg
				default = index
			choices.append((slotMsg % (slotCode, slotType, imageDictionary[slotCode]["imagename"], current), (slotCode, True)))
		choices.append((_("No, don't flash this image"), False))
		self.session.openWithCallback(self.checkMedia, MessageBox, _("Do you want to flash the image '%s'?") % self.imageName, list=choices, default=default, windowTitle=self.getTitle())

	def checkMedia(self, choice):
		if choice:
			self.recordCheck = not MultiBoot.canMultiBoot() or (MultiBoot.getCurrentSlotCode() == choice[0] if isinstance(choice, (tuple, list)) else True)  # Ignore recordCheck if not the current slot

			def findMedia(paths):
				def availableSpace(path):
					if isdir(path) and access(path, W_OK):
						try:
							fs = statvfs(path)
							return (fs.f_bavail * fs.f_frsize) / (1 << 20)
						except OSError as err:
							print("[FlashManager] checkMedia Error %d: Unable to get status for '%s'!  (%s)" % (err.errno, path, err.strerror))
					return 0

				def checkIfDevice(path, diskStats):
					deviceID = stat(path).st_dev
					return (major(deviceID), minor(deviceID)) in diskStats

				diskStats = [(int(x[0]), int(x[1])) for x in [x.split()[0:3] for x in open("/proc/diskstats").readlines()] if x[2].startswith("sd") or x[2].startswith("mmc")]
				for path in paths:
					if isdir(path) and checkIfDevice(path, diskStats) and availableSpace(path) > 500:
						return (path, True)
				devices = []
				mounts = []
				for path in ["/media/%s" % x for x in listdir("/media")] + (["/media/net/%s" % x for x in listdir("/media/net")] if isdir("/media/net") else []):
					if checkIfDevice(path, diskStats):
						devices.append((path, availableSpace(path)))
					else:
						mounts.append((path, availableSpace(path)))
				devices.sort(key=lambda x: x[1], reverse=True)
				mounts.sort(key=lambda x: x[1], reverse=True)
				return ((devices[0][1] > 500 and (devices[0][0], True)) if devices else mounts and mounts[0][1] > 500 and (mounts[0][0], False)) or (None, None)

			if "backup" not in str(choice) and not self.downloadOnly:
				if MultiBoot.canMultiBoot():
					self.slotCode = choice[0]
				if BoxInfo.getItem("distro") in self.imageName:
					self.session.openWithCallback(self.backupQuestionCallback, MessageBox, _("Do you want to backup settings?"), default=True, timeout=10, windowTitle=self.getTitle())
				else:
					self.backupQuestionCallback(None)
				return
			destination, isDevice = findMedia(["/media/hdd", "/media/usb"])
			if destination:
				destination = join(destination, "images")
				self.zippedImage = "://" in self.source and join(destination, self.imageName) or self.source
				self.unzippedImage = join(destination, "%s.unzipped" % basename(self.imageName)[:-4])
				try:
					if isfile(destination):
						unlink(destination)
					if not isdir(destination):
						mkdir(destination)
					if self.downloadOnly:
						self.startDownload()
					elif isDevice or "no_backup" == choice:
						self.startBackupSettings(choice)
					else:
						self.session.openWithCallback(self.startBackupSettings, MessageBox, _("Warning: There is only a network drive to store the backup. This means the auto restore will not work after the flash. Alternatively, mount the network drive after the flash and perform a manufacturer reset to auto restore."), windowTitle=self.getTitle())
				except OSError:
					self.session.openWithCallback(self.keyCancel, MessageBox, _("Error: Unable to create the required directories on the target device (e.g. USB stick or hard disk)! Please verify device and try again."), type=MessageBox.TYPE_ERROR, windowTitle=self.getTitle())
			else:
				self.session.openWithCallback(self.keyCancel, MessageBox, _("Error: Could not find a suitable device! Please remove some downloaded images or attach another device (e.g. USB stick) with sufficient free space and try again."), type=MessageBox.TYPE_ERROR, windowTitle=self.getTitle())
		else:
			self.keyCancel()

	def backupQuestionCallback(self, answer):
		self.checkMedia("backup" if answer else "no_backup")

	def startBackupSettings(self, answer):
		if answer:
			if answer == "backup" or answer is True:
				self.session.openWithCallback(self.flashPostAction, BackupScreen, runBackup=True)
			else:
				self.flashPostAction()
		else:
			self.keyCancel()

	def flashPostAction(self, retVal=True):
		if retVal:
			self.recordCheck = False
			text = _("Please select what to do after flash of the following image:")
			text = "%s\n%s" % (text, self.imageName)
			if BoxInfo.getItem("distro") in self.imageName:
				if exists(join(self.backupBasePath, "images/config/myrestore.sh")):
					text = "%s\n%s" % (text, _("(The file '/media/hdd/images/config/myrestore.sh' exists and will be run after the image is flashed.)"))
				choices = [
					(_("Upgrade (Flash & restore all)"), "restoresettingsandallplugins"),
					(_("Clean (Just flash and start clean)"), "wizard"),
					(_("Flash and restore settings and no plugins"), "restoresettingsnoplugin"),
					(_("Flash and restore settings and selected plugins (Ask user)"), "restoresettings"),
					(_("Do not flash image"), "abort")
				]
				default = self.selectPrevPostFlashAction()
				if "backup" in self.imageName:
					choices = [
						(_("Only Flash Backup Image"), "nothing"),
						# (_("Flash & restore all"), "restoresettingsandallplugins"),
						# (_("Flash and restore settings and no plugins"), "restoresettingsnoplugin"),
						# (_("Flash and restore settings and selected plugins (Ask user)"), "restoresettings"),
						(_("Do not flash image"), "abort")
					]
					default = 0
			else:
				choices = [
					(_("Clean (Just flash and start clean)"), "wizard"),
					(_("Do not flash image"), "abort")
				]
				default = 0
			self.session.openWithCallback(self.postFlashActionCallback, MessageBox, text, list=choices, default=default, windowTitle=self.getTitle())
		else:
			self.keyCancel()

	def selectPrevPostFlashAction(self):
		index = 1
		if exists(join(self.backupBasePath, "images/config/settings")):
			index = 3
			if exists(join(self.backupBasePath, "images/config/noplugins")):
				index = 2
			if exists(join(self.backupBasePath, "images/config/plugins")):
				index = 0
		return index

	def postFlashActionCallback(self, choice):
		if choice:
			knownFlagFiles = ("settings", "plugins", "noplugins", "slow", "fast", "turbo")
			for directory in listdir("/media"):  # Remove known flag files from devices other than self.backupBasePath.
				if directory not in ("audiocd", "autofs", basename(self.backupBasePath.rstrip("/"))):
					for flagFile in knownFlagFiles:
						flagPath = join("/media", directory, "images/config", flagFile)
						if isfile(flagPath) and getsize(flagPath) == 0:
							unlink(flagPath)
			rootFolder = join(self.backupBasePath, "images/config")
			if choice != "abort" and self.recordCheck:
				self.recordCheck = False
				recording = self.session.nav.RecordTimer.isRecording()
				nextRecordingTime = self.session.nav.RecordTimer.getNextRecordingTime()
				if recording or (nextRecordingTime > 0 and (nextRecordingTime - time()) < 360):
					self.choice = choice
					self.session.openWithCallback(self.recordWarning, MessageBox, "%s\n\n%s" % (_("Recording(s) are in progress or coming up in few seconds!"), _("Flash your %s %s and reboot now?") % getBoxDisplayName()), default=False, windowTitle=self.getTitle())
					return
			restoreSettings = ("restoresettings" in choice)
			restoreSettingsnoPlugin = (choice == "restoresettingsnoplugin")
			restoreAllPlugins = (choice == "restoresettingsandallplugins")
			if restoreSettings:
				self.saveEPG()
			if choice != "abort":
				filesToCreate = []
				try:
					if not exists(rootFolder):
						makedirs(rootFolder)
				except OSError as err:
					print("[FlashManager] postFlashActionCallback Error %d: Failed to create '%s' folder!  (%s)" % (err.errno, rootFolder, err.strerror))
				if restoreSettings:
					filesToCreate.append("settings")
				if restoreAllPlugins:
					filesToCreate.append("plugins")
				if restoreSettingsnoPlugin:
					filesToCreate.append("noplugins")
				for fileName in ["settings", "plugins", "noplugins"]:
					path = join(rootFolder, fileName)
					if fileName in filesToCreate:
						try:
							open(path, "w").close()
						except OSError as err:
							print("[FlashManager] postFlashActionCallback Error %d: failed to create %s! (%s)" % (err.errno, path, err.strerror))
					else:
						if exists(path):
							unlink(path)
				if restoreSettings:
					if config.plugins.softwaremanager.restoremode.value is not None:
						try:
							for fileName in ["slow", "fast", "turbo"]:
								path = join(rootFolder, fileName)
								if fileName == config.plugins.softwaremanager.restoremode.value:
									if not exists(path):
										open(path, "w").close()
								elif exists(path):
									unlink(path)
						except OSError as err:
							print("[FlashManager] postFlashActionCallback Error %d: Failed to create restore mode flag file '%s'!  (%s)" % (err.errno, path, err.strerror))
				self.startDownload()
			else:
				self.keyCancel()
		else:
			self.keyCancel()

	def recordWarning(self, answer):
		if answer:
			self.postFlashActionCallback(self.choice)
		else:
			self.keyCancel()

	def saveEPG(self):
		epgCache = eEPGCache.getInstance()
		epgCache.save()

	def startDownload(self, reply=True):  # DEBUG: This is never called with an argument!
		self.show()
		if reply:
			if "://" in self.source:
				self["header"].setText(_("Downloading Image"))
				self["info"].setText(self.imageName)
				self["summary_header"].setText(self["header"].getText())
				self.downloader = DownloadWithProgress(self.source.replace(" ", "%20"), self.zippedImage)
				self.downloader.addProgress(self.downloadProgress)
				self.downloader.addEnd(self.downloadEnd)
				self.downloader.addError(self.downloadError)
				self.downloader.start()
			else:
				self.unzip()
		else:
			self.keyCancel()

	def downloadProgress(self, current, total):
		if total > 0:  # total is -1 while the download size is still unknown
			self["progress"].setValue(100 * current // total)
			eta = self.downloader.getEta()
			eta = f" / {eta}s" if eta > 0 else ""
			self["info"].setText(f"{self.imageName}{eta}")

	def downloadEnd(self, filename=None):
		self.downloader.stop()
		if self.downloadOnly:
			self.close()
		else:
			self.unzip()

	def downloadError(self, error):
		self.downloader.stop()
		self.session.openWithCallback(self.keyCancel, MessageBox, "%s\n\n%s" % (_("Error downloading image '%s'!") % self.imageName, error), type=MessageBox.TYPE_ERROR, windowTitle=self.getTitle())

	def unzip(self):
		self["header"].setText(_("Unzipping Image"))
		self["summary_header"].setText(self["header"].getText())
		self["info"].setText("%s\n\n%s" % (self.imageName, _("Please wait")))
		self["progress"].hide()
		self.delay = eTimer()
		self.delay.callback.append(self.startUnzip)
		self.delay.start(0, True)

	def startUnzip(self):
		try:
			with ZipFile(self.zippedImage, mode="r") as zipData:
				# Only clear this image's extraction directory when flashing it,
				# never remove other unpacked images while browsing the list.
				if (islink(self.unzippedImage) or ismount(self.unzippedImage)
						or basename(self.unzippedImage) != "%s.unzipped" % basename(self.imageName)[:-4]
						or dirname(realpath(self.unzippedImage)) != realpath(dirname(self.unzippedImage))):
					raise ValueError("Unsafe image extraction directory")
				if isdir(self.unzippedImage):
					rmtree(self.unzippedImage)
				zipData.extractall(self.unzippedImage)  # NOSONAR
			target = next(
				(join(p, "rootfs.tar.bz2") for p, _, f in walk(self.unzippedImage)
					if "rootfs.ubi" in f and "rootfs.tar.bz2" in f),
				None
			)
			if target and exists(target):
				remove(target)
			self.flashImage()
		except Exception as err:
			print("[FlashManager] startUnzip Error: %s!" % str(err))
			self.session.openWithCallback(self.keyCancel, MessageBox, _("Error unzipping image '%s'!") % self.imageName, type=MessageBox.TYPE_ERROR, windowTitle=self.getTitle())

	def flashImage(self):
		if BoxInfo.getItem("model") in ("dm820", "dm7080") and not hasattr(self, "dreamKernelA"):
			def featuresDone(data, retVal, extraArgs):
				self.dreamKernelA = retVal == 0 and "dream-kernel-a" in data.split()
				self.containerOFGWrite = None
				self.flashImage()
			self.containerOFGWrite = Console()
			self.containerOFGWrite.ePopen(["/usr/bin/ofgwrite_bin", "/usr/bin/ofgwrite_bin", "--features"], callback=featuresDone)
			return

		def findImageFiles(path):
			for path, subDirs, files in walk(path):
				if not subDirs and files:
					return checkImageFiles(files) and path

		self["header"].setText(_("Flashing Image"))
		self["summary_header"].setText(self["header"].getText())
		imageFiles = findImageFiles(self.unzippedImage)
		if imageFiles:
			rootSubDir = None
			bootSlots = MultiBoot.canMultiBoot() and MultiBoot.getBootSlots()
			if bootSlots:
				mtdKernel = bootSlots[self.slotCode]["kernel"] if BoxInfo.getItem("HasKexecMultiboot") else bootSlots[self.slotCode]["kernel"].split(sep)[2]
				mtdRootFS = bootSlots[self.slotCode]["device"] if bootSlots[self.slotCode].get("ubi") else bootSlots[self.slotCode]["device"].split(sep)[2]
				if MultiBoot.hasRootSubdir(self.slotCode):
					rootSubDir = bootSlots[self.slotCode]["rootsubdir"]
					currentSlot = MultiBoot.getCurrentSlotCode()
			else:
				mtdKernel = BoxInfo.getItem("mtdkernel")
				mtdRootFS = BoxInfo.getItem("mtdrootfs")
				if BoxInfo.getItem("model") in ("dreamone", "dreamtwo"):
					try:
						with open("/proc/cmdline") as fd:
							for arg in fd.read().split():
								if arg.startswith("root=/dev/mmcblk1p"):
									mtdRootFS = arg[len("root=/dev/"):]
									break
					except OSError:
						pass
			if BoxInfo.getItem("HasKexecMultiboot"):
				if self.slotCode == "R":
					cmdArgs = ["-r", "-k", "-f"]
					Console().ePopen([UMOUNT, UMOUNT, "/proc/cmdline"])
				else:
					cmdArgs = ["-r%s" % mtdRootFS, "-k", "-m%s" % self.slotCode]
					if "uuid" in bootSlots[self.slotCode] and "mmcblk" not in mtdRootFS:
						cmdArgs.insert(2, "-s%s/linuxrootfs" % BoxInfo.getItem("model")[2:])
			elif BoxInfo.getItem("model") in ("dreamone", "dreamtwo") and not BoxInfo.getItem("HasGPT"):  # Temp solution ofgwrite auto detection not ready.
				cmdArgs = ["-r%s" % mtdRootFS, "-k%s" % mtdKernel]
			elif BoxInfo.getItem("model") in ("dreamone", "dreamtwo") and BoxInfo.getItem("HasGPT"):  # Temp solution ofgwrite auto detection not ready.
				cmdArgs = ["-r%s" % mtdRootFS, "-a"]
			elif BoxInfo.getItem("model") in ("dm820", "dm7080"):
				if rootSubDir is None:
					cmdArgs = ["-r"] if self.dreamKernelA else ["-rmmcblk0p1"]
				else:
					cmdArgs = ["-r%s" % mtdRootFS, "-c%s" % currentSlot, "-m%s" % self.slotCode]
				# Chkroot guests keep sharing A. Update it with the main internal image.
				if self.dreamKernelA and (rootSubDir is None or (mtdRootFS == "mmcblk0p1" and rootSubDir == "linuxrootfs1")):
					cmdArgs.append("-k")
			elif MultiBoot.canMultiBoot() and self.slotCode not in ("R", "F"):  # Receiver with SD card MultiBoot if (rootSubDir) is None.
				newNativeAdditionalSlot = isNewNativeAdditionalSlot(self.slotCode, bootSlots[self.slotCode])
				if BoxInfo.getItem("chkrootmb") or newNativeAdditionalSlot:
					if newNativeAdditionalSlot:
						print("[FlashManager] Preserving the shared NewMB slot 1 kernel while flashing additional slot '%s'." % self.slotCode)
					cmdArgs = ["-r%s" % mtdRootFS, "-c%s" % currentSlot, "-m%s" % self.slotCode]
				else:
					cmdArgs = ["-r%s" % mtdRootFS, "-k%s" % mtdKernel, "-m0"] if (rootSubDir) is None else ["-r", "-k", "-m%s" % self.slotCode]
			elif BoxInfo.getItem("model") in ("dm800se", "dm500hd"):  # Temp solution ofgwrite auto detection not ready.
				cmdArgs = ["-r%s" % mtdRootFS, "-f"]
			elif BoxInfo.getItem("model") in ("zgemmah82h",):  # Temp solution ofgwrite kill e2 not allways works.
				cmdArgs = ["-r", "-k", "-f"]
			elif mtdKernel == mtdRootFS:  # Receiver with kernel and rootfs on one partition.
				cmdArgs = ["-r"]
			else:  # Normal non MultiBoot receiver.
				cmdArgs = ["-r", "-k"]
			self.containerOFGWrite = Console()
			self.containerOFGWrite.ePopen([OFGWRITE, OFGWRITE] + cmdArgs + ['%s' % imageFiles], callback=self.flashImageDone)
			fbClass.getInstance().lock()
		else:
			self.session.openWithCallback(self.keyCancel, MessageBox, _("Error: Image '%s' to install is invalid!") % self.imageName, type=MessageBox.TYPE_ERROR, windowTitle=self.getTitle())

	def flashImageDone(self, data, retVal, extraArgs):
		fbClass.getInstance().unlock()
		self.containerOFGWrite = None
		if retVal == 0:
			slotCode = getattr(self, "slotCode", None)
			if slotCode and BoxInfo.getItem("model") in ("dreamone", "dreamtwo") and BoxInfo.getItem("HasGPT"):
				MultiBoot.updateDreamBootSection(slotCode)
			self["header"].setText(_("Flashing image successful"))
			self["summary_header"].setText(self["header"].getText())
			self["info"].setText("%s\n\n%s\n%s" % (self.imageName, _("Press OK for MultiBoot selection."), _("Press EXIT to close.")))
		else:
			self.session.openWithCallback(self.keyCancel, MessageBox, _("Flashing image '%s' was not successful!") % self.imageName, type=MessageBox.TYPE_ERROR, windowTitle=self.getTitle())
