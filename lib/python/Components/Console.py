from enigma import eConsoleAppContainer
from Tools.BoundFunction import boundFunction

class Console(object):
	def __init__(self):
		self.appContainers = {}
		self.appResults = {}
		self.callbacks = {}
		self.extra_args = {}

	def ePopen(self, cmd, callback, extra_args=[]):
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
		self.appContainers[name].dataAvail.get().append(boundFunction(self.dataAvailCB,name))
		self.appContainers[name].appClosed.get().append(boundFunction(self.finishedCB,name))
		retval = self.appContainers[name].execute(cmd)
		if retval:
			self.finishedCB(name, retval)

	def dataAvailCB(self, name, data):
		self.appResults[name] += data

	def finishedCB(self, name, retval):
		del self.appContainers[name].dataAvail.get()[:]
		del self.appContainers[name].appClosed.get()[:]
		data = self.appResults[name]
		extra_args = self.extra_args[name]
		del self.appContainers[name]
		del self.extra_args[name]
		self.callbacks[name](data,retval,extra_args)
		del self.callbacks[name]
