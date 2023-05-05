from Screens.Screen import Screen
from Plugins.Plugin import PluginDescriptor
from Components.Button import Button
from Components.ActionMap import ActionMap
from Components.config import config, configfile, ConfigSubsection, getConfigListEntry, ConfigSelection
from Components.ConfigList import ConfigListScreen
from Components.Label import Label
from enigma import eTimer, getDesktop

config.plugins.aml = ConfigSubsection()
config.plugins.aml.governor = ConfigSelection(default="performance", choices=[("interactive", "Interactive - responsive and savvy"), ("schedutil", "schedutil - scheduler-driven (suggested)"), ("performance", "Performance -max full time (default)")])
config.plugins.aml.maxfrq = ConfigSelection(default="1800000", choices=[("500000", "500 MHz"),
	("667000", "667 MHz"),
	("1000000", "1 GHz"),
	("1200000", "1.2 GHz"),
	("1398000", "1.4 GHz"),
	("1512000", "1.5 GHz"),
	("1608000", "1.6 GHz"),
	("1704000", "1.7 GHz"),
	("1800000", "1.8 GHz (default)")])
config.plugins.aml.minfrq = ConfigSelection(default="500000", choices=[("500000", "500 MHz (default)"),
	("667000", "667 MHz"),
	("1000000", "1 GHz"),
	("1200000", "1.2 GHz"),
	("1398000", "1.4 GHz"),
	("1512000", "1.5 GHz"),
	("1608000", "1.6 GHz"),
	("1704000", "1.7 GHz"),
	("1800000", "1.8 GHz")])
config.plugins.aml.maxfrq2 = ConfigSelection(default="1704000", choices=[("500000", "500 MHz"),
	("667000", "667 MHz"),
	("1000000", "1 GHz"),
	("1200000", "1.2 GHz"),
	("1398000", "1.4 GHz"),
	("1512000", "1.5 GHz"),
	("1608000", "1.6 GHz"),
	("1704000", "1.7 GHz (default)")])
config.plugins.aml.minfrq2 = ConfigSelection(default="500000", choices=[("500000", "500 MHz (default)"),
	("667000", "667 MHz"),
	("1000000", "1 GHz"),
	("1200000", "1.2 GHz"),
	("1398000", "1.4 GHz"),
	("1512000", "1.5 GHz"),
	("1608000", "1.6 GHz"),
	("1704000", "1.7 GHz")])


def leaveStandby():
	print("[AmlFRQ] Leave Standby")
	initBooster()


def standbyCounterChanged(configElement):
	print("[AmlFRQ] In Standby")
	initStandbyBooster()
	from Screens.Standby import inStandby
	inStandby.onClose.append(leaveStandby)


def initBooster():
	print("[AmlFRQ] initBooster")
	try:
		with open("/sys/devices/system/cpu/cpu0/cpufreq/scaling_max_freq", "w") as fd:
			fd.write(config.plugins.aml.maxfrq.getValue())
		with open("/sys/devices/system/cpu/cpu0/cpufreq/scaling_min_freq", "w") as fd:
			fd.write(config.plugins.aml.minfrq.getValue())
		with open("/sys/devices/system/cpu/cpu2/cpufreq/scaling_max_freq", "w") as fd:
			fd.write(config.plugins.aml.maxfrq2.getValue())
		with open("/sys/devices/system/cpu/cpu2/cpufreq/scaling_min_freq", "w") as fd:
			fd.write(config.plugins.aml.minfrq2.getValue())
		with open("/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor", "w") as fd:
			fd.write(config.plugins.aml.governor.getValue())
		with open("/sys/devices/system/cpu/cpu2/cpufreq/scaling_governor", "w") as fd:
			fd.write(config.plugins.aml.governor.getValue())
	except OSError:
		pass


def initStandbyBooster():
	print("[AmlFRQ] initStandbyBooster")
	try:
		with open("/sys/devices/system/cpu/cpu0/cpufreq/scaling_max_freq", "w") as fd:
			fd.write(config.plugins.aml.minfrq.getValue())
		with open("/sys/devices/system/cpu/cpu2/cpufreq/scaling_max_freq", "w") as fd:
			fd.write(config.plugins.aml.minfrq2.getValue())
	except OSError:
		pass


class AmlFRQ(ConfigListScreen, Screen):

	def __init__(self, session, args=None):
		DESKHEIGHT = getDesktop(0).size().height()
		if DESKHEIGHT == 720:
			self.skin = """
			<screen  position="0,0" size="1280,720" title="CPU Frequency Setup" flags="wfNoBorder" backgroundColor="#25062748">
			<widget source="Title" render="Label" position="140,93" size="1000,45" zPosition="2" halign="center" font="Regular; 24" backgroundColor="#25062748" transparent="1" valign="center" />
			<ePixmap name="" position="140,100" size="1000,546" pixmap="MetrixHD/ibts/background.png" zPosition="-10" />
			<eLabel name="" position="156,151" size="855,432" zPosition="-5" />
			<ePixmap pixmap="enigma2/icon/default.png" position="1044,189" size="60,46" zPosition="1" />
			<eLabel name="" position="1028,290" size="96,33" font="Regular; 18" valign="center" halign="center" text="Exit" />
			<ePixmap pixmap="MetrixHD/buttons/buttons.png" position="142,595" size="733,37" alphatest="blend" zPosition="100" />

			<widget name="key_red" position="156,595" size="236,37" zPosition="1" font="Regular; 18" halign="center" valign="center" backgroundColor="#9f1313" transparent="0" foregroundColor="#cccccc" />
			<widget name="key_green" position="401,595" size="236,37" zPosition="1" font="Regular; 18" halign="center" valign="center" backgroundColor="#1f771f" transparent="0" foregroundColor="#cccccc" />
			<widget name="key_yellow" position="646,595" size="236,37" zPosition="1" font="Regular; 18" halign="center" valign="center" backgroundColor="#a08500" transparent="0" foregroundColor="#cccccc" />

			<widget name="config" position="166,160" size="840,169" scrollbarMode="showOnDemand" font="Regular; 18" itemHeight="32" selectionPixmap="MetrixHD/SkinDesign/CoolNow.png" transparent="1" scrollbarSliderforegroundColor="#cccccc" scrollbarSliderBorderColor="#25062748" />
			<widget name="tempc"  position="166,366"  size="486,33" font="Regular; 18" valign="center" halign="left" />
			<widget name="voltc"  position="166,406"  size="486,33" font="Regular; 18" valign="center" halign="left" />
			<widget name="frqc"   position="166,446"  size="486,33" font="Regular; 18" valign="center" halign="left" />
			<widget name="frqc"   position="166,486"  size="486,33" font="Regular; 18" valign="center" halign="left" />

			<eLabel name="" position="1028,248" size="96,33" font="Regular; 18" valign="center" halign="center" text="OK" />
			</screen>"""
		else:
			self.skin = """
			<screen  position="0,0" size="1920,1080" title="CPU Frequency Setup" flags="wfNoBorder" backgroundColor="#25062748">
			<widget source="Title" render="Label" position="210,140" size="1500,68" zPosition="2" halign="center" font="Regular; 36" backgroundColor="#25062748" transparent="1" valign="center" />
			<ePixmap name="" position="210,150" size="1500,820" pixmap="MetrixHD/ibts/background.png" zPosition="-10" />
			<eLabel name="" position="235,227" size="1283,648" zPosition="-5" />
			<ePixmap pixmap="enigma2/icon/default.png" position="1567,284" size="90,70" zPosition="1" />
			<eLabel name="" position="1542,435" size="145,50" font="Regular; 28" valign="center" halign="center" text="Exit" />
			<ePixmap pixmap="MetrixHD/buttons/buttons.png" position="214,893" size="1100,56" alphatest="blend" zPosition="100" />
			<widget name="key_red" position="235,893" size="354,56" zPosition="1" font="Regular; 28" halign="center" valign="center" backgroundColor="#9f1313" transparent="0" foregroundColor="#cccccc" />
			<widget name="key_green" position="602,893" size="354,56" zPosition="1" font="Regular; 28" halign="center" valign="center" backgroundColor="#1f771f" transparent="0" foregroundColor="#cccccc" />
			<widget name="key_yellow" position="969,893" size="354,56" zPosition="1" font="Regular; 28" halign="center" valign="center" backgroundColor="#a08500" transparent="0" foregroundColor="#cccccc" />
			<widget name="config" position="250,240" size="1260,244" scrollbarMode="showOnDemand" font="Regular; 28" itemHeight="48" selectionPixmap="MetrixHD/SkinDesign/CoolNow.png" transparent="1" scrollbarSliderforegroundColor="#cccccc" scrollbarSliderBorderColor="#25062748" />
			<widget name="tempc"  position="250,550"  size="680,50" font="Regular; 28" valign="center" halign="left" />
			<widget name="voltc"  position="250,610"  size="680,50" font="Regular; 28" valign="center" halign="left" />
			<widget name="frqc"   position="250,670"  size="680,50" font="Regular; 28" valign="center" halign="left" />
			<widget name="frqc2"   position="250,730"  size="680,50" font="Regular; 28" valign="center" halign="left" />

			<eLabel name="" position="1542,372" size="145,50" font="Regular; 28" valign="center" halign="center" text="OK" />
			</screen>"""

		Screen.__init__(self, session)
		self.onClose.append(self.abort)
		self.onChangedEntry = []
		self.list = []
		ConfigListScreen.__init__(self, self.list, session=self.session, on_change=self.changedEntry)
		self.createSetup()
		self["key_red"] = Button(_("Cancel"))
		self["key_green"] = Button(_("Save"))
		self["key_yellow"] = Button(_("Test"))
		self["setupActions"] = ActionMap(["SetupActions", "ColorActions"], {"save": self.save,
		"cancel": self.cancel,
		"ok": self.save,
		"yellow": self.Test}, -2)

	def createSetup(self):
		print("[AmlFRQ] createSetup initializing")
		self.editListEntry = None
		self.list = []
		self.list.append(getConfigListEntry(_("Set MAX CPU frequency for cores 0 and 1"), config.plugins.aml.maxfrq))
		self.list.append(getConfigListEntry(_("Set MIN CPU frequency for cores 0 and 1"), config.plugins.aml.minfrq))
		self.list.append(getConfigListEntry(_("Set MAX CPU frequency for cores 2, 3, 4 and 5"), config.plugins.aml.maxfrq2))
		self.list.append(getConfigListEntry(_("Set MIN CPU frequency for cores 2, 3, 4 and 5"), config.plugins.aml.minfrq2))
		self.list.append(getConfigListEntry(_("Set Scaling governor"), config.plugins.aml.governor))
		self["config"].list = self.list
		self["config"].l.setList(self.list)
		self["tempc"] = Label()
		self["voltc"] = Label()
		self["frqc"] = Label()
		self["frqc2"] = Label()
		self.timer = eTimer()
		if self.getcurrentData not in self.timer.callback:
			print("[AmlFRQ] createSetup in Timer")
			self.timer.callback.append(self.getcurrentData)
			self.timer.start(2000, True)

	def getcurrentData(self):
		self.temp = "N/A"
		self.voltage = "N/A"
		self.cfrq = "N/A"
		self.cfrq2 = "N/A"
		try:
			with open("/sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq", "r") as fd:
				self.cfrq = fd.read().strip()
			with open("/sys/devices/system/cpu/cpu2/cpufreq/scaling_cur_freq", "r") as fd:
				self.cfrq2 = fd.read().strip()
			with open("/proc/stb/fp/temp_sensor_avs", "r") as fd:
				self.temp = fd.read().strip()
			with open("/sys/devices/system/cpu/cpufreq/policy0/brcm_avs_voltage", "r") as fd:
				self.voltage = fd.read().strip()
		except Exception:
			pass
		try:
			self.cfrq = str(int(self.cfrq) / 1000)
			self.cfrq2 = str(int(self.cfrq2) / 1000)
			self.voltage = str(int(self.voltage, 16))
		except Exception:
			pass

		self["tempc"].setText(_("Current Temperature (SoC): %s °C") % self.temp)
		self.icfrq = int(float(self.cfrq))
		if self.icfrq >= 500 and self.icfrq <= 1200:
			self.voltage = "0.731"
		elif self.icfrq == 1398:
			self.voltage = "0.761"
		elif self.icfrq == 1512:
			self.voltage = "0.791"
		elif self.icfrq == 1608:
			self.voltage = "0.831"
		elif self.icfrq == 1704:
			self.voltage = "0.961"
		elif self.icfrq == 1800:
			self.voltage = "0.981"
		self["voltc"].setText(_("Current CPU cores 0 and 1 Voltage: %s V") % self.voltage)
		self["frqc"].setText(_("Current CPU Frequency cores 0 and 1: %s MHz") % self.cfrq)
		self["frqc2"].setText(_("Current CPU Frequency other cores: %s MHz") % self.cfrq2)
		self.timer.start(1000, True)

	def changedEntry(self):
		for x in self.onChangedEntry:
			x()
		self.newConfig()

	def newConfig(self):
		print(self["config"].getCurrent()[0])
		if self["config"].getCurrent()[0] == _("Start Boot Frequency"):
			self.createSetup()

	def abort(self):
		self.timer.stop()
		if self.getcurrentData in self.timer.callback:
			self.timer.callback.remove(self.getcurrentData)
		print("[AmlFRQ] aborting")

	def save(self):
		for x in self["config"].list:
			x[1].save()

		configfile.save()
		initBooster()
		self.close()

	def cancel(self):
		initBooster()
		for x in self["config"].list:
			x[1].cancel()

		self.close()

	def Test(self):
		initBooster()


class U5_Booster:

	def __init__(self, session):
		print("[AmlFRQ] Booster initializing")
		self.session = session
		self.service = None
		self.onClose = []
		initBooster()

	def shutdown(self):
		self.abort()

	def abort(self):
		self.timer.stop()
		if self.getcurrentData in self.timer.callback:
			self.timer.callback.remove(self.getcurrentData)
		print("[AmlFRQ] Booster aborting")

	config.misc.standbyCounter.addNotifier(standbyCounterChanged, initial_call=False)


def main(menuid):
	return [(_("CPU Control"), startBooster, "CPU Control", None)] if menuid == "system" else []


def startBooster(session, **kwargs):
	session.open(AmlFRQ)


wbooster = None
gReason = -1
mySession = None


def dinobotbooster():
	global wbooster
	global mySession
	global gReason
	if gReason == 0 and mySession != None and wbooster == None:
		print("[AmlFRQ] booster Starting !!")
		wbooster = U5_Booster(mySession)
	elif gReason == 1 and wbooster != None:
		print("[AmlFRQ] booster Stopping !!")
		wbooster = None


def sessionstart(reason, **kwargs):
	global mySession
	global gReason
	print("[AmlFRQ] sessionstart")
	if "session" in kwargs:
		mySession = kwargs["session"]
	else:
		gReason = reason
	dinobotbooster()


def Plugins(**kwargs):
	return [PluginDescriptor(where=[PluginDescriptor.WHERE_AUTOSTART, PluginDescriptor.WHERE_SESSIONSTART], fnc=sessionstart), PluginDescriptor(name="FRQ Setup", description="Set CPU speed settings", where=PluginDescriptor.WHERE_MENU, fnc=main)]
