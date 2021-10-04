from fcntl import ioctl
from os import listdir, open as osopen, close as osclose, write as oswrite, O_RDWR, O_NONBLOCK
from os.path import isdir, isfile
from platform import machine
from boxbranding import getBoxType, getBrandOEM
from struct import pack

from enigma import eRCInput

from keyids import KEYIDS, KEYIDNAMES
from Components.config import ConfigSubsection, ConfigInteger, ConfigSelection, ConfigYesNo, ConfigText, ConfigSlider, config
from Components.SystemInfo import BoxInfo
from Tools.Directories import SCOPE_KEYMAPS, SCOPE_SKINS, fileReadLine, fileWriteLine, fileReadLines, fileReadXML, resolveFilename, pathExists

from six import ensure_str
MODULE_NAME = __name__.split(".")[-1]

REMOTE_MODEL = 0
REMOTE_RCTYPE = 1
REMOTE_NAME = 2
REMOTE_DISPLAY_NAME = 3

config.inputDevices = ConfigSubsection()


class InputDevices:
	def __init__(self):
		self.Devices = {}
		self.currentDevice = ""
		devices = listdir("/dev/input/")

		for device in devices:
			if isdir("/dev/input/%s" % device):
				continue
			try:
				_buffer = "\0" * 512
				self.fd = osopen("/dev/input/%s" % device, O_RDWR | O_NONBLOCK)
				self.name = ioctl(self.fd, self.EVIOCGNAME(256), _buffer)
				self.name = self.name[:self.name.find(b"\0")]
				self.name = ensure_str(self.name)
				if str(self.name).find("Keyboard") != -1:
					self.name = 'keyboard'
				osclose(self.fd)
			except (IOError, OSError) as err:
				print("[InputDevice] Error: device='%s' getInputDevices <ERROR: ioctl(EVIOCGNAME): '%s'>" % (device, str(err)))
				self.name = None

			if self.name:
				self.Devices[device] = {
					'name': self.name,
					'type': self.getInputDeviceType(self.name),
					'enabled': False,
					'configuredName': None
				}

				# load default remote control "delay" and "repeat" values for ETxxxx ("QuickFix Scrollspeed Menues" proposed by Xtrend Support)
				if getBoxType().startswith('et'):
					self.setDeviceDefaults(device) 

	def EVIOCGNAME(self, length):
		# include/uapi/asm-generic/ioctl.h
		IOC_NRBITS = 8
		IOC_TYPEBITS = 8
		IOC_SIZEBITS = 13 if "mips" in machine() else 14
		IOC_NRSHIFT = 0
		IOC_TYPESHIFT = IOC_NRSHIFT + IOC_NRBITS
		IOC_SIZESHIFT = IOC_TYPESHIFT + IOC_TYPEBITS
		IOC_DIRSHIFT = IOC_SIZESHIFT + IOC_SIZEBITS
		IOC_READ = 2
		return (IOC_READ << IOC_DIRSHIFT) | (length << IOC_SIZESHIFT) | (0x45 << IOC_TYPESHIFT) | (0x06 << IOC_NRSHIFT)

	def getInputDeviceType(self, name):
		if "remote control" in name:
			return "remote"
		elif "keyboard" in name:
			return "keyboard"
		elif "mouse" in name:
			return "mouse"
		else:
			print("[InputDevices] Unknown device type: %s" % name)
			return None

	def getDeviceList(self):
		return sorted(list(self.Devices.keys()))

	# struct input_event {
	# 	struct timeval time;    -> ignored
	# 	__u16 type;             -> EV_REP (0x14)
	# 	__u16 code;             -> REP_DELAY (0x00) or REP_PERIOD (0x01)
	# 	__s32 value;            -> DEFAULTS: 700(REP_DELAY) or 100(REP_PERIOD)
	# }; -> size = 16
	#
	def setDeviceDefaults(self, device):
		print("[InputDevices] setDeviceDefaults for device %s" % device)
		self.setDeviceAttribute(device, 'configuredName', None)
		eventRepeat = pack("LLHHi", 0, 0, 0x14, 0x01, 100)
		eventDelay = pack("LLHHi", 0, 0, 0x14, 0x00, 700)
		fd = osopen("/dev/input/%s" % device, O_RDWR)
		oswrite(fd, eventRepeat)
		oswrite(fd, eventDelay)
		osclose(fd)

	def setDeviceEnabled(self, device, value):
		oldVal = self.getDeviceAttribute(device, 'enabled')
		# print "[InputDevices] setDeviceEnabled for device %s to %s from %s" % (device,value,oldval)
		self.setDeviceAttribute(device, 'enabled', value)
		if oldVal is True and value is False:
			self.setDeviceDefaults(device)

	def getDeviceName(self, device):
		if device in list(self.Devices.keys()):
			return self.Devices[device].get("name", device)
		return "Unknown device name"

	def setDeviceName(self, device, value):
		# print "[InputDevices] setDeviceName for device %s to %s" % (device,value)
		self.setDeviceAttribute(device, 'configuredName', value)

	def setDeviceDelay(self, device, value): # REP_DELAY
		if self.getDeviceAttribute(device, 'enabled'):
			# print("[InputDevices] setDeviceDelay for device %s to %d ms" % (device, value))
			event = pack('LLHHi', 0, 0, 0x14, 0x00, int(value))
			fd = osopen("/dev/input/" + device, O_RDWR)
			oswrite(fd, event)
			osclose(fd)

	def setDeviceRepeat(self, device, value): # REP_PERIOD
		if self.getDeviceAttribute(device, 'enabled'):
			# print("[InputDevices] setDeviceRepeat for device %s to %d ms" % (device, value))
			event = pack('LLHHi', 0, 0, 0x14, 0x01, int(value))
			fd = osopen("/dev/input/" + device, O_RDWR)
			oswrite(fd, event)
			osclose(fd)

	def getDeviceAttribute(self, device, attribute):
		if device in self.Devices and attribute in self.Devices[device]:
			return self.Devices[device][attribute]
		return None

	def setDeviceAttribute(self, device, attribute, value):
		# print "[InputDevices] setting for device", device, "attribute", attribute, " to value", value
		if device in self.Devices:
			self.Devices[device][attribute] = value




class RemoteControl:
	knownCompatibleRemotes = [
		("gb0", "gb1", "gb2", "gb3", "gb4"),
		("ini0", "ini1", "ini2", "ini3", "ini4", "ini5", "ini6", "ini7", "ini8"),
		("wetek", "wetek2", "wetek3"),
		("zgemma1", "zgemma2", "zgemma3", "zgemma4", "zgemma5", "zgemma6", "zgemma7", "evo6", "evo7")
	]

	def __init__(self):
		self.model = BoxInfo.getItem("model")
		self.rcName = BoxInfo.getItem("rcname")
		self.rcType = self.readRemoteControlType()
		remotes = fileReadXML(resolveFilename(SCOPE_SKINS, "remotes.xml"), source=MODULE_NAME)
		self.remotes = []
		if remotes:
			for remote in sorted(remotes.findall("remote"), key=lambda remote: (remote.tag, remote.get("displayName"))):
				model = remote.attrib.get("model")
				rcType = remote.attrib.get("rcType")
				codeName = remote.attrib.get("codeName")
				displayName = remote.attrib.get("displayName")
				if codeName and displayName:
					if config.crash.debugRemoteControls.value:
						print("[InputDevice] Adding remote control identifier for '%s'." % displayName)
					self.remotes.append((model, rcType, codeName, displayName))
		self.remotes.insert(0, ("", "", "", _("Default")))
		if BoxInfo.getItem("RemoteTypeZeroAllowed", False):
			self.remotes.insert(1, ("", "0", "", _("All supported")))
		rcChoices = []
		default = "0"
		for index, remote in enumerate(self.remotes):
			index = str(index)
			rcChoices.append((index, remote[REMOTE_DISPLAY_NAME]))
			if self.model == remote[REMOTE_MODEL] and self.rcType == remote[REMOTE_RCTYPE] and self.rcName in [x.strip() for x in remote[REMOTE_NAME].split(",")]:
				print("[InputDevice] Default remote control identified as '%s'.  (model='%s', rcName='%s', rcType='%s')" % (remote[REMOTE_DISPLAY_NAME], self.model, self.rcName, self.rcType))
				default = index
		config.inputDevices.remotesIndex = ConfigSelection(choices=rcChoices, default=default)
		self.remote = self.loadRemoteControl(BoxInfo.getItem("RCMapping"))

	def loadRemoteControl(self, filename):
		print("[InputDevice] Loading remote control '%s'." % filename)
		rcs = fileReadXML(filename, source=MODULE_NAME)
		rcButtons = {}
		if rcs:
			rc = rcs.find("rc")
			if rc:
				logRemaps = []
				remapButtons = {}
				placeHolder = 0
				rcButtons["keyIds"] = []
				rcButtons["image"] = rc.attrib.get("image")
				if config.crash.debugRemoteControls.value:
					print("[InputDevice] Remote control image file '%s'." % rcButtons["image"])
				for button in rc.findall("button"):
					id = button.attrib.get("id", "KEY_RESERVED")
					remap = button.attrib.get("remap")
					keyId = KEYIDS.get(id)
					remapId = KEYIDS.get(remap)
					if keyId is not None and remapId is not None:
						logRemaps.append((id, remap))
						remapButtons[keyId] = remapId
						keyId = remapId
					if keyId == 0:
						placeHolder -= 1
						keyId = placeHolder
					rcButtons["keyIds"].append(keyId)
					rcButtons[keyId] = {}
					rcButtons[keyId]["id"] = id
					rcButtons[keyId]["label"] = button.attrib.get("label")
					rcButtons[keyId]["pos"] = [int(x.strip()) for x in button.attrib.get("pos", "0").split(",")]
					rcButtons[keyId]["title"] = button.attrib.get("title")
					rcButtons[keyId]["shape"] = button.attrib.get("shape")
					rcButtons[keyId]["coords"] = [int(x.strip()) for x in button.attrib.get("coords", "0").split(",")]
					if config.crash.debugRemoteControls.value:
						print("[InputDevice] Remote control button id='%s', keyId='%s', label='%s', pos='%s', title='%s', shape='%s', coords='%s'." % (id, keyId, rcButtons[keyId]["label"], rcButtons[keyId]["pos"], rcButtons[keyId]["title"], rcButtons[keyId]["shape"], rcButtons[keyId]["coords"]))
				if logRemaps:
					for remap in logRemaps:
						print("[InputDevice] Remapping '%s' to '%s'." % (remap[0], remap[1]))
					for evdev, evdevinfo in sorted(iInputDevices.Devices.items()):
						if evdevinfo["type"] == "remote":
							result = eRCInput.getInstance().setKeyMapping(evdevinfo["name"], remapButtons)
							resStr = {
								eRCInput.remapOk: "Remap completed okay.",
								eRCInput.remapUnsupported: "Error: Remapping not supported on device!",
								eRCInput.remapFormatErr: "Error: Remap map in incorrect format!",
								eRCInput.remapNoSuchDevice: "Error: Unknown device!",
							}.get(result, "Error: Unknown error!")
							print("[InputDevice] Remote remap evdev='%s', name='%s': %s" % (evdev, evdevinfo["name"], resStr))
		return rcButtons

	def getRemoteControlKeyList(self):
		return self.remote["keyIds"]

	def getRemoteControlKeyLabel(self, keyId):
		if keyId in self.remote:
			return self.remote[keyId]["label"]
		print("[InputDevice] Button '%s' (%d) is not available on the current remote control." % (KEYIDNAMES.get(keyId), keyId))
		return None

	def getRemoteControlKeyPos(self, keyId):
		if keyId in self.remote:
			return self.remote[keyId]["pos"]
		print("[InputDevice] Button '%s' (%d) is not available on the current remote control." % (KEYIDNAMES.get(keyId), keyId))
		return None

	def readRemoteControlType(self):
		return fileReadLine("/proc/stb/ir/rc/type", "-1", source=MODULE_NAME)

	def writeRemoteControlType(self, rcType):
		if rcType > 0:
			fileWriteLine("/proc/stb/ir/rc/type", rcType, source=MODULE_NAME)

	def getOpenWebIfHTML(self):
		html = []
		error = False
		image = self.remote["image"]
		if image:
			html.append("<img border=\"0\" src=\"%s\" usemap=\"#map\" />" % image)
			html.append("<map name=\"map\">")
			for keyId in self.remote["keyIds"]:
				attribs = []
				title = self.remote[keyId]["title"]
				if title:
					attribs.append("title=\"%s\"" % title)
				else:
					error = True
				shape = self.remote[keyId]["shape"]
				if shape:
					attribs.append("shape=\"%s\"" % shape)
				else:
					error = True
				coords = ",".join([str(x) for x in self.remote[keyId]["coords"]])
				if coords:
					attribs.append("coords=\"%s\"" % coords)
				else:
					error = True
				if keyId > 0:
					attribs.append("onclick=\"pressMenuRemote('%d');\"" % keyId)
				html.append("\t<area %s />" % " ".join(attribs))
			html.append("</map>")
		else:
			error = True
		return None if error else "\n".join(html)


class InitInputDevices:
	def __init__(self):
		self.currentDevice = ""
		for device in sorted(list(iInputDevices.Devices.keys())):
			# print "[InitInputDevices] -> creating config entry for device: %s -> %s  " % (self.currentDevice, iInputDevices.Devices[device]["name"])
			self.currentDevice = device
			self.setupConfigEntries(self.currentDevice)
			self.currentDevice = ""

	def setupConfigEntries(self, device):
		setattr(config.inputDevices, device, ConfigSubsection())
		configItem = getattr(config.inputDevices, device)
		model = BoxInfo.getItem("model")
		configItem.enabled = ConfigYesNo(default=(model == 'dm800' or model == 'azboxhd'))
		configItem.enabled.addNotifier(self.inputDevicesEnabledChanged)
		configItem.name = ConfigText(default="")
		configItem.name.addNotifier(self.inputDevicesNameChanged)
		repeat = 100
		if model in ('maram9', 'classm', 'axodin', 'axodinc', 'starsatlx', 'genius', 'evo', 'galaxym6'):
			repeat = 400
		elif model == 'azboxhd':
			repeat = 150
		configItem.repeat = ConfigSlider(default=repeat, increment = 10, limits=(0, 500))
		configItem.repeat.addNotifier(self.inputDevicesRepeatChanged)
		if model in ('maram9', 'classm', 'axodin', 'axodinc', 'starsatlx', 'genius', 'evo', 'galaxym6'):
			delay = 200
		else:
			delay = 700
		configItem.delay = ConfigSlider(default=delay, increment = 100, limits=(0, 5000))
		configItem.delay.addNotifier(self.inputDevicesDelayChanged)

	def inputDevicesEnabledChanged(self, configElement):
		if self.currentDevice != "" and iInputDevices.currentDevice == "":
			iInputDevices.setDeviceEnabled(self.currentDevice, configElement.value)
		elif iInputDevices.currentDevice != "":
			iInputDevices.setDeviceEnabled(iInputDevices.currentDevice, configElement.value)

	def inputDevicesNameChanged(self, configElement):
		if self.currentDevice != "" and iInputDevices.currentDevice == "":
			iInputDevices.setDeviceName(self.currentDevice, configElement.value)
			if configElement.value != "":
				devname = iInputDevices.getDeviceAttribute(self.currentDevice, 'name')
				if devname != configElement.value:
					configItem = getattr(config.inputDevices, "%s.enabled" % self.currentDevice)
					configItem.value = False
					configItem.save()
		elif iInputDevices.currentDevice != "":
			iInputDevices.setDeviceName(iInputDevices.currentDevice, configElement.value)

	def inputDevicesDelayChanged(self, configElement):
		if self.currentDevice != "" and iInputDevices.currentDevice == "":
			iInputDevices.setDeviceDelay(self.currentDevice, configElement.value)
		elif iInputDevices.currentDevice != "":
			iInputDevices.setDeviceDelay(iInputDevices.currentDevice, configElement.value)

	def inputDevicesRepeatChanged(self, configElement):
		if self.currentDevice != "" and iInputDevices.currentDevice == "":
			iInputDevices.setDeviceRepeat(self.currentDevice, configElement.value)
		elif iInputDevices.currentDevice != "":
			iInputDevices.setDeviceRepeat(iInputDevices.currentDevice, configElement.value)


iInputDevices = InputDevices()


class RcTypeControl():
	def __init__(self):
		if pathExists('/proc/stb/ir/rc/type') and getBrandOEM() not in ('gigablue', 'odin', 'ini', 'entwopia', 'tripledot'):
			self.isSupported = True

			if config.plugins.remotecontroltype.rctype.value != 0:
				self.writeRcType(config.plugins.remotecontroltype.rctype.value)
		else:
			self.isSupported = False

	def multipleRcSupported(self):
		return self.isSupported

	def writeRcType(self, rctype):
		fd = open('/proc/stb/ir/rc/type', 'w')
		fd.write('%d' % rctype)
		fd.close()


iRcTypeControl = RcTypeControl()
remoteControl = RemoteControl()
