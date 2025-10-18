from sys import maxsize

from enigma import eActionMap

from keyids import KEYIDS
from Components.config import config
from Tools.Directories import fileReadXML

MODULE_NAME = __name__.split(".")[-1]

keyBindings = {}
unmapDict = {}


def addKeyBinding(filename, key, context, mapTo, flags):
	keyBindings.setdefault((context, mapTo), []).append((key, filename, flags))


def queryKeyBinding(context, mapTo):  # Returns a list of (key, flags) for a specified "mapTo" action in a context.
	return [(x[0], x[2]) for x in keyBindings[(context, mapTo)]] if (context, mapTo) in keyBindings else []


def getKeyBindingKeys(filterFunction=lambda x: True):
	return filter(filterFunction, keyBindings)


def removeContext(context, actionMapInstance):  # Remove all entries for a context.
	removeActions = []
	for contxt, mapTo in keyBindings:
		if contxt == context:
			contextAction = (context, mapTo)
			removeActions.append(contextAction)
	for contextAction in removeActions:
		if contextAction in keyBindings:
			binding = keyBindings[contextAction]
			actionMapInstance.unbindPythonKey(context, binding[0][0], contextAction[1])
			del keyBindings[contextAction]


def removeKeyBinding(key, context, mapTo, wild=True):
	if wild and mapTo == "*":
		for contxt, mapTo in keyBindings.keys():
			if contxt == context:
				removeKeyBinding(key, context, mapTo, False)
	else:
		contextAction = (context, mapTo)
		if contextAction in keyBindings:
			bind = [x for x in keyBindings[contextAction] if x[0] != key]
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
	key = -1
	flagToValue = {
		"m": 1,
		"b": 2,
		"r": 4,
		"l": 8,
		"s": 32,
	}
	for element in domKeys.findall("key"):
		keyName = element.attrib.get("id")
		if keyName is None:
			print(f"[ActionMap] Error: Key map attribute 'id' in context '{context}' in file '{filename}' must be specified!")
			error = True
		else:
			try:
				if len(keyName) == 1:
					key = ord(keyName) | 0x8000
				elif keyName[0] == "\\":
					match keyName[1].lower():
						case "x":
							key = int(keyName[2:], 16) | 0x8000
						case "d":
							key = int(keyName[2:], 10) | 0x8000
						case "o":
							key = int(keyName[2:], 8) | 0x8000
						case "b":
							key = int(keyName[2:], 2) | 0x8000
						case _:
							print(f"[ActionMap] Error: Key map id '{keyName}' in context '{context}' in file '{filename}' is not a hex, decimal, octal or binary number!")
							error = True
				else:
					key = KEYIDS.get(keyName, -1)
					if key is None:
						print(f"[ActionMap] Error: Key map id '{keyName}' in context '{context}' in file '{filename}s' is undefined/invalid!")
						error = True
			except ValueError:
				print(f"[ActionMap] Error: Key map id '{keyName}' in context '{context}' in file '{filename}' can not be evaluated!")
				key = -1
				error = True
		mapTo = element.attrib.get("mapTo", element.attrib.get("mapto"))
		unmap = element.attrib.get("unmap")
		if mapTo is None and unmap is None:
			print(f"[ActionMap] Error: At least one of the attributes 'mapTo' or 'unmap' in context '{context}' id '{keyName}' ({key}) in file '{filename}' must be specified!")
			error = True
		flags = element.attrib.get("flags")
		if flags is None:
			print(f"[ActionMap] Error: Attribute 'flag' in context '{context}' id '{keyName}' ({key}) in file '{filename}' must be specified!")
			error = True
		else:
			newFlags = sum(flagToValue[x] for x in flags)
			if not newFlags:
				print(f"[ActionMap] Error: Attribute 'flag' value '{flags}' in context '{context}' id '{keyName}' ({key}) in file '{filename}' appears invalid!")
				error = True
			flags = newFlags
		if not error:
			if unmap is None:  # If a key was unmapped, it can only be assigned a new function in the same key map file (avoid file parsing sequence dependency).
				if unmapDict.get((context, keyName, mapTo)) in [filename, None]:
					if config.crash.debugActionMaps.value:
						print(f"[ActionMap] Context '{context}' keyName '{keyName}' ({key}) mapped to '{mapTo}' (Device: {device.capitalize()}).")
					actionMapInstance.bindKey(filename, device, key, flags, context, mapTo)
					addKeyBinding(filename, key, context, mapTo, flags)
			else:
				actionMapInstance.unbindPythonKey(context, key, unmap)
				unmapDict.update({(context, keyName, unmap): filename})


def loadKeymap(filename, replace=False):
	def getKeyCode(keyName):
		if len(keyName) == 1:
			keyCode = ord(keyName) | 0x8000
		elif keyName[0] == "\\":
			if keyName[1] == "x":
				keyCode = int(keyName[2:], 0x10) | 0x8000
			elif keyName[1] == "d":
				keyCode = int(keyName[2:]) | 0x8000
			else:
				print(f"[ActionMap] Key id '{keyName}' is neither hexadecimal nor decimal!")
		else:
			try:
				keyCode = KEYIDS[keyName]
			except KeyError:
				print(f"[ActionMap] Key id '{keyName}' is illegal!")
		return keyCode

	def parseTrans(filename, actionMap, device, keys):
		for toggle in keys.findall("toggle"):
			attributeGet = toggle.attrib.get
			actionMap.bindToggle(filename, device, getKeyCode(attributeGet("from")))
		for element in keys.findall("key"):
			attributeGet = element.attrib.get
			keyNameIn = attributeGet("from")
			keyNameOut = attributeGet("to")
			toggle = int(attributeGet("toggle") or "0")
			assert keyNameIn, f"[ActionMap] {filename}: Error: Must specify key to translate from '{keyNameIn}'!"
			assert keyNameOut, f"[ActionMap] {filename}: Error: Must specify key to translate to '{keyNameOut}'!"
			actionMap.bindTranslation(filename, device, getKeyCode(keyNameIn), getKeyCode(keyNameOut), toggle)

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
		self.disbledActions = []
		self.prio = prio
		self.parentScreen = parentScreen.__class__.__name__ if parentScreen else "N/A"  # and [x for x in parentScreen.__class__.__mro__ if x.__name__ == "Screen"] else "N/A"
		self.actionMapInstance = eActionMap.getInstance()
		self.execActive = False
		self.bound = False
		self.legacyBound = False
		self.enabled = True
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

	def execBegin(self):
		self.execActive = True
		self.checkBind()

	def execEnd(self):
		self.execActive = False
		self.checkBind()

	def destroy(self):
		pass

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

	def getEnabled(self):
		return self.enabled

	def setEnabled(self, enabled):
		self.enabled = enabled
		self.checkBind()

	def setEnabledAction(self, action, enabled):
		if action in self.actions:
			if enabled and action in self.disbledActions:
				self.disbledActions.remove(action)
			if not enabled and action not in self.disbledActions:
				self.disbledActions.append(action)

	def action(self, context, action):
		if action in self.actions and action not in self.disbledActions:
			if config.crash.debugActionMaps.value:
				print(f"[ActionMap] Map screen '{self.parentScreen}' context '{context}' -> Action '{action}'.")
			response = self.actions[action]()
			result = response if response is not None else 1
		else:
			result = 0
		# print(f"[ActionMap] Map screen '{self.parentScreen}' context '{context}' -> Unknown action '{action}'!  (Typo in map?)")
		return result

	def legacyAction(self, context, action):
		if action in self.legacyActions:
			if config.crash.debugActionMaps.value:
				print(f"[ActionMap] Map screen '{self.parentScreen}' context '{context}' -> Legacy action '{action}' ({self.legacyActions[action]}).")
			response = self.legacyActions[action]()
			result = response if response is not None else 1
		else:
			result = 0
		# print(f"[ActionMap] Map screen '{self.parentScreen}' context '{context}' -> Unknown legacy action '{action}'!  (Typo in map?)")
		return result

	def addAction(self, action, response):
		self.actions[action] = response

	def removeAction(self, action):
		if action in self.actions:
			del self.actions[action]


class NumberActionMap(ActionMap):
	def action(self, contexts, action):
		if action in ("0", "1", "2", "3", "4", "5", "6", "7", "8", "9") and action in self.actions:
			response = self.actions[action](int(action))
			if config.crash.debugActionMaps.value:
				print(f"[ActionMap] Map screen '{self.parentScreen}' context '{contexts}' -> function'{self.actions[action]}'.")
			result = response if response is not None else 1
		else:
			result = ActionMap.action(self, contexts, action)
		return result


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

	def addAction(self, parent, context, action, response):
		if not isinstance(response, (list, tuple)):
			response = (response, None)
		elif queryKeyBinding(context, action) and response[1]:
			for (actionMap, oldContext, actions) in parent.helpList:
				if oldContext == context and actionMap == self:
					actions.append((action, response[1]))
					break
		ActionMap.addAction(self, action, response[0])

	def removeAction(self, parent, context, action):
		for (actionMap, oldContext, actions) in parent.helpList:
			if oldContext == context and actionMap == self:
				actions[:] = [x for x in actions if x[0] != action]  # The list copy forces the change to not be local only.
		ActionMap.removeAction(self, action)


class HelpableNumberActionMap(NumberActionMap, HelpableActionMap):
	def __init__(self, parent, contexts, actions=None, prio=0, description=None):
		# Initialize NumberActionMap with empty context and actions
		# so that the underlying ActionMap is only initialized with
		# these once, via the HelpableActionMap.
		NumberActionMap.__init__(self, [], {})
		HelpableActionMap.__init__(self, parent, contexts, actions, prio, description)
