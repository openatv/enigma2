from Screen import Screen
from Components.Button import Button
from Components.ServiceList import ServiceList
from Components.ActionMap import ActionMap
from EpgSelection import EPGSelection
from enigma import eServiceReference, eEPGCache, eEPGCachePtr, eServiceCenter, eServiceCenterPtr, iMutableServiceListPtr

from Screens.FixedMenu import FixedMenu

import xml.dom.minidom

class ChannelContextMenu(FixedMenu):
	def __init__(self, session, csel):
		self.csel = csel
		
		menu = [ ]
		
		if csel.mutableList is not None:
			if not csel.bouquet_mark_edit:
				if csel.movemode:
					menu.append(("disable move mode", self.toggleMoveMode))
				else:
					menu.append(("enable move mode", self.toggleMoveMode))

			if not csel.movemode:
				if csel.bouquet_mark_edit:
					menu.append(("end bouquet edit", self.bouquetMarkEnd))
					menu.append(("abort bouquet edit", self.bouquetMarkAbort))
				else:
					menu.append(("edit bouquet...", self.bouquetMarkStart))

			if not csel.bouquet_mark_edit and not csel.movemode:
				menu.append(("remove service", self.removeCurrentService))
			menu.append(("back", self.close))
		else:
			menu.append(("back", self.close))

		FixedMenu.__init__(self, session, "Channel Selection", menu)
		self.skinName = "Menu"

	def removeCurrentService(self):
		self.close()
		self.csel.removeCurrentService()

	def toggleMoveMode(self):
		self.csel.toggleMoveMode()
		self.close()

	def bouquetMarkStart(self):
		self.close()
		self.csel.startMarkedEdit()

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
		self.setRoot(eServiceReference("""1:0:1:0:0:0:0:0:0:0:(type == 1)"""))
		
		#self["okbutton"] = Button("ok", [self.channelSelected])
		
		class ChannelActionMap(ActionMap):
			def action(self, contexts, action):
				if action[:7] == "bouquet":
					l = self.csel
					list = l["list"]
					list.setMode(list.MODE_NORMAL)
					l.setRoot(eServiceReference("1:7:1:0:0:0:0:0:0:0:" + action[8:]))
				else:
					if action == "cancel":
						l = self.csel
						if l.movemode: #movemode active?
							l.channelSelected() # unmark
							l.toggleMoveMode() # disable move mode
						elif l.bouquet_mark_edit:
							l.endMarkedEdit(True) # abort edit mode
					ActionMap.action(self, contexts, action)

		self["actions"] = ChannelActionMap(["ChannelSelectActions", "OkCancelActions", "ContextMenuActions"], 
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
		ref=self["list"].getCurrent()
		ptr=eEPGCache.getInstance()
		if ptr.startTimeQuery(ref) != -1:
			self.session.open(EPGSelection, ref)
		else:
			print 'no epg for service', ref.toString()

#  multiple marked entry stuff ( edit mode, later multiepg selection )
	def startMarkedEdit(self):
		l = self["list"]
		# add all services from the current list to internal marked set in listboxservicecontent
		if self.mutableList is not None:
			self.bouquetRoot = l.getRoot()
			self.clearMarks() # this clears the internal marked set in the listboxservicecontent
			self.bouquet_mark_edit = True
			self.__marked = l.getRootServices()
			for x in self.__marked:
				l.addMarked(eServiceReference(x))

	def removeCurrentService(self):
		l = self["list"]
		ref=l.getCurrent()
		if ref.valid() and self.mutableList is not None:
			self.mutableList.removeService(ref)
			self.mutableList.flushChanges() #FIXME dont flush on each single removed service
			self.setRoot(l.getRoot())

	def endMarkedEdit(self, abort):
		l = self["list"]
		if not abort and self.mutableList is not None:
			new_marked = set(l.getMarked())
			old_marked = set(self.__marked)
			removed = old_marked - new_marked
			added = new_marked - old_marked
			changed = False
			for x in removed:
				changed = True
				self.mutableList.removeService(eServiceReference(x))
			for x in added:
				changed = True
				self.mutableList.addService(eServiceReference(x))
			if changed:
				self.mutableList.flushChanges()
				#self.setRoot(self.bouquetRoot)
				self.showFavourites()
		self.__marked = []
		self.clearMarks()
		self.bouquet_mark_edit = False
		self.bouquetRoot = None

	def setRoot(self, root):
		if not self.movemode:
			if not self.bouquet_mark_edit:
				serviceHandler = eServiceCenter.getInstance()
				list = serviceHandler.list(root)
				if list is not None:
					self.mutableList = list.startEdit()
				else:
					self.mutableList = None
			self["list"].setRoot(root)

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
			self.setRoot(ref)
		elif self.bouquet_mark_edit:
			self.doMark()
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

	def toggleMoveMode(self):
		if self.movemode:
			if self.entry_marked:
				self.channelSelected() # unmark current entry
			self.movemode = False
			self.mutableList.flushChanges() # FIXME add check if changes was made
		else:
			self.movemode = True

	def showFavourites(self):
		self.setRoot(eServiceReference('1:7:1:0:0:0:0:0:0:0:(type == 1) FROM BOUQUET "userbouquet.favourites.tv" ORDER BY bouquet'))
		list = self["list"]
		list.setMode(list.MODE_FAVOURITES)
