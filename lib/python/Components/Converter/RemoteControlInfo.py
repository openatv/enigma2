from enigma import eInputDeviceManager

from Components.Converter.Converter import Converter
from Components.Element import cached

BATTERY_LOW_LEVEL = 20  # Same threshold as DFU_BATTERY_MIN in inputdevicemanager.h.


# Information about the connected Bluetooth LE remote control (DreamBLE).
#
# Usage: <convert type="RemoteControlInfo">Battery</convert>
#
# Battery    - text "85%", value/range for Progress renderers
# BatteryLow - boolean, battery level below 20%
# Signal     - text "-58 dBm"
# Name       - remote control name
# Connected  - boolean, a remote control is connected
#
class RemoteControlInfo(Converter):
	BATTERY = 0
	BATTERY_LOW = 1
	SIGNAL = 2
	NAME = 3
	CONNECTED = 4

	def __init__(self, type):
		Converter.__init__(self, type)
		self.type = {
			"Battery": self.BATTERY,
			"BatteryLow": self.BATTERY_LOW,
			"Signal": self.SIGNAL,
			"Name": self.NAME,
			"Connected": self.CONNECTED
		}.get(type, self.BATTERY)
		self.manager = eInputDeviceManager.getInstance()
		if self.manager:
			self.manager.getDeviceListChanged().append(self.deviceListChanged)
			self.manager.getDeviceStateChanged().append(self.deviceStateChanged)

	def destroy(self):
		if self.manager:
			self.manager.getDeviceListChanged().remove(self.deviceListChanged)
			self.manager.getDeviceStateChanged().remove(self.deviceStateChanged)
			self.manager = None
		Converter.destroy(self)

	def deviceListChanged(self):
		self.changed((self.CHANGED_ALL,))

	def deviceStateChanged(self, address, state):
		self.changed((self.CHANGED_ALL,))

	def getDevice(self):
		if self.manager and self.manager.available():
			devices = self.manager.getConnectedDevices()
			if devices:
				return devices[0]
		return None

	@cached
	def getText(self):
		device = self.getDevice()
		if device:
			if self.type == self.BATTERY:
				level = device.batteryLevel()
				return f"{level}%" if level > 0 else ""
			if self.type == self.SIGNAL:
				rssi = device.rssi()
				return f"{rssi} dBm" if rssi else ""
			if self.type == self.NAME:
				return device.name()
		return ""

	text = property(getText)

	@cached
	def getValue(self):
		device = self.getDevice()
		return device.batteryLevel() if device and self.type == self.BATTERY else 0

	value = property(getValue)

	range = 100

	@cached
	def getBoolean(self):
		device = self.getDevice()
		if device:
			if self.type == self.CONNECTED:
				return True
			if self.type == self.BATTERY_LOW:
				return 0 < device.batteryLevel() < BATTERY_LOW_LEVEL
		return False

	boolean = property(getBoolean)
