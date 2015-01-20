from Plugins.Plugin import PluginDescriptor

def videoFinetuneMain(session, **kwargs):
	from VideoFinetune import VideoFinetune
	session.open(VideoFinetune)

def startSetup(menuid):
	if menuid != "video_menu":
		return [ ]

	return [(_("Testscreens"), videoFinetuneMain, "video_finetune", 10)]

def Plugins(**kwargs):
	return PluginDescriptor(name=_("Testscreens"), description=_("Testscreens that are helpfull to fine-tune your display"), where = PluginDescriptor.WHERE_MENU, needsRestart = False, fnc=startSetup)
