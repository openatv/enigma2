from enigma import *
import xml.dom.minidom

def dump(x, i=0):
	print " " * i + str(x)
	try:
		for n in x.childNodes:
			dump(n, i + 1)
	except:
		None

dom = xml.dom.minidom.parseString(
	"<screen name=\"clockDialog\"> \
		<widget name=\"okbutton\" position=\"10,10\" size=\"280,40\" /> \
		<widget name=\"theClock\" position=\"10,60\" size=\"280,50\" /> \
		<widget name=\"title\" position=\"10,120\" size=\"280,50\" /> \
	</screen>")

def applyGUIskin(screen, skin, name):
	dump(dom[screen])
	screen.data["okbutton"]["instance"].move(ePoint(10, 10))
	screen.data["okbutton"]["instance"].resize(eSize(280, 40))

	screen.data["theClock"]["instance"].move(ePoint(10, 60))
	screen.data["theClock"]["instance"].resize(eSize(280, 50))

	screen.data["title"]["instance"].move(ePoint(10, 120))
	screen.data["title"]["instance"].resize(eSize(280, 50))
