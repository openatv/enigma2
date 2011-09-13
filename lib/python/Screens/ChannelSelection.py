from Tools.Profile import profile

from Screen import Screen
from Components.Button import Button
from Components.ServiceList import ServiceList
from Components.ActionMap import NumberActionMap, ActionMap, HelpableActionMap
from Components.MenuList import MenuList
from Components.ServiceEventTracker import ServiceEventTracker, InfoBarBase
profile("ChannelSelection.py 1")
from EpgSelection import EPGSelection
from enigma import eServiceReference, eEPGCache, eServiceCenter, eRCInput, eTimer, eDVBDB, iPlayableService, iServiceInformation, getPrevAsciiCode, eEnv
from Components.config import config, ConfigSubsection, ConfigText
from Tools.NumericalTextInput import NumericalTextInput
profile("ChannelSelection.py 2")
from Components.NimManager import nimmanager
profile("ChannelSelection.py 2.1")
from Components.Sources.RdsDecoder import RdsDecoder
profile("ChannelSelection.py 2.2")
from Components.Sources.ServiceEvent import ServiceEvent
profile("ChannelSelection.py 2.3")
from Components.Input import Input
profile("ChannelSelection.py 3")
from Components.ChoiceList import ChoiceList, ChoiceEntryComponent
from Components.SystemInfo import SystemInfo
from Screens.InputBox import InputBox, PinInput
from Screens.MessageBox import MessageBox
from Screens.ServiceInfo import ServiceInfo
profile("ChannelSelection.py 4")
from Screens.PictureInPicture import PictureInPicture
from Screens.RdsDisplay import RassInteractive
from ServiceReference import ServiceReference
from Tools.BoundFunction import boundFunction
from os import remove
profile("ChannelSelection.py after imports")

FLAG_SERVICE_NEW_FOUND = 64 #define in lib/dvb/idvb.h as dxNewFound = 64

class BouquetSelector(Screen):
	def __init__(self, session, bouquets, selectedFunc, enableWrapAround=False):
		Screen.__init__(self, session)

		self.selectedFunc=selectedFunc

		self["actions"] = ActionMap(["OkCancelActions"],
			{
				"ok": self.okbuttonClick,
				"cancel": self.cancelClick
			})
		entrys = [ (x[0], x[1]) for x in bouquets ]
		self["menu"] = MenuList(entrys, enableWrapAround)

	def getCurrent(self):
		cur = self["menu"].getCurrent()
		return cur and cur[1]

	def okbuttonClick(self):
		self.selectedFunc(self.getCurrent())

	def up(self):
		self["menu"].up()

	def down(self):
		self["menu"].down()

	def cancelClick(self):
		self.close(False)

class SilentBouquetSelector:
	def __init__(self, bouquets, enableWrapAround=False, current=0):
		self.bouquets = [b[1] for b in bouquets]
		self.pos = current
		self.count = len(bouquets)
		self.enableWrapAround = enableWrapAround

	def up(self):
		if self.pos > 0 or self.enableWrapAround:
			self.pos = (self.pos - 1) % self.count

	def down(self):
		if self.pos < (self.count - 1) or self.enableWrapAround:
			self.pos = (self.pos + 1) % self.count

	def getCurrent(self):
		return self.bouquets[self.pos]

# csel.bouquet_mark_edit values
OFF = 0
EDIT_BOUQUET = 1
EDIT_ALTERNATIVES = 2

def append_when_current_valid(current, menu, args, level = 0, key = ""):
	if current and current.valid() and level <= config.usage.setup_level.index:
		menu.append(ChoiceEntryComponent(key, args))

class ChannelContextMenu(Screen):
	def __init__(self, session, csel):

		Screen.__init__(self, session)
		#raise Exception("we need a better summary screen here")
		self.csel = csel
		self.bsel = None

		self["actions"] = ActionMap(["OkCancelActions", "ColorActions", "NumberActions"],
			{
				"ok": self.okbuttonClick,
				"cancel": self.cancelClick,
				"blue": self.showServiceInPiP
			})
		menu = [ ]

		self.pipAvailable = False
		current = csel.getCurrentSelection()
		current_root = csel.getRoot()
		current_sel_path = current.getPath()
		current_sel_flags = current.flags
		inBouquetRootList = current_root and current_root.getPath().find('FROM BOUQUET "bouquets.') != -1 #FIXME HACK
		inBouquet = csel.getMutableList() is not None
		haveBouquets = config.usage.multibouquet.value

		if not (current_sel_path or current_sel_flags & (eServiceReference.isDirectory|eServiceReference.isMarker)):
			append_when_current_valid(current, menu, (_("show transponder info"), self.showServiceInformations), level = 2)
		if csel.bouquet_mark_edit == OFF and not csel.movemode:
			if not inBouquetRootList:
				isPlayable = not (current_sel_flags & (eServiceReference.isMarker|eServiceReference.isDirectory))
				if isPlayable:
					if config.ParentalControl.configured.value:
						from Components.ParentalControl import parentalControl
						if parentalControl.getProtectionLevel(csel.getCurrentSelection().toCompareString()) == -1:
							append_when_current_valid(current, menu, (_("add to parental protection"), boundFunction(self.addParentalProtection, csel.getCurrentSelection())), level = 0)
						else:
							append_when_current_valid(current, menu, (_("remove from parental protection"), boundFunction(self.removeParentalProtection, csel.getCurrentSelection())), level = 0)
					if haveBouquets:
						bouquets = self.csel.getBouquetList()
						if bouquets is None:
							bouquetCnt = 0
						else:
							bouquetCnt = len(bouquets)
						if not inBouquet or bouquetCnt > 1:
							append_when_current_valid(current, menu, (_("add service to bouquet"), self.addServiceToBouquetSelected), level = 0)
					else:
						if not inBouquet:
							append_when_current_valid(current, menu, (_("add service to favourites"), self.addServiceToBouquetSelected), level = 0)
				else:
					if current_root.getPath().find('FROM SATELLITES') != -1:
						append_when_current_valid(current, menu, (_("remove selected satellite"), self.removeSatelliteServices), level = 0)
					if haveBouquets:
						if not inBouquet and current_sel_path.find("PROVIDERS") == -1:
							append_when_current_valid(current, menu, (_("copy to bouquets"), self.copyCurrentToBouquetList), level = 0)
					if current_sel_path.find("flags == %d" %(FLAG_SERVICE_NEW_FOUND)) != -1:
						append_when_current_valid(current, menu, (_("remove all new found flags"), self.removeAllNewFoundFlags), level = 0)
				if inBouquet:
					append_when_current_valid(current, menu, (_("remove entry"), self.removeCurrentService), level = 0)
				if current_root and current_root.getPath().find("flags == %d" %(FLAG_SERVICE_NEW_FOUND)) != -1:
					append_when_current_valid(current, menu, (_("remove new found flag"), self.removeNewFoundFlag), level = 0)
				if isPlayable and SystemInfo.get("NumVideoDecoders", 1) > 1:
					append_when_current_valid(current, menu, (_("Activate Picture in Picture"), self.showServiceInPiP), level = 0, key = "blue")
					self.pipAvailable = True
			else:
					menu.append(ChoiceEntryComponent(text = (_("add bouquet"), self.showBouquetInputBox)))
					append_when_current_valid(current, menu, (_("remove entry"), self.removeBouquet), level = 0)

		if inBouquet: # current list is editable?
			if csel.bouquet_mark_edit == OFF:
				if not csel.movemode:
					append_when_current_valid(current, menu, (_("enable move mode"), self.toggleMoveMode), level = 1)
					if not inBouquetRootList and current_root and not (current_root.flags & eServiceReference.isGroup):
						menu.append(ChoiceEntryComponent(text = (_("add marker"), self.showMarkerInputBox)))
						if haveBouquets:
							append_when_current_valid(current, menu, (_("enable bouquet edit"), self.bouquetMarkStart), level = 0)
						else:
							append_when_current_valid(current, menu, (_("enable favourite edit"), self.bouquetMarkStart), level = 0)
						if current_sel_flags & eServiceReference.isGroup:
							append_when_current_valid(current, menu, (_("edit alternatives"), self.editAlternativeServices), level = 2)
							append_when_current_valid(current, menu, (_("show alternatives"), self.showAlternativeServices), level = 2)
							append_when_current_valid(current, menu, (_("remove all alternatives"), self.removeAlternativeServices), level = 2)
						elif not current_sel_flags & eServiceReference.isMarker:
							append_when_current_valid(current, menu, (_("add alternatives"), self.addAlternativeServices), level = 2)
				else:
					append_when_current_valid(current, menu, (_("disable move mode"), self.toggleMoveMode), level = 0)
			else:
				if csel.bouquet_mark_edit == EDIT_BOUQUET:
					if haveBouquets:
						append_when_current_valid(current, menu, (_("end bouquet edit"), self.bouquetMarkEnd), level = 0)
						append_when_current_valid(current, menu, (_("abort bouquet edit"), self.bouquetMarkAbort), level = 0)
					else:
						append_when_current_valid(current, menu, (_("end favourites edit"), self.bouquetMarkEnd), level = 0)
						append_when_current_valid(current, menu, (_("abort favourites edit"), self.bouquetMarkAbort), level = 0)
				else:
						append_when_current_valid(current, menu, (_("end alternatives edit"), self.bouquetMarkEnd), level = 0)
						append_when_current_valid(current, menu, (_("abort alternatives edit"), self.bouquetMarkAbort), level = 0)

		menu.append(ChoiceEntryComponent(text = (_("back"), self.cancelClick)))
		self["menu"] = ChoiceList(menu)

	def okbuttonClick(self):
		self["menu"].getCurrent()[0][1]()

	def cancelClick(self):
		self.close(False)

	def showServiceInformations(self):
		self.session.open( ServiceInfo, self.csel.getCurrentSelection() )

	def showBouquetInputBox(self):
		self.session.openWithCallback(self.bouquetInputCallback, InputBox, title=_("Please enter a name for the new bouquet"), text="bouquetname", maxSize=False, visible_width = 56, type=Input.TEXT)

	def bouquetInputCallback(self, bouquet):
		if bouquet is not None:
			self.csel.addBouquet(bouquet, None)
		self.close()

	def addParentalProtection(self, service):
		from Components.ParentalControl import parentalControl
		parentalControl.protectService(service.toCompareString())
		self.close()

	def removeParentalProtection(self, service):
		self.session.openWithCallback(boundFunction(self.pinEntered, service.toCompareString()), PinInput, pinList = [config.ParentalControl.servicepin[0].value], triesEntry = config.ParentalControl.retries.servicepin, title = _("Enter the service pin"), windowTitle = _("Change pin code"))

	def pinEntered(self, service, result):
		if result:
			from Components.ParentalControl import parentalControl
			parentalControl.unProtectService(service)
			self.close()
		else:
			self.session.openWithCallback(self.close, MessageBox, _("The pin code you entered is wrong."), MessageBox.TYPE_ERROR)
			
	def showServiceInPiP(self):
		if not self.pipAvailable:
			return
		if self.session.pipshown:
			del self.session.pip
		self.session.pip = self.session.instantiateDialog(PictureInPicture)
		self.session.pip.show()
		newservice = self.csel.servicelist.getCurrent()
		if self.session.pip.playService(newservice):
			self.session.pipshown = True
			self.session.pip.servicePath = self.csel.getCurrentServicePath()
			self.close(True)
		else:
			self.session.pipshown = False
			del self.session.pip
			self.session.openWithCallback(self.close, MessageBox, _("Could not open Picture in Picture"), MessageBox.TYPE_ERROR)

	def addServiceToBouquetSelected(self):
		bouquets = self.csel.getBouquetList()
		if bouquets is None:
			cnt = 0
		else:
			cnt = len(bouquets)
		if cnt > 1: # show bouquet list
			self.bsel = self.session.openWithCallback(self.bouquetSelClosed, BouquetSelector, bouquets, self.addCurrentServiceToBouquet)
		elif cnt == 1: # add to only one existing bouquet
			self.addCurrentServiceToBouquet(bouquets[0][1], closeBouquetSelection = False)

	def bouquetSelClosed(self, recursive):
		self.bsel = None
		if recursive:
			self.close(False)

	def removeSatelliteServices(self):
		curpath = self.csel.getCurrentSelection().getPath()
		idx = curpath.find("satellitePosition == ")
		if idx != -1:
			tmp = curpath[idx+21:]
			idx = tmp.find(')')
			if idx != -1:
				satpos = int(tmp[:idx])
				eDVBDB.getInstance().removeServices(-1, -1, -1, satpos)
		self.close()

	def copyCurrentToBouquetList(self):
		self.csel.copyCurrentToBouquetList()
		self.close()

	def removeBouquet(self):
		self.csel.removeBouquet()
		self.close()

	def showMarkerInputBox(self):
		self.session.openWithCallback(self.markerInputCallback, InputBox, title=_("Please enter a name for the new marker"), text="markername", maxSize=False, visible_width = 56, type=Input.TEXT)

	def markerInputCallback(self, marker):
		if marker is not None:
			self.csel.addMarker(marker)
		self.close()

	def addCurrentServiceToBouquet(self, dest, closeBouquetSelection = True):
		self.csel.addServiceToBouquet(dest)
		if self.bsel is not None:
			self.bsel.close(True)
		else:
			self.close(closeBouquetSelection) # close bouquet selection

	def removeCurrentService(self):
		self.csel.removeCurrentService()
		self.close()

	def toggleMoveMode(self):
		self.csel.toggleMoveMode()
		self.close()

	def bouquetMarkStart(self):
		self.csel.startMarkedEdit(EDIT_BOUQUET)
		self.close()

	def bouquetMarkEnd(self):
		self.csel.endMarkedEdit(abort=False)
		self.close()

	def bouquetMarkAbort(self):
		self.csel.endMarkedEdit(abort=True)
		self.close()

	def removeNewFoundFlag(self):
		eDVBDB.getInstance().removeFlag(self.csel.getCurrentSelection(), FLAG_SERVICE_NEW_FOUND)
		self.close()

	def removeAllNewFoundFlags(self):
		curpath = self.csel.getCurrentSelection().getPath()
		idx = curpath.find("satellitePosition == ")
		if idx != -1:
			tmp = curpath[idx+21:]
			idx = tmp.find(')')
			if idx != -1:
				satpos = int(tmp[:idx])
				eDVBDB.getInstance().removeFlags(FLAG_SERVICE_NEW_FOUND, -1, -1, -1, satpos)
		self.close()

	def editAlternativeServices(self):
		self.csel.startMarkedEdit(EDIT_ALTERNATIVES)
		self.close()

	def showAlternativeServices(self):
		self.csel.enterPath(self.csel.getCurrentSelection())
		self.close()

	def removeAlternativeServices(self):
		self.csel.removeAlternativeServices()
		self.close()

	def addAlternativeServices(self):
		self.csel.addAlternativeServices()
		self.csel.startMarkedEdit(EDIT_ALTERNATIVES)
		self.close()

class SelectionEventInfo:
	def __init__(self):
		self["ServiceEvent"] = ServiceEvent()
		self.servicelist.connectSelChanged(self.__selectionChanged)
		self.timer = eTimer()
		self.timer.callback.append(self.updateEventInfo)
		self.onShown.append(self.__selectionChanged)

	def __selectionChanged(self):
		if self.execing:
			self.timer.start(100, True)

	def updateEventInfo(self):
		cur = self.getCurrentSelection()
		self["ServiceEvent"].newService(cur)

class ChannelSelectionEPG:
	def __init__(self):
		self["ChannelSelectEPGActions"] = ActionMap(["ChannelSelectEPGActions"],
			{
				"showEPGList": self.showEPGList,
			})

	def showEPGList(self):
		ref=self.getCurrentSelection()
		if ref:
			self.savedService = ref
			self.session.openWithCallback(self.SingleServiceEPGClosed, EPGSelection, ref, serviceChangeCB=self.changeServiceCB)

	def SingleServiceEPGClosed(self, ret=False):
		self.setCurrentSelection(self.savedService)

	def changeServiceCB(self, direction, epg):
		beg = self.getCurrentSelection()
		while True:
			if direction > 0:
				self.moveDown()
			else:
				self.moveUp()
			cur = self.getCurrentSelection()
			if cur == beg or not (cur.flags & eServiceReference.isMarker):
				break
		epg.setService(ServiceReference(self.getCurrentSelection()))

class ChannelSelectionEdit:
	def __init__(self):
		self.entry_marked = False
		self.movemode = False
		self.bouquet_mark_edit = OFF
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
					return 0 # fall-trough
				elif action == "ok":
					return 0 # fall-trough
				else:
					return ActionMap.action(self, contexts, action)

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
		list = root and serviceHandler.list(root)
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

	def addMarker(self, name):
		current = self.servicelist.getCurrent()
		mutableList = self.getMutableList()
		cnt = 0
		while mutableList:
			str = '1:64:%d:0:0:0:0:0:0:0::%s'%(cnt, name)
			ref = eServiceReference(str)
			if current and current.valid():
				if not mutableList.addService(ref, current):
					self.servicelist.addService(ref, True)
					mutableList.flushChanges()
					break
			elif not mutableList.addService(ref):
				self.servicelist.addService(ref, True)
				mutableList.flushChanges()
				break
			cnt+=1

	def addAlternativeServices(self):
		cur_service = ServiceReference(self.getCurrentSelection())
		root = self.getRoot()
		cur_root = root and ServiceReference(root)
		mutableBouquet = cur_root.list().startEdit()
		if mutableBouquet:
			name = cur_service.getServiceName()
			print "NAME", name
			if self.mode == MODE_TV:
				str = '1:134:1:0:0:0:0:0:0:0:FROM BOUQUET \"alternatives.%s.tv\" ORDER BY bouquet'%(self.buildBouquetID(name))
			else:
				str = '1:134:2:0:0:0:0:0:0:0:FROM BOUQUET \"alternatives.%s.radio\" ORDER BY bouquet'%(self.buildBouquetID(name))
			new_ref = ServiceReference(str)
			if not mutableBouquet.addService(new_ref.ref, cur_service.ref):
				mutableBouquet.removeService(cur_service.ref)
				mutableBouquet.flushChanges()
				eDVBDB.getInstance().reloadBouquets()
				mutableAlternatives = new_ref.list().startEdit()
				if mutableAlternatives:
					mutableAlternatives.setListName(name)
					if mutableAlternatives.addService(cur_service.ref):
						print "add", cur_service.ref.toString(), "to new alternatives failed"
					mutableAlternatives.flushChanges()
					self.servicelist.addService(new_ref.ref, True)
					self.servicelist.removeCurrent()
					self.servicelist.moveUp()
				else:
					print "get mutable list for new created alternatives failed"
			else:
				print "add", str, "to", cur_root.getServiceName(), "failed"
		else:
			print "bouquetlist is not editable"

	def addBouquet(self, bName, services):
		serviceHandler = eServiceCenter.getInstance()
		mutableBouquetList = serviceHandler.list(self.bouquet_root).startEdit()
		if mutableBouquetList:
			if self.mode == MODE_TV:
				bName += " (TV)"
				str = '1:7:1:0:0:0:0:0:0:0:FROM BOUQUET \"userbouquet.%s.tv\" ORDER BY bouquet'%(self.buildBouquetID(bName))
			else:
				bName += " (Radio)"
				str = '1:7:2:0:0:0:0:0:0:0:FROM BOUQUET \"userbouquet.%s.radio\" ORDER BY bouquet'%(self.buildBouquetID(bName))
			new_bouquet_ref = eServiceReference(str)
			if not mutableBouquetList.addService(new_bouquet_ref):
				mutableBouquetList.flushChanges()
				eDVBDB.getInstance().reloadBouquets()
				mutableBouquet = serviceHandler.list(new_bouquet_ref).startEdit()
				if mutableBouquet:
					mutableBouquet.setListName(bName)
					if services is not None:
						for service in services:
							if mutableBouquet.addService(service):
								print "add", service.toString(), "to new bouquet failed"
					mutableBouquet.flushChanges()
				else:
					print "get mutable list for new created bouquet failed"
				# do some voodoo to check if current_root is equal to bouquet_root
				cur_root = self.getRoot();
				str1 = cur_root and cur_root.toString()
				pos1 = str1 and str1.find("FROM BOUQUET") or -1
				pos2 = self.bouquet_rootstr.find("FROM BOUQUET")
				if pos1 != -1 and pos2 != -1 and str1[pos1:] == self.bouquet_rootstr[pos2:]:
					self.servicelist.addService(new_bouquet_ref)
			else:
				print "add", str, "to bouquets failed"
		else:
			print "bouquetlist is not editable"

	def copyCurrentToBouquetList(self):
		provider = ServiceReference(self.getCurrentSelection())
		providerName = provider.getServiceName()
		serviceHandler = eServiceCenter.getInstance()
		services = serviceHandler.list(provider.ref)
		self.addBouquet(providerName, services and services.getContent('R', True))

	def removeAlternativeServices(self):
		cur_service = ServiceReference(self.getCurrentSelection())
		root = self.getRoot()
		cur_root = root and ServiceReference(root)
		list = cur_service.list()
		first_in_alternative = list and list.getNext()
		if first_in_alternative:
			edit_root = cur_root and cur_root.list().startEdit()
			if edit_root:
				if not edit_root.addService(first_in_alternative, cur_service.ref):
					self.servicelist.addService(first_in_alternative, True)
				else:
					print "couldn't add first alternative service to current root"
			else:
				print "couldn't edit current root!!"
		else:
			print "remove empty alternative list !!"
		self.removeBouquet()
		self.servicelist.moveUp()

	def removeBouquet(self):
		refstr = self.getCurrentSelection().toString()
		print "removeBouquet", refstr
		self.bouquetNumOffsetCache = { }
		pos = refstr.find('FROM BOUQUET "')
		filename = None
		if pos != -1:
			refstr = refstr[pos+14:]
			pos = refstr.find('"')
			if pos != -1:
				filename = eEnv.resolve('${sysconfdir}/enigma2/') + refstr[:pos]
		self.removeCurrentService()
		try:
			if filename is not None:
				remove(filename)
		except OSError:
			print "error during remove of", filename

#  multiple marked entry stuff ( edit mode, later multiepg selection )
	def startMarkedEdit(self, type):
		self.savedPath = self.servicePath[:]
		if type == EDIT_ALTERNATIVES:
			self.enterPath(self.getCurrentSelection())
		self.mutableList = self.getMutableList()
		# add all services from the current list to internal marked set in listboxservicecontent
		self.clearMarks() # this clears the internal marked set in the listboxservicecontent
		self.saved_title = self.getTitle()
		pos = self.saved_title.find(')')
		new_title = self.saved_title[:pos+1]
		if type == EDIT_ALTERNATIVES:
			self.bouquet_mark_edit = EDIT_ALTERNATIVES
			new_title += ' ' + _("[alternative edit]")
		else:
			self.bouquet_mark_edit = EDIT_BOUQUET
			if config.usage.multibouquet.value:
				new_title += ' ' + _("[bouquet edit]")
			else:
				new_title += ' ' + _("[favourite edit]")
		self.setTitle(new_title)
		self.__marked = self.servicelist.getRootServices()
		for x in self.__marked:
			self.servicelist.addMarked(eServiceReference(x))
		self.showAllServices()

	def endMarkedEdit(self, abort):
		if not abort and self.mutableList is not None:
			self.bouquetNumOffsetCache = { }
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
		self.bouquet_mark_edit = OFF
		self.mutableList = None
		self.setTitle(self.saved_title)
		self.saved_title = None
		# self.servicePath is just a reference to servicePathTv or Radio...
		# so we never ever do use the asignment operator in self.servicePath
		del self.servicePath[:] # remove all elements
		self.servicePath += self.savedPath # add saved elements
		del self.savedPath
		self.setRoot(self.servicePath[-1])

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
				self.bouquetNumOffsetCache = { }
				mutableList.flushChanges() #FIXME dont flush on each single removed service
				self.servicelist.removeCurrent()

	def addServiceToBouquet(self, dest, service=None):
		mutableList = self.getMutableList(dest)
		if not mutableList is None:
			if service is None: #use current selected service
				service = self.servicelist.getCurrent()
			if not mutableList.addService(service):
				self.bouquetNumOffsetCache = { }
				mutableList.flushChanges()
				# do some voodoo to check if current_root is equal to dest
				cur_root = self.getRoot();
				str1 = cur_root and cur_root.toString() or -1
				str2 = dest.toString()
				pos1 = str1.find("FROM BOUQUET")
				pos2 = str2.find("FROM BOUQUET")
				if pos1 != -1 and pos2 != -1 and str1[pos1:] == str2[pos2:]:
					self.servicelist.addService(service)

	def toggleMoveMode(self):
		if self.movemode:
			if self.entry_marked:
				self.toggleMoveMarked() # unmark current entry
			self.movemode = False
			self.pathChangeDisabled = False # re-enable path change
			self.mutableList.flushChanges() # FIXME add check if changes was made
			self.mutableList = None
			self.setTitle(self.saved_title)
			self.saved_title = None
			cur_root = self.getRoot()
			if cur_root and cur_root == self.bouquet_root:
				self.bouquetNumOffsetCache = { }
		else:
			self.mutableList = self.getMutableList()
			self.movemode = True
			self.pathChangeDisabled = True # no path change allowed in movemode
			self.saved_title = self.getTitle()
			new_title = self.saved_title
			pos = self.saved_title.find(')')
			new_title = self.saved_title[:pos+1] + ' ' + _("[move mode]") + self.saved_title[pos+1:]
			self.setTitle(new_title);

	def handleEditCancel(self):
		if self.movemode: #movemode active?
			self.channelSelected() # unmark
			self.toggleMoveMode() # disable move mode
		elif self.bouquet_mark_edit != OFF:
			self.endMarkedEdit(True) # abort edit mode

	def toggleMoveMarked(self):
		if self.entry_marked:
			self.servicelist.setCurrentMarked(False)
			self.entry_marked = False
		else:
			self.servicelist.setCurrentMarked(True)
			self.entry_marked = True

	def doContext(self):
		self.session.openWithCallback(self.exitContext, ChannelContextMenu, self)
		
	def exitContext(self, close = False):
		if close:
			self.cancel()

MODE_TV = 0
MODE_RADIO = 1

# type 1 = digital television service
# type 4 = nvod reference service (NYI)
# type 17 = MPEG-2 HD digital television service
# type 22 = advanced codec SD digital television
# type 24 = advanced codec SD NVOD reference service (NYI)
# type 25 = advanced codec HD digital television
# type 27 = advanced codec HD NVOD reference service (NYI)
# type 2 = digital radio sound service
# type 10 = advanced codec digital radio sound service

service_types_tv = '1:7:1:0:0:0:0:0:0:0:(type == 1) || (type == 17) || (type == 22) || (type == 25) || (type == 134) || (type == 195)'
service_types_radio = '1:7:2:0:0:0:0:0:0:0:(type == 2) || (type == 10)'

class ChannelSelectionBase(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)

		self["key_red"] = Button(_("All"))
		self["key_green"] = Button(_("Satellites"))
		self["key_yellow"] = Button(_("Provider"))
		self["key_blue"] = Button(_("Favourites"))

		self["list"] = ServiceList()
		self.servicelist = self["list"]

		self.numericalTextInput = NumericalTextInput()
		self.numericalTextInput.setUseableChars(u'1234567890ABCDEFGHIJKLMNOPQRSTUVWXYZ')

		self.servicePathTV = [ ]
		self.servicePathRadio = [ ]
		self.servicePath = [ ]
		self.rootChanged = False

		self.mode = MODE_TV

		self.pathChangeDisabled = False

		self.bouquetNumOffsetCache = { }

		self["ChannelSelectBaseActions"] = NumberActionMap(["ChannelSelectBaseActions", "NumberActions", "InputAsciiActions"],
			{
				"showFavourites": self.showFavourites,
				"showAllServices": self.showAllServices,
				"showProviders": self.showProviders,
				"showSatellites": self.showSatellites,
				"nextBouquet": self.nextBouquet,
				"prevBouquet": self.prevBouquet,
				"nextMarker": self.nextMarker,
				"prevMarker": self.prevMarker,
				"gotAsciiCode": self.keyAsciiCode,
				"1": self.keyNumberGlobal,
				"2": self.keyNumberGlobal,
				"3": self.keyNumberGlobal,
				"4": self.keyNumberGlobal,
				"5": self.keyNumberGlobal,
				"6": self.keyNumberGlobal,
				"7": self.keyNumberGlobal,
				"8": self.keyNumberGlobal,
				"9": self.keyNumberGlobal,
				"0": self.keyNumber0
			})
		self.recallBouquetMode()

	def getBouquetNumOffset(self, bouquet):
		if not config.usage.multibouquet.value:
			return 0
		str = bouquet.toString()
		offsetCount = 0
		if not self.bouquetNumOffsetCache.has_key(str):
			serviceHandler = eServiceCenter.getInstance()
			bouquetlist = serviceHandler.list(self.bouquet_root)
			if not bouquetlist is None:
				while True:
					bouquetIterator = bouquetlist.getNext()
					if not bouquetIterator.valid(): #end of list
						break
					self.bouquetNumOffsetCache[bouquetIterator.toString()]=offsetCount
					if not (bouquetIterator.flags & eServiceReference.isDirectory):
						continue
					servicelist = serviceHandler.list(bouquetIterator)
					if not servicelist is None:
						while True:
							serviceIterator = servicelist.getNext()
							if not serviceIterator.valid(): #check if end of list
								break
							playable = not (serviceIterator.flags & (eServiceReference.isDirectory|eServiceReference.isMarker))
							if playable:
								offsetCount += 1
		return self.bouquetNumOffsetCache.get(str, offsetCount)

	def recallBouquetMode(self):
		if self.mode == MODE_TV:
			self.service_types = service_types_tv
			if config.usage.multibouquet.value:
				self.bouquet_rootstr = '1:7:1:0:0:0:0:0:0:0:FROM BOUQUET "bouquets.tv" ORDER BY bouquet'
			else:
				self.bouquet_rootstr = '%s FROM BOUQUET "userbouquet.favourites.tv" ORDER BY bouquet'%(self.service_types)
		else:
			self.service_types = service_types_radio
			if config.usage.multibouquet.value:
				self.bouquet_rootstr = '1:7:1:0:0:0:0:0:0:0:FROM BOUQUET "bouquets.radio" ORDER BY bouquet'
			else:
				self.bouquet_rootstr = '%s FROM BOUQUET "userbouquet.favourites.radio" ORDER BY bouquet'%(self.service_types)
		self.bouquet_root = eServiceReference(self.bouquet_rootstr)

	def setTvMode(self):
		self.mode = MODE_TV
		self.servicePath = self.servicePathTV
		self.recallBouquetMode()
		title = self.getTitle()
		pos = title.find(" (")
		if pos != -1:
			title = title[:pos]
		title += " (TV)"
		self.setTitle(title)

	def setRadioMode(self):
		self.mode = MODE_RADIO
		self.servicePath = self.servicePathRadio
		self.recallBouquetMode()
		title = self.getTitle()
		pos = title.find(" (")
		if pos != -1:
			title = title[:pos]
		title += " (Radio)"
		self.setTitle(title)

	def setRoot(self, root, justSet=False):
		path = root.getPath()
		inBouquetRootList = path.find('FROM BOUQUET "bouquets.') != -1 #FIXME HACK
		pos = path.find('FROM BOUQUET')
		isBouquet = (pos != -1) and (root.flags & eServiceReference.isDirectory)
		if not inBouquetRootList and isBouquet:
			self.servicelist.setMode(ServiceList.MODE_FAVOURITES)
			self.servicelist.setNumberOffset(self.getBouquetNumOffset(root))
		else:
			self.servicelist.setMode(ServiceList.MODE_NORMAL)
		self.servicelist.setRoot(root, justSet)
		self.rootChanged = True
		self.buildTitleString()

	def removeModeStr(self, str):
		if self.mode == MODE_TV:
			pos = str.find(' (TV)')
		else:
			pos = str.find(' (Radio)')
		if pos != -1:
			return str[:pos]
		return str

	def getServiceName(self, ref):
		str = self.removeModeStr(ServiceReference(ref).getServiceName())
		if not str:
			pathstr = ref.getPath()
			if 'FROM PROVIDERS' in pathstr:
				return _("Provider")
			if 'FROM SATELLITES' in pathstr:
				return _("Satellites")
			if ') ORDER BY name' in pathstr:
				return _("All")
		return str

	def buildTitleString(self):
		titleStr = self.getTitle()
		pos = titleStr.find(']')
		if pos == -1:
			pos = titleStr.find(')')
		if pos != -1:
			titleStr = titleStr[:pos+1]
			Len = len(self.servicePath)
			if Len > 0:
				base_ref = self.servicePath[0]
				if Len > 1:
					end_ref = self.servicePath[Len-1]
				else:
					end_ref = None
				nameStr = self.getServiceName(base_ref)
				titleStr += ' ' + nameStr
				if end_ref is not None:
					if Len > 2:
						titleStr += '/../'
					else:
						titleStr += '/'
					nameStr = self.getServiceName(end_ref)
					titleStr += nameStr
				self.setTitle(titleStr)

	def moveUp(self):
		self.servicelist.moveUp()

	def moveDown(self):
		self.servicelist.moveDown()

	def clearPath(self):
		del self.servicePath[:]

	def enterPath(self, ref, justSet=False):
		self.servicePath.append(ref)
		self.setRoot(ref, justSet)

	def pathUp(self, justSet=False):
		prev = self.servicePath.pop()
		if self.servicePath:
			current = self.servicePath[-1]
			self.setRoot(current, justSet)
			if not justSet:
				self.setCurrentSelection(prev)
		return prev

	def isBasePathEqual(self, ref):
		if len(self.servicePath) > 1 and self.servicePath[0] == ref:
			return True
		return False

	def isPrevPathEqual(self, ref):
		length = len(self.servicePath)
		if length > 1 and self.servicePath[length-2] == ref:
			return True
		return False

	def preEnterPath(self, refstr):
		return False

	def showAllServices(self):
		if not self.pathChangeDisabled:
			refstr = '%s ORDER BY name'%(self.service_types)
			if not self.preEnterPath(refstr):
				ref = eServiceReference(refstr)
				currentRoot = self.getRoot()
				if currentRoot is None or currentRoot != ref:
					self.clearPath()
					self.enterPath(ref)

	def showSatellites(self):
		if not self.pathChangeDisabled:
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
							unsigned_orbpos = service.getUnsignedData(4) >> 16
							orbpos = service.getData(4) >> 16
							if orbpos < 0:
								orbpos += 3600
							if service.getPath().find("FROM PROVIDER") != -1:
								service_type = _("Providers")
							elif service.getPath().find("flags == %d" %(FLAG_SERVICE_NEW_FOUND)) != -1:
								service_type = _("New")
							else:
								service_type = _("Services")
							try:
								# why we need this cast?
								service_name = str(nimmanager.getSatDescription(orbpos))
							except:
								if unsigned_orbpos == 0xFFFF: #Cable
									service_name = _("Cable")
								elif unsigned_orbpos == 0xEEEE: #Terrestrial
									service_name = _("Terrestrial")
								else:
									if orbpos > 1800: # west
										orbpos = 3600 - orbpos
										h = _("W")
									else:
										h = _("E")
									service_name = ("%d.%d" + h) % (orbpos / 10, orbpos % 10)
							service.setName("%s - %s" % (service_name, service_type))
							self.servicelist.addService(service)
						cur_ref = self.session.nav.getCurrentlyPlayingServiceReference()
						if cur_ref:
							pos = self.service_types.rfind(':')
							refstr = '%s (channelID == %08x%04x%04x) && %s ORDER BY name' %(self.service_types[:pos+1],
								cur_ref.getUnsignedData(4), # NAMESPACE
								cur_ref.getUnsignedData(2), # TSID
								cur_ref.getUnsignedData(3), # ONID
								self.service_types[pos+1:])
							ref = eServiceReference(refstr)
							ref.setName(_("Current Transponder"))
							self.servicelist.addService(ref)
						self.servicelist.finishFill()
						if prev is not None:
							self.setCurrentSelection(prev)

	def showProviders(self):
		if not self.pathChangeDisabled:
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
		if not self.pathChangeDisabled:
			if len(self.servicePath) > 1:
				#when enter satellite root list we must do some magic stuff..
				ref = eServiceReference('%s FROM SATELLITES ORDER BY satellitePosition'%(self.service_types))
				if self.isBasePathEqual(ref):
					self.showSatellites()
				else:
					self.pathUp()
				if direction < 0:
					self.moveUp()
				else:
					self.moveDown()
				ref = self.getCurrentSelection()
				self.enterPath(ref)

	def inBouquet(self):
		if self.servicePath and self.servicePath[0] == self.bouquet_root:
			return True
		return False

	def atBegin(self):
		return self.servicelist.atBegin()

	def atEnd(self):
		return self.servicelist.atEnd()

	def nextBouquet(self):
		self.changeBouquet(+1)

	def prevBouquet(self):
		self.changeBouquet(-1)

	def showFavourites(self):
		if not self.pathChangeDisabled:
			if not self.preEnterPath(self.bouquet_rootstr):
				if self.isBasePathEqual(self.bouquet_root):
					self.pathUp()
				else:
					currentRoot = self.getRoot()
					if currentRoot is None or currentRoot != self.bouquet_root:
						self.clearPath()
						self.enterPath(self.bouquet_root)

	def keyNumberGlobal(self, number):
		unichar = self.numericalTextInput.getKey(number)
		charstr = unichar.encode("utf-8")
		if len(charstr) == 1:
			self.servicelist.moveToChar(charstr[0])

	def keyAsciiCode(self):
		unichar = unichr(getPrevAsciiCode())
		charstr = unichar.encode("utf-8")
		if len(charstr) == 1:
			self.servicelist.moveToChar(charstr[0])

	def getRoot(self):
		return self.servicelist.getRoot()

	def getCurrentSelection(self):
		return self.servicelist.getCurrent()

	def setCurrentSelection(self, service):
		self.servicelist.setCurrent(service)

	def getBouquetList(self):
		bouquets = [ ]
		serviceHandler = eServiceCenter.getInstance()
		if config.usage.multibouquet.value:
			list = serviceHandler.list(self.bouquet_root)
			if list:
				while True:
					s = list.getNext()
					if not s.valid():
						break
					if s.flags & eServiceReference.isDirectory:
						info = serviceHandler.info(s)
						if info:
							bouquets.append((info.getName(s), s))
				return bouquets
		else:
			info = serviceHandler.info(self.bouquet_root)
			if info:
				bouquets.append((info.getName(self.bouquet_root), self.bouquet_root))
			return bouquets
		return None

	def keyNumber0(self, num):
		if len(self.servicePath) > 1:
			self.keyGoUp()
		else:
			self.keyNumberGlobal(num)

	def keyGoUp(self):
		if len(self.servicePath) > 1:
			if self.isBasePathEqual(self.bouquet_root):
				self.showFavourites()
			else:
				ref = eServiceReference('%s FROM SATELLITES ORDER BY satellitePosition'%(self.service_types))
				if self.isBasePathEqual(ref):
					self.showSatellites()
				else:
					ref = eServiceReference('%s FROM PROVIDERS ORDER BY name'%(self.service_types))
					if self.isBasePathEqual(ref):
						self.showProviders()
					else:
						self.showAllServices()

	def nextMarker(self):
		self.servicelist.moveToNextMarker()

	def prevMarker(self):
		self.servicelist.moveToPrevMarker()

HISTORYSIZE = 20

#config for lastservice
config.tv = ConfigSubsection()
config.tv.lastservice = ConfigText()
config.tv.lastroot = ConfigText()
config.radio = ConfigSubsection()
config.radio.lastservice = ConfigText()
config.radio.lastroot = ConfigText()
config.servicelist = ConfigSubsection()
config.servicelist.lastmode = ConfigText(default = "tv")

class ChannelSelection(ChannelSelectionBase, ChannelSelectionEdit, ChannelSelectionEPG, SelectionEventInfo):
	def __init__(self, session):
		ChannelSelectionBase.__init__(self,session)
		ChannelSelectionEdit.__init__(self)
		ChannelSelectionEPG.__init__(self)
		SelectionEventInfo.__init__(self)

		self["actions"] = ActionMap(["OkCancelActions", "TvRadioActions"],
			{
				"cancel": self.cancel,
				"ok": self.channelSelected,
				"keyRadio": self.setModeRadio,
				"keyTV": self.setModeTv,
			})

		self.__event_tracker = ServiceEventTracker(screen=self, eventmap=
			{
				iPlayableService.evStart: self.__evServiceStart,
				iPlayableService.evEnd: self.__evServiceEnd
			})

		self.lastChannelRootTimer = eTimer()
		self.lastChannelRootTimer.callback.append(self.__onCreate)
		self.lastChannelRootTimer.start(100,True)

		self.history_tv = [ ]
		self.history_radio = [ ]
		self.history = self.history_tv
		self.history_pos = 0

		self.lastservice = config.tv.lastservice
		self.lastroot = config.tv.lastroot
		self.revertMode = None
		config.usage.multibouquet.addNotifier(self.multibouquet_config_changed)
		self.new_service_played = False
		self.onExecBegin.append(self.asciiOn)

	def asciiOn(self):
		rcinput = eRCInput.getInstance()
		rcinput.setKeyboardMode(rcinput.kmAscii)

	def asciiOff(self):
		rcinput = eRCInput.getInstance()
		rcinput.setKeyboardMode(rcinput.kmNone)

	def multibouquet_config_changed(self, val):
		self.recallBouquetMode()

	def __evServiceStart(self):
		service = self.session.nav.getCurrentService()
		if service:
			info = service.info()
			if info:
				refstr = info.getInfoString(iServiceInformation.sServiceref)
				self.servicelist.setPlayableIgnoreService(eServiceReference(refstr))

	def __evServiceEnd(self):
		self.servicelist.setPlayableIgnoreService(eServiceReference())

	def setMode(self):
		self.rootChanged = True
		self.restoreRoot()
		lastservice=eServiceReference(self.lastservice.value)
		if lastservice.valid():
			self.setCurrentSelection(lastservice)

	def setModeTv(self):
		if self.revertMode is None and config.servicelist.lastmode.value == "radio":
			self.revertMode = MODE_RADIO
		self.history = self.history_tv
		self.lastservice = config.tv.lastservice
		self.lastroot = config.tv.lastroot
		config.servicelist.lastmode.value = "tv"
		self.setTvMode()
		self.setMode()

	def setModeRadio(self):
		if self.revertMode is None and config.servicelist.lastmode.value == "tv":
			self.revertMode = MODE_TV
		if config.usage.e1like_radio_mode.value:
			self.history = self.history_radio
			self.lastservice = config.radio.lastservice
			self.lastroot = config.radio.lastroot
			config.servicelist.lastmode.value = "radio"
			self.setRadioMode()
			self.setMode()

	def __onCreate(self):
		if config.usage.e1like_radio_mode.value:
			if config.servicelist.lastmode.value == "tv":
				self.setModeTv()
			else:
				self.setModeRadio()
		else:
			self.setModeTv()
		lastservice=eServiceReference(self.lastservice.value)
		if lastservice.valid():
			self.zap()

	def channelSelected(self):
		ref = self.getCurrentSelection()
		if self.movemode:
			self.toggleMoveMarked()
		elif (ref.flags & 7) == 7:
			self.enterPath(ref)
		elif self.bouquet_mark_edit != OFF:
			if not (self.bouquet_mark_edit == EDIT_ALTERNATIVES and ref.flags & eServiceReference.isGroup):
				self.doMark()
		elif not (ref.flags & eServiceReference.isMarker): # no marker
			root = self.getRoot()
			if not root or not (root.flags & eServiceReference.isGroup):
				self.zap()
				self.asciiOff()
				self.close(ref)

	#called from infoBar and channelSelected
	def zap(self):
		self.revertMode=None
		ref = self.session.nav.getCurrentlyPlayingServiceReference()
		nref = self.getCurrentSelection()
		if ref is None or ref != nref:
			self.new_service_played = True
			self.session.nav.playService(nref)
			self.saveRoot()
			self.saveChannel(nref)
			config.servicelist.lastmode.save()
			self.addToHistory(nref)

	def newServicePlayed(self):
		ret = self.new_service_played
		self.new_service_played = False
		return ret

	def addToHistory(self, ref):
		if self.servicePath is not None:
			tmp=self.servicePath[:]
			tmp.append(ref)
			try:
				del self.history[self.history_pos+1:]
			except:
				pass
			self.history.append(tmp)
			hlen = len(self.history)
			if hlen > HISTORYSIZE:
				del self.history[0]
				hlen -= 1
			self.history_pos = hlen-1

	def historyBack(self):
		hlen = len(self.history)
		if hlen > 1 and self.history_pos > 0:
			self.history_pos -= 1
			self.setHistoryPath()

	def historyNext(self):
		hlen = len(self.history)
		if hlen > 1 and self.history_pos < (hlen-1):
			self.history_pos += 1
			self.setHistoryPath()

	def setHistoryPath(self):
		path = self.history[self.history_pos][:]
		ref = path.pop()
		del self.servicePath[:]
		self.servicePath += path
		self.saveRoot()
		root = path[-1]
		cur_root = self.getRoot()
		if cur_root and cur_root != root:
			self.setRoot(root)
		self.session.nav.playService(ref)
		self.setCurrentSelection(ref)
		self.saveChannel(ref)

	def saveRoot(self):
		path = ''
		for i in self.servicePath:
			path += i.toString()
			path += ';'
		if path and path != self.lastroot.value:
			self.lastroot.value = path
			self.lastroot.save()

	def restoreRoot(self):
		tmp = [x for x in self.lastroot.value.split(';') if x != '']
		current = [x.toString() for x in self.servicePath]
		if tmp != current or self.rootChanged:
			self.clearPath()
			cnt = 0
			for i in tmp:
				self.servicePath.append(eServiceReference(i))
				cnt += 1
			if cnt:
				path = self.servicePath.pop()
				self.enterPath(path)
			else:
				self.showFavourites()
				self.saveRoot()
			self.rootChanged = False

	def preEnterPath(self, refstr):
		if self.servicePath and self.servicePath[0] != eServiceReference(refstr):
			pathstr = self.lastroot.value
			if pathstr is not None and pathstr.find(refstr) == 0:
				self.restoreRoot()
				lastservice=eServiceReference(self.lastservice.value)
				if lastservice.valid():
					self.setCurrentSelection(lastservice)
				return True
		return False

	def saveChannel(self, ref):
		if ref is not None:
			refstr = ref.toString()
		else:
			refstr = ""
		if refstr != self.lastservice.value:
			self.lastservice.value = refstr
			self.lastservice.save()

	def setCurrentServicePath(self, path):
		if self.history:
			self.history[self.history_pos] = path
		else:
			self.history.append(path)
		self.setHistoryPath()

	def getCurrentServicePath(self):
		if self.history:
			return self.history[self.history_pos]
		return None

	def recallPrevService(self):
		hlen = len(self.history)
		if hlen > 1:
			if self.history_pos == hlen-1:
				tmp = self.history[self.history_pos]
				self.history[self.history_pos] = self.history[self.history_pos-1]
				self.history[self.history_pos-1] = tmp
			else:
				tmp = self.history[self.history_pos+1]
				self.history[self.history_pos+1] = self.history[self.history_pos]
				self.history[self.history_pos] = tmp
			self.setHistoryPath()

	def cancel(self):
		if self.revertMode is None:
			self.restoreRoot()
			lastservice=eServiceReference(self.lastservice.value)
			if lastservice.valid() and self.getCurrentSelection() != lastservice:
				self.setCurrentSelection(lastservice)
		elif self.revertMode == MODE_TV:
			self.setModeTv()
		elif self.revertMode == MODE_RADIO:
			self.setModeRadio()
		self.revertMode = None
		self.asciiOff()
		self.close(None)

class RadioInfoBar(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		self["RdsDecoder"] = RdsDecoder(self.session.nav)

class ChannelSelectionRadio(ChannelSelectionBase, ChannelSelectionEdit, ChannelSelectionEPG, InfoBarBase):
	ALLOW_SUSPEND = True

	def __init__(self, session, infobar):
		ChannelSelectionBase.__init__(self, session)
		ChannelSelectionEdit.__init__(self)
		ChannelSelectionEPG.__init__(self)
		InfoBarBase.__init__(self)
		self.infobar = infobar
		self.onLayoutFinish.append(self.onCreate)

		self.info = session.instantiateDialog(RadioInfoBar) # our simple infobar

		self["actions"] = ActionMap(["OkCancelActions", "TvRadioActions"],
			{
				"keyTV": self.cancel,
				"keyRadio": self.cancel,
				"cancel": self.cancel,
				"ok": self.channelSelected,
			})

		self.__event_tracker = ServiceEventTracker(screen=self, eventmap=
			{
				iPlayableService.evStart: self.__evServiceStart,
				iPlayableService.evEnd: self.__evServiceEnd
			})

########## RDS Radiotext / Rass Support BEGIN
		self.infobar = infobar # reference to real infobar (the one and only)
		self["RdsDecoder"] = self.info["RdsDecoder"]
		self["RdsActions"] = HelpableActionMap(self, "InfobarRdsActions",
		{
			"startRassInteractive": (self.startRassInteractive, _("View Rass interactive..."))
		},-1)
		self["RdsActions"].setEnabled(False)
		infobar.rds_display.onRassInteractivePossibilityChanged.append(self.RassInteractivePossibilityChanged)
		self.onClose.append(self.__onClose)

	def __onClose(self):
		lastservice=eServiceReference(config.tv.lastservice.value)
		self.session.nav.playService(lastservice)

	def startRassInteractive(self):
		self.info.hide();
		self.infobar.rass_interactive = self.session.openWithCallback(self.RassInteractiveClosed, RassInteractive)

	def RassInteractiveClosed(self):
		self.info.show()
		self.infobar.rass_interactive = None
		self.infobar.RassSlidePicChanged()

	def RassInteractivePossibilityChanged(self, state):
		self["RdsActions"].setEnabled(state)
########## RDS Radiotext / Rass Support END

	def cancel(self):
		self.infobar.rds_display.onRassInteractivePossibilityChanged.remove(self.RassInteractivePossibilityChanged)
		self.info.hide()
		#set previous tv service
		self.close(None)

	def __evServiceStart(self):
		service = self.session.nav.getCurrentService()
		if service:
			info = service.info()
			if info:
				refstr = info.getInfoString(iServiceInformation.sServiceref)
				self.servicelist.setPlayableIgnoreService(eServiceReference(refstr))

	def __evServiceEnd(self):
		self.servicelist.setPlayableIgnoreService(eServiceReference())

	def saveRoot(self):
		path = ''
		for i in self.servicePathRadio:
			path += i.toString()
			path += ';'
		if path and path != config.radio.lastroot.value:
			config.radio.lastroot.value = path
			config.radio.lastroot.save()

	def restoreRoot(self):
		tmp = [x for x in config.radio.lastroot.value.split(';') if x != '']
		current = [x.toString() for x in self.servicePath]
		if tmp != current or self.rootChanged:
			cnt = 0
			for i in tmp:
				self.servicePathRadio.append(eServiceReference(i))
				cnt += 1
			if cnt:
				path = self.servicePathRadio.pop()
				self.enterPath(path)
			else:
				self.showFavourites()
				self.saveRoot()
			self.rootChanged = False

	def preEnterPath(self, refstr):
		if self.servicePathRadio and self.servicePathRadio[0] != eServiceReference(refstr):
			pathstr = config.radio.lastroot.value
			if pathstr is not None and pathstr.find(refstr) == 0:
				self.restoreRoot()
				lastservice=eServiceReference(config.radio.lastservice.value)
				if lastservice.valid():
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
		else:
			self.session.nav.stopService()
		self.info.show()

	def channelSelected(self): # just return selected service
		ref = self.getCurrentSelection()
		if self.movemode:
			self.toggleMoveMarked()
		elif (ref.flags & 7) == 7:
			self.enterPath(ref)
		elif self.bouquet_mark_edit != OFF:
			if not (self.bouquet_mark_edit == EDIT_ALTERNATIVES and ref.flags & eServiceReference.isGroup):
				self.doMark()
		elif not (ref.flags & eServiceReference.isMarker): # no marker
			cur_root = self.getRoot()
			if not cur_root or not (cur_root.flags & eServiceReference.isGroup):
				playingref = self.session.nav.getCurrentlyPlayingServiceReference()
				if playingref is None or playingref != ref:
					self.session.nav.playService(ref)
					config.radio.lastservice.value = ref.toString()
					config.radio.lastservice.save()
				self.saveRoot()

class SimpleChannelSelection(ChannelSelectionBase):
	def __init__(self, session, title):
		ChannelSelectionBase.__init__(self, session)
		self["actions"] = ActionMap(["OkCancelActions", "TvRadioActions"],
			{
				"cancel": self.close,
				"ok": self.channelSelected,
				"keyRadio": self.setModeRadio,
				"keyTV": self.setModeTv,
			})
		self.title = title
		self.onLayoutFinish.append(self.layoutFinished)

	def layoutFinished(self):
		self.setModeTv()

	def channelSelected(self): # just return selected service
		ref = self.getCurrentSelection()
		if (ref.flags & 7) == 7:
			self.enterPath(ref)
		elif not (ref.flags & eServiceReference.isMarker):
			ref = self.getCurrentSelection()
			self.close(ref)

	def setModeTv(self):
		self.setTvMode()
		self.showFavourites()

	def setModeRadio(self):
		self.setRadioMode()
		self.showFavourites()
