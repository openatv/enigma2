from os import waitpid

from enigma import eConsoleAppContainer


class ConsoleItem:
	def __init__(self, containers, cmd, callback, extraArgs, binary=False):
		self.containers = containers
		if isinstance(cmd, str):  # Until .execute supports a better API.
			cmd = [cmd]
		name = cmd[0]
		if name in self.containers:  # Create a unique name.
			name = "%s@%s" % (str(cmd), hex(id(self)))
		self.name = name
		self.callback = callback
		self.extraArgs = extraArgs if extraArgs else []
		self.container = eConsoleAppContainer()
		self.binary = binary
		self.containers[name] = self
		# If the caller isn't interested in our results, we don't need to store the output either.
		if callback:
			self.appResults = []
			self.container.dataAvail.append(self.dataAvailCB)
		self.container.appClosed.append(self.finishedCB)
		if len(cmd) > 1:
			print("[Console] Processing command '%s' with arguments %s." % (cmd[0], str(cmd[1:])))
		else:
			print("[Console] Processing command line '%s'." % cmd[0])
		retVal = self.container.execute(*cmd)
		if retVal:
			self.finishedCB(retVal)
		if not callback:
			pid = self.container.getPID()
			try:
				# print("[Console] Waiting for command (PID %d) to finish." % pid)
				waitpid(pid, 0)
				# print("[Console] Command on PID %d finished." % pid)
			except OSError as err:
				print("[Console] Error %s: Wait for command on PID %d to terminate failed!  (%s)" % (err.errno, pid, err.strerror))

	def dataAvailCB(self, data):
		self.appResults.append(data)

	def finishedCB(self, retVal):
		print("[Console] Command '%s' finished." % self.name)
		del self.containers[self.name]
		del self.container.dataAvail[:]
		del self.container.appClosed[:]
		del self.container
		callback = self.callback
		if callback and callable(callback):
			data = b"".join(self.appResults)
			data = data if self.binary else data.decode()
			callback(data, retVal, self.extraArgs)


class Console:
	"""
		Console by default will work with strings on callback.
		If binary data required class shoud be initialized with Console(binary=True)
	"""

	def __init__(self, binary=False):
		# Still called appContainers because Network.py
		# and WirelessLan/Wlan.py accesses it to know if there's still
		# stuff running.
		self.appContainers = {}
		self.appResults = {}
		self.binary = binary

	def ePopen(self, cmd, callback=None, extra_args=None):
		return ConsoleItem(self.appContainers, cmd, callback, extra_args, self.binary)

	def eBatch(self, cmds, callback, extra_args=None, debug=False):
		self.debug = debug
		cmd = cmds.pop(0)
		self.ePopen(cmd, self.eBatchCB, [cmds, callback, extra_args])

	def eBatchCB(self, data, retVal, extraArg):
		(cmds, callback, extraArgs) = extraArg
		if self.debug:
			if isinstance(data, bytes):
				data = data.decode("UTF-8", "ignore")
			print("[Console] eBatch DEBUG: retVal=%s, cmds left=%d, data:\n%s" % (retVal, len(cmds), data))
		if cmds:
			cmd = cmds.pop(0)
			self.ePopen(cmd, self.eBatchCB, [cmds, callback, extraArgs])
		else:
			callback(extraArgs)

	def kill(self, name):
		if name in self.appContainers:
			print("[Console] Killing command '%s'." % name)
			self.appContainers[name].container.kill()

	def killAll(self):
		for name, item in self.appContainers.items():
			print("[Console] Killing all commands '%s'." % name)
			item.container.kill()
