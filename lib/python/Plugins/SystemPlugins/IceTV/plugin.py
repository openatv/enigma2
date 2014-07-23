# kate: replace-tabs on; indent-width 4; remove-trailing-spaces all; show-tabs on; newline-at-eof on;

from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Plugins.Plugin import PluginDescriptor
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
        print "[IceTV] sessionstart Here is where we should save the config"
    else:
        print "[IceTV] sessionstart with unknown reason:", reason

def wizard_main(*args, **kwargs):
    print "[IceTV] wizard"
    return Wizpop(*args, **kwargs)

def plugin_main(session, **kwargs):
    session.open(MessageBox, _("IceTV plugin"), MessageBox.TYPE_INFO, timeout = 10)

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
#            icon = "IceTV_icon.png",
            fnc = plugin_main
            ),
        PluginDescriptor(
            name = "IceTV",
            where = PluginDescriptor.WHERE_WIZARD,
            description = _("IceTV"),
            fnc = (95, wizard_main)
            ),
        ]
