#	-*-	coding:	utf-8	-*-

from twagenthelper import TwAgentHelper
from imports import *

class youtubeUrl:


	def __init__(self, session):
		self.callBack = None
		self.errBack = None
		self.session = session
		self.error = ""
		self.useProxy = False
		puser = "user!"
		ppass = "pass!"
		self.yt_tw_agent_hlp = TwAgentHelper(use_proxy=self.useProxy, p_user=puser, p_pass=ppass, use_cookies=True)
		mp_globals.proxy = self.useProxy

	def addCallback(self, cbFunc):
		self.callBack = cbFunc

	def addErrback(self, errFunc):
		self.errBack = errFunc

	def dataError(self, error):
		self.error = self.error % str(error)
		self.errReturn()

	def errReturn(self, url=None):
		del self.yt_tw_agent_hlp
		if self.errBack == None:
			self.session.openWithCallback(self.cbYTErr, MessageBox,str(self.error), MessageBox.TYPE_INFO, timeout=10)
		else:
			self.errBack(self.error)

	def cbYTErr(self, res):
		return

	def getVideoUrl(self, url, videoPrio=2):
		# this part is from mtube plugin

		if not self.callBack:
			self.error = '[YoutubeURL] Error: no callBack set'
			self.errReturn()

		if videoPrio == 0:
			self.VIDEO_FMT_PRIORITY_MAP = {
			'38' : 5, #MP4 Original (HD)
#			'37' : 5, #MP4 1080p (HD)
			'22' : 4, #MP4 720p (HD)
			'35' : 2, #FLV 480p
			'18' : 1, #MP4 360p
			'34' : 3, #FLV 360p
			}
		elif videoPrio == 1:
			self.VIDEO_FMT_PRIORITY_MAP = {
			'38' : 5, #MP4 Original (HD)
#			'37' : 5, #MP4 1080p (HD)
			'22' : 4, #MP4 720p (HD)
			'35' : 1, #FLV 480p
			'18' : 2, #MP4 360p
			'34' : 3, #FLV 360p
			}
		else:
			self.VIDEO_FMT_PRIORITY_MAP = {
			'38' : 2, #MP4 Original (HD)
#			'37' : 1, #MP4 1080p (HD)
			'22' : 1, #MP4 720p (HD)
			'35' : 3, #FLV 480p
			'18' : 4, #MP4 360p
			'34' : 5, #FLV 360p
			}

		self.video_url = None
		self.video_id = url
		self.videoPrio = videoPrio

		# Getting video webpage
		#URLs for YouTube video pages will change from the format http://www.youtube.com/watch?v=ylLzyHk54Z0 to http://www.youtube.com/watch#!v=ylLzyHk54Z0.
		watch_url = 'http://www.youtube.com/watch?v=%s&safeSearch=none'%self.video_id
		self.error = "[YoutubeURL] Error: Unable to retrieve watchpage:\n%s"
		self.yt_tw_agent_hlp.getWebPage(self.parseVInfo, self.dataError, watch_url, False)

	def parseVInfo(self, videoinfo):
		flashvars = self.extractFlashVars(videoinfo, 0)
		if not flashvars.has_key(u"url_encoded_fmt_stream_map"):
			# Attempt to see if YouTube has issued an error message
			if 'reason' not in flashvars:
				pc = False
				if 'ypc-offer-title' in videoinfo:
					pc = True
					msg = re.search('ypc-offer-title">.*?<a.*?">(.*?)</a', videoinfo, re.S)
					self.error = '[YoutubeURL] Error: Paid Content'
					if msg:
						self.error += ': "%s"' % msg.group(1)
				else:
					msg = re.search('class="message">(.*?)</', videoinfo, re.S)
					if msg:
						self.error = '[YoutubeURL] Error: %s' % msg.group(1).strip()
					else:
						self.error = '[YoutubeURL] Error: unable to extract "url_encoded_fmt_stream_map" parameter for unknown reason'
				if not pc and 'og:restrictions:age' in videoinfo:
					el = '&el=embedded'
					info_url = ('http://www.youtube.com/get_video_info?&video_id=%s%s&ps=default&eurl=&gl=US&hl=en' % (self.video_id, el))
					self.error = "[YoutubeURL] Error: Unable to retrieve videoinfo page:\n%s"
					self.yt_tw_agent_hlp.getWebPage(self.parseVInfo2, self.dataError, info_url, False)
					return
			else:
				reason = unquote_plus(videoinfo['reason'][0])
				self.error = '[YoutubeURL] Error: YouTube said: %s' % reason.decode('utf-8')

			self.errReturn(self.video_url)
		else:
			links = {}
			for url_desc in flashvars[u"url_encoded_fmt_stream_map"].split(u","):
				url_desc_map = parse_qs(url_desc)
				if not (url_desc_map.has_key(u"url") or url_desc_map.has_key(u"stream")):
					continue

				key = int(url_desc_map[u"itag"][0])
				url = u""

				if url_desc_map.has_key(u"url"):
					url = urllib.unquote(url_desc_map[u"url"][0])
				elif url_desc_map.has_key(u"conn") and url_desc_map.has_key(u"stream"):
					url = urllib.unquote(url_desc_map[u"conn"][0])
					if url.rfind("/") < len(url) -1:
						url = url + "/"
					url = url + urllib.unquote(url_desc_map[u"stream"][0])
				elif url_desc_map.has_key(u"stream") and not url_desc_map.has_key(u"conn"):
					url = urllib.unquote(url_desc_map[u"stream"][0])

				if url_desc_map.has_key(u"sig"):
					url = url + u"&signature=" + url_desc_map[u"sig"][0]
				elif url_desc_map.has_key(u"s"):
					sig = url_desc_map[u"s"][0]
					flashvars = self.extractFlashVars(videoinfo, 1)
					js = flashvars[u"js"]
					url = url + u"&signature=" + decryptor.decryptSignature(sig, js)

				try:
					links[self.VIDEO_FMT_PRIORITY_MAP[str(key)]] = url
				except KeyError:
					print 'skipping',key,'fmt not in priority videos'
					continue
			try:
				self.video_url = links[sorted(links.iterkeys())[0]].encode('utf-8')
				del self.yt_tw_agent_hlp
				self.callBack(self.video_url)
			except (KeyError,IndexError):
				self.error = "[YoutubeURL] Error: no video url found"
				self.errReturn(self.video_url)

	def parseVInfo2(self, videoinfo):
		videoinfo = parse_qs(videoinfo)
		if not videoinfo.has_key(u"url_encoded_fmt_stream_map"):
			self.error = '[YoutubeURL] Error: unable to extract "url_encoded_fmt_stream_map" parameter for unknown reason'
			self.errReturn(self.video_url)
		else:
			video_fmt_map = {}
			fmt_infomap = {}
			tmp_fmtUrlDATA = videoinfo['url_encoded_fmt_stream_map'][0].split(',')
			for fmtstring in tmp_fmtUrlDATA:
				fmturl = fmtid = fmtsig = ""
				if videoinfo.has_key('url_encoded_fmt_stream_map'):
					try:
						for arg in fmtstring.split('&'):
							if arg.find('=') >= 0:
								key, value = arg.split('=')
								if key == 'itag':
									if len(value) > 3:
										value = value[:2]
									fmtid = value
								elif key == 'url':
									fmturl = value
								elif key == 'sig':
									fmtsig = value

						if fmtid != "" and fmturl != "" and self.VIDEO_FMT_PRIORITY_MAP.has_key(fmtid):
							video_fmt_map[self.VIDEO_FMT_PRIORITY_MAP[fmtid]] = { 'fmtid': fmtid, 'fmturl': unquote_plus(fmturl), 'fmtsig': fmtsig }
							fmt_infomap[int(fmtid)] = "%s&signature=%s" %(unquote_plus(fmturl), fmtsig)
						fmturl = fmtid = fmtsig = ""

					except:
						self.error = "[YoutubeURL] Error parsing fmtstring: %s" % fmtstring
						self.errReturn(self.video_url)
						return

				else:
					(fmtid,fmturl) = fmtstring.split('|')

				if self.VIDEO_FMT_PRIORITY_MAP.has_key(fmtid) and fmtid != "":
					video_fmt_map[self.VIDEO_FMT_PRIORITY_MAP[fmtid]] = { 'fmtid': fmtid, 'fmturl': unquote_plus(fmturl) }
					fmt_infomap[int(fmtid)] = unquote_plus(fmturl)

			if video_fmt_map and len(video_fmt_map):
				print "[youtubeUrl] found best available video format:",video_fmt_map[sorted(video_fmt_map.iterkeys())[0]]['fmtid']
				best_video = video_fmt_map[sorted(video_fmt_map.iterkeys())[0]]
				if best_video['fmtsig']:
					self.video_url = "%s&signature=%s" %(best_video['fmturl'].split(';')[0], best_video['fmtsig'])
				else:
					self.video_url = "%s" %(best_video['fmturl'].split(';')[0])
				del self.yt_tw_agent_hlp
				self.callBack(self.video_url)
			else:
				self.error = "[YoutubeURL] Error: no video url found"
				self.errReturn(self.video_url)

	def removeAdditionalEndingDelimiter(self, data):
		pos = data.find("};")
		if pos != -1:
			data = data[:pos + 1]
		return data

	def extractFlashVars(self, data, assets):
		flashvars = {}
		found = False

		for line in data.split("\n"):
			if line.strip().find(";ytplayer.config = ") > 0:
				found = True
				p1 = line.find(";ytplayer.config = ") + len(";ytplayer.config = ") - 1
				p2 = line.rfind(";")
				if p1 <= 0 or p2 <= 0:
					continue
				data = line[p1 + 1:p2]
				break
		data = self.removeAdditionalEndingDelimiter(data)

		if found:
			data = json.loads(data)
			if assets:
				flashvars = data["assets"]
			else:
				flashvars = data["args"]
		return flashvars

# source from http://github.com/rg3/youtube-dl/issues/1208
class CVevoSignAlgoExtractor:
	# MAX RECURSION Depth for security
	MAX_REC_DEPTH = 5

	def __init__(self):
		from simple_lru_cache import SimpleLRUCache
		self.algoCache = SimpleLRUCache(5)

		self._cleanTmpVariables()

	def _cleanTmpVariables(self):
		self.fullAlgoCode = ''
		self.allLocalFunNamesTab = []
		self.playerData = ''

	def _jsToPy(self, jsFunBody):
		pythonFunBody = jsFunBody.replace('function', 'def').replace('{', ':\n\t').replace('}', '').replace(';', '\n\t').replace('var ', '')
		pythonFunBody = pythonFunBody.replace('.reverse()', '[::-1]')

		lines = pythonFunBody.split('\n')
		for i in range(len(lines)):
			# a.split("") -> list(a)
			match = re.search('(\w+?)\.split\(""\)', lines[i])
			if match:
				lines[i] = lines[i].replace( match.group(0), 'list(' + match.group(1)  + ')')
			# a.length -> len(a)
			match = re.search('(\w+?)\.length', lines[i])
			if match:
				lines[i] = lines[i].replace( match.group(0), 'len(' + match.group(1)  + ')')
			# a.slice(3) -> a[3:]
			match = re.search('(\w+?)\.slice\(([0-9]+?)\)', lines[i])
			if match:
				lines[i] = lines[i].replace( match.group(0), match.group(1) + ('[%s:]' % match.group(2)) )
			# a.join("") -> "".join(a)
			match = re.search('(\w+?)\.join\(("[^"]*?")\)', lines[i])
			if match:
				lines[i] = lines[i].replace( match.group(0), match.group(2) + '.join(' + match.group(1) + ')' )
		return "\n".join(lines)

	def _getLocalFunBody(self, funName):
		# get function body
		match = re.search('(function %s\([^)]+?\){[^}]+?})' % funName, self.playerData)
		if match:
			# return jsFunBody
			return match.group(1)
		return ''

	def _getAllLocalSubFunNames(self, mainFunBody):
		match = re.compile('[ =(,](\w+?)\([^)]*?\)').findall( mainFunBody )
		if len(match):
			# first item is name of main function, so omit it
			funNameTab = set( match[1:] )
			return funNameTab
		return set()

	def decryptSignature(self, s, playerUrl):
		print("decrypt_signature sign_len[%d] playerUrl[%s]" % (len(s), playerUrl) )

		# clear local data
		self._cleanTmpVariables()

		# use algoCache
		if playerUrl not in self.algoCache:
			# get player HTML 5 sript
			if not playerUrl.startswith('http'):
				url = 'http:' + playerUrl
			else:
				url = playerUrl

			request = urllib2.Request(url)
			try:
				self.playerData = urllib2.urlopen(request).read()
				self.playerData = self.playerData.decode('utf-8', 'ignore')
			except:
				print('Unable to download playerUrl webpage')
				return ''

			# get main function name
			match = re.search("signature=(\w+?)\([^)]\)", self.playerData)
			if match:
				mainFunName = match.group(1)
				print('Main signature function name = "%s"' % mainFunName)
			else:
				print('Can not get main signature function name')
				return ''

			self._getfullAlgoCode( mainFunName )

			# wrap all local algo function into one function extractedSignatureAlgo()
			algoLines = self.fullAlgoCode.split('\n')
			for i in range(len(algoLines)):
				algoLines[i] = '\t' + algoLines[i]
			self.fullAlgoCode  = 'def extractedSignatureAlgo(param):'
			self.fullAlgoCode += '\n'.join(algoLines)
			self.fullAlgoCode += '\n\treturn %s(param)' % mainFunName
			self.fullAlgoCode += '\noutSignature = extractedSignatureAlgo( inSignature )\n'

			# after this function we should have all needed code in self.fullAlgoCode

			print( "---------------------------------------" )
			print( "|    ALGO FOR SIGNATURE DECRYPTION    |" )
			print( "---------------------------------------" )
			print( self.fullAlgoCode                         )
			print( "---------------------------------------" )

			try:
				algoCodeObj = compile(self.fullAlgoCode, '', 'exec')
			except:
				print('decryptSignature compile algo code EXCEPTION')
				return ''
		else:
			# get algoCodeObj from algoCache
			print('Algo taken from cache')
			algoCodeObj = self.algoCache[playerUrl]

		# for security alow only flew python global function in algo code
		vGlobals = {"__builtins__": None, 'len': len, 'list': list}

		# local variable to pass encrypted sign and get decrypted sign
		vLocals = { 'inSignature': s, 'outSignature': '' }

		# execute prepared code
		try:
			exec( algoCodeObj, vGlobals, vLocals )
		except:
			print('decryptSignature exec code EXCEPTION')
			return ''

		print('Decrypted signature = [%s]' % vLocals['outSignature'])
		# if algo seems ok and not in cache, add it to cache
		if playerUrl not in self.algoCache and '' != vLocals['outSignature']:
			print('Algo from player [%s] added to cache' % playerUrl)
			self.algoCache[playerUrl] = algoCodeObj

		# free not needed data
		self._cleanTmpVariables()

		return vLocals['outSignature']

	# Note, this method is using a recursion
	def _getfullAlgoCode( self, mainFunName, recDepth = 0 ):
		if self.MAX_REC_DEPTH <= recDepth:
			print('_getfullAlgoCode: Maximum recursion depth exceeded')
			return

		funBody = self._getLocalFunBody( mainFunName )
		if '' != funBody:
			funNames = self._getAllLocalSubFunNames(funBody)
			if len(funNames):
				for funName in funNames:
					if funName not in self.allLocalFunNamesTab:
						self.allLocalFunNamesTab.append(funName)
						print("Add local function %s to known functions" % mainFunName)
						self._getfullAlgoCode( funName, recDepth + 1 )

			# conver code from javascript to python
			funBody = self._jsToPy(funBody)
			self.fullAlgoCode += '\n' + funBody + '\n'
		return

decryptor = CVevoSignAlgoExtractor()
