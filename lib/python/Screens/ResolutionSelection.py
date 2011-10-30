from Screen import Screen
from Screens.ChoiceBox import ChoiceBox

class ResolutionSelection(Screen):
	def __init__(self, session, infobar=None):
		Screen.__init__(self, session)
		self.session = session
		
		xresString = open("/proc/stb/vmpeg/0/xres", "r").read()
		yresString = open("/proc/stb/vmpeg/0/yres", "r").read()
		fpsString = open("/proc/stb/vmpeg/0/framerate", "r").read()
		xres = int(xresString, 16)
		yres = int(yresString, 16)
		fps = int(fpsString, 16)
		fpsFloat = float(fps)
		fpsFloat = fpsFloat/1000


		selection = 0 
		tlist = [] 
		tlist.append((_("Exit"), "exit")) 
		tlist.append((_("Auto(not available)"), "auto")) 
		tlist.append(("Video: " + str(xres) + "x" + str(yres) + "@" + str(fpsFloat) + "hz", "")) 
		tlist.append(("--", "")) 
		tlist.append(("576i", "576i50")) 
		tlist.append(("576p", "576p50")) 
		tlist.append(("720p", "720p50")) 
		tlist.append(("1080i", "1080i50")) 
		tlist.append(("1080p@23.976hz", "1080p23")) 
		tlist.append(("1080p@24hz", "1080p24")) 
		tlist.append(("1080p@25hz", "1080p25")) 

		keys = ["green", "yellow", "blue", "", "0", "1", "2", "3", "4", "5", "6", "7", "8", "9" ] 

		mode = open("/proc/stb/video/videomode").read()[:-1] 
		print mode 
		for x in range(len(tlist)): 
			if tlist[x][1] == mode: 
				selection = x

		self.session.openWithCallback(self.ResolutionSelected, ChoiceBox, title=_("Please select a resolution..."), list = tlist, selection = selection, keys = keys)
		#return

	def ResolutionSelected(self, Resolution):
		if not Resolution is None:
			if isinstance(Resolution[1], str):
				if Resolution[1] == "exit":
					self.ExGreen_toggleGreen()
				elif Resolution[1] != "auto":
					open("/proc/stb/video/videomode", "w").write(Resolution[1]) 
					from enigma import gFBDC
					gFBDC.getInstance().setResolution(-1, -1)
					self.ExGreen_toggleGreen()
		return
