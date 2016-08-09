##
## Picon renderer by Gruffy .. some speedups by Ghost
##
from Tools.Directories import fileExists
from Tools.Alternatives import GetWithAlternative
from Components.config import config
from enigma import eServiceCenter, eServiceReference

searchPaths = ('/usr/share/enigma2/%s/', '/media/usb/%s/')
path = "picon"
nameCache = { }
pngname = ""

def findFile(serviceName):
	path = "picon"
	piconsize = int(config.usage.servicelist_show_picon.value)
	if path == "picon":
		normal_path = config.usage.servicelist_picon_dir.value + "/"
		opt_path = None
		if piconsize == 50:
			opt_path = config.usage.servicelist_picon_dir.value + "_50x30/"
		elif piconsize == 100:
			opt_path = config.usage.servicelist_picon_dir.value + "_100x60/"
		for path in (opt_path, normal_path):
			if path and serviceName:
				pngname = path + serviceName + ".png"
				if fileExists(pngname):
					return pngname
	for searchpath in searchPaths:
		piconpath = path
		if piconsize == 50:
			piconpath = path + "_50x30"
		elif piconsize == 100:
			piconpath = path + "_100x60"
		if piconsize > 0:
			pngname = (searchpath % piconpath) + serviceName + ".png"
			if fileExists(pngname):
				return pngname
		pngname = (searchpath % path) + serviceName + ".png"
		if fileExists(pngname):
			return pngname
	return ""

def findPicon(service):
	pngname = ""
	sname = service
	s_name = sname
	if sname.startswith("1:134"):
		sname = GetWithAlternative(service)
	for protocol in ("http", "rtmp", "rtsp", "mms", "rtp"):
		pos = sname.rfind(':' + protocol )
		if pos != -1:
			sname = sname.split(protocol)[0]
			break
	pos = sname.rfind(':')
	if pos != -1:
		sname = sname[:pos].rstrip(':').replace(':','_')
	pngname = nameCache.get(sname, "")
	if pngname == "":
		pngname = findFile(sname)
		if pngname == "":
			serviceHandler = eServiceCenter.getInstance()
			service = eServiceReference(s_name)
			if service and service is not None:
				info = serviceHandler.info(service)
				if info and info is not None:
					service_name = info.getName(service).replace('\xc2\x86','').replace('\xc2\x87', '').replace('/', '_')
					print service_name
					pngname = findFile(service_name)
		if pngname == "" and sname.startswith("4097_"):
			pngname = findFile(sname.replace("4097_", "1_", 1))
		if pngname != "":
			nameCache[sname] = pngname
	return pngname
