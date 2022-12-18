from array import array
from binascii import hexlify
from fcntl import ioctl
from glob import glob
from locale import format_string
from os import popen, stat
from os.path import isfile
from re import search
from socket import AF_INET, SOCK_DGRAM, inet_ntoa, socket
from struct import pack, unpack
from subprocess import PIPE, Popen
from sys import maxsize, modules, version as pyversion
from time import localtime, strftime

from Components.SystemInfo import BoxInfo
from Tools.Directories import fileReadLine, fileReadLines

MODULE_NAME = __name__.split(".")[-1]

socfamily = BoxInfo.getItem("socfamily")
MODEL = BoxInfo.getItem("model")


def _ifinfo(sock, addr, ifname):
	iface = pack('256s', bytes(ifname[:15], 'utf-8'))
	info = ioctl(sock.fileno(), addr, iface)
	if addr == 0x8927:
		return ''.join(['%02x:' % ord(chr(char)) for char in info[18:24]])[:-1].upper()
	else:
		return inet_ntoa(info[20:24])


def getIfConfig(ifname):
	ifreq = {"ifname": ifname}
	infos = {}
	sock = socket(AF_INET, SOCK_DGRAM)
	# Offsets defined in /usr/include/linux/sockios.h on linux 2.6.
	infos["addr"] = 0x8915  # SIOCGIFADDR
	infos["brdaddr"] = 0x8919  # SIOCGIFBRDADDR
	infos["hwaddr"] = 0x8927  # SIOCSIFHWADDR
	infos["netmask"] = 0x891b  # SIOCGIFNETMASK
	try:
		for k, v in infos.items():
			ifreq[k] = _ifinfo(sock, v, ifname)
	except Exception as ex:
		print("[About] getIfConfig Ex: %s" % str(ex))
		pass
	sock.close()
	return ifreq


def getIfTransferredData(ifname):
	lines = fileReadLines("/proc/net/dev", source=MODULE_NAME)
	if lines:
		for line in lines:
			if ifname in line:
				data = line.split("%s:" % ifname)[1].split()
				rx_bytes, tx_bytes = (data[0], data[8])
				return rx_bytes, tx_bytes


def getVersionString():
	return str(BoxInfo.getItem("imageversion"))


def getImageVersionString():
	return str(BoxInfo.getItem("imageversion"))


def getFlashDateString():
	try:
		tm = localtime(stat("/boot").st_ctime)
		if tm.tm_year >= 2011:
			return strftime(_("%Y-%m-%d"), tm)
		else:
			return _("Unknown")
	except:
		return _("Unknown")


def getBuildDateString():
	version = fileReadLine("/etc/version", source=MODULE_NAME)
	if version is None:
		return _("Unknown")
	return "%s-%s-%s" % (version[:4], version[4:6], version[6:8])


def getUpdateDateString():
	build = BoxInfo.getItem("compiledate")
	if build and build.isdigit():
		return "%s-%s-%s" % (build[:4], build[4:6], build[6:])
	return _("Unknown")


def getEnigmaVersionString():
	return str(BoxInfo.getItem("imageversion"))


def getGStreamerVersionString():
	from enigma import getGStreamerVersionString
	return getGStreamerVersionString()


def getFFmpegVersionString():
	lines = fileReadLines("/var/lib/opkg/info/ffmpeg.control", source=MODULE_NAME)
	if lines:
		for line in lines:
			if line[0:8] == "Version:":
				return line[9:].split("+")[0]
	return _("Not Installed")


def getKernelVersionString():
	version = fileReadLine("/proc/version", source=MODULE_NAME)
	if version is None:
		return _("Unknown")
	return version.split(" ", 4)[2].split("-", 2)[0]


def getCPUSerial():
	lines = fileReadLines("/proc/cpuinfo", source=MODULE_NAME)
	if lines:
		for line in lines:
			if line[0:6] == "Serial":
				return line[10:26]
	return _("Undefined")


def _getCPUSpeedMhz():
	if MODEL in ('hzero', 'h8', 'sfx6008', 'sfx6018'):
		return 1200
	elif MODEL in ('vuduo4k',):
		return 2100
	else:
		return 0


def getCPUInfoString():
	cpuCount = 0
	cpuSpeedStr = "-"
	cpuSpeedMhz = _getCPUSpeedMhz()
	processor = ""
	lines = fileReadLines("/proc/cpuinfo", source=MODULE_NAME)
	if lines:
		for line in lines:
			line = [x.strip() for x in line.strip().split(":", 1)]
			if not processor and line[0] in ("system type", "model name", "Processor"):
				processor = line[1].split()[0]
			elif not cpuSpeedMhz and line[0] == "cpu MHz":
				cpuSpeedMhz = float(line[1])
			elif line[0] == "processor":
				cpuCount += 1
		if processor.startswith("ARM") and isfile("/proc/stb/info/chipset"):
			processor = "%s (%s)" % (fileReadLine("/proc/stb/info/chipset", "", source=MODULE_NAME).upper(), processor)
		if not cpuSpeedMhz:
			cpuSpeed = fileReadLine("/sys/devices/system/cpu/cpu0/cpufreq/cpuinfo_max_freq", source=MODULE_NAME)
			if cpuSpeed:
				cpuSpeedMhz = int(cpuSpeed) / 1000
			else:
				try:
					cpuSpeedMhz = int(int(hexlify(open("/sys/firmware/devicetree/base/cpus/cpu@0/clock-frequency", "rb").read()), 16) / 100000000) * 100
				except:
					cpuSpeedMhz = "1500"
		temperature = None
		if isfile("/proc/stb/fp/temp_sensor_avs"):
			temperature = fileReadLine("/proc/stb/fp/temp_sensor_avs", source=MODULE_NAME)
		elif isfile("/proc/stb/power/avs"):
			temperature = fileReadLine("/proc/stb/power/avs", source=MODULE_NAME)
#		elif isfile("/proc/stb/fp/temp_sensor"):
#			temperature = fileReadLine("/proc/stb/fp/temp_sensor", source=MODULE_NAME)
#		elif isfile("/proc/stb/sensors/temp0/value"):
#			temperature = fileReadLine("/proc/stb/sensors/temp0/value", source=MODULE_NAME)
#		elif isfile("/proc/stb/sensors/temp/value"):
#			temperature = fileReadLine("/proc/stb/sensors/temp/value", source=MODULE_NAME)
		elif isfile("/sys/devices/virtual/thermal/thermal_zone0/temp"):
			temperature = fileReadLine("/sys/devices/virtual/thermal/thermal_zone0/temp", source=MODULE_NAME)
			if temperature:
				temperature = int(temperature) / 1000
		elif isfile("/sys/class/thermal/thermal_zone0/temp"):
			temperature = fileReadLine("/sys/class/thermal/thermal_zone0/temp", source=MODULE_NAME)
			if temperature:
				temperature = int(temperature) / 1000
		elif isfile("/proc/hisi/msp/pm_cpu"):
			lines = fileReadLines("/proc/hisi/msp/pm_cpu", source=MODULE_NAME)
			if lines:
				for line in lines:
					if "temperature = " in line:
						temperature = int(line.split("temperature = ")[1].split()[0])

		if cpuSpeedMhz and cpuSpeedMhz >= 1000:
			cpuSpeedStr = _("%s GHz") % format_string("%.1f", cpuSpeedMhz / 1000)
		else:
			cpuSpeedStr = _("%d MHz") % int(cpuSpeedMhz)

		if temperature:
			degree = u"\u00B0"
			if not isinstance(degree, str):
				degree = degree.encode("UTF-8", errors="ignore")
			if isinstance(temperature, float):
				temperature = format_string("%.1f", temperature)
			else:
				temperature = str(temperature)
			return (processor, cpuSpeedStr, ngettext("%d core", "%d cores", cpuCount) % cpuCount, "%s%s C" % (temperature, degree))
			#return ("%s %s MHz (%s) %s%sC") % (processor, cpuSpeed, ngettext("%d core", "%d cores", cpuCount) % cpuCount, temperature, degree)
		return (processor, cpuSpeedStr, ngettext("%d core", "%d cores", cpuCount) % cpuCount, "")
		#return ("%s %s MHz (%s)") % (processor, cpuSpeed, ngettext("%d core", "%d cores", cpuCount) % cpuCount)


def getSystemTemperature():
	temperature = ""
	if isfile("/proc/stb/sensors/temp0/value"):
		temperature = fileReadLine("/proc/stb/sensors/temp0/value", source=MODULE_NAME)
	elif isfile("/proc/stb/sensors/temp/value"):
		temperature = fileReadLine("/proc/stb/sensors/temp/value", source=MODULE_NAME)
	elif isfile("/proc/stb/fp/temp_sensor"):
		temperature = fileReadLine("/proc/stb/fp/temp_sensor", source=MODULE_NAME)
	if temperature:
		return "%s%s C" % (temperature, u"\u00B0")
	return temperature


def getChipSetString():
	if MODEL in ('dm7080', 'dm820'):
		return "7435"
	elif MODEL in ('dm520', 'dm525'):
		return "73625"
	elif MODEL in ('dm900', 'dm920', 'et13000', 'sf5008'):
		return "7252S"
	elif MODEL in ('hd51', 'vs1500', 'h7'):
		return "7251S"
	elif MODEL in ('alien5',):
		return "S905D"
	else:
		chipset = fileReadLine("/proc/stb/info/chipset", source=MODULE_NAME)
		if chipset is None:
			return _("Undefined")
		return str(chipset.lower().replace('\n', '').replace('bcm', '').replace('brcm', '').replace('sti', ''))


def getCPUBrand():
	if BoxInfo.getItem("AmlogicFamily"):
		return _("Amlogic")
	elif BoxInfo.getItem("HiSilicon"):
		return _("HiSilicon")
	elif socfamily.startswith("smp"):
		return _("Sigma Designs")
	elif BoxInfo.getItem("STi"):
		return _("Sti")
	elif socfamily.startswith("bcm") or BoxInfo.getItem("brand") == "rpi":
		return _("Broadcom")
	print("[About] No CPU brand?")
	return _("Undefined")


def getCPUArch():
	if BoxInfo.getItem("ArchIsARM64"):
		return _("ARM64")
	elif BoxInfo.getItem("ArchIsARM"):
		return _("ARM")
	return _("Mipsel")


def getFlashType():
	if BoxInfo.getItem("SmallFlash"):
		return _("Small - Tiny image")
	elif BoxInfo.getItem("MiddleFlash"):
		return _("Middle - Lite image")
	return _("Normal - Standard image")


def getDriverInstalledDate():

	def extractDate(value):
		match = search('[0-9]{8}', value)
		if match:
			return match[0]
		else:
			return value

	filenames = glob("/var/lib/opkg/info/*dvb-modules*.control")
	if filenames:
		lines = fileReadLines(filenames[0], source=MODULE_NAME)
		if lines:
			for line in lines:
				if line[0:8] == "Version:":
					return extractDate(line)
	filenames = glob("/var/lib/opkg/info/*dvb-proxy*.control")
	if filenames:
		lines = fileReadLines(filenames[0], source=MODULE_NAME)
		if lines:
			for line in lines:
				if line[0:8] == "Version:":
					return extractDate(line)
	filenames = glob("/var/lib/opkg/info/*platform-util*.control")
	if filenames:
		lines = fileReadLines(filenames[0], source=MODULE_NAME)
		if lines:
			for line in lines:
				if line[0:8] == "Version:":
					return extractDate(line)
	return _("Unknown")


def getPythonVersionString():
	try:
		return pyversion.split(' ')[0]
	except:
		return _("Unknown")


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
		ifaceName = names.tobytes()[index:index + 16].decode().split("\0", 1)[0]  # PY3
		# ifaceName = str(names.tolist[index:index + 16]).split("\0", 1)[0] # PY2
		if ifaceName != "lo":
			ifaces.append((ifaceName, inet_ntoa(names[index + 20:index + 24])))
	return ifaces


def getBoxUptime():
	upTime = fileReadLine("/proc/uptime", source=MODULE_NAME)
	if upTime is None:
		return "-"
	secs = int(upTime.split(".")[0])
	times = []
	if secs > 86400:
		days = secs // 86400
		secs = secs % 86400
		times.append(ngettext("%d Day", "%d Days", days) % days)
	h = secs // 3600
	m = (secs % 3600) // 60
	times.append(ngettext("%d Hour", "%d Hours", h) % h)
	times.append(ngettext("%d Minute", "%d Minutes", m) % m)
	return " ".join(times)


def getGlibcVersion():
	process = Popen(("/lib/libc.so.6"), stdout=PIPE, stderr=PIPE, universal_newlines=True)
	stdout, stderr = process.communicate()
	if process.returncode == 0:
		for line in stdout.split("\n"):
			if line.startswith("GNU C Library"):
				data = line.split()[-1]
				if data.endswith("."):
					data = data[0:-1]
				return data
	print("[About] Get glibc version failed.")
	return _("Unknown")


def getGccVersion():
	process = Popen(("/lib/libc.so.6"), stdout=PIPE, stderr=PIPE, universal_newlines=True)
	stdout, stderr = process.communicate()
	if process.returncode == 0:
		for line in stdout.split("\n"):
			if line.startswith("Compiled by GNU CC version"):
				data = line.split()[-1]
				if data.endswith("."):
					data = data[0:-1]
				return data
	print("[About] Get gcc version failed.")
	return _("Unknown")


def getopensslVersionString():
	lines = fileReadLines("/var/lib/opkg/info/openssl.control", source=MODULE_NAME)
	if lines:
		for line in lines:
			if line[0:8] == "Version:":
				return line[9:].split("+")[0]
	return _("Not Installed")


# For modules that do "from About import about"
about = modules[__name__]
