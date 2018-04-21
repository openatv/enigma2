import bisect
from time import sleep
from struct import unpack, Struct
from ctypes import CDLL, c_longlong

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
from Components.config import config, ConfigYesNo
from Screens.MovieSelection import MovieSelection

apscParser = Struct(">qq")    # big-endian, 64-bit offset and 64-bit PTS/data

config.usage.cutlisteditor_tutorial_seen = ConfigYesNo(default=False)

def SecToMSS(sec):
	return "%d:%02d" % (sec / 60, sec % 60)

def CutListEntry(where, what, where_next=None):
	w = where / 90
	ms = w % 1000
	s = (w / 1000) % 60
	m = (w / 60000) % 60
	h = w / 3600000
	type, type_col = (
		("IN",   0x004000),
		("OUT",  0x400000),
		("MARK", 0x000040),
		("LAST", 0x000000),
		("EOF",  0x000000),
		("",     0x000000)
	)[what if what < 5 else 5]

	d = SecToMSS((where_next / 90 - w) / 1000) if where_next else ""

	return (where, what), "%dh:%02dm:%02ds:%03d" % (h, m, s, ms), type, d, type_col

class CutListContextMenu(FixedMenu):
	RET_STARTCUT = 0
	RET_ENDCUT = 1
	RET_DELETECUT = 2
	RET_MARKIN = 12
	RET_MARK = 3
	RET_DELETEMARK = 4
	RET_REMOVEBEFORE = 5
	RET_REMOVEAFTER = 6
	RET_ENABLECUTS = 7
	RET_DISABLECUTS = 8
	RET_EXECUTECUTS = 9
	RET_QUICKEXECUTE = 10
	RET_GRABFRAME = 11

	SHOW_STARTCUT = 0
	SHOW_ENDCUT = 1
	SHOW_DELETECUT = 2

	def __init__(self, session, state, nearmark, cut_state):
		menu = [(_("back"), self.close)] #, (None, )]

		if state == self.SHOW_STARTCUT:
			menu.append((_("start cut here (reset)"), self.startCut))
		else:
			menu.append((_("start cut here"), self.startCut))

		if state == self.SHOW_ENDCUT:
			menu.append((_("end cut here (reset)"), self.endCut))
		else:
			menu.append((_("end cut here"), self.endCut))

		if state == self.SHOW_DELETECUT:
			menu.append((_("delete cut"), self.deleteCut))
		else:
			menu.append((_("delete cut (disabled)"), ))

		menu.append((_("remove before this position"), self.removeBefore))
		menu.append((_("remove after this position"), self.removeAfter))

		if cut_state == 2:
			menu.append((_("enable cuts (preview)"), self.enableCuts))
		else:
			menu.append((_("disable cuts (edit)"), self.disableCuts))

		menu.append((_("execute cuts and exit"), self.executeCuts))
		menu.append((_("quick execute"), self.quickExecute))

		menu.append((_("insert mark after each in"), self.markIn))

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

	def markIn(self):
		self.close(self.RET_MARKIN)

	def insertMark(self):
		self.close(self.RET_MARK)

	def removeMark(self):
		self.close(self.RET_DELETEMARK)

	def removeBefore(self):
		self.close(self.RET_REMOVEBEFORE)

	def removeAfter(self):
		self.close(self.RET_REMOVEAFTER)

	def enableCuts(self):
		self.close(self.RET_ENABLECUTS)

	def disableCuts(self):
		self.close(self.RET_DISABLECUTS)

	def executeCuts(self):
		self.close(self.RET_EXECUTECUTS)

	def quickExecute(self):
		self.close(self.RET_QUICKEXECUTE)

	def grabFrame(self):
		self.close(self.RET_GRABFRAME)

class CutListEditor(Screen, InfoBarBase, InfoBarSeek, InfoBarCueSheetSupport, HelpableScreen):
	skin = """
	<screen flags="wfNoBorder" position="0,0" size="1280,720" title="Cutlist editor">
		<panel name="FullScreenWindow" />
		<eLabel position="50,86" size="380,520" backgroundColor="grey" zPosition="1"/>
		<eLabel position="51,87" size="378,518" backgroundColor="black" zPosition="2"/>
		<widget position="60,96" size="360,450" render="Listbox" scrollbarMode="showOnDemand" source="cutlist" transparent="1" zPosition="3">
			<convert type="TemplatedMultiContent">
						{"template": [
						MultiContentEntryText(pos=(10,2), size=(160, 20), text = 1, backcolor = MultiContentTemplateColor(4)),
						MultiContentEntryText(pos=(180,2), size=(80, 20), text = 2, flags = RT_HALIGN_CENTER, backcolor = MultiContentTemplateColor(4)),
						MultiContentEntryText(pos=(270,2), size=(70, 20), text = 3, flags = RT_HALIGN_RIGHT, backcolor = MultiContentTemplateColor(4))
						],

						"fonts": [gFont("Regular", 20)],
						"itemHeight": 25
						}
					</convert>
		</widget>
		<eLabel position="240,548" size=" 80,20" text="IN" zPosition="3" halign="center" font="Regular;20" backgroundColor="#004000"/>
		<widget position="330,548" size=" 70,20" name="InLen" zPosition="3" halign="right" font="Regular;20" backgroundColor="#004000"/>
		<eLabel position="240,573" size=" 80,20" text="OUT" zPosition="3" halign="center" font="Regular;20" backgroundColor="#400000"/>
		<widget position="330,573" size=" 70,20" name="OutLen" zPosition="3" halign="right" font="Regular;20" backgroundColor="#400000"/>
		<eLabel position="462,86" size="768,432" backgroundColor="transparent2" zPosition="3"/>
		<widget position="462,86" size="768,432" name="Video" zPosition="-10"/>
		<widget position="462,528" size="768,30" backgroundColor="black" font="Regular; 18" halign="center" render="Label" source="session.CurrentService" transparent="1" valign="center" zPosition="3" foregroundColor="white">
			<convert type="ServiceName">Name</convert>
		</widget>
		<widget position="462,559" size="768,25" backgroundColor="black" font="Regular; 19" halign="center" render="Label" source="session.CurrentService" transparent="1" valign="center" zPosition="3" foregroundColor="white">
			<convert type="ServicePosition">Position,Detailed</convert>
		</widget>
		<widget position="430,584" size=" 65,25" name="SeekState" zPosition="1" halign="right" font="Regular;20" valign="center"/>
		<widget position="510,586" size="720,20" name="Timeline" backgroundColor="un808888" foregroundColor="black" pointer="position_arrow.png:3,5" zPosition="3"/>
		<panel name="FullscreenMenuButtonPanel" />
		<panel name="FullScreenColourPanel" />
		<panel name="FullscreenHelpButtonPanel" />
	</screen>"""

	BACK_BACK = 0
	BACK_RESTORE = 1
	BACK_RESTOREEXIT = 2
	BACK_REMOVEMARKS = 3
	BACK_REMOVECUTS = 4
	BACK_REMOVEALL = 5

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
		self.pauseService()

		# disable cutlists. we want to freely browse around in the movie
		# However, downloading and uploading the cue sheet restores the
		# default state, so we need to keep disabling it.
		self.cut_state = 2

		self.getCuesheet()

		# preserve the original cuts to possibly restore them later
		self.prev_cuts = self.cut_list[:]
		self.last_mark = [x for x in self.prev_cuts if x[1] == self.CUT_TYPE_LAST]
		self.edited = False
		self.MovieSelection = isinstance(self.session.current_dialog, MovieSelection) and self.session.current_dialog

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
		self["key_yellow"] = Label(_("Step back"))
		self["key_blue"]   = Label(_("Step forward"))

		self["SeekActions"].actions.update({"stepFwd": self.stepFwd})
		self.helpList.append((self["SeekActions"], "CutlistSeekActions", [("stepFwd", _("Step forward"))]))

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
				"execute": (self.execute, _("Execute cuts and exit")),
				"quickExecute": (self.quickExecute, _("Quick execute...")),
				"leave": (self.exit, _("Exit editor")),
				"showMenu": (self.showMenu, _("Menu")),
				"backMenu": (self.backMenu, _("Restore previous cuts...")),
			}, prio=-4)

		self.onExecBegin.append(self.showTutorial)
		self.__event_tracker = ServiceEventTracker(screen=self, eventmap=
			{
				iPlayableService.evCuesheetChanged: self.refillList
			})

		# to track new entries we save the last version of the cutlist
		self.last_cuts = self.getCutlist()
		self.cut_start = None
		self.cut_end = None
		self.state = CutListContextMenu.SHOW_DELETECUT
		self.inhibit_seek = False
		self.inhibit_cut = False
		self.onClose.append(self.__onClose)
		# Use onShown to set the initial list index, since apparently that doesn't
		# work from here.
		self.onShown.append(self.__onShown)

	def __onShown(self, override=False):
		if self.already_shown and not override:
			return
		if self.cut_list:
			cl = self["cutlist"]
			# If there's only marks, jump to the first (assuming a new recording).
			if not [x for x in self.cut_list if x[1] != self.CUT_TYPE_MARK]:
				# Assume the start mark has been missed if it's not less than
				# 16 minutes.
				if self.cut_list[0][0] < 16*60*90000:
					cl.index = 1
			else:
				# Playback will start at the initial IN cut, so point the list
				# there, too.
				if cl.list[0][0][1] == self.CUT_TYPE_OUT:
					cl.index = 1

	def __onClose(self):
		if self.MovieSelection:
			if self.last_mark and not [x for x in self.cut_list if x[1] == self.CUT_TYPE_LAST]:
				service = self.session.nav.getCurrentlyPlayingServiceReference()
				from Screens.InfoBarGenerics import delResumePoint
				delResumePoint(service)
				self.MovieSelection["list"].invalidateCurrentItem()
			if self.edited:
				self.MovieSelection.diskinfo.update()
		self.session.nav.playService(self.old_service, forceRestart=True)

	def updateStateLabel(self, state):
		self["SeekState"].setText(state[3].strip())

	def showTutorial(self):
		if not config.usage.cutlisteditor_tutorial_seen.value:
			config.usage.cutlisteditor_tutorial_seen.value = True
			config.usage.cutlisteditor_tutorial_seen.save()
			self.session.open(MessageBox,_("Welcome to the cutlist editor.\n\nSeek to the start of the stuff you want to cut away, press RED.\n\nThen seek to the end, press GREEN. That's it."), MessageBox.TYPE_INFO)

	def checkSkipShowHideLock(self):
		pass

	def setCutListEnable(self):
		service = self.session.nav.getCurrentService()
		cue = service and service.cueSheet()
		if cue is not None:
			cue.setCutListEnable(self.cut_state)

	def getCuesheet(self):
		self.downloadCuesheet()
		self.setCutListEnable()

	def putCuesheet(self):
		self.uploadCuesheet()
		self.setCutListEnable()

	def setType(self, index, type):
		if len(self.cut_list):
			self.cut_list[index] = (self.cut_list[index][0], type)
			self["cutlist"].modifyEntry(index, CutListEntry(*self.cut_list[index]))

	def setOut(self):
		if self.inhibit_cut:
			self.inhibit_cut = False
			return
		self.setSeekState(self.SEEK_STATE_PAUSE)
		self.context_position = self.cueGetCurrentPosition()
		self.menuCallback(CutListContextMenu.RET_STARTCUT)

	def setIn(self):
		if self.inhibit_cut:
			self.inhibit_cut = False
			return
		self.setSeekState(self.SEEK_STATE_PAUSE)
		self.context_position = self.cueGetCurrentPosition()
		self.menuCallback(CutListContextMenu.RET_ENDCUT)

	def setStart(self):
		self.setSeekState(self.SEEK_STATE_PAUSE)
		self.context_position = self.cueGetCurrentPosition()
		self.menuCallback(CutListContextMenu.RET_REMOVEBEFORE)
		self.inhibit_cut = True

	def setEnd(self):
		self.setSeekState(self.SEEK_STATE_PAUSE)
		self.context_position = self.cueGetCurrentPosition()
		self.menuCallback(CutListContextMenu.RET_REMOVEAFTER)
		self.inhibit_cut = True

	def quickExecute(self):
		self.setSeekState(self.SEEK_STATE_PAUSE)
		self.context_position = self.cueGetCurrentPosition()
		self.menuCallback(CutListContextMenu.RET_QUICKEXECUTE)

	def execute(self):
		self.setSeekState(self.SEEK_STATE_PAUSE)
		self.context_position = self.cueGetCurrentPosition()
		self.menuCallback(CutListContextMenu.RET_EXECUTECUTS)

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
		first_cut = None
		for pts, type in self.cut_list:
			if last_type != type in (self.CUT_TYPE_IN, self.CUT_TYPE_OUT):
				if type == self.CUT_TYPE_IN:
					out_len += pts - last_pts
				else:
					in_len += pts - last_pts
				last_pts, last_type = pts, type
				if first_cut is None:
					first_cut = (self.CUT_TYPE_OUT, self.CUT_TYPE_IN)[type]
		if length:
			if last_type == self.CUT_TYPE_OUT:
				out_len += length - last_pts
			else:
				in_len += length - last_pts
		self["InLen"].setText(SecToMSS(in_len / 90000))
		self["OutLen"].setText(SecToMSS(out_len / 90000))

		if first_cut is None:
			first_cut = self.CUT_TYPE_IN
		cl = self.cut_list
		if cl and cl[0][1] == self.CUT_TYPE_LAST and cl[0][0] <= 1: # remove state indicator marks
			cl = cl[1:]
		r = [CutListEntry(0, first_cut, cl[0][0] if cl else length)]
		for i, e in enumerate(cl):
			if i == len(cl) - 1:
				n = length
			else:
				n = cl[i+1][0]
			r.append(CutListEntry(*e, where_next=n))
		if length:
			r.append(CutListEntry(length, 4))
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
			# EOF may not be seekable, so go back a bit (2 seems sufficient) and then
			# forward to the next access point (which will flicker if EOF is
			# seekable, but better than waiting for a timeout when it's not).
			if where[0][1] == 4:
				curpos = seek.getPlayPosition()
				seek.seekTo(pts-2)
				i = 0
				while i < 15:
					i += 1
					sleep(0.01)
					if seek.getPlayPosition() != curpos:
						seek.seekRelative(1, 1)
						break
			else:
				seek.seekTo(pts)

	def refillList(self):
		print "cue sheet changed, refilling"
		self.getCuesheet()

		# select the first changed entry from the end (not counting EOF)
		new_list = self.getCutlist()
		self["cutlist"].list = new_list

		l1 = len(new_list) - 1
		l2 = len(self.last_cuts) - 1
		if new_list[l1][0][1] != 4: l1 += 1
		if self.last_cuts[l2][0][1] != 4: l2 += 1
		for i in range(min(l1, l2)):
			if new_list[l1-i-1][0] != self.last_cuts[l2-i-1][0]:
				self["cutlist"].setIndex(l1-i-1)
				break
		self.last_cuts = new_list

	def showMenu(self):
		curpos = self.cueGetCurrentPosition()
		if curpos is None:
			return
		self.setSeekState(self.SEEK_STATE_PAUSE)
		self.context_position = curpos

		self.context_nearest_mark = self.toggleMark(onlyreturn=True)
		if self.context_nearest_mark is None:
			nearmark = False
		else:
			nearmark = True

		self.session.openWithCallback(self.menuCallback, CutListContextMenu, self.state, nearmark, self.cut_state)

	def menuCallback(self, *result):
		if not len(result):
			return
		result = result[0]

		if result in (CutListContextMenu.RET_STARTCUT, CutListContextMenu.RET_ENDCUT):
			if result == CutListContextMenu.RET_STARTCUT:
				self.cut_start = self.context_position
				self.state = CutListContextMenu.SHOW_STARTCUT
				if self.cut_end is None:
					return
				if self.cut_start >= self.cut_end:
					self.cut_end = None
					return
			else: # CutListContextMenu.RET_ENDCUT
				self.cut_end = self.context_position
				self.state = CutListContextMenu.SHOW_ENDCUT
				if self.cut_start is None:
					return
				if self.cut_end <= self.cut_start:
					self.cut_start = None
					return
			# remove marks between the new cut
			for (where, what) in self.cut_list[:]:
				if self.cut_start <= where <= self.cut_end:
					self.cut_list.remove((where, what))

			bisect.insort(self.cut_list, (self.cut_start, 1))
			bisect.insort(self.cut_list, (self.cut_end, 0))
			self.putCuesheet()
			self.cut_start = self.cut_end = None
			self.state = CutListContextMenu.SHOW_DELETECUT
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
		elif result == CutListContextMenu.RET_MARKIN:
			added = 1
			first = True
			for (i, (where, what)) in enumerate(self.cut_list[:]):
				if what == self.CUT_TYPE_IN:
					if not first:
						self.cut_list.insert(i+added, (where, self.CUT_TYPE_MARK))
						added += 1
					first = False
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
		elif result == CutListContextMenu.RET_QUICKEXECUTE:
			menu = [(_("cancel"), 0),
					(_("end at this position"), 1),
					(_("punch cuts"), 2),
					(_("both"), 3)]
			self.session.openWithCallback(self.quickCallback, ChoiceBox, title=_("How would you like to modify the movie?\nWarning: This operation cannot be undone!"), list=menu)
		elif result == CutListContextMenu.RET_ENABLECUTS:
			self.cut_state = 3
			self.setCutListEnable()
		elif result == CutListContextMenu.RET_DISABLECUTS:
			self.cut_state = 2
			self.setCutListEnable()
		elif result == CutListContextMenu.RET_EXECUTECUTS:
			try:
				from Plugins.Extensions.MovieCut.plugin import main
				service = self.session.nav.getCurrentlyPlayingServiceReference()
				self.session.nav.stopService()	# need to stop to save the cuts file
				main(self.session, service)
				self.close()
			except ImportError:
				self.session.open(MessageBox, _("The MovieCut plugin is not installed."), type=MessageBox.TYPE_INFO, timeout=10)
		elif result == CutListContextMenu.RET_GRABFRAME:
			self.grabFrame()

	def quickCallback(self, answer):
		answer = answer and answer[1]
		if not answer:
			return
		truncpts = None
		if answer & 1:
			truncpts = self.context_position
		elif self.cut_list[-1][1] == self.CUT_TYPE_OUT:
			truncpts = self.cut_list[-1][0]
		if truncpts:
			# remove marks from the truncate position
			for (where, what) in self.cut_list[:]:
				if where >= truncpts:
					self.cut_list.remove((where, what))
			self.inhibit_seek = True
			self.putCuesheet()
			self.inhibit_seek = False
			self.prev_cuts = self.cut_list[:]
			self.last_cuts = self.getCutlist()
		service = self.session.nav.getCurrentlyPlayingServiceReference()
		self.session.nav.stopService()
		movie = service.getPath()
		if self.loadAP(movie):
			if truncpts:
				self.trunc(movie, truncpts)
			if answer & 2:
				self.punch(movie)
			self.edited = True
		self.session.nav.playService(service)
		self.pauseService()
		self.setCutListEnable()
		self.__onShown(override=True)

	def backMenu(self):
		menu = [(_("back"), self.BACK_BACK),
				(_("restore previous cuts"), self.BACK_RESTORE),
				(_("restore previous cuts & exit"), self.BACK_RESTOREEXIT),
				(_("remove marks (preserve cuts)"), self.BACK_REMOVEMARKS),
				(_("remove cuts (preserve marks)"), self.BACK_REMOVECUTS),
				(_("remove all"), self.BACK_REMOVEALL)]
		self.session.openWithCallback(self.backCallback, ChoiceBox, title=_("Restore cuts"), list=menu)

	def backCallback(self, result):
		if result and result[1]:
			if result[1] == self.BACK_REMOVEALL:
				self.cut_list = []
			elif result[1] == self.BACK_REMOVEMARKS:
				self.cut_list = [x for x in self.cut_list if x[1] != self.CUT_TYPE_MARK]
			elif result[1] == self.BACK_REMOVECUTS:
				self.cut_list = [x for x in self.cut_list if x[1] not in (self.CUT_TYPE_IN, self.CUT_TYPE_OUT)]
			else:
				self.cut_list = self.prev_cuts
			self.inhibit_seek = True
			self.putCuesheet()
			self.inhibit_seek = False
			if result[1] == self.BACK_RESTOREEXIT:
				self.close()

	def stepFwd(self):
		self.doSeekRelative(1)

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

	def trunc(self, movie, pts):
		i = self.getAP(pts)
		if i < len(self.ap):
			i += 1
		offset = self.ap[i][1]
		with open(movie, "r+b") as f:
			f.truncate(offset)

		def truncapsc(suffix):
			with open(movie + suffix, "r+b") as f:
				while True:
					data = f.read(8192 * apscParser.size)
					if len(data) < apscParser.size:
						break
					ofs = apscParser.unpack_from(data, len(data) - apscParser.size)[0]
					if ofs >= offset:
						apsc = unpack(">%dq" % (len(data) / 8), data)
						for i, ofs in enumerate(apsc[::2]):
							if ofs >= offset:
								f.truncate(f.tell() - len(data) + i * apscParser.size)
								return

		truncapsc(".ap")
		truncapsc(".sc")

	def punch(self, movie):
		outpts = [x[0] for x in self.cut_list if x[1] == self.CUT_TYPE_OUT]
		inpts  = [x[0] for x in self.cut_list if x[1] == self.CUT_TYPE_IN]
		if not outpts and not inpts:
			return
		if not outpts or inpts[0] < outpts[0]:
			outpts.insert(0, 0)
		# Final out was removed before being called.
		try:
			so = CDLL("libext2fs.so.2")
			fallocate64 = so.fallocate64
		except:
			return
		with open(movie, "r+b") as f:
			fd = f.fileno()
			last = len(self.ap) - 1
			for c in range(0, len(outpts)):
				o = self.getAP(outpts[c]) + 2
				if o > last:
					o = last
				i = self.getAP(inpts[c]) - 1
				if i < 0:
					i = 0
				# FALLOC_FL_PUNCH_HOLE | FALLOC_FL_KEEP_SIZE
				fallocate64(fd, 3, c_longlong(self.ap[o][1]), c_longlong(self.ap[i][1] - self.ap[o][1]))

	# Return the index of the access point at or after PTS.
	def getAP(self, pts):
		i = bisect.bisect_left(self.ap, (pts, 0))
		return i if i < len(self.ap) else i - 1

	def loadAP(self, movie):
		self.ap = []
		try:
			with open(movie + ".ap", "rb") as f:
				data = f.read()
		except:
			return False
		if len(data) < 2 * apscParser.size:
			return False

		data = unpack(">%dq" % (len(data) / 8), data)

		ofs1, currentDelta = data[0], data[1]
		if ofs1 != 0:
			ofs2, pts2 = data[2], data[3]
			if ofs1 < ofs2:
				diff = ofs2 - ofs1
				tdiff = pts2 - currentDelta
				tdiff *= ofs1
				tdiff /= diff
				currentDelta -= tdiff
		lastpts = -1
		append = self.ap.append
		for i in zip(data[0::2], data[1::2]):
			current = i[1] - currentDelta
			diff = current - lastpts
			if diff <= 0 or diff > 90000*10:
				currentDelta = i[1] - lastpts - 90000/25
			lastpts = i[1] - currentDelta
			append((lastpts, i[0]))

		return True
