import bisect

from enigma import getDesktop, iPlayableService

from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Screens.ChoiceBox import ChoiceBox
from Components.ServicePosition import ServicePositionGauge
from Components.ActionMap import HelpableActionMap
from Components.ServiceEventTracker import ServiceEventTracker, InfoBarBase
from Components.VideoWindow import VideoWindow
from Components.Label import Label
from Screens.InfoBarGenerics import InfoBarSeek, InfoBarCueSheetSupport
from Screens.FixedMenu import FixedMenu
from Screens.HelpMenu import HelpableScreen
from Components.Sources.List import List


def SecToMSS(sec):
	return "%d:%02d" % (sec / 60, sec % 60)

def CutListEntry(where, what, where_next=None):
	w = where / 90
	ms = w % 1000
	s = (w / 1000) % 60
	m = (w / 60000) % 60
	h = w / 3600000
	if what == 0:
		type = "IN"
		type_col = 0x004000
	elif what == 1:
		type = "OUT"
		type_col = 0x400000
	elif what == 2:
		type = "MARK"
		type_col = 0x000040
	elif what == 3:
		type = "LAST"
		type_col = 0x000000

	d = SecToMSS((where_next / 90 - w) / 1000) if where_next else ""

	return (where, what), "%dh:%02dm:%02ds:%03d" % (h, m, s, ms), type, d, type_col

class CutListContextMenu(FixedMenu):
	RET_STARTCUT = 0
	RET_ENDCUT = 1
	RET_DELETECUT = 2
	RET_MARK = 3
	RET_DELETEMARK = 4
	RET_REMOVEBEFORE = 5
	RET_REMOVEAFTER = 6
	RET_GRABFRAME = 7
	RET_ENABLECUTS = 8
	RET_DISABLECUTS = 9
	RET_EXECUTECUTS = 10

	SHOW_STARTCUT = 0
	SHOW_ENDCUT = 1
	SHOW_DELETECUT = 2

	def __init__(self, session, state, nearmark, cut_state):
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

		if cut_state == 2:
			menu.append((_("enable cuts"), self.enableCuts))
		else:
			menu.append((_("disable cuts"), self.disableCuts))

		menu.append((_("execute cuts"), self.executeCuts))

#		menu.append((None, ))

		if not nearmark:
			menu.append((_("insert mark here"), self.insertMark))
		else:
			menu.append((_("remove this mark"), self.removeMark))

		menu.append((_("grab this frame as bitmap"), self.grabFrame))
		FixedMenu.__init__(self, session, _("Cut"), menu)
		self.skinName = "CutListMenu"

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

	def enableCuts(self):
		return self.close(self.RET_ENABLECUTS)

	def disableCuts(self):
		return self.close(self.RET_DISABLECUTS)

	def executeCuts(self):
		return self.close(self.RET_EXECUTECUTS)

	def grabFrame(self):
		self.close(self.RET_GRABFRAME)

class CutListEditor(Screen, InfoBarBase, InfoBarSeek, InfoBarCueSheetSupport, HelpableScreen):
	skin = """
	<screen position="0,0" size="720,576" flags="wfNoBorder">
		<eLabel text="Cutlist editor" position="65,60" size="300,25" font="Regular;20" />
		<widget source="global.CurrentTime" render="Label" position="268,60" size="394,20" font="Regular;20" halign="right">
			<convert type="ClockToText">Format:%A %B %d, %H:%M</convert>
		</widget>
		<eLabel position="268,98" size="394,304" backgroundColor="#505555" />
		<widget name="Video" position="270,100" zPosition="1" size="390,300" backgroundColor="transparent" />
		<widget source="session.CurrentService" render="Label" position="135,405" size="450,50" font="Regular;22" halign="center" valign="center">
			<convert type="ServiceName">Name</convert>
		</widget>
		<widget source="session.CurrentService" render="Label" position="320,450" zPosition="1" size="420,25" font="Regular;20" halign="left" valign="center">
			<convert type="ServicePosition">Position,Detailed</convert>
		</widget>
		<widget name="SeekState" position="210,450" zPosition="1" size="100,25" halign="right" font="Regular;20" valign="center" />
		<eLabel position="48,98" size="204,274" backgroundColor="#505555" />
		<eLabel position="50,100" size="200,270" backgroundColor="#000000" />
		<widget source="cutlist" position="50,100" zPosition="1" size="200,270" scrollbarMode="showOnDemand" transparent="1" render="Listbox" >
			<convert type="TemplatedMultiContent">
				{"template": [
						MultiContentEntryText(size=(125, 20), text = 1, backcolor = MultiContentTemplateColor(3)),
						MultiContentEntryText(pos=(125,0), size=(50, 20), text = 2, flags = RT_HALIGN_RIGHT, backcolor = MultiContentTemplateColor(3))
					],
				 "fonts": [gFont("Regular", 18)],
				 "itemHeight": 20
				}
			</convert>
		</widget>
		<widget name="Timeline" position="50,485" size="615,20" backgroundColor="#505555" pointer="position_arrow.png:3,5" foregroundColor="black" />
		<ePixmap pixmap="icons/mp_buttons.png" position="305,515" size="109,13" alphatest="on" />
	</screen>"""

	BACK_BACK = 0
	BACK_RESTORE = 1
	BACK_RESTOREEXIT = 2
	BACK_REMOVE = 3

	tutorial_seen = False

	def __init__(self, session, service):
		self.skin = CutListEditor.skin
		Screen.__init__(self, session)
		Screen.setTitle(self, _("Cutlist editor"))
		InfoBarSeek.__init__(self, actionmap = "CutlistSeekActions")
		InfoBarCueSheetSupport.__init__(self)
		InfoBarBase.__init__(self, steal_current_service = True)
		HelpableScreen.__init__(self)
		self.old_service = session.nav.getCurrentlyPlayingServiceReference()
		session.nav.playService(service)

		# disable cutlists. we want to freely browse around in the movie
		# However, downloading and uploading the cue sheet restores the
		# default state, so we need to keep disabling it.
		service = session.nav.getCurrentService()
		self.cue = service and service.cueSheet()
		self.cut_state = 2

		self.getCuesheet()

		# preserve the original cuts to possibly restore them later
		self.prev_cuts = self.cut_list[:]

		self["InLen"] = Label()
		self["OutLen"] = Label()
		self["Timeline"] = ServicePositionGauge(self.session.nav)
		self["cutlist"] = List(self.getCutlist())
		self["cutlist"].onSelectionChanged.append(self.selectionChanged)
		self["SeekState"] = Label()
		self.onPlayStateChanged.append(self.updateStateLabel)
		self.updateStateLabel(self.seekstate)

		self["key_red"]    = Label(_("Start cut"))
		self["key_green"]  = Label(_("End cut"))
		self["key_yellow"] = Label(_("Backward"))
		self["key_blue"]   = Label(_("Forward"))

		desktopSize = getDesktop(0).size()
		self["Video"] = VideoWindow(decoder = 0, fb_width=desktopSize.width(), fb_height=desktopSize.height())

		self["actions"] = HelpableActionMap(self, "CutListEditorActions",
			{
				"setIn": (self.setIn, _("Make this mark an 'in' point")),
				"setOut": (self.setOut, _("Make this mark an 'out' point")),
				"setStart": (self.setStart, _("Make this mark the initial 'in' point")),
				"setEnd": (self.setEnd, _("Make this mark the final 'out' point")),
				"setMark": (self.setMark, _("Make this mark just a mark")),
				"addMark": (self.__addMark, _("Add a mark")),
				"removeMark": (self.__removeMark, _("Remove a mark")),
				"leave": (self.exit, _("Exit editor")),
				"showMenu": (self.showMenu, _("Menu")),
				"backMenu": (self.backMenu, _("Restore previous cuts")),
			}, prio=-4)

		self.onExecBegin.append(self.showTutorial)
		self.__event_tracker = ServiceEventTracker(screen=self, eventmap=
			{
				iPlayableService.evCuesheetChanged: self.refillList
			})

		# to track new entries we save the last version of the cutlist
		self.last_cuts = self.getCutlist()
		self.cut_start = None
		self.inhibit_seek = False
		self.onClose.append(self.__onClose)

	def __onClose(self):
		self.session.nav.playService(self.old_service, forceRestart=True)

	def updateStateLabel(self, state):
		self["SeekState"].setText(state[3].strip())

	def showTutorial(self):
		if not CutListEditor.tutorial_seen:
			CutListEditor.tutorial_seen = True
			self.session.open(MessageBox,_("Welcome to the cutlist editor.\n\nSeek to the start of the stuff you want to cut away. Press OK, select 'start cut'.\n\nThen seek to the end, press OK, select 'end cut'. That's it."), MessageBox.TYPE_INFO)

	def checkSkipShowHideLock(self):
		pass

	def getCuesheet(self):
		self.downloadCuesheet()
		if self.cue is not None:
			self.cue.setCutListEnable(self.cut_state)

	def putCuesheet(self):
		self.uploadCuesheet()
		if self.cue is not None:
			self.cue.setCutListEnable(self.cut_state)

	def setType(self, index, type):
		if len(self.cut_list):
			self.cut_list[index] = (self.cut_list[index][0], type)
			self["cutlist"].modifyEntry(index, CutListEntry(*self.cut_list[index]))

	def setOut(self):
		self.setSeekState(self.SEEK_STATE_PAUSE)
		#self.context_position = self.cueGetCurrentPosition()
		#self.menuCallback(CutListContextMenu.RET_STARTCUT)
		self.cut_start = self.cueGetCurrentPosition()

	def setIn(self):
		self.setSeekState(self.SEEK_STATE_PAUSE)
		self.context_position = self.cueGetCurrentPosition()
		if self.cut_start is None or self.cut_start >= self.context_position:
			return
		self.menuCallback(CutListContextMenu.RET_ENDCUT)

	def setStart(self):
		self.setSeekState(self.SEEK_STATE_PAUSE)
		self.context_position = self.cueGetCurrentPosition()
		self.menuCallback(CutListContextMenu.RET_REMOVEBEFORE)

	def setEnd(self):
		self.setSeekState(self.SEEK_STATE_PAUSE)
		self.context_position = self.cueGetCurrentPosition()
		self.menuCallback(CutListContextMenu.RET_REMOVEAFTER)

	def setMark(self):
		m = self["cutlist"].getIndex()
		self.setType(m, 2)
		self.putCuesheet()

	def __addMark(self):
		self.toggleMark(onlyadd=True, tolerance=90000) # do not allow two marks in <1s

	def __removeMark(self):
		m = self["cutlist"].getCurrent()
		m = m and m[0]
		if m is not None:
			self.removeMark(m)

	def exit(self):
		self.close()

	def getCutlist(self):
		length = self.getSeek() and self.getSeek().getLength()
		length = not length[0] and length[1] or 0

		in_len = out_len = 0
		last_pts, last_type = 0, self.CUT_TYPE_LAST
		for pts, type in self.cut_list:
			if last_type != type in (self.CUT_TYPE_IN, self.CUT_TYPE_OUT):
				if type == self.CUT_TYPE_IN:
					out_len += pts - last_pts
				else:
					in_len += pts - last_pts
				last_pts, last_type = pts, type
		if length:
			if last_type == self.CUT_TYPE_OUT:
				out_len += length - last_pts
			else:
				in_len += length - last_pts
		self["InLen"].setText(SecToMSS(in_len / 90000))
		self["OutLen"].setText(SecToMSS(out_len / 90000))

		r = [ ]
		for i, e in enumerate(self.cut_list):
			if i == len(self.cut_list) - 1:
				n = length
			else:
				n = self.cut_list[i+1][0]
			r.append(CutListEntry(*e, where_next=n))
		return r

	def selectionChanged(self):
		if not self.inhibit_seek:
			where = self["cutlist"].getCurrent()
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
		self.getCuesheet()

		# get the first changed entry, counted from the end, and select it
		new_list = self.getCutlist()
		self["cutlist"].list = new_list

		l1 = len(new_list)
		l2 = len(self.last_cuts)
		for i in range(min(l1, l2)):
			if new_list[l1-i-1] != self.last_cuts[l2-i-1]:
				self["cutlist"].setIndex(l1-i-1)
				break
		self.last_cuts = new_list

	def getStateForPosition(self, pos):
		state = -1
		for (where, what) in self.cut_list:
			if what in [0, 1]:
				if where < pos:
					state = what
				elif where == pos:
					state = 1
				elif state == -1:
					state = 1 - what
		if state == -1:
			state = 0
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

		self.session.openWithCallback(self.menuCallback, CutListContextMenu, state, nearmark, self.cut_state)

	def menuCallback(self, *result):
		if not len(result):
			return
		result = result[0]

		if result == CutListContextMenu.RET_STARTCUT:
			self.cut_start = self.context_position
		elif result == CutListContextMenu.RET_ENDCUT:
			# remove marks between the new cut
			for (where, what) in self.cut_list[:]:
				if self.cut_start <= where <= self.context_position:
					self.cut_list.remove((where, what))

			bisect.insort(self.cut_list, (self.cut_start, 1))
			bisect.insort(self.cut_list, (self.context_position, 0))
			self.putCuesheet()
			self.cut_start = None
		elif result == CutListContextMenu.RET_DELETECUT:
			out_before = None
			in_after = None

			for (where, what) in self.cut_list:
				if what == 1 and where <= self.context_position: # out
					out_before = (where, what)
				elif what == 0 and where < self.context_position: # in, before out
					out_before = None
				elif what == 0 and where >= self.context_position and in_after is None:
					in_after = (where, what)

			if out_before is not None:
				self.cut_list.remove(out_before)

			if in_after is not None:
				self.cut_list.remove(in_after)
			self.inhibit_seek = True
			self.putCuesheet()
			self.inhibit_seek = False
		elif result == CutListContextMenu.RET_MARK:
			self.__addMark()
		elif result == CutListContextMenu.RET_DELETEMARK:
			self.cut_list.remove(self.context_nearest_mark)
			self.inhibit_seek = True
			self.putCuesheet()
			self.inhibit_seek = False
		elif result == CutListContextMenu.RET_REMOVEBEFORE:
			# remove marks before current position
			for (where, what) in self.cut_list[:]:
				if where <= self.context_position:
					self.cut_list.remove((where, what))
			# add 'in' point
			bisect.insort(self.cut_list, (self.context_position, 0))
			self.inhibit_seek = True
			self.putCuesheet()
			self.inhibit_seek = False
		elif result == CutListContextMenu.RET_REMOVEAFTER:
			# remove marks after current position
			for (where, what) in self.cut_list[:]:
				if where >= self.context_position:
					self.cut_list.remove((where, what))
			# add 'out' point
			bisect.insort(self.cut_list, (self.context_position, 1))
			self.inhibit_seek = True
			self.putCuesheet()
			self.inhibit_seek = False
		elif result == CutListContextMenu.RET_ENABLECUTS:
			self.cut_state = 3
			if self.cue is not None:
				self.cue.setCutListEnable(self.cut_state)
		elif result == CutListContextMenu.RET_DISABLECUTS:
			self.cut_state = 2
			if self.cue is not None:
				self.cue.setCutListEnable(self.cut_state)
		elif result == CutListContextMenu.RET_EXECUTECUTS:
			try:
				from Plugins.Extensions.MovieCut.plugin import main
				service = self.session.nav.getCurrentlyPlayingServiceReference()
				self.session.nav.stopService()	# need to stop to save the cuts file
				main(self.session, service)
				self.close()
			except ImportError:
				self.session.open(Message, _("The MovieCut plugin is not installed."), type=MessageBox.TYPE_INFO, timeout=10)
		elif result == CutListContextMenu.RET_GRABFRAME:
			self.grabFrame()

	def backMenu(self):
		menu = [(_("back"), self.BACK_BACK),
				(_("restore previous cuts"), self.BACK_RESTORE),
				(_("restore previous cuts & exit"), self.BACK_RESTOREEXIT),
				(_("remove all cuts"), self.BACK_REMOVE)]
		self.session.openWithCallback(self.backCallback, ChoiceBox, title="Restore cuts", list=menu)

	def backCallback(self, result):
		if result and result[1]:
			self.cut_list = self.prev_cuts if result[1] != self.BACK_REMOVE else []
			self.inhibit_seek = True
			self.putCuesheet()
			self.inhibit_seek = False
			if result[1] == self.BACK_RESTOREEXIT:
				self.close()

	# we modify the "play" behavior a bit:
	# if we press pause while being in slowmotion, we will pause (and not play)
	def playpauseService(self):
		if self.seekstate != self.SEEK_STATE_PLAY and not self.isStateSlowMotion(self.seekstate):
			self.unPauseService()
		else:
			self.pauseService()

	def grabFrame(self):
		path = self.session.nav.getCurrentlyPlayingServiceReference().getPath()
		from Components.Console import Console
		grabConsole = Console()
		cmd = 'grab -vblpr%d "%s"' % (180, path.rsplit('.',1)[0] + ".png")
		grabConsole.ePopen(cmd)
		self.playpauseService()
