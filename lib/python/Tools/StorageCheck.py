"""One-shot setup validation without blocking the GUI on remote storage."""

from threading import Lock
from twisted.internet.threads import deferToThread
from twisted.python.failure import Failure
from enigma import eTimer

storageCheckLock = Lock()


class StoragePathCheck:
	def __init__(self, validator, callback):
		self._validator = validator
		self._callback = callback
		self._generation = 0
		self._pending = False
		self._timer = eTimer()
		self._timer.callback.append(self._timedOut)

	def start(self, paths):
		# Keep the slot occupied until the worker actually exits, even after
		# timeout/closing/reopening Setup. Never accumulate stuck NAS workers.
		if self._pending or not storageCheckLock.acquire(False):
			return False
		self._generation += 1
		self._pending = True
		self._timer.startLongTimer(5)
		try:
			operation = deferToThread(self._run, tuple(dict.fromkeys(paths)))
		except Exception:
			storageCheckLock.release()
			self.cancel()
			return False
		operation.addBoth(self._finished, self._generation)
		return True

	def _run(self, paths):
		try:
			errors = {}
			for path in paths:
				try:
					self._validator(path)
				except (OSError, ValueError) as err:
					print(f"[StorageCheck] Cannot use '{path}': {err}")
					errors[path] = _("Storage directory '%s' is unavailable or not writable.") % path
			return errors
		finally:
			storageCheckLock.release()

	def _finished(self, result, generation):
		if generation == self._generation:
			self._pending = False
			self._timer.stop()
			self._callback(None if isinstance(result, Failure) else result)

	def _timedOut(self):
		self.cancel()
		self._callback(None)

	def cancel(self):
		self._generation += 1
		self._pending = False
		self._timer.stop()
