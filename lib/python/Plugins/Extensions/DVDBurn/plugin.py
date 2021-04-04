from __future__ import absolute_import
from Plugins.Plugin import PluginDescriptor


def main(session, **kwargs):
	from .TitleList import TitleList
	return session.open(TitleList.TitleList)


def main_add(session, service, **kwargs):
	dvdburn = main(session, **kwargs)
	dvdburn.selectedSource(service)


def Plugins(**kwargs):
	descr = _("Burn to medium")
	return [PluginDescriptor(name=_("DVD Burn"), description=descr, where=PluginDescriptor.WHERE_MOVIELIST, needsRestart=True, fnc=main_add, icon="dvdburn.png"),
		PluginDescriptor(name=_("DVD Burn"), description=descr, where=PluginDescriptor.WHERE_PLUGINMENU, needsRestart=True, fnc=main, icon="dvdburn.png")]
