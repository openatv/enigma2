from Plugins.Plugin import PluginDescriptor
from Components.ServiceEventTracker import ServiceEventTracker
from Components.ServiceList import ServiceList
from Screens.InfoBar import InfoBar
from enigma import *


class Channelnumber:

	def __init__(self, session):
		self.session = session
		self.onClose = [ ]
		
		self.__event_tracker = ServiceEventTracker(screen=self,eventmap=
			{
				iPlayableService.evUpdatedEventInfo: self.__eventInfoChanged
			})

	def __eventInfoChanged(self):
		service = self.session.nav.getCurrentService()
		info = service and service.info()
		if info is None:
			chnr = "---"
		else:
			chnr = self.getchannelnr()
		info = None
		service = None
		open("/proc/vfd", "w").write(chnr + '\n')


	def getchannelnr(self):
		if InfoBar.instance is None:
			chnr = "---"
			return chnr
		MYCHANSEL = InfoBar.instance.servicelist
		markersOffset = 0
		myRoot = MYCHANSEL.getRoot()
		mySrv = MYCHANSEL.servicelist.getCurrent()
		chx = MYCHANSEL.servicelist.l.lookupService(mySrv)
		if not MYCHANSEL.inBouquet():
			pass
		else:
			serviceHandler = eServiceCenter.getInstance()
			mySSS = serviceHandler.list(myRoot)
			SRVList = mySSS and mySSS.getContent("SN", True)
			for i in range(len(SRVList)):
				if chx == i:
					break
				testlinet = SRVList[i]
				testline = testlinet[0].split(":")
				if testline[1] == "64":
					markersOffset = markersOffset + 1
		chx = (chx - markersOffset) + 1
		rx = MYCHANSEL.getBouquetNumOffset(myRoot)
		chnr = str(chx + rx)
		return chnr

ChannelnumberInstance = None

def main(session, **kwargs):
	global ChannelnumberInstance
	if ChannelnumberInstance is None:
		ChannelnumberInstance = Channelnumber(session)

def Plugins(**kwargs):
	return [ PluginDescriptor(name="Channelnumber", description="Show Channel Number", where = PluginDescriptor.WHERE_SESSIONSTART, fnc=main ) ]

