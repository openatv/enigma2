from enigma import eListboxPythonMultiContent, eListbox, gFont, RT_HALIGN_LEFT, RT_HALIGN_RIGHT, RT_VALIGN_TOP, RT_VALIGN_BOTTOM, getDesktop

from HTMLComponent import HTMLComponent
from GUIComponent import GUIComponent
from Tools.FuzzyDate import FuzzyTime
from Tools.LoadPixmap import LoadPixmap
from timer import TimerEntry
from Tools.Directories import resolveFilename, SCOPE_ACTIVE_SKIN


class TimerList(HTMLComponent, GUIComponent, object):
#
#  | <Name of the Timer>     <Service>  <orb.pos>|
#  | <state>  <start, end>  |
#
	def buildTimerEntry(self, timer, processed):
		screenwidth = getDesktop(0).size().width()
		height = self.l.getItemSize().height()
		width = self.l.getItemSize().width()
		res = [ None ]
		x = (2*width) // 3
		if screenwidth and screenwidth == 1920:
			res.append((eListboxPythonMultiContent.TYPE_TEXT, 39, 3, x-36, 38, 3, RT_HALIGN_LEFT|RT_VALIGN_BOTTOM, timer.name))
		else:
			res.append((eListboxPythonMultiContent.TYPE_TEXT, 26, 3, x-24, 25, 0, RT_HALIGN_LEFT|RT_VALIGN_BOTTOM, timer.name))
		text = ("%s  %s") % (timer.service_ref.getServiceName(), self.getOrbitalPos(timer.service_ref))
		if screenwidth and screenwidth == 1920:
			res.append((eListboxPythonMultiContent.TYPE_TEXT, x, 3, width-x-3, 35, 4, RT_HALIGN_RIGHT|RT_VALIGN_BOTTOM, text))
		else:
			res.append((eListboxPythonMultiContent.TYPE_TEXT, x, 3, width-x-2, 23, 1, RT_HALIGN_RIGHT|RT_VALIGN_BOTTOM, text))

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
		if timer.justplay:
			text = repeatedtext + ((" %s "+ _("(ZAP)")) % (begin[1]))
		else:
			text = repeatedtext + ((" %s ... %s (%d " + _("mins") + ")") % (begin[1], FuzzyTime(timer.end)[1], (timer.end - timer.begin) / 60))
		if screenwidth and screenwidth == 1920:
			res.append((eListboxPythonMultiContent.TYPE_TEXT, 225, 38, width-225, 35, 4, RT_HALIGN_RIGHT|RT_VALIGN_BOTTOM, text))
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
				if timer.justplay:
					state = _("zapped")
					icon = self.iconZapped
				else:
					state = _("recording...")
					icon = self.iconRecording
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
			res.append((eListboxPythonMultiContent.TYPE_TEXT, 39, 38, 225, 35, 4, RT_HALIGN_LEFT|RT_VALIGN_BOTTOM, state))
		else:
			res.append((eListboxPythonMultiContent.TYPE_TEXT, 26, 26, 150, 23, 1, RT_HALIGN_LEFT|RT_VALIGN_BOTTOM, state))
		if icon:
			if screenwidth and screenwidth == 1920:
				res.append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHABLEND, 3, 39, 30, 30, icon))
			else:
				res.append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHABLEND, 2, 26, 20, 20, icon))

		if timer.isAutoTimer:
			if screenwidth and screenwidth == 1920:
				res.append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHABLEND, 3, 5, 30, 30, self.iconAutoTimer))
			else:
				res.append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHABLEND, 2, 3, 20, 20, self.iconAutoTimer))
		line = LoadPixmap(resolveFilename(SCOPE_ACTIVE_SKIN, "div-h.png"))
		res.append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHABLEND, 0, height-2, width, 2, line))

		return res

	def __init__(self, list):
		GUIComponent.__init__(self)
		self.l = eListboxPythonMultiContent()
		self.l.setBuildFunc(self.buildTimerEntry)
		self.l.setFont(0, gFont("Regular", 20))
		self.l.setFont(1, gFont("Regular", 18))
		self.l.setFont(2, gFont("Regular", 16))
		self.l.setFont(3, gFont("Regular", 30))
		self.l.setFont(4, gFont("Regular", 27))
		self.l.setFont(5, gFont("Regular", 24))
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
		self.iconAutoTimer = LoadPixmap(resolveFilename(SCOPE_ACTIVE_SKIN, "icons/timer_autotimer.png"))

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

	def getOrbitalPos(self, ref):
		refstr = None
		if hasattr(ref, 'sref'):
			refstr = str(ref.sref)
		else:
			refstr = str(ref)

		if '%3a//' in refstr:
			return "%s" % _("Stream")
		op = int(refstr.split(':', 10)[6][:-4] or "0",16)
		if op == 0xeeee:
			return "%s" % _("DVB-T")
		if op == 0xffff:
			return "%s" % _("DVB-C")
		direction = 'E'
		if op > 1800:
			op = 3600 - op
			direction = 'W'
		return ("%d.%d\xc2\xb0%s") % (op // 10, op % 10, direction)

