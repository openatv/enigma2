#Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License
#
#Copyright (c) 2024-2025 jbleyel

#Permission is hereby granted, free of charge, to any person obtaining a copy
#of this software and associated documentation files (the "Software"), to deal
#in the Software without restriction, including without limitation the rights
#to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#copies of the Software, and to permit persons to whom the Software is
#furnished to do so, subject to the following conditions:
#1. Non-Commercial Use: You may not use the Software or any derivative works
#   for commercial purposes without obtaining explicit permission from the
#   copyright holder.
#2. Share Alike: If you distribute or publicly perform the Software or any
#   derivative works, you must do so under the same license terms, and you
#   must make the source code of any derivative works available to the
#   public.
#3. Attribution: You must give appropriate credit to the original author(s)
#   of the Software by including a prominent notice in your derivative works.
#THE SOFTWARE IS PROVIDED "AS IS," WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#FITNESS FOR A PARTICULAR PURPOSE, AND NONINFRINGEMENT. IN NO EVENT SHALL
#THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES, OR
#OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT, OR OTHERWISE,
#ARISING FROM, OUT OF, OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
#OTHER DEALINGS IN THE SOFTWARE.
#
#For more details about the CC BY-NC-SA 4.0 License, please visit:
#https://creativecommons.org/licenses/by-nc-sa/4.0/


from glob import glob
from os import mkdir
from os.path import exists, join, realpath
from re import search, split, sub

from enigma import eTimer, getDeviceDB

from Components.ActionMap import HelpableActionMap
from Components.config import config, ConfigSelection, ConfigText, NoSave
from Components.Console import Console
from Components.Storage import StorageDevice, cleanMediaDirs, getProcMountsNew, EXPANDER_MOUNT
from Components.Label import Label
from Components.Harddisk import harddiskmanager
from Components.Sources.List import List
from Components.Sources.StaticText import StaticText
from Components.SystemInfo import BoxInfo  # , getBoxDisplayName
from Components.Task import job_manager
from Screens.ChoiceBox import ChoiceBox
import Screens.InfoBar
from Screens.MessageBox import MessageBox
from Screens.Screen import Screen
from Screens.Setup import Setup
from Screens.Standby import QUIT_REBOOT, TryQuitMainloop
from Screens.VirtualKeyBoard import VirtualKeyBoard
from Tools.Conversions import scaleNumber
from Tools.LoadPixmap import LoadPixmap
from Tools.Directories import SCOPE_GUISKIN, fileReadLine, fileReadLines, fileWriteLines, resolveFilename

MODULE_NAME = __name__.split(".")[-1]


class StorageDeviceAction(Setup):
	ACTION_INITIALIZE = 1
	ACTION_CHECK = 2
	ACTION_EXT4CONVERSION = 3
	ACTION_WIPE = 4
	ACTION_FORMAT = 5
	ACTION_LABEL = 6

	def __init__(self, session, storageDevice, action, actionText):
		self.storageDevice = storageDevice
		self["key_green"] = StaticText(_("Start"))

		self.action = action
		fileSystems = ["ext4", "ext3", "ext2"]

		if storageDevice.size < (1024 ** 3):  # 1GB
			fileSystems.append("msdos")
		elif storageDevice.size < (2 * 1024 ** 3):  # 2GB
			fileSystems.append("fat")
		if storageDevice.size <= (32 * 1024 ** 3):  # 32GB
			fileSystems.append("vfat")  # FAT32

		if exists("/usr/sbin/mkfs.exfat"):
			fileSystems.append("exfat")

		if exists("/usr/bin/ntfsfix") and exists("/usr/sbin/mkntfs"):
			fileSystems.append("ntfs")  # NTFS optional

		fileSystems.append("swap")

		self.formatMode = ConfigSelection(default=0, choices=[(0, _("Simple")), (1, _("Advanced"))])
		self.formatFileSystems = []
		self.formatLabels = []
		self.formatsizes = []
		self.numOfPartitions = 1
		defaultFs = self.storageDevice.fsType if self.storageDevice.isPartition else "ext4"
		if defaultFs not in fileSystems:
			defaultFs = "ext4"

		for i in range(20):
			self.formatFileSystems.append(ConfigSelection(default=defaultFs, choices=[(x, x) for x in fileSystems]))
			self.formatLabels.append(ConfigText(default=f"DISK_{i + 1}", fixed_size=False))
			self.formatsizes.append(ConfigSelection(default=100 if i == 0 else 0, choices=[(x, f"{x}%") for x in range(0, 101)]))

#			if storageDevice.size < (1024 ** 3):  # 1GB
#				MB = 1024 ** 2
#				self.formatSize = ConfigSelection(default=100 * MB, choices=choices + [(x * MB, scaleNumber(x * MB, format="%.f")) for x in range(1, 100)])
#			elif storageDevice.size < (1024 ** 4):  # 1TB
#				GB = 1024 ** 3
#				self.formatSize = ConfigSelection(default=100, choices=choices + [(x * GB, scaleNumber(x * GB, format="%.f")) for x in range(1, 100)])
#			else:
#				GB = 1024 ** 3
#				self.formatSize = ConfigSelection(default=100, choices=choices + [(x * GB, scaleNumber(x * GB, format="%.f")) for x in range(1, 100)])
		default = "gpt" if storageDevice.size > (2 * (1024 ** 3)) else "msdos"  # 2GB -> "gpt" else "msdos"
		choices = [
			("gpt", "GPT"),
			("msdos", "MBR")
		]
		self.formatPartion = ConfigSelection(default=default, choices=choices)

		Setup.__init__(self, session=session, setup="StorageDeviceAction")
		self.setTitle(actionText)

	def getActionParameters(self):
		if self.action == self.ACTION_FORMAT:
			return {"fsType": self.formatFileSystems[0].value, "label": self.formatLabels[0].value}
		elif self.action == self.ACTION_INITIALIZE:
			uuids = {}
			fsTypes = {}
			for device in [x.replace("/dev/", "") for x in glob(f"{self.storageDevice.devicePoint}*") if x != self.storageDevice.devicePoint]:
				uuid = fileReadLine(f"/dev/uuid/{device}", default=None, source=MODULE_NAME)
				fsType = fileReadLine(f"/dev/fstype/{device}", default=None, source=MODULE_NAME)
				if uuid:
					uuids[device] = uuid
				if fsType:
					fsTypes[device] = fsType
			if self.formatMode.value:
				partitions = []
				for i in range(self.numOfPartitions):
					if self.formatFileSystems[i].value:
						partitions.append({"fsType": self.formatFileSystems[i].value, "size": self.formatsizes[i].value, "label": self.formatLabels[i].value})
				return {"partitionType": self.formatPartion.value, "partitions": partitions, "uuids": uuids, "fsTypes": fsTypes}
			else:
				return {"partitionType": self.formatPartion.value, "partitions": [{"fsType": self.formatFileSystems[0].value, "size": 100}], "uuids": uuids, "fsTypes": fsTypes}
		else:
			return None

	def createSetup(self):  # NOSONAR silence S2638
		items = []
		if self.action == self.ACTION_FORMAT:
			diskInfo = f"{_("Device")}: {self.storageDevice.name} / {scaleNumber(self.storageDevice.diskSize, format="%.2f")}"
			if self.storageDevice.location:
				diskInfo = f"{diskInfo} / {self.storageDevice.location}"
			items.append((diskInfo,))
			diskInfo = f"{_("Partition")}: {self.storageDevice.fsType} / {scaleNumber(self.storageDevice.size, format="%.2f")}"
			items.append((diskInfo,))
		else:
			diskInfo = f"{_("Device")}: {self.storageDevice.name} / {scaleNumber(self.storageDevice.diskSize, format="%.2f")}"
			if self.storageDevice.location:
				diskInfo = f"{diskInfo} / {self.storageDevice.location}"
			items.append((diskInfo,))
		if self.action == self.ACTION_FORMAT:
			items.append((_("File system"), self.formatFileSystems[0]))
			if self.formatFileSystems[0].value != "swap":
				items.append((_("Label"), self.formatLabels[0]))
		elif self.action == self.ACTION_INITIALIZE:
			items.append((_("Mode"), self.formatMode))
			if self.formatMode.value:
				items.append((_("Partition Type"), self.formatPartion))
				for i in range(self.numOfPartitions):
					items.append((f"Partion {i + 1}",))
					items.append((_("Size"), self.formatsizes[i]))
					items.append((_("File system"), self.formatFileSystems[i]))
					if self.formatFileSystems[i].value != "swap":
						items.append((_("Label"), self.formatLabels[i]))
		Setup.createSetup(self, appendItems=items)

	def changedEntry(self):
		current = self["config"].getCurrent()[1]
		if current:
			if current == self.formatPartion:
				for pos in range(20):
					self.formatsizes[pos].value = 0
				self.formatsizes[0].value = 100
				self.numOfPartitions = 1
			else:
				currentPos = -1
				maxParts = 4 if self.formatPartion.value == "msdos" else 20
				for pos in range(maxParts):
					if current == self.formatsizes[pos]:
						currentPos = pos
						break
				if self.formatMode.value and currentPos != -1:
					fullSize = 0
					for pos in range(maxParts):
						if pos > currentPos:
							self.formatsizes[pos].value = 0
					for pos in range(maxParts):
						size = self.formatsizes[pos].value
						fullSize += size
						if fullSize > 99:
							self.numOfPartitions = pos + 1
							for morePos in range(pos + 1, maxParts):
								self.formatsizes[morePos].value = 0
							break
						if size == 0 and fullSize < 100:
							self.numOfPartitions = pos + 1
							self.formatsizes[pos].value = 100 - fullSize
							break

		Setup.changedEntry(self)

	def keyCancel(self):
		self.close(None)

	def keySave(self):
		self.close(self.getActionParameters())


class StorageDeviceManager():
	def createDevicesList(self):
		def alphanumKey(s):
			return [int(text) if text.isdigit() else text for text in split(r'(\d+)', s)]
		swapDevices = [x for x in fileReadLines("/proc/swaps", default=[], source=MODULE_NAME) if x.startswith("/") and "partition" in x]
		partitions = fileReadLines("/proc/partitions", default=[], source=MODULE_NAME)
		mounts = getProcMountsNew()
		fstab = fileReadLines("/etc/fstab", default=[], source=MODULE_NAME)
		knownDevices = fileReadLines("/etc/udev/known_devices", default=[], source=MODULE_NAME)
		deviceList = []
		unknownList = []
		seenDevices = []
		black = BoxInfo.getItem("mtdblack")
		for line in partitions:
			parts = line.strip().split()
			if parts:
				device = parts[3]
				if not device.startswith(black) and device not in seenDevices:
					seenDevices.append(device)
		seenDevices = sorted(seenDevices, key=alphanumKey)

		for device in seenDevices:
			isPartition = search(r"^sd[a-z][1-9][\d]*$", device) or search(r"^mmcblk[\d]p[\d]*$", device)
			if not isPartition:
				if not search(r"^sd[a-z]*$", device) and not search(r"^mmcblk[\d]*$", device):
					continue
			deviceList.append(self.createDevice(device, bool(isPartition), mounts, swapDevices, partitions, knownDevices, fstab))

		seenUUIDs = [device.get("UUID") for device in deviceList if device.get("UUID")]

		expanderUUID = None
		for line in fstab:
			if EXPANDER_MOUNT in line:
				parts = line.split()
				if parts[0].startswith("UUID="):
					UUID = parts[0].replace("UUID=", "")
					expanderUUID = UUID
					seenUUIDs.append(UUID)

		expanderDisk = None
		if expanderUUID:
			for device in deviceList:
				if device.get("UUID") == expanderUUID:
					expanderDisk = device.get("disk")
					break

		if expanderDisk:
			for device in deviceList:
				if device.get("disk") == expanderDisk:
					device["FlashExpander"] = True
					description = device["description"]
					device["description"] = f"{description}\n{_("Flash Expander")}: {_("Enabled")}"

		for index, line in enumerate(fstab):
			parts = line.split()
			if parts and parts[0].startswith("UUID="):
				UUID = parts[0].replace("UUID=", "")
				if UUID in seenUUIDs:
					continue
				if config.crash.debugStorage.value:
					print(f"[DeviceManager] DEBUG fstab line {index + 1} / UUID {UUID} not in device list")

				deviceData = {
					"UUID": UUID,
					"devicePoint": parts[1],
					"isUnknown": True,
					"FlashExpander": False
				}
				unknownList.append(deviceData)
		if config.crash.debugStorage.value:
			print(f"[DeviceManager] DEBUG deviceList:\n{deviceList}\nunknownList:\n{unknownList}")
		return deviceList, unknownList

	def createDevice(self, device, isPartition, mounts, swapDevices, partitions, knownDevices, fstab):
		def getDeviceTypeModel():
			devicePath = realpath(join("/sys/block", device2, "device"))
			deviceType = 0  # USB
			if device2.startswith("mmcblk"):
				model = fileReadLine(join("/sys/block", device2, "device/name"), default="", source=MODULE_NAME)
				deviceType = 1  # MMC
			else:
				model = fileReadLine(join("/sys/block", device2, "device/model"), default="", source=MODULE_NAME)
			if "pci" in devicePath or "ahci" in devicePath or "ata" in devicePath:
				deviceType = 2  # HDD
			return devicePath[4:], deviceType, model

		if isPartition:
			device2 = device[:7] if device.startswith("mmcblk") else sub(r"[\d]", "", device)
		else:
			device2 = device
		physdev, deviceType, model = getDeviceTypeModel()
		deviceLocation = ""
		for physdevprefix, pdescription in list(getDeviceDB().items()):
			if physdev.startswith(physdevprefix):
				deviceLocation = pdescription

		deviceMounts = []
		mounts = [x for x in mounts if EXPANDER_MOUNT not in x[1]]
		swapState = False
		devicePoint = f"/dev/{device}"
		if isPartition:
			for parts in [parts for parts in mounts if devicePoint == parts[0]]:
				mountP = parts[1]
				mountFsType = parts[2]
				rw = parts[3]
				deviceMounts.append((mountP, mountFsType, rw))

			if not deviceMounts:
				swapDevicesNames = [x.split()[0] for x in swapDevices]
				for parts in [parts for parts in mounts if devicePoint != parts[0]]:
					if f"/dev/{device}" in swapDevicesNames:
						mountP = "swap"
						mountFsType = "swap"
						rw = ""
						swapState = True
						break
					else:
						mountP = _("None")
						mountFsType = _("unavailable")
						rw = _("None")
		else:
			mountP = ""
			rw = ""
			mountFsType = ""

		size = 0
		diskSize = 0
		for line in partitions:
			if line.find(device) != -1:
				parts = line.strip().split()
				size = int(parts[2]) * 1024
				break

		if isPartition:
			for line in partitions:
				if line.find(device2) != -1:
					parts = line.strip().split()
					diskSize = int(parts[2]) * 1024
					break

		if not size:
			size = fileReadLine(join("/sys/block", device2, device, "size"), default=None, source=MODULE_NAME)
			try:
				size = int(size) * 512
			except ValueError:
				size = 0

		if not diskSize:
			diskSize = size
		if size:
			isMounted = len([parts for parts in mounts if mountP == parts[1]])
			UUID = fileReadLine(f"/dev/uuid/{device}", default="", source=MODULE_NAME)
			fsType = fileReadLine(f"/dev/fstype/{device}", default="", source=MODULE_NAME)
			label = fileReadLine(f"/dev/label/{device}", default="", source=MODULE_NAME)
			knownDevice = ""
			for known in knownDevices:
				if UUID and UUID in known:
					knownDevice = known
			fstabMountPoint = ""
			for line in fstab:
				if EXPANDER_MOUNT not in line:
					fstabData = line.split()
					if fstabData:
						if UUID and UUID in fstabData[0]:
							fstabMountPoint = fstabData[1]
						elif devicePoint in fstabData:
							fstabMountPoint = fstabData[0]

			description = []
			if not isPartition:
				description.append(f"{_("Path")}: {physdev}")
			if deviceLocation:
				description.append(f"{_("Position")}: {deviceLocation}")
			description = "\n".join(description)
			deviceData = {
				"name": model,
				"device": device,
				"disk": device2,
				"UUID": UUID,
				"mountPoint": mountP,
				"devicePoint": devicePoint,
				"fstabMountPoint": fstabMountPoint,
				"isMounted": isMounted,
				"knownDevice": knownDevice,
				"model": model,
				"location": deviceLocation,
				"description": description,
				"deviceType": deviceType,
				"fsType": fsType,
				"isPartition": isPartition,
				"rw": rw,
				"size": size,
				"diskSize": diskSize,
				"mountFsType": mountFsType,
				"swapState": swapState,
				"isUnknown": False,
				"FlashExpander": False,
				"label": label
			}
			return deviceData

	def getMountPoints(self, deviceType, fstab=None, onlyPossible=False):
		match deviceType:
			case 0:
				result = ["usb", "usb2", "usb3", "usb4", "usb5"]
			case 1:
				result = ["mmc", "mmc2", "mmc3", "mmc4", "mmc5"]
			case _:
				result = []
		result.extend(["hdd", "hdd2", "hdd3", "hdd4", "hdd5"])
		if onlyPossible:
			fstab = fstab or []
			fstabMountPoints = [x.split()[1] for x in fstab if x]
			for dev in result[:]:
				for fstabMountPoint in fstabMountPoints:
					if fstabMountPoint == f"/media/{dev}" and dev in result:
						result.remove(dev)
		return result


class DeviceManager(Screen):

	MOUNT = "/bin/mount"
	UMOUNT = "/bin/umount"

	LIST_SELECTION = 0
	LIST_DEVICE = 1
	LIST_DEVICE_INDENT = 2
	LIST_DESCRIPTION = 3
	LIST_SIZE = 4
	LIST_PARTITION_SEPARATOR = 5
	LIST_IMAGE = 6
#	LIST_MOUNT_POINT = 7
#	LIST_DEVICE_POINT = 8
#	LIST_ISMOUNTED = 9
	LIST_DATA = 10

	DEVICE_TYPES = {
		0: ("USB: ", "icons/dev_usbstick.png"),
		1: ("MMC: ", "icons/dev_mmc.png"),
		2: (_("HARD DISK: "), "icons/dev_hdd.png")
	}
	DEVICE_TYPES_NAME = 0
	DEVICE_TYPES_ICON = 1

	skin = """
	<screen name="DeviceManager" title="Device Manager" position="center,center" size="1080,465" resolution="1280,720">
		<widget source="devicelist" render="Listbox" position="0,0" size="1080,325">
			<templates>
				<template name="Default" fonts="Regular;20,Regular;24" itemHeight="30">
					<mode name="default">
						<text index="Device" position="34,0" size="220,30" font="0" />
						<text index="DeviceIndent" position="52,0" size="220,30" font="0" />
						<text index="Description" position="450,0" size="400,30" font="0" verticalAlignment="top" horizontalAlignment="left" />
						<text index="Size" position="900,0" size="180,30" font="0" verticalAlignment="top" horizontalAlignment="right" />
						<text index="PartitionSeparator" position="6,6" size="30,30" font="1" verticalAlignment="center" />
						<pixmap index="Image" position="0,0" size="30,30" alpha="blend" scale="centerScaled" />
					</mode>
				</template>
			</templates>
		</widget>
		<eRectangle position="0,328" size="e,1" />
		<widget name="description" position="0,330" size="e,100" font="Regular;20" verticalAlignment="top" horizontalAlignment="left" />
		<widget source="key_red" render="Label" position="0,e-40" size="180,40" backgroundColor="key_red" font="Regular;20" foregroundColor="key_text" horizontalAlignment="center" noWrap="1" verticalAlignment="center">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="key_green" render="Label" position="190,e-40" size="180,40" backgroundColor="key_green" font="Regular;20" foregroundColor="key_text" horizontalAlignment="center" noWrap="1" verticalAlignment="center">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="key_yellow" render="Label" position="380,e-40" size="180,40" backgroundColor="key_yellow" font="Regular;20" foregroundColor="key_text" horizontalAlignment="center" noWrap="1" verticalAlignment="center">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="key_blue" render="Label" position="570,e-40" size="180,40" backgroundColor="key_blue" font="Regular;20" foregroundColor="key_text" horizontalAlignment="center" noWrap="1" verticalAlignment="center">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="key_help" render="Label" position="e-80,e-40" size="80,40" backgroundColor="key_back" font="Regular;20" foregroundColor="key_text" horizontalAlignment="center" noWrap="1" verticalAlignment="center">
			<convert type="ConditionalShowHide" />
		</widget>
	</screen>"""

	def __init__(self, session):
		Screen.__init__(self, session, mandatoryWidgets=["devicelist"], enableHelp=True)
		self.setTitle(_("Device Manager"))
		self.onChangedEntry = []
		self.deviceList = []

		indexNames = {
			"Selection": self.LIST_SELECTION,  # This is a dummy entry for selection
			"Image": self.LIST_IMAGE,
			"PartitionSeparator": self.LIST_PARTITION_SEPARATOR,
			"Description": self.LIST_DESCRIPTION,
			"DeviceIndent": self.LIST_DEVICE_INDENT,
			"Device": self.LIST_DEVICE,
			"Size": self.LIST_SIZE
		}

		self["devicelist"] = List(self.deviceList, indexNames=indexNames)
		self["devicelist"].onSelectionChanged.append(self.selectionChanged)
		self["key_red"] = StaticText(_("Cancel"))
		self["key_green"] = StaticText(_("Actions"))
		self["key_yellow"] = StaticText(_("Mount Point"))
		self["key_blue"] = StaticText(_("Unmount"))
		self["description"] = Label()
		self["actions"] = HelpableActionMap(self, ["OkCancelActions", "ColorActions", "MenuActions"], {
			"ok": (self.keyMountPoint, _("Select a permanent mount point for the current device")),
			"cancel": (self.close, _("Close the Device Manager screen")),
			"close": (self.keyClose, _("Close the Device Manager screen and exit all menus")),
			"menu": (self.keyMenu, _("Hard Disk Settings")),
			"red": (self.close, _("Close the Device Manager screen")),
			"green": (self.keyActions, _("Select an action for the current device")),
			"yellow": (self.keyMountPoints, _("Select a permanent mount point for all devices")),
			"blue": (self.keyBlue, _("Toggle a temporary mount for the current device"))
		}, prio=0, description=_("Device Manager Actions"))
		self.needReboot = False
		self.storageDevices = StorageDeviceManager()
		self.updateDevices()
		self.console = Console()

	def buildList(self):
		self.deviceList = []
		storageDeviceList, unknownList = self.storageDevices.createDevicesList()
		for storageDevice in storageDeviceList:

			deviceDisplayName = "" if storageDevice.get("isPartition") else storageDevice.get("device")
			deviceDisplayNameIndent = storageDevice.get("device") if storageDevice.get("isPartition") else ""

			mountPoint = storageDevice.get("mountPoint")
			label = storageDevice.get("label")

			size = f"{scaleNumber(storageDevice.get("size"), format="%.2f")}"

			if storageDevice.get("isPartition"):
				if ":None" in storageDevice.get("knownDevice"):
					mountPoint = "Ignore"

				rw = storageDevice.get("rw")
				if rw.startswith("rw"):
					rw = " R/W"
				elif rw.startswith("ro"):
					rw = " R/O"
				else:
					rw = ""

				fs = storageDevice.get("fsType")
				if fs == "swap":
					swapState = _("On") if storageDevice.get("swapState") else _("Off")
					des = f"{_("Swap")}: {swapState}"
				else:
					des = f"{label or _("No Name")}: {mountPoint} {fs}{rw}"
				separator = "└"
				devicePixmap = None
			else:
				separator = ""
				devicePixmap = LoadPixmap(resolveFilename(SCOPE_GUISKIN, self.DEVICE_TYPES[storageDevice.get("deviceType")][self.DEVICE_TYPES_ICON]))
				deviceName = self.DEVICE_TYPES[storageDevice.get("deviceType")][self.DEVICE_TYPES_NAME]
				des = f"{deviceName}{storageDevice.get("model")}"

			#										3		4			5		6		7			8			9			10		11	     12		    		13
			# res = (selection, deviceName, des, devicePixmap, mountP, deviceP, isMounted, UUID, UUIDMount, devMount, knownDevice, deviceType, model, deviceLocation, description)
			res = ("", deviceDisplayName, deviceDisplayNameIndent, des, size, separator, devicePixmap, storageDevice.get("mountPoint"), storageDevice.get("devicePoint"), storageDevice.get("isMounted"), storageDevice)
			self.deviceList.append(res)

		if unknownList:
			res = (None, _("Unknown Devices"), "", "", "", "", None, "", "", "", {})
			self.deviceList.append(res)
			for unknownItem in unknownList:
				res = ("", "", unknownItem.get("devicePoint"), unknownItem.get("UUID"), "", "", None, "", "", "", unknownItem)
				self.deviceList.append(res)

		self["devicelist"].list = self.deviceList

	def selectionChanged(self):
		if self["devicelist"].list:
			current = self["devicelist"].getCurrent()
			if current:
				storageDevice = current[self.LIST_DATA]
				# mountPoint = current[3]
				if current:
					try:
						name = str(current[0])
						description = str(current[1].replace("\t", "  "))
					except Exception:
						name = ""
						description = ""
				else:
					name = ""
					description = ""
				self["key_green"].setText(_("Action"))
				if storageDevice.get("FlashExpander"):
					self["key_blue"].setText("")
				elif storageDevice.get("fsType") == "swap":
					self["key_blue"].setText(_("Off") if storageDevice.get("swapState") else _("On"))
				elif storageDevice.get("isPartition"):
					if storageDevice.get("fstabMountPoint"):
						self["key_blue"].setText("")
					elif ":None" in storageDevice.get("knownDevice"):
						self["key_blue"].setText(_("Activate"))
					else:
						self["key_blue"].setText(_("Unmount") if storageDevice.get("isMounted") else _("Mount"))
				elif storageDevice.get("isUnknown"):
					self["key_blue"].setText("")
					self["key_green"].setText(_("Remove"))
				else:
					self["key_blue"].setText("")

				for callback in self.onChangedEntry:
					if callback and callable(callback):
						callback(name, description)

				self["description"].setText(storageDevice.get("description"))

	def keyMenu(self):
		self.session.open(DeviceManagerSetup)

	def keyClose(self):
		if self.needReboot:
			self.session.open(TryQuitMainloop, QUIT_REBOOT)
		else:
			self.close((True, ))

	def keyMountPoints(self):
		def keyMountPointsCallback(needsReboot=False):
			self.needReboot = self.needReboot or needsReboot
			self.updateDevices()

		self.session.openWithCallback(keyMountPointsCallback, DeviceManagerMountPoints, storageDevices=self.storageDevices)

	def keyMountPoint(self):
		def keyMountPointCallback(needsReboot=False):
			self.needReboot = self.needReboot or needsReboot
			self.updateDevices()

		if self["devicelist"].list:
			current = self["devicelist"].getCurrent()
			if current:
				storageDevice = current[self.LIST_DATA]
				if storageDevice.get("FlashExpander"):
					return
				elif storageDevice.get("fsType") == "swap":
					def swapCallback(data, retVal, extraArgs):
						if retVal:
							print(f"[DeviceManager] swap failed / RC:{retVal}")
							if config.crash.debugStorage.value:
								print(data)
						self.updateDevices()
					command = "swapoff" if storageDevice.get("swapState") else "swapon"
					self.console.ePopen([command, command, storageDevice.get("devicePoint")], swapCallback)
				elif storageDevice.get("isPartition"):
					self.session.openWithCallback(keyMountPointCallback, DeviceManagerMountPoints, index=self["devicelist"].getCurrentIndex(), storageDevices=self.storageDevices)

	def keyBlue(self):
		def keyBlueCallback(answer):
			def checkMount(data, retVal, extraArgs):
				if retVal:
					print(f"[DeviceManager] mount failed for device:{devicePoint} / RC:{retVal}")
					if config.crash.debugStorage.value:
						print(data)
				self.updateDevices()
				mountok = False
				mounts = getProcMountsNew()
				for parts in mounts:
					if parts[0] == devicePoint:
						mountok = True
				if not mountok:
					self.session.open(MessageBox, _("Mount failed"), MessageBox.TYPE_INFO, timeout=5)
				else:
					harddiskmanager.refreshMountPoints()
			if answer:
				if not exists(answer[1]):
					mkdir(answer[1], 0o755)
				cmd = [self.MOUNT, self.MOUNT]
				if storageDevice.get("fsType") == "exfat":
					cmd += ["-t", "exfat"]
				cmd += [f"/dev/{storageDevice.get("device")}", f"{answer[1]}/"]
				self.console.ePopen(cmd, checkMount)

		current = self["devicelist"].getCurrent()
		if current:
			storageDevice = current[self.LIST_DATA]
			if storageDevice.get("fsType") == "swap":
				def swapCallback(data, retVal, extraArgs):
					if retVal:
						print(f"[DeviceManager] swap failed / RC:{retVal}")
						if config.crash.debugStorage.value:
							print(data)
					self.updateDevices()
				command = "swapoff" if storageDevice.get("swapState") else "swapon"
				self.console.ePopen([command, command, storageDevice.get("devicePoint")], swapCallback)
			elif storageDevice.get("isPartition") and not storageDevice.get("fstabMountPoint"):
				knownDevice = storageDevice.get("knownDevice")
				if ":None" in knownDevice:
					knownDevices = fileReadLines("/etc/udev/known_devices", [], source=MODULE_NAME)
					if knownDevice in knownDevices:
						knownDevices.remove(knownDevice)
					fileWriteLines("/etc/udev/known_devices", knownDevices, source=MODULE_NAME)
				else:
					devicePoint = storageDevice.get("devicePoint")
					if storageDevice.get("isMounted"):
						self.console.ePopen([self.UMOUNT, self.UMOUNT, storageDevice.get("mountPoint")])
						mounts = getProcMountsNew()
						for parts in mounts:
							if parts[1] == storageDevice.get("mountPoint"):
								self.session.open(MessageBox, _("Can't unmount partition, make sure it is not being used for swap or record/time shift paths"), MessageBox.TYPE_INFO)
						cleanMediaDirs()
					else:
						title = _("Select the new mount point for: '%s'") % storageDevice.get("model")
						fstab = fileReadLines("/etc/fstab", default=[], source=MODULE_NAME)
						label = storageDevice.get("label")
						device = storageDevice.get("device")
						choiceList = [(f"/media/{x}", f"/media/{x}") for x in self.storageDevices.getMountPoints(storageDevice.get("deviceType"), fstab, onlyPossible=True) + [device, label]]
						self.session.openWithCallback(keyBlueCallback, ChoiceBox, choiceList=choiceList, buttonList=[], windowTitle=title)
				self.updateDevices()

	def updateDevices(self):
		self.buildList()

	def stopTimeshift(self, confirmed):
		if confirmed:
			self.curentservice = self.session.nav.getCurrentlyPlayingServiceReference()
			self.session.nav.stopService()
			Screens.InfoBar.InfoBar.instance.stopTimeshiftcheckTimeshiftRunningCallback(True)
			self.hddConfirmed(True)

	def hddConfirmed(self, confirmed):
		if confirmed:
			try:
				job_manager.AddJob(self.getActionFunction(self.currentAction, self.currentStorageDevice)(self.currentOptions))
				for job in job_manager.getPendingJobs():
					if job.name in (_("Initializing storage device..."), _("Checking file system..."), _("Converting ext3 to ext4..."), _("Wiping storage device..."), _("Formatting storage device...")):
						self.showJobView(job)
						break
			except Exception as ex:
				self.session.open(MessageBox, str(ex), type=MessageBox.TYPE_ERROR, timeout=10)

	def showJobView(self, job):
		from Screens.TaskView import JobView
		job_manager.in_background = False
		self.session.openWithCallback(self.JobViewCB, JobView, job, cancelable=False, afterEventChangeable=False, afterEvent="close")

	def JobViewCB(self, in_background):
		job_manager.in_background = in_background
		if self.curentservice:
			self.session.nav.playService(self.curentservice)
		harddiskmanager.refresh(self.currentStorageDevice.disk)
		self.updateDevices()

	def getActionFunction(self, action, storageDevice):
		return {
			StorageDeviceAction.ACTION_INITIALIZE: storageDevice.createInitializeJob,
			StorageDeviceAction.ACTION_CHECK: storageDevice.createCheckJob,
			StorageDeviceAction.ACTION_EXT4CONVERSION: storageDevice.createExt4ConversionJob,
			StorageDeviceAction.ACTION_WIPE: storageDevice.createWipeJob,
			StorageDeviceAction.ACTION_FORMAT: storageDevice.createFormatJob
		}.get(action)

	def keyActions(self):
		def renameActionCallback(data, retVal, extraArgs):
			if retVal:
				print(f"[DeviceManager] rename failed / RC:{retVal}")
				if config.crash.debugStorage.value:
					print(data)

			def renameActionCallback2():
				self.reloadTimer = None
				self.updateDevices()
			self.reloadTimer = eTimer()
			self.reloadTimer.callback.append(renameActionCallback2)
			self.reloadTimer.start(1000, True)

		def renameCallback(newName):
			if newName:
				newName = storageDevice.normalizeLabel(newName, storageDevice.getLabelLimit(storageDevice.fsType))
				params = [storageDevice.devicePoint, newName]
				if "extfat" == storageDevice.fsType:
					cmd = "/usr/sbin/exfatlabel"
				elif "ntfs" in storageDevice.fsType:  # Not supported yet because you need to unmount
					cmd = "/usr/sbin/ntfslabel"
				elif "fat" in storageDevice.fsType:
					params = ["-i", storageDevice.devicePoint, f"::{newName}"]
					cmd = "/usr/bin/mlabel"
				else:
					cmd = "/sbin/e2label"
				self.console.ePopen([cmd, cmd] + params, callback=renameActionCallback)

		def keyActionsSetupCallback(options):
			if options is not None:
				self.currentOptions = options
				actionQuestion = {
					StorageDeviceAction.ACTION_CHECK: _("Do you really want to check the file system?\nThis could take a long time!"),
					StorageDeviceAction.ACTION_EXT4CONVERSION: _("Do you really want to convert the file system?\nYou cannot go back!")
				}
				question = actionQuestion.get(self.currentAction) or _("Do you really want to format the device in the Linux file system?\nAll data on the device will be lost!")
				if Screens.InfoBar.InfoBar.instance and Screens.InfoBar.InfoBar.instance.timeshiftEnabled():
					message = "%s\n\n%s" % (question, _("You seem to be in time shift, the service will briefly stop as time shift stops."))
					message = "%s\n%s" % (message, _("Do you want to continue?"))
					self.session.openWithCallback(self.stopTimeshift, MessageBox, message)
				else:
					message = "%s\n%s" % (question, _("You can continue watching TV etc. while this is running."))
					self.session.openWithCallback(self.hddConfirmed, MessageBox, message)

		def keyActionsCallback(action):
			self.currentAction = action
			options = {"debug": True} if config.crash.debugStorage.value else {}
			if action:
				if action == StorageDeviceAction.ACTION_LABEL:
					self.session.openWithCallback(renameCallback, VirtualKeyBoard, title=_("Please enter the new name:"), text=storageDevice.label)
				elif action in (StorageDeviceAction.ACTION_FORMAT, StorageDeviceAction.ACTION_INITIALIZE):
					self.session.openWithCallback(keyActionsSetupCallback, StorageDeviceAction, storageDevice, action, _("Format Storage Device"))
				elif action == StorageDeviceAction.ACTION_WIPE:
					uuids = {}
					for device in [x.replace("/dev/", "") for x in glob(f"{storageDevice.devicePoint}*") if x != storageDevice.devicePoint]:
						uuid = fileReadLine(f"/dev/uuid/{device}", default=None, source=MODULE_NAME)
						if uuid:
							uuids[device] = uuid
					keyActionsSetupCallback(options | {"uuids": uuids})
				else:
					keyActionsSetupCallback(options)

		current = self["devicelist"].getCurrent()
		if current:
			self.curentservice = None
			storageDevice = current[self.LIST_DATA]
			storageDevice = StorageDevice(storageDevice)

			if storageDevice.FlashExpander:
				return
			if storageDevice.isUnknown:
				fstab = fileReadLines("/etc/fstab", default=[], source=MODULE_NAME)
				fstabNew = []
				for line in fstab:
					if EXPANDER_MOUNT not in line and storageDevice.UUID in line and storageDevice.devicePoint in line:
						continue
					fstabNew.append(line)
				fileWriteLines("/etc/fstab", fstabNew, source=MODULE_NAME)
				self.updateDevices()
				return

			fileSystems = ["ext4", "ext3", "ext2"]

			if storageDevice.size < (1024 ** 3):  # 1GB
				fileSystems.append("msdos")
			elif storageDevice.size < (2 * 1024 ** 3):  # 2GB
				fileSystems.append("fat")
			if storageDevice.size <= (32 * 1024 ** 3):  # 32GB
				fileSystems.append("vfat")  # FAT32

			if exists("/usr/sbin/fsck.exfat"):
				fileSystems.append("exfat")
			if exists("/usr/bin/ntfsfix") and exists("/usr/sbin/mkntfs"):
				fileSystems.append("ntfs")  # NTFS optional

			if storageDevice.isPartition:
				choiceList = [
					(_("Cancel"), 0),
					(_("Format Storage Device"), StorageDeviceAction.ACTION_FORMAT)
				]
				if storageDevice.fsType in fileSystems:
					choiceList.append((_("File System Check"), StorageDeviceAction.ACTION_CHECK))
				if storageDevice.fsType == "ext3":
					choiceList.append((_("Convert file system ext3 to ext4"), StorageDeviceAction.ACTION_EXT4CONVERSION))
				if "ntfs" not in storageDevice.fsType and storageDevice.fsType in fileSystems:  # NTFS not supported yet becaue you need to unmount
					choiceList.append((_("Rename"), StorageDeviceAction.ACTION_LABEL))
			else:
				choiceList = [
					(_("Cancel"), 0),
					(_("Format Storage Device"), StorageDeviceAction.ACTION_INITIALIZE),
					(_("Wipe Storage Device"), StorageDeviceAction.ACTION_WIPE)
				]

			self.currentStorageDevice = storageDevice
			self.currentAction = 0
			self.session.openWithCallback(keyActionsCallback, MessageBox, text=(_("Select")), list=choiceList, windowTitle=self.getTitle())

	def createSummary(self):
		return DevicesPanelSummary


class DeviceManagerMountPoints(Setup):
	UMOUNT = "/bin/umount"
	MOUNT = "/bin/mount"
	defaultOptions = {
		"auto": "",
		"ext4": "defaults,noatime",
		"vfat": "rw,iocharset=utf8,uid=0,gid=0,umask=0022",
		"exfat": "rw,iocharset=utf8,uid=0,gid=0,umask=0022",
		"ntfs-3g": "defaults,uid=0,gid=0,umask=0022",
		"iso9660": "ro,defaults",
		"udf": "ro,defaults",
		"hfsplus": "rw,force,uid=0,gid=0",
		"btrfs": "defaults,noatime",
		"xfs": "defaults,compress=zstd,noatime",
		"fuseblk": "defaults,uid=0,gid=0"
	}

	def __init__(self, session, index=-1, storageDevices=None):
		if storageDevices:
			self.storageDevices = storageDevices
		else:
			self.storageDevices = StorageDeviceManager()
		self.devices, self.disks = self.buildDevices(index)
		self.mountPoints = []
		self.customMountPoints = []
		self.fileSystems = []
		self.deviceMounts = []
		self.options = []
		single = index != -1
		fstab = fileReadLines("/etc/fstab", default=[], source=MODULE_NAME) if single else []
		noMediaHdd = len(self.devices) == 1 and not [line for line in fstab if "/media/hdd" in line]  # No media/hdd and only one device
		self.configMode = ConfigSelection(default=0, choices=[(0, _("Simple")), (1, _("Advanced"))])
		self.console = Console()

		# device , fstabmountpoint, isMounted , deviceUuid, name, deviceType, fsType, size, disk, label
		for index, device in enumerate(self.devices):
			deviceType = device[5]
			fstabMountPoint = device[1]
			if noMediaHdd:
				fstabMountPoint = "/media/hdd"
			choiceList = [("None", "None")]

			if "sr" in device[0]:
				fileSystems = ["auto", "iso9660", "udf"]
				choiceList.extend([("/media/cdrom", "/media/cdrom"), ("/media/dvd", "/media/dvd")])
				defaultMountpoint = fstabMountPoint or "/media/cdrom"
			else:
				possibleMounts = [f"/media/{x}" for x in self.storageDevices.getMountPoints(deviceType)]
				if single:
					for mounts in fstab:
						if mounts and mounts.split()[1] in possibleMounts:
							possibleMounts.remove(mounts.split()[1])
					choiceList.extend([(x, x) for x in possibleMounts])
				else:
					choiceList.extend([(x, x) for x in possibleMounts])
				if fstabMountPoint and fstabMountPoint not in [x[0] for x in choiceList]:
					choiceList.insert(1, (fstabMountPoint, fstabMountPoint))
				label = device[9]
				if label:
					label = f"/media/{label.replace(" ", "_")}"
					choiceList.append((label, label))

				defaultMountpoint = fstabMountPoint or "None"
				fileSystems = ["auto", "ext4", "vfat"]
				if exists("/sbin/mount.exfat"):
					fileSystems.append("exfat")
				if exists("/sbin/mount.ntfs-3g"):
					fileSystems.append("ntfs")
				if exists("/sbin/mount.fuse"):
					fileSystems.append("fuseblk")
				fileSystems.extend(["hfsplus", "btrfs", "xfs"])
			devMount = device[0].replace("/dev/", "/media/")
			choiceList.append((devMount, devMount))
			choiceList.append(("", "Custom"))
			self.mountPoints.append(NoSave(ConfigSelection(default=defaultMountpoint, choices=choiceList)))
			self.customMountPoints.append(NoSave(ConfigText()))
			fileSystemChoices = [(x, x) for x in fileSystems]
			self.fileSystems.append(NoSave(ConfigSelection(default=fileSystems[0], choices=fileSystemChoices)))
			self.options.append(NoSave(ConfigText("defaults")))

		Setup.__init__(self, session=session, setup="DeviceManagerMountPoints")
		self.setTitle(_("Select the mount points"))

	def buildDevices(self, deviceIndex=-1):
		storageDeviceList, extraList = self.storageDevices.createDevicesList()
		devices = []
		disks = {}
		for index, storageDevice in enumerate(storageDeviceList):
			if deviceIndex == -1 or index == deviceIndex:
				if storageDevice.get("fsType") == "swap":
					continue
				if storageDevice.get("isPartition"):
					devices.append((storageDevice.get("devicePoint"), storageDevice.get("fstabMountPoint"), storageDevice.get("isMounted"), storageDevice.get("UUID"), storageDevice.get("name"), storageDevice.get("deviceType"), storageDevice.get("fsType"), storageDevice.get("size"), storageDevice.get("disk"), storageDevice.get("label")))
				else:
					diskInfo = f"{_("Device")}: {storageDevice.get("name")} / {scaleNumber(storageDevice.get("diskSize"), format="%.2f")}"
					if storageDevice.get("location"):
						diskInfo = f"{diskInfo} / {storageDevice.get("location")}"
					disks[storageDevice.get("disk")] = diskInfo
		return devices, disks

	def appendEntries(self, index, device):
		items = []
		# device , fstabmountpoint, isMounted , deviceUuid, name, deviceType, fsType, size, disk, label
		partInfo = f"{device[9] or _("No Name")}: {device[0]} / {scaleNumber(device[7], format="%.2f")}"
		partInfoDesc = f"{_("File system")}: {device[6]}"
		items.append((partInfo, self.mountPoints[index], f"{_("Select the mountpoint for the device.")}\n{partInfoDesc}", index, device[8]))
		if self.mountPoints[index].value != "None":
			if self.mountPoints[index].value == "":
				items.append((_("Custom mountpoint"), self.customMountPoints[index], _("Define the custom mountpoint for the device."), index, device[8]))
			if self.configMode.value:  # Advanced
				items.append((_("File system"), self.fileSystems[index], _("Select the file system for the device."), index, device[8]))
				items.append((_("Options"), self.options[index], _("Define the file system mount options."), index, device[8]))
		return items

	def createSetup(self):  # NOSONAR silence S2638
		items = [(_("Mode"), self.configMode)]
		for index, device in enumerate(self.devices):
			items = items + self.appendEntries(index, device)
		Setup.createSetup(self, appendItems=items)

	def changedEntry(self):
		current = self["config"].getCurrent()[1]
		if current != self.configMode:
			index = self["config"].getCurrent()[3]
			if current == self.fileSystems[index]:
				self.options[index].value = self.defaultOptions.get(self.fileSystems[index].value)
		Setup.changedEntry(self)

	def setFootnote(self, footnote):
		if self["config"].getCurrent()[1] != self.configMode:
			disk = self["config"].getCurrent()[4]
			footnote = self.disks.get(disk, "")
		Setup.setFootnote(self, footnote)

	def keySave(self):
		def keySaveCallback(data, retVal, extraArgs):
			if retVal:
				print(f"[DeviceManager] mount failed / RC:{retVal}")
				if config.crash.debugStorage.value:
					print(data)

			needReboot = False
#			isMounted = current[5]
#			mountp = current[3]
#			device = current[4]
#			self.updateDevices()
#			if answer[0] == "None" or device != current[4] or current[5] != isMounted or mountp != current[3]:
#				self.needReboot = True

			mounts = getProcMountsNew()
			mediaMounts = [f"{x[0]}:{x[1]}" for x in mounts if x[1].startswith("/media/")]
			removeMounts = []
			for removeMount in [x for x in mediaMounts if x not in self.deviceMounts]:
				mountPoint = removeMount.split(":")[1]
				removeMounts.append(mountPoint)
			if removeMounts:
				self.console.ePopen([self.UMOUNT, self.UMOUNT] + removeMounts)
				self.console.ePopen([self.MOUNT, self.MOUNT, "-a"])

			cleanMediaDirs()
			harddiskmanager.refreshMountPoints()
			self.close(needReboot)

		oldFstab = fileReadLines("/etc/fstab", default=[], source=MODULE_NAME)
		newFstab = []

		UUIDs = [device[3] for device in self.devices if device[3]]

		for line in oldFstab:
			found = False
			for UUID in UUIDs:
				if UUID in line:
					found = True
					break

			if not found or EXPANDER_MOUNT in line:
				newFstab.append(line)

		self.deviceMounts = []

		for index, device in enumerate(self.devices):
			mountPoint = self.mountPoints[index].value or f"/media/{self.customMountPoints[index].value}"
			fileSystem = self.fileSystems[index].value
			options = self.options[index].value
			# device , fstabmountpoint, isMounted , deviceUuid, name, choiceList
			UUID = device[3]
			if mountPoint != "None":
				self.deviceMounts.append(f"{device[0]}:{mountPoint}")
				if UUID:
					newFstab.append(f"UUID={device[3]}\t{mountPoint}\t{fileSystem}\t{options}\t0 0")
				else:  # This should not happen
					newFstab.append(f"{device[0]}\t{mountPoint}\t{fileSystem}\t{options}\t0 0")
				if not exists(mountPoint):
					mkdir(mountPoint, 0o755)

		if newFstab != oldFstab:
			knownDevices = fileReadLines("/etc/udev/known_devices", default=[], source=MODULE_NAME)
			knownDevicesUUIDs = [x.split(":")[0] for x in knownDevices if ":" in x]
			saveKnownDevices = False
			for line in newFstab:
				if line.startswith("UUID=") and EXPANDER_MOUNT not in line:
					UUID = line.split()[0].replace("UUID=", "")
					if UUID not in knownDevicesUUIDs:
						mountPoint = line.split()[1]
						knownDevices.append(f"{UUID}:{mountPoint}")
						saveKnownDevices = True
			if saveKnownDevices:
				fileWriteLines("/etc/udev/known_devices", knownDevices, source=MODULE_NAME)
			fileWriteLines("/etc/fstab", newFstab, source=MODULE_NAME)
			self.console.ePopen([self.MOUNT, self.MOUNT, "-a"], keySaveCallback)
		else:
			self.close(False)

	def closeRecursive(self):
		self.close(False)

	def keyCancel(self):
		self.close(False)


class DeviceManagerSetup(Setup):
	def __init__(self, session):
		Setup.__init__(self, session, "HardDisk")


class DevicesPanelSummary(Screen):
	def __init__(self, session, parent):
		Screen.__init__(self, session, parent=parent)
		self.skinName = "SetupSummary"
		self["entry"] = StaticText("")
		self["value"] = StaticText("")
		self.onShow.append(self.addWatcher)
		self.onHide.append(self.removeWatcher)

	def addWatcher(self):
		self.parent.onChangedEntry.append(self.selectionChanged)
		self.parent.selectionChanged()

	def removeWatcher(self):
		self.parent.onChangedEntry.remove(self.selectionChanged)

	def selectionChanged(self, name, desc):
		self["entry"].text = name
		self["value"].text = desc
