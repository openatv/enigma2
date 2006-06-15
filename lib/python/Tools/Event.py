
class Event:
	def __init__(self, start = None, stop = None):
		self.list = [ ]
		self.start = start
		self.stop = stop
	
	def __call__(self, *args, **kwargs):
		for x in self.list:
			x(*args, **kwargs)

	def listen(self, fnc):
		was_empty = len(self.list) == 0
		self.list.append(fnc)
		if was_empty:
			if self.start:
				self.start()

	def unlisten(self, fnc):
		self.list.remove(fnc)
		if len(self.list) == 0:
			if self.stop:
				self.stop()
