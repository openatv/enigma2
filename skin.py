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
	"""<skin>
		<windowstyle type="skinned">
			<color name="defaultBackground" color="#4075a7" />
			<borderset name="bsWindow">
				<pixmap pos="bpTopLeft"     filename="data/b_w_tl.png" />
				<pixmap pos="bpTop"         filename="data/b_w_t.png"  />
				<pixmap pos="bpTopRight"    filename="data/b_w_tr.png" />
				<pixmap pos="bpLeft"        filename="data/b_w_l.png"  />
				<pixmap pos="bpRight"       filename="data/b_w_r.png"  />
				<pixmap pos="bpBottomLeft"  filename="data/b_w_bl.png" />
				<pixmap pos="bpBottom"      filename="data/b_w_b.png"  />
				<pixmap pos="bpBottomRight" filename="data/b_w_br.png" />
			</borderset>
		</windowstyle>
		<screen name="mainMenu" position="300,100" size="300,300" title="real main menu">
			<widget name="okbutton" position="10,190" size="280,50" font="Arial;20" valign="center" halign="center" />
			<widget name="title" position="10,10" size="280,20" />
			<widget name="menu" position="10,30" size="280,140" />
		</screen>
		<screen name="clockDisplay" position="300,100" size="300,300">
			<widget name="okbutton" position="10,10" size="280,40" />
			<widget name="title" position="10,120" size="280,50" />
			<widget name="theClock" position="10,60" size="280,50" />
		</screen>
		<screen name="infoBar" position="0,380" size="720,151" title="InfoBar" flags="wfNoBorder">
			<ePixmap position="0,0" size="720,151" pixmap="info-bg.png" />
			
			<widget name="ServiceName" position="69,30" size="427,26" valign="center" font="Arial;32" />
			<widget name="CurrentTime" position="575,10" size="66,30" />
			<widget name="Event_Now" position="273,68" size="282,30" font="Arial;29" backgroundColor="#586D88" />
			<widget name="Event_Next" position="273,98" size="282,30" font="Arial;29" />
			<widget name="Event_Now_Duration" position="555,68" size="70,26" font="Arial;26" />
			<widget name="Event_Next_Duration" position="555,98" size="70,26" font="Arial;26" />
<!--			<eLabel position="70,0" size="300,30" text=".oO skin Oo." font="Arial;20" /> -->
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
	</skin>""")

# filters all elements of childNode with the specified function
# example: nodes = elementsWithTag(childNodes, lambda x: x == "bla")
def elementsWithTag(el, tag):

	# fiiixme! (works but isn't nice)
	if tag.__class__ == "".__class__:
		str = tag
		tag = lambda x: x == str
		
	for x in el:
		if x.nodeType != xml.dom.minidom.Element.nodeType:
			continue
		if tag(x.tagName):
			yield x

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
		raise "color must be #aarrggbb"
	return gRGB(int(str[1:], 0x10))

def applyAttributes(guiObject, node, desktop):
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
				print desktop
				desktop.makeCompatiblePixmap(ptr)
				guiObject.setPixmap(ptr)
#				guiObject.setPixmapFromFile(value)
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
			elif attrib != 'name':
				print "unsupported attribute " + attrib + "=" + value
		except AttributeError:
			print "widget %s (%s) doesn't support attribute %s!" % ("", guiObject.__class__.__name__, attrib)

def loadSkin():
	print "loading skin..."
	
	def getPNG(x):
		g = gPixmapPtr()
		loadPNG(g, x)
		g = g.grabRef()
		return g
	
	skin = dom.childNodes[0]
	assert skin.tagName == "skin", "root element in skin must be 'skin'!"
	
	for windowstyle in elementsWithTag(skin.childNodes, "windowstyle"):
		style = eWindowStyleSkinned()
		
		for borderset in elementsWithTag(windowstyle.childNodes, "borderset"):
			bsName = str(borderset.getAttribute("name"))
			for pixmap in elementsWithTag(borderset.childNodes, "pixmap"):
				bpName = str(pixmap.getAttribute("pos"))
				filename = str(pixmap.getAttribute("filename"))
				
				style.setPixmap(eWindowStyleSkinned.__dict__[bsName], eWindowStyleSkinned.__dict__[bpName], getPNG(filename))

		for color in elementsWithTag(windowstyle.childNodes, "color"):
			type = str(color.getAttribute("name"))
			color = parseColor(color.getAttribute("color"))
			
			if type == "defaultBackground":
				style.setDefaultBackgroundColor(color)
			else:
				raise "unknown color %s" % (type)
			
		x = eWindowStyleManagerPtr()
		eWindowStyleManager.getInstance(x)
		x.setStyle(style)

def applyGUIskin(screen, skin, name, desktop):
	myscreen = None
	
	# first, find the corresponding screen element
	skin = dom.childNodes[0]
	
	for x in elementsWithTag(skin.childNodes, "screen"):
		if x.getAttribute('name') == name:
			myscreen = x
	del skin
	
	assert myscreen != None, "no skin for screen '" + name + "' found!"
	
	applyAttributes(screen.instance, myscreen, desktop)
	
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
		
		applyAttributes(guiObject, widget, desktop)

	# now walk additional objects
	for widget in elementsWithTag(myscreen.childNodes, lambda x: x != "widget"):
		if widget.tagName == "eLabel":
			guiObject = eLabel(screen.instance)
		elif widget.tagName == "ePixmap":
			guiObject = ePixmap(screen.instance)
		else:
			raise str("unsupported stuff : %s" % widget.tagName)
		
		applyAttributes(guiObject, widget, desktop	)
		guiObject.thisown = 0
