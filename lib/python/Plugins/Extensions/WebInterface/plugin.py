from Plugins.Plugin import PluginDescriptor

sessions = [ ]

def startWebserver():
	from twisted.internet import reactor
	from twisted.web2 import server, http, static, resource, stream
	import webif

	class ScreenPage(resource.Resource):
		def render(self, req):
			global sessions
			if sessions == [ ]:
				return http.Response("please wait until enigma has booted")
			
			s = stream.ProducerStream()
			webif.renderPage(s, req, sessions[0])  # login?
			return http.Response(stream=s)

	class Toplevel(resource.Resource):
		addSlash = True
		
		def render(self, req):
			return 'Hello! you want probably go to <a href="/test">the test</a> instead.'

		child_test = ScreenPage() # "/test"
		child_hdd = static.File("/hdd")

	site = server.Site(Toplevel())
	
	reactor.listenTCP(80, http.HTTPFactory(site))

def autostart(reason, **kwargs):
	if "session" in kwargs:
		global sessions
		sessions.append(kwargs["session"])
		return

	if reason == 0:
		try:
			startWebserver()
		except ImportError:
			print "twisted not available, not starting web services"

def Plugins(**kwargs):
	return PluginDescriptor(where = [PluginDescriptor.WHERE_SESSIONSTART, PluginDescriptor.WHERE_AUTOSTART], fnc = autostart)
