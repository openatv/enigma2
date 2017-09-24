from Plugins.Plugin import PluginDescriptor
from Components.PluginComponent import plugins
from Components.config import config, ConfigSubsection, ConfigSelection
from enigma import eDBoxLCD

from qpip import QuadPipScreen, setDecoderMode

def main(session, **kwargs):
	session.open(QuadPipScreen)

def autoStart(reason, **kwargs):
	if reason == 0:
		setDecoderMode("normal")
	elif reason == 1:
		pass

def Plugins(**kwargs):
	list = []
	list.append(
		PluginDescriptor(name=_("Enable Quad PIP"),
		description="Quad Picture in Picture",
		where = [PluginDescriptor.WHERE_EXTENSIONSMENU],
		fnc = main))

	list.append(
		PluginDescriptor(
		where = [PluginDescriptor.WHERE_AUTOSTART],
		fnc = autoStart))

	return list

