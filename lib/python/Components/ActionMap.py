from sys import maxsize

from enigma import eActionMap

from keyids import KEYIDS
from Components.config import config
from Tools.Directories import fileReadXML

MODULE_NAME = __name__.split(".")[-1]

keyBindings = {}
unmapDict = {}


def addKeyBinding(filename, keyId, context, mapto, flags):
	keyBindings.setdefault((context, mapto), []).append((keyId, filename, flags))


def queryKeyBinding(context, mapto):  # Returns a list of (keyId, flags) for a specified "mapto" action in a context.
	return [(x[0], x[2]) for x in keyBindings[(context, mapto)]] if (context, mapto) in keyBindings else []


def getKeyBindingKeys(filterFunction=lambda key: True):
	return filter(filterFunction, keyBindings)


def removeContext(context, actionMapInstance):  # Remove all entries for a context.
	removeActions = []
	for contxt, mapto in keyBindings:
		if contxt == context:
			contextAction = (context, mapto)
			removeActions.append(contextAction)
	for contextAction in removeActions:
		if contextAction in keyBindings:
			binding = keyBindings[contextAction]
			actionMapInstance.unbindPythonKey(context, binding[0][0], contextAction[1])
			del keyBindings[contextAction]


def removeKeyBinding(keyId, context, mapto, wild=True):
	if wild and mapto == "*":
		for contxt, mapto in keyBindings.keys():
			if contxt == context:
				removeKeyBinding(keyId, context, mapto, False)
	else:
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


def parseKeymap(filename, context, actionMapInstance, device, domKeys):
	unmapDict = {}
	error = False
	keyId = -1
	flagToValue = {
		"m": 1,
		"b": 2,
		"r": 4,
		"l": 8,
		"s": 32,
	}
	for key in domKeys.findall("key"):
		keyName = key.attrib.get("id")
		if keyName is None:
			print(f"[ActionMap] Error: Key map attribute 'id' in context '{context}' in file '{filename}' must be specified!")
			error = True
		else:
			try:
				if len(keyName) == 1:
					keyId = ord(keyName) | 0x8000
				elif keyName[0] == "\\":
					if keyName[1].lower() == "x":
						keyId = int(keyName[2:], 16) | 0x8000
					elif keyName[1].lower() == "d":
						keyId = int(keyName[2:], 10) | 0x8000
					elif keyName[1].lower() == "o":
						keyId = int(keyName[2:], 8) | 0x8000
					elif keyName[1].lower() == "b":
						keyId = int(keyName[2:], 2) | 0x8000
					else:
						print(f"[ActionMap] Error: Key map id '{keyName}' in context '{context}' in file '{filename}' is not a hex, decimal, octal or binary number!")
						error = True
				else:
					keyId = KEYIDS.get(keyName, -1)
					if keyId is None:
						print(f"[ActionMap] Error: Key map id '{keyName}' in context '{context}' in file '{filename}s' is undefined/invalid!")
						error = True
			except ValueError:
				print(f"[ActionMap] Error: Key map id '{keyName}' in context '{context}' in file '{filename}' can not be evaluated!")
				keyId = -1
				error = True
		mapto = key.attrib.get("mapto")
		unmap = key.attrib.get("unmap")
		if mapto is None and unmap is None:
			print(f"[ActionMap] Error: At least one of the attributes 'mapto' or 'unmap' in context '{context}' id '{keyName}' ({keyId}) in file '{filename}' must be specified!")
			error = True
		flags = key.attrib.get("flags")
		if flags is None:
			print(f"[ActionMap] Error: Attribute 'flag' in context '{context}' id '{keyName}' ({keyId}) in file '{filename}' must be specified!")
			error = True
		else:
			newFlags = sum(flagToValue[x] for x in flags)
			if not newFlags:
				print(f"[ActionMap] Error: Attribute 'flag' value '{flags}' in context '{context}' id '{keyName}' ({keyId}) in file '{filename}' appears invalid!")
				error = True
			flags = newFlags
		if not error:
			if unmap is None:  # If a key was unmapped, it can only be assigned a new function in the same key map file (avoid file parsing sequence dependency).
				if unmapDict.get((context, keyName, mapto)) in [filename, None]:
					if config.crash.debugActionMaps.value:
						print(f"[ActionMap] Context '{context}' keyName '{keyName}' ({keyId}) mapped to '{mapto}' (Device: {device.capitalize()}).")
					actionMapInstance.bindKey(filename, device, keyId, flags, context, mapto)
					addKeyBinding(filename, keyId, context, mapto, flags)
			else:
				actionMapInstance.unbindPythonKey(context, keyId, unmap)
				unmapDict.update({(context, keyName, unmap): filename})


def getKeyId(id):
	if len(id) == 1:
		keyid = ord(id) | 0x8000
	elif id[0] == "\\":
		if id[1] == "x":
			keyid = int(id[2:], 0x10) | 0x8000
		elif id[1] == "d":
			keyid = int(id[2:]) | 0x8000
		else:
			print(f"[ActionMap] Key id '{id}' is neither hexadecimal nor decimal!")
	else:
		try:
			keyid = KEYIDS[id]
		except KeyError:
			print(f"[ActionMap] Key id '{id}' is illegal!")
	return keyid


def loadKeymap(filename, replace=False):
	def parseTrans(filename, actionmap, device, keys):
		for toggle in keys.findall("toggle"):
			get_attr = toggle.attrib.get
			toggle_key = get_attr("from")
			toggle_key = getKeyId(toggle_key)
			actionmap.bindToggle(filename, device, toggle_key)
		for key in keys.findall("key"):
			get_attr = key.attrib.get
			keyin = get_attr("from")
			keyout = get_attr("to")
			toggle = get_attr("toggle") or "0"
			assert keyin, f"[ActionMap] {filename}: Error: Must specify key to translate from '{keyin}'!"
			assert keyout, f"[ActionMap] {filename}: Error: Must specify key to translate to '{keyout}'!"
			keyin = getKeyId(keyin)
			keyout = getKeyId(keyout)
			toggle = int(toggle)
			actionmap.bindTranslation(filename, device, keyin, keyout, toggle)

	actionMapInstance = eActionMap.getInstance()
	domKeymap = fileReadXML(filename, source=MODULE_NAME)
	if domKeymap is not None:
		replace = replace or (domKeymap.get("load", "") == "replace")
		print(f"[ActionMap] LoadKeymap '{filename}' with replace {replace}.")
		for domMap in domKeymap.findall("map"):
			context = domMap.attrib.get("context")
			if context is None:
				print(f"ActionMap] Error: All key map action maps in '{filename}' must have a context!")
			else:
				if replace and keyBindings:  # Remove all entries for an existing context.
					removeContext(context, actionMapInstance)
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
	def __init__(self, contexts=None, actions=None, prio=0, parentScreen=None):
		self.contexts = contexts or []
		self.actions = actions or {}
		self.prio = prio
		self.actionMapInstance = eActionMap.getInstance()
		self.bound = False
		self.execActive = False
		self.enabled = True
		self.legacyBound = False
		self.parentScreen = parentScreen.__class__.__name__ if parentScreen else "N/A"  # and [x for x in parentScreen.__class__.__mro__ if x.__name__ == "Screen"] else "N/A"
		undefinedAction = list(self.actions.keys())
		leftActionDefined = "left" in undefinedAction
		rightActionDefined = "right" in undefinedAction
		leftAction = None
		rightAction = None
		for action in undefinedAction[:]:
			for context in self.contexts:
				if context == "NavigationActions":
					if action == "pageUp" and not leftActionDefined:
						leftAction = self.actions[action]
					if action == "pageDown" and not rightActionDefined:
						rightAction = self.actions[action]
				if queryKeyBinding(context, action):
					undefinedAction.remove(action)
					break
		if leftAction and rightAction and config.misc.actionLeftRightToPageUpPageDown.value:
			if config.crash.debugActionMaps.value:
				print(f"[ActionMap] DEBUG: Creating legacy LEFT/RIGHT navigation action map entries. Left: '{leftAction}' / Right: '{rightAction}'.")
			self.legacyActions = {
				"left": leftAction,
				"right": rightAction
			}
		else:
			self.legacyActions = {}
		if undefinedAction:
			print(f"[ActionMap] Map context{"s" if len(self.contexts) > 1 else ""} '{", ".join(sorted(self.contexts))}': Undefined action{"s" if len(undefinedAction) > 1 else ""} '{", ".join(sorted(undefinedAction))}'!")

	def getEnabled(self):
		return self.enabled

	def setEnabled(self, enabled):
		self.enabled = enabled
		self.checkBind()

	def doBind(self):
		if not self.legacyBound and self.legacyActions:
			self.actionMapInstance.bindAction("NavigationActions", maxsize - 1, self.legacyAction)
			self.legacyBound = True
		if not self.bound:
			for context in self.contexts:
				self.actionMapInstance.bindAction(context, self.prio, self.action)
			self.bound = True

	def doUnbind(self):
		if self.legacyBound and self.legacyActions:
			self.actionMapInstance.unbindAction("NavigationActions", self.legacyAction)
			self.legacyBound = False
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
			if config.crash.debugActionMaps.value:
				print(f"[ActionMap] Map screen '{self.parentScreen}' context '{context}' -> Action '{action}'.")
			response = self.actions[action]()
			return response if response is not None else 1
		print(f"[ActionMap] Map screen '{self.parentScreen}' context '{context}' -> Unknown action '{action}'!  (Typo in map?)")
		return 0

	def legacyAction(self, context, action):
		if action in self.legacyActions:
			if config.crash.debugActionMaps.value:
				print(f"[ActionMap] Map screen '{self.parentScreen}' context '{context}' -> Legacy action '{action}'.")
				print(self.legacyActions[action])
			response = self.legacyActions[action]()
			return response if response is not None else 1
		print(f"[ActionMap] Map screen '{self.parentScreen}' context '{context}' -> Unknown legacy action '{action}'!  (Typo in map?)")
		return 0

	def destroy(self):
		pass


class NumberActionMap(ActionMap):
	def action(self, contexts, action):
		if action in ("0", "1", "2", "3", "4", "5", "6", "7", "8", "9") and action in self.actions:
			response = self.actions[action](int(action))
			if config.crash.debugActionMaps.value:
				print(f"[ActionMap] Map screen '{self.parentScreen}' context '{contexts}' -> function'{self.actions[action]}'.")
			return response if response is not None else 1
		return ActionMap.action(self, contexts, action)


# An ActionMap which automatically puts the actions into the helpList.
#
# A context list is allowed, and for backward compatibility, a single
# string context name also is allowed.
#
# Sorry for this complicated code.  It's not more than converting a
# "documented" ActionMap (where the values are possibly (function,
# help)-tuples) into a "classic" ActionMap, where values are just
# functions.  The classic ActionMap is then passed to the
# ActionMapconstructor,	the collected help strings (with correct
# context, action) is added to the screen's "helpList", which will
# be picked up by the "Screen".
#
class HelpableActionMap(ActionMap):
	def __init__(self, parent, contexts, actions=None, prio=0, description=None):
		if isinstance(contexts, str):
			contexts = [contexts]
		actions = actions or {}
		self.description = description
		actionDict = {}
		for context in contexts:
			actionList = []
			for (action, response) in actions.items():
				if not isinstance(response, (list, tuple)):
					response = (response, None)
				if queryKeyBinding(context, action):
					actionList.append((action, response[1]))
				actionDict[action] = response[0]
			parent.helpList.append((self, context, actionList))
		ActionMap.__init__(self, contexts, actionDict, prio, parentScreen=parent)


class HelpableNumberActionMap(NumberActionMap, HelpableActionMap):
	def __init__(self, parent, contexts, actions=None, prio=0, description=None):
		# Initialize NumberActionMap with empty context and actions
		# so that the underlying ActionMap is only initialized with
		# these once, via the HelpableActionMap.
		NumberActionMap.__init__(self, [], {})
		HelpableActionMap.__init__(self, parent, contexts, actions, prio, description)
