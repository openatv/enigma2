from enigma import eConsoleAppContainer
from Tools.BoundFunction import boundFunction

# Struct to hold items
class ConsoleItem:
	def __init__(self, callback, extra_args):
		self.appResults = []
		self.extra_args = extra_args
		self.callback = callback
		self.container = eConsoleAppContainer()

class Console(object):
	def __init__(self):
		# Still called appContainers because Network.py accesses it to
		# know if there's still stuff running
		self.appContainers = {}
		self.counter = 0

	def ePopen(self, cmd, callback=None, extra_args=None):
		if not extra_args: extra_args = []
		name = cmd
		if self.appContainers.has_key(name):
			self.counter += 1
			name = cmd + '#' + str(self.counter)
		print "[Console] command:", cmd
		item = ConsoleItem(callback, extra_args)
		item.container.dataAvail.append(boundFunction(self.dataAvailCB, item))
		item.container.appClosed.append(boundFunction(self.finishedCB, name))
		self.appContainers[name] = item
		if isinstance(cmd, str): # until .execute supports a better api
			cmd = [cmd]
		retval = item.container.execute(*cmd)
		if retval:
			self.finishedCB(name, retval)

	def eBatch(self, cmds, callback, extra_args=None, debug=False):
		if not extra_args: extra_args = []
		self.debug = debug
		cmd = cmds.pop(0)
		self.ePopen(cmd, self.eBatchCB, [cmds, callback, extra_args])

	def eBatchCB(self, data, retval, _extra_args):
		(cmds, callback, extra_args) = _extra_args
		if self.debug:
			print '[eBatch] retval=%s, cmds left=%d, data:\n%s' % (retval, len(cmds), data)
		if cmds:
			cmd = cmds.pop(0)
			self.ePopen(cmd, self.eBatchCB, [cmds, callback, extra_args])
		else:
			callback(extra_args)

	def dataAvailCB(self, item, data):
		item.appResults.append(data)

	def finishedCB(self, name, retval):
		item = self.appContainers[name]
		del self.appContainers[name]
		del item.container.dataAvail[:]
		del item.container.appClosed[:]
		del item.container
		data = ''.join(item.appResults)
		extra_args = item.extra_args
		callback = item.callback
		del item
		if callback is not None:
			callback(data, retval, extra_args)

	def kill(self, name):
		if name in self.appContainers:
			print "[Console] killing: ", name
			self.appContainers[name].container.kill()

	def killAll(self):
		for name, item in self.appContainers.items():
			print "[Console] killing: ", name
			item.container.kill()
