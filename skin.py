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

from Tools.Directories import resolveFilename, SCOPE_SKIN, SCOPE_SKIN_IMAGE, SCOPE_FONTS

dom_skins = [ ]

def loadSkin(name):
	# read the skin
	dom_skins.append(xml.dom.minidom.parse(resolveFilename(SCOPE_SKIN, name)))

loadSkin('skin.xml')
loadSkin('skin_default.xml')

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

def collectAttributes(skinAttributes, node, skin_path_prefix=None):
	# walk all attributes
	for p in range(node.attributes.length):
		a = node.attributes.item(p)
		
		# convert to string (was: unicode)
		attrib = str(a.name)
		# TODO: localization? as in e1?
		value = a.value.encode("utf-8")
		
		if skin_path_prefix and attrib in ["pixmap", "pointer"] and len(value) and value[0:2] == "~/":
			value = skin_path_prefix + value[1:]
		
		skinAttributes.append((attrib, value))

def loadPixmap(path):
	ptr = loadPNG(path)
	if ptr is None:
		raise "pixmap file %s not found!" % (path)
	return ptr

def applySingleAttribute(guiObject, desktop, attrib, value):
	# and set attributes
	try:
		if attrib == 'position':
			guiObject.move(parsePosition(value))
		elif attrib == 'size':
			guiObject.resize(parseSize(value))
		elif attrib == 'title':
			guiObject.setTitle(_(value))
		elif attrib == 'text':
			guiObject.setText(value)
		elif attrib == 'font':
			guiObject.setFont(parseFont(value))
		elif attrib == 'zPosition':
			guiObject.setZPosition(int(value))
		elif attrib == "pixmap":
			ptr = loadPixmap(resolveFilename(SCOPE_SKIN_IMAGE, value))
			# that __deref__ still scares me!
			desktop.makeCompatiblePixmap(ptr.__deref__())
			guiObject.setPixmap(ptr.__deref__())
			# guiObject.setPixmapFromFile(value)
		elif attrib == "alphatest": # used by ePixmap
			guiObject.setAlphatest(
				{ "on": True,
				  "off": False
				}[value])
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
		elif attrib == "shadowColor":
			guiObject.setShadowColor(parseColor(value))
		elif attrib == "selectionDisabled":
			guiObject.setSelectionEnable(0)
		elif attrib == "transparent":
			guiObject.setTransparent(int(value))
		elif attrib == "borderColor":
			guiObject.setBorderColor(parseColor(value))
		elif attrib == "borderWidth":
			guiObject.setBorderWidth(int(value))
		elif attrib == "scrollbarMode":
			guiObject.setScrollbarMode(
				{ "showOnDemand": guiObject.showOnDemand,
					"showAlways": guiObject.showAlways,
					"showNever": guiObject.showNever
				}[value])
		elif attrib == "enableWrapAround":
			guiObject.setWrapAround(True)
		elif attrib == "pointer":
			(name, pos) = value.split(':')
			pos = parsePosition(pos)
			ptr = loadPixmap(resolveFilename(SCOPE_SKIN_IMAGE, name))
			desktop.makeCompatiblePixmap(ptr.__deref__())
			guiObject.setPointer(ptr.__deref__(), pos)
		elif attrib == 'shadowOffset':
			guiObject.setShadowOffset(parsePosition(value))
		elif attrib != 'name':
			print "unsupported attribute " + attrib + "=" + value
	except int:
# AttributeError:
		print "widget %s (%s) doesn't support attribute %s!" % ("", guiObject.__class__.__name__, attrib)

def applyAllAttributes(guiObject, desktop, attributes):
	for (attrib, value) in attributes:
		applySingleAttribute(guiObject, desktop, attrib, value)

def loadSingleSkinData(desktop, dom_skin):
	"""loads skin data like colors, windowstyle etc."""
	
	skin = dom_skin.childNodes[0]
	assert skin.tagName == "skin", "root element in skin must be 'skin'!"
	
	for c in elementsWithTag(skin.childNodes, "colors"):
		for color in elementsWithTag(c.childNodes, "color"):
			name = str(color.getAttribute("name"))
			color = str(color.getAttribute("value"))
			
			if not len(color):
				raise ("need color and name, got %s %s" % (name, color))
				
			colorNames[name] = parseColor(color)
	
	for c in elementsWithTag(skin.childNodes, "fonts"):
		for font in elementsWithTag(c.childNodes, "font"):
			filename = str(font.getAttribute("filename") or "<NONAME>")
			name = str(font.getAttribute("name") or "Regular")
			scale = int(font.getAttribute("scale") or "100")
			is_replacement = font.getAttribute("replacement") != ""
			addFont(resolveFilename(SCOPE_FONTS, filename), name, scale, is_replacement)
	
	for windowstyle in elementsWithTag(skin.childNodes, "windowstyle"):
		style = eWindowStyleSkinned()
		
		# defaults
		font = gFont("Regular", 20)
		offset = eSize(20, 5)
		
		for title in elementsWithTag(windowstyle.childNodes, "title"):
			offset = parseSize(title.getAttribute("offset"))
			font = parseFont(str(title.getAttribute("font")))

		style.setTitleFont(font);
		style.setTitleOffset(offset)
		
		for borderset in elementsWithTag(windowstyle.childNodes, "borderset"):
			bsName = str(borderset.getAttribute("name"))
			for pixmap in elementsWithTag(borderset.childNodes, "pixmap"):
				bpName = str(pixmap.getAttribute("pos"))
				filename = str(pixmap.getAttribute("filename"))
				
				png = loadPixmap(resolveFilename(SCOPE_SKIN_IMAGE, filename))
				
				# adapt palette
				desktop.makeCompatiblePixmap(png.__deref__())
				style.setPixmap(eWindowStyleSkinned.__dict__[bsName], eWindowStyleSkinned.__dict__[bpName], png.__deref__())

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

def loadSkinData(desktop):
	for dom_skin in dom_skins:
		loadSingleSkinData(desktop, dom_skin)

def lookupScreen(name):
	for dom_skin in dom_skins:
		# first, find the corresponding screen element
		skin = dom_skin.childNodes[0] 
		for x in elementsWithTag(skin.childNodes, "screen"):
			if x.getAttribute('name') == name:
				return x
	return None

def readSkin(screen, skin, name, desktop):
	myscreen = lookupScreen(name)
	
	# otherwise try embedded skin
	myscreen = myscreen or getattr(screen, "parsedSkin", None)
	
	# try uncompiled embedded skin
	if myscreen is None and getattr(screen, "skin", None):
		myscreen = screen.parsedSkin = xml.dom.minidom.parseString(screen.skin).childNodes[0]
	
	assert myscreen is not None, "no skin for screen '" + name + "' found!"

	screen.skinAttributes = [ ]
	
	skin_path_prefix = getattr(screen, "skin_path", None)

	collectAttributes(screen.skinAttributes, myscreen, skin_path_prefix)
	
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
		
		collectAttributes(attributes, widget, skin_path_prefix)

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
		collectAttributes(w.skinAttributes, widget, skin_path_prefix)
		
		# applyAttributes(guiObject, widget, desktop)
		# guiObject.thisown = 0
		screen.additionalWidgets.append(w)
