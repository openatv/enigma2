from Screen import Screen
from Components.ActionMap import ActionMap

import xml.dom.minidom
from xml.dom import EMPTY_NAMESPACE
from skin import elementsWithTag

from Tools import XMLTools

setupdom = xml.dom.minidom.parseString(
	"""
	<setup key="rc" title="RC Menu">
		<item text="Repeat Rate">config.inputDevices.repeat</item>
		<item text="Delay Rate">config.inputDevices.delay</item>
	</setup>
	""")

def getValbyAttr(x, attr):
	for p in range(x.attributes.length):
		a = x.attributes.item(p)
		attrib = str(a.name)
		value = str(a.value)
		if attrib == attr:
			return value
	
	return ""

class Setup(Screen):

	def createDialog(self, childNode):
		print "createDialog"
		for x in childNode:
			if x.nodeType != xml.dom.minidom.Element.nodeType:
				continue
			elif x.tagName == 'item':
				ItemText = getValbyAttr(x, "text")
				b = XMLTools.mergeText(x.childNodes);
				print "item " + ItemText + " " + b
				#add to configlist
				
	def __init__(self, session, setup):
		Screen.__init__(self, session)

		print "request setup for " + setup
		
		entries = setupdom.childNodes
		
		for x in entries:             #walk through the actual nodelist
			if x.nodeType != xml.dom.minidom.Element.nodeType:
				continue
			elif x.tagName == 'setup':
				ItemText = getValbyAttr(x, "key")
				if ItemText != setup:
					continue
				self.createDialog(x.childNodes);
				

		self["actions"] = ActionMap(["OkCancelActions"], 
			{
				#"ok": self.inc,
				"cancel": self.close
			})
