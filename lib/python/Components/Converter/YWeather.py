# YWeather by 2boom 2013 v.0.6
# xml from http://weather.yahooapis.com/forecastrss

from Components.Converter.Converter import Converter
from Components.Element import cached
from Tools.Directories import fileExists
from Poll import Poll
import time
import os
from urllib2 import Request, urlopen
import socket

class YWeather(Poll, Converter, object):
	weather_city = '711665'
	time_update = 20
	time_update_ms = 30000
	city = 0
	country = 1
	direction = 2
	speed = 3
	humidity = 4
	visibility = 5
	pressure = 6
	pressurenm = 7
	wtext = 8
	temp = 9
	picon = 10
	wtext2 = 11
	templow2 = 12
	temphigh2 = 13
	picon2 = 14
	day2 = 15
	date2 = 16
	wtext3 = 17
	templow3 = 18
	temphigh3 = 19
	picon3 = 20
	day3 = 21
	date3 = 22
	wtext4 = 23
	templow4 = 24
	temphigh4 = 25
	picon4 = 26
	day4 = 27
	date4 = 28
	wtext5 = 29
	templow5 = 30
	temphigh5 = 31
	picon5 = 32
	day5 = 33
	date5 = 34

	def __init__(self, type):
		Converter.__init__(self, type)
		Poll.__init__(self)
		if type == "city":
			self.type = self.city
		elif type == "country":
			self.type = self.country
		elif type == "direction":
			self.type = self.direction
		elif type == "speed":
			self.type = self.speed
		elif type == "humidity":
			self.type = self.humidity
		elif type == "visibility":
			self.type = self.visibility
		elif type == "pressure":
			self.type = self.pressure
		elif type == "pressurenm":
			self.type = self.pressurenm
		elif type == "text":
			self.type = self.wtext
		elif type == "temp":
			self.type = self.temp
		elif type == "picon":
			self.type = self.picon
		elif type == "text2":
			self.type = self.wtext2
		elif type == "templow2":
			self.type = self.templow2
		elif type == "temphigh2":
			self.type = self.temphigh2
		elif type == "day2":
			self.type = self.day2
		elif type == "date2":
			self.type = self.date2
		elif type == "picon2":
			self.type = self.picon2
		elif type == "text3":
			self.type = self.wtext3
		elif type == "templow3":
			self.type = self.templow3
		elif type == "temphigh3":
			self.type = self.temphigh3
		elif type == "day3":
			self.type = self.day3
		elif type == "date3":
			self.type = self.date3
		elif type == "picon3":
			self.type = self.picon3
		elif type == "text4":
			self.type = self.wtext4
		elif type == "templow4":
			self.type = self.templow4
		elif type == "temphigh4":
			self.type = self.temphigh4
		elif type == "day4":
			self.type = self.day4
		elif type == "date4":
			self.type = self.date4
		elif type == "picon4":
			self.type = self.picon4
		elif type == "text5":
			self.type = self.wtext5
		elif type == "templow5":
			self.type = self.templow5
		elif type == "temphigh5":
			self.type = self.temphigh5
		elif type == "day5":
			self.type = self.day5
		elif type == "date5":
			self.type = self.date5
		elif type == "picon5":
			self.type = self.picon5
		self.poll_interval = self.time_update_ms
		self.poll_enabled = True

	def fetchXML(self, URL, save_to):
		socket_timeout = 10
		socket.setdefaulttimeout(socket_timeout)
		req = Request(URL)
		try:
			response = urlopen(req)
		except Exception, e:
			if hasattr(e, 'code') and hasattr(e, 'reason'):
				print "[YWeather][fetchXML] Failed to retrieve XML file. Error: %s %s" % (str(e.code), str(e.reason))
			else:
				if hasattr(e, 'reason'):
					print '[YWeather][fetchXML] Failed to retrieve XML file. Error: ', str(e.reason)
				else:
					print '[YWeather][fetchXML] Failed to retrieve XML file.'
			return

		try:
			with open(save_to, "w") as f:
				f.write(response.read().replace("><", ">\n<"))
				f.close
			print '[YWeather][fetchXML] XML file retrieved and saved.'
			return True
		except:
			print '[YWeather][fetchXML] XML file retrieved and but could not be saved.'
			return

	@cached
	def getText(self):
		xweather = {'ycity':"N/A", 'ycountry':"N/A", 'ydirection':"N/A", 'yspeed':"N/A", 'yhumidity':"N/A",
				'yvisibility':"N/A", 'ypressure':"N/A", 'ytext':"N/A", 'ytemp':"N/A", 'ypicon':"3200",
				'yday2':"N/A", 'yday3':"N/A", 'yday4':"N/A", 'yday5':"N/A",
				'ypiconday2':"3200", 'ypiconday3':"3200", 'ypiconday4':"3200", 'ypiconday5':"3200",
				'ydate2':"N/A", 'ydate3':"N/A", 'ydate4':"N/A", 'ydate5':"N/A",
				'ytextday2':"N/A", 'ytextday3':"N/A", 'ytextday4':"N/A", 'ytextday5':"N/A",
				'ytemphighday2':"N/A", 'ytemphighday3':"N/A", 'ytemphighday4':"N/A", 'ytemphighday5':"N/A",
				'ytemplowday2':"N/A", 'ytemplowday3':"N/A", 'ytemplowday4':"N/A", 'ytemplowday5':"N/A"}
		direct = 0
		info = ""
		XML_location = "/tmp/yweather.xml"
		if fileExists("/usr/lib/enigma2/python/Plugins/Extensions/iSkin/Weather/Config/Location_id"):
			self.weather_city = open("/usr/lib/enigma2/python/Plugins/Extensions/iSkin/Weather/Config/Location_id").read()
		elif fileExists("/usr/lib/enigma2/python/Plugins/Extensions/YahooWeather/Config/Location_id"):
			self.weather_city = open("/usr/lib/enigma2/python/Plugins/Extensions/YahooWeather/Config/Location_id").read()
		if fileExists(XML_location) and (int((time.time() - os.stat(XML_location).st_mtime)/60) >= self.time_update):
			os.remove(XML_location)
		XML_URL = "https://query.yahooapis.com/v1/public/yql?q=select%%20*%%20from%%20weather.forecast%%20where%%20woeid=%ss%%20AND%%20u=%%22c%%22" % self.weather_city
		if not fileExists(XML_location) and self.fetchXML(XML_URL, XML_location) != True:
			with open(XML_location, "w") as f:
				f.write("None")
				f.close
			return 'N/A'
		wday = 1
		for line in open(XML_location):
			#print "[YWeather][gText] line:", line
			if line.find("<yweather:location") > -1:
				xweather['ycity'] = line.split('city')[1].split('"')[1]
				xweather['ycountry'] = line.split('country')[1].split('"')[1]
			elif line.find("<yweather:wind") > -1:
				xweather['ydirection'] = line.split('direction')[1].split('"')[1]
				xweather['yspeed'] = line.split('speed')[1].split('"')[1]
			elif line.find("<yweather:atmosphere") > -1:
				xweather['yhumidity'] = line.split('humidity')[1].split('"')[1]
				xweather['yvisibility'] = line.split('visibility')[1].split('"')[1]
				xweather['ypressure'] = line.split('pressure')[1].split('"')[1]
			elif line.find("<yweather:condition") > -1:
				xweather['ytext'] = line.split('text')[1].split('"')[1]
				xweather['ypicon'] = line.split('code')[1].split('"')[1]
				xweather['ytemp'] = line.split('temp')[1].split('"')[1]
			elif line.find('yweather:forecast') > -1:
				if wday == 2:
					xweather['yday2'] =  line.split('day')[1].split('"')[1]
					xweather['ydate2'] =  line.split('date')[1].split('"')[1]
					xweather['ytextday2'] = line.split('text')[1].split('"')[1]
					xweather['ypiconday2'] =  line.split('code')[1].split('"')[1]
					xweather['ytemphighday2'] = line.split('high')[1].split('"')[1]
					xweather['ytemplowday2'] = line.split('low')[1].split('"')[1]
				elif wday == 3:
					xweather['yday3'] =  line.split('day')[1].split('"')[1]
					xweather['ydate3'] =  line.split('date')[1].split('"')[1]
					xweather['ytextday3'] = line.split('text')[1].split('"')[1]
					xweather['ypiconday3'] =  line.split('code')[1].split('"')[1]
					xweather['ytemphighday3'] = line.split('high')[1].split('"')[1]
					xweather['ytemplowday3'] = line.split('low')[1].split('"')[1]
				elif wday == 4:
					xweather['yday4'] =  line.split('day')[1].split('"')[1]
					xweather['ydate4'] =  line.split('date')[1].split('"')[1]
					xweather['ytextday4'] = line.split('text')[1].split('"')[1]
					xweather['ypiconday4'] =  line.split('code')[1].split('"')[1]
					xweather['ytemphighday4'] = line.split('high')[1].split('"')[1]
					xweather['ytemplowday4'] = line.split('low')[1].split('"')[1]
				elif wday == 5:
					xweather['yday5'] =  line.split('day')[1].split('"')[1]
					xweather['ydate5'] =  line.split('date')[1].split('"')[1]
					xweather['ytextday5'] = line.split('text')[1].split('"')[1]
					xweather['ypiconday5'] =  line.split('code')[1].split('"')[1]
					xweather['ytemphighday5'] = line.split('high')[1].split('"')[1]
					xweather['ytemplowday5'] = line.split('low')[1].split('"')[1]
				wday = wday + 1

		#print "[YWeather][gText] xweather:", xweather

		if self.type == self.city:
			info = xweather['ycity']
		elif self.type == self.country:
			info = xweather['ycountry']
		elif self.type == self.direction:
			if xweather['ydirection'] != "N/A":
				direct = int(xweather['ydirection'])
				if direct >= 0 and direct <= 20:
					info = _('N')
				elif direct >= 21 and direct <= 35:
					info = _('nne')
				elif direct >= 36 and direct <= 55:
					info = _('ne')
				elif direct >= 56 and direct <= 70:
					info = _('ene')
				elif direct >= 71 and direct <= 110:
					info = _('E')
				elif direct >= 111 and direct <= 125:
					info = _('ese')
				elif direct >= 126 and direct <= 145:
					info = _('se')
				elif direct >= 146 and direct <= 160:
					info = _('sse')
				elif direct >= 161 and direct <= 200:
					info = _('S')
				elif direct >= 201 and direct <= 215:
					info = _('ssw')
				elif direct >= 216 and direct <= 235:
					info = _('sw')
				elif direct >= 236 and direct <= 250:
					info = _('wsw')
				elif direct >= 251 and direct <= 290:
					info = _('W')
				elif direct >= 291 and direct <= 305:
					info = _('wnw')
				elif direct >= 306 and direct <= 325:
					info = _('nw')
				elif direct >= 326 and direct <= 340:
					info = _('nnw')
				elif direct >= 341 and direct <= 360:
					info = _('N')
			else:
				info = "N/A"
		elif self.type == self.speed:
			info = xweather['yspeed'] + ' km/h'
		elif self.type == self.humidity:
			info = xweather['yhumidity'] + ' mb'
		elif self.type == self.visibility:
			info = xweather['yvisibility'] + ' km'
		elif self.type == self.pressure:
			info = xweather['ypressure'] + ' mb'
		elif self.type == self.pressurenm:
			if xweather['ypressure'] != "N/A":
				info = "%d mmHg" % round(float(xweather['ypressure']) * 0.75)
			else:
				info = "N/A"
		elif self.type == self.wtext:
			info = xweather['ytext']
		elif self.type == self.temp:
			if info != "N/A":
				info = xweather['ytemp'] + '%s' % unichr(176).encode("latin-1")
			else:
				info = xweather['ytemp']
		elif self.type == self.picon:
			info = xweather['ypicon']
		elif self.type == self.wtext2:
			info = xweather['ytextday2']
		elif self.type == self.templow2:
			if info != "N/A":
				info = xweather['ytemplowday2'] + '%s' % unichr(176).encode("latin-1")
			else:
				info = xweather['ytemplowday2']
		elif self.type == self.temphigh2:
			if info != "N/A":
				info = xweather['ytemphighday2'] + '%s' % unichr(176).encode("latin-1")
			else:
				info = xweather['ytemphighday2']
		elif self.type == self.picon2:
			info = xweather['ypiconday2']
		elif self.type == self.day2:
			if xweather['yday2'] != "N/A":
				day = xweather['yday2']
				if day == 'Mon':
					info = _('Mon')
				elif day == 'Tue':
					info = _('Tue')
				elif day == 'Wed':
					info = _('Wed')
				elif day == 'Thu':
					info = _('Thu')
				elif day == 'Fri':
					info = _('Fri')
				elif day == 'Sat':
					info = _('Sat')
				elif day == 'Sun':
					info = _('Sun')
			else:
				info = "N/A"
		elif self.type == self.date2:
			info = xweather['ydate2']
		elif self.type == self.wtext3:
			info = xweather['ytextday3']
		elif self.type == self.templow3:
			if info != "N/A":
				info = xweather['ytemplowday3'] + '%s' % unichr(176).encode("latin-1")
			else:
				info = xweather['ytemplowday3']
		elif self.type == self.temphigh3:
			if info != "N/A":
				info = xweather['ytemphighday3'] + '%s' % unichr(176).encode("latin-1")
			else:
				info = xweather['ytemphighday3']
		elif self.type == self.picon3:
			info = xweather['ypiconday3']
		elif self.type == self.day3:
			if xweather['yday3'] != "N/A":
				day = xweather['yday3']
				if day == 'Mon':
					info = _('Mon')
				elif day == 'Tue':
					info = _('Tue')
				elif day == 'Wed':
					info = _('Wed')
				elif day == 'Thu':
					info = _('Thu')
				elif day == 'Fri':
					info = _('Fri')
				elif day == 'Sat':
					info = _('Sat')
				elif day == 'Sun':
					info = _('Sun')
			else:
				info = "N/A"
		elif self.type == self.date3:
			info = xweather['ydate3']
		elif self.type == self.wtext4:
			info = xweather['ytextday4']
		elif self.type == self.templow4:
			if info != "N/A":
				info = xweather['ytemplowday4'] + '%s' % unichr(176).encode("latin-1")
			else:
				info = xweather['ytemplowday4']
		elif self.type == self.temphigh4:
			if info != "N/A":
				info = xweather['ytemphighday4'] + '%s' % unichr(176).encode("latin-1")
			else:
				info = xweather['ytemphighday4']
		elif self.type == self.picon4:
			info = xweather['ypiconday4']
		elif self.type == self.day4:
			if xweather['yday4'] != "N/A":
				day = xweather['yday4']
				if day == 'Mon':
					info = _('Mon')
				elif day == 'Tue':
					info = _('Tue')
				elif day == 'Wed':
					info = _('Wed')
				elif day == 'Thu':
					info = _('Thu')
				elif day == 'Fri':
					info = _('Fri')
				elif day == 'Sat':
					info = _('Sat')
				elif day == 'Sun':
					info = _('Sun')
			else:
				info = "N/A"
		elif self.type == self.date4:
			info = xweather['ydate4']
		elif self.type == self.wtext5:
			info = xweather['ytextday5']
		elif self.type == self.templow5:
			if info != "N/A":
				info = xweather['ytemplowday5'] + '%s' % unichr(176).encode("latin-1")
			else:
				info = xweather['ytemplowday5']
		elif self.type == self.temphigh5:
			if info != "N/A":
				info = xweather['ytemphighday5'] + '%s' % unichr(176).encode("latin-1")
			else:
				info = xweather['ytemphighday5']
		elif self.type == self.picon5:
			info = xweather['ypiconday5']
		elif self.type == self.day5:
			if xweather['yday5'] != "N/A":
				day = xweather['yday5']
				if day == 'Mon':
					info = _('Mon')
				elif day == 'Tue':
					info = _('Tue')
				elif day == 'Wed':
					info = _('Wed')
				elif day == 'Thu':
					info = _('Thu')
				elif day == 'Fri':
					info = _('Fri')
				elif day == 'Sat':
					info = _('Sat')
				elif day == 'Sun':
					info = _('Sun')
			else:
				info = "N/A"
		elif self.type == self.date5:
			info = xweather['ydate5']
		#print "[YWeather][gText] info:", info
		return info

	text = property(getText)

	def changed(self, what):
		Converter.changed(self, (self.CHANGED_POLL,))
