from enigma import ePicLoad, eTimer, getDesktop

from Screens.Screen import Screen
from Tools.Directories import resolveFilename, pathExists, SCOPE_MEDIA
from Plugins.Plugin import PluginDescriptor

from Components.Pixmap import Pixmap, MovingPixmap
from Components.ActionMap import ActionMap, NumberActionMap
from Components.Label import Label
from Components.Button import Button
from Components.FileList import FileList
from Components.AVSwitch import AVSwitch
from Components.Sources.List import List
from Components.ConfigList import ConfigList

from Components.config import config, ConfigSubsection, ConfigInteger, ConfigSelection, ConfigText, ConfigEnableDisable, KEY_LEFT, KEY_RIGHT, KEY_0, getConfigListEntry

def getAspectforPic():
	return AVSwitch().getFramebufferScale()

config.pic = ConfigSubsection()
config.pic.framesize = ConfigInteger(default=30, limits=(5, 99))
config.pic.slidetime = ConfigInteger(default=10, limits=(10, 60))
config.pic.resize = ConfigSelection(default="1", choices = [("0", _("simple")), ("1", _("better"))])
config.pic.cache = ConfigEnableDisable(default=True)
config.pic.lastDir = ConfigText(default=resolveFilename(SCOPE_MEDIA))
config.pic.infoline = ConfigEnableDisable(default=True)
config.pic.loop = ConfigEnableDisable(default=True)
config.pic.bgcolor = ConfigSelection(default="#00000000", choices = [("#00000000", _("black")),("#009eb9ff", _("blue")),("#00ff5a51", _("red")), ("#00ffe875", _("yellow")), ("#0038FF48", _("green"))])
config.pic.textcolor = ConfigSelection(default="#0038FF48", choices = [("#00000000", _("black")),("#009eb9ff", _("blue")),("#00ff5a51", _("red")), ("#00ffe875", _("yellow")), ("#0038FF48", _("green"))])

class picshow(Screen):
	def __init__(self, session):
		self.skin = """<screen position="80,80" size="560,440" title="PicturePlayer" >
			<ePixmap position="0,0" size="140,40" pixmap="skin_default/buttons/red.png" alphatest="on" />
			<ePixmap position="140,0" size="140,40" pixmap="skin_default/buttons/green.png" alphatest="on" />
			<ePixmap position="280,0" size="140,40" pixmap="skin_default/buttons/yellow.png" alphatest="on" />
			<ePixmap position="420,0" size="140,40" pixmap="skin_default/buttons/blue.png" alphatest="on" />
			<widget name="key_red" position="0,0" size="140,40" font="Regular;20" backgroundColor="#9f1313" zPosition="2" transparent="1" shadowColor="black" shadowOffset="-1,-1" />
			<widget name="key_green" position="140,0" size="140,40" font="Regular;20" backgroundColor="#1f771f" zPosition="2" transparent="1" shadowColor="black" shadowOffset="-1,-1" />
			<widget name="key_yellow" position="280,0" size="140,40" font="Regular;20" backgroundColor="#a08500" zPosition="2" transparent="1" shadowColor="black" shadowOffset="-1,-1" />
			<widget name="key_blue" position="420,0" size="140,40" font="Regular;20" backgroundColor="#18188b" zPosition="2" transparent="1" shadowColor="black" shadowOffset="-1,-1" />
			<widget name="label" position="5,55" size="350,140" font="Regular;19" />
			<widget name="thn" position="360,40" size="180,160" alphatest="on" />
			<widget name="filelist" position="5,205" zPosition="2" size="550,230" scrollbarMode="showOnDemand" />
			</screen>"""

		Screen.__init__(self, session)

		self["actions"] = ActionMap(["OkCancelActions", "ColorActions", "DirectionActions"],
		{
			"cancel": self.KeyExit,
			"red": self.KeyRed,
			"yellow": self.KeyYellow,
			"blue": self.KeyBlue,
			"ok": self.KeyOk
		}, -1)

		self["key_red"] = Button(_("Thumbnails"))
		self["key_green"] = Button()
		self["key_yellow"] = Button(_("Exif"))
		self["key_blue"] = Button(_("Setup"))
		self["label"] = Label()
		self["thn"] = Pixmap()

		currDir = config.pic.lastDir.value
		if not pathExists(currDir):
			currDir = "/"

		self.filelist = FileList(currDir, matchingPattern = "(?i)^.*\.(jpeg|jpg|jpe|png|bmp|gif)")
		self["filelist"] = self.filelist
		self["filelist"].onSelectionChanged.append(self.selectionChanged)
		
		self.ThumbTimer = eTimer()
		self.ThumbTimer.callback.append(self.showThumb)

		self.picload = ePicLoad()
		self.picload.PictureData.get().append(self.showPic)
		
		self.onLayoutFinish.append(self.setConf)

	def showPic(self, picInfo=""):
		ptr = self.picload.getData()
		if ptr != None:
			self["thn"].instance.setPixmap(ptr.__deref__())
			self["thn"].show()

		text = picInfo.split('\n',1)
		self["label"].setText(text[1])
		self["label"].show()
		
	def showThumb(self):
		if not self.filelist.canDescent():
			if self.picload.getThumbnail(self.filelist.getCurrentDirectory() + self.filelist.getFilename()) == 1:
				self.ThumbTimer.start(500, True)

	def selectionChanged(self):
		if not self.filelist.canDescent():
			self.ThumbTimer.start(500, True)
		else:
			self["label"].hide()
			self["thn"].hide()
		
	def KeyRed(self):
		#if not self.filelist.canDescent():
		self.session.openWithCallback(self.callbackView, Pic_Thumb, self.filelist.getFileList(), self.filelist.getSelectionIndex(), self.filelist.getCurrentDirectory())
	
	def KeyYellow(self):
		if not self.filelist.canDescent():
			self.session.open(Pic_Exif, self.picload.getInfo(self.filelist.getCurrentDirectory() + self.filelist.getFilename()))
	
	def KeyBlue(self):
		self.session.openWithCallback(self.setConf ,Pic_Setup)

	def KeyOk(self):
		if self.filelist.canDescent():
			self.filelist.descent()
		else:
			self.session.openWithCallback(self.callbackView, Pic_Full_View, self.filelist.getFileList(), self.filelist.getSelectionIndex(), self.filelist.getCurrentDirectory())

	def setConf(self):
		#0=Width 1=Height 2=Aspect 3=use_cache 4=resize_type 5=Background(#AARRGGBB)
		self.picload.setPara([self["thn"].instance.size().width(), self["thn"].instance.size().height(), getAspectforPic(), config.pic.cache.value, int(config.pic.resize.value), "#00000000"])
		
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

#------------------------------------------------------------------------------------------

class Pic_Setup(Screen):
	def __init__(self, session):
		self.skin = """<screen position="120,180" size="480,210" title="Settings" >
					<widget name="liste" position="5,5" size="470,200" />
				</screen>"""
		Screen.__init__(self, session)

		self["actions"] = NumberActionMap(["SetupActions"],
		{
			"cancel": self.close,
			"left": self.keyLeft,
			"right": self.keyRight,
			"0": self.keyNumber,
			"1": self.keyNumber,
			"2": self.keyNumber,
			"3": self.keyNumber,
			"4": self.keyNumber,
			"5": self.keyNumber,
			"6": self.keyNumber,
			"7": self.keyNumber,
			"8": self.keyNumber,
			"9": self.keyNumber
		}, -1)
		
		list = []
		self["liste"] = ConfigList(list)
		list.append(getConfigListEntry(_("Slideshow Interval (sec.)"), config.pic.slidetime))
		list.append(getConfigListEntry(_("Scaling Mode"), config.pic.resize))
		list.append(getConfigListEntry(_("Cache Thumbnails"), config.pic.cache))
		list.append(getConfigListEntry(_("show Infoline"), config.pic.infoline))
		list.append(getConfigListEntry(_("Frame size in full view"), config.pic.framesize))
		list.append(getConfigListEntry(_("slide picture in loop"), config.pic.loop))
		list.append(getConfigListEntry(_("backgroundcolor"), config.pic.bgcolor))
		list.append(getConfigListEntry(_("textcolor"), config.pic.textcolor))
		
	def keyLeft(self):
		self["liste"].handleKey(KEY_LEFT)

	def keyRight(self):
		self["liste"].handleKey(KEY_RIGHT)
		
	def keyNumber(self, number):
		self["liste"].handleKey(KEY_0 + number)

#---------------------------------------------------------------------------

class Pic_Exif(Screen):
	def __init__(self, session, exiflist):
		self.skin = """<screen position="80,120" size="560,360" title="Info" >
				<widget source="menu" render="Listbox" position="0,0" size="560,360" scrollbarMode="showOnDemand" selectionDisabled="1" >
				<convert type="TemplatedMultiContent">
					{"template": [  MultiContentEntryText(pos = (5, 5), size = (250, 30), flags = RT_HALIGN_LEFT, text = 0), MultiContentEntryText(pos = (260, 5), size = (290, 30), flags = RT_HALIGN_LEFT, text = 1)], "fonts": [gFont("Regular", 20)], "itemHeight": 30 }
				</convert>
				</widget>
			</screen>"""
		Screen.__init__(self, session)

		self["actions"] = ActionMap(["OkCancelActions"],
		{
			"cancel": self.close
		}, -1)
		
		exifdesc = [_("Filename:"), "EXIF-Version:", "Make:", "Camera:", "Date/Time:", "Width / Height:", "Flash used:", "Orientation:", "User Comments:", "Metering Mode:", "Exposure Program:", "Light Source:", "CompressedBitsPerPixel:", "ISO Speed Rating:", "X-Resolution:", "Y-Resolution:", "Resolution Unit:", "Brightness:", "Exposure Time:", "Exposure Bias:", "Distance:", "CCD-Width:", "ApertureFNumber:"]
		list = []

		for x in range(len(exiflist)):
			if x>0:
				list.append((exifdesc[x], exiflist[x]))
			else:
				name = exiflist[x].split('/')[-1]
				list.append((exifdesc[x], name))
		self["menu"] = List(list)

#----------------------------------------------------------------------------------------

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
		
		size_w = getDesktop(0).size().width()
		size_h = getDesktop(0).size().height()
		self.thumbsX = size_w / (self.spaceX + self.picX) # thumbnails in X
		self.thumbsY = size_h / (self.spaceY + self.picY) # thumbnails in Y
		self.thumbsC = self.thumbsX * self.thumbsY # all thumbnails
		
		self.positionlist = []
		skincontent = ""

		posX = -1
		for x in range(self.thumbsC):
			posY = x / self.thumbsX
			posX += 1
			if posX >= self.thumbsX:
				posX = 0
			
			absX = self.spaceX + (posX*(self.spaceX + self.picX))
			absY = self.spaceY + (posY*(self.spaceY + self.picY))
			self.positionlist.append((absX, absY))
			skincontent += "<widget name=\"label" + str(x) + "\" position=\"" + str(absX+5) + "," + str(absY+self.picY-textsize) + "\" size=\"" + str(self.picX - 10) + ","  + str(textsize) + "\" font=\"Regular;14\" zPosition=\"2\" transparent=\"1\" noWrap=\"1\" foregroundColor=\"" + self.textcolor + "\" />"
		
			skincontent += "<widget name=\"thumb" + str(x) + "\" position=\"" + str(absX+5)+ "," + str(absY+5) + "\" size=\"" + str(self.picX -10) + "," + str(self.picY - (textsize*2)) + "\" zPosition=\"2\" transparent=\"1\" alphatest=\"on\" />"
		
		
		# Screen, backgroundlabel and MovingPixmap
		self.skin = "<screen position=\"0,0\" size=\"" + str(size_w) + "," + str(size_h) + "\" flags=\"wfNoBorder\" > \
			<eLabel position=\"0,0\" zPosition=\"0\" size=\""+ str(size_w) + "," + str(size_h) + "\" backgroundColor=\"" + self.color + "\" /><widget name=\"frame\" position=\"35,30\" size=\"190,200\" pixmap=\"pic_frame.png\" zPosition=\"1\" alphatest=\"on\" />"  + skincontent + "</screen>"
		
		Screen.__init__(self, session)
		
		self["actions"] = ActionMap(["OkCancelActions", "ColorActions", "DirectionActions", "MovieSelectionActions"],
		{
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
			self["label"+str(x)] = Label()
			self["thumb"+str(x)] = Pixmap()
			
		self.Thumbnaillist = []
		self.filelist = []
		self.currPage = -1
		self.dirlistcount = 0
		self.path = path

		index = 0
		framePos = 0
		Page = 0
		for x in piclist:
			if x[0][1] == False:
				self.filelist.append((index, framePos, Page, x[0][0],  path + x[0][0]))
				index += 1
				framePos += 1
				if framePos > (self.thumbsC -1):
					framePos = 0
					Page += 1
			else:
				self.dirlistcount += 1
		
		self.maxentry = len(self.filelist)-1
		self.index = lastindex - self.dirlistcount
		if self.index < 0:
			self.index = 0

		self.picload = ePicLoad()
		self.picload.PictureData.get().append(self.showPic)
		
		self.onLayoutFinish.append(self.setPicloadConf)
		
		self.ThumbTimer = eTimer()
		self.ThumbTimer.callback.append(self.showPic)

	def setPicloadConf(self):
		self.picload.setPara([self["thumb0"].instance.size().width(), self["thumb0"].instance.size().height(), getAspectforPic(), config.pic.cache.value, int(config.pic.resize.value), self.color])
		self.paintFrame()
		
		
	def paintFrame(self):
		#print "index=" + str(self.index)
		if self.maxentry < self.index or self.index < 0:
			return

		pos = self.positionlist[self.filelist[self.index][T_FRAME_POS]]
		self["frame"].moveTo( pos[0], pos[1], 1)
		self["frame"].startMoving()
		
		if self.currPage != self.filelist[self.index][T_PAGE]:
			self.currPage = self.filelist[self.index][T_PAGE]
			self.newPage()

	def newPage(self):
		self.Thumbnaillist = []
		#clear Labels and Thumbnail
		for x in range(self.thumbsC):
			self["label"+str(x)].setText("")
			self["thumb"+str(x)].hide()
		#paint Labels and fill Thumbnail-List
		for x in self.filelist:
			if x[T_PAGE] == self.currPage:
				self["label"+str(x[T_FRAME_POS])].setText("(" + str(x[T_INDEX]+1) + ") " + x[T_NAME])
				self.Thumbnaillist.append([0, x[T_FRAME_POS], x[T_FULL]])
				
		#paint Thumbnail start
		self.showPic()

	def showPic(self, picInfo=""):
		for x in range(len(self.Thumbnaillist)):
			if self.Thumbnaillist[x][0] == 0:
				if self.picload.getThumbnail(self.Thumbnaillist[x][2]) == 1: #zu tun probier noch mal
					self.ThumbTimer.start(500, True)
				else:
					self.Thumbnaillist[x][0] = 1
				break
			elif self.Thumbnaillist[x][0] == 1:
				self.Thumbnaillist[x][0] = 2
				ptr = self.picload.getData()
				if ptr != None:
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
			self.index =self.maxentry
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
		del self.picload
		self.close(self.index + self.dirlistcount)

#---------------------------------------------------------------------------

class Pic_Full_View(Screen):
	def __init__(self, session, filelist, index, path):

		self.textcolor = config.pic.textcolor.value
		self.bgcolor = config.pic.bgcolor.value
		space = config.pic.framesize.value
		size_w = getDesktop(0).size().width()
		size_h = getDesktop(0).size().height()
		
		self.skin = "<screen position=\"0,0\" size=\"" + str(size_w) + "," + str(size_h) + "\" flags=\"wfNoBorder\" > \
			<eLabel position=\"0,0\" zPosition=\"0\" size=\""+ str(size_w) + "," + str(size_h) + "\" backgroundColor=\""+ self.bgcolor +"\" /><widget name=\"pic\" position=\"" + str(space) + "," + str(space) + "\" size=\"" + str(size_w-(space*2)) + "," + str(size_h-(space*2)) + "\" zPosition=\"1\" alphatest=\"on\" /> \
			<widget name=\"point\" position=\""+ str(space+5) + "," + str(space+2) + "\" size=\"20,20\" zPosition=\"2\" pixmap=\"skin_default/icons/record.png\" alphatest=\"on\" /> \
			<widget name=\"play_icon\" position=\""+ str(space+25) + "," + str(space+2) + "\" size=\"20,20\" zPosition=\"2\" pixmap=\"skin_default/icons/ico_mp_play.png\"  alphatest=\"on\" /> \
			<widget name=\"file\" position=\""+ str(space+45) + "," + str(space) + "\" size=\""+ str(size_w-(space*2)-50) + ",25\" font=\"Regular;20\" halign=\"left\" foregroundColor=\"" + self.textcolor + "\" zPosition=\"2\" noWrap=\"1\" transparent=\"1\" /></screen>"

		Screen.__init__(self, session)
		
		self["actions"] = ActionMap(["OkCancelActions", "ColorActions", "DirectionActions", "MovieSelectionActions"],
		{
			"cancel": self.Exit,
			"green": self.PlayPause,
			"yellow": self.PlayPause,
			"blue": self.nextPic,
			"red": self.prevPic,
			"left": self.prevPic,
			"right": self.nextPic,
			"showEventInfo": self.StartExif,
		}, -1)
		
		self["point"] = Pixmap()
		self["pic"] = Pixmap()
		self["play_icon"] = Pixmap()
		self["file"] = Label(_("please wait, loading picture..."))
		
		self.old_index = 0
		self.filelist = []
		self.lastindex = index
		self.currPic = []
		self.shownow = True
		self.dirlistcount = 0

		for x in filelist:
			if len(filelist[0]) == 3: #orig. filelist
				if x[0][1] == False:
					self.filelist.append(path + x[0][0])
				else:
					self.dirlistcount += 1
			else: # thumbnaillist
				self.filelist.append(x[T_FULL])

		self.maxentry = len(self.filelist)-1
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
		self.picload.setPara([self["pic"].instance.size().width(), self["pic"].instance.size().height(), getAspectforPic(), 0, int(config.pic.resize.value), self.bgcolor])
		
		self["play_icon"].hide()
		if config.pic.infoline.value == False:
			self["file"].hide()
		self.start_decode()

	def ShowPicture(self):
		if self.shownow and len(self.currPic):
			self.shownow = False
			self["file"].setText(self.currPic[0])
			self.lastindex = self.currPic[1]
			self["pic"].instance.setPixmap(self.currPic[2].__deref__())
			self.currPic = []
			
			self.next()
			self.start_decode()
	
	def finish_decode(self, picInfo=""):
		self["point"].hide()
		ptr = self.picload.getData()
		if ptr != None:
			text = ""
			try:
				text = picInfo.split('\n',1)
				text = "(" + str(self.index+1) + "/" + str(self.maxentry+1) + ") " + text[0].split('/')[-1]
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
		print "slide to next Picture index=" + str(self.lastindex)
		if config.pic.loop.value==False and self.lastindex == self.maxentry:
			self.PlayPause()
		self.shownow = True
		self.ShowPicture()

	def PlayPause(self):
		if self.slideTimer.isActive():
			self.slideTimer.stop()
			self["play_icon"].hide()
		else:
			self.slideTimer.start(config.pic.slidetime.value*1000)
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
		del self.picload
		self.close(self.lastindex + self.dirlistcount)

#------------------------------------------------------------------------------------------

def main(session, **kwargs):
	session.open(picshow)

def filescan_open(list, session, **kwargs):
	# Recreate List as expected by PicView
	filelist = [((file.path, False), None) for file in list]
	session.open(Pic_Full_View, filelist, 0, file.path)

def filescan(**kwargs):
	from Components.Scanner import Scanner, ScanPath

	# Overwrite checkFile to only detect local
	class LocalScanner(Scanner):
		def checkFile(self, file):
			return fileExists(file.path)

	return \
		LocalScanner(mimetypes = ["image/jpeg", "image/png", "image/gif", "image/bmp"],
			paths_to_scan = 
				[
					ScanPath(path = "DCIM", with_subdirs = True),
					ScanPath(path = "", with_subdirs = False),
				],
			name = "Pictures", 
			description = "View Photos...",
			openfnc = filescan_open,
		)

def Plugins(**kwargs):
	return \
		[PluginDescriptor(name=_("PicturePlayer"), description=_("fileformats (BMP, PNG, JPG, GIF)"), icon="pictureplayer.png", where = PluginDescriptor.WHERE_PLUGINMENU, fnc=main),
		 PluginDescriptor(name=_("PicturePlayer"), where = PluginDescriptor.WHERE_FILESCAN, fnc = filescan)]
