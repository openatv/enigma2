# by digiteng...12-2019
# v1.1a 01-2020
from json import load
from os.path import isdir
from os import mkdir
from re import search, sub
from urllib.parse import quote
from urllib.request import urlopen

from Components.Converter.Converter import Converter
from Components.Element import cached


class pstrCnvrt(Converter):

	def __init__(self, type):
		Converter.__init__(self, type)
		self.type = type

	@cached
	def getText(self):
		event = self.source.event
		if event is None:
			return ""
		else:
			if self.type == "POSTER":
				self.evnt = event.getEventName()
				try:
					p = r"((.*?)) \([T](\d+)\)"  # NOSONAR -> Make sure the regex used here, which is vulnerable to polynomial runtime due to backtracking, cannot lead to denial of service.
					e1 = search(p, self.evnt)
					jr = self.evnt
					if e1:
						jr = e1.group(1)
					self.evntNm = sub(r"\s+", "+", jr)
					ses_ep = self.sessionEpisode(event)
					self.searchPoster("tv" if ses_ep != "" and len(ses_ep) > 0 else "multi")
					return self.evntNm
				except Exception:
					return ""
			else:
				return ""
	text = property(getText)

	def searchPoster(self, searchMode):
		url_json = "https://api.themoviedb.org/3/search/%s?api_key=3c3efcf47c3577558812bb9d64019d65&query=%s" % (searchMode, quote(self.evnt))
		jp = load(urlopen(url_json))
		imgP = (jp["results"][0]["poster_path"])
		url_poster = "https://image.tmdb.org/t/p/w185_and_h278_bestv2%s" % (imgP)
		try:
			if not isdir("/tmp/poster"):
				mkdir("/tmp/poster")
			with open("/tmp/poster/poster.jpg", "wb") as fd:
				fd.write(urlopen(url_poster).read())
				# return self.evntNm
		except Exception:
			pass

	def sessionEpisode(self, event):
		fd = "%s\n%s" % (event.getShortDescription(), event.getExtendedDescription())
		pattern = [r'(\d+). Staffel, Folge (\d+)', r'T(\d+) Ep.(\d+)', r'"Episodio (\d+)" T(\d+)']
		for i in pattern:
			seg = search(i, fd)
			if seg:
				if search("Episodio", i):
					return "S%sE%s" % (seg.group(2).zfill(2), seg.group(1).zfill(2))
				else:
					return "S%sE%s" % (seg.group(1).zfill(2), seg.group(2).zfill(2))
		return ""
