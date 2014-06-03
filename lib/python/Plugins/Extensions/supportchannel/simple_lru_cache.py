#	-*-	coding:	utf-8	-*-

class SimpleLRUCache:

	def __init__(self, size):
		self.cache = []
		self.size = size

	def __contains__(self, key):
		for x in self.cache:
			if x[0] == key:
				return True

		return False

	def __getitem__(self, key):
		for i in range(len(self.cache)):
			x = self.cache[i]
			if x[0] == key:
				del self.cache[i]
				self.cache.append(x)
				return x[1]

		raise KeyError

	def __setitem__(self, key, value):
		for i in range(len(self.cache)):
			x = self.cache[i]
			if x[0] == key:
				if i < (len(self.cache) - 1):
					x[1] = value
					del self.cache[i]
					self.cache.append(x)
				else:
					self.cache[-1][1] = value
				return

		if len(self.cache) == self.size:
			self.cache = self.cache[1:]

		self.cache.append([key, value])

	def __delitem__(self, key):
		for i in range(len(self.cache)):
			if self.cache[i][0] == key:
				del self.cache[i]
				return

		raise KeyError

	def resize(self, x=None):
		assert x > 0
		self.size = x
		if x < len(self.cache):
			del self.cache[:len(self.cache) - x]