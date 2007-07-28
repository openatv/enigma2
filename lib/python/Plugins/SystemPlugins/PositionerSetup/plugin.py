from enigma import eTimer, eDVBSatelliteEquipmentControl, eDVBResourceManager, \
	eDVBDiseqcCommand, eDVBFrontendParametersSatellite, eDVBFrontendParameters,\
	iDVBFrontend

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
from Components.config import ConfigSatlist, ConfigNothing, ConfigSelection, ConfigSubsection, KEY_LEFT, KEY_RIGHT, getConfigListEntry

from time import sleep

class PositionerSetup(Screen):
	skin = """
		<screen position="100,100" size="560,400" title="Positioner setup..." >
			<widget name="list" position="100,0" size="350,155" />

			<widget name="red" position="0,155" size="140,80" backgroundColor="red" halign="center" valign="center" font="Regular;21" />
			<widget name="green" position="140,155" size="140,80" backgroundColor="green" halign="center" valign="center" font="Regular;21" />
			<widget name="yellow" position="280,155" size="140,80" backgroundColor="yellow" halign="center" valign="center" font="Regular;21" />
			<widget name="blue" position="420,155" size="140,80" backgroundColor="blue" halign="center" valign="center" font="Regular;21" />
			
			<widget name="snr" text="SNR:" position="0,245" size="60,22" font="Regular;21" />
			<widget name="agc" text="AGC:" position="0,270" size="60,22" font="Regular;21" />
			<widget name="ber" text="BER:" position="0,295" size="60,22" font="Regular;21" />
			<widget name="lock" text="Lock:" position="0,320" size="60,22" font="Regular;21" />
			<widget name="snr_percentage" position="220,245" size="60,22" font="Regular;21" />
			<widget name="agc_percentage" position="220,270" size="60,22" font="Regular;21" />
			<widget name="ber_value" position="220,295" size="60,22" font="Regular;21" />
			<widget name="lock_state" position="60,320" size="150,22" font="Regular;21" />
			<widget name="snr_bar" position="60,245" size="150,22" />
			<widget name="agc_bar" position="60,270" size="150,22" />
			<widget name="ber_bar" position="60,295" size="150,22" />

			<widget name="frequency" text="Frequency:" position="300,245" size="120,22" font="Regular;21" />
			<widget name="symbolrate" text="Symbolrate:" position="300,270" size="120,22" font="Regular;21" />
			<widget name="fec" text="FEC:" position="300,295" size="120,22" font="Regular;21" />
			<widget name="frequency_value" position="420,245" size="120,22" font="Regular;21" />
			<widget name="symbolrate_value" position="420,270" size="120,22" font="Regular;21" />
			<widget name="fec_value" position="420,295" size="120,22" font="Regular;21" />
		</screen>"""
	def __init__(self, session, feid):
		self.skin = PositionerSetup.skin
		Screen.__init__(self, session)
		self.feid = feid
		self.oldref = None
		
		if not self.openFrontend():
			self.oldref = session.nav.getCurrentlyPlayingServiceReference()
			session.nav.stopService() # try to disable foreground service
			if not self.openFrontend():
				if session.pipshown: # try to disable pip
					session.pipshown = False
					del session.pip
					if not self.openFrontend():
						self.frontend = None # in normal case this should not happen

		self.frontendStatus = { }

		self.diseqc = Diseqc(self.frontend)
		self.tuner = Tuner(self.frontend)
		self.tuner.tune((0,0,0,0,0,0))
		
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
		self["snr_percentage"] = TunerInfo(TunerInfo.SNR_PERCENTAGE, statusDict = self.frontendStatus)
		self["agc_percentage"] = TunerInfo(TunerInfo.AGC_PERCENTAGE, statusDict = self.frontendStatus)
		self["ber_value"] = TunerInfo(TunerInfo.BER_VALUE, statusDict = self.frontendStatus)
		self["snr_bar"] = TunerInfo(TunerInfo.SNR_BAR, statusDict = self.frontendStatus)
		self["agc_bar"] = TunerInfo(TunerInfo.AGC_BAR, statusDict = self.frontendStatus)
		self["ber_bar"] = TunerInfo(TunerInfo.BER_BAR, statusDict = self.frontendStatus)
		self["lock_state"] = TunerInfo(TunerInfo.LOCK_STATE, statusDict = self.frontendStatus)

		self["frequency"] = Label()
		self["symbolrate"] = Label()
		self["fec"] = Label()

		self["frequency_value"] = Label("")
		self["symbolrate_value"] = Label("")
		self["fec_value"] = Label("")
		
		self["actions"] = ActionMap(["DirectionActions", "OkCancelActions", "ColorActions"],
		{
			"ok": self.go,
			"cancel": self.keyCancel,
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

	def restartPrevService(self, yesno):
		if yesno:
			if self.frontend:
				self.frontend = None
				del self.raw_channel
			self.session.nav.playService(self.oldref)
		self.close(None)
	
	def keyCancel(self):
		if self.oldref:
			self.session.openWithCallback(self.restartPrevService, MessageBox, _("Zap back to service before positioner setup?"), MessageBox.TYPE_YESNO)
		else:
			self.restartPrevService(False)

	def openFrontend(self):
		res_mgr = eDVBResourceManager.getInstance()
		if res_mgr:
			self.raw_channel = res_mgr.allocateRawChannel(self.feid)
			if self.raw_channel:
				self.frontend = self.raw_channel.getFrontend()
				if self.frontend:
					return True
				else:
					print "getFrontend failed"
			else:
				print "getRawChannel failed"
		else:
			print "getResourceManager instance failed"
		return False

	def createConfig(self):
		self.positioner_tune = ConfigNothing()
		self.positioner_move = ConfigNothing()
		self.positioner_finemove = ConfigNothing()
		self.positioner_limits = ConfigNothing()
		self.positioner_goto0 = ConfigNothing()
		storepos = []
		for x in range(1,255):
			storepos.append(str(x))
		self.positioner_storage = ConfigSelection(choices = storepos)

	def createSetup(self):
		self.list.append((_("Tune"), self.positioner_tune, "tune"))
		self.list.append((_("Positioner movement"), self.positioner_move, "move"))
		self.list.append((_("Positioner fine movement"), self.positioner_finemove, "finemove"))
		self.list.append((_("Set limits"), self.positioner_limits, "limits"))
		self.list.append((_("Positioner storage"), self.positioner_storage, "storage"))
		self.list.append((_("Goto 0"), self.positioner_goto0, "goto0"))
		self["list"].l.setList(self.list)

	def go(self):
		pass

	def getCurrentConfigPath(self):
		return self["list"].getCurrent()[2]

	def up(self):
		if not self.isMoving:
			self["list"].instance.moveSelection(self["list"].instance.moveUp)
			self.updateColors(self.getCurrentConfigPath())

	def down(self):
		if not self.isMoving:
			self["list"].instance.moveSelection(self["list"].instance.moveDown)
			self.updateColors(self.getCurrentConfigPath())

	def left(self):
		self["list"].handleKey(KEY_LEFT)

	def right(self):
		self["list"].handleKey(KEY_RIGHT)

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
			self.blue.setText(_("Limits on"))
		elif entry == "storage":
			self.red.setText("")
			self.green.setText(_("Store position"))
			self.yellow.setText(_("Goto position"))
			self.blue.setText("")
		elif entry == "goto0":
			self.red.setText(_("Goto 0"))
			self.green.setText("")
			self.yellow.setText("")
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
		elif entry == "goto0":
			print "move to position 0"
			self.diseqccommand("moveTo", 0)

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
			self.diseqccommand("moveWest", 0xFF) # one step
		elif entry == "storage":
			print "store at position", int(self.positioner_storage.value)
			self.diseqccommand("store", int(self.positioner_storage.value))
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
			self.diseqccommand("moveEast", 0xFF) # one step
		elif entry == "storage":
			print "move to position", int(self.positioner_storage.value)
			self.diseqccommand("moveTo", int(self.positioner_storage.value))
		elif entry == "limits":
			self.diseqccommand("limitEast")

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
		elif entry == "limits":
			self.diseqccommand("limitOn")

	def diseqccommand(self, cmd, param = 0):
		self.diseqc.command(cmd, param)
		self.tuner.retune()

	def updateStatus(self):
		if self.frontend:
			self.frontend.getFrontendStatus(self.frontendStatus)
		self["snr_percentage"].update()
		self["agc_percentage"].update()
		self["ber_value"].update()
		self["snr_bar"].update()
		self["agc_bar"].update()
		self["ber_bar"].update()
		self["lock_state"].update()
		transponderdata = self.tuner.getTransponderData()
		self["frequency_value"].setText(str(transponderdata.get("frequency")))
		self["symbolrate_value"].setText(str(transponderdata.get("symbol_rate")))
		self["fec_value"].setText(str(transponderdata.get("fec_inner")))
		if self.frontendStatus.get("tuner_locked", 0) == 1 and self.isMoving and self.stopOnLock:
			self.diseqccommand("stop")
			self.isMoving = False
			self.stopOnLock = False
			self.updateColors(self.getCurrentConfigPath())

	def tune(self, transponder):
		if transponder is not None:
			self.tuner.tune(transponder)

class Diseqc:
	def __init__(self, frontend):
		self.frontend = frontend

	def command(self, what, param = 0):
		if self.frontend:
			cmd = eDVBDiseqcCommand()
			if what == "moveWest":
				string = 'e03169' + ("%02x" % param)
			elif what == "moveEast":
				string = 'e03168' + ("%02x" % param)
			elif what == "moveTo":
				string = 'e0316b' + ("%02x" % param)
			elif what == "store":
				string = 'e0316a' + ("%02x" % param)
			elif what == "limitOn":
				string = 'e0316a00'
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
			self.frontend.setTone(iDVBFrontend.toneOff)
			sleep(0.015) # wait 15msec after disable tone
			self.frontend.sendDiseqc(cmd)
			if string == 'e03160': #positioner stop
				sleep(0.05)
				self.frontend.sendDiseqc(cmd) # send 2nd time

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
		parm.modulation = 1 # FIXMEE !! HARDCODED QPSK
		feparm = eDVBFrontendParameters()
		feparm.setDVBS(parm, True)
		self.lastparm = feparm
		if self.frontend:
			self.frontend.tune(feparm)

	def retune(self):
		if self.frontend:
			self.frontend.tune(self.lastparm)

	def getTransponderData(self):
		ret = { }
		if self.frontend:
			self.frontend.getTransponderData(ret, True)
		return ret

tuning = None

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
		self.typeOfTuningEntry = getConfigListEntry(_('Tune'), tuning.type)
		self.list.append(self.typeOfTuningEntry)
		self.satEntry = getConfigListEntry(_('Satellite'), tuning.sat)
		self.list.append(self.satEntry)
		if tuning.type.value == "manual_transponder":
			self.list.append(getConfigListEntry(_('Frequency'), self.scan_sat.frequency))
			self.list.append(getConfigListEntry(_('Inversion'), self.scan_sat.inversion))
			self.list.append(getConfigListEntry(_('Symbol Rate'), self.scan_sat.symbolrate))
			self.list.append(getConfigListEntry(_("Polarity"), self.scan_sat.polarization))
			self.list.append(getConfigListEntry(_("FEC"), self.scan_sat.fec))
		elif tuning.type.value == "predefined_transponder":
			self.list.append(getConfigListEntry(_("Transponder"), tuning.transponder))
		self["config"].list = self.list
		self["config"].l.setList(self.list)

	def newConfig(self):
		if self["config"].getCurrent() == self.typeOfTuningEntry:
			self.createSetup()
		elif self["config"].getCurrent() == self.satEntry:
			self.createSetup()

	def createConfig(self, foo):
		global tuning
		if not tuning:
			tuning = ConfigSubsection()
			tuning.type = ConfigSelection(
				default = "manual_transponder",
				choices = { "manual_transponder" : _("Manual transponder"),
							"predefined_transponder" : _("Predefined transponder") } )
			tuning.sat = ConfigSatlist(list=nimmanager.getRotorSatListForNim(self.feid))
			tuning.sat.addNotifier(self.tuningSatChanged)
			self.updateTransponders()
			TunerScreenConfigCreated = True
		ScanSetup.createConfig(self, None)

	def tuningSatChanged(self, *parm):
		self.updateTransponders()

	def updateTransponders(self):
		if len(tuning.sat.choices):
			transponderlist = nimmanager.getTransponders(int(tuning.sat.value))
			tps = []
			cnt=0
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
				tps.append(str(x[1]) + "," + str(x[2]) + "," + pol + "," + fec)
			tuning.transponder = ConfigSelection(choices=tps)

	def keyGo(self):
		returnvalue = (0, 0, 0, 0, 0, 0)
		satpos = int(tuning.sat.value)
		if tuning.type.value == "manual_transponder":
			returnvalue = (
				self.scan_sat.frequency.value,
				self.scan_sat.symbolrate.value,
				self.scan_sat.polarization.index,
				self.scan_sat.fec.index,
				self.scan_sat.inversion.index,
				satpos)
		elif tuning.type.value == "predefined_transponder":
			transponder = nimmanager.getTransponders(satpos)[tuning.transponder.index]
			returnvalue = (int(transponder[1] / 1000), int(transponder[2] / 1000), transponder[3], transponder[4], 2, satpos)
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
			n = nimmanager.nim_slots[x]
			nimMenuList.append((n.friendly_full_name, x))
		
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
	nimList = nimmanager.getNimListOfType("DVB-S")
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

def PositionerSetupStart(menuid, **kwargs):
	if menuid == "scan":
		return [(_("Positioner setup"), PositionerMain)]
	else:
		return []

def Plugins(**kwargs):
	if (nimmanager.hasNimType("DVB-S")):
		return PluginDescriptor(name=_("Positioner setup"), description="Setup your positioner", where = PluginDescriptor.WHERE_SETUP, fnc=PositionerSetupStart)
	else:
		return []
