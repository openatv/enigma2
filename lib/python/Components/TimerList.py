from HTMLComponent import *
from GUIComponent import *

from Tools.FuzzyDate import FuzzyTime
import time

from enigma import eListboxPythonMultiContent, eListbox, gFont, loadPNG
from timer import TimerEntry
from Tools.Directories import resolveFilename, SCOPE_SKIN_IMAGE

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
	
	res.append((eListboxPythonMultiContent.TYPE_TEXT, 0, 0, 560, 30, 0, RT_HALIGN_LEFT|RT_VALIGN_CENTER, timer.service_ref.getServiceName()))
	res.append((eListboxPythonMultiContent.TYPE_TEXT, 0, 30, 560, 20, 1, RT_HALIGN_LEFT|RT_VALIGN_CENTER, timer.name))
	
	repeatedtext = ""
	days = [ _("Mon"), _("Tue"), _("Wed"), _("Thu"), _("Fri"), _("Sat"), _("Sun") ]
	if timer.repeated:
		flags = timer.repeated
		count = 0
		for x in range(0, 7):
				if (flags & 1 == 1):
					if (count != 0):
						repeatedtext += ", "
					repeatedtext += days[x]
					count += 1
				flags = flags >> 1
		if timer.justplay:
			res.append((eListboxPythonMultiContent.TYPE_TEXT, 0, 50, 400, 20, 1, RT_HALIGN_LEFT|RT_VALIGN_CENTER, repeatedtext + ((" %s "+ _("(ZAP)")) % (FuzzyTime(timer.begin)[1], FuzzyTime(timer.end)[1]))))
		else:
			res.append((eListboxPythonMultiContent.TYPE_TEXT, 0, 50, 400, 20, 1, RT_HALIGN_LEFT|RT_VALIGN_CENTER, repeatedtext + (" %s ... %s" % (FuzzyTime(timer.begin)[1], FuzzyTime(timer.end)[1]))))
	else:
		if timer.justplay:
			res.append((eListboxPythonMultiContent.TYPE_TEXT, 0, 50, 400, 20, 1, RT_HALIGN_LEFT|RT_VALIGN_CENTER, repeatedtext + (("%s, %s " + _("(ZAP)")) % (FuzzyTime(timer.begin)))))
		else:
			res.append((eListboxPythonMultiContent.TYPE_TEXT, 0, 50, 400, 20, 1, RT_HALIGN_LEFT|RT_VALIGN_CENTER, repeatedtext + ("%s, %s ... %s" % (FuzzyTime(timer.begin) + FuzzyTime(timer.end)[1:]))))

	if not processed:
		if timer.state == TimerEntry.StateWaiting:
			state = _("waiting")
		elif timer.state == TimerEntry.StatePrepared:
			state = _("about to start")
		elif timer.state == TimerEntry.StateRunning:
			if timer.justplay:
				state = _("zapped")
			else:
				state = _("recording...")
		else:
			state = _("<unknown>")
	else:
		state = _("done!")
	
	res.append((eListboxPythonMultiContent.TYPE_TEXT, 320, 50, 240, 20, 1, RT_HALIGN_RIGHT|RT_VALIGN_CENTER, state))

	if timer.disabled:
		png = loadPNG(resolveFilename(SCOPE_SKIN_IMAGE, "redx.png"))
		res.append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHATEST, 490, 5, 40, 40, png))
	
	return res

class TimerList(HTMLComponent, GUIComponent):
	def __init__(self, list):
		GUIComponent.__init__(self)
		self.l = eListboxPythonMultiContent()
		self.l.setList(list)
		self.l.setFont(0, gFont("Regular", 20))
		self.l.setFont(1, gFont("Regular", 18))
	
	def getCurrent(self):
		return self.l.getCurrentSelection()
	
	def GUIcreate(self, parent):
		self.instance = eListbox(parent)
		self.instance.setContent(self.l)
		self.instance.setItemHeight(70)

	def moveToIndex(self, index):
		self.instance.moveSelectionTo(index)

	def getCurrentIndex(self):
		return self.instance.getCurrentIndex()

	def moveDown(self):
		self.instance.moveSelection(self.instance.moveDown)

	def GUIdelete(self):
		self.instance.setContent(None)
		self.instance = None

	def invalidate(self):
		self.l.invalidate()

