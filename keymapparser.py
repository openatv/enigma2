import enigma
import xml.etree.cElementTree

from keyids import KEYIDS

# these are only informational (for help)...
from Tools.KeyBindings import addKeyBinding

def parseKeys(context, filename, actionmap, device, keys):
	for x in keys.findall("key"):
		get_attr = x.attrib.get
		kid = get_attr("id")
		mapto = get_attr("mapto")
		flags = get_attr("flags")

		if not kid:
			print "[keymapparser] %s: must specify id in context %s, mapto '%s'" % (filename, context, mapto or "<none>")
			continue
		if not mapto:
			print "[keymapparser] %s: must specify mapto in context %s, id '%s'" % (filename, context, kid)
			continue

		def flag_ascii_to_id(x):
			try:
				return {'m': 1, 'b': 2, 'r': 4, 'l': 8}[x]
			except:
				print "[keymapparser] %s: ignoring unknown flag '%s' in context %s, id '%s'" % (filename, x, context, kid)
				return 0

		flags = flags and sum(map(flag_ascii_to_id, flags))
		if not flags:
			print "[keymapparser] %s: must specify at least one flag in context %s, id '%s'" % (filename, context, kid)
			continue

		if len(kid) == 1:
			keyid = ord(kid) | 0x8000
		elif kid[0] == '\\':
			try:
				if kid[1] == 'x':
					keyid = int(kid[2:], 0x10) | 0x8000
				elif kid[1] == 'd':
					keyid = int(kid[2:]) | 0x8000
				else:
					raise ValueError
			except:
				print "[keymapparser] %s: key id '%s' is neither hex nor dec" % (filename, kid)
				continue
		else:
			try:
				keyid = KEYIDS[kid]
			except:
				print "[keymapparser] %s: unknown key id '%s'" % (filename, kid)
				continue

		actionmap.bindKey(filename, device, keyid, flags, context, mapto)
		addKeyBinding(filename, keyid, context, mapto, flags)

def readKeymap(filename):
	p = enigma.eActionMap.getInstance()

	try:
		dom = xml.etree.cElementTree.parse(filename)
	except:
		print "[keymapparser] %s: keymap not well-formed." % filename
		return

	keymap = dom.getroot()

	for cmap in keymap.findall("map"):
		context = cmap.attrib.get("context")
		if not context:
			print "[keymapparser] %s: map must have context" % filename
			continue

		parseKeys(context, filename, p, "generic", cmap)

		for device in cmap.findall("device"):
			parseKeys(context, filename, p, device.attrib.get("name"), device)

def removeKeymap(filename):
	p = enigma.eActionMap.getInstance()
	p.unbindKeyDomain(filename)
