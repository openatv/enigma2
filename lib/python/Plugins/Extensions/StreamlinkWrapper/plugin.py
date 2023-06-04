from Plugins.Plugin import PluginDescriptor

try:
	import streamlink
	Streamlink = True
except ImportError:
	Streamlink = False


def zap(session, service, **kwargs):
	errormsg = None
	if service and "http" in service.toString():
		url = service.toString()
		url = url.split(":")
		if len(url) > 9:
			url = url[10]
			if Streamlink and url.startswith("streamlink%3a//"):
				url = url.replace("streamlink%3a//", "")
				url = url.replace("%3a", ":")
				try:
					streams = streamlink.streams(url)
					if streams:
						url = streams["best"].to_url()
						print("[ChannelSelection] zap / streamlink result url %s" % url)
						return (url, errormsg)
					else:
						errormsg = "No Link found!"
						print("[ChannelSelection] zap / streamlink no streams")
				except Exception as e:
					errormsg = str(e)
					print("[ChannelSelection] zap / streamlink failed %s" % str(e))
					pass
	return (None, errormsg)


def Plugins(**kwargs):
	if Streamlink:
		return [PluginDescriptor(name="StreamlinkWrapper", description="StreamlinkWrapper", where=PluginDescriptor.WHERE_CHANNEL_ZAP, needsRestart=False, fnc=zap)]
	else:
		return []
