# kate: replace-tabs on; indent-width 4; remove-trailing-spaces all; show-tabs on; newline-at-eof on;
# -*- coding:utf-8 -*-

'''
Copyright (C) 2014 Peter Urbanec
All Right Reserved
License: Proprietary / Commercial - contact enigma.licensing (at) urbanec.net
'''

from enigma import eTimer, eEPGCache
from boxbranding import getMachineBrand, getMachineName
from Components.ActionMap import ActionMap
from Components.ConfigList import ConfigListScreen
from Components.Label import Label
from Components.MenuList import MenuList
from Components.Pixmap import Pixmap
from Components.config import getConfigListEntry
from Plugins.Plugin import PluginDescriptor
from Screens.ChoiceBox import ChoiceBox
from Screens.Screen import Screen
import time
from . import config
import API as ice
from Plugins.SystemPlugins.IceTV import saveConfigFile

_session = None


class IceTVMain(ChoiceBox):

    def __init__(self, session, *args, **kwargs):
        global _session
        if _session is None:
            _session = session
        menu = [("Enable IceTV", "CALLFUNC", enableIceTV),
                ("Disable IceTV", "CALLFUNC", disableIceTV),
                ("Configure IceTV", "CALLFUNC", configIceTV),
                ("Fetch EPG", "CALLFUNC", fetchEpg),
                ]
        super(IceTVMain, self).__init__(session, title=_("IceTV"), list=menu)

    def close(self, retval):
        print "[IceTV] IceTVMain answer was", retval
        super(IceTVMain, self).close()


def enableIceTV(res=None):
    print "[IceTV] enableIceTV"
    config.epg.eit.value = False
    config.epg.save()
    config.plugins.icetv.enable_epg.value = True
    epgcache = eEPGCache.getInstance()
    epgcache.setEpgSources(0)
    epgcache.clear()
    epgcache.save()
    saveConfigFile()


def disableIceTV(res=None):
    print "[IceTV] disableIceTV"
    epgcache = eEPGCache.getInstance()
    epgcache.setEpgSources(0)
    epgcache.clear()
    epgcache.save()
    epgcache.setEpgSources(eEPGCache.NOWNEXT | eEPGCache.SCHEDULE | eEPGCache.SCHEDULE_OTHER)
    config.epg.eit.value = True
    config.epg.save()
    config.plugins.icetv.enable_epg.value = False
    saveConfigFile()


def configIceTV(res=None):
    print "[IceTV] configIceTV"
    _session.open(IceTVUserTypeScreen)


def fetchEpg(res=None):
    print "[IceTV] fetchEpg"
    shows = getShows()
    channel_service_map = makeChanServMap(shows["channels"])
    channel_show_map = makeChanShowMap(shows["shows"])
    epgcache = eEPGCache.getInstance()
    for channel_id in channel_show_map.keys():
        print "[IceTV] inserting %d shows into" % len(channel_show_map[channel_id]), channel_service_map[channel_id]
        print "[IceTV] first one:", channel_show_map[channel_id][0]
        epgcache.importEvents(channel_service_map[channel_id], channel_show_map[channel_id])

def makeChanServMap(channels):
    res = {}
    for channel in channels:
        channel_id = channel["id"]
        for triplet in channel["dvb_triplets"]:
            res.setdefault(channel_id, []).append((int(triplet["original_network_id"]),
                                                   int(triplet["transport_stream_id"]),
                                                   int(triplet["service_id"])))
    return res

def makeChanShowMap(shows):
    res = {}
    for show in shows:
        channel_id = show["channel_id"]
        # Fit within 16 bits, but never pass 0
        event_id = (int(show["id"]) % 65530) + 1
        start = int(time.mktime(time.strptime(show["start"].split("+")[0], "%Y-%m-%dT%H:%M:%S")))
        stop = int(time.mktime(time.strptime(show["stop"].split("+")[0], "%Y-%m-%dT%H:%M:%S")))
        duration = stop - start
        title = show["title"].encode("utf8")
        short = show["subtitle"].encode("utf8")
        extended = show["desc"].encode("utf8")
        res.setdefault(channel_id, []).append((start, duration, title, short, extended, 0, event_id))
    return res


def getShows():
    req = ice.Shows()
    last_update = config.plugins.icetv.last_update_time.value
    req.params["last_update_time"] = last_update
    return req.get().json()


def autostart_main(reason, **kwargs):
    if reason == 0:
        print "[IceTV] autostart start"
    elif reason == 1:
        print "[IceTV] autostart stop"
        print "[IceTV] autostart Here is where we should save the config"
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
    return IceTVMain(*args, **kwargs)


def plugin_main(session, **kwargs):
    global _session
    if _session is None:
        _session = session
    session.open(IceTVMain)


def Plugins(**kwargs):
    return [
        PluginDescriptor(
            name="IceTV",
            where=PluginDescriptor.WHERE_AUTOSTART,
            description=_("IceTV"),
            fnc=autostart_main
        ),
        PluginDescriptor(
            name="IceTV",
            where=PluginDescriptor.WHERE_SESSIONSTART,
            description=_("IceTV"),
            fnc=sessionstart_main
        ),
        PluginDescriptor(
            name="IceTV",
            where=PluginDescriptor.WHERE_PLUGINMENU,
            description=_("IceTV"),
            icon="icon.png",
            fnc=plugin_main
        ),
#         PluginDescriptor(
#             name="IceTV",
#             where=PluginDescriptor.WHERE_WIZARD,
#             description=_("IceTV"),
#             fnc=(95, wizard_main)
#         ),
    ]


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
                      "If you already have an IceTV subscription, please select "
                      "'Existing User', if not, then select 'New User'.")

    def __init__(self, session, args=None):
        self.session = session
        Screen.__init__(self, session)
        self["title"] = Label(_("Welcome to IceTV"))
        self["instructions"] = Label(_(self._instructions))
        options = []
        options.append((_("New User"), "newUser"))
        options.append((_("Existing User"), "oldUser"))
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
                      "service announcements, account reminders and promotional offers.")
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
                                _("Your email address is required to use an IceTV account")),
             getConfigListEntry(self._password, config.plugins.icetv.member.password,
                                _("Choose a password with at least 5 characters")),
             getConfigListEntry(self._label, config.plugins.icetv.device.label,
                                _("Choose a label that will identify this device within IceTV services")),
        ]
        ConfigListScreen.__init__(self, self.list, session)
        self["InusActions"] = ActionMap(contexts=["SetupActions", "ColorActions"],
                                        actions={
                                             "cancel": self.keyCancel,
                                             "red": self.keyCancel,
                                             "green": self.keySave,
                                             "blue": self.KeyText,
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
<screen name="IceTVLogin" position="320,130" size="640,510" title="IceTV - Login" >
    <widget name="instructions" position="20,10" size="600,100" font="Regular;22" />
    <widget name="message" position="30,120" size="580,300" font="Console; 16" zPosition="1" />

    <widget name="description" position="20,e-90" size="600,60" font="Regular;18" foregroundColor="grey" halign="left" valign="top" />
    <ePixmap name="green" position="170,e-28" size="15,16" pixmap="skin_default/buttons/button_green.png" alphatest="blend" />
    <widget name="key_red" position="40,e-30" size="150,25" valign="top" halign="left" font="Regular;20" />
    <widget name="key_green" position="190,e-30" size="150,25" valign="top" halign="left" font="Regular;20" />
    <widget name="key_yellow" position="340,e-30" size="150,25" valign="top" halign="left" font="Regular;20" />
    <widget name="key_blue" position="490,e-30" size="150,25" valign="top" halign="left" font="Regular;20" />
</screen>"""

    _instructions = _("Contacting IceTV server and setting up your %s %s.") % (getMachineBrand(), getMachineName())
    _wait = _("Please wait...")

    def __init__(self, session, args=None):
        self.session = session
        Screen.__init__(self, session)
        self["instructions"] = Label(self._instructions)
        self["description"] = Label(self._wait)
        self["message"] = Label()
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
            self["message"].setText(_("Setup is complete.\n\n"
                                      "Congratulations, you have successfully configured your %s %s "
                                      "for use with the IceTV Smart Recording service.\n\n"
                                      "For more information, visit icetv.com.au\n\n"
                                      "Your IceTV guide will now download in the background.")
                                    % (getMachineBrand(), getMachineName()))
            self["description"].setText("")
        except RuntimeError as ex:
            print "[IceTV] Login failure:", ex
            msg = _("Login failure: ") + str(ex)
            if hasattr(ex, 'response'):
                print "[IceTV] Server says:", ex.response.text
                msg += "\n%s" % str(ex.response.text).strip()
            self["description"].setText(_("There was an error while trying to login."))
            self["message"].setText(msg)

    def loginCmd(self):
        ice.Login(config.plugins.icetv.member.email_address.value,
                  config.plugins.icetv.member.password.value).post()


class IceTVCreateLogin(IceTVLogin):

    def loginCmd(self):
        ice.Login(config.plugins.icetv.member.email_address.value,
                  config.plugins.icetv.member.password.value,
                  config.plugins.icetv.member.region_id.value).post()
