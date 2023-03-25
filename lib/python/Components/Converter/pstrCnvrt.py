# -*- coding: utf-8 -*-
# by digiteng...12-2019
# v1.1a 01-2020
from Components.Converter.Converter import Converter
from Components.Element import cached
import json
import re
import os

from urllib.parse import quote
from urllib.request import urlopen


if not os.path.isdir('/tmp/poster'):
	os.mkdir('/tmp/poster')


class pstrCnvrt(Converter):

	def __init__(self, type):
		Converter.__init__(self, type)
		self.type = type

	@cached
	def getText(self):
		event = self.source.event
		if event is None:
			return ''

		if not event is None:
			if self.type == 'POSTER':
				self.evnt = event.getEventName()
				try:
					p = '((.*?)) \([T](\d+)\)'
					e1 = re.search(p, self.evnt)
					if e1:
						jr = e1.group(1)
						self.evntNm = re.sub('\s+', '+', jr)
					else:
						self.evntNm = re.sub('\s+', '+', self.evnt)

					ses_ep = self.sessionEpisode(event)
					if ses_ep != '' and len(ses_ep) > 0:
						self.srch = 'tv'
						self.searchPoster()
					else:
						self.srch = 'multi'
						self.searchPoster()
					return self.evntNm
				except:
					pass
		else:
			return ''
	text = property(getText)

	def searchPoster(self):
		url_json = 'https://api.themoviedb.org/3/search/%s?api_key=3c3efcf47c3577558812bb9d64019d65&query=%s' % (self.srch, quote(self.evnt))
		jp = json.load(urlopen(url_json))
		imgP = (jp['results'][0]['poster_path'])
		url_poster = 'https://image.tmdb.org/t/p/w185_and_h278_bestv2%s' % (imgP)
		dwn_poster = '/tmp/poster/poster.jpg'

		with open(dwn_poster, 'wb') as f:
			f.write(urlopen(url_poster).read())
			f.close()
			return self.evntNm

	def sessionEpisode(self, event):
		fd = event.getShortDescription() + '\n' + event.getExtendedDescription()
		pattern = ['(\d+). Staffel, Folge (\d+)', 'T(\d+) Ep.(\d+)', '"Episodio (\d+)" T(\d+)']
		for i in pattern:
			seg = re.search(i, fd)
			if seg:
				if re.search('Episodio', i):
					return 'S' + seg.group(2).zfill(2) + 'E' + seg.group(1).zfill(2)
				else:
					return 'S' + seg.group(1).zfill(2) + 'E' + seg.group(2).zfill(2)
		return ''
