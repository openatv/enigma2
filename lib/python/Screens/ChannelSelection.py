from Screen import Screen
from Components.Button import Button
from Components.ServiceList import ServiceList
from Components.ActionMap import NumberActionMap
from EpgSelection import EPGSelection
from enigma import eServiceReference, eEPGCache, eEPGCachePtr, eServiceCenter, eServiceCenterPtr, iMutableServiceListPtr, iStaticServiceInformationPtr, eTimer
from Components.config import config, configElement, ConfigSubsection, configText
from Screens.FixedMenu import FixedMenu
from Tools.NumericalTextInput import NumericalTextInput
from Components.NimManager import nimmanager

import xml.dom.minidom

class BouquetSelector(FixedMenu):
	def __init__(self, session, bouquets, selectedFunc):
		self.selectedFunc=selectedFunc
		entrys = [ ]
		for x in bouquets:
			entrys.append((x[0], self.bouquetSelected, x[1]))
		FixedMenu.__init__(self, session, "Bouquetlist", entrys)
		self.skinName = "Menu"

	def bouquetSelected(self):
		self.selectedFunc(self["menu"].getCurrent()[2])

class ChannelContextMenu(FixedMenu):
	def __init__(self, session, csel):
		self.csel = csel

		menu = [ ]

		inBouquetRootList = csel.servicelist.getRoot().getPath().find('FROM BOUQUET "bouquets.') != -1 #FIXME HACK
		inBouquet = csel.getMutableList() is not None
		haveBouquets = csel.bouquet_root.getPath().find('FROM BOUQUET "bouquets.') != -1

		if not csel.bouquet_mark_edit and not csel.movemode and not inBouquetRootList:
			if (csel.getCurrentSelection().flags & eServiceReference.flagDirectory) != eServiceReference.flagDirectory:
				if haveBouquets:
					menu.append((_("add service to bouquet"), self.addServiceToBouquetSelected))
				else:
					menu.append((_("add service to favourites"), self.addServiceToBouquetSelected))
			if inBouquet:
				menu.append((_("remove service"), self.removeCurrentService))

		if inBouquet: # current list is editable?
			if not csel.bouquet_mark_edit:
				if not csel.movemode:
					menu.append((_("enable move mode"), self.toggleMoveMode))
					if not inBouquetRootList:
						if haveBouquets:
							menu.append((_("enable bouquet edit"), self.bouquetMarkStart))
						else:
							menu.append((_("enable favourite edit"), self.bouquetMarkStart))
				else:
					menu.append((_("disable move mode"), self.toggleMoveMode))
			elif not inBouquetRootList:
				if haveBouquets:
					menu.append((_("end bouquet edit"), self.bouquetMarkEnd))
					menu.append((_("abort bouquet edit"), self.bouquetMarkAbort))
				else:
					menu.append((_("end favourites edit"), self.bouquetMarkEnd))
					menu.append((_("abort favourites edit"), self.bouquetMarkAbort))

		menu.append((_("back"), self.close))

		FixedMenu.__init__(self, session, _("Channel Selection"), menu)
		self.skinName = "Menu"

	def addServiceToBouquetSelected(self):
		bouquets = self.csel.getBouquetList()
		if bouquets is None:
			cnt = 0
		else:
			cnt = len(bouquets)
		if cnt > 1: # show bouquet list
			self.session.open(BouquetSelector, bouquets, self.addCurrentServiceToBouquet)
		elif cnt == 1: # add to only one existing bouquet
			self.addCurrentServiceToBouquet(bouquet[0][1])
		else: #no bouquets in root.. so assume only one favourite list is used
			self.addCurrentServiceToBouquet(self.csel.bouquet_root)

	def addCurrentServiceToBouquet(self, dest):
		self.csel.addCurrentServiceToBouquet(dest)
		self.close()

	def removeCurrentService(self):
		self.csel.removeCurrentService()
		self.close()

	def toggleMoveMode(self):
		self.csel.toggleMoveMode()
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

class ChannelSelectionEdit:
	def __init__(self):
		self.entry_marked = False
		self.movemode = False
		self.bouquet_mark_edit = False
		self.mutableList = None
		self.__marked = [ ]
		self.saved_title = None
		self.saved_root = None

	def getMutableList(self, root=eServiceReference()):
		if not self.mutableList is None:
			return self.mutableList
		serviceHandler = eServiceCenter.getInstance()
		if not root.valid():
			root=self.servicelist.getRoot()
		list = serviceHandler.list(root)
		if list is not None:
			return list.startEdit()
		return None

#  multiple marked entry stuff ( edit mode, later multiepg selection )
	def startMarkedEdit(self):
		self.mutableList = self.getMutableList()
		# add all services from the current list to internal marked set in listboxservicecontent
		self.bouquetRoot = self.servicelist.getRoot()
		self.clearMarks() # this clears the internal marked set in the listboxservicecontent
		self.saved_title = self.instance.getTitle()
		new_title = self.saved_title
		if self.bouquet_root.getPath().find('FROM BOUQUET "bouquets.') != -1:
			new_title += ' ' + _("[bouquet edit]")
		else:
			new_title += ' ' + _("[favourite edit]")
		self.instance.setTitle(new_title)
		self.bouquet_mark_edit = True
		self.__marked = self.servicelist.getRootServices()
		for x in self.__marked:
			self.servicelist.addMarked(eServiceReference(x))
		self.saved_root = self.getRoot()
		self.showAllServices()

	def endMarkedEdit(self, abort):
		if not abort and self.mutableList is not None:
			new_marked = set(self.servicelist.getMarked())
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
		self.__marked = []
		self.clearMarks()
		self.bouquet_mark_edit = False
		self.bouquetRoot = None
		self.mutableList = None
		self.instance.setTitle(self.saved_title)
		self.saved_title = None
		self.setRoot(self.saved_root)

	def clearMarks(self):
		self.servicelist.clearMarks()

	def doMark(self):
		ref = self.servicelist.getCurrent()
		if self.servicelist.isMarked(ref):
			self.servicelist.removeMarked(ref)
		else:
			self.servicelist.addMarked(ref)

	def removeCurrentService(self):
		ref = self.servicelist.getCurrent()
		mutableList = self.getMutableList()
		if ref.valid() and mutableList is not None:
			if not mutableList.removeService(ref):
				currentIndex = self.servicelist.getCurrentIndex()
				self.servicelist.moveDown()
				if self.servicelist.getCurrentIndex() == currentIndex:
					currentIndex -= 1
				mutableList.flushChanges() #FIXME dont flush on each single removed service
				self.setRoot(self.servicelist.getRoot())
				self.servicelist.moveToIndex(currentIndex)

	def addCurrentServiceToBouquet(self, dest):
		mutableList = self.getMutableList(dest)
		if not mutableList is None:
			if not mutableList.addService(self.servicelist.getCurrent()):
				mutableList.flushChanges()
		self.close()

	def toggleMoveMode(self):
		if self.movemode:
			if self.entry_marked:
				self.toggleMoveMarked() # unmark current entry
			self.movemode = False
			self.mutableList.flushChanges() # FIXME add check if changes was made
			self.mutableList = None
			self.instance.setTitle(self.saved_title)
			self.saved_title = None
		else:
			self.mutableList = self.getMutableList()
			self.movemode = True
			self.saved_title = self.instance.getTitle()
			new_title = self.saved_title
			new_title += ' ' + _("[move mode]");
			self.instance.setTitle(new_title);

	def handleEditCancel(self):
		if self.movemode: #movemode active?
			self.channelSelected() # unmark
			self.toggleMoveMode() # disable move mode
		elif self.bouquet_mark_edit:
			self.endMarkedEdit(True) # abort edit mode

	def toggleMoveMarked(self):
		if self.entry_marked:
			self.servicelist.setCurrentMarked(False)
			self.entry_marked = False
		else:
			self.servicelist.setCurrentMarked(True)
			self.entry_marked = True

	def doContext(self):
		self.session.open(ChannelContextMenu, self)

class ChannelSelectionBase(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)

		# this makes it much simple to implement a selectable radio or tv mode :)
		self.service_types_tv = '1:7:1:0:0:0:0:0:0:0:(type == 1) || (type == 17)'
		self.service_types_radio = '1:7:1:0:0:0:0:0:0:0:(type == 2)'

		self.service_types = self.service_types_tv

		#self.bouquet_root = eServiceReference('1:7:1:0:0:0:0:0:0:0:(type == 1) FROM BOUQUET "bouquets.tv" ORDER BY bouquet')
		self.bouquet_root = eServiceReference('%s FROM BOUQUET "userbouquet.favourites.tv" ORDER BY bouquet'%(self.service_types))

		self["key_red"] = Button(_("All"))
		self["key_green"] = Button(_("Satellites"))
		self["key_yellow"] = Button(_("Provider"))
		self["key_blue"] = Button(_("Favourites"))

		self["list"] = ServiceList()
		self.servicelist = self["list"]

		#self["okbutton"] = Button("ok", [self.channelSelected])

		self.numericalTextInput = NumericalTextInput()

	def getBouquetNumOffset(self, bouquet):
		if self.bouquet_root.getPath().find('FROM BOUQUET "bouquets.') == -1: #FIXME HACK
			return 0
		offsetCount = 0
		serviceHandler = eServiceCenter.getInstance()
		bouquetlist = serviceHandler.list(self.bouquet_root)
		if not bouquetlist is None:
			while True:
				bouquetIterator = bouquetlist.getNext()
				if not bouquetIterator.valid() or bouquetIterator == bouquet: #end of list or bouquet found
					break
				if ((bouquetIterator.flags & eServiceReference.flagDirectory) != eServiceReference.flagDirectory):
					continue
				servicelist = serviceHandler.list(bouquetIterator)
				if not servicelist is None:
					while True:
						serviceIterator = servicelist.getNext()
						if not serviceIterator.valid(): #check if end of list
							break
						if serviceIterator.flags: #playable services have no flags
							continue
						offsetCount += 1
		return offsetCount

	def setRootBase(self, root, justSet=False):
		inBouquetRootList = root.getPath().find('FROM BOUQUET "bouquets.') != -1 #FIXME HACK
		if not inBouquetRootList and (root.getPath().find('FROM BOUQUET') != -1):
			self.servicelist.setMode(ServiceList.MODE_FAVOURITES)
			self.servicelist.setNumberOffset(self.getBouquetNumOffset(root))
		else:
			self.servicelist.setMode(ServiceList.MODE_NORMAL)
		self.servicelist.setRoot(root, justSet)

	def moveUp(self):
		self.servicelist.moveUp()

	def moveDown(self):
		self.servicelist.moveDown()

	def showAllServices(self):
		ref = eServiceReference('%s ORDER BY name'%(self.service_types))
		self.setRoot(ref)

	def showSatellites(self):
		ref = eServiceReference('%s FROM SATELLITES ORDER BY satellitePosition'%(self.service_types))
		self.setRoot(ref, True)
		serviceHandler = eServiceCenter.getInstance()
		servicelist = serviceHandler.list(ref)
		if not servicelist is None:
			while True:
				service = servicelist.getNext()
				if not service.valid(): #check if end of list
					break
				orbpos = service.getData(4) >> 16
				if service.getPath().find("FROM PROVIDER") != -1:
					service_name = _("Providers")
				else:
					service_name = _("Services")
				try:
					service_name += str(' - %s'%(nimmanager.getSatDescription(orbpos)))
					service.setName(service_name) # why we need this cast?
				except:
					if orbpos > 1800: # west
						service.setName("%s (%3.1f" + _("W") + ")" %(str, (0 - (orbpos - 3600)) / 10.0))
					else:
						service.setName("%s (%3.1f" + _("E") + ")" % (str, orbpos / 10.0))
				self.servicelist.addService(service)
		self.servicelist.finishFill()

	def showProviders(self):
		ref = eServiceReference('%s FROM PROVIDERS ORDER BY name'%(self.service_types))
		self.setRoot(ref)

	def showFavourites(self):
		self.setRoot(self.bouquet_root)

	def keyNumberGlobal(self, number):
		char = self.numericalTextInput.getKey(number)
		print "You pressed number " + str(number)
		print "You would go to character " + str(char)
		self.servicelist.moveToChar(char)

	def enterBouquet(self, action):
		if action[:7] == "bouquet":
			if action.find("FROM BOUQUET") != -1:
				self.setRoot(eServiceReference("1:7:1:0:0:0:0:0:0:0:" + action[8:]))
			else:
				self.setRoot(eServiceReference("1:0:1:0:0:0:0:0:0:0:" + action[8:]))
			return True
		return False

	def getRoot(self):
		return self.servicelist.getRoot()

	def getCurrentSelection(self):
		return self.servicelist.getCurrent()

	def setCurrentSelection(self, service):
		self.servicelist.setCurrent(service)

	def cancel(self):
		self.close(None)

	def getBouquetList(self):
		serviceCount=0
		bouquets = [ ]
		serviceHandler = eServiceCenter.getInstance()
		list = serviceHandler.list(self.bouquet_root)
		if not list is None:
			while True:
				s = list.getNext()
				if not s.valid():
					break
				if ((s.flags & eServiceReference.flagDirectory) == eServiceReference.flagDirectory):
					info = serviceHandler.info(s)
					if not info is None:
						bouquets.append((info.getName(s), s))
				else:
					serviceCount += 1
			if len(bouquets) == 0 and serviceCount > 0:
				info = serviceHandler.info(self.bouquet_root)
				if not info is None:
					bouquets.append((info.getName(self.bouquet_root), self.bouquet_root))
			return bouquets
		return None

class ChannelSelection(ChannelSelectionBase, ChannelSelectionEdit):
	def __init__(self, session):
		ChannelSelectionBase.__init__(self,session)
		ChannelSelectionEdit.__init__(self)

		#config for lastservice
		config.tv = ConfigSubsection();
		config.tv.lastservice = configElement("config.tv.lastservice", configText, "", 0);
		config.tv.lastroot = configElement("config.tv.lastroot", configText, "", 0);

		class ChannelActionMap(NumberActionMap):
			def action(self, contexts, action):
				if not self.csel.enterBouquet(action):
					if action == "cancel":
						self.csel.handleEditCancel()
					NumberActionMap.action(self, contexts, action)
		self["actions"] = ChannelActionMap(["ChannelSelectActions", "OkCancelActions", "ContextMenuActions"],
			{
				"cancel": self.cancel,
				"ok": self.channelSelected,
				"mark": self.doMark,
				"contextMenu": self.doContext,
				"showFavourites": self.showFavourites,
				"showAllServices": self.showAllServices,
				"showProviders": self.showProviders,
				"showSatellites": self.showSatellites,
				"showEPGList": self.showEPGList,
				"1": self.keyNumberGlobal,
				"2": self.keyNumberGlobal,
				"3": self.keyNumberGlobal,
				"4": self.keyNumberGlobal,
				"5": self.keyNumberGlobal,
				"6": self.keyNumberGlobal,
				"7": self.keyNumberGlobal,
				"8": self.keyNumberGlobal,
				"9": self.keyNumberGlobal,
				"0": self.keyNumberGlobal
			})
		self["actions"].csel = self
		self.onShown.append(self.onShow)

#		self.onLayoutFinish.append(self.onCreate)
		self.lastChannelRootTimer = eTimer()
		self.lastChannelRootTimer.timeout.get().append(self.onCreate)
		self.lastChannelRootTimer.start(100,True)

	def onCreate(self):
		lastroot=eServiceReference(config.tv.lastroot.value)
		if lastroot.valid():
			self.setRoot(lastroot)
		else:
			self.showFavourites()
			self.saveRoot(self.getRoot())
		lastservice=eServiceReference(config.tv.lastservice.value)
		if lastservice.valid():
			self.session.nav.playService(lastservice)
			self.servicelist.setCurrent(lastservice)

	def onShow(self):
		ref = self.session.nav.getCurrentlyPlayingServiceReference()
		if ref is not None and ref.valid() and ref.getPath() == "":
			self.servicelist.setPlayableIgnoreService(ref)
		else:
			self.servicelist.setPlayableIgnoreService(eServiceReference())

	def showEPGList(self):
		ref=self.getCurrentSelection()
		ptr=eEPGCache.getInstance()
		if ptr.startTimeQuery(ref) != -1:
			self.session.open(EPGSelection, ref)
		else:
			print 'no epg for service', ref.toString()

	def channelSelected(self):
		ref = self.getCurrentSelection()
		if self.movemode:
			self.toggleMoveMarked()
		elif (ref.flags & 7) == 7:
			self.setRoot(ref)
		elif self.bouquet_mark_edit:
			self.doMark()
		else:
			self.zap()
			self.close(ref)

	def setRoot(self, root, justSet=False):
		if not self.movemode:
			self.setRootBase(root, justSet)

	#called from infoBar and channelSelected
	def zap(self):
		self.session.nav.playService(self.getCurrentSelection())
		self.saveRoot(self.getRoot())
		self.saveChannel()

	def saveRoot(self, root):
		if root is not None:
			config.tv.lastroot.value = root.toString()
			config.tv.lastroot.save()

	def saveChannel(self):
		ref = self.session.nav.getCurrentlyPlayingServiceReference()
		if ref is not None:
			refstr = ref.toString()
		else:
			refstr = ""
		config.tv.lastservice.value = refstr
		config.tv.lastservice.save()

	def cancel(self):
		self.close(None)
		lastroot=eServiceReference(config.tv.lastroot.value)
		lastservice=eServiceReference(config.tv.lastservice.value)
		if lastroot.valid() and self.getRoot() != lastroot:
			self.setRoot(lastroot)
		if lastservice.valid() and self.getCurrentSelection() != lastservice:
			self.servicelist.setCurrent(lastservice)

class SimpleChannelSelection(ChannelSelectionBase):
	def __init__(self, session, title):
		ChannelSelectionBase.__init__(self, session)
		self.title = title
		self.onShown.append(self.onExecCallback)

		class ChannelActionMap(NumberActionMap):
			def action(self, contexts, action):
				if not self.csel.enterBouquet(action):
					NumberActionMap.action(self, contexts, action)
		self["actions"] = ChannelActionMap(["ChannelSelectActions", "OkCancelActions", "ContextMenuActions"],
			{
				"cancel": self.cancel,
				"ok": self.channelSelected,
				"showFavourites": self.showFavourites,
				"showAllServices": self.showAllServices,
				"showProviders": self.showProviders,
				"showSatellites": self.showSatellites,
				"1": self.keyNumberGlobal,
				"2": self.keyNumberGlobal,
				"3": self.keyNumberGlobal,
				"4": self.keyNumberGlobal,
				"5": self.keyNumberGlobal,
				"6": self.keyNumberGlobal,
				"7": self.keyNumberGlobal,
				"8": self.keyNumberGlobal,
				"9": self.keyNumberGlobal,
				"0": self.keyNumberGlobal
			})
		self["actions"].csel = self

	def onExecCallback(self):
		print "onExecCallback"
		self.showFavourites()
		self.session.currentDialog.instance.setTitle(self.title)

	def channelSelected(self): # just return selected service
		ref = self.getCurrentSelection()
		self.close(ref)

	def setRoot(self, root):
		self.setRootBase(root)

