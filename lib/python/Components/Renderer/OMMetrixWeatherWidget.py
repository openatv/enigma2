#!/usr/bin/env python
# -*- coding: iso-8859-1 -*-
#######################################################################
#
#	MetrixWeather for Enigma2
#	Coded by Sinthex IT-Solutions (c) 2014
#	www.open-store.net
#
#
#  This plugin is licensed under the Creative Commons
#  Attribution-NonCommercial-ShareAlike 3.0 Unported License.
#  To view a copy of this license, visit http://creativecommons.org/licenses/by-nc-sa/3.0/
#  or send a letter to Creative Commons, 559 Nathan Abbott Way, Stanford, California 94305, USA.
#
#  This plugin is NOT free software. It is open source, you are allowed to
#  modify it (if you keep the license), but it may not be commercially
#  distributed other than under the conditions noted above.
#
#
#######################################################################

from Renderer import Renderer
from Components.VariableText import VariableText
import urllib2
from enigma import ePixmap
from datetime import datetime
from Components.Element import cached
from xml.dom.minidom import parseString
from Components.config import config, configfile, ConfigSubsection, ConfigSelection, ConfigNumber, ConfigSelectionNumber, ConfigYesNo, ConfigText

def initWeatherConfig():
	config.plugins.MetrixWeather = ConfigSubsection()
	#MetrixWeather
	config.plugins.MetrixWeather.enabled = ConfigYesNo(default=False)
	config.plugins.MetrixWeather.woeid = ConfigNumber(default=665912) #Location (metrixweather.open-store.net)
	config.plugins.MetrixWeather.tempUnit = ConfigSelection(default="Celsius", choices = [
		("Celsius", _("Celsius")),
		("Fahrenheit", _("Fahrenheit"))
	])
	config.plugins.MetrixWeather.refreshInterval = ConfigNumber(default=60)
	config.plugins.MetrixWeather.lastUpdated = ConfigText(default="2001-01-01 01:01:01")

	## RENDERER CONFIG:
	config.plugins.MetrixWeather.currentLocation = ConfigText(default="N/A")
	config.plugins.MetrixWeather.currentWeatherCode = ConfigText(default="(")
	config.plugins.MetrixWeather.currentWeatherText = ConfigText(default="N/A")
	config.plugins.MetrixWeather.currentWeatherTemp = ConfigText(default="0")

	config.plugins.MetrixWeather.forecastTodayCode = ConfigText(default="(")
	config.plugins.MetrixWeather.forecastTodayDay = ConfigText(default="N/A")
	config.plugins.MetrixWeather.forecastTodayText = ConfigText(default="N/A")
	config.plugins.MetrixWeather.forecastTodayTempMin = ConfigText(default="0")
	config.plugins.MetrixWeather.forecastTodayTempMax = ConfigText(default="0")

	config.plugins.MetrixWeather.forecastTomorrowCode = ConfigText(default="(")
	config.plugins.MetrixWeather.forecastTomorrowDay = ConfigText(default="N/A")
	config.plugins.MetrixWeather.forecastTomorrowText = ConfigText(default="N/A")
	config.plugins.MetrixWeather.forecastTomorrowTempMin = ConfigText(default="0")
	config.plugins.MetrixWeather.forecastTomorrowTempMax = ConfigText(default="0")
	
	config.plugins.MetrixWeather.forecast2daysCode = ConfigText(default="(")
	config.plugins.MetrixWeather.forecast2daysDay = ConfigText(default="N/A")
	config.plugins.MetrixWeather.forecast2daysText = ConfigText(default="N/A")
	config.plugins.MetrixWeather.forecast2daysTempMin = ConfigText(default="0")
	config.plugins.MetrixWeather.forecast2daysTempMax = ConfigText(default="0")

	config.plugins.MetrixWeather.forecast3daysCode = ConfigText(default="(")
	config.plugins.MetrixWeather.forecast3daysDay = ConfigText(default="N/A")
	config.plugins.MetrixWeather.forecast3daysText = ConfigText(default="N/A")
	config.plugins.MetrixWeather.forecast3daysTempMin = ConfigText(default="0")
	config.plugins.MetrixWeather.forecast3daysTempMax = ConfigText(default="0")

	config.plugins.MetrixWeather.forecast4daysCode = ConfigText(default="(")
	config.plugins.MetrixWeather.forecast4daysDay = ConfigText(default="N/A")
	config.plugins.MetrixWeather.forecast4daysText = ConfigText(default="N/A")
	config.plugins.MetrixWeather.forecast4daysTempMin = ConfigText(default="0")
	config.plugins.MetrixWeather.forecast4daysTempMax = ConfigText(default="0")

	config.plugins.MetrixWeather.save()
	configfile.save()

initWeatherConfig()
	
class OMMetrixWeatherWidget(Renderer):

	def __init__(self):
		Renderer.__init__(self)

	def changed(self, what):
		if self.instance:
			if what[0] != self.CHANGED_CLEAR:
				if config.plugins.MetrixWeather.enabled.saved_value:
					self.instance.show()
					self.getWeather()
				else:
					self.instance.hide()
	GUI_WIDGET = ePixmap

	def getWeather(self):
		# skip if weather-widget is already up to date
		tdelta = datetime.now() - datetime.strptime(config.plugins.MetrixWeather.lastUpdated.value,"%Y-%m-%d %H:%M:%S")
		if int(tdelta.seconds) < (config.plugins.MetrixWeather.refreshInterval.value * 60):
			return
		woeid = config.plugins.MetrixWeather.woeid.value
		print "[OMMetrixWeather] lookup for ID " + str(woeid)
		url = "http://query.yahooapis.com/v1/public/yql?q=select%20item%20from%20weather.forecast%20where%20woeid%3D%22"+str(woeid)+"%22&format=xml"
		#url = "http://query.yahooapis.com/v1/public/yql?q=select%20item%20from%20weather.forecast%20where%20woeid%3D%22"+str(self.woeid)+"%22%20u%3Dc&format=xml"
		try:
			file = urllib2.urlopen(url, timeout=2)
			data = file.read()
			file.close()
			config.plugins.MetrixWeather.lastUpdated.value = str(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

			dom = parseString(data)
			title = self.getText(dom.getElementsByTagName('title')[0].childNodes)
			config.plugins.MetrixWeather.currentLocation.value = str(title).split(',')[0].replace("Conditions for ","")
	
			currentWeather = dom.getElementsByTagName('yweather:condition')[0]
			currentWeatherCode = currentWeather.getAttributeNode('code')
			config.plugins.MetrixWeather.currentWeatherCode.value = self.ConvertCondition(currentWeatherCode.nodeValue)
			currentWeatherTemp = currentWeather.getAttributeNode('temp')
			config.plugins.MetrixWeather.currentWeatherTemp.value = self.getTemp(currentWeatherTemp.nodeValue)
			currentWeatherText = currentWeather.getAttributeNode('text')
			config.plugins.MetrixWeather.currentWeatherText.value = currentWeatherText.nodeValue
	
			currentWeather = dom.getElementsByTagName('yweather:forecast')[0]
			currentWeatherCode = currentWeather.getAttributeNode('code')
			config.plugins.MetrixWeather.forecastTodayCode.value = self.ConvertCondition(currentWeatherCode.nodeValue)
			currentWeatherTemp = currentWeather.getAttributeNode('high')
			config.plugins.MetrixWeather.forecastTodayTempMax.value = self.getTemp(currentWeatherTemp.nodeValue)
			currentWeatherTemp = currentWeather.getAttributeNode('low')
			config.plugins.MetrixWeather.forecastTodayTempMin.value = self.getTemp(currentWeatherTemp.nodeValue)
			currentWeatherText = currentWeather.getAttributeNode('text')
			config.plugins.MetrixWeather.forecastTodayText.value = currentWeatherText.nodeValue
			currentWeatherDay = currentWeather.getAttributeNode('day')
			config.plugins.MetrixWeather.forecastTodayDay.value = currentWeatherDay.nodeValue
	
			currentWeather = dom.getElementsByTagName('yweather:forecast')[1]
			currentWeatherCode = currentWeather.getAttributeNode('code')
			config.plugins.MetrixWeather.forecastTomorrowCode.value = self.ConvertCondition(currentWeatherCode.nodeValue)
			currentWeatherTemp = currentWeather.getAttributeNode('high')
			config.plugins.MetrixWeather.forecastTomorrowTempMax.value = self.getTemp(currentWeatherTemp.nodeValue)
			currentWeatherTemp = currentWeather.getAttributeNode('low')
			config.plugins.MetrixWeather.forecastTomorrowTempMin.value = self.getTemp(currentWeatherTemp.nodeValue)
			currentWeatherText = currentWeather.getAttributeNode('text')
			config.plugins.MetrixWeather.forecastTomorrowText.value = currentWeatherText.nodeValue
			currentWeatherDay = currentWeather.getAttributeNode('day')
			config.plugins.MetrixWeather.forecastTomorrowDay.value = currentWeatherDay.nodeValue

			currentWeather = dom.getElementsByTagName('yweather:forecast')[2]
			currentWeatherCode = currentWeather.getAttributeNode('code')
			config.plugins.MetrixWeather.forecast2daysCode.value = self.ConvertCondition(currentWeatherCode.nodeValue)
			currentWeatherTemp = currentWeather.getAttributeNode('high')
			config.plugins.MetrixWeather.forecast2daysTempMax.value = self.getTemp(currentWeatherTemp.nodeValue)
			currentWeatherTemp = currentWeather.getAttributeNode('low')
			config.plugins.MetrixWeather.forecast2daysTempMin.value = self.getTemp(currentWeatherTemp.nodeValue)
			currentWeatherText = currentWeather.getAttributeNode('text')
			config.plugins.MetrixWeather.forecast2daysText.value = currentWeatherText.nodeValue
			currentWeatherDay = currentWeather.getAttributeNode('day')
			config.plugins.MetrixWeather.forecast2daysDay.value = currentWeatherDay.nodeValue

			currentWeather = dom.getElementsByTagName('yweather:forecast')[3]
			currentWeatherCode = currentWeather.getAttributeNode('code')
			config.plugins.MetrixWeather.forecast3daysCode.value = self.ConvertCondition(currentWeatherCode.nodeValue)
			currentWeatherTemp = currentWeather.getAttributeNode('high')
			config.plugins.MetrixWeather.forecast3daysTempMax.value = self.getTemp(currentWeatherTemp.nodeValue)
			currentWeatherTemp = currentWeather.getAttributeNode('low')
			config.plugins.MetrixWeather.forecast3daysTempMin.value = self.getTemp(currentWeatherTemp.nodeValue)
			currentWeatherText = currentWeather.getAttributeNode('text')
			config.plugins.MetrixWeather.forecast3daysText.value = currentWeatherText.nodeValue
			currentWeatherDay = currentWeather.getAttributeNode('day')
			config.plugins.MetrixWeather.forecast3daysDay.value = currentWeatherDay.nodeValue

			currentWeather = dom.getElementsByTagName('yweather:forecast')[4]
			currentWeatherCode = currentWeather.getAttributeNode('code')
			config.plugins.MetrixWeather.forecast4daysCode.value = self.ConvertCondition(currentWeatherCode.nodeValue)
			currentWeatherTemp = currentWeather.getAttributeNode('high')
			config.plugins.MetrixWeather.forecast4daysTempMax.value = self.getTemp(currentWeatherTemp.nodeValue)
			currentWeatherTemp = currentWeather.getAttributeNode('low')
			config.plugins.MetrixWeather.forecast4daysTempMin.value = self.getTemp(currentWeatherTemp.nodeValue)
			currentWeatherText = currentWeather.getAttributeNode('text')
			config.plugins.MetrixWeather.forecast4daysText.value = currentWeatherText.nodeValue
			currentWeatherDay = currentWeather.getAttributeNode('day')
			config.plugins.MetrixWeather.forecast4daysDay.value = currentWeatherDay.nodeValue

			config.plugins.MetrixWeather.save()
			configfile.save()
			
		except Exception as error:
			print "Cant get weather data: %r" % error
			# cancel weather function
			return

	def getText(self,nodelist):
		rc = []
		for node in nodelist:
			if node.nodeType == node.TEXT_NODE:
				rc.append(node.data)
		return ''.join(rc)

	def ConvertCondition(self, c):
		c = int(c)
		condition = "("
		if c == 0 or c == 1 or c == 2:
			condition = "S"
		elif c == 3 or c == 4:
			condition = "Z"
		elif c == 5  or c == 6 or c == 7 or c == 18:
			condition = "U"
		elif c == 8 or c == 10 or c == 25:
			condition = "G"
		elif c == 9:
			condition = "Q"
		elif c == 11 or c == 12 or c == 40:
			condition = "R"
		elif c == 13 or c == 14 or c == 15 or c == 16 or c == 41 or c == 46 or c == 42 or c == 43:
			condition = "W"
		elif c == 17 or c == 35:
			condition = "X"
		elif c == 19:
			condition = "F"
		elif c == 20 or c == 21 or c == 22:
			condition = "L"
		elif c == 23 or c == 24:
			condition = "S"
		elif c == 26 or c == 44:
			condition = "N"
		elif c == 27 or c == 29:
			condition = "I"
		elif c == 28 or c == 30:
			condition = "H"
		elif c == 31 or c == 33:
			condition = "C"
		elif c == 32 or c == 34:
			condition = "B"
		elif c == 36:
			condition = "B"
		elif c == 37 or c == 38 or c == 39 or c == 45 or c == 47:
			condition = "0"
		else:
			condition = ")"
		return str(condition)

	def getTemp(self,temp):
		if config.plugins.MetrixWeather.tempUnit.value == "Fahrenheit":
			return str(int(round(float(temp),0)))
		else:
			celsius = (float(temp) - 32 ) * 5 / 9
			return str(int(round(float(celsius),0)))
