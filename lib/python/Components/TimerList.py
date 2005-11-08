from HTMLComponent import *
from GUIComponent import *

from Tools.FuzzyDate import FuzzyTime

from enigma import eListboxPythonMultiContent, eListbox, gFont


RT_HALIGN_LEFT = 0
RT_HALIGN_RIGHT = 1
RT_HALIGN_CENTER = 2
RT_HALIGN_BLOCK = 4

RT_VALIGN_TOP = 0
RT_VALIGN_CENTER = 8
RT_VALIGN_BOTTOM = 16

RT_WRAP = 32


#
#  | <Service>     <Name of the Timer>  |
#  | <start>                     <end>  |
#
def TimerEntry(timer, processed):
	res = [ timer ]
	

	res.append((0, 0, 400, 30, 0, RT_HALIGN_LEFT, timer.service_ref.getServiceName()))
	res.append((0, 30, 200, 20, 1, RT_HALIGN_LEFT, "%s, %s" % FuzzyTime(timer.begin)))

	res.append((200, 0, 200, 20, 1, RT_HALIGN_RIGHT, timer.description))	
	if processed:
		res.append((200, 30, 200, 20, 1, RT_HALIGN_RIGHT, FuzzyTime(timer.end)[1]))
	else:
		res.append((200, 30, 200, 20, 1, RT_HALIGN_RIGHT, "done"))
	return res

class TimerList(HTMLComponent, GUIComponent):
	def __init__(self, list):
		GUIComponent.__init__(self)
		self.l = eListboxPythonMultiContent()
		self.l.setList(list)
		self.l.setFont(0, gFont("Arial", 20))
		self.l.setFont(1, gFont("Arial", 18))
	
	def getCurrent(self):
		return self.l.getCurrentSelection()
	
	def GUIcreate(self, parent):
		self.instance = eListbox(parent)
		self.instance.setContent(self.l)
		self.instance.setItemHeight(50)
	
	def GUIdelete(self):
		self.instance.setContent(None)
		self.instance = None


