from Screen import Screen
from Components.Button import Button
from Components.ServiceList import ServiceList
from Components.ActionMap import ActionMap

from enigma import eServiceReference

class ChannelSelection(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)

		self["key_red"] = Button("red")
		self["key_green"] = Button("green")
		self["key_yellow"] = Button("yellow")
		self["key_blue"] = Button("blue")
		
		self["list"] = ServiceList()
		self["list"].setRoot(eServiceReference("""1:0:1:0:0:0:0:0:0:0:(provider=="ARD") && (type == 1)"""))
		
		#self["okbutton"] = Button("ok", [self.channelSelected])
		
		class ChannelActionMap(ActionMap):
			def action(self, contexts, action):
				if action[:7] == "bouquet":
					print "setting root to " + action[8:]
					self.csel["list"].setRoot(eServiceReference("1:0:1:0:0:0:0:0:0:0:" + action[8:]))
				else:
					ActionMap.action(self, contexts, action)

		self["actions"] = ChannelActionMap(["ChannelSelectActions", "OkCancelActions"], 
			{
				"cancel": self.close,
				"ok": self.channelSelected,
				"mark": self.doMark
			})
		self["actions"].csel = self

	def doMark(self):
		ref = self["list"].getCurrent()
		if self["list"].isMarked(ref):
			self["list"].removeMarked(ref)
		else:
			self["list"].addMarked(ref)
			
	def channelSelected(self):
		self.session.nav.playService(self["list"].getCurrent())
		self.close()

	#called from infoBar
	def zap(self):
		self.session.nav.playService(self["list"].getCurrent())

	def moveUp(self):
		self["list"].moveUp()

	def moveDown(self):
		self["list"].moveDown()

