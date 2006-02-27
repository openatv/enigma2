from Plugins.Plugin import PluginDescriptor

from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Components.ServicePosition import ServicePositionGauge
from Components.ActionMap import HelpableActionMap
from Components.MenuList import MenuList
from Components.MultiContent import MultiContentEntryText, RT_HALIGN_RIGHT
from Components.ServiceEventTracker import ServiceEventTracker

from Screens.InfoBarGenerics import InfoBarSeek, InfoBarCueSheetSupport

from Components.GUIComponent import GUIComponent

from enigma import eListboxPythonMultiContent, eListbox, gFont, iPlayableService

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
	res.append(MultiContentEntryText(size=(400, 20), text = "%dh:%02dm:%02ds:%03d" % (h, m, s, ms)))
	res.append(MultiContentEntryText(pos=(400,0), size=(130, 20), text = type, flags = RT_HALIGN_RIGHT))

	return res

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
	
	def GUIcreate(self, parent):
		self.instance = eListbox(parent)
		self.instance.setContent(self.l)
		self.instance.setItemHeight(30)
		self.instance.selectionChanged.get().append(self.selectionChanged)

	def selectionChanged(self):
		for x in self.onSelectionChanged:
			x()
	
	def GUIdelete(self):
		self.instance.selectionChanged.get().remove(self.selectionChanged)
		self.instance.setContent(None)
		self.instance = None
	
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

class CutListEditor(Screen, InfoBarSeek, InfoBarCueSheetSupport):
	skin = """
		<screen position="100,100" size="550,400" title="Test" >
			<widget name="Timeline" position="10,0" size="530,40" 
				pointer="/usr/share/enigma2/position_pointer.png:3,5" />
			<widget name="Cutlist" position="10,50" size="530,200" />
		</screen>"""
	def __init__(self, session, service):
		self.skin = CutListEditor.skin
		Screen.__init__(self, session)
		InfoBarSeek.__init__(self)
		InfoBarCueSheetSupport.__init__(self)
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
		
		self["actions"] = HelpableActionMap(self, "CutListEditorActions",
			{
				"setIn": (self.setIn, _("Make this mark an 'in' point")),
				"setOut": (self.setOut, _("Make this mark an 'out' point")),
				"setMark": (self.setMark, _("Make this mark just a mark")),
				"addMark": (self.__addMark, _("Add a mark")),
				"removeMark": (self.__removeMark, _("Remove a mark")),
				"leave": (self.exit, _("Exit editor"))
			})
		
		self.tutorial_seen = False
		
		self.onExecBegin.append(self.showTutorial)
		self.__event_tracker = ServiceEventTracker(screen=self, eventmap=
			{
				iPlayableService.evCuesheetChanged: self.refillList
			})

		# to track new entries we save the last version of the cutlist
		self.last_cuts = [ ]
		
	def showTutorial(self):
		if not self.tutorial_seen:
			self.tutorial_seen = True
			self.session.open(MessageBox, 
				"""Welcome to the Cutlist editor. It has a *very* unintuitive handling:

You can add use the color keys to move around in the recorded movie. 
By pressing shift-yellow, you can add a mark or remove an existing one.
You can then assign them to be either 'in' or 'out' positions by selecting them in the list and pressing 1 or 2.
				""", MessageBox.TYPE_INFO)
	
	def checkSkipShowHideLock(self):
		pass
	
	def setType(self, index, type):
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

def main(session, service):
	session.open(CutListEditor, service)

def Plugins():
 	return PluginDescriptor(name="Cutlist Editor", description=_("Cutlist editor..."), where = PluginDescriptor.WHERE_MOVIELIST, fnc=main)
