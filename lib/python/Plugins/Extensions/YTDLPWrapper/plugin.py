from Plugins.Plugin import PluginDescriptor

try:
	from yt_dlp import YoutubeDL
except ImportError:
	YoutubeDL = None

SCHEMA = "YT-DLP%3a//"
WRAPPER = "YTDLPWrapper"


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
					ydl = YoutubeDL({"format": "b/bv*+ba/bv*", "no_color": True, "usenetrc": True})
					result = ydl.extract_info(url, download=False)
					result = ydl.sanitize_info(result)
					stream = result.get("url") if result else None
					if not stream and result:
						# Video and audio come as separate streams, which the player cannot
						# merge. Hand it the master playlist holding both instead.
						for fmt in (result.get("requested_formats") or []) + (result.get("formats") or []):
							stream = fmt.get("manifest_url")
							if stream:
								break
					if stream:
						print(f"[{WRAPPER}] playService result url '{stream}'")
						return (stream, errormsg)
					else:
						errormsg = "No Link found!"
						print(f"[{WRAPPER}] playService no streams")
				except Exception as e:
					errormsg = str(e)
					print(f"[{WRAPPER}] playService failed {e}")
	return (None, errormsg)


def Plugins(**kwargs):
	if YoutubeDL:
		return [PluginDescriptor(name="YTDLPWrapper", description="YTDLPWrapper", where=PluginDescriptor.WHERE_PLAYSERVICE, needsRestart=False, fnc=playService)]
	else:
		return []
