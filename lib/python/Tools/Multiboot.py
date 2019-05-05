from Components.SystemInfo import SystemInfo
from Components.Console import Console
from boxbranding import getMachineMtdRoot,getMachineMtdKernel,getBoxType,getMachineName
from Tools.Directories import pathExists
import os, time
import shutil
import subprocess

def GetCurrentImage():
	if SystemInfo["canMultiBoot"]:
		if SystemInfo["HasRootSubdir"]:
			return SystemInfo["HasRootSubdir"] and (int(open('/sys/firmware/devicetree/base/chosen/bootargs', 'r').read()[:-1].split("rootsubdir=linuxrootfs")[1].split(' ')[0]))
		else:
			f = open('/sys/firmware/devicetree/base/chosen/bootargs', 'r').read()
			if "%s" %(SystemInfo["canMultiBoot"][2]) in f:
				return SystemInfo["canMultiBoot"] and (int(open('/sys/firmware/devicetree/base/chosen/bootargs', 'r').read()[:-1].split("%s" % SystemInfo["canMultiBoot"][2])[1].split(' ')[0])-SystemInfo["canMultiBoot"][0])/2
			else:
				return 0	# if media not in SystemInfo["canMultiBoot"], then using SDcard and Image is in eMMC (1st slot) so tell caller with 0 return

def GetCurrentKern():
	if SystemInfo["HasRootSubdir"]:
		return SystemInfo["HasRootSubdir"] and (int(open('/sys/firmware/devicetree/base/chosen/bootargs', 'r').read()[:-1].split("kernel=/dev/mmcblk0p")[1].split(' ')[0]))
	return getMachineMtdKernel()

def GetCurrentRoot():
	if SystemInfo["HasRootSubdir"]:
		return SystemInfo["HasRootSubdir"] and (int(open('/sys/firmware/devicetree/base/chosen/bootargs', 'r').read()[:-1].split("root=/dev/mmcblk0p")[1].split(' ')[0]))
	return getMachineMtdRoot()

def GetCurrentImageMode():
	return SystemInfo["canMultiBoot"] and SystemInfo["canMode12"] and int(open('/sys/firmware/devicetree/base/chosen/bootargs', 'r').read().replace('\0', '').split('=')[-1])

def GetSTARTUPFile():
	if SystemInfo["HAScmdline"]:
		return "cmdline.txt"
	else:
		return "STARTUP"

def ReadSTARTUP():
	return SystemInfo["canMultiBoot"] and open('/tmp/startupmount/%s' %GetSTARTUPFile(), 'r').read()

def GetBoxName():
	box = getBoxType()
	machinename = getMachineName()
	if box in ('uniboxhd1', 'uniboxhd2', 'uniboxhd3'):
		box = "ventonhdx"
	elif box == 'odinm6':
		box = getMachineName().lower()
	elif box == "inihde" and machinename.lower() == "xpeedlx":
		box = "xpeedlx"
	elif box in ('xpeedlx1', 'xpeedlx2'):
		box = "xpeedlx"
	elif box == "inihde" and machinename.lower() == "hd-1000":
		box = "sezam-1000hd"
	elif box == "ventonhdx" and machinename.lower() == "hd-5000":
		box = "sezam-5000hd"
	elif box == "ventonhdx" and machinename.lower() == "premium twin":
		box = "miraclebox-twin"
	elif box == "xp1000" and machinename.lower() == "sf8 hd":
		box = "sf8"
	elif box.startswith('et') and not box in ('et8000', 'et8500', 'et8500s', 'et10000'):
		box = box[0:3] + 'x00'
	elif box == 'odinm9':
		box = 'maram9'
	elif box.startswith('sf8008'):
		box = "sf8008"
	return box

class GetImagelist():
	MOUNT = 0
	UNMOUNT = 1
	NoRun = 0		# receivers only uses 1 media for multiboot
	FirstRun = 1		# receiver uses eMMC and SD card for multiboot - so handle SDcard slots 1st via SystemInfo(canMultiBoot)
	LastRun = 2		# receiver uses eMMC and SD card for multiboot - and then handle eMMC (currently one time)

	def __init__(self, callback):
		if SystemInfo["canMultiBoot"]:
			(self.firstslot, self.numberofslots) = SystemInfo["canMultiBoot"][:2]
			if SystemInfo["HasSDmmc"]:
				self.numberofslots -= 1
			self.callback = callback
			self.imagelist = {}
			if not os.path.isdir('/tmp/testmount'):
				os.mkdir('/tmp/testmount')
			self.container = Console()
			self.slot = 1
			self.slot2 = 1
			if SystemInfo["HasSDmmc"]:
				self.SDmmc = self.FirstRun	# process SDcard slots
			else:
				self.SDmmc = self.NoRun		# only mmc slots
			self.phase = self.MOUNT
			self.part = SystemInfo["canMultiBoot"][2]	# pick up slot type
			self.run()
		else:
			callback({})

	def run(self):
		if SystemInfo["HasRootSubdir"]:
			if self.slot == 1 and os.path.islink("/dev/block/by-name/linuxrootfs"):
				self.part2 = os.readlink("/dev/block/by-name/linuxrootfs")[5:]
				self.container.ePopen('mount /dev/block/by-name/linuxrootfs /tmp/testmount' if self.phase == self.MOUNT else 'umount /tmp/testmount', self.appClosed)
			else:
				self.part2 = os.readlink("/dev/block/by-name/userdata")[5:]
				self.container.ePopen('mount /dev/block/by-name/userdata /tmp/testmount' if self.phase == self.MOUNT else 'umount /tmp/testmount', self.appClosed)
			if self.phase == self.MOUNT:
				self.imagelist[self.slot2] = { 'imagename': _("Empty slot"), 'part': '%s' %self.part2 }
		else:
			if self.SDmmc == self.LastRun:
				self.part2 = getMachineMtdRoot()	# process mmc slot
				self.slot2 = 1
			else:
				self.part2 = "%s" %(self.part + str(self.slot * 2 + self.firstslot))
				if self.SDmmc == self.FirstRun:
					self.slot2 += 1			# allow for mmc slot"
			if self.phase == self.MOUNT:
				self.imagelist[self.slot2] = { 'imagename': _("Empty slot"), 'part': '%s' %self.part2 }
			self.container.ePopen('mount /dev/%s /tmp/testmount' %self.part2 if self.phase == self.MOUNT else 'umount /tmp/testmount', self.appClosed)

	def appClosed(self, data, retval, extra_args):
		if retval == 0 and self.phase == self.MOUNT:
			BuildVersion = "  "	
			Build = " "	#ViX Build No.#
			Dev = " "	#ViX Dev No.#
			Creator = " " 	#Openpli Openvix Openatv etc #
			Date = " "	
			BuildType = " "	#release etc #
			self.OsPath = "NoPath"
			if SystemInfo["HasRootSubdir"]:
				if self.slot == 1 and os.path.isfile("/tmp/testmount/linuxrootfs1/usr/bin/enigma2"):
					self.OsPath = "/tmp/testmount/linuxrootfs1"
				elif os.path.isfile("/tmp/testmount/linuxrootfs%s/usr/bin/enigma2" % self.slot):
					self.OsPath = "/tmp/testmount/linuxrootfs%s" % self.slot
					print "multiboot tools 1 slots", self.slot, self.slot2
			else:
				if os.path.isfile("/tmp/testmount/usr/bin/enigma2"):
					self.OsPath = '/tmp/testmount'
			print "Tools/Multiboot OsPath %s " %self.OsPath
			if self.OsPath != "NoPath":
				try:
					Creator = open("%s/etc/issue" %self.OsPath).readlines()[-2].capitalize().strip()[:-6].replace("-release", " rel")
				except:
					Creator = _("unknow")
				print "Tools/Multiboot Creator %s" %Creator 
				if Creator.startswith("Openpli"):
					build = [x.split("-")[-2:-1][0][-8:] for x in open("%s/var/lib/opkg/info/openpli-bootlogo.control" %self.OsPath).readlines() if x.startswith("Version:")]
					Date = "%s-%s-%s" % (build[0][6:], build[0][4:6], build[0][2:4])
					BuildVersion = "%s %s" % (Creator, Date)
				elif Creator.startswith("Openvix"):
					reader = boxbranding_reader(self.OsPath)
					BuildType = reader.getImageType()
					Build = reader.getImageBuild()
					Dev = BuildType != "release" and " %s" % reader.getImageDevBuild() or ''
					BuildVersion = "%s %s %s %s" % (Creator, BuildType[0:3], Build, Dev)
				else:
					st = os.stat('%s/var/lib/opkg/status' %self.OsPath)
					tm = time.localtime(st.st_mtime)
					if tm.tm_year >= 2011:
						Date = time.strftime("%d-%m-%Y", tm).replace("-20", "-")
					BuildVersion = "%s rel %s" % (Creator, Date)
				self.imagelist[self.slot2] =  { 'imagename': '%s' %BuildVersion, 'part': '%s' %self.part2 }
			self.phase = self.UNMOUNT
			self.run()
		elif self.slot < self.numberofslots:
			self.slot += 1
			self.slot2 = self.slot
			self.phase = self.MOUNT
			self.run()
		elif self.SDmmc == self.FirstRun:
			self.phase = self.MOUNT
			self.SDmmc = self.LastRun	# processed SDcard now process mmc slot
			self.run()
		else:
			self.container.killAll()
			if not os.path.ismount('/tmp/testmount'):
				os.rmdir('/tmp/testmount')
			self.callback(self.imagelist)


class boxbranding_reader:		# many thanks to Huevos for creating this reader - well beyond my skill levels! 
	def __init__(self, OsPath):
		if pathExists('%s/usr/lib64' %OsPath):
			self.branding_path = "%s/usr/lib64/enigma2/python/" %OsPath
		else:
			self.branding_path = "%s/usr/lib/enigma2/python/" %OsPath
		self.branding_file = "boxbranding.so"
		self.tmp_path = "/tmp/"
		self.helper_file = "helper.py"

		self.output = {
			"getMachineBuild": "",
			"getMachineProcModel": "",
			"getMachineBrand": "",
			"getMachineName": "",
			"getMachineMtdKernel": "",
			"getMachineKernelFile": "",
			"getMachineMtdRoot": "",
			"getMachineRootFile": "",
			"getMachineMKUBIFS": "",
			"getMachineUBINIZE": "",
			"getBoxType": "",
			"getBrandOEM": "",
			"getOEVersion": "",
			"getDriverDate": "",
			"getImageVersion": "",
			"getImageBuild": "",
			"getImageDistro": "",
			"getImageFolder": "",
			"getImageFileSystem": "",
			"getImageDevBuild": "",
			"getImageType": "",
			"getMachineMake": "",
			"getImageArch": "",
			"getFeedsUrl": "",
		}
		self.createHelperFile()
		self.copyBrandingFile()
		self.readBrandingFile()
		self.removeHelperFile()
		self.removeBrandingFile()
		self.addBrandingMethods()

	def readBrandingFile(self): # reads boxbranding.so and updates self.output
		output = eval(subprocess.check_output(['python', self.tmp_path + self.helper_file]))
		if output:
			for att in self.output.keys():
				self.output[att] = output[att]

	def addBrandingMethods(self): # this creates reader.getBoxType(), reader.getImageDevBuild(), etc
		l =  {}                
		for att in self.output.keys():
			exec("def %s(self): return self.output['%s']" % (att, att), None, l)
		for name, value in l.items():
			setattr(boxbranding_reader, name, value)

	def createHelperFile(self):
		f = open(self.tmp_path + self.helper_file, "w+")
		f.write(self.helperFileContent())
		f.close()

	def copyBrandingFile(self):
		shutil.copy2(self.branding_path + self.branding_file, self.tmp_path + self.branding_file)

	def removeHelperFile(self):
		self.removeFile(self.tmp_path + self.helper_file)

	def removeBrandingFile(self):
		self.removeFile(self.tmp_path + self.branding_file)

	def removeFile(self, toRemove):
			if os.path.isfile(toRemove):
				os.remove(toRemove)

	def helperFileContent(self):
		eol = "\n"
		out = []
		out.append("try:%s" % eol)
		out.append("\timport boxbranding%s" % eol)
		out.append("\toutput = {%s" % eol)
		for att in self.output.keys():
			out.append('\t\t"%s": boxbranding.%s(),%s' % (att, att, eol))
		out.append("\t}%s" % eol)
		out.append("except:%s" % eol)
		out.append("\t\toutput = None%s" % eol)
		out.append("print output%s" % eol)
		return ''.join(out)


class EmptySlot():
	MOUNT = 0
	UNMOUNT = 1
	def __init__(self, Contents, callback):
		self.callback = callback
		self.container = Console()
		(self.firstslot, self.numberofslots, self.mtdboot) = SystemInfo["canMultiBoot"]
		if SystemInfo["HasSDmmc"]:
			self.numberofslots -= 1
		self.slot = Contents
		if not os.path.isdir('/tmp/testmount'):
			os.mkdir('/tmp/testmount')
		if SystemInfo["HasRootSubdir"]:
			self.part = "%s%s" %(self.mtdboot, GetCurrentRoot())
		else:
			if SystemInfo["HasSDmmc"]:			# allow for mmc & SDcard in passed slot number, so SDcard slot -1
				self.slot -= 1
			self.part = "%s%s" %(self.mtdboot, str(self.slot * 2 + self.firstslot))
			if SystemInfo["HasSDmmc"] and self.slot == 0:	# this is the mmc slot, so pick up from MtdRoot
				self.part = getMachineMtdRoot()
		self.phase = self.MOUNT
		self.run()

	def run(self):
		if SystemInfo["HasRootSubdir"]:
			if self.slot == 1 and os.path.islink("/dev/block/by-name/linuxrootfs"):
				self.container.ePopen('mount /dev/block/by-name/linuxrootfs /tmp/testmount' if self.phase == self.MOUNT else 'umount /tmp/testmount', self.appClosed)
			else:
				self.container.ePopen('mount /dev/block/by-name/userdata /tmp/testmount' if self.phase == self.MOUNT else 'umount /tmp/testmount', self.appClosed)
		else:
			self.container.ePopen('mount /dev/%s /tmp/testmount' %self.part if self.phase == self.MOUNT else 'umount /tmp/testmount', self.appClosed)

	
	def appClosed(self, data, retval, extra_args):
		if retval == 0 and self.phase == self.MOUNT:
			if SystemInfo["HasRootSubdir"]:
				if os.path.isfile("/tmp/testmount/linuxrootfs%s/usr/bin/enigma2" %self.slot):
					os.rename('/tmp/testmount/linuxrootfs%s/usr/bin/enigma2' %self.slot, '/tmp/testmount/linuxrootfs%s/usr/bin/enigmax.bin' %self.slot)
			else:
				if os.path.isfile("/tmp/testmount/usr/bin/enigma2"):
					os.rename('/tmp/testmount/usr/bin/enigma2', '/tmp/testmount/usr/bin/enigmax.bin')
			self.phase = self.UNMOUNT
			self.run()
		else:
			self.container.killAll()
			if not os.path.ismount('/tmp/testmount'):
				os.rmdir('/tmp/testmount')
			self.callback()
