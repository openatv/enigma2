#	-*-	coding:	utf-8	-*-

from Components.config import config
from yt_url import *

class YoutubeLink:
	def __init__(self, session):
		print "YoutubeLink:"
		self.session = session
		self._callback = None
		self.title = ''
		self.videoPrio = 1

	def getLink(self, cb_play, cb_err, title, url, imgurl):
		print "getLink:"
		print "VideoPrio: ", self.videoPrio
		self._callback = cb_play
		self.title = title
		self.imgurl = imgurl
		y = youtubeUrl(self.session)
		y.addErrback(cb_err)
		y.addCallback(self.cbYTLink)
		y.getVideoUrl(url, self.videoPrio)

	def cbYTLink(self, link):
		print "cbYTLink:",link
		self._callback(self.title, link, imgurl=self.imgurl)