from os import waitpid

from enigma import eConsoleAppContainer
import six


class ConsoleItem:
	def __init__(self, containers, cmd, callback, extraArgs):
		self.containers = containers
		if isinstance(cmd, str):  # Until .execute supports a better api.
			cmd = [cmd]
		name = cmd[0]
		if name in self.containers:  # Create a unique name.
			name = "%s@%s" % (str(cmd), hex(id(self)))
		self.name = name
		self.callback = callback
		self.extraArgs = extraArgs
		self.container = eConsoleAppContainer()
		self.containers[name] = self
		# If the caller isn't interested in our results, we don't need to store the output either.
		if callback is not None:
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
		if callback is None:
			try:
				waitpid(self.container.getPID(), 0)
			except (IOError, OSError):
				pass

	def dataAvailCB(self, data):
		self.appResults.append(data)

	def finishedCB(self, retVal):
		print("[Console] Command '%s' finished." % self.name)
		del self.containers[self.name]
		del self.container.dataAvail[:]
		del self.container.appClosed[:]
		del self.container
		callback = self.callback
		if callback is not None:
			data = b"".join(self.appResults)
			callback(data, retVal, self.extraArgs)


class Console(object):
	def __init__(self):
		# Still called appContainers because Network.py, SoftwareTools.py
		# and WirelessLan/Wlan.py accesses it to know if there's still
		# stuff running.
		self.appContainers = {}
		self.appResults = {} # FIXME : Do ee need this

	def ePopen(self, cmd, callback=None, extra_args=None):
		if not extra_args:
			extra_args = []
		return ConsoleItem(self.appContainers, cmd, callback, extra_args)

	def eBatch(self, cmds, callback, extra_args=None, debug=False):
		if not extra_args:
			extra_args = []
		self.debug = debug
		cmd = cmds.pop(0)
		self.ePopen(cmd, self.eBatchCB, [cmds, callback, extra_args])

	def eBatchCB(self, data, retVal, extraArg):
		(cmds, callback, extraArgs) = extraArg
		if self.debug:
			data = six.ensure_str(data)
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
		for name, item in list(self.appContainers.items()):  # FIXME : Do ee need list
			print("[Console] Killing all commands '%s'." % name)
			item.container.kill()
