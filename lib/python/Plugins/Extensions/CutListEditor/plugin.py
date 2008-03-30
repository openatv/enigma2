from Plugins.Plugin import PluginDescriptor

from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Components.ServicePosition import ServicePositionGauge
from Components.ActionMap import HelpableActionMap
from Components.MultiContent import MultiContentEntryText
from Components.ServiceEventTracker import ServiceEventTracker
from Components.VideoWindow import VideoWindow
from Screens.InfoBarGenerics import InfoBarSeek, InfoBarCueSheetSupport, InfoBarServiceName
from Components.GUIComponent import GUIComponent
from enigma import eListboxPythonMultiContent, eListbox, gFont, iPlayableService, RT_HALIGN_RIGHT
from Screens.FixedMenu import FixedMenu
from Screens.HelpMenu import HelpableScreen
import bisect

def CutListEntry(where, what):
	res = [ (where, what) ]
	w = where / 90
	ms = w % 1000
	s = (w / 1000) % 60
	m = (w / 60000) % 60
	h = w / 3600000
	if what == 0:
		type = "IN"
	elif what == 1:
		type = "OUT"
	elif what == 2:
		type = "MARK"
	elif what == 3:
		type = "LAST"
	res.append(MultiContentEntryText(size=(400, 20), text = "%dh:%02dm:%02ds:%03d" % (h, m, s, ms)))
	res.append(MultiContentEntryText(pos=(400,0), size=(130, 20), text = type, flags = RT_HALIGN_RIGHT))

	return res

class CutListContextMenu(FixedMenu):
	RET_STARTCUT = 0
	RET_ENDCUT = 1
	RET_DELETECUT = 2
	RET_MARK = 3
	RET_DELETEMARK = 4
	RET_REMOVEBEFORE = 5
	RET_REMOVEAFTER = 6

	SHOW_STARTCUT = 0
	SHOW_ENDCUT = 1
	SHOW_DELETECUT = 2

	def __init__(self, session, state, nearmark):
		menu = [(_("back"), self.close)] #, (None, )]

		if state == self.SHOW_STARTCUT:
			menu.append((_("start cut here"), self.startCut))
		else:
			menu.append((_("start cut here"), ))

		if state == self.SHOW_ENDCUT:
			menu.append((_("end cut here"), self.endCut))
		else:
			menu.append((_("end cut here"), ))

		if state == self.SHOW_DELETECUT:
			menu.append((_("delete cut"), self.deleteCut))
		else:
			menu.append((_("delete cut"), ))

		menu.append((_("remove before this position"), self.removeBefore))
		menu.append((_("remove after this position"), self.removeAfter))

#		menu.append((None, ))

		if not nearmark:
			menu.append((_("insert mark here"), self.insertMark))
		else:
			menu.append((_("remove this mark"), self.removeMark))

		FixedMenu.__init__(self, session, _("Cut"), menu)
		self.skinName = "Menu"

	def startCut(self):
		self.close(self.RET_STARTCUT)

	def endCut(self):
		self.close(self.RET_ENDCUT)

	def deleteCut(self):
		self.close(self.RET_DELETECUT)

	def insertMark(self):
		self.close(self.RET_MARK)

	def removeMark(self):
		self.close(self.RET_DELETEMARK)

	def removeBefore(self):
		self.close(self.RET_REMOVEBEFORE)

	def removeAfter(self):
		self.close(self.RET_REMOVEAFTER)


class CutList(GUIComponent):
	def __init__(self, list):
		GUIComponent.__init__(self)
		self.l = eListboxPythonMultiContent()
		self.setList(list)
		self.l.setFont(0, gFont("Regular", 20))
		self.onSelectionChanged = [ ]

	def getCurrent(self):
		return self.l.getCurrentSelection()

	def getCurrentIndex(self):
		return self.l.getCurrentSelectionIndex()

	GUI_WIDGET = eListbox

	def postWidgetCreate(self, instance):
		instance.setContent(self.l)
		instance.setItemHeight(30)
		instance.selectionChanged.get().append(self.selectionChanged)

	def preWidgetRemove(self, instance):
		instance.setContent(None)
		instance.selectionChanged.get().remove(self.selectionChanged)

	def selectionChanged(self):
		for x in self.onSelectionChanged:
			x()

	def invalidateEntry(self, index):
		self.l.invalidateEntry(index)

	def setIndex(self, index, data):
		self.list[index] = data
		self.invalidateEntry(index)

	def setList(self, list):
		self.list = list
		self.l.setList(self.list)

	def setSelection(self, index):
		if self.instance is not None:
			self.instance.moveSelectionTo(index)

class CutListEditor(Screen, InfoBarSeek, InfoBarCueSheetSupport, InfoBarServiceName, HelpableScreen):
	skin = """
		<screen position="0,0" size="720,576" flags="wfNoBorder" backgroundColor="#444444">
			<eLabel position="360,0" size="360,313" backgroundColor="#ffffff" />
			<widget name="Video" position="370,10" size="340,268" backgroundColor="transparent" zPosition="1" />

			<eLabel position="50,80" size="300,24" text="Name:" font="Regular;20" foregroundColor="#cccccc" transparent="1" />

			<widget source="CurrentService" render="Label" position="50,110" size="300,60" font="Regular;22" >
				<convert type="ServiceName">Name</convert>
			</widget>

			<widget source="CurrentService" render="Label" position="370,278" size="340,25" 
				backgroundColor="#000000" foregroundColor="#ffffff" font="Regular;19" zPosition="1" >
				<convert type="ServicePosition">PositionDetailed</convert>
			</widget>

			<widget name="Timeline" position="50,500" size="620,40" backgroundColor="#000000"
				pointer="/usr/share/enigma2/position_pointer.png:3,5" foregroundColor="#ffffff" />
			<widget name="Cutlist" position="50,325" size="620,175" scrollbarMode="showOnDemand" transparent="1" />
		</screen>"""
	def __init__(self, session, service):
		self.skin = CutListEditor.skin
		Screen.__init__(self, session)
		InfoBarSeek.__init__(self, actionmap = "CutlistSeekActions")
		InfoBarCueSheetSupport.__init__(self)
		InfoBarServiceName.__init__(self)
		HelpableScreen.__init__(self)
		self.old_service = session.nav.getCurrentlyPlayingServiceReference()
		session.nav.playService(service)

		service = session.nav.getCurrentService()
		cue = service and service.cueSheet()
		if cue is not None:
			# disable cutlists. we want to freely browse around in the movie
			print "cut lists disabled!"
			cue.setCutListEnable(0)

		self.downloadCuesheet()

		self["Timeline"] = ServicePositionGauge(self.session.nav)
		self["Cutlist"] = CutList(self.getCutlist())
		self["Cutlist"].onSelectionChanged.append(self.selectionChanged)

		self["Video"] = VideoWindow(decoder = 0)

		self["actions"] = HelpableActionMap(self, "CutListEditorActions",
			{
				"setIn": (self.setIn, _("Make this mark an 'in' point")),
				"setOut": (self.setOut, _("Make this mark an 'out' point")),
				"setMark": (self.setMark, _("Make this mark just a mark")),
				"addMark": (self.__addMark, _("Add a mark")),
				"removeMark": (self.__removeMark, _("Remove a mark")),
				"leave": (self.exit, _("Exit editor")),
				"showMenu": (self.showMenu, _("menu")),
			}, prio=-4)

		self.tutorial_seen = False

		self.onExecBegin.append(self.showTutorial)
		self.__event_tracker = ServiceEventTracker(screen=self, eventmap=
			{
				iPlayableService.evCuesheetChanged: self.refillList
			})

		# to track new entries we save the last version of the cutlist
		self.last_cuts = [ ]
		self.cut_start = None

	def showTutorial(self):
		if not self.tutorial_seen:
			self.tutorial_seen = True
			self.session.open(MessageBox, 
				"""Welcome to the Cutlist editor. 

Seek to the start of the stuff you want to cut away. Press OK, select 'start cut'.

Then seek to the end, press OK, select 'end cut'. That's it.
				""", MessageBox.TYPE_INFO)

	def checkSkipShowHideLock(self):
		pass

	def setType(self, index, type):
		if len(self.cut_list):
			self.cut_list[index] = (self.cut_list[index][0], type)
			self["Cutlist"].setIndex(index, CutListEntry(*self.cut_list[index]))

	def setIn(self):
		m = self["Cutlist"].getCurrentIndex()
		self.setType(m, 0)
		self.uploadCuesheet()

	def setOut(self):
		m = self["Cutlist"].getCurrentIndex()
		self.setType(m, 1)
		self.uploadCuesheet()

	def setMark(self):
		m = self["Cutlist"].getCurrentIndex()
		self.setType(m, 2)
		self.uploadCuesheet()

	def __addMark(self):
		self.toggleMark(onlyadd=True, tolerance=90000) # do not allow two marks in <1s

	def __removeMark(self):
		m = self["Cutlist"].getCurrent()
		m = m and m[0]
		if m is not None:
			self.removeMark(m)

	def exit(self):
		self.session.nav.playService(self.old_service)
		self.close()

	def getCutlist(self):
		r = [ ]
		for e in self.cut_list:
			r.append(CutListEntry(*e))
		return r

	def selectionChanged(self):
		where = self["Cutlist"].getCurrent()
		if where is None:
			print "no selection"
			return
		pts = where[0][0]
		seek = self.getSeek()
		if seek is None:
			print "no seek"
			return
		seek.seekTo(pts)

	def refillList(self):
		print "cue sheet changed, refilling"
		self.downloadCuesheet()

		# get the first changed entry, and select it
		new_list = self.getCutlist()
		self["Cutlist"].setList(new_list)

		for i in range(min(len(new_list), len(self.last_cuts))):
			if new_list[i] != self.last_cuts[i]:
				self["Cutlist"].setSelection(i)
				break
		self.last_cuts = new_list

	def getStateForPosition(self, pos):
		state = 0 # in

		# when first point is "in", the beginning is "out"
		if len(self.cut_list) and self.cut_list[0][1] == 0:
			state = 1

		for (where, what) in self.cut_list:
			if where < pos:
				if what == 0: # in
					state = 0
				elif what == 1: # out
					state = 1
		return state

	def showMenu(self):
		curpos = self.cueGetCurrentPosition()
		if curpos is None:
			return

		self.setSeekState(self.SEEK_STATE_PAUSE)

		self.context_position = curpos

		self.context_nearest_mark = self.toggleMark(onlyreturn=True)

		cur_state = self.getStateForPosition(curpos)
		if cur_state == 0:
			print "currently in 'IN'"
			if self.cut_start is None or self.context_position < self.cut_start:
				state = CutListContextMenu.SHOW_STARTCUT
			else:
				state = CutListContextMenu.SHOW_ENDCUT
		else:
			print "currently in 'OUT'"
			state = CutListContextMenu.SHOW_DELETECUT

		if self.context_nearest_mark is None:
			nearmark = False
		else:
			nearmark = True

		self.session.openWithCallback(self.menuCallback, CutListContextMenu, state, nearmark)

	def menuCallback(self, *result):
		if not len(result):
			return
		result = result[0]

		if result == CutListContextMenu.RET_STARTCUT:
			self.cut_start = self.context_position
		elif result == CutListContextMenu.RET_ENDCUT:
			# remove in/out marks between the new cut
			for (where, what) in self.cut_list[:]:
				if self.cut_start <= where <= self.context_position and what in [0,1]:
					self.cut_list.remove((where, what))

			bisect.insort(self.cut_list, (self.cut_start, 1))
			bisect.insort(self.cut_list, (self.context_position, 0))
			self.uploadCuesheet()
			self.cut_start = None
		elif result == CutListContextMenu.RET_DELETECUT:
			out_before = None
			in_after = None

			for (where, what) in self.cut_list:
				if what == 1 and where < self.context_position: # out
					out_before = (where, what)
				elif what == 0 and where < self.context_position: # in, before out
					out_before = None
				elif what == 0 and where > self.context_position and in_after is None:
					in_after = (where, what)

			if out_before is not None:
				self.cut_list.remove(out_before)

			if in_after is not None:
				self.cut_list.remove(in_after)
			self.uploadCuesheet()
		elif result == CutListContextMenu.RET_MARK:
			self.__addMark()
		elif result == CutListContextMenu.RET_DELETEMARK:
			self.cut_list.remove(self.context_nearest_mark)
			self.uploadCuesheet()
		elif result == CutListContextMenu.RET_REMOVEBEFORE:
			# remove in/out marks before current position
			for (where, what) in self.cut_list[:]:
				if where <= self.context_position and what in [0,1]:
					self.cut_list.remove((where, what))
			# add 'in' point
			bisect.insort(self.cut_list, (self.context_position, 0))
			self.uploadCuesheet()
		elif result == CutListContextMenu.RET_REMOVEAFTER:
			# remove in/out marks after current position
			for (where, what) in self.cut_list[:]:
				if where >= self.context_position and what in [0,1]:
					self.cut_list.remove((where, what))
			# add 'out' point
			bisect.insort(self.cut_list, (self.context_position, 1))
			self.uploadCuesheet()

	# we modify the "play" behavior a bit:
	# if we press pause while being in slowmotion, we will pause (and not play)
	def playpauseService(self):
		if self.seekstate != self.SEEK_STATE_PLAY and not self.isStateSlowMotion(self.seekstate):
			self.unPauseService()
		else:
			self.pauseService()

def main(session, service, **kwargs):
	session.open(CutListEditor, service)

def Plugins(**kwargs):
 	return PluginDescriptor(name="Cutlist Editor", description=_("Cutlist editor..."), where = PluginDescriptor.WHERE_MOVIELIST, fnc=main)
