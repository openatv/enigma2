from Plugins.Plugin import PluginDescriptor

try:
	import streamlink
	Streamlink = True
except ImportError:
	Streamlink = False

SCHEMA = "streamlink%3a//"
WRAPPER = "StreamlinkWrapper"


def playService(service, **kwargs):
	errormsg = None
	if service and SCHEMA in service.toString():
		url = service.toString()
		url = url.split(":")
		if len(url) > 9:
			url = url[10]
			if Streamlink and url.startswith(SCHEMA):
				url = url.replace(SCHEMA, "")
				url = url.replace("%3a", ":")
				try:
					streams = streamlink.streams(url)
					if streams:
						url = streams["best"].to_url()
						print(f"[{WRAPPER}] playService result url '{url}'")
						return (url, errormsg)
					else:
						errormsg = "No Link found!"
						print(f"[{WRAPPER}] playService no streams")
				except Exception as e:
					errormsg = str(e)
					print(f"[{WRAPPER}] playService failed {e}")
	return (None, errormsg)


def Plugins(**kwargs):
	if Streamlink:
		return [PluginDescriptor(name=WRAPPER, description="StreamlinkWrapper", where=PluginDescriptor.WHERE_PLAYSERVICE, needsRestart=False, fnc=playService)]
	else:
		return []
