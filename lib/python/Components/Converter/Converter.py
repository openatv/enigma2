from Tools.Event import Event

class Converter:
	def __init__(self):
		self.changed = Event(start = self.start, stop = self.stop)
	
	def connect(self, source):
		source.changed.listen(self.changed)
		self.source = source
	
	def disconnect(self):
		self.source.changed.unlisten(self.changed)

	def start(self):
		pass
	
	def stop(self):
		pass
