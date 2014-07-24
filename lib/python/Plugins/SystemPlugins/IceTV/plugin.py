# kate: replace-tabs on; indent-width 4; remove-trailing-spaces all; show-tabs on; newline-at-eof on;
# -*- coding:utf-8 -*-

from Plugins.Plugin import PluginDescriptor
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Components.Label import Label
from Components.ConfigList import ConfigListScreen
from Components.MenuList import MenuList
from Components.ActionMap import ActionMap
from Components.config import config, configfile, ConfigSubsection, ConfigText, ConfigPassword, ConfigSelection, getConfigListEntry
from Components.Pixmap import Pixmap

config.plugins.icetv = ConfigSubsection()
config.plugins.icetv.email = ConfigText(visible_width=50, fixed_size=False)
config.plugins.icetv.password = ConfigPassword(visible_width=50, fixed_size=False, censor="●")
checktimes = {
    "2 minutes": 2 * 60,
    "5 minutes": 5 * 60,
    "10 minutes": 10 * 60,
    "15 minutes": 15 * 60,
    "30 minutes": 30 * 60,
    "1 hour": 60 * 60,
    "2 hours": 2 * 60 * 60,
    "3 hours": 3 * 60 * 60,
    "4 hours": 4 * 60 * 60,
    "5 hours": 5 * 60 * 60,
    "6 hours": 6 * 60 * 60,
    "7 hours": 7 * 60 * 60,
    "8 hours": 8 * 60 * 60,
    "12 hours": 12 * 60 * 60,
    "24 hours": 24 * 60 * 60,
}
config.plugins.icetv.refresh_interval = ConfigSelection(default="15 minutes", choices=checktimes)

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
            name = "IceTV",
            where = PluginDescriptor.WHERE_AUTOSTART,
            description = _("IceTV"),
            fnc = autostart_main
            ),
        PluginDescriptor(
            name = "IceTV",
            where = PluginDescriptor.WHERE_SESSIONSTART,
            description = _("IceTV"),
            fnc = sessionstart_main
            ),
        PluginDescriptor(
            name = "IceTV",
            where = PluginDescriptor.WHERE_PLUGINMENU,
            description = _("IceTV"),
            icon = "icon.png",
            fnc = plugin_main
            ),
        PluginDescriptor(
            name = "IceTV",
            where = PluginDescriptor.WHERE_WIZARD,
            description = _("IceTV"),
            fnc = (95, wizard_main)
            ),
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
        self.close()

    def newUserClicked(self):
        print "[IceTV] newUserClicked"
        self.close()

    def oldUserClicked(self):
        print "[IceTV] oldUserClicked"
        self.close()


_email = _("Email")
_password = _("Password")

class IceTVNewUserSetup(ConfigListScreen, Screen):
    skin = """
<screen name="IceTVNewUserSetup" position="320,140" size="640,540" title="IceTV - New user" >
    <widget name="instructions" position="20,20" size="600,100" font="Regular;22" />
    <widget name="config" position="20,120" size="600,60" />
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

    instructions = "Please enter your email address. This is required for us to send you service announcements, account reminders and promotional offers."

    def __init__(self, session, args=None):
        self.session = session
        Screen.__init__(self, session)
        self["instructions"] = Label(_(self.instructions))
        self["description"] = Label("Description")
        self["HelpWindow"] = Label()
        self["key_red"] = Label(_("Cancel"))
        self["key_green"] = Label(_("Save"))
        self["key_yellow"] = Label()
        self["key_blue"] = Label(_("Keyboard"))
        self["VKeyIcon"] = Pixmap()
        self.list = []
        self.list.append(getConfigListEntry(_email, config.plugins.icetv.email, _("Your email address is required to create a new IceTV account")))
        self.list.append(getConfigListEntry(_password, config.plugins.icetv.password, _("Choose a password with at least 5 characters")))
        ConfigListScreen.__init__(self, self.list, session)
        self["InusActions"] = ActionMap(contexts=["SetupActions", "ColorActions"],
                                 actions={
                                     "cancel": self.keyCancel,
                                     "red": self.keyCancel,
                                     "green": self.keySave,
                                     "blue": self.KeyText,
                                     }, prio=-2)

    def keyCancel(self):
        sel = self["config"].getCurrent()
        if sel:
            if sel[0] in (_email, _password):
                if sel[1].help_window.instance is not None:
                    sel[1].help_window.hide()
        self.closeMenuList()
