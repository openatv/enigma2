from enigma import eActionMap

from Tools.KeyBindings import queryKeyBinding


class ActionMap:
	def __init__(self, contexts=None, actions=None, prio=0):
		self.contexts = contexts or []
		self.actions = actions or {}
		self.prio = prio
		self.p = eActionMap.getInstance()
		self.bound = False
		self.exec_active = False
		self.enabled = True
		unknown = self.actions.keys()
		for action in unknown[:]:
			for context in self.contexts:
				if queryKeyBinding(context, action):
					unknown.remove(action)
					break
		if unknown:
			print "[ActionMap] Keymap(s) '%s' -> Undefined action(s) '%s'." % (", ".join(contexts), ", ".join(unknown))

	def setEnabled(self, enabled):
		self.enabled = enabled
		self.checkBind()

	def doBind(self):
		if not self.bound:
			for context in self.contexts:
				self.p.bindAction(context, self.prio, self.action)
			self.bound = True

	def doUnbind(self):
		if self.bound:
			for context in self.contexts:
				self.p.unbindAction(context, self.action)
			self.bound = False

	def checkBind(self):
		if self.exec_active and self.enabled:
			self.doBind()
		else:
			self.doUnbind()

	def execBegin(self):
		self.exec_active = True
		self.checkBind()

	def execEnd(self):
		self.exec_active = False
		self.checkBind()

	def action(self, context, action):
		if action in self.actions:
			print "[ActionMap] Keymap '%s' -> Action = '%s'." % (context, action)
			res = self.actions[action]()
			if res is not None:
				return res
			return 1
		else:
			print "[ActionMap] Keymap '%s' -> Unknown action '%s'! (Typo in keymap?)" % (context, action)
			return 0

	def destroy(self):
		pass


class NumberActionMap(ActionMap):
	def action(self, contexts, action):
		if action in ("0", "1", "2", "3", "4", "5", "6", "7", "8", "9") and action in self.actions:
			res = self.actions[action](int(action))
			if res is not None:
				return res
			return 1
		else:
			return ActionMap.action(self, contexts, action)


class HelpableActionMap(ActionMap):
	# An Actionmap which automatically puts the actions into the helpList.
	#
	# A context list is allowed, and for backward compatibility, a single
	# string context name also is allowed.
	#
	# Sorry for this complicated code.  It's not more than converting a
	# "documented" actionmap (where the values are possibly (function,
	# help)-tuples) into a "classic" actionmap, where values are just
	# functions.  The classic actionmap is then passed to the
	# ActionMapconstructor,	the collected helpstrings (with correct
	# context, action) is added to the screen's "helpList", which will
	# be picked up by the "HelpableScreen".
	def __init__(self, parent, contexts, actions=None, prio=0, description=None):
		if not hasattr(contexts, '__iter__'):
			contexts = [contexts]
		actions = actions or {}
		self.description = description
		adict = {}
		for context in contexts:
			alist = []
			for (action, funchelp) in actions.iteritems():
				# Check if this is a tuple.
				if isinstance(funchelp, tuple):
					if queryKeyBinding(context, action):
						alist.append((action, funchelp[1]))
					adict[action] = funchelp[0]
				else:
					if queryKeyBinding(context, action):
						alist.append((action, None))
					adict[action] = funchelp
			parent.helpList.append((self, context, alist))
		ActionMap.__init__(self, contexts, adict, prio)


class HelpableNumberActionMap(NumberActionMap, HelpableActionMap):
	def __init__(self, parent, contexts, actions=None, prio=0, description=None):
		# Initialise NumberActionMap with empty context and actions
		# so that the underlying ActionMap is only initialised with
		# these once, via the HelpableActionMap.
		NumberActionMap.__init__(self, [], {})
		HelpableActionMap.__init__(self, parent, contexts, actions, prio, description)
