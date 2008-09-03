from Plugins.Plugin import PluginDescriptor

def main(session, service, **kwargs):
	import TitleList
	import DVDProject
	#project = DVDProject.DVDProject()
	#project.addService(service)
	burner = session.open(TitleList.TitleList)
	burner.selectedSource(service)
	

def Plugins(**kwargs):
	return PluginDescriptor(name="DVD Tool", description=_("Burn to DVD..."), where = PluginDescriptor.WHERE_MOVIELIST, fnc=main)
