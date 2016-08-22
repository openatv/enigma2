from HTMLComponent import HTMLComponent
from GUIComponent import GUIComponent
from skin import parseFont

from Tools.FuzzyDate import FuzzyTime

from enigma import eListboxPythonMultiContent, eListbox, gFont, RT_HALIGN_LEFT, RT_HALIGN_RIGHT, RT_VALIGN_CENTER, RT_VALIGN_TOP, RT_VALIGN_BOTTOM
from Tools.Alternatives import GetWithAlternative
from Tools.LoadPixmap import LoadPixmap
from Tools.TextBoundary import getTextBoundarySize
from timer import TimerEntry
from Tools.Directories import resolveFilename, SCOPE_ACTIVE_SKIN


class TimerList(HTMLComponent, GUIComponent, object):
#
#  | <Name of the Timer>    <Service> |
#  | <state>  <orb.pos>  <start, end> |
#
	def buildTimerEntry(self, timer, processed):
		height = self.l.getItemSize().height()
		width = self.l.getItemSize().width()
		res = [ None ]

		serviceName = "  " + timer.service_ref.getServiceName()

		serviceNameWidth = getTextBoundarySize(self.instance, self.serviceNameFont, self.l.getItemSize(), serviceName).width()
		if 200 > width - serviceNameWidth - self.iconWidth - self.iconMargin:
			serviceNameWidth = width - 200 - self.iconWidth - self.iconMargin

		res.append((eListboxPythonMultiContent.TYPE_TEXT, width - serviceNameWidth, 0, serviceNameWidth, self.rowSplit, 0, RT_HALIGN_RIGHT|RT_VALIGN_BOTTOM, serviceName))
		res.append((eListboxPythonMultiContent.TYPE_TEXT, self.iconWidth + self.iconMargin, 0, width - serviceNameWidth - self.iconWidth - self.iconMargin, self.rowSplit, 2, RT_HALIGN_LEFT|RT_VALIGN_BOTTOM, timer.name))

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
		if timer.justplay:
			if timer.end > timer.begin + 3:
				text = repeatedtext + ((" %s ... %s (" + _("ZAP") + ", %d " + _("mins") + ")") % (begin[1], FuzzyTime(timer.end)[1], (timer.end - timer.begin) / 60))
			else:
				text = repeatedtext + ((" %s (" + _("ZAP") + ")") % (begin[1]))
		else:
			text = repeatedtext + ((" %s ... %s (%d " + _("mins") + ")") % (begin[1], FuzzyTime(timer.end)[1], (timer.end - timer.begin) / 60))

		icon = None
		if not processed:
			if timer.state == TimerEntry.StateWaiting:
				state = _("waiting")
				if timer.isAutoTimer:
					icon = self.iconAutoTimer
				else:
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
		elif timer.disabled:
			state = _("disabled")
			icon = self.iconDisabled
		elif timer.failed:
			state = _("failed")
			icon = self.iconFailed
		else:
			state = _("done!")
			icon = self.iconDone

		icon and res.append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHABLEND, self.iconMargin / 2, (self.rowSplit - self.iconHeight) / 2, self.iconWidth, self.iconHeight, icon))

		orbpos = self.getOrbitalPos(timer.service_ref)
		orbposWidth = getTextBoundarySize(self.instance, self.font, self.l.getItemSize(), orbpos).width()
		res.append((eListboxPythonMultiContent.TYPE_TEXT, self.satPosLeft, self.rowSplit, orbposWidth, self.itemHeight - self.rowSplit, 1, RT_HALIGN_LEFT|RT_VALIGN_TOP, orbpos))
		res.append((eListboxPythonMultiContent.TYPE_TEXT, self.iconWidth + self.iconMargin, self.rowSplit, self.satPosLeft - self.iconWidth - self.iconMargin, self.itemHeight - self.rowSplit, 1, RT_HALIGN_LEFT|RT_VALIGN_TOP, state))
		res.append((eListboxPythonMultiContent.TYPE_TEXT, self.satPosLeft + orbposWidth, self.rowSplit, width - self.satPosLeft - orbposWidth, self.itemHeight - self.rowSplit, 1, RT_HALIGN_RIGHT|RT_VALIGN_TOP, text))

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
		#currently intended that all icons have the same size
		self.iconWidth = self.iconWait.size().width()
		self.iconHeight = self.iconWait.size().height()
		self.iconRecording = LoadPixmap(resolveFilename(SCOPE_ACTIVE_SKIN, "icons/timer_rec.png"))
		self.iconPrepared = LoadPixmap(resolveFilename(SCOPE_ACTIVE_SKIN, "icons/timer_prep.png"))
		self.iconDone = LoadPixmap(resolveFilename(SCOPE_ACTIVE_SKIN, "icons/timer_done.png"))
		self.iconRepeat = LoadPixmap(resolveFilename(SCOPE_ACTIVE_SKIN, "icons/timer_rep.png"))
		self.iconZapped = LoadPixmap(resolveFilename(SCOPE_ACTIVE_SKIN, "icons/timer_zap.png"))
		self.iconDisabled = LoadPixmap(resolveFilename(SCOPE_ACTIVE_SKIN, "icons/timer_off.png"))
		self.iconFailed = LoadPixmap(resolveFilename(SCOPE_ACTIVE_SKIN, "icons/timer_failed.png"))
		self.iconAutoTimer = LoadPixmap(resolveFilename(SCOPE_ACTIVE_SKIN, "icons/timer_autotimer.png"))

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
		instance.setWrapAround(True)

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
		refstr = refstr and GetWithAlternative(refstr)
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
