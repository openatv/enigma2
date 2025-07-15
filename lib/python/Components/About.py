from array import array
from binascii import hexlify
from fcntl import ioctl
from glob import glob
from locale import format_string
from os import stat
from os.path import isfile
from platform import libc_ver
from re import search
from socket import AF_INET, SOCK_DGRAM, inet_ntoa, socket
from struct import pack, unpack
from sys import maxsize, modules, version as pyversion
from time import localtime, strftime

from Components.SystemInfo import BoxInfo
from Tools.Directories import fileReadLine, fileReadLines

MODULE_NAME = __name__.split(".")[-1]

DEGREE = "\u00B0"


def getIfConfig(interfaceName):
	def interfaceInfo(sock, value, interfaceName):
		interface = pack("256s", bytes(interfaceName[:15], "UTF-8"))
		info = ioctl(sock.fileno(), value, interface)
		return "".join([f"{ord(chr(character)):02x}:" for character in info[18:24]])[:-1].upper() if value == 0x8927 else inet_ntoa(info[20:24])

	interface = {"ifname": interfaceName}
	info = {}
	# Offsets defined in /usr/include/linux/sockios.h on linux 2.6.
	info["addr"] = 0x8915  # SIOCGIFADDR
	info["brdaddr"] = 0x8919  # SIOCGIFBRDADDR
	info["hwaddr"] = 0x8927  # SIOCSIFHWADDR
	info["netmask"] = 0x891b  # SIOCGIFNETMASK
	sock = socket(AF_INET, SOCK_DGRAM)
	try:
		for key, value in info.items():
			interface[key] = interfaceInfo(sock, value, interfaceName)
	except Exception as err:
		print("[About] Error: getIfConfig returned an error!  ({str(err)})")
	sock.close()
	return interface


def getIfTransferredData(interfaceName):
	for line in fileReadLines("/proc/net/dev", default=[], source=MODULE_NAME):
		if interfaceName in line:
			data = line.split(f"{interfaceName}:")[1].split()
			rxBytes, txBytes = (data[0], data[8])
			return rxBytes, txBytes


def getVersionString():
	return str(BoxInfo.getItem("imageversion"))


def getImageVersionString():
	return str(BoxInfo.getItem("imageversion"))


def getFlashDateString():
	try:
		localTime = localtime(stat("/home").st_ctime)
		return strftime(_("%Y-%m-%d"), localTime) if localTime.tm_year >= 2011 else _("Unknown")
	except Exception:
		return _("Unknown")


def getBuildDateString():
	version = fileReadLine("/etc/version", default="", source=MODULE_NAME)
	return f"{version[:4]}-{version[4:6]}-{version[6:8]}" if version else _("Unknown")


def getUpdateDateString():
	build = BoxInfo.getItem("compiledate")
	return f"{build[:4]}-{build[4:6]}-{build[6:]}" if build and build.isdigit() else _("Unknown")


def getEnigmaVersionString():
	return str(BoxInfo.getItem("imageversion"))


def getKernelVersionString():
	version = fileReadLine("/proc/version", default="", source=MODULE_NAME)
	return version.split(" ", 4)[2].split("-", 2)[0] if version else _("Unknown")


def getCPUSerial():
	result = _("Undefined")
	for line in fileReadLines("/proc/cpuinfo", default=[], source=MODULE_NAME):
		if line[0:6] == "Serial":
			result = line[10:26]
			break
	return result


def _getCPUSpeedMhz():
	result = 0
	model = BoxInfo.getItem("model")
	if model in ("hzero", "h8", "sfx6008", "sfx6018"):
		result = 1200
	elif model in ("dreamone", "dreamtwo", "dreamseven"):
		result = 1800
	elif model in ("vuduo4k",):
		result = 2100
	return result


def getCPUInfoString():
	cpuCount = 0
	cpuSpeedStr = "-"
	cpuSpeedMhz = _getCPUSpeedMhz()
	processor = ""
	for line in fileReadLines("/proc/cpuinfo", default=[], source=MODULE_NAME):
		line = [x.strip() for x in line.strip().split(":", 1)]
		if not processor and line[0] in ("system type", "model name", "Processor"):
			processor = line[1].split()[0]
		elif not cpuSpeedMhz and line[0] == "cpu MHz":
			cpuSpeedMhz = float(line[1])
		elif line[0] == "processor":
			cpuCount += 1
	if processor.startswith("ARM") and isfile("/proc/stb/info/chipset"):
		processor = f"{fileReadLine("/proc/stb/info/chipset", default="", source=MODULE_NAME).upper()} ({processor})"
	if not cpuSpeedMhz:
		cpuSpeed = fileReadLine("/sys/devices/system/cpu/cpu0/cpufreq/cpuinfo_max_freq", default="", source=MODULE_NAME)
		if cpuSpeed:
			cpuSpeedMhz = int(cpuSpeed) / 1000
		else:
			try:
				cpuSpeedMhz = int(int(hexlify(open("/sys/firmware/devicetree/base/cpus/cpu@0/clock-frequency", "rb").read()), 16) / 100000000) * 100
			except Exception:
				cpuSpeedMhz = 1500
	temperature = None
	if isfile("/proc/stb/fp/temp_sensor_avs"):
		temperature = fileReadLine("/proc/stb/fp/temp_sensor_avs", default=None, source=MODULE_NAME)
	elif isfile("/proc/stb/power/avs"):
		temperature = fileReadLine("/proc/stb/power/avs", default=None, source=MODULE_NAME)
	# elif isfile("/proc/stb/fp/temp_sensor"):
	# 	temperature = fileReadLine("/proc/stb/fp/temp_sensor", default=None, source=MODULE_NAME)
	# elif isfile("/proc/stb/sensors/temp0/value"):
	# 	temperature = fileReadLine("/proc/stb/sensors/temp0/value", default=None, source=MODULE_NAME)
	# elif isfile("/proc/stb/sensors/temp/value"):
	# 	temperature = fileReadLine("/proc/stb/sensors/temp/value", default=None, source=MODULE_NAME)
	elif isfile("/sys/devices/virtual/thermal/thermal_zone0/temp"):
		temperature = fileReadLine("/sys/devices/virtual/thermal/thermal_zone0/temp", default=None, source=MODULE_NAME)
		if temperature:
			temperature = int(temperature) / 1000
	elif isfile("/sys/class/thermal/thermal_zone0/temp"):
		temperature = fileReadLine("/sys/class/thermal/thermal_zone0/temp", default=None, source=MODULE_NAME)
		if temperature:
			temperature = int(temperature) / 1000
	elif isfile("/proc/hisi/msp/pm_cpu"):
		for line in fileReadLines("/proc/hisi/msp/pm_cpu", default=[], source=MODULE_NAME):
			if "temperature = " in line:
				temperature = int(line.split("temperature = ")[1].split()[0])
				# break  # Without this break the code returns the last line containing the string!
	cpuSpeedStr = _("%s GHz") % format_string("%.1f", cpuSpeedMhz / 1000) if cpuSpeedMhz and cpuSpeedMhz >= 1000 else _("%d MHz") % int(cpuSpeedMhz)
	if temperature:
		if isinstance(temperature, float):
			temperature = format_string("%.1f", temperature)
		else:
			temperature = str(temperature)
		return (processor, cpuSpeedStr, ngettext("%d core", "%d cores", cpuCount) % cpuCount, f"{temperature}{DEGREE}C")
		# return f"{processor} {cpuSpeed} MHz ({ngettext("%d core", "%d cores", cpuCount) % cpuCount}) {temperature}{DEGREE}C"
	return (processor, cpuSpeedStr, ngettext("%d core", "%d cores", cpuCount) % cpuCount, "")
	# return f"{processor} {cpuSpeed} MHz ({ngettext("%d core", "%d cores", cpuCount) % cpuCount})"


def getSystemTemperature():
	if isfile("/proc/stb/sensors/temp0/value"):
		temperature = fileReadLine("/proc/stb/sensors/temp0/value", default=None, source=MODULE_NAME)
	elif isfile("/proc/stb/sensors/temp/value"):
		temperature = fileReadLine("/proc/stb/sensors/temp/value", default=None, source=MODULE_NAME)
	elif isfile("/proc/stb/fp/temp_sensor"):
		temperature = fileReadLine("/proc/stb/fp/temp_sensor", default=None, source=MODULE_NAME)
	else:
		temperature = None
	return f"{temperature}{DEGREE}C" if temperature else ""


def getCPUBrand():
	socFamily = BoxInfo.getItem("socfamily")
	if BoxInfo.getItem("AmlogicFamily"):
		result = _("Amlogic")
	elif BoxInfo.getItem("HiSilicon"):
		result = _("HiSilicon")
	elif socFamily.startswith("smp"):
		result = _("Sigma Designs")
	elif socFamily.startswith("bcm") or BoxInfo.getItem("brand") == "rpi":
		result = _("Broadcom")
	else:
		print("[About] Error: No CPU brand!")
		result = _("Undefined")
	return result


def getCPUArch():
	if BoxInfo.getItem("ArchIsARM64"):
		result = _("ARM64")
	elif BoxInfo.getItem("ArchIsARM"):
		result = _("ARM")
	else:
		result = _("Mipsel")
	return result


def getFlashType():
	if BoxInfo.getItem("SmallFlash"):
		result = _("Small - Tiny image")
	elif BoxInfo.getItem("MiddleFlash"):
		result = _("Middle - Lite image")
	else:
		result = _("Normal - Standard image")
	return result


def getDriverInstalledDate():
	result = None
	for template in ("/var/lib/opkg/info/*dvb-modules*.control", "/var/lib/opkg/info/*dvb-proxy*.control", "/var/lib/opkg/info/*platform-util*.control"):
		filenames = glob(template)
		if filenames:
			for line in fileReadLines(filenames[0], default=[], source=MODULE_NAME):
				if line[0:8] == "Version:":
					value = line[8:].strip()
					match = search(r"\d{8}", value)
					result = match[0] if match else value
					break
		if result:
			break
	return result if result else _("Unknown")


def GetIPsFromNetworkInterfaces():
	structSize = 40 if maxsize > 2 ** 32 else 32
	sock = socket(AF_INET, SOCK_DGRAM)
	maxPossible = 8  # Initial value.
	while True:
		_bytes = maxPossible * structSize
		names = array("B")
		for index in range(_bytes):
			names.append(0)
		outbytes = unpack("iL", ioctl(sock.fileno(), 0x8912, pack("iL", _bytes, names.buffer_info()[0])))[0]  # 0x8912 = SIOCGIFCONF
		if outbytes == _bytes:
			maxPossible *= 2
		else:
			break
	ifaces = []
	for index in range(0, outbytes, structSize):
		ifaceName = names.tobytes()[index:index + 16].decode().split("\0", 1)[0]
		if ifaceName != "lo":
			ifaces.append((ifaceName, inet_ntoa(names[index + 20:index + 24])))
	return ifaces


def getBoxUptime():
	upTime = fileReadLine("/proc/uptime", default=None, source=MODULE_NAME)
	if upTime:
		seconds = int(upTime.split(".")[0])
		times = []
		if seconds > 86400:
			days = seconds // 86400
			seconds = seconds % 86400
			times.append(ngettext("%d Day", "%d Days", days) % days)
		hours = seconds // 3600
		minutes = (seconds % 3600) // 60
		times.append(ngettext("%d Hour", "%d Hours", hours) % hours)
		times.append(ngettext("%d Minute", "%d Minutes", minutes) % minutes)
		result = " ".join(times)
	else:
		result = "-"
	return result


def getGlibcVersion():
	try:
		result = libc_ver()[1]
	except Exception:
		print("[About] Error: Get glibc version failed!")
		result = _("Unknown")
	return result


def getGccVersion():
	try:
		result = pyversion.split("[GCC ")[1].replace("]", "")
	except Exception:
		print("[About] Error: Get gcc version failed!")
		result = _("Unknown")
	return result


def getPythonVersionString():
	try:
		result = pyversion.split(" ")[0]
	except Exception:
		result = _("Unknown")
	return result


def getVersionFromOpkg(fileName):
	return next((line[9:].split("+")[0] for line in fileReadLines(f"/var/lib/opkg/info/{fileName}.control", default=[], source=MODULE_NAME) if line.startswith("Version:")), _("Not Installed"))


# For modules that do "from About import about"
about = modules[__name__]
