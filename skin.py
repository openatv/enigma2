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
			<widget name="okbutton" position="10,190" size="280,50" font="Arial:20" valign="center" halign="center" />
			<widget name="title" position="10,10" size="280,20" />
			<widget name="menu" position="10,30" size="280,140" />
		</screen>
		<screen name="clockDisplay" position="300,100" size="300,300">
			<widget name="okbutton" position="10,10" size="280,40" />
			<widget name="title" position="10,120" size="280,50" />
			<widget name="theClock" position="10,60" size="280,50" />
		</screen>
		<screen name="infoBar" position="80,350" size="540,150" title="InfoBar">
			<widget name="CurrentTime" position="10,10" size="40,30" />
			<widget name="ServiceName" position="50,20" size="200,30" />
			<widget name="Event_Now" position="100,40" size="300,30" />
			<widget name="Event_Next" position="100,90" size="300,30" />
			<widget name="Event_Now_Duration" position="440,40" size="80,30" />
			<widget name="Event_Next_Duration" position="440,90" size="80,30" />
		</screen>
		<screen name="channelSelection" position="100,80" size="500,240" title="Channel Selection">
			<widget name="list" position="20,50" size="300,150" />
			<widget name="okbutton" position="340,50" size="140,30" />
		</screen>
		<screen name="serviceScan" position="150,100" size="300,200" title="Service Scan">
			<widget name="scan_progress" position="10,10" size="280,50" />
			<widget name="scan_state" position="10,60" size="280,30" />
			<widget name="okbutton" position="10,100" size="280,40" />
		</screen>
	</skin>
""")


def elementsWithTag(el, tag):
	for x in el:
		if x.nodeType != xml.dom.minidom.Element.nodeType:
			continue
		if x.tagName == tag:
			yield x

def parsePosition(str):
	x, y = str.split(',')
	return ePoint(int(x), int(y))

def parseSize(str):
	x, y = str.split(',')
	return eSize(int(x), int(y))

def parseFont(str):
	name, size = str.split(':')
	return gFont(name, int(size))

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
		try:
			if attrib == 'position':
				guiObject.move(parsePosition(value))
			elif attrib == 'size':
				guiObject.resize(parseSize(value))
			elif attrib == 'title':
				guiObject.setTitle(value)
			elif attrib == 'font':
				guiObject.setFont(parseFont(value))
			elif attrib == "valign":
				try:
					guiObject.setVAlign(
						{ "top": guiObject.alignTop,
							"center": guiObject.alignCenter,
							"bottom": guiObject.alignBottom
						}[value])
				except KeyError:
					print "valign must be either top, center or bottom!"
			elif attrib == "halign":
				try:
					guiObject.setHAlign(
						{ "left": guiObject.alignLeft,
							"center": guiObject.alignCenter,
							"right": guiObject.alignRight,
							"block": guiObject.alignBlock
						}[value])
				except KeyError:
					print "halign must be either left, center, right or block!"
			elif attrib != 'name':
				print "unsupported attribute " + attrib + "=" + value
		except AttributeError:
			print "widget %s (%s) doesn't support attribute %s!" % ("", guiObject.__class__.__name__, attrib)

def applyGUIskin(screen, parent, skin, name):
	
	myscreen = None
	
	# first, find the corresponding screen element
	skin = dom.childNodes[0]
	assert skin.tagName == "skin", "root element in skin must be 'skin'!"
	
	for x in elementsWithTag(skin.childNodes, "screen"):
		if x.getAttribute('name') == name:
			myscreen = x
	del skin
	
	assert myscreen != None, "no skin for screen '" + name + "' found!"
	
	applyAttributes(parent, myscreen)
	
	# now walk all widgets
	for widget in elementsWithTag(myscreen.childNodes, "widget"):
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
