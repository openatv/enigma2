# by digiteng...12-2019
# v1.1a 01-2020
from json import load
from os import mkdir
from os.path import isdir
from re import fullmatch, search, sub
from urllib.parse import urlencode
from urllib.request import urlopen
from Components.Converter.Converter import Converter
from Components.Element import cached


class pstrCnvrt(Converter):
	def __init__(self, tokens):
		Converter.__init__(self, tokens)
		self.type = tokens

	@cached
	def getText(self):
		text = ""
		event = self.source.event
		if event is not None and self.type == "POSTER":
			self.evnt = event.getEventName()
			try:
				pattern = r"((.*?)) \([T](\d+)\)"  # NOSONAR -> Make sure the regex used here, which is vulnerable to polynomial runtime due to backtracking, cannot lead to denial of service.
				found = search(pattern, self.evnt)
				eventName = found.group(1) if found else self.evnt
				self.evntNm = sub(r"\s+", "+", eventName)
				self.searchPoster(bool(self.sessionEpisode(event)))
				text = self.evntNm
			except Exception:
				text = ""
		return text

	text = property(getText)

	def searchPoster(self, isSeries):
		searchUrl = "https://api.themoviedb.org/3/search/tv" if isSeries else "https://api.themoviedb.org/3/search/multi"
		jsonData = load(urlopen(f"{searchUrl}?{urlencode({'api_key': '3c3efcf47c3577558812bb9d64019d65', 'query': self.evnt})}"))
		posterPath = jsonData["results"][0]["poster_path"]
		if isinstance(posterPath, str) and fullmatch(r"/[\w-]+\.(?:jpg|jpeg|png)", posterPath):  # Only accept a plain file name from the API response.
			try:
				if not isdir("/tmp/poster"):
					mkdir("/tmp/poster")
				with open("/tmp/poster/poster.jpg", "wb") as fd:
					fd.write(urlopen(f"https://image.tmdb.org/t/p/w185_and_h278_bestv2{posterPath}").read())
			except Exception:
				pass

	def sessionEpisode(self, event):
		result = ""
		description = f"{event.getShortDescription()}\n{event.getExtendedDescription()}"
		for pattern in (r"(\d+). Staffel, Folge (\d+)", r"T(\d+) Ep.(\d+)", r"\"Episodio (\d+)\" T(\d+)"):
			found = search(pattern, description)
			if found:
				season, episode = (found.group(2), found.group(1)) if "Episodio" in pattern else (found.group(1), found.group(2))
				result = f"S{season.zfill(2)}E{episode.zfill(2)}"
				break
		return result
