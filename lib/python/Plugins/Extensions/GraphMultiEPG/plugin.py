from Plugins.Plugin import PluginDescriptor
from GraphMultiEpg import GraphMultiEPG
from Screens.ChannelSelection import BouquetSelector
from enigma import eServiceCenter, eServiceReference
from ServiceReference import ServiceReference
from Screens.Screen import Screen
from Components.ActionMap import ActionMap
from Components.MenuList import MenuList

Session = None
Servicelist = None
bouquetSel = None
epg_bouquet = None
epg = None

class SelectBouquet(Screen):
	skin = """<screen name="SelectBouquet" position="center,center" size="300,240" title="Choose bouquet">
              <widget name="menu" position="10,10" size="290,225" scrollbarMode="showOnDemand" />
          </screen>"""

	def __init__(self, session, bouquets, curbouquet, direction, enableWrapAround=True):
		Screen.__init__(self, session)

		self["actions"] = ActionMap(["OkCancelActions", "EPGSelectActions"],
			{
				"ok": self.okbuttonClick,
				"cancel": self.cancelClick,
				"nextBouquet": self.up,
				"prevBouquet": self.down
			})
		entrys = [ (x[0], x[1]) for x in bouquets ]
		self["menu"] = MenuList(entrys, enableWrapAround)
		idx = 0
		for x in bouquets:
			if x[1] == curbouquet:
				break
			idx += 1
		self.idx = idx
		self.dir = direction
		self.onShow.append(self.__onShow)

	def __onShow(self):
		self["menu"].moveToIndex(self.idx)
		if self.dir == -1:
			self.down()
		else:
			self.up()

	def getCurrent(self):
		cur = self["menu"].getCurrent()
		return cur and cur[1]

	def okbuttonClick(self):
		self.close(self.getCurrent())

	def up(self):
		self["menu"].up()

	def down(self):
		self["menu"].down()

	def cancelClick(self):
		self.close(None)


def zapToService(service):
	if not service is None:
		if Servicelist.getRoot() != epg_bouquet: #already in correct bouquet?
			Servicelist.clearPath()
			if Servicelist.bouquet_root != epg_bouquet:
				Servicelist.enterPath(Servicelist.bouquet_root)
			Servicelist.enterPath(epg_bouquet)
		Servicelist.setCurrentSelection(service) #select the service in Servicelist
		Servicelist.zap()

def getBouquetServices(bouquet):
	services = [ ]
	Servicelist = eServiceCenter.getInstance().list(bouquet)
	if not Servicelist is None:
		while True:
			service = Servicelist.getNext()
			if not service.valid(): #check if end of list
				break
			if service.flags & (eServiceReference.isDirectory | eServiceReference.isMarker): #ignore non playable services
				continue
			services.append(ServiceReference(service))
	return services

def cleanup():
	global Session
	Session = None
	global Servicelist
	Servicelist = None
	global bouquets
	bouquets = None
	global epg_bouquet
	epg_bouquet = None
	global epg
	epg = None

def closed(ret=False):
	cleanup()

def onSelectBouquetClose(bouquet):
	if not bouquet is None:
		services = getBouquetServices(bouquet)
		if len(services):
			global epg_bouquet
			epg_bouquet = bouquet
			epg.setServices(services)
			epg.setTitle(ServiceReference(epg_bouquet).getServiceName())

def changeBouquetCB(direction, epgcall):
	global epg
	epg = epgcall
	Session.openWithCallback(onSelectBouquetClose, SelectBouquet, bouquets, epg_bouquet, direction)

def main(session, servicelist = None, **kwargs):
	global Session
	Session = session
	global Servicelist
	Servicelist = servicelist
	global bouquets
	bouquets = Servicelist and Servicelist.getBouquetList()
	global epg_bouquet
	epg_bouquet = Servicelist and Servicelist.getRoot()
	if epg_bouquet is not None:
		if len(bouquets) > 1 :
			cb = changeBouquetCB
		else:
			cb = None
		services = getBouquetServices(epg_bouquet)
		Session.openWithCallback(closed, GraphMultiEPG, services, zapToService, cb, ServiceReference(epg_bouquet).getServiceName())

def Plugins(**kwargs):
	name = _("Graphical Multi EPG")
	descr = _("A graphical EPG for all services of an specific bouquet")
	return [PluginDescriptor(name=name, description=descr, where = PluginDescriptor.WHERE_EVENTINFO, needsRestart = False, fnc=main),
		PluginDescriptor(name=name, description=descr, where = PluginDescriptor.WHERE_EXTENSIONSMENU, needsRestart = False, fnc=main)]
