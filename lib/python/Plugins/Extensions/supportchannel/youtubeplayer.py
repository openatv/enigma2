#	-*-	coding:	utf-8	-*-

from Components.config import config
from Screens.MessageBox import MessageBox
from simpleplayer import SimplePlayer
from youtubelink import YoutubeLink

class YoutubePlayer(SimplePlayer):

	def __init__(self, session, playList, playIdx=0, playAll=False, listTitle=None, plType='local', title_inr=0, showPlaylist=True, showCover=False):
		print "YoutubePlayer:"
		SimplePlayer.__init__(self, session, playList, playIdx=playIdx, playAll=playAll, listTitle=listTitle, plType=plType, title_inr=title_inr, ltype='youtube', showPlaylist=showPlaylist, cover=showCover)

	def getVideo(self):
		print "getVideo:"
		dhTitle = self.playList[self.playIdx][self.title_inr]
		if len(self.playList[self.playIdx]) >= 6:
			gid = self.playList[self.playIdx][5]
			if gid in ('P', 'C'):
				self.dataError('This isn\'t a video: '+dhTitle)
				return
		dhVideoId = self.playList[self.playIdx][2]
		imgurl =  self.playList[self.playIdx][3]
		YoutubeLink(self.session).getLink(self.playStream, self.ytError, dhTitle, dhVideoId, imgurl=imgurl)

	def ytError(self, error):
		msg = "Title: %s\n%s" % (self.playList[self.playIdx][self.title_inr], error)
		self.dataError(msg)