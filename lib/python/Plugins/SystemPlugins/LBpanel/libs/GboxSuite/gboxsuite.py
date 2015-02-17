# 2014.10.12 15:51:23 CEST
from Imports import *
from GboxSuiteMainMenu import *

def GboxSuiteMain(session, **kwargs):
    session.open(GboxSuiteMainMenu)



def Plugins(**kwargs):
    return [PluginDescriptor(name='Gbox Suite\xb2', where=PluginDescriptor.WHERE_EXTENSIONSMENU, fnc=GboxSuiteMain), PluginDescriptor(name='Gbox Suite\xb2', description='Gbox Suite\xb2', icon='suite.png', where=PluginDescriptor.WHERE_PLUGINMENU, fnc=GboxSuiteMain)]



