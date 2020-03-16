from json import loads
from urllib2 import URLError, urlopen

# Data available from http://ip-api.com/json/:
#
# 	Name		Description				Example			Type
# 	--------------	--------------------------------------	----------------------	------
# 	status		success or fail				success			string
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
# 	currency	National currency			USD			string
# 	isp		ISP name				Google			string
# 	org		Organization name			Google			string
# 	as		AS number and organization, separated
# 			by space (RIR). Empty for IP blocks 
# 			not being announced in BGP tables.	AS15169 Google Inc.	string
# 	asname		AS name (RIR). Empty for IP blocks not
# 			being announced in BGP tables.		GOOGLE			string
# 	reverse		Reverse DNS of the IP
# 			(Not fetched as it delays response)	wi-in-f94.1e100.net	string
# 	mobile		Mobile (cellular) connection		true			bool
# 	proxy		Proxy, VPN or Tor exit address		true			bool
# 	hosting		Hosting, colocated or data center	true			bool
# 	query		IP used for the query			173.194.67.94		string

geolocation = {}

def InitGeolocation():
	global geolocation
	if len(geolocation) == 0:
		try:
			response = urlopen("http://ip-api.com/json/?fields=33288191", data=None, timeout=10).read()
			# print "[Geolocation] DEBUG:", response
			if response:
				geolocation = loads(response)
			status = geolocation.get("status", None)
			if status and status == "success":
				print "[Geolocation] Geolocation data initialised."
			else:
				print "[Geolocation] Error: Geolocation lookup returned a '%s' status!  Message '%s' returned." % (status, geolocation.get("message", None))
		except URLError as err:
			if hasattr(err, 'code'):
				print "[Geolocation] Error: Geolocation data not available! (Code: %s)" % err.code
			if hasattr(err, 'reason'):
				print "[Geolocation] Error: Geolocation data not available! (Reason: %s)" % err.reason
		except ValueError:
			print "[Geolocation] Error: Geolocation data returned can not be processed!"

def RefreshGeolocation():
	global geolocation
	geolocation = {}
	InitGeolocation()
