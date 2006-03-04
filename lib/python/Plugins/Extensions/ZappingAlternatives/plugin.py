from enigma import *
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.Input import Input
from Components.GUIComponent import *
from Components.Pixmap import Pixmap
from Components.MenuList import MenuList
from Components.FileList import FileEntryComponent, FileList
from Navigation import Navigation
import NavigationInstance
from Screens.ChannelSelection import SimpleChannelSelection
from ServiceReference import ServiceReference
from Plugins.Plugin import PluginDescriptor
from Tools.Directories import resolveFilename, SCOPE_CONFIG
import xml.dom.minidom
from Tools.XMLTools import elementsWithTag

import os

alternatives = {}

def addAlternative(service1, service2):
	if not alternatives.has_key(service1):
		alternatives[service1] = []
	alternatives[service1].append(service2)
	if not alternatives.has_key(service2):
		alternatives[service2] = []
	alternatives[service2].append(service1)

def removeAlternative(service1, service2):
	alternatives[service1].remove(service2)
	alternatives[service2].remove(service1)
	if len(alternatives[service1]) == 0:
		del alternatives[service1]
	if len(alternatives[service2]) == 0:
		del alternatives[service2]
		
def loadAlternatives():
	doc = xml.dom.minidom.parse(self.filename)
	
	root = doc.childNodes[0]
	for service in elementsWithTag(root.childNodes, 'service'):
		newService = str(service.getAttribute('ref'))
		for alternative in elementsWithTag(service.childNodes, 'alternative'):
			newAlternative = str(alternative.getAttribute('ref'))
			addAlternative(newService, newAlternative)

def sortKey(x):
	return str.lower(ServiceReference(x).getServiceName().strip())
			
class AlternativeZapping(Screen):
	skin = """
		<screen position="100,100" size="560,400" title="Services alternatives setup..." >
			<widget name="red" position="0,0" size="140,40" backgroundColor="red" halign="center" valign="center" font="Regular;21" />
			<widget name="green" position="140,0" size="140,40" backgroundColor="green" halign="center" valign="center" font="Regular;21" />
			<widget name="yellow" position="280,0" size="140,40" backgroundColor="yellow" halign="center" valign="center" font="Regular;21" />
			<widget name="blue" position="420,0" size="140,40" backgroundColor="blue" halign="center" valign="center" font="Regular;21" />
			<widget name="serviceslist" position="0,40" size="280,360" />
			<widget name="alternativeslist" position="280,40" size="280,360" selectionDisabled="1" />
		</screen>"""
	def __init__(self, session):
		self.skin = AlternativeZapping.skin
		Screen.__init__(self, session)

		self.filename = resolveFilename(SCOPE_CONFIG, "alternatives.xml")
		
		self.red = Label("")
		self["red"] = self.red
		self.green = Label(_("Add service"))
		self["green"] = self.green
		self.yellow = Label("")
		self["yellow"] = self.yellow
		self.blue = Label("")
		self["blue"] = self.blue
		
		self.alternatives = {}
		
		self.serviceslist = []
		self.alternativeslist = []
		
		try:
			self.loadAlternatives()
		except:
			pass
		self["serviceslist"] = MenuList(self.serviceslist)
		self["alternativeslist"] = MenuList(self.alternativeslist)

		self.onShown.append(self.updateServices)
		self.onShown.append(self.updateAlternatives)

		self["actions"] = ActionMap(["DirectionActions", "OkCancelActions", "ColorActions"],
		{
			"ok": self.go,
			"cancel": self.go,
			"up": self.up,
			"down": self.down,
			"left": self.left,
			"right": self.right,
			"red": self.redKey,
			"green": self.greenKey,
			"yellow": self.yellowKey,
			"blue": self.blueKey,
		}, -1)
		
	def saveAlternatives(self):
		doc = xml.dom.minidom.Document()
		root_element = doc.createElement('alternatives')
		doc.appendChild(root_element)
		root_element.appendChild(doc.createTextNode("\n"))
		
		for alternative in self.alternatives.keys():
			t = doc.createTextNode("\t")
			root_element.appendChild(t)
			t = doc.createElement('service')
			t.setAttribute("ref", alternative)
			root_element.appendChild(t)
			t.appendChild(doc.createTextNode("\n"))
			for x in self.alternatives[alternative]:
				t.appendChild(doc.createTextNode("\t\t"))
				l = doc.createElement('alternative')
				l.setAttribute("ref", str(x))
				t.appendChild(l)
				t.appendChild(doc.createTextNode("\n"))
			t.appendChild(doc.createTextNode("\t"))
			root_element.appendChild(t)
			t = doc.createTextNode("\n")
			root_element.appendChild(t)
		file = open(self.filename, "w")
		doc.writexml(file)
		file.write("\n")
		file.close()
	
	def loadAlternatives(self):
		self.alternatives = {}
		alternatives = {}
		doc = xml.dom.minidom.parse(self.filename)
		
		root = doc.childNodes[0]
		for service in elementsWithTag(root.childNodes, 'service'):
			newService = str(service.getAttribute('ref'))
			if not self.alternatives.has_key(newService):
				self.alternatives[newService] = []
			for alternative in elementsWithTag(service.childNodes, 'alternative'):
				newAlternative = str(alternative.getAttribute('ref'))
				self.alternatives[newService].append(newAlternative)
				addAlternative(newService, newAlternative)
		
	def go(self):
		self.saveAlternatives()
		self.close()
	
	def up(self):
		self["serviceslist"].instance.moveSelection(self["serviceslist"].instance.moveUp)
		self.updateAlternatives()
		
	def down(self):
		self["serviceslist"].instance.moveSelection(self["serviceslist"].instance.moveDown)
		self.updateAlternatives()
	
	def left(self):
		pass
	
	def right(self):
		pass
	
	def redKey(self):
		for x in self.alternatives[self["serviceslist"].getCurrent()[1]]:
			removeAlternative(self["serviceslist"].getCurrent()[1], x)
		if len(self.serviceslist) > 0:
			del self.alternatives[self["serviceslist"].getCurrent()[1]]
		self.updateServices()
		self.updateAlternatives()
	
	def finishedAlternativeSelection(self, args):
		self.alternatives[self["serviceslist"].getCurrent()[1]].append(str(ServiceReference(args)))
		addAlternative(self["serviceslist"].getCurrent()[1], str(ServiceReference(args)))
		self.updateAlternatives()
	
	def updateServices(self):
		self.serviceslist = []
		keys = self.alternatives.keys()
		keys.sort(key = sortKey)
		for x in keys:
			self.serviceslist.append((ServiceReference(x).getServiceName(), x))
			
		self["serviceslist"].setList(self.serviceslist)
		if len(self.serviceslist) > 0:
			self.yellow.setText(_("Add alternative"))
			self.red.setText(_("Remove service"))
		else:
			self.yellow.setText("")
			self.red.setText("")
	
	def selectService(self, ref):
		count = 0
		for x in self["serviceslist"].list:
			if x[1] == ref:
				self["serviceslist"].instance.moveSelectionTo(count)
				return
			count += 1
			
			
	def updateAlternatives(self):
		self.alternativeslist = []
	
		if len(self.serviceslist) > 0:
			alternativelist = self.alternatives[self["serviceslist"].getCurrent()[1]]

			for x in alternativelist:
				self.alternativeslist.append((ServiceReference(x).getServiceName(), x))
			
		self["alternativeslist"].setList(self.alternativeslist)
			
	def greenKey(self):
		self.session.openWithCallback(self.finishedChannelSelection, SimpleChannelSelection, _("Select reference service"))

	def finishedChannelSelection(self, args):
		serviceString = str(ServiceReference(args))
		if not self.alternatives.has_key(serviceString):
			self.alternatives[serviceString] = []
		self.updateServices()
		self.updateAlternatives()
		self.selectService(serviceString)

	def yellowKey(self):
		if len(self.serviceslist) > 0:
			self.session.openWithCallback(self.finishedAlternativeSelection, SimpleChannelSelection, _("Select alternative service"))
	
	def blueKey(self):
		pass


oldPlayService = NavigationInstance.instance.playService

def playService(self, ref):
	if not oldPlayService(ref):
		if alternatives.has_key(str(ServiceReference(ref))):
			for x in alternatives[str(ServiceReference(ref))]:
				if oldPlayService(ServiceReference(x).ref):
					return 1
		return 0
	return 1

def autostart(reason):
	if reason == 0:
		try:
			loadAlternatives()
		except:
			pass
		NavigationInstance.instance.playService = type(NavigationInstance.instance.playService)(playService, NavigationInstance, Navigation)

def AlternativeZappingSetup(session):
	session.open(AlternativeZapping)

def Plugins():
 	return [PluginDescriptor(where = PluginDescriptor.WHERE_AUTOSTART, fnc = autostart),
 			PluginDescriptor(name="Alternative services setup" , description="Defines alternatives for services.", where = PluginDescriptor.WHERE_PLUGINMENU, fnc=AlternativeZappingSetup)]
