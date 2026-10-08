from twisted.internet import reactor
from twisted.internet.defer import Deferred
from twisted.python.failure import Failure
from twisted.web.error import Error

from enigma import eInternetCheck

from Tools.Downloader import formatError, getJson


# Data available from http://ip-api.com/json/:
#
# 	Name		Description				Example			Type
# 	--------------	--------------------------------------	----------------------	------
# 	status		"success" or "fail"			success			string
# 	message		Included only when status is fail. Can
# 			be one of the following: private range,
# 			reserved range, invalid query		invalid query		string
# 	continent	Continent name				North America		string
# 	continentCode	Two-letter continent code		NA			string
# 	country		Country name				United States		string
# 	countryCode	Two-letter country code
# 			ISO 3166-1 alpha-2			US			string
# 	region		Region/state short code (FIPS or ISO)	CA or 10		string
# 	regionName	Region/state				California		string
# 	city		City					Mountain View		string
# 	district	District (subdivision of city)		Old Farm District	string
# 	zip		Zip code				94043			string
# 	lat		Latitude				37.4192			float
# 	lon		Longitude				-122.0574		float
# 	timezone	City timezone				America/Los_Angeles	string
# 	offset		Timezone UTC DST offset in seconds	-25200			int
# 	currency	National currency			USD			string
# 	isp		ISP name				Google			string
# 	org		Organization name			Google			string
# 	as		AS number and organization, separated
# 			by space (RIR). Empty for IP blocks
# 			not being announced in BGP tables.	AS15169 Google Inc.	string
# 	asname		AS name (RIR). Empty for IP blocks not
# 			being announced in BGP tables.		GOOGLE			string
# 	reverse		Reverse DNS of the IP			wi-in-f94.1e100.net	string
# 			(Warning: Requesting this field can delay response!)
# 	mobile		Mobile (cellular) connection		true			bool
# 	proxy		Proxy, VPN or Tor exit address		true			bool
# 	hosting		Hosting, colocated or data center	true			bool
# 	query		IP used for the query			173.194.67.94		string
geolocationFields = {
	"country": 0x00000001,
	"countryCode": 0x00000002,
	"region": 0x00000004,
	"regionName": 0x00000008,
	"city": 0x00000010,
	"zip": 0x00000020,
	"lat": 0x00000040,
	"lon": 0x00000080,
	"timezone": 0x00000100,
	"isp": 0x00000200,
	"org": 0x00000400,
	"as": 0x00000800,
	"reverse": 0x00001000,
	"query": 0x00002000,
	"status": 0x00004000,
	"message": 0x00008000,
	"mobile": 0x00010000,
	"proxy": 0x00020000,
	# "": 0x00040000,
	"district": 0x00080000,
	"continent": 0x00100000,
	"continentCode": 0x00200000,
	"asname": 0x00400000,
	"currency": 0x00800000,
	"hosting": 0x01000000,
	"offset": 0x02000000
}


class Geolocation:
	def __init__(self):
		self.geolocation = {}
		self.internetChecks = {}
		# Enable this line to force load the geolocation data on initialization.
		# NOT: Doing this without user consent may violate privacy laws!
		# self.getGeolocationData(fields=None)

	def checkInternetAccess(self, host, timeout):
		""" Runs eInternetCheck in its own thread, the SWIG call to checkInternetAccess() would hold the GIL. """
		def checkCallback(result):
			reactor.callLater(0, self.internetChecks.pop, key)  # Release the check outside of its own callback.
			deferred.callback(result)

		deferred = Deferred()
		key = object()  # The callback must not reference the check, else the check is never freed.
		check = eInternetCheck()
		check.callback.get().append(checkCallback)
		self.internetChecks[key] = check
		check.startThread(host, timeout, True)
		return deferred

	def getGeolocationData(self, fields=None, useCache=True, screen=None, callback=None):
		""" Returns a Deferred with the geolocation data or {} on failure.
			The callback is called with the geolocation data.
			With screen it does not fire anymore once that screen is closed. """
		async def fetch():
			geolocation = await self.fetchGeolocationData(fields, useCache)
			if screenClosed:
				await Deferred()  # Never fires, the waiting caller is dropped with its screen.
			return geolocation

		screenClosed = []
		if screen is not None:
			screen.onClose.append(lambda: screenClosed.append(True))
		deferred = Deferred.fromCoroutine(fetch())
		if callback:
			deferred.addCallback(callback)
		return deferred

	async def fetchGeolocationData(self, fields, useCache):
		fields = self.fieldsToNumber(fields)
		if useCache and self.checkGeolocationData(fields):
			print("[Geolocation] Using cached data.")
			return self.geolocation
		internetAccess = await self.checkInternetAccess("ip-api.com", 5)
		if internetAccess == 0:  # 0=Site reachable, 1=DNS error, 2=Other network error, 3=No link, 4=No active adapter.
			try:
				geolocation = await getJson(f"http://ip-api.com/json/?fields={fields}", timeout=5)
				if not isinstance(geolocation, dict):
					raise ValueError("Geolocation data is not a JSON object")
				status = geolocation.get("status", "unknown/undefined")
				if status == "success":
					print("[Geolocation] Geolocation data retrieved.")
					self.geolocation.update(geolocation)
					return self.geolocation
				print(f"[Geolocation] Error: Geolocation lookup returned '{status}' status!  Message '{geolocation.get('message')}' returned.")
			except Error as err:
				print(f"[Geolocation] Error: Geolocation lookup returned a status code of {int(err.status)}!")
			except ValueError:
				print("[Geolocation] Error: Geolocation data returned can not be processed!")
			except Exception:
				print(f"[Geolocation] Error: Geolocation server connection failure! ({formatError(Failure())})")
		elif internetAccess == 1:
			print("[Geolocation] Error: Geolocation server DNS error!")
		elif internetAccess == 2:
			print("[Geolocation] Error: Internet access error!")
		elif internetAccess == 3:
			print("[Geolocation] Error: Network adapter not connected to a network!")
		elif internetAccess == 4:
			print("[Geolocation] Error: No network adapter enabled/available!")
		return {}

	def fieldsToNumber(self, fields):
		if fields is None:
			fields = [x for x in geolocationFields.keys() if x not in ("message", "reverse", "status")]  # Don't include "reverse" by default as there is a performance hit!
		elif isinstance(fields, str):
			fields = [x.strip() for x in fields.split(",")]
		if isinstance(fields, int):
			number = fields
		else:
			number = 0
			for field in fields:
				value = geolocationFields.get(field, 0)
				if value:
					number |= value
				else:
					print(f"[Geolocation] Warning: Ignoring invalid geolocation field '{field}'!")
		# print("[Geolocation] DEBUG: fields='%s' -> number=%d." % (sorted(fields), number))
		return number | 0x0000C000  # Always get "status" and "message".

	def checkGeolocationData(self, fields):
		keys = list(self.geolocation.keys())
		for field in [x for x in geolocationFields.keys() if x != "message"]:
			value = geolocationFields[field]
			# print("[Geolocation] DEBUG: field '%s', value=%d, fields=%d, match=%d." % (field, value, fields, fields & value))
			if fields & value and field not in keys:
				# print("[Geolocation] DEBUG: Required value not in cache.")
				return False
		# print("[Geolocation] DEBUG: Required value(s) in cache.")
		return True

	def clearGeolocationData(self):
		self.geolocation = {}


geolocation = Geolocation()
