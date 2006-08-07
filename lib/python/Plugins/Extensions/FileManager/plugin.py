from enigma import *
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Components.ActionMap import NumberActionMap
from Components.Label import Label
from Components.Input import Input
from Components.GUIComponent import *
from Components.Pixmap import Pixmap
from Components.FileList import FileEntryComponent, FileList
from Plugins.Plugin import PluginDescriptor

import os

class FileManager(Screen):
	skin = """
		<screen position="100,100" size="550,400" title="Test" >
			<!--widget name="text" position="0,0" size="550,25" font="Regular;20" /-->
			<widget name="list" position="10,0" size="190,250" scrollbarMode="showOnDemand" />
			<widget name="pixmap" position="200,0" size="190,250" alphatest="on" />
		</screen>"""
	def __init__(self, session, args = None):
		self.skin = FileManager.skin
		Screen.__init__(self, session)

		self["list"] = FileList("/", matchingPattern = "^.*\.(png|avi|mp3|mpeg|ts)", useServiceRef = True)
		self["pixmap"] = Pixmap()
		
		#self["text"] = Input("1234", maxSize=True, type=Input.NUMBER)
				
		self["actions"] = NumberActionMap(["WizardActions", "InputActions"],
		{
			"ok": self.ok,
			"back": self.close,
#			"left": self.keyLeft,
#			"right": self.keyRight,
			"1": self.keyNumberGlobal,
			"2": self.keyNumberGlobal,
			"3": self.keyNumberGlobal,
			"4": self.keyNumberGlobal,
			"5": self.keyNumberGlobal,
			"6": self.keyNumberGlobal,
			"7": self.keyNumberGlobal,
			"8": self.keyNumberGlobal,
			"9": self.keyNumberGlobal,
			"0": self.keyNumberGlobal
		}, -1)
		
	def keyLeft(self):
		self["text"].left()
	
	def keyRight(self):
		self["text"].right()
	
	def ok(self):
		
		if self["list"].canDescent(): # isDir
			self["list"].descent()
		else:
			self["pixmap"].instance.setPixmapFromFile(self["list"].getFilename())
	
	def keyNumberGlobal(self, number):
		print "pressed", number
		self["text"].number(number)

def main(session, **kwargs):
	session.open(FileManager)

def Plugins(**kwargs):
 	return PluginDescriptor(name="File-Manager", description="Let's you view/edit files in your Dreambox", where = PluginDescriptor.WHERE_PLUGINMENU, fnc=main)
