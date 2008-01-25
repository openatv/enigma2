from Plugins.Plugin import PluginDescriptor

def videoFinetuneMain(session, **kwargs):
	from VideoFinetune import VideoFinetune
	session.open(VideoFinetune)

def startSetup(menuid):
	if menuid != "system": 
		return [ ]

	return [(("Video Finetune"), videoFinetuneMain, "video_finetune", None)]

def Plugins(**kwargs):
	return [
		PluginDescriptor(name=("Video Finetune"), description=("Fine-tune your video"), where = PluginDescriptor.WHERE_MENU, fnc=startSetup) 
	]
