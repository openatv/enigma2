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

	def scale(self, num):
		negative = num < 0
		if negative:
			num = -num

		i = self.firstScaleIndex
		scaledNum = round(float(num) / self.scaleTable[i][1], self.decimals)
		while scaledNum >= self.maxVal and i < len(self.scaleTable) - 1:
			i += 1
			scaledNum = round(float(num) / self.scaleTable[i][1], self.decimals)

		if negative:
			scaledNum = -scaledNum

		return ("%.*f" % (self.decimals, scaledNum), self.scaleTable[i][0])

	def __call__(self, num):
		return self.scale(num)

if __name__ == "__main__":
	import sys
	sys.argv.pop(0)
	kwargs = {}
	while '=' in sys.argv[0]:
		(arg, val) = sys.argv.pop(0).split("=", 1)
		kwargs[arg] = eval(val)
	scaler = UnitScaler(**kwargs)
	for arg in sys.argv:
		val = eval(arg)
		print arg, val, scaler(val)
