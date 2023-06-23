from os import remove
from os.path import isfile
from sys import _current_frames
from threading import Thread, current_thread
from time import sleep
from traceback import extract_stack

from Components.config import config


class StackTracePrinter(Thread):
	@classmethod
	def getInstance(self):
		return self.instance

	instance = None

	def __init__(self):
		Thread.__init__(self)
		print("[StackTrace] Initializing StackTracePrinter.")
		StackTracePrinter.instance = self
		self.__running = False

	def activate(self, MainThread_ident):
		print("[StackTrace] Activating StackTracePrinter.")
		self.MainThread_ident = MainThread_ident
		if not self.__running:
			self.__running = True
			self.start()

	def run(self):
		while (self.__running == True):
			if (isfile("/tmp/doPythonStackTrace")):
				remove("/tmp/doPythonStackTrace")
				if config.crash.pystackonspinner.value:
					log = []
					log.append("[StackTrace] ========== Stacktrace of active Python threads ===========")
					for threadId, stack in list(_current_frames().items()):
						if (threadId != current_thread().ident):
							if (threadId == self.MainThread_ident):
								log.append("[StackTrace] ========== MainThread 0x%08x =========================" % threadId)
							else:
								log.append("[StackTrace] ========== Thread ID  0x%08x =========================" % threadId)
							for filename, lineno, name, line in extract_stack(stack):
								log.append('[StackTrace] File: "%s", line %d, in %s' % (filename, lineno, name))
								if line:
									log.append("[StackTrace]   %s" % (line.strip()))
					del stack
					log.append("[StackTrace] ========== Stacktrace end ================================")
					for line in log:  # This is done so that each line of the output is timestamped.
						print(line)
			sleep(1)
		Thread.__init__(self)

	def deactivate(self):
		print("[StackTrace] Deactivating StackTracePrinter.")
		self.__running = False
