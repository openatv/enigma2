from Plugins.Plugin import PluginDescriptor

try:
	from youtube_dl import YoutubeDL
except ImportError:
	YoutubeDL = None

SCHEMA = "YT-DL%3a//"
WRAPPER = "YTDLWrapper"


def playService(service, **kwargs):
	errormsg = None
	if service and SCHEMA in service.toString():
		url = service.toString()
		url = url.split(":")
		if len(url) > 9:
			url = url[10]
			if YoutubeDL is not None and url.startswith(SCHEMA):
				url = url.replace(SCHEMA, "")
				url = url.replace("%3a", ":")
				try:
					ydl = YoutubeDL({'format': 'best'})
					result = ydl.extract_info(url, download=False)
					if result and hasattr(result, "url"):
						url = result['url']
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
	if YoutubeDL:
		return [PluginDescriptor(name="YTDLWrapper", description="YTDLWrapper", where=PluginDescriptor.WHERE_PLAYSERVICE, needsRestart=False, fnc=playService)]
	else:
		return []
