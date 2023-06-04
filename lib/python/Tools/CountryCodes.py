# The ISO3166 list of countries is built by the International module.
#
# The list contains 5 fields:
# 	1: Country name translated to local language
# 	2: ISO3166 ALPHA-2 code
#	3: ISO3166 ALPHA-3 code
#	4: ISO3166 Numeric code
# 	5: English name of the country
#
# The list is sorted by the English name.

ISO3166 = []


def setISO3166(data):
	global ISO3166
	ISO3166 = data
	# print("[CountryCodes] Country codes:\n%s" % "\n".join([str(x) for x in ISO3166]))
