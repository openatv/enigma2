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
		<screen name="testDialog">
			<widget name="okbutton" position="10,120" size="280,40" />
			<widget name="title" position="10,10" size="280,20" />
			<widget name="menu" position="10,30" size="280,90" />
		</screen>
		<screen name="clockDisplay" position="300,100" size="300,300">
			<widget name="okbutton" position="10,10" size="280,40" />
			<widget name="title" position="10,120" size="280,50" />
			<widget name="theClock" position="10,60" size="280,50" />
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
		
		# and set attributes
		if a.name == 'position':
			guiObject.move(parsePosition(a.value))
		elif a.name == 'size':
			guiObject.resize(parseSize(a.value))
		elif a.name != 'name':
			print "unsupported attribute " + a.name

def applyGUIskin(screen, skin, name):
	
	myscreen = None
	
	# first, find the corresponding screen element
	skin = dom.getElementsByTagName("skin")[0]
	screens = skin.getElementsByTagName("screen")
	del skin
	for x in screens:
		if x.getAttribute('name') == name:
			myscreen = x
	
	assert myscreen != None, "no skin for screen " + name + " found!"
	
	print "ok, found screen.."
	
	# now walk all widgets
	for widget in myscreen.getElementsByTagName("widget"):
		name = widget.getAttribute('name')
		if name == None:
			print "widget has no name!"
			continue
		
		# get corresponding gui object
		guiObject = screen.data[name]["instance"]
		applyAttributes(guiObject, widget)
