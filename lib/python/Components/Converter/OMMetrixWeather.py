#!/usr/bin/env python
# -*- coding: iso-8859-1 -*-
#######################################################################
#
#    MetrixWeather for Enigma2
#    Coded by Sinthex IT-Solutions (c) 2014
#    www.open-store.net
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
from Components.Converter.Converter import Converter
from Components.config import config, ConfigText, ConfigNumber, ConfigDateTime
from Components.Element import cached

class OMMetrixWeather(Converter, object):

	def __init__(self, type):
		Converter.__init__(self, type)
		self.type = type

	@cached

	def getText(self):
		try:
			if config.plugins.MetrixWeather.enabled.saved_value:
				if self.type == "currentLocation":
					return config.plugins.MetrixWeather.currentLocation.saved_value
				if self.type == "currentWeatherTemp":
					return config.plugins.MetrixWeather.currentWeatherTemp.saved_value
				elif self.type == "currentWeatherText":
					return config.plugins.MetrixWeather.currentWeatherText.saved_value
				elif self.type == "currentWeatherCode":
					return config.plugins.MetrixWeather.currentWeatherCode.saved_value
				elif self.type == "forecastTodayCode":
					return config.plugins.MetrixWeather.forecastTodayCode.saved_value
				elif self.type == "forecastTodayTempMin":
					return config.plugins.MetrixWeather.forecastTodayTempMin.saved_value + " " + self.getCF()
				elif self.type == "forecastTodayTempMax":
					return config.plugins.MetrixWeather.forecastTodayTempMax.saved_value + " " + self.getCF()
				elif self.type == "forecastTodayText":
					return config.plugins.MetrixWeather.forecastTodayText.saved_value
				elif self.type == "forecastTodayDay":
					return config.plugins.MetrixWeather.forecastTodayDay.saved_value
				elif self.type == "forecastTomorrowCode":
					return config.plugins.MetrixWeather.forecastTomorrowCode.saved_value
				elif self.type == "forecastTomorrowTempMin":
					return config.plugins.MetrixWeather.forecastTomorrowTempMin.saved_value + " " + self.getCF()
				elif self.type == "forecastTomorrowTempMax":
					return config.plugins.MetrixWeather.forecastTomorrowTempMax.saved_value + " " + self.getCF()
				elif self.type == "forecastTomorrowText":
					return config.plugins.MetrixWeather.forecastTomorrowText.saved_value
				elif self.type == "forecastTomorrowDay":
					return config.plugins.MetrixWeather.forecastTomorrowDay.saved_value
				elif self.type == "forecast2daysCode":
					return config.plugins.MetrixWeather.forecast2daysCode.saved_value
				elif self.type == "forecast2daysTempMin":
					return config.plugins.MetrixWeather.forecast2daysTempMin.saved_value + " " + self.getCF()
				elif self.type == "forecast2daysTempMax":
					return config.plugins.MetrixWeather.forecast2daysTempMax.saved_value + " " + self.getCF()
				elif self.type == "forecast2daysText":
					return config.plugins.MetrixWeather.forecast2daysText.saved_value
				elif self.type == "forecast2daysDay":
					return config.plugins.MetrixWeather.forecast2daysDay.saved_value
				elif self.type == "forecast3daysCode":
					return config.plugins.MetrixWeather.forecast3daysCode.saved_value
				elif self.type == "forecast3daysTempMin":
					return config.plugins.MetrixWeather.forecast3daysTempMin.saved_value + " " + self.getCF()
				elif self.type == "forecast3daysTempMax":
					return config.plugins.MetrixWeather.forecast3daysTempMax.saved_value + " " + self.getCF()
				elif self.type == "forecast3daysText":
					return config.plugins.MetrixWeather.forecast3daysText.saved_value
				elif self.type == "forecast3daysDay":
					return config.plugins.MetrixWeather.forecast3daysDay.saved_value
				elif self.type == "forecast4daysCode":
					return config.plugins.MetrixWeather.forecast4daysCode.saved_value
				elif self.type == "forecast4daysTempMin":
					return config.plugins.MetrixWeather.forecast4daysTempMin.saved_value + " " + self.getCF()
				elif self.type == "forecast4daysTempMax":
					return config.plugins.MetrixWeather.forecast4daysTempMax.saved_value + " " + self.getCF()
				elif self.type == "forecast4daysText":
					return config.plugins.MetrixWeather.forecast4daysText.saved_value
				elif self.type == "forecast4daysDay":
					return config.plugins.MetrixWeather.forecast4daysDay.saved_value
				elif self.type == "title":
					return self.getCF() + " | " + config.plugins.MetrixWeather.currentLocation.saved_value
				elif self.type == "CF":
					return self.getCF() 
				else:
					return ""
			else:
				return ""
		except:
			return ""
	text = property(getText)

	def getCF(self):
		if config.plugins.MetrixWeather.tempUnit.saved_value == "Fahrenheit":
			return "°F"
		else: 
			return "°C"
