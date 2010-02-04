from Screens.MessageBox import MessageBox

class ServiceStopScreen:
	def __init__(self):
		try:
			self.session
		except:
			print "[ServiceStopScreen] ERROR: no self.session set"

		self.oldref = None
		self.onClose.append(self.__onClose)
		
	def pipAvailable(self):
		# pip isn't available in every state of e2
		try:
			self.session.pipshown
			pipavailable = True
		except:
			pipavailable = False
		return pipavailable
		
	def stopService(self):		
		self.oldref = self.session.nav.getCurrentlyPlayingServiceReference()
		self.session.nav.stopService()
		if self.pipAvailable():
			if self.session.pipshown: # try to disable pip
				self.session.pipshown = False
				del self.session.pip
		
	def __onClose(self):
		self.session.nav.playService(self.oldref)
		
	def restoreService(self, msg = _("Zap back to previously tuned service?")):
		if self.oldref:
			self.session.openWithCallback(self.restartPrevService, MessageBox, msg, MessageBox.TYPE_YESNO)
		else:
			self.restartPrevService(False)
		
	def restartPrevService(self, yesno):
		if not yesno:
			self.oldref=None
		self.close()