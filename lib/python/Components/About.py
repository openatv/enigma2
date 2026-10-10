from array import array
from fcntl import ioctl
from socket import AF_INET, SOCK_DGRAM, inet_ntoa, socket
from struct import pack, unpack
from sys import maxsize, modules

from Components.SystemInfo import BoxInfo
from Tools.Directories import fileReadLines

MODULE_NAME = __name__.split(".")[-1]


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
		print(f"[About] Error: getIfConfig returned an error!  ({str(err)})")
	sock.close()
	return interface


def getIfTransferredData(interfaceName):
	for line in fileReadLines("/proc/net/dev", default=[], source=MODULE_NAME):
		if interfaceName in line:
			data = line.split(f"{interfaceName}:")[1].split()
			rxBytes, txBytes = (data[0], data[8])
			return rxBytes, txBytes


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


# Shims, moved to BoxInfo
getCPUSerial = BoxInfo.getCPUSerial
getCPUInfoString = BoxInfo.getCPUInfoString
getSystemTemperature = BoxInfo.getSystemTemperature
getRAMTemperature = BoxInfo.getRAMTemperature
getCPUCurrentSpeed = BoxInfo.getCPUCurrentSpeed
getCPUBrand = BoxInfo.getCPUBrand
getCPUArch = BoxInfo.getCPUArch
getFlashType = BoxInfo.getFlashType
getDriverInstalledDate = BoxInfo.getDriverInstalledDate
getBoxUptime = BoxInfo.getBoxUptime
getKernelVersionString = BoxInfo.getKernelVersionString
getFlashDateString = BoxInfo.getFlashDateString
getGlibcVersion = BoxInfo.getGlibcVersion
getGccVersion = BoxInfo.getGccVersion
getPythonVersionString = BoxInfo.getPythonVersionString
getVersionString = BoxInfo.getImageVersionString
getImageVersionString = BoxInfo.getImageVersionString
getEnigmaVersionString = BoxInfo.getImageVersionString
getBuildDateString = BoxInfo.getBuildDateString
getUpdateDateString = BoxInfo.getUpdateDateString
getVersionFromOpkg = BoxInfo.getVersionFromOpkg

# For modules that do "from About import about"
about = modules[__name__]
