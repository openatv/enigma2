
keyBindings = { }

def addKeyBinding(key, context, action):
	if (context, action) in keyBindings:
		keyBindings[(context, action)].append(key)
	else:
		keyBindings[(context, action)] = [key]

def queryKeyBinding(context, action):
	if (context, action) in keyBindings:
		return keyBindings[(context, action)]
	else:
		return [ ]

def getKeyDescription(key):
	return "key_%0x" % key
