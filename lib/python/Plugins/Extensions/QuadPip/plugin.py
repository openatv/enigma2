from Plugins.Plugin import PluginDescriptor

from .qpip import QuadPipScreen, setDecoderMode


def main(session, **kwargs):
	session.open(QuadPipScreen)


def autoStart(reason, **kwargs):
	if reason == 0:
		setDecoderMode("normal")
	elif reason == 1:
		pass


def Plugins(**kwargs):
	return [
		PluginDescriptor(name=_("Enable Quad PiP"), description="Quad Picture in Picture", where=[PluginDescriptor.WHERE_EXTENSIONSMENU], fnc=main),
		PluginDescriptor(where=[PluginDescriptor.WHERE_AUTOSTART], fnc=autoStart)
		]
