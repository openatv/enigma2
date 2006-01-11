from enigma import *
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Components.ActionMap import ActionMap
from Components.Label import Label

import os

def getPlugins():
	return [("Tuxbox-Plugin1", "function", "main", 0),
			("Tuxbox-Plugin2", "function", "main", 1)]

def main(session, args):
	print "Running plugin with number", args