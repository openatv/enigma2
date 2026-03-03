from bisect import bisect_left, bisect_right


class TolerantDict:
	def __init__(self, d):
		self.d = dict(d)
		self.keys = sorted(self.d.keys())  # O(n) once

	def get_within(self, q, tol):
		# Find candidate neighbors
		i = bisect_left(self.keys, q)
		best = None
		# right neighbor
		if i < len(self.keys):
			k = self.keys[i]
			if abs(k - q) <= tol:
				best = k
		# left neighbor
		if i > 0:
			k = self.keys[i - 1]
			if abs(k - q) <= tol and (best is None or abs(k - q) < abs(best - q)):
				best = k
		return (best, self.d[best]) if best is not None else (None, None)

	def get_all_in_window(self, q, tol):
		# All keys in [q - tol, q + tol]
		left = bisect_left(self.keys, q - tol)
		right = bisect_right(self.keys, q + tol)
		ks = self.keys[left:right]
		return [(k, self.d[k]) for k in ks]
