from collections import deque
from time import monotonic
from traceback import print_exc

from enigma import eTimer


class StartupTasks:
	"""Run optional startup work after the GUI enters its event loop.

	Steps run on the GUI thread and must be short. A step can return a Twisted
	Deferred for independent worker work; its completion resumes the queue on
	the GUI thread. Workers must not create or access Enigma GUI objects.
	"""

	def __init__(self):
		self.tasks = deque()
		self.current = None
		self.started = False
		self.stopped = False
		self.waiting = False
		self.completed = []
		self.failures = []
		self.timer = eTimer()
		self.timer.callback.append(self.runNext)

	def add(self, name, steps):
		if self.stopped or name in self.completed or name == (self.current[0] if self.current else None) or any(x[0] == name for x in self.tasks):
			return
		self.tasks.append((name, iter(steps)))
		if self.started and not self.waiting and not self.timer.isActive():
			self.timer.start(20, True)

	def start(self):
		if not self.started and not self.stopped:
			self.started = True
			# Let initial screen painting and service-start events run first.
			self.timer.start(100, True)

	def stop(self):
		self.stopped = True
		self.timer.stop()
		self.tasks.clear()
		self.current = None

	def runNext(self):
		if self.stopped:
			return
		if self.current is None:
			if not self.tasks:
				return
			self.current = self.tasks.popleft()
			self.taskStarted = monotonic()
			print(f"[StartupTasks] Starting {self.current[0]}.")
		try:
			step = next(self.current[1])
		except StopIteration:
			self.finish()
			return
		except Exception:
			print_exc()
			self.finish(failed=True)
			return
		try:
			result = step()
			if hasattr(result, "addCallbacks"):
				self.waiting = True
				result.addCallbacks(self.resume, self.failed)
			else:
				self.resume()
		except Exception:
			print_exc()
			self.finish(failed=True)

	def resume(self, result=None):
		self.waiting = False
		if not self.stopped:
			self.timer.start(20, True)

	def failed(self, failure):
		if not self.stopped:
			print(f"[StartupTasks] {failure.getTraceback()}")
			self.finish(failed=True)

	def finish(self, failed=False):
		if self.stopped or self.current is None:
			return
		name = self.current[0]
		(self.failures if failed else self.completed).append(name)
		print(f"[StartupTasks] {name} {'failed' if failed else 'ready'} after {monotonic() - self.taskStarted:.3f}s.")
		self.current = None
		self.resume()


startupTasks = StartupTasks()
