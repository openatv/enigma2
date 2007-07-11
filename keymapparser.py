import xml.dom.minidom
import enigma
from Tools.XMLTools import elementsWithTag

from keyids import KEYIDS;

# these are only informational (for help)...
from Tools.KeyBindings import addKeyBinding

def readKeymap(filename = "/usr/share/enigma2/keymap.xml"):

	p = enigma.eActionMap.getInstance()
	assert p

	source = open(filename)

	try:
		dom = xml.dom.minidom.parse(source)
	except:
		raise "keymap %s not well-formed." % filename

	keymap = dom.childNodes[0]

	maps = elementsWithTag(keymap.childNodes, "map")

	for cmap in maps:
		context = str(cmap.getAttribute("context"))
		assert context != "", "map must have context"

		def parseKeys(device, keys):
			for x in elementsWithTag(keys.childNodes, "key"):
				mapto = str(x.getAttribute("mapto"))
				id = x.getAttribute("id")
				flags = x.getAttribute("flags")

				flag_ascii_to_id = lambda x: {'m':1,'b':2,'r':4,'l':8}[x]

#				try:
				flags = sum(map(flag_ascii_to_id, flags))
#				print "-> " + str(flags)
#				except:
#					raise str("%s: illegal flags '%s' specificed in context %s, id '%s'" % (filename, flags, context, id))

				assert mapto != "", "%s: must specify mapto in context %s, id '%s'" % (filename, context, id)
				assert id != "", "%s: must specify id in context %s, mapto '%s'" % (filename, context, mapto)
				assert flags != 0, "%s: must specify at least one flag in context %s, id '%s'" % (filename, context, id)

				if len(id) == 1:
					keyid = ord(id) | 0x8000
				elif id[0] == '\\':
					if id[1] == 'x':
						keyid = int(id[2:], 0x10) | 0x8000
					elif id[1] == 'd':
						keyid = int(id[2:]) | 0x8000
					else:
						raise "key id '" + str(id) + "' is neither hex nor dec"
				else:
					try:
						keyid = KEYIDS[id]
					except:
						raise "key id '" + str(id) + "' is illegal"

#				print context + "::" + mapto + " -> " + device + "." + hex(keyid)
				p.bindKey(filename, device, keyid, flags, context, mapto)
				addKeyBinding(filename, keyid, context, mapto, flags)

		parseKeys("generic", cmap)

		for device in elementsWithTag(cmap.childNodes, "device"):
			parseKeys(str(device.getAttribute("name")), device)

def removeKeymap(filename):
	p = enigma.eActionMap.getInstance()
	p.unbindKeyDomain(filename)
