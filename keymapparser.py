import xml.dom.minidom
import enigma
from Tools.XMLTools import elementsWithTag

from keyids import KEYIDS;

# these are only informational (for help)...
from Tools.KeyBindings import addKeyBinding

def readKeymap():

	p = enigma.eActionMapPtr()
	enigma.eActionMap.getInstance(p)
	assert p
	
	filename1 = "data/keymap.xml"
	filename2 = "/usr/share/enigma2/keymap.xml"
		
	try:
		source = open(filename1)
		filename = filename1
	except:
		source = open(filename2)
		filename = filename2
#		raise "couldn't open keymap.xml!"
	
	try:
		dom = xml.dom.minidom.parse(source)
	except:
		raise "keymap not well-formed."
	
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
				
				flag_ascii_to_id = lambda x: {'m':1,'b':2,'r':4}[x]
				
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
				p.bindKey(device, keyid, flags, context, mapto)
				addKeyBinding(keyid, context, mapto)
		
		parseKeys("generic", cmap)
		
		for device in elementsWithTag(cmap.childNodes, "device"):
			parseKeys(str(device.getAttribute("name")), device)

