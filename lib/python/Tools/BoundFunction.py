class boundFunction:
	def __init__(self, fnc, *args, **kwargs):
		self.fnc = fnc
		self.args = args
		self.kwargs = kwargs
	def __call__(self, *args, **kwargs):
		newkwargs = self.kwargs
		newkwargs.update(kwargs)
		return self.fnc(*self.args + args, **newkwargs)
