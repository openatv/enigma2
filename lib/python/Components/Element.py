from Tools.CList import CList

# down                       up
# Render Converter Converter Source

# a bidirectional connection

def cached(f):
	name = f.__name__
	def wrapper(self):
		cache = self.cache
		if cache is None:
			return f(self)
		if name not in cache:
			cache[name] = (True, f(self))
		return cache[name][1]
	return wrapper

class ElementError(Exception):
    def __init__(self, message):
        self.msg = message

    def __str__(self):
        return self.msg

class Element(object):
	CHANGED_DEFAULT = 0   # initial "pull" state
	CHANGED_ALL = 1       # really everything changed
	CHANGED_CLEAR = 2     # we're expecting a real update soon. don't bother polling NOW, but clear data.
	CHANGED_SPECIFIC = 3  # second tuple will specify what exactly changed
	CHANGED_POLL = 4      # a timer expired

	SINGLE_SOURCE = True

	def __init__(self):
		self.downstream_elements = CList()
		self.master = None
		self.sources = [ ]
		self.source = None
		self.__suspended = True
		self.cache = None

	def connectDownstream(self, downstream):
		self.downstream_elements.append(downstream)
		if self.master is None:
			self.master = downstream

	def connectUpstream(self, upstream):
		assert not self.SINGLE_SOURCE or self.source is None
		self.sources.append(upstream)
		# self.source always refers to the last recent source added.
		self.source = upstream
		self.changed((self.CHANGED_DEFAULT,))

	def connect(self, upstream):
		self.connectUpstream(upstream)
		upstream.connectDownstream(self)

	# we disconnect from down to up
	def disconnectAll(self):
		# we should not disconnect from upstream if
		# there are still elements depending on us.
		assert len(self.downstream_elements) == 0, "there are still downstream elements left"

		# Sources don't have a source themselves. don't do anything here.
		for s in self.sources:
			s.disconnectDownstream(self)

		if self.source:
			# sources are owned by the Screen, so don't destroy them here.
			self.destroy()
		self.source = None
		self.sources = [ ]

	def disconnectDownstream(self, downstream):
		self.downstream_elements.remove(downstream)
		if self.master == downstream:
			self.master = None

		if len(self.downstream_elements) == 0:
			self.disconnectAll()

	# default action: push downstream
	def changed(self, *args, **kwargs):
		self.cache = { }
		self.downstream_elements.changed(*args, **kwargs)
		self.cache = None

	def setSuspend(self, suspended):
		changed = self.__suspended != suspended
		if not self.__suspended and suspended:
			self.doSuspend(1)
		elif self.__suspended and not suspended:
			self.doSuspend(0)

		self.__suspended = suspended
		if changed:
			for s in self.sources:
				s.checkSuspend()

	suspended = property(lambda self: self.__suspended, setSuspend)

	def checkSuspend(self):
		self.suspended = reduce(lambda x, y: x and y.__suspended, self.downstream_elements, True)

	def doSuspend(self, suspend):
		pass

	def destroy(self):
		pass
