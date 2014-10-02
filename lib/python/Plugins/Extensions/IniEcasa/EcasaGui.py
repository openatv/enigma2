from __future__ import print_function

#pragma mark - GUI

#pragma mark Screens
from Screens.ChoiceBox import ChoiceBox
from Screens.Screen import Screen
from Screens.HelpMenu import HelpableScreen
from Screens.InfoBarGenerics import InfoBarNotifications
from Screens.LocationBox import LocationBox
from Screens.MessageBox import MessageBox
from Plugins.SystemPlugins.Toolkit.NTIVirtualKeyBoard import NTIVirtualKeyBoard
from EcasaSetup import EcasaSetup

#pragma mark Components
from Components.ActionMap import HelpableActionMap
from Components.AVSwitch import AVSwitch
from Components.Label import Label
from Components.Pixmap import Pixmap, MovingPixmap
from Components.Sources.StaticText import StaticText
from Components.Sources.List import List

#pragma mark Configuration
from Components.config import config

#pragma mark Picasa
from .PicasaApi import PicasaApi
from Plugins.SystemPlugins.Toolkit.TagStrip import strip_readable

#pragma mark Flickr
from .FlickrApi import FlickrApi

from enigma import ePicLoad, eTimer, getDesktop
from Tools.Directories import resolveFilename, SCOPE_PLUGINS
from Tools.Notifications import AddPopup
from collections import deque
from Plugins.SystemPlugins.Toolkit.SimpleThread import SimpleThread

try:
	xrange = xrange
except NameError:
	xrange = range

our_print = lambda *args, **kwargs: print("[EcasaGui]", *args, **kwargs)

AUTHENTICATION_ERROR_ID = "EcasaAuthenticationError"

class EcasaPictureWall(Screen, HelpableScreen, InfoBarNotifications):
	"""Base class for so-called "picture walls"."""
	PICS_PER_PAGE = 15
	PICS_PER_ROW = 5
	skin = """<screen position="center,center" size="600,380">
		<ePixmap position="0,0" size="140,40" pixmap="skin_default/buttons/red.png" transparent="1" alphatest="on"/>
		<ePixmap position="140,0" size="140,40" pixmap="skin_default/buttons/green.png" transparent="1" alphatest="on"/>
		<ePixmap position="280,0" size="140,40" pixmap="skin_default/buttons/yellow.png" transparent="1" alphatest="on"/>
		<ePixmap position="420,0" size="140,40" pixmap="skin_default/buttons/blue.png" transparent="1" alphatest="on"/>
		<ePixmap position="565,10" size="35,25" pixmap="skin_default/buttons/key_menu.png" alphatest="on"/>
		<widget source="key_red" render="Label" position="0,0" zPosition="1" size="140,40" valign="center" halign="center" font="Regular;21" transparent="1" foregroundColor="white" shadowColor="black" shadowOffset="-1,-1"/>
		<widget source="key_green" render="Label" position="140,0" zPosition="1" size="140,40" valign="center" halign="center" font="Regular;21" transparent="1" foregroundColor="white" shadowColor="black" shadowOffset="-1,-1"/>
		<widget source="key_yellow" render="Label" position="280,0" zPosition="1" size="140,40" valign="center" halign="center" font="Regular;21" transparent="1" foregroundColor="white" shadowColor="black" shadowOffset="-1,-1"/>
		<widget source="key_blue" render="Label" position="420,0" zPosition="1" size="140,40" valign="center" halign="center" font="Regular;21" transparent="1" foregroundColor="white" shadowColor="black" shadowOffset="-1,-1"/>
		<widget name="waitingtext" position="100,179" size="400,22" valign="center" halign="center" font="Regular;22"/>
		<widget name="image0"  position="30,50"   size="90,90"/>
		<widget name="image1"  position="140,50"  size="90,90"/>
		<widget name="image2"  position="250,50"  size="90,90"/>
		<widget name="image3"  position="360,50"  size="90,90"/>
		<widget name="image4"  position="470,50"  size="90,90"/>
		<widget name="image5"  position="30,160"  size="90,90"/>
		<widget name="image6"  position="140,160" size="90,90"/>
		<widget name="image7"  position="250,160" size="90,90"/>
		<widget name="image8"  position="360,160" size="90,90"/>
		<widget name="image9"  position="470,160" size="90,90"/>
		<widget name="image10" position="30,270"  size="90,90"/>
		<widget name="image11" position="140,270" size="90,90"/>
		<widget name="image12" position="250,270" size="90,90"/>
		<widget name="image13" position="360,270" size="90,90"/>
		<widget name="image14" position="470,270" size="90,90"/>
		<!-- TODO: find some better picture -->
		<widget name="highlight" position="30,142" size="90,5"/>
		</screen>"""
	def __init__(self, session, api=None):
		Screen.__init__(self, session)
		HelpableScreen.__init__(self)
		InfoBarNotifications.__init__(self)

		if api is None:
			if config.plugins.ecasa.last_backend.value == 'picasa':
				self.api = PicasaApi(cache=config.plugins.ecasa.cache.value)
			else:
				self.api = FlickrApi(config.plugins.ecasa.flickr_api_key.value, cache=config.plugins.ecasa.cache.value)
			try:
				self.api.setCredentials(
					config.plugins.ecasa.google_username.value,
					config.plugins.ecasa.google_password.value
				)
			except Exception as e:
				AddPopup(
					_("Unable to authenticate with Google: %s.") % (e.message),
					MessageBox.TYPE_ERROR,
					5,
					id=AUTHENTICATION_ERROR_ID,
				)
		else:
			self.api = api

		self["key_red"] = StaticText(_("<"))
		#self["key_green"] = StaticText(_("Albums"))
		self["key_green"] = StaticText()
		self["key_yellow"] = StaticText(_("Search"))
		self["key_blue"] = StaticText(_(">"))
		for i in xrange(self.PICS_PER_PAGE):
			self['image%d' % i] = Pixmap()
			self['title%d' % i] = StaticText()
		self["highlight"] = MovingPixmap()
		self["waitingtext"] = Label(_("Please wait... Loading list..."))

		self["overviewActions"] = HelpableActionMap(self, "EcasaOverviewActions",
			{
				"up": self.up,
				"down": self.down,
				"left": self.left,
				"right": self.right,
				"blue": (self.nextPage, _("Show next page")),
				"red": (self.prevPage, _("Show previous page")),
				"select": self.select,
				"exit": self.close,
				#"albums":(self.albums, _("Show your albums (if logged in)")),
				"search":(self.search, _("Start a new search")),
				#"contextMenu":(self.contextMenu, _("Open context menu")),
			}, prio=-1)

		self.offset = 0
		self.__highlighted = 0
		self.pictures = ()

		# thumbnail loader
		self.picload = ePicLoad()
		self.picload.PictureData.get().append(self.gotPicture)
		self.currentphoto = None
		self.queue = deque()

		self.onLayoutFinish.append(self.layoutFinished)

	def layoutFinished(self):
		self["highlight"].instance.setPixmapFromFile(resolveFilename(SCOPE_PLUGINS, "Extensions/IniEcasa/highlighted.png"))
		self["highlight"].hide()

		size = self['image0'].instance.size()
		sc = AVSwitch().getFramebufferScale()
		self.picload.setPara((size.width(), size.height(), sc[0], sc[1], False, 1, '#ff000000'))

	@property
	def highlighted(self):
		return self.__highlighted

	@highlighted.setter
	def highlighted(self, highlighted):
		our_print("setHighlighted", highlighted)
		# only allow to select valid pictures
		if highlighted + self.offset >= len(self.pictures): return

		self.__highlighted = highlighted
		pixmap = self['image%d' % highlighted]
		origpos = pixmap.getPosition()
		origsize = pixmap.instance.size()
		# TODO: hardcoded highlight offset is evil :P
		self["highlight"].moveTo(origpos[0], origpos[1]+origsize.height()+2, 1)
		self["highlight"].startMoving()

	def gotPicture(self, picInfo=None):
		ptr = self.picload.getData()
		idx = self.pictures.index(self.currentphoto)
		realIdx = (idx - self.offset) % self.PICS_PER_PAGE
		if ptr is not None:
			self['image%d' % realIdx].instance.setPixmap(ptr)
		else:
			our_print("gotPicture got invalid results for idx", idx, "("+str(realIdx)+")")
			# NOTE: we could use a different picture here that indicates a failure
			self['image%d' % realIdx].instance.setPixmap(None)
			# NOTE: the thread WILL most likely be hung and NOT recover from it, so we should remove the old picload and create a new one :/
		self.currentphoto = None
		self.maybeDecode()

	def maybeDecode(self):
		if self.currentphoto is not None: return
		try:
			filename, self.currentphoto = self.queue.pop()
		except IndexError:
			our_print("no queued photos")
			# no more pictures
			pass
		else:
			self.picload.startDecode(filename)

	def pictureDownloaded(self, tup):
		filename, photo = tup
		self.queue.append((filename, photo))
		self.maybeDecode()

	def pictureDownloadFailed(self, tup):
		error, photo = tup
		our_print("pictureDownloadFailed", error, photo)
		# TODO: indicate in gui

	def setup(self):
		our_print("setup")
		self["waitingtext"].hide()
		self["highlight"].show()
		self.queue.clear()
		pictures = self.pictures
		for i in xrange(self.PICS_PER_PAGE):
			try:
				our_print("trying to initiate download of idx", i+self.offset)
				picture = pictures[i+self.offset]
				self.api.downloadThumbnail(picture).addCallbacks(self.pictureDownloaded, self.pictureDownloadFailed)
			except IndexError:
				# no more pictures
				self['image%d' % i].instance.setPixmap(None)
			except Exception as e:
				our_print("unexpected exception in setup:", e)

	def up(self):
		# TODO: implement for incomplete pages
		highlighted = (self.highlighted - self.PICS_PER_ROW) % self.PICS_PER_PAGE
		our_print("up. before:", self.highlighted, ", after:", highlighted)
		self.highlighted = highlighted

		# we requested an invalid idx
		if self.highlighted != highlighted:
			# so skip another row
			highlighted = (highlighted - self.PICS_PER_ROW) % self.PICS_PER_PAGE
			our_print("up2. before:", self.highlighted, ", after:", highlighted)
			self.highlighted = highlighted

	def down(self):
		# TODO: implement for incomplete pages
		highlighted = (self.highlighted + self.PICS_PER_ROW) % self.PICS_PER_PAGE
		our_print("down. before:", self.highlighted, ", after:", highlighted)
		self.highlighted = highlighted

		# we requested an invalid idx
		if self.highlighted != highlighted:
			# so try to skip another row
			highlighted = (highlighted + self.PICS_PER_ROW) % self.PICS_PER_PAGE
			our_print("down2. before:", self.highlighted, ", after:", highlighted)
			self.highlighted = highlighted

	def left(self):
		highlighted = (self.highlighted - 1) % self.PICS_PER_PAGE
		our_print("left. before:", self.highlighted, ", after:", highlighted)
		self.highlighted = highlighted

		# we requested an invalid idx
		if self.highlighted != highlighted:
			# go to last possible item
			highlighted = (len(self.pictures) - 1) % self.PICS_PER_PAGE
			our_print("left2. before:", self.highlighted, ", after:", highlighted)
			self.highlighted = highlighted

	def right(self):
		highlighted = (self.highlighted + 1) % self.PICS_PER_PAGE
		if highlighted + self.offset >= len(self.pictures):
			highlighted = 0
		our_print("right. before:", self.highlighted, ", after:", highlighted)
		self.highlighted = highlighted
	def nextPage(self):
		our_print("nextPage")
		if not self.pictures: return
		offset = self.offset + self.PICS_PER_PAGE
		Len = len(self.pictures)
		if offset >= Len:
			self.offset = 0
		else:
			self.offset = offset
			if offset + self.highlighted > Len:
				self.highlighted = Len - offset - 1
		self.setup()
	def prevPage(self):
		our_print("prevPage")
		if not self.pictures: return
		offset = self.offset - self.PICS_PER_PAGE
		if offset < 0:
			Len = len(self.pictures) - 1
			offset = Len - (Len % self.PICS_PER_PAGE)
			self.offset = offset
			if offset + self.highlighted >= Len:
				self.highlighted = Len - offset
		else:
			self.offset = offset
		self.setup()

	def prevFunc(self):
		old = self.highlighted
		self.left()
		highlighted = self.highlighted
		if highlighted > old:
			self.prevPage()

		photo = None
		try:
			# NOTE: using self.highlighted as prevPage might have moved this if the page is not full
			photo = self.pictures[self.highlighted+self.offset]
		except IndexError:
			pass
		return photo

	def nextFunc(self):
		old = self.highlighted
		self.right()
		highlighted = self.highlighted
		if highlighted < old:
			self.nextPage()

		photo = None
		try:
			# NOTE: using self.highlighted as nextPage might have moved this if the page is not full
			photo = self.pictures[self.highlighted+self.offset]
		except IndexError:
			pass
		return photo

	def select(self):
		try:
			photo = self.pictures[self.highlighted+self.offset]
		except IndexError:
			our_print("no such picture")
			# TODO: indicate in gui
		else:
			self.session.open(EcasaPicture, photo, api=self.api, prevFunc=self.prevFunc, nextFunc=self.nextFunc)
	def albums(self):
		self.session.open(EcasaAlbumview, self.api, user=config.plugins.ecasa.user.value)
	def search(self):
		self.session.openWithCallback(
			self.searchCallback,
			NTIVirtualKeyBoard,
			title=_("Enter text to search for")
		)
	def searchCallback(self, text=None):
		if text:
			# Maintain history
			history = config.plugins.ecasa.searchhistory.value
			if text not in history:
				history.insert(0, text)
				del history[10:]
			else:
				history.remove(text)
				history.insert(0, text)
			config.plugins.ecasa.searchhistory.save()

			thread = SimpleThread(lambda:self.api.getSearch(text, limit=str(config.plugins.ecasa.searchlimit.value)))
			self.session.open(EcasaFeedview, thread, api=self.api, title=_("Search for %s") % (text))

	def contextMenu(self):
		options = [
			(_("Setup"), self.openSetup),
			(_("Search History"), self.openHistory),
		]
		self.session.openWithCallback(
			self.menuCallback,
			ChoiceBox,
			list=options
		)

	def menuCallback(self, ret=None):
		if ret:
			ret[1]()

	def openSetup(self):
		self.session.openWithCallback(self.setupClosed, EcasaSetup)

	def openHistory(self):
		options = [(x, x) for x in config.plugins.ecasa.searchhistory.value]

		if options:
			self.session.openWithCallback(
				self.historyWrapper,
				ChoiceBox,
				title=_("Select text to search for"),
				list=options
			)
		else:
			self.session.open(
				MessageBox,
				_("No history"),
				type=MessageBox.TYPE_INFO
			)

	def historyWrapper(self, ret):
		if ret:
			self.searchCallback(ret[1])

	def setupClosed(self):
		if config.plugins.ecasa.last_backend.value == 'picasa':
			if not isinstance(self.api, PicasaApi):
				self.api = PicasaApi(cache=config.plugins.ecasa.cache.value)
		else:
			if not isinstance(self.api, FlickrApi):
				self.api = FlickrApi(config.plugins.ecasa.flickr_api_key.value, cache=config.plugins.ecasa.cache.value)

		try:
			self.api.setCredentials(
				config.plugins.ecasa.google_username.value,
				config.plugins.ecasa.google_password.value
			)
		except Exception as e:
			AddPopup(
				_("Unable to authenticate with Google: %s.") % (e.message),
				MessageBox.TYPE_ERROR,
				5,
				id=AUTHENTICATION_ERROR_ID,
			)
		self.api.cache = config.plugins.ecasa.cache.value

	def gotPictures(self, pictures):
		if not self.instance: return
		self.pictures = pictures
		self.setup()

	def errorPictures(self, error):
		if not self.instance: return
		our_print("errorPictures", error)
		self.session.open(
			MessageBox,
			_("Error downloading") + ': ' + error.value.message.encode('utf-8'),
			type=MessageBox.TYPE_ERROR,
			timeout=3
		)
		self["waitingtext"].hide()

class EcasaOverview(EcasaPictureWall):
	"""Overview and supposed entry point of ecasa. Shows featured pictures on the "EcasaPictureWall"."""
	def __init__(self, session):
		EcasaPictureWall.__init__(self, session)
		self.skinName = ["EcasaOverview", "EcasaPictureWall"]
		thread = SimpleThread(self.api.getFeatured)
		thread.deferred.addCallbacks(self.gotPictures, self.errorPictures)
		thread.start()

		self.onClose.append(self.__onClose)

	def openSetup(self):
		self.session.openWithCallback(self.setupClosed, EcasaSetup, allowApiChange=True)

	def setupClosed(self):
		api = self.api
		EcasaPictureWall.setupClosed(self)
		if api != self.api:
			self.pictures = ()
			self["highlight"].hide()
			for i in xrange(self.PICS_PER_PAGE):
				self['image%d' % i].instance.setPixmap(None)
			self["waitingtext"].show()

			thread = SimpleThread(self.api.getFeatured)
			thread.deferred.addCallbacks(self.gotPictures, self.errorPictures)
			thread.start()

	def __onClose(self):
		thread = SimpleThread(lambda: self.api.cleanupCache(config.plugins.ecasa.cachesize.value))
		thread.start()

	def layoutFinished(self):
		EcasaPictureWall.layoutFinished(self)
		self.setTitle(_("Flickr: %s") % (_("Featured Photos")))

class EcasaFeedview(EcasaPictureWall):
	"""Display a nonspecific feed."""
	def __init__(self, session, thread, api=None, title=None):
		EcasaPictureWall.__init__(self, session, api=api)
		self.skinName = ["EcasaFeedview", "EcasaPictureWall"]
		self.feedTitle = title
		self['key_green'].text = ''
		thread.deferred.addCallbacks(self.gotPictures, self.errorPictures)
		thread.start()

	def layoutFinished(self):
		EcasaPictureWall.layoutFinished(self)
		self.setTitle(_("Flickr: %s") % (self.feedTitle.encode('utf-8') or _("Album")))

	def albums(self):
		pass

class EcasaAlbumview(Screen, HelpableScreen, InfoBarNotifications):
	"""Displays albums."""
	skin = """<screen position="center,center" size="560,420">
		<ePixmap pixmap="skin_default/buttons/red.png" position="0,0" size="140,40" transparent="1" alphatest="on" />
		<ePixmap pixmap="skin_default/buttons/green.png" position="140,0" size="140,40" transparent="1" alphatest="on" />
		<ePixmap pixmap="skin_default/buttons/yellow.png" position="280,0" size="140,40" transparent="1" alphatest="on" />
		<ePixmap pixmap="skin_default/buttons/blue.png" position="420,0" size="140,40" transparent="1" alphatest="on" />
		<widget source="key_red" render="Label" position="0,0" zPosition="1" size="140,40" font="Regular;20" valign="center" halign="center" backgroundColor="#1f771f" transparent="1" />
		<widget source="key_green" render="Label" position="140,0" zPosition="1" size="140,40" font="Regular;20" valign="center" halign="center" backgroundColor="#1f771f" transparent="1" />
		<widget source="key_yellow" render="Label" position="280,0" zPosition="1" size="140,40" font="Regular;20" valign="center" halign="center" backgroundColor="#1f771f" transparent="1" />
		<widget source="key_blue" render="Label" position="420,0" zPosition="1" size="140,40" font="Regular;20" valign="center" halign="center" backgroundColor="#1f771f" transparent="1" />
		<widget source="list" render="Listbox" position="0,50" size="560,360" scrollbarMode="showAlways">
			<convert type="TemplatedMultiContent">
				{"template": [
						MultiContentEntryText(pos=(1,1), size=(540,22), text=0, font=0, flags=RT_HALIGN_LEFT|RT_VALIGN_CENTER),
					],
					"fonts": [gFont("Regular", 20)],
					"itemHeight": 24
				}
			</convert>
		</widget>
	</screen>"""
	def __init__(self, session, api, user='default'):
		Screen.__init__(self, session)
		HelpableScreen.__init__(self)
		InfoBarNotifications.__init__(self)
		self.api = api
		self.user = user

		self['list'] = List()
		self['key_red'] = StaticText(_("Close"))
		self['key_green'] = StaticText()
		self['key_yellow'] = StaticText(_("Change user"))
		self['key_blue'] = StaticText(_("User history"))

		self["albumviewActions"] = HelpableActionMap(self, "EcasaAlbumviewActions",
			{
				"select":(self.select, _("Show album")),
				"exit":(self.close, _("Close")),
				"users":(self.users, _("Change user")),
				"history":(self.history, _("User history")),
			}, prio=-1)

		self.acquireAlbumsForUser(user)
		self.onLayoutFinish.append(self.layoutFinished)

	def layoutFinished(self):
		self.setTitle(_("Flickr: Albums for user %s") % (self.user.encode('utf-8'),))

	def acquireAlbumsForUser(self, user):
		thread = SimpleThread(lambda:self.api.getAlbums(user=user))
		thread.deferred.addCallbacks(self.gotAlbums, self.errorAlbums)
		thread.start()

	def gotAlbums(self, albums):
		if not self.instance: return
		self['list'].list = albums

	def errorAlbums(self, error):
		if not self.instance: return
		our_print("errorAlbums", error)
		self['list'].setList([(_("Error downloading"), "0", None)])
		self.session.open(
			MessageBox,
			_("Error downloading") + ': ' + error.value.message.encode('utf-8'),
			type=MessageBox.TYPE_ERROR,
			timeout=30,
		)

	def select(self):
		cur = self['list'].getCurrent()
		if cur and cur[-1]:
			album = cur[-1]
			title = cur[0] # NOTE: retrieve from array to be independent of underlaying API as the flickr and picasa albums are not compatible here
			thread = SimpleThread(lambda:self.api.getAlbum(album))
			self.session.open(EcasaFeedview, thread, api=self.api, title=title)

	def users(self):
		self.session.openWithCallback(
			self.searchCallback,
			NTIVirtualKeyBoard,
			title = _("Enter username")
		)
	def searchCallback(self, text=None):
		if text:
			# Maintain history
			history = config.plugins.ecasa.userhistory.value
			if text not in history:
				history.insert(0, text)
				del history[10:]
			else:
				history.remove(text)
				history.insert(0, text)
			config.plugins.ecasa.userhistory.save()

			self.session.openWithCallback(self.close, EcasaAlbumview, self.api, text)

	def history(self):
		options = [(x, x) for x in config.plugins.ecasa.userhistory.value]

		if options:
			self.session.openWithCallback(
				self.historyWrapper,
				ChoiceBox,
				title=_("Select user"),
				list=options
			)
		else:
			self.session.open(
				MessageBox,
				_("No history"),
				type=MessageBox.TYPE_INFO
			)

	def historyWrapper(self, ret):
		if ret:
			self.searchCallback(ret[1])

class EcasaPicture(Screen, HelpableScreen, InfoBarNotifications):
	"""Display a single picture and its metadata."""
	PAGE_PICTURE = 0
	PAGE_INFO = 1
	def __init__(self, session, photo, api=None, prevFunc=None, nextFunc=None):
		size_w = getDesktop(0).size().width()
		size_h = getDesktop(0).size().height()
		self.skin = """<screen position="0,0" size="{size_w},{size_h}" flags="wfNoBorder">
			<widget name="pixmap" position="0,0" size="{size_w},{size_h}" backgroundColor="black" zPosition="2"/>
			<widget source="title" render="Label" position="25,20" zPosition="1" size="{labelwidth},40" valign="center" halign="left" font="Regular;21" transparent="1" foregroundColor="white" shadowColor="black" shadowOffset="-1,-1"/>
			<widget source="summary" render="Label" position="25,60" zPosition="1" size="{labelwidth},100" valign="top" halign="left" font="Regular;21" transparent="1" foregroundColor="white" shadowColor="black" shadowOffset="-1,-1"/>
			<widget source="keywords" render="Label" position="25,160" zPosition="1" size="{labelwidth},40" valign="center" halign="left" font="Regular;21" transparent="1" foregroundColor="white" shadowColor="black" shadowOffset="-1,-1"/>
			<widget source="camera" render="Label" position="25,180" zPosition="1" size="{labelwidth},40" valign="center" halign="left" font="Regular;21" transparent="1" foregroundColor="white" shadowColor="black" shadowOffset="-1,-1"/>
		</screen>""".format(size_w=size_w,size_h=size_h,labelwidth=size_w-50)
		Screen.__init__(self, session)
		HelpableScreen.__init__(self)
		InfoBarNotifications.__init__(self)

		self.api = api
		self.page = self.PAGE_PICTURE
		self.prevFunc = prevFunc
		self.nextFunc = nextFunc
		self.nextPhoto = None

		self['pixmap'] = Pixmap()
		self['camera'] = StaticText()
		self['title'] = StaticText()
		self['summary'] = StaticText()
		self['keywords'] = StaticText()

		self["pictureActions"] = HelpableActionMap(self, "EcasaPictureActions",
			{
				"info": (self.info, _("Show metadata")),
				"exit": (self.close, _("Close")),
				"contextMenu":(self.contextMenu, _("Open context menu")),
			}, prio=-1)
		if prevFunc and nextFunc:
			self["directionActions"] = HelpableActionMap(self, "DirectionActions",
				{
					"left": self.previous,
					"right": self.next,
				}, prio=-2)

		self.picload = ePicLoad()
		self.picload.PictureData.get().append(self.gotPicture)
		self.timer = eTimer()
		self.timer.callback.append(self.timerFired)

		# populate with data, initiate download
		self.reloadData(photo)

		self.onClose.append(self.__onClose)

	def __onClose(self):
		if self.nextPhoto is not None:
			self.toggleSlideshow()

	def gotPicture(self, picInfo=None):
		our_print("picture decoded")
		ptr = self.picload.getData()
		if ptr is not None:
			self['pixmap'].instance.setPixmap(ptr)
			if self.nextPhoto is not None:
				self.timer.start(config.plugins.ecasa.slideshow_interval.value*1000, True)

	def cbDownload(self, tup):
		if not self.instance: return
		filename, photo = tup
		self.picload.startDecode(filename)

	def ebDownload(self, tup):
		if not self.instance: return
		error, photo = tup
		print("ebDownload", error)
		self.session.open(
			MessageBox,
			_("Error downloading") + ': ' + error.value.message.encode('utf-8'),
			type=MessageBox.TYPE_ERROR,
			timeout=3
		)

	def info(self):
		our_print("info")
		if self.page == self.PAGE_PICTURE:
			self.page = self.PAGE_INFO
			self['pixmap'].hide()
		else:
			self.page = self.PAGE_PICTURE
			self['pixmap'].show()

	def contextMenu(self):
		options = [
			(_("Download Picture"), self.doDownload),
		]
		photo = self.photo
		if photo.author:
			author = photo.author[0]
			options.append(
				(_("%s's Gallery") % (author.name.text), self.showAlbums)
			)
		if self.prevFunc and self.nextFunc:
			options.append(
				(_("Start Slideshow") if self.nextPhoto is None else _("Stop Slideshow"), self.toggleSlideshow)
			)
		self.session.openWithCallback(
			self.menuCallback,
			ChoiceBox,
			list=options
		)

	def menuCallback(self, ret=None):
		if ret:
			ret[1]()

	def doDownload(self):
		self.session.openWithCallback(
			self.gotFilename,
			LocationBox,
			_("Where to save?"),
			self.photo.media.content[0].url.split('/')[-1],
		)

	def gotFilename(self, res):
		if res:
			try:
				self.api.copyPhoto(self.photo, res)
			except Exception as e:
				self.session.open(
					MessageBox,
					_("Unable to download picture: %s") % (e),
					type=MessageBox.TYPE_INFO
				)

	def showAlbums(self):
		self.session.open(EcasaAlbumview, self.api, user=self.photo.author[0].email.text)

	def toggleSlideshow(self):
		# is slideshow currently running?
		if self.nextPhoto is not None:
			self.timer.stop()
			self.previous() # we already moved forward in our parent view, so move back
			self.nextPhoto = None
		else:
			self.timer.start(config.plugins.ecasa.slideshow_interval.value*1000, True)
			self.timerFired()

	def timerFired(self):
		if self.nextPhoto:
			self.reloadData(self.nextPhoto)
			self.timer.stop()
		self.nextPhoto = self.nextFunc()
		# XXX: for now, only start download. later on we might want to pre-parse the picture
		self.api.downloadPhoto(self.nextPhoto)

	def reloadData(self, photo):
		if photo is None: return
		self.photo = photo
		unk = _("unknown")

		# camera
		if photo.exif.make and photo.exif.model:
			camera = '%s %s' % (photo.exif.make.text, photo.exif.model.text)
		elif photo.exif.make:
			camera = photo.exif.make.text
		elif photo.exif.model:
			camera = photo.exif.model.text
		else:
			camera = unk
		self['camera'].text = _("Camera: %s") % (camera,)

		title = photo.title.text.encode('utf-8') if photo.title.text else unk
		self.setTitle(_("Flickr: %s") % (title))
		self['title'].text = _("Title: %s") % (title,)
		summary = strip_readable(photo.summary.text).replace('\n\nView Photo', '').encode('utf-8') if photo.summary.text else ''
		self['summary'].text = summary
		if photo.media and photo.media.keywords and photo.media.keywords.text:
			keywords = photo.media.keywords.text
			# TODO: find a better way to handle this
			if len(keywords) > 50:
				keywords = keywords[:47] + "..."
		else:
			keywords = unk
		self['keywords'].text = _("Keywords: %s") % (keywords,)

		try:
			real_w = int(photo.media.content[0].width)
			real_h = int(photo.media.content[0].heigth)
		except Exception as e:
			our_print("EcasaPicture.__init__: illegal w/h values, using max size!")
			size = getDesktop(0).size()
			real_w = size.width()
			real_h = size.height()

		sc = AVSwitch().getFramebufferScale()
		self.picload.setPara((real_w, real_h, sc[0], sc[1], False, 1, '#ff000000'))

		# NOTE: no need to start an extra thread for this, twisted is "parallel" enough in this case
		self.api.downloadPhoto(photo).addCallbacks(self.cbDownload, self.ebDownload)

	def previous(self):
		if self.prevFunc: self.reloadData(self.prevFunc())
		self['pixmap'].instance.setPixmap(None)
	def next(self):
		if self.nextFunc: self.reloadData(self.nextFunc())
		self['pixmap'].instance.setPixmap(None)
