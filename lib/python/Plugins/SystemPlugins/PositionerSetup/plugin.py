from enigma import eTimer, eDVBSatelliteEquipmentControl
from Screens.Screen import Screen
from Plugins.Plugin import PluginDescriptor

from Components.Label import Label
from Components.ConfigList import ConfigList
from Components.ActionMap import ActionMap
from Components.config import config, ConfigSubsection, configElement_nonSave, configNothing, getConfigListEntry, configSelection

class PositionerSetup(Screen):
	skin = """
		<screen position="100,100" size="560,400" title="Positioner setup..." >
			<widget name="red" position="0,100" size="140,80" backgroundColor="red" halign="center" valign="center" font="Regular;21" />
			<widget name="green" position="140,100" size="140,80" backgroundColor="green" halign="center" valign="center" font="Regular;21" />
			<widget name="yellow" position="280,100" size="140,80" backgroundColor="yellow" halign="center" valign="center" font="Regular;21" />
			<widget name="blue" position="420,100" size="140,80" backgroundColor="blue" halign="center" valign="center" font="Regular;21" />
			<widget name="status" position="0,200" size="550,40" font="Regular;15" />
			<widget name="list" position="100,0" size="350,100" />
		</screen>"""
	def __init__(self, session):
		self.skin = PositionerSetup.skin
		Screen.__init__(self, session)
		
		self.createConfig()
		
		self.status = Label("")
		self["status"] = self.status
		
		self.red = Label("")
		self["red"] = self.red
		self.green = Label("")
		self["green"] = self.green
		self.yellow = Label("")
		self["yellow"] = self.yellow
		self.blue = Label("")
		self["blue"] = self.blue

		self.list = []
		self["list"] = ConfigList(self.list)
		self.createSetup()

		self["actions"] = ActionMap(["DirectionActions", "OkCancelActions", "ColorActions"],
		{
			"ok": self.go,
			"cancel": self.close,
			"up": self.up,
			"down": self.down,
			"left": self.left,
			"right": self.right,
			"red": self.redKey,
			"green": self.greenKey,
			"yellow": self.yellowKey,
			"blue": self.blueKey,
		}, -1)
		
		self.updateColors("move")
		
		self.statusTimer = eTimer()
		self.statusTimer.timeout.get().append(self.updateStatus)
		self.statusTimer.start(500, False)
		
	def createConfig(self):
		config.positioner = ConfigSubsection()
		config.positioner.move = configElement_nonSave("move", configNothing, 0, None)
		config.positioner.limits = configElement_nonSave("limits", configNothing, 0, None)
		config.positioner.storage = configElement_nonSave("storage", configSelection, 0, ("1", "2", "3"))
	
	def createSetup(self):
		self.list.append(getConfigListEntry(_("Positioner movement"), config.positioner.move))
		self.list.append(getConfigListEntry(_("Set limits"), config.positioner.limits))
		self.list.append(getConfigListEntry(_("Positioner storage"), config.positioner.storage))
		
		self["list"].l.setList(self.list)
		
	def go(self):
		pass
	
	def up(self):
		self["list"].instance.moveSelection(self["list"].instance.moveUp)
		self.updateColors(self["list"].getCurrent()[1].parent.configPath)
	
	def down(self):
		self["list"].instance.moveSelection(self["list"].instance.moveDown)
		self.updateColors(self["list"].getCurrent()[1].parent.configPath)
	
	def left(self):
		self["list"].handleKey(config.key["prevElement"])
	
	def right(self):
		self["list"].handleKey(config.key["nextElement"])
	
	def updateColors(self, entry):
		if entry == "move":
			self.red.setText(_("Move east"))
			self.green.setText(_("Step east"))
			self.yellow.setText(_("Step west"))
			self.blue.setText(_("Move west"))
		elif entry == "limits":
			self.red.setText(_("Limits off"))
			self.green.setText(_("Limit east"))
			self.yellow.setText(_("Limit west"))
			self.blue.setText("")
		elif entry == "storage":
			self.red.setText(_("Apply satellite"))
			self.green.setText(_("Store position"))
			self.yellow.setText(_("Goto position"))
			self.blue.setText("")
		else:
			self.red.setText("")
			self.green.setText("")
			self.yellow.setText("")
			self.blue.setText("")
	
	def redKey(self):
		print "red"
	
	def greenKey(self):
		pass
	
	def yellowKey(self):
		pass
	
	def blueKey(self):
		pass

	def updateStatus(self):
		if eDVBSatelliteEquipmentControl.getInstance().isRotorMoving():
			self.status.setText("moving...")
		else:
			self.status.setText("not moving")
		
def PositionerMain(session, **kwargs):
	session.open(PositionerSetup)

def Plugins(**kwargs):
	return PluginDescriptor(name="Positioner setup", description="Setup your positioner", where = PluginDescriptor.WHERE_PLUGINMENU, fnc=PositionerMain)
