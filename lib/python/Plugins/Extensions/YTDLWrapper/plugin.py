from Plugins.Plugin import PluginDescriptor

try:
	from youtube_dl import YoutubeDL
except ImportError:
	YoutubeDL = None


def zap(session, service, **kwargs):
	errormsg = None
	if service and "http" in service.toString():
		url = service.toString()
		url = url.split(":")
		if len(url) > 9:
			url = url[10]
			if YoutubeDL is not None and url.startswith("YT-DL%3a//"):
				url = url.replace("YT-DL%3a//", "")
				url = url.replace("%3a", ":")
				try:
					ydl = YoutubeDL({'format': 'best'})
					result = ydl.extract_info(url, download=False)
					if result and hasattr(result, "url"):
						url = result['url']
						print("[ChannelSelection] zap / YoutubeDL result url %s" % url)
						return (url, errormsg)
					else:
						errormsg = "No Link found!"
						print("[ChannelSelection] zap / YoutubeDL no streams")
				except Exception as e:
					errormsg = str(e)
					print("[ChannelSelection] zap / YoutubeDL failed %s" % str(e))
					pass
	return (None, errormsg)


def Plugins(**kwargs):
	if YoutubeDL:
		return [PluginDescriptor(name="YTDLWrapper", description="YTDLWrapper", where=PluginDescriptor.WHERE_CHANNEL_ZAP, needsRestart=False, fnc=zap)]
	else:
		return []
