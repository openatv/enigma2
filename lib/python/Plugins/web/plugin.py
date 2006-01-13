from enigma import *

from twisted.internet import reactor
from twisted.web2 import server, http, static

def autostart():
	print "Web startup"
	toplevel = static.File("/hdd")
	site = server.Site(toplevel)
	
	reactor.listenTCP(80, http.HTTPFactory(site))

def autoend():
	pass

def getPicturePaths():
	return []

def getPlugins():
	return []
	
def getMenuRegistrationList():
	return []
