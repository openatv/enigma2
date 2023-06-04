from __future__ import print_function
from __future__ import absolute_import
from Screens.Screen import Screen
from Screens.ChoiceBox import ChoiceBox
from Components.SystemInfo import BoxInfo


class ResolutionSelection(Screen):
	def __init__(self, session, infobar=None):
		Screen.__init__(self, session)

		if BoxInfo.getItem("AmlogicFamily"):
			xresString = open("/sys/class/video/frame_width", "r").read()
			yresString = open("/sys/class/video/frame_height", "r").read()
			fpsString = open("/proc/stb/vmpeg/0/frame_rate", "r").read()
			xres = int(xresString)
			yres = int(yresString)
			fps = int(fpsString)
		else:
			xresString = open("/proc/stb/vmpeg/0/xres", "r").read()
			yresString = open("/proc/stb/vmpeg/0/yres", "r").read()
			fpsString = open("/proc/stb/vmpeg/0/framerate", "r").read()
			xres = int(xresString, 16)
			yres = int(yresString, 16)
			fps = int(fpsString, 16)
			fpsFloat = float(fps)
			fpsFloat = fpsFloat / 1000

		selection = 0
		tlist = []
		tlist.append((_("Exit"), "exit"))
		tlist.append((_("Auto(not available)"), "auto"))
		tlist.append((_("Video: ") + str(xres) + "x" + str(yres) + "@" + str(fpsFloat) + "hz", ""))
		tlist.append(("--", ""))
		tlist.append(("576i", "576i50"))
		tlist.append(("576p", "576p50"))
		tlist.append(("720p", "720p50"))
		tlist.append(("1080i", "1080i50"))
		tlist.append(("1080p@23.976hz", "1080p23"))
		tlist.append(("1080p@24hz", "1080p24"))
		tlist.append(("1080p@25hz", "1080p25"))

		keys = ["green", "yellow", "blue", "", "0", "1", "2", "3", "4", "5", "6", "7", "8", "9"]

		if BoxInfo.getItem("AmlogicFamily"):
			mode = open("/sys/class/display/mode").read()[:-1]
		else:
			mode = open("/proc/stb/video/videomode").read()[:-1]
		print(mode)
		for x in list(range(len(tlist))):
			if tlist[x][1] == mode:
				selection = x

		self.session.openWithCallback(self.ResolutionSelected, ChoiceBox, title=_("Please select a resolution..."), list=tlist, selection=selection, keys=keys)
		#return

	def ResolutionSelected(self, Resolution):
		if not Resolution is None:
			if isinstance(Resolution[1], str):
				if Resolution[1] == "exit":
					self.ExGreen_toggleGreen()
				elif Resolution[1] != "auto":
					if BoxInfo.getItem("AmlogicFamily"):
						open("/sys/class/display/mode", "w").write(Resolution[1])
					else:
						open("/proc/stb/video/videomode", "w").write(Resolution[1])
					from enigma import gFBDC
					gFBDC.getInstance().setResolution(-1, -1)
					self.ExGreen_toggleGreen()
		return
