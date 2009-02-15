from enigma import eConsoleAppContainer
from Tools.BoundFunction import boundFunction

class Console(object):
	def __init__(self):
		self.appContainers = {}
		self.appResults = {}
		self.callbacks = {}
		self.extra_args = {}

	def ePopen(self, cmd, callback=None, extra_args=[]):
		name = cmd
		i = 0
		while self.appContainers.has_key(name):
			name = cmd +'_'+ str(i)
			i += 1
		print "[ePopen] command:", cmd
		self.appResults[name] = ""
		self.extra_args[name] = extra_args
		self.callbacks[name] = callback
		self.appContainers[name] = eConsoleAppContainer()
		self.appContainers[name].dataAvail.append(boundFunction(self.dataAvailCB,name))
		self.appContainers[name].appClosed.append(boundFunction(self.finishedCB,name))
		if isinstance(cmd, str): # until .execute supports a better api
			cmd = [cmd]
		retval = self.appContainers[name].execute(*cmd)
		if retval:
			self.finishedCB(name, retval)

	def eBatch(self, cmds, callback, extra_args=[], debug=False):
		self.debug = debug
		cmd = cmds.pop(0)
		self.ePopen(cmd, self.eBatchCB, [cmds, callback, extra_args])

	def eBatchCB(self, data, retval, _extra_args):
		(cmds, callback, extra_args) = _extra_args
		if self.debug:
			print '[eBatch] retval=%s, cmds left=%d, data:\n%s' % (retval, len(cmds), data)
		if len(cmds):
			cmd = cmds.pop(0)
			self.ePopen(cmd, self.eBatchCB, [cmds, callback, extra_args])
		else:
			callback(extra_args)

	def dataAvailCB(self, name, data):
		self.appResults[name] += data

	def finishedCB(self, name, retval):
		del self.appContainers[name].dataAvail[:]
		del self.appContainers[name].appClosed[:]
		data = self.appResults[name]
		extra_args = self.extra_args[name]
		del self.appContainers[name]
		del self.extra_args[name]
		if self.callbacks[name]:
			self.callbacks[name](data,retval,extra_args)
		del self.callbacks[name]

	def kill(self,name):
		if name in self.appContainers:
			print "[Console] killing: ",self.appContainers[name]
			self.appContainers[name].kill()

	def killAll(self):
		for name in self.appContainers:
			self.kill(name)
