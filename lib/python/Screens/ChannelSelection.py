from Screen import Screen
from Components.Button import Button
from Components.ServiceList import ServiceList
from Components.ActionMap import NumberActionMap, ActionMap
from Components.MenuList import MenuList
from EpgSelection import EPGSelection
from enigma import eServiceReference, eEPGCache, eEPGCachePtr, eServiceCenter, eServiceCenterPtr, iMutableServiceListPtr, iStaticServiceInformationPtr, eTimer, eDVBDB
from Components.config import config, configElement, ConfigSubsection, configText, currentConfigSelectionElement
from Screens.FixedMenu import FixedMenu
from Tools.NumericalTextInput import NumericalTextInput
from Components.NimManager import nimmanager
from Components.ServiceName import ServiceName
from Components.Clock import Clock
from Components.EventInfo import EventInfo
from ServiceReference import ServiceReference
from re import *
from os import remove

import xml.dom.minidom

class BouquetSelector(Screen):
	def __init__(self, session, bouquets, selectedFunc):
		Screen.__init__(self, session)

		self.selectedFunc=selectedFunc

		self["actions"] = ActionMap(["OkCancelActions"],
			{
				"ok": self.okbuttonClick,
				"cancel": self.cancelClick
			})
		entrys = [ ]
		for x in bouquets:
			entrys.append((x[0], x[1]))
		self["menu"] = MenuList(entrys)

	def okbuttonClick(self):
		self.selectedFunc(self["menu"].getCurrent()[1])
		self.close(True)

	def cancelClick(self):
		self.close(False)

class ChannelContextMenu(Screen):
	def __init__(self, session, csel):
		Screen.__init__(self, session)
		self.csel = csel

		self["actions"] = ActionMap(["OkCancelActions"],
			{
				"ok": self.okbuttonClick,
				"cancel": self.cancelClick
			})
		menu = [ ]

		inBouquetRootList = csel.getRoot().getPath().find('FROM BOUQUET "bouquets.') != -1 #FIXME HACK
		inBouquet = csel.getMutableList() is not None
		haveBouquets = csel.bouquet_root.getPath().find('FROM BOUQUET "bouquets.') != -1

		if not csel.bouquet_mark_edit and not csel.movemode:
			if not inBouquetRootList:
				if (csel.getCurrentSelection().flags & eServiceReference.flagDirectory) != eServiceReference.flagDirectory:
					if haveBouquets:
						menu.append((_("add service to bouquet"), self.addServiceToBouquetSelected))
					else:
						menu.append((_("add service to favourites"), self.addServiceToBouquetSelected))
				elif haveBouquets:
					if not inBouquet and csel.getCurrentSelection().getPath().find("PROVIDERS") == -1:
						menu.append((_("copy to favourites"), csel.copyCurrentToBouquetList))
				if inBouquet:
					menu.append((_("remove service"), self.removeCurrentService))
			elif haveBouquets:
				menu.append((_("remove bouquet"), csel.removeBouquet))

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

		menu.append((_("back"), self.cancelClick))
		self["menu"] = MenuList(menu)

	def okbuttonClick(self):
		self["menu"].getCurrent()[1]()

	def cancelClick(self):
		self.close(False)

	def addServiceToBouquetSelected(self):
		bouquets = self.csel.getBouquetList()
		if bouquets is None:
			cnt = 0
		else:
			cnt = len(bouquets)
		if cnt > 1: # show bouquet list
			self.session.openWithCallback(self.bouquetSelClosed, BouquetSelector, bouquets, self.addCurrentServiceToBouquet)
		elif cnt == 1: # add to only one existing bouquet
			self.addCurrentServiceToBouquet(bouquets[0][1])
		else: #no bouquets in root.. so assume only one favourite list is used
			self.addCurrentServiceToBouquet(self.csel.bouquet_root)

	def bouquetSelClosed(self, recursive):
		if recursive:
			self.close(False)

	def copyCurrentToBouquetList(self):
		self.csel.copyCurrentToBouquetList()
		self.close()

	def removeBouquet(self):
		self.csel.removeBouquet()
		self.close()

	def addCurrentServiceToBouquet(self, dest):
		self.csel.addCurrentServiceToBouquet(dest)

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

class ChannelSelectionEPG:
	def __init__(self):
		self["ChannelSelectEPGActions"] = ActionMap(["ChannelSelectEPGActions"],
			{
				"showEPGList": self.showEPGList,
			})

	def showEPGList(self):
		ref=self.getCurrentSelection()
		ptr=eEPGCache.getInstance()
		if ptr.startTimeQuery(ref) != -1:
			self.session.open(EPGSelection, ref)
		else:
			print 'no epg for service', ref.toString()

class ChannelSelectionEdit:
	def __init__(self):
		self.entry_marked = False
		self.movemode = False
		self.bouquet_mark_edit = False
		self.mutableList = None
		self.__marked = [ ]
		self.saved_title = None
		self.saved_root = None

		class ChannelSelectionEditActionMap(ActionMap):
			def __init__(self, csel, contexts = [ ], actions = { }, prio=0):
				ActionMap.__init__(self, contexts, actions, prio)
				self.csel = csel
			def action(self, contexts, action):
				if action == "cancel":
					self.csel.handleEditCancel()
				elif action == "ok":
					pass # avoid typo warning...
				else:
					ActionMap.action(self, contexts, action)
		self["ChannelSelectEditActions"] = ChannelSelectionEditActionMap(self, ["ChannelSelectEditActions", "OkCancelActions"],
			{
				"contextMenu": self.doContext,
			})

	def getMutableList(self, root=eServiceReference()):
		if not self.mutableList is None:
			return self.mutableList
		serviceHandler = eServiceCenter.getInstance()
		if not root.valid():
			root=self.getRoot()
		list = serviceHandler.list(root)
		if list is not None:
			return list.startEdit()
		return None

	def buildBouquetID(self, str):
		tmp = str.lower()
		name = ''
		for c in tmp:
			if (c >= 'a' and c <= 'z') or (c >= '0' and c <= '9'):
				name += c
			else:
				name += '_'
		return name

	def copyCurrentToBouquetList(self):
		provider = ServiceReference(self.getCurrentSelection())
		serviceHandler = eServiceCenter.getInstance()
		mutableBouquetList = serviceHandler.list(self.bouquet_root).startEdit()
		if mutableBouquetList:
			providerName = provider.getServiceName()
			if self.mode == MODE_TV:
				str = '1:7:1:0:0:0:0:0:0:0:(type == 1) FROM BOUQUET \"userbouquet.%s.tv\" ORDER BY bouquet'%(self.buildBouquetID(providerName))
			else:
				str = '1:7:2:0:0:0:0:0:0:0:(type == 2) FROM BOUQUET \"userbouquet.%s.radio\" ORDER BY bouquet'%(self.buildBouquetID(providerName))
			new_bouquet_ref = eServiceReference(str)
			if not mutableBouquetList.addService(new_bouquet_ref):
				mutableBouquetList.flushChanges()
				eDVBDB.getInstance().reloadBouquets()
				mutableBouquet = serviceHandler.list(new_bouquet_ref).startEdit()
				if mutableBouquet:
					mutableBouquet.setListName(providerName)
					list = [ ]
					services = serviceHandler.list(provider.ref)
					if not services is None:
						if not services.getContent(list, True):
							for service in list:
								if mutableBouquet.addService(service):
									print "add", service.toString(), "to new bouquet failed"
							mutableBouquet.flushChanges()
						else:
							print "getContent failed"
					else:
						print "list provider", providerName, "failed"
				else:
					print "get mutable list for new created bouquet failed"
			else:
				print "add", str, "to bouquets failed"
		else:
			print "bouquetlist is not editable"

	def removeBouquet(self):
		refstr = self.getCurrentSelection().toString()
		pos = refstr.find('FROM BOUQUET "')
		if pos != -1:
			refstr = refstr[pos+14:]
			print refstr
			pos = refstr.find('"')
			if pos != -1:
				filename = '/etc/enigma2/' + refstr[:pos] # FIXMEEE !!! HARDCODED /etc/enigma2
		self.removeCurrentService()
		remove(filename)
		eDVBDB.getInstance().reloadBouquets()

#  multiple marked entry stuff ( edit mode, later multiepg selection )
	def startMarkedEdit(self):
		self.mutableList = self.getMutableList()
		# add all services from the current list to internal marked set in listboxservicecontent
		self.bouquetRoot = self.getRoot()
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
				self.setRoot(self.getRoot())
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
			self.pathChangedDisabled = False # re-enable path change
			self.mutableList.flushChanges() # FIXME add check if changes was made
			self.mutableList = None
			self.instance.setTitle(self.saved_title)
			self.saved_title = None
		else:
			self.mutableList = self.getMutableList()
			self.movemode = True
			self.pathChangedDisabled = True # no path change allowed in movemode
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

MODE_TV = 0
MODE_RADIO = 1

class ChannelSelectionBase(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)

		# this makes it much simple to implement a selectable radio or tv mode :)
		self.service_types_tv = '1:7:1:0:0:0:0:0:0:0:(type == 1) || (type == 17)'
		self.service_types_radio = '1:7:2:0:0:0:0:0:0:0:(type == 2)'

		self["key_red"] = Button(_("All"))
		self["key_green"] = Button(_("Satellites"))
		self["key_yellow"] = Button(_("Provider"))
		self["key_blue"] = Button(_("Favourites"))

		self["list"] = ServiceList()
		self.servicelist = self["list"]

		self.numericalTextInput = NumericalTextInput()

		self.servicePathTV = [ ]
		self.servicePathRadio = [ ]

		self.pathChangedDisabled = False

		self["ChannelSelectBaseActions"] = NumberActionMap(["ChannelSelectBaseActions", "NumberActions"],
			{
				"showFavourites": self.showFavourites,
				"showAllServices": self.showAllServices,
				"showProviders": self.showProviders,
				"showSatellites": self.showSatellites,
				"nextBouquet": self.nextBouquet,
				"prevBouquet": self.prevBouquet,
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

	def appendDVBTypes(self, ref):
		path = ref.getPath()
		pos = path.find(' FROM BOUQUET')
		if pos != -1:
			return eServiceReference(self.service_types + path[pos:])
		return ref

	def getBouquetNumOffset(self, bouquet):
		bouquet = self.appendDVBTypes(bouquet)
		if self.bouquet_root.getPath().find('FROM BOUQUET "bouquets.') == -1: #FIXME HACK
			return 0
		offsetCount = 0
		serviceHandler = eServiceCenter.getInstance()
		bouquetlist = serviceHandler.list(self.bouquet_root)
		if not bouquetlist is None:
			while True:
				bouquetIterator = self.appendDVBTypes(bouquetlist.getNext())
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

	def recallBouquetMode(self):
		if self.mode == MODE_TV:
			self.service_types = self.service_types_tv
			if currentConfigSelectionElement(config.usage.multibouquet) == "yes":
				self.bouquet_rootstr = '1:7:1:0:0:0:0:0:0:0:(type == 1) FROM BOUQUET "bouquets.tv" ORDER BY bouquet'
			else:
				self.bouquet_rootstr = '%s FROM BOUQUET "userbouquet.favourites.tv" ORDER BY bouquet'%(self.service_types)
		else:
			self.service_types = self.service_types_radio
			if currentConfigSelectionElement(config.usage.multibouquet) == "yes":
				self.bouquet_rootstr = '1:7:1:0:0:0:0:0:0:0:(type == 1) FROM BOUQUET "bouquets.radio" ORDER BY bouquet'
			else:
				self.bouquet_rootstr = '%s FROM BOUQUET "userbouquet.favourites.radio" ORDER BY bouquet'%(self.service_types)
		self.bouquet_root = eServiceReference(self.bouquet_rootstr)

	def setTvMode(self):
		title = self.instance.getTitle()
		pos = title.find(" (")
		if pos != -1:
			title = title[:pos]
		title += " (TV)"
		self.instance.setTitle(title)
		self.mode = MODE_TV
		self.recallBouquetMode()

	def setRadioMode(self):
		title = self.instance.getTitle()
		pos = title.find(" (")
		if pos != -1:
			title = title[:pos]
		title += " (Radio)"
		self.instance.setTitle(title)
		self.mode = MODE_RADIO
		self.recallBouquetMode()

	def setRoot(self, root, justSet=False):
		path = root.getPath()
		inBouquetRootList = path.find('FROM BOUQUET "bouquets.') != -1 #FIXME HACK
		pos = path.find(' FROM BOUQUET')
		isBouquet = pos != -1
		if not inBouquetRootList and isBouquet:
			self.servicelist.setMode(ServiceList.MODE_FAVOURITES)
			self.servicelist.setNumberOffset(self.getBouquetNumOffset(root))
			refstr = self.service_types + path[pos:]
			root = eServiceReference(refstr)
		else:
			self.servicelist.setMode(ServiceList.MODE_NORMAL)
		self.servicelist.setRoot(root, justSet)

	def moveUp(self):
		self.servicelist.moveUp()

	def moveDown(self):
		self.servicelist.moveDown()

	def clearPath(self):
		if self.mode == MODE_RADIO:
			self.servicePathRadio = [ ]
		else:
			self.servicePathTV = [ ]

	def enterPath(self, ref, justSet=False):
		if self.mode == MODE_RADIO:
			self.servicePathRadio.append(ref)
		else:
			self.servicePathTV.append(ref)
		self.setRoot(ref, justSet)

	def pathUp(self, justSet=False):
		if self.mode == MODE_TV:
			prev = self.servicePathTV.pop()
			length = len(self.servicePathTV)
			if length:
				current = self.servicePathTV[length-1]
		else:
			prev = self.servicePathRadio.pop()
			length = len(self.servicePathRadio)
			if length:
				current = self.servicePathRadio[length-1]
		self.setRoot(current, justSet)
		if not justSet:
			self.setCurrentSelection(prev)
		return prev

	def isBasePathEqual(self, ref):
		if self.mode == MODE_RADIO and len(self.servicePathRadio) > 1 and self.servicePathRadio[0] == ref:
			return True
		elif self.mode == MODE_TV and len(self.servicePathTV) > 1 and self.servicePathTV[0] == ref:
			return True
		return False

	def isPrevPathEqual(self, ref):
		path = self.servicePathRadio
		if self.mode == MODE_TV:
			path = self.servicePathTV
		length = len(path)
		if length > 1 and path[length-2] == ref:
			return True
		return False

	def preEnterPath(self, refstr):
		return False

	def showAllServices(self):
		if not self.pathChangedDisabled:
			refstr = '%s ORDER BY name'%(self.service_types)
			if not self.preEnterPath(refstr):
				ref = eServiceReference(refstr)
				currentRoot = self.getRoot()
				if currentRoot is None or currentRoot != ref:
					self.clearPath()
					self.enterPath(ref)

	def showSatellites(self):
		if not self.pathChangedDisabled:
			refstr = '%s FROM SATELLITES ORDER BY satellitePosition'%(self.service_types)
			if not self.preEnterPath(refstr):
				ref = eServiceReference(refstr)
				justSet=False
				prev = None

				if self.isBasePathEqual(ref):
					if self.isPrevPathEqual(ref):
						justSet=True
					prev = self.pathUp(justSet)
				else:
					currentRoot = self.getRoot()
					if currentRoot is None or currentRoot != ref:
						justSet=True
						self.clearPath()
						self.enterPath(ref, True)
				if justSet:
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
							if prev is not None:
								self.setCurrentSelection(prev)

	def showProviders(self):
		if not self.pathChangedDisabled:
			refstr = '%s FROM PROVIDERS ORDER BY name'%(self.service_types)
			if not self.preEnterPath(refstr):
				ref = eServiceReference(refstr)
				if self.isBasePathEqual(ref):
					self.pathUp()
				else:
					currentRoot = self.getRoot()
					if currentRoot is None or currentRoot != ref:
						self.clearPath()
						self.enterPath(ref)

	def changeBouquet(self, direction):
		if not self.pathChangedDisabled:
			if self.isBasePathEqual(self.bouquet_root):
				self.pathUp()
				if direction < 0:
					self.moveUp()
				else:
					self.moveDown()
				ref = self.getCurrentSelection()
				self.enterPath(ref)

	def nextBouquet(self):
		self.changeBouquet(+1)

	def prevBouquet(self):
		self.changeBouquet(-1)

	def showFavourites(self):
		if not self.pathChangedDisabled:
			if not self.preEnterPath(self.bouquet_rootstr):
				if self.isBasePathEqual(self.bouquet_root):
					self.pathUp()
				else:
					currentRoot = self.getRoot()
					if currentRoot is None or currentRoot != self.bouquet_root:
						self.clearPath()
						self.enterPath(self.bouquet_root)

	def keyNumberGlobal(self, number):
		char = self.numericalTextInput.getKey(number)
		self.servicelist.moveToChar(char)

	def getRoot(self):
		return self.servicelist.getRoot()

	def getCurrentSelection(self):
		return self.servicelist.getCurrent()

	def setCurrentSelection(self, service):
		servicepath = service.getPath()
		pos = servicepath.find(" FROM BOUQUET")
		if pos != -1:
			if self.mode == MODE_TV:
				servicepath = '(type == 1)' + servicepath[pos:]
			else:
				servicepath = '(type == 2)' + servicepath[pos:]
			service.setPath(servicepath)
		self.servicelist.setCurrent(service)

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

class ChannelSelection(ChannelSelectionBase, ChannelSelectionEdit, ChannelSelectionEPG):
	def __init__(self, session):
		ChannelSelectionBase.__init__(self,session)
		ChannelSelectionEdit.__init__(self)
		ChannelSelectionEPG.__init__(self)

		#config for lastservice
		config.tv = ConfigSubsection();
		config.tv.lastservice = configElement("config.tv.lastservice", configText, "", 0);
		config.tv.lastroot = configElement("config.tv.lastroot", configText, "", 0);
		config.tv.prevservice = configElement("config.tv.prevservice", configText, "", 0);
		config.tv.prevroot = configElement("config.tv.prevroot", configText, "", 0);

		self["actions"] = ActionMap(["OkCancelActions"],
			{
				"cancel": self.cancel,
				"ok": self.channelSelected,
			})
		self.onShown.append(self.__onShown)

		self.lastChannelRootTimer = eTimer()
		self.lastChannelRootTimer.timeout.get().append(self.__onCreate)
		self.lastChannelRootTimer.start(100,True)

	def __onCreate(self):
		self.setTvMode()
		self.servicePathTV = [ ]
		self.restoreRoot()
		lastservice=eServiceReference(config.tv.lastservice.value)
		if lastservice.valid():
			self.setCurrentSelection(lastservice)
			self.session.nav.playService(lastservice)

	def __onShown(self):
		self.recallBouquetMode()
		ref = self.session.nav.getCurrentlyPlayingServiceReference()
		if ref is not None and ref.valid() and ref.getPath() == "":
			self.servicelist.setPlayableIgnoreService(ref)
		else:
			self.servicelist.setPlayableIgnoreService(eServiceReference())

	def channelSelected(self):
		ref = self.getCurrentSelection()
		if self.movemode:
			self.toggleMoveMarked()
		elif (ref.flags & 7) == 7:
			self.enterPath(ref)
		elif self.bouquet_mark_edit:
			self.doMark()
		else:
			self.zap()
			self.close(ref)

	#called from infoBar and channelSelected
	def zap(self):
		ref = self.session.nav.getCurrentlyPlayingServiceReference()
		if ref is None or ref != self.getCurrentSelection():
			self.session.nav.playService(self.getCurrentSelection())
		self.saveRoot()
		self.saveChannel()

	def saveRoot(self):
		path = ''
		for i in self.servicePathTV:
			path += i.toString()
			path += ';'
		if config.tv.prevroot.value != config.tv.lastroot.value:
			config.tv.prevroot.value = config.tv.lastroot.value
			config.tv.prevroot.save()
		if len(path) and path != config.tv.lastroot.value:
			config.tv.lastroot.value = path
			config.tv.lastroot.save()

	def restoreRoot(self):
		self.servicePathTV = [ ]
		re = compile('.+?;')
		tmp = re.findall(config.tv.lastroot.value)
		cnt = 0
		for i in tmp:
			self.servicePathTV.append(eServiceReference(i[:len(i)-1]))
			cnt += 1
		if cnt:
			path = self.servicePathTV.pop()
			self.enterPath(path)
		else:
			self.showFavourites()
			self.saveRoot()

	def preEnterPath(self, refstr):
		if len(self.servicePathTV) and self.servicePathTV[0] != eServiceReference(refstr):
			pathstr = config.tv.lastroot.value
			if pathstr is not None and pathstr.find(refstr) == 0:
				self.restoreRoot()
				lastservice=eServiceReference(config.tv.lastservice.value)
				if lastservice is not None:
					self.setCurrentSelection(lastservice)
				return True
		return False

	def saveChannel(self):
		ref = self.session.nav.getCurrentlyPlayingServiceReference()
		if ref is not None:
			refstr = ref.toString()
		else:
			refstr = ""
		if refstr != config.tv.lastservice.value:
			config.tv.prevservice.value = config.tv.lastservice.value
			config.tv.prevservice.save()
			config.tv.lastservice.value = refstr
			config.tv.lastservice.save()

	def recallPrevService(self):
		if len(config.tv.prevservice.value) and len(config.tv.prevroot.value):
			if config.tv.lastroot.value != config.tv.prevroot.value:
				tmp = config.tv.lastroot.value
				config.tv.lastroot.value = config.tv.prevroot.value
				config.tv.lastroot.save()
				config.tv.prevroot.value = tmp
				config.tv.prevroot.save()
				self.restoreRoot()
			if config.tv.lastservice.value != config.tv.prevservice.value:
				tmp = config.tv.lastservice.value
				config.tv.lastservice.value = config.tv.prevservice.value
				config.tv.lastservice.save()
				config.tv.prevservice.value = tmp
				config.tv.prevservice.save()
				lastservice=eServiceReference(config.tv.lastservice.value)
				self.session.nav.playService(lastservice)
				self.setCurrentSelection(lastservice)

	def cancel(self):
		self.close(None)
		self.restoreRoot()
		lastservice=eServiceReference(config.tv.lastservice.value)
		if lastservice.valid() and self.getCurrentSelection() != lastservice:
			self.setCurrentSelection(lastservice)

from Screens.InfoBarGenerics import InfoBarEvent, InfoBarServiceName, InfoBarInstantRecord

class RadioInfoBar(Screen, InfoBarEvent, InfoBarServiceName, InfoBarInstantRecord):
	def __init__(self, session):
		Screen.__init__(self, session)
		InfoBarEvent.__init__(self)
		InfoBarServiceName.__init__(self)
		InfoBarInstantRecord.__init__(self)
		self["Clock"] = Clock()

class ChannelSelectionRadio(ChannelSelectionBase, ChannelSelectionEdit, ChannelSelectionEPG):
	def __init__(self, session):
		ChannelSelectionBase.__init__(self, session)
		ChannelSelectionEdit.__init__(self)
		ChannelSelectionEPG.__init__(self)

		config.radio = ConfigSubsection();
		config.radio.lastservice = configElement("config.radio.lastservice", configText, "", 0);
		config.radio.lastroot = configElement("config.radio.lastroot", configText, "", 0);
		self.onLayoutFinish.append(self.onCreate)

		self.info = session.instantiateDialog(RadioInfoBar)

		self["actions"] = ActionMap(["OkCancelActions", "TvRadioActions"],
			{
				"keyTV": self.closeRadio,
				"keyRadio": self.closeRadio,
				"cancel": self.closeRadio,
				"ok": self.channelSelected,
			})

	def saveRoot(self):
		path = ''
		for i in self.servicePathRadio:
			path += i.toString()
			path += ';'
		if len(path) and path != config.radio.lastroot.value:
			config.radio.lastroot.value = path
			config.radio.lastroot.save()

	def restoreRoot(self):
		self.servicePathRadio = [ ]
		re = compile('.+?;')
		tmp = re.findall(config.radio.lastroot.value)
		cnt = 0
		for i in tmp:
			self.servicePathRadio.append(eServiceReference(i[:len(i)-1]))
			cnt += 1
		if cnt:
			path = self.servicePathRadio.pop()
			self.enterPath(path)
		else:
			self.showFavourites()
			self.saveRoot()

	def preEnterPath(self, refstr):
		if len(self.servicePathRadio) and self.servicePathRadio[0] != eServiceReference(refstr):
			pathstr = config.radio.lastroot.value
			if pathstr is not None and pathstr.find(refstr) == 0:
				self.restoreRoot()
				lastservice=eServiceReference(config.radio.lastservice.value)
				if lastservice is not None:
					self.setCurrentSelection(lastservice)
				return True
		return False

	def onCreate(self):
		self.setRadioMode()
		self.restoreRoot()
		lastservice=eServiceReference(config.radio.lastservice.value)
		if lastservice.valid():
			self.servicelist.setCurrent(lastservice)
			self.session.nav.playService(lastservice)
			self.servicelist.setPlayableIgnoreService(lastservice)
		self.info.show()

	def channelSelected(self): # just return selected service
		ref = self.getCurrentSelection()
		if self.movemode:
			self.toggleMoveMarked()
		elif (ref.flags & 7) == 7:
			self.enterPath(ref)
		elif self.bouquet_mark_edit:
			self.doMark()
		else:
			playingref = self.session.nav.getCurrentlyPlayingServiceReference()
			if playingref is None or playingref != ref:
				self.session.nav.playService(ref)
				self.servicelist.setPlayableIgnoreService(ref)
				config.radio.lastservice.value = ref.toString()
				config.radio.lastservice.save()
			self.saveRoot()

	def closeRadio(self):
		self.info.hide()
		#set previous tv service
		lastservice=eServiceReference(config.tv.lastservice.value)
		self.session.nav.playService(lastservice)
		self.close(None)

class SimpleChannelSelection(ChannelSelectionBase):
	def __init__(self, session, title):
		ChannelSelectionBase.__init__(self, session)
		self.title = title
		self.onShown.append(self.__onExecCallback)

		self["actions"] = ActionMap(["OkCancelActions", "TvRadioActions"],
			{
				"cancel": self.cancel,
				"ok": self.channelSelected,
				"keyRadio": self.setModeRadio,
				"keyTV": self.setModeTv,
			})

	def __onExecCallback(self):
		self.session.currentDialog.instance.setTitle(self.title)
		self.setModeTv()

	def channelSelected(self): # just return selected service
		ref = self.getCurrentSelection()
		if (ref.flags & 7) == 7:
			self.enterPath(ref)
		else:
			ref = self.getCurrentSelection()
			self.close(ref)

	def setModeTv(self):
		self.setTvMode()
		self.showFavourites()

	def setModeRadio(self):
		self.setRadioMode()
		self.showFavourites()
