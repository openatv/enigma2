# kate: replace-tabs on; indent-width 4; remove-trailing-spaces all; show-tabs on; newline-at-eof on;
# -*- coding:utf-8 -*-

from enigma import eTimer
from Components.ActionMap import ActionMap
from Components.ConfigList import ConfigListScreen
from Components.Label import Label
from Components.MenuList import MenuList
from Components.Pixmap import Pixmap
from Components.config import getConfigListEntry
from Plugins.Plugin import PluginDescriptor
from Screens.MessageBox import MessageBox
from Screens.Screen import Screen
from . import config
import API as ice


class Wizpop(MessageBox):
    def __init__(self, session, *args, **kwargs):
        super(Wizpop, self).__init__(session, _("Enable IceTV?"))

    def close(self, retval):
        print "[IceTV] Wizpop answer was", retval
        super(Wizpop, self).close()


def autostart_main(reason, **kwargs):
    if reason == 0:
        print "[IceTV] autostart start"
    elif reason == 1:
        print "[IceTV] autostart stop"
        print "[IceTV] autostart Here is where we should save the config"
    else:
        print "[IceTV] autostart with unknown reason:", reason

def sessionstart_main(reason, session, **kwargs):
    if reason == 0:
        print "[IceTV] sessionstart start"
    elif reason == 1:
        print "[IceTV] sessionstart stop"
    else:
        print "[IceTV] sessionstart with unknown reason:", reason

def wizard_main(*args, **kwargs):
    print "[IceTV] wizard"
    return Wizpop(*args, **kwargs)

def plugin_main(session, **kwargs):
    session.open(IceTVUserTypeScreen)

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
<screen name="IceTVUserTypeScreen" position="320,140" size="640,400" title="IceTV - Account selection" >
 <widget position="20,20" size="600,40" name="title" font="Regular;32" />
 <widget position="20,80" size="600,200" name="instructions" font="Regular;22" />
 <widget position="20,300" size="600,100" name="menu" />
</screen>
"""
    instructions = """In order to allow you to access all the features of the IceTV smart recording service, we need to gather some basic information.

If you already have an IceTV subscription, please select 'Existing User', if not, then select 'New User'.
"""

    def __init__(self, session, args=None):
        self.session = session
        Screen.__init__(self, session)
        self["title"] = Label(_("Welcome to IceTV"))
        self["instructions"] = Label(_(self.instructions))
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
        selection = self["menu"].l.getCurrentSelection()
        print "[IceTV] ok - selection: ", selection
        if selection[1] == "newUser":
            self.session.open(IceTVNewUserSetup)
        elif selection[1] == "oldUser":
            self.session.open(IceTVOldUserSetup)
        self.close()


class IceTVNewUserSetup(ConfigListScreen, Screen):
    skin = """
<screen name="IceTVNewUserSetup" position="320,130" size="640,550" title="IceTV - User Information" >
    <widget name="instructions" position="20,10" size="600,100" font="Regular;22" />
    <widget name="config" position="20,110" size="600,75" />

    <widget name="HelpWindow" position="500,320" size="1,1" />

    <widget name="description" position="20,e-100" size="600,70" font="Regular;18" foregroundColor="grey" halign="left" valign="top" />
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

    def hideHelper(self):
        sel = self["config"].getCurrent()
        if sel and sel[1].help_window.instance is not None:
            sel[1].help_window.hide()

    def keyCancel(self):
        self.hideHelper()
        self.closeMenuList()

    def keySave(self):
        self.hideHelper()
        print "[IceTV] new user", self["config"]
        self.session.open(IceTVRegionSetup)


class IceTVOldUserSetup(IceTVNewUserSetup):

    def keySave(self):
        self.hideHelper()
        print "[IceTV] old user", self["config"]
#        self.session.open(IceTVLogin)


class IceTVRegionSetup(Screen):
    skin = """
<screen name="IceTVRegionSetup" position="320,130" size="640,550" title="IceTV - Region" >
    <widget name="instructions" position="20,10" size="600,100" font="Regular;22" />
    <widget name="config" position="30,120" size="580,325" enableWrapAround="1" scrollbarMode="showAlways"/>

    <widget name="description" position="20,e-100" size="600,70" font="Regular;18" foregroundColor="grey" halign="left" valign="top" />
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
        self["key_red"] = Label(_("Cancel"))
        self["key_green"] = Label(_("Save"))
        self["key_yellow"] = Label()
        self["key_blue"] = Label()
        self.regionList = []
        self["config"] = MenuList(self.regionList)
        self["IrsActions"] = ActionMap(contexts=["SetupActions", "ColorActions"],
                                       actions={"cancel": self.keyCancel,
                                                "red": self.keyCancel,
                                                "green": self.keySave,
                                                "ok": self.keySave,
                                                }, prio=-2
                                       )
        self.createTimer = eTimer()
        self.createTimer.callback.append(self.onCreate)
        self.onLayoutFinish.append(self.layoutFinished)

    def layoutFinished(self):
        self.createTimer.start(3)

    def onCreate(self):
        self.createTimer.stop()
        self.getRegionList()

    def keyCancel(self):
        self.close()

    def keySave(self):
        item = self["config"].getCurrent()
        print "[IceTV] region: ", item
#        self.session.open(IceTVCreateLogin)

    def getRegionList(self):
        msg = ""
        rl = []
        try:
            res = ice.Regions().get().json()
            regions = res["regions"]
            for region in regions:
                rl.append((str(region["name"]), int(region["id"])))
        except RuntimeError as ex:
            msg = _("Can not download list of regions: ") + ex
        self["description"].setText(msg)
        self["config"].setList(rl)
