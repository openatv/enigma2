from enigma import eListbox
from enigma import eListboxPythonMultiContent
from enigma import ePicLoad
from enigma import loadPNG
from enigma import gFont
from enigma import eEnv
### Picturelist
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Screens.InputBox import InputBox
from Screens.ChoiceBox import ChoiceBox
from Screens.InfoBarGenerics import InfoBarNotifications
from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.MenuList import MenuList
from Components.Sources.List import List
from Components.FileList import EXTENSIONS
from Components.AVSwitch import AVSwitch
## configmenu
from Components.config import config, ConfigSubsection,ConfigSelection,ConfigText,ConfigYesNo
####
from Components.Input import Input
from Components.Pixmap import Pixmap
from Plugins.Plugin import PluginDescriptor
from Tools.Notifications import AddPopup
### System
import os
from re import compile
from itertools import chain
## XML
from pyexpat import ExpatError
import xml.dom.minidom

### my
from WebcamViewConfig import WebcamViewerMenu
from PictureScreen import PictureScreen
from WebcamTravel import TravelWebcamviewer
###
myname = "Webcam Viewer"
myversion = "1.2"

config.plugins.pictureviewer = ConfigSubsection()
config.plugins.pictureviewer.slideshowtime = ConfigSelection(default="5000", choices = [("5000", _("5 Seconds")), ("10000", _("10 Seconds")), ("20000", _("20 Seconds")), ("60000", _("1 Minute"))])
config.plugins.pictureviewer.slideshowmode = ConfigSelection(default="0", choices = [("0", _("normal")), ("1", _("endless"))])
#not editable configs
config.plugins.pictureviewer.slideshowext = ConfigText(default=".3ssl")
config.plugins.pictureviewer.matchingPattern = ConfigText(default="(?i)^.*\.(jpeg|jpg|jpe|png|bmp|gif)")
config.plugins.pictureviewer.slideshowdir = ConfigText(default="/media/hdd/slideshows/")
config.plugins.pictureviewer.rootdir = ConfigText(default="/media/")
config.plugins.pictureviewer.stopserviceonstart = ConfigYesNo(default = False)
SLIDESHOWMODE_NORMAL = 0
SLIDESHOWMODE_REPEAT = 1

originalservice = None
mysession = None


def startPictureviewer(session, **kwargs):
	global originalservice, mysession
	mysession = session
	originalservice = session.nav.getCurrentlyPlayingServiceReference()
	if config.plugins.pictureviewer.stopserviceonstart.value:
		session.nav.stopService()
	session.openWithCallback(mainCB, PictureViewer)

def startWebcamviewer(session, **kwargs):
	global originalservice, mysession
	mysession = session
	originalservice = session.nav.getCurrentlyPlayingServiceReference()
	if config.plugins.pictureviewer.stopserviceonstart.value:
		session.nav.stopService()
	xmlpaths = [
		eEnv.resolve("${sysconfdir}/enigma2/webcam.xml"),
		eEnv.resolve("${libdir}/enigma2/python/Plugins/Extensions/IniWebcamViewer/webcam.xml"),
	]
	warnmsgs = []
	errmsgs = []
	while xmlpaths:
		path = xmlpaths.pop(0)
		if not os.path.isfile(path):
			warnmsgs.append(_("Config file %s not found.") % (path))
			continue
		with open(path) as fp:
			try:
				xmlnode = xml.dom.minidom.parse(fp)
				session.openWithCallback(mainCB, WebcamViewer, xmlnode.childNodes[1])

				# show errors in a popup and cleanup pending messages
				if errmsgs:
					AddPopup(
						'\n'.join(errmsgs),
						MessageBox.TYPE_WARNING,
						-1
					)
				del errmsgs[:]
				del warnmsgs[:]
				break
			except ExpatError as e:
				errmsgs.append(_("Loading config file %s failed: %s") % (path, e))
	if errmsgs or warnmsgs:
		session.open(
			MessageBox,
			'\n'.join(chain(warnmsgs, errmsgs)),
			MessageBox.TYPE_WARNING
		)




def mainCB():
	global originalservice, mysession
	if config.plugins.pictureviewer.stopserviceonstart.value:
		mysession.nav.playService(originalservice)

def menu(menuid, **kwargs):
    if menuid == 'id_mainmenu_photos':
        return [(_('Web Cams'), startWebcamviewer, 'id_mainmenu_photos_webcam', 70)]
    return []
  
def Plugins(path, **kwargs):
	global plugin_path
	plugin_path = path  
	list = [PluginDescriptor(where=PluginDescriptor.WHERE_MENU, fnc=menu)]
	return list

###################
class ViewerSelectScreen(Screen):
	skin = ""
	def __init__(self, session, args = 0):
		skin =  """<screen position="93,70" size="550,450">
		<widget name="list" position="0,0" size="550,450"  />
		</screen>"""
		self.skin = skin
		Screen.__init__(self, session)
		self.slideshowfiles = []
		self.slideshowfiles.append((_("WebcamViewer"),STARTWEBCAMVIEWER))
		self.slideshowfiles.append((_("online webcam.travel"),STARTWEBCAMTRAVEL))
		self["list"] = MenuList(self.slideshowfiles)
		self["actions"] = ActionMap(["WizardActions", "MenuActions", "DirectionActions", "ShortcutActions"],
			{
			 "ok": self.go,
			 "back": self.close
			 }, -1)

	def go(self):
		selection = self["list"].getCurrent()
		if selection:
			self.close(self.session,selection[1])


###################
class Slideshow:
	filelist = []
	currentslideshowitem = 0
	wbviewer = False

	def __init__(self, session, callback):
		self.session = session
		self.callback = callback

	def setfiles(self, filelist):
		self.filelist = filelist

	def start(self):
		if len(self.filelist) > 0:
			self.currentslideshowitem = -1
			self.nextSlideshowItem()

	def nextSlideshowItem(self, prev = False):
		currentslideshowitem = self.currentslideshowitem
		if prev:
   			currentslideshowitem -= 2
		if currentslideshowitem < 0:
			currentslideshowitem = -1
		if currentslideshowitem is not (len(self.filelist) - 1):
			currentslideshowitem += 1
			filetoshow = self.filelist[currentslideshowitem][1]
			if not self.wbviewer:
				self.wbviewer = self.session.openWithCallback(
									self.cb,
									PictureScreen,
									filetoshow.split("/")[-1],
									filetoshow,
									slideshowcallback = self.nextSlideshowItem
				)
			else:
				self.wbviewer.filename = filetoshow
				self.wbviewer.do()
			self.currentslideshowitem = currentslideshowitem
		elif int(config.plugins.pictureviewer.slideshowmode.value) is SLIDESHOWMODE_REPEAT:
			print "["+myname+"] restarting slideshow"
			self.start()
		else:
			print "["+myname+"] slideshow finished"
			self.wbviewer.exit()
			self.cb()

	def cb(self):
		self.callback()
###################
class PictureViewer(Screen):
	skin = ""
	filelist = []
	currList = "slideshowlist"
	wbviewer = False
	loadedslideshowlistlistname = False

	def __init__(self, session, args = 0):
		skin =  """<screen position="93,70" size="550,450" title="%s">
		<widget name="menu" position="1,1" size="275,400"  scrollbarMode="showOnDemand" />
		<widget name="pixmap" position="275,1" size="275,200" backgroundColor="red" />
		<widget name="slist" position="275,200" size="275,200"  scrollbarMode="showOnDemand" />
		<widget name="buttonred" position="6,405" size="130,40" backgroundColor="red" valign="center" halign="center" zPosition="2" foregroundColor="white" font="Regular;18" />
		<widget name="buttongreen" position="142,405" size="130,40" backgroundColor="green" valign="center" halign="center" zPosition="2" foregroundColor="white" font="Regular;18" />
		<widget name="buttonyellow" position="278,405" size="130,40" backgroundColor="yellow" valign="center" halign="center" zPosition="2" foregroundColor="white" font="Regular;18" />
		<widget name="buttonblue" position="414,405" size="130,40" backgroundColor="blue" valign="center" halign="center" zPosition="2" foregroundColor="white" font="Regular;18" />
		</screen>""" % config.plugins.pictureviewer.rootdir.value
		self.skin = skin
		Screen.__init__(self, session)

		self.filelist = PictureList(config.plugins.pictureviewer.rootdir.value, matchingPattern = config.plugins.pictureviewer.matchingPattern.value)
		self["menu"] = self.filelist

		self.preview = Pixmap()
		self["pixmap"] = self.preview

		self.slideshowfiles = []
		self.slideshowlist =MenuList(self.slideshowfiles)
		self["slist"] = self.slideshowlist

		self["buttonred"] = Label("")
		self["buttongreen"] = Label("")
		self["buttonyellow"] = Label("")
		self["buttonblue"] = Label("")

		self["actions"] = ActionMap(["WizardActions", "MenuActions", "DirectionActions", "ShortcutActions"],
			{
			 "ok": self.go,
			 "back": self.close,
			 "menu": self.openMenu,
			 "up": self.up,
			 "down": self.down,
			 "left": self.leftUp,
			 "right": self.rightUp,
			 "red": self.KeyRed,
			 "green": self.KeyGreen,
			 "yellow": self.KeyYellow,
			 "blue": self.switchList,
			 }, -1)

		self.onLayoutFinish.append(self.switchList)
		self.onLayoutFinish.append(self.updateInfoPanel)

	def KeyGreen(self):
		if self.currList is "filelist":
			# adding all files in current dir to slideshowlist
			dirname = self["menu"].getCurrentDir()
			if os.path.isdir(dirname):
				s = os.listdir(dirname)
				s.sort()
				for file in s:
					if compile(config.plugins.pictureviewer.matchingPattern.value).search(dirname + file):
						self.slideshowfiles.append((_(file),dirname + file))
				self["slist"].l.setList(self.slideshowfiles)
		else:
			#loading list
			list = []
			try:
				for file in os.listdir(config.plugins.pictureviewer.slideshowdir.value):
					if file.endswith(config.plugins.pictureviewer.slideshowext.value):
						list.append((_(file.split("/")[-1]),file))
				self.session.openWithCallback(
						self.fileToLoadFilelistEntered,
						ChoiceBox,
						_("select List to load"),
						list
				)
			except IOError,e:
				print "["+myname+"] IOError:",e
			except OSError,e:
				print "["+myname+"] OSError:",e

	def KeyRed(self):
		if self.currList is "filelist" :
			#do slideshow
			self.hide()
			x = Slideshow(self.session, self.show)
			x.setfiles(self.slideshowfiles)
			x.start()
		else:
			# save filelist
			if not self.loadedslideshowlistlistname:
				newname = "slideshowlist"
			else:
				newname = self.loadedslideshowlistlistname
			self.session.openWithCallback(
					self.fileToSaveFilelistEntered,
					InputBox,
					title = _("Enter filename to save the List:"),
					text = newname,
					maxSize = False,
					type = Input.TEXT
			)

	def fileToLoadFilelistEntered(self, fileselection):
		if fileselection is not None:
			   try:
				   filename = fileselection[1]
				   fp = open(config.plugins.pictureviewer.slideshowdir.value + filename)
				   list = []
				   for x in fp.readlines():
					   file = x.replace("\n","")
					   if x.startswith("#"):
						   pass
					   elif not os.path.exists(file):
						   print "["+myname+"] loaded file from filelist isnt avaible! ignoreing ->", file
					   else:
						   list.append((_(file.split("/")[-1]), file))
				   self.slideshowfiles = list
				   self["slist"].l.setList(self.slideshowfiles)
				   self.loadedslideshowlistlistname = filename.replace(config.plugins.pictureviewer.slideshowext.value, "")
			   except IOError, e:
				   print "["+myname+"] error:", e

	def fileToSaveFilelistEntered(self, filename):
		if filename is not None:
			print "["+myname+"] saving list to ", config.plugins.pictureviewer.slideshowdir.value+filename + config.plugins.pictureviewer.slideshowext.value
			try:
				if not os.path.exists(config.plugins.pictureviewer.slideshowdir.value):
					print "+" * 10, os.path.basename(filename)
					os.mkdir(config.plugins.pictureviewer.slideshowdir.value)
				fp = open(config.plugins.pictureviewer.slideshowdir.value + filename+config.plugins.pictureviewer.slideshowext.value, "w")
				fp.write("# this is a slideshow file for "+myname+" made by V"+myversion+"\n")
				fp.write("# you can make your own... each line with full path of the imagefile\n")
				fp.write("# by importing this file,we will ignoring a file if is doesnt exist\n")
				for x in self.slideshowfiles:
					fp.write(x[1] + "\n")
				fp.close()
			except IOError, e:
				print "["+myname+"] error:", e

	def KeyYellow(self):
		if self.currList is "filelist":
			# add picture to list
			fullfile = self["menu"].getSelection()[0]
			if os.path.isfile(fullfile):
				self.slideshowfiles.append((_(fullfile.split("/")[-1]), fullfile))
				self["slist"].l.setList(self.slideshowfiles)
		else:
			# deleting an Picture
			if len(self.slideshowfiles) >= 1:
				indexinlist = self["slist"].l.getCurrentSelectionIndex()
				self.slideshowfiles.pop(indexinlist)
				self["slist"].l.setList(self.slideshowfiles)

	def switchList(self):
		if self.currList is "filelist" :
			# Slideshow activieren
			self.filelist.selectionEnabled(0)
			self.slideshowlist.selectionEnabled(1)
			self["buttonred"].setText("speichern")
			self["buttongreen"].setText("laden")
			self["buttonyellow"].setText("loeschen")
			self["buttonblue"].setText("Dateien")
			self.currList = "slideshowlist"
		else:
			# filelist activieren
			self.filelist.selectionEnabled(1)
			self.slideshowlist.selectionEnabled(0)
			self["buttonred"].setText("starte Slideshow")
			self["buttongreen"].setText("alle hinzufuegen")
			self["buttonyellow"].setText("hinzufuegen")
			self["buttonblue"].setText("Slideshow bearbeiten")
			self.currList = "filelist"

	def go(self):
		if self.currList is "filelist" :
			selection = self["menu"].getSelection()
			if self.filelist.canDescent():
				self.setTitle(selection[0])
				self.filelist.descent()
			else:
				if selection[1] == True: # isDir
					pass
				else:
					print "["+myname+"] file selected ", selection[0]
					if os.path.isfile(selection[0]):
						self.session.open(PictureScreen,selection[0].split("/")[-1], selection[0])
					else:
						print "["+myname+"] file not found ", selection[0]
		else:
			self.updateInfoPanel()

	def up(self):
		 if self.currList is "filelist":
			 self.filelist.up()
			 self.updateInfoPanel()
		 else:
			 self.slideshowlist.up()

	def leftUp(self):
		 if self.currList is "filelist":
			 self.filelist.pageUp()
			 self.updateInfoPanel()
		 else:
			 self.slideshowlist.pageUp()

	def rightUp(self):
		if self.currList is "filelist":
			 self.filelist.pageDown()
			 self.updateInfoPanel()
		else:
			 self.slideshowlist.pageDown()

	def down(self):
		 if self.currList is "filelist":
			 self.filelist.down()
			 self.updateInfoPanel()
		 else:
			 self.slideshowlist.down()

	def updateInfoPanel(self):
		if self.currList is "filelist":
			selectedfile = self["menu"].getSelection()[0]
		else:
			selectedfile = self["slist"].l.getCurrentSelection()[1]
		sc=AVSwitch().getFramebufferScale()
		self.picload = ePicLoad()
		self.picload.PictureData.get().append(self.updateInfoPanelCB)
		self.picload.setPara((self["pixmap"].instance.size().width(), self["pixmap"].instance.size().height(), sc[0], sc[1], False, 1, "#FF000000"))
		self.picload.startDecode(selectedfile)


	def updateInfoPanelCB(self, picInfo = None):
		ptr = self.picload.getData()
		if ptr is not None:
			self["pixmap"].instance.setPixmap(ptr)
		else:
			pass

	def output(self,str):
		print "+" * 10, str

	def openMenu(self):
		self.session.open(WebcamViewerMenu)
###################
class WebcamViewer(Screen, InfoBarNotifications):
	skin = ""
	filelist = []
	def __init__(self, session,xmlnode, args = 0):
		self.xmlnode = xmlnode
		screen_x = 736
		screen_y = 576
		size_x = 350
		size_y = 250
		pos_x = (screen_x/2)-(size_x/2)
		pos_y = (screen_y/2)-(size_y/2)
		skin = """
		<screen position="%i,%i" size="%i,%i" title="%s">
			<widget name="menu" position="1,1" size="%i,%i"  scrollbarMode="showOnDemand"/>
		</screen>""" % (pos_x,pos_y,size_x,size_y,myname,size_x,size_y)
		self.skin = skin
		Screen.__init__(self, session)
		InfoBarNotifications.__init__(self)

		self.filelist = List(self.getMenuData())
		self["menu"] = self.filelist
		self["actions"] = ActionMap(["WizardActions", "DirectionActions"],
			{
			 "ok": self.go,
			 "back": self.close,
			 }, -1)
		self.onLayoutFinish.append(self.settingTitle)

	def settingTitle(self):
		self.setTitle(myname + ": " + self.menutitle)

	def go(self):
		selected = self["menu"].getCurrent()[1]
		menuitemtitle = self["menu"].getCurrent()[0]
		type = selected[0]
		data = selected[1]
		if menuitemtitle.startswith("webcam.travel"):
			self.session.openWithCallback(self.cb, TravelWebcamviewer)
		elif type.startswith("cam"):
			self.session.open(PictureScreen, menuitemtitle, data)
		else:
			self.hide()
			self.session.openWithCallback(self.cb, WebcamViewer, data)

	def cb(self):
		self.show()

	def getMenuData(self):
		xloader = XMLloader()
		self.menutitle = xloader.getScreenXMLTitle(self.xmlnode)
		data =[]
		if self.menutitle =="Mainmenu":
			data.append((_("webcam.travel"), "webcam.travel"))
		for node in self.xmlnode.childNodes:
			if node.nodeType != xml.dom.minidom.Element.nodeType or node.tagName != 'menu':
				continue
			nodex = {}
			nodex['name'] = xloader.get_txt(node, "name", "no name")
			data.append((_("*" + nodex['name']), ["node", node]))

		for node in self.xmlnode.childNodes:
			if node.nodeType != xml.dom.minidom.Element.nodeType or node.tagName != 'cam':
				continue
			nodex = {}
			nodex['name'] = xloader.get_txt(node, "name", "no name")
			nodex['url'] =xloader.get_txt(node, "url", "no url")
			data.append((_(nodex['name']), ["cam", nodex['url']]))
		return data
###################

##################
class PictureList(MenuList):
	def __init__(self, directory, matchingPattern = None, enableWrapAround = False):
		MenuList.__init__(self, None, enableWrapAround, eListboxPythonMultiContent)
		self.showDirectories = True
		self.showFiles = True
		self.isTop = False
		self.matchingPattern = matchingPattern
		self.changeDir(directory)
		self.l.setFont(0, gFont("Regular", 18))
		self.currentDir = directory

	def getCurrentDir(self):
		return self.currentDir

	def getSelection(self):
		return self.l.getCurrentSelection()[0]

	def getFileList(self):
		return self.list

	def changeDir(self, directory):
		self.currentDir = directory
		self.list = []

		directories = []
		files = []
		files = os.listdir(directory)
		files.sort()
		tmpfiles = files[:]
		for x in tmpfiles:
			if os.path.isdir(directory + "/" + x):
				directories.append(x)
				files.remove(x)
		directories.sort()
		files.sort()
		if directory != "/" and self.showDirectories and not self.isTop:
			self.list.append(self.getPictureEntryComponent("..", '/'.join(directory.split('/')[:-2]) + '/', True))

		if self.showDirectories:
			for x in directories:
				name = (directory+x).split('/')[-1]
				self.list.append(self.getPictureEntryComponent(name, '/'.join(directory.split('/')[:-1]) + '/' + x + '/', True))

		if self.showFiles:
			for x in files:
				path = directory + x
				name = x
				if self.matchingPattern is not None:
					if compile(self.matchingPattern).search(path):
						self.list.append(self.getPictureEntryComponent(name,path, False))
				else:
					pass

		self.l.setList(self.list)

	def canDescent(self):
		return self.getSelection()[1]

	def descent(self):
		self.changeDir(self.getSelection()[0])

	def getFilename(self):
		return self.getSelection()[0].getPath()

	def getServiceRef(self):
		return self.getSelection()[0]

	def postWidgetCreate(self, instance):
		MenuList.postWidgetCreate(self, instance)
		instance.setItemHeight(23)

	def getPictureEntryComponent(self,name, absolute, isDir):
		""" name={angezeigter Name}, absolute={vollstaendiger Pfad}, isDir={True,False} """
		res = [ (absolute, isDir) ]
		res.append((eListboxPythonMultiContent.TYPE_TEXT, 35, 1, 200, 20, 0, 0, name))
		if isDir:
			png = loadPNG("/usr/share/enigma2/extensions/directory.png")
		else:
			extension = name.split('.')
			extension = extension[-1].lower()
			if EXTENSIONS.has_key(extension):
				png = loadPNG("/usr/share/enigma2/extensions/" + EXTENSIONS[extension] + ".png")
			else:
				png = None
		if png is not None:
			res.append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHATEST, 10, 2, 20, 20, png))
		return res


##################
class XMLloader:
	DEFAULT_NAMESPACES = (
		  None, # RSS 0.91, 0.92, 0.93, 0.94, 2.0
		  'http://purl.org/rss/1.0/', # RSS 1.0
		  'http://my.netscape.com/rdf/simple/0.9/' # RSS 0.90
		)
	DUBLIN_CORE = ('http://purl.org/dc/elements/1.1/',)
	def getElementsByTagName(self, node, tagName, possibleNamespaces = DEFAULT_NAMESPACES):
		for namespace in possibleNamespaces:
			children = node.getElementsByTagNameNS(namespace, tagName)
			if len(children):
				return children
		return []

	def node_data(self, node, tagName, possibleNamespaces = DEFAULT_NAMESPACES):
		children = self.getElementsByTagName(node, tagName, possibleNamespaces)
		node = len(children) and children[0] or None
		return node and "".join([child.data.encode("utf-8") for child in node.childNodes]) or None

	def get_txt(self, node, tagName, default_txt = ""):
		"""
		Liefert den Inhalt >tagName< des >node< zurueck, ist dieser nicht
		vorhanden, wird >default_txt< zurueck gegeben.
		"""
		return self.node_data(node, tagName) or self.node_data(node, tagName, self.DUBLIN_CORE) or default_txt

	def getScreenXMLTitle(self,node):
		return self.get_txt(node, "name", "no title")

