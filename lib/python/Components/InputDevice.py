from fcntl import ioctl
from os import O_NONBLOCK, O_RDWR, close as osclose, listdir, open as osopen, write as oswrite
from os.path import exists, isdir, isfile, join
from platform import machine
from struct import pack

from enigma import eRCInput

from keyids import KEYIDS, KEYIDNAMES
from Components.config import ConfigSelection, ConfigSlider, ConfigSubsection, ConfigText, ConfigYesNo, config
from Components.Console import Console
from Components.International import international
from Components.SystemInfo import BoxInfo
from Tools.Directories import SCOPE_KEYMAPS, SCOPE_SKINS, fileReadLine, fileReadLines, fileReadXML, fileWriteLine, resolveFilename

MODULE_NAME = __name__.split(".")[-1]

config.inputDevices = ConfigSubsection()


class InputDevices:
	def __init__(self):
		self.devices = {}
		self.currentDevice = None
		for device in sorted(listdir("/dev/input/")):

			if isdir(join("/dev/input", device)):
				continue
			try:
				_buffer = "\0" * 512
				self.fd = osopen(join("/dev/input", device), O_RDWR | O_NONBLOCK)
				self.name = ioctl(self.fd, self.EVIOCGNAME(256), _buffer)
				self.name = self.name[:self.name.find(b"\0")].decode()
				if str(self.name).find("Keyboard") != -1:
					self.name = "keyboard"
				osclose(self.fd)
			except OSError as err:
				print(f"[InputDevice] Error: device='{device}' getInputDevices <ERROR: ioctl(EVIOCGNAME): '{str(err)}'>")
				self.name = None

			if self.name:
				devType = self.getInputDeviceType(self.name.lower())
				print(f"[InputDevice] Found device '{device}' with name '{self.name}' of type '{'Unknown' if devType is None else devType.capitalize()}'.")
				# What was this for?
				# if self.name == "aml_keypad":
				# 	print("[InputDevice] ALERT: Old code flag for 'aml_keypad'.")
				# 	self.name = "dreambox advanced remote control (native)"
				# if self.name in BLACKLIST:
				# 	print("[InputDevice] ALERT: Old code flag for device in blacklist.")
				# 	continue
				self.devices[device] = {
					"name": self.name,
					"type": devType,
					"enabled": False,
					"configuredName": None
				}

				# Load default remote control "delay" and "repeat" values for ETxxxx ("QuickFix Scrollspeed Menues" proposed by Xtrend Support).
				if BoxInfo.getItem("machinebuild").startswith("et"):
					self.setDeviceDefaults(device)

	def EVIOCGNAME(self, length):
		# Include/uapi/asm-generic/ioctl.h.
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
			print(f"[InputDevice] Warning: Unknown device type: '{name}'!")
			return None

	def getDeviceList(self):
		return sorted(list(self.devices.keys()))

	# struct input_event {
	# 	struct timeval time;    -> ignored
	# 	__u16 type;             -> EV_REP (0x14)
	# 	__u16 code;             -> REP_DELAY (0x00) or REP_PERIOD (0x01)
	# 	__s32 value;            -> DEFAULTS: 700(REP_DELAY) or 100(REP_PERIOD)
	# }; -> size = 16
	#
	def setDeviceDefaults(self, device):
		print(f"[InputDevice] setDeviceDefaults DEBUG: Device '{device}'.")
		self.setDeviceAttribute(device, "configuredName", None)
		eventRepeat = pack("LLHHi", 0, 0, 0x14, 0x01, 100)
		eventDelay = pack("LLHHi", 0, 0, 0x14, 0x00, 700)
		fd = osopen(join("/dev/input", device), O_RDWR)
		oswrite(fd, eventRepeat)
		oswrite(fd, eventDelay)
		osclose(fd)

	def setDeviceEnabled(self, device, value):
		oldVal = self.getDeviceAttribute(device, "enabled")
		# print(f"[InputDevices] setDeviceEnabled for device '{device}' to '{value}' from '{oldval}'.")
		self.setDeviceAttribute(device, "enabled", value)
		if oldVal is True and value is False:
			self.setDeviceDefaults(device)

	def getDeviceName(self, device):
		if device in list(self.devices.keys()):
			return self.devices[device].get("name", device)
		return "Unknown device name"

	def setDeviceName(self, device, value):
		# print(f"[InputDevices] setDeviceName for device '{device}' to '{value}'.")
		self.setDeviceAttribute(device, "configuredName", value)

	def setDeviceDelay(self, device, value):  # REP_DELAY.
		if self.getDeviceAttribute(device, "enabled"):
			# print(f"[InputDevices] setDeviceDelay for device '{device}' to {value} ms.")
			event = pack("LLHHi", 0, 0, 0x14, 0x00, int(value))
			fd = osopen(join("/dev/input", device), O_RDWR)
			oswrite(fd, event)
			osclose(fd)

	def setDeviceRepeat(self, device, value):  # REP_PERIOD.
		if self.getDeviceAttribute(device, "enabled"):
			# print(f"[InputDevices] setDeviceRepeat for device '{device}' to {value} ms.")
			event = pack("LLHHi", 0, 0, 0x14, 0x01, int(value))
			fd = osopen(join("/dev/input", device), O_RDWR)
			oswrite(fd, event)
			osclose(fd)

	def getDeviceAttribute(self, device, attribute):
		if device in self.devices and attribute in self.devices[device]:
			return self.devices[device][attribute]
		return None

	def setDeviceAttribute(self, device, attribute, value):
		# print "[InputDevices] setting for device", device, "attribute", attribute, " to value", value
		if device in self.devices:
			self.devices[device][attribute] = value


class Keyboard:
	KEYBOARD_KMAP = 0
	KEYBOARD_PATH = 1
	KEYBOARD_NAME = 2
	KEYBOARD_DISPLAY_NAME = 3

	def __init__(self):
		self.keyboards = []
		keyboards = fileReadXML(resolveFilename(SCOPE_KEYMAPS, "keyboards.xml"), source=MODULE_NAME)
		if keyboards is not None:
			for keyboard in sorted(keyboards.findall("keyboard"), key=lambda keyboard: (keyboard.tag, keyboard.get("name"))):
				keyboardKmap = keyboard.attrib.get("kmap")
				keyboardName = keyboard.attrib.get("name")
				if keyboardKmap and keyboardName:
					keyboardKmapPath = resolveFilename(SCOPE_KEYMAPS, keyboardKmap)
					if isfile(keyboardKmapPath):
						if config.crash.debugKeyboards.value:
							print(f"[InputDevice] Adding keyboard definition '{keyboardKmap}' for '{keyboardName}'.")
						self.keyboards.append((keyboardKmap, keyboardKmapPath, keyboardName, _(keyboardName)))
					else:
						print(f"[InputDevice] Error: Keyboard definition '{keyboardKmapPath}' doesn't exist for '{keyboardName}'!")
				else:
					print(f"[InputDevice] Error: Keyboard definition is invalid!  (kmap='{keyboardKmap}', name='{keyboardName}')")
		languageDefault = f"{international.getLanguageKeyboard()}.kmap"
		keyboardChoices = []
		default = 0
		for index, keyboard in enumerate(self.keyboards):
			keyboardChoices.append((index, keyboard[self.KEYBOARD_DISPLAY_NAME]))
			if languageDefault == keyboard[self.KEYBOARD_KMAP]:
				print(f"[InputDevice] Default keyboard identified as '{keyboard[self.KEYBOARD_DISPLAY_NAME]}' using '{keyboard[self.KEYBOARD_KMAP]}'.")
				default = index
		config.inputDevices.keyboardsIndex = ConfigSelection(default=default, choices=keyboardChoices)
		self.loadKeyboard(config.inputDevices.keyboardsIndex.value)

	def loadKeyboard(self, index):
		if 0 <= index < len(self.keyboards):
			path = self.keyboards[index][self.KEYBOARD_PATH]
			print(f"[InputDevice] Loading selected keyboard '{self.keyboards[index][self.KEYBOARD_NAME]}' from '{path}'.")
			if isfile(path):
				Console().ePopen(f"/sbin/loadkmap < {path}")
			else:
				print(f"[InputDevice] Error: Keyboard definition '{path}' does not exist!")
		else:
			print(f"[InputDevice] Error: Keyboard definition index '{index}' is invalid!")


class RemoteControl:
	REMOTE_MODEL = 0
	REMOTE_RCTYPE = 1
	REMOTE_NAME = 2
	REMOTE_DISPLAY_NAME = 3

	knownCompatibleRemotes = [
		("gb0", "gb1", "gb2", "gb3", "gb4"),
		("ini0", "ini1", "ini2", "ini3", "ini4", "ini5", "ini6", "ini7", "ini8"),
		("zgemma1", "zgemma2", "zgemma3", "zgemma4", "zgemma5", "zgemma6", "zgemma7", "evo6", "evo7")
	]

	def __init__(self):
		self.model = BoxInfo.getItem("model")
		self.rcName = BoxInfo.getItem("rcname")
		self.rcType = self.readRemoteControlType()
		remotes = fileReadXML(resolveFilename(SCOPE_SKINS, "remotes.xml"), source=MODULE_NAME)
		self.remotes = []
		if remotes is not None:
			for remote in sorted(remotes.findall("remote"), key=lambda remote: (remote.tag, remote.get("displayName"))):
				model = remote.attrib.get("model")
				rcType = remote.attrib.get("rcType")
				codeName = remote.attrib.get("codeName")
				displayName = remote.attrib.get("displayName")
				if codeName and displayName:
					if config.crash.debugRemoteControls.value:
						print(f"[InputDevice] Adding remote control identifier for '{displayName}'.")
					self.remotes.append((model, rcType, codeName, displayName))
		self.remotes.insert(0, ("", "", "", _("Default")))
		if BoxInfo.getItem("RemoteTypeZeroAllowed", False):
			self.remotes.insert(1, ("", "0", "", _("All supported")))
		rcChoices = []
		default = "0"
		for index, remote in enumerate(self.remotes):
			index = str(index)
			rcChoices.append((index, remote[self.REMOTE_DISPLAY_NAME]))
			if self.model == remote[self.REMOTE_MODEL] and self.rcType == remote[self.REMOTE_RCTYPE] and self.rcName in [x.strip() for x in remote[self.REMOTE_NAME].split(",")]:
				print(f"[InputDevice] Default remote control identified as '{remote[self.REMOTE_DISPLAY_NAME]}'.  (model='{self.model}', rcName='{self.rcName}', rcType='{self.rcType}')")
				default = index
		config.inputDevices.remotesIndex = ConfigSelection(choices=rcChoices, default=default)
		self.remote = self.loadRemoteControl(BoxInfo.getItem("RCMapping"))

	def loadRemoteControl(self, filename):
		print(f"[InputDevice] Loading remote control '{filename}'.")
		rcs = fileReadXML(filename, source=MODULE_NAME)
		rcButtons = {}
		if rcs is not None:
			rc = rcs.find("rc")
			if rc is not None:
				logRemaps = []
				remapButtons = {}
				placeHolder = 0
				rcButtons["keyIds"] = []
				rcButtons["image"] = rc.attrib.get("image")
				if config.crash.debugRemoteControls.value:
					print(f"[InputDevice] Remote control image file '{rcButtons['image']}'.")
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
						print(f"[InputDevice] Remote control button id='{id}', keyId='{keyId}', label='{rcButtons[keyId]['label']}', pos='{rcButtons[keyId]['pos']}', title='{rcButtons[keyId]['title']}', shape='{rcButtons[keyId]['shape']}', coords='{rcButtons[keyId]['coords']}'.")
				if logRemaps:
					for remap in logRemaps:
						print(f"[InputDevice] Remapping '{remap[0]}' to '{remap[1]}'.")
					for evdev, evdevinfo in sorted(inputDevices.devices.items()):
						if evdevinfo["type"] == "remote":
							result = eRCInput.getInstance().setKeyMapping(evdevinfo["name"], remapButtons)
							resStr = {
								eRCInput.remapOk: "Remap completed okay.",
								eRCInput.remapUnsupported: "Error: Remapping not supported on device!",
								eRCInput.remapFormatErr: "Error: Remap map in incorrect format!",
								eRCInput.remapNoSuchDevice: "Error: Unknown device!",
							}.get(result, "Error: Unknown error!")
							print(f"[InputDevice] Remote remap evdev='{evdev}', name='{evdevinfo['name']}': {resStr}")
		return rcButtons

	def getRemoteControlPixmap(self):
		return BoxInfo.getItem("RCImage")

	def getRemoteControlKeyList(self):
		return self.remote["keyIds"]

	def getRemoteControlKeyLabel(self, keyId):
		if keyId in self.remote:
			return self.remote[keyId]["label"]
		print(f"[InputDevice] Button '{KEYIDNAMES.get(keyId)}' ({keyId}) is not available on the current remote control.")
		return None

	def getRemoteControlKeyPos(self, keyId):
		if keyId in self.remote:
			return self.remote[keyId]["pos"]
		print(f"[InputDevice] Button '{KEYIDNAMES.get(keyId)}' ({keyId}) is not available on the current remote control.")
		return None

	def readRemoteControlType(self):
		return fileReadLine("/proc/stb/ir/rc/type", "0", source=MODULE_NAME)

	def writeRemoteControlType(self, rcType):
		if rcType > 0:
			fileWriteLine("/proc/stb/ir/rc/type", rcType, source=MODULE_NAME)

	def getOpenWebifHTML(self):
		html = []
		error = False
		image = self.remote["image"]
		if image:
			html.append(f"<img border=\"0\" src=\"{image}\" usemap=\"#map\" />")
			html.append("<map name=\"map\">")
			for keyId in self.remote["keyIds"]:
				attribs = []
				title = self.remote[keyId]["title"]
				if title:
					attribs.append(f"title=\"{title}\"")
				else:
					error = True
				shape = self.remote[keyId]["shape"]
				if shape:
					attribs.append(f"shape=\"{shape}\"")
				else:
					error = True
				coords = ",".join([str(x) for x in self.remote[keyId]["coords"]])
				if coords:
					attribs.append(f"coords=\"{coords}\"")
				else:
					error = True
				if keyId > 0:
					attribs.append(f"onclick=\"pressMenuRemote('{keyId}');\"")
				html.append(f"\t<area {' '.join(attribs)} />")
			html.append("</map>")
		else:
			error = True
		return None if error else "\n".join(html)


class InitInputDevices:
	def __init__(self):
		self.currentDevice = None
		for device in sorted(list(inputDevices.devices.keys())):
			print(f"[InputDevice] InitInputDevices DEBUG: Creating config entry for device: '{device}' -> '{inputDevices.devices[device]['name']}'.")
			self.currentDevice = device
			self.setupConfigEntries(self.currentDevice)
			self.currentDevice = None

	def setupConfigEntries(self, device):
		setattr(config.inputDevices, device, ConfigSubsection())
		configItem = getattr(config.inputDevices, device)
		configItem.enabled = ConfigYesNo(default=BoxInfo.getItem("RemoteEnable", False))
		configItem.enabled.addNotifier(self.inputDevicesEnabledChanged)
		configItem.name = ConfigText(default="", fixed_size=False)
		configItem.name.addNotifier(self.inputDevicesNameChanged)
		configItem.repeat = ConfigSlider(default=BoxInfo.getItem("RemoteRepeat", 100), increment=10, limits=(0, 500))
		configItem.repeat.addNotifier(self.inputDevicesRepeatChanged)
		configItem.delay = ConfigSlider(default=BoxInfo.getItem("RemoteDelay", 700), increment=100, limits=(0, 5000))
		configItem.delay.addNotifier(self.inputDevicesDelayChanged)

	def inputDevicesEnabledChanged(self, configElement):
		if self.currentDevice and inputDevices.currentDevice is None:
			inputDevices.setDeviceEnabled(self.currentDevice, configElement.value)
		elif inputDevices.currentDevice:
			inputDevices.setDeviceEnabled(inputDevices.currentDevice, configElement.value)

	def inputDevicesNameChanged(self, configElement):
		if self.currentDevice and inputDevices.currentDevice is None:
			inputDevices.setDeviceName(self.currentDevice, configElement.value)
			if configElement.value:
				devName = inputDevices.getDeviceAttribute(self.currentDevice, "name")
				if devName != configElement.value:
					configItem = getattr(config.inputDevices, f"{self.currentDevice}.enabled")
					configItem.value = False
					configItem.save()
		elif inputDevices.currentDevice:
			inputDevices.setDeviceName(inputDevices.currentDevice, configElement.value)

	def inputDevicesDelayChanged(self, configElement):
		if self.currentDevice and inputDevices.currentDevice is None:
			inputDevices.setDeviceDelay(self.currentDevice, configElement.value)
		elif inputDevices.currentDevice:
			inputDevices.setDeviceDelay(inputDevices.currentDevice, configElement.value)

	def inputDevicesRepeatChanged(self, configElement):
		if self.currentDevice and inputDevices.currentDevice is None:
			inputDevices.setDeviceRepeat(self.currentDevice, configElement.value)
		elif inputDevices.currentDevice:
			inputDevices.setDeviceRepeat(inputDevices.currentDevice, configElement.value)


inputDevices = InputDevices()
iInputDevices = inputDevices  # Deprecated support old plugins.


class RcTypeControl():
	def __init__(self):
		if exists("/proc/stb/ir/rc/type") and BoxInfo.getItem("brand") not in ("gigablue", "odin", "ini", "entwopia", "tripledot"):
			self.isSupported = True

			if config.plugins.remotecontroltype.rctype.value != 0:
				self.writeRcType(config.plugins.remotecontroltype.rctype.value)
		else:
			self.isSupported = False

	def multipleRcSupported(self):
		return self.isSupported

	def writeRcType(self, rctype):
		fd = open("/proc/stb/ir/rc/type", "w")
		fd.write(f"{rctype}")
		fd.close()


iRcTypeControl = RcTypeControl()
keyboard = Keyboard()
remoteControl = RemoteControl()
