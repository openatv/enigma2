from enigma import eTimer, eDVBSatelliteEquipmentControl, eDVBResourceManager, eDVBDiseqcCommand, eDVBResourceManagerPtr, iDVBChannelPtr, iDVBFrontendPtr, iDVBFrontend, eDVBFrontendParametersSatellite, eDVBFrontendParameters
from Screens.Screen import Screen
from Screens.ScanSetup import ScanSetup
from Screens.MessageBox import MessageBox
from Plugins.Plugin import PluginDescriptor

from Components.Label import Label
from Components.ConfigList import ConfigList
from Components.TunerInfo import TunerInfo
from Components.ActionMap import ActionMap
from Components.NimManager import nimmanager
from Components.MenuList import MenuList
from Components.config import config, ConfigSubsection, configElement_nonSave, configNothing, getConfigListEntry, configSelection, currentConfigSelectionElement, configSatlist

class PositionerSetup(Screen):
	skin = """
		<screen position="100,100" size="560,400" title="Positioner setup..." >
			<widget name="list" position="100,0" size="350,130" />

			<widget name="red" position="0,130" size="140,80" backgroundColor="red" halign="center" valign="center" font="Regular;21" />
			<widget name="green" position="140,130" size="140,80" backgroundColor="green" halign="center" valign="center" font="Regular;21" />
			<widget name="yellow" position="280,130" size="140,80" backgroundColor="yellow" halign="center" valign="center" font="Regular;21" />
			<widget name="blue" position="420,130" size="140,80" backgroundColor="blue" halign="center" valign="center" font="Regular;21" />
			
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

			<widget name="frequency" text="Frequency:" position="300,220" size="120,22" font="Regular;21" />
			<widget name="symbolrate" text="Symbolrate:" position="300,245" size="120,22" font="Regular;21" />
			<widget name="fec" text="FEC:" position="300,270" size="120,22" font="Regular;21" />
			<widget name="frequency_value" position="420,220" size="120,22" font="Regular;21" />
			<widget name="symbolrate_value" position="420,245" size="120,22" font="Regular;21" />
			<widget name="fec_value" position="420,270" size="120,22" font="Regular;21" />
		</screen>"""
	def __init__(self, session, feid):
		self.skin = PositionerSetup.skin
		Screen.__init__(self, session)
		
		self.session.nav.stopService()
		
		self.feid = feid
		
		self.diseqc = Diseqc(self.feid)
		self.tuner = Tuner(self.diseqc.getFrontend())
		self.tuner.tune((0,0,0,0,0,0,0,0,0))
		
		#self.session.nav.stopService()
		
		self.createConfig()
		
		self.isMoving = False
		self.stopOnLock = False
		
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
		
		self["snr"] = Label()
		self["agc"] = Label()
		self["ber"] = Label()
		self["lock"] = Label()
		self["snr_percentage"] = TunerInfo(TunerInfo.SNR_PERCENTAGE, frontendfkt = self.diseqc.getFrontend)
		self["agc_percentage"] = TunerInfo(TunerInfo.AGC_PERCENTAGE, frontendfkt = self.diseqc.getFrontend)
		self["ber_value"] = TunerInfo(TunerInfo.BER_VALUE, frontendfkt = self.diseqc.getFrontend)
		self["snr_bar"] = TunerInfo(TunerInfo.SNR_BAR, frontendfkt = self.diseqc.getFrontend)
		self["agc_bar"] = TunerInfo(TunerInfo.AGC_BAR, frontendfkt = self.diseqc.getFrontend)
		self["ber_bar"] = TunerInfo(TunerInfo.BER_BAR, frontendfkt = self.diseqc.getFrontend)
		self["lock_state"] = TunerInfo(TunerInfo.LOCK_STATE, frontendfkt = self.diseqc.getFrontend)

		self["frequency"] = Label()
		self["symbolrate"] = Label()
		self["fec"] = Label()

		self["frequency_value"] = Label("")
		self["symbolrate_value"] = Label("")
		self["fec_value"] = Label("")
		
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
		self.statusTimer.start(50, False)
		
	def createConfig(self):
		config.positioner = ConfigSubsection()
		config.positioner.tune = configElement_nonSave("tune", configNothing, 0, None)
		config.positioner.move = configElement_nonSave("move", configNothing, 0, None)
		config.positioner.finemove = configElement_nonSave("finemove", configNothing, 0, None)
		config.positioner.limits = configElement_nonSave("limits", configNothing, 0, None)
		storepos = []
		for x in range(255):
			storepos.append(str(x))
		config.positioner.storage = configElement_nonSave("storage", configSelection, 0, storepos)
	
	def createSetup(self):
		self.list.append(getConfigListEntry(_("Tune"), config.positioner.tune))
		self.list.append(getConfigListEntry(_("Positioner movement"), config.positioner.move))
		self.list.append(getConfigListEntry(_("Positioner fine movement"), config.positioner.finemove))
		self.list.append(getConfigListEntry(_("Set limits"), config.positioner.limits))
		self.list.append(getConfigListEntry(_("Positioner storage"), config.positioner.storage))
		
		self["list"].l.setList(self.list)
		
	def go(self):
		pass
	
	def getCurrentConfigPath(self):
		return self["list"].getCurrent()[1].parent.configPath
	
	def up(self):
		if not self.isMoving:
			self["list"].instance.moveSelection(self["list"].instance.moveUp)
			self.updateColors(self.getCurrentConfigPath())
	
	def down(self):
		if not self.isMoving:
			self["list"].instance.moveSelection(self["list"].instance.moveDown)
			self.updateColors(self.getCurrentConfigPath())
	
	def left(self):
		self["list"].handleKey(config.key["prevElement"])
	
	def right(self):
		self["list"].handleKey(config.key["nextElement"])
	
	def updateColors(self, entry):
		if entry == "tune":
			self.red.setText(_("Tune"))
			self.green.setText("")
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
				self.green.setText(_("Search west"))
				self.yellow.setText(_("Search east"))
				self.blue.setText(_("Move east"))
		elif entry == "finemove":
			self.red.setText("")
			self.green.setText(_("Step west"))
			self.yellow.setText(_("Step east"))
			self.blue.setText("")
		elif entry == "limits":
			self.red.setText(_("Limits off"))
			self.green.setText(_("Limit west"))
			self.yellow.setText(_("Limit east"))
			self.blue.setText("")
		elif entry == "storage":
			self.red.setText("")
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
				self.diseqccommand("stop")
				self.isMoving = False
				self.stopOnLock = False
			else:
				self.diseqccommand("moveWest", 0)
				self.isMoving = True
			self.updateColors("move")
		elif entry == "limits":
			self.diseqccommand("limitOff")
		elif entry == "tune":
			self.session.openWithCallback(self.tune, TunerScreen, self.feid)
				
	def greenKey(self):
		entry = self.getCurrentConfigPath()
		if entry == "move":
			if self.isMoving:
				self.diseqccommand("stop")
				self.isMoving = False
				self.stopOnLock = False
			else:
				self.isMoving = True
				self.stopOnLock = True
				self.diseqccommand("moveWest", 0)
			self.updateColors("move")
		elif entry == "finemove":
			print "stepping west"
			self.diseqccommand("moveWest", 1)
		elif entry == "storage":
			print "store at position", (config.positioner.storage.value + 1)
			self.diseqccommand("store", config.positioner.storage.value + 1)
		elif entry == "limits":
			self.diseqccommand("limitWest")
	
	def yellowKey(self):
		entry = self.getCurrentConfigPath()
		if entry == "move":
			if self.isMoving:
				self.diseqccommand("stop")
				self.isMoving = False
				self.stopOnLock = False
			else:
				self.isMoving = True
				self.stopOnLock = True
				self.diseqccommand("moveEast", 0)
			self.updateColors("move")
		elif entry == "finemove":
			print "stepping east"
			self.diseqccommand("moveEast", 1)
		elif entry == "storage":
			print "move to position", (config.positioner.storage.value + 1)
			self.diseqccommand("moveTo", config.positioner.storage.value + 1)
		elif entry == "limits":
			self.diseqccommand("limitEast")
#	
	def blueKey(self):
		entry = self.getCurrentConfigPath()
		if entry == "move":
			if self.isMoving:
				self.diseqccommand("stop")
				self.isMoving = False
				self.stopOnLock = False
			else:
				self.diseqccommand("moveEast", 0)
				self.isMoving = True
			self.updateColors("move")
			print "moving east"
			
	def diseqccommand(self, cmd, param = 0):
		self.diseqc.command(cmd, param)
		self.tuner.retune()

	def updateStatus(self):
		self["snr_percentage"].update()
		self["agc_percentage"].update()
		self["ber_value"].update()
		self["snr_bar"].update()
		self["agc_bar"].update()
		self["ber_bar"].update()
		self["lock_state"].update()
		transponderdata = self.tuner.getTransponderData()
		self["frequency_value"].setText(str(transponderdata["frequency"]))
		self["symbolrate_value"].setText(str(transponderdata["symbol_rate"]))
		self["fec_value"].setText(str(transponderdata["fec_inner"]))
		if transponderdata["tuner_locked"] == 1 and self.isMoving and self.stopOnLock:
			self.diseqccommand("stop")
			self.isMoving = False
			self.stopOnLock = False
			self.updateColors(self.getCurrentConfigPath())

	def tune(self, transponder):
		if transponder is not None:
			self.tuner.tune(transponder)
			
class Diseqc:
	def __init__(self, feid = 0):
		self.ready = False
		self.feid = feid
		res_mgr = eDVBResourceManagerPtr()
		if eDVBResourceManager.getInstance(res_mgr) == 0:
			self.raw_channel = iDVBChannelPtr()
			if res_mgr.allocateRawChannel(self.raw_channel, self.feid) == 0:
				self.frontend = iDVBFrontendPtr()
				if self.raw_channel.getFrontend(self.frontend) == 0:
					self.ready = True
				else:
					print "getFrontend failed"
			else:
				print "getRawChannel failed"
		else:
			print "getResourceManager instance failed"
	
	def getFrontend(self):
		return self.frontend
		
	def command(self, what, param = 0):
		if self.ready:
			cmd = eDVBDiseqcCommand()
			if what == "moveWest":
				string = 'e03169' + ("%02x" % param)
			elif what == "moveEast":
				string = 'e03168' + ("%02x" % param)
			elif what == "moveTo":
				string = 'e0316b' + ("%02x" % param)
			elif what == "store":
				string = 'e0316a' + ("%02x" % param)
			elif what == "limitOff":
				string = 'e03163'
			elif what == "limitEast":
				string = 'e03166'
			elif what == "limitWest":
				string = 'e03167'
			else:
				string = 'e03160' #positioner stop
			print "diseqc command:",
			print string
			
			cmd.setCommandString(string)
			self.frontend.sendDiseqc(cmd)
			
class Tuner:
	def __init__(self, frontend):
		self.frontend = frontend
		
	def tune(self, transponder):
		print "tuning to transponder with data", transponder
		parm = eDVBFrontendParametersSatellite()
		parm.frequency = transponder[0] * 1000
		parm.symbol_rate = transponder[1] * 1000
		parm.polarisation = transponder[2]
		parm.fec = transponder[3]
		parm.inversion = transponder[4]
		parm.orbital_position = transponder[5]
		parm.system = 0  # FIXMEE !! HARDCODED DVB-S (add support for DVB-S2)
		feparm = eDVBFrontendParameters()
		feparm.setDVBS(parm, True)
		self.lastparm = feparm
		self.frontend.tune(feparm)
	
	def retune(self):
		self.frontend.tune(self.lastparm)
	
	def getTransponderData(self):
		return self.frontend.readTransponderData(True)

class TunerScreen(ScanSetup):
	skin = """
		<screen position="90,100" size="520,400" title="Tune">
			<widget name="config" position="20,10" size="460,350" scrollbarMode="showOnDemand" />
			<widget name="introduction" position="20,360" size="350,30" font="Regular;23" />
		</screen>"""

	def __init__(self, session, feid):
		self.feid = feid
		ScanSetup.__init__(self, session)

		self["introduction"].setText("")
		
	def createSetup(self):
		self.typeOfTuningEntry = None
		self.satEntry = None

		self.list = []
		self.typeOfTuningEntry = getConfigListEntry(_('Tune'), config.tuning.type)
		self.list.append(self.typeOfTuningEntry)
		self.satEntry = getConfigListEntry(_('Satellite'), config.tuning.sat)
		self.list.append(self.satEntry)
		if currentConfigSelectionElement(config.tuning.type) == "manual_transponder":
			self.list.append(getConfigListEntry(_('Frequency'), config.scan.sat.frequency))
			self.list.append(getConfigListEntry(_('Inversion'), config.scan.sat.inversion))
			self.list.append(getConfigListEntry(_('Symbol Rate'), config.scan.sat.symbolrate))
			self.list.append(getConfigListEntry(_("Polarity"), config.scan.sat.polarization))
			self.list.append(getConfigListEntry(_("FEC"), config.scan.sat.fec))
		elif currentConfigSelectionElement(config.tuning.type) == "predefined_transponder":
			self.list.append(getConfigListEntry(_("Transponder"), config.tuning.transponder))
		self["config"].list = self.list
		self["config"].l.setList(self.list)

	def newConfig(self):
		if self["config"].getCurrent() == self.typeOfTuningEntry:
			self.createSetup()
		elif self["config"].getCurrent() == self.satEntry:
			self.updateSats()
			self.createSetup()

	def createConfig(self):
		config.tuning = ConfigSubsection()
		
		config.tuning.type = configElement_nonSave("config.tuning.type", configSelection, 0, (("manual_transponder", _("Manual transponder")), ("predefined_transponder", _("Predefined satellite"))))
		
		config.tuning.sat = configElement_nonSave("config.tuning.sat", configSatlist, 192, nimmanager.getRotorSatListForNim(self.feid))
		ScanSetup.createConfig(self)
		self.updateSats()
		
	def updateSats(self):
		satnum = config.tuning.sat.value
		satlist = config.tuning.sat.vals
		if len(satlist):
			transponderlist = nimmanager.getTransponders(satlist[satnum][1])
			list = []
			for x in transponderlist:
				if x[3] == 0:
					pol = "H"
				elif x[3] == 1:
					pol = "V"
				elif x[3] == 2:
					pol = "CL"
				elif x[3] == 3:
					pol = "CR"
				if x[4] == 0:
					fec = "FEC_AUTO"
				elif x[4] == 1:
					fec = "FEC_1_2"
				elif x[4] == 2:
					fec = "FEC_2_3"
				elif x[4] == 3:
					fec = "FEC_3_4"
				elif x[4] == 4:
					fec = "FEC_5_6"
				elif x[4] == 5:
					fec = "FEC_7_8"
				elif x[4] == 5:
					fec = "FEC_8_9"
				elif x[4] == 6:
					fec = "FEC_None"
				list.append(str(x[1]) + "," + str(x[2]) + "," + pol + "," + fec)
			config.tuning.transponder = configElement_nonSave("config.tuning.transponder", configSelection, 0, list)
	
	def keyGo(self):
		returnvalue = (0, 0, 0, 0, 0, 0, 0)
		satpos = config.tuning.sat.vals[config.tuning.sat.value][1]
		if currentConfigSelectionElement(config.tuning.type) == "manual_transponder":
			returnvalue = (config.scan.sat.frequency.value[0], config.scan.sat.symbolrate.value[0], config.scan.sat.polarization.value, config.scan.sat.fec.value, config.scan.sat.inversion.value, satpos)
		elif currentConfigSelectionElement(config.tuning.type) == "predefined_transponder":
			transponder = nimmanager.getTransponders(config.tuning.sat.vals[config.tuning.sat.value][1])[config.tuning.transponder.value]
			returnvalue = (int(transponder[1] / 100), int(transponder[2] / 1000), transponder[3], transponder[4], 2, config.tuning.sat.vals[config.tuning.sat.value][1], satpos)
		self.close(returnvalue)

	def keyCancel(self):
		self.close(None)

class NimSelection(Screen):
	skin = """
		<screen position="140,165" size="400,100" title="select Slot">
			<widget name="nimlist" position="20,10" size="360,75" />
		</screen>"""
		
	def __init__(self, session):
		Screen.__init__(self, session)

		nimlist = nimmanager.getNimListOfType(nimmanager.nimType["DVB-S"])
		nimMenuList = []
		for x in nimlist:
			nimMenuList.append((_("NIM ") + (["A", "B", "C", "D"][x]) + ": " + nimmanager.getNimName(x) + " (" + nimmanager.getNimTypeName(x) + ")", x))
		
		self["nimlist"] = MenuList(nimMenuList)

		self["actions"] = ActionMap(["OkCancelActions"],
		{
			"ok": self.okbuttonClick ,
			"cancel": self.close
		}, -1)

	def okbuttonClick(self):
		selection = self["nimlist"].getCurrent()
		self.session.open(PositionerSetup, selection[1])

def PositionerMain(session, **kwargs):
	nimList = nimmanager.getNimListOfType(nimmanager.nimType["DVB-S"])
	if len(nimList) == 0:
		session.open(MessageBox, _("No positioner capable frontend found."), MessageBox.TYPE_ERROR)
	else:
		if session.nav.RecordTimer.isRecording():
			session.open(MessageBox, _("A recording is currently running. Please stop the recording before trying to configure the positioner."), MessageBox.TYPE_ERROR)
		else:
			usableNims = []
			for x in nimList:
				configured_rotor_sats = nimmanager.getRotorSatListForNim(x)
				if len(configured_rotor_sats) != 0:
					usableNims.append(x)
			if len(usableNims) == 1:
				session.open(PositionerSetup, usableNims[0])
			elif len(usableNims) > 1:
				session.open(NimSelection)
			else:
				session.open(MessageBox, _("No tuner is configured for use with a diseqc positioner!"), MessageBox.TYPE_ERROR)

def Plugins(**kwargs):
	return PluginDescriptor(name="Positioner setup", description="Setup your positioner", where = PluginDescriptor.WHERE_PLUGINMENU, fnc=PositionerMain)
