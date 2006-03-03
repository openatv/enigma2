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

import os

alternatives = {}

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
		
		self.red = Label("")
		self["red"] = self.red
		self.green = Label(_("Add service"))
		self["green"] = self.green
		self.yellow = Label("")
		self["yellow"] = self.yellow
		self.blue = Label("")
		self["blue"] = self.blue
		
		self.serviceslist = []
		self["serviceslist"] = MenuList(self.serviceslist)

		self.alternativeslist = []
		self["alternativeslist"] = MenuList(self.alternativeslist)
		
		self.onShown.append(self.updateServices)
		self.onShown.append(self.updateAlternatives)

		self["actions"] = ActionMap(["DirectionActions", "OkCancelActions", "ColorActions"],
		{
			"ok": self.go,
			"cancel": self.close,
			"up": self.up,
			"down": self.down,
			"left": self.left,
			"right": self.right,
			"red": self.redKey,
			"green": self.greenKey,
			"yellow": self.yellowKey,
			"blue": self.blueKey,
		}, -1)
		
	def go(self):
		pass
	
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
		if len(self.serviceslist) > 0:
			del alternatives[self["serviceslist"].getCurrent()[1]]
		self.updateServices()
		self.updateAlternatives()
	
	def finishedAlternativeSelection(self, args):
		alternatives[self["serviceslist"].getCurrent()[1]].append(str(ServiceReference(args)))
		self.updateAlternatives()
	
	def updateServices(self):
		self.serviceslist = []
		
		for x in alternatives.keys():
			self.serviceslist.append((ServiceReference(x).getServiceName(), x))
			
		self["serviceslist"].l.setList(self.serviceslist)
		if len(self.serviceslist) > 0:
			self.yellow.setText(_("Add alternative"))
			self.red.setText(_("Remove service"))
		else:
			self.yellow.setText("")
			self.red.setText("")
			
	def updateAlternatives(self):
		self.alternativeslist = []
	
		if len(self.serviceslist) > 0:
			alternativelist = alternatives[self["serviceslist"].getCurrent()[1]]

			for x in alternativelist:
				self.alternativeslist.append((ServiceReference(x).getServiceName(), x))
			
		self["alternativeslist"].l.setList(self.alternativeslist)
			
	def greenKey(self):
		self.session.openWithCallback(self.finishedChannelSelection, SimpleChannelSelection, _("Select reference service"))

	def finishedChannelSelection(self, args):
		if alternatives.has_key(str(ServiceReference(args))):
			pass
		else:
			alternatives[str(ServiceReference(args))] = []
		print alternatives
		self.updateServices()
		#oldref = self.timer.service_ref
		#try:
			#self.timer.service_ref = ServiceReference(args)
			#config.timerentry.service.vals = (str(self.timer.service_ref.getServiceName()),)
			#self["config"].invalidate(config.timerentry.service)
		#except:
		#	print "you pressed cancel"
			#self.timer.service_ref = oldref
	
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
		NavigationInstance.instance.playService = type(NavigationInstance.instance.playService)(playService, NavigationInstance, Navigation)

def AlternativeZappingSetup(session):
	session.open(AlternativeZapping)

def Plugins():
 	return [PluginDescriptor(where = PluginDescriptor.WHERE_AUTOSTART, fnc = autostart),
 			PluginDescriptor(name="Alternative services setup" , description="Defines alternatives for services.", where = PluginDescriptor.WHERE_PLUGINMENU, fnc=AlternativeZappingSetup)]
