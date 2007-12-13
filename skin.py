import xml.dom.minidom
from os import path

from enigma import eSize, ePoint, gFont, eWindow, eLabel, ePixmap, eWindowStyleManager, \
	loadPNG, addFont, gRGB, eWindowStyleSkinned

from Components.config import ConfigSubsection, ConfigText, config
from Components.Converter.Converter import Converter
from Components.Sources.Source import Source, ObsoleteSource
from Tools.Directories import resolveFilename, SCOPE_SKIN, SCOPE_SKIN_IMAGE, SCOPE_FONTS
from Tools.Import import my_import

from Tools.XMLTools import elementsWithTag, mergeText

colorNames = dict()

def dump(x, i=0):
	print " " * i + str(x)
	try:
		for n in x.childNodes:
			dump(n, i + 1)
	except:
		None

class SkinError(Exception):
	def __init__(self, message):
		self.message = message

	def __str__(self):
		return self.message

dom_skins = [ ]

def loadSkin(name):
	# read the skin
	filename = resolveFilename(SCOPE_SKIN, name)
	mpath = path.dirname(filename) + "/"
	dom_skins.append((mpath, xml.dom.minidom.parse(filename)))

# we do our best to always select the "right" value
# skins are loaded in order of priority: skin with
# highest priority is loaded last, usually the user-provided
# skin.

# currently, loadSingleSkinData (colors, bordersets etc.)
# are applied one-after-each, in order of ascending priority.
# the dom_skin will keep all screens in descending priority,
# so the first screen found will be used.

# example: loadSkin("nemesis_greenline/skin.xml")
config.skin = ConfigSubsection()
config.skin.primary_skin = ConfigText(default = "skin.xml")

try:
	loadSkin(config.skin.primary_skin.value)
except (SkinError, IOError, AssertionError), err:
	print "SKIN ERROR:", err
	print "defaulting to standard skin..."
	config.skin.primary_skin.value = 'skin.xml'
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
			raise SkinError("color '%s' must be #aarrggbb or valid named color" % (str))
	return gRGB(int(str[1:], 0x10))

def collectAttributes(skinAttributes, node, skin_path_prefix=None, ignore=[]):
	# walk all attributes
	for p in range(node.attributes.length):
		a = node.attributes.item(p)
		
		# convert to string (was: unicode)
		attrib = str(a.name)
		# TODO: localization? as in e1?
		value = a.value.encode("utf-8")
		
		if attrib in ["pixmap", "pointer", "seek_pointer", "backgroundPixmap", "selectionPixmap"]:
			value = resolveFilename(SCOPE_SKIN_IMAGE, value, path_prefix=skin_path_prefix)
		
		if attrib not in ignore:
			skinAttributes.append((attrib, value))

def loadPixmap(path):
	ptr = loadPNG(path)
	if ptr is None:
		raise SkinError("pixmap file %s not found!" % (path))
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
			guiObject.setText(_(value))
		elif attrib == 'font':
			guiObject.setFont(parseFont(value))
		elif attrib == 'zPosition':
			guiObject.setZPosition(int(value))
		elif attrib in ["pixmap", "backgroundPixmap", "selectionPixmap"]:
			ptr = loadPixmap(value) # this should already have been filename-resolved.
			desktop.makeCompatiblePixmap(ptr)
			if attrib == "pixmap":
				guiObject.setPixmap(ptr)
			elif attrib == "backgroundPixmap":
				guiObject.setBackgroundPicture(ptr)
			elif attrib == "selectionPixmap":
				guiObject.setSelectionPicture(ptr)
			# guiObject.setPixmapFromFile(value)
		elif attrib == "alphatest": # used by ePixmap
			guiObject.setAlphatest(
				{ "on": 1,
				  "off": 0,
				  "blend": 2,
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
		elif attrib == "backgroundColorSelected":
			guiObject.setBackgroundColorSelected(parseColor(value))
		elif attrib == "foregroundColor":
			guiObject.setForegroundColor(parseColor(value))
		elif attrib == "foregroundColorSelected":
			guiObject.setForegroundColorSelected(parseColor(value))
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
		elif attrib == "pointer" or attrib == "seek_pointer":
			(name, pos) = value.split(':')
			pos = parsePosition(pos)
			ptr = loadPixmap(name)
			desktop.makeCompatiblePixmap(ptr)
			guiObject.setPointer({"pointer": 0, "seek_pointer": 1}[attrib], ptr, pos)
		elif attrib == 'shadowOffset':
			guiObject.setShadowOffset(parsePosition(value))
		elif attrib == 'noWrap':
			guiObject.setNoWrap(1)
		else:
			raise SkinError("unsupported attribute " + attrib + "=" + value)
	except int:
# AttributeError:
		print "widget %s (%s) doesn't support attribute %s!" % ("", guiObject.__class__.__name__, attrib)

def applyAllAttributes(guiObject, desktop, attributes):
	for (attrib, value) in attributes:
		applySingleAttribute(guiObject, desktop, attrib, value)

def loadSingleSkinData(desktop, dom_skin, path_prefix):
	"""loads skin data like colors, windowstyle etc."""
	
	skin = dom_skin.childNodes[0]
	assert skin.tagName == "skin", "root element in skin must be 'skin'!"

	for c in elementsWithTag(skin.childNodes, "output"):
		id = int(c.getAttribute("id") or "0")
		if id == 0: # framebuffer
			for res in elementsWithTag(c.childNodes, "resolution"):
				xres = int(res.getAttribute("xres" or "720"))
				yres = int(res.getAttribute("yres" or "576"))
				bpp = int(res.getAttribute("bpp" or "32"))

				from enigma import gFBDC
				i = gFBDC.getInstance()
				i.setResolution(xres, yres)

				if bpp != 32:
					# load palette (not yet implemented)
					pass

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
			addFont(resolveFilename(SCOPE_FONTS, filename, path_prefix=path_prefix), name, scale, is_replacement)
	
	for windowstyle in elementsWithTag(skin.childNodes, "windowstyle"):
		style = eWindowStyleSkinned()
		id = int(windowstyle.getAttribute("id") or "0")
		
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
				
				png = loadPixmap(resolveFilename(SCOPE_SKIN_IMAGE, filename, path_prefix=path_prefix))
				
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
			
		x = eWindowStyleManager.getInstance()
		x.setStyle(id, style)

def loadSkinData(desktop):
	skins = dom_skins[:]
	skins.reverse()
	for (path, dom_skin) in skins:
		loadSingleSkinData(desktop, dom_skin, path)

def lookupScreen(name):
	for (path, dom_skin) in dom_skins:
		# first, find the corresponding screen element
		skin = dom_skin.childNodes[0] 
		for x in elementsWithTag(skin.childNodes, "screen"):
			if x.getAttribute('name') == name:
				return x, path
	return None, None

def readSkin(screen, skin, names, desktop):
	if not isinstance(names, list):
		names = [names]

	name = "<embedded-in-'%s'>" % screen.__class__.__name__

	# try all skins, first existing one have priority
	for n in names:
		myscreen, path = lookupScreen(n)
		if myscreen is not None:
			# use this name for debug output
			name = n
			break

	# otherwise try embedded skin
	myscreen = myscreen or getattr(screen, "parsedSkin", None)

	# try uncompiled embedded skin
	if myscreen is None and getattr(screen, "skin", None):
		myscreen = screen.parsedSkin = xml.dom.minidom.parseString(screen.skin).childNodes[0]

	assert myscreen is not None, "no skin for screen '" + repr(names) + "' found!"

	screen.skinAttributes = [ ]
	
	skin_path_prefix = getattr(screen, "skin_path", path)

	collectAttributes(screen.skinAttributes, myscreen, skin_path_prefix, ignore=["name"])
	
	screen.additionalWidgets = [ ]
	screen.renderer = [ ]
	
	visited_components = set()
	
	# now walk all widgets
	for widget in elementsWithTag(myscreen.childNodes, "widget"):
		# ok, we either have 1:1-mapped widgets ('old style'), or 1:n-mapped 
		# widgets (source->renderer).

		wname = widget.getAttribute('name')
		wsource = widget.getAttribute('source')
		

		if wname is None and wsource is None:
			print "widget has no name and no source!"
			continue
		
		if wname:
			visited_components.add(wname)

			# get corresponding 'gui' object
			try:
				attributes = screen[wname].skinAttributes = [ ]
			except:
				raise SkinError("component with name '" + wname + "' was not found in skin of screen '" + name + "'!")

#			assert screen[wname] is not Source

			# and collect attributes for this
			collectAttributes(attributes, widget, skin_path_prefix, ignore=['name'])
		elif wsource:
			# get corresponding source

			while True: # until we found a non-obsolete source

				# parse our current "wsource", which might specifiy a "related screen" before the dot,
				# for example to reference a parent, global or session-global screen.
				scr = screen

				# resolve all path components
				path = wsource.split('.')
				while len(path) > 1:
					scr = screen.getRelatedScreen(path[0])
					if scr is None:
						print wsource
						print name
						raise SkinError("specified related screen '" + wsource + "' was not found in screen '" + name + "'!")
					path = path[1:]

				# resolve the source.
				source = scr.get(path[0])
				if isinstance(source, ObsoleteSource):
					# however, if we found an "obsolete source", issue warning, and resolve the real source.
					print "WARNING: SKIN '%s' USES OBSOLETE SOURCE '%s', USE '%s' INSTEAD!" % (name, wsource, source.new_source)
					print "OBSOLETE SOURCE WILL BE REMOVED %s, PLEASE UPDATE!" % (source.removal_date)
					if source.description:
						print source.description

					wsource = source.new_source
				else:
					# otherwise, use that source.
					break

			if source is None:
				raise SkinError("source '" + wsource + "' was not found in screen '" + name + "'!")
			
			wrender = widget.getAttribute('render')
			
			if not wrender:
				raise SkinError("you must define a renderer with render= for source '%s'" % (wsource))
			
			for converter in elementsWithTag(widget.childNodes, "convert"):
				ctype = converter.getAttribute('type')
				assert ctype, "'convert'-tag needs a 'type'-attribute"
				parms = mergeText(converter.childNodes).strip()
				converter_class = my_import('.'.join(["Components", "Converter", ctype])).__dict__.get(ctype)
				
				c = None
				
				for i in source.downstream_elements:
					if isinstance(i, converter_class) and i.converter_arguments == parms:
						c = i

				if c is None:
					print "allocating new converter!"
					c = converter_class(parms)
					c.connect(source)
				else:
					print "reused converter!"
	
				source = c
			
			renderer_class = my_import('.'.join(["Components", "Renderer", wrender])).__dict__.get(wrender)
			
			renderer = renderer_class() # instantiate renderer
			
			renderer.connect(source) # connect to source
			attributes = renderer.skinAttributes = [ ]
			collectAttributes(attributes, widget, skin_path_prefix, ignore=['render', 'source'])
			
			screen.renderer.append(renderer)

	from Components.GUIComponent import GUIComponent
	nonvisited_components = [x for x in set(screen.keys()) - visited_components if isinstance(x, GUIComponent)]
	
	assert not nonvisited_components, "the following components in %s don't have a skin entry: %s" % (name, ', '.join(nonvisited_components))

	# now walk additional objects
	for widget in elementsWithTag(myscreen.childNodes, lambda x: x != "widget"):
		if widget.tagName == "applet":
			codeText = mergeText(widget.childNodes).strip()
			type = widget.getAttribute('type')

			code = compile(codeText, "skin applet", "exec")
			
			if type == "onLayoutFinish":
				screen.onLayoutFinish.append(code)
			else:
				raise SkinError("applet type '%s' unknown!" % type)
			
			continue
		
		class additionalWidget:
			pass
		
		w = additionalWidget()
		
		if widget.tagName == "eLabel":
			w.widget = eLabel
		elif widget.tagName == "ePixmap":
			w.widget = ePixmap
		else:
			raise SkinError("unsupported stuff : %s" % widget.tagName)
		
		w.skinAttributes = [ ]
		collectAttributes(w.skinAttributes, widget, skin_path_prefix, ignore=['name'])
		
		# applyAttributes(guiObject, widget, desktop)
		# guiObject.thisown = 0
		screen.additionalWidgets.append(w)
