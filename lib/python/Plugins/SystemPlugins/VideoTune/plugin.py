from Plugins.Plugin import PluginDescriptor

def videoFinetuneMain(session, **kwargs):
	from VideoFinetune import VideoFinetune
	session.open(VideoFinetune)

def videoFinetuneWizard(*args, **kwargs):
	# the way the video wizard tells this plugin that the "testcard" should be displayed is not so nice yet.
	show_testcard = False
	try:
		from Components.config import config
		show_testcard = config.misc.showtestcard.value
	except KeyError:
		print "not showing fine-tuning wizard, config variable doesn't exist"
	if show_testcard:
		from VideoFinetune import VideoFinetune
		config.misc.showtestcard.value = False
		return VideoFinetune(*args, **kwargs)
	else:
		print "showtestcard is false"
		from Screens.Screen import Screen
		class Dummy(Screen):
			skin = "<screen></screen>"
			def __init__(self, session):
				Screen.__init__(self, session)
				self.close()
		return Dummy(*args, **kwargs)

def startSetup(menuid):
	if menuid != "system": 
		return [ ]

	return [(_("Video Fine-Tuning"), videoFinetuneMain, "video_finetune", None)]

def Plugins(**kwargs):
	return [
		PluginDescriptor(name=_("Video Fine-Tuning"), description=_("fine-tune your display"), where = PluginDescriptor.WHERE_MENU, needsRestart = False, fnc=startSetup),
		PluginDescriptor(name=_("Video Fine-Tuning Wizard"), where = PluginDescriptor.WHERE_WIZARD, needsRestart = False, fnc=(1, videoFinetuneWizard))
	]
