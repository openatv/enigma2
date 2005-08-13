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

dom = xml.dom.minidom.parseString(
	"""<skin>
	
		<colors>
			<color name="white" 	value="#ffffff" />
			<color name="black" 	value="#000000" />
			<color name="dark"  	value="#294a6b" />
			
			<color name="red" 		value="#ff0000" />
			<color name="green" 	value="#00ff00" />
			<color name="blue" 		value="#0000ff" />
			<color name="yellow"	value="#c0c000" />
		</colors>
		<windowstyle type="skinned">
			<color name="Background" color="#4075a7" />
			<color name="LabelForeground" color="#ffffff" />
			<color name="ListboxBackground" color="#4075a7" />
			<color name="ListboxForeground" color="#ffffff" />
			<color name="ListboxSelectedBackground" color="#404080" />
			<color name="ListboxSelectedForeground" color="#ffffff" />
			<color name="ListboxMarkedBackground" color="#ff0000" />
			<color name="ListboxMarkedForeground" color="#ffffff" />
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
		</windowstyle> """ """
		<screen name="Menu" position="300,100" size="300,300" title="real main menu">
<!--			<widget name="okbutton" position="10,190" size="280,50" font="Arial;20" valign="center" halign="center" />-->
			<widget name="title" position="10,10" size="280,20" />
			<widget name="menu" position="10,30" size="280,200" />
			
		</screen>
		<screen name="ScartLoopThrough" position="0,0" size="720,576">
		</screen>
		<screen name="ConfigMenu" position="300,100" size="300,300" title="real main menu">
			<widget name="txt_var_1" position="20,20" size="100,20" />
			<widget name="btn_var_1" position="110,20" size="200,20" />
			<widget name="txt_var_2" position="20,60" size="100,20" />
			<widget name="btn_var_2" position="110,60" size="200,20" />
		</screen>
		<screen name="configOSD" position="140,125" size="460,350" title="OSD Settings">
			<widget name="okbutton" position="20,245" size="205,40" />
			<widget name="txt_alpha" position="20,20" size="110,20" />
			<widget name="sld_alpha" position="150,20" size="290,20" />
			<widget name="txt_brightness" position="20,60" size="120,20" />
			<widget name="sld_brightness" position="150,20" size="290,20" />
			<widget name="txt_gamma" position="20,100" size="120,20" />
			<widget name="sld_gamma" position="150,100" size="290,20" />
		</screen>
		<screen name="configTest" position="300,100" size="300,300" title="config menu">
			<widget name="config" position="10,30" size="280,140" />
		</screen>
		<screen name="TimerEditList" position="160,100" size="420,430" title="Timer Editor">
			<widget name="timerlist" position="10,30" size="400,300" />
		</screen>
		<screen name="clockDisplay" position="300,100" size="300,300">
			<widget name="okbutton" position="10,10" size="280,40" />
			<widget name="title" position="10,120" size="280,50" />
			<widget name="theClock" position="10,60" size="280,50" />
		</screen>
		<screen name="InfoBar" flags="wfNoBorder" position="0,380" size="720,148" title="InfoBar">
			<ePixmap position="0,0" size="720,148" pixmap="data/info-bg.png" />
			
			<widget name="ServiceName" position="69,25" size="427,26" valign="center" font="Arial;22" backgroundColor="#101258" />
			<widget name="CurrentTime" position="575,10" size="80,30" backgroundColor="dark" font="Arial;19" />
			<widget name="Volume" position="575,45" size="100,5" backgroundColor="dark" />
			<widget name="Event_Now" position="273,68" size="282,30" font="Arial;22" backgroundColor="dark" />
			<widget name="Event_Next" position="273,98" size="282,30" font="Arial;22" backgroundColor="dark" />
			<widget name="Event_Now_Duration" position="555,68" size="70,26" font="Arial;22" backgroundColor="dark" />
			<widget name="Event_Next_Duration" position="555,98" size="70,26" font="Arial;22" backgroundColor="dark" />
<!--			<eLabel position="70,0" size="300,30" text=".oO skin Oo." font="Arial;20" /> -->
		</screen>
 		<screen name="ChannelSelection" position="90,100" size="560,420" title="Channel Selection">
			<widget name="list" position="0,50" size="560,340" />
<!--			<widget name="okbutton" position="340,50" size="140,30" />-->
			<widget name="key_red" position="0,0" size="140,40" backgroundColor="red" />
			<widget name="key_green" position="140,0" size="140,40" backgroundColor="green" />
			<widget name="key_yellow" position="280,0" size="140,40" backgroundColor="yellow" />
			<widget name="key_blue" position="420,0" size="140,40" backgroundColor="blue" />
		</screen>
 		<screen name="MovieSelection" position="150,100" size="400,420" title="Select-a-movie">
			<widget name="list" position="0,50" size="400,300" />
		</screen>
		<screen name="ServiceScan" position="150,100" size="300,200" title="Service Scan">
			<widget name="scan_progress" position="10,10" size="280,50" />
			<widget name="scan_state" position="10,60" size="280,30" />
		</screen>
		<screen name="TimerEdit" position="70,100" size="590,335" title="Timer Edit">
			<widget name="description" position="10,10" size="580,40" font="Arial;25" />
			<widget name="lbegin" position="405,102" size="103,30" font="Arial;25" foregroundColor="red" />
			<widget name="lend" position="405,158" size="103,30" font="Arial;25" foregroundColor="green" />
			<widget name="begin" position="508,105" size="72,35" font="Arial;25" />
			<widget name="end" position="508,150" size="72,35" font="Arial;25" />
			<widget name="apply" position="10,240" size="250,35" />
		</screen>
		<screen name="MessageBox" position="0,300" size="720,10" title="Message">
			<widget name="text" position="0,0" size="500,0" font="Arial;25" />
			<applet type="onLayoutFinish">
# this should be factored out into some helper code, but currently demonstrated applets.
from enigma import eSize, ePoint

orgwidth = self.instance.size().width()
orgpos = self.instance.position()
textsize = self["text"].getSize()

# y size still must be fixed in font stuff...
textsize = (textsize[0], textsize[1] + 20)
wsize = (textsize[0] + 20, textsize[1] + 20)

# resize 
self.instance.resize(eSize(*wsize))

# resize label
self["text"].instance.resize(eSize(*textsize))

# center window
newwidth = wsize[0]
self.instance.move(ePoint(orgpos.x() + (orgwidth - newwidth)/2, orgpos.y()))
			</applet>
		</screen>
	</skin>""")

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
	
	assert myscreen != None, "no skin for screen '" + name + "' found!"

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
		print screen.additionalWidgets
		screen.additionalWidgets.append(w)
