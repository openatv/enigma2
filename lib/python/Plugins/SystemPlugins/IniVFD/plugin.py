from Screens.Screen import Screen
from Plugins.Plugin import PluginDescriptor
from Components.Console import Console
from Components.Lcd import *
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
from Components.Network import iNetwork

config.plugins.ini_vfd = ConfigSubsection()
config.plugins.ini_vfd.circle_recording = ConfigYesNo(default = True)
config.plugins.ini_vfd.circle_recording_stanby = ConfigYesNo(default = True)
config.plugins.ini_vfd.lan_icon = ConfigYesNo(default = True)

RecCircle = None

class CirLanVfd:
	def __init__(self, session):
		self.session = session
		self.upTimer = eTimer()
		self.upTimer.timeout.get().append(self.up)
		self.upTimer.start(1000, 1)
		self.onClose = [ ]
		
		self.__event_tracker = ServiceEventTracker(screen=self,eventmap=
			{
				iPlayableService.evUpdatedEventInfo: self.__eventInfoChanged
			})

	def __eventInfoChanged(self):
		self.RecordingCircle()
		self.LanIcon()

	def LinkStatedataAvail(self,data):
		for item in data.splitlines():
			if "Link detected:" in item:
			        if "yes" in item:
					evfd.getInstance().vfd_symbol_network(1)
				else:
					evfd.getInstance().vfd_symbol_network(0)
				break
		else:
		      print "unknown"
		
	def getLinkState(self,iface):
		iNetwork.getLinkState(iface,self.LinkStatedataAvail)
			
	def up(self):
		self.RecordingCircle()
		self.upTimer.start(10000, 1)
	
	def LanIcon(self):
		if Screens.Standby.inStandby:
		  evfd.getInstance().vfd_symbol_network(0)
		else:
		  if config.plugins.ini_vfd.lan_icon.value:
		    self.getLinkState("eth0")
		  else:
		    evfd.getInstance().vfd_symbol_network(0)
		  
	def RecordingCircle(self):
		global RecCircle
		recordings = self.session.nav.getRecordings()
		if recordings:
			if config.plugins.ini_vfd.circle_recording.value:
				evfd.getInstance().vfd_symbol_circle(3)
				if Screens.Standby.inStandby:
				    if config.plugins.ini_vfd.circle_recording_stanby.value:
				      evfd.getInstance().vfd_symbol_circle(3)
				    else:
				      evfd.getInstance().vfd_symbol_circle(0)
				    self.LanIcon()
			else:
				evfd.getInstance().vfd_symbol_circle(0)
				self.LanIcon()
			RecCircle = True
		else:
			if RecCircle is not None:
				RecCircle = None
				evfd.getInstance().vfd_symbol_circle(0)
			self.LanIcon()

CirLanVfdInstance = None

def initVFD():
	print "[VFD-INI] initVFD"
	evfd.getInstance().vfd_symbol_network(0)
	evfd.getInstance().vfd_symbol_circle(0)


class ini_vfd:
	def __init__(self, session):
		print "[VFD-INI] initializing"
		self.session = session
		self.service = None
		self.onClose = [ ]

		self.Console = Console()
		
		initVFD()
		
		global CirLanVfdInstance
		if CirLanVfdInstance is None:
			CirLanVfdInstance = CirLanVfd(session) 

	def shutdown(self):
		self.abort()

	def abort(self):
		print "[VFD-INI] aborting"

iniVFD = None
gReason = -1
mySession = None

def controliniVFD():
	global iniVFD
	global gReason
	global mySession

	if gReason == 0 and mySession != None and iniVFD == None:
		print "[VFD-INI] Starting !!"
		iniVFD = ini_vfd(mySession)
	elif gReason == 1 and iniVFD != None:
		print "[VFD-INI] Stopping !!"
		evfd.getInstance().vfd_symbol_network(0)
		iniVFD = None


def sessionstart(reason, **kwargs):
	print "[VFD-INI] AutoStarting ini_vfd"
	global iniVFD
	global gReason
	global mySession

	if kwargs.has_key("session"):
		mySession = kwargs["session"]
	else:
		gReason = reason
	controliniVFD()

def Plugins(**kwargs):
 	return [ PluginDescriptor(where=[PluginDescriptor.WHERE_AUTOSTART, PluginDescriptor.WHERE_SESSIONSTART], fnc=sessionstart)]