# kate: replace-tabs on; indent-width 4; remove-trailing-spaces all; show-tabs on; newline-at-eof on;
# -*- coding:utf-8 -*-

'''
Copyright (C) 2014 Peter Urbanec
All Right Reserved
License: Proprietary / Commercial - contact enigma.licensing (at) urbanec.net
'''

from enigma import eTimer, eEPGCache, eDVBDB
from boxbranding import getMachineBrand, getMachineName
from Components.ActionMap import ActionMap
from Components.ConfigList import ConfigListScreen
from Components.Label import Label
from Components.MenuList import MenuList
from Components.Pixmap import Pixmap
from Components.config import getConfigListEntry
from Plugins.Plugin import PluginDescriptor
from Screens.ChoiceBox import ChoiceBox
from Screens.MessageBox import MessageBox
from Screens.Screen import Screen
from RecordTimer import RecordTimerEntry
from ServiceReference import ServiceReference
from calendar import timegm
from time import strptime, sleep, gmtime, strftime
from datetime import datetime
from . import config, saveConfigFile, enableIceTV, disableIceTV
from Components.Task import Job, PythonTask, job_manager
import API as ice
from collections import deque, defaultdict
from Screens.TextBox import TextBox
from Components.TimerSanityCheck import TimerSanityCheck

_session = None
passwordRequested = False

class EPGFetcher(object):
    def __init__(self):
        self.fetchTimer = eTimer()
        self.fetchTimer.callback.append(self.createFetchJob)
        config.plugins.icetv.refresh_interval.addNotifier(self.freqChanged, initial_call=False, immediate_feedback=False)
        self.fetchTimer.start(int(config.plugins.icetv.refresh_interval.value) * 1000)
        self.log = deque(maxlen=40)
        self.added_timers = []
        _session.nav.RecordTimer.onTimerAdded.append(self.onTimerAdded)
        self.deleted_timers = []
        _session.nav.RecordTimer.onTimerRemoved.append(self.onTimerRemoved)
        self.addLog("IceTV started")

    def onTimerAdded(self, entry):
        # print "[IceTV] timer added: ", entry
        if entry.iceTimerId is None and not entry.isAutoTimer:
            self.added_timers.append(entry)

    def onTimerRemoved(self, entry):
        # print "[IceTV] timer removed: ", entry
        if entry in self.added_timers:
            self.added_timers.remove(entry)
        if entry.iceTimerId:
            self.deleted_timers.append(entry.iceTimerId)

    def freqChanged(self, refresh_interval):
        self.fetchTimer.stop()
        self.fetchTimer.start(int(refresh_interval.value) * 1000)

    def addLog(self, msg):
        self.log.append("%s: %s" % (str(datetime.now()).split(".")[0], msg))

    def createFetchJob(self, res=None):
        if config.plugins.icetv.configured.value and config.plugins.icetv.enable_epg.value:
            global passwordRequested
            if passwordRequested:
                self.addLog("Can not proceed - you need to login first")
                return
            job = Job(_("IceTV update job"))
            task = PythonTask(job, _("Fetch"))
            task.work = self.work
            job_manager.AddJob(job)

    def work(self):
        self.doWork()

    def doWork(self):
        global passwordRequested
        self.addLog("Start update")
        if passwordRequested:
            self.addLog("Can not proceed - you need to login first")
            return False
        if not ice.have_credentials():
            passwordRequested = True
            self.addLog("No token, requesting password...")
            _session.open(IceTVNeedPassword)
            if not ice.have_credentials():
                return False
        res = True
        try:
            channel_service_map = self.makeChanServMap(self.getChannels())
        except (IOError, RuntimeError, KeyError) as ex:
            msg = "Can not retrieve channel map: " + str(ex)
            if hasattr(ex, 'response'):
                msg += "\n%s" % str(ex.response.text).strip()
            self.addLog(msg)
            return False
        # Delete iceTimers
        for iceTimerId in self.deleted_timers[:]:
            try:
                print "[IceTV] deleting timer:", iceTimerId
                self.deleteTimer(iceTimerId)
            except (IOError, RuntimeError, KeyError) as ex:
                msg = "Can not delete timer: " + str(ex)
                if hasattr(ex, 'response'):
                    msg += "\n%s" % str(ex.response.text).strip()
                self.addLog(msg)
                res = False
            self.deleted_timers.remove(iceTimerId)
        # Upload locally added timers
        for local_timer in self.added_timers[:]:
            try:
                print "[IceTV] uploading new timer:", local_timer
                res = self.postTimer(local_timer, channel_service_map)
#                local_timer.iceTimerId = res[0]["id"]
            except (IOError, RuntimeError, KeyError) as ex:
                msg = "Can not upload timer: " + str(ex)
                if hasattr(ex, 'response'):
                    msg += "\n%s" % str(ex.response.text).strip()
                self.addLog(msg)
                res = False
            self.added_timers.remove(local_timer)
        try:
            shows = self.getShows()
            channel_show_map = self.makeChanShowMap(shows["shows"])
            epgcache = eEPGCache.getInstance()
            for channel_id in channel_show_map.keys():
                if channel_id in channel_service_map:
                    epgcache.importEvents(channel_service_map[channel_id], channel_show_map[channel_id])
            epgcache.save()
            if "last_update_time" in shows:
                config.plugins.icetv.last_update_time.value = shows["last_update_time"]
                saveConfigFile()
            self.addLog("EPG download OK")
            if "timers" in shows:
                res = self.processTimers(shows["timers"], channel_service_map)
            self.addLog("End update")
            return res
        except (IOError, RuntimeError) as ex:
            msg = "Can not download EPG: " + str(ex)
            if hasattr(ex, 'response'):
                msg += "\n%s" % str(ex.response.text).strip()
            self.addLog(msg)
            res = False
        try:
            ice_timers = self.getTimers()
            if not self.processTimers(ice_timers, channel_service_map):
                res = False
            self.addLog("End update")
        except (IOError, RuntimeError) as ex:
            msg = "Can not download timers: " + str(ex)
            if hasattr(ex, 'response'):
                msg += "\n%s" % str(ex.response.text).strip()
            self.addLog(msg)
            res = False
        if not ice.have_credentials() and not passwordRequested:
            passwordRequested = True
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

    def serviceToIceChannelId(self, serviceref, channel_service_map):
        svc = str(serviceref).split(":")
        triplet = (int(svc[5], 16), int(svc[4], 16), int(svc[3], 16))
        for channel_id, dvbt in channel_service_map.iteritems():
            if triplet in dvbt:
                return channel_id

    def makeChanShowMap(self, shows):
        res = defaultdict(list)
        for show in shows:
            channel_id = long(show["channel_id"])
            # Fit within 16 bits, but never pass 0
            event_id = (int(show["id"]) % 65530) + 1
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
            res[channel_id].append((start, duration, title, short, extended, 0, event_id))
        return res

    def processTimers(self, timers, channel_service_map):
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
                message = iceTimer.get("message", "").encode("utf8")
                iceTimerId = iceTimer["id"].encode("utf8")
                if action == "forget":
                    for timer in _session.nav.RecordTimer.timer_list:
                        if timer.iceTimerId == iceTimerId:
                            # print "[IceTV] removing timer:", timer
                            _session.nav.RecordTimer.removeEntry(timer)
                    iceTimer["state"] = "completed"
                    iceTimer["message"] = "Removed"
                    update_queue.append(iceTimer)
                elif channel_id in channel_service_map:
                    completed = False
                    for timer in _session.nav.RecordTimer.processed_timers:
                        if timer.iceTimerId == iceTimerId:
                            # print "[IceTV] completed timer:", timer
                            iceTimer["state"] = "completed"
                            iceTimer["message"] = "Done"
                            update_queue.append(iceTimer)
                            completed = True
                    updated = False
                    if not completed:
                        for timer in _session.nav.RecordTimer.timer_list:
                            if timer.iceTimerId == iceTimerId:
                                # print "[IceTV] updating timer:", timer
                                if self.updateTimer(timer, name, start, duration, channel_service_map[channel_id]):
                                    if not self.modifyTimer(timer):
                                        _session.nav.RecordTimer.removeEntry(timer)
                                        iceTimer["state"] = "failed"
                                        iceTimer["message"] = "Failed to update the timer"
                                    else:
                                        iceTimer["state"] = "pending"
                                        iceTimer["message"] = "Updated"
                                else:
                                    iceTimer["state"] = "pending"
                                    iceTimer["message"] = "Up to date"
                                if timer.isRunning():
                                    iceTimer["state"] = "running"
                                    iceTimer["message"] = "Recording"
                                update_queue.append(iceTimer)
                                updated = True
                    created = False
                    if not completed and not updated:
                        channels = channel_service_map[channel_id]
                        # print "[IceTV] channel_id %s maps to" % channel_id, channels
                        db = eDVBDB.getInstance()
                        for channel in channels:
                            serviceref = ServiceReference("1:0:1:%x:%x:%x:EEEE0000:0:0:0:" % (channel[2], channel[1], channel[0]))
                            if db.isValidService(channel[1], channel[0], channel[2]):
                                # print "[IceTV] %s is valid" % str(serviceref), serviceref.getServiceName()
                                recording = RecordTimerEntry(serviceref, start, start + duration, name, name, None, iceTimerId=iceTimerId)
                                conflicts = _session.nav.RecordTimer.record(recording)
                                if conflicts is None:
                                    iceTimer["state"] = "pending"
                                    iceTimer["message"] = "Added"
                                    update_queue.append(iceTimer)
                                    created = True
                                    break
                                else:
                                    print "[IceTV] Timer conflict:", conflicts
                                    iceTimer["state"] = "failed"
                                    iceTimer["message"] = "Timer conflict"
                            else:
                                iceTimer["state"] = "failed"
                                iceTimer["message"] = "No matching service"
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
            msg = "Can not update timers: " + str(ex)
            if hasattr(ex, 'response'):
                msg += "\n%s" % str(ex.response.text).strip()
            self.addLog(msg)
            res = False
        return res

    def isIceTimerInUpdateQueue(self, iceTimer, update_queue):
        iceTimerId = iceTimer["id"].encode("utf8")
        for timer in update_queue:
            if iceTimerId == timer["id"].encode("utf8"):
                return True
        return False

    def isIceTimerInLocalTimerList(self, iceTimer, ignoreCompleted=False):
        iceTimerId = iceTimer["id"].encode("utf8")
        for timer in _session.nav.RecordTimer.timer_list:
            if timer.iceTimerId == iceTimerId:
                return True
        if not ignoreCompleted:
            for timer in _session.nav.RecordTimer.processed_timers:
                if timer.iceTimerId == iceTimerId:
                    return True
        return False

    def updateTimer(self, timer, name, start, duration, channels):
        changed = False
        db = eDVBDB.getInstance()
        for channel in channels:
            serviceref = ServiceReference("1:0:1:%x:%x:%x:EEEE0000:0:0:0:" % (channel[2], channel[1], channel[0]))
            if db.isValidService(channel[1], channel[0], channel[2]):
                if str(timer.service_ref) != str(serviceref):
                    changed = True
                    timer.service_ref = serviceref
                break
        if timer.name != name:
            changed = True
            timer.name = name
        if timer.begin != start:
            changed = True
            timer.begin = start
        end = start + duration
        if timer.end != end:
            changed = True
            timer.end = end
        return changed

    def modifyTimer(self, timer):
        timersanitycheck = TimerSanityCheck(self._session.nav.RecordTimer.timer_list, timer)
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
            self._session.nav.RecordTimer.timeChanged(timer)
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

    def postTimer(self, local_timer, channel_service_map):
        channel_id = self.serviceToIceChannelId(local_timer.service_ref, channel_service_map)
        req = ice.Timers()
        req.data["name"] = local_timer.name
        req.data["message"] = "Created by %s" % config.plugins.icetv.device.label.value
        req.data["action"] = "record"
        req.data["state"] = "pending"
        if local_timer.isRunning():
            req.data["state"] = "running"
        req.data["device_id"] = config.plugins.icetv.device.id.value
        req.data["channel_id"] = channel_id
        req.data["start_time"] = strftime("%Y-%m-%dT%H:%M:%S+00:00", gmtime(local_timer.begin))
        req.data["duration_minutes"] = (local_timer.end - local_timer.begin) / 60
        res = req.post()
#        return res.json().get("timers", [])
# The API spec says we'll get a dict with "timers" that will have a list of timers.
# In reality all that the server returns is an empty list "[]"
        return res.json()

    def deleteTimer(self, iceTimerId):
        req = ice.Timer(iceTimerId)
        req.delete()

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
        fetcher.fetchTimer.stop()
        fetcher = None


def wizard_main(*args, **kwargs):
    # TODO: Check that we have networking
    return IceTVSelectProviderScreen(*args, **kwargs)


def plugin_main(session, **kwargs):
    global _session
    if _session is None:
        _session = session
    session.open(IceTVMain)


def Plugins(**kwargs):
    res = []
    res.append(
        PluginDescriptor(
            name="IceTV",
            where=PluginDescriptor.WHERE_SESSIONSTART,
            description=_("IceTV"),
            fnc=sessionstart_main
        ))
    res.append(
        PluginDescriptor(
            name="IceTV",
            where=PluginDescriptor.WHERE_PLUGINMENU,
            description=_("IceTV version %s" % ice._version_string),
            icon="icon.png",
            fnc=plugin_main
        ))
    if not config.plugins.icetv.configured.value:
        res.append(
            PluginDescriptor(
                name="IceTV",
                where=PluginDescriptor.WHERE_WIZARD,
                description=_("IceTV"),
                fnc=(95, wizard_main)
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
                ("Login to IceTV server", "CALLFUNC", self.login),
                ("Configure IceTV", "CALLFUNC", self.configure),
                ("Enable IceTV", "CALLFUNC", self.enable),
                ("Disable IceTV", "CALLFUNC", self.disable),
               ]
        super(IceTVMain, self).__init__(session, title=_("IceTV version %s" % ice._version_string), list=menu)

    def enable(self, res=None):
        enableIceTV()
        _session.open(MessageBox, _("IceTV enabled"), type=MessageBox.TYPE_INFO, timeout=5)

    def disable(self, res=None):
        disableIceTV()
        _session.open(MessageBox, _("IceTV disabled"), type=MessageBox.TYPE_INFO, timeout=5)

    def configure(self, res=None):
        _session.open(IceTVUserTypeScreen)

    def fetch(self, res=None):
        if fetcher.doWork():
            _session.open(MessageBox, _("IceTV update completed OK"), type=MessageBox.TYPE_INFO, timeout=5)
        else:
            _session.open(MessageBox, _("IceTV update completed with errors.\n\nPlease check the log for details."), type=MessageBox.TYPE_ERROR, timeout=15)

    def login(self, res=None):
        _session.open(IceTVNeedPassword)

    def showLog(self, res=None):
        _session.open(LogView, "\n".join(fetcher.log))


class LogView(TextBox):
    skin = """<screen name="LogView" backgroundColor="background" position="90,150" size="1100,450" title="Log">
        <widget font="Console;18" name="text" position="0,4" size="1100,446"/>
</screen>"""


class IceTVSelectProviderScreen(Screen):
    skin = """
<screen name="IceTVSelectProviderScreen" position="280,140" size="720,410" title="Select TV guide provider" >
 <widget position="20,10" size="680,330" name="instructions" font="Regular;20" />
 <widget position="20,350" size="680,60" name="menu" />
</screen>
"""
    _instructions = _("IceTV  (Requires permanent Internet connection)\n\n"
                      "IceTV is a third party TV guide provider that gives your %(brand)s %(box)s "
                      "a total smart recording solution for a small monthly fee. "
                      "Build your own play lists of your favourite shows and series via your "
                      "computer, smart phone or tablet and IceTV will automatically set your %(box)s "
                      "to record them every time they air. Your %(box)s includes a free 3 month "
                      "IceTV subscription.\n\n\n\n"
                      "Free to air TV Guide  (No Internet connection required)\n\n"
                      "This is the Free To Air TV guide, broadcast by the TV stations and "
                      "received by your %(brand)s %(box)s via your TV antenna."
                      ) % {"brand": getMachineBrand(), "box": getMachineName()}

    def __init__(self, session, args=None):
        self.session = session
        Screen.__init__(self, session)
        self["instructions"] = Label(_(self._instructions))
        options = []
        options.append((_("IceTV (with free trial)\t- Requires Internet connection"), "iceEpg"))
        options.append((_("Free To Air               \t- No Internet connection required"), "eitEpg"))
        self["menu"] = MenuList(options)
        self["aMap"] = ActionMap(contexts=["OkCancelActions", "DirectionActions"],
                                 actions={
                                     "cancel": self.cancel,
                                     "ok": self.ok,
                                 }, prio=-1)
        sleep(2)    # Prevent display corruption if the screen is displayed too soon after enigma2 start up

    def cancel(self):
        self.hide()
        self.close()

    def ok(self):
        self.hide()
        selection = self["menu"].getCurrent()
        if selection[1] == "eitEpg":
            config.plugins.icetv.configured.value = True
            config.plugins.icetv.configured.save()
            disableIceTV()
        elif selection[1] == "iceEpg":
            enableIceTV()
            self.session.open(IceTVUserTypeScreen)
        self.close()


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

    def __init__(self, session, args=None):
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
        self.hide()
        self.close()

    def ok(self):
        selection = self["menu"].getCurrent()
        if selection[1] == "newUser":
            self.session.open(IceTVNewUserSetup)
        elif selection[1] == "oldUser":
            self.session.open(IceTVOldUserSetup)
        self.hide()
        self.close()


class IceTVNewUserSetup(ConfigListScreen, Screen):
    skin = """
<screen name="IceTVNewUserSetup" position="320,230" size="640,310" title="IceTV - User Information" >
    <widget name="instructions" position="20,10" size="600,100" font="Regular;22" />
    <widget name="config" position="20,120" size="600,100" />

    <widget name="description" position="20,e-90" size="600,60" font="Regular;18" foregroundColor="grey" halign="left" valign="top" />
    <ePixmap name="red" position="20,e-28" size="15,16" pixmap="skin_default/buttons/button_red.png" alphatest="blend" />
    <ePixmap name="green" position="170,e-28" size="15,16" pixmap="skin_default/buttons/button_green.png" alphatest="blend" />
    <widget name="VKeyIcon" position="470,e-28" size="15,16" pixmap="skin_default/buttons/button_blue.png" alphatest="blend" />
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

    def __init__(self, session, args=None):
        self.session = session
        Screen.__init__(self, session)
        self["instructions"] = Label(self._instructions)
        self["description"] = Label()
        self["HelpWindow"] = Label()
        self["key_red"] = Label(_("Cancel"))
        self["key_green"] = Label(_("Save"))
        self["key_yellow"] = Label()
        self["key_blue"] = Label(_("Keyboard"))
        self["VKeyIcon"] = Pixmap()
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
                                             "cancel": self.keyCancel,
                                             "red": self.keyCancel,
                                             "green": self.keySave,
                                             "blue": self.KeyText,
                                             "ok": self.KeyText,
                                         }, prio=-2)

    def keySave(self):
        self.saveAll()
        self.hide()
        self.session.open(IceTVRegionSetup)
        self.close()


class IceTVOldUserSetup(IceTVNewUserSetup):

    def keySave(self):
        self.saveAll()
        self.hide()
        self.session.open(IceTVLogin)
        self.close()


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

    def __init__(self, session, args=None):
        self.session = session
        Screen.__init__(self, session)
        self["instructions"] = Label(self._instructions)
        self["description"] = Label(self._wait)
        self["error"] = Label()
        self["error"].hide()
        self["key_red"] = Label(_("Cancel"))
        self["key_green"] = Label(_("Save"))
        self["key_yellow"] = Label()
        self["key_blue"] = Label()
        self.regionList = []
        self["config"] = MenuList(self.regionList)
        self["IrsActions"] = ActionMap(contexts=["SetupActions", "ColorActions"],
                                       actions={"cancel": self.cancel,
                                                "red": self.cancel,
                                                "green": self.save,
                                                "ok": self.save,
                                                }, prio=-2
                                       )
        self.createTimer = eTimer()
        self.createTimer.callback.append(self.onCreate)
        self.onLayoutFinish.append(self.layoutFinished)

    def layoutFinished(self):
        self.createTimer.start(3, True)

    def onCreate(self):
        self.createTimer.stop()
        self.getRegionList()

    def cancel(self):
        self.hide()
        self.close()

    def save(self):
        item = self["config"].getCurrent()
        config.plugins.icetv.member.region_id.value = item[1]
        config.plugins.icetv.member.region_id.save()
        self.session.open(IceTVCreateLogin)
        self.hide()
        self.close()

    def getRegionList(self):
        try:
            res = ice.Regions().get().json()
            regions = res["regions"]
            rl = []
            for region in regions:
                rl.append((str(region["name"]), int(region["id"])))
            self["config"].setList(rl)
            self["description"].setText("")
        except (IOError, RuntimeError) as ex:
            msg = "Can not download list of regions: " + str(ex)
            if hasattr(ex, 'response'):
                msg += "\n%s" % str(ex.response.text).strip()
            fetcher.addLog(msg)
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

    def __init__(self, session, args=None):
        self.session = session
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
                                       actions={"cancel": self.close,
                                                "red": self.close,
                                                "green": self.close,
                                                "ok": self.close,
                                                }, prio=-2
                                       )
        self.createTimer = eTimer()
        self.createTimer.callback.append(self.onCreate)
        self.onLayoutFinish.append(self.layoutFinished)

    def layoutFinished(self):
        self.createTimer.start(3, True)

    def onCreate(self):
        self.createTimer.stop()
        self.doLogin()

    def doLogin(self):
        try:
            if ice.have_credentials():
                ice.Logout().delete()
        except:
            # Failure to logout is not a show-stopper
            pass
        try:
            self.loginCmd()
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
            config.plugins.icetv.configured.save()
            fetcher.createFetchJob()
        except (IOError, RuntimeError) as ex:
            msg = "Login failure: " + str(ex)
            if hasattr(ex, 'response'):
                msg += "\n%s" % str(ex.response.text).strip()
            fetcher.addLog(msg)
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
    <widget name="VKeyIcon" position="470,e-28" size="15,16" pixmap="skin_default/buttons/button_blue.png" alphatest="blend" />
    <widget name="key_red" position="40,e-30" size="150,25" valign="top" halign="left" font="Regular;20" />
    <widget name="key_green" position="190,e-30" size="150,25" valign="top" halign="left" font="Regular;20" />
    <widget name="key_yellow" position="340,e-30" size="150,25" valign="top" halign="left" font="Regular;20" />
    <widget name="key_blue" position="490,e-30" size="150,25" valign="top" halign="left" font="Regular;20" />
</screen>"""

    _instructions = _("The IceTV server has requested password for %s.") % config.plugins.icetv.member.email_address.value
    _password = _("Password")
    _update_interval = _("Connect to IceTV server every")

    def __init__(self, session, args=None):
        self.session = session
        Screen.__init__(self, session)
        self["instructions"] = Label(self._instructions)
        self["description"] = Label()
        self["key_red"] = Label(_("Cancel"))
        self["key_green"] = Label(_("Login"))
        self["key_yellow"] = Label()
        self["key_blue"] = Label(_("Keyboard"))
        self["VKeyIcon"] = Pixmap()
        self.list = [
             getConfigListEntry(self._password, config.plugins.icetv.member.password,
                                _("Your existing IceTV password.")),
             getConfigListEntry(self._update_interval, config.plugins.icetv.refresh_interval,
                                _("Choose how often to connect to IceTV server to check for updates.")),
        ]
        ConfigListScreen.__init__(self, self.list, session)
        self["InpActions"] = ActionMap(contexts=["SetupActions", "ColorActions"],
                                       actions={
                                             "cancel": self.keyCancel,
                                             "red": self.keyCancel,
                                             "green": self.doLogin,
                                             "blue": self.KeyText,
                                             "ok": self.KeyText,
                                         }, prio=-2)

    def doLogin(self):
        self.saveAll()
        try:
            self.loginCmd()
            self.hide()
            self.close()
            global passwordRequested
            passwordRequested = False
            fetcher.addLog("Login OK")
            fetcher.createFetchJob()
        except (IOError, RuntimeError) as ex:
            msg = "Login failure: " + str(ex)
            if hasattr(ex, 'response'):
                msg += "\n%s" % str(ex.response.text).strip()
            fetcher.addLog(msg)
            self.session.open(MessageBox, _(msg), type=MessageBox.TYPE_ERROR)
            fetcher.addLog(msg)

    def loginCmd(self):
        ice.Login(config.plugins.icetv.member.email_address.value,
                  config.plugins.icetv.member.password.value).post()
