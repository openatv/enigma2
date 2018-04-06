from enigma import eListboxPythonMultiContent, eListbox, gFont, getDesktop, \
	RT_HALIGN_LEFT, RT_HALIGN_RIGHT, RT_VALIGN_TOP, RT_VALIGN_BOTTOM

from HTMLComponent import HTMLComponent
from GUIComponent import GUIComponent
from skin import parseFont
from Tools.FuzzyDate import FuzzyTime
from Tools.LoadPixmap import LoadPixmap
from timer import TimerEntry
from Tools.Directories import resolveFilename, SCOPE_ACTIVE_SKIN
from PowerTimer import AFTEREVENT, TIMERTYPE

def gettimerType(timer):
	timertype = {
		TIMERTYPE.NONE: _("Nothing"),
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
		AFTEREVENT.WAKEUP: _("Wake Up"),
		AFTEREVENT.WAKEUPTOSTANDBY: _("Wake Up To Standby"),
		AFTEREVENT.STANDBY: _("Standby"),
		AFTEREVENT.DEEPSTANDBY: _("Deep Standby")
		}[timer.afterEvent]
	return afterevent

class PowerTimerList(HTMLComponent, GUIComponent, object):
#
#  | <Name of the Timer>  <action after Timer > |
#  | <state>          <time range> <start, end> |
#
	def buildTimerEntry(self, timer, processed):
		height = self.l.getItemSize().height()
		width = self.l.getItemSize().width()
		res = [ None ]
		res.append((eListboxPythonMultiContent.TYPE_TEXT, self.iconWidth + self.iconMargin, 0, width, self.rowSplit, 0, RT_HALIGN_LEFT|RT_VALIGN_BOTTOM, gettimerType(timer)))
		if timer.timerType == TIMERTYPE.AUTOSTANDBY or timer.timerType == TIMERTYPE.AUTODEEPSTANDBY:
			if self.iconRepeat and timer.autosleeprepeat != "once":
				res.append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHABLEND, self.iconMargin / 2, self.rowSplit + (self.itemHeight - self.rowSplit - self.iconHeight) / 2, self.iconWidth, self.iconHeight, self.iconRepeat))
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
			autosleepwindow = ""
			if timer.autosleepwindow == 'yes':
				autosleepwindow = _("Time range:") + " " + FuzzyTime(timer.autosleepbegin)[1] + " ... " + FuzzyTime(timer.autosleepend)[1] + ", "
			res.append((eListboxPythonMultiContent.TYPE_TEXT, self.satPosLeft, self.rowSplit, width-self.satPosLeft, self.itemHeight - self.rowSplit, 1, RT_HALIGN_RIGHT|RT_VALIGN_TOP, autosleepwindow + _("Delay:") + " " + str(timer.autosleepdelay) + " (" + _("mins") + ")"))
		else:
			res.append((eListboxPythonMultiContent.TYPE_TEXT, self.satPosLeft, 0, width - self.satPosLeft, self.rowSplit, 2, RT_HALIGN_RIGHT|RT_VALIGN_BOTTOM, _('At End:') + ' ' + getafterEvent(timer)))
			begin = FuzzyTime(timer.begin)
			if timer.repeated:
				days = ( _("Mon"), _("Tue"), _("Wed"), _("Thu"), _("Fri"), _("Sat"), _("Sun") )
				repeatedtext = []
				flags = timer.repeated
				for x in (0, 1, 2, 3, 4, 5, 6):
					if flags & 1 == 1:
						repeatedtext.append(days[x])
					flags >>= 1
				if repeatedtext == [_("Mon"), _("Tue"), _("Wed"), _("Thu"), _("Fri"), _("Sat"), _("Sun")]:
					repeatedtext = _('Everyday')
				elif repeatedtext == [_("Mon"), _("Tue"), _("Wed"), _("Thu"), _("Fri")]:
					repeatedtext = _('Weekday')
				elif repeatedtext == [_("Sat"), _("Sun")]:
					repeatedtext = _('Weekend')
				else:
					repeatedtext = ", ".join(repeatedtext)
				if self.iconRepeat:
					res.append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHABLEND, self.iconMargin / 2, self.rowSplit + (self.itemHeight - self.rowSplit - self.iconHeight) / 2, self.iconWidth, self.iconHeight, self.iconRepeat))
			else:
				repeatedtext = begin[0] # date
			text = repeatedtext + ((" %s ... %s (%d " + _("mins") + ")") % (begin[1], FuzzyTime(timer.end)[1], (timer.end - timer.begin) / 60))
			res.append((eListboxPythonMultiContent.TYPE_TEXT, self.satPosLeft, self.rowSplit, width-self.satPosLeft, self.itemHeight - self.rowSplit, 1, RT_HALIGN_RIGHT|RT_VALIGN_TOP, text))
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
		icon and res.append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHABLEND, self.iconMargin / 2, (self.rowSplit - self.iconHeight) / 2, self.iconWidth, self.iconHeight, icon))
		res.append((eListboxPythonMultiContent.TYPE_TEXT, self.iconWidth + self.iconMargin, self.rowSplit, self.satPosLeft - self.iconWidth - self.iconMargin, self.itemHeight - self.rowSplit, 1, RT_HALIGN_LEFT|RT_VALIGN_TOP, state))
		line = LoadPixmap(resolveFilename(SCOPE_ACTIVE_SKIN, "div-h.png"))
		res.append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHABLEND, 0, height-2, width, 2, line))

		return res

	def __init__(self, list):
		GUIComponent.__init__(self)
		self.l = eListboxPythonMultiContent()
		self.l.setBuildFunc(self.buildTimerEntry)
		self.serviceNameFont = gFont("Regular", 20)
		self.font = gFont("Regular", 18)
		self.eventNameFont = gFont("Regular", 18)
		self.l.setList(list)
		self.itemHeight = 50
		self.rowSplit = 25
		self.iconMargin = 4
		self.satPosLeft = 160
		self.iconWait = LoadPixmap(resolveFilename(SCOPE_ACTIVE_SKIN, "icons/timer_wait.png"))
		self.iconWidth = self.iconWait.size().width()
		self.iconHeight = self.iconWait.size().height()
		self.iconRecording = LoadPixmap(resolveFilename(SCOPE_ACTIVE_SKIN, "icons/timer_rec.png"))
		self.iconPrepared = LoadPixmap(resolveFilename(SCOPE_ACTIVE_SKIN, "icons/timer_prep.png"))
		self.iconDone = LoadPixmap(resolveFilename(SCOPE_ACTIVE_SKIN, "icons/timer_done.png"))
		self.iconRepeat = LoadPixmap(resolveFilename(SCOPE_ACTIVE_SKIN, "icons/timer_rep.png"))
		self.iconZapped = LoadPixmap(resolveFilename(SCOPE_ACTIVE_SKIN, "icons/timer_zap.png"))
		self.iconDisabled = LoadPixmap(resolveFilename(SCOPE_ACTIVE_SKIN, "icons/timer_off.png"))
		self.iconFailed = LoadPixmap(resolveFilename(SCOPE_ACTIVE_SKIN, "icons/timer_failed.png"))

	def applySkin(self, desktop, parent):
		def itemHeight(value):
			self.itemHeight = int(value)
		def setServiceNameFont(value):
			self.serviceNameFont = parseFont(value, ((1,1),(1,1)))
		def setEventNameFont(value):
			self.eventNameFont = parseFont(value, ((1,1),(1,1)))
		def setFont(value):
			self.font = parseFont(value, ((1,1),(1,1)))
		def rowSplit(value):
			self.rowSplit = int(value)
		def iconMargin(value):
			self.iconMargin = int(value)
		def satPosLeft(value):
			self.satPosLeft = int(value)
		for (attrib, value) in list(self.skinAttributes):
			try:
				locals().get(attrib)(value)
				self.skinAttributes.remove((attrib, value))
			except:
				pass
		self.l.setItemHeight(self.itemHeight)
		self.l.setFont(0, self.serviceNameFont)
		self.l.setFont(1, self.font)
		self.l.setFont(2, self.eventNameFont)
		return GUIComponent.applySkin(self, desktop, parent)

	def getCurrent(self):
		cur = self.l.getCurrentSelection()
		return cur and cur[0]

	GUI_WIDGET = eListbox

	def postWidgetCreate(self, instance):
		instance.setContent(self.l)
		self.instance = instance

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

