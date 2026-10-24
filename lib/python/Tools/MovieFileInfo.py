from json import loads
from os.path import isabs, isfile

from enigma import eConsoleAppContainer, eTimer


class MovieFileInfo:
	MAX_OUTPUT = 256 * 1024
	PROBE = "/usr/bin/ffprobe"

	def __init__(self, callback):
		self.callback = callback
		self.output = bytearray()
		self.container = eConsoleAppContainer()
		self.container.dataAvail.append(self.dataReceived)
		self.container.appClosed.append(self.finished)
		self.timer = eTimer()
		self.timer.callback.append(self.timedOut)
		self.running = False

	def start(self, path):
		if not isabs(path) or not isfile(self.PROBE):
			self.finished(1)
			return
		# Inspect only the selected local file, with bounded probing and no shell.
		self.running = True
		self.timer.start(8000, True)
		result = self.container.execute(self.PROBE, self.PROBE, "-v", "quiet", "-protocol_whitelist", "file", "-analyzeduration", "3000000", "-probesize", "5000000", "-print_format", "json", "-show_format", "-show_streams", "-i", path)
		if result:
			self.finished(result)

	def dataReceived(self, data):
		if len(self.output) + len(data) > self.MAX_OUTPUT:
			self.deliver({"error": "tooLarge"})
			self.container.kill()
		else:
			self.output.extend(data)

	def timedOut(self):
		self.deliver({"error": "timeout"})
		if self.running:
			self.container.kill()

	def finished(self, result):
		self.running = False
		self.timer.stop()
		self.container.dataAvail.remove(self.dataReceived)
		self.container.appClosed.remove(self.finished)
		information = {"error": "unavailable"}
		if result == 0:
			try:
				data = loads(self.output)
				if isinstance(data, dict):
					information = {"format": data.get("format", {}), "streams": data.get("streams", [])}
			except (ValueError, UnicodeError):
				pass
		self.output.clear()
		self.deliver(information)

	def deliver(self, information):
		callback, self.callback = self.callback, None
		if callback is not None:
			callback(information)

	def close(self):
		self.callback = None
		self.timer.stop()
		if self.running:
			self.container.kill()
