from Components.Label import Label
from Components.Network import iNetwork
from Components.Sources.StaticText import StaticText
from Screens.Screen import Screen
from Screens.Processing import Processing
from Tools.ServiceHelper import ServiceHelper


class RestartNetworkNew:
	@staticmethod
	def start(callback):
		helper = ServiceHelper("netrestarter")
		Processing.instance.setDescription(_("Please wait while your network is restarting..."))
		Processing.instance.showProgress(endless=True)

		def restartCallback():
			def getInterfacesCallback(data):
				Processing.instance.hideProgress()
				if callback and callable(callback):
					callback()
			iNetwork.getInterfaces(getInterfacesCallback)
		helper.restart(callback=restartCallback)


class RestartNetwork(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		self.setTitle(_("Restart Network Adapter"))
		self.helper = ServiceHelper("netrestarter")
		skin = """
			<screen name="RestartNetwork" position="center,center" size="600,100" title="Restart Network Adapter" resolution="1280,720">
			<widget name="label" position="10,30" size="500,50" halign="center" font="Regular;20" transparent="1" foregroundColor="white" />
			</screen> """
		self.skin = skin
		text = _("Please wait while your network is restarting...")
		self["label"] = Label(text)
		self["summary_description"] = StaticText(text)
		self.onLayoutFinish.append(self.restartLan)

	def restartLan(self):
		iNetwork.restartNetwork(self.restartLanDataAvail)

	def restartLanDataAvail(self, data):
		if data is True:
			iNetwork.getInterfaces(self.getInterfacesDataAvail)

	def getInterfacesDataAvail(self, data):
		self.close()
