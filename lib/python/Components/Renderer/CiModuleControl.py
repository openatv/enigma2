from os import popen
from enigma import eDVBCI_UI, eLabel, iPlayableService
from Components.Renderer.Renderer import Renderer
from Components.SystemInfo import BoxInfo
from Components.VariableText import VariableText
from Tools.Hex2strColor import Hex2strColor
from skin import parameters


class CiModuleControl(Renderer, VariableText):
	GUI_WIDGET = eLabel

	def __init__(self):
		Renderer.__init__(self)
		VariableText.__init__(self)
		self.eDVBCIUIInstance = eDVBCI_UI.getInstance()
		self.eDVBCIUIInstance and self.eDVBCIUIInstance.ciStateChanged.get().append(self.ciModuleStateChanged)
		self.text = ""
		self.allVisible = False
		self.noVisibleState = "ciplushelper" in popen("top -n 1").read()
		self.colors = parameters.get("CiModuleControlColors", (0x007F7F7F, 0x00FFFF00, 0x0000FF00, 0x00FF2525))  # "state 0 (no module) gray", "state 1 (init module) yellow", "state 2 (module ready) green", "state -1 (error) red"

	def applySkin(self, desktop, parent):
		attribs = self.skinAttributes[:]
		for (attrib, value) in self.skinAttributes:
			if attrib == "allVisible":
				self.allVisible = value == "1"
				attribs.remove((attrib, value))
				break
		self.skinAttributes = attribs
		return Renderer.applySkin(self, desktop, parent)

	def ciModuleStateChanged(self, slot):
		self.changed(True)

	def changed(self, what):
		if what is True or what[0] == self.CHANGED_SPECIFIC and what[1] == iPlayableService.evStart:
			string = ""
			NUM_CI = BoxInfo.getItem("CommonInterface")
			if NUM_CI and NUM_CI > 0 and self.eDVBCIUIInstance:
				for slot in range(NUM_CI):
					state = self.eDVBCIUIInstance.getState(slot)
					if state == 1 and self.noVisibleState:
						continue
					add_num = True
					if string:
						string += " "
					if state not in (-1, 3):
						if state == 0:
							if not self.allVisible:
								string += ""
								add_num = False
							else:
								string += Hex2strColor(self.colors[0])  # no module
						elif state == 1:
							string += Hex2strColor(self.colors[1])  # init module
						elif state == 2:
							string += Hex2strColor(self.colors[2])  # module ready
					else:
						if not self.allVisible:
							string += ""
							add_num = False
						else:
							string += Hex2strColor(self.colors[3])  # error
					if add_num:
						string += "%d" % (slot + 1)
				if string:
					string = _("CI slot: ") + string
			self.text = string
