# -*- coding: utf-8 -*-

#This plugin is free software, you are allowed to
#modify it (if you keep the license),
#but you are not allowed to distribute/publish
#it without source code (this version and your modifications).
#This means you also have to distribute
#source code of your modifications.
#
#
#######################################################################
#    AtileHD Weather for VU+
#    Support: www.vuplus-support.org
#    THX to iMaxxx (c) 2013 for base idea
#######################################################################


from Components.Converter.Converter import Converter
from Components.Element import cached
from Components.config import config, ConfigSubsection, ConfigNumber, ConfigSelection
from twisted.web.client import getPage
from xml.dom.minidom import parseString
from enigma import eTimer

config.plugins.AtileHD = ConfigSubsection()
config.plugins.AtileHD.refreshInterval = ConfigNumber(default = "10")
config.plugins.AtileHD.woeid = ConfigNumber(default = "640161")
config.plugins.AtileHD.tempUnit = ConfigSelection(default = "Celsius", choices = [("Celsius", _("Celsius")),("Fahrenheit", _("Fahrenheit"))])

weather_data = None

class VWeather(Converter, object):

	def __init__(self, type):
		Converter.__init__(self, type)
		global weather_data
		if weather_data is None:
			weather_data = WeatherData()
		self.type = type

	@cached
	def getText(self):
		WeatherInfo = weather_data.WeatherInfo
		if self.type == "currentLocation":
			return WeatherInfo[self.type]
		if self.type == "currentWeatherTemp":
			return WeatherInfo[self.type]
		elif self.type == "currentWeatherText":
			return WeatherInfo[self.type]
		elif self.type == "currentWeatherCode":
			return WeatherInfo[self.type]
		elif self.type == "forecastTodayCode":
			return WeatherInfo[self.type]
		elif self.type == "forecastTodayDay":
			return WeatherInfo[self.type]
		elif self.type == "forecastTodayDate":
			return WeatherInfo[self.type]
		elif self.type == "forecastTodayTempMin":
			return WeatherInfo[self.type] + " " + self.getCF()
		elif self.type == "forecastTodayTempMax":
			return WeatherInfo[self.type] + " " + self.getCF()
		elif self.type == "forecastTodayText":
			return WeatherInfo[self.type]
		elif self.type == "forecastTomorrowCode":
			return WeatherInfo[self.type]
		elif self.type == "forecastTomorrowDay":
			return WeatherInfo[self.type]
		elif self.type == "forecastTomorrowDate":
			return WeatherInfo[self.type]
		elif self.type == "forecastTomorrowTempMin":
			return WeatherInfo[self.type] + " " + self.getCF()
		elif self.type == "forecastTomorrowTempMax":
			return WeatherInfo[self.type] + " " + self.getCF()
		elif self.type == "forecastTomorrowText":
			return WeatherInfo[self.type]
		elif self.type == "forecastTomorrow1Code":
			return WeatherInfo[self.type]
		elif self.type == "forecastTomorrow1Day":
			return WeatherInfo[self.type]
		elif self.type == "forecastTomorrow1Date":
			return WeatherInfo[self.type]
		elif self.type == "forecastTomorrow1TempMin":
			return WeatherInfo[self.type] + " " + self.getCF()
		elif self.type == "forecastTomorrow1TempMax":
			return WeatherInfo[self.type] + " " + self.getCF()
		elif self.type == "forecastTomorrow1Text":
			return WeatherInfo[self.type]
		elif self.type == "forecastTomorrow2Code":
			return WeatherInfo[self.type]
		elif self.type == "forecastTomorrow2Day":
			return WeatherInfo[self.type]
		elif self.type == "forecastTomorrow2Date":
			return WeatherInfo[self.type]
		elif self.type == "forecastTomorrow2TempMin":
			return WeatherInfo[self.type] + " " + self.getCF()
		elif self.type == "forecastTomorrow2TempMax":
			return WeatherInfo[self.type] + " " + self.getCF()
		elif self.type == "forecastTomorrow2Text":
			return WeatherInfo[self.type]
		elif self.type == "forecastTomorrow3Code":
			return WeatherInfo[self.type]
		elif self.type == "forecastTomorrow3Day":
			return WeatherInfo[self.type]
		elif self.type == "forecastTomorrow3Date":
			return WeatherInfo[self.type]
		elif self.type == "forecastTomorrow3TempMin":
			return WeatherInfo[self.type] + " " + self.getCF()
		elif self.type == "forecastTomorrow3TempMax":
			return WeatherInfo[self.type] + " " + self.getCF()
		elif self.type == "forecastTomorrow3Text":
			return WeatherInfo[self.type]
		elif self.type == "title":
			return self.getCF() + " | " + WeatherInfo[self.type]
		elif self.type == "CF":
			return self.getCF() 
		else:
			return ""

	def getCF(self):
		if config.plugins.AtileHD.tempUnit.value == "Fahrenheit":
			return "°F"
		else: 
			return "°C"

	text = property(getText)

class WeatherData:
	def __init__(self):
		self.WeatherInfo = WeatherInfo = { 
			"currentLocation": "N/A",
			"currentWeatherCode": "(",
			"currentWeatherText": "N/A",
			"currentWeatherTemp": "=",
			"forecastTodayCode": "(",
			"forecastTodayText": "N/A",
			"forecastTodayDay": "N/A",
			"forecastTodayDate": "N/A",
			"forecastTodayTempMin": "0",
			"forecastTodayTempMax": "0",
			"forecastTomorrowCode": "(",
			"forecastTomorrowText": "N/A",
			"forecastTomorrowDay": "N/A",
			"forecastTomorrowDate": "N/A",
			"forecastTomorrowTempMin": "0",
			"forecastTomorrowTempMax": "0",
			"forecastTomorrow1Code": "(",
			"forecastTomorrow1Text": "N/A",
			"forecastTomorrow1Day": "N/A",
			"forecastTomorrow1Date": "N/A",
			"forecastTomorrow1TempMin": "0",
			"forecastTomorrow1TempMax": "0",
			"forecastTomorrow2Code": "(",
			"forecastTomorrow2Text": "N/A",
			"forecastTomorrow2Day": "N/A",
			"forecastTomorrow2Date": "N/A",
			"forecastTomorrow2TempMin": "0",
			"forecastTomorrow2TempMax": "0",
			"forecastTomorrow3Code": "(",
			"forecastTomorrow3Text": "N/A",
			"forecastTomorrow3Day": "N/A",
			"forecastTomorrow3Date": "N/A",
			"forecastTomorrow3TempMin": "0",
			"forecastTomorrow3TempMax": "0",
		}
		if config.plugins.AtileHD.refreshInterval.value > 0:
			self.timer = eTimer()
			self.timer.callback.append(self.GetWeather)
			self.GetWeather()

	def downloadError(self, error = None):
		print "[WeatherUpdate] error fetching weather data"

	def GetWeather(self):
		timeout = config.plugins.AtileHD.refreshInterval.value * 1000 * 60
		if timeout > 0:
			self.timer.start(timeout, True)
			print "AtileHD lookup for ID " + str(config.plugins.AtileHD.woeid.value)
			url = "http://query.yahooapis.com/v1/public/yql?q=select%20item%20from%20weather.forecast%20where%20woeid%3D%22"+str(config.plugins.AtileHD.woeid.value)+"%22&format=xml"
			getPage(url,method = 'GET').addCallback(self.GotWeatherData).addErrback(self.downloadError)

	def GotWeatherData(self, data = None):
		if data is not None:
			dom = parseString(data)
			title = self.getText(dom.getElementsByTagName('title')[0].childNodes)
			self.WeatherInfo["currentLocation"] = str(title).split(',')[0].replace("Conditions for ","")

			weather = dom.getElementsByTagName('yweather:condition')[0]
			self.WeatherInfo["currentWeatherCode"] = self.ConvertCondition(weather.getAttributeNode('code').nodeValue)
			self.WeatherInfo["currentWeatherTemp"] = self.getTemp(weather.getAttributeNode('temp').nodeValue)
			self.WeatherInfo["currentWeatherText"] = _(str(weather.getAttributeNode('text').nodeValue))
			
			weather = dom.getElementsByTagName('yweather:forecast')[0]
			self.WeatherInfo["forecastTodayCode"] = self.ConvertCondition(weather.getAttributeNode('code').nodeValue)
			self.WeatherInfo["forecastTodayDay"] = _(weather.getAttributeNode('day').nodeValue)
			self.WeatherInfo["forecastTodayDate"] = self.getWeatherDate(weather)
			self.WeatherInfo["forecastTodayTempMax"] = self.getTemp(weather.getAttributeNode('high').nodeValue)
			self.WeatherInfo["forecastTodayTempMin"] = self.getTemp(weather.getAttributeNode('low').nodeValue)
			self.WeatherInfo["forecastTodayText"] = _(str(weather.getAttributeNode('text').nodeValue))
		
			weather = dom.getElementsByTagName('yweather:forecast')[1]
			self.WeatherInfo["forecastTomorrowCode"] = self.ConvertCondition(weather.getAttributeNode('code').nodeValue)
			self.WeatherInfo["forecastTomorrowDay"] = _(weather.getAttributeNode('day').nodeValue)
			self.WeatherInfo["forecastTomorrowDate"] = self.getWeatherDate(weather)
			self.WeatherInfo["forecastTomorrowTempMax"] = self.getTemp(weather.getAttributeNode('high').nodeValue)
			self.WeatherInfo["forecastTomorrowTempMin"] = self.getTemp(weather.getAttributeNode('low').nodeValue)
			self.WeatherInfo["forecastTomorrowText"] = _(str(weather.getAttributeNode('text').nodeValue))

			weather = dom.getElementsByTagName('yweather:forecast')[2]
			self.WeatherInfo["forecastTomorrow1Code"] = self.ConvertCondition(weather.getAttributeNode('code').nodeValue)
			self.WeatherInfo["forecastTomorrow1Day"] = _(weather.getAttributeNode('day').nodeValue)
			self.WeatherInfo["forecastTomorrow1Date"] = self.getWeatherDate(weather)
			self.WeatherInfo["forecastTomorrow1TempMax"] = self.getTemp(weather.getAttributeNode('high').nodeValue)
			self.WeatherInfo["forecastTomorrow1TempMin"] = self.getTemp(weather.getAttributeNode('low').nodeValue)
			self.WeatherInfo["forecastTomorrow1Text"] = _(str(weather.getAttributeNode('text').nodeValue))

			weather = dom.getElementsByTagName('yweather:forecast')[3]
			self.WeatherInfo["forecastTomorrow2Code"] = self.ConvertCondition(weather.getAttributeNode('code').nodeValue)
			self.WeatherInfo["forecastTomorrow2Day"] = _(weather.getAttributeNode('day').nodeValue)
			self.WeatherInfo["forecastTomorrow2Date"] = self.getWeatherDate(weather)
			self.WeatherInfo["forecastTomorrow2TempMax"] = self.getTemp(weather.getAttributeNode('high').nodeValue)
			self.WeatherInfo["forecastTomorrow2TempMin"] = self.getTemp(weather.getAttributeNode('low').nodeValue)
			self.WeatherInfo["forecastTomorrow2Text"] = _(str(weather.getAttributeNode('text').nodeValue))

			weather = dom.getElementsByTagName('yweather:forecast')[4]
			self.WeatherInfo["forecastTomorrow3Code"] = self.ConvertCondition(weather.getAttributeNode('code').nodeValue)
			self.WeatherInfo["forecastTomorrow3Day"] = _(weather.getAttributeNode('day').nodeValue)
			self.WeatherInfo["forecastTomorrow3Date"] = self.getWeatherDate(weather)
			self.WeatherInfo["forecastTomorrow3TempMax"] = self.getTemp(weather.getAttributeNode('high').nodeValue)
			self.WeatherInfo["forecastTomorrow3TempMin"] = self.getTemp(weather.getAttributeNode('low').nodeValue)
			self.WeatherInfo["forecastTomorrow3Text"] =_(str(weather.getAttributeNode('text').nodeValue))
			
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
		if config.plugins.AtileHD.tempUnit.value == "Fahrenheit":
			return str(int(round(float(temp),0)))
		else:
			celsius = (float(temp) - 32 ) * 5 / 9
			return str(int(round(float(celsius),0)))

	def getWeatherDate(self, weather):
		cur_weather = str(weather.getAttributeNode('date').nodeValue).split(" ")
		str_weather = cur_weather[0]
		if len(cur_weather) >= 2:
			str_weather += ". " + _(cur_weather[1])
		return str_weather
