# kate: replace-tabs on; indent-width 4; remove-trailing-spaces all; show-tabs on; newline-at-eof on;
# -*- coding:utf-8 -*-

'''
Copyright (C) 2014 Peter Urbanec
All Right Reserved
License: Proprietary / Commercial - contact enigma.licensing (at) urbanec.net
'''

from enigma import eTimer, eEPGCache, eDVBDB, eServiceReference, iRecordableService, eServiceCenter
from Components.ActionMap import ActionMap
from Components.ConfigList import ConfigListScreen
from Components.Label import Label
from Components.MenuList import MenuList
from Components.Pixmap import Pixmap
from Components.config import getConfigListEntry, ConfigText
from Components.Converter.genre import getGenreStringSub
from Components.SystemInfo import getBoxDisplayName
from Plugins.Plugin import PluginDescriptor
from Screens.ChoiceBox import ChoiceBox
from Screens.MessageBox import MessageBox
from Screens.Screen import Screen
from RecordTimer import RecordTimerEntry
from ServiceReference import ServiceReference, service_types_tv_ref
from Tools.Directories import resolveFilename, SCOPE_PLUGINS
from Tools.LoadPixmap import LoadPixmap
from calendar import timegm
from time import strptime, gmtime, localtime, strftime, time
from . import config, enableIceTV, disableIceTV
from . import API as ice
import requests
from collections import deque, defaultdict
from operator import itemgetter
from Screens.TextBox import TextBox
from Components.TimerSanityCheck import TimerSanityCheck
import NavigationInstance
from twisted.internet import reactor, threads
from os import path


def ensure_str(result):
    if isinstance(result, bytes):
        result = result.decode(encoding='utf-8', errors='strict')
    return result


_session = None
password_requested = False

genre_remaps = {
    "AUS": {
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
        "Cycling": 0x0e,
        "Dance": 0x62,
        "Documentary": 0xe0,
        "Drama": 0xd0,
        "Family": 0x0d,
        "Fantasy": 0xf2,
        "Film-Noir": 0x0c,
        "Finance": 0x0b,
        "Fishing": 0xa3,
        "Food/Wine": 0xa4,
        "Golf": 0x42,
        "Hockey": 0x4e,
        "Horror": 0xf1,
        "Horse Racing": 0x0a,
        "Lifestyle": 0xa2,
        "MMA": 0x09,
        "Mini Series": 0x08,
        "Murder": 0x1c,
        "Musical": 0x61,
        "Mystery": 0x1b,
        "Netball": 0x4d,
        "Parliament": 0x82,
        "Renovation": 0x07,
        "Rowing": 0xf8,
        "Rugby": 0x4c,
        "Rugby League": 0x4b,
        "Sailing": 0x06,
        "Science": 0x94,
        "Short Film": 0x05,
        "Sitcom": 0xf3,
        "Special": 0xb0,
        "Thriller": 0x1a,
        "Violence": 0x04,
        "War": 0x1e,
        "Western": 0x1d,
        "Wrestling": 0x03,
        "Youth": 0x02,
    },
    "DEU": {
        '': 0x00,
        'Abenteuer': 0x01,
        'Action': 0x56,
        'Adel': 0x54,
        'Agenten': 0x53,
        'American Sports': 0x52,
        'Animation': 0x55,
        'Anime': 0x51,
        'Architektur': 0x50,
        'Arzt': 0x4f,
        'Automobil': 0x4e,
        'B-Movie': 0x4d,
        'Bericht': 0x4c,
        'Berufe': 0x4b,
        'Beziehung': 0x4a,
        'Bildung': 0x49,
        'Biografie': 0x48,
        'Bollywood': 0x47,
        'Boulevard': 0x46,
        'Boxen': 0x45,
        'Call-in': 0x44,
        'Casting': 0x43,
        'Chronik': 0x42,
        'Comedy': 0xc0,
        'Comic': 0x41,
        'Computer': 0x3f,
        'Current Affairs': 0x81,
        'Dating': 0x3e,
        'Detektiv': 0x3d,
        'Documentary': 0xe0,
        'Dokumentation': 0x3c,
        'Drama': 0xd0,
        'Drogen': 0x3a,
        'Eastern': 0x39,
        'Einzelsportart': 0x38,
        'Energie': 0x37,
        'Epos': 0x36,
        'Erotik': 0x35,
        'Esoterik': 0x34,
        'Essen': 0x33,
        'Event': 0x32,
        'Extremsport': 0x31,
        'Familie': 0x30,
        'Fantasy': 0x2f,
        'Frauen': 0x2e,
        'Fu\xc3\x9fball': 0x2d,
        'F\xc3\xbcr Kinder': 0x2c,
        'Gangster': 0x2b,
        'Garten': 0x2a,
        'Geschichte': 0x29,
        'Gesellschaft': 0x28,
        'Gesundheit': 0x27,
        'Handball': 0x26,
        'Heimat': 0x25,
        'Heimwerker': 0x24,
        'Hobbys': 0x23,
        'Horror': 0x22,
        'Independent': 0x21,
        'Information': 0x20,
        'International': 0x1f,
        'Jugend': 0x1e,
        'Justiz': 0x1d,
        'Kampfsport': 0x1c,
        'Katastrophe': 0x1b,
        'Kinder': 0x1a,
        'Klassiker': 0x19,
        'Kneipensport': 0x18,
        'Kom\xc3\xb6die': 0x17,
        'Kraftsport': 0x16,
        'Krieg': 0x15,
        'Krimi': 0x13,
        'Kriminalit\xc3\xa4t': 0x12,
        'Kultur': 0x11,
        'Kunst': 0x10,
        'Kurzfilm': 0xef,
        'Landestypisch': 0xee,
        'Late Night': 0xed,
        'Leichtathletik': 0xec,
        'Lifestyle': 0xeb,
        'Literatur': 0xea,
        'Literaturverfilmung': 0xe9,
        'Magazin': 0xe8,
        'Mannschaftssport': 0xe7,
        'Medien': 0xe6,
        'Mode': 0xe5,
        'Motorsport': 0xe4,
        'Musical': 0xe3,
        'Musik': 0xe2,
        'Mystery': 0xe1,
        'M\xc3\xa4rchen': 0xdf,
        'Nachrichten': 0xde,
        'National': 0xdd,
        'Natur': 0xdc,
        'Neue Medien': 0xdb,
        'Olympia': 0xda,
        'Outdoor': 0xd9,
        'Parabel': 0xd8,
        'Parodie': 0xd7,
        'Poker': 0xd6,
        'Politik': 0xd5,
        'Portr\xc3\xa4t': 0xd4,
        'Prominent': 0xd3,
        'Psychologie': 0xd2,
        'Puppentrick': 0xd1,
        'Quiz': 0xcf,
        'Radsport': 0xce,
        'Reality': 0xcd,
        'Regional': 0xcc,
        'Reisen': 0xcb,
        'Reiten': 0xca,
        'Religion': 0xc9,
        'Reportage': 0xc8,
        'Revue': 0xc7,
        'Romantik': 0xc6,
        'Saga': 0xc5,
        'Satire': 0xc4,
        'Science-Fiction': 0xc3,
        'Serie': 0xc2,
        'Show': 0xc1,
        'Slapstick': 0xff,
        'Soap': 0xfe,
        'Special': 0xb0,
        'Spiele': 0xfd,
        'Spielfilm': 0xfc,
        'Sport': 0x40,
        'Sprache': 0xfb,
        'Stumm': 0xfa,
        'Talk': 0xf9,
        'Tanz': 0xf8,
        'Technik': 0xf7,
        'Theater': 0xf6,
        'Thriller': 0xf5,
        'Tiere': 0xf4,
        'Trag\xc3\xb6die': 0xf3,
        'Umweltbewusstsein': 0xf2,
        'Unterhaltung': 0xf1,
        'Verkehr': 0xf0,
        'Verschiedenes': 0x0f,
        'Videoclip': 0x0e,
        'Vorschau': 0x0d,
        'Waffen': 0x0c,
        'Wassersport': 0x0b,
        'Werbung': 0x0a,
        'Western': 0x09,
        'Wettbewerb': 0x08,
        'Wetter': 0x07,
        'Wintersport': 0x06,
        'Wirtschaft': 0x05,
        'Wissenschaft': 0x04,
        'Zeichentrick': 0x03,
        'Zirkus': 0x02,
    },
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
        msg += ": " + _("The IceTV server can not be reached. Try checking the Internet connection on your %s %s\nDetails") % getBoxDisplayName()
    msg += ": " + str(exception)
    if hasattr(exception, "response") and hasattr(exception.response, "text"):
        ex_text = str(exception.response.text).strip()
        if ex_text:
            msg += "\n" + ex_text
    logger.addLog(msg)
    return msg


class LogEntry(dict):
    def __init__(self, timestamp, log_message, sent=False):
        self.sent = sent
        self.timestamp = int(timestamp)
        self.log_message = log_message

    def get_timestamp(self):
        return self["timestamp"]

    def set_timestamp(self, timestamp):
        self["timestamp"] = timestamp

    timestamp = property(get_timestamp, set_timestamp)

    def get_log_message(self):
        return self["log_message"]

    def set_log_message(self, log_message):
        self["log_message"] = log_message

    log_message = property(get_log_message, set_log_message)

    def fmt(self):
        return "%s: %s" % (strftime("%Y-%m-%d %H:%M:%S", localtime(self.timestamp)), self.log_message)

    def __str__(self):
        return self.fmt()


class EPGFetcher:
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
        config.plugins.icetv.enable_epg.addNotifier(self.icetvEnableChanged, initial_call=False, immediate_feedback=False)
        config.plugins.icetv.enable_epg.callNotifiersOnSaveAndCancel = True
        self.log = deque(maxlen=40)
        self.send_scans = False
        # TODO: channel_service_map should probably be locked in case the user edits timers at the time of a fetch
        # Then again, the GIL may actually prevent issues here.
        self.channel_service_map = None
        self.service_set = None

        # Status updates for timers that can't be processed at
        # the time that a status change is flagged (e.g. for instant
        # timers that don't initially have an IceTV id.
        self.deferred_status = defaultdict(list)

        # Timers that have failed, but where, when the iRecordableService
        # issues its evEnd event, the iRecordableService.getError()
        # returns NoError (for example, evRecordWriteError).
        self.failed = {}

        self.settings = {}

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
                return self.isIceTVEpgChannel(entry.service_ref.ref)
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
            if event == iRecordableService.evRecordWriteError and id(event) not in self.failed:
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
            for tid, worklist in list(status.items()):
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

    def icetvEnableChanged(self, enable_epg):
        if not enable_epg.value:
            self.channel_service_map = None
            self.service_set = None

    def addLog(self, msg):
        entry = LogEntry(time(), msg)
        self.log.append(entry)
        print("[IceTV]", str(entry))

    def createFetchJob(self, res=None, send_scans=False):
        if config.plugins.icetv.configured.value and config.plugins.icetv.enable_epg.value:
            global password_requested
            if password_requested:
                self.addLog("Can not proceed - you need to login first")
                return
            # print "[IceTV] Create fetch job"
            self.send_scans = self.send_scans or send_scans
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
        old_service_set = self.service_set
        try:
            self.settings = dict((s["name"], ensure_str(s["value"]) if s["type"] == 2 else s["value"]) for s in self.getSettings())
            print("[EPGFetcher] settings", self.settings)
        except (Exception) as ex:
            self.settings = {}
            _logResponseException(self, _("Can not retrieve IceTV settings"), ex)
        send_logs = config.plugins.icetv.member.send_logs and self.settings.get("send_pvr_logs", False)
        print("[EPGFetcher] send_logs", send_logs)
        if send_logs:
            self.postPvrLogs()
        try:
            self.makeChanServMap(self.getChannels())
        except (Exception) as ex:
            _logResponseException(self, _("Can not retrieve channel map"), ex)
            if send_logs:
                self.postPvrLogs()
            return False
        if self.send_scans:
            self.postScans()
            self.send_scans = False
        epgcache = eEPGCache.getInstance()
        if old_service_set is not None:
            removed_services = old_service_set - self.service_set
            added_services = self.service_set - old_service_set
            for t in list(removed_services) + list(added_services):
                epgcache.flushEPG(t[2], t[0], t[1])
        else:
            added_services = set()
        try:
            res = self.processShowsBatched(added_triples=added_services)
            self.deferredPostStatus(None)
            self.statusCleanup()
            if res:  # Timers fetched in non-batched show fetch
                self.addLog("End update")
                if send_logs:
                    self.postPvrLogs()
                return res
            res = True  # Reset res ready for a separate timer download
        except (OSError, RuntimeError) as ex:
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
        except (Exception) as ex:
            _logResponseException(self, _("Can not download timers"), ex)
            res = False
        if not ice.haveCredentials() and not password_requested:
            password_requested = True
            self.addLog("No token, requesting password...")
            _session.open(IceTVNeedPassword)
        self.addLog("End update")
        self.deferredPostStatus(None)
        self.statusCleanup()
        if send_logs:
            self.postPvrLogs()
        return res

    def getTriplets(self):
        name_map = self.getScanChanNameMap()
        if not self.channel_service_map or not name_map:
            return None

        triplet_map = defaultdict(list)
        scan_list = []

        for id, triplets in list(self.channel_service_map.items()):
            for triplet in triplets:
                triplet_map[triplet].append(id)
        for name, triplets in list(name_map.items()):
            for triplet in triplets:
                if triplet in triplet_map:
                    for id in triplet_map[triplet]:
                        scan_list.append({"channel_id": id, "channel_name": name, "sid": triplet[2], "tsid": triplet[1], "onid": triplet[0]})
                else:
                    scan_list.append({"channel_name": name, "sid": triplet[2], "tsid": triplet[1], "onid": triplet[0]})
        return scan_list or None

    def getScanChanNameMap(self):
        name_map = defaultdict(list)

        serviceHandler = eServiceCenter.getInstance()
        servicelist = serviceHandler.list(service_types_tv_ref)
        if servicelist is not None:
            serviceRef = servicelist.getNext()
            while serviceRef.valid():
                name = ensure_str(ServiceReference(serviceRef).getServiceName()).strip()
                name_map[name].append(tuple(serviceRef.getUnsignedData(i) for i in (3, 2, 1)))
                serviceRef = servicelist.getNext()
        return name_map

    def makeChanServMap(self, channels):
        res = defaultdict(list)
        name_map = dict((n.upper(), t) for n, t in self.getScanChanNameMap().items())

        ice_services = set()
        for channel in channels:
            channel_id = int(channel["id"])
            triplets = []
            if "dvb_triplets" in channel:
                triplets = channel["dvb_triplets"]
            elif "dvbt_info" in channel:
                triplets = channel["dvbt_info"]
            for triplet in triplets:
                t = (int(triplet["original_network_id"]),
                     int(triplet["transport_stream_id"]),
                     int(triplet["service_id"]))
                res[channel_id].append(t)
                ice_services.add(t)

            names = [channel["name"].strip().upper()]
            if "name_short" in channel:
                name = channel["name_short"].strip().upper()
                if name not in names:
                    names.append(name)
            for n in channel.get("known_names", []):
                name = n.strip().upper()
                if name not in names:
                    names.append(name)

            for triplets in (name_map[n] for n in names if n in name_map):
                for triplet in (t for t in triplets if t not in res[channel_id]):
                    res[channel_id].append(triplet)
                    ice_services.add(triplet)
        self.channel_service_map = res
        self.service_set = ice_services
        return res

    def serviceToIceChannelId(self, serviceref):
        svc = str(serviceref).split(":")
        triplet = (int(svc[5], 16), int(svc[4], 16), int(svc[3], 16))
        for channel_id, dvbt in self.channel_service_map.items():
            if triplet in dvbt:
                return channel_id

    def makeChanShowMap(self, shows):
        res = defaultdict(list)
        for show in shows:
            channel_id = int(show["channel_id"])
            res[channel_id].append(show)
        return res

    def convertChanShows(self, shows, mapping_errors):
        country_code = config.plugins.icetv.member.country.value
        res = []
        category_cache = {}
        for show in shows:
            event_id = int(show.get("eit_id"))
            if event_id is None:
                event_id = ice.showIdToEventId(show["id"])
            if event_id <= 0:
                event_id = None
            if "deleted_record" in show and int(show["deleted_record"]) == 1:
                start = 999
                duration = 10
            else:
                start = int(show["start_unix"])
                stop = int(show["stop_unix"])
                duration = stop - start
            title = ensure_str(show.get("title", ""))
            short = ensure_str(show.get("subtitle", ""))
            extended = ensure_str(show.get("desc", ""))
            genres = []
            for g in show.get("category", []):
                name = ensure_str(g['name'])
                if name in category_cache:
                    eit_remap = category_cache[name]
                    genres.append(eit_remap)
                else:
                    eit = int(g.get("eit", "0"), 0) or 0x01
                    eit_remap = genre_remaps.get(country_code, {}).get(name, eit)
                    mapped_name = getGenreStringSub((eit_remap >> 4) & 0xf, eit_remap & 0xf, country=country_code)
                    if mapped_name == name:
                        genres.append(eit_remap)
                        category_cache[name] = eit_remap
                    elif name not in mapping_errors:
                        print('[EPGFetcher] ERROR: lookup of 0x%02x%s "%s" returned \"%s"' % (eit, (" (remapped to 0x%02x)" % eit_remap) if eit != eit_remap else "", name, mapped_name))
                        mapping_errors.add(name)
            p_rating = ((country_code, parental_ratings.get(ensure_str(show.get("rating", "")), 0x00)),)
            res.append((start, duration, title, short, extended, genres, event_id, p_rating))
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

    def triplesToChannels(self, triples):
        if triples:
            return set(ch for ch, tl in self.channel_service_map.items() for t in tl if t in triples)
        else:
            return set()

    def processShowsBatched(self, added_triples=None):
        # Maximum number of channels to fetch in a batch
        max_fetch = config.plugins.icetv.batchsize.value
        res = False
        added_channels = self.triplesToChannels(added_triples)
        channels = list(self.channel_service_map.keys())
        channels = list(set(channels) - added_channels)
        added_channels = list(added_channels)
        epgcache = eEPGCache.getInstance()
        channels_lists = [l for l in (added_channels, channels) if l]
        last_update_time = 0
        shows = None
        mapping_errors = set()
        for i, chan_list in enumerate(channels_lists):
            pos = 0
            while pos < len(chan_list):
                fetch_chans = chan_list[pos:pos + max_fetch]
                batch_fetch = added_channels or (max_fetch and len(fetch_chans) != len(chan_list))
                is_last_fetch = i == len(channels_lists) - 1 and pos + len(fetch_chans) >= len(chan_list)
                shows = self.getShows(chan_list=batch_fetch and fetch_chans or None, fetch_timers=is_last_fetch, fetch_from_epoch=chan_list is added_channels)
                channel_show_map = self.makeChanShowMap(shows["shows"])
                for channel_id in list(channel_show_map.keys()):
                    if channel_id in self.channel_service_map:
                        epgcache.importEvents(self.channel_service_map[channel_id], self.convertChanShows(channel_show_map[channel_id], mapping_errors))
                    if i == 0 and pos == 0 and "last_update_time" in shows:
                        last_update_time = shows["last_update_time"]
                if self.updateDescriptions(channel_show_map):
                    NavigationInstance.instance.RecordTimer.saveTimers()
                pos += len(fetch_chans) if max_fetch else len(chan_list)
        if shows is not None and "timers" in shows:
            res = self.processTimers(shows["timers"])
        config.plugins.icetv.last_update_time.value = last_update_time
        epgcache.save()
        self.addLog("EPG download OK")
        return res

    def processTimers(self, timers):
        update_queue = []
        for iceTimer in timers:
            # print "[IceTV] iceTimer:", iceTimer
            try:
                action = ensure_str(iceTimer.get("action", ""))
                state = ensure_str(iceTimer.get("state", ""))
                name = ensure_str(iceTimer.get("name", ""))
                start = int(timegm(strptime(iceTimer["start_time"].split("+")[0], "%Y-%m-%dT%H:%M:%S")))
                duration = 60 * int(iceTimer["duration_minutes"])
                channel_id = int(iceTimer["channel_id"])
                ice_timer_id = ensure_str(iceTimer["id"])
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
                                    iceTimer["state"] = "pending"
                                    iceTimer["message"] = "Timer already up to date '%s'" % name
                                    update_queue.append(iceTimer)
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
            except (OSError, RuntimeError, KeyError) as ex:
                print("[IceTV] Can not process iceTimer:", ex)
        # Send back updated timer states
        res = True
        try:
            self.putTimers(update_queue)
            self.addLog("Timers updated OK")
        except KeyError as ex:
            print("[IceTV] ", str(ex))
            res = False
        except (OSError, RuntimeError) as ex:
            _logResponseException(self, _("Can not update timers"), ex)
            res = False
        return res

    def isIceTimerInUpdateQueue(self, iceTimer, update_queue):
        ice_timer_id = ensure_str(iceTimer["id"])
        for timer in update_queue:
            if ice_timer_id == ensure_str(timer["id"]):
                return True
        return False

    def isIceTimerInLocalTimerList(self, iceTimer, ignoreCompleted=False):
        ice_timer_id = ensure_str(iceTimer["id"])
        for timer in _session.nav.RecordTimer.timer_list:
            if timer.ice_timer_id == ice_timer_id:
                return True
        if not ignoreCompleted:
            for timer in _session.nav.RecordTimer.processed_timers:
                if timer.ice_timer_id == ice_timer_id:
                    return True
        return False

    def isIceTVEpgChannel(self, service):
        sref = eServiceReference(service)
        triple = tuple(sref.getUnsignedData(i) for i in (3, 2, 1))
        return self.service_set and triple in self.service_set

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
                        _session.nav.RecordTimer.timeChanged(x)
                if timersanitycheck.check():
                    success = True
        else:
            success = True
        if success:
            _session.nav.RecordTimer.timeChanged(timer)
        return success

    def getSettings(self):
        req = ice.Settings()
        res = req.get().json()
        return res.get("settings", [])

    def getShows(self, chan_list=None, fetch_timers=True, fetch_from_epoch=False):
        req = ice.Shows()
        last_update = config.plugins.icetv.last_update_time.value
        req.params["last_update_time"] = 0 if fetch_from_epoch else last_update
        if chan_list:
            req.params["channel_id"] = ','.join(str(ch) for ch in chan_list)
        if not fetch_timers:
            req.params["hide_timers"] = 1
        return req.get().json()

    def getChannels(self):
        req = ice.UserChannels(config.plugins.icetv.member.region_id.value)
        res = req.get().json()
        return res.get("channels", [])

    def getAllChannels(self):
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
            timer["duration_minutes"] = ((local_timer.end - config.recording.margin_after.value * 60) - (local_timer.begin + config.recording.margin_before.value * 60)) // 60
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
        except (OSError, RuntimeError, KeyError) as ex:
            _logResponseException(self, _("Can not update timer"), ex)

    def postTimer(self, local_timer):
        if self.channel_service_map is None:
            try:
                self.makeChanServMap(self.getChannels())
            except (OSError, RuntimeError, KeyError) as ex:
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
                req.data["duration_minutes"] = ((local_timer.end - config.recording.margin_after.value * 60) - (local_timer.begin + config.recording.margin_before.value * 60)) // 60
                res = req.post()
                try:
                    local_timer.ice_timer_id = ensure_str(res.json()["timers"][0]["id"])
                    self.addLog("Timer '%s' created OK" % local_timer.name)
                    if local_timer.ice_timer_id is not None:
                        NavigationInstance.instance.RecordTimer.saveTimers()
                        self.deferredPostStatus(local_timer)
                except:
                    self.addLog("Couldn't get IceTV timer id for timer '%s'" % local_timer.name)

            except (OSError, RuntimeError, KeyError) as ex:
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
        except (OSError, RuntimeError, KeyError) as ex:
            _logResponseException(self, _("Can not delete timer"), ex)

    def postStatus(self, timer, state, message):
        try:
            channel_id = self.serviceToIceChannelId(timer.service_ref)
            req = ice.Timer(timer.ice_timer_id)
            req.data["message"] = message
            req.data["state"] = state
            # print "[EPGFetcher] postStatus", timer.name, message, state
            res = req.put()
        except (OSError, RuntimeError, KeyError) as ex:
            _logResponseException(self, _("Can not update timer status"), ex)
        self.deferredPostStatus(timer)

    def postScans(self):
        scan_list = self.getTriplets()
        print("[EPGFetcher] postScans", scan_list is not None)
        if scan_list is None:
            return
        try:
            req = ice.Scans()
            req.data["scans"] = scan_list
            res = req.post()
            print("[EPGFetcher] postScans", res)
        except (OSError, RuntimeError, KeyError) as ex:
            _logResponseException(self, _("Can not post scan information"), ex)

    def postPvrLogs(self):
        log_list = [l for l in self.log if not l.sent]
        print("[EPGFetcher] postPvrLogs", len(log_list))
        if not log_list:
            return
        try:
            req = ice.PvrLogs()
            req.data["logs"] = log_list
            res = req.post()
            print("[EPGFetcher] postPvrLogs", res, res.json()["count_of_log_entries"])
            for l in log_list:
                l.sent = True
        except (OSError, RuntimeError, KeyError) as ex:
            _logResponseException(self, _("Can not post PVR log information"), ex)


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


def after_scan(**kwargs):
    if fetcher is not None:
        fetcher.createFetchJob(send_scans=True)


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
    res.append(
        PluginDescriptor(
            name="IceTV",
            where=PluginDescriptor.WHERE_SERVICESCAN,
            description=_("IceTV version %s") % ice._version_string,
            fnc=after_scan
        ))
    return res


class IceTVUIBase:
    _banner = _("Find out more at %s")

    def __init__(self, title=None, description=None, server=None):
        if hasattr(self, "_instructions"):
            self["instructions"] = Label(self._instructions)
        if title is not None:
                self.setTitle(title)
        if description is not None:
                self["description"] = Label(description)
        if self._banner is not None:
            self["banner"] = Label()
            if server is None:
                    server = config.plugins.icetv.server.name.value
            self.setBanner(server)

    def setBanner(self, server):
        self["banner"].text = self._banner % server.replace("api.", "www.", 1)


class IceTVMain(ChoiceBox):
    skin = """
<screen name="IceTVMain" position="center,center" size="1060,350" zPosition="5">
    <ePixmap pixmap="/usr/lib/enigma2/python/Plugins/SystemPlugins/IceTV/icetv_logo172x100.png" position="202,0" size="172,100" alphatest="on" />
    <widget name="text" position="540,0" size="520,350" font="Regular;22" valign="center" halign="center" />
    <widget name="list" position="10,100" size="520,150" enableWrapAround="1" />
</screen>"""

    def __init__(self, session, *args, **kwargs):
        global _session
        if _session is None:
            _session = session
        self.skinName = "IceTVMain"
        text = IceTVUIBase._banner % config.plugins.icetv.server.name.value.replace("api.", "www.")

        menu = [
                (_("Show Log"), "CALLFUNC", self.showLog),
                (_("Fetch EPG and update timers now"), "CALLFUNC", self.fetch),
                (_("IceTV setup wizard"), "CALLFUNC", self.configure),
                (_("Login to IceTV server"), "CALLFUNC", self.login),
                (_("Enable IceTV"), "CALLFUNC", self.enable),
                (_("Disable IceTV"), "CALLFUNC", self.disable),
               ]
        try:
            # Use windowTitle for compatibility betwwen OpenATV & OpenViX
            super(IceTVMain, self).__init__(session, title=(_("IceTV version %s\n") + text) % ice._version_string, list=menu, skin_name=self.skinName, windowTitle=_("IceTV - Setup"))
        except TypeError:
            # Fallback for Beyonwiz
            super(IceTVMain, self).__init__(session, skin_name=self.skinName, title=(_("IceTV version %s\n") + text) % ice._version_string, list=menu)

        self.setTitle(_("IceTV - Setup"))
        self["debugactions"] = ActionMap(
            contexts=["DirectionActions"],
            actions={
                 "chplus": self.increaseDebug,
                 "chminus": self.decreaseDebug,
            }, prio=-1)

    def increaseDebug(self):
        if ice._debug_level < 4:
            ice._debug_level += 1
        print("[IceTV] debug level =", ice._debug_level)

    def decreaseDebug(self):
        if ice._debug_level > 0:
            ice._debug_level -= 1
        print("[IceTV] debug level =", ice._debug_level)

    def enable(self, res=None):
        enableIceTV()
        _session.open(MessageBox, _("IceTV enabled"), type=MessageBox.TYPE_INFO, timeout=5)

    def disable(self, res=None):
        disableIceTV()
        _session.open(MessageBox, _("IceTV disabled"), type=MessageBox.TYPE_INFO, timeout=5)

    def configure(self, res=None):
        _session.open(IceTVServerSetup)

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
        _session.open(IceTVLogView, "\n".join(str(l) for l in fetcher.log))


class IceTVLogView(TextBox):
    skin = """<screen name="IceTVLogView" backgroundColor="background" position="90,150" size="1100,450" title="Log">
        <widget font="Console;18" name="text" position="0,4" size="1100,446"/>
</screen>"""


class IceTVServerSetup(Screen, IceTVUIBase):
    skin = """
<screen name="IceTVServerSetup" position="center,center" size="1190,510" title="IceTV - Service selection" >
    <widget name="instructions" position="20,10" size="600,100" font="Regular;22" />
    <widget name="config" position="30,120" size="580,300" enableWrapAround="1" scrollbarMode="showAlways"/>
    <ePixmap pixmap="/usr/lib/enigma2/python/Plugins/SystemPlugins/IceTV/icetv_logo172x100.png" position="804,0" size="172,100" alphatest="on" />
    <widget name="banner" position="630,105" size="520,350" font="Regular;22" valign="center" halign="center" />
    <ePixmap name="red" position="20,e-28" size="15,16" pixmap="skin_default/buttons/button_red.png" alphatest="blend" />
    <ePixmap name="green" position="170,e-28" size="15,16" pixmap="skin_default/buttons/button_green.png" alphatest="blend" />
    <widget name="key_red" position="40,e-30" size="150,25" valign="top" halign="left" font="Regular;20" />
    <widget name="key_green" position="190,e-30" size="150,25" valign="top" halign="left" font="Regular;20" />
    <widget name="key_yellow" position="340,e-30" size="150,25" valign="top" halign="left" font="Regular;20" />
    <widget name="key_blue" position="490,e-30" size="150,25" valign="top" halign="left" font="Regular;20" />
</screen>"""

    _instructions = _(
        "Please select the IceTV service that you wish to use.\n\n"
        "IceTV is a subscription service that is only available in the listed countries."
    )

    def __init__(self, session):
        self.have_region_list = False
        Screen.__init__(self, session)
        IceTVUIBase.__init__(self, title=_("IceTV - Service selection"))
        self["key_red"] = Label(_("Cancel"))
        self["key_green"] = Label(_("Save"))
        self["key_yellow"] = Label()
        self["key_blue"] = Label()
        self["config"] = MenuList(sorted(list(ice.iceTVServers.items())))
        self["config"].onSelectionChanged.append(self.selectionChanged)
        self["IrsActions"] = ActionMap(contexts=["SetupActions", "ColorActions"],
                                       actions={"cancel": self.cancel,
                                                "red": self.cancel,
                                                "green": self.save,
                                                "ok": self.save,
                                                }, prio=-2
                                       )

    def onLayoutFinished(self):
        curr_server_name = config.plugins.icetv.server.name.value
        try:
                self["config"].moveToIndex(next(i for i, ent in enumerate(self["config"].list) if ent[1] == curr_server_name))
        except StopIteration:
                pass

    def selectionChanged(self):
        self.setBanner(self["config"].getCurrent()[1])

    def cancel(self):
        config.plugins.icetv.server.name.cancel()
        print("[IceTV] server reset to", config.plugins.icetv.server.name.value)
        self.close(False)

    def save(self):
        item = self["config"].getCurrent()
        config.plugins.icetv.server.name.value = item[1]
        print("[IceTV] server set to", config.plugins.icetv.server.name.value)
        self.session.openWithCallback(self.userDone, IceTVUserTypeScreen)

    def userDone(self, user_success):
        if user_success:
            self.close(True)


class IceTVUserTypeScreen(Screen, IceTVUIBase):
    skin = """
<screen name="IceTVUserTypeScreen" position="center,center" size="1190,455" title="IceTV - Account selection" >
 <widget position="20,20" size="600,40" name="title" font="Regular;32" />
 <widget position="20,80" size="600,200" name="instructions" font="Regular;22" />
    <ePixmap pixmap="/usr/lib/enigma2/python/Plugins/SystemPlugins/IceTV/icetv_logo172x100.png" position="804,0" size="172,100" alphatest="on" />
    <widget name="banner" position="630,105" size="520,350" font="Regular;22" valign="center" halign="center" />
 <widget position="20,300" size="600,100" name="menu" />
</screen>
"""
    _instructions = _("In order to allow you to access all the features of the "
                      "IceTV smart recording service, we need to gather some "
                      "basic information.\n\n"
                      "If you already have an IceTV subscription or trial, please select "
                      "'Existing or trial customer', if not, then select 'New customer'.")

    def __init__(self, session):
        Screen.__init__(self, session)
        self["title"] = Label(_("Welcome to IceTV"))
        IceTVUIBase.__init__(self, title=_("IceTV - Account selection"))
        options = []
        options.append((_("New customer"), "newUser"))
        options.append((_("Existing or trial customer"), "oldUser"))
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


class IceTVNewUserSetup(ConfigListScreen, Screen, IceTVUIBase):
    skin = """
<screen name="IceTVNewUserSetup" position="center,center" size="1190,455" title="IceTV - User Information" >
    <widget name="instructions" position="20,10" size="600,125" font="Regular;22" />
    <widget name="config" position="20,145" size="600,125" />

    <widget name="description" position="20,e-90" size="600,60" font="Regular;18" foregroundColor="grey" halign="left" valign="top" />
    <ePixmap pixmap="/usr/lib/enigma2/python/Plugins/SystemPlugins/IceTV/icetv_logo172x100.png" position="804,0" size="172,100" alphatest="on" />
    <widget name="banner" position="630,105" size="520,350" font="Regular;22" valign="center" halign="center" />
    <ePixmap name="red" position="20,e-28" size="15,16" pixmap="skin_default/buttons/button_red.png" alphatest="blend" />
    <ePixmap name="green" position="170,e-28" size="15,16" pixmap="skin_default/buttons/button_green.png" alphatest="blend" />
    <ePixmap name="blue" position="470,e-28" size="15,16" pixmap="skin_default/buttons/button_blue.png" alphatest="blend" />
    <widget name="key_red" position="40,e-30" size="150,25" valign="top" halign="left" font="Regular;20" />
    <widget name="key_green" position="190,e-30" size="150,25" valign="top" halign="left" font="Regular;20" />
    <widget name="key_yellow" position="340,e-30" size="150,25" valign="top" halign="left" font="Regular;20" />
    <widget name="key_blue" position="490,e-30" size="150,25" valign="top" halign="left" font="Regular;20" />
    <widget name="HelpWindow" position="0,10000" size="0,0" zPosition="1" transparent="1" alphatest="blend" />
</screen>"""

    _instructions = _("Please enter your email address, which will be your login.\n"
                      "Via your account on the IceTV website you can choose"
                      " to receive service announcements, account reminders"
                      " and promotional offers.")
    _email = _("Email")
    _password = _("Password")
    _label = _("Label")
    _update_interval = _("Connect to IceTV server every")
    _merge_eit = _("Merge broadcast EPG with IceTV")

    def __init__(self, session):
        Screen.__init__(self, session)
        IceTVUIBase.__init__(self, title=_("IceTV - User Information"), description="")
        self["instructions"] = Label(self._instructions)
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
             getConfigListEntry(self._merge_eit, config.plugins.icetv.merge_eit_epg,
                                _("Fill in channel EPGs from the broadcast EPG where there is no IceTV EPG for the channel")),
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
        if isinstance(selection[1], ConfigText):
            self.keyText()

    def cancel(self):
        for x in self["config"].list:
            x[1].cancel()
        self.close(False)

    def saveConfs(self):
        config.plugins.icetv.server.name.save()
        config.plugins.icetv.member.country.save()
        config.plugins.icetv.member.region_id.save()
        self.saveAll()

    def save(self):
        self.saveConfs()
        self.session.openWithCallback(self.regionDone, IceTVRegionSetup)

    def regionDone(self, region_success):
        if region_success:
            self.session.openWithCallback(self.loginDone, IceTVCreateLogin)

    def loginDone(self, login_success):
        if login_success:
            self.close(True)


class IceTVOldUserSetup(IceTVNewUserSetup):

    def __init__(self, session):
        super(IceTVOldUserSetup, self).__init__(session)
        self.skinName = self.__class__.__bases__[0].__name__

    def save(self):
        self.saveConfs()
        self.session.openWithCallback(self.loginDone, IceTVLogin)


class IceTVRegionSetup(Screen, IceTVUIBase):
    skin = """
<screen name="IceTVRegionSetup" position="center,center" size="1190,510" title="IceTV - Region" >
    <widget name="instructions" position="20,10" size="600,100" font="Regular;22" />
    <widget name="config" position="30,120" size="580,300" enableWrapAround="1" scrollbarMode="showAlways"/>
    <widget name="error" position="30,120" size="580,300" font="Console; 16" zPosition="1" />

    <widget name="description" position="20,e-90" size="600,60" font="Regular;18" foregroundColor="grey" halign="left" valign="top" />
    <ePixmap pixmap="/usr/lib/enigma2/python/Plugins/SystemPlugins/IceTV/icetv_logo172x100.png" position="804,0" size="172,100" alphatest="on" />
    <widget name="banner" position="630,105" size="520,350" font="Regular;22" valign="center" halign="center" />
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
        self.have_region_list = False
        Screen.__init__(self, session)
        IceTVUIBase.__init__(self, title=_("IceTV - Region"), description=self._wait)
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
        config.plugins.icetv.member.region_id.cancel()
        config.plugins.icetv.member.country.cancel()
        self.close(False)

    def save(self):
        item = self["config"].getCurrent()
        config.plugins.icetv.member.region_id.value = item[1]
        config.plugins.icetv.member.country.value = item[2]
        self.close(self.have_region_list)

    def getRegionList(self):
        try:
            res = ice.Regions().get().json()
            regions = res["regions"]
            rl = []
            for region in regions:
                rl.append((str(region["name"]), int(region["id"]), str(region["country_code_3"])))
            self["config"].setList(rl)
            self["description"].setText("")
            curr_region_id = config.plugins.icetv.member.region_id.value
            curr_country_code = config.plugins.icetv.member.country.value
            try:
                    self["config"].moveToIndex(next(i for i, ent in enumerate(rl) if ent[1] == curr_region_id and ent[2] == curr_country_code))
            except StopIteration:
                    pass
            if rl:
                self.have_region_list = True
        except (OSError, RuntimeError) as ex:
            msg = _logResponseException(fetcher, _("Can not download list of regions"), ex)
            self["description"].setText(_("There was an error downloading the region list"))
            self["error"].setText(msg)
            self["error"].show()


class IceTVLogin(Screen, IceTVUIBase):
    skin = """
<screen name="IceTVLogin" position="center,50" size="990,650" title="IceTV - Login" >
    <widget name="instructions" position="20,10" size="950,80" font="Regular;22" />
    <widget name="error" position="30,120" size="930,300" font="Console; 16" zPosition="1" />
    <widget name="qrcode" position="342,90" size="256,256" pixmap="/usr/lib/enigma2/python/Plugins/SystemPlugins/IceTV/de_qr_code.png" zPosition="1" />
    <widget name="message" position="20,360" size="950,250" font="Regular;22" />

    <ePixmap name="green" position="170,e-28" size="15,16" pixmap="skin_default/buttons/button_green.png" alphatest="blend" />
    <widget name="key_red" position="40,e-30" size="150,25" valign="top" halign="left" font="Regular;20" />
    <widget name="key_green" position="190,e-30" size="150,25" valign="top" halign="left" font="Regular;20" />
    <widget name="key_yellow" position="340,e-30" size="150,25" valign="top" halign="left" font="Regular;20" />
    <widget name="key_blue" position="490,e-30" size="150,25" valign="top" halign="left" font="Regular;20" />
</screen>"""

    _instructions = _("Contacting IceTV server and setting up your %s %s.") % getBoxDisplayName()
    _banner = None

    def __init__(self, session):
        self.success = False
        Screen.__init__(self, session)
        IceTVUIBase.__init__(self, title=_("IceTV - Login"))
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
                                       actions={"cancel": self.cancel,
                                                "red": self.cancel,
                                                "green": self.done,
                                                "ok": self.done,
                                                }, prio=-2
                                       )
        self.login_timer = eTimer()
        self.login_timer.callback.append(self.doLogin)
        self.onLayoutFinish.append(self.layoutFinished)

    def cancel(self):
        config.plugins.icetv.member.country.cancel()
        self.done()

    def done(self):
        self.close(self.success)

    def layoutFinished(self):
        qrcode = {
            "AUS": "au_qr_code.png",
            # The German IceTV service has closed down
            # "DEU": "de_qr_code.png",
        }.get(config.plugins.icetv.member.country.value, "au_qr_code.png")
        qrcode_path = resolveFilename(SCOPE_PLUGINS, path.join("SystemPlugins/IceTV", qrcode))
        if path.isfile(qrcode_path):
            self["qrcode"].instance.setPixmap(LoadPixmap(qrcode_path))
        else:
            print("[IceTV] missing QR code file", qrcode_path)

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
            self.success = self.setCountry()
            if not self.success:
                return
            self["instructions"].setText(_("Congratulations, you have successfully configured your %s %s "
                                           "for use with the IceTV Smart Recording service. "
                                           "Your IceTV guide will now download in the background.") % getBoxDisplayName())
            self["message"].setText(_("Everything in one place - IceTV does it for you!\n\n"
                                      "Using the IceTV app or website, 'My Shows' is your place to go to."
                                      " See the next 7 days of your recordings,"
                                      " favorite shows, keyword notifications,"
                                      " new series broadcasts, and our recommendations.\n\n"
                                      "Everything in one place. Simply select something new and press Record.\n\n"
                                      "IceTV's smartphone and tablet apps can be downloaded by scanning the code above."))
            self["qrcode"].show()
            config.plugins.icetv.configured.value = True
            config.plugins.icetv.last_update_time.value = 0
            enableIceTV()
            fetcher.createFetchJob(send_scans=True)
        except (OSError, RuntimeError) as ex:
            msg = _logResponseException(fetcher, _("Login failure"), ex)
            self["instructions"].setText(_("There was an error while trying to login."))
            self["message"].hide()
            self["error"].show()
            self["error"].setText(msg)

    def setCountry(self):
        try:
            res = ice.Region(config.plugins.icetv.member.region_id.value).get().json()
            regions = res["regions"]
            if regions:
                config.plugins.icetv.member.country.value = regions[0]["country_code_3"]
                return True
            else:
                self["instructions"].setText(_("No valid region details were found"))
                return False
        except (OSError, RuntimeError) as ex:
            msg = _logResponseException(fetcher, _("Can not download current region details"), ex)
            self["instructions"].setText(_("There was an error downloading current region details"))
            self["error"].setText(msg)
            self["error"].show()
            return False

    def loginCmd(self):
        ice.Login(config.plugins.icetv.member.email_address.value,
                  config.plugins.icetv.member.password.value).post()


class IceTVCreateLogin(IceTVLogin):

    def __init__(self, session):
        super(IceTVCreateLogin, self).__init__(session)
        self.skinName = self.__class__.__bases__[0].__name__

    def loginCmd(self):
        ice.Login(config.plugins.icetv.member.email_address.value,
                  config.plugins.icetv.member.password.value,
                  config.plugins.icetv.member.region_id.value).post()

    # The country will have been set in IceTVNewUserSetup
    def setCountry(self):
        return True


class IceTVNeedPassword(ConfigListScreen, Screen, IceTVUIBase):
    skin = """
<screen name="IceTVNeedPassword" position="center,center" size="1190,455" title="IceTV - Password required" >
    <widget name="instructions" position="20,10" size="600,100" font="Regular;22" />
    <widget name="config" position="20,120" size="600,100" />

    <widget name="description" position="20,e-90" size="600,60" font="Regular;18" foregroundColor="grey" halign="left" valign="top" />
    <ePixmap pixmap="/usr/lib/enigma2/python/Plugins/SystemPlugins/IceTV/icetv_logo172x100.png" position="804,0" size="172,100" alphatest="on" />
    <widget name="banner" position="630,105" size="520,350" font="Regular;22" valign="center" halign="center" />
    <ePixmap name="red" position="20,e-28" size="15,16" pixmap="skin_default/buttons/button_red.png" alphatest="blend" />
    <ePixmap name="green" position="170,e-28" size="15,16" pixmap="skin_default/buttons/button_green.png" alphatest="blend" />
    <ePixmap name="blue" position="470,e-28" size="15,16" pixmap="skin_default/buttons/button_blue.png" alphatest="blend" />
    <widget name="key_red" position="40,e-30" size="150,25" valign="top" halign="left" font="Regular;20" />
    <widget name="key_green" position="190,e-30" size="150,25" valign="top" halign="left" font="Regular;20" />
    <widget name="key_yellow" position="340,e-30" size="150,25" valign="top" halign="left" font="Regular;20" />
    <widget name="key_blue" position="490,e-30" size="150,25" valign="top" halign="left" font="Regular;20" />
    <widget name="HelpWindow" position="0,10000" size="0,0" zPosition="1" transparent="1" alphatest="blend" />
</screen>"""

    _instructions = _("The IceTV server has requested password for %s.")
    _password = _("Password")
    _update_interval = _("Connect to IceTV server every")

    def __init__(self, session):
        Screen.__init__(self, session)
        # This creates a new instance variable.
        # It doesn't change the class variable of the same name.
        self._instructions = self._instructions % config.plugins.icetv.member.email_address.value
        IceTVUIBase.__init__(self, title=_("IceTV - Password required"), description="")
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
        if isinstance(selection[1], ConfigText):
            self.keyText()

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
        except (OSError, RuntimeError) as ex:
            msg = _logResponseException(fetcher, _("Login failure"), ex)
            self.session.open(MessageBox, msg, type=MessageBox.TYPE_ERROR)

    def loginCmd(self):
        ice.Login(config.plugins.icetv.member.email_address.value,
                  config.plugins.icetv.member.password.value).post()
