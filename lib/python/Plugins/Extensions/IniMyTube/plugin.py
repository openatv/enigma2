from . import _

from Plugins.Plugin import PluginDescriptor
from MyTubeService import validate_cert
from enigma import eTPM
from Components.config import ConfigSubsection, config, ConfigYesNo

config.plugins.mytubestart = ConfigSubsection()
config.plugins.mytubestart.extmenu = ConfigYesNo(default=True)


def MyTubeMain(session, **kwargs):
	import ui
	session.open(ui.MyTubePlayerMainScreen,plugin_path)


def menu(menuid, **kwargs):
    if menuid == 'id_mainmenu_movies':
        return [(_('You Tube'), MyTubeMain, 'id_mainmenu_movies_youtube', 50)]
    return []


def Plugins(path, **kwargs):
	global plugin_path
	plugin_path = path  
	list = [PluginDescriptor(where=PluginDescriptor.WHERE_MENU, fnc=menu)]
	return list