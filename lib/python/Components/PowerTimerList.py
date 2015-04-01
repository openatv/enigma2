from enigma import eListboxPythonMultiContent, eListbox, gFont, getDesktop, \
	RT_HALIGN_LEFT, RT_HALIGN_RIGHT, RT_VALIGN_TOP, RT_VALIGN_BOTTOM

from HTMLComponent import HTMLComponent
from GUIComponent import GUIComponent
from Tools.FuzzyDate import FuzzyTime
from Tools.LoadPixmap import LoadPixmap
from timer import TimerEntry
from Tools.Directories import resolveFilename, SCOPE_ACTIVE_SKIN
from PowerTimer import AFTEREVENT, TIMERTYPE

def gettimerType(timer):
	timertype = {
		TIMERTYPE.WAKEUP: _("Wake Up"),
		TIMERTYPE.WAKEUPTOSTANDBY: _("Wake Up To Standby"),
		TIMERTYPE.STANDBY: _("Standby"),
		TIMERTYPE.AUTOSTANDBY: _("Auto Standby"),
		TIMERTYPE.AUTODEEPSTANDBY: _("Auto Deep Standby"),
		TIMERTYPE.DEEPSTANDBY: _("Deep Standby"),
		TIMERTYPE.REBOOT: _("Reboot"),
		TIMERTYPE.RESTART: _("Restart GUI")
		}[timer.timerType]
	return timertype

def getafterEvent(timer):
	afterevent = {
		AFTEREVENT.NONE: _("Nothing"),
		AFTEREVENT.WAKEUPTOSTANDBY: _("Wake Up To Standby"),
		AFTEREVENT.STANDBY: _("Standby"),
		AFTEREVENT.DEEPSTANDBY: _("Deep Standby")
		}[timer.afterEvent]
	return afterevent

class PowerTimerList(HTMLComponent, GUIComponent, object):
#
#  | <Service>     <Name of the Timer>  |
#  | <start, end>              <state>  |
#
	def buildTimerEntry(self, timer, processed):
		screenwidth = getDesktop(0).size().width()
		height = self.l.getItemSize().height()
		width = self.l.getItemSize().width()
		res = [ None ]
		x = width / 2
		if screenwidth and screenwidth == 1920:
			res.append((eListboxPythonMultiContent.TYPE_TEXT, 39, 3, width, 38, 2, RT_HALIGN_LEFT|RT_VALIGN_BOTTOM, gettimerType(timer)))
		else:
			res.append((eListboxPythonMultiContent.TYPE_TEXT, 26, 3, width, 25, 0, RT_HALIGN_LEFT|RT_VALIGN_BOTTOM, gettimerType(timer)))
		if timer.timerType == TIMERTYPE.AUTOSTANDBY or timer.timerType == TIMERTYPE.AUTODEEPSTANDBY:
			if self.iconRepeat and timer.autosleeprepeat != "once":
				if screenwidth and screenwidth == 1920:
					res.append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHABLEND, 3, 5, 30, 30, self.iconRepeat))
				else:
					res.append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHABLEND, 2, 3, 20, 20, self.iconRepeat))
			icon = None
			if not processed:
				if timer.state == TimerEntry.StateWaiting:
					state = _("waiting")
					icon = self.iconWait
				elif timer.state == TimerEntry.StatePrepared or timer.state == TimerEntry.StateRunning:
					state = _("running...")
					icon = self.iconZapped
				elif timer.state == TimerEntry.StateEnded:
					state = _("done!")
					icon = self.iconDone
				else:
					state = _("<unknown>")
					icon = None
			else:
				state = _("done!")
				icon = self.iconDone
			if screenwidth and screenwidth == 1920:
				res.append((eListboxPythonMultiContent.TYPE_TEXT, 225, 38, width-225, 35, 3, RT_HALIGN_RIGHT|RT_VALIGN_BOTTOM, _("Delay:") + " " + str(timer.autosleepdelay) + "(" + _("mins") + ")"))
			else:
				res.append((eListboxPythonMultiContent.TYPE_TEXT, 150, 26, width-150, 23, 1, RT_HALIGN_RIGHT|RT_VALIGN_BOTTOM, _("Delay:") + " " + str(timer.autosleepdelay) + "(" + _("mins") + ")"))
		else:
			if screenwidth and screenwidth == 1920:
				res.append((eListboxPythonMultiContent.TYPE_TEXT, x+36, 3, x-3-36, 35, 3, RT_HALIGN_RIGHT|RT_VALIGN_BOTTOM, _('At End:') + ' ' + getafterEvent(timer)))
			else:
				res.append((eListboxPythonMultiContent.TYPE_TEXT, x+24, 3, x-2-24, 23, 1, RT_HALIGN_RIGHT|RT_VALIGN_BOTTOM, _('At End:') + ' ' + getafterEvent(timer)))
			days = ( _("Mon"), _("Tue"), _("Wed"), _("Thu"), _("Fri"), _("Sat"), _("Sun") )
			begin = FuzzyTime(timer.begin)
			if timer.repeated:
				repeatedtext = []
				flags = timer.repeated
				for x in (0, 1, 2, 3, 4, 5, 6):
					if flags & 1 == 1:
						repeatedtext.append(days[x])
					flags >>= 1
				repeatedtext = ", ".join(repeatedtext)
				if self.iconRepeat:
					if screenwidth and screenwidth == 1920:
						res.append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHABLEND, 3, 5, 30, 30, self.iconRepeat))
					else:
						res.append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHABLEND, 2, 3, 20, 20, self.iconRepeat))
			else:
				repeatedtext = begin[0] # date
			text = repeatedtext + ((" %s ... %s (%d " + _("mins") + ")") % (begin[1], FuzzyTime(timer.end)[1], (timer.end - timer.begin) / 60))
			if screenwidth and screenwidth == 1920:
				res.append((eListboxPythonMultiContent.TYPE_TEXT, 225, 38, width-225, 35, 3, RT_HALIGN_RIGHT|RT_VALIGN_BOTTOM, text))
			else:
				res.append((eListboxPythonMultiContent.TYPE_TEXT, 150, 26, width-150, 23, 1, RT_HALIGN_RIGHT|RT_VALIGN_BOTTOM, text))
			icon = None
			if not processed:
				if timer.state == TimerEntry.StateWaiting:
					state = _("waiting")
					icon = self.iconWait
				elif timer.state == TimerEntry.StatePrepared:
					state = _("about to start")
					icon = self.iconPrepared
				elif timer.state == TimerEntry.StateRunning:
					state = _("running...")
					icon = self.iconZapped
				elif timer.state == TimerEntry.StateEnded:
					state = _("done!")
					icon = self.iconDone
				else:
					state = _("<unknown>")
					icon = None
			else:
				state = _("done!")
				icon = self.iconDone

		if timer.disabled:
			state = _("disabled")
			icon = self.iconDisabled

		if timer.failed:
			state = _("failed")
			icon = self.iconFailed
		if screenwidth and screenwidth == 1920:
			res.append((eListboxPythonMultiContent.TYPE_TEXT, 39, 38, 225, 35, 3, RT_HALIGN_LEFT|RT_VALIGN_BOTTOM, state))
		else:
			res.append((eListboxPythonMultiContent.TYPE_TEXT, 26, 26, 150, 23, 1, RT_HALIGN_LEFT|RT_VALIGN_BOTTOM, state))
		if icon:
			if screenwidth and screenwidth == 1920:
				res.append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHABLEND, 3, 39, 30, 30, icon))
			else:
				res.append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHABLEND, 2, 26, 20, 20, icon))
		line = LoadPixmap(resolveFilename(SCOPE_ACTIVE_SKIN, "div-h.png"))
		res.append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHABLEND, 0, height-2, width, 2, line))

		return res

	def __init__(self, list):
		GUIComponent.__init__(self)
		self.l = eListboxPythonMultiContent()
		self.l.setBuildFunc(self.buildTimerEntry)
		self.l.setFont(0, gFont("Regular", 20))
		self.l.setFont(1, gFont("Regular", 18))
		self.l.setFont(2, gFont("Regular", 30))
		self.l.setFont(3, gFont("Regular", 27))
		self.l.setItemHeight(50)
		self.l.setList(list)
		self.iconWait = LoadPixmap(resolveFilename(SCOPE_ACTIVE_SKIN, "icons/timer_wait.png"))
		self.iconRecording = LoadPixmap(resolveFilename(SCOPE_ACTIVE_SKIN, "icons/timer_rec.png"))
		self.iconPrepared = LoadPixmap(resolveFilename(SCOPE_ACTIVE_SKIN, "icons/timer_prep.png"))
		self.iconDone = LoadPixmap(resolveFilename(SCOPE_ACTIVE_SKIN, "icons/timer_done.png"))
		self.iconRepeat = LoadPixmap(resolveFilename(SCOPE_ACTIVE_SKIN, "icons/timer_rep.png"))
		self.iconZapped = LoadPixmap(resolveFilename(SCOPE_ACTIVE_SKIN, "icons/timer_zap.png"))
		self.iconDisabled = LoadPixmap(resolveFilename(SCOPE_ACTIVE_SKIN, "icons/timer_off.png"))
		self.iconFailed = LoadPixmap(resolveFilename(SCOPE_ACTIVE_SKIN, "icons/timer_failed.png"))

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

