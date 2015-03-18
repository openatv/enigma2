from boxbranding import getMachineBrand

from enigma import ePicLoad, eTimer, getDesktop, gMainDC, eSize

from Screens.Screen import Screen
from Screens.HelpMenu import HelpableScreen
from Tools.Directories import resolveFilename, pathExists, SCOPE_MEDIA
from Tools.HardwareInfo import HardwareInfo
from Components.About import about
from Components.Pixmap import Pixmap, MovingPixmap
from Components.Label import Label
from Components.ActionMap import ActionMap, HelpableActionMap
from Components.Sources.StaticText import StaticText
from Components.FileList import FileList
from Components.AVSwitch import AVSwitch
from Components.Sources.List import List
from Components.ConfigList import ConfigListScreen
from Components.config import config, ConfigSubsection, ConfigInteger, ConfigSelection, ConfigText, ConfigYesNo, getConfigListEntry
from Screens.LocationBox import defaultInhibitDirs

def getScale():
	return AVSwitch().getFramebufferScale()

config.pic = ConfigSubsection()
config.pic.framesize = ConfigInteger(default=30, limits=(0, 99))
config.pic.slidetime = ConfigInteger(default=5, limits=(1, 60))
config.pic.resize = ConfigSelection(default="1", choices=[("0", _("simple")), ("1", _("better"))])
config.pic.cache = ConfigYesNo(default=True)
config.pic.lastDir = ConfigText(default=resolveFilename(SCOPE_MEDIA))
config.pic.infoline = ConfigYesNo(default=True)
config.pic.loop = ConfigYesNo(default=True)
config.pic.bgcolor = ConfigSelection(default="#00000000", choices=[("#00000000", _("black")), ("#009eb9ff", _("blue")), ("#00ff5a51", _("red")), ("#00ffe875", _("yellow")), ("#0038FF48", _("green"))])
config.pic.textcolor = ConfigSelection(default="#0038FF48", choices=[("#00000000", _("black")), ("#009eb9ff", _("blue")), ("#00ff5a51", _("red")), ("#00ffe875", _("yellow")), ("#0038FF48", _("green"))])

class picshow(Screen):
	skin = """
		<screen name="picshow" position="center,center" size="560,440" title="Picture player" >
			<ePixmap pixmap="buttons/red.png" position="0,0" size="140,40" alphatest="on" />
			<ePixmap pixmap="buttons/green.png" position="140,0" size="140,40" alphatest="on" />
			<ePixmap pixmap="buttons/yellow.png" position="280,0" size="140,40" alphatest="on" />
			<widget source="key_red" render="Label" position="0,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" transparent="1" />
			<widget source="key_green" render="Label" position="140,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" transparent="1" />
			<widget source="key_yellow" render="Label" position="280,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#a08500" transparent="1" />
			<widget source="label" render="Label" position="5,55" size="350,140" font="Regular;19" backgroundColor="#25062748" transparent="1"  />
			<widget name="thn" position="360,40" size="180,160" alphatest="on" />
			<widget name="filelist" position="5,205" zPosition="2" size="550,230" scrollbarMode="showOnDemand" />
		</screen>"""

	def __init__(self, session):
		Screen.__init__(self, session)

		self["actions"] = ActionMap(["OkCancelActions", "ColorActions", "DirectionActions", "MenuActions"], {
			"cancel": self.KeyExit,
			"red": self.KeyExit,
			"green": self.KeyGreen,
			"yellow": self.KeyYellow,
			"blue": self.KeyBlue,
			"ok": self.KeyOk
		}, -1)

		self["key_red"] = StaticText(_("Close"))
		self["key_green"] = StaticText(_("Thumbnails"))
		self["key_yellow"] = StaticText("")
		self["key_blue"] = StaticText(_("Slideshow"))

		self["label"] = StaticText("")
		self["thn"] = Pixmap()

		currDir = config.pic.lastDir.value
		if not pathExists(currDir):
			currDir = config.pic.lastDir.default
			if not pathExists(currDir):
				currDir = "/"

		self.filelist = FileList(currDir, matchingPattern="(?i)^.*\.(jpeg|jpg|jpe|png|bmp|gif)", inhibitDirs=defaultInhibitDirs)
		self["filelist"] = self.filelist
		self["filelist"].onSelectionChanged.append(self.selectionChanged)

		self.ThumbTimer = eTimer()
		self.ThumbTimer.callback.append(self.showThumb)

		self.picload = ePicLoad()
		self.picload.PictureData.get().append(self.showPic)

		self.onLayoutFinish.append(self.setConf)

	def showPic(self, picInfo=""):
		ptr = self.picload.getData()
		if ptr is not None:
			self["thn"].instance.setPixmap(ptr.__deref__())
			self["thn"].show()

		text = picInfo.split('\n', 1)
		self["label"].setText(text[1])
		self["key_yellow"].setText(_("Information"))

	def showThumb(self):
		if not self.filelist.canDescent():
			if self.filelist.getCurrentDirectory() and self.filelist.getFilename():
				if self.picload.getThumbnail(self.filelist.getCurrentDirectory() + self.filelist.getFilename()) == 1:
					self.ThumbTimer.start(500, True)

	def selectionChanged(self):
		if not self.filelist.canDescent():
			self.ThumbTimer.start(500, True)
		else:
			self["label"].setText("")
			self["thn"].hide()
			self["key_yellow"].setText("")

	def KeyGreen(self):
		# if not self.filelist.canDescent():
		self.session.openWithCallback(self.callbackView, Pic_Thumb, self.filelist.getFileList(), self.filelist.getSelectionIndex(), self.filelist.getCurrentDirectory())

	def KeyYellow(self):
		if not self.filelist.canDescent():
			self.session.open(Pic_Exif, self.picload.getInfo(self.filelist.getCurrentDirectory() + self.filelist.getFilename()))

	def KeyBlue(self):
		if self.filelist.canDescent():
			self.filelist.descent()
		else:
			self.session.openWithCallback(self.callbackView, Pic_Full_View, self.filelist.getFileList(), self.filelist.getSelectionIndex(), self.filelist.getCurrentDirectory())

	def KeyOk(self):
		if self.filelist.canDescent():
			self.filelist.descent()
		else:
			self.session.openWithCallback(self.callbackView, Pic_Full_View, self.filelist.getFileList(), self.filelist.getSelectionIndex(), self.filelist.getCurrentDirectory())

	def setConf(self, retval=None):
		self.setTitle(_("Picture player"))
		sc = getScale()
		# 0=Width 1=Height 2=Aspect 3=use_cache 4=resize_type 5=Background(#AARRGGBB)
		self.picload.setPara((self["thn"].instance.size().width(), self["thn"].instance.size().height(), sc[0], sc[1], config.pic.cache.value, int(config.pic.resize.value), "#00000000"))

	def callbackView(self, val=0):
		if val > 0:
			self.filelist.moveToIndex(val)

	def KeyExit(self):
		del self.picload

		if self.filelist.getCurrentDirectory() is None:
			config.pic.lastDir.value = "/"
		else:
			config.pic.lastDir.value = self.filelist.getCurrentDirectory()

		config.pic.save()
		self.close()

# ------------------------------------------------------------------------------------------

class Pic_Setup(Screen, ConfigListScreen):

	def __init__(self, session):
		Screen.__init__(self, session)
		# for the skin: first try MediaPlayerSettings, then Setup, this allows individual skinning
		self.skinName = ["PicturePlayerSetup", "Setup"]
		self.setup_title = _("Settings")
		self.onChangedEntry = []
		self.session = session
		ConfigListScreen.__init__(self, [], session=session, on_change=self.changedEntry)
		self["actions"] = ActionMap(["SetupActions", "MenuActions"], {
			"cancel": self.keyCancel,
			"save": self.keySave,
			"ok": self.keySave,
			"menu": self.closeRecursive,
		}, -2)
		self['footnote'] = Label()
		self["HelpWindow"] = Pixmap()
		self["HelpWindow"].hide()
		self["VKeyIcon"] = Pixmap()
		self["VKeyIcon"].hide()
		self["description"] = Label()

		self["key_red"] = StaticText(_("Cancel"))
		self["key_green"] = StaticText(_("OK"))
		self["key_yellow"] = StaticText()
		self["key_blue"] = StaticText()
		self.createSetup()
		self.onLayoutFinish.append(self.layoutFinished)
		if self.selectionChanged not in self["config"].onSelectionChanged:
			self["config"].onSelectionChanged.append(self.selectionChanged)
		self.selectionChanged()

	def layoutFinished(self):
		self.setTitle(self.setup_title)

	def createSetup(self):
		size_w = getDesktop(0).size().width()
		size_h = getDesktop(0).size().height()
		setup_list = [
			getConfigListEntry(_("Slideshow interval (sec.)"), config.pic.slidetime, _("Time between slides when showing a slideshow.")),
			getConfigListEntry(_("Scaling mode"), config.pic.resize, _('Scaling mode for 24-bit images. "Simple" is single-pixel sampling. "Better" is averaged over a small sample. No effect on 8-bit images.')),
			getConfigListEntry(_("Cache thumbnails"), config.pic.cache, _("Save scaled thumbnail images to disk to avoid recalculating them.")),
			getConfigListEntry(_("Show info line"), config.pic.infoline, _("Show image information text in top left of the screen when displaying full-screen images.")),
			getConfigListEntry(_("Frame size in full view"), config.pic.framesize, _("Size in pixels of the narrowest part of a frame around the  full-screen image.")),
			getConfigListEntry(_("Continuously loop slideshow"), config.pic.loop, _("Show slideshow in a continuous loop. Otherwise stop the slideshow at the last image in the image list.")),
			getConfigListEntry(_("Background color"), config.pic.bgcolor, _("Colour of the frame surrounding a full-screen image display.")),
			getConfigListEntry(_("Text color"), config.pic.textcolor, _("Colour of the information text in a full-screen image display.")),
			getConfigListEntry(_("Full-screen view resolution"), config.usage.pic_resolution, _("Resolution of the full-screen image. The skin resolution is %dx%d." % (size_w, size_h))),
		]
		self["config"].list = setup_list
		self["config"].l.setList(setup_list)

	def selectionChanged(self):
		self["description"].setText(self["config"].getCurrent()[2])

	def keyLeft(self):
		ConfigListScreen.keyLeft(self)

	def keyRight(self):
		ConfigListScreen.keyRight(self)

	# for summary:
	def changedEntry(self):
		for x in self.onChangedEntry:
			x()

	def getCurrentEntry(self):
		return self["config"].getCurrent()[0]

	def getCurrentValue(self):
		return str(self["config"].getCurrent()[1].getText())

	def createSummary(self):
		from Screens.Setup import SetupSummary
		return SetupSummary

# ---------------------------------------------------------------------------

class Pic_Exif(Screen):
	skin = """
		<screen name="Pic_Exif" position="center,center" size="560,360" title="Info" >
			<ePixmap pixmap="buttons/red.png" position="0,0" size="140,40" alphatest="on" />
			<widget source="key_red" render="Label" position="0,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" transparent="1" />
			<widget source="menu" render="Listbox" position="5,50" size="550,310" scrollbarMode="showOnDemand" selectionDisabled="1" >
				<convert type="TemplatedMultiContent">
				{
					"template": [  MultiContentEntryText(pos = (5, 5), size = (250, 30), flags = RT_HALIGN_LEFT, text = 0), MultiContentEntryText(pos = (260, 5), size = (290, 30), flags = RT_HALIGN_LEFT, text = 1)],
					"fonts": [gFont("Regular", 20)],
					"itemHeight": 30
				}
				</convert>
			</widget>
		</screen>"""

	def __init__(self, session, exiflist):
		Screen.__init__(self, session)

		self["actions"] = ActionMap(["SetupActions", "ColorActions"], {
			"cancel": self.close
		}, -1)

		self["key_red"] = StaticText(_("Close"))

		exifdesc = [_("Filename") + ':', "EXIF-Version:", "Make:", "Camera:", "Date/Time:", "Width / Height:", "Flash used:", "Orientation:", "User Comments:", "Metering Mode:", "Exposure Program:", "Light Source:", "CompressedBitsPerPixel:", "ISO Speed Rating:", "X-Resolution:", "Y-Resolution:", "Resolution Unit:", "Brightness:", "Exposure Time:", "Exposure Bias:", "Distance:", "CCD-Width:", "Aperture f-Number:"]
		list = []

		for x in range(len(exiflist)):
			if x > 0:
				list.append((exifdesc[x], exiflist[x]))
			else:
				name = exiflist[x].split('/')[-1]
				list.append((exifdesc[x], name))
		self["menu"] = List(list)
		self.onLayoutFinish.append(self.layoutFinished)

	def layoutFinished(self):
		self.setTitle(_("Info"))

# ----------------------------------------------------------------------------------------

T_INDEX = 0
T_FRAME_POS = 1
T_PAGE = 2
T_NAME = 3
T_FULL = 4

class Pic_Thumb(Screen):
	def __init__(self, session, piclist, lastindex, path):

		self.textcolor = config.pic.textcolor.value
		self.color = config.pic.bgcolor.value
		textsize = 20
		self.spaceX = 35
		self.picX = 190
		self.spaceY = 30
		self.picY = 200

		self.size_w = getDesktop(0).size().width()
		self.size_h = getDesktop(0).size().height()
		self.thumbsX = self.size_w / (self.spaceX + self.picX)  # thumbnails in X
		self.thumbsY = self.size_h / (self.spaceY + self.picY)  # thumbnails in Y
		self.thumbsC = self.thumbsX * self.thumbsY  # all thumbnails

		self.positionlist = []
		skincontent = ""

		posX = -1
		for x in range(self.thumbsC):
			posY = x / self.thumbsX
			posX += 1
			if posX >= self.thumbsX:
				posX = 0

			absX = self.spaceX + (posX * (self.spaceX + self.picX))
			absY = self.spaceY + (posY * (self.spaceY + self.picY))
			self.positionlist.append((absX, absY))
			skincontent += "<widget source=\"label" + str(x) + "\" render=\"Label\" position=\"" + str(absX + 5) + "," + str(absY + self.picY - textsize) + "\" size=\"" + str(self.picX - 10) + "," + str(textsize) + "\" font=\"Regular;14\" zPosition=\"2\" transparent=\"1\" noWrap=\"1\" foregroundColor=\"" + self.textcolor + "\" />"
			skincontent += "<widget name=\"thumb" + str(x) + "\" position=\"" + str(absX + 5) + "," + str(absY + 5) + "\" size=\"" + str(self.picX - 10) + "," + str(self.picY - (textsize * 2)) + "\" zPosition=\"2\" transparent=\"1\" alphatest=\"on\" />"

		# Screen, backgroundlabel and MovingPixmap
		self.skin = "<screen position=\"0,0\" size=\"" + str(self.size_w) + "," + str(self.size_h) + "\" flags=\"wfNoBorder\" > \
			<eLabel position=\"0,0\" zPosition=\"0\" size=\"" + str(self.size_w) + "," + str(self.size_h) + "\" backgroundColor=\"" + self.color + "\" /><widget name=\"frame\" position=\"35,30\" size=\"190,200\" pixmap=\"pic_frame.png\" zPosition=\"1\" alphatest=\"on\" />" + skincontent + "</screen>"

		Screen.__init__(self, session)

		self["actions"] = ActionMap(["OkCancelActions", "ColorActions", "DirectionActions", "MovieSelectionActions"], {
			"cancel": self.Exit,
			"ok": self.KeyOk,
			"left": self.key_left,
			"right": self.key_right,
			"up": self.key_up,
			"down": self.key_down,
			"showEventInfo": self.StartExif,
		}, -1)

		self["frame"] = MovingPixmap()
		for x in range(self.thumbsC):
			self["label" + str(x)] = StaticText()
			self["thumb" + str(x)] = Pixmap()

		self.Thumbnaillist = []
		self.filelist = []
		self.currPage = -1
		self.dirlistcount = 0
		self.path = path

		index = 0
		framePos = 0
		Page = 0
		for x in piclist:
			if not x[0][1]:
				self.filelist.append((index, framePos, Page, x[0][0], path + x[0][0]))
				index += 1
				framePos += 1
				if framePos > (self.thumbsC - 1):
					framePos = 0
					Page += 1
			else:
				self.dirlistcount += 1

		self.maxentry = len(self.filelist) - 1
		self.index = lastindex - self.dirlistcount
		if self.index < 0:
			self.index = 0

		self.picload = ePicLoad()
		self.picload.PictureData.get().append(self.showPic)

		self.onLayoutFinish.append(self.setPicloadConf)

		self.ThumbTimer = eTimer()
		self.ThumbTimer.callback.append(self.showPic)

	def setPicloadConf(self):
		sc = getScale()
		self.picload.setPara([self["thumb0"].instance.size().width(), self["thumb0"].instance.size().height(), sc[0], sc[1], config.pic.cache.value, int(config.pic.resize.value), self.color])
		self.paintFrame()

	def paintFrame(self):
		# print "[PicturePlayer] index=" + str(self.index)
		if self.maxentry < self.index or self.index < 0:
			return

		pos = self.positionlist[self.filelist[self.index][T_FRAME_POS]]
		self["frame"].moveTo(pos[0], pos[1], 1)
		self["frame"].startMoving()

		if self.currPage != self.filelist[self.index][T_PAGE]:
			self.currPage = self.filelist[self.index][T_PAGE]
			self.newPage()

	def newPage(self):
		self.Thumbnaillist = []
		# clear Labels and Thumbnail
		for x in range(self.thumbsC):
			self["label" + str(x)].setText("")
			self["thumb" + str(x)].hide()
		# paint Labels and fill Thumbnail-List
		for x in self.filelist:
			if x[T_PAGE] == self.currPage:
				self["label" + str(x[T_FRAME_POS])].setText("(" + str(x[T_INDEX] + 1) + ") " + x[T_NAME])
				self.Thumbnaillist.append([0, x[T_FRAME_POS], x[T_FULL]])

		# paint Thumbnail start
		self.showPic()

	def showPic(self, picInfo=""):
		for x in range(len(self.Thumbnaillist)):
			if self.Thumbnaillist[x][0] == 0:
				if self.picload.getThumbnail(self.Thumbnaillist[x][2]) == 1:  # to do - allow retries
					self.ThumbTimer.start(500, True)
				else:
					self.Thumbnaillist[x][0] = 1
				break
			elif self.Thumbnaillist[x][0] == 1:
				self.Thumbnaillist[x][0] = 2
				ptr = self.picload.getData()
				if ptr is not None:
					self["thumb" + str(self.Thumbnaillist[x][1])].instance.setPixmap(ptr.__deref__())
					self["thumb" + str(self.Thumbnaillist[x][1])].show()

	def key_left(self):
		self.index -= 1
		if self.index < 0:
			self.index = self.maxentry
		self.paintFrame()

	def key_right(self):
		self.index += 1
		if self.index > self.maxentry:
			self.index = 0
		self.paintFrame()

	def key_up(self):
		self.index -= self.thumbsX
		if self.index < 0:
			self.index = self.maxentry
		self.paintFrame()

	def key_down(self):
		self.index += self.thumbsX
		if self.index > self.maxentry:
			self.index = 0
		self.paintFrame()

	def StartExif(self):
		if self.maxentry < 0:
			return
		self.session.open(Pic_Exif, self.picload.getInfo(self.filelist[self.index][T_FULL]))

	def KeyOk(self):
		if self.maxentry < 0:
			return
		self.old_index = self.index
		self.session.openWithCallback(self.callbackView, Pic_Full_View, self.filelist, self.index, self.path)

	def callbackView(self, val=0):
		self.index = val
		if self.old_index != self.index:
			self.paintFrame()

	def Exit(self):
		if self.ThumbTimer.isActive():
			self.ThumbTimer.stop()

		del self.picload
		self.close(self.index + self.dirlistcount)

# ---------------------------------------------------------------------------

class Pic_Full_View(Screen, HelpableScreen):
	def __init__(self, session, filelist, index, path):

		HelpableScreen.__init__(self)

		self.textcolor = config.pic.textcolor.value
		self.bgcolor = config.pic.bgcolor.value
		space = config.pic.framesize.value

		self.size_w = size_w = getDesktop(0).size().width()
		self.size_h = size_h = getDesktop(0).size().height()

		if config.usage.pic_resolution.value and (size_w, size_h) != eval(config.usage.pic_resolution.value):
			(size_w, size_h) = eval(config.usage.pic_resolution.value)
			gMainDC.getInstance().setResolution(size_w, size_h)
			getDesktop(0).resize(eSize(size_w, size_h))

		self.skin = "<screen position=\"0,0\" size=\"" + str(size_w) + "," + str(size_h) + "\" flags=\"wfNoBorder\" > \
			<eLabel position=\"0,0\" zPosition=\"0\" size=\"" + str(size_w) + "," + str(size_h) + "\" backgroundColor=\"" + self.bgcolor + "\" /><widget name=\"pic\" position=\"" + str(space) + "," + str(space) + "\" size=\"" + str(size_w - (space * 2)) + "," + str(size_h - (space * 2)) + "\" zPosition=\"1\" alphatest=\"on\" /> \
			<widget name=\"point\" position=\"" + str(space + 5) + "," + str(space + 2) + "\" size=\"20,20\" zPosition=\"2\" pixmap=\"skin_default/icons/record.png\" alphatest=\"on\" /> \
			<widget name=\"play_icon\" position=\"" + str(space + 25) + "," + str(space + 2) + "\" size=\"20,20\" zPosition=\"2\" pixmap=\"skin_default/icons/ico_mp_play.png\"  alphatest=\"on\" /> \
			<widget source=\"file\" render=\"Label\" position=\"" + str(space + 45) + "," + str(space) + "\" size=\"" + str(size_w - (space * 2) - 50) + ",25\" font=\"Regular;20\" borderWidth=\"1\" borderColor=\"#000000\" halign=\"left\" foregroundColor=\"" + self.textcolor + "\" zPosition=\"2\" noWrap=\"1\" transparent=\"1\" /></screen>"

		Screen.__init__(self, session)

		self["actions"] = HelpableActionMap(self, ["OkCancelActions", "ColorActions", "DirectionActions", "MovieSelectionActions"], {
			"cancel": (self.Exit, _("Return to picture index (list or thumbnails)")),
			"green": (self.PlayPause, _("Pause/run slideshow")),
			"yellow": (self.PlayPause, _("Pause/run slideshow")),
			"blue": (self.nextPic, _("Move to next picture")),
			"red": (self.prevPic, _("Move to previous picture")),
			"left": (self.prevPic, _("Move to previous picture")),
			"right": (self.nextPic, _("Move to next picture")),
			"showEventInfo": (self.StartExif, _("Show extended image information")),
		}, -1)

		self["point"] = Pixmap()
		self["pic"] = Pixmap()
		self["play_icon"] = Pixmap()
		self["file"] = StaticText(_("Please wait, loading picture..."))

		self.old_index = 0
		self.filelist = []
		self.lastindex = index
		self.currPic = []
		self.shownow = True
		self.dirlistcount = 0

		for x in filelist:
			if len(filelist[0]) == 3:  # orig. filelist
				if not x[0][1]:
					self.filelist.append(path + x[0][0])
				else:
					self.dirlistcount += 1
			elif len(filelist[0]) == 2:  # scanlist
				if not x[0][1]:
					self.filelist.append(x[0][0])
				else:
					self.dirlistcount += 1
			else:  # thumbnaillist
				self.filelist.append(x[T_FULL])

		self.maxentry = len(self.filelist) - 1
		self.index = index - self.dirlistcount
		if self.index < 0:
			self.index = 0

		self.picload = ePicLoad()
		self.picload.PictureData.get().append(self.finish_decode)

		self.slideTimer = eTimer()
		self.slideTimer.callback.append(self.slidePic)

		if self.maxentry >= 0:
			self.onLayoutFinish.append(self.setPicloadConf)

	def setPicloadConf(self):
		sc = getScale()
		self.picload.setPara([self["pic"].instance.size().width(), self["pic"].instance.size().height(), sc[0], sc[1], 0, int(config.pic.resize.value), self.bgcolor])

		self["play_icon"].hide()
		if not config.pic.infoline.value:
			self["file"].setText("")
		self.start_decode()

		self.PlayPause()

	def ShowPicture(self):
		if self.shownow and len(self.currPic):
			self.shownow = False
			if config.pic.infoline.value:
				self["file"].setText(self.currPic[0])
			else:
				self["file"].setText("")
			self.lastindex = self.currPic[1]
			self["pic"].instance.setPixmap(self.currPic[2].__deref__())
			self.currPic = []

			self.next()
			self.start_decode()

	def finish_decode(self, picInfo=""):
		self["point"].hide()
		ptr = self.picload.getData()
		if ptr is not None:
			text = ""
			try:
				text = picInfo.split('\n', 1)
				text = "(" + str(self.index + 1) + "/" + str(self.maxentry + 1) + ") " + text[0].split('/')[-1]
			except:
				pass
			self.currPic = []
			self.currPic.append(text)
			self.currPic.append(self.index)
			self.currPic.append(ptr)
			self.ShowPicture()

	def start_decode(self):
		self.picload.startDecode(self.filelist[self.index])
		self["point"].show()

	def next(self):
		self.index += 1
		if self.index > self.maxentry:
			self.index = 0

	def prev(self):
		self.index -= 1
		if self.index < 0:
			self.index = self.maxentry

	def slidePic(self):
		# print "[PicturePlayer] slide to next Picture index=" + str(self.lastindex)
		if not config.pic.loop.value and self.lastindex == self.maxentry:
			self.PlayPause()
		self.shownow = True
		self.ShowPicture()

	def PlayPause(self):
		if self.slideTimer.isActive():
			self.slideTimer.stop()
			self["play_icon"].hide()
		else:
			self.slideTimer.start(config.pic.slidetime.value * 1000)
			self["play_icon"].show()
			self.nextPic()

	def prevPic(self):
		self.currPic = []
		self.index = self.lastindex
		self.prev()
		self.start_decode()
		self.shownow = True

	def nextPic(self):
		self.shownow = True
		self.ShowPicture()

	def StartExif(self):
		if self.maxentry < 0:
			return
		self.session.open(Pic_Exif, self.picload.getInfo(self.filelist[self.lastindex]))

	def Exit(self):
		if self.slideTimer.isActive():
			self.slideTimer.stop()

		del self.picload

		if config.usage.pic_resolution.value and (self.size_w, self.size_h) != eval(config.usage.pic_resolution.value):
			gMainDC.getInstance().setResolution(self.size_w, self.size_h)
			getDesktop(0).resize(eSize(self.size_w, self.size_h))

		self.close(self.lastindex + self.dirlistcount)
