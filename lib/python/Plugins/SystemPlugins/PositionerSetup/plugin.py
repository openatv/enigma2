from enigma import eTimer, eDVBSatelliteEquipmentControl, eDVBResourceManager, eDVBDiseqcCommand, eDVBResourceManagerPtr, iDVBChannelPtr, iDVBFrontendPtr, iDVBFrontend
from Screens.Screen import Screen
from Plugins.Plugin import PluginDescriptor

from Components.Label import Label
from Components.ConfigList import ConfigList
from Components.TunerInfo import TunerInfo
from Components.ActionMap import ActionMap
from Components.config import config, ConfigSubsection, configElement_nonSave, configNothing, getConfigListEntry, configSelection

class PositionerSetup(Screen):
	skin = """
		<screen position="100,100" size="560,400" title="Positioner setup..." >
			<widget name="list" position="100,0" size="350,120" />

			<widget name="red" position="0,120" size="140,80" backgroundColor="red" halign="center" valign="center" font="Regular;21" />
			<widget name="green" position="140,120" size="140,80" backgroundColor="green" halign="center" valign="center" font="Regular;21" />
			<widget name="yellow" position="280,120" size="140,80" backgroundColor="yellow" halign="center" valign="center" font="Regular;21" />
			<widget name="blue" position="420,120" size="140,80" backgroundColor="blue" halign="center" valign="center" font="Regular;21" />
			
			<widget name="snr" text="SNR:" position="0,220" size="60,22" font="Regular;21" />
			<widget name="agc" text="AGC:" position="0,245" size="60,22" font="Regular;21" />
			<widget name="ber" text="BER:" position="0,270" size="60,22" font="Regular;21" />
			<widget name="lock" text="Lock:" position="0,295" size="60,22" font="Regular;21" />
			<widget name="snr_percentage" position="220,220" size="60,22" font="Regular;21" />
			<widget name="agc_percentage" position="220,245" size="60,22" font="Regular;21" />
			<widget name="ber_value" position="220,270" size="60,22" font="Regular;21" />
			<widget name="lock_state" position="60,295" size="150,22" font="Regular;21" />
			<widget name="snr_bar" position="60,220" size="150,22" />
			<widget name="agc_bar" position="60,245" size="150,22" />
			<widget name="ber_bar" position="60,270" size="150,22" />
		</screen>"""
	def __init__(self, session):
		self.skin = PositionerSetup.skin
		Screen.__init__(self, session)
		
		self.session.nav.stopService()
		
		self.diseqc = Diseqc()
		
		#self.session.nav.stopService()
		
		self.createConfig()
		
		self.isMoving = False
		
		self.red = Label("")
		self["red"] = self.red
		self.green = Label("")
		self["green"] = self.green
		self.yellow = Label("")
		self["yellow"] = self.yellow
		self.blue = Label("")
		self["blue"] = self.blue
		
		self.feid = 0

		self.list = []
		self["list"] = ConfigList(self.list)
		self.createSetup()
		
		self["snr"] = Label()
		self["agc"] = Label()
		self["ber"] = Label()
		self["lock"] = Label()
		self["snr_percentage"] = TunerInfo(TunerInfo.SNR_PERCENTAGE, self.session.nav.getCurrentService)
		self["agc_percentage"] = TunerInfo(TunerInfo.AGC_PERCENTAGE, self.session.nav.getCurrentService)
		self["ber_value"] = TunerInfo(TunerInfo.BER_VALUE, self.session.nav.getCurrentService)
		self["snr_bar"] = TunerInfo(TunerInfo.SNR_BAR, self.session.nav.getCurrentService)
		self["agc_bar"] = TunerInfo(TunerInfo.AGC_BAR, self.session.nav.getCurrentService)
		self["ber_bar"] = TunerInfo(TunerInfo.BER_BAR, self.session.nav.getCurrentService)
		self["lock_state"] = TunerInfo(TunerInfo.LOCK_STATE, self.session.nav.getCurrentService)
		
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
		
		self.updateColors("tune")
		
		self.statusTimer = eTimer()
		self.statusTimer.timeout.get().append(self.updateStatus)
		self.statusTimer.start(200, False)
		
	def createConfig(self):
		config.positioner = ConfigSubsection()
		config.positioner.tune = configElement_nonSave("tune", configNothing, 0, None)
		config.positioner.move = configElement_nonSave("move", configNothing, 0, None)
		config.positioner.limits = configElement_nonSave("limits", configNothing, 0, None)
		storepos = []
		for x in range(255):
			storepos.append(str(x))
		config.positioner.storage = configElement_nonSave("storage", configSelection, 0, storepos)
	
	def createSetup(self):
		self.list.append(getConfigListEntry(_("Tune"), config.positioner.tune))
		self.list.append(getConfigListEntry(_("Positioner movement"), config.positioner.move))
		self.list.append(getConfigListEntry(_("Set limits"), config.positioner.limits))
		self.list.append(getConfigListEntry(_("Positioner storage"), config.positioner.storage))
		
		self["list"].l.setList(self.list)
		
	def go(self):
		pass
	
	def getCurrentConfigPath(self):
		return self["list"].getCurrent()[1].parent.configPath
	
	def up(self):
		self["list"].instance.moveSelection(self["list"].instance.moveUp)
		self.updateColors(self.getCurrentConfigPath())
	
	def down(self):
		self["list"].instance.moveSelection(self["list"].instance.moveDown)
		self.updateColors(self.getCurrentConfigPath())
	
	def left(self):
		self["list"].handleKey(config.key["prevElement"])
	
	def right(self):
		self["list"].handleKey(config.key["nextElement"])
	
	def updateColors(self, entry):
		if entry == "tune":
			self.red.setText("tune manually")
			self.green.setText("predefined transponder")
			self.yellow.setText("")
			self.blue.setText("")
		elif entry == "move":
			if self.isMoving:
				self.red.setText(_("Stop"))
				self.green.setText(_("Stop"))
				self.yellow.setText(_("Stop"))
				self.blue.setText(_("Stop"))
			else:
				self.red.setText(_("Move west"))
				self.green.setText(_("Step west"))
				self.yellow.setText(_("Step east"))
				self.blue.setText(_("Move east"))
		elif entry == "limits":
			self.red.setText(_("Limits off"))
			self.green.setText(_("Limit west"))
			self.yellow.setText(_("Limit east"))
			self.blue.setText("")
		elif entry == "storage":
			self.red.setText()
			self.green.setText(_("Store position"))
			self.yellow.setText(_("Goto position"))
			self.blue.setText("")
		else:
			self.red.setText("")
			self.green.setText("")
			self.yellow.setText("")
			self.blue.setText("")
	
	def redKey(self):
		entry = self.getCurrentConfigPath()
		if entry == "move":
			if self.isMoving:
				self.diseqc.command("stop")
				self.isMoving = False
			else:
				self.diseqc.command("moveWest", 0)
				self.isMoving = True
			self.updateColors("move")
			print "moving west"
		elif entry == "limits":
			self.diseqc.command("limitOff")
				
	def greenKey(self):
		entry = self.getCurrentConfigPath()
		if entry == "move":
			print "stepping west"
			self.diseqc.command("moveWest", 1)
		elif entry == "storage":
			print "store at position", (config.positioner.storage.value + 1)
			self.diseqc.command("store", config.positioner.storage.value + 1)
		elif entry == "limits":
			self.diseqc.command("limitWest")
	
	def yellowKey(self):
		entry = self.getCurrentConfigPath()
		if entry == "move":
			print "stepping east"
			self.diseqc.command("moveEast", 1)
		elif entry == "storage":
			print "move to position", (config.positioner.storage.value + 1)
			self.diseqc.command("moveTo", config.positioner.storage.value + 1)
		elif entry == "limits":
			self.diseqc.command("limitEast")
#	
	def blueKey(self):
		entry = self.getCurrentConfigPath()
		if entry == "move":
			if self.isMoving:
				self.diseqc.command("stop")
				self.isMoving = False
			else:
				self.diseqc.command("moveEast", 0)
				self.isMoving = True
			self.updateColors("move")
			print "moving east"

	def updateStatus(self):
		self["snr_percentage"].update()
		self["agc_percentage"].update()
		self["ber_value"].update()
		self["snr_bar"].update()
		self["agc_bar"].update()
		self["ber_bar"].update()

class Diseqc:
	def __init__(self, feid = 0):
		self.ready = False
		self.feid = feid
		res_mgr = eDVBResourceManagerPtr()
		if eDVBResourceManager.getInstance(res_mgr) == 0:
			raw_channel = iDVBChannelPtr()
			if res_mgr.allocateRawChannel(raw_channel, self.feid) == 0:
				self.frontend = iDVBFrontendPtr()
				if raw_channel.getFrontend(self.frontend) == 0:
					self.frontend.setVoltage(iDVBFrontend.voltage18)
					self.ready = True
				else:
					print "getFrontend failed"
			else:
				print "getRawChannel failed"
		else:
				print "getResourceManager instance failed"
		
	def command(self, what, param = 0):
		if self.ready:
			cmd = eDVBDiseqcCommand()
			if what == "moveWest":
				string = '\xe1\x31\x69' + chr(param)
			elif what == "moveEast":
				string = '\xe1\x31\x68' + chr(param)
			elif what == "moveTo":
				string = '\xe1\x31\x6b' + chr(param)
			elif what == "store":
				string = '\xe1\x31\x6a' + chr(param)
			elif what == "limitOff":
				string = '\xe1\x31\x63'
			elif what == "limitEast":
				string = '\xe1\x31\x66'
			elif what == "limitWest":
				string = '\xe1\x31\x67'
			else:
				string = '\xe0\x31\x60' #positioner stop
			print "diseqc command:",
			for x in string:
				print hex(ord(x)),
			print
			
			cmd.setCommandString(string)
			self.frontend.sendDiseqc(cmd)
					
def PositionerMain(session, **kwargs):
	session.open(PositionerSetup)

def Plugins(**kwargs):
	return PluginDescriptor(name="Positioner setup", description="Setup your positioner", where = PluginDescriptor.WHERE_PLUGINMENU, fnc=PositionerMain)
