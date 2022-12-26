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
	if (context, mapto) in keyBindings:
		return [(x[0], x[2]) for x in keyBindings[(context, mapto)]]
	return []


def getKeyBindingKeys(filterFunction=lambda key: True):
	return filter(filterFunction, keyBindings)


def removeKeyBinding(keyId, context, mapto, wild=True):
	if wild and mapto == "*":
		for contxt, mapto in keyBindings.keys():
			if contxt == context:
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


def parseKeymap(filename, context, actionMapInstance, device, domKeys):
	unmapDict = {}
	error = False
	keyId = -1
	for key in domKeys.findall("key"):
		keyName = key.attrib.get("id")
		if keyName is None:
			print("[ActionMap] Error: Key map attribute 'id' in context '%s' in file '%s' must be specified!" % (context, filename))
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
						print("[ActionMap] Error: Key map id '%s' in context '%s' in file '%s' is not a hex, decimal, octal or binary number!" % (keyName, context, filename))
						error = True
				else:
					keyId = KEYIDS.get(keyName, -1)
					if keyId is None:
						print("[ActionMap] Error: Key map id '%s' in context '%s' in file '%s' is undefined/invalid!" % (keyName, context, filename))
						error = True
			except ValueError:
				print("[ActionMap] Error: Key map id '%s' in context '%s' in file '%s' can not be evaluated!" % (keyName, context, filename))
				keyId = -1
				error = True
		mapto = key.attrib.get("mapto")
		unmap = key.attrib.get("unmap")
		if mapto is None and unmap is None:
			print("[ActionMap] Error: At least one of the attributes 'mapto' or 'unmap' in context '%s' id '%s' (%d) in file '%s' must be specified!" % (context, keyName, keyId, filename))
			error = True
		flags = key.attrib.get("flags")
		if flags is None:
			print("[ActionMap] Error: Attribute 'flag' in context '%s' id '%s' (%d) in file '%s' must be specified!" % (context, keyName, keyId, filename))
			error = True
		else:
			flagToValue = lambda x: {
				"m": 1,
				"b": 2,
				"r": 4,
				"l": 8
			}[x]
			newFlags = sum(map(flagToValue, flags))
			if not newFlags:
				print("[ActionMap] Error: Attribute 'flag' value '%s' in context '%s' id '%s' (%d) in file '%s' appears invalid!" % (flags, context, keyName, keyId, filename))
				error = True
			flags = newFlags
		if not error:
			if unmap is None:  # If a key was unmapped, it can only be assigned a new function in the same key map file (avoid file parsing sequence dependency).
				if unmapDict.get((context, keyName, mapto)) in [filename, None]:
					if config.crash.debugActionMaps.value:
						print("[ActionMap] Context '%s' keyName '%s' (%d) mapped to '%s' (Device: %s)." % (context, keyName, keyId, mapto, device.capitalize()))
					actionMapInstance.bindKey(filename, device, keyId, flags, context, mapto)
					addKeyBinding(filename, keyId, context, mapto, flags)
			else:
				actionMapInstance.unbindPythonKey(context, keyId, unmap)
				unmapDict.update({(context, keyName, unmap): filename})


def getKeyId(id):  # FIME Remove keytranslation.xml.
	if len(id) == 1:
		keyid = ord(id) | 0x8000
	elif id[0] == "\\":
		if id[1] == "x":
			keyid = int(id[2:], 0x10) | 0x8000
		elif id[1] == "d":
			keyid = int(id[2:]) | 0x8000
		else:
			print("[ActionMap] Key id '%s' is neither hexadecimal nor decimal!" % id)
	else:
		try:
			keyid = KEYIDS[id]
		except KeyError:
			print("[ActionMap] Key id '%s' is illegal!" % id)
	return keyid


def parseTrans(filename, actionmap, device, keys):  # FIME Remove keytranslation.xml.
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
		assert keyin, "[ActionMap] %s: must specify key to translate from '%s'" % (filename, keyin)
		assert keyout, "[ActionMap] %s: must specify key to translate to '%s'" % (filename, keyout)
		keyin = getKeyId(keyin)
		keyout = getKeyId(keyout)
		toggle = int(toggle)
		actionmap.bindTranslation(filename, device, keyin, keyout, toggle)


def loadKeymap(filename):
	actionMapInstance = eActionMap.getInstance()
	domKeymap = fileReadXML(filename, source=MODULE_NAME)
	if domKeymap:
		for domMap in domKeymap.findall("map"):
			context = domMap.attrib.get("context")
			if context is None:
				print("ActionMap] Error: All key map action maps in '%s' must have a context!" % filename)
			else:
				parseKeymap(filename, context, actionMapInstance, "generic", domMap)
				for domDevice in domMap.findall("device"):
					parseKeymap(filename, context, actionMapInstance, domDevice.attrib.get("name"), domDevice)
		for domMap in domKeymap.findall("translate"):  # FIME Remove keytranslation.xml.
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
		self.legacyBound = False
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
				print("[ActionMap] DEBUG: Creating legacy navigation action map.")
				print(leftAction)
				print(rightAction)
			self.legacyActions = {
				"left": leftAction,
				"right": rightAction
			}
		else:
			self.legacyActions = {}
		if undefinedAction:
			context = "', '".join(sorted(self.contexts))
			contextPlural = "s" if len(self.contexts) > 1 else ""
			action = "', '".join(sorted(undefinedAction))
			actionPlural = "s" if len(undefinedAction) > 1 else ""
			print("[ActionMap] Map context%s '%s': Undefined action%s '%s'." % (contextPlural, context, actionPlural, action))

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
			print("[ActionMap] Map context '%s' -> Action '%s'." % (context, action))
			response = self.actions[action]()
			if response is not None:
				return response
			return 1
		print("[ActionMap] Map context '%s' -> Unknown action '%s'!  (Typo in map?)" % (context, action))
		return 0

	def legacyAction(self, context, action):
		if action in self.legacyActions:
			print("[ActionMap] Map context '%s' -> Legacy action '%s'." % (context, action))
			print(self.legacyActions[action])
			response = self.legacyActions[action]()
			if response is not None:
				return response
			return 1
		print("[ActionMap] Map context '%s' -> Unknown legacy action '%s'!  (Typo in map?)" % (context, action))
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
# be picked up by the "HelpableScreen".
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
		ActionMap.__init__(self, contexts, actionDict, prio)


class HelpableNumberActionMap(NumberActionMap, HelpableActionMap):
	def __init__(self, parent, contexts, actions=None, prio=0, description=None):
		# Initialize NumberActionMap with empty context and actions
		# so that the underlying ActionMap is only initialized with
		# these once, via the HelpableActionMap.
		NumberActionMap.__init__(self, [], {})
		HelpableActionMap.__init__(self, parent, contexts, actions, prio, description)
