from __future__ import print_function
from enigma import eActionMap
from keyids import KEYIDS
from Components.config import config
from Tools.Directories import fileReadXML
import six

MODULE_NAME = __name__.split(".")[-1]

keyBindings = {}
unmapDict = {}



class KeymapError(Exception):
	def __init__(self, message):
		self.msg = message

	def __str__(self):
		return self.msg


def addKeyBinding(filename, keyId, context, mapto, flags):
	keyBindings.setdefault((context, mapto), []).append((keyId, filename, flags))


def queryKeyBinding(context, mapto):  # Returns a list of (keyId, flags) for a specified mapto action in a context.
	if (context, mapto) in keyBindings:
		return [(x[0], x[2]) for x in keyBindings[(context, mapto)]]
	return []


def getKeyBindingKeys(filterFunction=lambda key: True):
	return filter(filterFunction, keyBindings)


def removeKeyBinding(keyId, context, mapto, wild=True):
	if wild and mapto == "*":
		for context, mapto in keyBindings.keys():
			if context == context:
				removeKeyBinding(keyId, context, mapto, False)
		return
	contextAction = (context, mapto)
	if contextAction in keyBindings:
		bind = [x for x in keyBindings[contextAction] if x[0] != keyId]
		if bind:
			keyBindings[contextAction] = bind
		else:
			del keyBindings[contextAction]


def removeKeyBindings(filename):  # Remove all entries of filename "domain".
	for keyBinding in keyBindings:
		keyBindings[keyBinding] = filter(lambda x: x[1] != filename, keyBindings[keyBinding])

def getKeyId(id):
	if len(id) == 1:
		keyid = ord(id) | 0x8000
	elif id[0] == '\\':
		if id[1] == 'x':
			keyid = int(id[2:], 0x10) | 0x8000
		elif id[1] == 'd':
			keyid = int(id[2:]) | 0x8000
		else:
			raise KeymapError("[keymapparser] key id '" + str(id) + "' is neither hex nor dec")
	else:
		try:
			keyid = KEYIDS[id]
		except:
			raise KeymapError("[keymapparser] key id '" + str(id) + "' is illegal")
	return keyid


def parseTrans(filename, actionmap, device, keys):
	for x in keys.findall("toggle"):
		get_attr = x.attrib.get
		toggle_key = get_attr("from")
		toggle_key = getKeyId(toggle_key)
		actionmap.bindToggle(filename, device, toggle_key)

	for x in keys.findall("key"):
		get_attr = x.attrib.get
		keyin = get_attr("from")
		keyout = get_attr("to")
		toggle = get_attr("toggle") or "0"
		assert keyin, "[keymapparser] %s: must specify key to translate from '%s'" % (filename, keyin)
		assert keyout, "[keymapparser] %s: must specify key to translate to '%s'" % (filename, keyout)

		keyin = getKeyId(keyin)
		keyout = getKeyId(keyout)
		toggle = int(toggle)
		actionmap.bindTranslation(filename, device, keyin, keyout, toggle)


def parseKeymap(filename, context, actionmap, device, keys):
	for x in keys.findall("key"):
		get_attr = x.attrib.get
		mapto = get_attr("mapto")
		unmap = get_attr("unmap")
		id = get_attr("id")
		flags = get_attr("flags")

		if unmap is not None:
			assert id, "[keymapparser] %s: must specify id in context %s, unmap '%s'" % (filename, context, unmap)
			keyid = getKeyId(id)
			actionmap.unbindPythonKey(context, keyid, unmap)
			unmapDict.update({(context, id, unmap): filename})
		else:
			assert mapto, "[keymapparser] %s: must specify mapto (or unmap) in context %s, id '%s'" % (filename, context, id)
			assert id, "[keymapparser] %s: must specify id in context %s, mapto '%s'" % (filename, context, mapto)
			keyid = getKeyId(id)

			flag_ascii_to_id = lambda x: {'m': 1, 'b': 2, 'r': 4, 'l': 8}[x]

			flags = sum(map(flag_ascii_to_id, flags))

			assert flags, "[keymapparser] %s: must specify at least one flag in context %s, id '%s'" % (filename, context, id)

			# if a key was unmapped, it can only be assigned a new function in the same keymap file (avoid file parsing sequence dependency)
			if unmapDict.get((context, id, mapto)) in [filename, None]:
#				print "[keymapparser] " + context + "::" + mapto + " -> " + device + "." + hex(keyid)
				actionmap.bindKey(filename, device, keyid, flags, context, mapto)
				addKeyBinding(filename, keyid, context, mapto, flags)


def loadKeymap(filename):
	actionMapInstance = eActionMap.getInstance()
	domKeymap = fileReadXML(filename, source=MODULE_NAME)
	if domKeymap:
		for domMap in domKeymap.findall("map"):
			context = domMap.attrib.get("context")
			if context is None:
				print("ActionMap] Error: All keymap action maps in '%s' must have a context!" % filename)
			else:
				parseKeymap(filename, context, actionMapInstance, "generic", domMap)
				for domDevice in domMap.findall("device"):
					parseKeymap(filename, context, actionMapInstance, domDevice.attrib.get("name"), domDevice)

		for domMap in domKeymap.findall("translate"):
			for domDevice in domMap.findall("device"):
				parseTrans(filename, actionMapInstance, domDevice.attrib.get("name"), domDevice)


def removeKeymap(filename):
	actionMapInstance = eActionMap.getInstance()
	actionMapInstance.unbindKeyDomain(filename)


class ActionMap:
	def __init__(self, contexts=None, actions=None, prio=0):
		self.contexts = contexts or []
		self.actions = actions or {}
		self.prio = prio
		self.actionMapInstance = eActionMap.getInstance()
		self.bound = False
		self.execActive = False
		self.enabled = True
		undefinedAction = list(self.actions.keys())
		for action in undefinedAction:
			for context in self.contexts:
				if queryKeyBinding(context, action):
					undefinedAction.remove(action)
					break
		if undefinedAction:
			print("[ActionMap] Keymap(s) '%s' -> Undefined action(s) '%s'." % (", ".join(contexts), ", ".join(unknown)))

	def setEnabled(self, enabled):
		self.enabled = enabled
		self.checkBind()

	def doBind(self):
		if not self.bound:
			for context in self.contexts:
				self.actionMapInstance.bindAction(context, self.prio, self.action)
			self.bound = True

	def doUnbind(self):
		if self.bound:
			for context in self.contexts:
				self.actionMapInstance.unbindAction(context, self.action)
			self.bound = False

	def checkBind(self):
		if self.execActive and self.enabled:
			self.doBind()
		else:
			self.doUnbind()

	def execBegin(self):
		self.execActive = True
		self.checkBind()

	def execEnd(self):
		self.execActive = False
		self.checkBind()

	def action(self, context, action):
		if action in self.actions:
			print("[ActionMap] Keymap '%s' -> Action '%s'." % (context, action))
			response = self.actions[action]()
			if response is not None:
				return response
			return 1
		print("[ActionMap] Keymap '%s' -> Unknown action '%s'! (Typo in keymap?)" % (context, action))
		return 0

	def destroy(self):
		pass


class NumberActionMap(ActionMap):
	def action(self, contexts, action):
		if action in ("0", "1", "2", "3", "4", "5", "6", "7", "8", "9") and action in self.actions:
			response = self.actions[action](int(action))
			if response is not None:
				return response
			return 1
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
	#
	def __init__(self, parent, contexts, actions=None, prio=0, description=None):
		def exists(record):
			for context in parent.helpList:
				if record in context[2]:
					print("[HelpActionMap] removed duplicity: %s %s" % (context[1], record))
					return True
			return False
		if not type(contexts) is list:
			contexts = [contexts]
		actions = actions or {}
		self.description = description
		actionDict = {}
		for context in contexts:
			actionList = []
			for (action, response) in six.iteritems(actions):
				# Check if this is a tuple.
				if isinstance(response, tuple):
					if queryKeyBinding(context, action):
						if not exists((action, response[1])):
							actionList.append((action, response[1]))
					actionDict[action] = response[0]
				else:
					if queryKeyBinding(context, action):
						if not exists((action, None)):
							actionList.append((action, None))
					actionDict[action] = response
			parent.helpList.append((self, context, actionList))
		ActionMap.__init__(self, contexts, actionDict, prio)


class HelpableNumberActionMap(NumberActionMap, HelpableActionMap):
	def __init__(self, parent, contexts, actions=None, prio=0, description=None):
		# Initialise NumberActionMap with empty context and actions
		# so that the underlying ActionMap is only initialised with
		# these once, via the HelpableActionMap.
		#
		NumberActionMap.__init__(self, [], {})
		HelpableActionMap.__init__(self, parent, contexts, actions, prio, description)
