from MenuList import MenuList

from Tools.Directories import SCOPE_CURRENT_SKIN, resolveFilename
from os import path

from enigma import eListboxPythonMultiContent, RT_VALIGN_CENTER, gFont, eServiceCenter

from Tools.LoadPixmap import LoadPixmap
import skin

STATE_PLAY = 0
STATE_PAUSE = 1
STATE_STOP = 2
STATE_REWIND = 3
STATE_FORWARD = 4
STATE_NONE = 5

class PlayList(MenuList):
	def __init__(self, enableWrapAround = False):
		MenuList.__init__(self, [], enableWrapAround, eListboxPythonMultiContent)
		font = skin.fonts.get("PlayList", ("Regular", 18, 23))
		self.l.setFont(0, gFont(font[0], font[1]))
		self.l.setItemHeight(font[2])
		self.currPlaying = -1
		self.oldCurrPlaying = -1
		self.serviceHandler = eServiceCenter.getInstance()
		self.state = STATE_NONE
		self.icons = [
			LoadPixmap(resolveFilename(SCOPE_CURRENT_SKIN, "skin_default/icons/ico_mp_play.png")),
			LoadPixmap(resolveFilename(SCOPE_CURRENT_SKIN, "skin_default/icons/ico_mp_pause.png")),
			LoadPixmap(resolveFilename(SCOPE_CURRENT_SKIN, "skin_default/icons/ico_mp_stop.png")),
			LoadPixmap(resolveFilename(SCOPE_CURRENT_SKIN, "skin_default/icons/ico_mp_rewind.png")),
			LoadPixmap(path=resolveFilename(SCOPE_CURRENT_SKIN, "skin_default/icons/ico_mp_forward.png")),
		]

	def PlaylistEntryComponent(self, serviceref, state):
		res = [ serviceref ]
		text = serviceref.getName()
		if text is "":
			text = path.split(serviceref.getPath().split('/')[-1])[1]
		x, y, w, h = skin.parameters.get("PlayListName",(25, 1, 470, 22))
		res.append((eListboxPythonMultiContent.TYPE_TEXT, x, y, w, h, 0, RT_VALIGN_CENTER, text))
		try:
			png = self.icons[state]
			x, y, w, h = skin.parameters.get("PlayListIcon",(5, 3, 16, 16))
			res.append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHATEST, x, y, w, h, png))
		except:
		        pass
		return res

	def clear(self):
		del self.list[:]
		self.l.setList(self.list)
		self.currPlaying = -1
		self.oldCurrPlaying = -1

	def getSelection(self):
		return self.l.getCurrentSelection() and self.l.getCurrentSelection()[0]

	def addFile(self, serviceref):
		self.list.append(self.PlaylistEntryComponent(serviceref, STATE_NONE))

	def updateFile(self, index, newserviceref):
		if index < len(self.list):
		    self.list[index] = self.PlaylistEntryComponent(newserviceref, STATE_NONE)

	def deleteFile(self, index):
		if self.currPlaying >= index:
			self.currPlaying -= 1
		del self.list[index]

	def setCurrentPlaying(self, index):
		self.oldCurrPlaying = self.currPlaying
		self.currPlaying = index
		self.moveToIndex(index)

	def updateState(self, state):
		self.state = state
		if len(self.list) > self.oldCurrPlaying and self.oldCurrPlaying != -1:
			self.list[self.oldCurrPlaying] = self.PlaylistEntryComponent(self.list[self.oldCurrPlaying][0], STATE_NONE)
		if self.currPlaying != -1 and self.currPlaying < len(self.list):
			self.list[self.currPlaying] = self.PlaylistEntryComponent(self.list[self.currPlaying][0], state)
		self.updateList()

	def isStopped(self):
		return self.state in (STATE_STOP, STATE_NONE)

	def playFile(self):
		self.updateState(STATE_PLAY)

	def pauseFile(self):
		self.updateState(STATE_PAUSE)

	def stopFile(self):
		self.updateState(STATE_STOP)

	def rewindFile(self):
		self.updateState(STATE_REWIND)

	def forwardFile(self):
		self.updateState(STATE_FORWARD)

	def updateList(self):
		self.l.setList(self.list)

	def getCurrentIndex(self):
		return self.currPlaying

	def getCurrentEvent(self):
		l = self.l.getCurrentSelection()
		return l and self.serviceHandler.info(l[0]).getEvent(l[0])

	def getCurrent(self):
		l = self.l.getCurrentSelection()
		return l and l[0]

	def getServiceRefList(self):
		return [ x[0] for x in self.list ]

	def __len__(self):
		return len(self.list)
