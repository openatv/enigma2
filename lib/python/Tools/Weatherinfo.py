#################################################################################################################
#                                                                                                               #
#   Weatherinfo for openTV is a multi-platform tool (tested for Enigma2 & Windows, but others very likely       #
#   Coded by Mr.Servo @ openATV and jbleyel @ openATV (c) 2022                                                  #
#   Purpose: get weather forecasts from MSN-Weather and/or OpenWeatherMap (OWM)                                 #
#   Output : DICT (MSN & OWM), JSON-file (MSN & OWM), XML-string (MSN only), XML-file (MSN only)                #
#   MSN : parsing MSN-homepage (without API-Key)                                                                #
#   OWM : accessing API-server (API-Key required)                                                               #
#---------------------------------------------------------------------------------------------------------------#
#   initialization and functions for MSN:                                                                       #
#   WI = WeatherInfo(mode="msn")                                                                                #
#   geodata = WI.getCitylist(...)'      > or set directly tuple geodata = (e.g. 'Berlin', '0', '0')}            #
#   msnxmlData = WI.getmsnxml()         > get XML-string (similar to the old MSN-Weather API)                   #
#   msnxmlData = WI.writemsnxml()       > get XML-string & write as file (similar to the old MSN-Weater API)    #
#---------------------------------------------------------------------------------------------------------------#
#   initialization for OWM:                                                                                     #
#   WI = WeatherInfo(mode="owm", apikey='my_apikey')                                                            #
#   {continue with 'geodata = WI.getCitylist(...)' only, no alternatives possible}                              #
#---------------------------------------------------------------------------------------------------------------#
#   common usage for MSN and OWM                                                                                #
#   geodata = WI.getCitylist(cityname='Berlin', scheme="it-it")     > get a list of search hits                 #
#   WI.start(geodata=geodata, units="metric", scheme="it-it", callback=MyCallbackFunction)                      #
#   DICT = WI.getinfo()                 > alternatively: DICT = WI.info                                         #
#   WI.writejson(filename)              > writes DICT as JSON-string in a file                                  #
#   DICT = WI.getreducedinfo()          > get reduced DICT for a simple forecast (e.g. Metrix-Weather)          #
#   WI.writereducedjson(filename)       > get reduced DICT & write reduced JSON-string as file                  #
#---------------------------------------------------------------------------------------------------------------#
#   Interactive call is also possible by setting WI.start(..., callback=None)   > example: see 'def main(argv)' #
#                                                                                                               #
#################################################################################################################

from sys import exit, argv
from json import dump, loads
from re import search, findall
from urllib.request import quote
from datetime import datetime, timedelta
from requests import get, exceptions
from getopt import getopt, GetoptError
from twisted.internet.reactor import callInThread
from xml.etree.ElementTree import Element, tostring

MODULE_NAME = __name__.split(".")[-1]


class Weatherinfo:
	def __init__(self, newmode="msn", apikey=None):
		self.SOURCES = ["msn", "owm"]  # supported Sourcecodes (the order must not be changed)
		self.DESTINATIONS = ["yahoo", "meteo"]  # supported Iconcodes (the order must not be changed)
		self.msnNorm = {
      					1: "1", 2: "1", 3: "1", 4: "4", 5: "4", 6: "6", 7: "7", 8: "8", 9: "9", 10: "8", 11: "8", 12: "9", 13: "8",
           				14: "8", 15: "7", 16: "7", 17: "8", 18: "9", 19: "8", 20: "7", 21: "9", 22: "8", 23: "8", 24: "7", 25: "7",
               			26: "7", 27: "27", 28: "1", 29: "1", 30: "4", 31: "4", 32: "4", 33: "6", 34: "7", 35: "8", 36: "9", 37: "8",
                  		38: "8", 39: "9", 40: "8", 41: "8", 42: "7", 43: "7", 44: "8", 45: "9", 46: "8", 47: "7", 48: "9", 49: "8",
                    	50: "8", 51: "8", 52: "7", 53: "7", 54: "27", 57: "7", 58: "7", 59: "7", 60: "7", 61: "6", 62: "6", 63: "9",
                     	64: "9", 65: "9", 66: "9", 67: "27", 68: "27", 69: "8", 70: "8", 71: "8", 72: "8", 73: "9", 74: "9", 75: "8",
                      	76: "8", 77: "8", 78: "8", 79: "8", 80: "8", 81: "7", 82: "7", 83: "8", 84: "8", 85: "8", 86: "8", 87: "6",
						88: "6", 89: "9", 90: "9", 91: "6", 92: "6", 93: "6", 94: "6", 95: "9", 96: "9", 101: "1", 102: "1"
      					}
		self.msnCodes = {
      					"1": ("32", "B"), "2": ("34", "B"), "3": ("30", "H"), "4": ("28", "H"), "5": ("26", "N"), "6": ("15", "X"),
                   		"7": ("15", "U"), "8": ("9", "Q"), "9": ("20", "M"), "10": ("10", "X"), "12": ("22", "J"), "14": ("11", "Q"),
                     	"15": ("41", "V"), "16": ("17", "X"), "17": ("9", "Q"), "19": ("9", "Q"), "20": ("14", "U"), "23": ("12", "R"),
                      	"26": ("46", "U"), "27": ("4", "P"), "28": ("31", "C"), "29": ("33", "C"), "30": ("29", "I"), "31": ("27", "I"),
                       	"39": ("22", "K"), "43": ("17", "X"), "44": ("9", "Q"), "50": ("12", "R"), "77": ("5", "W"), "78": ("5", "W"),
                        "82": ("46", "U"), "91": ("24", "S"), "na": ("NA", ")")
						}
		self.owmCodes = {
      					"200": ("4", "O"), "201": ("4", "O"), "202": ("4", "P"), "210": ("39", "O"), "211": ("4", "O"), "212": ("3", "P"),
		 				"221": ("38", "O"), "230": ("4", "O"), "231": ("4", "O"), "232": ("4", "O"), "300": ("9", "Q"), "301": ("9", "Q"),
		   				"302": ("9", "Q"), "310": ("9", "Q"), "311": ("9", "Q"), "312": ("9", "R"), "313": ("11", "R"), "314": ("12", "R"),
			 			"321": ("11", "R"), "500": ("9", "Q"), "501": ("11", "Q"), "502": ("12", "R"), "503": ("45", "R"),
			  			"504": ("45", "R"), "511": ("10", "W"), "520": ("40", "Q"), "521": ("11", "R"), "522": ("45", "R"),
			   			"531": ("40", "Q"), "600": ("13", "U"), "601": ("16", "V"), "602": ("41", "V"), "611": ("18", "X"),
						"612": ("10", "W"), "613": ("17", "X"), "615": ("5", "W"), "616": ("5", "W"), "620": ("14", "U"),
						"621": ("42", "U"), "622": ("46", "V"), "701": ("20", "M"), "711": ("22", "J"), "721": ("21", "E"),
						"731": ("19", "J"), "741": ("20", "E"), "751": ("19", "J"), "761": ("19", "J"), "762": ("22", "J"),
						"771": ("23", "F"), "781": ("0", "F"), "800": ("32", "B"), "801": ("34", "B"), "802": ("30", "H"),
						"803": ("26", "H"), "804": ("28", "N"), "na": ("NA", ")")
	  					}
		self.msnDescs = {
      					"1": "SunnyDayV3", "2": "MostlySunnyDay", "3": "PartlyCloudyDayV3", "4": "MostlyCloudyDayV2", "5": "CloudyV3",
				   		"6": "BlowingHailV2", "7": "BlowingSnowV2", "8": "LightRainV2", "9": "FogV2", "10": "FreezingRainV2",
					 	"12": "HazySmokeV2", "14": "ModerateRainV2", "15": "HeavySnowV2", "16": "HailDayV2", "19": "LightRainV3",
					  	"17": "LightRainShowerDay", "20": "LightSnowV2", "22": "ModerateRainV2", "23": "RainShowersDayV2",
						"24": "RainSnowV2", "26": "SnowShowersDayV2", "27": "ThunderstormsV2", "28": "ClearNightV3",
	  					"29": "MostlyClearNight", "30": "PartlyCloudyNightV2", "31": "MostlyCloudyNightV2",
		   				"32": "ClouddyHazeSmokeNightV2_106", "39": "HazeSmokeNightV2_106", "43": "HailNightV2", "44": "LightRainShowerNight",
			   			"50": "RainShowersNightV2", "67": "ThunderstormsV2", "77": "RainSnowV2", "78": "RainSnowShowersNightV2",
						"82": "SnowShowersNightV2", "91": "WindyV2", "na": "NA"
			   			}
		self.owmDescs = {
      					"200": "thunderstorm with light rain", "201": "thunderstorm with rain", "202": "thunderstorm with heavy rain",
				 		"210": "light thunderstorm", "211": "thunderstorm", "212": "heavy thunderstorm", "221": "ragged thunderstorm",
			   			"230": "thunderstorm with light drizzle", "231": "thunderstorm with drizzle", "232": "thunderstorm with heavy drizzle",
				 		"300": "light intensity drizzle", "301": "drizzle", "302": "heavy intensity drizzle", "310": "light intensity drizzle rain",
					  	"311": "drizzle rain", "312": "heavy intensity drizzle rain", "313": "shower rain and drizzle", "314": "heavy shower rain and drizzle",
					   	"321": "shower drizzle", "500": "light rain", "501": "moderate rain", "502": "heavy intensity rain", "503": "very heavy rain",
						"504": "extreme rain", "511": "freezing rain", "520": "light intensity shower rain", "521": "shower rain", "522": "heavy intensity shower rain",
						"531": "ragged shower rain", "600": "light snow", "601": "Snow", "602": "Heavy snow", "611": "Sleet", "612": "Light shower sleet",
						"613": "Shower sleet", "615": "Light rain and snow", "616": "Rain and snow", "620": "Light shower snow", "621": "Shower snow",
						"622": "Heavy shower snow", "701": "mist", "711": "Smoke", "721": "Haze", "731": "sand/ dust whirls", "741": "fog", "751": "sand",
						"761": "dust", "762": "volcanic ash", "771": "squalls", "781": "tornado", "800": "clear sky", "801": "few clouds: 11-25%",
						"802": "scattered clouds: 25-50%", "803": "broken clouds: 51-84%", "804": "overcast clouds: 85-100%", "na": "not available"
						}
		self.yahooDescs = {
      					"0": "tornado", "1": "tropical storm", "2": "hurricane", "3": "severe thunderstorms", "4": "thunderstorms", "5": "mixed rain and snow",
					   	"6": "mixed rain and sleet", "7": "mixed snow and sleet", "8": "freezing drizzle", "9": "drizzle", "10": "freezing rain",
						"11": "showers", "12": "showers", "13": "snow flurries", "14": "light snow showers", "15": "blowing snow", "16": "snow",
						"17": "hail", "18": "sleet", "19": "dust", "20": "foggy", "21": "haze", "22": "smoky", "23": "blustery", "24": "windy", "25": "cold",
						"26": "cloudy", "27": "mostly cloudy (night)", "28": "mostly cloudy (day)", "29": "partly cloudy (night)", "30": "partly cloudy (day)",
						"31": "clear (night)", "32": "sunny (day)", "33": "fair (night)", "34": "fair (day)", "35": "mixed rain and hail", "36": "hot",
						"37": "isolated thunderstorms", "38": "scattered thunderstorms", "39": "scattered thunderstorms", "40": "scattered showers",
						"41": "heavy snow", "42": "scattered snow showers", "43": "heavy snow", "44": "partly cloudy", "45": "thundershowers",
						"46": "snow showers", "47": "isolated thundershowers", "3200": "not available", "NA": "not available"
						}
		self.meteoDescs = {
      					"!": "windy_rain_inv", "\"": "snow_inv", "#": "snow_heavy_inv", "$": "hail_inv", "%": "clouds_inv", "&": "clouds_flash_inv", "'": "temperature",
					   	"(": "compass", ")": "na", "*": "celcius", "+": "fahrenheit", "0": "clouds_flash_alt", "1": "sun_inv", "2": "moon_inv", "3": "cloud_sun_inv",
						"4": "cloud_moon_inv", "5": "cloud_inv", "6": "cloud_flash_inv", "7": "drizzle_inv", "8": "rain_inv", "9": "windy_inv", "A": "sunrise",
				  		"B": "sun", "C": "moon", "D": "eclipse", "E": "mist", "F": "wind", "G": "snowflake", "H": "cloud_sun", "I": "cloud_moon", "J": "fog_sun",
						"K": "fog_moon", "L": "fog_cloud", "M": "fog", "N": "cloud", "O": "cloud_flash", "P": "cloud_flash_alt", "Q": "drizzle", "R": "rain",
						"S": "windy", "T": "windy_rain", "U": "snow", "V": "snow_alt", "W": "snow_heavy", "X": "hail", "Y": "clouds", "Z": "clouds_flash"
						}
		self.ready = False
		self.error = None
		self.info = None
		self.mode = None
		self.parser = None
		self.geodata = None
		self.units = None
		self.setmode(newmode, apikey)

	def setmode(self, newmode="msn", apikey=None):
		newmode = newmode.lower()
		if newmode in ("msn", "owm"):
			if self.mode != newmode:
				self.mode = newmode
				if newmode == "msn":
					self.apikey = apikey
					self.parser = self.msnparser
				elif newmode == "owm":
					if apikey is None:
						self.parser = None
						self.error = "[%s] ERROR in module 'setmode': API-Key for mode '%s' is missing!" % (MODULE_NAME, newmode)
						return self.error
					else:
						self.apikey = apikey
						self.parser = self.owmparser
			return None
		else:
			self.parser = None
			self.error = "[%s] ERROR in module 'setmode': unknown mode '%s'" % (MODULE_NAME, newmode)
			return self.error

	def getvalue(self, value, idx=1):
		return "N/A" if value is None else value.group(idx)

	def directionsign(self, degree):
		return "." if degree < 0 else ["↑ N", "↗ NE", "→ E", "↘ SE", "↓ S", "↙ SW", "← W", "↖ NW"][round(degree % 360 / 45 % 7.5)]

	def convert2icon(self, src, code):
		if code is None:
			self.error = "[%s] ERROR in module 'convert2icon': input code value is 'None'" % MODULE_NAME
			return None
		code = str(code).strip()
		if src is not None and src.lower() == "msn":
			common = self.msnCodes
		elif src is not None and src.lower() == "owm":
			common = self.owmCodes
		else:
			self.error = "[%s] ERROR in module 'convert2icon': convert source '%s' is unknown. Valid is: %s" % (MODULE_NAME, src, self.SOURCES)
			return None
		result = dict()
		if code in common:
			result["yahooCode"] = common[code][0]
			result["meteoCode"] = common[code][1]
		else:
			result["yahooCode"] = "N/A"
			result["meteoCode"] = "N/A"
			print("[%s] WARNING in module 'convert2icon': key '%s' not found in converting dicts." % (MODULE_NAME, code))
		return result

	def getCitylist(self, cityname=None, scheme="de-de"):
		if cityname is None:
			self.error = "[%s] ERROR in module 'getCitylist': missing cityname." % MODULE_NAME
			return None
		if self.mode == "msn":
			apicode = "ïîïééèéìèèèïîììîïì"
			apikey = ''
			for char in apicode:
				apikey += chr(ord(char) ^ 170)
			linkcode = "ÂÞÞÚÙÝÝÝÈÃÄÍÉÅÇËÚÃÜúÆËÉÏÙëßÞÅùßÍÍÏÙÞËÚÚÃÎÙÉÅßÄÞÛÙÙÏÞÇÁÞÙÙÏÞÆËÄÍÙ"
			linkstr = ""
			for char in linkcode:
				linkstr += chr(ord(char) ^ 170)
			link = linkstr % (apikey, cityname, scheme, scheme)
			jsonData = self.apiserver(link)
			if jsonData is None:
				self.error = "[%s] ERROR in module 'getCitylist': no MSN data found." % MODULE_NAME
				return None
			count = 0
			citylist = []
			for hit in jsonData["value"]:
				if hit["_type"] in ["Place", "LocalBusiness"]:
					count += 1
					if count > 9:
						break
					city = hit["name"] if "name" in hit else hit["address"]["text"]
					state = ""
					country = ""
					citylist.append((city + state + country, "0", "0"))
		elif self.mode == "owm":
			exceptions = {"br": "pt_br", "se": "sv, se", "es": "sp, es", "ua": "ua, uk", "cn": "zh_cn"}
			if scheme[:2] in exceptions:
				scheme = exceptions[scheme[:2]]
			items = cityname.split(",")
			city = "".join(items[:-1]).strip() if len(items) > 1 else items[0]
			country = "".join(items[-1:]).strip().upper() if len(items) > 1 else None
			link = "http://api.openweathermap.org/geo/1.0/direct?q=%s,%s&lang=%s&limit=15&appid=%s" % (city, country, scheme[:2], self.apikey)
			jsonData = self.apiserver(link)
			if jsonData is None:
				self.error = "[%s] ERROR in module 'getCitylist': no OWM data found." % MODULE_NAME
				return None
			count = 0
			citylist = []
			for hit in jsonData:
				count += 1
				if count > 9:
					break
				city = hit["local_names"][scheme[:2]] if "local_names" in hit and scheme[:2] in hit["local_names"] else hit["name"]
				state = ", " + hit["state"] if "state" in hit else ""
				country = ", " + hit["country"].upper() if "country" in hit else ""
				citylist.append((city + state + country, str(hit["lon"]), str(hit["lat"])))
		else:
			self.error = "[%s] ERROR in module 'start': unknown mode." % MODULE_NAME
			return None
		return citylist

	def start(self, geodata=None, units="metric", scheme="de-de", callback=None, reduced=False):
		self.geodata = geodata
		self.units = units.lower()
		self.scheme = scheme.lower()
		if self.mode == "msn":
			if geodata[0] is None:
				self.error = "[%s] ERROR in module 'start': missing cityname." % MODULE_NAME
				return None
		elif self.mode == "owm":
			if geodata[1] is None or geodata[2] is None:
				self.error = "[%s] ERROR in module 'start': missing geodata." % MODULE_NAME
				return None
		else:
			self.error = "[%s] ERROR in module 'start': unknown mode." % MODULE_NAME
			return None
		if callback is None:
			info = self.parser(callback, reduced)
			if self.error:
				return None
			else:
				return info
		else:
			callInThread(self.parser, callback, reduced)

	def msnparser(self, callback=None, reduced=False):
		self.ready = False
		self.error = None
		self.info = None
		# some pre-defined localized URLs
		localisation = {"de-de": "de-de/wetter/vorhersage/", "it-it": "it-it/meteo/previsioni/", "cs-cz": "cs-cz/pocasi/predpoved/",
				  		"pl-pl": "pl-pl/pogoda/prognoza/", "pt-pt": "pt-pt/meteorologia/previsao/", "es-es": "es-es/eltiempo/prevision/",
						"fr-fr": "fr-fr/meteo/previsions/", "da-dk": "da-dk/vejr/vejrudsigt/", "sv-se": "sv-se/vader/prognos/",
					 	"fi-fi": "fi-fi/saa/ennuste/", "nb-no": "nb-no/weather/vaermelding/", "tr-tr": "tr-tr/havaduroldumu/havadurumutahmini/",
					  	"el-gr": "el-gr/weather/forecast/", "ru-xl": "ru-xl/weather/forecast/", "ar-sa": "ar-sa/weather/forecast/",
					   	"ja-jp": "ja-jp/weather/forecast/", "ko-kr": "ko-kr/weather/forecast/", "th-th": "th-th/weather/forecast/",
						"vi-vn": "vi-vn/weather/forecast/"
						}
		link = None
		if self.scheme in localisation:
			link = "http://www.msn.com/%s" % localisation.get(self.scheme, "en-us/weather/forecast/")  # fallback to general localized url
		degunit = "F" if self.units == "imperial" else "C"
		if callback is not None:
			print("[%s] accessing MSN for weatherdata..." % MODULE_NAME)
		link += "in-%s?weadegreetype=%s" % (quote(self.geodata[0]), degunit)
		try:
			response = get(link)
			response.raise_for_status()
		except exceptions.RequestException as error:
			self.error = error
			return None
		if callback is not None:
			print("[%s] accessing OWM successful." % MODULE_NAME)
		# parse some data which are not included in JSON-string (embedded in homepage)
		output = response.content.decode("utf-8")
		startpos = output.find('</style><div data-t="')
		endpos = output.find('<script type="text/javascript" id="inlinebody-inline-script"')
		bereich = output[startpos:endpos]
		todayData = search('<div class="iconTempPartContainer-E1_1"><img class="iconTempPartIcon-E1_1" src="(.*?)" title="(.*?)"/></div>', bereich)
		svgsrc = self.getvalue(todayData, 1)
		svgdesc = self.getvalue(todayData, 2)
		svgdata = findall('<img class="iconTempPartIcon-E1_1" src="(.*?)" title="(.*?)"/></div>', bereich)
		# Create DICT "jsonData" from JSON-string and add some useful infos
		startpos = output.find("<script>")
		endpos = output.find("</script>", startpos)
		output = output[startpos:endpos].split("; ")
		if len(output) < 4:
			self.error = "[%s] ERROR in module 'msnparser': json data not found. Try again..." % MODULE_NAME
			return None
		try:
			output = loads(loads(output[0][output[0].find("=") + 1:])["value"])
			jsonData = output["WeatherData"]["_@STATE@_"]
		except IndexError as error:
			self.error = "[%s] ERROR in module 'msnparser': invalid json data from MSN-server. %s" % (MODULE_NAME, error)
			return None
		currdate = datetime.fromisoformat(jsonData["lastUpdated"])
		jsonData["currentCondition"]["deepLink"] = link  # replace by minimized link
		jsonData["currentCondition"]["date"] = currdate.strftime("%Y-%m-%d")  # add some missing info
		jsonData["currentCondition"]["image"]["svgsrc"] = svgsrc
		jsonData["currentCondition"]["image"]["svgdesc"] = svgdesc
		iconCode = self.convert2icon("MSN", jsonData["forecast"][0]["pvdrIcon"])
		if iconCode:
			jsonData["currentCondition"]["yahooCode"] = iconCode["yahooCode"]
			jsonData["currentCondition"]["meteoCode"] = iconCode["meteoCode"]
		else:
			jsonData["currentCondition"]["yahooCode"] = "N/A"
			jsonData["currentCondition"]["meteoCode"] = "N/A"
		jsonData["currentCondition"]["day"] = currdate.strftime("%A")
		jsonData["currentCondition"]["shortDay"] = currdate.strftime("%a")
		for idx, forecast in enumerate(jsonData["forecast"][:-2]):  # last two entries are not usable
			forecast["deepLink"] = link + "&day=%s" % (idx + 1)  # replaced by minimized link
			forecast["date"] = (currdate + timedelta(days=idx)).strftime("%Y-%m-%d")
			if idx < len(svgdata):
				forecast["image"]["svgsrc"] = svgdata[idx][0]
				forecast["image"]["svgdesc"] = svgdata[idx][1]
			else:
				forecast["image"]["svgsrc"] = "N/A"
				forecast["image"]["svgdesc"] = "N/A"
			iconCodes = self.convert2icon("MSN", forecast["pvdrIcon"])
			if iconCodes:
				forecast["yahooCode"] = iconCodes["yahooCode"]
				forecast["meteoCode"] = iconCodes["meteoCode"]
			else:
				forecast["yahooCode"] = "N/A"
				forecast["meteoCode"] = "N/A"
			forecast["day"] = (currdate + timedelta(days=idx)).strftime("%A")
			forecast["shortDay"] = (currdate + timedelta(days=idx)).strftime("%a")
		self.info = jsonData
		self.ready = True
		if callback is None:
			return self.info
		else:
			if reduced:
				callback(self.getreducedinfo(), self.error)
			else:
				callback(self.info, self.error)

	def writejson(self, filename):
		if not self.ready:
			self.error = "[%s] ERROR in module 'writejson': Parser not ready" % MODULE_NAME
			return None
		if self.info is None:
			self.error = "[%s] ERROR in module 'writejson': no data found." % MODULE_NAME
			return None
		with open(filename, "w") as f:
			dump(self.info, f)
		return filename

	def getmsnxml(self):  # only MSN supported
		if not self.ready:
			self.error = "[%s] ERROR in module 'getmsnxml': Parser not ready" % MODULE_NAME
			return None
		root = Element("weatherdata")
		root.set("xmlns:xsd", "http://www.w3.org/2001/XMLSchema")
		root.set("xmlns:xsi", "http://www.w3.org/2001/XMLSchema-instance")
		w = Element("weather")
		w.set("weatherlocationname", self.info["currentLocation"]["displayName"])
		w.set("url", self.info["currentCondition"]["deepLink"])
		w.set("degreetype", self.info["currentCondition"]["degreeSetting"][1:])
		w.set("lat", self.info["currentLocation"]["latitude"])
		w.set("long", self.info["currentLocation"]["longitude"])
		w.set("timezone", str(int(self.info["source"]["location"]["TimezoneOffset"][: 2])))
		w.set("alert", self.info["currentCondition"]["alertSignificance"])
		w.set("encodedlocationname", self.info["currentLocation"]["locality"].encode("ascii", "xmlcharrefreplace").decode().replace(" ", "%20").replace("\n", ""))
		root.append(w)
		c = Element("current")
		c.set("temperature", self.info["currentCondition"]["currentTemperature"])
		c.set("skycode", self.info["currentCondition"]["normalizedSkyCode"])
		c.set("skytext", self.info["currentCondition"]["skycode"]["children"])
		c.set("date", self.info["currentCondition"]["date"])
		c.set("svglink", self.info["currentCondition"]["image"]["svgsrc"])
		c.set("svgdesc", self.info["currentCondition"]["image"]["svgdesc"])
		c.set("yahoocode", self.info["currentCondition"]["yahooCode"])
		c.set("meteocode", self.info["currentCondition"]["meteoCode"])
		c.set("observationtime", self.info["lastUpdated"][11:19])
		c.set("observationpoint", self.info["currentLocation"]["locality"])
		c.set("feelslike", self.info["currentCondition"]["feels"].replace("°", ""))
		c.set("humidity", self.info["currentCondition"]["humidity"].replace("%", ""))
		c.set("winddisplay", self.info["currentCondition"]["windSpeed"] + " " + self.directionsign(self.info["currentCondition"]["windDir"]))
		c.set("winddisplay", "%s %s" % (self.info["currentCondition"]["windSpeed"], self.directionsign(self.info["currentCondition"]["windDir"])))
		c.set("day", self.info["forecast"][0]["dayTextLocaleString"])
		c.set("shortday", self.info["currentCondition"]["shortDay"])
		c.set("windspeed", self.info["currentCondition"]["windSpeed"])
		w.append(c)
		for forecast in self.info["forecast"][:-2]:  # last two entries are not usable
			f = Element("forecast")
			f.set("low", str(forecast["lowTemp"]))
			f.set("high", str(forecast["highTemp"]))
			f.set("skytextday", forecast["cap"])
			f.set("date", forecast["date"])
			f.set("svglink", forecast["image"]["svgsrc"])
			f.set("svgdesc", forecast["image"]["svgdesc"])
			f.set("yahoocode", forecast["yahooCode"])
			f.set("meteocode", forecast["meteoCode"])
			f.set("day", forecast["day"])
			f.set("shortday", forecast["shortDay"])
			f.set("precip", forecast["precipitation"])
			w.append(f)
		return root

	def writemsnxml(self, filename):  # only MSN supported
		if not self.ready:
			self.error = "[%s] ERROR in module 'writemsnxml': Parser not ready" % MODULE_NAME
			return None
		xmlData = self.getmsnxml()
		if xmlData is not None:
			xmlstring = tostring(xmlData, encoding="utf-8", method="html")
			with open(filename, "wb") as f:
				f.write(xmlstring)
			return filename
		self.error = "[%s] ERROR in module 'writemsnxml': no data found." % MODULE_NAME
		return None

	def apiserver(self, link):
		if link is None:
			self.error = "[%s] ERROR in module 'apiserver': missing link." % MODULE_NAME
			return None
		try:
			response = get(link)
			response.raise_for_status()
		except exceptions.RequestException as error:
			self.error = "[%s] ERROR in module 'apiserver': '%s" % (MODULE_NAME, error)
			return None
		try:
			jsonData = loads(response.content)
			if jsonData is None:
				self.error = "[%s] ERROR in module 'apiserver': owm-server access failed." % MODULE_NAME
				return None
		except IndexError as error:
			self.error = "[%s] ERROR in module 'apiserver': invalid json data from OWM-server. %s" % (MODULE_NAME, error)
			return None
		return jsonData

	def owmparser(self, callback=None, reduced=False):
		self.ready = False
		self.error = None
		self.info = None
		if self.geodata is None:
			self.error = "[%s] ERROR in module 'owmparser': missing geodata." % MODULE_NAME
			return None
		if not self.apikey:
			self.error = "[%s] ERROR in module' owmparser': API-key is missing!" % MODULE_NAME
			return None
		link = "https://api.openweathermap.org/data/2.5/onecall?&lon=%s&lat=%s&units=%s&exclude=hourly,minutely&lang=%s&appid=%s" % (self.geodata[1], self.geodata[2], self.units, self.scheme[:2], self.apikey)
		if callback is not None:
			print("[%s] accessing OWM for weatherdata..." % MODULE_NAME)
		jsonData = self.apiserver(link)
		if jsonData is None:
			return None
		if callback is not None:
			print("[%s] accessing OWM successful." % MODULE_NAME)
		jsonData["city"] = self.geodata[0]  # add some missing info
		timestamp = jsonData["current"]["dt"]
		jsonData["current"]["day"] = datetime.fromtimestamp(timestamp).strftime("%A")
		jsonData["current"]["shortDay"] = datetime.fromtimestamp(timestamp).strftime("%a")
		iconCodes = self.convert2icon("OWM", jsonData["current"]["weather"][0]["id"])
		if iconCodes:
			jsonData["current"]["weather"][0]["yahooCode"] = iconCodes["yahooCode"]
			jsonData["current"]["weather"][0]["meteoCode"] = iconCodes["meteoCode"]
		else:
			jsonData["current"]["weather"][0]["yahooCode"] = "N/A"
			jsonData["current"]["weather"][0]["meteoCode"] = "N/A"
		for forecast in jsonData["daily"]:
			timestamp = forecast["dt"]
			forecast["day"] = datetime.fromtimestamp(timestamp).strftime("%A")
			forecast["shortDay"] = datetime.fromtimestamp(timestamp).strftime("%a")
			iconCodes = self.convert2icon("OWM", forecast["weather"][0]["id"])
			if iconCodes:
				forecast["weather"][0]["yahooCode"] = iconCodes["yahooCode"]
				forecast["weather"][0]["meteoCode"] = iconCodes["meteoCode"]
			else:
				forecast["weather"][0]["yahooCode"] = "N/A"
				forecast["weather"][0]["meteoCode"] = "N/A"
			self.info = jsonData
			self.ready = True
		if callback is None:
			return self.info
		else:
			if reduced:
				callback(self.getreducedinfo(), self.error)
			else:
				callback(self.info, self.error)

	def getreducedinfo(self):
			reduced = dict()
			if self.parser is not None and self.mode == "msn":
				current = self.info["currentCondition"]  # current weather
				reduced["source"] = "MSN Weather"
				reduced["name"] = self.info["currentLocation"]["displayName"]
				reduced["id"] = self.info["source"]["id"]
				reduced["longitude"] = self.info["currentLocation"]["longitude"]
				reduced["latitude"] = self.info["currentLocation"]["latitude"]
				reduced["current"] = dict()
				reduced["current"]["observationTime"] = self.info["lastUpdated"]
				reduced["current"]["yahooCode"] = current["yahooCode"]
				reduced["current"]["meteoCode"] = current["meteoCode"]
				reduced["current"]["temp"] = current["currentTemperature"]
				reduced["current"]["feelsLike"] = current["feels"].replace("°", "").strip()
				reduced["current"]["humidity"] = current["humidity"].replace("%", "").strip()
				reduced["current"]["windSpeed"] = current["windSpeed"].replace("km/h", "").replace("mph", "").strip()
				windDir = current["windDir"]
				reduced["current"]["windDir"] = str(windDir)
				reduced["current"]["windDirSign"] = self.directionsign(windDir)
				date = current["date"]
				reduced["current"]["day"] = datetime(int(date[:4]), int(date[5:7]), int(date[8:])).strftime("%A")
				reduced["current"]["shortDay"] = datetime(int(date[:4]), int(date[5:7]), int(date[8:])).strftime("%a")
				reduced["current"]["date"] = date
				reduced["current"]["text"] = current["shortCap"]
				forecast = self.info["forecast"]
				reduced["forecast"] = dict()
				for idx in range(6):  # forecast of today and next 5 days
					reduced["forecast"][idx] = dict()
					reduced["forecast"][idx]["yahooCode"] = forecast[idx]["yahooCode"]
					reduced["forecast"][idx]["meteoCode"] = forecast[idx]["meteoCode"]
					reduced["forecast"][idx]["minTemp"] = str(forecast[idx]["lowTemp"])
					reduced["forecast"][idx]["maxTemp"] = str(forecast[idx]["highTemp"])
					date = forecast[idx]["date"]
					reduced["forecast"][idx]["day"] = datetime(int(date[:4]), int(date[5:7]), int(date[8:])).strftime("%A")
					reduced["forecast"][idx]["shortDay"] = datetime(int(date[:4]), int(date[5:7]), int(date[8:])).strftime("%a")
					reduced["forecast"][idx]["date"] = forecast[idx]["date"]
					reduced["forecast"][idx]["text"] = forecast[idx]["cap"]

			elif self.parser is not None and self.mode == "owm":
				current = self.info["current"]  # current weather
				reduced["source"] = "OpenWeatherMap"
				reduced["name"] = self.info["city"]
				reduced["id"] = "N/A"
				reduced["longitude"] = self.geodata[1]
				reduced["latitude"] = self.geodata[2]
				reduced["current"] = dict()
				reduced["current"]["observationTime"] = datetime.fromtimestamp(current["dt"]).astimezone().isoformat()
				reduced["current"]["yahooCode"] = current["weather"][0]["yahooCode"]
				reduced["current"]["meteoCode"] = current["weather"][0]["meteoCode"]
				reduced["current"]["temp"] = str(round(current["temp"]))
				reduced["current"]["feelsLike"] = str(round(current["feels_like"]))
				reduced["current"]["humidity"] = str(round(current["humidity"]))
				reduced["current"]["windSpeed"] = str(round(current["wind_speed"]))
				windDir = str(round(current["wind_deg"]))
				reduced["current"]["windDir"] = windDir
				reduced["current"]["windDirSign"] = self.directionsign(int(windDir))
				reduced["current"]["day"] = current["day"]
				reduced["current"]["shortDay"] = current["shortDay"]
				reduced["current"]["date"] = datetime.fromtimestamp(current["dt"]).strftime("%Y-%m-%d")
				reduced["current"]["text"] = current["weather"][0]["description"]
				forecast = self.info["daily"]
				reduced["forecast"] = dict()
				for idx in range(6):  # forecast of today and next 5 days
					reduced["forecast"][idx] = dict()
					reduced["forecast"][idx]["yahooCode"] = forecast[idx]["weather"][0]["yahooCode"]
					reduced["forecast"][idx]["meteoCode"] = forecast[idx]["weather"][0]["meteoCode"]
					reduced["forecast"][idx]["minTemp"] = str(round(forecast[idx]["temp"]["min"]))
					reduced["forecast"][idx]["maxTemp"] = str(round(forecast[idx]["temp"]["max"]))
					reduced["forecast"][idx]["day"] = forecast[idx]["day"]
					reduced["forecast"][idx]["shortDay"] = forecast[idx]["shortDay"]
					reduced["forecast"][idx]["date"] = datetime.fromtimestamp(forecast[idx]["dt"]).strftime("%Y-%m-%d")
					reduced["forecast"][idx]["text"] = forecast[idx]["weather"][0]["description"]
			else:
				self.error = "[%s] ERROR in module 'getreducedinfo': unknown source." % MODULE_NAME
				return None
			return reduced

	def writereducedjson(self, filename):
		if not self.ready:
			self.error = "[%s] ERROR in module 'writereducedjson': Parser not ready" % MODULE_NAME
			return None
		reduced = self.getreducedinfo()
		if reduced is None:
			self.error = "[%s] ERROR in module 'writereducedjson': no data found." % MODULE_NAME
			return None
		with open(filename, "w") as f:
			dump(reduced, f)
		return filename

	def getinfo(self):
		if not self.ready:
			self.error = "[%s] ERROR in module 'getinfo': Parser not ready" % MODULE_NAME
			return None
		return self.info

	def showDescription(self, src):
		self.error = None
		if src is not None and src.lower() == "msn":
			descs = self.msnDescs
		elif src is not None and src.lower() == "owm":
			descs = self.owmDescs
		elif src is not None and src.lower() == "yahoo":
			descs = self.yahooDescs
		elif src is not None and src.lower() == "meteo":
			descs = self.meteoDescs
		else:
			self.error = "[%s] ERROR in module 'showDescription': convert source '%s' is unknown. Valid is: %s" % (MODULE_NAME, src, self.SOURCES)
			return self.error
		print("+%s+" % ("-" * 38))
		print("| {0:<5}{1:<31} |".format("CODE", "DESCRIPTION_%s (COMPLETE)" % src.upper()))
		print("+%s+" % ("-" * 38))
		for desc in descs:
			print("| {0:<5}{1:<31} |".format(desc, descs[desc]))
		print("+%s+\n" % ("-" * 38))
		return None

	def showConvertrules(self, src, dest):
		if src is None:
			self.error = "[%s] ERROR in module 'showConvertrules': convert source '%s' is unknown. Valid is: %s" % (MODULE_NAME, src, self.SOURCES)
			return self.error
		if dest is not None and dest.lower() == "meteo":
			ddescs = self.meteoDescs
		elif dest is not None and dest.lower() == "yahoo":
			ddescs = self.yahooDescs
		else:
			self.error = "[%s] ERROR in module 'showConvertrules': convert destination '%s' is unknown. Valid is: %s" % (MODULE_NAME, src, self.DESTINATIONS)
			return self.error
		destidx = self.DESTINATIONS.index(dest)
		print("+%s+%s+" % ("-" * 38, "-" * 38))
		if src.lower() == "msn":
			print("| {0:<3} -> {1:<4}{2:<31} | {3:<5}{4:<25} |".format("NEW", "OLD", "DESCRIPTION_ % s(CONVERTER)" % src.upper(), "CODE", "DESCRIPTION_ % s" % dest.upper()))
			print("+%s+%s+" % ("-" * 38, "-" * 38))
			for scode in self.msnNorm:
				dcode = self.msnCodes[self.msnNorm[scode]][destidx]
				print("| {0:<3} -> {1:<4}{2:<31} | {3:<5}{4:<25} |".format(scode, self.msnNorm[scode], self.msnDescs[self.msnNorm[scode]], dcode, ddescs[dcode]))
		elif src.lower() == "owm":
			print("| {0:<5}{1:<31} | {2:<5}{3:<31} |".format("CODE", "DESCRIPTION_%s (CONVERTER)" % src.upper(), "CODE", "DESCRIPTION_%s" % dest.upper()))
			print("+%s+%s+" % ("-" * 38, "-" * 38))
			for scode in self.owmCodes:
				dcode = self.owmCodes[scode][destidx]
				print("| {0:<5}{1:<31} | {2:<5}{3:<31} |".format(scode, self.owmDescs[scode], dcode, ddescs[dcode]))
		else:
			self.error = "[%s] ERROR in module 'showConvertrules': convert source '%s' is unknown. Valid is: %s" % (MODULE_NAME, src, self.SOURCES)
			return self.error
		print("+%s+%s+\n" % ("-" * 38, "-" * 38))
		return None


def main(argv):
	city = ""
	units = "metric"
	scheme = "de-de"
	mode = "msn"
	apikey = None
	quiet = False
	control = False
	json = None
	reduced = None
	xml = None
	helpstring = "Weatherinfo v1.0: try 'Weatherinfo -h' for more information"
	try:
		opts, args = getopt(argv, "hqm:a:j:r:x:s:u:c", ["quiet =", "mode=", "apikey=", "json =", "reduced =", "xml =", "scheme =", "units =", "control ="])
	except GetoptError:
		print(helpstring)
		exit(2)
	for opt, arg in opts:
		opt = opt.lower().strip()
		arg = arg.lower().strip()
		if opt == "-h":
			print("Usage: Weatherinfo [options...] <cityname>\n"
			"-m, --mode <data>\t\tValid modes: 'owm' or 'msn' {'msn' is default}\n"
			"-a, --apikey <data>\t\tAPI-key required for 'owm' only\n"
			"-j, --json <filename>\t\tFile output formatted in JSON (all modes)\n"
			"-r, --reduced <filename>\tFile output formatted in JSON (minimum infos only)\n"
			"-x, --xml <filename>\t\tFile output formatted in XML (mode 'msn' only)\n"
			"-s, --scheme <data>\t\tCountry scheme {'de-de' is default}\n"
			"-u, --units <data>\t\tValid units: 'imperial' or 'metric' {'metric' is default}\n"
			"-c, --control\t\t\tShow iconcode-plaintexts and conversion rules\n"
			"-q, --quiet\t\t\tPerform without text output and select first found city")
			exit()
		elif opt in ("-u", "--units:"):
			if arg == "metric":
				units = arg
			elif arg == "imperial":
				units = arg
			else:
				print("ERROR: units '%s' is invalid. Valid parameters: 'metric' or 'imperial'" % arg)
				exit()
		elif opt in ("-j", "--json"):
			json = arg
		elif opt in ("-r", "--reduced"):
			reduced = arg
		elif opt in ("-x", "--xml"):
			xml = arg
		elif opt in ("-s", "--scheme"):
			scheme = arg
		elif opt in ("-m", "--mode"):
			if arg in ["msn", "owm"]:
				mode = arg
			else:
				print("ERROR: mode '%s' is invalid. Valid parameters: 'msn' or 'owm'" % arg)
				exit()
		elif opt in ("-a", "--apikey"):
			apikey = arg
		elif opt in ("-c", "control"):
			control = True
		elif opt in ("-q", "--quiet"):
			quiet = True
	if len(args) == 0 and not control:
		print(helpstring)
		exit()
	for part in args:
		city += part + " "
	city = city.strip()
	if len(city) < 3 and not control:
		print("ERROR: Cityname too short, please use at least 3 letters!")
		exit()
	weather = Weatherinfo(mode, apikey)
	if weather.error:
		print(weather.error.replace("[__main__]", ""))
		exit()
	if control:
		for src in weather.SOURCES + weather.DESTINATIONS:
			if weather.showDescription(src):
				print(weather.error.replace("[__main__]", ""))
		for src in weather.SOURCES:
			for dest in weather.DESTINATIONS:
				if weather.showConvertrules(src, dest):
					print(weather.error.replace("[__main__]", ""))
		exit()
	citylist = weather.getCitylist(city, scheme)
	if weather.error:
		print(weather.error.replace("[__main__]", ""))
		exit()
	if len(citylist) == 0:
		print("No cites found. Try another wording.")
		exit()
	geodata = citylist[0]
	if citylist and len(citylist) > 1 and not quiet:
		print("Found the following cities/areas:")
		for idx, item in enumerate(citylist):
			lon = " [lon=%s" % item[1] if float(item[1]) != 0.0 else ""
			lat = ", lat=%s]" % item[2] if float(item[2]) != 0.0 else ""
			print("%s = %s%s%s" % (idx + 1, item[0], lon, lat))
		choice = input("Select (1-%s)? : " % len(citylist))[:1]
		index = ord(choice) - 48 if len(choice) > 0 else -1
		if index > 0 and index < len(citylist) + 1:
			geodata = citylist[index - 1]
		else:
			print("Choice '%s' is not allowable (only numbers 1 to %s are valid).\nPlease try again." % (choice, len(citylist)))
			exit()
	info = weather.start(geodata=geodata, units=units, scheme=scheme)  # INTERACTIVE CALL (unthreaded)
	if info is not None and not control:
		if not quiet:
			if mode == "msn":
				print("Using city/area: %s" % info["currentLocation"]["displayName"])
			elif mode == "owm":
				if 'cod' in info:
					print("Found city/area: %s" % info["city"]["name"])
				else:
					print("Using city/area: %s [lon=%s, lat=%s]" % (info['city'], info["lon"], info["lat"]))
		if json:
			weather.writejson(json)
			if not quiet:
				print("File '%s' was successfully created." % json)
		if reduced:
			weather.writereducedjson(reduced)
			if not quiet:
				print("File '%s' was successfully created." % reduced)
		if xml:
			if mode == "msn":
				weather.writemsnxml(xml)
				if not quiet:
					print("File '%s' was successfully created." % xml)
			else:
				if not quiet:
					print("ERROR: XML is only supported in mode 'msn'.\nFile '%s' was not created..." % xml)
		exit()
	else:
		if weather.error:
			print(weather.error.replace("[__main__]", ""))
			exit()


if __name__ == "__main__":
   main(argv[1:])
