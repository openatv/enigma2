from Plugins.Plugin import PluginDescriptor
from Components.MultiContent import MultiContentEntryText, MultiContentEntryPixmapAlphaTest
from Components.ActionMap import ActionMap, HelpableActionMap, NumberActionMap
from Screens.Screen import Screen
from Components.Sources.List import List
from enigma import eSize, ePoint, eTimer, loadPNG, quitMainloop, eListbox, ePoint, RT_HALIGN_LEFT, RT_HALIGN_RIGHT, RT_HALIGN_CENTER, RT_VALIGN_CENTER, eListboxPythonMultiContent, gFont, getDesktop, ePicLoad, eServiceCenter, iServiceInformation, eServiceReference, iSeekableService, iPlayableService, iPlayableServicePtr
from Components.MenuList import MenuList
from Tools.LoadPixmap import LoadPixmap
from Components.Pixmap import Pixmap
from Components.Label import Label   
from Components.ServiceEventTracker import ServiceEventTracker, InfoBarBase
from Screens.InfoBarGenerics import InfoBarShowHide, NumberZap, InfoBarAudioSelection, InfoBarSubtitleSupport
from Screens.MessageBox import MessageBox
import servicewebts
from time import time
from streams import iptv_streams
from os import system

PLUGIN_PATH = '/usr/lib/enigma2/python/Plugins/Extensions/nStreamPlayer'

from enigma import addFont
try:
        addFont("%s/MyriadPro-Regular.otf" % PLUGIN_PATH, "RegularIPTV", 100, 1)
except Exception, ex: 
        print ex



def menu(menuid, **kwargs):
	if menuid == "mainmenu":
		return [("nStreamPlayer", Start_iptv_palyer, "nstreamplayer", 4)]
	return []

		
def Start_iptv_palyer(session, **kwargs):
	system("ethtool eth0 > /tmp/.eth0_test")
	zrodlo = open("/tmp/.eth0_test", 'r')
	for line in zrodlo.readlines():
		line = line.strip()
		if line.find('Link detected:') >= 0: # oscam
		    x = line.split(':',1)
		    addr = x[1].strip()
	if (addr=="yes"):
	  global STREAMS
	  STREAMS = iptv_streams()
	  STREAMS.get_list()
	  session.open(IPTVPlayer)
	else:
	  session.open(MessageBox, _("This plugin need internet connection. Please plug in ethernet cable and try again!"), MessageBox.TYPE_INFO, timeout=4)


class MyIptvPlaylist(Screen):
	skin = """	
	<screen name ="MyIptvPlaylist" position="0,0" size="1280,720" backgroundColor="#41000000" flags="wfNoBorder" title="Playlist" > 
		<widget name="feedlist" position="50,50" size="760,592" foregroundColorSelected="#ffffff" backgroundColor="#41000000" foregroundColor="#76addc" backgroundColorSelected="#41000000" selectionPixmap="%(path)s/img/x37.png"  enableWrapAround="1" zPosition="1" scrollbarMode="showOnDemand" transparent="0" />   
		<widget name="grouplist" foregroundColorSelected="#ffffff" backgroundColor="#41000000" foregroundColor="#76addc" backgroundColorSelected="#41000000" selectionPixmap="%(path)s/img/x37small.png" scrollbarMode="showOnDemand" position="826,92" size="380,552" zPosition="1"  />
		<ePixmap position="0,700"  size="1280,11" pixmap="%(path)s/img/tab_line.png"     zPosition="1" transparent="1" alphatest="blend" />
		<ePixmap position="147,664" pixmap="%(path)s/img/tab_active.png" size="204,37" zPosition="2" backgroundColor="#ffffff" alphatest="blend" />
		<ePixmap position="351,664" pixmap="%(path)s/img/tab_active.png" size="204,37" zPosition="2" backgroundColor="#ffffff" alphatest="blend" />
		<ePixmap position="155,671" size="25,25" pixmap="%(path)s/img/red.png"    zPosition="3" transparent="1" alphatest="blend" />
		<ePixmap position="359,671" size="25,25" pixmap="%(path)s/img/green.png"  zPosition="3" transparent="1" alphatest="blend" />
		<eLabel position="187,673" zPosition="4" size="140,24" halign="center" font="RegularIPTV;22" transparent="1" foregroundColor="#ffffff" backgroundColor="#41000000" text="All Channels" />
		<eLabel position="391,673" zPosition="4" size="140,24" halign="center" font="RegularIPTV;22" transparent="1" foregroundColor="#ffffff" backgroundColor="#41000000" text="Categories" />
		<!-- <widget backgroundColor="#41000000" foregroundColor="#ffffff" position="826,55" size="380,30"  name="pr_time" font="RegularIPTV;24" />  -->
		<!-- <widget backgroundColor="#41000000" foregroundColor="#ffffff" position="826,92" size="380,552" name="program" font="RegularIPTV;24" /> -->
	</screen>""" % {'path' : PLUGIN_PATH} 

	def __init__(self, session, index = None):
		Screen.__init__(self, session)   
		self.session = session  
		self.channel_list = STREAMS.iptv_list
		self.group_list	= STREAMS.groups
		self.index = index
		self.mode = 0
  
		self.mlist = MenuList([], enableWrapAround=True, content=eListboxPythonMultiContent)
		self.mlist.l.setFont(0, gFont('RegularIPTV', 22))
		self.mlist.l.setFont(1, gFont('RegularIPTV', 20)) 
		self.mlist.l.setFont(2, gFont('RegularIPTV', 14)) 
		self.mlist.l.setFont(3, gFont('RegularIPTV', 12))
		self.mlist.l.setItemHeight(37)  
		self["feedlist"] = self.mlist
		self.mlist.setList(map(channelEntryIPTVplaylist, self.channel_list))


		self.glist = MenuList([], enableWrapAround=True, content=eListboxPythonMultiContent)
		self.glist.l.setFont(0, gFont('RegularIPTV', 24))
		self.glist.l.setItemHeight(37) 
		self['grouplist'] = self.glist
		self.glist.setList(map(groupEntry, self.group_list))
		self['grouplist'].hide()
		
		self.glist.onSelectionChanged.append(self.update_channellist)
		self.mlist.onSelectionChanged.append(self.update_category)
		self.onShown.append(self.show_all)

		self["actions"] = HelpableActionMap(self, "nKTV", 
		{
			"red": self.show_all,
			"green": self.show_category,
			"ok": self.ok,
			"back": self.exit
		}, -1)
		

	def show_category(self):
		self['grouplist'].show()	
		self.mlist.selectionEnabled(0)
		self.glist.selectionEnabled(1) 
		self.mlist.setList(map(channelEntryIPTVplaylist, self.group_list[0][3]))
		self.mlist.moveToIndex(0)
		self.mode = 2


	def update_channellist(self):
		print self.glist.getSelectionIndex()
		group_index = self.glist.getSelectionIndex()
		self.channel_list = self.group_list[group_index][3]
		self.mlist.setList(map(channelEntryIPTVplaylist, self.channel_list))

		  
	def show_all(self):
		self.channel_list = STREAMS.iptv_list
		self['grouplist'].hide()
		self.mlist.setList(map(channelEntryIPTVplaylist, self.channel_list))
		self.mlist.moveToIndex(self.index)
		self.mlist.selectionEnabled(1)
		self.glist.selectionEnabled(0)
		self.mode = 0 
		
   	 
	def update_category(self):
		print 'update_category'

	def exit(self):
		if self.mode == 20:
			self.show_category()
		else:	
			self.close()
			
	def ok(self):
		if self.mode == 2:
			self['grouplist'].hide() 
			self.mlist.selectionEnabled(1)
			self.mlist.moveToIndex(0)
			self.mode = 20   
		elif self.mode != 2: 
			self.close(int(self.channel_list[self.mlist.getSelectionIndex()][0])-1)					
		
			
	
class IPTVPlayer(Screen, InfoBarBase, InfoBarShowHide, InfoBarAudioSelection, InfoBarSubtitleSupport):

	skin = """
	<screen name ="IPTVPlayer" position="0,550" size="1280,190" backgroundColor="#41000000" flags="wfNoBorder" title="IPTVplayer">
	    <ePixmap position="80,4" size="72,36" pixmap="%(path)s/img/72x36.png" zPosition="1" transparent="0" />
		<widget position="84,7" halign="center" size="64,28" foregroundColor="#ffffff" zPosition="2" name="channel_number" transparent="1" font="RegularIPTV;34"/>
		<widget position="160,7" size="650,34" foregroundColor="#ffffff" backgroundColor="#41000000" name="channel_name" font="RegularIPTV;34"/>
		<widget position="805,10" size="300,26" halign="right" foregroundColor="#f4df8d" backgroundColor="#41000000" name="group" font="RegularIPTV;26"/>
		<widget name="picon" position="120,68" size="35,35" backgroundColor="#41000000" />
		<ePixmap position="80,50" size="117,72" pixmap="%(path)s/img/pristavka.png" zPosition="10" transparent="1" alphatest="blend" />   	 
		<widget position="300,56" size="650,25" foregroundColor="#ffffff" backgroundColor="#41000000" name="programm" font="RegularIPTV;24"/>
	</screen>""" % {'path' : PLUGIN_PATH}


 	def __init__(self, session):
		Screen.__init__(self, session)
		InfoBarBase.__init__(self, steal_current_service=True)
		InfoBarShowHide.__init__(self)
		InfoBarAudioSelection.__init__(self)
		InfoBarSubtitleSupport.__init__(self)
		self['channel_name'] = Label('')
		self['picon'] = Pixmap()
		self['programm'] = Label('')
		self.InfoBar_NabDialog = Label('')
		self.session = session
		self['channel_number'] = Label('')
		self.channel_list = STREAMS.iptv_list
		self.group_list	= STREAMS.groups
		self.index = 0
		self.group_index = 0
		self['group'] = Label('')
		self.mode = 0

		self.oldService = self.session.nav.getCurrentlyPlayingServiceReference()
		self.onFirstExecBegin.append(self.play_channel)

		self["actions"] = HelpableActionMap(self, "nKTV",
		{
			"back": self.exit_box,
			"left": self.prevChannel,
			"right": self.nextChannel,
			"up": self.show_channel_list,
			"channelPlus": self.nextGroup,
			"channelMinus": self.prevGroup,   
		}, -1)                                            
			
		self["myNumberActions"] = NumberActionMap(["NumberActions", "InfobarAudioSelectionActions", "InfobarTeletextActions"],
		{   
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
		}, -1)


	def show_channel_list(self):
		self.session.openWithCallback(self.channel_answer, MyIptvPlaylist, self.index)
		
	def channel_answer(self, index = None): 
		if index > -1:
			self.index = index		
			self.play_channel()		
		
	def keyNumberGlobal(self, number):    
		self.session.openWithCallback(self.numberEntered, NumberZap, number)
		
	def numberEntered(self, num):
		self.index = num - 1
		if self.index >= 0:
			if self.index < len(self.channel_list):
				self.play_channel()			

	def play_channel(self): 
		print 'self.index'
		print self.index
		entry = self.channel_list[self.index]
		if self.mode == 0:
			self.group_index = entry[6] - 1
		self['channel_number'].setText('%i' % entry[0])
		self['channel_name'].setText(entry[1])
		self['programm'].setText(entry[3])
		self['picon'].instance.setPixmapFromFile('%s/picon35x35/%s' % (PLUGIN_PATH,entry[2]))
		self['group'].setText("[%i] %s" % (entry[6], entry[7]))
		
		if(entry[4]):
			id_s = 4114
		else:
			id_s = 4097
		url = entry[3]
		self.session.nav.stopService()
		sref = eServiceReference(id_s, 0, url)
		if entry[5]:
			sref.setData(2,int(entry[5])*1024)    
		self.session.nav.playService(sref)
		self.mode = 0
		
	def nextChannel(self):  
		self.index +=1
		if self.index == len(self.channel_list):
			self.index = 0          
		self.play_channel() 

	def prevChannel(self):
		self.index -=1
		if self.index == -1:
			self.index = len(self.channel_list)-1	
		self.play_channel()

	def nextGroup(self):
		self.mode = 1
		if self.group_index < len(self.group_list)-1:
			self.group_index = self.group_index + 1	
			print self.group_list[self.group_index] 	
			self.index = self.group_list[self.group_index][3][0][0]-1
		else:
			self.index = 0
		self.play_channel()		

	def prevGroup(self):
		self.mode = 1
		if self.group_index >= 1 :
			self.group_index = self.group_index - 1
			self.index = self.group_list[self.group_index][3][0][0]-1
		else:
			last_group = self.group_list - 1
			self.index = self.group_list[last_group][3][0][0]-1
		self.play_channel()	
			
	def exit_box(self):
		self.session.openWithCallback(self.exit, MessageBox, _("Exit Plugin?"), type=MessageBox.TYPE_YESNO)
		   
	def exit(self, message=None):
		if message:
			self.session.nav.playService(self.oldService)	
			self.close()

def groupEntry(entry):  
	menu_entry = [entry,
	(eListboxPythonMultiContent.TYPE_TEXT,5,7,60,37,0,RT_HALIGN_LEFT,'%i' % entry[0]),
	(eListboxPythonMultiContent.TYPE_TEXT,40,7,255,37,0,RT_HALIGN_LEFT,entry[1]),  
	(eListboxPythonMultiContent.TYPE_TEXT,290,7,50,37,0,RT_HALIGN_RIGHT, '(%s)' % entry[2])
	] 
	return menu_entry
				

def channelEntryIPTVplaylist(entry):  
	menu_entry = [entry,
	(eListboxPythonMultiContent.TYPE_TEXT,7,10,32,33,1,RT_HALIGN_CENTER,'%s' % entry[0]),
	(eListboxPythonMultiContent.TYPE_PIXMAP_ALPHATEST, 40, 1, 35, 35, loadPNG('%s/picon35x35/%s' % (PLUGIN_PATH, entry[2]) )),
	(eListboxPythonMultiContent.TYPE_TEXT,90,7,250,22,1,RT_HALIGN_LEFT,entry[1]),
	(eListboxPythonMultiContent.TYPE_TEXT,350,7,370,22,1,RT_HALIGN_LEFT,entry[3]),  
	(eListboxPythonMultiContent.TYPE_PIXMAP_ALPHATEST, 90, 28, 630, 3, loadPNG('%s/img/slider_1280x10_hbg.png' % PLUGIN_PATH))
	]  

	return menu_entry

def Plugins(**kwargs):
	return [
		#PluginDescriptor(name = "nStreamPlayer", description="plugin to watch video streams", where = PluginDescriptor.WHERE_MENU, fnc = menu),
		PluginDescriptor(name = "nStreamPlayer", description="plugin to watch video streams", where = PluginDescriptor.WHERE_PLUGINMENU, fnc=Start_iptv_palyer, icon="plugin.png")
	]

