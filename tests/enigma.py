# fake-enigma


class slot:
	def __init__(self):
		self.list = []

	def get(self):
		return self.list

	def __call__(self):
		for x in self.list:
			x()


timers = set()

import time  # noqa: E402

from events import eventfnc  # noqa: E402

##################### ENIGMA BASE


class eTimer:
	def __init__(self):
		self.timeout = slot()
		self.next_activation = None
		print("NEW TIMER")

	def start(self, msec, singleshot=False):
		print("start timer", msec)
		self.next_activation = time.time() + msec / 1000.0
		self.msec = msec
		self.singleshot = singleshot
		timers.add(self)

	def stop(self):
		timers.remove(self)

	def __repr__(self):
		return f"<eTimer timeout={repr(self.timeout)} next_activation={repr(self.next_activation)} singleshot={repr(self.singleshot)}>"

	def do(self):
		if self.singleshot:
			self.stop()
		self.next_activation += self.msec / 1000.0
		self.timeout()


def runIteration():
	running_timers = list(timers)
	assert len(running_timers), "no running timers, so nothing will ever happen!"
	running_timers.sort(key=lambda x: x.next_activation)

	print("running:", running_timers)

	next_timer = running_timers[0]

	now = time.time()
	delay = next_timer.next_activation - now

	if delay > 0:
		time.sleep(delay)
		now += delay

	while len(running_timers) and running_timers[0].next_activation <= now:
		running_timers[0].do()
		running_timers = running_timers[1:]


stopped = False


def stop():
	global stopped
	stopped = True


def run(duration=1000):
	stoptimer = eTimer()
	stoptimer.start(duration * 1000.0)
	stoptimer.callback.append(stop)
	while not stopped:
		runIteration()


##################### ENIGMA GUI

eSize = None
ePoint = None
gFont = None
eWindow = None
eLabel = None
ePixmap = None
eWindowStyleManager = None
loadPNG = None
addFont = None
gRGB = None
eWindowStyleSkinned = None
eButton = None
eListboxPythonStringContent = None
eListbox = None
eSubtitleWidget = None


class eEPGCache:
	@classmethod
	def getInstance(self):
		return self.instance

	instance = None

	def __init__(self):
		eEPGCache.instance = self

	def lookupEventTime(self, ref, query):
		return None


eEPGCache()

getBestPlayableServiceReference = None


class pNavigation:
	def __init__(self):
		self.m_event = slot()
		self.m_record_event = slot()

	@eventfnc
	def recordService(self, service):
		return iRecordableService(service)

	@eventfnc
	def stopRecordService(self, service):
		service.stop()

	@eventfnc
	def playService(self, service):
		return None

	def __repr__(self):
		return "pNavigation"


eRCInput = None
getPrevAsciiCode = None


class eServiceReference:

	isDirectory = 1
	mustDescent = 2
	canDescent = 4
	flagDirectory = isDirectory | mustDescent | canDescent
	shouldSort = 8
	hasSortKey = 16
	sort1 = 32
	isMarker = 64
	isGroup = 128

	def __init__(self, ref):
		self.ref = ref
		self.flags = 0

	def toString(self):
		return self.ref

	def __repr__(self):
		return self.toString()


class iRecordableService:
	def __init__(self, ref):
		self.ref = ref

	@eventfnc
	def prepare(self, filename, begin, end, event_id):
		return 0

	@eventfnc
	def start(self):
		return 0

	@eventfnc
	def stop(self):
		return 0

	def __repr__(self):
		return f"iRecordableService({repr(self.ref)})"


quitMainloop = None


eDVBVolumecontrol = None


class eRFmod:
	@classmethod
	def getInstance(self):
		return self.instance

	instance = None

	def __init__(self):
		eRFmod.instance = self

	def setFunction(self, value):
		print(f"[eRFmod] set function to {value}")

	def setTestmode(self, value):
		print(f"[eRFmod] set testmode to {value}")

	def setSoundFunction(self, value):
		print(f"[eRFmod] set sound function to {value}")

	def setSoundCarrier(self, value):
		print(f"[eRFmod] set sound carrier to {value}")

	def setChannel(self, value):
		print(f"[eRFmod] set channel to {value}")

	def setFinetune(self, value):
		print(f"[eRFmod] set finetune to {value}")


eRFmod()


class eDBoxLCD:
	@classmethod
	def getInstance(self):
		return self.instance

	instance = None

	def __init__(self):
		eDBoxLCD.instance = self

	def setLCDBrightness(self, value):
		print(f"[eDBoxLCD] set brightness to {value}")

	def setLCDContrast(self, value):
		print(f"[eDBoxLCD] set contrast to {value}")

	def setLED(self, value):
		print(f"[eDBoxLCD] set led button to {value}")

	def setInverted(self, value):
		print(f"[eDBoxLCD] set inverted to {value}")


eDBoxLCD()

Misc_Options = None


class eServiceCenter:
	@classmethod
	def getInstance(self):
		return self.instance

	instance = None

	def __init__(self):
		eServiceCenter.instance = self

	def info(self, ref):
		return None


eServiceCenter()

##################### ENIGMA CHROOT

print("import directories")
import Tools.Directories  # noqa: E402
print("done")

chroot = "."

for (x, (y, z)) in Tools.Directories.defaultPaths.items():
	Tools.Directories.defaultPaths[x] = (chroot + y, z)

Tools.Directories.defaultPaths[Tools.Directories.SCOPE_SKINS] = ("../data/", Tools.Directories.PATH_DONTCREATE)
Tools.Directories.defaultPaths[Tools.Directories.SCOPE_CONFIG] = ("/etc/enigma2/", Tools.Directories.PATH_DONTCREATE)

##################### ENIGMA CONFIG

print("import config")
import Components.config  # noqa: E402
print("done")

my_config = [
"config.skin.primary_skin=None\n"
]

Components.config.config.unpickle(my_config)

##################### ENIGMA ACTIONS


class eActionMap:
	def __init__(self):
		pass


##################### ENIGMA STARTUP:

def init_nav():
	print("init nav")
	import Navigation
	import NavigationInstance
	NavigationInstance.instance = Navigation.Navigation()


def init_record_config():
	print("init recording")
	import Components.RecordingConfig
	Components.RecordingConfig.InitRecordingConfig()


def init_parental_control():
	print("init parental")
	from Components.ParentalControl import InitParentalControl
	InitParentalControl()


def init_all():
	# this is stuff from StartEnigma.py
	init_nav()

	init_record_config()
	init_parental_control()

	import Components.InputDevice
	Components.InputDevice.InitInputDevices()

	import Components.AVSwitch
	Components.AVSwitch.InitAVSwitch()

	import Components.UsageConfig
	Components.UsageConfig.InitUsageConfig()

	import Components.Network
	Components.Network.InitNetwork()

	import Components.Lcd
	Components.Lcd.InitLcd()

	import Components.RFmod
	Components.RFmod.InitRFmod()

	import Screens.Ci
	Screens.Ci.InitCiConfig()
