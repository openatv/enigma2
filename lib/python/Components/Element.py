from functools import reduce

from Tools.CList import CList


# Render (Down) - Converter - Converter - Source (Up)
# A bidirectional connection.
#
class Element:
	CHANGED_DEFAULT = 0  # Initial "pull" state.
	CHANGED_ALL = 1  # Really everything changed.
	CHANGED_CLEAR = 2  # We're expecting a real update soon, don't bother polling NOW, but clear data.
	CHANGED_SPECIFIC = 3  # Second tuple will specify what exactly changed.
	CHANGED_POLL = 4  # A timer has expired.

	SINGLE_SOURCE = True

	def __init__(self):
		self.downstream_elements = CList()
		self.master = None
		self.sources = []
		self.source = None
		self.__suspended = True
		self.cache = None
		self.onChanged = []

	def connectDownstream(self, downstream):
		self.downstream_elements.append(downstream)
		if self.master is None:
			self.master = downstream

	def connectUpstream(self, upstream):
		assert not self.SINGLE_SOURCE or self.source is None
		self.sources.append(upstream)
		self.source = upstream  # The self.source always refers to the last recent source added.
		self.changed((self.CHANGED_DEFAULT,))

	def connect(self, upstream):
		self.connectUpstream(upstream)
		upstream.connectDownstream(self)

	def disconnectAll(self):  # We disconnect from down (Renderer) to up (Source).
		# We should not disconnect from upstream if there are still elements depending on us.
		assert len(self.downstream_elements) == 0, "there are still downstream elements left"
		for source in self.sources:  # Sources don't have a source themselves. don't do anything here.
			source.disconnectDownstream(self)
		if self.source:  # Sources are owned by the Screen, so don't destroy them here.
			self.destroy()
		self.source = None
		self.sources = []

	def disconnectDownstream(self, downstream):
		self.downstream_elements.remove(downstream)
		if self.master == downstream:
			self.master = None
		if len(self.downstream_elements) == 0:
			self.disconnectAll()

	def changed(self, *args, **kwargs):  # The default action is to push downstream.
		self.cache = {}
		self.downstream_elements.changed(*args, **kwargs)
		self.cache = None
		for method in self.onChanged:
			method()

	def setSuspend(self, suspended):
		changed = self.__suspended != suspended
		if not self.__suspended and suspended:
			self.doSuspend(1)
		elif self.__suspended and not suspended:
			self.doSuspend(0)
		self.__suspended = suspended
		if changed:
			for source in self.sources:
				source.checkSuspend()

	suspended = property(lambda self: self.__suspended, setSuspend)

	def checkSuspend(self):
		self.suspended = self.downstream_elements and reduce(lambda x, y: x and y.__suspended, self.downstream_elements, True)

	def doSuspend(self, suspend):
		pass

	def destroy(self):
		pass


class ElementError(Exception):
	def __init__(self, message):
		self.msg = message

	def __str__(self):
		return self.msg


def cached(item):
	def wrapper(self):
		cache = self.cache
		if cache is None:
			return item(self)
		if name not in cache:
			cache[name] = (True, item(self))
		return cache[name][1]

	name = item.__name__
	return wrapper
