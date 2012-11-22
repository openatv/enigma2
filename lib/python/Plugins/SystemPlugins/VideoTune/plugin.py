from Plugins.Plugin import PluginDescriptor

def videoFinetuneMain(session, **kwargs):
	from VideoFinetune import VideoFinetune
	session.open(VideoFinetune)

def startSetup(menuid):
	if menuid != "system": 
		return [ ]

	return [(_("Video fine tuning"), videoFinetuneMain, "video_finetune", None)]

def Plugins(**kwargs):
	return PluginDescriptor(name=_("Video fine tuning"), description=_("fine-tune your display"), where = PluginDescriptor.WHERE_MENU, needsRestart = False, fnc=startSetup)
