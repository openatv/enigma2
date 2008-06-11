from Plugins.Plugin import PluginDescriptor

def main(session, service, **kwargs):
	import TitleList
	import DVDProject
	project = DVDProject.DVDProject()
	project.addService(service)
	session.open(TitleList.TitleList, project)

def Plugins(**kwargs):
 	return PluginDescriptor(name="DVD Tool", description=_("Burn To DVD..."), where = PluginDescriptor.WHERE_MOVIELIST, fnc=main)
