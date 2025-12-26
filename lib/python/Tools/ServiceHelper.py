from socket import socket, AF_UNIX, SOCK_STREAM
from twisted.internet.reactor import callInThread

from enigma import eTimer


class ServiceHelper:
	def __init__(self, serviceName):
		self.serviceName = serviceName
		self.callbackTimer = eTimer()
		self.deamonSocket = None
		self.callback = None

	def _action(self, action):
		self.deamonSocket = socket(AF_UNIX, SOCK_STREAM)
		self.deamonSocket.connect("/tmp/deamon.socket")
		self.deamonSocket.send(f"{action},{self.serviceName}".encode())
		self._waitSocket()

	def restart(self, callback, timeout=5000):
		self.callback = callback
		self.timeout = timeout
		self._action("RESTART")

	def start(self, callback, timeout=5000):
		self.callback = callback
		self.timeout = timeout
		self._action("START")

	def stop(self, callback, timeout=5000):
		self.callback = callback
		self.timeout = timeout
		self._action("STOP")

	def _waitSocket(self):
		self.callbackTimer.timeout.get().append(self._closeSocket)
		self.callbackTimer.start(self.timeout, True)
		callInThread(self._listenSocket)

	def _listenSocket(self):
		data = None
		while not data:
			data = self.deamonSocket.recv(256)
		self._closeSocket()

	def _closeSocket(self):
		self.callbackTimer.stop()
		if self.deamonSocket:
			self.deamonSocket.close()
			self.deamonSocket = None
			if self.callback:
				self.callback()
