import xml.dom.minidom
import enigma

from keyids import KEYIDS;

def readKeymap():

	p = enigma.eActionMapPtr()
	enigma.eActionMap.getInstance(p)
	assert p
	
	filename = "keymap.xml"
	
	try:
		source = open(filename)
	except:
		raise "couldn't open keymap.xml!"
	
	try:
		dom = xml.dom.minidom.parse(source)
	except:
		raise "keymap not well-formed."
	
	try:	
		keymap = dom.getElementsByTagName("keymap")[0]
	except:
		raise "no keymap defined."
	
	maps = keymap.getElementsByTagName("map")
	
	for cmap in maps:
		context = str(cmap.getAttribute("context"))
		assert context != "", "map must have context"
	
		def parseKeys(device, keys):
			for x in keys.getElementsByTagName("key"):
				mapto = str(x.getAttribute("mapto"))
				id = x.getAttribute("id")
				flags = x.getAttribute("flags")
				
				flag_ascii_to_id = lambda x: {'m':1,'r':2,'b':4}[x]
				
#				try:
				flags = sum(map(flag_ascii_to_id, flags))
				print "-> " + str(flags)
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

				print context + "::" + mapto + " -> " + device + "." + hex(keyid)
				p.bindKey(device, keyid, 7, context, mapto)
		
		parseKeys("generic", cmap)
		
		for device in cmap.getElementsByTagName("device"):
			parseKeys(str(device.getAttribute("name")), device)

