from enigma import *
import xml.dom.minidom
from xml.dom import EMPTY_NAMESPACE

from Tools.XMLTools import elementsWithTag, mergeText

colorNames = dict()

def dump(x, i=0):
	print " " * i + str(x)
	try:
		for n in x.childNodes:
			dump(n, i + 1)
	except:
		None

# read the skin
try:
	# first we search in the current path
	skinfile = file('data/skin.xml', 'r')
except:
	# if not found in the current path, we use the global datadir-path
	skinfile = file('/usr/share/enigma2/skin.xml', 'r')
dom = xml.dom.minidom.parseString(skinfile.read())
skinfile.close()


def parsePosition(str):
	x, y = str.split(',')
	return ePoint(int(x), int(y))

def parseSize(str):
	x, y = str.split(',')
	return eSize(int(x), int(y))

def parseFont(str):
	name, size = str.split(';')
	return gFont(name, int(size))

def parseColor(str):
	if str[0] != '#':
		try:
			return colorNames[str]
		except:
			raise ("color '%s' must be #aarrggbb or valid named color" % (str))
	return gRGB(int(str[1:], 0x10))

def collectAttributes(skinAttributes, node):
	# walk all attributes
	for p in range(node.attributes.length):
		a = node.attributes.item(p)
		
		# convert to string (was: unicode)
		attrib = str(a.name)
		# TODO: proper UTF8 translation?! (for value)
		# TODO: localization? as in e1?
		value = str(a.value)
		
		skinAttributes.append((attrib, value))

def applySingleAttribute(guiObject, desktop, attrib, value):		
	# and set attributes
	try:
		if attrib == 'position':
			guiObject.move(parsePosition(value))
		elif attrib == 'size':
			guiObject.resize(parseSize(value))
		elif attrib == 'title':
			guiObject.setTitle(value)
		elif attrib == 'text':
			guiObject.setText(value)
		elif attrib == 'font':
			guiObject.setFont(parseFont(value))
		elif attrib == "pixmap":
			ptr = gPixmapPtr()
			if loadPNG(ptr, value):
				raise "loading PNG failed!"
			x = ptr
			ptr = ptr.__deref__()
			desktop.makeCompatiblePixmap(ptr)
			guiObject.setPixmap(ptr)
			# guiObject.setPixmapFromFile(value)
		elif attrib == "orientation": # used by eSlider
			try:
				guiObject.setOrientation(
					{ "orVertical": guiObject.orVertical,
						"orHorizontal": guiObject.orHorizontal
					}[value])
			except KeyError:
				print "oprientation must be either orVertical or orHorizontal!"
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
		elif attrib == "flags":
			flags = value.split(',')
			for f in flags:
				try:
					fv = eWindow.__dict__[f]
					guiObject.setFlag(fv)
				except KeyError:
					print "illegal flag %s!" % f
		elif attrib == "backgroundColor":
			guiObject.setBackgroundColor(parseColor(value))
		elif attrib == "foregroundColor":
			guiObject.setForegroundColor(parseColor(value))
		elif attrib != 'name':
			print "unsupported attribute " + attrib + "=" + value
	except int:
# AttributeError:
		print "widget %s (%s) doesn't support attribute %s!" % ("", guiObject.__class__.__name__, attrib)

def applyAllAttributes(guiObject, desktop, attributes):
	for (attrib, value) in attributes:
		applySingleAttribute(guiObject, desktop, attrib, value)

def loadSkin(desktop):
	print "loading skin..."
	
	def getPNG(x):
		g = gPixmapPtr()
		loadPNG(g, x)
		g = g.grabRef()
		return g
	
	skin = dom.childNodes[0]
	assert skin.tagName == "skin", "root element in skin must be 'skin'!"
	
	for c in elementsWithTag(skin.childNodes, "colors"):
		for color in elementsWithTag(c.childNodes, "color"):
			name = str(color.getAttribute("name"))
			color = str(color.getAttribute("value"))
			
			if not len(color):
				raise ("need color and name, got %s %s" % (name, color))
				
			colorNames[name] = parseColor(color)
	
	for windowstyle in elementsWithTag(skin.childNodes, "windowstyle"):
		style = eWindowStyleSkinned()
		
		style.setTitleFont(gFont("Arial", 20));
		style.setTitleOffset(eSize(20, 5));
		
		for borderset in elementsWithTag(windowstyle.childNodes, "borderset"):
			bsName = str(borderset.getAttribute("name"))
			for pixmap in elementsWithTag(borderset.childNodes, "pixmap"):
				bpName = str(pixmap.getAttribute("pos"))
				filename = str(pixmap.getAttribute("filename"))
				
				png = getPNG(filename)
				
				# adapt palette
				desktop.makeCompatiblePixmap(png)
				style.setPixmap(eWindowStyleSkinned.__dict__[bsName], eWindowStyleSkinned.__dict__[bpName], png)

		for color in elementsWithTag(windowstyle.childNodes, "color"):
			type = str(color.getAttribute("name"))
			color = parseColor(color.getAttribute("color"))
			
			try:
				style.setColor(eWindowStyleSkinned.__dict__["col" + type], color)
			except:
				raise ("Unknown color %s" % (type))
			
		x = eWindowStyleManagerPtr()
		eWindowStyleManager.getInstance(x)
		x.setStyle(style)

def readSkin(screen, skin, name, desktop):
	myscreen = None
	
	# first, find the corresponding screen element
	skin = dom.childNodes[0]
	
	for x in elementsWithTag(skin.childNodes, "screen"):
		if x.getAttribute('name') == name:
			myscreen = x
	del skin
	
	if myscreen is None:
		# try embedded skin
		print screen.__dict__
		if "parsedSkin" in screen.__dict__:
			myscreen = screen.parsedSkin
		elif "skin" in screen.__dict__:
			myscreen = screen.parsedSkin = xml.dom.minidom.parseString(screen.skin).childNodes[0]
	
	assert myscreen is not None, "no skin for screen '" + name + "' found!"

	screen.skinAttributes = [ ]
	collectAttributes(screen.skinAttributes, myscreen)
	
	screen.additionalWidgets = [ ]
	
	# now walk all widgets
	for widget in elementsWithTag(myscreen.childNodes, "widget"):
		wname = widget.getAttribute('name')
		if wname == None:
			print "widget has no name!"
			continue
		
		# get corresponding gui object
		try:
			attributes = screen[wname].skinAttributes = [ ]
		except:
			raise str("component with name '" + wname + "' was not found in skin of screen '" + name + "'!")
		
		collectAttributes(attributes, widget)

	# now walk additional objects
	for widget in elementsWithTag(myscreen.childNodes, lambda x: x != "widget"):
		if widget.tagName == "applet":
			codeText = mergeText(widget.childNodes).strip()
			type = widget.getAttribute('type')

			code = compile(codeText, "skin applet", "exec")
			
			if type == "onLayoutFinish":
				screen.onLayoutFinish.append(code)
			else:
				raise str("applet type '%s' unknown!" % type)
			
			continue
		
		class additionalWidget:
			pass
		
		w = additionalWidget()
		
		if widget.tagName == "eLabel":
			w.widget = eLabel
		elif widget.tagName == "ePixmap":
			w.widget = ePixmap
		else:
			raise str("unsupported stuff : %s" % widget.tagName)
		
		w.skinAttributes = [ ]
		collectAttributes(w.skinAttributes, widget)
		
		# applyAttributes(guiObject, widget, desktop)
		# guiObject.thisown = 0
		screen.additionalWidgets.append(w)
