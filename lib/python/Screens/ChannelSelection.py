from Screen import Screen
from Components.Button import Button
from Components.ServiceList import ServiceList
from Components.ActionMap import ActionMap
from EpgSelection import EPGSelection
from enigma import eServiceReference

from Screens.FixedMenu import FixedMenu

import xml.dom.minidom

class ChannelContextMenu(FixedMenu):
	def __init__(self, session, csel):
		self.csel = csel
		
		menu = [("back", self.close)]
		
		if csel.movemode:
			menu.append(("disable move mode", self.moveMode))
		else:
			menu.append(("enable move mode", self.moveMode))

		if csel.bouquet_mark_edit:
			menu.append(("end bouquet edit", self.bouquetMarkEnd))
			menu.append(("abort bouquet edit", self.bouquetMarkAbort))
		else:
			menu.append(("edit bouquet...", self.bouquetMarkStart))
		
		FixedMenu.__init__(self, session, "Channel Selection", menu)
		self.skinName = "Menu"

	def moveMode(self):
		self.csel.setMoveMode(self.csel.movemode)
		self.close()
	
	def bouquetMarkStart(self):
		self.csel.startMarkedEdit()
		self.close()
	
	def bouquetMarkEnd(self):
		self.csel.endMarkedEdit(abort=False)
		self.close()

	def bouquetMarkAbort(self):
		self.csel.endMarkedEdit(abort=True)
		self.close()
 
class ChannelSelection(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		
		self.entry_marked = False
		self.movemode = False
		self.bouquet_mark_edit = False
		
		## FIXME
		self.__marked = [ ]
		
		self["key_red"] = Button("All")
		self["key_green"] = Button("Provider")
		self["key_yellow"] = Button("Satellite")
		self["key_blue"] = Button("Favourites")
		
		self["list"] = ServiceList()
		self["list"].setRoot(eServiceReference("""1:0:1:0:0:0:0:0:0:0:(type == 1)"""))
		
		#self["okbutton"] = Button("ok", [self.channelSelected])
		
		class ChannelActionMap(ActionMap):
			def action(self, contexts, action):
				if action[:7] == "bouquet":
					l = self.csel["list"]
					l.setMode(l.MODE_NORMAL)
					l.setRoot(eServiceReference("1:0:1:0:0:0:0:0:0:0:" + action[8:]))
				else:
					ActionMap.action(self, contexts, action)

		self["actions"] = ChannelActionMap(["ChannelSelectActions", "OkCancelActions"], 
			{
				"cancel": self.close,
				"ok": self.channelSelected,
				"mark": self.doMark,
				"contextMenu": self.doContext,
				"showFavourites": self.showFavourites,
				"showEPGList": self.showEPGList
			})
		self["actions"].csel = self

	def showEPGList(self):
		self.session.open(EPGSelection, self["list"].getCurrent())

	#  marked edit mode
	def startMarkedEdit(self):
		self.bouquet_mark_edit = True
		self.clearMarks()
		
		# TODO
		marked = self.__marked
		
		l = self["list"]
		for x in marked:
			l.addMarked(x)
		
	def endMarkedEdit(self, abort):
		self.bouquet_mark_edit = True
		new_marked = self["list"].getMarked()
		self.__marked = new_marked
		self.clearMarks()
		self.bouquet_mark_edit = False

	def clearMarks(self):
		self["list"].clearMarks()
	
	def doMark(self):
		if not self.bouquet_mark_edit:
			return
		
		ref = self["list"].getCurrent()
		if self["list"].isMarked(ref):
			self["list"].removeMarked(ref)
		else:
			self["list"].addMarked(ref)
	
	# ...
	def channelSelected(self):
		ref = self["list"].getCurrent()
		if self.movemode:
			if self.entry_marked:
				self["list"].setCurrentMarked(False)
				self.entry_marked = False
			else:
				self["list"].setCurrentMarked(True)
				self.entry_marked = True
		elif (ref.flags & 7) == 7:
			l = self["list"]
			l.setMode(l.MODE_NORMAL)
			l.setRoot(ref)
		else:
			self.session.nav.playService(ref)
			self.close()

	#called from infoBar
	def zap(self):
		self.session.nav.playService(self["list"].getCurrent())

	def moveUp(self):
		self["list"].moveUp()

	def moveDown(self):
		self["list"].moveDown()

	def doContext(self):
		self.session.open(ChannelContextMenu, self)

	def setMoveMode(self, mode):
		if mode:
			self.movemode = False
		else:
			self.movemode = True

	def showFavourites(self):
		l = self["list" ]
		l.setRoot(eServiceReference('1:0:1:0:0:0:0:0:0:0:(provider == "fav")'))
		l.setMode(l.MODE_FAVOURITES)
