class boundFunction:
	def __init__(self, fnc, *args):
		self.fnc = fnc
		self.args = args
	def __call__(self, *args):
		self.fnc(*self.args + args)
