from datetime import datetime
from glob import glob
from json import loads
from locale import format_string
from os import listdir, remove, statvfs
from os.path import basename, getmtime, isdir, isfile, join as pathjoin
from select import select
from six import PY2
from ssl import _create_unverified_context  # For python 2.7.11 we need to bypass the certificate check
from subprocess import PIPE, Popen
from time import localtime, strftime, strptime
try:
	from urllib2 import urlopen
except ImportError:
	from urllib.request import urlopen

from enigma import eConsoleAppContainer, eDVBResourceManager, eGetEnigmaDebugLvl, eStreamServer, eTimer, getDesktop, getE2Rev

from boxbranding import getMachineBuild, getDriverDate

from skin import parameters
from Components.About import about
from Components.ActionMap import HelpableActionMap, HelpableNumberActionMap
from Components.config import config
from Components.Console import Console
from Components.Converter.ClientsStreaming import ClientsStreaming
from Components.Harddisk import Harddisk, harddiskmanager
from Components.InputDevice import REMOTE_DISPLAY_NAME, REMOTE_NAME, REMOTE_RCTYPE, remoteControl
from Components.Label import Label
from Components.Network import iNetwork
from Components.NimManager import nimmanager
from Components.Pixmap import Pixmap
from Components.ScrollLabel import ScrollLabel
# from Components.Storage import Harddisk, storageManager
from Components.SystemInfo import BoxInfo
from Components.Sources.StaticText import StaticText
from Screens.HelpMenu import HelpableScreen
from Screens.MessageBox import MessageBox
from Screens.ChoiceBox import ChoiceBox
from Screens.Screen import Screen, ScreenSummary
from Tools.Directories import SCOPE_GUISKIN, fileReadLine, fileReadLines, fileWriteLine, resolveFilename
from Tools.Geolocation import geolocation
from Tools.LoadPixmap import LoadPixmap
from Tools.MultiBoot import MultiBoot
from Tools.StbHardware import getFPVersion, getBoxProc, getHWSerial, getBoxRCType, getBoxProcType

MODULE_NAME = __name__.split(".")[-1]

INFO_COLORS = ["N", "H", "S", "P", "V", "M", "F"]
INFO_COLOR = {
	"B": None,
	"N": 0x00ffffff,  # Normal.
	"H": 0x00ffffff,  # Headings.
	"S": 0x00ffffff,  # Subheadings.
	"P": 0x00cccccc,  # Prompts.
	"V": 0x00cccccc,  # Values.
	"M": 0x00ffff00,  # Messages.
	"F": 0x0000ffff  # Features.
}

USECOMMA = "," in format_string("%.1f", 1)

def scaleNumber(number, style="Si", suffix="B", format="%.3f"):  # This temporary code is borrowed from the new Storage.py!
	units = ["", "K", "M", "G", "T", "P", "E", "Z", "Y"]
	style = style.capitalize()
	if style not in ("Si", "Iec", "Jedec"):
		print("[Information] Error: Invalid number unit style '%s' specified so 'Si' is assumed!" % style)
	if style == "Si":
		units[1] = units[1].lower()
	negative = number < 0
	if negative:
		number = -number
	digits = len(str(number))
	scale = int((digits - 1) // 3)
	result = float(number) / (10 ** (scale * 3)) if style == "Si" else float(number) / (1024 ** scale)
	if negative:
		result = -result
	# print("[Information] DEBUG: Number=%d, Digits=%d, Scale=%d, Factor=%d, Result=%f." % (number, digits, scale, 10 ** (scale * 3), result))
	return "%s %s%s%s" % (format_string(format, result), units[scale], ("i" if style == "Iec" and scale else ""), suffix)


BoxProcTypes = {
	"00": _("OTT Model"),
	"10": _("Single Tuner"),
	"11": _("Twin Tuner"),
	"12": _("Combo Tuner"),
	"22": _("Hybrid Tuner")
}

def getBoxProcTypeName():
	proctype = getBoxProcType()
	if proctype == "unknown":
		return proctype
	return "%s - %s" % (proctype, BoxProcTypes.get(proctype, _("Unknown")))

def convertDate(StringDate):
	## StringDate must be a string "YYYY-MM-DD" or "YYYYMMDD" / or integer YYYYMMDD
	try:
		if type(StringDate) == int:
			StringDate = str(StringDate)
		if len(StringDate) == 8:
			year = StringDate[0:4]
			month = StringDate[4:6]
			day = StringDate[6:8]
			StringDate = ' '.join((year, month, day))
		else:
			StringDate = StringDate.replace("-", " ")
		StringDate = strftime(config.usage.date.full.value, strptime(StringDate, "%Y %m %d"))
		return StringDate
	except:
		return _("Unknown")

def formatMinMax(values):
	# 'min=950 MHz,max=2.15 GHz,stepsize=125 kHz,tolerance=0 Hz'
	values = values.split(",")
	min = ""
	max = ""
	for value in values:
		if "min=" in value:
			min = value[4:]
		if "max=" in value:
			max = value[4:]
	if min and max:
		ret = "%s - %s" % (min, max)
		if USECOMMA:
			return ret.replace(".", ",")
		return ret
	else:
		return None

class InformationBase(Screen, HelpableScreen):
	skin = """
	<screen name="Information" position="center,center" size="950,560" resolution="1280,720">
		<widget name="information" position="10,10" size="e-20,e-60" colPosition="475" conditional="information" divideChar="|" font="Regular;20" noWrap="1" leftColAlign="left" rightColAlign="left" split="1" transparent="1" />
		<widget name="description" position="e-1,e-50" size="1,1" font="Regular;18" valign="center" conditional="description" />
		<widget source="key_red" render="Label" position="10,e-50" size="180,40" backgroundColor="key_red" conditional="key_red" font="Regular;20" foregroundColor="key_text" halign="center" valign="center">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="key_green" render="Label" position="200,e-50" size="180,40" backgroundColor="key_green" conditional="key_green" font="Regular;20" foregroundColor="key_text" halign="center" valign="center">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="key_yellow" render="Label" position="390,e-50" size="180,40" backgroundColor="key_yellow" conditional="key_yellow" font="Regular;20" foregroundColor="key_text" halign="center" valign="center">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="key_blue" render="Label" position="580,e-50" size="180,40" backgroundColor="key_blue" conditional="key_blue" font="Regular;20" foregroundColor="key_text" halign="center" valign="center">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="key_info" render="Label" position="e-180,e-50" size="80,40" backgroundColor="key_back" conditional="key_info" font="Regular;20" foregroundColor="key_text" halign="center" valign="center">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="key_help" render="Label" position="e-90,e-50" size="80,40" backgroundColor="key_back" conditional="key_help" font="Regular;20" foregroundColor="key_text" halign="center" valign="center">
			<convert type="ConditionalShowHide" />
		</widget>
	</screen>"""

	def __init__(self, session):
		Screen.__init__(self, session, mandatoryWidgets=["information", "description"])
		HelpableScreen.__init__(self)
		self.skinName = ["Information"]
		self["information"] = ScrollLabel()
		self["description"] = Label()
		self["key_red"] = StaticText(_("Close"))
		self["key_green"] = StaticText(_("Refresh"))
		self["actions"] = HelpableActionMap(self, ["CancelSaveActions", "OkActions", "NavigationActions"], {
			"cancel": (self.keyCancel, _("Close the screen")),
			"close": (self.closeRecursive, _("Close the screen and exit all menus")),
			"save": (self.refreshInformation, _("Refresh the screen")),
			"ok": (self.refreshInformation, _("Refresh the screen")),
			"top": (self["information"].moveTop, _("Move to first line / screen")),
			"pageUp": (self["information"].pageUp, _("Move up a screen")),
			"left": (self["information"].pageUp, _("Move up a screen")),
			"right": (self["information"].pageDown, _("Move down a screen")),
			"up": (self["information"].moveUp, _("Move up a line")),
			"down": (self["information"].moveDown, _("Move down a line")),
			"pageDown": (self["information"].pageDown, _("Move down a screen")),
			"bottom": (self["information"].moveBottom, _("Move to last line / screen"))
		}, prio=0, description=_("Common Information Actions"))
		#if isfile(resolveFilename(SCOPE_GUISKIN, "receiver/%s.png" % BoxInfo.getItem("model"))):
		#	self["key_info"] = StaticText(_("INFO"))
		#	self["infoActions"] = HelpableActionMap(self, ["InfoActions"], {
		#		"info": (self.showReceiverImage, _("Show receiver image(s)"))
		#	}, prio=0, description=_("Receiver Information Actions"))
		colors = parameters.get("InformationColors", (0x00ffffff, 0x00ffffff, 0x00ffffff, 0x00cccccc, 0x00cccccc, 0x00ffff00, 0x0000ffff))
		if len(colors) == len(INFO_COLORS):
			for index in range(len(colors)):
				INFO_COLOR[INFO_COLORS[index]] = colors[index]
		else:
			print("[Information] Warning: %d colors are defined in the skin when %d were expected!" % (len(colors), len(INFO_COLORS)))
		self["information"].setText(_("Loading information, please wait..."))
		self.onInformationUpdated = [self.displayInformation]
		self.onLayoutFinish.append(self.displayInformation)
		self.console = Console()
		self.informationTimer = eTimer()
		self.informationTimer.callback.append(self.fetchInformation)
		self.informationTimer.start(25)

	#def showReceiverImage(self):
	#	self.session.openWithCallback(self.informationWindowClosed, InformationImage)

	def keyCancel(self):
		self.console.killAll()
		self.close()

	def closeRecursive(self):
		self.console.killAll()
		self.close(True)

	def informationWindowClosed(self, *retVal):
		if retVal and retVal[0]:
			self.close(True)

	def fetchInformation(self):
		self.informationTimer.stop()
		for callback in self.onInformationUpdated:
			callback()

	def refreshInformation(self):
		self.informationTimer.start(25)
		for callback in self.onInformationUpdated:
			callback()

	def displayInformation(self):
		pass

	def getSummaryInformation(self):
		pass

	def createSummary(self):
		return InformationSummary


class InformationImage(Screen, HelpableScreen):
	skin = """
	<screen name="InformationImage" title="Receiver Image" position="center,center" size="950,560" resolution="1280,720">
		<widget name="name" position="10,10" size="e-20,25" font="Regular;20" halign="center" transparent="1" valign="center" />
		<widget name="image" position="10,45" size="e-20,e-105" alphatest="blend" scale="1" transparent="1" />
		<widget source="key_red" render="Label" position="10,e-50" size="180,40" backgroundColor="key_red" conditional="key_red" font="Regular;20" foregroundColor="key_text" halign="center" valign="center">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="key_green" render="Label" position="200,e-50" size="180,40" backgroundColor="key_green" conditional="key_green" font="Regular;20" foregroundColor="key_text" halign="center" valign="center">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="key_yellow" render="Label" position="390,e-50" size="180,40" backgroundColor="key_yellow" conditional="key_yellow" font="Regular;20" foregroundColor="key_text" halign="center" valign="center">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="key_help" render="Label" position="e-90,e-50" size="80,40" backgroundColor="key_back" conditional="key_help" font="Regular;20" foregroundColor="key_text" halign="center" valign="center">
			<convert type="ConditionalShowHide" />
		</widget>
	</screen>"""

	def __init__(self, session):
		Screen.__init__(self, session, mandatoryWidgets=["name", "image"])
		HelpableScreen.__init__(self)
		self["name"] = Label()
		self["image"] = Pixmap()
		self["key_red"] = StaticText(_("Close"))
		self["key_green"] = StaticText(_("Prev Image"))
		self["key_yellow"] = StaticText(_("Next Image"))
		self["actions"] = HelpableActionMap(self, ["OkCancelActions", "NavigationActions", "ColorActions"], {
			"cancel": (self.keyCancel, _("Close the screen")),
			"close": (self.closeRecursive, _("Close the screen and exit all menus")),
			"ok": (self.nextImage, _("Show next image")),
			"red": (self.keyCancel, _("Close the screen")),
			"green": (self.prevImage, _("Show previous image")),
			"yellow": (self.nextImage, _("Show next image")),
			"up": (self.prevImage, _("Show previous image")),
			"left": (self.prevImage, _("Show previous image")),
			"right": (self.nextImage, _("Show next image")),
			"down": (self.nextImage, _("Show next image"))
		}, prio=0, description=_("Receiver Image Actions"))
		self.images = (
			(_("Front"), "receiver/%s.png", BoxInfo.getItem("model")),
			(_("Rear"), "receiver/%s-rear.png", BoxInfo.getItem("model")),
			(_("Internal"), "receiver/%s-internal.png", BoxInfo.getItem("model")),
			(_("Remote Control"), "rc/%s.png", BoxInfo.getItem("rcname")),
			(_("Flashing"), "receiver/%s-flashing.png", BoxInfo.getItem("model"))
		)
		self.imageIndex = 0
		self.widgetContext = None
		self.onLayoutFinish.append(self.layoutFinished)

	def keyCancel(self):
		self.close()

	def closeRecursive(self):
		self.close(True)

	def prevImage(self):
		self.imageIndex -= 1
		if self.imageIndex < 0:
			self.imageIndex = len(self.images) - 1
		while not isfile(resolveFilename(SCOPE_GUISKIN, self.images[self.imageIndex][1] % self.images[self.imageIndex][2])):
			self.imageIndex -= 1
			if self.imageIndex < 0:
				self.imageIndex = len(self.images) - 1
				break
		self.layoutFinished()

	def nextImage(self):
		self.imageIndex += 1
		while not isfile(resolveFilename(SCOPE_GUISKIN, self.images[self.imageIndex][1] % self.images[self.imageIndex][2])):
			self.imageIndex += 1
			if self.imageIndex >= len(self.images):
				self.imageIndex = 0
				break
		self.layoutFinished()

	def layoutFinished(self):
		if self.widgetContext is None:
			self.widgetContext = tuple(self["image"].getPosition() + self["image"].getSize())
			print(self.widgetContext)
		self["name"].setText("%s %s  -  %s View" % (BoxInfo.getItem("displaybrand"), BoxInfo.getItem("displaymodel"), self.images[self.imageIndex][0]))
		imagePath = resolveFilename(SCOPE_GUISKIN, self.images[self.imageIndex][1] % self.images[self.imageIndex][2])
		image = LoadPixmap(imagePath)
		if image:
			self["image"].instance.setPixmap(image)


def formatLine(style, left, right=None):
	styleLen = len(style)
	leftStartColor = "" if styleLen > 0 and style[0] == "B" else "\c%08x" % (INFO_COLOR.get(style[0], "P") if styleLen > 0 else INFO_COLOR["P"])
	leftEndColor = "" if leftStartColor == "" else "\c%08x" % INFO_COLOR["N"]
	leftIndent = "    " * int(style[1]) if styleLen > 1 and style[1].isdigit() else ""
	rightStartColor = "" if styleLen > 2 and style[2] == "B" else "\c%08x" % (INFO_COLOR.get(style[2], "V") if styleLen > 2 else INFO_COLOR["V"])
	rightEndColor = "" if rightStartColor == "" else "\c%08x" % INFO_COLOR["N"]
	rightIndent = "    " * int(style[3]) if styleLen > 3 and style[3].isdigit() else ""
	if right is None:
		colon = "" if styleLen > 0 and style[0] in ("M", "P", "V") else ":"
		return "%s%s%s%s%s" % (leftIndent, leftStartColor, left, colon, leftEndColor)
	return "%s%s%s:%s|%s%s%s%s" % (leftIndent, leftStartColor, left, leftEndColor, rightIndent, rightStartColor, right, rightEndColor)


class CommitLogInformation(InformationBase):
	def __init__(self, session):
		InformationBase.__init__(self, session)
		self.baseTitle = _("Commit Information")
		self.setTitle(self.baseTitle)
		self.skinName.insert(0, "CommitLogInformation")
		self["systemMenuActions"] = HelpableActionMap(self, ["MenuActions"], {
			"menu": (self.selectCommit, _("Show selection for commit logs")),
		}, prio=0, description=_("Commit Information Actions"))
		self["commitActions"] = HelpableActionMap(self, ["DirectionActions"], {
			"moveUp": (self.previousCommit, _("Display previous commit log")),
			"moveDown": (self.nextCommit, _("Display next commit log")),
		}, prio=0, description=_("Commit Information Actions"))
		try:
			branch = getE2Rev()
			if "+" in branch:
				branch = branch.split("+")[1]
			branch = "?sha=%s" % branch
		except Exception as err:
			branch = ""

		self.projects = [
			("openATV Enigma2", "https://api.github.com/repos/openatv/enigma2/commits%s" % branch),
			("oe-alliance-plugins", "https://api.github.com/repos/oe-alliance/oe-alliance-plugins/commits"),
			("enigma2-plugins", "https://api.github.com/repos/oe-alliance/enigma2-plugins/commits")
		]
		self.project = 0
		self.cachedProjects = {}
		self.log = _("Retrieving %s commit log, please wait...") % self.projects[self.project][0]
		self["description"].setText(_("Press <> or menu to select the different commit logs"))

	def selectCommit(self):
		choices = [(cmd[0], str(idx)) for idx, cmd in enumerate(self.projects)]
		self.session.openWithCallback(self.selectCommitCallBack, ChoiceBox, title=_("Select commit log"), list=choices)

	def selectCommitCallBack(self, selected):
		if selected:
			self.project = int(selected[1]) % len(self.projects)
			self.log = _("Retrieving %s commit log, please wait...") % self.projects[self.project][0]
			self.informationTimer.start(25)

	def previousCommit(self):
		self.project = self.project == 0 and len(self.projects) - 1 or self.project - 1
		self.log = _("Retrieving %s commit log, please wait...") % self.projects[self.project][0]
		self.informationTimer.start(25)

	def nextCommit(self):
		self.project = self.project != len(self.projects) - 1 and self.project + 1 or 0
		self.log = _("Retrieving %s commit log, please wait...") % self.projects[self.project][0]
		self.informationTimer.start(25)

	def fetchInformation(self):
		# Limit the number of fetches per minute!
		self.informationTimer.stop()
		name = self.projects[self.project][0]
		url = self.projects[self.project][1]
		log = []
		try:
			try:
				rawLog = loads(urlopen(url, timeout=10, context=_create_unverified_context()).read())
			except Exception as err:
				rawLog = loads(urlopen(url, timeout=10).read())
			for data in rawLog:
				date = datetime.strptime(data["commit"]["committer"]["date"], "%Y-%m-%dT%H:%M:%SZ").strftime("%x %X")
				creator = "" #data["commit"]["author"]["name"]
				title = data["commit"]["message"]
				if log:
					log.append("")
				log.append("%s  %s" % (date, creator))
				log.append(title)
			if log:
				log = "\n".join(log).encode("UTF-8", "ignore") if PY2 else "\n".join(log)
				self.cachedProjects[name] = log
			else:
				log = _("The %s commit log contains no information.") % name
		except Exception as err:
			log.append(_("Error '%s' encountered retrieving the %s commit logs!") % (str(err), name))
			log.append("")
			log.append(_("The %s commit logs can't be retrieved, please try again later.") % name)
			log.append("")
			log.append(_("Access to the %s commit logs requires an internet connection.") % name)
			log = "\n".join(log)
		self.log = log
		for callback in self.onInformationUpdated:
			callback()

	def refreshInformation(self):
		# Limit the number of fetches per minute!
		self.cachedProjects = {}
		self.log = _("Retrieving %s commit log, please wait...") % self.projects[self.project][0]
		self.informationTimer.start(25)
		for callback in self.onInformationUpdated:
			callback()

	def displayInformation(self):
		name = self.projects[self.project][0]
		self.setTitle("%s - %s" % (self.baseTitle, name))
		if name in self.cachedProjects:
			self["information"].setText(self.cachedProjects[name])
		elif self.log:
			self["information"].setText(self.log)
		else:
			self["information"].setText(_("The %s commit log contains no information.") % name)


class GeolocationInformation(InformationBase):
	def __init__(self, session):
		InformationBase.__init__(self, session)
		self.setTitle(_("Geolocation Information"))
		self.skinName.insert(0, "GeolocationInformation")

	def displayInformation(self):
		info = []
		geolocationData = geolocation.getGeolocationData(fields="continent,country,regionName,city,lat,lon,timezone,currency,isp,org,mobile,proxy,query", useCache=False)
		if geolocationData.get("status", None) == "success":
			info.append(formatLine("H", _("Location information")))
			continent = geolocationData.get("continent", None)
			if continent:
				info.append(formatLine("P1", _("Continent"), continent))
			country = geolocationData.get("country", None)
			if country:
				info.append(formatLine("P1", _("Country"), country))
			state = geolocationData.get("regionName", None)
			if state:
				# TRANSLATORS: "State" is Location Info
				info.append(formatLine("P1", _("State"), state))
			city = geolocationData.get("city", None)
			if city:
				info.append(formatLine("P1", _("City"), city))
			latitude = geolocationData.get("lat", None)
			if latitude:
				info.append(formatLine("P1", _("Latitude"), latitude))
			longitude = geolocationData.get("lon", None)
			if longitude:
				info.append(formatLine("P1", _("Longitude"), longitude))
			info.append("")
			info.append(formatLine("H", _("Local information")))
			timezone = geolocationData.get("timezone", None)
			if timezone:
				info.append(formatLine("P1", _("Timezone"), timezone))
			currency = geolocationData.get("currency", None)
			if currency:
				info.append(formatLine("P1", _("Currency"), currency))
			info.append("")
			info.append(formatLine("H", _("Connection information")))
			isp = geolocationData.get("isp", None)
			if isp:
				ispOrg = geolocationData.get("org", None)
				if ispOrg:
					info.append(formatLine("P1", _("ISP"), "%s  (%s)" % (isp, ispOrg)))
				else:
					info.append(formatLine("P1", _("ISP"), isp))
			mobile = geolocationData.get("mobile", None)
			info.append(formatLine("P1", _("Mobile connection"), (_("Yes") if mobile else _("No"))))
			proxy = geolocationData.get("proxy", False)
			info.append(formatLine("P1", _("Proxy detected"), (_("Yes") if proxy else _("No"))))
			publicIp = geolocationData.get("query", None)
			if publicIp:
				info.append(formatLine("P1", _("Public IP"), publicIp))
		else:
			info.append(_("Geolocation information cannot be retrieved, please try again later."))
			info.append("")
			info.append(_("Access to geolocation information requires an internet connection."))
		self["information"].setText("\n".join(info).encode("UTF-8", "ignore") if PY2 else "\n".join(info))

	def getSummaryInformation(self):
		return "Geolocation Information"


class ImageInformation(InformationBase):
	def __init__(self, session):
		InformationBase.__init__(self, session)
		self.displayDistro = BoxInfo.getItem("displaydistro", "openATV")
		self.setTitle(_("%s Information") % self.displayDistro)
		self.skinName.insert(0, "ImageInformation")
		self["key_yellow"] = StaticText(_("Commit Logs"))
		self["key_blue"] = StaticText(_("Translation"))
		self["receiverActions"] = HelpableActionMap(self, ["ColorActions"], {
			"yellow": (self.showCommitLogs, _("Show latest commit log information")),
			"blue": (self.showTranslation, _("Show translation information"))
		}, prio=0, description=_("%s Information Actions") % self.displayDistro)
		self.resolutions = {
			480: _("NTSC"),
			576: _("PAL"),
			720: _("HD"),
			1080: _("FHD"),
			2160: _("4K"),
			4320: _("8K"),
			8640: _("16K")
		}
		self["description"].setText("https://github.com/openatv\n\nhttps://github.com/oe-alliance")
		self.imageMessage = ""

	def showCommitLogs(self):
		self.session.openWithCallback(self.informationWindowClosed, CommitLogInformation)

	def showTranslation(self):
		self.session.openWithCallback(self.informationWindowClosed, TranslationInformation)

	def displayInformation(self):
		info = []
		if self.imageMessage:
			for line in self.imageMessage:
				info.append(formatLine("M", line))
			info.append("")
		info.append(formatLine("H", _("%s information") % self.displayDistro))
		info.append(formatLine("P1", _("Info file checksum"), _("Invalid") if BoxInfo.getItem("checksumerror", False) else _("Valid")))
		override = BoxInfo.getItem("overrideactive", False)
		if override:
			info.append(formatLine("P1", _("Info file override"), _("Defined / Active")))
		info.append(formatLine("P1", _("Distribution version"), BoxInfo.getItem("imgversion")))
		info.append(formatLine("P1", _("Distribution revision"), convertDate(BoxInfo.getItem("imgrevision"))))
		info.append(formatLine("P1", _("Distribution language"), BoxInfo.getItem("imglanguage")))
		info.append(formatLine("P1", _("OEM Model"), getMachineBuild()))
		slotCode, bootCode = MultiBoot.getCurrentSlotAndBootCodes()
		if MultiBoot.canMultiBoot():
			device = MultiBoot.getBootDevice()
			if BoxInfo.getItem("HasHiSi") and "sda" in device:
				slotCode = int(slotCode)
				image = slotCode - 4 if slotCode > 4 else slotCode - 1
				device = _("SDcard slot %s%s") % (image, "  -  %s" % device if device else "")
			else:
				device = _("eMMC slot %s%s") % (slotCode, "  -  %s" % device if device else "")
			info.append(formatLine("P1", _("Hardware MultiBoot device"), device))
			info.append(formatLine("P1", _("MultiBoot startup file"), MultiBoot.getStartupFile()))
		if bootCode:
			info.append(formatLine("P1", _("MultiBoot boot mode"), MultiBoot.getBootCodeDescription(bootCode)))
		info.append(formatLine("P1", _("Software MultiBoot"), _("Yes") if BoxInfo.getItem("multiboot", False) else _("No")))
		info.append(formatLine("P1", _("Flash type"), about.getFlashType()))
		xResolution = getDesktop(0).size().width()
		yResolution = getDesktop(0).size().height()
		info.append(formatLine("P1", _("Skin & Resolution"), "%s  (%s  -  %s x %s)" % (config.skin.primary_skin.value.split('/')[0], self.resolutions.get(yResolution, "Unknown"), xResolution, yResolution)))
		info.append("")
		info.append(formatLine("H", _("Enigma2 information")))
		enigmaVersion = about.getEnigmaVersionString()
		enigmaVersion = enigmaVersion.rsplit("-", enigmaVersion.count("-") - 2)
		if len(enigmaVersion) == 3:
			enigmaVersion = "%s (%s-%s)" % (enigmaVersion[0], enigmaVersion[2], enigmaVersion[1].capitalize())
		elif len(enigmaVersion) == 1:
			enigmaVersion = "%s" % enigmaVersion[0]
		else:
			enigmaVersion = "%s (%s)" % (enigmaVersion[0], enigmaVersion[1].capitalize())
		info.append(formatLine("P1", _("Enigma2 version"), enigmaVersion))
		info.append(formatLine("P1", _("Enigma2 revision"), getE2Rev()))
		compileDate = str(BoxInfo.getItem("compiledate"))
		info.append(formatLine("P1", _("Last update"), convertDate("%s%s%s" % (compileDate[:4], compileDate[4:6], compileDate[6:]))))
		info.append(formatLine("P1", _("Last flash"), convertDate(about.getFlashDateString())))
		info.append(formatLine("P1", _("Enigma2 (re)starts"), config.misc.startCounter.value))
		info.append(formatLine("P1", _("Enigma2 debug level"), eGetEnigmaDebugLvl()))
		mediaService = BoxInfo.getItem("mediaservice")
		if mediaService:
			info.append(formatLine("P1", _("Media service"), mediaService.replace("enigma2-plugin-systemplugins-", "")))
		info.append("")
		info.append(formatLine("H", _("Build information")))
		info.append(formatLine("P1", _("Distribution"), BoxInfo.getItem("distro")))
		info.append(formatLine("P1", _("Distribution build"), BoxInfo.getItem("imagebuild")))
		info.append(formatLine("P1", _("Distribution build date"), convertDate(about.getBuildDateString())))
		info.append(formatLine("P1", _("Distribution architecture"), BoxInfo.getItem("architecture")))
		if BoxInfo.getItem("imagedir"):
			info.append(formatLine("P1", _("Distribution folder"), BoxInfo.getItem("imagedir")))
		if BoxInfo.getItem("imagefs"):
			info.append(formatLine("P1", _("Distribution file system"), BoxInfo.getItem("imagefs").strip()))
		info.append(formatLine("P1", _("Feed URL"), BoxInfo.getItem("feedsurl")))
		info.append(formatLine("P1", _("Compiled by"), BoxInfo.getItem("developername")))
		info.append("")
		info.append(formatLine("H", _("Software information")))
		info.append(formatLine("P1", _("GCC version"), about.getGccVersion()))
		info.append(formatLine("P1", _("Glibc version"), about.getGlibcVersion()))
		info.append(formatLine("P1", _("OpenSSL version"), about.getopensslVersionString()))
		info.append(formatLine("P1", _("Python version"), about.getPythonVersionString()))
		info.append(formatLine("P1", _("GStreamer version"), about.getGStreamerVersionString().replace("GStreamer ", "")))
		info.append(formatLine("P1", _("FFmpeg version"), about.getFFmpegVersionString()))
		bootId = fileReadLine("/proc/sys/kernel/random/boot_id", source=MODULE_NAME)
		if bootId:
			info.append(formatLine("P1", _("Boot ID"), bootId))
		uuId = fileReadLine("/proc/sys/kernel/random/uuid", source=MODULE_NAME)
		if uuId:
			info.append(formatLine("P1", _("UUID"), uuId))
		info.append("")
		info.append(formatLine("H", _("Boot information")))
		if BoxInfo.getItem("mtdbootfs"):
			info.append(formatLine("P1", _("MTD boot"), BoxInfo.getItem("mtdbootfs")))
		if BoxInfo.getItem("mtdkernel"):
			info.append(formatLine("P1", _("MTD kernel"), BoxInfo.getItem("mtdkernel")))
		if BoxInfo.getItem("mtdrootfs"):
			info.append(formatLine("P1", _("MTD root"), BoxInfo.getItem("mtdrootfs")))
		if BoxInfo.getItem("kernelfile"):
			info.append(formatLine("P1", _("Kernel file"), BoxInfo.getItem("kernelfile")))
		if BoxInfo.getItem("rootfile"):
			info.append(formatLine("P1", _("Root file"), BoxInfo.getItem("rootfile")))
		if BoxInfo.getItem("mkubifs"):
			info.append(formatLine("P1", _("MKUBIFS"), BoxInfo.getItem("mkubifs")))
		if BoxInfo.getItem("ubinize"):
			info.append(formatLine("P1", _("UBINIZE"), BoxInfo.getItem("ubinize")))
		self["information"].setText("\n".join(info).encode("UTF-8", "ignore") if PY2 else "\n".join(info))

	def getSummaryInformation(self):
		return "%s Information" % self.displayDistro


class MemoryInformation(InformationBase):
	def __init__(self, session):
		InformationBase.__init__(self, session)
		self.setTitle(_("Memory Information"))
		self.skinName.insert(0, "MemoryInformation")
		self["clearActions"] = HelpableActionMap(self, ["ColorActions"], {
			"yellow": (self.clearMemoryInformation, _("Clear the virtual memory caches"))
		}, prio=0, description=_("Memory Information Actions"))
		self["key_yellow"] = StaticText(_("Clear"))

	def displayInformation(self):
		info = []
		memInfo = fileReadLines("/proc/meminfo", source=MODULE_NAME)
		info.append(formatLine("H", _("RAM (Summary)")))
		for line in memInfo:
			key, value, units = [x for x in line.split()]
			if key == "MemTotal:":
				info.append(formatLine("P1", _("Total memory"), "%s %s" % (value, units)))
			if key == "MemFree:":
				info.append(formatLine("P1", _("Free memory"), "%s %s" % (value, units)))
			if key == "Buffers:":
				info.append(formatLine("P1", _("Buffers"), "%s %s" % (value, units)))
			if key == "Cached:":
				info.append(formatLine("P1", _("Cached"), "%s %s" % (value, units)))
			if key == "SwapTotal:":
				info.append(formatLine("P1", _("Total swap"), "%s %s" % (value, units)))
			if key == "SwapFree:":
				info.append(formatLine("P1", _("Free swap"), "%s %s" % (value, units)))
		info.append("")
		info.append(formatLine("H", _("FLASH")))
		stat = statvfs("/")
		diskSize = stat.f_blocks * stat.f_frsize
		diskFree = stat.f_bfree * stat.f_frsize
		diskUsed = diskSize - diskFree
		info.append(formatLine("P1", _("Total flash"), "%s  (%s)" % (scaleNumber(diskSize), scaleNumber(diskSize, "Iec"))))
		info.append(formatLine("P1", _("Used flash"), "%s  (%s)" % (scaleNumber(diskUsed), scaleNumber(diskUsed, "Iec"))))
		info.append(formatLine("P1", _("Free flash"), "%s  (%s)" % (scaleNumber(diskFree), scaleNumber(diskFree, "Iec"))))
		info.append("")
		info.append(formatLine("H", _("RAM (Details)")))
		for line in memInfo:
			key, value, units = [x for x in line.split()]
			info.append(formatLine("P1", key[:-1], "%s %s" % (value, units)))
		info.append("")
		info.append(formatLine("P1", _("The detailed information is intended for developers only.")))
		info.append(formatLine("P1", _("Please don't panic if you see values that look suspicious.")))
		self["information"].setText("\n".join(info).encode("UTF-8", "ignore") if PY2 else "\n".join(info))

	def clearMemoryInformation(self):
		eConsoleAppContainer().execute(*["/bin/sync", "/bin/sync"])
		fileWriteLine("/proc/sys/vm/drop_caches", "3")
		self.informationTimer.start(25)
		for callback in self.onInformationUpdated:
			callback()

	def getSummaryInformation(self):
		return "Memory Information Data"


class MultiBootInformation(InformationBase):
	def __init__(self, session):
		InformationBase.__init__(self, session)
		self.setTitle(_("MultiBoot Information"))
		self.skinName.insert(0, "MultiBootInformation")
		self.slotImages = None

	def fetchInformation(self):
		self.informationTimer.stop()
		MultiBoot.getSlotImageList(self.gotInformation)

	def gotInformation(self, slotImages):
		self.slotImages = slotImages
		for callback in self.onInformationUpdated:
			callback()

	def refreshInformation(self):
		self.slotImages = None
		MultiBoot.loadMultiBoot()
		self.informationTimer.start(25)
		for callback in self.onInformationUpdated:
			callback()

	def displayInformation(self):
		info = []
		info.append(formatLine("H", _("Boot slot information for %s %s") % (BoxInfo.getItem("displaybrand"), BoxInfo.getItem("displaymodel"))))
		info.append("")
		if self.slotImages:
			slotCode, bootCode = MultiBoot.getCurrentSlotAndBootCodes()
			slotImageList = sorted(self.slotImages.keys())
			currentMsg = "  -  %s" % _("Current")
			imageLists = {}
			for slot in slotImageList:
				for boot in self.slotImages[slot]["bootCodes"]:
					if imageLists.get(boot) is None:
						imageLists[boot] = []
					current = currentMsg if boot == bootCode and slot == slotCode else ""
					indent = "P0V0" if boot == "" else "P1V0"
					if current:
						indent = indent.replace("P", "F").replace("V", "F")
					imageLists[boot].append(formatLine(indent, _("Slot '%s'") % slot, "%s%s" % (self.slotImages[slot]["imagename"], current)))
			count = 0
			for bootCode in sorted(imageLists.keys()):
				if bootCode == "":
					continue
				if count:
					info.append("")
				info.append(formatLine("S", MultiBoot.getBootCodeDescription(bootCode), None))
				info.extend(imageLists[bootCode])
				count += 1
			if count:
				info.append("")
			if "" in imageLists:
				info.extend(imageLists[""])
		else:
			info.append(formatLine("P1", _("Retrieving boot slot information...")))
		self["information"].setText("\n".join(info))

	def getSummaryInformation(self):
		return "MultiBoot Information Data"


class NetworkInformation(InformationBase):
	def __init__(self, session):
		InformationBase.__init__(self, session)
		self.setTitle(_("Network Information"))
		self.skinName = ["Information", "WlanStatus"]
		#self["key_yellow"] = StaticText(_("WAN Geolocation"))
		self["key_yellow"] = StaticText(_("Geolocation"))
		self["geolocationActions"] = HelpableActionMap(self, ["ColorActions"], {
			# "yellow": (self.useGeolocation, _("Use geolocation to get WAN information")),
			"yellow": (self.showGeolocation, _("Show geolocation information"))
		}, prio=0, description=_("Network Information Actions"))
		self.interfaceData = {}
		self.geolocationData = []
		self.ifconfigAttributes = {
			"Link encap": "encapsulation",
			"HWaddr": "mac",
			"inet addr": "addr",
			"Bcast": "brdaddr",
			"Mask": "nmask",
			"inet6 addr": "addr6",
			"Scope": "scope",
			"MTU": "mtu",
			"Metric": "metric",
			"RX packets": "rxPackets",
			"rxerrors": "rxErrors",
			"rxdropped": "rxDropped",
			"rxoverruns": "rxOverruns",
			"rxframe": "rxFrame",
			"TX packets": "txPackets",
			"txerrors": "txErrors",
			"txdropped": "txDropped",
			"txoverruns": "txOverruns",
			"collisions": "txCollisions",
			"txqueuelen": "txQueueLen",
			"RX bytes": "rxBytes",
			"TX bytes": "txBytes"
		}
		self.iwconfigAttributes = {
			"interface": "interface",
			"standard": "standard",
			"ESSID": "ssid",
			"Mode": "mode",
			"Frequency": "frequency",
			"Access Point": "accessPoint",
			"Bit Rate": "bitrate",
			"Tx-Power": "transmitPower",
			"Retry short limit": "retryLimit",
			"RTS thr": "rtsThrottle",
			"Fragment thr": "fragThrottle",
			"Encryption key": "encryption",
			"Power Management": "powerManagement",
			"Link Quality": "signalQuality",
			"Signal level": "signalStrength",
			"Rx invalid nwid": "rxInvalidNwid",
			"Rx invalid crypt": "rxInvalidCrypt",
			"Rx invalid frag": "rxInvalidFrag",
			"Tx excessive retries": "txExcessiveReties",
			"Invalid misc": "invalidMisc",
			"Missed beacon": "missedBeacon"
		}
		self.ethtoolAttributes = {
			"Speed": "speed",
			"Duplex": "duplex",
			"Transceiver": "transceiver",
			"Auto-negotiation": "autoNegotiation",
			"Link detected": "link"
		}

	def showGeolocation(self):
		self.session.openWithCallback(self.informationWindowClosed, GeolocationInformation)

	def useGeolocation(self):
		geolocationData = geolocation.getGeolocationData(fields="isp,org,mobile,proxy,query", useCache=False)
		info = []
		if geolocationData.get("status", None) == "success":
			info.append("")
			info.append(formatLine("H", _("WAN connection information")))
			isp = geolocationData.get("isp", None)
			if isp:
				ispOrg = geolocationData.get("org", None)
				if ispOrg:
					info.append(formatLine("P1", _("ISP"), "%s  (%s)" % (isp, ispOrg)))
				else:
					info.append(formatLine("P1", _("ISP"), isp))
			mobile = geolocationData.get("mobile", None)
			info.append(formatLine("P1", _("Mobile connection"), (_("Yes") if mobile else _("No"))))
			proxy = geolocationData.get("proxy", False)
			info.append(formatLine("P1", _("Proxy detected"), (_("Yes") if proxy else _("No"))))
			publicIp = geolocationData.get("query", None)
			if publicIp:
				info.append(formatLine("P1", _("Public IP"), publicIp))
		else:
			info.append(_("Geolocation information cannot be retrieved, please try again later."))
			info.append("")
			info.append(_("Access to geolocation information requires an internet connection."))
		self.geolocationData = info
		for callback in self.onInformationUpdated:
			callback()

	def fetchInformation(self):
		self.informationTimer.stop()
		for interface in sorted([x for x in listdir("/sys/class/net") if not self.isBlacklisted(x)]):
			self.interfaceData[interface] = {}
			self.console.ePopen(("/sbin/ifconfig", "/sbin/ifconfig", interface), self.ifconfigInfoFinished, extra_args=interface)
			if iNetwork.isWirelessInterface(interface):
				self.console.ePopen(("/sbin/iwconfig", "/sbin/iwconfig", interface), self.iwconfigInfoFinished, extra_args=interface)
			else:
				self.console.ePopen(("/usr/sbin/ethtool", "/usr/sbin/ethtool", interface), self.ethtoolInfoFinished, extra_args=interface)
		for callback in self.onInformationUpdated:
			callback()

	def isBlacklisted(self, interface):
		for type in ("lo", "wifi", "wmaster", "sit", "tun", "sys", "p2p"):
			if interface.startswith(type):
				return True
		return False

	def ifconfigInfoFinished(self, result, retVal, extraArgs):  # This temporary code borrowed and adapted from the new but unreleased Network.py!
		if retVal == 0:
			capture = False
			data = ""
			if isinstance(result, bytes):
				result = result.decode("UTF-8", "ignore")
			for line in result.split("\n"):
				if line.startswith("%s " % extraArgs):
					capture = True
					if "HWaddr " in line:
						line = line.replace("HWaddr ", "HWaddr:")
					data += line
					continue
				if capture and line.startswith(" "):
					if " Scope:" in line:
						line = line.replace(" Scope:", " ")
					elif "X packets:" in line:
						pos = line.index("X packets:")
						direction = line[pos - 1:pos].lower()
						line = "%s%s" % (line[0:pos + 10], line[pos + 10:].replace(" ", "  %sx" % direction))
					elif " txqueuelen" in line:
						line = line.replace(" txqueuelen:", "  txqueuelen:")
					data += line
					continue
				if line == "":
					break
			data = list(filter(None, [x.strip().replace("=", ":", 1) for x in data.split("  ")]))
			data[0] = "interface:%s" % data[0]
			# print("[Network] DEBUG: Raw network data %s." % data)
			for item in data:
				if ":" not in item:
					flags = item.split()
					self.interfaceData[extraArgs]["up"] = True if "UP" in flags else False
					self.interfaceData[extraArgs]["status"] = "up" if "UP" in flags else "down"  # Legacy status flag.
					self.interfaceData[extraArgs]["running"] = True if "RUNNING" in flags else False
					self.interfaceData[extraArgs]["broadcast"] = True if "BROADCAST" in flags else False
					self.interfaceData[extraArgs]["multicast"] = True if "MULTICAST" in flags else False
					continue
				key, value = item.split(":", 1)
				key = self.ifconfigAttributes.get(key, None)
				if key:
					value = value.strip()
					if value.startswith("\""):
						value = value[1:-1]
					if key == "addr6":
						if key not in self.interfaceData[extraArgs]:
							self.interfaceData[extraArgs][key] = []
						self.interfaceData[extraArgs][key].append(value)
					else:
						self.interfaceData[extraArgs][key] = value
		for callback in self.onInformationUpdated:
			callback()

	def iwconfigInfoFinished(self, result, retVal, extraArgs):  # This temporary code borrowed and adapted from the new but unreleased Network.py!
		if retVal == 0:
			capture = False
			data = ""
			if isinstance(result, bytes):
				result = result.decode("UTF-8", "ignore")
			for line in result.split("\n"):
				if line.startswith("%s " % extraArgs):
					capture = True
					data += line
					continue
				if capture and line.startswith(" "):
					data += line
					continue
				if line == "":
					break
			data = list(filter(None, [x.strip().replace("=", ":", 1) for x in data.split("  ")]))
			data[0] = "interface:%s" % data[0]
			data[1] = "standard:%s" % data[1]
			for item in data:
				if ":" not in item:
					continue
				key, value = item.split(":", 1)
				key = self.iwconfigAttributes.get(key, None)
				if key:
					value = value.strip()
					if value.startswith("\""):
						value = value[1:-1]
					self.interfaceData[extraArgs][key] = value
			if "encryption" in self.interfaceData[extraArgs]:
				self.interfaceData[extraArgs]["encryption"] = _("Disabled or WPA/WPA2") if self.interfaceData[extraArgs]["encryption"] == "off" else _("Enabled")
			if "standard" in self.interfaceData[extraArgs] and "no wireless extensions" in self.interfaceData[extraArgs]["standard"]:
				del self.interfaceData[extraArgs]["standard"]
				self.interfaceData[extraArgs]["wireless"] = False
			else:
				self.interfaceData[extraArgs]["wireless"] = True
			if "ssid" in self.interfaceData[extraArgs]:
				self.interfaceData[extraArgs]["SSID"] = self.interfaceData[extraArgs]["ssid"]
		for callback in self.onInformationUpdated:
			callback()

	def ethtoolInfoFinished(self, result, retVal, extraArgs):  # This temporary code borrowed and adapted from the new but unreleased Network.py!
		if retVal == 0:
			if isinstance(result, bytes):
				result = result.decode("UTF-8", "ignore")
			for line in result.split("\n"):
				if "Speed:" in line:
					self.interfaceData[extraArgs]["speed"] = line.split(":")[1][:-4].strip()
				if "Duplex:" in line:
					self.interfaceData[extraArgs]["duplex"] = _(line.split(":")[1].strip().capitalize())
				if "Transceiver:" in line:
					self.interfaceData[extraArgs]["transeiver"] = _(line.split(":")[1].strip().capitalize())
				if "Auto-negotiation:" in line:
					self.interfaceData[extraArgs]["autoNegotiation"] = line.split(":")[1].strip().lower() == "on"
				if "Link detected:" in line:
					self.interfaceData[extraArgs]["link"] = line.split(":")[1].strip().lower() == "yes"
		for callback in self.onInformationUpdated:
			callback()

	def displayInformation(self):
		info = []
		hostname = fileReadLine("/proc/sys/kernel/hostname", source=MODULE_NAME)
		info.append(formatLine("H0H", _("Hostname"), hostname))
		for interface in sorted(list(self.interfaceData.keys())):
			info.append("")
			info.append(formatLine("H", _("Interface '%s'") % interface, iNetwork.getFriendlyAdapterName(interface)))
			if "up" in self.interfaceData[interface]:
				info.append(formatLine("P1", _("Status"), (_("Active") if self.interfaceData[interface]["up"] else _("Inactive"))))
				if self.interfaceData[interface]["up"]:
					if "addr" in self.interfaceData[interface]:
						info.append(formatLine("P1", _("IP"), self.interfaceData[interface]["addr"]))
					if "nmask" in self.interfaceData[interface]:
						info.append(formatLine("P1", _("Netmask"), self.interfaceData[interface]["nmask"]))
					if "brdaddr" in self.interfaceData[interface]:
						info.append(formatLine("P1", _("Broadcast"), self.interfaceData[interface]["brdaddr"]))
					if "addr6" in self.interfaceData[interface]:
						for addr6 in self.interfaceData[interface]["addr6"]:
							addr, scope = addr6.split()
							info.append(formatLine("P1", "IPv6 (%s)" % scope, addr))
					if "mac" in self.interfaceData[interface]:
						info.append(formatLine("P1", _("MAC"), self.interfaceData[interface]["mac"]))
					if "speed" in self.interfaceData[interface]:
						info.append(formatLine("P1", _("Speed"), "%s Mbps" % self.interfaceData[interface]["speed"]))
					if "duplex" in self.interfaceData[interface]:
						info.append(formatLine("P1", _("Duplex"), self.interfaceData[interface]["duplex"]))
					if "mtu" in self.interfaceData[interface]:
						info.append(formatLine("P1", _("MTU"), self.interfaceData[interface]["mtu"]))
					if "link" in self.interfaceData[interface]:
						info.append(formatLine("P1", _("Link detected"), (_("Yes") if self.interfaceData[interface]["link"] else _("No"))))
					if "ssid" in self.interfaceData[interface]:
						info.append(formatLine("P1", _("SSID"), self.interfaceData[interface]["ssid"]))
					if "standard" in self.interfaceData[interface]:
						info.append(formatLine("P1", _("Standard"), self.interfaceData[interface]["standard"]))
					if "encryption" in self.interfaceData[interface]:
						info.append(formatLine("P1", _("Encryption"), self.interfaceData[interface]["encryption"]))
					if "frequency" in self.interfaceData[interface]:
						info.append(formatLine("P1", _("Frequency"), self.interfaceData[interface]["frequency"]))
					if "accessPoint" in self.interfaceData[interface]:
						info.append(formatLine("P1", _("Access point"), self.interfaceData[interface]["accessPoint"]))
					if "bitrate" in self.interfaceData[interface]:
						info.append(formatLine("P1", _("Bit rate"), self.interfaceData[interface]["bitrate"]))
					if "signalQuality" in self.interfaceData[interface]:
						info.append(formatLine("P1", _("Signal quality"), self.interfaceData[interface]["signalQuality"]))
					if "signalStrength" in self.interfaceData[interface]:
						info.append(formatLine("P1", _("Signal strength"), self.interfaceData[interface]["signalStrength"]))
			if "rxBytes" in self.interfaceData[interface] or "txBytes" in self.interfaceData[interface]:
				info.append("")
				rxBytes = int(self.interfaceData[interface]["rxBytes"].split(" ")[0])
				txBytes = int(self.interfaceData[interface]["txBytes"].split(" ")[0])
				info.append(formatLine("P1", _("Bytes received"), "%d (%s)" % (rxBytes, scaleNumber(rxBytes, style="Iec", format="%.1f"))))
				info.append(formatLine("P1", _("Bytes sent"), "%d (%s)" % (txBytes, scaleNumber(txBytes, style="Iec", format="%.1f"))))
		info += self.geolocationData
		self["information"].setText("\n".join(info).encode("UTF-8", "ignore") if PY2 else "\n".join(info))


class ReceiverInformation(InformationBase):
	def __init__(self, session):
		InformationBase.__init__(self, session)
		self.setTitle(_("Receiver Information"))
		self.skinName.insert(0, "ReceiverInformation")
		self["key_yellow"] = StaticText(_("System"))
		self["key_blue"] = StaticText(_("Logs"))
		self["receiverActions"] = HelpableActionMap(self, ["ColorActions"], {
			"yellow": (self.showSystem, _("Show system information")),
			"blue": (self.showLogs, _("Show logs"))
		}, prio=0, description=_("Receiver Information Actions"))

	def showSystem(self):
		self.session.openWithCallback(self.informationWindowClosed, SystemInformation)

	def showLogs(self):
		self.session.openWithCallback(self.informationWindowClosed, SystemInformationLogs)

	def displayInformation(self):
		info = []
		info.append(formatLine("H", _("Hardware information")))
		info.append(formatLine("P1", _("Receiver name"), "%s %s" % (BoxInfo.getItem("displaybrand"), BoxInfo.getItem("displaymodel"))))
		info.append(formatLine("P1", _("Build Brand"), BoxInfo.getItem("brand")))
		platform = BoxInfo.getItem("platform")
		model = BoxInfo.getItem("model")
		info.append(formatLine("P1", _("Build Model"), model))
		if platform != model:
			info.append(formatLine("P1", _("Platform"), platform))
		procModel = getBoxProc()
		if procModel != model:
			info.append(formatLine("P1", _("Proc model"), procModel))
		procModelType = getBoxProcTypeName()
		if procModelType and procModelType != "unknown":
			info.append(formatLine("P1", _("Hardware type"), procModelType))
		hwSerial = getHWSerial()
		if hwSerial:
			info.append(formatLine("P1", _("Hardware serial"), (hwSerial if hwSerial != "unknown" else about.getCPUSerial())))
		hwRelease = fileReadLine("/proc/stb/info/release", source=MODULE_NAME)
		if hwRelease:
			info.append(formatLine("P1", _("Factory release"), hwRelease))
		displaytype = BoxInfo.getItem("displaytype").startswith(" ")
		if displaytype and not displaytype.startswith(" "):
			info.append(formatLine("P1", _("Display type"), displaytype))
		fpVersion = getFPVersion()
		if fpVersion and fpVersion != "unknown":
			info.append(formatLine("P1", _("Front processor version"), fpVersion))
		transcoding = _("Yes") if BoxInfo.getItem("transcoding") else _("MultiTranscoding") if BoxInfo.getItem("multitranscoding") else _("No")
		info.append(formatLine("P1", _("Transcoding"), transcoding))
		temp = about.getSystemTemperature()
		if temp:
			info.append(formatLine("P1", _("System temperature"), temp))
		info.append("")
		info.append(formatLine("H", _("Processor information")))
		cpu = about.getCPUInfoString()
		info.append(formatLine("P1", _("CPU"), cpu[0]))
		info.append(formatLine("P1", _("CPU speed/cores"), "%s %s" % (cpu[1], cpu[2])))
		if cpu[3]:
			info.append(formatLine("P1", _("CPU temperature"), cpu[3]))
		info.append(formatLine("P1", _("CPU brand"), about.getCPUBrand()))
		socFamily = BoxInfo.getItem("socfamily")
		if socFamily:
			info.append(formatLine("P1", _("SoC family"), socFamily))
		info.append(formatLine("P1", _("CPU architecture"), about.getCPUArch()))
		if BoxInfo.getItem("fpu"):
			info.append(formatLine("P1", _("FPU"), BoxInfo.getItem("fpu")))
		if BoxInfo.getItem("architecture") == "aarch64":
			info.append(formatLine("P1", _("MultiLib"), (_("Yes") if BoxInfo.getItem("multilib") else _("No"))))
		info.append("")
		info.append(formatLine("H", _("Remote control information")))
		rcIndex = int(config.inputDevices.remotesIndex.value)
		info.append(formatLine("P1", _("RC identification"), "%s  (Index: %d)" % (remoteControl.remotes[rcIndex][REMOTE_DISPLAY_NAME], rcIndex)))
		rcName = remoteControl.remotes[rcIndex][REMOTE_NAME]
		info.append(formatLine("P1", _("RC selected name"), rcName))
		boxName = BoxInfo.getItem("rcname")
		if boxName != rcName:
			info.append(formatLine("P1", _("RC default name"), boxName))
		rcType = remoteControl.remotes[rcIndex][REMOTE_RCTYPE]
		info.append(formatLine("P1", _("RC selected type"), rcType))
		boxType = BoxInfo.getItem("rctype")
		if boxType != rcType:
			info.append(formatLine("P1", _("RC default type"), boxType))
		boxRcType = getBoxRCType()
		if boxRcType:
			if boxRcType == "unknown":
				if isfile("/usr/bin/remotecfg"):
					boxRcType = _("Amlogic remote")
				elif isfile("/usr/sbin/lircd"):
					boxRcType = _("LIRC remote")
			if boxRcType != rcType and boxRcType != "unknown":
				info.append(formatLine("P1", _("RC detected type"), boxRcType))
		customCode = fileReadLine("/proc/stb/ir/rc/customcode", source=MODULE_NAME)
		if customCode:
			info.append(formatLine("P1", _("RC custom code"), customCode))
		if BoxInfo.getItem("HasHDMI-CEC") and config.hdmicec.enabled.value:
			info.append("")
			address = config.hdmicec.fixed_physical_address.value if config.hdmicec.fixed_physical_address.value != "0.0.0.0" else _("N/A")
			info.append(formatLine("P1", _("HDMI-CEC address"), address))
		info.append("")
		info.append(formatLine("H", _("Driver and kernel information")))
		info.append(formatLine("P1", _("Drivers version"), convertDate(getDriverDate())))
		info.append(formatLine("P1", _("Kernel version"), BoxInfo.getItem("kernel")))
		deviceId = fileReadLine("/proc/device-tree/amlogic-dt-id", source=MODULE_NAME)
		if deviceId:
			info.append(formatLine("P1", _("Device id"), deviceId))
		givenId = fileReadLine("/proc/device-tree/le-dt-id", source=MODULE_NAME)
		if givenId:
			info.append(formatLine("P1", _("Given device id"), givenId))
		info.append("")
		info.append(formatLine("H", _("Tuner information")))
		nims = nimmanager.nimListCompressed()
		for count in range(len(nims)):
			tuner, type = [x.strip() for x in nims[count].split(":", 1)]
			info.append(formatLine("P1", tuner, type))
		info.append("")
		info.append(formatLine("H", _("Drives information")))
		stat = statvfs("/")
		diskSize = stat.f_blocks * stat.f_frsize
		info.append(formatLine("P1", _("Internal flash"), "%s  (%s)" % (scaleNumber(diskSize), scaleNumber(diskSize, "Iec"))))
		hddList = harddiskmanager.HDDList()
		if hddList:
			for hdd in hddList:
				hdd = hdd[1]
				capacity = hdd.diskSize() * 1000000
				info.append(formatLine("P1", hdd.model(), "%s  (%s)" % (scaleNumber(capacity), scaleNumber(capacity, "Iec"))))
		else:
			info.append(formatLine("H", _("No hard disks detected.")))
		info.append("")
		info.append(formatLine("H", _("Network information")))
		for x in about.GetIPsFromNetworkInterfaces():
			info.append(formatLine("P1", x[0], x[1]))
		info.append("")
		info.append(formatLine("H", _("Uptime"), about.getBoxUptime()))
		if BoxInfo.getItem("HiSilicon"):
			info.append("")
			info.append(formatLine("H", _("HiSilicon specific information")))
			#info.append("")
			process = Popen(("/usr/bin/opkg", "list-installed"), stdout=PIPE, stderr=PIPE, universal_newlines=True)
			stdout, stderr = process.communicate()
			if process.returncode == 0:
				missing = True
				packageList = stdout.split("\n")
				revision = self.findPackageRevision("grab", packageList)
				if revision and revision != "r0":
					info.append(formatLine("P1", _("Grab"), revision))
					missing = False
				revision = self.findPackageRevision("hihalt", packageList)
				if revision:
					info.append(formatLine("P1", _("Halt"), revision))
					missing = False
				revision = self.findPackageRevision("libs", packageList)
				if revision:
					info.append(formatLine("P1", _("Libs"), revision))
					missing = False
				revision = self.findPackageRevision("partitions", packageList)
				if revision:
					info.append(formatLine("P1", _("Partitions"), revision))
					missing = False
				revision = self.findPackageRevision("reader", packageList)
				if revision:
					info.append(formatLine("P1", _("Reader"), revision))
					missing = False
				revision = self.findPackageRevision("showiframe", packageList)
				if revision:
					info.append(formatLine("P1", _("Showiframe"), revision))
					missing = False
				if missing:
					info.append(formatLine("P1", _("HiSilicon specific information not found.")))
			else:
				info.append(formatLine("P1", _("Package information currently not available!")))
		self["information"].setText("\n".join(info))

	def getSummaryInformation(self):
		return "Receiver Information"

	def findPackageRevision(self, package, packageList):
		revision = None
		data = [x for x in packageList if "-%s" % package in x]
		if data:
			data = data[0].split("-")
			if len(data) >= 4:
				revision = data[3]
		return revision


class DrivesInformation(InformationBase):
	def __init__(self, session):
		InformationBase.__init__(self, session)
		self.setTitle(_("Drives Information"))
		self.skinName.insert(0, "DrivesInformation")
		self["information"].setText(_("Retrieving network server information, please wait..."))
		self.mountInfo = []

	def fetchInformation(self):
		self.informationTimer.stop()
		self.console.ePopen("df -mh | grep -v '^Filesystem'", self.fetchComplete)
		for callback in self.onInformationUpdated:
			callback()

	def fetchComplete(self, result, retVal, extraArgs=None):
		result = result.replace("\n                        ", " ").split("\n")
		self.mountInfo = []
		for line in result:
			line = line.strip()
			if not line:
				continue
			data = line.split()
			if data[0].startswith("192") or data[0].startswith("//192"):
				# data[0] = ipAddress, data[1] = mountTotal, data[2] = mountUsed, data[3] = mountFree, data[4] = percetageUsed, data[5] = mountPoint.
				self.mountInfo.append(data)
		if isdir("/media/autofs"):
			for entry in sorted(listdir("/media/autofs")):
				path = pathjoin("/media/autofs", entry)
				keep = True
				for data in self.mountInfo:
					if data[5] == path:
						keep = False
						break
				if keep:
					self.mountInfo.append(["", 0, 0, 0, "N/A", path])
		for callback in self.onInformationUpdated:
			callback()

	def displayInformation(self):
		info = []
		info.append(formatLine("H", _("Detected drives")))
		partitions = sorted(harddiskmanager.getMountedPartitions(), key=lambda x: x.device or "")
		for partition in partitions:
			if partition.mountpoint == "/":
				info.append(formatLine("H1", "/dev/root", partition.description))
				stat = statvfs("/")
				diskSize = stat.f_blocks * stat.f_frsize
				diskFree = stat.f_bfree * stat.f_frsize
				diskUsed = diskSize - diskFree
				info.append(formatLine("P2", _("Mountpoint"), partition.mountpoint))
				info.append(formatLine("P2", _("Capacity"), "%s  (%s)" % (scaleNumber(diskSize), scaleNumber(diskSize, "Iec"))))
				info.append(formatLine("P2", _("Used"), "%s  (%s)" % (scaleNumber(diskUsed), scaleNumber(diskUsed, "Iec"))))
				info.append(formatLine("P2", _("Free"), "%s  (%s)" % (scaleNumber(diskFree), scaleNumber(diskFree, "Iec"))))
				break
		hddList = harddiskmanager.HDDList()
		if hddList:
			for hdd in hddList:
				hdd = hdd[1]
				info.append("")
				info.append(formatLine("H1", hdd.getDeviceName(), hdd.bus()))
				info.append(formatLine("P2", _("Model"), hdd.model()))
				diskSize = int(hdd.diskSize() * 1000000)
				info.append(formatLine("P2", _("Capacity"), "%s  (%s)" % (scaleNumber(diskSize), scaleNumber(diskSize, "Iec"))))
				info.append(formatLine("P2", _("Sleeping"), (_("Yes") if hdd.isSleeping() else _("No"))))
				for partition in partitions:
					if partition.device and pathjoin("/dev", partition.device).startswith(hdd.getDeviceName()):
						info.append(formatLine("P2", _("Partition"), partition.device))
						stat = statvfs(partition.mountpoint)
						diskSize = stat.f_blocks * stat.f_frsize
						diskFree = stat.f_bfree * stat.f_frsize
						diskUsed = diskSize - diskFree
						info.append(formatLine("P3", _("Mountpoint"), partition.mountpoint))
						info.append(formatLine("P3", _("Capacity"), "%s  (%s)" % (scaleNumber(diskSize), scaleNumber(diskSize, "Iec"))))
						info.append(formatLine("P3", _("Used"), "%s  (%s)" % (scaleNumber(diskUsed), scaleNumber(diskUsed, "Iec"))))
						info.append(formatLine("P3", _("Free"), "%s  (%s)" % (scaleNumber(diskFree), scaleNumber(diskFree, "Iec"))))
		else:
			info.append("")
			info.append(formatLine("H1", _("No hard disks detected.")))
		info.append("")
		info.append(formatLine("H", _("Detected network servers")))
		if self.mountInfo:
			for data in self.mountInfo:
				info.append(formatLine("H1", data[5]))
				if data[0]:
					info.append(formatLine("P2", _("Network address"), data[0]))
					info.append(formatLine("P2", _("Capacity"), data[1]))
					info.append(formatLine("P2", _("Used"), "%s  (%s)" % (data[2], data[4])))
					info.append(formatLine("P2", _("Free"), data[3]))
				else:
					info.append(formatLine("P2", _("Not currently mounted.")))
		else:
			info.append("")
			info.append(formatLine("P1", _("No network servers detected.")))
		self["information"].setText("\n".join(info))


class SystemInformation(InformationBase):
	def __init__(self, session):
		InformationBase.__init__(self, session)
		self.baseTitle = _("System Information")
		self.setTitle(self.baseTitle)
		self.skinName.insert(0, "SystemInformation")
		self["key_yellow"] = StaticText()
		self["key_blue"] = StaticText()
		self["systemMenuActions"] = HelpableActionMap(self, ["MenuActions"], {
			"menu": (self.selectDiagnostic, _("Show selection for system information screen")),
		}, prio=0, description=_("System Information Actions"))
		self["systemLogActions"] = HelpableActionMap(self, ["DirectionActions"], {
			"moveUp": (self.previousDiagnostic, _("Display previous system information screen")),
			"moveDown": (self.nextDiagnostic, _("Display next system information screen")),
		}, prio=0, description=_("System Information Actions"))
		self["logfileActions"] = HelpableActionMap(self, ["ColorActions"], {
			"yellow": (self.deleteLog, _("Delete the currently displayed log file")),
			"blue": (self.deleteAllLogs, _("Delete all log files"))
		}, prio=0, description=_("System Information Actions"))
		self["logfileActions"].setEnabled(False)
		self["number_actions"] = HelpableNumberActionMap(self, ["NumberActions"], {
			str(i): (self.selectDiagnosticNumber, _("Enter number to select screen")) for i in range(10)
		}, prio=0, description=_("System Information Actions"))
		self.commands = []
		self.numberOfCommands = 0
		self.commandIndex = 0
		self.commandData = ""
		self.shortTitle = False
		self.container = eConsoleAppContainer()
		self.container.dataAvail.append(self.dataAvail)
		self.container.appClosed.append(self.appClosed)
		self.log = _("Retrieving system information, please wait...")
		self["description"].setText(_("Press <> or menu to select the different info screens"))

	def selectDiagnosticNumber(self, number):
		self.commandIndex = number % len(self.commands)
		self.refreshInformation()

	def selectDiagnostic(self):
		choices = [(cmd[0], str(idx)) for idx, cmd in enumerate(self.commands)]
		self.session.openWithCallback(self.selectDiagnosticCallBack, ChoiceBox, title=_("Select information screen"), list=choices)

	def selectDiagnosticCallBack(self, selected):
		if selected:
			self.commandIndex = int(selected[1]) % len(self.commands)
			self.refreshInformation()

	def previousDiagnostic(self):
		self.commandIndex = (self.commandIndex - 1) % len(self.commands)
		self.refreshInformation()

	def nextDiagnostic(self):
		self.commandIndex = (self.commandIndex + 1) % len(self.commands)
		self.refreshInformation()

	def deleteLog(self):
		if self.commandIndex >= self.numberOfCommands:
			self.session.openWithCallback(self.removeLog, MessageBox, _("Do you want to delete this log file?"), default=False)

	def removeLog(self, answer):
		if answer:
			try:
				args = self.commands[self.commandIndex][1].split()
				remove(args[-1])
				self.session.open(MessageBox, _("Log file '%s' deleted.") % args[-1], type=MessageBox.TYPE_INFO, timeout=5, close_on_any_key=True, title=self.baseTitle)
			except OSError as err:
				self.session.open(MessageBox, _("Log file '%s' deleted.") % args[-1], type=MessageBox.TYPE_ERROR, timeout=5, title=self.baseTitle)
			self.informationTimer.start(25)
			for callback in self.onInformationUpdated:
				callback()

	def deleteAllLogs(self):
		if self.commandIndex >= self.numberOfCommands:
			self.session.openWithCallback(self.removeAllLogs, MessageBox, _("Do you want to delete all log files?"), default=False)

	def removeAllLogs(self, answer):
		if answer:
			filenames = [x for x in sorted(glob("/mnt/hdd/*.log"), key=lambda x: isfile(x) and getmtime(x))]
			filenames += [x for x in sorted(glob("/home/root/logs/enigma2_crash*.log"), key=lambda x: isfile(x) and getmtime(x))]
			filenames += [x for x in sorted(glob("/home/root/logs/Enigma2-debug*.log"), key=lambda x: isfile(x) and getmtime(x))]
			log = []
			type = MessageBox.TYPE_INFO
			close = True
			for filename in filenames:
				try:
					remove(filename)
					log.append(_("Log file '%s' deleted.") % filename)
				except OSError as err:
					type = MessageBox.TYPE_ERROR
					close = False
					log.append(_("Error %d: Log file '%s' wasn't deleted!  (%s)") % (err.errno, filename, err.strerror))
			log = "\n".join(log)
			self.session.open(MessageBox, log, type=type, timeout=5, close_on_any_key=close, title=self.baseTitle)
			self.informationTimer.start(25)
			for callback in self.onInformationUpdated:
				callback()

	def keyCancel(self):
		self.container.dataAvail.remove(self.dataAvail)
		self.container.appClosed.remove(self.appClosed)
		self.container = None
		InformationBase.keyCancel(self)

	def closeRecursive(self):
		self.container.dataAvail.remove(self.dataAvail)
		self.container.appClosed.remove(self.appClosed)
		self.container = None
		InformationBase.closeRecursive(self)

	def fetchInformation(self):
		self.informationTimer.stop()
		self.commands = [
#			("cpu", "/bin/cat /proc/cpuinfo | sed 's/\t\t/\t/'", "cpu"),
#			("edid", "/bin/cat /proc/stb/hdmi/raw_edid | edid-decode", "edid"),
			("dmesg", "/bin/dmesg", "dmesg"),
			("ifconfig", "/sbin/ifconfig", "ifconfig"),
			("df", "/bin/df -h", "df"),
			("top", "/usr/bin/top -b -n 1", "top"),
			("ps", "/bin/ps -l", "ps"),
			("mount", "/bin/mount", "mount"),
			("partitions", "/bin/cat /proc/partitions", "partitions"),
			("modules", "/bin/cat /proc/modules", "modules"),
			("build", "build", "build"),
		]
		if BoxInfo.getItem("HAVEEDIDDECODE"):
			self.commands.append(("edid", "/bin/cat /proc/stb/hdmi/raw_edid | edid-decode", "edid"))

		self.numberOfCommands = len(self.commands)
		self.commandIndex = min(len(self.commands) - 1, self.commandIndex)
		self.refreshInformation()

	def refreshInformation(self):
		command = self.commands[self.commandIndex][1]
		if command == "build":
			self.setTitle(_("Build Information"))
			self.displayBuildInformation()
			return
		self.log = _("Retrieving system information, please wait...")
		if self.shortTitle:
			self.setTitle(self.commands[self.commandIndex][0])
		else:
			self.setTitle("%s - %s" % (self.baseTitle, self.commands[self.commandIndex][0]))
		args = command.split()  # For safety don't use a shell command line!
		if args[0] == "/bin/cat" and "|" not in command:
			try:
				with open(args[1], "rb") as fd:
					data = fd.read()
				data = data.decode("UTF-8", "ignore")
				self.log = data
			except OSError as err:
				self.log = _("Error %d: The logfile '%s' could not be opened.  (%s)") % (err.errno, args[1], err.strerror)
		else:
			self.commandData = "" #"CUT" if self.commands[self.commandIndex][0] in ["mount", "modules"] else ""
			args.insert(0, args[0])
			if "|" in command:
				retVal = self.container.execute(command)
			else:
				retVal = self.container.execute(*args)
			pid = self.container.getPID()
			# print("[Information] DEBUG: System logs PID=%d." % pid)
			# try:
			# 	waitpid(pid, 0)
			# except OSError as err:
			# 	pass
		if self.commandIndex >= self.numberOfCommands:
			self["key_yellow"].text = _("Delete logfile")
			self["key_blue"].text = _("Delete all logfiles")
			self["logfileActions"].setEnabled(True)
		else:
			self["key_yellow"].text = ""
			self["key_blue"].text = ""
			self["logfileActions"].setEnabled(False)
		for callback in self.onInformationUpdated:
			callback()

	def dataAvail(self, data):
		if isinstance(data, bytes):
			data = data.decode("UTF-8", "ignore")
		self.commandData += data

	def cutData(self):
		if self.commandData[:3] == "CUT":
			text = ""
			for line in self.commandData.split("\n"):
				text = text + line[:95] + "\n"
			if text[-1:] == "\n":
				text = text[:-1]
			return text
		else:
			return self.commandData

	def appClosed(self, retVal):
		self.log = self.cutData()
		if retVal:
			self.log += "\n\n%s" % (_("An error occurred, error code %d, please try again later.") % retVal)
		for callback in self.onInformationUpdated:
			callback()

	def displayInformation(self):
		if not self.log:
			self.log = _("The '%s' log file contains no information.") % self.commands[self.commandIndex][2]
		self["information"].setText(self.log)

	def displayBuildInformation(self):
		info = []
		info.append(formatLine("H", "%s %s %s" % (_("Build information for"), BoxInfo.getItem("displaybrand"), BoxInfo.getItem("displaymodel"))))
		checksum = BoxInfo.getItem("checksumerror", False)
		if checksum:
			info.append(formatLine("M1", _("Error: Checksum is invalid!")))
		override = BoxInfo.getItem("overrideactive", False)
		if override:
			info.append(formatLine("M1", _("Warning: Overrides are currently active!")))
		if checksum or override:
			info.append("")
		for item in BoxInfo.getEnigmaInfoList():
			info.append(formatLine("P1", item, BoxInfo.getItem(item)))
		self["information"].setText("\n".join(info))


class SystemInformationLogs(SystemInformation):
	def __init__(self, session):
		SystemInformation.__init__(self, session)
		self.shortTitle = True

	def fetchInformation(self):
		self.informationTimer.stop()
		self.commands = [
			("messages", "/bin/cat /var/volatile/log/messages", "messages")
		]
		self.numberOfCommands = len(self.commands)
		#
		# TODO: Need to adjust path of log files to match current configurations!
		#
		installLog = "/home/root/autoinstall.log"
		if isfile(installLog):
			self.commands.append((_("Auto install log"), "/bin/cat %s" % installLog, installLog))
			self.numberOfCommands += 1
		crashLog = "/tmp/enigma2_crash.log"
		if isfile(crashLog):
			self.commands.append((_("Current crash log"), "/bin/cat %s" % crashLog, crashLog))
			self.numberOfCommands += 1
		filenames = [x for x in sorted(glob("/mnt/hdd/*.log"), key=lambda x: isfile(x) and getmtime(x))]
		if filenames:
			totalNumberOfLogfiles = len(filenames)
			logfileCounter = 1
			for filename in reversed(filenames):
				self.commands.append((_("Logfile '%s' (%d/%d)") % (basename(filename), logfileCounter, totalNumberOfLogfiles), "/bin/cat %s" % filename, filename))
				logfileCounter += 1
		filenames = [x for x in sorted(glob("/home/root/logs/enigma2_crash*.log"), key=lambda x: isfile(x) and getmtime(x))]
		if filenames:
			totalNumberOfLogfiles = len(filenames)
			logfileCounter = 1
			for filename in reversed(filenames):
				self.commands.append((_("Crash log '%s' (%d/%d)") % (basename(filename), logfileCounter, totalNumberOfLogfiles), "/bin/cat %s" % filename, filename))
				logfileCounter += 1
		filenames = [x for x in sorted(glob("/home/root/logs/Enigma2-debug*.log"), key=lambda x: isfile(x) and getmtime(x))]
		if filenames:
			totalNumberOfLogfiles = len(filenames)
			logfileCounter = 1
			for filename in reversed(filenames):
				self.commands.append((_("Debug log '%s' (%d/%d)") % (basename(filename), logfileCounter, totalNumberOfLogfiles), "/usr/bin/tail -n 1000 %s" % filename, filename))
				logfileCounter += 1
		self.commandIndex = min(len(self.commands) - 1, self.commandIndex)
		self.refreshInformation()		


class TranslationInformation(InformationBase):
	def __init__(self, session):
		InformationBase.__init__(self, session)
		self.setTitle(_("Translation Information"))
		self.skinName.insert(0, "TranslationInformation")

	def displayInformation(self):
		info = []
		translateInfo = _("TRANSLATOR_INFO")
		if translateInfo != "TRANSLATOR_INFO":
			info.append(formatLine("H", _("Translation information")))
			translateInfo = translateInfo.split("\n")
			for translate in translateInfo:
				info.append(formatLine("P1", translate))
			info.append("")
		translateInfo = _("").split("\n")  # This is deliberate to dump the translation information.
		for translate in translateInfo:
			if not translate:
				continue
			translate = [x.strip() for x in translate.split(":", 1)]
			if len(translate) == 1:
				translate.append("")
			info.append(formatLine("P1", translate[0], translate[1]))
		self["information"].setText("\n".join(info))

	def getSummaryInformation(self):
		return "Translation Information"


class TunerInformation(InformationBase):
	def __init__(self, session):
		InformationBase.__init__(self, session)
		self.setTitle(_("Tuner Information"))
		self.skinName.insert(0, "TunerInformation")

	def displayInformation(self):
		allsystems = ["DVB-S", "DVB-S2", "DVB-C", "DVB-T", "DVB-T2"]
		info = []
		info.append(formatLine("H", _("Detected tuners")))
		info.append("")
		nims = nimmanager.nimList()
		descList = []
		curIndex = -1
		for count in range(len(nims)):
			data = nims[count].split(":")
			idx = data[0].strip("Tuner").strip()
			desc = data[1].strip()
			if descList and descList[curIndex]["desc"] == desc:
				descList[curIndex]["end"] = idx
			else:
				descList.append({
					"desc": desc,
					"start": idx,
					"end": idx,
					"info" : eDVBResourceManager.getInstance().getFrontendCapabilities(count).splitlines()
				})
				curIndex += 1
			count += 1
		for count in range(len(descList)):
			data = descList[count]["start"] if descList[count]["start"] == descList[count]["end"] else ("%s-%s" % (descList[count]["start"], descList[count]["end"]))
			info.append(formatLine("P1", "Tuner %s" % data))
			try:
				# TUNER Info
				info.append(formatLine("P2", _("Name") , descList[count]["desc"]))
				frontend = descList[count]["info"]
				frequency = frontend[2].split(":")
				frequencyvalue = formatMinMax(frequency[1])
				symbolrate = frontend[3].split(":")
				symbolratevalue = formatMinMax(symbolrate[1])
				capabilities = frontend[4].split(":")[1]
				deliverysystem = frontend[5].split(":")[1]
				systems = []
				for system in allsystems:
					if system.replace("-", "") in deliverysystem:
						systems.append(system)
				if systems:
					info.append(formatLine("P2", _("Systems"), ", ".join(systems)))
				info.append(formatLine("P2", _("Multistream"), (_("Yes") if "MULTISTREAM" in capabilities else _("No"))))
				if frequencyvalue:
					info.append(formatLine("P2", _(frequency[0]), frequencyvalue))
				if symbolratevalue:
					info.append(formatLine("P2", _(symbolrate[0]), symbolratevalue))
				info.append("")
			except Exception as e:
				print("[Information] Error get frontends %s" % str(e))
				pass
		self["information"].setText("\n".join(info))
		return

	def tunerInfo(self):
		info = []
		return info

	def getSummaryInformation(self):
		return "DVB Information"


class StreamingInformation(InformationBase):
	def __init__(self, session):
		InformationBase.__init__(self, session)
		self.setTitle(_("Streaming Clients"))
		self.skinName.insert(0, "StreamingInformation")
		self.refreshTimer = eTimer()
		self["key_green"].text = ""
		self["key_blue"] = StaticText()
		self["streamActions"] = HelpableActionMap(self, ["ColorActions"], {
			"blue": (self.stopStreams, _("Stop Streams"))
		}, prio=0, description=_("Streaming Information Actions"))

	def stop(self):
		if self.displayInformation in self.refreshTimer.callback:
			self.refreshTimer.callback.remove(self.displayInformation)
		self.refreshTimer.stop()

	def displayInformation(self):
		if self.displayInformation not in self.refreshTimer.callback:
			self.refreshTimer.callback.append(self.displayInformation)
			self.refreshTimer.startLongTimer(0)
		info = []
		info.append(formatLine("H", _("Active Streaming Clients")))
		info.append("")
		clients = ClientsStreaming("DATA").getText()
		if clients:
			pos = 0
			for client in clients:
				pos = pos + 1
				info.append(formatLine("P1", "%s - %d" % (_("Client"), pos)))
				info.append(formatLine("P2", _("ServiceName"), client[1]))
				info.append(formatLine("P2", _("IP"), client[0]))
				info.append(formatLine("P2", _("Transcoding"), client[2]))
				info.append("")
		else:
			info.append(formatLine("P1", _("No clients streaming")))
		self["information"].setText("\n".join(info))
		self["key_blue"].setText(_("Stop Streams") if clients else "")
		self.refreshTimer.startLongTimer(5)

	def keyCancel(self):
		self.stop()
		InformationBase.keyCancel(self)

	def closeRecursive(self):
		self.stop()
		InformationBase.closeRecursive(self)

	def stopStreams(self):
		streamServer = eStreamServer.getInstance()
		if not streamServer:
			return
		for x in streamServer.getConnectedClients():
			streamServer.stopStream()

	def getSummaryInformation(self):
		return "Translation Information"


class InformationSummary(ScreenSummary):
	def __init__(self, session, parent):
		ScreenSummary.__init__(self, session, parent=parent)
		self.parent = parent
		self["information"] = StaticText()
		parent.onInformationUpdated.append(self.updateSummary)
		# self.updateSummary()

	def updateSummary(self):
		# print("[Information] DEBUG: Updating summary.")
		self["information"].setText(self.parent.getSummaryInformation())
