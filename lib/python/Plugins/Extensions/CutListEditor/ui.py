from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Components.ServicePosition import ServicePositionGauge
from Components.ActionMap import HelpableActionMap
from Components.MultiContent import MultiContentEntryText
from Components.ServiceEventTracker import ServiceEventTracker, InfoBarBase
from Components.VideoWindow import VideoWindow
from Components.Label import Label
from Components.config import config, ConfigSubsection, ConfigYesNo
from Screens.InfoBarGenerics import InfoBarSeek, InfoBarCueSheetSupport
from Components.GUIComponent import GUIComponent
from enigma import eListboxPythonMultiContent, eListbox, getDesktop, gFont, iPlayableService, RT_HALIGN_RIGHT
from Screens.FixedMenu import FixedMenu
from Screens.HelpMenu import HelpableScreen
from ServiceReference import ServiceReference
from Components.Sources.List import List

import bisect

try:
	from Plugins.Extensions.MovieCut.plugin import main as MovieCut
except:
	MovieCut = None

config.plugins.CutListEditor = ConfigSubsection()
config.plugins.CutListEditor.showIntro = ConfigYesNo(default=True)

def CutListEntry(where, what):
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
	return ((where, what), "%dh:%02dm:%02ds:%03d" % (h, m, s, ms), type, type_col)

class CutListContextMenu(FixedMenu):
	RET_STARTCUT = 0
	RET_ENDCUT = 1
	RET_DELETECUT = 2
	RET_MARK = 3
	RET_DELETEMARK = 4
	RET_REMOVEBEFORE = 5
	RET_REMOVEAFTER = 6
	RET_GRABFRAME = 7
	RET_TOGGLEINTRO = 8
	RET_MOVIECUT = 9

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

		menu.append((_("grab this frame as bitmap"), self.grabFrame))

		if config.plugins.CutListEditor.showIntro.value:
			menu.append((_("disable intro screen"), self.toggleIntro))
		else:
			menu.append((_("enable intro screen"), self.toggleIntro))

		if MovieCut:
			menu.append((_("execute cuts (requires MovieCut plugin)"), self.callMovieCut))

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

	def grabFrame(self):
		self.close(self.RET_GRABFRAME)

	def toggleIntro(self):
		self.close(self.RET_TOGGLEINTRO)

	def callMovieCut(self):
		self.close(self.RET_MOVIECUT)

class CutListEditor(Screen, InfoBarBase, InfoBarSeek, InfoBarCueSheetSupport, HelpableScreen):
	skin = """
	<screen position="0,0" size="720,576" title="Cutlist editor" flags="wfNoBorder">
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
		<widget name="Timeline" position="50,485" size="615,20" backgroundColor="#505555" pointer="skin_default/position_arrow.png:3,5" foregroundColor="black" />
		<ePixmap pixmap="skin_default/icons/mp_buttons.png" position="305,515" size="109,13" alphatest="on" />
	</screen>"""

	tutorial_seen = False

	def __init__(self, session, service):
		self.skin = CutListEditor.skin
		Screen.__init__(self, session)
		self.setTitle(_("Cutlist editor"))
		InfoBarSeek.__init__(self, actionmap = "CutlistSeekActions")
		InfoBarCueSheetSupport.__init__(self)
		InfoBarBase.__init__(self, steal_current_service = True)
		HelpableScreen.__init__(self)
		self.old_service = session.nav.getCurrentlyPlayingServiceOrGroup()
		self.cut_service = service
		session.nav.playService(service, adjust=False)

		service = session.nav.getCurrentService()
		cue = service and service.cueSheet()
		if cue is not None:
			# disable cutlists. we want to freely browse around in the movie
			print "cut lists disabled!"
			cue.setCutListEnable(0)

		self.downloadCuesheet()

		self["Timeline"] = ServicePositionGauge(self.session.nav)
		self["cutlist"] = List(self.getCutlist())
		self["cutlist"].onSelectionChanged.append(self.selectionChanged)
		self["SeekState"] = Label()
		self.onPlayStateChanged.append(self.updateStateLabel)
		self.updateStateLabel(self.seekstate)

		desktopSize = getDesktop(0).size()
		self["Video"] = VideoWindow(decoder = 0, fb_width=desktopSize.width(), fb_height=desktopSize.height())

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
		need_restart = self.old_service and self.session.nav.getCurrentlyPlayingServiceOrGroup() and self.old_service != self.session.nav.getCurrentlyPlayingServiceOrGroup() 
		self.session.nav.playService(self.old_service, forceRestart=need_restart, adjust=False)

	def updateStateLabel(self, state):
		self["SeekState"].setText(state[3].strip())

	def showTutorial(self):
		if config.plugins.CutListEditor.showIntro.value and not CutListEditor.tutorial_seen:
			CutListEditor.tutorial_seen = True
			self.session.open(MessageBox,_("Welcome to the cutlist editor.\n\nSeek to the start of the stuff you want to cut away. Press OK, select 'start cut'.\n\nThen seek to the end, press OK, select 'end cut'. That's it."), MessageBox.TYPE_INFO)

	def checkSkipShowHideLock(self):
		pass

	def setType(self, index, type):
		if len(self.cut_list):
			self.cut_list[index] = (self.cut_list[index][0], type)
			self["cutlist"].modifyEntry(index, CutListEntry(*self.cut_list[index]))

	def setIn(self):
		m = self["cutlist"].getIndex()
		self.setType(m, 0)
		self.uploadCuesheet()

	def setOut(self):
		m = self["cutlist"].getIndex()
		self.setType(m, 1)
		self.uploadCuesheet()

	def setMark(self):
		m = self["cutlist"].getIndex()
		self.setType(m, 2)
		self.uploadCuesheet()

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
		r = [ ]
		for e in self.cut_list:
			r.append(CutListEntry(*e))
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
		self.downloadCuesheet()

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
				if self.cut_start <= where <= self.context_position and what in (0,1):
					self.cut_list.remove((where, what))

			bisect.insort(self.cut_list, (self.cut_start, 1))
			bisect.insort(self.cut_list, (self.context_position, 0))
			self.uploadCuesheet()
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
			self.uploadCuesheet()
			self.inhibit_seek = False
		elif result == CutListContextMenu.RET_MARK:
			self.__addMark()
		elif result == CutListContextMenu.RET_DELETEMARK:
			self.cut_list.remove(self.context_nearest_mark)
			self.inhibit_seek = True
			self.uploadCuesheet()
			self.inhibit_seek = False
		elif result == CutListContextMenu.RET_REMOVEBEFORE:
			# remove in/out marks before current position
			for (where, what) in self.cut_list[:]:
				if where <= self.context_position and what in (0,1):
					self.cut_list.remove((where, what))
			# add 'in' point
			bisect.insort(self.cut_list, (self.context_position, 0))
			self.inhibit_seek = True
			self.uploadCuesheet()
			self.inhibit_seek = False
		elif result == CutListContextMenu.RET_REMOVEAFTER:
			# remove in/out marks after current position
			for (where, what) in self.cut_list[:]:
				if where >= self.context_position and what in (0,1):
					self.cut_list.remove((where, what))
			# add 'out' point
			bisect.insort(self.cut_list, (self.context_position, 1))
			self.inhibit_seek = True
			self.uploadCuesheet()
			self.inhibit_seek = False
		elif result == CutListContextMenu.RET_GRABFRAME:
			self.grabFrame()
		elif result == CutListContextMenu.RET_TOGGLEINTRO:
			self.toggleIntro()
		elif result == CutListContextMenu.RET_MOVIECUT:
			self.inhibit_seek = True
			self.uploadCuesheet()
			self.inhibit_seek = False
			self.session.nav.playService(self.old_service, forceRestart=True, adjust=False)
			if self.cut_service:
				try:
					MovieCut(session=self.session, service=self.cut_service)
				except:
					print "[CutListEditor] calling MovieCut failed"
			self.exit()

	# we modify the "play" behavior a bit:
	# if we press pause while being in slowmotion, we will pause (and not play)
	def playpauseService(self):
		if self.seekstate != self.SEEK_STATE_PLAY and not self.isStateSlowMotion(self.seekstate):
			self.unPauseService()
		else:
			self.pauseService()

	def grabFrame(self):
		service = self.session.nav.getCurrentlyPlayingServiceReference()
		if service:
			path = service.getPath()
			from Components.Console import Console
			grabConsole = Console()
			cmd = 'grab -vblpr%d "%s"' % (180, path.rsplit('.',1)[0] + ".png")
			grabConsole.ePopen(cmd)
			self.playpauseService()

	def toggleIntro(self):
		config.plugins.CutListEditor.showIntro.value = not config.plugins.CutListEditor.showIntro.value
		config.plugins.CutListEditor.showIntro.save()

