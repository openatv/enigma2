from Screens.Screen import Screen

from Components.VideoWindow import VideoWindow

class PictureInPicture(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		
		self["video"] = VideoWindow()