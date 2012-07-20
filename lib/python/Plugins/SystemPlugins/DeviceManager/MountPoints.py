import os
import re

class MountPoints():
	def __init__(self):
		self.entries = []
		self.uuids = []
		self.fstab = "/etc/fstab"
		self.blkid = "/sbin/blkid"

	def read(self):
		rows = open(self.fstab, "r").read().strip().split("\n")
		for row in rows:
			self.entries.append({
				"row": row,
				"data": re.split("\s+", row),
				"modified": False
			})

	def write(self):
		conf = open(self.fstab, "w")
		for entry in self.entries:
			if entry["modified"]:
				if len(entry["data"]) != 6:
					print "[DeviceManager] WARNING: fstab entry with not valid data"
					continue
				conf.write("\t".join(entry["data"]) + "\n")
			else:
				conf.write(entry["row"] + "\n")
		conf.close()

	def checkPath(self, path):
		return self.exist(path)

	def isMounted(self, path):
		mounts = open("/proc/mounts")
		for mount in mounts:
			res = mount.split(" ")
			if res and len(res) > 1:
				if res[1] == path:
					mounts.close()
					return True
		mounts.close()
		return False

	def getRealMount(self, device, partition):
		mounts = open("/proc/mounts")
		for mount in mounts:
			res = mount.split(" ")
			if res and len(res) > 1:
				if res[0] == "/dev/%s%i" % (device, partition):
					mounts.close()
					return res[1]
					
		mounts.close()
		return ""

	def umount(self, path):
		return os.system("umount %s" % path) == 0

	def mount(self, device, partition, path):
		return os.system("[ ! -d %s ] && mkdir %s\nmount /dev/%s%d %s" % (path, path, device, partition, path)) == 0

	def exist(self, path):
		for entry in self.entries:
			if (len(entry["data"]) == 6):
				if entry["data"][1] == path:
					return True
		return False

	def delete(self, path):
		for entry in self.entries:
			if (len(entry["data"]) == 6):
				if entry["data"][1] == path:
					self.entries.remove(entry)

	def deleteDisk(self, device):
		for i in range(1,4):
			res = self.get(device, i)
			if len(res) > 0:
				self.delete(res)

	def add(self, device, partition, path):
		uuid = self.getUUID(device, partition)
		for entry in self.entries:
			if (len(entry["data"]) == 6):
				if entry["data"][0] == "/dev/%s%i" % (device, partition):
					self.entries.remove(entry)
				elif entry["data"][0] == "UUID=" + uuid:
					self.entries.remove(entry)
				elif entry["data"][1] == path:
					self.entries.remove(entry)

		self.entries.append({
			"row": "",
			"data": ["UUID=" + uuid, path, "auto", "defaults", "1", "1"],
			"modified": True
		})

	def getUUID(self, device, partition):
		for uuid in self.uuids:
			if uuid["device"] == device and uuid["partition"] == partition:
				return uuid["uuid"]

		rows = os.popen(self.blkid).read().strip().split("\n")
		for row in rows:
			tmp = row.split(":")
			if len(tmp) < 2:
				continue

			if tmp[0] == "/dev/%s%i" % (device, partition):
				tmp.reverse()
				key = tmp.pop()
				tmp.reverse()
				value = ":".join(tmp)
				uuid = "00000000"
				ret = re.search('UUID=\"([\w\-]+)\"', value)
				if ret:
					uuid = ret.group(1)
				self.uuids.append({
					"device": device,
					"partition": partition,
					"uuid": uuid
				})
				return uuid

		return "00000000"

	def get(self, device, partition):
		uuid = self.getUUID(device, partition)
		for entry in self.entries:
			if (len(entry["data"]) == 6):
				if entry["data"][0] == "/dev/%s%i" % (device, partition):
					return entry["data"][1]
				elif entry["data"][0] == "UUID=" + uuid:
					return entry["data"][1]
		return ""