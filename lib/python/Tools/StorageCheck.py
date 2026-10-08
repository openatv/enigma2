"""One-shot setup validation without blocking the GUI on remote storage."""

from threading import Lock
from twisted.internet.threads import deferToThread
from twisted.python.failure import Failure
from enigma import eTimer

class StoragePathCheck:
	storageCheckLock = Lock()

	def __init__(self, validator, callback):
		self.validator = validator
		self.callback = callback
		self.generation = 0
		self.pending = False
		self.timer = eTimer()
		self.timer.callback.append(self.timedOut)

	def start(self, paths):
		# Keep the slot occupied until the worker actually exits, even after
		# timeout/closing/reopening Setup. Never accumulate stuck NAS workers.
		if self.pending or not self.storageCheckLock.acquire(False):
			return False
		self.generation += 1
		self.pending = True
		self.timer.startLongTimer(5)
		try:
			operation = deferToThread(self.checkPaths, tuple(dict.fromkeys(paths)))
		except Exception:
			self.storageCheckLock.release()
			self.cancel()
			return False
		operation.addBoth(self.finished, self.generation)
		return True

	def checkPaths(self, paths):
		try:
			errors = {}
			for path in paths:
				try:
					self.validator(path)
				except (OSError, ValueError) as err:
					print(f"[StorageCheck] Cannot use '{path}': {err}")
					errors[path] = _("Storage directory '%s' is unavailable or not writable.") % path
			return errors
		finally:
			self.storageCheckLock.release()

	def finished(self, result, generation):
		if generation == self.generation:
			self.pending = False
			self.timer.stop()
			self.callback(None if isinstance(result, Failure) else result)

	def timedOut(self):
		self.cancel()
		self.callback(None)

	def cancel(self):
		self.generation += 1
		self.pending = False
		self.timer.stop()
