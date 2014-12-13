from . import _

from Components.AVSwitch import AVSwitch
from Components.ActionMap import ActionMap
from Components.Button import Button
from Components.ConfigList import ConfigListScreen
from Components.Label import Label
from Components.MultiContent import MultiContentEntryText, MultiContentEntryPixmapAlphaTest
from Components.Pixmap import Pixmap
from Components.ProgressBar import ProgressBar
from Components.ScrollLabel import ScrollLabel
from Components.ServiceEventTracker import ServiceEventTracker
from Components.Sources.List import List
from Components.Task import Task, Job, job_manager
from Components.config import config, ConfigSelection, ConfigSubsection, ConfigText, ConfigYesNo, getConfigListEntry, ConfigPassword
#, ConfigIP, ConfigNumber, ConfigLocations
from MyTubeSearch import ConfigTextWithGoogleSuggestions, MyTubeSettingsScreen, MyTubeTasksScreen, MyTubeHistoryScreen
from MyTubeService import validate_cert, get_rnd, myTubeService
from Screens.ChoiceBox import ChoiceBox
from Screens.InfoBarGenerics import InfoBarNotifications, InfoBarSeek
from Screens.MessageBox import MessageBox
from Screens.Screen import Screen
from Screens.VirtualKeyBoard import VirtualKeyBoard
from Tools.BoundFunction import boundFunction
from Tools.Directories import resolveFilename, SCOPE_HDD, SCOPE_CURRENT_PLUGIN
from Tools.Downloader import downloadWithProgress

from __init__ import decrypt_block

from enigma import eTimer, ePoint, RT_HALIGN_LEFT, RT_VALIGN_CENTER, gFont, ePicLoad, eServiceReference, iPlayableService
from os import path as os_path, remove as os_remove
from twisted.web import client

config.plugins.mytube = ConfigSubsection()
config.plugins.mytube.search = ConfigSubsection()


config.plugins.mytube.search.searchTerm = ConfigTextWithGoogleSuggestions("", False)
config.plugins.mytube.search.orderBy = ConfigSelection(
				[
				 ("relevance", _("Relevance")),
				 ("viewCount", _("View Count")),
				 ("published", _("Published")),
				 ("rating", _("Rating"))
				], "published")
config.plugins.mytube.search.time = ConfigSelection(
				[
				 ("all_time", _("All Time")),
				 ("this_month", _("This Month")),
				 ("this_week", _("This Week")),
				 ("today", _("Today"))
				], "all_time")
config.plugins.mytube.search.racy = ConfigSelection(
				[
				 ("include", _("Yes")),
				 ("exclude", _("No"))
				], "include")
config.plugins.mytube.search.categories = ConfigSelection(
				[
				 (None, _("All")),
				 ("Film", _("Film & Animation")),
				 ("Autos", _("Autos & Vehicles")),
				 ("Music", _("Music")),
				 ("Animals", _("Pets & Animals")),
				 ("Sports", _("Sports")),
				 ("Travel", _("Travel & Events")),
				 ("Shortmov", _("Short Movies")),
				 ("Games", _("Gaming")),
				 ("Comedy", _("Comedy")),
				 ("People", _("People & Blogs")),
				 ("News", _("News & Politics")),
				 ("Entertainment", _("Entertainment")),
				 ("Education", _("Education")),
				 ("Howto", _("Howto & Style")),
				 ("Nonprofit", _("Nonprofits & Activism")),
				 ("Tech", _("Science & Technology"))
				], None)
config.plugins.mytube.search.lr = ConfigSelection(
				[
				 (None, _("All")),
				 ("au", _("Australia")),
				 ("br", _("Brazil")),
				 ("ca", _("Canada")),
				 ("cz", _("Czech Republic")),
				 ("fr", _("France")),
				 ("de", _("Germany")),
				 ("gb", _("Great Britain")),
				 ("au", _("Australia")),
				 ("nl", _("Holland")),
				 ("hk", _("Hong Kong")),
				 ("in", _("India")),
				 ("ie", _("Ireland")),
				 ("il", _("Israel")),
				 ("it", _("Italy")),
				 ("jp", _("Japan")),
				 ("mx", _("Mexico")),
				 ("nz", _("New Zealand")),
				 ("pl", _("Poland")),
				 ("ru", _("Russia")),
				 ("kr", _("South Korea")),
				 ("es", _("Spain")),
				 ("se", _("Sweden")),
				 ("tw", _("Taiwan")),
				 ("us", _("United States"))
				], None)
config.plugins.mytube.search.sortOrder = ConfigSelection(
				[
				 ("ascending", _("Ascending")),
				 ("descending", _("Descending"))
				], "descending")

config.plugins.mytube.general = ConfigSubsection()
config.plugins.mytube.general.showHelpOnOpen = ConfigYesNo(default = False)
config.plugins.mytube.general.loadFeedOnOpen = ConfigYesNo(default = True)
config.plugins.mytube.general.startFeed = ConfigSelection(
				[
				 ("hd", _("HD videos")),
				 ("most_viewed", _("Most viewed")),
				 ("top_rated", _("Top rated")),
				 ("recently_featured", _("Recently featured")),
				 ("most_discussed", _("Most discussed")),
				 ("top_favorites", _("Top favorites")),
				 ("most_linked", _("Most linked")),
				 ("most_responded", _("Most responded")),
				 ("most_recent", _("Most recent")),
				 ("most_popular", _("Most popular")),
				 ("most_shared", _("Most shared")),
				 ("on_the_web", _("Trending videos")),
				 ("my_subscriptions", _("My Subscriptions")),
				 ("my_favorites", _("My Favorites")),
				 ("my_history", _("My History")),
				 ("my_watch_later", _("My Watch Later")),
				 ("my_recommendations", _("My Recommendations")),
				 ("my_uploads", _("My Uploads")),
				], "on_the_web")
config.plugins.mytube.general.on_movie_stop = ConfigSelection(default = "ask", choices = [
	("ask", _("Ask user")), ("quit", _("Return to movie list")), ("playnext", _("Play next video")), ("playagain", _("Play video again")) ])

config.plugins.mytube.general.on_exit = ConfigSelection(default = "ask", choices = [
	("ask", _("Ask user")), ("quit", _("Return to movie list"))])

default = resolveFilename(SCOPE_HDD)
tmp = config.movielist.videodirs.value
if default not in tmp:
	tmp.append(default)
config.plugins.mytube.general.videodir = ConfigSelection(default = default, choices = tmp)
config.plugins.mytube.general.history = ConfigText(default="")
config.plugins.mytube.general.clearHistoryOnClose = ConfigYesNo(default = False)
config.plugins.mytube.general.AutoLoadFeeds = ConfigYesNo(default = True)
config.plugins.mytube.general.resetPlayService = ConfigYesNo(default = False)
config.plugins.mytube.general.username = ConfigText(default="", fixed_size = False)
config.plugins.mytube.general.password = ConfigPassword(default="")
#config.plugins.mytube.general.useHTTPProxy = ConfigYesNo(default = False)
#config.plugins.mytube.general.ProxyIP = ConfigIP(default=[0,0,0,0])
#config.plugins.mytube.general.ProxyPort = ConfigNumber(default=8080)


class downloadJob(Job):
	def __init__(self, url, file, title):
		Job.__init__(self, title)
		downloadTask(self, url, file)

class downloadTask(Task):
	def __init__(self, job, url, file):
		Task.__init__(self, job, ("download task"))
		self.end = 100
		self.url = url
		self.local = file

	def prepare(self):
		self.error = None

	def run(self, callback):
		self.callback = callback
		self.download = downloadWithProgress(self.url,self.local)
		self.download.addProgress(self.http_progress)
		self.download.start().addCallback(self.http_finished).addErrback(self.http_failed)

	def http_progress(self, recvbytes, totalbytes):
		#print "[IniMytube.downloadTask] http_progress recvbytes=%d, totalbytes=%d" % (recvbytes, totalbytes)
		self.progress = int(self.end*recvbytes/float(totalbytes))

	def http_finished(self, string=""):
		print "[IniMytube.downloadTask] http_finished" + str(string)
		Task.processFinished(self, 0)

	def http_failed(self, failure_instance=None, error_message=""):
		if error_message == "" and failure_instance is not None:
			error_message = failure_instance.getErrorMessage()
			print "[IniMytube.downloadTask] http_failed " + error_message
			Task.processFinished(self, 1)





class MyTubePlayerMainScreen(Screen, ConfigListScreen):
	BASE_STD_FEEDURL = "http://gdata.youtube.com/feeds/api/standardfeeds/"
	Details = {}
	#(entry, Title, Description, TubeID, thumbnail, PublishedDate,Views,duration,ratings )
	skin = """
		<screen name="MyTubePlayerMainScreen" flags="wfNoBorder" position="0,0" size="720,576" title="YouTube - Browser" >
			<ePixmap position="0,0" zPosition="-1" size="720,576" pixmap="~/mytubemain_bg.png" alphatest="on" transparent="1" backgroundColor="transparent"/>
			<widget name="config" zPosition="2" position="60,60" size="600,50" scrollbarMode="showNever" transparent="1" />
			<widget name="result" position="300,60" zPosition="3" size="350,50" font="Regular;21" transparent="1" backgroundColor="transparent" halign="right"/>
			<widget source="feedlist" render="Listbox" position="49,110" size="628,385" zPosition="1" scrollbarMode="showOnDemand" transparent="1" backgroundPixmap="~/list_bg.png" selectionPixmap="~/list_sel.png" >
				<convert type="TemplatedMultiContent">
				{"templates":
					{"default": (77,[
							MultiContentEntryPixmapAlphaTest(pos = (0, 0), size = (100, 75), png = 4), # index 4 is the thumbnail
							MultiContentEntryText(pos = (100, 1), size = (500, 22), font=0, flags = RT_HALIGN_LEFT | RT_VALIGN_TOP| RT_WRAP, text = 1), # index 1 is the Title
							MultiContentEntryText(pos = (100, 24), size = (300, 18), font=1, flags = RT_HALIGN_LEFT | RT_VALIGN_TOP| RT_WRAP, text = 5), # index 5 is the Published Date
							MultiContentEntryText(pos = (100, 43), size = (300, 18), font=1, flags = RT_HALIGN_LEFT | RT_VALIGN_TOP| RT_WRAP, text = 6), # index 6 is the Views Count
							MultiContentEntryText(pos = (400, 24), size = (200, 18), font=1, flags = RT_HALIGN_LEFT | RT_VALIGN_TOP| RT_WRAP, text = 7), # index 7 is the duration
							MultiContentEntryText(pos = (400, 43), size = (200, 18), font=1, flags = RT_HALIGN_LEFT | RT_VALIGN_TOP| RT_WRAP, text = 8), # index 8 is the ratingcount
						]),
					"state": (77,[
							MultiContentEntryText(pos = (10, 1), size = (560, 28), font=2, flags = RT_HALIGN_LEFT | RT_VALIGN_TOP| RT_WRAP, text = 0), # index 0 is the name
							MultiContentEntryText(pos = (10, 22), size = (560, 46), font=3, flags = RT_HALIGN_LEFT | RT_VALIGN_TOP| RT_WRAP, text = 1), # index 2 is the description
						])
					},
					"fonts": [gFont("Regular", 22),gFont("Regular", 18),gFont("Regular", 26),gFont("Regular", 20)],
					"itemHeight": 77
				}
				</convert>
			</widget>

			<ePixmap pixmap="skin_default/buttons/key_info.png" position="50,500" zPosition="4" size="35,25" alphatest="on" transparent="1" />
			<ePixmap pixmap="skin_default/buttons/key_menu.png" position="50,520" zPosition="4" size="35,25" alphatest="on" transparent="1" />
			<ePixmap position="90,500" size="100,40" zPosition="4" pixmap="~/plugin.png" alphatest="on" transparent="1" />
			<ePixmap position="190,500" zPosition="4" size="140,40" pixmap="skin_default/buttons/red.png" transparent="1" alphatest="on" />
			<ePixmap position="330,500" zPosition="4" size="140,40" pixmap="skin_default/buttons/green.png" transparent="1" alphatest="on" />
			<ePixmap position="470,500" zPosition="4" size="140,40" pixmap="skin_default/buttons/yellow.png" transparent="1" alphatest="on" />
			<ePixmap position="610,500" zPosition="4" size="140,40" pixmap="skin_default/buttons/blue.png" transparent="1" alphatest="on" />
			<widget name="key_red" position="190,500" zPosition="5" size="140,40" valign="center" halign="center" font="Regular;21" transparent="1" foregroundColor="white" shadowColor="black" shadowOffset="-1,-1" />
			<widget name="key_green" position="330,500" zPosition="5" size="140,40" valign="center" halign="center" font="Regular;21" transparent="1" foregroundColor="white" shadowColor="black" shadowOffset="-1,-1" />
			<widget name="key_yellow" position="470,500" zPosition="5" size="140,40" valign="center" halign="center" font="Regular;21" transparent="1" foregroundColor="white" shadowColor="black" shadowOffset="-1,-1" />
			<widget name="key_blue" position="610,500" zPosition="5" size="140,40" valign="center" halign="center" font="Regular;21" transparent="1" foregroundColor="white" shadowColor="black" shadowOffset="-1,-1" />
			<widget name="VKeyIcon" pixmap="skin_default/vkey_icon.png" position="620,495" zPosition="10" size="60,48" transparent="1" alphatest="on" />
			<widget name="thumbnail" position="0,0" size="100,75" alphatest="on"/> # fake entry for dynamic thumbnail resizing, currently there is no other way doing this.
			<widget name="HelpWindow" position="160,255" zPosition="1" size="1,1" transparent="1" alphatest="on" />
		</screen>"""

	def __init__(self, session, plugin_path):
		Screen.__init__(self, session)
		self.session = session

		self.skin_path = plugin_path
		self.FeedURL = None
		self.ytfeed = None
		self.currentFeedName = None
		self.videolist = []
		self.queryThread = None
		self.queryRunning = False

		self.video_playlist = []
		self.statuslist = []
		self.mytubeentries = None

		self.thumbnails = []
		self.index = 0
		self.maxentries = 0

		self.screenshotList = []
		self.pixmaps_to_load = []
		self.picloads = {}

		self.oldfeedentrycount = 0
		self.appendEntries = False
		self.lastservice = session.nav.getCurrentlyPlayingServiceReference()
		self.propagateUpDownNormally = True
		self.FirstRun = True
		self.HistoryWindow = None
		self.History = None
		self.searchtext = _("Welcome to the Youtube Player.\n\nWhile entering your search term(s) you will get suggestions displayed matching your search term.\n\nTo select a suggestion press DOWN on your remote, select the desired result and press OK on your remote to start the search.\n\nPress exit to get back to the input field.")
		self.feedtext = _("Welcome to the Youtube Player.\n\nUse the CH+ button to navigate to the search field and the CH- to navigate to the video entries.\n\nTo play a movie just press OK on your remote control.\n\nPress info to see the movie description.\n\nPress the Menu button for additional options.\n\nThe Help button shows this help again.")
		self.currList = "configlist"
		self.oldlist = None

		self["feedlist"] = List(self.videolist)
		self["thumbnail"] = Pixmap()
		self["thumbnail"].hide()
		self["HelpWindow"] = Pixmap()
		self["HelpWindow"].hide()
		self["key_red"] = Button()
		self["key_green"] = Button()
		self["key_yellow"] = Button()
		self["key_blue"] = Button()
		self["VKeyIcon"] = Pixmap()
		self["VKeyIcon"].hide()
		self["result"] = Label("")


		self["searchactions"] = ActionMap(["ShortcutActions", "WizardActions", "HelpActions", "MediaPlayerActions", "DirectionActions"],
		{
			"ok": self.keyOK,
			"back": self.leavePlayer,
			"red": self.leavePlayer,
			"yellow": self.handleHistory,
			"up": self.keyUp,
			"down": self.handleSuggestions,
			"left": self.keyLeft,
			"right": self.keyRight,
			"prevBouquet": self.switchToFeedList,
			"nextBouquet": self.switchToConfigList,
			"nextBouquet": self.KeyText,
			"displayHelp": self.handleHelpWindow,
			"menu" : self.handleMenu,
		}, -2)

		self["suggestionactions"] = ActionMap(["ShortcutActions", "WizardActions", "MediaPlayerActions", "HelpActions", "DirectionActions", "NumberActions"],
		{
			"ok": self.keyOK,
			"back": self.switchToConfigList,
			"red": self.switchToConfigList,
			"nextBouquet": self.switchToConfigList,
			"prevBouquet": self.switchToFeedList,
			"up": self.keyUp,
			"down": self.keyDown,
			"left": self.keyLeft,
			"right": self.keyRight,
			"0": self.toggleScreenVisibility
		}, -2)


		self["videoactions"] = ActionMap(["ShortcutActions", "WizardActions", "MediaPlayerActions", "MovieSelectionActions", "HelpActions", "DirectionActions"],
		{
			"ok": self.keyOK,
			"back": self.leavePlayer,
			"red": self.leavePlayer,
			"yellow": self.handleHistory,
			"up": self.keyUp,
			"down": self.keyDown,
			"nextBouquet": self.switchToConfigList,
			"green": self.keyStdFeed,
			"blue": self.showVideoInfo,
			"displayHelp": self.handleHelpWindow,
			"menu" : self.handleMenu,
		}, -2)

		self["statusactions"] = ActionMap(["ShortcutActions", "WizardActions", "HelpActions", "MediaPlayerActions"],
		{
			"back": self.leavePlayer,
			"red": self.leavePlayer,
			"nextBouquet": self.switchToConfigList,
			"green": self.keyStdFeed,
			"yellow": self.handleHistory,
			"menu": self.handleMenu
		}, -2)

		self["historyactions"] = ActionMap(["ShortcutActions", "WizardActions", "MediaPlayerActions", "MovieSelectionActions", "HelpActions", "DirectionActions"],
		{
			"ok": self.keyOK,
			"back": self.closeHistory,
			"red": self.closeHistory,
			"yellow": self.handleHistory,
			"up": self.keyUp,
			"down": self.keyDown,
			"left": self.keyLeft,
			"right": self.keyRight,
		}, -2)

		self["videoactions"].setEnabled(False)
		self["statusactions"].setEnabled(False)
		self["historyactions"].setEnabled(False)

		self.timer_startDownload = eTimer()
		self.timer_startDownload.timeout.callback.append(self.downloadThumbnails)
		self.timer_thumbnails = eTimer()
		self.timer_thumbnails.timeout.callback.append(self.updateFeedThumbnails)

		self.SearchConfigEntry = None
		self.searchContextEntries = []
		config.plugins.mytube.search.searchTerm.value = ""
		ConfigListScreen.__init__(self, self.searchContextEntries, session)
		self.createSetup()
		self.onLayoutFinish.append(self.layoutFinished)
		self.onShown.append(self.setWindowTitle)
		self.onClose.append(self.__onClose)
		self.Timer = eTimer()
		self.Timer.callback.append(self.TimerFire)

	def __onClose(self):
		myTubeService.resetAuthState()
		del self.Timer
		del self.timer_startDownload
		del self.timer_thumbnails
		self.Details = {}
		self.session.nav.playService(self.lastservice)

	def layoutFinished(self):
		self["key_red"].setText(_("Close"))
		self["key_green"].setText(_("Std. Feeds"))
		self["key_yellow"].setText(_("History"))
		self["key_blue"].setText(_("Information"))
		self["key_green"].hide()
		self["key_yellow"].show()
		self["key_blue"].hide()
		self.currList = "status"
		current = self["config"].getCurrent()
		if current[1].help_window.instance is not None:
			helpwindowpos = self["HelpWindow"].getPosition()
			current[1].help_window.instance.move(ePoint(helpwindowpos[0],helpwindowpos[1]))
			
		# we need to login here; startService() is fired too often for external curl
		self.tryUserLogin()

		self.statuslist.append(( _("Fetching feed entries"), _("Trying to download the Youtube feed entries. Please wait..." ) ))
		self["feedlist"].style = "state"
		self['feedlist'].setList(self.statuslist)
		self.Timer.start(200)

	def TimerFire(self):
		self.Timer.stop()
		if config.plugins.mytube.general.loadFeedOnOpen.value:
			self.setState('getFeed')
		else:
			self.setState('byPass')

	def setWindowTitle(self):
		self.setTitle(_("YouTube Player"))

	def createSetup(self):
		self.searchContextEntries = []
		self.SearchConfigEntry = getConfigListEntry(_("Search Term(s)"), config.plugins.mytube.search.searchTerm)
		self.searchContextEntries.append(self.SearchConfigEntry)
		self["config"].list = self.searchContextEntries


	def tryUserLogin(self):
		if config.plugins.mytube.general.username.value is "" or config.plugins.mytube.general.password.value is "":
			return

		try:
			myTubeService.auth_user(config.plugins.mytube.general.username.value, config.plugins.mytube.general.password.value)
			self.statuslist.append(( _("Login OK"), _('Hello') + ' ' + str(config.plugins.mytube.general.username.value)))
		except Exception as e:
			print '[MyTubePlayerMainScreen] Login-Error: ' + str(e)
			self.statuslist.append(( _("Login failed"), str(e)))

	def setVisibleHelp(self, enable):
		current = self["config"].getCurrent()
		if current[1].help_window is not None:
			if enable:
				current[1].help_window.show()
			else:
				current[1].help_window.hide()

	def setEnableConfig(self, enable):
		self["config_actions"].setEnabled(enable)
		self["VirtualKB"].setEnabled(enable)
		self.showVKeyboard(enable)
		self.setVisibleHelp(enable)

	def setState(self,status = None):
		print "[MyTubePlayerMainScreen] setState", status
		if status:
			self.currList = "status"
			self["videoactions"].setEnabled(False)
			self["searchactions"].setEnabled(False)
			self["historyactions"].setEnabled(False)
			self["statusactions"].setEnabled(True)
			self.setEnableConfig(False)
			self["key_green"].show()
			self["key_yellow"].show()
			self["key_blue"].hide()
			self.statuslist = []
			self.hideSuggestions()
			result = None

			if self.FirstRun == True:
				self.appendEntries = False
				myTubeService.startService()
			if self.HistoryWindow is not None:
				self.HistoryWindow.deactivate()
				self.HistoryWindow.instance.hide()
			if status == 'getFeed':
				self.statuslist.append(( _("Fetching feed entries"), _("Trying to download the Youtube feed entries. Please wait..." ) ))
			elif status == 'getSearchFeed':
				self.statuslist.append(( _("Fetching search entries"), _("Trying to download the Youtube search results. Please wait..." ) ))
			elif status == 'Error':
				self.statuslist.append(( _("An error occured."), _("There was an error getting the feed entries. Please try again." ) ))
			elif status == 'noVideos':
				self["key_green"].show()
				self.statuslist.append(( _("No videos to display"), _("Please select a standard feed or try searching for videos." ) ))
			elif status == 'byPass':
				self.statuslist.append(( _("Not fetching feed entries"), _("Please enter your search term." ) ))
				self["feedlist"].style = "state"
				self['feedlist'].setList(self.statuslist)
				self.switchToConfigList()
			self["feedlist"].style = "state"
			self['feedlist'].setList(self.statuslist)
			if self.FirstRun == True:
				if config.plugins.mytube.general.loadFeedOnOpen.value:
					self.getFeed(self.BASE_STD_FEEDURL, str(config.plugins.mytube.general.startFeed.value))

	def handleHelpWindow(self):
		print "[MyTubePlayerMainScreen] handleHelpWindow"
		if self.currList == "configlist":
			self.hideSuggestions()
			self.setVisibleHelp(False)
			self.session.openWithCallback(self.ScreenClosed, MyTubeVideoHelpScreen, self.skin_path, wantedinfo = self.searchtext, wantedtitle = _("YouTube Player - Help") )
		elif self.currList == "feedlist":
			self.session.openWithCallback(self.ScreenClosed, MyTubeVideoHelpScreen, self.skin_path, wantedinfo = self.feedtext, wantedtitle = _("YouTube Player - Help") )

	def handleFirstHelpWindow(self):
		#print "[MyTubePlayerMainScreen] handleFirstHelpWindow"
		#if config.plugins.mytube.general.showHelpOnOpen.value is True:
		#	if self.currList == "configlist":
		#		self.hideSuggestions()
		#		self.session.openWithCallback(self.firstRunHelpClosed, MyTubeVideoHelpScreen, self.skin_path,wantedinfo = self.feedtext, wantedtitle = _("MyTubePlayer Help") )
		#else:
		self.FirstRun = False

	def firstRunHelpClosed(self):
		if self.FirstRun == True:
			self.FirstRun = False
			self.switchToConfigList()

	def handleMenu(self):
		if self.currList == "configlist" or self.currList == "status":
			menulist = (
					(_("YouTube Settings"), "settings"),
				)
			self.setVisibleHelp(False)
			self.hideSuggestions()
			self.session.openWithCallback(self.openMenu, ChoiceBox, title=_("Select your choice."), list = menulist)

		elif self.currList == "feedlist":
			menulist = [(_("You Tube Settings"), "settings")]
			menulist.extend((
					(_("View related videos"), "related"),
					(_("View user videos"), "user_videos"),
					(_("View response videos"), "response"),
				))

			if myTubeService.is_auth() is True:
				menulist.extend((
						(_("Subscribe to user"), "subscribe"),
						(_("Add to favorites"), "favorite"),
					))

			if config.usage.setup_level.index >= 2: # expert+
				menulist.extend((
					(_("Download Video"), "download"),
					(_("View active downloads"), "downview")
				))

			self.hideSuggestions()
			self.setVisibleHelp(False)
			self.session.openWithCallback(self.openMenu, ChoiceBox, title=_("Select your choice."), list = menulist)

	def openMenu(self, answer):
		answer = answer and answer[1]
		if answer == "settings":
			print "[MyTubePlayerMainScreen] settings selected"
			self.session.openWithCallback(self.ScreenClosed,MyTubeSettingsScreen, self.skin_path )
		elif answer == "related":
			current = self["feedlist"].getCurrent()[0]
			self.setState('getFeed')
			self.getRelatedVideos(current)
		elif answer == "user_videos":
			current = self["feedlist"].getCurrent()[0]
			self.setState('getFeed')
			self.getUserVideos(current)
		elif answer == "subscribe":
			current = self["feedlist"].getCurrent()[0]
			self.session.open(MessageBox, current.subscribeToUser(), MessageBox.TYPE_INFO)
		elif answer == "favorite":
			current = self["feedlist"].getCurrent()[0]
			self.session.open(MessageBox, current.addToFavorites(), MessageBox.TYPE_INFO)
		elif answer == "response":
			current = self["feedlist"].getCurrent()[0]
			self.setState('getFeed')
			self.getResponseVideos(current)
		elif answer == "download":
			if self.currList == "feedlist":
				current = self[self.currList].getCurrent()
				if current:
					myentry = current[0]
					if myentry:
						myurl = myentry.getVideoUrl()
						filename = str(config.plugins.mytube.general.videodir.value)+ str(myentry.getTitle()) + '.mp4'
						job_manager.AddJob(downloadJob(myurl,filename, str(myentry.getTitle())[:30]))
		elif answer == "downview":
			self.tasklist = []
			for job in job_manager.getPendingJobs():
				self.tasklist.append((job,job.name,job.getStatustext(),int(100*job.progress/float(job.end)) ,str(100*job.progress/float(job.end)) + "%" ))
			self.session.open(MyTubeTasksScreen, self.skin_path , self.tasklist)
		elif answer == None:
			self.ScreenClosed()

	def KeyText(self):
		self.hideSuggestions()
		self.setVisibleHelp(False)
		self.session.openWithCallback(self.SearchEntryCallback, VirtualKeyBoard, title = (_("Enter your search term(s)")), text = config.plugins.mytube.search.searchTerm.value)

	def ScreenClosed(self):
		print "[MyTubePlayerMainScreen] ScreenCLosed, restoring old window state"
		if self.currList == "historylist":
			if self.HistoryWindow.status() is False:
				self.HistoryWindow.activate()
				self.HistoryWindow.instance.show()
		elif self.currList == "configlist":
			self.switchToConfigList()
			ConfigListScreen.keyOK(self)
		elif self.currList == "feedlist":
			self.switchToFeedList()

	def SearchEntryCallback(self, callback = None):
		current = self["config"].getCurrent()
		if callback is not None and len(callback):
			config.plugins.mytube.search.searchTerm.value = callback
			#ConfigListScreen.keyOK(self)
			self["config"].getCurrent()[1].getSuggestions()
			self.switchToConfigList()
			self.keyOK()
		
		if current[1].suggestionsWindow.instance is not None:
			current[1].suggestionsWindow.instance.show()

		self.switchToFeedList()
		if current[1].suggestionsWindow.instance is not None:
			current[1].suggestionsWindow.instance.hide()
		self.propagateUpDownNormally = True

	def openStandardFeedClosed(self, answer):
		answer = answer and answer[1]
		if answer is not None:
			self.setState('getFeed')
			self.appendEntries = False
			self.getFeed(self.BASE_STD_FEEDURL, str(answer))

	def handleLeave(self, how):
		self.is_closing = True
		if how == "ask":
			if self.currList == "configlist":
				list = (
					(_("Yes"), "quit"),
					(_("No"), "continue"),
					(_("No, but switch to video entries."), "switch2feed")
				)
			else:
				list = (
					(_("Yes"), "quit"),
					(_("No"), "continue"),
					(_("No, but switch to video search."), "switch2search")
				)
			self.session.openWithCallback(self.leavePlayerConfirmed, ChoiceBox, title=_("Really quit YouTube Player?"), list = list)
		else:
			self.leavePlayerConfirmed([True, how])

	def leavePlayer(self):
		print "[MyTubePlayerMainScreen] leavePlayer"
		if self.HistoryWindow is not None:
			self.HistoryWindow.deactivate()
			self.HistoryWindow.instance.hide()
		if self.currList == "configlist":
			current = self["config"].getCurrent()
			if current[1].suggestionsWindow.activeState is True:
				self.propagateUpDownNormally = True
				current[1].deactivateSuggestionList()
				self["config"].invalidateCurrent()
			else:
				self.hideSuggestions()
				self.setVisibleHelp(False)
				self.handleLeave(config.plugins.mytube.general.on_exit.value)
		else:
			self.hideSuggestions()
			self.setVisibleHelp(False)
			self.handleLeave(config.plugins.mytube.general.on_exit.value)

	def leavePlayerConfirmed(self, answer):
		answer = answer and answer[1]
		if answer == "quit":
			self.doQuit()
		elif answer == "continue":
			if self.currList == "historylist":
				if self.HistoryWindow.status() is False:
					self.HistoryWindow.activate()
					self.HistoryWindow.instance.show()
			elif self.currList == "configlist":
				self.switchToConfigList()
			elif self.currList == "feedlist":
				self.switchToFeedList()
		elif answer == "switch2feed":
			self.switchToFeedList()
		elif answer == "switch2search":
			self.switchToConfigList()
		elif answer == None:
			if self.currList == "historylist":
				if self.HistoryWindow.status() is False:
					self.HistoryWindow.activate()
					self.HistoryWindow.instance.show()
			elif self.currList == "configlist":
				self.switchToConfigList()
			elif self.currList == "feedlist":
				self.switchToFeedList()

	def doQuit(self):
		if self["config"].getCurrent()[1].suggestionsWindow is not None:
			self.session.deleteDialog(self["config"].getCurrent()[1].suggestionsWindow)
		if self.HistoryWindow is not None:
			self.session.deleteDialog(self.HistoryWindow)
		if config.plugins.mytube.general.showHelpOnOpen.value is True:
			config.plugins.mytube.general.showHelpOnOpen.value = False
			config.plugins.mytube.general.showHelpOnOpen.save()
		if not config.plugins.mytube.general.clearHistoryOnClose.value:
			if self.History and len(self.History):
				config.plugins.mytube.general.history.value = ",".join(self.History)
		else:
			config.plugins.mytube.general.history.value = ""
		config.plugins.mytube.general.history.save()
		config.plugins.mytube.general.save()
		config.plugins.mytube.save()
		self.cancelThread()
		self.close()

	def keyOK(self):
		print "[MyTubePlayerMainScreen] self.currList in KeyOK",self.currList
		if self.currList == "configlist" or self.currList == "suggestionslist":
			self["config"].invalidateCurrent()
			if config.plugins.mytube.search.searchTerm.value != "":
				self.add2History()
				searchContext = config.plugins.mytube.search.searchTerm.value
				print "[MyTubePlayerMainScreen] Search searchcontext",searchContext
				if isinstance(self["config"].getCurrent()[1], ConfigTextWithGoogleSuggestions) and not self.propagateUpDownNormally:
					self.propagateUpDownNormally = True
					self["config"].getCurrent()[1].deactivateSuggestionList()
				self.setState('getSearchFeed')
				self.runSearch(searchContext)
		elif self.currList == "feedlist":
			current = self[self.currList].getCurrent()
			if current:
				print "[MyTubePlayerMainScreen] KeyOK current", current
				myentry = current[0]
				if myentry is not None:
					myurl = myentry.getVideoUrl()
					print "[MyTubePlayerMainScreen] Playing URL",myurl
					if myurl is not None:
						myreference = eServiceReference(4097,0,myurl)
						myreference.setName(myentry.getTitle())
						self.session.openWithCallback(self.onPlayerClosed, MyTubePlayer, myreference, self.lastservice, infoCallback = self.showVideoInfo, nextCallback = self.getNextEntry, prevCallback = self.getPrevEntry )
					else:
						self.session.open(MessageBox, _("Sorry, video is not available!"), MessageBox.TYPE_INFO)
		elif self.currList == "historylist":
			if self.HistoryWindow is not None:
				config.plugins.mytube.search.searchTerm.value = self.HistoryWindow.getSelection()
			self["config"].invalidateCurrent()
			if config.plugins.mytube.search.searchTerm.value != "":
				searchContext = config.plugins.mytube.search.searchTerm.value
				print "[MyTubePlayerMainScreen]Search searchcontext",searchContext
				self.setState('getSearchFeed')
				self.runSearch(searchContext)

	def onPlayerClosed(self):
		if config.plugins.mytube.general.resetPlayService.value is True:
			self.session.nav.playService(self.lastservice)

	def toggleScreenVisibility(self):
		if self.shown is True:
			self.hide()
		else:
			self.show()

	def keyUp(self):
		print "[MyTubePlayerMainScreen] self.currList in KeyUp",self.currList
		if self.currList == "suggestionslist":
			if config.plugins.mytube.search.searchTerm.value != "":
				if not self.propagateUpDownNormally:
					self["config"].getCurrent()[1].suggestionListUp()
					self["config"].invalidateCurrent()
		elif self.currList == "feedlist":
			self[self.currList].selectPrevious()
		elif self.currList == "historylist":
			if self.HistoryWindow is not None and self.HistoryWindow.shown:
				self.HistoryWindow.up()

	def keyDown(self):
		print "[MyTubePlayerMainScreen] self.currList i KeyDown",self.currList
		if self.currList == "suggestionslist":
			if config.plugins.mytube.search.searchTerm.value != "":
				if not self.propagateUpDownNormally:
					self["config"].getCurrent()[1].suggestionListDown()
					self["config"].invalidateCurrent()
		elif self.currList == "feedlist":
			print "[MyTubePlayerMainScreen] feedlist count", self[self.currList].count(), "index", self[self.currList].index
			if self[self.currList].index == self[self.currList].count()-1 and myTubeService.getNextFeedEntriesURL() is not None:
				# load new feeds on last selected item
				if config.plugins.mytube.general.AutoLoadFeeds.value is False:
					self.session.openWithCallback(self.getNextEntries, MessageBox, _("Do you want to see more entries?"))
				else:
					self.getNextEntries(True)
			else:
				self[self.currList].selectNext()
		elif self.currList == "historylist":
			if self.HistoryWindow is not None and self.HistoryWindow.shown:
				self.HistoryWindow.down()
	def keyRight(self):
		print "[MyTubePlayerMainScreen] self.currList in KeyRight",self.currList
		if self.propagateUpDownNormally:
			ConfigListScreen.keyRight(self)
		else:
			if self.currList == "suggestionslist":
				if config.plugins.mytube.search.searchTerm.value != "":
					self["config"].getCurrent()[1].suggestionListPageDown()
					self["config"].invalidateCurrent()
			elif self.currList == "historylist":
				if self.HistoryWindow is not None and self.HistoryWindow.shown:
					self.HistoryWindow.pageDown()

	def keyLeft(self):
		print "[MyTubePlayerMainScreen] self.currList in KeyLeft",self.currList
		if self.propagateUpDownNormally:
			ConfigListScreen.keyLeft(self)
		else:
			if self.currList == "suggestionslist":
				if config.plugins.mytube.search.searchTerm.value != "":
					self["config"].getCurrent()[1].suggestionListPageUp()
					self["config"].invalidateCurrent()
			elif self.currList == "historylist":
				if self.HistoryWindow is not None and self.HistoryWindow.shown:
					self.HistoryWindow.pageDown()
	def keyStdFeed(self):
		self.setVisibleHelp(False)
		self.hideSuggestions()
		menulist = []

		if myTubeService.is_auth() is True:
			menulist.extend((
				(_("My Subscriptions"), "my_subscriptions"),
				(_("My Favorites"), "my_favorites"),
				(_("My History"), "my_history"),
				(_("My Watch Later"), "my_watch_later"),
				(_("My Recommendations"), "my_recommendations"),
				(_("My Uploads"), "my_uploads"),
			))

		menulist.extend((
			(_("HD videos"), "hd"),
			(_("Top rated"), "top_rated"),
			(_("Top favorites"), "top_favorites"),
			(_("Most viewed"), "most_viewed"),
			(_("Most popular"), "most_popular"),
			(_("Most recent"), "most_recent"),
			(_("Most discussed"), "most_discussed"),
			(_("Most linked"), "most_linked"),
			(_("Recently featured"), "recently_featured"),
			(_("Most responded"), "most_responded"),
			(_("Most shared"), "most_shared"),
			(_("Trending videos"), "on_the_web")
		))
		self.session.openWithCallback(self.openStandardFeedClosed, ChoiceBox, title=_("Select new feed to view."), list = menulist)

	def handleSuggestions(self):
		print "[MyTubePlayerMainScreen] handleSuggestions"
		print "[MyTubePlayerMainScreen] self.currList",self.currList
		if self.currList == "configlist":
			self.switchToSuggestionsList()
		elif self.currList == "historylist":
			if self.HistoryWindow is not None and self.HistoryWindow.shown:
				self.HistoryWindow.down()

	def switchToSuggestionsList(self):
		print "[MyTubePlayerMainScreen] switchToSuggestionsList"
		self.currList = "suggestionslist"
		self["statusactions"].setEnabled(False)
		self["videoactions"].setEnabled(False)
		self["searchactions"].setEnabled(False)
		self["suggestionactions"].setEnabled(True)
		self["historyactions"].setEnabled(False)
		self.setEnableConfig(False)
		self["key_green"].hide()
		self["key_yellow"].hide()
		self["key_blue"].hide()
		self.propagateUpDownNormally = False
		self["config"].invalidateCurrent()
		if self.HistoryWindow is not None and self.HistoryWindow.shown:
			self.HistoryWindow.deactivate()
			self.HistoryWindow.instance.hide()

	def switchToConfigList(self):
		print "[MyTubePlayerMainScreen] switchToConfigList"
		self.currList = "configlist"
		self["historyactions"].setEnabled(False)
		self["statusactions"].setEnabled(False)
		self["videoactions"].setEnabled(False)
		self["suggestionactions"].setEnabled(False)
		self["searchactions"].setEnabled(True)
		self.setEnableConfig(True)
		self["key_green"].hide()
		self["key_yellow"].show()
		self["key_blue"].hide()
		self["config"].invalidateCurrent()
		current = self["config"].getCurrent()
		if current[1].suggestionsWindow.instance is not None:
			current[1].suggestionsWindow.instance.show()
			current[1].getSuggestions()
		self.propagateUpDownNormally = True
		if self.HistoryWindow is not None and self.HistoryWindow.shown:
			self.HistoryWindow.deactivate()
			self.HistoryWindow.instance.hide()
		#if self.FirstRun == True:
		#	self.handleFirstHelpWindow()

	def switchToFeedList(self, append = False):
		print "[MyTubePlayerMainScreen] switchToFeedList"
		print "[MyTubePlayerMainScreen] switching to feedlist from:",self.currList
		print "[MyTubePlayerMainScreen] len(self.videolist):",len(self.videolist)
		if self.HistoryWindow is not None and self.HistoryWindow.shown:
			self.HistoryWindow.deactivate()
			self.HistoryWindow.instance.hide()
		self.hideSuggestions()
		if len(self.videolist):
			self.currList = "feedlist"
			self["videoactions"].setEnabled(True)
			self["suggestionactions"].setEnabled(False)
			self["searchactions"].setEnabled(False)
			self["statusactions"].setEnabled(False)
			self["historyactions"].setEnabled(False)
			self.setEnableConfig(False)
			self["key_green"].show()
			self["key_yellow"].show()
			self["key_blue"].show()
			if not append:
				self[self.currList].setIndex(0)
			self["feedlist"].updateList(self.videolist)
		else:
			self.setState('noVideos')


	def switchToHistory(self):
		print "[MyTubePlayerMainScreen] switchToHistory"
		self.oldlist = self.currList
		self.currList = "historylist"
		print "[MyTubePlayerMainScreen] switchToHistory currentlist",self.currList
		print "[MyTubePlayerMainScreen] switchToHistory oldlist",self.oldlist
		self.hideSuggestions()
		self["videoactions"].setEnabled(False)
		self["suggestionactions"].setEnabled(False)
		self["searchactions"].setEnabled(False)
		self["statusactions"].setEnabled(False)
		self["historyactions"].setEnabled(True)
		self.setEnableConfig(False)
		self["key_green"].hide()
		self["key_yellow"].show()
		self["key_blue"].hide()
		self.HistoryWindow.activate()
		self.HistoryWindow.instance.show()

	def handleHistory(self):
		if self.HistoryWindow is None:
			self.HistoryWindow = self.session.instantiateDialog(MyTubeHistoryScreen)
		if self.currList in ("configlist","feedlist"):
			if self.HistoryWindow.status() is False:
				print "[MyTubePlayerMainScreen] handleHistory status is FALSE, switchToHistory"
				self.switchToHistory()
		elif self.currList == "historylist":
			self.closeHistory()

	def closeHistory(self):
		print "[MyTubePlayerMainScreen] closeHistory currentlist",self.currList
		print "[MyTubePlayerMainScreen] closeHistory oldlist",self.oldlist
		if self.currList == "historylist":
			if self.HistoryWindow.status() is True:
				print "[MyTubePlayerMainScreen] closeHistory status is TRUE, closing historyscreen"
				self.HistoryWindow.deactivate()
				self.HistoryWindow.instance.hide()
				if self.oldlist == "configlist":
					self.switchToConfigList()
				elif self.oldlist == "feedlist":
					self.switchToFeedList()

	def add2History(self):
		if self.History is None:
			self.History = config.plugins.mytube.general.history.value.split(',')
		if self.History[0] == '':
			del self.History[0]
		print "[MyTubePlayerMainScreen] self.History in add",self.History
		if config.plugins.mytube.search.searchTerm.value in self.History:
			self.History.remove((config.plugins.mytube.search.searchTerm.value))
		self.History.insert(0,(config.plugins.mytube.search.searchTerm.value))
		if len(self.History) == 30:
			self.History.pop()
		config.plugins.mytube.general.history.value = ",".join(self.History)
		config.plugins.mytube.general.history.save()
		print "[MyTubePlayerMainScreen] history configvalue", config.plugins.mytube.general.history.value

	def hideSuggestions(self):
		current = self["config"].getCurrent()
		if current[1].suggestionsWindow.instance is not None:
			current[1].suggestionsWindow.instance.hide()
		self.propagateUpDownNormally = True

	def getFeed(self, feedUrl, feedName):
		self.queryStarted()
		self.queryThread = myTubeService.getFeed(feedUrl, feedName, self.gotFeed, self.gotFeedError)

	def getNextEntries(self, result):
		if not result:
			return
		nextUrl = myTubeService.getNextFeedEntriesURL()
		if nextUrl is not None:
			self.appendEntries = True
			self.getFeed(nextUrl, _("More video entries."))

	def getRelatedVideos(self, myentry):
		if myentry:
			myurl =  myentry.getRelatedVideos()
			print "[MyTubePlayerMainScreen] RELATEDURL--->",myurl
			if myurl is not None:
				self.appendEntries = False
				self.getFeed(myurl, _("Related video entries."))

	def getResponseVideos(self, myentry):
		if myentry:
			myurl =  myentry.getResponseVideos()
			print "[MyTubePlayerMainScreen] RESPONSEURL--->",myurl
			if myurl is not None:
				self.appendEntries = False
				self.getFeed(myurl, _("Response video entries."))

	def getUserVideos(self, myentry):
		if myentry:
			myurl =  myentry.getUserVideos()
			print "[MyTubePlayerMainScreen] RESPONSEURL--->",myurl
			if myurl is not None:
				self.appendEntries = False
				self.getFeed(myurl, _("User video entries."))

	def runSearch(self, searchContext = None):
		print "[MyTubePlayerMainScreen] runSearch"
		if searchContext is not None:
			print "[MyTubePlayerMainScreen] searchDialogClosed: ", searchContext
			self.searchFeed(searchContext)

	def searchFeed(self, searchContext, vals = None):
		print "[MyTubePlayerMainScreen] searchFeed"

		defaults = {
			'time': config.plugins.mytube.search.time.value,
			'orderby': config.plugins.mytube.search.orderBy.value,
			'startIndex': 1,
			'maxResults': 25,
		}

		# vals can overwrite default values; so search parameter are overwritable on function call
		if vals is not None:
			defaults.update(vals)

		self.queryStarted()
		self.appendEntries = False
		self.queryThread = myTubeService.search(searchContext,
					orderby = defaults['orderby'],
					time = defaults['time'],
					maxResults = defaults['maxResults'],
					startIndex = defaults['startIndex'],
					lr = config.plugins.mytube.search.lr.value,
					categories = [ config.plugins.mytube.search.categories.value ],
					sortOrder = config.plugins.mytube.search.sortOrder.value,
					callback = self.gotSearchFeed, errorback = self.gotSearchFeedError)

	def queryStarted(self):
		if self.queryRunning:
			self.cancelThread()
		self.queryRunning = True

	def queryFinished(self):
		self.queryRunning = False

	def cancelThread(self):
		print "[MyTubePlayerMainScreen] cancelThread"
		if self.queryThread is not None:
			self.queryThread.cancel()
		self.queryFinished()

	def gotFeed(self, feed):
		print "[MyTubePlayerMainScreen] gotFeed"
		self.queryFinished()
		if feed is not None:
			self.ytfeed = feed
		self.buildEntryList()
		text = _("Results: %s - Page: %s " % (str(myTubeService.getTotalResults()), str(myTubeService.getCurrentPage())))

		auth_username = myTubeService.getAuthedUsername()
		if auth_username:
			text = auth_username + ' - ' + text

		self["result"].setText(text)

	def gotFeedError(self, exception):
		print "[MyTubePlayerMainScreen] gotFeedError"
		self.queryFinished()
		self.setState('Error')

	def gotSearchFeed(self, feed):
		if self.FirstRun:
			self.FirstRun = False
		self.gotFeed(feed)

	def gotSearchFeedError(self, exception):
		if self.FirstRun:
			self.FirstRun = False
		self.gotFeedError(exception)

	def buildEntryList(self):
		self.mytubeentries = None
		self.screenshotList = []
		self.maxentries = 0
		self.mytubeentries = myTubeService.getEntries()
		self.maxentries = len(self.mytubeentries)-1
		if self.mytubeentries and len(self.mytubeentries):
			if self.appendEntries == False:
				self.videolist = []
				for entry in self.mytubeentries:
					TubeID = entry.getTubeId()
					thumbnailUrl = None
					thumbnailUrl = entry.getThumbnailUrl(0)
					if thumbnailUrl is not None:
						self.screenshotList.append((TubeID,thumbnailUrl))
					if not self.Details.has_key(TubeID):
						self.Details[TubeID] = { 'thumbnail': None}
					self.videolist.append(self.buildEntryComponent(entry, TubeID))
				if len(self.videolist):
					self["feedlist"].style = "default"
					self["feedlist"].disable_callbacks = True
					self["feedlist"].list = self.videolist
					self["feedlist"].disable_callbacks = False
					self["feedlist"].setIndex(0)
					self["feedlist"].setList(self.videolist)
					self["feedlist"].updateList(self.videolist)
					if self.FirstRun and not config.plugins.mytube.general.loadFeedOnOpen.value:
						self.switchToConfigList()
					else:
						self.switchToFeedList()
			else:
				self.oldfeedentrycount = self["feedlist"].count()
				for entry in self.mytubeentries:
					TubeID = entry.getTubeId()
					thumbnailUrl = None
					thumbnailUrl = entry.getThumbnailUrl(0)
					if thumbnailUrl is not None:
						self.screenshotList.append((TubeID,thumbnailUrl))
					if not self.Details.has_key(TubeID):
						self.Details[TubeID] = { 'thumbnail': None}
					self.videolist.append(self.buildEntryComponent(entry, TubeID))
				if len(self.videolist):
					self["feedlist"].style = "default"
					old_index = self["feedlist"].index
					self["feedlist"].disable_callbacks = True
					self["feedlist"].list = self.videolist
					self["feedlist"].disable_callbacks = False
					self["feedlist"].setList(self.videolist)
					self["feedlist"].setIndex(old_index)
					self["feedlist"].updateList(self.videolist)
					self["feedlist"].selectNext()
					self.switchToFeedList(True)
			if not self.timer_startDownload.isActive():
				print "[MyTubePlayerMainScreen] start download timer in buildEntryList"
				self.timer_startDownload.start(5)
		else:
			self.setState('Error')
			pass

	def buildEntryComponent(self, entry,TubeID):
		Title = entry.getTitle()
		print "[MyTubePlayerMainScreen] Title-->",Title
		Description = entry.getDescription()
		myTubeID = TubeID
		PublishedDate = entry.getPublishedDate()
		if PublishedDate is not "unknown":
			published = PublishedDate.split("T")[0]
		else:
			published = "unknown"
		Views = entry.getViews()
		if Views is not "not available":
			views = Views
		else:
			views = "not available"
		Duration = entry.getDuration()
		if Duration is not 0:
			durationInSecs = int(Duration)
			mins = int(durationInSecs / 60)
			secs = durationInSecs - mins * 60
			duration = "%d:%02d" % (mins, secs)
		else:
			duration = "not available"
		Ratings = entry.getNumRaters()
		if Ratings is not "":
			ratings = Ratings
		else:
			ratings = ""
		thumbnail = None
		if self.Details[myTubeID]["thumbnail"]:
			thumbnail = self.Details[myTubeID]["thumbnail"]
		return((entry, Title, Description, myTubeID, thumbnail, _("Added: ") + str(published), _("Views: ") + str(views), _("Duration: ") + str(duration), _("Ratings: ") + str(ratings) ))

	def getNextEntry(self):
		i = self["feedlist"].getIndex() + 1
		if i < len(self.videolist):
			self["feedlist"].selectNext()
			current = self["feedlist"].getCurrent()
			if current:
				myentry = current[0]
				if myentry:
					myurl = myentry.getVideoUrl()
					if myurl is not None:
						print "[MyTubePlayerMainScreen] Got a URL to stream"
						myreference = eServiceReference(4097,0,myurl)
						myreference.setName(myentry.getTitle())
						return myreference,False
					else:
						print "[MyTubePlayerMainScreen] NoURL im getNextEntry"
						return None,True

		print "[MyTubePlayerMainScreen] no more entries to play"
		return None,False

	def getPrevEntry(self):
		i = self["feedlist"].getIndex() - 1
		if i >= 0:
			self["feedlist"].selectPrevious()
			current = self["feedlist"].getCurrent()
			if current:
				myentry = current[0]
				if myentry:
					myurl = myentry.getVideoUrl()
					if myurl is not None:
						print "[MyTubePlayerMainScreen] Got a URL to stream"
						myreference = eServiceReference(4097,0,myurl)
						myreference.setName(myentry.getTitle())
						return myreference,False
					else:
						return None,True
		return None,False

	def showVideoInfo(self):
		if self.currList == "feedlist":
			self.openInfoScreen()

	def openInfoScreen(self):
		if self.currList == "feedlist":
			current = self[self.currList].getCurrent()
			if current:
				myentry = current[0]
				if myentry:
					print "[MyTubePlayerMainScreen] Title im showVideoInfo",myentry.getTitle()
					videoinfos = myentry.PrintEntryDetails()
					self.session.open(MyTubeVideoInfoScreen, self.skin_path, videoinfo = videoinfos )

	def downloadThumbnails(self):
		self.timer_startDownload.stop()
		for entry in self.screenshotList:
			thumbnailUrl = entry[1]
			tubeid = entry[0]
			thumbnailFile = "/tmp/"+str(tubeid)+".jpg"
			if self.Details.has_key(tubeid):
				if self.Details[tubeid]["thumbnail"] is None:
					if thumbnailUrl is not None:
						if tubeid not in self.pixmaps_to_load:
							self.pixmaps_to_load.append(tubeid)
							if (os_path.exists(thumbnailFile) == True):
								self.fetchFinished(False,tubeid)
							else:
								client.downloadPage(thumbnailUrl,thumbnailFile).addCallback(self.fetchFinished,str(tubeid)).addErrback(self.fetchFailed,str(tubeid))
					else:
						if tubeid not in self.pixmaps_to_load:
							self.pixmaps_to_load.append(tubeid)
							self.fetchFinished(False,tubeid, failed = True)

	def fetchFailed(self,string,tubeid):
		print "[MyTubePlayerMainScreen] thumbnail-fetchFailed for: ",tubeid,string.getErrorMessage()
		self.fetchFinished(False,tubeid, failed = True)

	def fetchFinished(self,x,tubeid, failed = False):
		print "[MyTubePlayerMainScreen] thumbnail-fetchFinished for:",tubeid
		self.pixmaps_to_load.remove(tubeid)
		if failed:
			thumbnailFile = resolveFilename(SCOPE_CURRENT_PLUGIN, "Extensions/IniMyTube/plugin.png")
		else:
			thumbnailFile = "/tmp/"+str(tubeid)+".jpg"
		sc = AVSwitch().getFramebufferScale()
		if (os_path.exists(thumbnailFile) == True):
			self.picloads[tubeid] = ePicLoad()
			self.picloads[tubeid].PictureData.get().append(boundFunction(self.finish_decode, tubeid))
			self.picloads[tubeid].setPara((self["thumbnail"].instance.size().width(), self["thumbnail"].instance.size().height(), sc[0], sc[1], False, 1, "#00000000"))
			self.picloads[tubeid].startDecode(thumbnailFile)
		else:
			self.pixmaps_to_load.append(tubeid)
			self.fetchFinished(False,tubeid, failed = True)

	def finish_decode(self,tubeid,info):
		print "[MyTubePlayerMainScreen] thumbnail finish_decode:", tubeid,info
		ptr = self.picloads[tubeid].getData()
		thumbnailFile = "/tmp/"+str(tubeid)+".jpg"
		if ptr != None:
			if self.Details.has_key(tubeid):
				self.Details[tubeid]["thumbnail"] = ptr
			if (os_path.exists(thumbnailFile) == True):
				os_remove(thumbnailFile)
			del self.picloads[tubeid]
		else:
			del self.picloads[tubeid]
			if self.Details.has_key(tubeid):
				self.Details[tubeid]["thumbnail"] = None
		self.timer_thumbnails.start(1)

	def updateFeedThumbnails(self):
		self.timer_thumbnails.stop()
		if len(self.picloads) != 0:
			self.timer_thumbnails.start(1)
		else:
			idx = 0
			for entry in self.videolist:
				tubeid = entry[3]
				if self.Details.has_key(tubeid):
					if self.Details[tubeid]["thumbnail"] is not None:
						thumbnail = entry[4]
						if thumbnail == None:
							myentry = entry[0]
							self.videolist[idx] = self.buildEntryComponent(myentry, tubeid )
				idx += 1
			if self.currList == "feedlist":
				self["feedlist"].updateList(self.videolist)


class MyTubeVideoInfoScreen(Screen):
	skin = """
		<screen name="MyTubeVideoInfoScreen" flags="wfNoBorder" position="0,0" size="720,576" title="YouTube - Video Info" >
			<ePixmap position="0,0" zPosition="-1" size="720,576" pixmap="~/mytubemain_bg.png" alphatest="on" transparent="1" backgroundColor="transparent"/>
			<widget name="title" position="60,50" size="600,50" zPosition="5" valign="center" halign="left" font="Regular;21" transparent="1" foregroundColor="white" shadowColor="black" shadowOffset="-1,-1" />
			<widget name="starsbg" pixmap="~/starsbar_empty.png" position="560,220" zPosition="5" size="100,20" transparent="1" alphatest="on" />
			<widget name="stars" pixmap="~/starsbar_filled.png" position="560,220" zPosition="6" size="100,20"  transparent="1" />
			<widget source="infolist" render="Listbox" position="50,110" size="620,110" zPosition="6" scrollbarMode="showNever" selectionDisabled="1" transparent="1">
				<convert type="TemplatedMultiContent">
				{"templates":
					{"default": (110,[
							MultiContentEntryPixmapAlphaTest(pos = (0, 4), size = (130, 98), png = 0), # index 0 is the thumbnail
							MultiContentEntryPixmapAlphaTest(pos = (130, 4), size = (130, 98), png = 1), # index 0 is the thumbnail
							MultiContentEntryPixmapAlphaTest(pos = (260, 4), size = (130, 98), png = 2), # index 0 is the thumbnail
							MultiContentEntryPixmapAlphaTest(pos = (390, 4), size = (130, 98), png = 3), # index 0 is the thumbnail
						]),
					"state": (110,[
							MultiContentEntryText(pos = (10, 40), size = (550, 38), font=2, flags = RT_HALIGN_LEFT | RT_VALIGN_TOP| RT_WRAP, text = 0), # index 0 is the name
						])
					},
					"fonts": [gFont("Regular", 20),gFont("Regular", 14),gFont("Regular", 28)],
					"itemHeight": 110
				}
				</convert>
			</widget>
			<widget name="author" position="60,220" size="300,20" zPosition="10" font="Regular;21" transparent="1" halign="left" valign="top" />
			<widget name="duration" position="370,220" size="200,20" zPosition="10" font="Regular;21" transparent="1" halign="left" valign="top" />
			<widget name="published" position="60,245" size="300,20" zPosition="10" font="Regular;21" transparent="1" halign="left" valign="top" />
			<widget name="views" position="370,245" size="200,20" zPosition="10" font="Regular;21" transparent="1" halign="left" valign="top" />
			<widget name="tags" position="60,270" size="600,20" zPosition="10" font="Regular;21" transparent="1" halign="left" valign="top" />
			<widget name="detailtext" position="60,300" size="610,200" zPosition="10" font="Regular;21" transparent="1" halign="left" valign="top"/>
			<ePixmap position="100,500" size="100,40" zPosition="0" pixmap="~/plugin.png" alphatest="on" transparent="1" />
			<ePixmap position="220,500" zPosition="4" size="140,40" pixmap="skin_default/buttons/red.png" transparent="1" alphatest="on" />
			<widget name="key_red" position="220,500" zPosition="5" size="140,40" valign="center" halign="center" font="Regular;21" transparent="1" foregroundColor="white" shadowColor="black" shadowOffset="-1,-1" />
			<widget name="thumbnail" position="0,0" size="130,98" alphatest="on"/> # fake entry for dynamic thumbnail resizing, currently there is no other way doing this.
		</screen>"""

	def __init__(self, session, plugin_path, videoinfo = None):
		Screen.__init__(self, session)
		self.session = session
		self.skin_path = plugin_path
		self.videoinfo = videoinfo
		self.infolist = []
		self.thumbnails = []
		self.picloads = {}
		self["title"] = Label()
		self["key_red"] = Button(_("Close"))
		self["thumbnail"] = Pixmap()
		self["thumbnail"].hide()
		self["detailtext"] = ScrollLabel()
		self["starsbg"] = Pixmap()
		self["stars"] = ProgressBar()
		self["duration"] = Label()
		self["author"] = Label()
		self["published"] = Label()
		self["views"] = Label()
		self["tags"] = Label()
		self["shortcuts"] = ActionMap(["ShortcutActions", "WizardActions", "MovieSelectionActions", "DirectionActions"],
		{
			"back": self.close,
			"red": self.close,
			"up": self.pageUp,
			"down":	self.pageDown,
			"left":	self.pageUp,
			"right": self.pageDown,
		}, -2)

		self["infolist"] = List(self.infolist)
		self.timer = eTimer()
		self.timer.callback.append(self.picloadTimeout)
		self.onLayoutFinish.append(self.layoutFinished)
		self.onShown.append(self.setWindowTitle)

	def layoutFinished(self):
		self.statuslist = []
		self.statuslist.append(( _("Downloading screenshots. Please wait..." ),_("Downloading screenshots. Please wait..." ) ))
		self["infolist"].style = "state"
		self['infolist'].setList(self.statuslist)
		self.loadPreviewpics()
		if self.videoinfo["Title"] is not None:
			self["title"].setText(self.videoinfo["Title"])
		Description = None
		if self.videoinfo["Description"] is not None:
			Description = self.videoinfo["Description"]
		else:
			Description = None
		if Description is not None:
			self["detailtext"].setText(Description.strip())

		if self.videoinfo["RatingAverage"] is not 0:
			ratingStars = int(round(20 * float(self.videoinfo["RatingAverage"]), 0))
			self["stars"].setValue(ratingStars)
		else:
			self["stars"].hide()
			self["starsbg"].hide()

		if self.videoinfo["Duration"] is not 0:
			durationInSecs = int(self.videoinfo["Duration"])
			mins = int(durationInSecs / 60)
			secs = durationInSecs - mins * 60
			duration = "%d:%02d" % (mins, secs)
			self["duration"].setText(_("Duration: ") + str(duration))

		if self.videoinfo["Author"] is not None or '':
			self["author"].setText(_("Author: ") + self.videoinfo["Author"])

		if self.videoinfo["Published"] is not "unknown":
			self["published"].setText(_("Added: ") + self.videoinfo["Published"].split("T")[0])

		if self.videoinfo["Views"] is not "not available":
			self["views"].setText(_("Views: ") + str(self.videoinfo["Views"]))

		if self.videoinfo["Tags"] is not "not available":
			self["tags"].setText(_("Tags: ") + str(self.videoinfo["Tags"]))

	def setWindowTitle(self):
		self.setTitle(_("YouTube Video Info"))

	def pageUp(self):
		self["detailtext"].pageUp()

	def pageDown(self):
		self["detailtext"].pageDown()

	def loadPreviewpics(self):
		self.thumbnails = []
		self.mythumbubeentries = None
		self.index = 0
		self.maxentries = 0
		self.picloads = {}
		self.mythumbubeentries = self.videoinfo["Thumbnails"]
		self.maxentries = len(self.mythumbubeentries)-1
		if self.mythumbubeentries and len(self.mythumbubeentries):
			currindex = 0
			for entry in self.mythumbubeentries:
				TubeID = self.videoinfo["TubeID"]
				ThumbID = TubeID + str(currindex)
				thumbnailFile = "/tmp/" + ThumbID + ".jpg"
				currPic = [currindex,ThumbID,thumbnailFile,None]
				self.thumbnails.append(currPic)
				thumbnailUrl = None
				thumbnailUrl = entry
				if thumbnailUrl is not None:
					client.downloadPage(thumbnailUrl,thumbnailFile).addCallback(self.fetchFinished,currindex,ThumbID).addErrback(self.fetchFailed,currindex,ThumbID)
				currindex +=1
		else:
			pass

	def fetchFailed(self, string, index, id):
		print "[MyTubeVideoInfoScreen] fetchFailed for index:" + str(index) + "for ThumbID:" + id + string.getErrorMessage()

	def fetchFinished(self, string, index, id):
		print "[MyTubeVideoInfoScreen] fetchFinished for index:" + str(index) + " for ThumbID:" + id
		self.decodePic(index)

	def decodePic(self, index):
		sc = AVSwitch().getFramebufferScale()
		self.picloads[index] = ePicLoad()
		self.picloads[index].PictureData.get().append(boundFunction(self.finish_decode, index))
		for entry in self.thumbnails:
			if entry[0] == index:
				self.index = index
				thumbnailFile = entry[2]
				if (os_path.exists(thumbnailFile) == True):
					print "[MyTubeVideoInfoScreen] decodePic decoding thumbnail for index:"+  str(self.index) + "and file: " + thumbnailFile
					self.picloads[index].setPara((self["thumbnail"].instance.size().width(), self["thumbnail"].instance.size().height(), sc[0], sc[1], False, 1, "#00000000"))
					self.picloads[index].startDecode(thumbnailFile)
				else:
					print "[MyTubeVideoInfoScreen] decodePic Thumbnail file NOT FOUND !!!-->:",thumbnailFile

	def finish_decode(self, picindex = None, picInfo=None):
		print "[MyTubeVideoInfoScreen] finish_decode - of INDEX", picindex
		ptr = self.picloads[picindex].getData()
		if ptr != None:
			self.thumbnails[picindex][3] = ptr
			if (os_path.exists(self.thumbnails[picindex][2]) == True):
				print "[MyTubeVideoInfoScreen] finish_decode removing", self.thumbnails[picindex][2]
				os_remove(self.thumbnails[picindex][2])
				del self.picloads[picindex]
				if len(self.picloads) == 0:
					self.timer.startLongTimer(3)

	def picloadTimeout(self):
		self.timer.stop()
		if len(self.picloads) == 0:
				self.buildInfoList()
		else:
			self.timer.startLongTimer(2)

	def buildInfoList(self):
		self.infolist = []
		Thumbail0 = None
		Thumbail1 = None
		Thumbail2 = None
		Thumbail3 = None
		if self.thumbnails[0][3] is not None:
			Thumbail0 = self.thumbnails[0][3]
		if self.thumbnails[1][3] is not None:
			Thumbail1 = self.thumbnails[1][3]
		if self.thumbnails[2][3] is not None:
			Thumbail2 = self.thumbnails[2][3]
		if self.thumbnails[3][3] is not None:
			Thumbail3 = self.thumbnails[3][3]
		self.infolist.append(( Thumbail0, Thumbail1, Thumbail2, Thumbail3))
		if len(self.infolist):
			self["infolist"].style = "default"
			self["infolist"].disable_callbacks = True
			self["infolist"].list = self.infolist
			self["infolist"].disable_callbacks = False
			self["infolist"].setIndex(0)
			self["infolist"].setList(self.infolist)
			self["infolist"].updateList(self.infolist)


class MyTubeVideoHelpScreen(Screen):
	skin = """
		<screen name="MyTubeVideoHelpScreen" flags="wfNoBorder" position="0,0" size="720,576" title="You Tube - Help" >
			<ePixmap position="0,0" zPosition="-1" size="720,576" pixmap="~/mytubemain_bg.png" alphatest="on" transparent="1" backgroundColor="transparent"/>
			<widget name="title" position="60,50" size="600,50" zPosition="5" valign="center" halign="left" font="Regular;21" transparent="1" foregroundColor="white" shadowColor="black" shadowOffset="-1,-1" />
			<widget name="detailtext" position="60,120" size="610,370" zPosition="10" font="Regular;21" transparent="1" halign="left" valign="top"/>
			<ePixmap position="100,500" size="100,40" zPosition="0" pixmap="~/plugin.png" alphatest="on" transparent="1" />
			<ePixmap position="220,500" zPosition="4" size="140,40" pixmap="skin_default/buttons/red.png" transparent="1" alphatest="on" />
			<widget name="key_red" position="220,500" zPosition="5" size="140,40" valign="center" halign="center" font="Regular;21" transparent="1" foregroundColor="white" shadowColor="black" shadowOffset="-1,-1" />
		</screen>"""

	def __init__(self, session, plugin_path, wantedinfo = None, wantedtitle = None):
		Screen.__init__(self, session)
		self.session = session
		self.skin_path = plugin_path
		self.wantedinfo = wantedinfo
		self.wantedtitle = wantedtitle
		self["title"] = Label()
		self["key_red"] = Button(_("Close"))
		self["detailtext"] = ScrollLabel()

		self["shortcuts"] = ActionMap(["ShortcutActions", "WizardActions", "DirectionActions"],
		{
			"back": self.close,
			"red": self.close,
			"up": self.pageUp,
			"down":	self.pageDown,
			"left":	self.pageUp,
			"right": self.pageDown,
		}, -2)

		self.onLayoutFinish.append(self.layoutFinished)
		self.onShown.append(self.setWindowTitle)

	def layoutFinished(self):
		if self.wantedtitle is None:
			self["title"].setText(_("Help"))
		else:
			self["title"].setText(self.wantedtitle)
		if self.wantedinfo is None:
			self["detailtext"].setText(_("This is the help screen. Feed me with something to display."))
		else:
			self["detailtext"].setText(self.wantedinfo)

	def setWindowTitle(self):
		self.setTitle(_("YouTube Video help"))

	def pageUp(self):
		self["detailtext"].pageUp()

	def pageDown(self):
		self["detailtext"].pageDown()


class MyTubePlayer(Screen, InfoBarNotifications, InfoBarSeek):
	STATE_IDLE = 0
	STATE_PLAYING = 1
	STATE_PAUSED = 2
	ENABLE_RESUME_SUPPORT = True
	ALLOW_SUSPEND = True

	skin = """<screen name="MyTubePlayer" flags="wfNoBorder" position="0,380" size="720,160" title="InfoBar" backgroundColor="transparent">
		<ePixmap position="0,0" pixmap="skin_default/info-bg_mp.png" zPosition="-1" size="720,160" />
		<ePixmap position="29,40" pixmap="skin_default/screws_mp.png" size="665,104" alphatest="on" />
		<ePixmap position="48,70" pixmap="skin_default/icons/mp_buttons.png" size="108,13" alphatest="on" />
		<ePixmap pixmap="skin_default/icons/icon_event.png" position="207,78" size="15,10" alphatest="on" />
		<widget source="session.CurrentService" render="Label" position="230,73" size="360,40" font="Regular;20" backgroundColor="#263c59" shadowColor="#1d354c" shadowOffset="-1,-1" transparent="1">
			<convert type="ServiceName">Name</convert>
		</widget>
		<widget source="session.CurrentService" render="Label" position="580,73" size="90,24" font="Regular;20" halign="right" backgroundColor="#4e5a74" transparent="1">
			<convert type="ServicePosition">Length</convert>
		</widget>
		<widget source="session.CurrentService" render="Label" position="205,129" size="100,20" font="Regular;18" halign="center" valign="center" backgroundColor="#06224f" shadowColor="#1d354c" shadowOffset="-1,-1" transparent="1">
			<convert type="ServicePosition">Position</convert>
		</widget>
		<widget source="session.CurrentService" render="PositionGauge" position="300,133" size="270,10" zPosition="2" pointer="skin_default/position_pointer.png:540,0" transparent="1" foregroundColor="#20224f">
			<convert type="ServicePosition">Gauge</convert>
		</widget>
		<widget source="session.CurrentService" render="Label" position="576,129" size="100,20" font="Regular;18" halign="center" valign="center" backgroundColor="#06224f" shadowColor="#1d354c" shadowOffset="-1,-1" transparent="1">
			<convert type="ServicePosition">Remaining</convert>
		</widget>
		</screen>"""

	def __init__(self, session, service, lastservice, infoCallback = None, nextCallback = None, prevCallback = None):
		Screen.__init__(self, session)
		InfoBarNotifications.__init__(self)
		InfoBarSeek.__init__(self)
		self.session = session
		self.service = service
		self.infoCallback = infoCallback
		self.nextCallback = nextCallback
		self.prevCallback = prevCallback
		self.screen_timeout = 5000
		self.nextservice = None

		print "[MyTubePlayer] evEOF=%d" % iPlayableService.evEOF
		self.__event_tracker = ServiceEventTracker(screen = self, eventmap =
			{
				iPlayableService.evSeekableStatusChanged: self.__seekableStatusChanged,
				iPlayableService.evStart: self.__serviceStarted,
				iPlayableService.evEOF: self.__evEOF,
			})

		self["actions"] = ActionMap(["OkCancelActions", "InfobarSeekActions", "MediaPlayerActions", "MovieSelectionActions"],
		{
				"ok": self.ok,
				"cancel": self.leavePlayer,
				"stop": self.leavePlayer,
				"playpauseService": self.playpauseService,
				"seekFwd": self.playNextFile,
				"seekBack": self.playPrevFile,
				"showEventInfo": self.showVideoInfo,
			}, -2)


		self.lastservice = lastservice

		self.hidetimer = eTimer()
		self.hidetimer.timeout.get().append(self.ok)
		self.returning = False

		self.state = self.STATE_PLAYING
		self.lastseekstate = self.STATE_PLAYING

		self.onPlayStateChanged = [ ]
		self.__seekableStatusChanged()

		self.play()
		self.onClose.append(self.__onClose)

	def __onClose(self):
		self.session.nav.stopService()

	def __evEOF(self):
		print "[MyTubePlayer] Event EOF evEOF=%d" % iPlayableService.evEOF
		self.session.nav.stopService()
		self.handleLeave(config.plugins.mytube.general.on_movie_stop.value)

	def __setHideTimer(self):
		self.hidetimer.start(self.screen_timeout)

	def showInfobar(self):
		self.show()
		if self.state == self.STATE_PLAYING:
			self.__setHideTimer()
		else:
			pass

	def hideInfobar(self):
		self.hide()
		self.hidetimer.stop()

	def ok(self):
		if self.shown:
			self.hideInfobar()
		else:
			self.showInfobar()

	def showVideoInfo(self):
		if self.shown:
			self.hideInfobar()
		if self.infoCallback is not None:
			self.infoCallback()

	def playNextFile(self):
		print "[MyTubePlayer] playNextFile"
		nextservice,error = self.nextCallback()
		print "[MyTubePlayer] nextservice--->",nextservice
		if nextservice is None:
			self.handleLeave(config.plugins.mytube.general.on_movie_stop.value, error)
		else:
			self.playService(nextservice)
			self.showInfobar()

	def playPrevFile(self):
		print "[MyTubePlayer] playPrevFile"
		prevservice,error = self.prevCallback()
		if prevservice is None:
			self.handleLeave(config.plugins.mytube.general.on_movie_stop.value, error)
		else:
			self.playService(prevservice)
			self.showInfobar()

	def playagain(self):
		print "[MyTubePlayer] playagain"
		if self.state != self.STATE_IDLE:
			self.stopCurrent()
		self.play()

	def playService(self, newservice):
		if self.state != self.STATE_IDLE:
			self.stopCurrent()
		self.service = newservice
		self.play()

	def play(self):
		if self.state == self.STATE_PAUSED:
			if self.shown:
				self.__setHideTimer()
		self.state = self.STATE_PLAYING
		self.session.nav.playService(self.service)
		if self.shown:
			self.__setHideTimer()

	def stopCurrent(self):
		print "[MyTubePlayer] stopCurrent"
		self.session.nav.stopService()
		self.state = self.STATE_IDLE

	def playpauseService(self):
		print "[MyTubePlayer] playpauseService"
		if self.state == self.STATE_PLAYING:
			self.pauseService()
		elif self.state == self.STATE_PAUSED:
			self.unPauseService()

	def pauseService(self):
		print "[MyTubePlayer] pauseService"
		if self.state == self.STATE_PLAYING:
			self.setSeekState(self.STATE_PAUSED)

	def unPauseService(self):
		print "[MyTubePlayer] unPauseService"
		if self.state == self.STATE_PAUSED:
			self.setSeekState(self.STATE_PLAYING)


	def getSeek(self):
		service = self.session.nav.getCurrentService()
		if service is None:
			return None

		seek = service.seek()

		if seek is None or not seek.isCurrentlySeekable():
			return None

		return seek

	def isSeekable(self):
		if self.getSeek() is None:
			return False
		return True

	def __seekableStatusChanged(self):
		print "[MyTubePlayer] seekable status changed!"
		if not self.isSeekable():
			self["SeekActions"].setEnabled(False)
			self.setSeekState(self.STATE_PLAYING)
		else:
			self["SeekActions"].setEnabled(True)
			print "[MyTubePlayer] seekable"

	def __serviceStarted(self):
		self.state = self.STATE_PLAYING
		self.__seekableStatusChanged()

	def setSeekState(self, wantstate, onlyGUI = False):
		print "[MyTubePlayer] setSeekState"
		if wantstate == self.STATE_PAUSED:
			print "[MyTubePlayer] trying to switch to Pause- state:",self.STATE_PAUSED
		elif wantstate == self.STATE_PLAYING:
			print "[MyTubePlayer] trying to switch to playing- state:",self.STATE_PLAYING
		service = self.session.nav.getCurrentService()
		if service is None:
			print "[MyTubePlayer] No Service found"
			return False
		pauseable = service.pause()
		if pauseable is None:
			print "[MyTubePlayer] not pauseable."
			self.state = self.STATE_PLAYING

		if pauseable is not None:
			print "[MyTubePlayer] service is pausable"
			if wantstate == self.STATE_PAUSED:
				print "[MyTubePlayer] WANT TO PAUSE"
				pauseable.pause()
				self.state = self.STATE_PAUSED
				if not self.shown:
					self.hidetimer.stop()
					self.show()
			elif wantstate == self.STATE_PLAYING:
				print "[MyTubePlayer] WANT TO PLAY"
				pauseable.unpause()
				self.state = self.STATE_PLAYING
				if self.shown:
					self.__setHideTimer()

		for c in self.onPlayStateChanged:
			c(self.state)

		return True

	def handleLeave(self, how, error = False):
		self.is_closing = True
		if how == "ask":
			list = (
				(_("Yes"), "quit"),
				(_("No, but play video again"), "playagain"),
				(_("Yes, but play next video"), "playnext"),
				(_("Yes, but play previous video"), "playprev"),
			)
			if error is False:
				self.session.openWithCallback(self.leavePlayerConfirmed, ChoiceBox, title=_("Stop playing this movie?"), list = list)
			else:
				self.session.openWithCallback(self.leavePlayerConfirmed, ChoiceBox, title=_("No playable video found! Stop playing this movie?"), list = list)
		else:
			self.leavePlayerConfirmed([True, how])

	def leavePlayer(self):
		self.handleLeave(config.plugins.mytube.general.on_movie_stop.value)

	def leavePlayerConfirmed(self, answer):
		answer = answer and answer[1]
		if answer == "quit":
			print '[MyTubePlayer] quitting'
			self.close()
		elif answer == "playnext":
			self.playNextFile()
		elif answer == "playprev":
			self.playPrevFile()
		elif answer == "playagain":
			self.playagain()

	def doEofInternal(self, playing):
		if not self.execing:
			return
		if not playing :
			return
		self.handleLeave(config.usage.on_movie_eof.value)
