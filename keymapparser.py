import enigma
import xml.etree.cElementTree

from keyids import KEYIDS

# these are only informational (for help)...
from Tools.KeyBindings import addKeyBinding

class KeymapError(Exception):
	def __init__(self, message):
		self.msg = message

	def __str__(self):
		return self.msg

def parseKeys(context, filename, actionmap, device, keys):
	for x in keys.findall("key"):
		get_attr = x.attrib.get
		mapto = get_attr("mapto")
		id = get_attr("id")
		flags = get_attr("flags")

		flag_ascii_to_id = lambda x: {'m':1,'b':2,'r':4,'l':8}[x]

		flags = sum(map(flag_ascii_to_id, flags))

		assert mapto, "%s: must specify mapto in context %s, id '%s'" % (filename, context, id)
		assert id, "%s: must specify id in context %s, mapto '%s'" % (filename, context, mapto)
		assert flags, "%s: must specify at least one flag in context %s, id '%s'" % (filename, context, id)

		if len(id) == 1:
			keyid = ord(id) | 0x8000
		elif id[0] == '\\':
			if id[1] == 'x':
				keyid = int(id[2:], 0x10) | 0x8000
			elif id[1] == 'd':
				keyid = int(id[2:]) | 0x8000
			else:
				raise KeymapError("[Keymapparser] key id '" + str(id) + "' is neither hex nor dec")
		else:
			try:
				keyid = KEYIDS[id]
			except:
				raise KeymapError("[Keymapparser] key id '" + str(id) + "' is illegal")
#				print context + "::" + mapto + " -> " + device + "." + hex(keyid)
		actionmap.bindKey(filename, device, keyid, flags, context, mapto)
		addKeyBinding(filename, keyid, context, mapto, flags)

def readKeymap(filename):
	p = enigma.eActionMap.getInstance()
	assert p

	source = open(filename)

	try:
		dom = xml.etree.cElementTree.parse(source)
	except:
		raise KeymapError("[Keymapparser] keymap %s not well-formed." % filename)

	source.close()
	keymap = dom.getroot()

	for cmap in keymap.findall("map"):
		context = cmap.attrib.get("context")
		assert context, "map must have context"

		parseKeys(context, filename, p, "generic", cmap)

		for device in cmap.findall("device"):
			parseKeys(context, filename, p, device.attrib.get("name"), device)

def removeKeymap(filename):
	p = enigma.eActionMap.getInstance()
	p.unbindKeyDomain(filename)
