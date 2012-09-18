from Plugins.Plugin import PluginDescriptor

def videoFinetuneMain(session, **kwargs):
	from VideoFinetune import VideoFinetune
	session.open(VideoFinetune)

def startSetup(menuid):
	if menuid != "system": 
		return [ ]

	return [(_("Video Fine-Tuning"), videoFinetuneMain, "video_finetune", None)]

def Plugins(**kwargs):
	return PluginDescriptor(name=_("Video Fine-Tuning"), description=_("fine-tune your display"), where = PluginDescriptor.WHERE_MENU, needsRestart = False, fnc=startSetup)
