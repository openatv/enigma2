from enigma import eServiceReference
from enigma import iPlayableService
from Components.ServiceEventTracker import ServiceEventTracker
from twisted.internet import reactor
from time import time

# for localized messages
from . import _


class StreamPlayer:
    STATE_PLAYINGSTARTED = 0
    STATE_STOP = 1
    STATE_PLAYLISTENDS = 2
    is_playing = False
    trackstarttime = 0
    currentplaylistitemnumber = 0
    playlist = None
    onClose = []
    def __init__(self,session, args = 0):
        self.session = session
        self.oldService = self.session.nav.getCurrentlyPlayingServiceReference()
        self.onStateChanged = []
        self.__event_tracker = ServiceEventTracker(screen=self,eventmap=
            {
                iPlayableService.evStart: self.__onStart,
                iPlayableService.evEOF: self.__onStop,
            })
    def __onStart(self):
        self.trackstarttime = time()
    
    def __onStop(self):
        self.stop()
        
    def setSession(self,session):
        self.session = session
        
    def setPlaylist(self,playlist):
        if self.playlist is not None:
            self.currentplaylistitemnumber = 0 
        self.playlist = playlist
        
    def stateChanged(self,reason):
        for i in self.onStateChanged:
            i(reason)   

    def getRemaining(self):
        track = self.playlist.getTrack(self.currentplaylistitemnumber)
        if track is False:
            return "N/A"
        else:
            remaining = int((track["duration"]/1000) - (time() - self.trackstarttime))
            minutes = int(remaining/60)
            seconds = int(remaining-(minutes*60))
            def shiftchars(integer,char):
                if integer in range(0,10):
                    return char+str(integer)
                else:
                    return str(integer)
            return "-%s:%s"%(shiftchars(minutes," "), shiftchars(seconds,"0"))
    
    def play(self,tracknumber=False):
        if tracknumber is False:
            self.currentplaylistitemnumber = 0 
        else:
            self.currentplaylistitemnumber = tracknumber
        
        track = self.playlist.getTrack(self.currentplaylistitemnumber)
        if track is False:
            print "no track to play"
        elif track['location'] != "no location":
            print "playing item "+str(self.currentplaylistitemnumber) +"/"+str(self.playlist.length)+" with url ",track['location']
            reactor.callLater(1, self._delayedPlay, eServiceReference(4097,0,track['location']))
            self.is_playing = True

    def _delayedPlay(self,sref):
        if self.is_playing: # making sure, that no one presses stop while we had wait 
            self.session.nav.playService(sref)
    
    def skip(self):
        self.stop()
                
    def stop(self,text="",force=False):
        if self.playlist is None:
            self.is_playing = False
            self.stateChanged(self.STATE_STOP)
        elif force is False and self.playlist.length > 0 and (self.playlist.length-1) > self.currentplaylistitemnumber:
            self.play(tracknumber=self.currentplaylistitemnumber+1)
            self.stateChanged(self.STATE_PLAYINGSTARTED)
        elif self.is_playing is True and force is True:
            pass
            self.session.nav.playService(self.oldService)
            self.is_playing = False
            self.stateChanged(self.STATE_STOP)            
        else:
            self.stateChanged(self.STATE_PLAYLISTENDS)
            
    def exit(self):
        for x in self.onClose:
            x()
        self.stop()
    
    def getMetadata(self,key):
        try:
            track = self.playlist.getTrack(self.currentplaylistitemnumber)
            return track[key]
        except:
            return "N/A"