#	-*-	coding:	utf-8	-*-
#from imports import *
from twisted.web.client import downloadPage
from enigma import gPixmapPtr, ePicLoad, eTimer
from Components.AVSwitch import AVSwitch
from Components.Pixmap import Pixmap
from Tools.Directories import fileExists
from Components.config import config
import mp_globals
from debuglog import printlog as printl

class CoverHelper:

	COVER_PIC_PATH = "/tmp/Icon.jpg"
	NO_COVER_PIC_PATH = "/images/no_coverArt.png"

	def __init__(self, cover, callback=None, nc_callback=None):
		self._cover = cover
		self.picload = ePicLoad()
		self._no_picPath = "%s/skins/%s%s" % (mp_globals.pluginPath, config.supportchannel.skin.value, self.NO_COVER_PIC_PATH)
		self._callback = callback
		self._nc_callback = nc_callback
		self.coverTimerStart = eTimer()

	def getCoverTimerStart(self):
		self.coverTimerStart.startLongTimer(20)

	def getCover(self, url):
		self.getCoverTimerStart()
		print "getCover:", url
		if url:
			downloadPage(url, self.COVER_PIC_PATH).addCallback(self.showCover).addErrback(self.dataErrorP)
		else:
			self.showCoverNone()

	def dataErrorP(self, error):
		print "dataErrorP:"
		printl(error,self)
		self.showCoverNone()

	def showCover(self, picData):
		print "_showCover:"
		self.showCoverFile(self.COVER_PIC_PATH)

	def showCoverNone(self):
		print "_showCoverNone:"
		if self._nc_callback:
			self._cover.hide()
			self._nc_callback()
		else:
			self.showCoverFile(self._no_picPath)

	def showCoverFile(self, picPath):
		print "showCoverFile:"
		if fileExists(picPath):
			self._cover.instance.setPixmap(gPixmapPtr())
			scale = AVSwitch().getFramebufferScale()
			size = self._cover.instance.size()
			self.picload.setPara((size.width(), size.height(), scale[0], scale[1], False, 1, "#FF000000"))
			if self.picload.startDecode(picPath, 0, 0, False) == 0:
				ptr = self.picload.getData()
				if ptr != None:
					self._cover.instance.setPixmap(ptr)
					self._cover.show()
		else:
			printl("Coverfile not found: %s" % picPath, self, "E")

		if self._callback:
			self._callback()