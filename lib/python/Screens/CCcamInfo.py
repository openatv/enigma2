# -*- coding: UTF-8 -*-
# CCcam Info by AliAbdul
from base64 import encodestring
from os import listdir, remove, rename, system, popen, path

from enigma import eListboxPythonMultiContent, eTimer, gFont, loadPNG, RT_HALIGN_RIGHT, getDesktop

from Components.ActionMap import ActionMap, NumberActionMap
from Components.config import config, getConfigListEntry
from Components.ConfigList import ConfigListScreen
from Components.Console import Console
from Components.Label import Label
from Components.MenuList import MenuList
from Components.MultiContent import MultiContentEntryText, MultiContentEntryPixmapAlphaTest, MultiContentEntryPixmapAlphaBlend
from Components.ScrollLabel import ScrollLabel
from Screens.HelpMenu import HelpableScreen

#from Screens.InfoBar import InfoBar
from Screens.LocationBox import LocationBox
from Screens.MessageBox import MessageBox
from Screens.Screen import Screen
from Screens.VirtualKeyBoard import VirtualKeyBoard
from Tools.Directories import fileExists, SCOPE_ACTIVE_SKIN, resolveFilename
from twisted.internet import reactor
from twisted.web.client import HTTPClientFactory
from urlparse import urlparse, urlunparse
import skin

#TOGGLE_SHOW = InfoBar.toggleShow

VERSION = "v2"
DATE = "21.11.2014"

#############################################################

###global
f = 1
screenwidth = getDesktop(0).size().width()
if screenwidth and screenwidth == 1920:
	f = 1.5
elif screenwidth and screenwidth > 1920:
	f = 3
###global

def confPath():
	search_dirs = [ "/usr", "/var", "/etc" ]
	sdirs = " ".join(search_dirs)
	cmd = 'find %s -name "CCcam.cfg" | head -n 1' % sdirs
	res = popen(cmd).read()
	if res == "":
		return None
	else:
		return res.replace("\n", "")

def _parse(url):
	url = url.strip()
	parsed = urlparse(url)
	scheme = parsed[0]
	path = urlunparse(('','') + parsed[2:])

	host, port = parsed[1], 80

	if '@' in host:
		username, host = host.split('@')
		if ':' in username:
			username, password = username.split(':')
		else:
			password = ""
	else:
		username = ""
		password = ""

	if ':' in host:
		host, port = host.split(':')
		port = int(port)

	if path == "":
		path = "/"

	return scheme, host, port, path, username, password

def getPage(url, contextFactory=None, *args, **kwargs):
	scheme, host, port, path, username, password = _parse(url)

	if username and password:
		url = scheme + '://' + host + ':' + str(port) + path
		basicAuth = encodestring("%s:%s" % (username, password))
		authHeader = "Basic " + basicAuth.strip()
		AuthHeaders = {"Authorization": authHeader}

		if kwargs.has_key("headers"):
			kwargs["headers"].update(AuthHeaders)
		else:
			kwargs["headers"] = AuthHeaders

	factory = HTTPClientFactory(url, *args, **kwargs)
	reactor.connectTCP(host, port, factory)

	return factory.deferred

def searchConfig():
	global CFG, CFG_path
	CFG = confPath()
	CFG_path = '/var/etc'
	if CFG:
		CFG_path =  path.dirname(CFG)

#############################################################

class HelpableNumberActionMap(NumberActionMap):
	def __init__(self, parent, context, actions, prio):
		alist = []
		adict = {}
		for (action, funchelp) in actions.iteritems():
			alist.append((action, funchelp[1]))
			adict[action] = funchelp[0]
		NumberActionMap.__init__(self, [context], adict, prio)
		parent.helpList.append((self, context, alist))

#############################################################

TranslationHelper = [
	["Current time", _("Current time")],
	["NodeID", _("NodeID")],
	["Uptime", _("Uptime")],
	["Connected clients", _("Connected clients")],
	["Active clients", _("Active clients")],
	["Total handled client ecm's", _("Total handled client ecm's")],
	["Total handled client emm's", _("Total handled client emm's")],
	["Peak load (max queued requests per workerthread)", _("Peak load (max queued requests per workerthread)")],
	["card reader", _("card reader")],
	["no or unknown card inserted", _("no or unknown card inserted")],
	["system:", _("system:")],
	["caid:", _("caid:")],
	["provider:", _("provider:")],
	["provid:", _("provid:")],
	["using:", _("using:")],
	["address:", _("address:")],
	["hops:", _("hops:")],
	["pid:", _("pid:")],
	["share:", _("share:")],
	["handled", _("handled")],
	[" and", _(" and")],
	["card", _("card")],
	["Cardserial", _("Cardserial")],
	["ecm time:", _("ecm time:")]]

def translateBlock(block):
	for x in TranslationHelper:
		if block.__contains__(x[0]):
			block = block.replace(x[0], x[1])
	return block

#############################################################

def getConfigValue(l):
	list = l.split(":")
	ret = ""

	if len(list) > 1:
		ret = (list[1]).replace("\n", "").replace("\r", "")
		if ret.__contains__("#"):
			idx = ret.index("#")
			ret = ret[:idx]
		while ret.startswith(" "):
			ret = ret[1:]
		while ret.endswith(" "):
			ret = ret[:-1]

	return ret

#############################################################

def notBlackListed(entry):
	try:
		f = open(config.cccaminfo.blacklist.value, "r")
		content = f.read().split("\n")
		f.close()
	except:
		content = []
	ret = True
	for x in content:
		if x == entry:
			ret = False
	return ret

#############################################################

menu_list = [
	_("General"),
	_("Clients"),
	_("Active clients"),
	_("Servers"),
	_("Shares"),
	_("Share View"),
	_("Extended Shares"),
	_("Providers"),
	_("Entitlements"),
	_("ecm.info"),
	_("Menu config"),
	_("Local box"),
	_("Remote box"),
	_("Free memory"),
	_("Switch config"),
	_("About")]

#############################################################

if path.exists(resolveFilename(SCOPE_ACTIVE_SKIN, "icons/lock_on.png")):
	lock_on = loadPNG(resolveFilename(SCOPE_ACTIVE_SKIN, "icons/lock_on.png"))
else:
	lock_on = loadPNG("/usr/share/enigma2/skin_default/icons/lock_on.png")
	
if path.exists(resolveFilename(SCOPE_ACTIVE_SKIN, "icons/lock_off.png")):
	lock_off = loadPNG(resolveFilename(SCOPE_ACTIVE_SKIN, "icons/lock_off.png"))
else:
	lock_off = loadPNG("/usr/share/enigma2/skin_default/icons/lock_off.png")

def getConfigNameAndContent(fileName):
	try:
		f = open(fileName, "r")
		content = f.read()
		f.close()
	except:
		content = ""

	if content.startswith("#CONFIGFILE NAME="):
		content = content.replace("\r", "\n")
		name = content[17:]
		idx = name.index("\n")
		name = name[:idx]
	else:
		name = fileName.replace(CFG_path + "/", "")

	return name, content

#############################################################

class CCcamList(MenuList):
	def __init__(self, list):
		MenuList.__init__(self, list, False, eListboxPythonMultiContent)
		self.l.setItemHeight(int(30*f))
		self.l.setFont(0, gFont("Regular", int(20*f)))

class CCcamShareList(MenuList):
	def __init__(self, list):
		MenuList.__init__(self, list, False, eListboxPythonMultiContent)
		self.l.setItemHeight(int(60*f))
		self.l.setFont(0, gFont("Regular", int(18*f)))

class CCcamConfigList(MenuList):
	def __init__(self, list):
		MenuList.__init__(self, list, False, eListboxPythonMultiContent)
		self.l.setItemHeight(int(30*f))
		self.l.setFont(0, gFont("Regular", int(20*f)))

class CCcamShareViewList(MenuList):
	def __init__(self, list):
		MenuList.__init__(self, list, False, eListboxPythonMultiContent)
		self.l.setItemHeight(int(30*f))
		self.l.setFont(0, gFont("Regular", int(18*f)))

def CCcamListEntry(name, idx):
	res = [name]
	if idx == 10:
		idx = "red"
	elif idx == 11:
		idx = "green"
	elif idx == 12:
		idx = "yellow"
	elif idx == 13:
		idx = "blue"
	elif idx == 14:
		idx = "menu"
	elif idx == 15:
		idx = "info"
	if path.exists(resolveFilename(SCOPE_ACTIVE_SKIN, "buttons/key_%s.png" % str(idx))):
		png = resolveFilename(SCOPE_ACTIVE_SKIN, "buttons/key_%s.png" % str(idx))
	else:
		png = "/usr/share/enigma2/skin_default/buttons/key_%s.png" % str(idx)
	if fileExists(png):
		x, y, w, h = skin.parameters.get("ChoicelistIcon",(5*f, 0, 35*f, 25*f))
		res.append(MultiContentEntryPixmapAlphaBlend(pos=(x, y), size=(w, h), png=loadPNG(png)))
	x, y, w, h = skin.parameters.get("ChoicelistName",(45*f, 2*f, 550*f, 25*f))
	res.append(MultiContentEntryText(pos=(x, y), size=(w, h), font=0, text=name))
	return res

def CCcamServerListEntry(name, color):
	res = [name]
	if path.exists(resolveFilename(SCOPE_ACTIVE_SKIN, "buttons/key_%s.png" %  color)):
		png = resolveFilename(SCOPE_ACTIVE_SKIN, "buttons/key_%s.png" %  color)
	else:
		png = "/usr/share/enigma2/skin_default/buttons/key_%s.png" % color
	if fileExists(png):
		x, y, w, h = skin.parameters.get("ChoicelistIcon",(5*f, 0, 35*f, 25*f))
		res.append(MultiContentEntryPixmapAlphaBlend(pos=(x, y), size=(w, h), png=loadPNG(png)))
	x, y, w, h = skin.parameters.get("ChoicelistName",(45*f, 2*f, 550*f, 25*f))
	res.append(MultiContentEntryText(pos=(x, y), size=(w, h), font=0, text=name))
	return res

def CCcamShareListEntry(hostname, type, caid, system, uphops, maxdown):
	res = [(hostname, type, caid, system, uphops, maxdown),
			MultiContentEntryText(pos=(0, 0), size=(300*f, 25*f), font=0, text=hostname),
			MultiContentEntryText(pos=(300*f, 0), size=(300*f, 25*f), font=0, text=_("Type: ") + type, flags=RT_HALIGN_RIGHT),
			MultiContentEntryText(pos=(0, 20*f), size=(300*f, 25*f), font=0, text=_("CaID: ") + caid),
			MultiContentEntryText(pos=(300*f, 20*f), size=(300*f, 25*f), font=0, text=_("System: ") + system, flags=RT_HALIGN_RIGHT),
			MultiContentEntryText(pos=(0, 40*f), size=(300*f, 25*f), font=0, text=_("Uphops: ") + uphops),
			MultiContentEntryText(pos=(300*f, 40*f), size=(300*f, 25*f), font=0, text=_("Maxdown: ") + maxdown, flags=RT_HALIGN_RIGHT)]
	return res

def CCcamShareViewListEntry(caidprovider, providername, numberofcards, numberofreshare):
	res = [(caidprovider, providername, numberofcards),
			MultiContentEntryText(pos=(0, 0), size=(500*f, 25*f), font=0, text=providername),
			MultiContentEntryText(pos=(500*f, 0), size=(50*f, 25*f), font=0, text=numberofcards, flags=RT_HALIGN_RIGHT),
			MultiContentEntryText(pos=(550*f, 0), size=(50*f, 25*f), font=0, text=numberofreshare, flags=RT_HALIGN_RIGHT)]
	return res

def CCcamConfigListEntry(file):
	res = [file]

	try:
		f = open(CFG, "r")
		org = f.read()
		f.close()
	except:
		org = ""

	(name, content) = getConfigNameAndContent(file)

	if content == org:
		png = lock_on
		x, y, w, h = skin.parameters.get("SelectionListLock",(5*f, 0, 25*f, 25*f))
	else:
		png = lock_off
		x, y, w, h = skin.parameters.get("SelectionListLockOff",(5*f, 0, 25*f, 25*f))
	res.append(MultiContentEntryPixmapAlphaBlend(pos=(x, y), size=(w, h), png=png))
	x, y, w, h = skin.parameters.get("SelectionListDescr",(45*f, 2*f, 550*f, 25*f))
	res.append(MultiContentEntryText(pos=(x, y), size=(w, h), font=0, text=name))

	return res

def CCcamMenuConfigListEntry(name, blacklisted):
	res = [name]

	if blacklisted:
		png = lock_off
		x, y, w, h = skin.parameters.get("SelectionListLockOff",(5*f, 0, 25*f, 25*f))
	else:
		png = lock_on
		x, y, w, h = skin.parameters.get("SelectionListLock",(5*f, 0, 25*f, 25*f))
	res.append(MultiContentEntryPixmapAlphaBlend(pos=(x, y), size=(w, h), png=png))
	x, y, w, h = skin.parameters.get("SelectionListDescr",(45*f, 2*f, 550*f, 25*f))
	res.append(MultiContentEntryText(pos=(x, y), size=(w, h), font=0, text=name))

	return res

#############################################################

class CCcamInfoMain(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		Screen.setTitle(self, _("CCcam Info"))
		self.session = session

		self["menu"] = CCcamList([])

		self.working = False
		self.Console = Console()
		searchConfig()

		if config.cccaminfo.profile.value == "":
			self.readConfig()
		else:
			self.url = config.cccaminfo.profile.value

		self["actions"] = NumberActionMap(["CCcamInfoActions"],
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
				"0": self.keyNumberGlobal,
				"red": self.red,
				"green": self.green,
				"yellow": self.yellow,
				"blue": self.blue,
				"menu": self.menu,
				"info": self.info,
				"ok": self.okClicked,
				"cancel": self.close,
				"up": self.up,
				"down": self.down,
				"left": self.left,
				"right": self.right
			}, -2)

		self.onLayoutFinish.append(self.updateMenuList)

	def updateMenuList(self):
		self.working = True

		self.menu_list = []
		for x in self.menu_list:
			del self.menu_list[0]

		list = []
		idx = 0
		for x in menu_list:
			if notBlackListed(x):
				list.append(CCcamListEntry(x, idx))
				self.menu_list.append(x)
				idx += 1

		self["menu"].setList(list)
		self.working = False

	def readConfig(self):
		self.url = "http://127.0.0.1:16001"

		username = None
		password = None

		try:
			f = open(CFG, 'r')

			for l in f:
				if l.startswith('WEBINFO LISTEN PORT :'):
					port = getConfigValue(l)
					if port != "":
						self.url = self.url.replace('16001', port)

				elif l.startswith('WEBINFO USERNAME :'):
					username = getConfigValue(l)

				elif l.startswith('WEBINFO PASSWORD :'):
					password = getConfigValue(l)

			f.close()
		except:
			pass

		if (username is not None) and (password is not None) and (username != "") and (password != ""):
			self.url = self.url.replace('http://', ("http://%s:%s@" % (username, password)))

		config.cccaminfo.profile.value = ""
		config.cccaminfo.profile.save()

	def profileSelected(self, url=None):
		if url is not None:
			self.url = url
			config.cccaminfo.profile.value = self.url
			config.cccaminfo.profile.save()
			self.showInfo(_("New profile: ") + url, _("Profile"))
		else:
			self.showInfo(_("Using old profile: ") + self.url, _("Profile"))

	def keyNumberGlobal(self, idx):
		if self.working == False and (idx < len(self.menu_list)):
			self.working = True
			sel = self.menu_list[idx]

			if sel == _("General"):
				getPage(self.url).addCallback(self.showCCcamGeneral).addErrback(self.getWebpageError)

			elif sel == _("Clients"):
				getPage(self.url + "/clients").addCallback(self.showCCcamClients).addErrback(self.getWebpageError)

			elif sel == _("Active clients"):
				getPage(self.url + "/activeclients").addCallback(self.showCCcamClients).addErrback(self.getWebpageError)

			elif sel == _("Servers"):
				getPage(self.url + "/servers").addCallback(self.showCCcamServers).addErrback(self.getWebpageError)

			elif sel == _("Shares"):
				getPage(self.url + "/shares").addCallback(self.showCCcamShares).addErrback(self.getWebpageError)

			elif sel == _("Share View"):
				self.session.openWithCallback(self.workingFinished, CCcamShareViewMenu, self.url)

			elif sel == _("Extended Shares"):
				self.session.openWithCallback(self.workingFinished, CCcamInfoShareInfo, "None", self.url)

			elif sel == _("Providers"):
				getPage(self.url + "/providers").addCallback(self.showCCcamProviders).addErrback(self.getWebpageError)

			elif sel == _("Entitlements"):
				getPage(self.url + "/entitlements").addCallback(self.showCCcamEntitlements).addErrback(self.getWebpageError)

			elif sel == _("ecm.info"):
				self.session.openWithCallback(self.showEcmInfoFile, CCcamInfoEcmInfoSelection)

			elif sel == _("Menu config"):
				self.session.openWithCallback(self.updateMenuList, CCcamInfoMenuConfig)

			elif sel == _("Local box"):
				self.readConfig()
				self.showInfo(_("Profile: Local box"), _("Local box"))

			elif sel == _("Remote box"):
				self.session.openWithCallback(self.profileSelected, CCcamInfoRemoteBoxMenu)

			elif sel == _("Free memory"):
				if not self.Console:
					self.Console = Console()
				self.working = True
				self.Console.ePopen("free", self.showFreeMemory)

			elif sel == _("Switch config"):
				self.session.openWithCallback(self.workingFinished, CCcamInfoConfigSwitcher)

			else:
				self.showInfo(_("CCcam Info %s\nby AliAbdul %s\n\nThis plugin shows you the status of your CCcam.") % (VERSION, DATE), _("About"))

	def red(self):
		self.keyNumberGlobal(10)

	def green(self):
		self.keyNumberGlobal(11)

	def yellow(self):
		self.keyNumberGlobal(12)

	def blue(self):
		self.keyNumberGlobal(13)

	def menu(self):
		self.keyNumberGlobal(14)

	def info(self):
		self.keyNumberGlobal(15)

	def okClicked(self):
		self.keyNumberGlobal(self["menu"].getSelectedIndex())

	def up(self):
		if not self.working:
			self["menu"].up()

	def down(self):
		if not self.working:
			self["menu"].down()

	def left(self):
		if not self.working:
			self["menu"].pageUp()

	def right(self):
		if not self.working:
			self["menu"].pageDown()

	def getWebpageError(self, error=""):
		print str(error)
		self.session.openWithCallback(self.workingFinished, MessageBox, _("Error reading webpage!"), MessageBox.TYPE_ERROR)

	def showFile(self, file):
		try:
			f = open(file, "r")
			content = f.read()
			f.close()
		except:
			content = _("Could not open the file %s!") % file

		self.showInfo(translateBlock(content), " ")

	def showEcmInfoFile(self, file=None):
		if file is not None:
			self.showFile("/tmp/"+file)
		self.workingFinished()

	def showCCcamGeneral(self, html):
		if html.__contains__('<BR><BR>'):
			idx = html.index('<BR><BR>')
			idx2 = html.index('<BR></BODY>')
			html = html[idx+8:idx2].replace("<BR>", "\n").replace("\n\n", "\n")
			self.infoToShow = html
			getPage(self.url + "/shares").addCallback(self.showCCcamGeneral2).addErrback(self.getWebpageError)
		else:
			self.showInfo(_("Error reading webpage!"), _("Error"))

	def showCCcamGeneral2(self, html):
		if html.__contains__("Welcome to CCcam"):
			idx = html.index("Welcome to CCcam")
			html = html[idx+17:]
			idx = html.index(" ")
			version = html[:idx]
			self.infoToShow = "%s%s\n%s" % (_("Version: "), version, self.infoToShow)

		if html.__contains__("Available shares:"):
			idx = html.index("Available shares:")
			html = html[idx+18:]
			idx = html.index("\n")
			html = html[:idx]
			self.showInfo(translateBlock("%s %s\n%s" % (_("Available shares:"), html, self.infoToShow)), _("General"))
		else:
			self.showInfo(translateBlock(self.infoToShow), _("General"))

	def showCCcamClients(self, html):
		firstLine = True
		clientList = []
		infoList = []
		lines = html.split("\n")

		for l in lines:
			if l.__contains__('|'):
				if firstLine:
					firstLine = False
				else:
					list = l.split('|')
					if len(list) > 8:
						username = list[1].replace(" ", "")
						if username != "":
							hostname = list[2].replace(" ", "")
							connected = list[3].replace(" ", "")
							idleTime = list[4].replace(" ", "")
							ecm = list[5].replace(" ", "")
							emm = list[6].replace(" ", "")
							version = list[7].replace(" ", "")
							share = list[8].replace(" ", "")

							if version == "":
								version = "N/A"

							ecmEmm = "ECM: " + ecm + " - EMM: " + emm

							infoList.append([username, _("Hostname: ") + hostname, _("Connected: ") + connected, _("Idle Time: ") + idleTime, _("Version: ") + version, _("Last used share: ") + share, ecmEmm])
							clientList.append(username)
		self.set_title = _("CCcam Client Info")
		self.openSubMenu(clientList, infoList, self.set_title)

	def showCCcamServers(self, html):
		firstLine = True
		infoList = []
		lines = html.split("\n")

		for l in lines:
			if l.__contains__('|'):
				if firstLine:
					firstLine = False
				else:
					list = l.split('|')
					if len(list) > 7:
						hostname = list[1].replace(" ", "")
						if hostname != "":
							connected = list[2].replace(" ", "")
							type = list[3].replace(" ", "")
							version = list[4].replace(" ", "")
							nodeid = list[5].replace(" ", "")
							cards = list[6].replace(" ", "")

							if version == "":
								version = "N/A"

							if nodeid == "":
								nodeid = "N/A"

							infoList.append([hostname, _("Cards: ") + cards, _("Type: ") + type, _("Version: ") + version, _("NodeID: ") + nodeid, _("Connected: ") + connected])

		self.session.openWithCallback(self.workingFinished, CCcamInfoServerMenu, infoList, self.url)

	def showCCcamShares(self, html):
		firstLine = True
		sharesList = []
		infoList = []
		lines = html.split("\n")

		for l in lines:
			if l.__contains__('|'):
				if firstLine:
					firstLine = False
				else:
					list = l.split('|')
					if len(list) > 7:
						hostname = list[1].replace(" ", "")
						if hostname != "":
							type = list[2].replace(" ", "")
							caid = list[3].replace(" ", "")
							system = list[4].replace(" ", "")

							string = list[6]
							while string.startswith(" "):
								string = string[1:]

							while string.endswith(" "):
								string = string[:-1]

							idx = string.index(" ")
							uphops = string[:idx]
							string = string[idx+1:]

							while string.startswith(" "):
								string = string[1:]
							maxdown = string

							if len(caid) == 3:
								caid = "0" + caid

							infoList.append([hostname, _("Type: ") + type, _("CaID: ") + caid, _("System: ") + system, _("Uphops: ") + uphops, _("Maxdown: ") + maxdown])
							sharesList.append(hostname + " - " + _("CaID: ") + caid)

		self.set_title = _("CCcam Shares Info")
		self.openSubMenu(sharesList, infoList, self.set_title)

	def showCCcamProviders(self, html):
		firstLine = True
		providersList = []
		infoList = []
		lines = html.split("\n")

		for l in lines:
			if l.__contains__('|'):
				if firstLine:
					firstLine = False
				else:
					list = l.split('|')
					if len(list) > 5:
						caid = list[1].replace(" ", "")
						if caid != "":
							provider = list[2].replace(" ", "")
							providername = list[3].replace(" ", "")
							system = list[4].replace(" ", "")

							infoList.append([_("CaID: ") + caid, _("Provider: ") + provider, _("Provider Name: ") + providername, _("System: ") + system])
							providersList.append(_("CaID: ") + caid + " - " + _("Provider: ") + provider)

		self.set_title = _("CCcam Provider Info")
		self.openSubMenu(providersList, infoList, self.set_title)

	def showCCcamEntitlements(self, html):
		if html.__contains__('<PRE>'):
			idx = html.index('<PRE>')
			idx2 = html.index('</PRE>')
			html = html[idx+5:idx2].replace("\n\n", "\n")
			if html == "":
				html = _("No card inserted!")
			self.showInfo(translateBlock(html), _("Entitlements"))
		else:
			self.showInfo(_("Error reading webpage!"), _("Entitlements"))

	def showInfo(self, info, set_title):
		self.session.openWithCallback(self.workingFinished, CCcamInfoInfoScreen, info, set_title)

	def openSubMenu(self, list, infoList, set_title):
		self.session.openWithCallback(self.workingFinished, CCcamInfoSubMenu, list, infoList, set_title)

	def workingFinished(self, callback=None):
		self.working = False

	def showFreeMemory(self, result, retval, extra_args):
		if retval == 0:
			if result.__contains__("Total:"):
				idx = result.index("Total:")
				result = result[idx+6:]

				tmpList = result.split(" ")
				list = []
				for x in tmpList:
					if x != "":
						list.append(x)

				self.showInfo("%s\n\n  %s %s\n  %s %s\n  %s %s" % (_("Free memory:"), _("Total:"), list[0], _("Used:"), list[1], _("Free:"), list[2]), _("Free memory"))
			else:
				self.showInfo(result, _("Free memory"))
		else:
			self.showInfo(str(result), _("Free memory"))

#############################################################

class CCcamInfoEcmInfoSelection(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		Screen.setTitle(self, _("CCcam ECM Info"))
		list = []
		tmp = listdir("/tmp/")
		for x in tmp:
			if x.endswith('.info') and x.startswith('ecm'):
				list.append(x)
		self["list"] = MenuList(list)

		self["actions"] = ActionMap(["CCcamInfoActions"], {"ok": self.ok, "cancel": self.close}, -1)

	def ok(self):
		self.close(self["list"].getCurrent())

#############################################################

class CCcamInfoInfoScreen(Screen):
	def __init__(self, session, info, set_title):
		Screen.__init__(self, session)
		Screen.setTitle(self, set_title)
		self["text"] = ScrollLabel(info)

		self["actions"] = ActionMap(["CCcamInfoActions"],
			{
				"ok": self.close,
				"cancel": self.close,
				"up": self["text"].pageUp,
				"down": self["text"].pageDown,
				"left": self["text"].pageUp,
				"right": self["text"].pageDown,
			}, -1)

#############################################################

class CCcamShareViewMenu(Screen, HelpableScreen):
	def __init__(self, session, url):
		Screen.__init__(self, session)
		HelpableScreen.__init__(self)
		self.session = session
		Screen.setTitle(self, _("CCcam Share Info"))
		self.url = url
		self.list = []
		self.providers = {}
		self.uphop = -1
		self.working = True

		self["list"] = CCcamShareViewList([])
		self["uphops"] = Label()
		self["cards"] = Label()
		self["providers"] = Label()
		self["reshare"] = Label()
		self["title"] = Label()

		self["actions"] = HelpableNumberActionMap(self, "CCcamInfoActions",
			{
				"cancel": (self.exit, _("close share view")),
				"0": (self.getUphop, _("show cards with uphop 0")),
				"1": (self.getUphop, _("show cards with uphop 1")),
				"2": (self.getUphop, _("show cards with uphop 2")),
				"3": (self.getUphop, _("show cards with uphop 3")),
				"4": (self.getUphop, _("show cards with uphop 4")),
				"5": (self.getUphop, _("show cards with uphop 5")),
				"6": (self.getUphop, _("show cards with uphop 6")),
				"7": (self.getUphop, _("show cards with uphop 7")),
				"8": (self.getUphop, _("show cards with uphop 8")),
				"9": (self.getUphop, _("show cards with uphop 9")),
				"green": (self.showAll, _("show all cards")),
				"incUphop": (self.incUphop, _("increase uphop by 1")),
				"decUphop": (self.decUphop, _("decrease uphop by 1")),
				"ok": (self.getServer, _("get the cards' server")),
			}, -1)

		self.onLayoutFinish.append(self.getProviders)

	def exit(self):
		if not self.working:
			self.close()

	def getProviders(self):
		getPage(self.url + "/providers").addCallback(self.readProvidersCallback).addErrback(self.readError)

	def readError(self, error=None):
		self.session.open(MessageBox, _("Error reading webpage!"), MessageBox.TYPE_ERROR)
		self.working = False

	def readSharesCallback(self, html):
		firstLine = True
		providerList = []
		countList = []
		shareList = []
		reshareList = []
		self.hostList = []
		self.caidList = []
		count = 0
		totalcards = 0
		totalproviders = 0
		resharecards = 0
		numberofreshare = 0
		lines = html.split("\n")

		for l in lines:
			if l.__contains__('|'):
				if firstLine:
					firstLine = False
				else:
					list = l.split("|")
					if len(list) > 7:
						hostname = list[1].replace(" ", "")
						if hostname != "":
							if self.uphop == -1:
								caid = list[3].replace(" ", "")
								provider = list[5].replace(" ", "")

								caidprovider = self.formatCaidProvider(caid, provider)


								string = list[6]
								while string.startswith(" "):
									string = string[1:]

								while string.endswith(" "):
									string = string[:-1]

								idx = string.index(" ")
								maxdown = string[idx+1:]

								while maxdown.startswith(" "):
									maxdown = maxdown[1:]
									down = maxdown

								if caidprovider not in providerList:
									providerList.append(caidprovider)
									count = 1
									countList.append(count)
									numberofcards = count
									providername = self.providers.get(caidprovider, 'Multiple Providers given')
									#if providername == 'Multiple Providers given':
									#	print caidprovider
									numberofreshare = 0
									if int(down)>0:
										resharecards += 1
										numberofreshare = 1
									reshareList.append(numberofreshare)

									shareList.append(CCcamShareViewListEntry(caidprovider, providername, str(numberofcards), str(numberofreshare)))
									self.list.append([caidprovider, providername, numberofcards,  numberofreshare])

									totalproviders += 1

								elif caidprovider in providerList:
									i = providerList.index(caidprovider)
									count = countList[i]
									count += 1
									countList[i] = count
									numberofcards = count

									if int(down)>0:
										reshare = reshareList[i]
										reshare += 1
										reshareList[i] = reshare
										numberofreshare = 0
										numberofreshare = reshare
										resharecards +=1
									elif int(down)==0:
										numberofreshare = reshareList[i]

									providername = self.providers.get(caidprovider, 'Multiple Providers given')
									shareList[i] = CCcamShareViewListEntry(caidprovider, providername, str(numberofcards), str(numberofreshare))

								self.hostList.append(hostname)
								self.caidList.append(caidprovider)

								totalcards += 1

								ulevel = _("All")

							else:
								updown = list[6]
								while updown.startswith(" "):
									updown = updown[1:]

								while updown.endswith(" "):
									updown = updown[:-1]

								idx = updown.index(" ")
								up = updown[:idx]

								maxdown = updown[idx+1:]

								while maxdown.startswith(" "):
									maxdown = maxdown[1:]
									down = maxdown

								ulevel = str(self.uphop)

								if int(up) == self.uphop:
									caid = list[3].replace(" ", "")
									provider = list[5].replace(" ", "")
									caidprovider = self.formatCaidProvider(caid, provider)
									if caidprovider not in providerList:
										providerList.append(caidprovider)
										count = 1
										countList.append(count)
										numberofcards = count
										providername = self.providers.get(caidprovider, 'Multiple Providers given')
										#if providername == 'Multiple Providers given':
										#	print caidprovider

										numberofreshare = 0
										if int(down)>0:
											resharecards += 1
											numberofreshare = 1
										reshareList.append(numberofreshare)

										shareList.append(CCcamShareViewListEntry(caidprovider, providername, str(numberofcards), str(numberofreshare)))
										self.list.append([caidprovider, providername, numberofcards, numberofreshare])

										totalproviders += 1
									elif caidprovider in providerList:
										i = providerList.index(caidprovider)
										count = countList[i]
										count += 1
										countList[i] = count
										numberofcards = count

										if int(down)>0:
											reshare = reshareList[i]
											reshare += 1
											#if caidprovider == "05021700":
											#	print "re: %d" %(reshare)
											reshareList[i] = reshare
											numberofreshare = 0
											numberofreshare = reshare
											resharecards +=1
										elif int(down)==0:
											numberofreshare = reshareList[i]

										providername = self.providers.get(caidprovider, 'Multiple Providers given')
										shareList[i] = CCcamShareViewListEntry(caidprovider, providername, str(numberofcards), str(numberofreshare))

									self.hostList.append(hostname)
									self.caidList.append(caidprovider)
									totalcards += 1
									#maxdown = list[6]
									#while maxdown.startswith(" "):
										#maxdown = maxdown[1:]
										#down = maxdown
									#if int(down)>0:
										#resharecards +=1

		self.instance.setTitle("%s (%s %d) %s %s" % (_("Share View"), _("Total cards:"), totalcards, _("Hops:"), ulevel))
		self["title"].setText("%s (%s %d) %s %s" % (_("Share View"), _("Total cards:"), totalcards, _("Hops:"), ulevel))
		self["list"].setList(shareList)
		self["uphops"].setText("%s %s" %(_("Hops:"), ulevel))
		self["cards"].setText("%s %s" %(_("Total cards:"), totalcards))
		self["providers"].setText("%s %s" %(_("Providers:"), totalproviders))
		self["reshare"].setText("%s %d" %(_("Reshare:"), resharecards))
		self.working = False

	def readProvidersCallback(self, html):
		firstLine = True
		lines = html.split("\n")
		for l in lines:
			if l.__contains__('|'):
				if firstLine:
					firstLine = False
				else:
					list = l.split('|')
					if len(list) > 5:
						caid = list[1].replace(" ", "")
						if caid != "":
							provider = list[2].replace(" ", "")
							providername = list[3]
							caidprovider = self.formatCaidProvider(caid, provider)
							self.providers.setdefault(caidprovider, providername)
		getPage(self.url + "/shares").addCallback(self.readSharesCallback).addErrback(self.readError)

	def formatCaidProvider(self, caid, provider):
		pos = provider.find(",")
		if pos != -1:
			provider = provider[pos+1:]
			pos = provider.find(",")
			if pos != -1:
				provider = provider[0:pos]

		if len(provider) == 0:
			provider = "0000"
		elif len(provider) == 1:
			provider = "000" + provider
		elif len(provider) == 2:
			provider = "00" + provider
		elif len(provider) == 3:
			provider = "0" + provider

		if len(caid) == 3:
			caid = "0" + caid

		if caid.startswith("0500") and len(provider) == 5:
			caid = "050"
		elif caid.startswith("0500") and len(provider) == 6:
			caid = "05"

		if caid.startswith("06"):
			caidprovider = caid
		elif caid.startswith("0d22"):
			caidprovider = caid
		elif caid.startswith("0d05"):
			caidprovider = caid
		elif caid.startswith("09"):
			caidprovider = caid
		elif caid.startswith("17"):
			caidprovider = caid
		elif caid.startswith("18"):
			caidprovider = caid
		elif caid.startswith("4a"):
			caidprovider = caid
		else:
			caidprovider = caid + provider
		return caidprovider

	def getUphop(self, uphop):
		self.uphop = uphop
		self.getProviders()

	def showAll(self):
		self.uphop = -1
		self.getProviders()

	def incUphop(self):
		if self.uphop < 9:
			self.uphop += 1
			self.getProviders()

	def decUphop(self):
		if self.uphop > -1:
			self.uphop -= 1
			self.getProviders()

	def getServer(self):
		server = _("Servers:") + " \n"
		sel = self["list"].getCurrent()
		if sel is not None:
			e = 0
			while e < len(self.caidList):
				if sel[0][0] == self.caidList[e]:
					pos = self.hostList[e].find(":")
					if pos != -1:
						server += self.hostList[e][0:pos] + "\n"
					else:
						server += self.hostList[e] + "\n"
				e += 1
			self.session.open(CCcamInfoInfoScreen, server, _("Servers"))

#############################################################

class CCcamInfoSubMenu(Screen):
	def __init__(self, session, list, infoList, set_title):
		Screen.__init__(self, session)
		self.session = session
		Screen.setTitle(self, _(set_title))
		self.infoList = infoList
		self["list"] = MenuList(list)
		self["info"] = Label()

		self["actions"] = ActionMap(["CCcamInfoActions"], {"ok": self.okClicked, "cancel": self.close}, -1)

		self["list"].onSelectionChanged.append(self.showInfo)
		self.onLayoutFinish.append(self.showInfo)

	def okClicked(self):
		info = self.getInfo()
		if info != "":
			self.session.open(MessageBox, info, MessageBox.TYPE_INFO)

	def showInfo(self):
		info = self.getInfo()
		self["info"].setText(info)

	def getInfo(self):
		try:
			idx = self["list"].getSelectedIndex()

			info = ""
			infoList = self.infoList[idx]
			for x in infoList:
				info += x + "\n"

			return info
		except:
			return ""

#############################################################

class CCcamInfoServerMenu(Screen):
	def __init__(self, session, infoList, url):
		Screen.__init__(self, session)
		self.session = session
		Screen.setTitle(self, _("CCcam Server Info"))
		self.infoList = infoList
		self.url = url

		list = []
		for x in self.infoList:
			if x[5].replace(_("Connected: "), "") == "": #offline - red
				list.append(CCcamServerListEntry(x[0], "red"))
			elif x[1] == _("Cards: 0"): #online with no card - blue
				list.append(CCcamServerListEntry(x[0], "blue"))
			else: #online with cards - green
				list.append(CCcamServerListEntry(x[0], "green"))
		self["list"] = CCcamList(list)
		self["info"] = Label()

		self["actions"] = ActionMap(["CCcamInfoActions"], {"ok": self.okClicked, "cancel": self.close}, -1)

		self["list"].onSelectionChanged.append(self.showInfo)
		self.onLayoutFinish.append(self.showInfo)

	def showInfo(self):
		info = self.getInfo()
		self["info"].setText(info)

	def getInfo(self):
		try:
			idx = self["list"].getSelectedIndex()

			info = ""
			infoList = self.infoList[idx]
			for x in infoList:
				info += x + "\n"

			return info
		except:
			return ""

	def okClicked(self):
		sel = self["list"].getCurrent()
		if sel is not None:
			self.session.open(CCcamInfoShareInfo, sel[0], self.url)

#############################################################

class CCcamInfoRemoteBox:
	def __init__(self, name, ip, username, password, port):
		self.name = name
		self.ip = ip
		self.username = username
		self.password = password
		self.port = port

#############################################################

class CCcamInfoConfigMenu(ConfigListScreen, Screen):
	def __init__(self, session, profile):
		Screen.__init__(self, session)
		Screen.setTitle(self, _("CCcam Info Setup"))
		config.cccaminfo.name.value = profile.name
		config.cccaminfo.ip.value = profile.ip
		config.cccaminfo.username.value = profile.username
		config.cccaminfo.password.value = profile.password
		config.cccaminfo.port.value = profile.port

		ConfigListScreen.__init__(self, [
			getConfigListEntry(_("Name:"), config.cccaminfo.name),
			getConfigListEntry(_("IP:"), config.cccaminfo.ip),
			getConfigListEntry(_("Username:"), config.cccaminfo.username),
			getConfigListEntry(_("Password:"), config.cccaminfo.password),
			getConfigListEntry(_("Port:"), config.cccaminfo.port)])

		self["actions"] = ActionMap(["CCcamInfoActions"], {"ok": self.okClicked, "cancel": self.exit}, -2)

	def okClicked(self):
		self.close(CCcamInfoRemoteBox(config.cccaminfo.name.value, config.cccaminfo.ip.value, config.cccaminfo.username.value, config.cccaminfo.password.value, config.cccaminfo.port.value))

	def exit(self):
		self.close(None)

#############################################################

class CCcamInfoRemoteBoxMenu(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		self.session = session
		Screen.setTitle(self, _("CCcam Remote Info"))
		self.list = []
		self.profiles = []

		self["key_red"] = Label(_("Delete"))
		self["key_green"] = Label(_("New"))
		self["key_yellow"] = Label(_("Location"))
		self["key_blue"] = Label(_("Edit"))
		self["list"] = MenuList([])

		self["actions"] = ActionMap(["CCcamInfoActions"],
			{
				"cancel": self.exit,
				"ok": self.profileSelected,
				"red": self.delete,
				"green": self.new,
				"yellow": self.location,
				"blue": self.edit
			}, -1)

		self.onLayoutFinish.append(self.readProfiles)

	def readProfiles(self):
		try:
			f = open(config.cccaminfo.profiles.value, "r")
			content = f.read()
			f.close()
		except:
			content = ""
		profiles = content.split("\n")
		for profile in profiles:
			if profile.__contains__("|"):
				tmp = profile.split("|")
				if len(tmp) == 5:
					name = tmp[0]
					ip = tmp[1]
					username = tmp[2]
					password = tmp[3]
					port = int(tmp[4])
					self.list.append(name)
					self.profiles.append(CCcamInfoRemoteBox(name, ip, username, password, port))
		self["list"].setList(self.list)

	def saveConfigs(self):
		content = ""
		for x in self.profiles:
			content = "%s\n%s|%s|%s|%s|%d" % (content, x.name, x.ip, x.username, x.password, x.port)
		try:
			f = open(config.cccaminfo.profiles.value, "w")
			f.write(content)
			f.close()
		except:
			pass

	def exit(self):
		self.saveConfigs()
		self.close(None)

	def profileSelected(self):
		self.saveConfigs()
		if len(self.list) > 0:
			idx = self["list"].getSelectionIndex()
			cur = self.profiles[idx]
			if cur.ip == "":
				url = None
			else:
				if cur.username != "" and cur.password != "":
					url = "http://%s:%s@%s:%d" % (cur.username, cur.password, cur.ip, cur.port)
				else:
					url = "http://%s:%d" % (cur.ip, cur.port)
			self.close(url)

	def delete(self):
		if len(self.list) > 0:
			idx = self["list"].getSelectionIndex()
			del self.list[idx]
			del self.profiles[idx]
			self["list"].setList(self.list)

	def new(self):
		self.session.openWithCallback(self.newCallback, CCcamInfoConfigMenu, CCcamInfoRemoteBox("Profile", "192.168.2.12", "", "", 16001))

	def newCallback(self, callback):
		if callback:
			self.list.append(callback.name)
			self.profiles.append(callback)
			self["list"].setList(self.list)

	def location(self):
		self.session.openWithCallback(self.locationCallback, LocationBox)

	def locationCallback(self, callback):
		if callback:
			config.cccaminfo.profiles.value = ("%s/CCcamInfo.profiles"%callback).replace("//", "/")
			config.cccaminfo.profiles.save()
		del self.list
		self.list = []
		del self.profiles
		self.profiles = []
		self.readProfiles()

	def edit(self):
		if len(self.list) > 0:
			idx = self["list"].getSelectionIndex()
			self.session.openWithCallback(self.editCallback, CCcamInfoConfigMenu, self.profiles[idx])

	def editCallback(self, callback):
		if callback:
			idx = self["list"].getSelectionIndex()
			del self.list[idx]
			del self.profiles[idx]
			self.list.append(callback.name)
			self.profiles.append(callback)
			self["list"].setList(self.list)

#############################################################

class CCcamInfoShareInfo(Screen):
	def __init__(self, session, hostname, url):
		Screen.__init__(self, session)
		self.session = session
		Screen.setTitle(self, _("CCcam Share Info"))
		self.hostname = hostname
		self.url = url
		self.list = []
		self.uphops = -1
		self.maxdown = -1
		self.working = True

		self["key_red"] = Label(_("Uphops +"))
		self["key_green"] = Label(_("Uphops -"))
		self["key_yellow"] = Label(_("Maxdown +"))
		self["key_blue"] = Label(_("Maxdown -"))
		self["list"] = CCcamShareList([])

		self["actions"] = ActionMap(["CCcamInfoActions"],
			{
				"cancel": self.exit,
				"red": self.uhopsPlus,
				"green": self.uhopsMinus,
				"yellow": self.maxdownPlus,
				"blue": self.maxdownMinus
			}, -1)

		self.onLayoutFinish.append(self.readShares)

	def exit(self):
		if not self.working:
			self.close()

	def readShares(self):
		getPage(self.url + "/shares").addCallback(self.readSharesCallback).addErrback(self.readSharesError)

	def readSharesError(self, error=None):
		self.session.open(MessageBox, _("Error reading webpage!"), MessageBox.TYPE_ERROR)
		self.working = False

	def readSharesCallback(self, html):
		firstLine = True
		shareList = []
		count = 0
		lines = html.split("\n")

		for l in lines:
			if l.__contains__('|'):
				if firstLine:
					firstLine = False
				else:
					list = l.split("|")
					if len(list) > 7:
						hostname = list[1].replace(" ", "")
						if (self.hostname == "None" or self.hostname == hostname) and hostname != "":
							type = list[2].replace(" ", "")
							caid = list[3].replace(" ", "")
							system = list[4].replace(" ", "")

							string = list[6]
							while string.startswith(" "):
								string = string[1:]

							while string.endswith(" "):
								string = string[:-1]

							idx = string.index(" ")
							uphops = string[:idx]
							string = string[idx+1:]

							while string.startswith(" "):
								string = string[1:]
							maxdown = string

							if len(caid) == 3:
								caid = "0" + caid

							shareList.append(CCcamShareListEntry(hostname, type, caid, system, uphops, maxdown))
							self.list.append([hostname, type, caid, system, uphops, maxdown])
							count += 1

		if self.uphops < 0:
			textUhops = _("All")
		else:
			textUhops = str(self.uphops)

		if self.maxdown < 0:
			textMaxdown = _("All")
		else:
			textMaxdown = str(self.maxdown)

		self.instance.setTitle("%s %d (%s%s / %s%s)" % (_("Available shares:"), count, _("Uphops: "), textUhops, _("Maxdown: "), textMaxdown))
		self["list"].setList(shareList)
		self.working = False

	def uhopsPlus(self):
		if not self.working:
			self.uphops += 1
			if self.uphops > 9:
				self.uphops = -1
			self.refreshList()

	def uhopsMinus(self):
		if not self.working:
			self.uphops -= 1
			if self.uphops < -1:
				self.uphops = 9
			self.refreshList()

	def maxdownPlus(self):
		if not self.working:
			self.maxdown += 1
			if self.maxdown > 9:
				self.maxdown = -1
			self.refreshList()

	def maxdownMinus(self):
		if not self.working:
			self.maxdown -= 1
			if self.maxdown < -1:
				self.maxdown = 9
			self.refreshList()

	def refreshList(self):
		shareList = []
		count = 0
		self.working = True

		for x in self.list:
			(hostname, type, caid, system, uphops, maxdown) = x
			if (uphops == str(self.uphops) or self.uphops == -1) and (maxdown == str(self.maxdown) or self.maxdown == -1):
				shareList.append(CCcamShareListEntry(hostname, type, caid, system, uphops, maxdown))
				count += 1

		if self.uphops < 0:
			textUhops = _("All")
		else:
			textUhops = str(self.uphops)

		if self.maxdown < 0:
			textMaxdown = _("All")
		else:
			textMaxdown = str(self.maxdown)

		self.instance.setTitle("%s %d (%s%s / %s%s)" % (_("Available shares:"), count, _("Uphops: "), textUhops, _("Maxdown: "), textMaxdown))
		self["list"].setList(shareList)
		self.working = False

#############################################################

class CCcamInfoConfigSwitcher(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		self.session = session
		Screen.setTitle(self, _("CCcam Config Switcher"))
		self["key_red"] = Label(_("Delete"))
		self["key_green"] = Label(_("Activate"))
		self["key_yellow"] = Label(_("Rename"))
		self["key_blue"] = Label(_("Content"))
		self["list"] = CCcamConfigList([])

		self["actions"] = ActionMap(["CCcamInfoActions"],
			{
				"ok": self.activate,
				"cancel": self.close,
				"red": self.delete,
				"green": self.activate,
				"yellow": self.rename,
				"blue": self.showContent
			}, -1)

		self.onLayoutFinish.append(self.showConfigs)

	def showConfigs(self):
		list = []

		try:
			files = listdir(CFG_path)
		except:
			files = []

		for file in files:
			if file.startswith("CCcam_") and file.endswith(".cfg"):
				list.append(CCcamConfigListEntry(CFG_path + "/"+file))

		self["list"].setList(list)

	def delete(self):
		fileName = self["list"].getCurrent()
		if fileName is not None:
			self.fileToDelete = fileName[0]
			self.session.openWithCallback(self.deleteConfirmed, MessageBox, (_("Delete %s?") % self.fileToDelete))

	def deleteConfirmed(self, yesno):
		if yesno:
			remove(self.fileToDelete)
			if fileExists(self.fileToDelete):
				self.session.open(MessageBox, _("Delete failed!"), MessageBox.TYPE_ERROR)
			else:
				self.session.open(MessageBox, _("Deleted %s!") % self.fileToDelete, MessageBox.TYPE_INFO)
				self.showConfigs()

	def activate(self):
		fileName = self["list"].getCurrent()
		if fileName is not None:
			fileName = fileName[0]
			# Delete old backup
			backupFile = "%s.backup" % CFG
			if fileExists(backupFile):
				remove(backupFile)
			# Create a backup of the original /var/etc/CCcam.cfg file
			rename(CFG, backupFile)
			# Now copy the selected cfg file
			system("cp -f %s %s" % (fileName, CFG))
			self.showConfigs()

	def rename(self):
		fileName = self["list"].getCurrent()
		if fileName is not None:
			self.fileToRename = fileName[0]
			(name, sel) = getConfigNameAndContent(self.fileToRename)
			self.session.openWithCallback(self.renameCallback, VirtualKeyBoard, title=_("Rename to:"), text=name)

	def renameCallback(self, callback):
		if callback is not None:
			try:
				f = open(self.fileToRename, "r")
				content = f.read()
				f.close()
			except:
				content = None

			if content is not None:
				content = content.replace("\r", "\n")
				if content.startswith("#CONFIGFILE NAME=") and content.__contains__("\n"):
					idx = content.index("\n")
					content = content[:idx+2]

				content = "#CONFIGFILE NAME=%s\n%s" % (callback, content)

				try:
					f = open(self.fileToRename, "w")
					f.write(content)
					f.close()
					self.session.open(MessageBox, _("Renamed %s!") % self.fileToRename, MessageBox.TYPE_INFO)
					self.showConfigs()
				except:
					self.session.open(MessageBox, _("Rename failed!"), MessageBox.TYPE_ERROR)
			else:
				self.session.open(MessageBox, _("Rename failed!"), MessageBox.TYPE_ERROR)

	def showContent(self):
		fileName = self["list"].getCurrent()
		if fileName is not None:
			try:
				f = open(fileName[0], "r")
				content = f.read()
				f.close()
			except:
				content = _("Could not open the file %s!") % fileName[0]
			self.session.open(CCcamInfoInfoScreen, content, _("CCcam Config Switcher"))

#############################################################

class CCcamInfoMenuConfig(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		self.session = session
		Screen.setTitle(self, _("CCcam Info Config"))
		self["key_red"] = Label(_("Cancel"))
		self["key_green"] = Label(_("Save"))
		self["key_yellow"] = Label(_("Location"))
		self["list"] = CCcamConfigList([])
		self.getBlacklistedMenuEntries()

		self["actions"] = ActionMap(["CCcamInfoActions"],
			{
				"ok": self.changeState,
				"cancel": self.close,
				"red": self.close,
				"green": self.save,
				"yellow": self.location
			}, -1)

		self.onLayoutFinish.append(self.showConfigs)

	def getBlacklistedMenuEntries(self):
		try:
			f = open(config.cccaminfo.blacklist.value, "r")
			content = f.read()
			f.close()
			self.blacklisted = content.split("\n")
		except:
			self.blacklisted = []

	def changeState(self):
		cur = self["list"].getCurrent()
		if cur is not None:
			cur = cur[0]
			if cur in self.blacklisted:
				idx = 0
				for x in self.blacklisted:
					if x == cur:
						del self.blacklisted[idx]
						break
					idx += 1
			else:
				self.blacklisted.append(cur)
		self.showConfigs()

	def showConfigs(self):
		list = []
		for x in menu_list:
			if x != _("Menu config"):
				if x in self.blacklisted:
					list.append(CCcamMenuConfigListEntry(x, True))
				else:
					list.append(CCcamMenuConfigListEntry(x, False))
		self["list"].setList(list)

	def save(self):
		content = ""
		for x in self.blacklisted:
			content = content + x + "\n"
		content = content.replace("\n\n", "\n")
		try:
			f = open(config.cccaminfo.blacklist.value, "w")
			f.write(content)
			f.close()
			self.session.open(MessageBox, _("Configfile %s saved.") % config.cccaminfo.blacklist.value, MessageBox.TYPE_INFO)
		except:
			self.session.open(MessageBox, _("Could not save configfile %s!") % config.cccaminfo.blacklist.value, MessageBox.TYPE_ERROR)

	def location(self):
		self.session.openWithCallback(self.locationCallback, LocationBox)

	def locationCallback(self, callback):
		if callback:
			config.cccaminfo.blacklist.value = ("%s/CCcamInfo.blacklisted"%callback).replace("//", "/")
			config.cccaminfo.blacklist.save()
