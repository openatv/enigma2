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

def parseKeys(context, filename, actionmap, device, keys):
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
		else:	
			assert mapto, "[keymapparser] %s: must specify mapto (or unmap) in context %s, id '%s'" % (filename, context, id)
			assert id, "[keymapparser] %s: must specify id in context %s, mapto '%s'" % (filename, context, mapto)
			keyid = getKeyId(id)

			flag_ascii_to_id = lambda x: {'m':1,'b':2,'r':4,'l':8}[x]

			flags = sum(map(flag_ascii_to_id, flags))

			assert flags, "[keymapparser] %s: must specify at least one flag in context %s, id '%s'" % (filename, context, id)

#			print "[keymapparser] " + context + "::" + mapto + " -> " + device + "." + hex(keyid)
			actionmap.bindKey(filename, device, keyid, flags, context, mapto)
			addKeyBinding(filename, keyid, context, mapto, flags)

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

		keyin  = getKeyId(keyin)
		keyout = getKeyId(keyout)
		toggle = int(toggle)
		actionmap.bindTranslation(filename, device, keyin, keyout, toggle)

def readKeymap(filename):
	p = enigma.eActionMap.getInstance()
	assert p

	try:
		source = open(filename)
	except:
		print "[keymapparser] keymap file " + filename + " not found"
		return

	try:
		dom = xml.etree.cElementTree.parse(source)
	except:
		raise KeymapError("[keymapparser] keymap %s not well-formed." % filename)

	source.close()
	keymap = dom.getroot()

	for cmap in keymap.findall("map"):
		context = cmap.attrib.get("context")
		assert context, "[keymapparser] map must have context"

		parseKeys(context, filename, p, "generic", cmap)

		for device in cmap.findall("device"):
			parseKeys(context, filename, p, device.attrib.get("name"), device)

	for ctrans in keymap.findall("translate"):
		for device in ctrans.findall("device"):
			parseTrans(filename, p, device.attrib.get("name"), device)

def removeKeymap(filename):
	p = enigma.eActionMap.getInstance()
	p.unbindKeyDomain(filename)
