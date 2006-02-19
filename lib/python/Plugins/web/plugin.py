from twisted.internet import reactor
from twisted.web2 import server, http, static
from Plugins.Plugin import PluginDescriptor

def startWebserver():
	toplevel = static.File("/hdd")
	site = server.Site(toplevel)
	
	reactor.listenTCP(80, http.HTTPFactory(site))

def autostart(reason):
	if reason == 0:
		try:
			startWebserver()
		except ImportError:
			print "twisted not available, not starting web services"

def Plugins():
	return PluginDescriptor(where = PluginDescriptor.WHERE_AUTOSTART, fnc = autostart)
