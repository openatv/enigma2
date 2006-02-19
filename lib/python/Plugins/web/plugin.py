from twisted.internet import reactor
from twisted.web2 import server, http, static

# this is currently not working
def startWebserver():
	print "Web startup"
	toplevel = static.File("/hdd")
	site = server.Site(toplevel)
	
	reactor.listenTCP(80, http.HTTPFactory(site))

def Plugins():
    return [ ]
