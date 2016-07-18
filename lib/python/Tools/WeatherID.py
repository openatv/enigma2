#-*- coding: UTF-8 -*-

# source: https://code.google.com/p/python-weather-api/

from urllib2 import urlopen, URLError
from urllib import urlencode
import sys
import re
import json

WOEID_SEARCH_URL     = 'http://query.yahooapis.com/v1/public/yql'
WOEID_QUERY_STRING   = 'select line1, line2, line3, line4, woeid from geo.placefinder where text="%s"'

def get_woeid_from_yahoo(search_string):    
	encoded_string = search_string.encode('utf-8')
	params = {'q': WOEID_QUERY_STRING % encoded_string, 'format': 'json'}
	url = '?'.join((WOEID_SEARCH_URL, urlencode(params)))
	try:
		handler = urlopen(url, timeout = 10)
	except URLError:
		return {'error': _('Could not connect to server')}

	content_type = handler.info().dict['content-type']
	try:
		charset = re.search('charset\=(.*)', content_type).group(1)
	except AttributeError:
		charset = 'utf-8'
	if charset.lower() != 'utf-8':
		json_response = handler.read().decode(charset).encode('utf-8')
	else:
		json_response = handler.read()
	handler.close()
	yahoo_woeid_result = json.loads(json_response)

	try:
		result = yahoo_woeid_result['query']['results']['Result']
	except KeyError:
		return yahoo_woeid_result
	except TypeError:
		return {'error': _('No matching place names found')}

	woeid_data = {}
	woeid_data['count'] = yahoo_woeid_result['query']['count']
	for i in xrange(yahoo_woeid_result['query']['count']):
		try:
			place_data = result[i]
		except KeyError:
			place_data = result
		name_lines = [place_data[tag] for tag in ['line1','line2','line3','line4'] if place_data[tag] is not None]
		place_name = ', '.join(name_lines)
		woeid_data[i] = (place_data['woeid'], place_name)

	return woeid_data
