from enigma import *
import xml.dom.minidom
from xml.dom import EMPTY_NAMESPACE

def dump(x, i=0):
	print " " * i + str(x)
	try:
		for n in x.childNodes:
			dump(n, i + 1)
	except:
		None

dom = xml.dom.minidom.parseString(
	"""
	<skin>
		<screen name="mainMenu" position="300,100" size="300,300" title="real main menu">
			<widget name="okbutton" position="10,190" size="280,50" />
			<widget name="title" position="10,10" size="280,20" />
			<widget name="menu" position="10,30" size="280,140" />
		</screen>
		<screen name="clockDisplay" position="300,100" size="300,300">
			<widget name="okbutton" position="10,10" size="280,40" />
			<widget name="title" position="10,120" size="280,50" />
			<widget name="theClock" position="10,60" size="280,50" />
		</screen>
		<screen name="infoBar" position="100,100" size="300,400" title="InfoBar">
			<widget name="channelSwitcher" position="10,190" size="280,50" />
		</screen>
		<screen name="channelSelection" position="300,100" size="300,300" title="Channel Selection">
			<widget name="okbutton" position="10,190" size="280,50" />
			<widget name="list" position="10,30" size="280,140" />
		</screen>
		<screen name="serviceScan" position="150,100" size="300,200" title="Service Scan">
			<widget name="scan_progress" position="10,10" size="280,50" />
			<widget name="scan_state" position="10,60" size="280,30" />
			<widget name="okbutton" position="10,100" size="280,40" />
		</screen>
	</skin>
""")



def parsePosition(str):
	x, y = str.split(',')
	return ePoint(int(x), int(y))

def parseSize(str):
	x, y = str.split(',')
	return eSize(int(x), int(y))

def applyAttributes(guiObject, node):
	# walk all attributes
	for p in range(node.attributes.length):
		a = node.attributes.item(p)
		
		# convert to string (was: unicode)
		attrib = str(a.name)
		# TODO: proper UTF8 translation?! (for value)
		# TODO: localization? as in e1?
		value = str(a.value)
		
		# and set attributes
		if attrib == 'position':
			guiObject.move(parsePosition(value))
		elif attrib == 'size':
			guiObject.resize(parseSize(value))
		elif attrib == 'title':
			guiObject.setTitle(value)
		elif attrib != 'name':
			print "unsupported attribute " + attrib + "=" + value

def applyGUIskin(screen, parent, skin, name):
	
	myscreen = None
	
	# first, find the corresponding screen element
	skin = dom.getElementsByTagName("skin")[0]
	screens = skin.getElementsByTagName("screen")
	del skin
	for x in screens:
		if x.getAttribute('name') == name:
			myscreen = x
	
	assert myscreen != None, "no skin for screen '" + name + "' found!"
	
	applyAttributes(parent, myscreen)
	
	# now walk all widgets
	for widget in myscreen.getElementsByTagName("widget"):
		wname = widget.getAttribute('name')
		if wname == None:
			print "widget has no name!"
			continue
		
		# get corresponding gui object
		try:
			guiObject = screen[wname].instance
		except:
			raise str("component with name '" + wname + "' was not found in skin of screen '" + name + "'!")
		
		applyAttributes(guiObject, widget)
