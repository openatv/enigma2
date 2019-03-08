from Components.Console import Console
import sys
import re
from boxbranding import getImageVersion, getMachineBrand, getMachineBuild
import socket, fcntl, struct
import enigma
import os

# Be carefull with this function. Some legacy code expects this to return a
# string that can be parsed as a float. What's worse, there are some assumptions
# made about what that value means (such as "4.0" signifying a transition point
# for package names (based on oe-alliance versioning))
def getVersionString():
	return getImageVersion()

def parseImageVersionFile():
	result = {}
	try:
		with open('/etc/image-version', 'r') as f:
			lines = f.readlines()
		for x in lines:
			splitted = x.split('=', 1)
			if len(splitted) == 2:
				result[splitted[0].strip()] = splitted[1].strip()
	except:
		pass
	return result

# Use a cached version for two reasons:
# 1. It's faster
# 2. It shows the currently running version rather than the installed, but
#    not active version (because the user has not restarted since updating)
image_version_info = parseImageVersionFile()

def getImageVersionString():
	return image_version_info.get('version', _("unknown"))

def getBuildString():
	return image_version_info.get('build', _("unknown"))

def getLastUpdateString():
	return image_version_info.get('date', _("unknown"))

def getImageUrlString():
	return image_version_info.get('url', "www.beyonwiz.com.au")

def getEnigmaVersionString():
	return enigma.getEnigmaVersionString()

def getGStreamerVersionString():
	return enigma.getGStreamerVersionString()

def getKernelVersionString():
	result = _("unknown")
	try:
		with open("/proc/version","r") as f:
			result = f.read().split(' ', 4)[2].split('-',2)[0]
	except:
		pass
	return result

class BootLoaderVersionFetcher:
	monMap = {
			"Jan": "01", "Feb": "02", "Mar": "03",
			"Apr": "04", "May": "05", "Jun": "06",
			"Jul": "07", "Aug": "08", "Sep": "09",
			"Oct": "10", "Nov": "11", "Dec": "12",
		}
	dateMatch = "(Sun|Mon|Tue|Wed|Thu|Fri|Sat) (" + '|'.join(monMap.keys()) + ") ([ 1-3][0-9]) [0-2][0-9]:[0-5][0-9]:[0-5][0-9] [A-Za-z]+ ([0-9]{4})"
	dateMatchRe = re.compile(dateMatch)

	def __init__(self):
		pass

	def searchBootVer(self, appcallback):
		if (os.path.isfile("/proc/device-tree/bolt/date")):
			with open("/proc/device-tree/bolt/date") as f:
				result = f.read().strip()
			appcallback(result)
		else:
			self.console = Console()
			cmd = "strings -n 28 /dev/mtd3ro | grep ' [0-2][0-9]:[0-5][0-9]:[0-5][0-9] '"
			self.console.ePopen(cmd, callback=self.searchBootVerFinished, extra_args=appcallback)

	def searchBootVerFinished(self, result, retval, extra_args):
		callback = extra_args
		latest_date = (0, 0, 0, "Unknown")
		if retval == 0:
			for line in result.splitlines():
				line = line.strip()
				match = self.dateMatchRe.search(line)
				groups = match and match.groups()
				if groups and len(groups) == 4:
					month = self.monMap[groups[1]]
					day = groups[2]
					if day[0] == ' ':
						day = '0' + day[1:]
					year = groups[3]
					d = (year, month, day, line)
					if latest_date < d:
						latest_date = d
		if callback:
			callback(latest_date[3])

__bootLoaderFetcher = BootLoaderVersionFetcher()

def getBootLoaderVersion(callback):
	__bootLoaderFetcher.searchBootVer(callback)

SIOCGIFADDR    = 0x8915
SIOCGIFBRDADDR = 0x8919
SIOCSIFHWADDR  = 0x8927
SIOCGIFNETMASK = 0x891b
SIOCGIFFLAGS   = 0x8913

ifflags = {
	"up":          0x1,	# interface is up
	"broadcast":   0x2,	# broadcast address valid
	"debug":       0x4,	# turn on debugging
	"loopback":    0x8,	# is a loopback net
	"pointopoint": 0x10,	# interface is has p-p link
	"notrailers":  0x20,	# avoid use of trailers
	"running":     0x40,	# interface RFC2863 OPER_UP
	"noarp":       0x80,	# no ARP protocol
	"promisc":     0x100,	# receive all packets
	"allmulti":    0x200,	# receive all multicast packets
	"master":      0x400,	# master of a load balancer
	"slave":       0x800,	# slave of a load balancer
	"multicast":   0x1000,	# Supports multicast
	"portsel":     0x2000,	# can set media type
	"automedia":   0x4000,	# auto media select active
	"dynamic":     0x8000,	# dialup device with changing addresses
	"lower_up":    0x10000,	# driver signals L1 up
	"dormant":     0x20000,	# driver signals dormant
	"echo":        0x40000,	# echo sent packets
}

def _ifinfo(sock, addr, ifname):
	iface = struct.pack('256s', ifname[:15])
	info  = fcntl.ioctl(sock.fileno(), addr, iface)
	if addr == SIOCSIFHWADDR:
		return ':'.join(['%02X' % ord(char) for char in info[18:24]])
	elif addr == SIOCGIFFLAGS:
		return socket.ntohl(struct.unpack("!L", info[16:20])[0])
	else:
		return socket.inet_ntoa(info[20:24])

def getIfConfig(ifname):
	ifreq = {'ifname': ifname}
	infos = {}
	sock  = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	# offsets defined in /usr/include/linux/sockios.h on linux 2.6
	infos['addr']    = SIOCGIFADDR
	infos['brdaddr'] = SIOCGIFBRDADDR
	infos['hwaddr']  = SIOCSIFHWADDR
	infos['netmask'] = SIOCGIFNETMASK
	infos['flags']   = SIOCGIFFLAGS
	try:
		for k,v in infos.items():
			ifreq[k] = _ifinfo(sock, v, ifname)
	except:
		pass
	if 'flags' in ifreq:
		flags = ifreq['flags']
		ifreq['flags'] = dict([(name, bool(flags & flag)) for name, flag in ifflags.items()])
	sock.close()
	return ifreq

def getAllIfTransferredData():
	transData = {}
	with open("/proc/net/dev") as f:
		lines = f.readlines()
	for line in lines:
		flds = line.split(':')
		if len(flds) > 1:
			ifname = flds[0].strip()
			flds = flds[1].strip().split()
			rx_bytes, tx_bytes = (flds[0], flds[8])
			transData[ifname] = (rx_bytes, tx_bytes)
	return transData

def getIfTransferredData(ifname):
	with open("/proc/net/dev") as f:
		lines = f.readlines()
	for line in lines:
		if ifname in line:
			data = line.split('%s:' % ifname)[1].split()
			rx_bytes, tx_bytes = (data[0], data[8])
			return rx_bytes, tx_bytes
	return None

def getGateways():
	gateways = {}
	count = 0
	with open("/proc/net/route") as f:
		lines = f.readlines()
	for line in lines:
		if count > 0:
			flds = line.strip().split()
			for i in range(1, 4):
				flds[i] = int(flds[i], 16)
			if flds[3] & 2:
				if flds[0] not in gateways:
					gateways[flds[0]] = []
				gateways[flds[0]].append({
					"destination": socket.inet_ntoa(struct.pack("!L", socket.htonl(flds[1]))),
					"gateway": socket.inet_ntoa(struct.pack("!L", socket.htonl(flds[2])))
				})
		count += 1
	return gateways

def getIfGateways(ifname):
	return getGateways().get(ifname)

def getModelString():
	result = _("unknown")
	try:
		with open("/proc/stb/info/boxtype", "r") as f:
			result = f.readline().strip()
	except:
		pass
	return result

def getIsBroadcom():
	try:
		with open('/proc/cpuinfo', 'r') as f:
			lines = f.readlines()
		for x in lines:
			splitted = x.split(': ')
			if len(splitted) > 1:
				splitted[1] = splitted[1].replace('\n','')
				if splitted[0].startswith("Hardware"):
					system = splitted[1].split(' ')[0]
				elif splitted[0].startswith("system type"):
					if splitted[1].split(' ')[0].startswith('BCM'):
						system = 'Broadcom'
		if 'Broadcom' in system:
			return True
	except:
		pass
	return False

def getChipSetString():
	result = _("unknown")
	try:
		with open('/proc/stb/info/chipset', 'r') as f:
			chipset = f.read()
		return str(chipset.lower().replace('\n','').replace('brcm','').replace('bcm',''))
	except:
		pass
	return result

def getCPUSpeedString():
	cpu_speed = 0
	try:
		with open('/proc/cpuinfo', 'r') as f:
			lines = f.readlines()
		for x in lines:
			splitted = x.split(': ')
			if len(splitted) > 1:
				splitted[1] = splitted[1].replace('\n','')
				if splitted[0].startswith("cpu MHz"):
					cpu_speed = float(splitted[1].split(' ')[0])
					break

		if cpu_speed == 0:
			if getMachineBuild() in ('hd51','hd52','sf4008'):
				import binascii
				with open('/sys/firmware/devicetree/base/cpus/cpu@0/clock-frequency', 'rb') as f:
					clockfrequency = f.read()
				cpu_speed = round(int(binascii.hexlify(clockfrequency), 16)/1000000,1)
			else:
				with open('/sys/devices/system/cpu/cpu0/cpufreq/cpuinfo_max_freq', 'r') as f:
					cpu_speed = float(f.read()) / 1000
	except:
		pass

	if cpu_speed > 0:
		return "%sMHz" % str(int(cpu_speed))
	return _("unknown")

def getCPUArch():
	if "ARM" in getCPUString():
		return getCPUString()
	return _("Mipsel")

def getCPUString():
	result = _("unknown")
	try:
		with open('/proc/cpuinfo', 'r') as f:
			lines = f.readlines()
		for x in lines:
			splitted = x.split(': ')
			if len(splitted) > 1:
				splitted[1] = splitted[1].replace('\n','')
				if splitted[0].startswith("system type"):
					result = splitted[1].split(' ')[0]
				elif splitted[0].startswith("model name"):
					result = splitted[1].split(' ')[0]
				elif splitted[0].startswith("Processor"):
					result = splitted[1].split(' ')[0]
	except:
		pass
	return result

def getCpuCoresString():
	cores = 0
	try:
		with open('/proc/cpuinfo', 'r') as f:
			lines = f.readlines()
		for x in lines:
			splitted = x.split(': ')
			if len(splitted) > 1:
				splitted[1] = splitted[1].replace('\n','')
				if splitted[0].startswith("processor"):
					cores = max(cores, int(splitted[1]))
	except:
		pass
	return str(cores + 1)

def getPythonVersionString():
	v = sys.version_info
	return "%s.%s.%s" % (v[0], v[1], v[2])

# For modules that do "from About import about"
about = sys.modules[__name__]
