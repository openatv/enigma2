from HTMLComponent import HTMLComponent
from GUIComponent import GUIComponent

from Tools.FuzzyDate import FuzzyTime

from enigma import eListboxPythonMultiContent, eListbox, gFont, \
	RT_HALIGN_LEFT, RT_HALIGN_RIGHT, RT_VALIGN_CENTER, RT_VALIGN_TOP, RT_VALIGN_BOTTOM
from Tools.LoadPixmap import LoadPixmap
from timer import TimerEntry
from Tools.Directories import resolveFilename, SCOPE_CURRENT_SKIN, SCOPE_SKIN_IMAGE

class TimerList(HTMLComponent, GUIComponent, object):
#
#  | <Service>     <Name of the Timer>  |
#  | <start, end>              <state>  |
#
	def buildTimerEntry(self, timer, processed):
		width = self.l.getItemSize().width()
		res = [ None ]
		if timer.disabled:
			png = LoadPixmap(resolveFilename(SCOPE_SKIN_IMAGE, "skin_default/icons/redx.png"))
			res.append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHATEST, width-40, 1, 40, 40, png))
			width -= 40
		x = (2*width) // 3
		res.append((eListboxPythonMultiContent.TYPE_TEXT, 0, 0, x, 25, 1, RT_HALIGN_LEFT|RT_VALIGN_BOTTOM, timer.name))
		res.append((eListboxPythonMultiContent.TYPE_TEXT, x, 0, width-x, 25, 0, RT_HALIGN_RIGHT|RT_VALIGN_BOTTOM, timer.service_ref.getServiceName()))

		days = ( _("Mon"), _("Tue"), _("Wed"), _("Thu"), _("Fri"), _("Sat"), _("Sun") )
		if timer.repeated:
			repeatedtext = []
			flags = timer.repeated
			for x in (0, 1, 2, 3, 4, 5, 6):
				if (flags & 1 == 1):
					repeatedtext.append(days[x])
				flags = flags >> 1
			repeatedtext = ", ".join(repeatedtext)
		else:
			repeatedtext = ""
		if timer.justplay:
			text = repeatedtext + ((" %s "+ _("(ZAP)")) % (FuzzyTime(timer.begin)[1])) 
		else:
			text = repeatedtext + ((" %s ... %s (%d " + _("mins") + ")") % (FuzzyTime(timer.begin)[1], FuzzyTime(timer.end)[1], (timer.end - timer.begin) / 60))
		res.append((eListboxPythonMultiContent.TYPE_TEXT, 150, 25, width-150, 20, 1, RT_HALIGN_RIGHT|RT_VALIGN_TOP, text))

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
			elif timer.state == TimerEntry.StateEnded:
				state = _("done!")
			else:
				state = _("<unknown>")
		else:
			state = _("done!")

		if timer.disabled:
			state = _("disabled")

		res.append((eListboxPythonMultiContent.TYPE_TEXT, 0, 25, 150, 20, 1, RT_HALIGN_LEFT|RT_VALIGN_TOP, state))

		return res

	def __init__(self, list):
		GUIComponent.__init__(self)
		self.l = eListboxPythonMultiContent()
		self.l.setBuildFunc(self.buildTimerEntry)
		self.l.setFont(0, gFont("Regular", 20))
		self.l.setFont(1, gFont("Regular", 18))
		self.l.setItemHeight(50)
		self.l.setList(list)
	
	def getCurrent(self):
		cur = self.l.getCurrentSelection()
		return cur and cur[0]
	
	GUI_WIDGET = eListbox
	
	def postWidgetCreate(self, instance):
		instance.setContent(self.l)

	def moveToIndex(self, index):
		self.instance.moveSelectionTo(index)

	def getCurrentIndex(self):
		return self.instance.getCurrentIndex()

	currentIndex = property(getCurrentIndex, moveToIndex)
	currentSelection = property(getCurrent)

	def moveDown(self):
		self.instance.moveSelection(self.instance.moveDown)

	def invalidate(self):
		self.l.invalidate()

	def entryRemoved(self, idx):
		self.l.entryRemoved(idx)

