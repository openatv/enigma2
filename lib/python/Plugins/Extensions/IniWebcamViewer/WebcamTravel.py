from Screens.Screen import Screen
from Components.Sources.List import List
from Components.Button import Button
from Components.Label import Label
from Components.ActionMap import ActionMap
from Screens.InputBox import InputBox
from Components.Input import Input
from Components.MultiContent import MultiContentEntryText, MultiContentEntryPixmapAlphaTest
from Components.Pixmap import Pixmap
from Components.AVSwitch import AVSwitch
from Tools.BoundFunction import boundFunction

from enigma import eListboxPythonMultiContent, RT_HALIGN_LEFT, RT_HALIGN_RIGHT, ePicLoad, eTimer

from PictureScreen import PictureScreen

from twisted.web.client import getPage, downloadPage
# from twisted.internet import reactor

from xml.etree.cElementTree import fromstring as cElementTree_fromstring

from os import remove as os_remove
from os.path import exists as os_path_exists
from datetime import datetime

from urllib import quote as urllib_quote
#########################################

class TravelWebcamviewer(Screen):
	skin = ""

	def __init__(self, session, args=0):
		skin = """<screen position="93,70" size="550,450" title="Webcams provided by webcams.travel">

			<widget source="list" render="Listbox" position="0,0" size="550,350" zPosition="1" scrollbarMode="showOnDemand" transparent="1"  >
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
					"status": (77,[
							MultiContentEntryText(pos = (10, 1), size = (500, 28), font=2, flags = RT_HALIGN_LEFT | RT_VALIGN_TOP| RT_WRAP, text = 0), # index 0 is the name
							MultiContentEntryText(pos = (10, 22), size = (500, 46), font=3, flags = RT_HALIGN_LEFT | RT_VALIGN_TOP| RT_WRAP, text = 1), # index 2 is the description
						])
					},
					"fonts": [gFont("Regular", 22),gFont("Regular", 18),gFont("Regular", 26),gFont("Regular", 20)],
					"itemHeight": 77
				}
				</convert>
			</widget>
			<widget name="thumbnail" position="0,0" size="100,75" alphatest="on"/> # fake entry for dynamic thumbnail resizing, currently there is no other way doing this.

			<widget name="count" position="5,360" zPosition="5" size="140,40" valign="center" halign="center" font="Regular;21" transparent="1" foregroundColor="white" shadowColor="black" shadowOffset="-1,-1" />
			<widget name="page" position="150,360" zPosition="5" size="140,40" valign="center" halign="center" font="Regular;21" transparent="1" foregroundColor="white" shadowColor="black" shadowOffset="-1,-1" />
			<widget name="currentnumbers" position="295,360" zPosition="5" size="140,40" valign="center" halign="center" font="Regular;21" transparent="1" foregroundColor="white" shadowColor="black" shadowOffset="-1,-1" />

			<ePixmap position="5,410" zPosition="0" size="140,40" pixmap="skin_default/buttons/red.png" transparent="1" alphatest="on" />
			<ePixmap position="150,410" zPosition="1" size="140,40" pixmap="skin_default/buttons/green.png" transparent="1" alphatest="on" />
			<ePixmap position="295,410" zPosition="2" size="140,40" pixmap="skin_default/buttons/yellow.png" transparent="1" alphatest="on" />
			<!-- #not used now# ePixmap position="445,410" zPosition="3" size="140,40" pixmap="skin_default/buttons/blue.png" transparent="1" alphatest="on" //-->
			<widget name="key_red" position="5,410" zPosition="5" size="140,40" valign="center" halign="center" font="Regular;21" transparent="1" foregroundColor="white" shadowColor="black" shadowOffset="-1,-1" />
			<widget name="key_green" position="150,410" zPosition="5" size="140,40" valign="center" halign="center" font="Regular;21" transparent="1" foregroundColor="white" shadowColor="black" shadowOffset="-1,-1" />
			<widget name="key_yellow" position="295,410" zPosition="5" size="140,40" valign="center" halign="center" font="Regular;21" transparent="1" foregroundColor="white" shadowColor="black" shadowOffset="-1,-1" />
			<widget name="key_blue" position="445,410" zPosition="5" size="140,40" valign="center" halign="center" font="Regular;21" transparent="1" foregroundColor="white" shadowColor="black" shadowOffset="-1,-1" />

		</screen>"""
		self.skin = skin
		Screen.__init__(self, session)
		self.picloads = {}
		self.thumbnails = {}

		self["list"] = List([])
		self["thumbnail"] = Pixmap()
		self["thumbnail"].hide()

		self["count"] = Label(_("Cams: "))
		self["page"] = Label(_("Page: "))
		self["currentnumbers"] = Label(_("current: "))

		self["key_red"] = Button()
		self["key_green"] = Button()
		self["key_yellow"] = Button()
		self["key_blue"] = Button()
		self.onLayoutFinish.append(self._setButtonTexts)

		self["actions"] = ActionMap(["WizardActions", "MenuActions", "DirectionActions", "ShortcutActions"], {
			"ok": self.onOK,
			"red": self.onRed,
			"green": self.onGreen,
			"yellow": self.onYellow,
			"back": self.close
		}, -1)
		self.finish_loading = True
		self.timer_default = eTimer()
		self.timer_default.timeout.callback.append(self.buildCamList)

		self.timer_status = eTimer()
		self.timer_status.timeout.callback.append(self.buildStatusList)

		self.timer_labels = eTimer()
		self.timer_labels.timeout.callback.append(self.refreshLabels)

		self.onLayoutFinish.append(self.loadData)

	def _setButtonTexts(self):
		self["key_red"].setText(_("Previous page"))
		self["key_red"].hide()
		self["key_green"].setText(_("Next page"))
		self["key_green"].hide()
		self["key_yellow"].setText(_("Search"))

	def onOK(self):
		selection = self["list"].getCurrent()
		if selection:
			print selection
			self.session.open(PictureScreen, selection[0].title, selection[0].pic_url)

	def onRed(self):
		if self.hasPrevPage():
			self.timer_status.start(1)
			WebcamTravelerAPI().list_popular(self.onDataLoaded, _page=self.page - 1)

	def onGreen(self):
		if self.hasNextPage():
			self.timer_status.start(1)
			WebcamTravelerAPI().list_popular(self.onDataLoaded, _page=self.page + 1)

	def onYellow(self):
		self.session.openWithCallback(self.onSearchkeyEntered, InputBox, title=_("Please enter a searchkey:"), text="Search Webcams", maxSize=False, type=Input.TEXT)

	def onSearchkeyEntered(self, value):
		if value is not None and self.finish_loading:
			self.timer_status.start(1)
			WebcamTravelerAPI().search(self.onDataLoaded, value)
			self.finish_loading = False

	def loadData(self):
		if self.finish_loading:
			self.timer_status.start(1)
			WebcamTravelerAPI().list_popular(self.onDataLoaded)
			self.finish_loading = False

	def onDataLoaded(self, list, count=0, page=0, per_page=0):
		print "onDataLoaded", list, count, page, per_page
		self.count = count
		self.page = page
		self.per_page = per_page

		self.pixmaps_to_load = []
		self.picloads = {}
		self.thumbnails = {}
		self.list = list
		self.downloadThumbnails()

	def downloadThumbnails(self):
		for cam in self.list:
			self.pixmaps_to_load.append(cam.webcamid)
			downloadPage(cam.thumbnail_url, "/tmp/" + str(cam.webcamid) + "_thumb.jpg").addCallback(self.fetchFinished, cam.webcamid).addErrback(self.fetchFailed, cam.webcamid)

	def fetchFailed(self, string, webcamid):
		print "fetchFailed", webcamid, string.getErrorMessage()
		self.buildEntryStatus(string.getErrorMessage())
		self.pixmaps_to_load.remove(webcamid)

	def fetchFinished(self, x, webcamid):
		print "fetchFinished", x, webcamid
		self.pixmaps_to_load.remove(webcamid)

		sc = AVSwitch().getFramebufferScale()
		if os_path_exists("/tmp/" + str(webcamid) + "_thumb.jpg"):
			self.picloads[webcamid] = ePicLoad()
			self.picloads[webcamid].PictureData.get().append(boundFunction(self.finish_decode, webcamid))
			self.picloads[webcamid].setPara((self["thumbnail"].instance.size().width(), self["thumbnail"].instance.size().height(), sc[0], sc[1], False, 1, "#00000000"))
			self.picloads[webcamid].startDecode("/tmp/" + str(webcamid) + "_thumb.jpg")
		else:
			print "[decodePic] Thumbnail file NOT FOUND !!!-->:", thumbnailFile

	def finish_decode(self, webcamid, info):
		print "finish_decode - of webcamid", webcamid, info
		ptr = self.picloads[webcamid].getData()
		if ptr is not None:
			self.thumbnails[webcamid] = ptr
			print "removing file"
			os_remove("/tmp/" + str(webcamid) + "_thumb.jpg")
			del self.picloads[webcamid]
			self.timer_default.start(1)

	def buildStatusList(self):
		self.timer_status.stop()
		print "buildStatusList"
		statuslist = []
		statuslist.append(self.buildEntryStatus("loading data"))

		self["list"].style = "status"
		self["list"].disable_callbacks = True
		self["list"].list = statuslist
		self["list"].disable_callbacks = False
		self["list"].setIndex(0)
		self["list"].setList(statuslist)
		self["list"].updateList(statuslist)

	def buildCamList(self):
		if len(self.picloads) != 0:
			return
		self.timer_default.stop()
		print "buildCamList"
		statuslist = []
		for cam in self.list:
			try:
				x = self.buildEntryCam(cam)
				statuslist.append(x)
			except KeyError:
				pass

		self["list"].style = "default"
		self["list"].disable_callbacks = True
		self["list"].list = statuslist
		self["list"].disable_callbacks = False
		self["list"].setIndex(0)
		self["list"].setList(statuslist)
		self["list"].updateList(statuslist)
		self.timer_labels.start(1)

	def refreshLabels(self):
		self.timer_labels.stop()
		if self.hasNextPage():
			self["key_green"].show()
		else:
			self["key_green"].hide()

		if self.hasPrevPage():
			self["key_red"].show()
		else:
			self["key_red"].hide()
		self["count"].setText(_("Cams: ") + str(self.count))
		self["page"].setText(_("Page: ") + str(self.page) + "/" + str(self.count / self.per_page))
		self["currentnumbers"].setText(_("current: ") + str(((self.page - 1) * self.per_page) + 1) + "-" + str(((self.page - 1) * self.per_page) + len(self.list)))

		self.finish_loading = True

	def buildEntryCam(self, cam):
		return ((cam, cam.title, cam.webcamid, "last update", self.thumbnails[cam.webcamid], _("Last updated: ") + cam.last_update, _("Views: ") + cam.view_count, _("User: ") + cam.user, _("Ratings: ") + cam.rating_avg))

	def buildEntryStatus(self, text):
		return (("loading ...", "please wait just a moment", "cccccccccccc", "last update", "1111111111111", _("Last updated: "), _("Views: "), _("Duration: "), _("Ratings: ")))

	def hasNextPage(self):
		if (self.per_page * (self.page + 1) > self.count):
			return False
		else:
			return True

	def hasPrevPage(self):
		if (self.page > 1):
			return True
		else:
			return False

#########################################

#########################################
# API ###################################
#########################################
#########################################
#########################################

class WebcamTravelerAPI:
	APIKEY = "4fc0163634276a71fdf7e849ef0a9d23"
	URL_HOST = "api.webcams.travel"
	URL_FORMAT = "rest"

	def get(self, method, callback, errorback, **kwargs):
		url = "http://" + self.URL_HOST + "/" + self.URL_FORMAT + "?method=" + method + "&devid=" + self.APIKEY
		for key in kwargs:
			print key, kwargs[key]
			url += "&" + str(key) + "=" + str(kwargs[key])
		print url
		cb = getPage(url).addCallback(callback)
		if errorback is not None:
			cb.addErrback(errorback)
		else:
			cb.addErrback(self.loadingFailed)

	def loadingFailed(self, reason):
		print "loadingFailed", reason

	def list_popular(self, callback, _page=1, _per_page=30):
		"""	wct.webcams.list_popular
			Get the popular webcams.

			devid (required)
				Your developer ID. If you do not have one, please signup for a developer ID.
			per_page (optional)
				Number of webcams to return per page. If this argument is omitted, it defaults to 10. The maximum allowed value is 50.
			page (optional)
				The page of results to return. If this argument is omitted, it defaults to 1.
		"""
		cb = lambda raw: self.list_popularCB(raw, callback)
		self.get("wct.webcams.list_popular", cb, None, page=_page, per_page=_per_page)

	def list_popularCB(self, raw, callback):
		dom = cElementTree_fromstring(raw)
		list, _count, _page, _per_page = self.parseWebcam(dom)
		callback(list, count=_count, page=_page, per_page=_per_page)

	def parseWebcam(self, dom):
		cams = dom.findall("webcams")
		_count = int(cams[0].findtext("count", 0))
		_page = int(cams[0].findtext("page", 0))
		_per_page = int(cams[0].findtext("per_page", 0))
		list = []
		for cam in cams[0].findall("webcam"):
			ca = Cam(cam)
			list.append(ca)
		return list, _count, _page, _per_page

	def search(self, callback, searchkey, _page=1, _per_page=30):
		"""wct.search.webcams

			Search the webcams by the given query.


			Arguments

			devid (required)
			Your developer ID. If you do not have one, please signup for a developer ID.
			query (required)
			The query to search for.
			per_page (optional)
			Number of comments to return per page. If this argument is omitted, it defaults to 10. The maximum allowed value is 50.
			page (optional)
			The page of results to return. If this argument is omitted, it defaults to 1.
		"""
		cb = lambda raw: self.searchCB(raw, callback)
		self.get("wct.search.webcams", cb, None, query=urllib_quote(searchkey), page=_page, per_page=_per_page)

	def searchCB(self, raw, callback):
		dom = cElementTree_fromstring(raw)
		list, _count, _page, _per_page = self.parseWebcam(dom)
		callback(list, count=_count, page=_page, per_page=_per_page)


class Cam:
	def __init__(self, element):
		self.title = element.findtext("title", 0).encode('utf-8', "ignore")
		self.webcamid = int(element.findtext("webcamid", 0))
		self.pic_url = "http://images.webcams.travel/webcam/" + str(self.webcamid) + ".jpg"
		# self.icon_url = element.findtext("icon_url", 0)
		self.thumbnail_url = element.findtext("thumbnail_url", 0)
		self.view_count = element.findtext("view_count", 0)
		self.user = element.findtext("user", 0)
		self.userid = element.findtext("userid", 0)
		self.rating_avg = element.findtext("rating_avg", 0)
		self.rating_count = element.findtext("rating_count", 0)
		self.city = element.findtext("city", 0)
		self.country = element.findtext("country", 0)
		self.continent = element.findtext("continent", 0)
		self.latitude = element.findtext("latitude", 0)
		self.longitude = element.findtext("longitude", 0)

		datex = datetime.fromtimestamp(int(element.findtext("last_update", 0)))
		self.last_update = datex.strftime("%d.%m.%Y %H:%M:%S")
