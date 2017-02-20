from boxbranding import getImageVersion, getMachineBuild
from sys import modules
import socket, fcntl, struct

def getVersionString():
	return getImageVersion()

def getFlashDateString():
	try:
		f = open("/etc/install","r")
		flashdate = f.read()
		f.close()
		return flashdate
	except:
		return _("unknown")

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

def getChipSetString():
	try:
		f = open('/proc/stb/info/chipset', 'r')
		chipset = f.read()
		f.close()
		return str(chipset.lower().replace('\n','').replace('brcm','bcm'))
	except IOError:
		return _("unavailable")

def getCPUSpeedString():
	cpu_speed = 0
	try:
		file = open('/proc/cpuinfo', 'r')
		lines = file.readlines()
		file.close()
		for x in lines:
			splitted = x.split(': ')
			if len(splitted) > 1:
				splitted[1] = splitted[1].replace('\n','')
				if splitted[0].startswith("cpu MHz"):
					cpu_speed = float(splitted[1].split(' ')[0])
					break
	except IOError:
		print "[About] getCPUSpeedString, /proc/cpuinfo not available"

	if cpu_speed == 0:
		if getMachineBuild() in ('hd51','hd52','sf4008'):
			import binascii
			f = open('/sys/firmware/devicetree/base/cpus/cpu@0/clock-frequency', 'rb')
			clockfrequency = f.read()
			f.close()
			cpu_speed = round(int(binascii.hexlify(clockfrequency), 16)/1000000,1)
		else:
			try: # Solo4K
				file = open('/sys/devices/system/cpu/cpu0/cpufreq/cpuinfo_max_freq', 'r')
				cpu_speed = float(file.read()) / 1000
				file.close()
			except IOError:
				print "[About] getCPUSpeedString, /sys/devices/system/cpu/cpu0/cpufreq/cpuinfo_max_freq not available"

	if cpu_speed > 0:
		if cpu_speed >= 1000:
			cpu_speed = "%sGHz" % str(round(cpu_speed/1000,1))
		else:
			cpu_speed = "%sMHz" % str(int(cpu_speed))
		return cpu_speed
	return _("unavailable")

def getCPUArch():
	if "ARM" in getCPUString():
		return getCPUString()
	return _("Mipsel")

def getCPUString():
	system = _("unavailable")
	try:
		file = open('/proc/cpuinfo', 'r')
		lines = file.readlines()
		for x in lines:
			splitted = x.split(': ')
			if len(splitted) > 1:
				splitted[1] = splitted[1].replace('\n','')
				if splitted[0].startswith("system type"):
					system = splitted[1].split(' ')[0]
				elif splitted[0].startswith("model name"):
					system = splitted[1].split(' ')[0]
				elif splitted[0].startswith("Processor"):
					system = splitted[1].split(' ')[0]
		file.close()
		return system
	except IOError:
		return _("unavailable")

def getCpuCoresString():
	MachinesCores = {
					1 : 'Single core',
					2 : 'Dual core',
					4 : 'Quad core',
					8 : 'Octo core'
					}
	try:
		cores = 1
		file = open('/proc/cpuinfo', 'r')
		lines = file.readlines()
		file.close()
		for x in lines:
			splitted = x.split(': ')
			if len(splitted) > 1:
				splitted[1] = splitted[1].replace('\n','')
				if splitted[0].startswith("processor"):
					cores = int(splitted[1]) + 1
		return MachinesCores[cores]
	except IOError:
		return _("unavailable")

def _ifinfo(sock, addr, ifname):
	iface = struct.pack('256s', ifname[:15])
	info  = fcntl.ioctl(sock.fileno(), addr, iface)
	if addr == 0x8927:
		return ''.join(['%02x:' % ord(char) for char in info[18:24]])[:-1].upper()
	else:
		return socket.inet_ntoa(info[20:24])

def getIfConfig(ifname):
	ifreq = {'ifname': ifname}
	infos = {}
	sock  = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	# offsets defined in /usr/include/linux/sockios.h on linux 2.6
	infos['addr']    = 0x8915 # SIOCGIFADDR
	infos['brdaddr'] = 0x8919 # SIOCGIFBRDADDR
	infos['hwaddr']  = 0x8927 # SIOCSIFHWADDR
	infos['netmask'] = 0x891b # SIOCGIFNETMASK
	try:
		for k,v in infos.items():
			ifreq[k] = _ifinfo(sock, v, ifname)
	except:
		pass
	sock.close()
	return ifreq

def getIfTransferredData(ifname):
	f = open('/proc/net/dev', 'r')
	for line in f:
		if ifname in line:
			data = line.split('%s:' % ifname)[1].split()
			rx_bytes, tx_bytes = (data[0], data[8])
			f.close()
			return rx_bytes, tx_bytes

def getPythonVersionString():
	import sys
	return "%s.%s.%s" % (sys.version_info.major,sys.version_info.minor,sys.version_info.micro)

# For modules that do "from About import about"
about = modules[__name__]
