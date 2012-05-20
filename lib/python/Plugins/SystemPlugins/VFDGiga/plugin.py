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
from enigma import evfd, iPlayableService, eServiceCenter, eTimer
from os import system
from Plugins.Plugin import PluginDescriptor
from Components.ServiceEventTracker import ServiceEventTracker
from Components.ServiceList import ServiceList
from Screens.InfoBar import InfoBar
from time import localtime, time
import Screens.Standby

config.plugins.VFD_Giga = ConfigSubsection()
config.plugins.VFD_Giga.showClock = ConfigSelection(default = "Yes", choices = [("False",_("in standby: ") + _("No")),("True",_("in standby: ") + _("Yes")),("True_All",_("Yes")),("Off",_("Off"))])
config.plugins.VFD_Giga.setLed = ConfigYesNo(default = True)
led = [("0",_("None")),("1",_("Blue")),("2",_("Red")),("3",_("Purple"))]				
config.plugins.VFD_Giga.ledRUN = ConfigSelection(led, default = "Blue")
config.plugins.VFD_Giga.ledSBY = ConfigSelection(led, default = "Red")
config.plugins.VFD_Giga.ledREC = ConfigSelection(led, default = "Purple")
config.plugins.VFD_Giga.timeMode = ConfigSelection(default = "24h", choices = [("12h"),("24h")])

RecLed = None

class Channelnumber:

	def __init__(self, session):
		self.session = session
		self.sign = 0
		self.zaPrik = eTimer()
		self.zaPrik.timeout.get().append(self.vrime)
		self.zaPrik.start(1000, 1)
		self.onClose = [ ]
		
		self.__event_tracker = ServiceEventTracker(screen=self,eventmap=
			{
				iPlayableService.evUpdatedEventInfo: self.__eventInfoChanged
			})

	def __eventInfoChanged(self):
		self.RecordingLed()
		if config.plugins.VFD_Giga.showClock.value == 'Off' or config.plugins.VFD_Giga.showClock.value == 'True_All':
			return
		service = self.session.nav.getCurrentService()
		info = service and service.info()
		if info is None:
			chnr = "---"
		else:
			chnr = self.getchannelnr()
		info = None
		service = None
		########## Center Channel number #################
		t = len(chnr)
		if t == 1:
			CentChnr = " " + chnr + "  " + '\n'
		elif t == 2:
			CentChnr = " " + chnr + " " + '\n'
		elif t == 3:
			CentChnr = chnr + " " + '\n'
		else:
			CentChnr = chnr + '\n'
		#################################################

		open("/proc/vfd", "w").write(CentChnr)

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

	def prikaz(self):
		if config.plugins.VFD_Giga.showClock.value == 'True' or config.plugins.VFD_Giga.showClock.value == 'True_All':
			clock = str(localtime()[3])
			clock1 = str(localtime()[4])
			if config.plugins.VFD_Giga.timeMode.value != '24h':
				if int(clock) > 12:
					clock = str(int(clock) - 12)
		
			if self.sign == 0:
				clock2 = "%02d:%02d" % (int(clock), int(clock1))
				self.sign = 1
			else:
				clock2 = "%02d%02d" % (int(clock), int(clock1))
				self.sign = 0

			evfd.getInstance().vfd_write_string(clock2) 
		else:
			evfd.getInstance().vfd_write_string("    ")
			
	def vrime(self):
		self.RecordingLed()
		if config.plugins.VFD_Giga.showClock.value == 'Off':
			evfd.getInstance().vfd_write_string("    ")
			self.zaPrik.start(10000, 1)
			return
		else:
			self.zaPrik.start(1000, 1)
	
		if Screens.Standby.inStandby or config.plugins.VFD_Giga.showClock.value == 'True_All':
			self.prikaz()

	def RecordingLed(self):
		global RecLed
		recordings = self.session.nav.getRecordings()
		if recordings:
			if RecLed is None:
				evfd.getInstance().vfd_led(config.plugins.VFD_Giga.ledREC.value)
				RecLed = True
		else:
			if RecLed is not None:
				RecLed = None
				if Screens.Standby.inStandby:
					evfd.getInstance().vfd_led(config.plugins.VFD_Giga.ledSBY.value)
				else:
					evfd.getInstance().vfd_led(config.plugins.VFD_Giga.ledRUN.value)

ChannelnumberInstance = None

def leaveStandby():
	print "[GIGA-VFD] Leave Standby"

	try:
		open("/proc/stb/fp/rtc", "w").write(str(0))
	except IOError:
		print "setRTCtime failed!"

	if config.plugins.VFD_Giga.showClock.value == 'Off':
		evfd.getInstance().vfd_write_string("    ")

	if RecLed is None:		
		if config.plugins.VFD_Giga.setLed.value:
			evfd.getInstance().vfd_led(config.plugins.VFD_Giga.ledRUN.value)
		else:
			evfd.getInstance().vfd_led("0")
	else:
		evfd.getInstance().vfd_led(config.plugins.VFD_Giga.ledREC.value)

def standbyCounterChanged(configElement):
	print "[GIGA-VFD] In Standby"
	
	from Screens.Standby import inStandby
	inStandby.onClose.append(leaveStandby)
	
	if config.plugins.VFD_Giga.showClock.value == 'Off':
		evfd.getInstance().vfd_write_string("    ")
	
	if RecLed is None:	
		if config.plugins.VFD_Giga.setLed.value:
			evfd.getInstance().vfd_led(config.plugins.VFD_Giga.ledSBY.value)
		else:
			evfd.getInstance().vfd_led("0")
	else:
		evfd.getInstance().vfd_led(config.plugins.VFD_Giga.ledREC.value)

def initVFD():
	print "[GIGA-VFD] initVFD"
	
	if config.plugins.VFD_Giga.setLed.value:
		evfd.getInstance().vfd_led(config.plugins.VFD_Giga.ledRUN.value)
	else:
		evfd.getInstance().vfd_led("0")
	if config.plugins.VFD_Giga.showClock.value == 'True' or config.plugins.VFD_Giga.showClock.value == 'True_All':
		forcmd = '1'
	elif config.plugins.VFD_Giga.showClock.value == 'Off':
		evfd.getInstance().vfd_write_string("    ")
		forcmd = '0'
	else:
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
		
		self.onChangedEntry = [ ]
		self.list = []
		ConfigListScreen.__init__(self, self.list, session = self.session, on_change = self.changedEntry)
						
		self.createSetup()
		
		self.Console = Console()
		self["key_red"] = Button(_("Cancel"))
		self["key_green"] = Button(_("Save"))
		self["key_yellow"] = Button(_("Update Date/Time"))

		self["setupActions"] = ActionMap(["SetupActions","ColorActions"],
		{
			"save": self.save,
			"cancel": self.cancel,
			"ok": self.save,
			"yellow": self.Update,
		}, -2)
	
	def createSetup(self):
		self.editListEntry = None
		self.list = []
		self.list.append(getConfigListEntry(_("Enable led"), config.plugins.VFD_Giga.setLed))
		if config.plugins.VFD_Giga.setLed.value:
			self.list.append(getConfigListEntry(_("Led state RUN"), config.plugins.VFD_Giga.ledRUN))	
			self.list.append(getConfigListEntry(_("Led state Standby"), config.plugins.VFD_Giga.ledSBY))	
			self.list.append(getConfigListEntry(_("Led state Record"), config.plugins.VFD_Giga.ledREC))	
			evfd.getInstance().vfd_led(str(config.plugins.VFD_Giga.ledRUN.value))
		else:
			evfd.getInstance().vfd_led("0")
		self.list.append(getConfigListEntry(_("Show clock"), config.plugins.VFD_Giga.showClock))
		if config.plugins.VFD_Giga.showClock.value != "Off":
			self.list.append(getConfigListEntry(_("Time mode"), config.plugins.VFD_Giga.timeMode))
			cmd = 'echo 1 > /proc/stb/fp/display_clock'
		else:
			cmd = 'echo 0 > /proc/stb/fp/display_clock'
			evfd.getInstance().vfd_led("0")
		res = system(cmd)
		self["config"].list = self.list
		self["config"].l.setList(self.list)	

	def changedEntry(self):
		for x in self.onChangedEntry:
			x()
		self.newConfig()
			
	def newConfig(self):
		print self["config"].getCurrent()[0]
		if self["config"].getCurrent()[0] == _('Enable led'):
			self.createSetup()	
		if self["config"].getCurrent()[0][:3].upper() == 'LED':
			evfd.getInstance().vfd_led(str(config.plugins.VFD_Giga.ledRUN.value))
		if self["config"].getCurrent()[0] == _('Show clock'):
			self.createSetup()						
	
	def abort(self):
		print "aborting"

	def save(self):
		for x in self["config"].list:
			x[1].save()
		
		configfile.save()
		initVFD()
		self.close()

	def cancel(self):
		initVFD()
		for x in self["config"].list:
			x[1].cancel()
		self.close()

	def Update(self):
		self.createSetup()
		initVFD()

class VFD_Giga:
	def __init__(self, session):
		print "VFD_Giga initializing"
		self.session = session
		self.service = None
		self.onClose = [ ]

		self.Console = Console()
		
		initVFD()
		
		global ChannelnumberInstance
		if ChannelnumberInstance is None:
			ChannelnumberInstance = Channelnumber(session) 

	def shutdown(self):
		self.abort()

	def abort(self):
		print "VFD_Giga aborting"

	config.misc.standbyCounter.addNotifier(standbyCounterChanged, initial_call = False)

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
		try:
			open("/proc/stb/fp/rtc", "w").write(str(0))
		except IOError:
			print "setRTCtime failed!"
		gigaVfd = VFD_Giga(mySession)
	elif gReason == 1 and gigaVfd != None:
		print "Stopping VFD_Giga"
		import time
		if time.localtime().tm_isdst == 0:
			forsleep = int(time.time())-time.timezone
		else:
			forsleep = int(time.time())-time.altzone-time.timezone
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
