from Plugins.Plugin import PluginDescriptor

def main(session, **kwargs):
	import TitleList
	import DVDProject
	#project = DVDProject.DVDProject()
	#project.addService(service)
	return session.open(TitleList.TitleList)
	
def main_add(session, service, **kwargs):
	dvdburn = main(session, **kwargs)
	dvdburn.selectedSource(service)

def Plugins(**kwargs):
	return [PluginDescriptor(name="DVD Burn", description=_("Burn to DVD..."), where = PluginDescriptor.WHERE_MOVIELIST, fnc=main_add), 
		PluginDescriptor(name="DVD Burn", description=_("Burn to DVD..."), where = PluginDescriptor.WHERE_PLUGINMENU, fnc=main) ]
