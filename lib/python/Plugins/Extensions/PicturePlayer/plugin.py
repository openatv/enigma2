from enigma import *

from Screens.Screen import Screen
from Screens.ServiceInfo import ServiceInfoList, ServiceInfoListEntry
from Components.ActionMap import ActionMap, NumberActionMap
from Components.Pixmap import Pixmap, MovingPixmap
from Components.Label import Label

from Components.ConfigList import ConfigList
from Components.config import *

from Tools.Directories import resolveFilename, SCOPE_MEDIA
from Components.FileList import FileEntryComponent, FileList
from Components.AVSwitch import AVSwitch

from Plugins.Plugin import PluginDescriptor

import os

config.pic = ConfigSubsection()
config.pic.slidetime = ConfigInteger(default=10, limits=(5, 60))
config.pic.resize = ConfigSelection(default="0", choices = [("0", _("simple")), ("1", _("better"))])
config.pic.cache = ConfigEnableDisable(default=True)
config.pic.lastDir = ConfigText(default=resolveFilename(SCOPE_MEDIA))
config.pic.rotate = ConfigSelection(default="0", choices = [("0", _("none")), ("1", _("manual")), ("2", _("by Exif"))])

def getAspect():
	val = AVSwitch().getAspectRatioSetting()
	return val/2

#------------------------------------------------------------------------------------------

class ThumbView(Screen):
	skin = """
		<screen position="0,0" size="720,576" flags="wfNoBorder" title="ThumbView" >
			<eLabel position="0,0" zPosition="0" size="720,576" backgroundColor="black" />
			<widget name="frame" position="50,63" size="190,200" pixmap="pic_frame.png" zPosition="1" alphatest="on" />
			<widget name="label0" position="55,240" size="180,20" font="Regular;13" halign="center" zPosition="2" transparent="1" />
			<widget name="label1" position="270,240" size="180,20" font="Regular;13" halign="center" zPosition="2" transparent="1" />
			<widget name="label2" position="485,240" size="180,20" font="Regular;13" halign="center" zPosition="2" transparent="1" />
			<widget name="label3" position="55,465" size="180,20" font="Regular;13" halign="center" zPosition="2" transparent="1" />
			<widget name="label4" position="270,465" size="180,20" font="Regular;13" halign="center" zPosition="2" transparent="1" />
			<widget name="label5" position="485,465" size="180,20" font="Regular;13" halign="center" zPosition="2" transparent="1" />
			<widget name="thumb0" position="55,68" size="180,160" zPosition="2" transparent="1"  />
			<widget name="thumb1" position="270,68" size="180,160" zPosition="2" transparent="1" />
			<widget name="thumb2" position="485,68" size="180,160" zPosition="2" transparent="1" />
			<widget name="thumb3" position="55,293" size="180,160" zPosition="2" transparent="1" />
			<widget name="thumb4" position="270,293" size="180,160" zPosition="2" transparent="1" />
			<widget name="thumb5" position="485,293" size="180,160" zPosition="2" transparent="1" />
		</screen>"""
	
	def __init__(self, session, filelist, name, path):
		self.skin = ThumbView.skin
		Screen.__init__(self, session)

		self["actions"] = ActionMap(["OkCancelActions", "DirectionActions", "MovieSelectionActions"],
		{
			"cancel": self.Exit,
			"ok": self.KeyOk,
			"showEventInfo": self.StartExif,
			"right": self.key_right,
			"left": self.key_left,
			"up": self.key_up,
			"down": self.key_down
		}, -1)
		
		for x in range(6):
			self["label"+str(x)] = Label()
			self["thumb"+str(x)] = Pixmap()
		self["frame"] = MovingPixmap()
		
		self.aspect = getAspect()
		self.path = path
		self.filelist = filelist
		self.currPage = -1
		self.index = 0
		self.old_index = 0
		self.thumblist = []
		self.thumbindex = 0
		self.list = []
		self.poslist = [[50,63],[265,63],[480,63],[50,288],[265,288],[480,288]]
		
		count=0
		pos=0
		for x in self.filelist:
			if x[0][1] == False:
				self.list.append((x[0][0], self.path + x[0][0], count/6, pos, "(" + str(count+1) + ")  "))
				pos += 1
				if pos == 6:
					pos = 0
				if x[0][0] == name:
					self.index = count
				count += 1
		self.maxentry = len(self.list)-1
		
		self.ThumbTimer = eTimer()
		self.ThumbTimer.timeout.get().append(self.showThumb)

		self.fillPage()
		
	def key_left(self):
		self.index -= 1
		if self.index < 0:
			self.index = self.maxentry
		self.fillPage()
		
	def key_right(self):
		self.index += 1
		if self.index > self.maxentry:
			self.index = 0
		self.fillPage()
		
	def key_up(self):
		self.index -= 3
		if self.index < 0:
			self.index = 0
		self.fillPage()
		
	def key_down(self):
		self.index += 3
		if self.index > self.maxentry:
			self.index = self.maxentry
		self.fillPage()
		
	def fillPage(self):
		self["frame"].moveTo(self.poslist[self.list[self.index][3]][0], self.poslist[self.list[self.index][3]][1], 1)
		self["frame"].startMoving()
		
		if self.list[self.index][2] != self.currPage:
			self.currPage = self.list[self.index][2]
			textlist = ["","","","","",""]
			self.thumblist = ["","","","","",""]
			
			for x in self.list:
				if x[2] == self.currPage:
					textlist[x[3]] = x[4] + x[0]
					self.thumblist[x[3]] = x[0]
					
			for x in range(6):
				self["label"+str(x)].setText(textlist[x])
				self["thumb"+str(x)].hide()
				
			self.ThumbTimer.start(500, True)
		
	def showThumb(self):
		if self.thumblist[self.thumbindex] != "":
			cachefile = ""
			if config.pic.cache.value:
				cachedir = self.path + ".Thumbnails/"
				if not os.path.exists(cachedir):
					os.mkdir(cachedir)
				cachefile = cachedir + self.thumblist[self.thumbindex] + str(180) + str(160) + str(self.aspect)

			ptr = loadPic(self.path + self.thumblist[self.thumbindex], 180, 160, self.aspect, int(config.pic.resize.value), int(config.pic.rotate.value),1, cachefile)
			if ptr != None:
				self["thumb"+str(self.thumbindex)].show()
				self["thumb"+str(self.thumbindex)].instance.setPixmap(ptr.__deref__())
			
			self.thumbindex += 1
			if self.thumbindex < 6:
				self.ThumbTimer.start(500, True)
			else:
				self.thumbindex = 0
		else:
			self.thumbindex = 0
		
	def StartExif(self):
		self.session.open(ExifView, self.list[self.index][1], self.list[self.index][0])

	def KeyOk(self):
		self.old_index = self.index
		self.session.openWithCallback(self.returnView ,PicView, self.filelist, self.list[self.index][0], self.path)
		
	def returnView(self, val=0):
		self.index = val
		if self.old_index != self.index:
			self.fillPage()
		
	def Exit(self):
		self.close(self.index)

#------------------------------------------------------------------------------------------

class PicView(Screen):
	skin = """
		<screen position="0,0" size="720,576" flags="wfNoBorder" title="PicturePlayer" >
			<eLabel position="0,0" zPosition="0" size="720,576" backgroundColor="black" />
			<widget name="picture" position="80,50" size="560,450" zPosition="1" transparent="1" />
			<widget name="point" position="80,515" size="15,15" zPosition="1" pixmap="BlinkingPoint-fs8.png" alphatest="on" />
			<widget name="file" position="150,510" size="350,30" font="Regular;20" halign="center" zPosition="1" transparent="1" />
			<ePixmap position="500,515" size="36,20" pixmap="key_info-fs8.png" zPosition="1" alphatest="on" />
			<ePixmap position="550,515" size="20,20" pixmap="ico_mp_rewind.png"  zPosition="1" alphatest="on" />
			<widget name="play" position="575,515" size="20,20" pixmap="ico_mp_play.png"  zPosition="1" alphatest="on" />
			<widget name="pause" position="600,515" size="20,20" pixmap="ico_mp_pause.png"  zPosition="1" alphatest="on" />
			<ePixmap position="625,515" size="20,20" pixmap="ico_mp_forward.png"  zPosition="1" alphatest="on" />
		</screen>"""
	
	def __init__(self, session, filelist, name, path):
		self.skin = PicView.skin
		Screen.__init__(self, session)

		self["actions"] = ActionMap(["OkCancelActions", "ColorActions", "MovieSelectionActions"],
		{
			"cancel": self.Exit,
			"showEventInfo": self.StartExif,
			"green": self.Play,
			"yellow": self.Pause,
			"blue": self.nextPic,
			"red": self.prevPic
		}, -1)

		self.aspect = getAspect()
		self.blinking = False
		self.autoShow = True
		self.slideOn = False
		self.pauseOn = False
		self.index = 0
		self.list = []
		
		count=0
		for x in filelist:
			if x[0][1] == False:
				self.list.append((x[0][0], path + x[0][0], 0))
				if x[0][0] == name:
					self.index = count
				count += 1
		self.maxentry = len(self.list)-1

		self["file"] = Label(_("please wait, loading picture..."))
		self["picture"] = Pixmap()
		self["point"] = Pixmap()
		self["play"] = Pixmap()
		self["pause"] = Pixmap()
		
		self.decodeTimer = eTimer()
		self.decodeTimer.timeout.get().append(self.decodePic)
		self.decodeTimer.start(300, True)

		self.slideTimer = eTimer()
		self.slideTimer.timeout.get().append(self.slidePic)
		
		
	def Pause(self):
		if self.slideOn:
			if self.pauseOn:
				self.pauseOn=False
				self["pause"].show()
			else:
				self.pauseOn=True
				self["play"].show()
				self.slideValue = 0
		
	def Play(self):
		if self.pauseOn == False:
			if self.slideOn:
				self.slideOn=False
				self["play"].show()
			else:
				self.slideOn=True
				self.slideTimer.start(1000, True)
			
			self.slideValue = int(config.pic.slidetime.value)
		
	def slidePic(self):
		if self.slideOn == True and self.pauseOn == False:
			self.blinkingWidget("play")
			self.slideValue -= 1
			if self.slideValue <= 0:
				self.slideValue = int(config.pic.slidetime.value)
				self.nextPic()
		
			self.slideTimer.start(1000, True)

		if self.pauseOn:
			self.blinkingWidget("pause")
			self.slideTimer.start(1000, True)

	def decodePic(self):
		self.currPic = loadPic(self.list[self.index][1], 560, 450, self.aspect, int(config.pic.resize.value), int(config.pic.rotate.value),1)
		self["point"].hide()
		if self.autoShow:
			self.showPic()
			self.autoShow = False
		
	def showPic(self):
		if self.currPic != None:
			self.old = self.index
			self["file"].setText(self.list[self.old][0] + "  (" + str(self.old+1) + "/" + str(self.maxentry+1) + ")")
			self["picture"].instance.setPixmap(self.currPic.__deref__())

		self.next()
		self["point"].show()
		self.decodeTimer.start(300, True)
		
	def nextPic(self):
		self.showPic()
		
	def prevPic(self):
		self.index = self.old
		self.prev()
		self.autoShow = True
		self["point"].show()
		self.decodeTimer.start(300, True)
		
	def next(self):
		self.index += 1
		if self.index > self.maxentry:
			self.index = 0

	def prev(self):
		self.index -= 1
		if self.index < 0:
			self.index = self.maxentry
			
	def blinkingWidget(self, name):
		if self.blinking:
			self.blinking=False
			self[name].show()
		else:
			self.blinking=True
			self[name].hide()

	def StartExif(self):
		if self.pauseOn == False:
			self.Pause()
		self.session.openWithCallback(self.StopExif ,ExifView, self.list[self.old][1], self.list[self.old][0])
		
	def StopExif(self):
		if self.pauseOn:
			self.Pause()

	def Exit(self):
		self.close(self.old)

#------------------------------------------------------------------------------------------

class ExifView(Screen):
	skin = """
		<screen position="80,130" size="560,320" title="Exif-Data" >
			<widget name="exiflist" position="5,5" size="550,310" selectionDisabled="1" />
		</screen>"""
	
	def __init__(self, session, fullname, name):
		self.skin = ExifView.skin
		Screen.__init__(self, session)

		self["actions"] = ActionMap(["OkCancelActions"],
		{
			"cancel": self.close
		}, -1)
		
		dlist = ["Name:", "EXIF-Version:", "Camera-Make:", "Camera-Model:", "Date/Time:", "User Comments:", "Width / Height:", "Orientation:", "Metering Mode:", "Exposure Program:", "Light Source:", "Flash used:", "CompressedBitsPerPixel:", "ISO Speed Rating:", "X-Resolution:", "Y-Resolution:", "Resolution Unit:", "Brightness:", "Exposure Time:", "Exposure Bias:", "Distance:", "CCD-Width:", "ApertureFNumber:"]
		tlist = [ ]
		self["exiflist"] = ServiceInfoList(tlist)
		tlist.append(ServiceInfoListEntry(dlist[0], name))
		count=1
		for x in getExif(fullname):
			tlist.append(ServiceInfoListEntry(dlist[count], x))
			count += 1

#------------------------------------------------------------------------------------------

class PicSetup(Screen):
	skin = """
		<screen position="160,220" size="400,120" title="Settings" >
			<widget name="liste" position="10,10" size="380,100" />
		</screen>"""
	
	def __init__(self, session):
		self.skin = PicSetup.skin
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
		
		self.list = []
		self["liste"] = ConfigList(self.list)
		self.list.append(getConfigListEntry(_("Slideshow Interval (sec.)"), config.pic.slidetime))
		self.list.append(getConfigListEntry(_("Scaling Mode"), config.pic.resize))
		self.list.append(getConfigListEntry(_("Cache Thumbnails"), config.pic.cache))
		#self.list.append(getConfigListEntry(_("Rotate Picture"), config.pic.rotate))
		
	def keyLeft(self):
		self["liste"].handleKey(KEY_LEFT)

	def keyRight(self):
		self["liste"].handleKey(KEY_RIGHT)
		
	def keyNumber(self, number):
		self["liste"].handleKey(KEY_0 + number)


#------------------------------------------------------------------------------------------

class picmain(Screen):
	skin = """
		<screen position="160,90" size="400,390" title="PicturePlayer" >
			<ePixmap position="10,40" size="36,20" pixmap="key_menu-fs8.png" transparent="1" alphatest="on" />
			<ePixmap position="10,70" size="36,20" pixmap="key_info-fs8.png" transparent="1" alphatest="on" />
			<ePixmap position="12,100" size="36,20" pixmap="key_red-fs8.png" transparent="1" alphatest="on" />
			<eLabel text="Settings" position="60,40" size="120,25" font="Regular;20" transparent="1" />
			<eLabel text="Exif-Data" position="60,70" size="120,25" font="Regular;20" transparent="1" />
			<eLabel text="Thumbnails" position="60,100" size="120,25" font="Regular;20" transparent="1" />
			<widget name="thumbnail" position="200,5" size="180,160" alphatest="on" />
			<widget name="filelist" position="5,170" zPosition="2" size="390,210" scrollbarMode="showOnDemand" />
		</screen>"""
	
	def __init__(self, session):
		self.skin = picmain.skin
		Screen.__init__(self, session)

		self["actions"] = ActionMap(["OkCancelActions", "DirectionActions", "ColorActions", "MovieSelectionActions"],
		{
			"ok": self.KeyOk,
			"cancel": self.Exit,
			"right": self.rightDown,
			"left": self.leftUp,
			"up": self.up,
			"down": self.down,
			"showEventInfo": self.StartExif,
			"contextMenu": self.Settings,
			"red": self.StartThumb
		}, -1)
		
		self.aspect = getAspect()
		self.currDir = config.pic.lastDir.value
		if not os.path.exists(self.currDir):
			self.currDir = "/"
		
		self.filelist = FileList(self.currDir, matchingPattern = "(?i)^.*\.(jpeg|jpg|png|bmp)")
		self["filelist"] = self.filelist
		self["thumbnail"] = Pixmap()
		
		self.ThumbTimer = eTimer()
		self.ThumbTimer.timeout.get().append(self.showThumb)
		self.ThumbTimer.start(500, True)
		
	def up(self):
		self["filelist"].up()
		self.ThumbTimer.start(1500, True)

	def down(self):
		self["filelist"].down()
		self.ThumbTimer.start(1500, True)
		
	def leftUp(self):
		self["filelist"].pageUp()
		self.ThumbTimer.start(1500, True)
		
	def rightDown(self):
		self["filelist"].pageDown()
		self.ThumbTimer.start(1500, True)

	def showThumb(self):
		if not self.filelist.canDescent():
			cachefile = ""
			if config.pic.cache.value:
				cachedir = self.currDir + ".Thumbnails/"
				if not os.path.exists(cachedir):
					os.mkdir(cachedir)
				cachefile = cachedir + self.filelist.getSelection()[0] + str(180) + str(160) + str(self.aspect)

			ptr = loadPic(self.currDir + self.filelist.getSelection()[0], 180, 160, self.aspect, int(config.pic.resize.value), 0, 0, cachefile)
			if ptr != None:
				self["thumbnail"].show()
				self["thumbnail"].instance.setPixmap(ptr.__deref__())
		else:
			self["thumbnail"].hide()

	def KeyOk(self):
		if self.filelist.canDescent():
			self.currDir = self.filelist.getSelection()[0]
			self.filelist.descent()
		else:
			self.session.openWithCallback(self.returnVal, PicView, self.filelist.getFileList(), self.filelist.getSelection()[0], self.currDir)
			
	def StartThumb(self):
		self.session.openWithCallback(self.returnVal, ThumbView, self.filelist.getFileList(), self.filelist.getSelection()[0], self.currDir)

	def returnVal(self, val=0):
		print val

	def StartExif(self):
		if not self.filelist.canDescent():
			self.session.open(ExifView, self.currDir + self.filelist.getSelection()[0], self.filelist.getSelection()[0])

	def Settings(self):
		self.session.open(PicSetup)
	
	def Exit(self):
		config.pic.lastDir.value = self.currDir
		config.pic.save()
		self.close()

#------------------------------------------------------------------------------------------

def main(session, **kwargs):
	session.open(picmain)

def Plugins(**kwargs):
	return PluginDescriptor(name="PicturePlayer", description="Picture Viewer (BMP, PNG, JPG)", icon="pictureplayer.png", where = PluginDescriptor.WHERE_PLUGINMENU, fnc=main)
