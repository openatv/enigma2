# kate: replace-tabs on; indent-width 4; remove-trailing-spaces all; show-tabs on; newline-at-eof on;
# -*- coding:utf-8 -*-

'''
Copyright (C) 2014 Peter Urbanec
All Right Reserved
License: Proprietary / Commercial - contact enigma.licensing (at) urbanec.net
'''

from enigma import eTimer, eEPGCache, eDVBDB, eServiceReference, iRecordableService
from boxbranding import getMachineBrand, getMachineName
from Components.ActionMap import ActionMap
from Components.ConfigList import ConfigListScreen
from Components.Label import Label
from Components.MenuList import MenuList
from Components.Pixmap import Pixmap
from Components.config import getConfigListEntry
from Components.Converter.genre import getGenreStringSub
from Plugins.Plugin import PluginDescriptor
from Screens.ChoiceBox import ChoiceBox
from Screens.MessageBox import MessageBox
from Screens.Screen import Screen
from RecordTimer import RecordTimerEntry
from ServiceReference import ServiceReference
from calendar import timegm
from time import strptime, gmtime, strftime, time
from datetime import datetime
from . import config, enableIceTV, disableIceTV
import API as ice
import requests
from collections import deque, defaultdict
from operator import itemgetter
from Screens.TextBox import TextBox
from Components.TimerSanityCheck import TimerSanityCheck
import NavigationInstance
from twisted.internet import reactor, threads

_session = None
password_requested = False

genre_remaps = {
    "AFL": 0xf7,
    "Action": 0x1f,
    "American Football": 0xf6,
    "Baseball": 0xf5,
    "Basketball": 0xf4,
    "Boxing": 0x4a,
    "Business & Finance": 0x84,
    "Cartoon": 0x51,
    "Comedy": 0xc0,
    "Cricket": 0x4f,
    "Current Affairs": 0x81,
    "Cycling": 0x0d,
    "Dance": 0x62,
    "Documentary": 0xe0,
    "Drama": 0xd0,
    "Family": 0x0c,
    "Fantasy": 0xf2,
    "Film-Noir": 0x0b,
    "Finance": 0x0a,
    "Fishing": 0xa3,
    "Food/Wine": 0xa4,
    "Golf": 0x42,
    "Hockey": 0x4e,
    "Horror": 0xf1,
    "Horse Racing": 0x09,
    "Lifestyle": 0xa2,
    "MMA": 0x08,
    "Mini Series": 0x07,
    "Murder": 0x1c,
    "Musical": 0x61,
    "Mystery": 0x1b,
    "Netball": 0x4d,
    "Parliament": 0x82,
    "Renovation": 0x06,
    "Rowing": 0xf8,
    "Rugby": 0x4c,
    "Rugby League": 0x4b,
    "Sailing": 0x05,
    "Science": 0x94,
    "Short Film": 0x04,
    "Sitcom": 0xf3,
    "Special": 0xb0,
    "Thriller": 0x1a,
    "War": 0x1e,
    "Western": 0x1d,
    "Wrestling": 0x03,
    "Youth": 0x02,
}

parental_ratings = {
    "": 0x00,
    "P": 0x02,
    "C": 0x04,
    "G": 0x06,
    "PG": 0x08,
    "M": 0x0a,
    "MA": 0x0c,
    "AV": 0x0e,
    "R": 0x0F,
    "TBA": 0x00,
}

def _logResponseException(logger, heading, exception):
    msg = heading
    if isinstance(exception, requests.exceptions.ConnectionError):
        msg += ": " + _("The IceTV server can not be reached. Try checking the Internet connection on your %s %s\nDetails") % (getMachineBrand(), getMachineName())
    msg += ": " + str(exception)
    if hasattr(exception, "response") and hasattr(exception.response, "text"):
        ex_text = str(exception.response.text).strip()
        if ex_text:
            msg += "\n" + ex_text
    logger.addLog(msg)
    return msg

class EPGFetcher(object):
    START_EVENTS = {
        iRecordableService.evStart,
    }
    END_EVENTS = {
        iRecordableService.evEnd,
        iRecordableService.evGstRecordEnded,
    }
    ERROR_EVENTS = {
        iRecordableService.evRecordWriteError,
    }
    EVENT_CODES = {
        iRecordableService.evStart: _("Recording started"),
        iRecordableService.evEnd: _("Recording finished"),
        iRecordableService.evTunedIn: _("Tuned for recording"),
        iRecordableService.evTuneFailed: _("Recording tuning failed"),
        iRecordableService.evRecordRunning: _("Recording running"),
        iRecordableService.evRecordStopped: _("Recording stopped"),
        iRecordableService.evNewProgramInfo: _("New program info"),
        iRecordableService.evRecordFailed: _("Recording failed"),
        iRecordableService.evRecordWriteError: _("Record write error (no space on disk?)"),
        iRecordableService.evNewEventInfo: _("New event info"),
        iRecordableService.evRecordAborted: _("Recording aborted"),
        iRecordableService.evGstRecordEnded: _("Streaming recording ended"),
    }
    ERROR_CODES = {
        iRecordableService.NoError: _("No error"),
        iRecordableService.errOpenRecordFile: _("Error opening recording file"),
        iRecordableService.errNoDemuxAvailable: _("No demux available"),
        iRecordableService.errNoTsRecorderAvailable: _("No TS recorder available"),
        iRecordableService.errDiskFull: _("Disk full"),
        iRecordableService.errTuneFailed: _("Recording tuning failed"),
        iRecordableService.errMisconfiguration: _("Misconfiguration in channel allocation"),
        iRecordableService.errNoResources: _("Can't allocate program source (e.g. tuner)"),
    }

    def __init__(self):
        self.fetch_timer = eTimer()
        self.fetch_timer.callback.append(self.createFetchJob)
        config.plugins.icetv.refresh_interval.addNotifier(self.freqChanged, initial_call=False, immediate_feedback=False)
        self.fetch_timer.start(int(config.plugins.icetv.refresh_interval.value) * 1000)
        self.log = deque(maxlen=40)
        # TODO: channel_service_map should probably be locked in case the user edits timers at the time of a fetch
        # Then again, the GIL may actually prevent issues here.
        self.channel_service_map = None

        # Status updates for timers that can't be processed at
        # the time that a status change is flagged (e.g. for instant
        # timers that don't initially have an IceTV id.
        self.deferred_status = defaultdict(list)

        # Timers that have failed, but where, when the iRecordableService
        # issues its evEnd event, the iRecordableService.getError()
        # returns NoError (for example, evRecordWriteError).
        self.failed = {}

        # Update status for timers that are already running at startup
        # Use id(None) for their key to differentiate them from deferred
        # updates for specific timers
        message = self.EVENT_CODES[iRecordableService.evStart]
        state = "running"
        for entry in _session.nav.RecordTimer.timer_list:
            if entry.record_service and self.shouldProcessTimer(entry):
                self.deferred_status[id(None)].append((entry, state, message, int(time())))

        _session.nav.RecordTimer.onTimerAdded.append(self.onTimerAdded)
        _session.nav.RecordTimer.onTimerRemoved.append(self.onTimerRemoved)
        _session.nav.RecordTimer.onTimerChanged.append(self.onTimerChanged)
        _session.nav.record_event.append(self.gotRecordEvent)
        self.addLog("IceTV started")

    def shouldProcessTimer(self, entry):
        if entry.isAutoTimer:
            return False
        if config.plugins.icetv.configured.value and config.plugins.icetv.enable_epg.value:
            global password_requested
            if password_requested:
                self.addLog("Can not proceed - you need to login first")
                return False
            else:
                return True
        else:
            # IceTV is not enabled
            return False

    def onTimerAdded(self, entry):
        # print "[IceTV] timer added: ", entry
        if not self.shouldProcessTimer(entry):
            return
        # print "[IceTV] Add timer job"
        reactor.callInThread(self.postTimer, entry)

    def onTimerRemoved(self, entry):
        # print "[IceTV] timer removed: ", entry
        if not self.shouldProcessTimer(entry) or not entry.ice_timer_id:
            return
        # print "[IceTV] Delete timer job"
        reactor.callInThread(self.deleteTimer, entry.ice_timer_id)

    def onTimerChanged(self, entry):
        # print "[IceTV] timer changed: ", entry

        # If entry.cancelled is True, the timer is being deleted
        # and will be processed by a subsequent onTimerRemoved() call

        if not self.shouldProcessTimer(entry) or entry.cancelled:
            return
        if entry.end <= entry.begin:
            self.onTimerRemoved(entry)
            return
        if entry.ice_timer_id is None:
            # New timer as far as IceTV is concerned
            # print "[IceTV] Add timer job"
            reactor.callInThread(self.postTimer, entry)
        else:
            # print "[IceTV] Modify timer jobs"
            ice_timer_id = entry.ice_timer_id
            entry.ice_timer_id = None
            # Delete the timer on the IceTV side, then post the new one
            # print "[IceTV] Modify timer jobs - delete timer job"
            d = threads.deferToThread(lambda: self.deleteTimer(ice_timer_id))
            d.addCallback(lambda x: self.deferredPostTimer(entry))

    def gotRecordEvent(self, rec_service, event):
        if event not in self.START_EVENTS and event not in self.END_EVENTS and event not in self.ERROR_EVENTS:
            return

        rec_service_id = rec_service.getPtrString()
        rec_timer = None
        for entry in _session.nav.RecordTimer.timer_list:
            if entry.record_service and entry.record_service.getPtrString() == rec_service_id and self.shouldProcessTimer(entry):
                rec_timer = entry
                break

        if rec_timer:
            self.processEvent(rec_timer, event, rec_service.getError())

    def processEvent(self, entry, event, err):
        state = None
        message = None
        if err != iRecordableService.NoError and (event in self.START_EVENTS or event in self.END_EVENTS):
            state = "failed"
            message = self.EVENT_CODES[iRecordableService.evRecordFailed]
        elif event in self.START_EVENTS:
            state = "running" if err == iRecordableService.NoError else "failed"
        elif event in self.END_EVENTS:
            if err == iRecordableService.NoError and id(event) not in self.failed:
                state = "completed"
            else:
                state = "failed"
                if id(event) in self.failed:
                    del self.failed[id(event)]
        elif event in self.ERROR_EVENTS:
            state = "failed"
            if event == evRecordWriteError and id(event) not in self.failed:
                # use same structure as deferred_status to simplify cleanup
                # Hold otherwise unused reference to entry so
                # that id(entry) remains valid
                self.failed[id(event)] = [(event, int(time()))]

        if state:
            if not message:
                message = self.EVENT_CODES.get(event, _("Unknown recording event"))
            if err != iRecordableService.NoError:
                message += ": %s" % self.ERROR_CODES.get(err, _("Unknown error code"))
            if entry.ice_timer_id:
                reactor.callInThread(self.postStatus, entry, state, message)
            else:
                # Timer started before IceTV timer is assigned
                self.deferred_status[id(entry)].append((entry, state, message, int(time())))

    def statusCleanup(self):
        def doTimeouts(status, timeout):
            for tid, worklist in status.items():
                if worklist and min(worklist, key=itemgetter(-1))[-1] < timeout:
                    status[tid] = [ent for ent in worklist if ent[-1] >= timeout]
                    if not status[tid]:
                        del status[tid]

        now = int(time())
        old24h = now - 24 * 60 * 60  # recordings don't run more tha 24 hours
        doTimeouts(self.deferred_status, old24h)
        doTimeouts(self.failed, old24h)

    def deferredPostTimer(self, entry):
        # print "[IceTV] Modify timer jobs - add timer job"
        reactor.callInThread(self.postTimer, entry)

    def deferredPostStatus(self, entry):
        tid = id(entry)
        if tid in self.deferred_status:
            reactor.callInThread(self.postStatus, *self.deferred_status[tid].pop(0)[0:3])
            if not self.deferred_status[tid]:
                del self.deferred_status[tid]

    def freqChanged(self, refresh_interval):
        self.fetch_timer.stop()
        self.fetch_timer.start(int(refresh_interval.value) * 1000)

    def addLog(self, msg):
        logMsg = "%s: %s" % (str(datetime.now()).split(".")[0], msg)
        self.log.append(logMsg)
        print "[IceTV]", logMsg

    def createFetchJob(self, res=None):
        if config.plugins.icetv.configured.value and config.plugins.icetv.enable_epg.value:
            global password_requested
            if password_requested:
                self.addLog("Can not proceed - you need to login first")
                return
            # print "[IceTV] Create fetch job"
            reactor.callInThread(self.doWork)

    def doWork(self):
        global password_requested
        self.addLog("Start update")
        if password_requested:
            self.addLog("Can not proceed - you need to login first")
            return False
        if not ice.haveCredentials():
            password_requested = True
            self.addLog("No token, requesting password...")
            _session.open(IceTVNeedPassword)
            if not ice.haveCredentials():
                return False
        res = True
        try:
            self.channel_service_map = self.makeChanServMap(self.getChannels())
        except (Exception) as ex:
            _logResponseException(self, _("Can not retrieve channel map"), ex)
            return False
        try:
            shows = self.getShows()
            channel_show_map = self.makeChanShowMap(shows["shows"])
            epgcache = eEPGCache.getInstance()
            for channel_id in channel_show_map.keys():
                if channel_id in self.channel_service_map:
                    epgcache.importEvents(self.channel_service_map[channel_id], channel_show_map[channel_id])
            epgcache.save()
            if "last_update_time" in shows:
                config.plugins.icetv.last_update_time.value = shows["last_update_time"]
            self.addLog("EPG download OK")
            if self.updateDescriptions(channel_show_map):
                NavigationInstance.instance.RecordTimer.saveTimer()
            if "timers" in shows:
                res = self.processTimers(shows["timers"])
            self.addLog("End update")
            self.deferredPostStatus(None)
            self.statusCleanup()
            return res
        except (IOError, RuntimeError) as ex:
            if hasattr(ex, "response") and hasattr(ex.response, "status_code") and ex.response.status_code == 404:
                # Ignore 404s when there are no EPG updates - buggy server
                self.addLog("No EPG updates")
            else:
                _logResponseException(self, _("Can not download EPG"), ex)
                res = False
        try:
            ice_timers = self.getTimers()
            if not self.processTimers(ice_timers):
                res = False
            self.addLog("End update")
        except (Exception) as ex:
            _logResponseException(self, _("Can not download timers"), ex)
            res = False
        if not ice.haveCredentials() and not password_requested:
            password_requested = True
            self.addLog("No token, requesting password...")
            _session.open(IceTVNeedPassword)
        return res

    def makeChanServMap(self, channels):
        res = defaultdict(list)
        for channel in channels:
            channel_id = long(channel["id"])
            triplets = []
            if "dvb_triplets" in channel:
                triplets = channel["dvb_triplets"]
            elif "dvbt_info" in channel:
                triplets = channel["dvbt_info"]
            for triplet in triplets:
                res[channel_id].append(
                    (int(triplet["original_network_id"]),
                     int(triplet["transport_stream_id"]),
                     int(triplet["service_id"])))
        return res

    def serviceToIceChannelId(self, serviceref):
        svc = str(serviceref).split(":")
        triplet = (int(svc[5], 16), int(svc[4], 16), int(svc[3], 16))
        for channel_id, dvbt in self.channel_service_map.iteritems():
            if triplet in dvbt:
                return channel_id

    def makeChanShowMap(self, shows):
        res = defaultdict(list)
        for show in shows:
            channel_id = long(show["channel_id"])
            event_id = int(show.get("eit_id"))
            if event_id is None:
                event_id = ice.showIdToEventId(show["id"])
            if event_id <= 0:
                event_id = None
            if "deleted_record" in show and int(show["deleted_record"]) == 1:
                start = 999
                duration = 10
            else:
                start = int(timegm(strptime(show["start"].split("+")[0], "%Y-%m-%dT%H:%M:%S")))
                stop = int(timegm(strptime(show["stop"].split("+")[0], "%Y-%m-%dT%H:%M:%S")))
                duration = stop - start
            title = show.get("title", "").encode("utf8")
            short = show.get("subtitle", "").encode("utf8")
            extended = show.get("desc", "").encode("utf8")
            genres = []
            for g in show.get("category", []):
                name = g['name']
                eit = int(g["eit"], 0) or 0x01
                eit_remap = genre_remaps.get(name, eit)
                mapped_name = getGenreStringSub((eit_remap >> 4) & 0xf, eit_remap & 0xf, country="AUS")
                if mapped_name == name:
                        genres.append(eit_remap)
                else:
                    print '[EPGFetcher] ERROR: lookup of 0x%02x%s "%s" returned \"%s"' % (eit, (" (remapped to 0x%02x)" % eit_remap) if eit != eit_remap else "", name, mapped_name)
            p_rating = (("AUS", parental_ratings.get(show.get("rating", "").encode("utf8"), 0x00)),)
            res[channel_id].append((start, duration, title, short, extended, genres, event_id, p_rating))
        return res

    def updateDescriptions(self, showMap):

        # Emulate what the XML parser does to CR and LF in attributes
        def attrNewlines(s):
            return s.replace("\r\n", ' ').replace('\r', ' ').replace('\n', ' ') if '\r' in s or '\n' in s else s

        updated = False
        if not showMap:
            return updated
        for timer in _session.nav.RecordTimer.timer_list:
            if timer.ice_timer_id and timer.service_ref.ref and not getattr(timer, "record_service", None):
                evt = timer.getEventFromEPGId() or timer.getEventFromEPG()
                if evt:
                    timer_updated = False
                    # servicename = timer.service_ref.getServiceName()
                    desc = attrNewlines(evt.getShortDescription())
                    if not desc:
                        desc = attrNewlines(evt.getExtendedDescription())
                    if desc and timer.description != desc and attrNewlines(timer.description) != desc:
                            # print "[EPGFetcher] updateDescriptions from EPG description", servicename, "'" + timer.name + "':", "'" + timer.description + "' -> '" + desc + "'"
                            timer.description = desc
                            timer_updated = True
                    eit = evt.getEventId()
                    if eit and timer.eit != eit:
                            # print "[EPGFetcher] updateDescriptions from EPG eit", servicename, "'" + timer.name + "':", timer.eit, "->", eit
                            timer.eit = eit
                            timer_updated = True
                    if timer_updated:
                        self.addLog("Update timer details from EPG '" + timer.name + "'")
                    updated |= timer_updated
        return updated

    def processTimers(self, timers):
        update_queue = []
        for iceTimer in timers:
            # print "[IceTV] iceTimer:", iceTimer
            try:
                action = iceTimer.get("action", "").encode("utf8")
                state = iceTimer.get("state", "").encode("utf8")
                name = iceTimer.get("name", "").encode("utf8")
                start = int(timegm(strptime(iceTimer["start_time"].split("+")[0], "%Y-%m-%dT%H:%M:%S")))
                duration = 60 * int(iceTimer["duration_minutes"])
                channel_id = long(iceTimer["channel_id"])
                ice_timer_id = iceTimer["id"].encode("utf8")
                if action == "forget":
                    for timer in _session.nav.RecordTimer.timer_list:
                        if timer.ice_timer_id == ice_timer_id:
                            # print "[IceTV] removing timer:", timer
                            _session.nav.RecordTimer.removeEntry(timer)
                            break
                    else:
                        self.deleteTimer(ice_timer_id)
                elif state == "completed":
                    continue    # Completely ignore completed timers - the server should not be sending those back to us anyway.
                elif channel_id in self.channel_service_map:
                    completed = False
                    for timer in _session.nav.RecordTimer.processed_timers:
                        if timer.ice_timer_id == ice_timer_id:
                            # print "[IceTV] completed timer:", timer
                            iceTimer["state"] = "completed"
                            iceTimer["message"] = "Done"
                            update_queue.append(iceTimer)
                            completed = True
                    updated = False
                    if not completed:
                        for timer in _session.nav.RecordTimer.timer_list:
                            if timer.ice_timer_id == ice_timer_id:
                                # print "[IceTV] updating timer:", timer
                                eit = int(iceTimer.get("eit_id", -1))
                                if eit <= 0:
                                    eit = None
                                if self.updateTimer(timer, name, start - config.recording.margin_before.value * 60, start + duration + config.recording.margin_after.value * 60, eit, self.channel_service_map[channel_id]):
                                    if not self.modifyTimer(timer):
                                        iceTimer["state"] = "failed"
                                        iceTimer["message"] = "Failed to update timer '%s'" % name
                                        update_queue.append(iceTimer)
                                        self.addLog("Failed to update timer '%s" % name)
                                else:
                                    self.onTimerChanged(timer)
                                updated = True
                    created = False
                    if not completed and not updated:
                        channels = self.channel_service_map[channel_id]
                        # print "[IceTV] channel_id %s maps to" % channel_id, channels
                        db = eDVBDB.getInstance()
                        # Sentinel values used if there are no channel matches
                        iceTimer["state"] = "failed"
                        iceTimer["message"] = "No matching service"
                        for channel in channels:
                            serviceref = db.searchReference(channel[1], channel[0], channel[2])
                            if serviceref.valid():
                                serviceref = ServiceReference(eServiceReference(serviceref))
                                # print "[IceTV] New %s is valid" % str(serviceref), serviceref.getServiceName()
                                eit = int(iceTimer.get("eit_id", -1))
                                if eit <= 0:
                                    eit = None
                                recording = RecordTimerEntry(serviceref, start - config.recording.margin_before.value * 60, start + duration + config.recording.margin_after.value * 60, name, "", eit, ice_timer_id=ice_timer_id)
                                conflicts = _session.nav.RecordTimer.record(recording)
                                if conflicts is None:
                                    iceTimer["state"] = "pending"
                                    iceTimer["message"] = "Added"
                                    created = True
                                    break
                                else:
                                    names = [r.name for r in conflicts]
                                    iceTimer["state"] = "failed"
                                    iceTimer["message"] = "Timer conflict: '%s'" % "', '".join(names)
                                    # print "[IceTV] Timer conflict:", conflicts
                                    self.addLog("Timer '%s' conflicts with %s" % (name, "', '".join([n for n in names if n != name])))
                    if not completed and not updated and not created:
                        iceTimer["state"] = "failed"
                        update_queue.append(iceTimer)
                else:
                    iceTimer["state"] = "failed"
                    iceTimer["message"] = "No valid service mapping for channel_id %d" % channel_id
                    update_queue.append(iceTimer)
            except (IOError, RuntimeError, KeyError) as ex:
                print "[IceTV] Can not process iceTimer:", ex
        # Send back updated timer states
        res = True
        try:
            self.putTimers(update_queue)
            self.addLog("Timers updated OK")
        except KeyError as ex:
            print "[IceTV] ", str(ex)
            res = False
        except (IOError, RuntimeError) as ex:
            _logResponseException(self, _("Can not update timers"), ex)
            res = False
        return res

    def isIceTimerInUpdateQueue(self, iceTimer, update_queue):
        ice_timer_id = iceTimer["id"].encode("utf8")
        for timer in update_queue:
            if ice_timer_id == timer["id"].encode("utf8"):
                return True
        return False

    def isIceTimerInLocalTimerList(self, iceTimer, ignoreCompleted=False):
        ice_timer_id = iceTimer["id"].encode("utf8")
        for timer in _session.nav.RecordTimer.timer_list:
            if timer.ice_timer_id == ice_timer_id:
                return True
        if not ignoreCompleted:
            for timer in _session.nav.RecordTimer.processed_timers:
                if timer.ice_timer_id == ice_timer_id:
                    return True
        return False

    def updateTimer(self, timer, name, start, end, eit, channels):
        changed = False
        db = eDVBDB.getInstance()
        for channel in channels:
            serviceref = db.searchReference(channel[1], channel[0], channel[2])
            if serviceref.valid():
                serviceref = ServiceReference(eServiceReference(serviceref))
                # print "[IceTV] Updated %s is valid" % str(serviceref), serviceref.getServiceName()
                if str(timer.service_ref) != str(serviceref):
                    changed = True
                    timer.service_ref = serviceref
                break
        if name and timer.name != name:
            changed = True
            timer.name = name
        if timer.begin != start:
            changed = True
            timer.begin = start
        if timer.end != end:
            changed = True
            timer.end = end
        if eit and timer.eit != eit:
            changed = True
            timer.eit = eit
        return changed

    def modifyTimer(self, timer):
        timersanitycheck = TimerSanityCheck(_session.nav.RecordTimer.timer_list, timer)
        success = False
        if not timersanitycheck.check():
            simulTimerList = timersanitycheck.getSimulTimerList()
            if simulTimerList is not None:
                for x in simulTimerList:
                    if x.setAutoincreaseEnd(timer):
                        self.session.nav.RecordTimer.timeChanged(x)
                if timersanitycheck.check():
                    success = True
        else:
            success = True
        if success:
            _session.nav.RecordTimer.timeChanged(timer)
        return success

    def getShows(self):
        req = ice.Shows()
        last_update = config.plugins.icetv.last_update_time.value
        req.params["last_update_time"] = last_update
        return req.get().json()

    def getChannels(self):
        req = ice.Channels(config.plugins.icetv.member.region_id.value)
        res = req.get().json()
        return res.get("channels", [])

    def getTimers(self):
        req = ice.Timers()
        res = req.get().json()
        return res.get("timers", [])

    def putTimers(self, timers):
        if timers:
            req = ice.Timers()
            req.data["timers"] = timers
            res = req.put().json()
            return res.get("timers", [])
        return []

    def putTimer(self, local_timer):
        try:
            # print "[IceTV] updating ice_timer", local_timer.ice_timer_id
            req = ice.Timer(local_timer.ice_timer_id)
            timer = {}
            if not local_timer.eit:
                self.addLog("Timer '%s' has no event id; update not sent to IceTV" % local_timer.name)
                return
            timer["id"] = local_timer.ice_timer_id
            timer["eit_id"] = local_timer.eit
            timer["start_time"] = strftime("%Y-%m-%dT%H:%M:%S+00:00", gmtime(local_timer.begin + config.recording.margin_before.value * 60))
            timer["duration_minutes"] = ((local_timer.end - config.recording.margin_after.value * 60) - (local_timer.begin + config.recording.margin_before.value * 60)) / 60
            if local_timer.isRunning():
                timer["state"] = "running"
                timer["message"] = "Recording on %s" % config.plugins.icetv.device.label.value
            elif local_timer.state == RecordTimerEntry.StateEnded:
                timer["state"] = "completed"
                timer["message"] = "Recorded on %s" % config.plugins.icetv.device.label.value
            elif local_timer.state == RecordTimerEntry.StateFailed:
                timer["state"] = "failed"
                timer["message"] = "Failed to record"
            else:
                timer["state"] = "pending"
                timer["message"] = "Will record on %s" % config.plugins.icetv.device.label.value
            req.data["timers"] = [timer]
            res = req.put().json()
            self.addLog("Timer '%s' updated OK" % local_timer.name)
        except (IOError, RuntimeError, KeyError) as ex:
            _logResponseException(self, _("Can not update timer"), ex)

    def postTimer(self, local_timer):
        if self.channel_service_map is None:
            try:
                self.channel_service_map = self.makeChanServMap(self.getChannels())
            except (IOError, RuntimeError, KeyError) as ex:
                _logResponseException(self, _("Can not retrieve channel map"), ex)
                return
        if local_timer.ice_timer_id is None:
            try:
                # print "[IceTV] uploading new timer"
                if not local_timer.eit:
                    self.addLog("Timer '%s' has no event id; not sent to IceTV" % local_timer.name)
                    return
                channel_id = self.serviceToIceChannelId(local_timer.service_ref)
                req = ice.Timers()
                req.data["eit_id"] = local_timer.eit
                req.data["name"] = local_timer.name
                req.data["message"] = "Created by %s" % config.plugins.icetv.device.label.value
                req.data["action"] = "record"
                if local_timer.isRunning():
                    req.data["state"] = "running"
                else:
                    req.data["state"] = "pending"
                req.data["device_id"] = config.plugins.icetv.device.id.value
                req.data["channel_id"] = channel_id
                req.data["start_time"] = strftime("%Y-%m-%dT%H:%M:%S+00:00", gmtime(local_timer.begin + config.recording.margin_before.value * 60))
                req.data["duration_minutes"] = ((local_timer.end - config.recording.margin_after.value * 60) - (local_timer.begin + config.recording.margin_before.value * 60)) / 60
                res = req.post()
                try:
                    local_timer.ice_timer_id = res.json()["timers"][0]["id"].encode("utf8")
                    self.addLog("Timer '%s' created OK" % local_timer.name)
                    if local_timer.ice_timer_id is not None:
                        NavigationInstance.instance.RecordTimer.saveTimer()
                        self.deferredPostStatus(local_timer)
                except:
                    self.addLog("Couldn't get IceTV timer id for timer '%s'" % local_timer.name)

            except (IOError, RuntimeError, KeyError) as ex:
                _logResponseException(self, _("Can not upload timer"), ex)
        else:
            # Looks like a timer just added by IceTV, so this is an update
            self.putTimer(local_timer)

    def deleteTimer(self, ice_timer_id):
        try:
            # print "[IceTV] deleting timer:", ice_timer_id
            req = ice.Timer(ice_timer_id)
            req.delete()
            self.addLog("Timer deleted OK")
        except (IOError, RuntimeError, KeyError) as ex:
            _logResponseException(self, _("Can not delete timer"), ex)

    def postStatus(self, timer, state, message):
        try:
            channel_id = self.serviceToIceChannelId(timer.service_ref)
            req = ice.Timer(timer.ice_timer_id)
            req.data["message"] = message
            req.data["state"] = state
            print "[EPGFetcher] postStatus", timer.name, message, state
            res = req.put()
        except (IOError, RuntimeError, KeyError) as ex:
            _logResponseException(self, _("Can not update timer status"), ex)
        self.deferredPostStatus(timer)

fetcher = None

def sessionstart_main(reason, session, **kwargs):
    global _session
    global fetcher
    if reason == 0:
        if _session is None:
            _session = session
        if fetcher is None:
            fetcher = EPGFetcher()
        fetcher.createFetchJob()
    elif reason == 1:
        _session = None
        fetcher.fetch_timer.stop()
        fetcher = None


def plugin_main(session, **kwargs):
    global _session
    global fetcher
    if _session is None:
        _session = session
    if fetcher is None:
        fetcher = EPGFetcher()
    session.open(IceTVMain)

def Plugins(**kwargs):
    res = []
    res.append(
        PluginDescriptor(
            name="IceTV",
            where=PluginDescriptor.WHERE_SESSIONSTART,
            description=_("IceTV"),
            fnc=sessionstart_main,
            needsRestart=True
        ))
    res.append(
        PluginDescriptor(
            name="IceTV",
            where=PluginDescriptor.WHERE_PLUGINMENU,
            description=_("IceTV version %s") % ice._version_string,
            icon="icon.png",
            fnc=plugin_main
        ))
    return res


class IceTVMain(ChoiceBox):
    def __init__(self, session, *args, **kwargs):
        global _session
        if _session is None:
            _session = session
        menu = [
                ("Show log", "CALLFUNC", self.showLog),
                ("Fetch EPG and update timers now", "CALLFUNC", self.fetch),
                ("IceTV setup wizard", "CALLFUNC", self.configure),
                ("Login to IceTV server", "CALLFUNC", self.login),
                ("Enable IceTV", "CALLFUNC", self.enable),
                ("Disable IceTV", "CALLFUNC", self.disable),
               ]
        super(IceTVMain, self).__init__(session, title=_("IceTV version %s") % ice._version_string, list=menu)
        self["debugactions"] = ActionMap(
            contexts=["DirectionActions"],
            actions={
                 "chplus": self.increaseDebug,
                 "chminus": self.decreaseDebug,
            }, prio=-1)

    def increaseDebug(self):
        if ice._debug_level < 4:
            ice._debug_level += 1
        print "[IceTV] debug level =", ice._debug_level

    def decreaseDebug(self):
        if ice._debug_level > 0:
            ice._debug_level -= 1
        print "[IceTV] debug level =", ice._debug_level

    def enable(self, res=None):
        enableIceTV()
        _session.open(MessageBox, _("IceTV enabled"), type=MessageBox.TYPE_INFO, timeout=5)

    def disable(self, res=None):
        disableIceTV()
        _session.open(MessageBox, _("IceTV disabled"), type=MessageBox.TYPE_INFO, timeout=5)

    def configure(self, res=None):
        _session.open(IceTVUserTypeScreen)

    def fetch(self, res=None):
        try:
            if fetcher.doWork():
                _session.open(MessageBox, _("IceTV update completed OK"), type=MessageBox.TYPE_INFO, timeout=5)
                return
        except (Exception) as ex:
            fetcher.addLog("Error trying to fetch: %s" % str(ex))
        _session.open(MessageBox, _("IceTV update completed with errors.\n\nPlease check the log for details."), type=MessageBox.TYPE_ERROR, timeout=15)

    def login(self, res=None):
        _session.open(IceTVNeedPassword)

    def showLog(self, res=None):
        _session.open(IceTVLogView, "\n".join(fetcher.log))


class IceTVLogView(TextBox):
    skin = """<screen name="IceTVLogView" backgroundColor="background" position="90,150" size="1100,450" title="Log">
        <widget font="Console;18" name="text" position="0,4" size="1100,446"/>
</screen>"""


class IceTVUserTypeScreen(Screen):
    skin = """
<screen name="IceTVUserTypeScreen" position="320,130" size="640,400" title="IceTV - Account selection" >
 <widget position="20,20" size="600,40" name="title" font="Regular;32" />
 <widget position="20,80" size="600,200" name="instructions" font="Regular;22" />
 <widget position="20,300" size="600,100" name="menu" />
</screen>
"""
    _instructions = _("In order to allow you to access all the features of the "
                      "IceTV smart recording service, we need to gather some "
                      "basic information.\n\n"
                      "If you already have an IceTV subscription or trial, please select "
                      "'Existing or trial user', if not, then select 'New user'.")

    def __init__(self, session):
        self.session = session
        Screen.__init__(self, session)
        self["title"] = Label(_("Welcome to IceTV"))
        self["instructions"] = Label(_(self._instructions))
        options = []
        options.append((_("New user"), "newUser"))
        options.append((_("Existing or trial user"), "oldUser"))
        self["menu"] = MenuList(options)
        self["aMap"] = ActionMap(contexts=["OkCancelActions", "DirectionActions"],
                                 actions={
                                     "cancel": self.cancel,
                                     "ok": self.ok,
                                 }, prio=-1)

    def cancel(self):
        self.close(False)

    def ok(self):
        selection = self["menu"].getCurrent()
        if selection[1] == "newUser":
            self.session.openWithCallback(self.userDone, IceTVNewUserSetup)
        elif selection[1] == "oldUser":
            self.session.openWithCallback(self.userDone, IceTVOldUserSetup)

    def userDone(self, success):
        if success:
            self.close(True)

class IceTVNewUserSetup(ConfigListScreen, Screen):
    skin = """
<screen name="IceTVNewUserSetup" position="320,230" size="640,310" title="IceTV - User Information" >
    <widget name="instructions" position="20,10" size="600,100" font="Regular;22" />
    <widget name="config" position="20,120" size="600,100" />

    <widget name="description" position="20,e-90" size="600,60" font="Regular;18" foregroundColor="grey" halign="left" valign="top" />
    <ePixmap name="red" position="20,e-28" size="15,16" pixmap="skin_default/buttons/button_red.png" alphatest="blend" />
    <ePixmap name="green" position="170,e-28" size="15,16" pixmap="skin_default/buttons/button_green.png" alphatest="blend" />
    <ePixmap name="blue" position="470,e-28" size="15,16" pixmap="skin_default/buttons/button_blue.png" alphatest="blend" />
    <widget name="key_red" position="40,e-30" size="150,25" valign="top" halign="left" font="Regular;20" />
    <widget name="key_green" position="190,e-30" size="150,25" valign="top" halign="left" font="Regular;20" />
    <widget name="key_yellow" position="340,e-30" size="150,25" valign="top" halign="left" font="Regular;20" />
    <widget name="key_blue" position="490,e-30" size="150,25" valign="top" halign="left" font="Regular;20" />
</screen>"""

    _instructions = _("Please enter your email address. This is required for us to send you "
                      "service announcements, account reminders, promotional offers and "
                      "a welcome email.")
    _email = _("Email")
    _password = _("Password")
    _label = _("Label")
    _update_interval = _("Connect to IceTV server every")

    def __init__(self, session):
        self.session = session
        Screen.__init__(self, session)
        self["instructions"] = Label(self._instructions)
        self["description"] = Label()
        self["HelpWindow"] = Label()
        self["key_red"] = Label(_("Cancel"))
        self["key_green"] = Label(_("Save"))
        self["key_yellow"] = Label()
        self["key_blue"] = Label(_("Keyboard"))
        self.list = [
             getConfigListEntry(self._email, config.plugins.icetv.member.email_address,
                                _("Your email address is used to login to IceTV services.")),
             getConfigListEntry(self._password, config.plugins.icetv.member.password,
                                _("Your password must have at least 5 characters.")),
             getConfigListEntry(self._label, config.plugins.icetv.device.label,
                                _("Choose a label that will identify this device within IceTV services.")),
             getConfigListEntry(self._update_interval, config.plugins.icetv.refresh_interval,
                                _("Choose how often to connect to IceTV server to check for updates.")),
        ]
        ConfigListScreen.__init__(self, self.list, session)
        self["InusActions"] = ActionMap(contexts=["SetupActions", "ColorActions"],
                                        actions={
                                             "cancel": self.cancel,
                                             "red": self.cancel,
                                             "green": self.save,
                                             "blue": self.keyboard,
                                             "ok": self.keyboard,
                                         }, prio=-2)

    def keyboard(self):
        selection = self["config"].getCurrent()
        if selection[1] is not config.plugins.icetv.refresh_interval:
            self.KeyText()

    def cancel(self):
        for x in self["config"].list:
            x[1].cancel()
        self.close(False)

    def save(self):
        self.saveAll()
        self.session.openWithCallback(self.regionDone, IceTVRegionSetup)

    def regionDone(self, region_success):
        if region_success:
            self.session.openWithCallback(self.loginDone, IceTVCreateLogin)

    def loginDone(self, login_success):
        if login_success:
            self.close(True)


class IceTVOldUserSetup(IceTVNewUserSetup):

    def save(self):
        self.saveAll()
        self.session.openWithCallback(self.loginDone, IceTVLogin)


class IceTVRegionSetup(Screen):
    skin = """
<screen name="IceTVRegionSetup" position="320,130" size="640,510" title="IceTV - Region" >
    <widget name="instructions" position="20,10" size="600,100" font="Regular;22" />
    <widget name="config" position="30,120" size="580,300" enableWrapAround="1" scrollbarMode="showAlways"/>
    <widget name="error" position="30,120" size="580,300" font="Console; 16" zPosition="1" />

    <widget name="description" position="20,e-90" size="600,60" font="Regular;18" foregroundColor="grey" halign="left" valign="top" />
    <ePixmap name="red" position="20,e-28" size="15,16" pixmap="skin_default/buttons/button_red.png" alphatest="blend" />
    <ePixmap name="green" position="170,e-28" size="15,16" pixmap="skin_default/buttons/button_green.png" alphatest="blend" />
    <widget name="key_red" position="40,e-30" size="150,25" valign="top" halign="left" font="Regular;20" />
    <widget name="key_green" position="190,e-30" size="150,25" valign="top" halign="left" font="Regular;20" />
    <widget name="key_yellow" position="340,e-30" size="150,25" valign="top" halign="left" font="Regular;20" />
    <widget name="key_blue" position="490,e-30" size="150,25" valign="top" halign="left" font="Regular;20" />
</screen>"""

    _instructions = _("Please select the region that most closely matches your physical location. "
                      "The region is required to enable us to provide the correct guide information "
                      "for the channels you can receive.")
    _wait = _("Please wait while the list downloads...")

    def __init__(self, session):
        self.session = session
        self.have_region_list = False
        Screen.__init__(self, session)
        self["instructions"] = Label(self._instructions)
        self["description"] = Label(self._wait)
        self["error"] = Label()
        self["error"].hide()
        self["key_red"] = Label(_("Cancel"))
        self["key_green"] = Label(_("Save"))
        self["key_yellow"] = Label()
        self["key_blue"] = Label()
        self["config"] = MenuList([])
        self["IrsActions"] = ActionMap(contexts=["SetupActions", "ColorActions"],
                                       actions={"cancel": self.cancel,
                                                "red": self.cancel,
                                                "green": self.save,
                                                "ok": self.save,
                                                }, prio=-2
                                       )
        self.region_list_timer = eTimer()
        self.region_list_timer.callback.append(self.getRegionList)
        self.onLayoutFinish.append(self.layoutFinished)

    def layoutFinished(self):
        self.region_list_timer.start(3, True)

    def cancel(self):
        self.close(False)

    def save(self):
        item = self["config"].getCurrent()
        config.plugins.icetv.member.region_id.value = item[1]
        config.plugins.icetv.member.region_id.save()
        self.close(self.have_region_list)

    def getRegionList(self):
        try:
            res = ice.Regions().get().json()
            regions = res["regions"]
            rl = []
            for region in regions:
                rl.append((str(region["name"]), int(region["id"])))
            self["config"].setList(rl)
            self["description"].setText("")
            if rl:
                self.have_region_list = True
        except (IOError, RuntimeError) as ex:
            msg = _logResponseException(fetcher, _("Can not download list of regions"), ex)
            self["description"].setText(_("There was an error downloading the region list"))
            self["error"].setText(msg)
            self["error"].show()


class IceTVLogin(Screen):
    skin = """
<screen name="IceTVLogin" position="220,115" size="840,570" title="IceTV - Login" >
    <widget name="instructions" position="20,10" size="800,80" font="Regular;22" />
    <widget name="error" position="30,120" size="780,300" font="Console; 16" zPosition="1" />
    <widget name="qrcode" position="292,90" size="256,256" pixmap="/usr/lib/enigma2/python/Plugins/SystemPlugins/IceTV/qr_code.png" zPosition="1" />
    <widget name="message" position="20,360" size="800,170" font="Regular;22" />

    <ePixmap name="green" position="170,e-28" size="15,16" pixmap="skin_default/buttons/button_green.png" alphatest="blend" />
    <widget name="key_red" position="40,e-30" size="150,25" valign="top" halign="left" font="Regular;20" />
    <widget name="key_green" position="190,e-30" size="150,25" valign="top" halign="left" font="Regular;20" />
    <widget name="key_yellow" position="340,e-30" size="150,25" valign="top" halign="left" font="Regular;20" />
    <widget name="key_blue" position="490,e-30" size="150,25" valign="top" halign="left" font="Regular;20" />
</screen>"""

    _instructions = _("Contacting IceTV server and setting up your %s %s.") % (getMachineBrand(), getMachineName())

    def __init__(self, session):
        self.session = session
        self.success = False
        Screen.__init__(self, session)
        self["instructions"] = Label(self._instructions)
        self["message"] = Label()
        self["error"] = Label()
        self["error"].hide()
        self["qrcode"] = Pixmap()
        self["qrcode"].hide()
        self["key_red"] = Label()
        self["key_green"] = Label(_("Done"))
        self["key_yellow"] = Label()
        self["key_blue"] = Label()
        self["IrsActions"] = ActionMap(contexts=["SetupActions", "ColorActions"],
                                       actions={"cancel": self.done,
                                                "red": self.done,
                                                "green": self.done,
                                                "ok": self.done,
                                                }, prio=-2
                                       )
        self.login_timer = eTimer()
        self.login_timer.callback.append(self.doLogin)
        self.onLayoutFinish.append(self.layoutFinished)

    def done(self):
        self.close(self.success)

    def layoutFinished(self):
        self.login_timer.start(3, True)

    def doLogin(self):
        try:
            if ice.haveCredentials():
                ice.Logout().delete()
        except:
            # Failure to logout is not a show-stopper
            pass
        try:
            self.loginCmd()
            self.success = True
            self["instructions"].setText(_("Congratulations, you have successfully configured your %s %s "
                                           "for use with the IceTV Smart Recording service. "
                                           "Your IceTV guide will now download in the background.") % (getMachineBrand(), getMachineName()))
            self["message"].setText(_("Enjoy how IceTV can enhance your TV viewing experience by "
                                      "downloading the IceTV app to your smartphone or tablet. "
                                      "The IceTV app is available free from the iTunes App Store, "
                                      "the Google Play Store and the Windows Phone Store.\n\n"
                                      "Download it today!"))
            self["qrcode"].show()
            config.plugins.icetv.configured.value = True
            enableIceTV()
            fetcher.createFetchJob()
        except (IOError, RuntimeError) as ex:
            msg = _logResponseException(fetcher, _("Login failure"), ex)
            self["instructions"].setText(_("There was an error while trying to login."))
            self["message"].hide()
            self["error"].show()
            self["error"].setText(msg)

    def loginCmd(self):
        ice.Login(config.plugins.icetv.member.email_address.value,
                  config.plugins.icetv.member.password.value).post()


class IceTVCreateLogin(IceTVLogin):

    def loginCmd(self):
        ice.Login(config.plugins.icetv.member.email_address.value,
                  config.plugins.icetv.member.password.value,
                  config.plugins.icetv.member.region_id.value).post()


class IceTVNeedPassword(ConfigListScreen, Screen):
    skin = """
<screen name="IceTVNeedPassword" position="320,230" size="640,310" title="IceTV - Password required" >
    <widget name="instructions" position="20,10" size="600,100" font="Regular;22" />
    <widget name="config" position="20,120" size="600,100" />

    <widget name="description" position="20,e-90" size="600,60" font="Regular;18" foregroundColor="grey" halign="left" valign="top" />
    <ePixmap name="red" position="20,e-28" size="15,16" pixmap="skin_default/buttons/button_red.png" alphatest="blend" />
    <ePixmap name="green" position="170,e-28" size="15,16" pixmap="skin_default/buttons/button_green.png" alphatest="blend" />
    <ePixmap name="blue" position="470,e-28" size="15,16" pixmap="skin_default/buttons/button_blue.png" alphatest="blend" />
    <widget name="key_red" position="40,e-30" size="150,25" valign="top" halign="left" font="Regular;20" />
    <widget name="key_green" position="190,e-30" size="150,25" valign="top" halign="left" font="Regular;20" />
    <widget name="key_yellow" position="340,e-30" size="150,25" valign="top" halign="left" font="Regular;20" />
    <widget name="key_blue" position="490,e-30" size="150,25" valign="top" halign="left" font="Regular;20" />
</screen>"""

    _instructions = _("The IceTV server has requested password for %s.")
    _password = _("Password")
    _update_interval = _("Connect to IceTV server every")

    def __init__(self, session):
        self.session = session
        Screen.__init__(self, session)
        self["instructions"] = Label(self._instructions % config.plugins.icetv.member.email_address.value)
        self["description"] = Label()
        self["key_red"] = Label(_("Cancel"))
        self["key_green"] = Label(_("Login"))
        self["key_yellow"] = Label()
        self["key_blue"] = Label(_("Keyboard"))
        self.list = [
             getConfigListEntry(self._password, config.plugins.icetv.member.password,
                                _("Your existing IceTV password.")),
             getConfigListEntry(self._update_interval, config.plugins.icetv.refresh_interval,
                                _("Choose how often to connect to IceTV server to check for updates.")),
        ]
        ConfigListScreen.__init__(self, self.list, session)
        self["InpActions"] = ActionMap(contexts=["SetupActions", "ColorActions"],
                                       actions={
                                             "cancel": self.cancel,
                                             "red": self.cancel,
                                             "green": self.doLogin,
                                             "blue": self.keyboard,
                                             "ok": self.keyboard,
                                         }, prio=-2)

    def keyboard(self):
        selection = self["config"].getCurrent()
        if selection[1] is not config.plugins.icetv.refresh_interval:
            self.KeyText()

    def cancel(self):
        for x in self["config"].list:
            x[1].cancel()
        self.close()

    def doLogin(self):
        try:
            self.loginCmd()
            self.saveAll()
            self.hide()
            self.close()
            global password_requested
            password_requested = False
            fetcher.addLog("Login OK")
            fetcher.createFetchJob()
        except (IOError, RuntimeError) as ex:
            msg = _logResponseException(fetcher, _("Login failure"), ex)
            self.session.open(MessageBox, msg, type=MessageBox.TYPE_ERROR)

    def loginCmd(self):
        ice.Login(config.plugins.icetv.member.email_address.value,
                  config.plugins.icetv.member.password.value).post()
