# -*- coding: iso-8859-1 -*-
from enigma import ePythonMessagePump

from __init__ import decrypt_block
from ThreadQueue import ThreadQueue
import gdata.youtube
import gdata.youtube.service
from gdata.service import BadAuthentication

from twisted.web import client
from twisted.internet import reactor
from urllib2 import Request, URLError, urlopen as urlopen2
from socket import gaierror, error
import os, socket
from urllib import quote, unquote_plus, unquote
from httplib import HTTPConnection, CannotSendRequest, BadStatusLine, HTTPException

from urlparse import parse_qs
from threading import Thread

HTTPConnection.debuglevel = 1

def validate_cert(cert, key):
	buf = decrypt_block(cert[8:], key)
	if buf is None:
		return None
	return buf[36:107] + cert[139:196]

def get_rnd():
	try:
		rnd = os.urandom(8)
		return rnd
	except:
		return None

std_headers = {
	'User-Agent': 'Mozilla/5.0 (X11; U; Linux x86_64; en-US; rv:1.9.2.6) Gecko/20100627 Firefox/3.6.6',
	'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.7',
	'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
	'Accept-Language': 'en-us,en;q=0.5',
}

#config.plugins.mytube = ConfigSubsection()
#config.plugins.mytube.general = ConfigSubsection()
#config.plugins.mytube.general.useHTTPProxy = ConfigYesNo(default = False)
#config.plugins.mytube.general.ProxyIP = ConfigIP(default=[0,0,0,0])
#config.plugins.mytube.general.ProxyPort = ConfigNumber(default=8080)
#class MyOpener(FancyURLopener):
#	version = 'Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.8.0.12) Gecko/20070731 Ubuntu/dapper-security Firefox/1.5.0.12'


class GoogleSuggestions():
	def __init__(self):
		self.hl = "en"
		self.conn = None

	def prepareQuery(self):
		#GET /complete/search?output=toolbar&client=youtube-psuggest&xml=true&ds=yt&hl=en&jsonp=self.gotSuggestions&q=s
		self.prepQuerry = "/complete/search?output=toolbar&client=youtube&xml=true&ds=yt&"
		if self.hl is not None:
			self.prepQuerry = self.prepQuerry + "hl=" + self.hl + "&"
		self.prepQuerry = self.prepQuerry + "jsonp=self.gotSuggestions&q="
		print "[MyTube - GoogleSuggestions] prepareQuery:",self.prepQuerry

	def getSuggestions(self, queryString):
		self.prepareQuery()
		if queryString is not "":
			query = self.prepQuerry + quote(queryString)
			self.conn = HTTPConnection("google.com")
			try:
				self.conn = HTTPConnection("google.com")
				self.conn.request("GET", query, "", {"Accept-Encoding": "UTF-8"})
			except (CannotSendRequest, gaierror, error):
				self.conn.close()
				print "[MyTube - GoogleSuggestions] Can not send request for suggestions"
				return None
			else:
				try:
					response = self.conn.getresponse()
				except BadStatusLine:
					self.conn.close()
					print "[MyTube - GoogleSuggestions] Can not get a response from google"
					return None
				else:
					if response.status == 200:
						data = response.read()
						header = response.getheader("Content-Type", "text/xml; charset=ISO-8859-1")
						charset = "ISO-8859-1"
						try:
							charset = header.split(";")[1].split("=")[1]
							print "[MyTube - GoogleSuggestions] Got charset %s" %charset
						except:
							print "[MyTube - GoogleSuggestions] No charset in Header, falling back to %s" %charset
						data = data.decode(charset).encode("utf-8")
						self.conn.close()
						return data
					else:
						self.conn.close()
						return None
		else:
			return None

class MyTubeFeedEntry():
	def __init__(self, feed, entry, favoritesFeed = False):
		self.feed = feed
		self.entry = entry
		self.favoritesFeed = favoritesFeed
		self.thumbnail = {}
		"""self.myopener = MyOpener()
		urllib.urlopen = MyOpener().open
		if config.plugins.mytube.general.useHTTPProxy.value is True:
			proxy = {'http': 'http://'+str(config.plugins.mytube.general.ProxyIP.getText())+':'+str(config.plugins.mytube.general.ProxyPort.value)}
			self.myopener = MyOpener(proxies=proxy)
			urllib.urlopen = MyOpener(proxies=proxy).open
		else:
			self.myopener = MyOpener()
			urllib.urlopen = MyOpener().open"""

	def isPlaylistEntry(self):
		return False

	def getTubeId(self):
		#print "[MyTubeFeedEntry] getTubeId"
		ret = None
		if self.entry.media.player:
			split = self.entry.media.player.url.split("=")
			ret = split.pop()
			if ret.startswith('youtube_gdata'):
				tmpval=split.pop()
				if tmpval.endswith("&feature"):
					tmp = tmpval.split("&")
					ret = tmp.pop(0)
		return ret

	def getTitle(self):
		#print "[MyTubeFeedEntry] getTitle",self.entry.media.title.text
		return self.entry.media.title.text

	def getDescription(self):
		#print "[MyTubeFeedEntry] getDescription"
		if self.entry.media is not None and self.entry.media.description is not None:
			return self.entry.media.description.text
		return "not vailable"

	def getThumbnailUrl(self, index = 0):
		#print "[MyTubeFeedEntry] getThumbnailUrl"
		if index < len(self.entry.media.thumbnail):
			return self.entry.media.thumbnail[index].url
		return None

	def getPublishedDate(self):
		if self.entry.published is not None:
			return self.entry.published.text
		return "unknown"

	def getViews(self):
		if self.entry.statistics is not None:
			return self.entry.statistics.view_count
		return "not available"

	def getDuration(self):
		if self.entry.media is not None and self.entry.media.duration is not None:
			return self.entry.media.duration.seconds
		else:
			return 0

	def getRatingAverage(self):
		if self.entry.rating is not None:
			return self.entry.rating.average
		return 0


	def getNumRaters(self):
		if self.entry.rating is not None:
			return self.entry.rating.num_raters
		return ""

	def getAuthor(self):
		authors = []
		for author in self.entry.author:
			authors.append(author.name.text)
		author = ", ".join(authors)
		return author

	def PrintEntryDetails(self):
		EntryDetails = { 'Title': None, 'TubeID': None, 'Published': None, 'Published': None, 'Description': None, 'Category': None, 'Tags': None, 'Duration': None, 'Views': None, 'Rating': None, 'Thumbnails': None}
		EntryDetails['Title'] = self.entry.media.title.text
		EntryDetails['TubeID'] = self.getTubeId()
		EntryDetails['Description'] = self.getDescription()
		EntryDetails['Category'] = self.entry.media.category[0].text
		EntryDetails['Tags'] = self.entry.media.keywords.text
		EntryDetails['Published'] = self.getPublishedDate()
		EntryDetails['Views'] = self.getViews()
		EntryDetails['Duration'] = self.getDuration()
		EntryDetails['Rating'] = self.getNumRaters()
		EntryDetails['RatingAverage'] = self.getRatingAverage()
		EntryDetails['Author'] = self.getAuthor()
		# show thumbnails
		list = []
		for thumbnail in self.entry.media.thumbnail:
			print 'Thumbnail url: %s' % thumbnail.url
			list.append(str(thumbnail.url))
		EntryDetails['Thumbnails'] = list
		#print EntryDetails
		return EntryDetails

	def getVideoUrl(self):
		VIDEO_FMT_PRIORITY_MAP = {
			'38' : 1, #MP4 Original (HD)
			'37' : 2, #MP4 1080p (HD)
			'22' : 3, #MP4 720p (HD)
			'18' : 4, #MP4 360p
			'35' : 5, #FLV 480p
			'34' : 6, #FLV 360p
		}
		video_url = None
		video_id = str(self.getTubeId())

		# Getting video webpage
		#URLs for YouTube video pages will change from the format http://www.youtube.com/watch?v=ylLzyHk54Z0 to http://www.youtube.com/watch#!v=ylLzyHk54Z0.
		watch_url = 'http://www.youtube.com/watch?v=%s&gl=US&hl=en' % video_id
		watchrequest = Request(watch_url, None, std_headers)
		try:
			print "[MyTube] trying to find out if a HD Stream is available",watch_url
			watchvideopage = urlopen2(watchrequest).read()
		except (URLError, HTTPException, socket.error), err:
			print "[MyTube] Error: Unable to retrieve watchpage - Error code: ", str(err)
			return video_url

		# Get video info
		for el in ['&el=embedded', '&el=detailpage', '&el=vevo', '']:
			info_url = ('http://www.youtube.com/get_video_info?&video_id=%s%s&ps=default&eurl=&gl=US&hl=en' % (video_id, el))
			request = Request(info_url, None, std_headers)
			try:
				infopage = urlopen2(request).read()
				videoinfo = parse_qs(infopage)
				if ('url_encoded_fmt_stream_map' or 'fmt_url_map') in videoinfo:
					break
			except (URLError, HTTPException, socket.error), err:
				print "[MyTube] Error: unable to download video infopage",str(err)
				return video_url

		if ('url_encoded_fmt_stream_map' or 'fmt_url_map') not in videoinfo:
			# Attempt to see if YouTube has issued an error message
			if 'reason' not in videoinfo:
				print '[MyTube] Error: unable to extract "fmt_url_map" or "url_encoded_fmt_stream_map" parameter for unknown reason'
			else:
				reason = unquote_plus(videoinfo['reason'][0])
				print '[MyTube] Error: YouTube said: %s' % reason.decode('utf-8')
			return video_url

		video_fmt_map = {}
		fmt_infomap = {}
		if videoinfo.has_key('url_encoded_fmt_stream_map'):
			tmp_fmtUrlDATA = videoinfo['url_encoded_fmt_stream_map'][0].split(',')
		else:
			tmp_fmtUrlDATA = videoinfo['fmt_url_map'][0].split(',')
		for fmtstring in tmp_fmtUrlDATA:
			fmturl = fmtid = fmtsig = ""
			if videoinfo.has_key('url_encoded_fmt_stream_map'):
				try:
					for arg in fmtstring.split('&'):
						if arg.find('=') >= 0:
							print arg.split('=')
							key, value = arg.split('=')
							if key == 'itag':
								if len(value) > 3:
									value = value[:2]
								fmtid = value
							elif key == 'url':
								fmturl = value
							elif key == 'sig':
								fmtsig = value
								
					if fmtid != "" and fmturl != "" and fmtsig != ""  and VIDEO_FMT_PRIORITY_MAP.has_key(fmtid):
						video_fmt_map[VIDEO_FMT_PRIORITY_MAP[fmtid]] = { 'fmtid': fmtid, 'fmturl': unquote_plus(fmturl), 'fmtsig': fmtsig }
						fmt_infomap[int(fmtid)] = "%s&signature=%s" %(unquote_plus(fmturl), fmtsig)
					fmturl = fmtid = fmtsig = ""

				except:
					print "error parsing fmtstring:",fmtstring
					
			else:
				(fmtid,fmturl) = fmtstring.split('|')
			if VIDEO_FMT_PRIORITY_MAP.has_key(fmtid) and fmtid != "":
				video_fmt_map[VIDEO_FMT_PRIORITY_MAP[fmtid]] = { 'fmtid': fmtid, 'fmturl': unquote_plus(fmturl) }
				fmt_infomap[int(fmtid)] = unquote_plus(fmturl)
		print "[MyTube] got",sorted(fmt_infomap.iterkeys())
		if video_fmt_map and len(video_fmt_map):
			print "[MyTube] found best available video format:",video_fmt_map[sorted(video_fmt_map.iterkeys())[0]]['fmtid']
			best_video = video_fmt_map[sorted(video_fmt_map.iterkeys())[0]]
			video_url = "%s&signature=%s" %(best_video['fmturl'].split(';')[0], best_video['fmtsig'])
			print "[MyTube] found best available video url:",video_url

		return video_url

	def getRelatedVideos(self):
		print "[MyTubeFeedEntry] getRelatedVideos()"
		for link in self.entry.link:
			#print "Related link: ", link.rel.endswith
			if link.rel.endswith("video.related"):
				print "Found Related: ", link.href
				return link.href

	def getResponseVideos(self):
		print "[MyTubeFeedEntry] getResponseVideos()"
		for link in self.entry.link:
			#print "Responses link: ", link.rel.endswith
			if link.rel.endswith("video.responses"):
				print "Found Responses: ", link.href
				return link.href

	def getUserVideos(self):
		print "[MyTubeFeedEntry] getUserVideos()"
		username = self.getAuthor()
		myuri = 'http://gdata.youtube.com/feeds/api/users/%s/uploads' % username
		print "Found Uservideos: ", myuri
		return myuri

class MyTubePlayerService():
#	Do not change the client_id and developer_key in the login-section!
#	ClientId: ytapi-dream-MyTubePlayer-i0kqrebg-0
#	DeveloperKey: AI39si4AjyvU8GoJGncYzmqMCwelUnqjEMWTFCcUtK-VUzvWygvwPO-sadNwW5tNj9DDCHju3nnJEPvFy4WZZ6hzFYCx8rJ6Mw
	def __init__(self):
		print "[MyTube] MyTubePlayerService - init"
		self.feedentries = []
		self.feed = None

	def startService(self):
		print "[MyTube] MyTubePlayerService - startService"
		self.yt_service = gdata.youtube.service.YouTubeService(
			developer_key = 'AI39si4AjyvU8GoJGncYzmqMCwelUnqjEMWTFCcUtK-VUzvWygvwPO-sadNwW5tNj9DDCHju3nnJEPvFy4WZZ6hzFYCx8rJ6Mw',
			client_id = 'ytapi-dream-MyTubePlayer-i0kqrebg-0'
		)
#		self.loggedIn = False
		#os.environ['http_proxy'] = 'http://169.229.50.12:3128'
		#proxy = os.environ.get('http_proxy')
		#print "FOUND ENV PROXY-->",proxy
		#for a in os.environ.keys():
		#	print a

	def stopService(self):
		print "[MyTube] MyTubePlayerService - stopService"
		del self.ytService

	def getFeedService(self, feedname):
		if feedname == "top_rated":
			return self.yt_service.GetTopRatedVideoFeed
		elif feedname == "most_viewed":
			return self.yt_service.GetMostViewedVideoFeed
		elif feedname == "recently_featured":
			return self.yt_service.GetRecentlyFeaturedVideoFeed
		elif feedname == "top_favorites":
			return self.yt_service.GetTopFavoritesVideoFeed
		elif feedname == "most_recent":
			return self.yt_service.GetMostRecentVideoFeed
		elif feedname == "most_discussed":
			return self.yt_service.GetMostDiscussedVideoFeed
		elif feedname == "most_linked":
			return self.yt_service.GetMostLinkedVideoFeed
		elif feedname == "most_responded":
			return self.yt_service.GetMostRespondedVideoFeed
		return self.yt_service.GetYouTubeVideoFeed

	def getFeed(self, url, feedname = "", callback = None, errorback = None):
		print "[MyTube] MyTubePlayerService - getFeed:",url, feedname
		self.feedentries = []
		ytservice = self.yt_service.GetYouTubeVideoFeed
		if feedname in ("hd", "most_popular", "most_shared", "on_the_web"):
			if feedname == "hd":
				url = "http://gdata.youtube.com/feeds/api/videos/-/HD"
			else:
				url = url + feedname
		elif feedname in ("top_rated","most_viewed","recently_featured","top_favorites","most_recent","most_discussed","most_linked","most_responded"):
			url = None
			ytservice = self.getFeedService(feedname)

		queryThread = YoutubeQueryThread(ytservice, url, self.gotFeed, self.gotFeedError, callback, errorback)
		queryThread.start()
		return queryThread

	def search(self, searchTerms, startIndex = 1, maxResults = 25,
					orderby = "relevance", time = 'all_time', racy = "include",
					author = "", lr = "", categories = "", sortOrder = "ascending",
					callback = None, errorback = None):
		print "[MyTube] MyTubePlayerService - search()"
		self.feedentries = []
		query = gdata.youtube.service.YouTubeVideoQuery()
		query.vq = searchTerms
		query.orderby = orderby
		query.time = time
		query.racy = racy
		query.sortorder = sortOrder
		if lr is not None:
			query.lr = lr
		if categories[0] is not None:
			query.categories = categories
		query.start_index = startIndex
		query.max_results = maxResults
		queryThread = YoutubeQueryThread(self.yt_service.YouTubeQuery, query, self.gotFeed, self.gotFeedError, callback, errorback)
		queryThread.start()
		return queryThread

	def gotFeed(self, feed, callback):
		if feed is not None:
			self.feed = feed
			for entry in self.feed.entry:
				MyFeedEntry = MyTubeFeedEntry(self, entry)
				self.feedentries.append(MyFeedEntry)
		if callback is not None:
			callback(self.feed)

	def gotFeedError(self, exception, errorback):
		if errorback is not None:
			errorback(exception)


	def getTitle(self):
		return self.feed.title.text

	def getEntries(self):
		return self.feedentries

	def itemCount(self):
		return self.feed.items_per_page.text

	def getTotalResults(self):
		return self.feed.total_results.text

	def getNextFeedEntriesURL(self):
		for link in self.feed.link:
			if link.rel == "next":
				return link.href
		return None

class YoutubeQueryThread(Thread):
	def __init__(self, query, param, gotFeed, gotFeedError, callback, errorback):
		Thread.__init__(self)
		self.messagePump = ePythonMessagePump()
		self.messages = ThreadQueue()
		self.gotFeed = gotFeed
		self.gotFeedError = gotFeedError
		self.callback = callback
		self.errorback = errorback
		self.query = query
		self.param = param
		self.canceled = False
		self.messagePump.recv_msg.get().append(self.finished)

	def cancel(self):
		self.canceled = True

	def run(self):
		try:
			if self.param is None:
				feed = self.query()
			else:
				feed = self.query(self.param)
			self.messages.push((True, feed, self.callback))
			self.messagePump.send(0)
		except Exception, ex:
			self.messages.push((False, ex, self.errorback))
			self.messagePump.send(0)

	def finished(self, val):
		if not self.canceled:
			message = self.messages.pop()
			if message[0]:
				self.gotFeed(message[1], message[2])
			else:
				self.gotFeedError(message[1], message[2])

myTubeService = MyTubePlayerService()
