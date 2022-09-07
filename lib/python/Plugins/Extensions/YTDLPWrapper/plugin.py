from Plugins.Plugin import PluginDescriptor

try:
	from yt_dlp import YoutubeDL
except ImportError:
    YoutubeDL = None


def zap(session, service, **kwargs):
	errormsg = None
	if service and "http" in service.toString():
		url = service.toString()
		url = url.split(":")
		if len(url) > 9:
			url = url[10]
			if YoutubeDL is not None and url.startswith("YT-DLP%3a//"):
				url = url.replace("YT-DLP%3a//", "")
				url = url.replace("%3a", ":")
				try:
					ydl = YoutubeDL({"format": "b", "no_color": True})
					result = ydl.extract_info(url, download=False)
					result = ydl.sanitize_info(result)
					if result and result.get("url"):
						url = result["url"]
						print("[ChannelSelection] zap / YoutubeDLP result url %s" % url)
						return (url, errormsg)
					else:
						errormsg = "No Link found!"
						print("[ChannelSelection] zap / YoutubeDLP no streams")
				except Exception as e:
					errormsg = str(e)
					print("[ChannelSelection] zap / YoutubeDLP failed %s" % str(e))
					pass
	return (None, errormsg)


def Plugins(**kwargs):
	if YoutubeDL:
		return [PluginDescriptor(name="YTDLPWrapper", description="YTDLPWrapper", where=PluginDescriptor.WHERE_CHANNEL_ZAP, needsRestart=False, fnc=zap)]
	else:
		return []
