from enigma import *

class ActionMap:
	def __init__(self, contexts = [ ], actions = { }, prio=0):
		self.actions = actions
		self.contexts = contexts
		self.prio = prio
		self.p = eActionMapPtr()
		eActionMap.getInstance(self.p)

	def execBegin(self):
		for ctx in self.contexts:
			self.p.bindAction(ctx, self.prio, self.action)

	def execEnd(self):
		for ctx in self.contexts:
			self.p.unbindAction(ctx, self.action)

	def action(self, context, action):
		print " ".join(("action -> ", context, action))
		if self.actions.has_key(action):
			self.actions[action]()
			return 1
		else:
			print "unknown action %s/%s! typo in keymap?" % (context, action)
			return 0

class NumberActionMap(ActionMap):
	def action(self, contexts, action):
		numbers = ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"]
		if (action in numbers and self.actions.has_key(action)):
			self.actions[action](int(action))
			return 1
		else:
			return ActionMap.action(self, contexts, action)
