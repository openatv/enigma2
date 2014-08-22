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
from time import strptime
from datetime import datetime
from . import config, saveConfigFile, enableIceTV, disableIceTV
from Components.Task import Job, PythonTask, job_manager
import API as ice
from collections import deque
from Screens.TextBox import TextBox

_session = None


class IceTVMain(ChoiceBox):
    def __init__(self, session, *args, **kwargs):
        global _session
        if _session is None:
            _session = session
        menu = [("Enable IceTV", "CALLFUNC", self.enable),
                ("Disable IceTV", "CALLFUNC", self.disable),
                ("Configure IceTV", "CALLFUNC", self.configure),
                ("Fetch EPG", "CALLFUNC", fetcher.fetchEpg),
                ("Show log", "CALLFUNC", self.showLog),
                ]
        super(IceTVMain, self).__init__(session, title=_("IceTV"), list=menu)

    def enable(self, res=None):
        enableIceTV()
        _session.open(MessageBox, _("IceTV enabled"), type=MessageBox.TYPE_INFO, timeout=5)

    def disable(self, res=None):
        disableIceTV()
        _session.open(MessageBox, _("IceTV disabled"), type=MessageBox.TYPE_INFO, timeout=5)

    def configure(self, res=None):
        _session.open(IceTVUserTypeScreen)



    def showLog(self, res=None):
        _session.open(LogView, "\n".join(fetcher.log))

class LogView(TextBox):
    skin = """<screen name="LogView" backgroundColor="background" position="90,150" size="1100,450" title="Log">
        <widget font="Console;18" name="text" position="0,4" size="1100,446"/>
</screen>"""


class EPGFetcher(object):
    def __init__(self):
        print "[IceTV] Created EPGFetcher"
        self.fetchTimer = eTimer()
        self.fetchTimer.callback.append(self.createFetchJob)
        self.fetchTimer.start(3 * 60 * 1000)

    def createFetchJob(self):
        print "[IceTV] Created EPGFetcher fetch job"
        job = Job(_("IceTV update job"))
        task = PythonTask(job, _("Fetch"))
        task.work = self.doWork
        job_manager.AddJob(job)

    def fetchEpg(self, res=None):
        print "[IceTV] fetchEpg"
        self.doWork()
    def addLog(self, msg):
        self.log.append("%s: %s" % (str(datetime.now()).split(".")[0], msg))


    def doWork(self):
        print "[IceTV] EPGFetcher doWork()"
        self.addLog("Start update")
        try:
            shows = self.getShows()
            channel_service_map = self.makeChanServMap(shows["channels"])
            channel_show_map = self.makeChanShowMap(shows["shows"])
            epgcache = eEPGCache.getInstance()
            for channel_id in channel_show_map.keys():
                print "[IceTV] inserting %d shows into" % len(channel_show_map[channel_id]), channel_service_map[channel_id]
                print "[IceTV] first one:", channel_show_map[channel_id][0]
                epgcache.importEvents(channel_service_map[channel_id], channel_show_map[channel_id])
            epgcache.save()
            if "last_update_time" in shows:
                config.plugins.icetv.last_update_time.value = shows["last_update_time"]
                saveConfigFile()
            self.addLog("EPG download OK")
            if "timers" in shows:
                self.processTimers(shows["timers"])
            self.addLog("End update")
            return
        except RuntimeError as ex:
            print "[IceTV] Can not download EPG:", ex
            self.addLog("Can not download EPG: " + str(ex))
        try:
            timers = self.getTimers()
            self.processTimers(timers)
            self.addLog("End update")
        except RuntimeError as ex:
            print "[IceTV] Can not download timers:", ex
            self.addLog("Can not download timers: " + str(ex))

    def makeChanServMap(self, channels):
        res = {}
        for channel in channels:
            channel_id = long(channel["id"])
            triplets = []
            if "dvb_triplets" in channel:
                triplets = channel["dvb_triplets"]
            elif "dvbt_info" in channel:
                triplets = channel["dvbt_info"]
            for triplet in triplets:
                res.setdefault(channel_id, []).append((int(triplet["original_network_id"]),
                                                       int(triplet["transport_stream_id"]),
                                                       int(triplet["service_id"])))
        return res

    def makeChanShowMap(self, shows):
        res = {}
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
            res.setdefault(channel_id, []).append((start, duration, title, short, extended, 0, event_id))
        return res

    def processTimers(self, timers):
        update_queue = []
        channel_service_map = self.makeChanServMap(self.getChannels())
        for iceTimer in timers:
            print "[IceTV] iceTimer:", iceTimer
            try:
                action = iceTimer.get("action", "").encode("utf8")
                state = iceTimer.get("state", "").encode("utf8")
                name = iceTimer.get("name", "").encode("utf8")
                start = int(timegm(strptime(iceTimer["start_time"].split("+")[0], "%Y-%m-%dT%H:%M:%S")))
                duration = 60 * int(iceTimer["duration_minutes"])
                message = iceTimer.get("message", "").encode("utf8")
                iceTimerId = iceTimer["id"].encode("utf8")
                if action == "forget":
                    for timer in _session.nav.RecordTimer.timer_list:
                        if timer.iceTimerId == iceTimerId:
                            print "[IceTV] removing timer:", timer
                            _session.nav.RecordTimer.removeEntry(timer)
                    iceTimer["state"] = "completed"
                    update_queue.append(iceTimer)
                else:
                    completed = False
                    for timer in _session.nav.RecordTimer.processed_timers:
                        if timer.iceTimerId == iceTimerId:
                            print "[IceTV] completed timer:", timer
                            iceTimer["state"] = "completed"
                            update_queue.append(iceTimer)
                            completed = True
                    # Create or update iceTimer
                    updated = False
                    if not completed:
                        for timer in _session.nav.RecordTimer.timer_list:
                            if timer.iceTimerId == iceTimerId:
                                print "[IceTV] updating timer:", timer
                                # TODO: Update and run sanity checks see TimerEdit.finishedEdit
                                _session.nav.RecordTimer.timeChanged(timer)
                                iceTimer["state"] = "pending"
                                update_queue.append(iceTimer)
                                updated = True
                    created = False
                    if not completed and not updated:
                        channel_id = long(iceTimer["channel_id"])
                        channels = channel_service_map[channel_id]
                        print "[IceTV] channel_id %s maps to" % channel_id, channels
                        db = eDVBDB.getInstance()
                        for channel in channels:
                            serviceref = ServiceReference("1:0:1:%x:%x:%x:EEEE0000:0:0:0:" % (channel[2], channel[1], channel[0]))
                            if db.isValidService(channel[1], channel[0], channel[2]):
                                print "[IceTV] %s is valid" % str(serviceref), serviceref.getServiceName()
                                recording = RecordTimerEntry(serviceref, start, start + duration, name, message, None, iceTimerId=iceTimerId)
                                conflicts = _session.nav.RecordTimer.record(recording)
                                if conflicts is None:
                                    print "[IceTV] Timer added to service:", serviceref
                                    iceTimer["state"] = "pending"
                                    update_queue.append(iceTimer)
                                    created = True
                                    break
                                else:
                                    print "[IceTV] Timer conflict / bad service:", conflicts
                            else:
                                print "[IceTV] %s is NOT valid" % str(serviceref)
                    if not completed and not updated and not created:
                        iceTimer["state"] = "failed"
                        update_queue.append(iceTimer)
            except (RuntimeError, KeyError) as ex:
                print "[IceTV] Can not process iceTimer:", ex
        # Now send back updated timer states
        try:
            self.putTimers(update_queue)
            self.addLog("Timers updated OK")
        except (RuntimeError, KeyError) as ex:
            print "[IceTV] Can not update server timers:", ex
            self.addLog("Can not update server timers: " + str(ex))

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
        print "[IceTV] get timers:", res
        return res.get("timers", [])

    def putTimers(self, timers):
        req = ice.Timers()
        req.data["timers"] = timers
        res = req.put()
        print "[IceTV] put timers:", res

fetcher = EPGFetcher()

def autostart_main(reason, **kwargs):
    if reason == 0:
        print "[IceTV] autostart start"
    elif reason == 1:
        print "[IceTV] autostart stop"
    else:
        print "[IceTV] autostart with unknown reason:", reason


def sessionstart_main(reason, session, **kwargs):
    global _session
    if reason == 0:
        print "[IceTV] sessionstart start"
        if _session is None:
            _session = session
    elif reason == 1:
        print "[IceTV] sessionstart stop"
        _session = None
    else:
        print "[IceTV] sessionstart with unknown reason:", reason


def wizard_main(*args, **kwargs):
    print "[IceTV] wizard"
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
            where=PluginDescriptor.WHERE_AUTOSTART,
            description=_("IceTV"),
            fnc=autostart_main
        ))
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
            description=_("IceTV"),
            icon="icon.png",
            fnc=plugin_main
        ))
    if not config.plugins.icetv.configured.value:
        # TODO: Check that we have networking
        res.append(
            PluginDescriptor(
                name="IceTV",
                where=PluginDescriptor.WHERE_WIZARD,
                description=_("IceTV"),
                fnc=(95, wizard_main)
            ))
    return res


class IceTVSelectProviderScreen(Screen):
    skin = """
<screen name="IceTVSelectProviderScreen" position="320,130" size="640,400" title="Select EPG provider" >
 <widget position="20,20" size="600,280" name="instructions" font="Regular;20" />
 <widget position="20,300" size="600,100" name="menu" />
</screen>
"""
    _instructions = _("IceTV will change the way you watch TV! IceTV gives you the power to "
                      "discover and manage programmes you want to see. Build your own playlists "
                      "of TV Shows based on the series and favourites you are interested in "
                      "and, when they air, IceTV will take care of the rest. You can set TV "
                      "show recordings from wherever you are. Whether you're sitting in front "
                      "of the TV, on the bus or on holidays overseas. With IceTV choose the "
                      "show you want to record and press 'record'. Simple!\n\n"
                      "Free To Air - Basic EPG as broadcast by the TV stations."
                      )

    def __init__(self, session, args=None):
        self.session = session
        Screen.__init__(self, session)
        self["instructions"] = Label(_(self._instructions))
        options = []
        options.append((_("IceTV (with free trial)"), "iceEpg"))
        options.append((_("Free To Air"), "eitEpg"))
        self["menu"] = MenuList(options)
        self["aMap"] = ActionMap(contexts=["OkCancelActions", "DirectionActions"],
                                 actions={
                                     "cancel": self.cancel,
                                     "ok": self.ok,
                                 }, prio=-1)

    def cancel(self):
        self.close()

    def ok(self):
        selection = self["menu"].getCurrent()
        print "[IceTV] ok - selection: ", selection
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
        self.close()

    def ok(self):
        selection = self["menu"].getCurrent()
        print "[IceTV] ok - selection: ", selection
        if selection[1] == "newUser":
            self.session.open(IceTVNewUserSetup)
        elif selection[1] == "oldUser":
            self.session.open(IceTVOldUserSetup)
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
                                _("Choose a password with at least 5 characters.")),
             getConfigListEntry(self._label, config.plugins.icetv.device.label,
                                _("Choose a label that will identify this device within IceTV services.")),
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
        print "[IceTV] new user", self["config"]
        self.saveAll()
        self.session.open(IceTVRegionSetup)
        self.close()


class IceTVOldUserSetup(IceTVNewUserSetup):

    def keySave(self):
        print "[IceTV] old user", self["config"]
        self.saveAll()
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
                                       actions={"cancel": self.close,
                                                "red": self.close,
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

    def save(self):
        item = self["config"].getCurrent()
        print "[IceTV] region: ", item
        config.plugins.icetv.member.region_id.value = item[1]
        config.plugins.icetv.member.region_id.save()
        self.session.open(IceTVCreateLogin)
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
        except RuntimeError as ex:
            print "[IceTV] Can not download list of regions:", ex
            msg = _("Can not download list of regions: ") + str(ex)
            if hasattr(ex, 'response'):
                print "[IceTV] Server says:", ex.response.text
                msg += "\n%s" % str(ex.response.text).strip()
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
        except RuntimeError as ex:
            print "[IceTV] Login failure:", ex
            msg = _("Login failure: ") + str(ex)
            if hasattr(ex, 'response'):
                print "[IceTV] Server says:", ex.response.text
                msg += "\n%s" % str(ex.response.text).strip()
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
