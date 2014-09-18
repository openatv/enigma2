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
				elif self.type == "forecastTomorrowCode":
					return config.plugins.MetrixWeather.forecastTomorrowCode.saved_value
				elif self.type == "forecastTomorrowTempMin":
					return config.plugins.MetrixWeather.forecastTomorrowTempMin.saved_value + " " + self.getCF()
				elif self.type == "forecastTomorrowTempMax":
					return config.plugins.MetrixWeather.forecastTomorrowTempMax.saved_value + " " + self.getCF()
				elif self.type == "forecastTomorrowText":
					return config.plugins.MetrixWeather.forecastTomorrowText.saved_value
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
