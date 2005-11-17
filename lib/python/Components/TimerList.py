from HTMLComponent import *
from GUIComponent import *

from Tools.FuzzyDate import FuzzyTime
import time

from enigma import eListboxPythonMultiContent, eListbox, gFont
from timer import TimerEntry

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
#  | <start, end>              <state>  |
#
def TimerEntryComponent(timer, processed):
	res = [ timer ]
	
	print time.strftime("%c", time.localtime(timer.begin))
	print time.strftime("%c", time.localtime(timer.end))
		
	res.append((0, 0, 400, 30, 0, RT_HALIGN_LEFT, timer.service_ref.getServiceName()))
	repeatedtext = ""
	days = [ "Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun" ]
	if (timer.repeated != 0):
		flags = timer.repeated
		count = 0
		for x in range(0, 7):
				if (flags & 1 == 1):
					if (count != 0):
						repeatedtext += ", "
					repeatedtext += days[x]
					count += 1
				flags = flags >> 1
		res.append((0, 30, 200, 20, 1, RT_HALIGN_LEFT, repeatedtext + (" %s ... %s" % (FuzzyTime(timer.begin)[1], FuzzyTime(timer.end)[1]))))
	else:
		res.append((0, 30, 200, 20, 1, RT_HALIGN_LEFT, repeatedtext + ("%s, %s ... %s" % (FuzzyTime(timer.begin) + FuzzyTime(timer.end)[1:]))))

	res.append((300, 0, 200, 20, 1, RT_HALIGN_RIGHT, timer.description))
	
	if not processed:
		if timer.state == TimerEntry.StateWait:
			state = "waiting"
		elif timer.state == TimerEntry.StatePrepare:
			state = "about to start"
		elif timer.state == TimerEntry.StateRunning:
			state = "recording..."
		else:
			state = "<unknown>"
	else:
		state = "done!"
	
	res.append((300, 30, 200, 20, 1, RT_HALIGN_RIGHT, state))
	
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

	def invalidate(self):
		self.l.invalidate()

