from Plugins.Plugin import PluginDescriptor
from GraphMultiEpg import GraphMultiEPG
from Screens.ChannelSelection import SimpleChannelSelection
import Screens.InfoBar
from enigma import eServiceCenter, eServiceReference
from ServiceReference import ServiceReference
from Screens.Screen import Screen
from Components.ActionMap import ActionMap
from Components.MenuList import MenuList
from Components.config import config

Session = None
Servicelist = None
bouquetSel = None
epg_bouquet = None
epg = None

def zapToService(service, preview = False, zapback = False):
	if Servicelist.startServiceRef is None:
		Servicelist.startServiceRef = Session.nav.getCurrentlyPlayingServiceOrGroup()
	if not service is None:
		if not preview and not zapback:
			if Servicelist.getRoot() != epg_bouquet:
				Servicelist.clearPath()
				if Servicelist.bouquet_root != epg_bouquet:
					Servicelist.enterPath(Servicelist.bouquet_root)
				Servicelist.enterPath(epg_bouquet)
			Servicelist.setCurrentSelection(service)
		if not zapback or preview:
			Servicelist.zap(not preview, preview, ref=preview and service or None)
	if (Servicelist.dopipzap or zapback) and not preview:
		Servicelist.zapBack()
	if not preview:
		Servicelist.revertMode = None
		Servicelist.startServiceRef = None
		Servicelist.startRoot = None

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

def onSelectBouquetClose(*args):
	if args and len(args) == 2:
		serviceref, bouquetref = args[:2]
		services = getBouquetServices(bouquetref)
		global epg_bouquet
		epg_bouquet = bouquetref
		epg.setServices(services)
		epg.setTitle(ServiceReference(epg_bouquet).getServiceName())
		epg["list"].moveToService(serviceref)

def changeBouquetCB(direction, epgcall):
	global epg
	epg = epgcall
	Session.openWithCallback(onSelectBouquetClose, SimpleChannelSelection, _("Select channel"), True, True, epg["list"].getCurrent()[1].ref)

def main(session, servicelist = None, **kwargs):
	global Session
	Session = session
	global Servicelist
	Servicelist = servicelist or Screens.InfoBar.InfoBar.instance.servicelist
	global bouquets
	bouquets = Servicelist and Servicelist.getBouquetList()
	global epg_bouquet
	epg_bouquet = Servicelist and Servicelist.getRoot()
	runGraphMultiEpg()

def runGraphMultiEpg():
	global Servicelist
	global bouquets
	global epg_bouquet
	if epg_bouquet is not None:
		if len(bouquets) > 1 :
			cb = changeBouquetCB
		else:
			cb = None
		services = getBouquetServices(epg_bouquet)
		Session.openWithCallback(reopen, GraphMultiEPG, services, zapToService, cb, ServiceReference(epg_bouquet).getServiceName())

def reopen(answer):
	if answer is None:
		runGraphMultiEpg()
	else:
		closed(answer)

def Plugins(**kwargs):
	name = _("Graphical Multi EPG")
	descr = _("A graphical EPG for all services of an specific bouquet")
	list = [(PluginDescriptor(name=name, description=descr, where = PluginDescriptor.WHERE_EVENTINFO, needsRestart = False, fnc=main))]
	if config.misc.graph_mepg.extension_menu.value:
		list.append(PluginDescriptor(name=name, description=descr, where = PluginDescriptor.WHERE_EXTENSIONSMENU, needsRestart = False, fnc=main))
	return list
