from Tools.Directories import resolveFilename, SCOPE_SYSETC
from Components.Console import Console
import sys
import time
import re
from boxbranding import getImageVersion, getMachineBrand
from sys import modules
import socket, fcntl, struct

def getVersionString():
	return getImageVersion()

def getImageVersionString():
	try:
		file = open(resolveFilename(SCOPE_SYSETC, 'image-version'), 'r')
		lines = file.readlines()
		for x in lines:
			splitted = x.split('=')
			if splitted[0] == "version":
				version = splitted[1].replace('\n','')
		file.close()
		return version
	except IOError:
		return "unavailable"

def getImageUrlString():
	try:
		if getMachineBrand() == "GI":
			return "www.xpeed-lx.de"
		elif getMachineBrand() == "Beyonwiz":
			return "www.beyonwiz.com.au"
		else:
			file = open(resolveFilename(SCOPE_SYSETC, 'image-version'), 'r')
			lines = file.readlines()
			for x in lines:
				splitted = x.split('=')
				if splitted[0] == "url":
					version = splitted[1].replace('\n','')
			file.close()
			return version
	except IOError:
		return "unavailable"

def getEnigmaVersionString():
	return getImageVersion()

def getGStreamerVersionString():
	import enigma
	return enigma.getGStreamerVersionString()

def getKernelVersionString():
	try:
		f = open("/proc/version","r")
		kernelversion = f.read().split(' ', 4)[2].split('-',2)[0]
		f.close()
		return kernelversion
	except:
		return _("unknown")

def getLastUpdateString():
	try:
		file = open(resolveFilename(SCOPE_SYSETC, 'image-version'), 'r')
		lines = file.readlines()
		for x in lines:
			splitted = x.split('=')
			if splitted[0] == "date":
				#YYYY MM DD hh mm
				#2005 11 29 01 16
				string = splitted[1].replace('\n','')
				year = string[0:4]
				month = string[4:6]
				day = string[6:8]
				date = '-'.join((year, month, day))
				hour = string[8:10]
				minute = string[10:12]
				time = ':'.join((hour, minute))
				lastupdated = ' '.join((date, time))
		file.close()
		return lastupdated
	except IOError:
		return "unavailable"


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
		self.console = Console()
		cmd = "strings -n 28 /dev/mtd3ro | grep ' [0-2][0-9]:[0-5][0-9]:[0-5][0-9] '"
		self.console.ePopen(cmd, callback=self.searchBootVerFinished, extra_args=appcallback)

	def searchBootVerFinished(self, result, retval, extra_args):
		callback = extra_args
		latest_date = (0, 0, 0, "Unknown")
		for line in result.splitlines():
			line = line.strip()
			match = self.dateMatchRe.search(line)
			groups = match.groups()
			if len(groups) == 4:
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

import socket, fcntl, struct

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
	for line in file("/proc/net/dev").readlines():
		flds = line.split(':')
		if len(flds) > 1:
			ifname = flds[0].strip()
			flds = flds[1].strip().split()
			rx_bytes, tx_bytes = (flds[0], flds[8])
			transData[ifname] = (rx_bytes, tx_bytes)
	return transData

def getIfTransferredData(ifname):
	for line in file("/proc/net/dev").readlines():
		if ifname in line:
			data = line.split('%s:' % ifname)[1].split()
			rx_bytes, tx_bytes = (data[0], data[8])
			return rx_bytes, tx_bytes
	return None

def getGateways():
	gateways = {}
	count = 0
	for line in file("/proc/net/route").readlines():
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
	try:
		file = open("/proc/stb/info/boxtype", "r")
		model = file.readline().strip()
		file.close()
		return model
	except IOError:
		return "unknown"		

def getChipSetString():
	try:
		f = open('/proc/stb/info/chipset', 'r')
		chipset = f.read()
		f.close()
		return str(chipset.lower().replace('\n','').replace('bcm',''))
	except IOError:
		return "unavailable"

def getCPUSpeedString():
	try:
		file = open('/proc/cpuinfo', 'r')
		lines = file.readlines()
		for x in lines:
			splitted = x.split(': ')
			if len(splitted) > 1:
				splitted[1] = splitted[1].replace('\n','')
				if splitted[0].startswith("cpu MHz"):
					mhz = float(splitted[1].split(' ')[0])
					if mhz and mhz >= 1000:
						mhz = "%s GHz" % str(round(mhz/1000,1))
					else:
						mhz = "%s MHz" % str(round(mhz,1))
		file.close()
		return mhz
	except IOError:
		return "unavailable"

def getCPUString():
	try:
		file = open('/proc/cpuinfo', 'r')
		lines = file.readlines()
		for x in lines:
			splitted = x.split(': ')
			if len(splitted) > 1:
				splitted[1] = splitted[1].replace('\n','')
				if splitted[0].startswith("system type"):
					system = splitted[1].split(' ')[0]
				elif splitted[0].startswith("Processor"):
					system = splitted[1].split(' ')[0]
		file.close()
		return system 
	except IOError:
		return "unavailable"

def getCpuCoresString():
	try:
		file = open('/proc/cpuinfo', 'r')
		lines = file.readlines()
		for x in lines:
			splitted = x.split(': ')
			if len(splitted) > 1:
				splitted[1] = splitted[1].replace('\n','')
				if splitted[0].startswith("processor"):
					if int(splitted[1]) > 0:
						cores = 2
					else:
						cores = 1
		file.close()
		return cores
	except IOError:
		return "unavailable"

# For modules that do "from About import about"
about = sys.modules[__name__]
