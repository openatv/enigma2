from urllib import unquote_plus
from twisted.web.client import getPage
from md5 import md5 # to encode password
from string import split, rstrip

from xml.dom.minidom import parseString

# for localized messages
from . import _

class LastFMEventRegister:
    def __init__(self):
        self.onMetadataChangedList = []
    
    def addOnMetadataChanged(self,callback):
        self.onMetadataChangedList.append(callback)

    def removeOnMetadataChanged(self,callback):
        self.onMetadataChangedList.remove(callback)
    
    def onMetadataChanged(self,metad):
        for i in self.onMetadataChangedList:
            i(metadata=metad)

lastfm_event_register = LastFMEventRegister()
            
class LastFMHandler:
    def __init__(self):
        pass
    def onPlaylistLoaded(self,reason):
        pass
    def onConnectSuccessful(self,reason):
        pass
    def onConnectFailed(self,reason):
        pass
    def onCommandFailed(self,reason):
        pass
    def onTrackSkiped(self,reason):
        pass
    def onTrackLoved(self,reason):
        pass
    def onTrackBanned(self,reason):
        pass
    def onGlobalTagsLoaded(self,tags):
        pass
    def onTopTracksLoaded(self,tracks):
        pass
    def onRecentTracksLoaded(self,tracks):
        pass
    def onRecentBannedTracksLoaded(self,tracks):
        pass
    def onRecentLovedTracksLoaded(self,tracks):
        pass
    def onNeighboursLoaded(self,user):
        pass
    def onFriendsLoaded(self,user):
        pass
    def onStationChanged(self,reason):
        pass    
    def onMetadataLoaded(self,metadata):
        pass

class LastFM(LastFMHandler):
    DEFAULT_NAMESPACES = (
        None, # RSS 0.91, 0.92, 0.93, 0.94, 2.0
        'http://purl.org/rss/1.0/', # RSS 1.0
        'http://my.netscape.com/rdf/simple/0.9/' # RSS 0.90
    )
    DUBLIN_CORE = ('http://purl.org/dc/elements/1.1/',)
    
    version = "1.0.1"
    platform = "linux"
    host = "ws.audioscrobbler.com"
    port = 80
    metadata = {}
    info={}
    cache_toptags= "/tmp/toptags"
    playlist = None
    
    def __init__(self):
        LastFMHandler.__init__(self)
        self.state = False # if logged in
                    
    def connect(self,username,password):
#        getPage(self.host,self.port
#                            ,"/radio/handshake.php?version=" + self.version + "&platform=" + self.platform + "&username=" + username + "&passwordmd5=" + self.hexify(md5(password).digest())
#                            ,callback=self.connectCB,errorback=self.onConnectFailed)
        url = "http://"+self.host+":"+str(self.port)+"/radio/handshake.php?version=" + self.version + "&platform=" + self.platform + "&username=" + username + "&passwordmd5=" + self.hexify(md5(password).digest())
        getPage(url).addCallback(self.connectCB).addErrback(self.onConnectFailed)

    def connectCB(self,data):
        self.info = self._parselines(data)
        if self.info.has_key("session"):
            self.lastfmsession = self.info["session"]
            if self.lastfmsession.startswith("FAILED"):
                self.onConnectFailed(self.info["msg"])
            else:
                self.streamurl = self.info["stream_url"]
                self.baseurl = self.info["base_url"]
                self.basepath = self.info["base_path"]
                self.subscriber = self.info["subscriber"]
                self.framehack = self.info["base_path"]
                self.state = True
                self.onConnectSuccessful("loggedin")
                
        else:
            self.onConnectFailed("login failed")
        
    def _parselines(self, str):
        res = {}
        vars = split(str, "\n")
        for v in vars:
            x = split(rstrip(v), "=", 1)
            if len(x) == 2:
                try:
                    res[x[0]] = x[1].encode("utf-8")
                except UnicodeDecodeError:
                    res[x[0]] = "unicodeproblem"
            elif x != [""]:
                print "(urk?", x, ")"
        return res

    def loadPlaylist(self):
        print "LOADING PLAYLIST"
        if self.state is not True:
            self.onCommandFailed("not logged in")
        else:
#            getPage(self.info["base_url"],80
#                            ,self.info["base_path"] + "/xspf.php?sk=" + self.info["session"]+"&discovery=0&desktop=1.3.1.1"
#                            ,callback=self.loadPlaylistCB,errorback=self.onCommandFailed)
            url = "http://"+self.info["base_url"]+":80"+self.info["base_path"] + "/xspf.php?sk=" + self.info["session"] + "&discovery=0&desktop=2.0"
            getPage(url).addCallback(self.loadPlaylistCB).addErrback(self.onCommandFailed)

    def loadPlaylistCB(self,xmlsource):
        self.playlist = LastFMPlaylist(xmlsource)
        self.onPlaylistLoaded("playlist loaded")
    
    def getPersonalURL(self,username,level=50):
        return "lastfm://user/%s/recommended/32"%username
    
    def getNeighboursURL(self,username):
        return "lastfm://user/%s/neighbours"%username

    def getLovedURL(self,username):
        return "lastfm://user/%s/loved"%username
    
    def getSimilarArtistsURL(self,artist=None):
        if artist is None and self.metadata.has_key('artist'):
            return "lastfm://artist/%s/similarartists"%self.metadata['artist'].replace(" ","%20")
        else:
            return "lastfm://artist/%s/similarartists"%artist.replace(" ","%20")

    def getArtistsLikedByFans(self,artist=None):
        if artist is None and self.metadata.has_key('artist'):
            return "lastfm://artist/%s/fans"%self.metadata['artist'].replace(" ","%20")
        else:
            return "lastfm://artist/%s/fans"%artist.replace(" ","%20")
    
    def getArtistGroup(self,artist=None):
        if artist is None and self.metadata.has_key('artist'):
            return "lastfm://group/%s"%self.metadata['artist'].replace(" ","%20")
        else:
            return "lastfm://group/%s"%artist.replace(" ","%20")
    def command(self, cmd,callback):
        # commands = skip, love, ban, rtp, nortp
        if self.state is not True:
            self.onCommandFailed("not logged in")
        else:
#            getPage(self.info["base_url"],80
#                            ,self.info["base_path"] + "/control.php?command=" + cmd + "&session=" + self.info["session"]
#                            ,callback=callback,errorback=self.onCommandFailed)
            url = "http://"+self.info["base_url"]+":80"+self.info["base_path"] + "/control.php?command=" + cmd + "&session=" + self.info["session"]
            getPage(url).addCallback(callback).addErrback(self.onCommandFailed)
 
    def onTrackLovedCB(self,response):
        res = self._parselines(response)
        if res["response"] == "OK":
            self.onTrackLoved("Track loved")
        else:
            self.onCommandFailed("Server returned FALSE")

    def onTrackBannedCB(self,response):
        res = self._parselines(response)
        if res["response"] == "OK":
            self.onTrackBanned("Track baned")
        else:
            self.onCommandFailed("Server returned FALSE")

    def onTrackSkipedCB(self,response):
        res = self._parselines(response)
        if res["response"] == "OK":
            self.onTrackSkiped("Track skiped")
        else:
            self.onCommandFailed("Server returned FALSE")
                        
    def love(self):
        return self.command("love",self.onTrackLovedCB)

    def ban(self):
        return self.command("ban",self.onTrackBannedCB)

    def skip(self):
        """unneeded"""
        return self.command("skip",self.onTrackSkipedCB)
    
    def hexify(self,s):
        result = ""
        for c in s:
            result = result + ("%02x" % ord(c))
        return result
    

    def XMLgetElementsByTagName( self, node, tagName, possibleNamespaces=DEFAULT_NAMESPACES ):
        for namespace in possibleNamespaces:
            children = node.getElementsByTagNameNS(namespace, tagName)
            if len(children): return children
        return []

    def XMLnode_data( self, node, tagName, possibleNamespaces=DEFAULT_NAMESPACES):
        children = self.XMLgetElementsByTagName(node, tagName, possibleNamespaces)
        node = len(children) and children[0] or None
        return node and "".join([child.data.encode("utf-8") for child in node.childNodes]) or None

    def XMLget_txt( self, node, tagName, default_txt="" ):
        return self.XMLnode_data( node, tagName ) or self.XMLnode_data( node, tagName, self.DUBLIN_CORE ) or default_txt

    def getGlobalTags( self ,force_reload=False):
        if self.state is not True:
            self.onCommandFailed("not logged in")
        else:
#            getPage(self.info["base_url"],80
#                            ,"/1.0/tag/toptags.xml"
#                            ,callback=self.getGlobalTagsCB,errorback=self.onCommandFailed)
            url = "http://"+self.info["base_url"]+":80"+"/1.0/tag/toptags.xml"
            getPage(url).addCallback(self.getGlobalTagsCB).addErrback(self.onCommandFailed)

    def getGlobalTagsCB(self,result):
        try:
            rssDocument = parseString(result)
            data =[]
            for node in self.XMLgetElementsByTagName(rssDocument, 'tag'):
                nodex={}
                nodex['_display'] = nodex['name'] = node.getAttribute("name").encode("utf-8")
                nodex['count'] =  node.getAttribute("count").encode("utf-8")
                nodex['stationurl'] = "lastfm://globaltags/"+node.getAttribute("name").encode("utf-8").replace(" ","%20")
                nodex['url'] =  node.getAttribute("url").encode("utf-8")
                data.append(nodex)
            self.onGlobalTagsLoaded(data)
        except xml.parsers.expat.ExpatError,e:
            self.onCommandFailed(e)

    def getTopTracks(self,username):
        if self.state is not True:
            self.onCommandFailed("not logged in")
        else:
#            getPage(self.info["base_url"],80
#                            ,"/1.0/user/%s/toptracks.xml"%username
#                            ,callback=self.getTopTracksCB,errorback=self.onCommandFailed)
            url = "http://"+self.info["base_url"]+"/1.0/user/"+username+"/toptracks.xml"
            getPage(url).addCallback(self.getTopTracksCB).addErrback(self.onCommandFailed)
           
    def getTopTracksCB(self,result):
        re,rdata = self._parseTracks(result)
        if re:
            self.onTopTracksLoaded(rdata)
        else:
            self.onCommandFailed(rdata)
            
    def getRecentTracks(self,username):
        if self.state is not True:
            self.onCommandFailed("not logged in")
        else:
#            getPage(self.info["base_url"],80
#                            ,"/1.0/user/%s/recenttracks.xml"%username
#                            ,callback=self.getRecentTracksCB,errorback=self.onCommandFailed)
            url = "http://"+self.info["base_url"]+"/1.0/user/"+username+"/recenttracks.xml"
            getPage(url).addCallback(self.getRecentTracksCB).addErrback(self.onCommandFailed)
           
    def getRecentTracksCB(self,result):
        re,rdata = self._parseTracks(result)
        if re:
            self.onRecentTracksLoaded(rdata)
        else:
            self.onCommandFailed(rdata)
    
    def getRecentLovedTracks(self,username):
        if self.state is not True:
            self.onCommandFailed("not logged in")
        else:
#            getPage(self.info["base_url"],80
#                            ,"/1.0/user/%s/recentlovedtracks.xml"%username
#                            ,callback=self.getRecentLovedTracksCB,errorback=self.onCommandFailed)
            url = "http://"+self.info["base_url"]+"/1.0/user/"+username+"/recentlovedtracks.xml"
            getPage(url).addCallback(self.getRecentLovedTracksCB).addErrback(self.onCommandFailed)
           
    def getRecentLovedTracksCB(self,result):
        re,rdata = self._parseTracks(result)
        if re:
            self.onRecentLovedTracksLoaded(rdata)
        else:
            self.onCommandFailed(rdata)

    def getRecentBannedTracks(self,username):
        if self.state is not True:
            self.onCommandFailed("not logged in")
        else:
#            getPage(self.info["base_url"],80
#                            ,"/1.0/user/%s/recentbannedtracks.xml"%username
#                            ,callback=self.getRecentBannedTracksCB,errorback=self.onCommandFailed)
            url = "http://"+self.info["base_url"]+"/1.0/user/"+username+"/recentbannedtracks.xml"
            getPage(url).addCallback(self.getRecentBannedTracksCB).addErrback(self.onCommandFailed)
           
    def getRecentBannedTracksCB(self,result):
        re,rdata = self._parseTracks(result)
        if re:
            self.onRecentBannedTracksLoaded(rdata)
        else:
            self.onCommandFailed(rdata)

    def _parseTracks(self,xmlrawdata):
        #print xmlrawdata
        try:
            rssDocument = parseString(xmlrawdata)
            data =[]
            for node in self.XMLgetElementsByTagName(rssDocument, 'track'):
                nodex={}
                nodex['name'] = self.XMLget_txt(node, "name", "N/A" )
                nodex['artist'] =  self.XMLget_txt(node, "artist", "N/A" )
                nodex['playcount'] = self.XMLget_txt(node, "playcount", "N/A" )
                nodex['stationurl'] =  "lastfm://artist/"+nodex['artist'].replace(" ","%20")+"/similarartists"#+nodex['name'].replace(" ","%20")
                nodex['url'] =  self.XMLget_txt(node, "url", "N/A" )
                nodex['_display'] = nodex['artist']+" - "+nodex['name']
                data.append(nodex)
            return True,data
        except xml.parsers.expat.ExpatError,e:
            print e
            return False,e

    def getNeighbours(self,username):
        if self.state is not True:
            self.onCommandFailed("not logged in")
        else:
#            getPage(self.info["base_url"],80
#                            ,"/1.0/user/%s/neighbours.xml"%username
#                            ,callback=self.getNeighboursCB,errorback=self.onCommandFailed)
            url = "http://"+self.info["base_url"]+"/1.0/user/"+username+"/neighbours.xml"
            getPage(url).addCallback(self.getNeighboursCB).addErrback(self.onCommandFailed)
           
    def getNeighboursCB(self,result):
        re,rdata = self._parseUser(result)
        if re:
            self.onNeighboursLoaded(rdata)
        else:
            self.onCommandFailed(rdata)

    def getFriends(self,username):
        if self.state is not True:
            self.onCommandFailed("not logged in")
        else:
#            getPage(self.info["base_url"],80
#                            ,"/1.0/user/%s/friends.xml"%username
#                            ,callback=self.getFriendsCB,errorback=self.onCommandFailed)
            url = "http://"+self.info["base_url"]+"/1.0/user/"+username+"/friends.xml"
            getPage(url).addCallback(self.getFriendsCB).addErrback(self.onCommandFailed)
           
    def getFriendsCB(self,result):
        re,rdata = self._parseUser(result)
        if re:
            self.onFriendsLoaded(rdata)
        else:
            self.onCommandFailed(rdata)


    def _parseUser(self,xmlrawdata):
        #print xmlrawdata
        try:
            rssDocument = parseString(xmlrawdata)
            data =[]
            for node in self.XMLgetElementsByTagName(rssDocument, 'user'):
                nodex={}
                nodex['name'] = node.getAttribute("username").encode("utf-8")
                nodex['url'] =  self.XMLget_txt(node, "url", "N/A" )
                nodex['stationurl'] =  "lastfm://user/"+nodex['name']+"/personal"
                nodex['_display'] = nodex['name']
                data.append(nodex)
            return True,data
        except xml.parsers.expat.ExpatError,e:
            print e
            return False,e

    def changeStation(self,url):
        if self.state is not True:
            self.onCommandFailed("not logged in")
        else:
#            getPage(self.info["base_url"],80
#                            ,self.info["base_path"] + "/adjust.php?session=" + self.info["session"] + "&url=" + url
#                            ,callback=self.changeStationCB,errorback=self.onCommandFailed)
            url = "http://"+self.info["base_url"]+":80"+self.info["base_path"] + "/adjust.php?session=" + self.info["session"] + "&url=" + url
            getPage(url).addCallback(self.changeStationCB).addErrback(self.onCommandFailed)
           
    def changeStationCB(self,result):
        res = self._parselines(result)
        if res["response"] == "OK":
            self.onStationChanged (_("Station changed"))
        else:
            self.onCommandFailed (_("Server returned") + " " +res["response"])

############
class LastFMPlaylist:
    """
        this is the new way last.fm handles streams with metadata
    """
    DEFAULT_NAMESPACES = (None,)
    DUBLIN_CORE = ('http://purl.org/dc/elements/1.1/',) #why do i need this?
    
    name = "N/A"
    creator = "N/A"
    tracks = []
    length = 0
    
    def __init__(self,xmlsource):
        self.xmldoc = parseString(xmlsource)
        self.name = unquote_plus(self._get_txt( self.xmldoc, "title", "no playlistname" ))
        self.creator =self._get_txt( self.xmldoc, "creator", "no playlistcreator" )
        self.parseTracks()

    def getTracks(self):
        return self.tracks

    def getTrack(self,tracknumber):
        try:
            return self.tracks[tracknumber]
        except IndexError:
            return False
    
    def parseTracks(self):
        try:
            self.tracks = []
            for node in self._getElementsByTagName(self.xmldoc, 'track'):
                nodex={}
                nodex['station'] =  self.name
                nodex['location'] =  self._get_txt( node, "location", "no location" )
                nodex['title'] =  self._get_txt( node, "title", "no title" )
                nodex['id'] =  self._get_txt( node, "id", "no id" )
                nodex['album'] =  self._get_txt( node, "album", "no album" )
                nodex['creator'] =  self._get_txt( node, "creator", "no creator" )
                nodex['duration'] =  int(self._get_txt( node, "duration", "0" ))
                nodex['image'] =  self._get_txt( node, "image", "no image" )
                self.tracks.append(nodex)
            self.length = len(self.tracks)
            return True
        except:
            return False
    
    def _getElementsByTagName( self, node, tagName, possibleNamespaces=DEFAULT_NAMESPACES ):
        for namespace in possibleNamespaces:
            children = node.getElementsByTagNameNS(namespace, tagName)
            if len(children): return children
        return []

    def _node_data( self, node, tagName, possibleNamespaces=DEFAULT_NAMESPACES):
        children = self._getElementsByTagName(node, tagName, possibleNamespaces)
        node = len(children) and children[0] or None
        return node and "".join([child.data.encode("utf-8") for child in node.childNodes]) or None

    def _get_txt( self, node, tagName, default_txt="" ):
        return self._node_data( node, tagName ) or self._node_data( node, tagName, self.DUBLIN_CORE ) or default_txt
