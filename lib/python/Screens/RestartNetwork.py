from Screens.Processing import Processing
from Screens.ParentalControlSetup import ProtectedScreen
from Screens.Screen import Screen
from Tools.ServiceAction import ServiceAction


class RestartNetworkNew:
	@staticmethod
	def start(callback=None):
		Processing.instance.setDescription(_("Please wait while your network is restarting..."))
		Processing.instance.showProgress(endless=True)

		def _done(exitCode=None):
			Processing.instance.hideProgress()
			if callback and callable(callback):
				callback()

		ServiceAction.netrestart(_done, timeout=10000)


class RestartNetwork(Screen, ProtectedScreen):
	protectionSections = ("configuration",)

	skin = """
		<screen name="RestartNetwork" position="center,center" size="0,0" flags="wfNoBorder" />"""

	def __init__(self, session):
		Screen.__init__(self, session)
		ProtectedScreen.__init__(self)
		self.skinName = "DUMMY"
		self.onLayoutFinish.append(self.protectedCallback(self._restart))

	def _restart(self):
		RestartNetworkNew.start(callback=self.close)
