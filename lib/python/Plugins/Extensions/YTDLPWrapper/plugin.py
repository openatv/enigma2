from Plugins.Plugin import PluginDescriptor

try:
	from yt_dlp import YoutubeDL
except ImportError:
    YoutubeDL = None

def zap(session, service, **kwargs):
	if service and "http" in service.toString():
		url = service.toString()
		url = url.split(":")
		if len(url) > 9:
			url = url[10]
			if YoutubeDL is not None and url.startswith("YT-DLP%3a//"):
				url = url.replace("YT-DLP%3a//", "")
				url = url.replace("%3a", ":")
				try:
					ydl = YoutubeDL({'format': 'best'})
					result = ydl.extract_info(url, download=False)
					if result and hasattr(result, "url"):
						url = result['url']
						print("[ChannelSelection] zap / YT-DLP result url %s" % url)
						return url
					else:
						print("[ChannelSelection] zap / YT-DLP no streams")
				except Exception as e:
					print("[ChannelSelection] zap / YT-DLP failed %s" % str(e))
					pass
	return None


def Plugins(**kwargs):
	if YoutubeDL:
		return [PluginDescriptor(name="YTDLPWrapper", description="YTDLPWrapper", where=PluginDescriptor.WHERE_CHANNEL_ZAP, needsRestart = False, fnc=zap)]
	else:
		return []
