# This plugin is free software, you are allowed to
# modify it (if you keep the license),
# but you are not allowed to distribute/publish
# it without source code (this version and your modifications).
# This means you also have to distribute
# source code of your modifications.
#
#
#######################################################################
#    AtileHD Weather for VU+
#    Support: www.vuplus-support.org
#    THX to iMaxxx (c) 2013 for base idea
#######################################################################

from xml.dom.minidom import parseString
import requests

from enigma import eTimer

from Components.Converter.Converter import Converter
from Components.Element import cached
from Components.config import ConfigNumber, ConfigSelection, ConfigSubsection, config

config.plugins.AtileHD = ConfigSubsection()
config.plugins.AtileHD.refreshInterval = ConfigNumber(default="10")
config.plugins.AtileHD.woeid = ConfigNumber(default="640161")
config.plugins.AtileHD.tempUnit = ConfigSelection(default="Celsius", choices=[("Celsius", _("Celsius")), ("Fahrenheit", _("Fahrenheit"))])

weather_data = None


class VWeather(Converter):
	def __init__(self, tokens):
		Converter.__init__(self, tokens)
		global weather_data
		if weather_data is None:
			weather_data = WeatherData()
		self.type = tokens

	def getCF(self):
		return "°F" if config.plugins.AtileHD.tempUnit.value == "Fahrenheit" else "°C"

	@cached
	def getText(self):
		text = ""
		weatherInfo = weather_data.WeatherInfo
		match self.type:
			case "CF":
				text = self.getCF()
			case "title":
				text = f"{self.getCF()} | {weatherInfo[self.type]}"
			case _ if self.type.endswith(("TempMax", "TempMin")) and self.type in weatherInfo:
				text = f"{weatherInfo[self.type]} {self.getCF()}"
			case _ if self.type in weatherInfo:
				text = weatherInfo[self.type]
		return text

	text = property(getText)


class WeatherData:
	def __init__(self):
		self.WeatherInfo = {
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

	def ConvertCondition(self, code):
		code = int(code)
		conditions = {
			"0": (37, 38, 39, 45, 47),
			"B": (32, 34, 36),
			"C": (31, 33),
			"F": (19,),
			"G": (8, 10, 25),
			"H": (28, 30),
			"I": (27, 29),
			"L": (20, 21, 22),
			"N": (26, 44),
			"Q": (9,),
			"R": (11, 12, 40),
			"S": (0, 1, 2, 23, 24),
			"U": (5, 6, 7, 18),
			"W": (13, 14, 15, 16, 41, 42, 43, 46),
			"X": (17, 35),
			"Z": (3, 4)
		}
		return next((condition for condition, codes in conditions.items() if code in codes), ")")

	def downloadError(self, error=None):
		print("[VWeather] error fetching weather data")

	def getTemp(self, temp):
		temp = float(temp)
		if config.plugins.AtileHD.tempUnit.value != "Fahrenheit":
			temp = (temp - 32) * 5 / 9
		return str(int(round(temp, 0)))

	def getText(self, nodelist):
		return "".join(x.data for x in nodelist if x.nodeType == x.TEXT_NODE)

	def GetWeather(self):
		timeout = config.plugins.AtileHD.refreshInterval.value * 1000 * 60
		if timeout > 0:
			self.timer.start(timeout, True)
			woeid = config.plugins.AtileHD.woeid.value
			print(f"[VWeather] lookup for ID {woeid}")
			try:
				response = requests.get(f"http://query.yahooapis.com/v1/public/yql?q=select%20item%20from%20weather.forecast%20where%20woeid%3D%22{woeid}%22&format=xml")
				response.raise_for_status()
			except requests.exceptions.RequestException as error:
				self.downloadError(error)
			else:
				self.GotWeatherData(response.content)

	def getWeatherDate(self, weather):
		weatherDate = str(weather.getAttributeNode("date").nodeValue).split(" ")
		return f"{weatherDate[0]}. {_(weatherDate[1])}" if len(weatherDate) >= 2 else weatherDate[0]

	def GotWeatherData(self, data=None):
		if data is not None:
			dom = parseString(data)
			title = self.getText(dom.getElementsByTagName("title")[0].childNodes)
			self.WeatherInfo["currentLocation"] = str(title).split(",")[0].replace("Conditions for ", "")
			weather = dom.getElementsByTagName("yweather:condition")[0]
			self.WeatherInfo["currentWeatherCode"] = self.ConvertCondition(weather.getAttributeNode("code").nodeValue)
			self.WeatherInfo["currentWeatherTemp"] = self.getTemp(weather.getAttributeNode("temp").nodeValue)
			self.WeatherInfo["currentWeatherText"] = _(str(weather.getAttributeNode("text").nodeValue))
			forecasts = dom.getElementsByTagName("yweather:forecast")
			for index, prefix in enumerate(("forecastToday", "forecastTomorrow", "forecastTomorrow1", "forecastTomorrow2", "forecastTomorrow3")):
				weather = forecasts[index]
				self.WeatherInfo[f"{prefix}Code"] = self.ConvertCondition(weather.getAttributeNode("code").nodeValue)
				self.WeatherInfo[f"{prefix}Day"] = _(weather.getAttributeNode("day").nodeValue)
				self.WeatherInfo[f"{prefix}Date"] = self.getWeatherDate(weather)
				self.WeatherInfo[f"{prefix}TempMax"] = self.getTemp(weather.getAttributeNode("high").nodeValue)
				self.WeatherInfo[f"{prefix}TempMin"] = self.getTemp(weather.getAttributeNode("low").nodeValue)
				self.WeatherInfo[f"{prefix}Text"] = _(str(weather.getAttributeNode("text").nodeValue))
