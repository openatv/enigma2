from skin import parseColor, parseFont

# Apply non-standard attributes to object obj (normally a Screen or Component)

# skinAttrs is a dict in this form
# 	attribMap = {
# 		# Plain int
# 		"borderWidth": ("int", "borderWidth"),
# 		# Font
# 		"font": ("font", "bouquetFontName", "bouquetFontSize"),
# 		# Color
# 		"foregroundColor": ("color", "foreColor"),
# 		# String
# 		"extraText": ("str", "extraText"),
# 	}
# The keys are the names of the attribute in the attribute list
# (normally from a skin <screen/> or <widget/>.
# The first element of the tuple is a key to a decoder, and the remaining
# element(s) of the tuple name the attribute(s) that will be created/set
# in obj.
# In the example, the skin attribute font="Regular;20" will set
# obj.bouquetFontName to "Regular" and bouquetFontSize to 20 (an int,
# not a str).

# callerApplyMap allows built-in attribute converters to be over-ridden
# or added to. It has the same form as applyMap in
# applyExtraSkinAttributes().
# The key is a decoder name given as the first element in the tuples
# in attribMap and the value is a callable that will be called to
# decode the skin attribute and created/set it in obj

# applyExtraSkinAttributes() returns a shallow copy of skinAttrs
# with all skin attributes handled by applyExtraSkinAttributes()
# removed.

def applyExtraSkinAttributes(obj, skinAttrs, attribMap, callerApplyMap=None):
	def applyStrAttrib(obj, objAttrs, value):
		setattr(obj, objAttrs[0], value)

	def applyIntAttrib(obj, objAttrs, value):
		setattr(obj, objAttrs[0], int(value))

	def applyFontAttrib(obj, objAttrs, value):
		font = parseFont(value, ((1, 1), (1, 1)))
		setattr(obj, objAttrs[0], font.family)
		setattr(obj, objAttrs[1], font.pointSize)

	def applyColorAttrib(obj, objAttrs, value):
		setattr(obj, objAttrs[0], parseColor(value).argb())

	applyMap = {
		"str": applyStrAttrib,
		"int": applyIntAttrib,
		"font": applyFontAttrib,
		"color": applyColorAttrib,
	}

	# Callers can override/extend function map
	if callerApplyMap is not None:
		applyMap = dict(applyMap.items() + callerApplyMap.items())

	if skinAttrs is not None:
		attribs = []
		for (attrib, value) in skinAttrs:
			if attrib in attribMap:
				mapEnt = attribMap[attrib]
				type = mapEnt[0]
				if type in applyMap:
					applyMap[type](obj, mapEnt[1:], value)
				else:
					print "[applyExtraSkinAttributes]", "Unknown type %s in attribute map for skin attribute %s" % (type, attrib)
			else:
				attribs.append((attrib, value))
		return attribs
	else:
		return None
