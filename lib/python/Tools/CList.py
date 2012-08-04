class CList(list):
	def __getattr__(self, attr):
		return CList([getattr(a, attr) for a in self])

	def __call__(self, *args, **kwargs):
		for x in self:
			x(*args, **kwargs)
