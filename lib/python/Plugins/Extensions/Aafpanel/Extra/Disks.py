import os
import re

class Disks():
	def __init__(self):
		self.disks = []
		self.readDisks()
		self.readPartitions()
		
	def readDisks(self):
		partitions = open('/proc/partitions', 'r')
		for part in partitions:
			res = re.sub("\s+", " ", part).strip().split(" ")
			if res and len(res) == 4:
				if len(res[3]) == 3 and res[3][:2] == "sd":
					self.disks.append([ res[3],
										int(res[2]) * 1024,
										self.isRemovable(res[3]),
										self.getModel(res[3]),
										self.getVendor(res[3]),
										[ ] ])
		
	def readPartitions(self):
		partitions = open('/proc/partitions', 'r')
		for part in partitions:
			res = re.sub("\s+", " ", part).strip().split(" ")
			if res and len(res) == 4:
				if len(res[3]) > 3 and res[3][:2] == "sd":
					for i in self.disks:
						if i[0] == res[3][:3]:
							i[5].append([ res[3], int(res[2]) * 1024, self.isLinux(res[3]) ])
							break
							
	def isRemovable(self, device):
		removable = open("/sys/block/%s/removable" % device, "r").read().strip()
		if removable == "1":
			return True
		return False
		
	# in this case device is full device with slice number... for example sda1
	def isLinux(self, device):
		cmd = "/sbin/fdisk -l | grep \"/dev/%s\" | sed s/\*// | awk '{ print $6 \" \" $7 \" \" $8 }'" % device
		fdisk = os.popen(cmd, "r")
		res = fdisk.read().strip()
		fdisk.close()
		return res
		
	def getModel(self, device):
		return open("/sys/block/%s/device/model" % device, "r").read().strip()
		
	def getVendor(self, device):
		return open("/sys/block/%s/device/vendor" % device, "r").read().strip()
		
	def isMounted(self, device):
		mounts = open("/proc/mounts")
		for mount in mounts:
			res = mount.split(" ")
			if res and len(res) > 1:
				if res[0][:8] == "/dev/%s" % device:
					mounts.close()
					return True
		mounts.close()
		return False
		
	def isMountedP(self, device, partition):
		mounts = open("/proc/mounts")
		for mount in mounts:
			res = mount.split(" ")
			if res and len(res) > 1:
				if res[0][:9] == "/dev/%s%s" % (device, partition):
					mounts.close()
					return True
		mounts.close()
		return False
	
	def getMountedP(self, device, partition):
		mounts = open("/proc/mounts")
		for mount in mounts:
			res = mount.split(" ")
			if res and len(res) > 1:
				if res[0] == "/dev/%s%d" % (device, partition):
					mounts.close()
					return res[1]
		mounts.close()
		return None
		
	def umount(self, device):
		mounts = open("/proc/mounts")
		for mount in mounts:
			res = mount.split(" ")
			if res and len(res) > 1:
				if res[0][:8] == "/dev/%s" % device:
					print "umount %s" % res[0]
					if os.system("umount %s" % res[0]) != 0:
						mounts.close()
						return False
		mounts.close()
		return True
		
	def umountP(self, device, partition):
		if os.system("umount /dev/%s%d" % (device, partition)) != 0:
			return False
			
		return True
			
	def mountP(self, device, partition, path):
		if os.system("mount /dev/%s%d %s" % (device, partition, path)) != 0:
			return False
		return True
		
	def mount(self, fdevice, path):
		if os.system("mount /dev/%s %s" % (fdevice, path)) != 0:
			return False
		return True
		
	# type:
	# 0 -> one partition
	# 1 -> two partition (2 x 50%)
	# 2 -> two partition (75% 25%)
	# 3 -> three partition (3 x 33%)
	# 4 -> four partition (4 x 25%)
	#
	# return value:
	# 0 -> ok
	# -1 -> umount failed
	# -2 -> sfdisk failed
	def fdisk(self, device, size, type):
		print "partitioning device %s" % device
		if self.isMounted(device):
			print "device is mounted... umount"
			if not self.umount(device):
				print "umount failed!"
				return -1
			
		if type == 0:
			flow = "0,\n;\n;\n;\ny\n"
		elif type == 1:
			psize = (size / (1024*1024)) / 2
			flow = ",%d\n;\n;\n;\ny\n" % psize
		elif type == 2:
			psize = ((size / (1024*1024)) / 4) * 3
			flow = ",%d\n;\n;\n;\ny\n" % psize
		elif type == 3:
			psize = (size / (1024*1024)) / 3
			flow = ",%d\n,%d\n;\n;\ny\n" % (psize, psize)
		elif type == 4:
			psize = (size / (1024*1024)) / 4
			flow = ",%d\n,%d\n,%d\n;\ny\n" % (psize, psize, psize)
		
		cmd = "%s -f -uM /dev/%s" % ("/usr/sbin/sfdisk", device)
		sfdisk = os.popen(cmd, "w")
		sfdisk.write(flow)
		if sfdisk.close():
			return -2
			
		return 0
		
	# return value:
	# 0 -> ok
	# -1 -> umount failed
	# -2 -> sfdisk failed
	def chkfs(self, device, partition):
		fdevice = "%s%d" % (device, partition)
		print "checking device %s" % fdevice
		if self.isMountedP(device, partition):
			oldmp = self.getMountedP(device, partition)
			print "partition is mounted... umount"
			if not self.umountP(device, partition):
				print "umount failed!"
				return -1
		else:
			oldmp = ""

		if self.isMountedP(device, partition):
				return -1
			
		ret = os.system("/sbin/fsck /dev/%s" % fdevice)
		
		if len(oldmp) > 0:
			self.mount(fdevice, oldmp)
			
		if ret == 0:
			return 0
		return -2;
		
	def mkfs(self, device, partition):
		dev = "%s%d" % (device, partition)
		size = 0
		partitions = open("/proc/partitions")
		for part in partitions:
			res = re.sub("\s+", " ", part).strip().split(" ")
			if res and len(res) == 4:
				if res[3] == dev:
					size = int(res[2])
					break
					
		if size == 0:
			return -1
			
		if self.isMountedP(device, partition):
			oldmp = self.getMountedP(device, partition)
			print "partition is mounted... umount"
			if not self.umountP(device, partition):
				print "umount failed!"
				return -2
		else:
			oldmp = ""
		
		filesystem = open("/proc/filesystems")
		for fsys in filesystem:
			if fsys.strip() == "ext4":
				cmd = "/sbin/mkfs.ext4 "
				break
			else:
				cmd = "/sbin/mkfs.ext3 "
			
		if size > 4 * 1024 * 1024 * 1024:
			cmd += "-T largefile "
		cmd += "-m0 -O dir_index /dev/" + dev
		ret = os.system(cmd)
		print "return mkfs:",ret
		
		if len(oldmp) > 0:
			self.mount(dev, oldmp)
			
		if ret == 0:
			return 0
		return -3;
		