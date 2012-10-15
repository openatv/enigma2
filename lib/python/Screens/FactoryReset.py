from Screens.MessageBox import MessageBox

class FactoryReset(MessageBox):
	def __init__(self, session):
		MessageBox.__init__(self, session, _("When you do a factory reset, you will lose ALL your configuration data\n"
			"(including bouquets, services, satellite data ...)\n"
			"After completion of factory reset, your STB_BOX will restart automatically!\n\n"
			"Really do a factory reset?"), MessageBox.TYPE_YESNO, default = False)
		self.setTitle(_("Factory reset"))
		self.skinName = "MessageBox"
