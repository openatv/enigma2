from glob import glob
from json import dumps, loads
from os import O_CREAT, O_EXCL, O_NOFOLLOW, O_RDONLY, O_WRONLY, close, fchmod, fchown, fdopen, fstat, fsync, lstat, open as osOpen, replace, stat, statvfs, unlink
from os.path import basename, dirname, exists, isabs, join, realpath
from re import sub
from stat import S_ISBLK, S_ISREG
from tempfile import mkstemp
from twisted.internet.threads import deferToThread

from Components.config import ConfigText, ConfigYesNo, config, configfile
from Components.Console import Console
from Components.Harddisk import getProcMounts, harddiskmanager
from Tools.Directories import fileReadLines

config.usage.swapautostart = ConfigYesNo(default=False)
config.usage.swapfiles = ConfigText(default="[]", fixed_size=False)


class SwapManager:
	CREATE_FILESYSTEMS = ("ext2", "ext3", "ext4")
	LOCAL_FILESYSTEMS = ("ext2", "ext3", "ext4", "xfs", "btrfs", "f2fs", "jfs", "reiserfs", "ubifs", "jffs2", "overlay", "vfat", "ntfs", "ntfs3", "fuseblk")

	def __init__(self):
		self.console = Console(binary=True)
		self.busy = False

	def decodePath(self, path):
		return sub(r"\\([0-7]{3})", lambda match: chr(int(match[1], 8)), path)

	def readActive(self):
		entries = {}
		for line in fileReadLines("/proc/swaps", default=[])[1:]:
			parts = line.split()
			if len(parts) == 5:
				try:
					path = realpath(self.decodePath(parts[0]))
					entries[path] = {"path": path, "type": parts[1], "size": int(parts[2]) * 1024, "used": int(parts[3]) * 1024, "priority": int(parts[4])}
				except ValueError:
					print(f"[SwapManager] Invalid /proc/swaps entry: {line}")
		return entries

	def registeredFiles(self):
		try:
			paths = loads(config.usage.swapfiles.value)
			return [x for x in paths if isinstance(x, str) and isabs(x)] if isinstance(paths, list) else []
		except ValueError:
			return []

	def rememberFile(self, path, remove=False):
		paths = set(self.registeredFiles())
		if remove:
			paths.discard(path)
		else:
			paths.add(path)
		config.usage.swapfiles.value = dumps(sorted(paths))
		config.usage.swapfiles.save()
		configfile.save()

	def fileInfo(self, path):
		# Never read a device while looking for swap files.
		info = lstat(path)
		if not S_ISREG(info.st_mode):
			raise ValueError(_("This is not a regular swap file."))
		with fdopen(osOpen(path, O_RDONLY | O_NOFOLLOW), "rb") as source:
			if (info.st_dev, info.st_ino) != (fstat(source.fileno()).st_dev, fstat(source.fileno()).st_ino):
				raise ValueError(_("The swap file has changed. Refresh the list and try again."))
			header = source.read(65536)
		if not any(header[x - 10:x] in (b"SWAPSPACE2", b"SWAP-SPACE") for x in (4096, 8192, 16384, 32768, 65536)):
			raise ValueError(_("The file does not contain a valid swap header."))
		return info

	def localMount(self, path, mounts=None):
		mounts = getProcMounts() if mounts is None else mounts
		matching = [x for x in mounts if len(x) >= 4 and (path == x[1] or path.startswith(x[1].rstrip("/") + "/"))]
		mount = max(matching, key=lambda item: len(item[1])) if matching else None
		return mount if mount and mount[2] in self.LOCAL_FILESYSTEMS else None

	def getLocations(self):
		locations = []
		seen = set()
		mounts = getProcMounts()
		names = {realpath(x.mountpoint): x.description for x in harddiskmanager.getMountedPartitions(mounts=mounts)}
		for mount in mounts:
			if len(mount) < 4 or mount[2] not in self.CREATE_FILESYSTEMS or "ro" in mount[3].split(","):
				continue
			try:
				path = realpath(mount[1])
				device = stat(path).st_dev
				if device not in seen:
					space = statvfs(path)
					source = realpath(mount[0]) if isabs(mount[0]) else mount[0]
					name = _("Internal flash") if path == "/" else names.get(path, basename(source))
					locations.append({"path": path, "device": device, "source": source, "name": name, "free": space.f_bavail * space.f_frsize})
					seen.add(device)
			except OSError as error:
				print(f"[SwapManager] Storage {mount[1]}: {error}")
		return sorted(locations, key=lambda item: (item["path"] == "/", item["path"]))

	def scan(self, callback):
		registered = self.registeredFiles()

		def scanFinished(result, retVal, extraArgs):
			error = "" if retVal in (0, 2) else _("Swap partition detection failed. Active and configured swaps are still listed.")
			deferred = deferToThread(self.collectEntries, result.decode("UTF-8", "replace"), registered)
			deferred.addCallback(lambda entries: callback(entries, error))
			deferred.addErrback(lambda failure: callback([], str(failure.value)))

		self.console.ePopen(("/sbin/blkid", "/sbin/blkid", "-c", "/dev/null", "-t", "TYPE=swap", "-o", "export"), scanFinished)

	def collectEntries(self, result, registered):
		devices = {}
		aliases = {}
		for block in result.split("\n\n"):
			data = dict(x.split("=", 1) for x in block.splitlines() if "=" in x)
			if data.get("TYPE") == "swap" and data.get("DEVNAME", "").startswith("/dev/"):
				path = realpath(data["DEVNAME"])
				devices[path] = {"type": "partition"}
				for key in ("UUID", "LABEL", "PARTUUID", "PARTLABEL"):
					if key in data:
						aliases[f"{key}={data[key]}"] = path
		mounts = getProcMounts()
		for line in fileReadLines("/etc/fstab", default=[]):
			parts = line.split()
			if not line.lstrip().startswith("#") and len(parts) >= 4 and parts[2] == "swap":
				spec = self.decodePath(parts[0])
				path = aliases.get(spec, spec)
				if "=" in path and not isabs(path):
					kind, value = path.split("=", 1)
					if kind in ("UUID", "LABEL", "PARTUUID", "PARTLABEL"):
						link = join("/dev/disk", f"by-{kind.lower()}", value)
						if exists(link):
							path = link
				if isabs(path):
					path = realpath(path)
				entry = devices.setdefault(path, {"type": "partition" if path.startswith("/dev/") or not isabs(path) else "file"})
				entry.update(fstab=True, noauto="noauto" in parts[3].split(","))
		candidates = set(registered)
		for mount in mounts:
			if len(mount) >= 3 and mount[2] in self.LOCAL_FILESYSTEMS:
				for pattern in ("swap*", "*.swap", ".swap/swap*"):
					candidates.update(glob(join(mount[1], pattern)))
		candidates.add("/.FlashExpander/swapfile")
		for path in candidates:
			if path in registered:
				devices.setdefault(path, {"type": "file"})
			if isabs(path) and self.localMount(path, mounts):
				try:
					self.fileInfo(path)
					devices.setdefault(realpath(path), {"type": "file"})
				except (OSError, ValueError):
					pass
		active = self.readActive()
		for path, data in active.items():
			devices.setdefault(path, {}).update(data)
		entries = []
		for path, data in sorted(devices.items()):
			entry = {"path": path, "size": 0, "used": 0, "priority": 0, "active": path in active, "available": False, "fstab": False, "noauto": False, "identity": None}
			entry.update(data)
			try:
				if entry["type"] == "file":
					if not self.localMount(path, mounts):
						raise ValueError("Swap file is not on local storage")
					info = self.fileInfo(path)
					if not entry["active"]:
						entry["size"] = info.st_size
				else:
					info = stat(path)
					if not S_ISBLK(info.st_mode):
						raise ValueError("Not a block device")
					if not entry["active"]:
						with open(join("/sys/class/block", basename(path), "size")) as source:
							entry["size"] = int(source.read().strip()) * 512
				entry["available"] = True
				entry["identity"] = (info.st_dev, info.st_ino, info.st_rdev)
			except (OSError, ValueError) as error:
				print(f"[SwapManager] Unavailable {path}: {error}")
			entries.append(entry)
		return entries

	def addFile(self, path):
		if not isabs(path):
			raise ValueError(_("Select a swap file on local storage."))
		path = realpath(path)
		if not self.localMount(path):
			raise ValueError(_("Select a swap file on local storage."))
		self.fileInfo(path)
		self.rememberFile(realpath(path))

	def checkIdentity(self, entry):
		info = lstat(entry["path"])
		if (info.st_dev, info.st_ino, info.st_rdev) != entry["identity"]:
			raise ValueError(_("The swap device has changed. Refresh the list and try again."))
		if entry["type"] == "file" and not S_ISREG(info.st_mode):
			raise ValueError(_("This is not a regular swap file."))

	def setActive(self, entry, active, callback):
		if self.busy:
			callback(_("Another swap operation is still running."))
			return
		try:
			self.checkIdentity(entry)
			if entry["type"] == "file":
				self.rememberFile(entry["path"])
		except (OSError, ValueError) as error:
			callback(str(error))
			return
		self.busy = True
		command = "/sbin/swapon" if active else "/sbin/swapoff"

		def finished(result, retVal, extraArgs):
			self.busy = False
			actual = entry["path"] in self.readActive()
			callback("" if actual == active else _("Unable to change swap state for '%s'.\n%s") % (entry["path"], result.decode("UTF-8", "replace").strip()))

		if (entry["path"] in self.readActive()) == active:
			finished(b"", 0, None)
		else:
			self.console.ePopen((command, command, entry["path"]), finished)

	def delete(self, entry, callback):
		if entry["type"] != "file":
			callback(_("Only swap files can be deleted."))
			return

		def stopped(error):
			if not error:
				try:
					self.checkIdentity(entry)
					if entry["path"] in self.readActive():
						raise ValueError(_("The swap file is still active and cannot be deleted."))
					self.removeFstabEntry(entry["path"])
					unlink(entry["path"])
					self.rememberFile(entry["path"], remove=True)
				except (OSError, ValueError) as failure:
					error = str(failure)
			callback(error)

		self.setActive(entry, False, stopped)

	def removeFstabEntry(self, path):
		fstab = realpath("/etc/fstab")
		with open(fstab) as source:
			lines = source.readlines()
		filtered = []
		for line in lines:
			parts = line.split()
			if line.lstrip().startswith("#") or len(parts) < 3 or parts[2] != "swap" or realpath(self.decodePath(parts[0])) != path:
				filtered.append(line)
		if filtered != lines:
			# Replace atomically and retain permissions; unrelated entries stay intact.
			info = stat(fstab)
			fd, temporary = mkstemp(prefix=".fstab-swap-", dir=dirname(fstab))
			try:
				with fdopen(fd, "w") as target:
					fchown(target.fileno(), info.st_uid, info.st_gid)
					fchmod(target.fileno(), info.st_mode & 0o7777)
					target.writelines(filtered)
					target.flush()
					fsync(target.fileno())
				replace(temporary, fstab)
			finally:
				if exists(temporary):
					unlink(temporary)

	def create(self, location, size, callback):
		if self.busy:
			callback(_("Another swap operation is still running."))
			return
		try:
			if size not in (32, 64, 128, 256, 512, 1024, 1536, 2048, 4096, 8192):
				raise ValueError(_("Invalid swap file size."))
			path = location["path"]
			mount = self.localMount(path)
			if not mount or mount[1] != path or mount[2] not in self.CREATE_FILESYSTEMS or "ro" in mount[3].split(",") or stat(path).st_dev != location["device"]:
				raise ValueError(_("The selected storage device is no longer available."))
			space = statvfs(path)
			if space.f_bavail * space.f_frsize < (size + 16) * 1024 * 1024:
				raise ValueError(_("Not enough free space for this swap file."))
			for index in range(1000):
				fileName = join(path, "swapfile" if not index else f"swapfile{index}")
				try:
					fd = osOpen(fileName, O_WRONLY | O_CREAT | O_EXCL, 0o600)
					break
				except FileExistsError:
					continue
			else:
				raise ValueError(_("No unused swap file name is available."))
			info = fstat(fd)
			close(fd)
			entry = {"path": fileName, "type": "file", "identity": (info.st_dev, info.st_ino, info.st_rdev)}
		except (OSError, ValueError) as error:
			callback(str(error))
			return
		self.busy = True

		def finished(result, retVal, extraArgs):
			error = ""
			try:
				self.checkIdentity(entry)
				if retVal:
					raise ValueError(_("Creating the swap file failed.\n%s") % result.decode("UTF-8", "replace").strip())
				self.fileInfo(fileName)
				self.rememberFile(fileName)
			except (OSError, ValueError) as failure:
				error = str(failure)
				try:
					self.checkIdentity(entry)
					if fileName not in self.readActive():
						unlink(fileName)
				except (OSError, ValueError):
					pass
			self.busy = False
			callback(error)

		def allocated(result, retVal, extraArgs):
			try:
				self.checkIdentity(entry)
				if retVal or stat(fileName).st_size != size * 1024 * 1024:
					finished(result, retVal or 1, None)
					return
			except (OSError, ValueError) as error:
				finished(str(error).encode("UTF-8"), 1, None)
				return
			self.console.ePopen(("/sbin/mkswap", "/sbin/mkswap", fileName), finished)

		# Fully allocate the file; sparse files and holes cannot be used as swap.
		self.console.ePopen(("/bin/dd", "/bin/dd", "if=/dev/zero", f"of={fileName}", "bs=1048576", f"count={size}", "conv=fsync"), allocated)


swapManager = SwapManager()
