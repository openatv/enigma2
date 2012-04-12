from Screens.Screen import Screen
from Plugins.Plugin import PluginDescriptor
from Components.Console import Console
from Components.Button import Button
from Components.ActionMap import ActionMap
from Components.ConfigList import ConfigList
from Components.config import config, configfile, ConfigSubsection, ConfigEnableDisable, \
     getConfigListEntry, ConfigInteger, ConfigSelection, ConfigYesNo 
from Components.ConfigList import ConfigListScreen
from Tools.Directories import resolveFilename, SCOPE_PLUGINS
from enigma import evfd, iPlayableService, eServiceCenter
from os import system
from Plugins.Plugin import PluginDescriptor
from Components.ServiceEventTracker import ServiceEventTracker
from Components.ServiceList import ServiceList
from Screens.InfoBar import InfoBar

config.plugins.VFD_Giga = ConfigSubsection()
config.plugins.VFD_Giga.showClock = ConfigEnableDisable(default = True)
config.plugins.VFD_Giga.setLed = ConfigYesNo(default = True)
led = {"0":"None","1":"Blue","2":"Red","3":"Purple"}				
config.plugins.VFD_Giga.ledRUN = ConfigSelection(led, default = "1")
config.plugins.VFD_Giga.ledSBY = ConfigSelection(led, default = "2")
config.plugins.VFD_Giga.ledREC = ConfigSelection(led, default = "3")
config.plugins.VFD_Giga.timeMode = ConfigSelection(default = "24h", choices = [("12h"),("24h")])

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

def initVFD():
	forledx = file('/etc/vfdled','r')
	forled = eval(forledx)	
	if forled[0] == 'True':
		evfd.getInstance().vfd_led(str(forled[1]))
	else:
		evfd.getInstance().vfd_led(str(0))
	if forled[4] == 'True':
		evfd.getInstance().vfd_led(str(forled[1]))
		forcmd = '1'
	else:
		evfd.getInstance().vfd_led(str(0))
		forcmd = '0'
	cmd = 'echo '+str(forcmd)+' > /proc/stb/fp/display_clock'
	res = system(cmd)
	
class VFD_GigaSetup(ConfigListScreen, Screen):
	def __init__(self, session, args = None):
	
		self.skin = """
			<screen position="100,100" size="500,210" title="VFD_Giga Setup" >
				<widget name="config" position="20,15" size="460,150" scrollbarMode="showOnDemand" />
				<ePixmap position="40,165" size="140,40" pixmap="skin_default/buttons/green.png" alphatest="on" />
				<ePixmap position="180,165" size="140,40" pixmap="skin_default/buttons/red.png" alphatest="on" />
				<widget name="key_green" position="40,165" size="140,40" font="Regular;20" backgroundColor="#1f771f" zPosition="2" transparent="1" shadowColor="black" shadowOffset="-1,-1" />
				<widget name="key_red" position="180,165" size="140,40" font="Regular;20" backgroundColor="#9f1313" zPosition="2" transparent="1" shadowColor="black" shadowOffset="-1,-1" />
			</screen>"""
		
		Screen.__init__(self, session)
		self.onClose.append(self.abort)
		
		self.list = []
		ConfigListScreen.__init__(self, self.list)
						
		self.createSetup()
		
		self.Console = Console()
                self["key_red"] = Button(_("Cancel"))
                self["key_green"] = Button(_("Save"))
                self["key_yellow"] = Button(_("Update Date/Time"))
                                
		self["setupActions"] = ActionMap(["SetupActions"],
		{
			"save": self.save,
			"cancel": self.cancel,
			"ok": self.save,
		}, -2)
	
	def createSetup(self):	
		self.list = []
		self.list.append(getConfigListEntry(_("Enable led"), config.plugins.VFD_Giga.setLed))
		self.ledenable = config.plugins.VFD_Giga.setLed.value
		if self.ledenable == True:
			self.list.append(getConfigListEntry(_("Led state RUN"), config.plugins.VFD_Giga.ledRUN))	
			self.list.append(getConfigListEntry(_("Led state Standby"), config.plugins.VFD_Giga.ledSBY))	
			self.list.append(getConfigListEntry(_("Led state Record"), config.plugins.VFD_Giga.ledREC))	
			evfd.getInstance().vfd_led(str(config.plugins.VFD_Giga.ledRUN.value))
		else:
			evfd.getInstance().vfd_led("0")
		self.list.append(getConfigListEntry(_("Show clock"), config.plugins.VFD_Giga.showClock))
		if config.plugins.VFD_Giga.showClock.value == True:
			self.list.append(getConfigListEntry(_("Time mode"), config.plugins.VFD_Giga.timeMode))
			cmd = 'echo 1 > /proc/stb/fp/display_clock'
		else:
			cmd = 'echo 0 > /proc/stb/fp/display_clock'
			evfd.getInstance().vfd_led("0")
		res = system(cmd)
		self["config"].list = self.list
		self["config"].l.setList(self.list)			
			
	def newConfig(self):
		if self["config"].getCurrent()[0] == 'Enable led':
			self.ledenable = config.plugins.VFD_Giga.setLed.value
			self.createSetup()	
		if self["config"].getCurrent()[0][:3] == 'Led':
			evfd.getInstance().vfd_led(str(config.plugins.VFD_Giga.ledRUN.value))
		if self["config"].getCurrent()[0] == 'Show clock':
			self.createSetup()						
	
	def keyLeft(self):
		ConfigListScreen.keyLeft(self)
		self.newConfig()

	def keyRight(self):
		ConfigListScreen.keyRight(self)
		self.newConfig()
	
	def abort(self):
		print "aborting"

	def save(self):
		for x in self["config"].list:
			x[1].save()
		
		configfile.save()
		
		forfile = []
		forfile.append(str(config.plugins.VFD_Giga.setLed.value))
		forfile.append(str(config.plugins.VFD_Giga.ledRUN.value))
		forfile.append(str(config.plugins.VFD_Giga.ledSBY.value))
		forfile.append(str(config.plugins.VFD_Giga.ledREC.value))
		forfile.append(str(config.plugins.VFD_Giga.showClock.value))
		forfile.append(str(config.plugins.VFD_Giga.timeMode.value))
		fp = file('/etc/vfdled','w')
		fp.write(str(forfile))
		fp.close()
		
		self.close()

	def cancel(self):
		for x in self["config"].list:
			x[1].cancel()
		self.close()

class VFD_Giga:
	def __init__(self, session):
		print "VFD_Giga initializing"
		self.session = session
		self.service = None
		self.onClose = [ ]

		self.Console = Console()
		evfd.getInstance().vfd_led(str(config.plugins.VFD_Giga.ledRUN.value))
		
		global ChannelnumberInstance
		if ChannelnumberInstance is None:
			ChannelnumberInstance = Channelnumber(session) 
		    			
	def shutdown(self):
		self.abort()

	def abort(self):
		print "VFD_Giga aborting"

def main(menuid):
	if menuid != "system": 
			return [ ] 	
	return [(_("VFD_Giga"), startVFD, "VFD_Giga", None)] 

def startVFD(session, **kwargs): 
	session.open(VFD_GigaSetup) 	
	
gigaVfd = None
gReason = -1
mySession = None

def controlgigaVfd():
	global gigaVfd
	global gReason
	global mySession
	
	if gReason == 0 and mySession != None and gigaVfd == None:
		print "Starting VFD_Giga"
		gigaVfd = VFD_Giga(mySession)
	elif gReason == 1 and gigaVfd != None:
		print "Stopping VFD_Giga"
		import time
		if time.localtime().tm_isdst == 0:
			forsleep = int(time.time())-time.timezone
		else:
			forsleep = int(time.time())-time.altzone			
		try:
			open("/proc/stb/fp/rtc", "w").write(str(forsleep))
		except IOError:
			print "setRTCtime failed!" 		
		gigaVfd = None

def sessionstart(reason, **kwargs):
	print "AutoStarting VFD_Giga"
	global gigaVfd
	global gReason
	global mySession

	if kwargs.has_key("session"):
		mySession = kwargs["session"]
	else:
		gReason = reason
	controlgigaVfd()

def Plugins(**kwargs):
 	return [ PluginDescriptor(where=[PluginDescriptor.WHERE_AUTOSTART, PluginDescriptor.WHERE_SESSIONSTART], fnc=sessionstart),
 		PluginDescriptor(name="VFD_Giga", description="Change VFD display settings",where = PluginDescriptor.WHERE_MENU, fnc = main) ]
