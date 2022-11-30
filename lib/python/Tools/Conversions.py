from locale import format_string
from time import localtime, time, strftime, strptime

from Components.config import config


def formatDate(date):  # "date" must be a string "YYYY-MM-DD", "YYYYMMDD" or integer YYYYMMDD.
	try:
		date = str(date) if isinstance(date, int) else date.strip().replace("-", "").replace("/", "").replace(":", "").replace(",", "").replace(".", "").replace(" ", "")
		return strftime(config.usage.date.long.value, strptime(date, "%Y%m%d"))
	except Exception:
		pass
	return _("Unknown")


def fuzzyDate(date, inPast=False):
	dateLocal = localtime(date)
	now = time()
	nowLocal = localtime(now)
	if dateLocal[:3] == nowLocal[:3]:  # Time is the same day.
		formattedDate = _("Today")
	elif dateLocal[0] == nowLocal[0] and dateLocal[7] == nowLocal[7] - 1 and inPast:  # Time is the previous day. (Doesn't work on New Year's day!)
		formattedDate = _("Yesterday")
	elif ((date - now) < 7 * 86400) and (now < date) and not inPast:  # Time is in the same week (must be in the future).
		formattedDate = strftime("%a", dateLocal)
	elif dateLocal[0] == nowLocal[0]:  # Time is in the same year.
		if inPast:  # The day is wanted in MediaList.
			formattedDate = strftime(config.usage.date.dayshort.value, dateLocal)
		else:
			formattedDate = strftime(config.usage.date.short.value, dateLocal)
	else:
		formattedDate = strftime(config.usage.date.long.value, dateLocal)
	timeLocal = strftime(config.usage.time.short.value, dateLocal)
	return formattedDate, timeLocal


def scaleNumber(number, style="Si", suffix="B", format="%.3f"):
	units = ["", "K", "M", "G", "T", "P", "E", "Z", "Y"]
	style = style.capitalize()
	# if style == "Auto":
	# 	style = config.usage.scaleUnits.value
	if style not in ("Si", "Iec", "Jedec"):
		print("[Conversions] Error: Invalid number unit style '%s' specified so 'Si' is assumed!" % style)
	if style == "Si":
		units[1] = units[1].lower()
	negative = number < 0
	if negative:
		number = -number
	digits = len(str(number))
	scale = int((digits - 1) // 3)
	result = float(number) / (10 ** (scale * 3)) if style == "Si" else float(number) / (1024 ** scale)
	if negative:
		result = -result
	# print("[Conversions] DEBUG: Number=%d, Digits=%d, Scale=%d, Factor=%d, Result=%f." % (number, digits, scale, 10 ** (scale * 3), result))
	# if suffix:
	return "%s %s%s%s" % (format_string(format, result), units[scale], ("i" if style == "Iec" and scale else ""), suffix)
	# return format_string("%d", result, grouping=True) if isinstance(


class UnitMultipliers:
	Si = (
		("", 10 ** 0),
		("k", 10 ** 3),
		("M", 10 ** 6),
		("G", 10 ** 9),
		("T", 10 ** 12),
		("P", 10 ** 15),
		("E", 10 ** 18),
		("Z", 10 ** 21),
		("Y", 10 ** 24)
	)
	SiFull = (
		("y", 10 ** -24),
		("z", 10 ** -21),
		("a", 10 ** -18),
		("f", 10 ** -15),
		("p", 10 ** -12),
		("n", 10 ** -9),
		("u", 10 ** -6),
		("m", 10 ** -3),
	) + Si
	Iec = (
		("", 1024 ** 0),
		("Ki", 1024 ** 1),
		("Mi", 1024 ** 2),
		("Gi", 1024 ** 3),
		("Ti", 1024 ** 4),
		("Pi", 1024 ** 5),
		("Ei", 1024 ** 6),
		("Zi", 1024 ** 7),
		("Yi", 1024 ** 8),
	)
	Jedec = (
		("", 1024 ** 0),
		("K", 1024 ** 1),
		("M", 1024 ** 2),
		("G", 1024 ** 3),
		("T", 1024 ** 4),
		("P", 1024 ** 5),
		("E", 1024 ** 6),
		("Z", 1024 ** 7),
		("Y", 1024 ** 8),
	)
	Default = Si


class UnitScaler:
	def __init__(self, scaleTable=UnitMultipliers.Default, firstScaleIndex=1, maxNumLen=4, decimals=0):
		self.scaleTable = scaleTable
		self.firstScaleIndex = min(firstScaleIndex, len(scaleTable) - 1)
		self.maxNumLen = max(maxNumLen, 3)
		self.decimals = decimals
		self.maxVal = 10 ** maxNumLen

	def scale(self, number):
		negative = number < 0
		if negative:
			number = -number
		index = self.firstScaleIndex
		scaledNum = round(float(number) / self.scaleTable[index][1], self.decimals)
		while scaledNum >= self.maxVal and index < len(self.scaleTable) - 1:
			index += 1
			scaledNum = round(float(number) / self.scaleTable[index][1], self.decimals)
		if negative:
			scaledNum = -scaledNum
		return ("%.*f" % (self.decimals, scaledNum), self.scaleTable[index][0])

	def __call__(self, number):
		return self.scale(number)


class NumberScaler:
	def __init__(self):
		self.styles = {
			"Si": UnitMultipliers.Si,
			"Sifull": UnitMultipliers.SiFull,
			"Iec": UnitMultipliers.Iec,
			"Jedec": UnitMultipliers.Jedec
		}

	def scale(self, number, style=None, suffix="B", firstScaleIndex=1, maxNumLen=4, decimals=0):
		if style is None:
			style = "Si"  # config.usage.scaleUnits.value
		style = style.capitalize()
		if style not in ("Si", "Sifull", "Iec", "Jedec"):
			print("[Conversions] Error: Invalid number unit style '%s' specified so '%s' is assumed!" % (style, config.usage.scaleUnits.value))
		scaleTable = self.styles.get(style, UnitMultipliers.Default)
		firstScaleIndex = min(firstScaleIndex, len(scaleTable) - 1)
		maxNumLen = max(maxNumLen, 3)
		maxVal = 10 ** maxNumLen
		negative = number < 0
		if negative:
			number = -number
		index = firstScaleIndex
		scaledNum = round(float(number) / scaleTable[index][1], decimals)
		while scaledNum >= maxVal and index < len(scaleTable) - 1:
			index += 1
			scaledNum = round(float(number) / scaleTable[index][1], decimals)
		if negative:
			scaledNum = -scaledNum
		return "%s %s%s" % ("%.*f" % (decimals, scaledNum), scaleTable[index][0], suffix)
