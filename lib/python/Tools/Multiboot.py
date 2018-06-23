from Components.SystemInfo import SystemInfo
from Components.Console import Console
from boxbranding import getMachineMtdKernel
import os

MTDKERNEL = getMachineMtdKernel()

def GetCurrentImage():
	print MTDKERNEL[0:7]
	return SystemInfo["HaveMultiBoot"] and (int(open('/sys/firmware/devicetree/base/chosen/bootargs', 'r').read().replace('\0', '').split('%s' %(MTDKERNEL[0:8]))[1].split(' ')[0])-SystemInfo["HaveMultiBoot"][0])/2

def GetCurrentImageMode():
	return SystemInfo["HaveMultiBoot"] and SystemInfo["HaveMultiBootHD"] and int(open('/sys/firmware/devicetree/base/chosen/bootargs', 'r').read().replace('\0', '').split('=')[-1])

class GetImagelist():
	MOUNT = 0
	UNMOUNT = 1


	def __init__(self, callback):
		if SystemInfo["HaveMultiBoot"]:
			(self.firstslot, self.numberofslots) = SystemInfo["HaveMultiBoot"]
			self.callback = callback
			self.imagelist = {}
			if not os.path.isdir('/tmp/testmount'):
				os.mkdir('/tmp/testmount')
			self.container = Console()
			self.slot = 1
			self.phase = self.MOUNT
			self.run()
		else:	
			callback({})
	
	def run(self):
		self.container.ePopen('mount /dev/%s%s /tmp/testmount' %(MTDKERNEL[0:8], str(self.slot * 2 + self.firstslot)) if self.phase == self.MOUNT else 'umount /tmp/testmount', self.appClosed)
			
	def appClosed(self, data, retval, extra_args):
		if retval == 0 and self.phase == self.MOUNT:
			BuildVersion = "  "
			Build = " "
			build = " "
			Creator = " " 
			Date = " "
			Dev = " "
			Type = " "
			if os.path.isfile("/tmp/testmount/usr/bin/enigma2") and os.path.isfile('/tmp/testmount/etc/image-version'):
				file = open('/tmp/testmount/etc/image-version', 'r')
				lines = file.read().splitlines()
				for x in lines:
					splitted = x.split('=')
					if len(splitted) > 1:
						if splitted[0].startswith("Type"):
							Type = splitted[1].split(' ')[1]
						elif splitted[0].startswith("Dev"):
							Dev = splitted[1].split(' ')[1]
						elif splitted[0].startswith("Build"):
							Build = splitted[1].split(' ')[1]
						elif splitted[0].startswith("creator"):
							Creator = splitted[1].split(' ')[0]
						elif splitted[0].startswith("build_type"):
							build = splitted[1].split(' ')[0]
				file.close()
				if Type == "release":		
					BuildVersion = " " + "rel" + " " + Build
				else:
					BuildVersion = " " + "dev" + " " + Build + " " + Dev
			if os.path.isfile('/tmp/testmount/etc/version') and Build == " ":
				version = open("/tmp/testmount/etc/version","r").read()
				Date = "%s-%s-%s" % (version[6:8], version[4:6], version[2:4])
				if Creator == "openATV" and build == "0":
					BuildVersion = " " + "rel" + " " + Date
				else:									
					BuildVersion = "  " + Date
			if os.path.isfile("/tmp/testmount/usr/bin/enigma2"):
				self.imagelist[self.slot] =  { 'imagename': open("/tmp/testmount/etc/issue").readlines()[-2].capitalize().strip()[:-6].replace("-release", " rel") + BuildVersion}
			else:
				self.imagelist[self.slot] = { 'imagename': _("Empty slot")}
			self.phase = self.UNMOUNT
			self.run()
		elif self.slot < self.numberofslots:
			self.slot += 1
			self.imagelist[self.slot] = { 'imagename': _("Empty slot")}
			self.phase = self.MOUNT
			self.run()
		else:
			self.container.killAll()
			if not os.path.ismount('/tmp/testmount'):
				os.rmdir('/tmp/testmount')
			self.callback(self.imagelist)
