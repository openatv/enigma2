#
#  SHOUTcast E2
#
#  $Id$
#
#  Coded by Dr.Best (c) 2010
#  Support: www.dreambox-tools.info
#
#  This plugin is licensed under the Creative Commons 
#  Attribution-NonCommercial-ShareAlike 3.0 Unported 
#  License. To view a copy of this license, visit
#  http://creativecommons.org/licenses/by-nc-sa/3.0/ or send a letter to Creative
#  Commons, 559 Nathan Abbott Way, Stanford, California 94305, USA.
#
#  Alternatively, this plugin may be distributed and executed on hardware which
#  is licensed by Dream Multimedia GmbH.

#  This plugin is NOT free software. It is open source, you are allowed to
#  modify it (if you keep the license), but it may not be commercially 
#  distributed other than under the conditions noted above.
#

from Plugins.Plugin import PluginDescriptor
from Screens.Screen import Screen
from Components.ActionMap import ActionMap
from Components.Label import Label
from enigma import eServiceReference
from enigma import eListboxPythonMultiContent, eListbox, gFont, \
	RT_HALIGN_LEFT, RT_HALIGN_RIGHT, RT_VALIGN_CENTER
from Tools.LoadPixmap import LoadPixmap
import xml.etree.cElementTree
from enigma import iPlayableService, iServiceInformation

from twisted.internet import reactor, defer
from twisted.web import client
from twisted.web.client import HTTPClientFactory
from Components.Pixmap import Pixmap
from enigma import ePicLoad
from Components.ScrollLabel import ScrollLabel
import string
import os
from enigma import getDesktop
from Components.config import config, ConfigSubsection, ConfigSelection, ConfigDirectory, ConfigYesNo, Config, ConfigInteger, ConfigSubList, ConfigText, getConfigListEntry, configfile
from Components.ConfigList import ConfigListScreen
from Screens.MessageBox import MessageBox
from Components.GUIComponent import GUIComponent
from Components.Sources.StaticText import StaticText
from urllib import quote
from twisted.web.client import downloadPage
from Screens.ChoiceBox import ChoiceBox
from Screens.VirtualKeyBoard import VirtualKeyBoard
from enigma import eTimer
from enigma import eConsoleAppContainer
from Components.Input import Input
from Screens.InputBox import InputBox
from Components.FileList import FileList
# for localized messages
from . import _

coverfiles = ("/tmp/.cover.ping", "/tmp/.cover.pong")
containerStreamripper = None
config.plugins.shoutcast = ConfigSubsection()
config.plugins.shoutcast.showcover = ConfigYesNo(default = True)
config.plugins.shoutcast.showinextensions = ConfigYesNo(default = False)
config.plugins.shoutcast.streamingrate = ConfigSelection(default="0", choices = [("0",_("All")), ("64",_(">= 64 kbps")), ("128",_(">= 128 kbps")), ("192",_(">= 192 kbps")), ("256",_(">= 256 kbps"))])
config.plugins.shoutcast.reloadstationlist = ConfigSelection(default="0", choices = [("0",_("Off")), ("1",_("every minute")), ("3",_("every three minutes")), ("5",_("every five minutes"))])
config.plugins.shoutcast.dirname = ConfigDirectory(default = "/hdd/streamripper/")
config.plugins.shoutcast.riptosinglefile = ConfigYesNo(default = False)
config.plugins.shoutcast.createdirforeachstream = ConfigYesNo(default = True)
config.plugins.shoutcast.addsequenceoutputfile = ConfigYesNo(default = False)
config.plugins.shoutcast.coverwidth = ConfigText (default = "200", fixed_size = False, visible_width = 8)
config.plugins.shoutcast.coverheight = ConfigText (default = "300", fixed_size = False, visible_width = 8)

devid = "fa1jo93O_raeF0v9"

class SHOUTcastGenre:
	def __init__(self, name = "", id = 0, haschilds = "false", parentid = 0, opened = "false"):
		self.name = name
		self.id = id
		self.haschilds = haschilds
		self.parentid = parentid
		self.opened = opened

class SHOUTcastStation:
	def __init__(self, name = "", mt = "", id = "", br = "", genre = "", ct = "", lc = "", ml = "", nsc = "", cst = ""):
		self.name = name.replace("- a SHOUTcast.com member station", "")
		self.mt = mt
		self.id = id
		self.br = br
		self.genre = genre
		self.ct = ct
		self.lc = lc
		self.ml = ml
		self.nsc = nsc
		self.cst = cst

class Favorite:
	def __init__(self, configItem = None):
		self.configItem = configItem

class myHTTPClientFactory(HTTPClientFactory):
	def __init__(self, url, method='GET', postdata=None, headers=None,
			agent="SHOUTcast", timeout=0, cookies=None,
			followRedirect=1, lastModified=None, etag=None):
		HTTPClientFactory.__init__(self, url, method=method, postdata=postdata,
		headers=headers, agent=agent, timeout=timeout, cookies=cookies, followRedirect=followRedirect)

	def clientConnectionLost(self, connector, reason):
		lostreason=("Connection was closed cleanly" in vars(reason))
		if lostreason==None:
			print"[SHOUTcast] Lost connection, reason: %s ,trying to reconnect!" %reason
			connector.connect()

	def clientConnectionFailed(self, connector, reason):
		print"[SHOUTcast] connection failed, reason: %s,trying to reconnect!" %reason
		connector.connect()

def sendUrlCommand(url, contextFactory=None, timeout=60, *args, **kwargs):
	scheme, host, port, path = client._parse(url)
	factory = myHTTPClientFactory(url, *args, **kwargs)
	# print "scheme=%s host=%s port=%s path=%s\n" % (scheme, host, port, path)
	reactor.connectTCP(host, port, factory, timeout=timeout)
	return factory.deferred

def main(session,**kwargs):
	session.open(SHOUTcastWidget)

def Plugins(**kwargs):
	list = [PluginDescriptor(name="SHOUTcast", description=_("listen to shoutcast internet-radio"), where = [PluginDescriptor.WHERE_PLUGINMENU], icon="plugin.png", fnc=main)] # always show in plugin menu
	if config.plugins.shoutcast.showinextensions.value:
		list.append (PluginDescriptor(name="SHOUTcast", description=_("listen to shoutcast internet-radio"), where = [PluginDescriptor.WHERE_EXTENSIONSMENU], fnc=main))
	return list

class SHOUTcastWidget(Screen):

	GENRELIST = 0
	STATIONLIST = 1
	FAVORITELIST = 2
	SEARCHLIST = 3

	STREAMRIPPER_BIN = '/usr/bin/streamripper'

	SC = 'http://api.shoutcast.com'
	SCY = 'http://yp.shoutcast.com'

	FAVORITE_FILE_DEFAULT = '/usr/lib/enigma2/python/Plugins/Extensions/SHOUTcast/favorites'
	FAVORITE_FILE_OLD = '/usr/lib/enigma2/python/Plugins/Extensions/SHOUTcast/favorites.user'
	FAVORITE_FILE = '/etc/enigma2/SHOUTcast.favorites'

	sz_w = getDesktop(0).size().width() - 90
	sz_h = getDesktop(0).size().height() - 95
	print "[SHOUTcast] desktop size %dx%d\n" % (sz_w+90, sz_h+100)
	if sz_h < 500:
		sz_h += 4
	skin = """
		<screen name="SHOUTcastWidget" position="center,65" title="SHOUTcast" size="%d,%d">
			<ePixmap position="5,0" zPosition="4" size="140,40" pixmap="skin_default/buttons/red.png" transparent="1" alphatest="on" />
			<ePixmap position="150,0" zPosition="4" size="140,40" pixmap="skin_default/buttons/green.png" transparent="1" alphatest="on" />
			<ePixmap position="295,0" zPosition="4" size="140,40" pixmap="skin_default/buttons/yellow.png" transparent="1" alphatest="on" />
			<ePixmap position="440,0" zPosition="4" size="140,40" pixmap="skin_default/buttons/blue.png" transparent="1" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/key_menu.png" position="585,10" zPosition="0" size="35,25" alphatest="on" />
			<widget render="Label" source="key_red" position="5,0" size="140,40" zPosition="5" valign="center" halign="center" backgroundColor="red" font="Regular;21" transparent="1" foregroundColor="white" shadowColor="black" shadowOffset="-1,-1" />
			<widget render="Label" source="key_green" position="150,0" size="140,40" zPosition="5" valign="center" halign="center" backgroundColor="red" font="Regular;21" transparent="1" foregroundColor="white" shadowColor="black" shadowOffset="-1,-1" />
			<widget render="Label" source="key_yellow" position="295,0" size="140,40" zPosition="5" valign="center" halign="center" backgroundColor="red" font="Regular;21" transparent="1" foregroundColor="white" shadowColor="black" shadowOffset="-1,-1" />
			<widget render="Label" source="key_blue" position="440,0" size="140,40" zPosition="5" valign="center" halign="center" backgroundColor="red" font="Regular;21" transparent="1" foregroundColor="white" shadowColor="black" shadowOffset="-1,-1" />
			<widget name="headertext" position="5,47" zPosition="1" size="%d,23" font="Regular;20" transparent="1"  backgroundColor="#00000000"/>
			<widget name="statustext" position="5,240" zPosition="1" size="%d,90" font="Regular;20" halign="center" valign="center" transparent="0"  backgroundColor="#00000000"/>
			<widget name="list" position="5,80" zPosition="2" size="%d,%d" scrollbarMode="showOnDemand" transparent="0"  backgroundColor="#00000000"/>
			<widget name="titel" position="115,%d" zPosition="1" size="%d,40" font="Regular;18" transparent="1"  backgroundColor="#00000000"/>
			<widget name="station" position="115,%d" zPosition="1" size="%d,40" font="Regular;18" transparent="1"  backgroundColor="#00000000"/>
			<widget name="console" position="115,%d" zPosition="1" size="%d,40" font="Regular;18" transparent="1"  backgroundColor="#00000000"/>
			<widget name="cover" zPosition="2" position="5,%d" size="102,110" alphatest="blend" />
			<ePixmap position="%d,41" zPosition="4" size="120,35" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/SHOUTcast/shoutcast-logo1-fs8.png" transparent="1" alphatest="on" />
		</screen>""" %(
			sz_w, sz_h, # size
			sz_w - 135, # size headertext
			sz_w - 100, # size statustext
			sz_w - 10, sz_h - 205, # size list
			sz_h - 105, # position titel
			sz_w - 125, # size titel
			sz_h - 70, # position station
			sz_w - 125, # size station
			sz_h - 25, # position console
			sz_w - 125, # size console
			sz_h - 105, # position cover
			sz_w - 125, # position logo
			)
	
	def __init__(self, session):
		self.session = session
		Screen.__init__(self, session)
		self.oldtitle = None
		self.currentcoverfile = 0
		self.currentGoogle = None
		self.nextGoogle = None
		self.currPlay = None
		self.CurrentService = self.session.nav.getCurrentlyPlayingServiceReference()
		self.session.nav.stopService()
		self.session.nav.event.append(self.__event)
		self["cover"] = Cover()
		self["key_red"] = StaticText(_("Record"))
		self["key_green"] = StaticText(_("Genres"))
		self["key_yellow"] = StaticText(_("Stations"))
		self["key_blue"] = StaticText(_("Favorites"))
		self.mode = self.FAVORITELIST
		self["list"] = SHOUTcastList()
		self["list"].connectSelChanged(self.onSelectionChanged)
		self["statustext"] = Label(_("Getting SHOUTcast genre list..."))
		self["actions"] = ActionMap(["WizardActions", "DirectionActions", "ColorActions", "EPGSelectActions"],
		{
			"ok": self.ok_pressed,
			"back": self.close,
			"menu": self.menu_pressed,
			"red": self.red_pressed,
			"green": self.green_pressed,
			"yellow": self.yellow_pressed,
			"blue": self.blue_pressed,
			
		}, -1)
		self.stationList = []
		self.stationListIndex = 0
		self.genreList = []
		self.genreListIndex = 0
		self.favoriteList = []
		self.favoriteListIndex = 0

		self.favoriteConfig = Config()
		if os.path.exists(self.FAVORITE_FILE):
			self.favoriteConfig.loadFromFile(self.FAVORITE_FILE)
		elif os.path.exists(self.FAVORITE_FILE_OLD):
			self.favoriteConfig.loadFromFile(self.FAVORITE_FILE_OLD)
		else:
			self.favoriteConfig.loadFromFile(self.FAVORITE_FILE_DEFAULT)
		self.favoriteConfig.entriescount =  ConfigInteger(0)
		self.favoriteConfig.Entries = ConfigSubList()
		self.initFavouriteConfig()
		self.stationListXML = ""
		self["titel"] = Label()
		self["station"] = Label()
		self["headertext"] = Label()
		self["console"] = Label()
		self.headerTextString = ""
		self.stationListHeader = ""
		self.tunein = ""
		self.searchSHOUTcastString = ""
		self.currentStreamingURL = ""
		self.currentStreamingStation = ""
		self.stationListURL = ""
		self.onClose.append(self.__onClose)
		self.onLayoutFinish.append(self.getFavoriteList)

		self.reloadStationListTimer = eTimer()
		self.reloadStationListTimer.timeout.get().append(self.reloadStationListTimerTimeout)
		self.reloadStationListTimerVar = int(config.plugins.shoutcast.reloadstationlist.value)

		self.visible = True

		global containerStreamripper
		if containerStreamripper is None:
			containerStreamripper = eConsoleAppContainer()

		containerStreamripper.dataAvail.append(self.streamripperDataAvail)
		containerStreamripper.appClosed.append(self.streamripperClosed)

		if containerStreamripper.running():
			self["key_red"].setText(_("Stop record"))
			# just to hear to recording music when starting the plugin...
			self.currentStreamingStation = _("Recording stream station")
			self.playServiceStream("http://localhost:9191")

	def streamripperClosed(self, retval):
		if retval == 0:
			self["console"].setText("")
		self["key_red"].setText(_("Record"))

	def streamripperDataAvail(self, data):
		sData = data.replace('\n','')
		self["console"].setText(sData)

	def stopReloadStationListTimer(self):
		if self.reloadStationListTimer.isActive():
			self.reloadStationListTimer.stop()

	def reloadStationListTimerTimeout(self):
		self.stopReloadStationListTimer()
		if self.mode == self.STATIONLIST:
			# print "[SHOUTcast] reloadStationList: %s " % self.stationListURL
			sendUrlCommand(self.stationListURL, None,10).addCallback(self.callbackStationList).addErrback(self.callbackStationListError)

	def InputBoxStartRecordingCallback(self, returnValue = None):
		if returnValue:
			recordingLength =  int(returnValue) * 60
			if not os.path.exists(config.plugins.shoutcast.dirname.value):
				os.mkdir(config.plugins.shoutcast.dirname.value)
			args = []
			args.append(self.currentStreamingURL)
			args.append('-d')
			args.append(config.plugins.shoutcast.dirname.value)
			args.append('-r')
			args.append('9191')
			if recordingLength != 0:
				args.append('-l')
				args.append("%d" % int(recordingLength))
			if config.plugins.shoutcast.riptosinglefile.value:
				args.append('-a')
				args.append('-A')
			if not config.plugins.shoutcast.createdirforeachstream.value:
				args.append('-s')
			if config.plugins.shoutcast.addsequenceoutputfile.value:
				args.append('-q')
			cmd = [self.STREAMRIPPER_BIN, self.STREAMRIPPER_BIN] + args
			containerStreamripper.execute(*cmd)
			self["key_red"].setText(_("Stop record"))

	def deleteRecordingConfirmed(self,val):
		if val:
			containerStreamripper.sendCtrlC()

	def red_pressed(self):
		if containerStreamripper.running():
			self.session.openWithCallback(self.deleteRecordingConfirmed, MessageBox, _("Do you really want to stop the recording?"))
		else:
			if len(self.currentStreamingURL) != 0:
				self.session.openWithCallback(self.InputBoxStartRecordingCallback, InputBox, windowTitle = _("Recording length"),  title=_("Enter in minutes (0 means unlimited)"), text="0", type=Input.NUMBER)
			else:
				self.session.open(MessageBox, _("Only running streamings can be recorded!"), type = MessageBox.TYPE_INFO,timeout = 20 )

	def green_pressed(self):
		if self.mode != self.GENRELIST:
			self.stopReloadStationListTimer()
			self.mode = self.GENRELIST
		if not self.genreList:
			self.getGenreList()
		else:
			self.showGenreList()

	def yellow_pressed(self):
		if self.mode != self.STATIONLIST:
			if len(self.stationList):
				self.mode = self.STATIONLIST
				self.headerTextString = _("SHOUTcast station list for %s") % self.stationListHeader
				self["headertext"].setText(self.headerTextString)
				self["list"].setMode(self.mode)
				self["list"].setList([ (x,) for x in self.stationList])
				self["list"].moveToIndex(self.stationListIndex)
				if self.reloadStationListTimerVar != 0:
					self.reloadStationListTimer.start(60000 * self.reloadStationListTimerVar)

	def blue_pressed(self):
		if self.mode != self.FAVORITELIST:
			self.stopReloadStationListTimer()
			self.getFavoriteList(self.favoriteListIndex)

	def getFavoriteList(self, favoriteListIndex = 0):
		self["statustext"].setText("")
		self.headerTextString = _("Favorite list")
		self["headertext"].setText(self.headerTextString)
		self.mode = self.FAVORITELIST
		self["list"].setMode(self.mode)
		favoriteList = []
		for item in self.favoriteConfig.Entries:
			favoriteList.append(Favorite(configItem=item))
		self["list"].setList([ (x,) for x in favoriteList])
		if len(favoriteList):
			self["list"].moveToIndex(favoriteListIndex)
		self["list"].show()

	def getGenreList(self, genre = "all" , id = 0):
		self["headertext"].setText("")
		self["statustext"].setText(_("Getting SHOUTcast genre list for %s..." % genre))
		self["list"].hide()
		if len(devid) > 8:
			url = self.SC + "/genre/secondary?parentid=%s&k=%s&f=xml" % (id, devid)
		else:
			url = "http://207.200.98.1/sbin/newxml.phtml"
		sendUrlCommand(url, None,10).addCallback(self.callbackGenreList).addErrback(self.callbackGenreListError)

	def callbackGenreList(self, xmlstring):
		self["headertext"].setText(_("SHOUTcast genre list"))
		self.genreListIndex = 0
		self.mode = self.GENRELIST
		self.genreList = self.fillGenreList(xmlstring)
		self["statustext"].setText("")
		if not len(self.genreList):
			self["statustext"].setText(_("Got 0 genres. Could be a network problem.\nPlease try again..."))
		else:
			self.showGenreList()

	def callbackGenreListError(self, error = None):
		if error is not None:
			try:
				self["list"].hide()
				self["statustext"].setText(_("%s\nPress green-button to try again...") % str(error.getErrorMessage()))
			except: pass
		
	def fillGenreList(self, xmlstring):
		genreList = []
		# print "[SHOUTcast] fillGenreList\n%s" % xmlstring
		try:
			root = xml.etree.cElementTree.fromstring(xmlstring)
		except: return []
		data = root.find("data")
		if data == None:
			print "[SHOUTcast] could not find data tag, assume flat listing\n"
			return [SHOUTcastGenre(name=childs.get("name")) for childs in root.findall("genre")]
		for glist in data.findall("genrelist"):
			for childs in glist.findall("genre"):
				gn = childs.get("name")
				gid = childs.get("id")
				gparentid = childs.get("parentid")
				ghaschilds = childs.get("haschildren")
				#print "[SHOUTcast] Genre %s id=%s parent=%s haschilds=%s\n" % (gn, gid, gparentid, ghaschilds)
				genreList.append(SHOUTcastGenre(name = gn, id = gid, parentid = gparentid, haschilds = ghaschilds))
				if ghaschilds == "true":
					for childlist in childs.findall("genrelist"):
						for genre in childlist.findall("genre"):
							gn = genre.get("name")
							gid = genre.get("id")
							gparentid = genre.get("parentid")
							ghaschilds = genre.get("haschildren")
							# print "[SHOUTcast]   Genre %s id=%s parent=%s haschilds=%s\n" % (gn, gid, gparentid, ghaschilds)
							genreList.append(SHOUTcastGenre(name = gn, id = gid, parentid = gparentid, haschilds = ghaschilds))
		return genreList

	def showGenreList(self):
		self["headertext"].setText(_("SHOUTcast genre list"))
		self["list"].setMode(self.mode)
		self["list"].setList([ (x,) for x in self.genreList])
		self["list"].moveToIndex(self.genreListIndex)
		self["list"].show()

	def onSelectionChanged(self):
		pass
		# till I find a better solution
#		if self.mode == self.STATIONLIST:
#			self.stationListIndex = self["list"].getCurrentIndex()
#		elif self.mode == self.FAVORITELIST:
#			self.favoriteListIndex = self["list"].getCurrentIndex()
#		elif self.mode == self.GENRELIST:
#			self.genreListIndex = self["list"].getCurrentIndex()

	def ok_pressed(self):
		if self.visible:
			sel = None
			try:
				sel = self["list"].l.getCurrentSelection()[0]
			except:return
			if sel is None:
				return
			else:
				if self.mode == self.GENRELIST:
					self.genreListIndex = self["list"].getCurrentIndex()
					self.getStationList(sel.name)
				elif self.mode == self.STATIONLIST:
					self.stationListIndex = self["list"].getCurrentIndex()
					self.stopPlaying()
					if len(devid) > 8:
						url = self.SCY + "/sbin/tunein-station.pls?id=%s" % (sel.id)
					self["list"].hide()
					self["statustext"].setText(_("Getting streaming data from\n%s") % sel.name)
					self.currentStreamingStation = sel.name
					sendUrlCommand(url, None, 10).addCallback(self.callbackPLS).addErrback(self.callbackStationListError)
				elif self.mode == self.FAVORITELIST:
					self.favoriteListIndex = self["list"].getCurrentIndex()
					if sel.configItem.type.value == "url":
						self.stopPlaying()
						self["headertext"].setText(self.headerTextString)
						self.currentStreamingStation = sel.configItem.name.value
						self.playServiceStream(sel.configItem.text.value)
					elif sel.configItem.type.value == "pls":
						self.stopPlaying()
						url = sel.configItem.text.value
						self["list"].hide()
						self["statustext"].setText(_("Getting streaming data from\n%s") % sel.configItem.name.value)
						self.currentStreamingStation = sel.configItem.name.value
						sendUrlCommand(url, None,10).addCallback(self.callbackPLS).addErrback(self.callbackStationListError)
					elif sel.configItem.type.value == "genre":
						self.getStationList(sel.configItem.name.value)
				elif self.mode == self.SEARCHLIST and self.searchSHOUTcastString != "":
					self.searchSHOUTcast(self.searchSHOUTcastString)
		else:
			self.showWindow()

	def stopPlaying(self):
		self.currentStreamingURL = ""
		self.currentStreamingStation = ""
		self["headertext"].setText("")
		self["titel"].setText("")
		self["station"].setText("")
		self.summaries.setText("")
		if config.plugins.shoutcast.showcover.value:
			self["cover"].doHide()
		self.session.nav.stopService()
		
	def callbackPLS(self, result):
		self["headertext"].setText(self.headerTextString)
		found = False
		parts = string.split(result,"\n")
		for lines in parts:
			if lines.find("File1=") != -1:
				line = string.split(lines,"File1=")
				found = True
				self.playServiceStream(line[-1].rstrip().strip())
				
		if found:
			self["statustext"].setText("")
			self["list"].show()
		else:
			self.currentStreamingStation = ""
			self["statustext"].setText(_("No streaming data found..."))
			self["list"].show()
	def getStationList(self,genre):
		self.stationListHeader = _("genre %s") % genre
		self.headerTextString = _("SHOUTcast station list for %s") % self.stationListHeader
		self["headertext"].setText("")
		self["statustext"].setText(_("Getting %s") %  self.headerTextString)
		self["list"].hide()
		if len(devid) > 8:
			self.stationListURL = self.SC + "/station/advancedsearch&f=xml&k=%s&search=%s" % (devid, genre)
		else:
			self.stationListURL = "http://207.200.98.1/sbin/newxml.phtml?genre=%s" % genre
		self.stationListIndex = 0
		sendUrlCommand(self.stationListURL, None, 10).addCallback(self.callbackStationList).addErrback(self.callbackStationListError)

	def callbackStationList(self, xmlstring):
		self.searchSHOUTcastString = ""
		self.stationListXML = xmlstring
		self["headertext"].setText(self.headerTextString)
		self.mode = self.STATIONLIST
		self["list"].setMode(self.mode)
		self.stationList = self.fillStationList(xmlstring)
		self["statustext"].setText("")
		self["list"].setList([ (x,) for x in self.stationList])
		if len(self.stationList):
			self["list"].moveToIndex(self.stationListIndex)
		self["list"].show()
		if self.reloadStationListTimerVar != 0:
			self.reloadStationListTimer.start(1000 * 60)

	def fillStationList(self,xmlstring):
		stationList = []
		try:
			root = xml.etree.cElementTree.fromstring(xmlstring)
		except: return []
		config_bitrate = int(config.plugins.shoutcast.streamingrate.value)
		data = root.find("data")
		if data == None:
			print "[SHOUTcast] could not find data tag\n"
			return []
		for slist in data.findall("stationlist"):
			for childs in slist.findall("tunein"):
				self.tunein = childs.get("base")
			for childs in slist.findall("station"):
				try: bitrate = int(childs.get("br"))
				except: bitrate = 0
				if bitrate >= config_bitrate:
					stationList.append(SHOUTcastStation(name = childs.get("name"), 
									mt = childs.get("mt"), id = childs.get("id"), br = childs.get("br"), 
									genre = childs.get("genre"), ct = childs.get("ct"), lc = childs.get("lc"), ml = childs.get("ml"), nsc = childs.get("nsc"),
									cst = childs.get("cst")))
		return stationList

	def menu_pressed(self):
		if not self.visible:
			self.showWindow()
		options = [(_("Config"), self.config),(_("Search"), self.search),]
		if self.mode == self.FAVORITELIST and self.getSelectedItem() is not None:
			options.extend(((_("rename current selected favorite"), self.renameFavorite),))
			options.extend(((_("remove current selected favorite"), self.removeFavorite),))
		elif self.mode == self.GENRELIST and self.getSelectedItem() is not None:
			options.extend(((_("Add current selected genre to favorite"), self.addGenreToFavorite),))
		elif self.mode == self.STATIONLIST and self.getSelectedItem() is not None:
			options.extend(((_("Add current selected station to favorite"), self.addStationToFavorite),))
		if len(self.currentStreamingURL) != 0:
			options.extend(((_("Add current playing stream to favorite"), self.addCurrentStreamToFavorite),))
		options.extend(((_("Hide"), self.hideWindow),))
		self.session.openWithCallback(self.menuCallback, ChoiceBox,list = options)

	def menuCallback(self, ret):
		ret and ret[1]()

	def hideWindow(self):
		self.visible = False
		self.hide()

	def showWindow(self):
		self.visible = True
		self.show()

	def addGenreToFavorite(self):
		sel = self.getSelectedItem()
		if sel is not None:
			self.addFavorite(name = sel.name, text = sel.name, favoritetype = "genre")			

	def addStationToFavorite(self):
		sel = self.getSelectedItem()
		if sel is not None:
			self.addFavorite(name = sel.name, text = self.SCY + "/sbin/tunein-station.pls?id=%s" % (sel.id), favoritetype = "pls", audio = sel.mt, bitrate = sel.br)			

	def addCurrentStreamToFavorite(self):
		self.addFavorite(name = self.currentStreamingStation, text = self.currentStreamingURL, favoritetype = "url")

	def addFavorite(self, name = "", text = "", favoritetype = "", audio = "", bitrate = ""):
		self.favoriteConfig.entriescount.value = self.favoriteConfig.entriescount.value + 1
		self.favoriteConfig.entriescount.save()
		newFavorite = self.initFavouriteEntryConfig()
		newFavorite.name.value = name
		newFavorite.text.value = text
		newFavorite.type.value = favoritetype
		newFavorite.audio.value = audio
		newFavorite.bitrate.value = bitrate
		newFavorite.save()
		self.favoriteConfig.saveToFile(self.FAVORITE_FILE)

	def renameFavorite(self):
		sel = self.getSelectedItem()
		if sel is not None:
			self.session.openWithCallback(self.renameFavoriteFinished, VirtualKeyBoard, title = _("Enter new name for favorite item"), text = sel.configItem.name.value)

	def renameFavoriteFinished(self, text = None):
		if text:
			sel = self.getSelectedItem()
			sel.configItem.name.value = text
			sel.configItem.save()
			self.favoriteConfig.saveToFile(self.FAVORITE_FILE)
			self.favoriteListIndex = 0
			self.getFavoriteList()


	def removeFavorite(self):
		sel = self.getSelectedItem()
		if sel is not None:
			self.favoriteConfig.entriescount.value = self.favoriteConfig.entriescount.value - 1
			self.favoriteConfig.entriescount.save()
			self.favoriteConfig.Entries.remove(sel.configItem)
			self.favoriteConfig.Entries.save()
			self.favoriteConfig.saveToFile(self.FAVORITE_FILE)
			self.favoriteListIndex = 0
			self.getFavoriteList()

	def search(self):
		self.session.openWithCallback(self.searchSHOUTcast, VirtualKeyBoard, title = _("Enter text to search for"))

	def searchSHOUTcast(self, searchstring = None):
		if searchstring:
			self.stopReloadStationListTimer()
			self.stationListHeader = _("search-criteria %s") % searchstring
			self.headerTextString = _("SHOUTcast station list for %s") % self.stationListHeader
			self["headertext"].setText("")
			self["statustext"].setText(_("Searching SHOUTcast for %s...") % searchstring)
			self["list"].hide()
			if len(devid) > 8:
			   self.stationListURL = self.SC + "/station/advancedsearch&f=xml&k=%s&search=%s" % (devid, searchstring)
			else:
			   self.stationListURL = "http://207.200.98.1/sbin/newxml.phtml?search=%s" % searchstring
			self.mode = self.SEARCHLIST
			self.searchSHOUTcastString = searchstring
			self.stationListIndex = 0
			sendUrlCommand(self.stationListURL, None, 10).addCallback(self.callbackStationList).addErrback(self.callbackStationListError)

	def config(self):
		self.stopReloadStationListTimer()
		self.session.openWithCallback(self.setupFinished, SHOUTcastSetup)

	def setupFinished(self, result):
		if result:
			if config.plugins.shoutcast.showcover.value:
				self["cover"].doShow()
			else:
				self["cover"].doHide()
			if self.mode == self.STATIONLIST:
				self.reloadStationListTimerVar = int(config.plugins.shoutcast.reloadstationlist.value)
				self.stationListIndex = 0
				self.callbackStationList(self.stationListXML)

	def callbackStationListError(self, error = None):
		if error is not None:
			try:
				self["list"].hide()
				self["statustext"].setText(_("%s\nPress OK to try again...") % str(error.getErrorMessage()))
			except: pass

	def Error(self, error = None):
		if error is not None:
			# print "[SHOUTcast] Error: %s\n" % error
			try:
				self["list"].hide()
				self["statustext"].setText(str(error.getErrorMessage()))
			except: pass
		if self.nextGoogle:
			self.currentGoogle = self.nextGoogle
			self.nextGoogle = None
			sendUrlCommand(self.currentGoogle, None, 10).addCallback(self.GoogleImageCallback).addErrback(self.Error)
		else:
			self.currentGoogle = None
	
	def __onClose(self):
		global coverfiles
		for f in coverfiles:
			try:
				os.unlink(f)
			except:
				pass
		self.stopReloadStationListTimer()
		self.session.nav.playService(self.CurrentService)
		self.session.nav.event.remove(self.__event)
		self.currPlay = None
		containerStreamripper.dataAvail.remove(self.streamripperDataAvail)
		containerStreamripper.appClosed.remove(self.streamripperClosed)

	def GoogleImageCallback(self, result):
		global coverfiles
		if self.nextGoogle:
			self.currentGoogle = self.nextGoogle
			self.nextGoogle = None
			sendUrlCommand(self.currentGoogle, None, 10).addCallback(self.GoogleImageCallback).addErrback(self.Error)
			return
		self.currentGoogle = None
		foundPos = result.find("unescapedUrl\":\"")
		foundPos2 = result.find("\",\"url\":\"")
		if foundPos != -1 and foundPos2 != -1:
			url=result[foundPos+15:foundPos2]
			if len(url)>15:
				url= url.replace(" ", "%20")
				print "download url: %s " % url
				validurl = True
			else:
				validurl = False
				print "[SHOUTcast] invalid cover url or pictureformat!"
				if config.plugins.shoutcast.showcover.value:
					self["cover"].doHide()
			if validurl:
				self.currentcoverfile = (self.currentcoverfile + 1) % len(coverfiles)
				try:
					os.unlink(coverfiles[self.currentcoverfile-1])
				except:
					pass
				coverfile = coverfiles[self.currentcoverfile]
				print "[SHOUTcast] downloading cover from %s to %s" % (url, coverfile)
				downloadPage(url, coverfile).addCallback(self.coverDownloadFinished, coverfile).addErrback(self.coverDownloadFailed)

	def coverDownloadFailed(self,result):
		print "[SHOUTcast] cover download failed:", result
		if config.plugins.shoutcast.showcover.value:
			self["statustext"].setText(_("Error downloading cover..."))
			self["cover"].doHide()

	def coverDownloadFinished(self, result, coverfile):
		if config.plugins.shoutcast.showcover.value:
			print "[SHOUTcast] cover download finished:", coverfile
			self["statustext"].setText("")
			self["cover"].updateIcon(coverfile)
			self["cover"].doShow()
		
	def __event(self, ev):
		if ev != 17:
			print "[SHOUTcast] EVENT ==>", ev
		if ev == 1 or ev == 4:
			print "[SHOUTcast] Tuned in, playing now!"
		if ev == 3 or ev == 7:
			self["statustext"].setText(_("Stream stopped playing, playback of stream stopped!"))
			print "[SHOUTcast] Stream stopped playing, playback of stream stopped!"
			self.session.nav.stopService()
		if ev == 5:
			if not self.currPlay:
				return
			sTitle = self.currPlay.info().getInfoString(iServiceInformation.sTagTitle)
			if self.oldtitle != sTitle:
				self.oldtitle=sTitle
				sTitle = sTitle.replace("Title:", "")[:55]
				if config.plugins.shoutcast.showcover.value:
					searchpara="album cover "
					if sTitle:
						url = "http://ajax.googleapis.com/ajax/services/search/images?v=1.0&q=%s%s&biw=%s&bih=%s&ift=jpg&ift=gif&ift=png" % (quote(searchpara), quote(sTitle), config.plugins.shoutcast.coverwidth.value, config.plugins.shoutcast.coverheight.value)
					else:
						url = "http://ajax.googleapis.com/ajax/services/search/images?v=1.0&q=no+cover+pic&biw=%s&bih=%s&ift=jpg&ift=gif&ift=png" % (config.plugins.shoutcast.coverwidth.value, config.plugins.shoutcast.coverheight.value)
					print "[SHOUTcast] coverurl = %s " % url
					if self.currentGoogle:
						self.nextGoogle = url
					else:
						self.currentGoogle = url
						sendUrlCommand(url, None, 10).addCallback(self.GoogleImageCallback).addErrback(self.Error)
				if len(sTitle) == 0:
					sTitle = "n/a"
				title = _("Title: %s") % sTitle
				print "[SHOUTcast] Title: %s " % title
				self["titel"].setText(title)
				self.summaries.setText(title)
			else:
				print "[SHOUTcast] Ignoring useless updated info provided by streamengine!"
		#if ev == 6 or (ev > 8 and ev != 17):
		#	print "[SHOUTcast] Abnormal event %s from stream, so stop playing!" % ev
		#	self["statustext"].setText(_("Abnormal event from stream, aborting!"))
		#	self.session.nav.stopService()
			
	def playServiceStream(self, url):
		self.currPlay = None
		self.session.nav.stopService()
		if config.plugins.shoutcast.showcover.value:
			self["cover"].doHide()
		sref = eServiceReference("4097:0:0:0:0:0:0:0:0:0:%s" % url.replace(':', '%3a'))
		try:
			self.session.nav.playService(sref)
		except:
			print "[SHOUTcast] Could not play %s" % sref
		self.currPlay = self.session.nav.getCurrentService()
		self.currentStreamingURL = url
		self["titel"].setText(_("Title: n/a"))
		self["station"].setText(_("Station: %s") % self.currentStreamingStation)

	def createSummary(self):
		return SHOUTcastLCDScreen

	def initFavouriteEntryConfig(self):
		self.favoriteConfig.Entries.append(ConfigSubsection())
		i = len(self.favoriteConfig.Entries) -1
		self.favoriteConfig.Entries[i].name = ConfigText(default = "")
		self.favoriteConfig.Entries[i].text = ConfigText(default = "")
		self.favoriteConfig.Entries[i].type = ConfigText(default = "")
		self.favoriteConfig.Entries[i].audio = ConfigText(default = "")
		self.favoriteConfig.Entries[i].bitrate = ConfigText(default = "")
		return self.favoriteConfig.Entries[i]

	def initFavouriteConfig(self):
		count = self.favoriteConfig.entriescount.value
		if count != 0:
			i = 0
			while i < count:
				self.initFavouriteEntryConfig()
				i += 1

	def getSelectedItem(self):
		sel = None
		try:
			sel = self["list"].l.getCurrentSelection()[0]
		except:return None
		return sel

class Cover(Pixmap):
	visible = 0

	def __init__(self):
		Pixmap.__init__(self)
		self.picload = ePicLoad()
		self.picload.PictureData.get().append(self.paintIconPixmapCB)
		self.decoding = None
		self.decodeNext = None

	def doShow(self):
		if not self.visible == 1:
			self.visible = 1
			print "[SHOUTcast] cover visible %s self.show" % self.visible
			self.show()

	def doHide(self):
		if not self.visible == 0:
			self.visible = 0
			print "[SHOUTcast] cover visible %s self.hide" % self.visible
			self.hide()

	def onShow(self):
		Pixmap.onShow(self)
		coverwidth=self.instance.size().width()
		if int(config.plugins.shoutcast.coverwidth.value) > coverwidth:
			config.plugins.shoutcast.coverwidth.value = str(coverwidth)
		coverheight=self.instance.size().height()
		if int(config.plugins.shoutcast.coverheight.value) > coverheight:
			config.plugins.shoutcast.coverheight.value = str(coverheight)	
		self.picload.setPara((coverwidth, coverheight, 1, 1, False, 1, "#00000000"))
		
	def paintIconPixmapCB(self, picInfo=None):
		ptr = self.picload.getData()
		if ptr != None:
			self.instance.setPixmap(ptr.__deref__())
			if self.visible:
				self.doShow()
		if self.decodeNext is not None:
			self.decoding = self.decodeNext
			self.decodeNext = None
			if self.picload.startDecode(self.decoding) != 0:
				print "[Shoutcast] Failed to start decoding next image"
				self.decoding = None
		else:
			self.decoding = None

	def updateIcon(self, filename):
		if self.decoding is not None:
			self.decodeNext = filename
		else:
			if self.picload.startDecode(filename) == 0:
				self.decoding = filename
			else:
				print "[Shoutcast] Failed to start decoding image"
				self.decoding = None

class SHOUTcastList(GUIComponent, object):
	def buildEntry(self, item):
		width = self.l.getItemSize().width()
		res = [ None ]
		if self.mode == 0: # GENRELIST
			print "[SHOUTcast] list name=%s haschilds=%s opened=%s\n" % (item.name, item.haschilds, item.opened)
			if item.parentid == "0": # main genre
				if item.haschilds == "true":
					if item.opened == "true":
						iname = "- %s" % item.name
					else:
						iname = "+ %s" % item.name
				else:
					iname = item.name
			else:
				iname = "     %s" % item.name
			res.append((eListboxPythonMultiContent.TYPE_TEXT, 0, 0, width, 22, 0, RT_HALIGN_LEFT|RT_VALIGN_CENTER, iname))
		elif self.mode == 1: # STATIONLIST
			res.append((eListboxPythonMultiContent.TYPE_TEXT, 0, 3, width, 20, 1, RT_HALIGN_LEFT|RT_VALIGN_CENTER, item.name))
			res.append((eListboxPythonMultiContent.TYPE_TEXT, 0, 23, width, 20, 1, RT_HALIGN_LEFT|RT_VALIGN_CENTER, item.ct))
			res.append((eListboxPythonMultiContent.TYPE_TEXT, 0, 43, width / 2, 20, 1, RT_HALIGN_LEFT|RT_VALIGN_CENTER, _("Audio: %s") % item.mt))
			res.append((eListboxPythonMultiContent.TYPE_TEXT,  width / 2, 43, width / 2, 20, 1, RT_HALIGN_RIGHT|RT_VALIGN_CENTER, _("Bit rate: %s kbps") % item.br))
		elif self.mode == 2: # FAVORITELIST
			res.append((eListboxPythonMultiContent.TYPE_TEXT, 0, 3, width, 20, 1, RT_HALIGN_LEFT|RT_VALIGN_CENTER, item.configItem.name.value))
			res.append((eListboxPythonMultiContent.TYPE_TEXT, 0, 23, width, 20, 1, RT_HALIGN_LEFT|RT_VALIGN_CENTER, "%s (%s)" % (item.configItem.text.value, item.configItem.type.value)))
			if len(item.configItem.audio.value) != 0:
				res.append((eListboxPythonMultiContent.TYPE_TEXT, 0, 43, width / 2, 20, 1, RT_HALIGN_LEFT|RT_VALIGN_CENTER, _("Audio: %s") % item.configItem.audio.value))
			if len(item.configItem.bitrate.value) != 0:
				res.append((eListboxPythonMultiContent.TYPE_TEXT,  width / 2, 43, width / 2, 20, 1, RT_HALIGN_RIGHT|RT_VALIGN_CENTER, _("Bit rate: %s kbps") % item.configItem.bitrate.value))
		return res

	def __init__(self):
		GUIComponent.__init__(self)
		self.l = eListboxPythonMultiContent()
		self.l.setFont(0, gFont("Regular", 20))
		self.l.setFont(1, gFont("Regular", 18))
		self.l.setBuildFunc(self.buildEntry)
		self.l.setItemHeight(22)
		self.onSelectionChanged = [ ]
		self.mode = 0

	def setMode(self, mode):
		self.mode = mode
		if mode == 0: # GENRELIST
			self.l.setItemHeight(22)
		elif mode == 1 or mode == 2: # STATIONLIST OR FAVORITELIST
			self.l.setItemHeight(69)

	def connectSelChanged(self, fnc):
		if not fnc in self.onSelectionChanged:
			self.onSelectionChanged.append(fnc)

	def disconnectSelChanged(self, fnc):
		if fnc in self.onSelectionChanged:
			self.onSelectionChanged.remove(fnc)

	def selectionChanged(self):
		for x in self.onSelectionChanged:
			x()
	
	def getCurrent(self):
		cur = self.l.getCurrentSelection()
		return cur and cur[0]
	
	GUI_WIDGET = eListbox
	
	def postWidgetCreate(self, instance):
		instance.setContent(self.l)
		instance.selectionChanged.get().append(self.selectionChanged)

	def preWidgetRemove(self, instance):
		instance.setContent(None)
		instance.selectionChanged.get().remove(self.selectionChanged)

	def moveToIndex(self, index):
		self.instance.moveSelectionTo(index)

	def getCurrentIndex(self):
		return self.instance.getCurrentIndex()

	currentIndex = property(getCurrentIndex, moveToIndex)
	currentSelection = property(getCurrent)

	def setList(self, list):
		self.l.setList(list)

class SHOUTcastLCDScreen(Screen):
	skin = """
	<screen position="0,0" size="132,64" title="SHOUTcast">
		<widget name="text1" position="4,0" size="132,14" font="Regular;12" halign="center" valign="center"/>
		<widget name="text2" position="4,14" size="132,49" font="Regular;10" halign="center" valign="center"/>
	</screen>""" 

	def __init__(self, session, parent):
		Screen.__init__(self, session)
		self["text1"] =  Label("SHOUTcast")
		self["text2"] = Label("")

	def setText(self, text):
		self["text2"].setText(text[0:39])


class SHOUTcastSetup(Screen, ConfigListScreen):

	skin = """
		<screen position="center,center" size="600,400" title="SHOUTcast Setup" >
			<ePixmap pixmap="skin_default/buttons/red.png" position="10,0" zPosition="0" size="140,40" transparent="1" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/green.png" position="155,0" zPosition="0" size="140,40" transparent="1" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/yellow.png" position="300,0" zPosition="0" size="140,40" transparent="1" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/blue.png" position="445,0" zPosition="0" size="140,40" transparent="1" alphatest="on" />
			<widget render="Label" source="key_red" position="10,0" size="140,40" zPosition="5" valign="center" halign="center" backgroundColor="red" font="Regular;21" transparent="1" foregroundColor="white" shadowColor="black" shadowOffset="-1,-1" />
			<widget render="Label" source="key_green" position="150,0" size="140,40" zPosition="5" valign="center" halign="center" backgroundColor="red" font="Regular;21" transparent="1" foregroundColor="white" shadowColor="black" shadowOffset="-1,-1" />
			<widget name="config" position="10,50" size="580,400" scrollbarMode="showOnDemand" />
		</screen>""" 

	def __init__(self, session):
		Screen.__init__(self, session)

		self["key_red"] = StaticText(_("Cancel"))
		self["key_green"] = StaticText(_("OK"))

		self.list = [
			getConfigListEntry(_("Show cover:"), config.plugins.shoutcast.showcover),
			getConfigListEntry(_("Coverwidth:"), config.plugins.shoutcast.coverwidth),
			getConfigListEntry(_("Coverheight:"), config.plugins.shoutcast.coverheight),
			getConfigListEntry(_("Show in extension menu:"), config.plugins.shoutcast.showinextensions),
			getConfigListEntry(_("Streaming rate:"), config.plugins.shoutcast.streamingrate),
			getConfigListEntry(_("Reload station list:"), config.plugins.shoutcast.reloadstationlist),
			getConfigListEntry(_("Rip to single file, name is timestamped"), config.plugins.shoutcast.riptosinglefile),
			getConfigListEntry(_("Create a directory for each stream"), config.plugins.shoutcast.createdirforeachstream),
			getConfigListEntry(_("Add sequence number to output file"), config.plugins.shoutcast.addsequenceoutputfile),
				]
		self.dirname = getConfigListEntry(_("Recording location:"), config.plugins.shoutcast.dirname)
		self.list.append(self.dirname)
		
		ConfigListScreen.__init__(self, self.list, session)
		self["setupActions"] = ActionMap(["SetupActions", "ColorActions"],
		{
			"green": self.keySave,
			"cancel": self.keyClose,
			"ok": self.keySelect,
		}, -2)

	def keySelect(self):
		cur = self["config"].getCurrent()
		if cur == self.dirname:
			self.session.openWithCallback(self.pathSelected,SHOUTcastStreamripperRecordingPath,config.plugins.shoutcast.dirname.value)

	def pathSelected(self, res):
		if res is not None:
			config.plugins.shoutcast.dirname.value = res

	def keySave(self):
		for x in self["config"].list:
			x[1].save()
		configfile.save()
		self.close(True)

	def keyClose(self):
		for x in self["config"].list:
			x[1].cancel()
		self.close(False)


class SHOUTcastStreamripperRecordingPath(Screen):
	skin = """<screen name="SHOUTcastStreamripperRecordingPath" position="center,center" size="560,320" title="Select record path for streamripper">
			<ePixmap pixmap="skin_default/buttons/red.png" position="0,0" zPosition="0" size="140,40" transparent="1" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/green.png" position="140,0" zPosition="0" size="140,40" transparent="1" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/yellow.png" position="280,0" zPosition="0" size="140,40" transparent="1" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/blue.png" position="420,0" zPosition="0" size="140,40" transparent="1" alphatest="on" />
			<widget name="target" position="0,60" size="540,22" valign="center" font="Regular;22" />
			<widget name="filelist" position="0,100" zPosition="1" size="560,220" scrollbarMode="showOnDemand"/>
			<widget render="Label" source="key_red" position="0,0" size="140,40" zPosition="5" valign="center" halign="center" backgroundColor="red" font="Regular;21" transparent="1" foregroundColor="white" shadowColor="black" shadowOffset="-1,-1" />
			<widget render="Label" source="key_green" position="140,0" size="140,40" zPosition="5" valign="center" halign="center" backgroundColor="red" font="Regular;21" transparent="1" foregroundColor="white" shadowColor="black" shadowOffset="-1,-1" />
		</screen>"""
		
	def __init__(self, session, initDir):
		Screen.__init__(self, session)
		inhibitDirs = ["/bin", "/boot", "/dev", "/etc", "/lib", "/proc", "/sbin", "/sys", "/usr", "/var"]
		inhibitMounts = []
		self["filelist"] = FileList(initDir, showDirectories = True, showFiles = False, inhibitMounts = inhibitMounts, inhibitDirs = inhibitDirs)
		self["target"] = Label()
		self["actions"] = ActionMap(["WizardActions", "DirectionActions", "ColorActions", "EPGSelectActions"],
		{
			"back": self.cancel,
			"left": self.left,
			"right": self.right,
			"up": self.up,
			"down": self.down,
			"ok": self.ok,
			"green": self.green,
			"red": self.cancel
			
		}, -1)
		self["key_red"] = StaticText(_("Cancel"))
		self["key_green"] = StaticText(_("OK"))

	def cancel(self):
		self.close(None)

	def green(self):
		self.close(self["filelist"].getSelection()[0])

	def up(self):
		self["filelist"].up()
		self.updateTarget()

	def down(self):
		self["filelist"].down()
		self.updateTarget()

	def left(self):
		self["filelist"].pageUp()
		self.updateTarget()

	def right(self):
		self["filelist"].pageDown()
		self.updateTarget()

	def ok(self):
		if self["filelist"].canDescent():
			self["filelist"].descent()
			self.updateTarget()

	def updateTarget(self):
		currFolder = self["filelist"].getSelection()[0]
		if currFolder is not None:
			self["target"].setText(currFolder)
		else:
			self["target"].setText(_("Invalid Location"))

	def up(self):
		self["filelist"].up()
		self.updateTarget()

	def down(self):
		self["filelist"].down()
		self.updateTarget()

	def left(self):
		self["filelist"].pageUp()
		self.updateTarget()

	def right(self):
		self["filelist"].pageDown()
		self.updateTarget()

	def ok(self):
		if self["filelist"].canDescent():
			self["filelist"].descent()
			self.updateTarget()

	def updateTarget(self):
		currFolder = self["filelist"].getSelection()[0]
		if currFolder is not None:
			self["target"].setText(currFolder)
		else:
			self["target"].setText(_("Invalid Location"))
