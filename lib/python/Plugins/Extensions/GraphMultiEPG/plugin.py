from Plugins.Plugin import PluginDescriptor
from GraphMultiEpg import GraphMultiEPG
from Screens.ChannelSelection import BouquetSelector, SilentBouquetSelector
from enigma import eServiceCenter, eServiceReference
from ServiceReference import ServiceReference
from Components.config import config

Session = None
Servicelist = None

bouquetSel = None
epg_bouquet = None
dlg_stack = [ ]

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

def closed(ret=False):
	closedScreen = dlg_stack.pop()
	global bouquetSel
	if bouquetSel and closedScreen == bouquetSel:
		bouquetSel = None
	dlgs=len(dlg_stack)
	if ret and dlgs > 0: # recursive close wished
		dlg_stack[dlgs-1].close(dlgs > 1)
	if dlgs <= 0:
		cleanup()

def openBouquetEPG(bouquet):
	services = getBouquetServices(bouquet)
	if len(services):
		global epg_bouquet
		epg_bouquet = bouquet
		dlg_stack.append(Session.openWithCallback(closed, GraphMultiEPG, services, zapToService, changeBouquetCB))
		return True
	return False

def changeBouquetCB(direction, epg):
	if bouquetSel:
		if direction > 0:
			bouquetSel.down()
		else:
			bouquetSel.up()
		bouquet = bouquetSel.getCurrent()
		services = getBouquetServices(bouquet)
		if len(services):
			global epg_bouquet
			epg_bouquet = bouquet
			epg.setServices(services)

def openAskBouquet(Session, bouquets, cnt):
	if cnt > 1: # show bouquet list
		global bouquetSel
		bouquetSel = Session.openWithCallback(closed, BouquetSelector, bouquets, openBouquetEPG, enableWrapAround=True)
		dlg_stack.append(bouquetSel)
	elif cnt == 1:
		if not openBouquetEPG(bouquets[0][1]):
			cleanup()

def openSilent(Servicelist, bouquets, cnt):
	root = Servicelist.getRoot()
	if cnt > 1: # create bouquet list
		global bouquetSel
		current = 0
		rootstr = root.toCompareString()
		for bouquet in bouquets:
			if bouquet[1].toCompareString() == rootstr:
				break
			current += 1
		if current >= cnt:
			current = 0
		bouquetSel = SilentBouquetSelector(bouquets, True, current)
	if cnt >= 1: # open current bouquet
		if not openBouquetEPG(root):
			cleanup()

def main(session, servicelist, **kwargs):
	global Session
	Session = session
	global Servicelist
	Servicelist = servicelist
	bouquets = Servicelist.getBouquetList()
	if bouquets is None:
		cnt = 0
	else:
		cnt = len(bouquets)
	if config.usage.multiepg_ask_bouquet.value:
		openAskBouquet(session, bouquets, cnt)
	else:
		openSilent(servicelist, bouquets, cnt)

def Plugins(**kwargs):
	name = _("Graphical Multi EPG")
	descr = _("A graphical EPG for all services of an specific bouquet")
	return [PluginDescriptor(name=name, description=descr, where = PluginDescriptor.WHERE_EVENTINFO, needsRestart = False, fnc=main),
		PluginDescriptor(name=name, description=descr, where = PluginDescriptor.WHERE_EXTENSIONSMENU, needsRestart = False, fnc=main)]
