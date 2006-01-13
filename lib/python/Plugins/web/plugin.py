from enigma import *

from twisted.internet import reactor
from twisted.web2 import server, http, static

def autostart():
	print "Web startup"
	# For example, serve the /tmp directory
	toplevel = static.File("/tmp")
	site = server.Site(toplevel)
	
	reactor.listenTCP(8080, http.HTTPFactory(site))

def autoend():
	pass

def getPicturePaths():
	return []

def getPlugins():
	return []
	
def getMenuRegistrationList():
	return []
