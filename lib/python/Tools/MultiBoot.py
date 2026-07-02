#!/usr/bin/env python3
# Dual-mode: `python3 MultiBoot.py [--slot N | --slotnames]` scans & writes JSON;
# enigma2 imports MultiBootClass which reads it. stdlib-only above __main__.
from datetime import datetime
from glob import glob
from hashlib import md5
from json import dump, load
from os import listdir, makedirs, mkdir, rename, rmdir, stat, unlink
from os.path import basename, dirname, exists, isdir, isfile, join, islink, realpath
from re import findall, search
from struct import calcsize, pack, unpack, error
from subprocess import run
from sys import argv as sysArgv, exit as sysExit, stderr
from tempfile import mkdtemp
from time import monotonic

MODULE_NAME = __name__.split(".")[-1]

MOUNT = "/bin/mount"
UMOUNT = "/bin/umount"
REMOVE = "/bin/rm"
PREFIX = "MultiBoot_"
COMMAND_FILE = "cmdline.txt"
DUAL_BOOT_FILE = "/dev/block/by-name/flag"
DREAM_BOOT_FILE = "/data/bootconfig.txt"
STARTUP_FILE = "STARTUP"
STARTUP_ONCE = "STARTUP_ONCE"
STARTUP_TEMPLATE = "STARTUP_*"
STARTUP_ANDROID = "STARTUP_ANDROID"
STARTUP_ANDROID_LINUXSE = "STARTUP_ANDROID_LINUXSE"
STARTUP_RECOVERY = "STARTUP_RECOVERY"
STARTUP_FLASH = "STARTUP_FLASH"
STARTUP_BOXMODE = "BOXMODE"  # This is known as bootCode in this code.
SLOTNAMES_FILE = "SLOTNAMES"
BOOT_DEVICE_LIST = ("/dev/mmcblk0p1", "/dev/mmcblk1p1", "/dev/mmcblk0p3", "/dev/mmcblk0p4", "/dev/mtdblock2", "/dev/block/by-name/bootoptions", "/dev/block/by-name/others", "/dev/block/by-name/startup")
BOOT_DEVICE_LIST_VUPLUS = ("/dev/mmcblk0p4", "/dev/mmcblk0p7", "/dev/mmcblk0p9")  # Kexec kernel Vu+ MultiBoot.

JSON_FILE = "/var/run/multiboot.json"
SCAN_LOG = "/tmp/multiboot-scan.log"

KNOWN_DISTROS = {
	"beyonwiz": "Beyonwiz", "blackhole": "Black Hole", "dreambox": "DreamOS",
	"egami": "EGAMI", "gemini": "GeminiProject", "newnigma2": "Newnigma2",
	"openatv": "OpenATV", "openbh": "OpenBH", "opendreambox": "OpenDreambox",
	"opendroid": "OpenDroid", "openeight": "OpenEight", "openhdf": "OpenHDF",
	"opennfr": "OpenNFR", "openpli": "OpenPLi", "openspa": "OpenSpa",
	"openvision": "Open Vision", "openvix": "OpenViX", "pure2": "PurE2",
	"sif": "Sif", "teamblue": "teamBlue", "vti": "VTi",
}


def _naturalKey(key):
	# Pad every digit run to a fixed width so "STARTUP_10" > "STARTUP_2" as plain string compare.
	return "".join(f"{int(x):010d}" if x.isdigit() else x for x in findall(r"\d+|\D+", str(key)))


def _sortDictNatural(obj):
	if isinstance(obj, dict):
		return {k: _sortDictNatural(v) for k, v in sorted(obj.items(), key=lambda kv: _naturalKey(kv[0]))}
	return obj


# STARTUP
# STARTUP_LINUX_1_BOXMODE_1
# boot emmcflash0.linuxkernel 'root=/dev/mmcblk0p3 rootsubdir=linuxrootfs1 kernel=/dev/mmcblk0p2 rw rootwait h7_4.boxmode=1'
# STARTUP_LINUX_2_BOXMODE_1
# boot emmcflash0.linuxkernel2 'root=/dev/mmcblk0p8 rootsubdir=linuxrootfs2 kernel=/dev/mmcblk0p4 rw rootwait h7_4.boxmode=1'
# STARTUP_LINUX_3_BOXMODE_1
# boot emmcflash0.linuxkernel3 'root=/dev/mmcblk0p8 rootsubdir=linuxrootfs3 kernel=/dev/mmcblk0p5 rw rootwait h7_4.boxmode=1'
# STARTUP_LINUX_4_BOXMODE_1
# boot emmcflash0.linuxkernel4 'root=/dev/mmcblk0p8 rootsubdir=linuxrootfs4 kernel=/dev/mmcblk0p6 rw rootwait h7_4.boxmode=1'
# STARTUP_LINUX_1_BOXMODE_12
# boot emmcflash0.linuxkernel 'brcm_cma=520M@248M brcm_cma=192M@768M root=/dev/mmcblk0p3 rootsubdir=linuxrootfs1 kernel=/dev/mmcblk0p2 rw rootwait h7_4.boxmode=12'
# STARTUP_LINUX_2_BOXMODE_12
# boot emmcflash0.linuxkernel2 'brcm_cma=520M@248M brcm_cma=192M@768M root=/dev/mmcblk0p8 rootsubdir=linuxrootfs2 kernel=/dev/mmcblk0p4 rw rootwait h7_4.boxmode=12'
# STARTUP_LINUX_3_BOXMODE_12
# boot emmcflash0.linuxkernel3 'brcm_cma=520M@248M brcm_cma=192M@768M root=/dev/mmcblk0p8 rootsubdir=linuxrootfs3 kernel=/dev/mmcblk0p5 rw rootwait h7_4.boxmode=12'
# STARTUP_LINUX_4_BOXMODE_12
# boot emmcflash0.linuxkernel4 'brcm_cma=520M@248M brcm_cma=192M@768M root=/dev/mmcblk0p8 rootsubdir=linuxrootfs4 kernel=/dev/mmcblk0p6 rw rootwait h7_4.boxmode=12'
#
# STARTUP
# STARTUP_1
# boot emmcflash0.kernel1: 'root=/dev/mmcblk0p5 rootwait rw rootflags=data=journal libata.force=1:3.0G,2:3.0G,3:3.0G coherent_poll=2M vmalloc=525m bmem=529m@491m bmem=608m@2464m'
# STARTUP_2
# boot emmcflash0.kernel2: 'root=/dev/mmcblk0p7 rootwait rw rootflags=data=journal libata.force=1:3.0G,2:3.0G,3:3.0G coherent_poll=2M vmalloc=525m bmem=529m@491m bmem=608m@2464m'
# STARTUP_3
# boot emmcflash0.kernel3: 'root=/dev/mmcblk0p9 rootwait rw rootflags=data=journal libata.force=1:3.0G,2:3.0G,3:3.0G coherent_poll=2M vmalloc=525m bmem=529m@491m bmem=608m@2464m'
#
# STARTUP (sfx6008)
# boot internalflash0.linuxkernel1 'ubi.mtd=12 root=ubi0:ubifs rootsubdir=linuxrootfs1 rootfstype=ubifs kernel=/dev/mtd10 userdataroot=/dev/mtd12 userdatasubdir=userdata1 mtdparts=hinand:1M(boot),1M(bootargs),1M(bootoptions),1M(baseparam),1M(pqparam),1M(logo),1M(deviceinfo),1M(softwareinfo),1M(loaderdb),16M(loader),6M(linuxkernel1),6M(linuxkernel2),-(userdata)'
#
# /sys/firmware/devicetree/base/chosen/bootargs
# console=ttyAMA0,115200 ubi.mtd=12 root=ubi0:ubifs rootsubdir=linuxrootfs1 rootfstype=ubifs kernel=/dev/mtd10 userdataroot=/dev/mtd12 userdatasubdir=userdata1 mtdparts=hinand:1M(boot),1M(bootargs),1M(bootoptions),1M(baseparam),1M(pqparam),1M(logo),1M(deviceinfo),1M(softwareinfo),1M(loaderdb),16M(loader),6M(linuxkernel1),6M(linuxkernel2),-(userdata) mem=512M mmz=ddr,0,0,160M vmalloc=500M MACHINEBUILD=sfx6008 OEM=octagon MODEL=sfx6008
#
# root=/dev/mmcblk0p3 rootsubdir=linuxrootfs1 kernel=/dev/mmcblk0p2 rw rootwait h7_4.boxmode=1
#


# ============================================================
# Scanner section — stdlib+subprocess only, no enigma2 deps.
# Can be executed by `python3 MultiBoot.py [--slot N | --slotnames]`
# at boot via init script and as an emergency fallback from
# MultiBootClass.__init__ when the JSON is missing.
# ============================================================

def _scan_log(msg):
	try:
		with open(SCAN_LOG, "a") as fd:
			fd.write(f"{datetime.now().isoformat(timespec='seconds')} {msg}\n")
	except OSError:
		pass


def _scan_run(cmd):
	return run(cmd, capture_output=True).returncode


def _scan_read_lines(path):
	try:
		with open(path, "r", errors="replace") as fd:
			return [line.rstrip("\n") for line in fd]
	except OSError:
		return []


def _scan_read_first_line(path):
	lines = _scan_read_lines(path)
	return lines[0] if lines else ""


def _scan_file_has(path, needle):
	return needle in _scan_read_first_line(path)


def _scan_resolve_device(device):
	return realpath(device) if islink(device) else device


def _scan_find_existing_mount(device):
	# /proc/mounts may list the source as a /dev/<symlink> (e.g. /dev/dreambox-data) while our
	# device is the resolved realdev (e.g. /dev/mmcblk0p4) — resolve both sides to match.
	resolved = _scan_resolve_device(device)
	try:
		with open("/proc/mounts") as fd:
			for line in fd:
				parts = line.split()
				if len(parts) < 2:
					continue
				src = parts[0]
				if src in (device, resolved):
					return parts[1].replace("\\040", " ")
				if src.startswith("/dev/") and _scan_resolve_device(src) == resolved:
					return parts[1].replace("\\040", " ")
	except OSError:
		pass
	return None


def _scan_mount_subroot(mount_point):
	# Return which FS path this mount exposes: "/" for a full mount, "/subdir" when the kernel
	# bound only a sub-directory.
	try:
		with open("/proc/self/mountinfo") as fd:
			for line in fd:
				parts = line.split()
				if len(parts) >= 5 and parts[4] == mount_point:
					return parts[3]
	except OSError:
		pass
	return "/"


class _ScanMount(object):
	# Reuse the existing mount if it exposes the whole FS; else mount fresh so sibling subdirs
	# hidden by a subtree-mount become visible.
	def __init__(self, device, opts=None):
		self.device = device
		self.opts = opts or []
		self.mount_point = None
		self.owned = False

	def __enter__(self):
		existing = _scan_find_existing_mount(self.device)
		if existing and _scan_mount_subroot(existing) == "/":
			self.mount_point = existing
			return existing
		self.mount_point = mkdtemp(prefix=PREFIX)
		if _scan_run([MOUNT] + self.opts + [self.device, self.mount_point]) == 0:
			self.owned = True
			return self.mount_point
		try:
			rmdir(self.mount_point)
		except OSError:
			pass
		self.mount_point = None
		return None

	def __exit__(self, *exc):
		if self.owned and self.mount_point:
			_scan_run([UMOUNT, self.mount_point])
			try:
				rmdir(self.mount_point)
			except OSError:
				pass


def _scan_get_param(line, param):
	return line.replace("userdataroot", "rootuserdata").rsplit(f"{param}=", 1)[1].split(" ", 1)[0]


def _scan_uuid_to_device(uuid):
	if uuid.startswith("UUID="):
		uuid = uuid[5:]
	try:
		for fname in listdir("/dev/uuid"):
			if _scan_read_first_line(join("/dev/uuid", fname)) == uuid:
				return f"/dev/{fname}"
	except OSError:
		pass
	return None


def _scan_process_value(value):
	if value is None:
		return None
	vt = value.upper() if value else ""
	if value.startswith(('"', "'")) and value.endswith(value[0]):
		return value[1:-1]
	if value.startswith("(") and value.endswith(")"):
		return tuple(_scan_process_value(x.strip()) for x in value[1:-1].split(","))
	if value.startswith("[") and value.endswith("]"):
		return [_scan_process_value(x.strip()) for x in value[1:-1].split(",")]
	if vt == "NONE":
		return None
	if vt in ("FALSE", "NO", "OFF", "DISABLED"):
		return False
	if vt in ("TRUE", "YES", "ON", "ENABLED"):
		return True
	if value.isdigit() or (value[:1] in ("-", "+") and value[1:].isdigit()):
		return int(value)
	for base_val, prefix in ((16, "0X"), (8, "0O"), (2, "0B")):
		if vt.startswith(prefix):
			try:
				return int(value, base_val)
			except ValueError:
				pass
	try:
		return float(value)
	except ValueError:
		pass
	return value


def _scan_check_checksum(lines):
	value = "Undefined!"
	data = []
	for line in lines:
		if line.startswith("checksum"):
			_, value = (x.strip() for x in line.split("=", 1))
		else:
			data.append(line)
	data.append("")
	result = md5(bytearray("\n".join(data), "UTF-8", errors="ignore")).hexdigest()  # NOSONAR
	return value != result


def _scan_read_slot_info(path, slot_code=None):
	info = {}
	for src in (path, path.replace(".info", ".conf")):
		lines = _scan_read_lines(src)
		if not lines:
			continue
		if src.endswith(".info") and _scan_check_checksum(lines):
			_scan_log(f"warning: slot '{slot_code or '?'}' checksum mismatch in {basename(src)}")
		for line in lines:
			if line.startswith("#") or not line.strip():
				continue
			if "=" in line:
				item, val = (x.strip() for x in line.split("=", 1))
				if item:
					info[item] = _scan_process_value(val)
	return info


def _scan_get_compile_date(path):
	status_file = "var/lib/opkg/status"
	if exists(join(path, "var/lib/dpkg/status")):
		status_file = "var/lib/dpkg/status"
	try:
		date = datetime.fromtimestamp(stat(join(path, status_file)).st_mtime).strftime("%Y%m%d")
		if date.startswith("1970"):
			date = datetime.fromtimestamp(stat(join(path, "usr/share/bootlogo.mvi")).st_mtime).strftime("%Y%m%d")
		date = max(date, datetime.fromtimestamp(stat(join(path, "usr/bin/enigma2")).st_mtime).strftime("%Y%m%d"))
	except OSError:
		date = "00000000"
	return date


def _display_distro(distro):
	key = distro.lower()
	if key in KNOWN_DISTROS:
		return KNOWN_DISTROS[key]
	for match, display in KNOWN_DISTROS.items():
		if match in key:
			return display
	return distro.capitalize()


def _scan_enigma2_pkg_version(path):
	for status_path in ("var/lib/opkg/status", "var/lib/dpkg/status"):
		lines = _scan_read_lines(join(path, status_path))
		if not lines:
			continue
		in_enigma2 = False
		for line in lines:
			if line.startswith("Package: "):
				in_enigma2 = line[9:].strip() == "enigma2"
			elif in_enigma2 and line.startswith("Version: "):
				version = line[9:].strip().split("+", 1)[0]
				if "-r" in version:
					version = version.split("-r", 1)[0]
				return version or None
	return None


def _scan_derive_slot_info(path):
	info = {"compiledate": _scan_get_compile_date(path)}
	lines = _scan_read_lines(join(path, "etc/issue"))
	if lines and "vuplus" not in lines[0] and len(lines) >= 2:
		data = lines[-2].strip()[:-6].split()
		info["distro"] = " ".join(data[:-1])
		info["displaydistro"] = _display_distro(info["distro"])
		info["imgversion"] = data[-1]
	else:
		info["distro"] = "Enigma2"
		info["displaydistro"] = "Enigma2"
		info["imgversion"] = "???"
	if info["imgversion"] in ("", "???"):
		pkg_version = _scan_enigma2_pkg_version(path)
		if pkg_version:
			info["imgversion"] = pkg_version
	return info


def _scan_format_slot_name(info):
	# Raw imagename "<distro> <version><revision>". compiledate is stored separately and appended
	# only in displayname; revision is dropped when it equals compiledate to avoid duplications.
	distro = info.get("displaydistro") or info.get("distro")
	if not distro:
		return None
	compile_date = str(info.get("compiledate", ""))
	revision = info.get("imgrevision")
	if revision is not None:
		revision = f".{revision:03d}" if info.get("distro") == "openvix" and isinstance(revision, int) else f" {revision}"
		revision = "" if revision.strip() == compile_date else revision
	else:
		revision = ""
	version = info.get("imgversion") or ""
	return f"{distro} {version}{revision}".rstrip()


def _scan_find_boot_device():
	is_kexec = _scan_file_has("/proc/cmdline", "kexec=1")
	candidates = BOOT_DEVICE_LIST_VUPLUS if is_kexec else BOOT_DEVICE_LIST
	for device in candidates:
		if not exists(device):
			continue
		with _ScanMount(device) as mount_point:
			if not mount_point:
				continue
			cmd_file = join(mount_point, COMMAND_FILE)
			startup_file = join(mount_point, STARTUP_FILE)
			if isfile(cmd_file) or isfile(startup_file):
				src = cmd_file if isfile(cmd_file) else startup_file
				startup_cmd = " ".join(x.strip() for x in _scan_read_lines(src) if x.strip())
				return _scan_resolve_device(device), startup_cmd
	return None, ""


def _scan_boot_slots(boot_device):
	# Each slot's "bootCodes" dict maps bootCode (string) → {startupfile, cmdline} — slotname and
	# displayname get attached later. Non-BOXMODE slots have one entry "1"; h7 has several.
	boot_slots = {}
	if not boot_device:
		return boot_slots
	with _ScanMount(boot_device) as mount_point:
		if not mount_point:
			return boot_slots
		for path in sorted(glob(join(mount_point, STARTUP_TEMPLATE))):
			file = basename(path)
			if "DISABLE" in file:
				continue
			if file == STARTUP_ANDROID:
				boot_code, slot_code = "1", "A"
			elif file == STARTUP_ANDROID_LINUXSE:
				boot_code, slot_code = "1", "L"
			elif file == STARTUP_RECOVERY:
				boot_code, slot_code = "1", "R"
			elif file == STARTUP_FLASH:
				boot_code, slot_code = "1", "F"
			elif STARTUP_BOXMODE in file:
				parts = file.rsplit("_", 3)
				boot_code, slot_code = parts[3], parts[1]
			else:
				boot_code, slot_code = "1", file.rsplit("_", 1)[1]
			if not slot_code:
				_scan_log(f"error: cannot derive slot code from '{file}'")
				continue
			line = " ".join(x.strip() for x in _scan_read_lines(path) if x.strip())
			slot = boot_slots.setdefault(slot_code, {})
			if "root=" in line:
				device = _scan_get_param(line, "root")
				if "UUID=" in device:
					uuid_dev = _scan_uuid_to_device(device)
					if uuid_dev:
						device = uuid_dev
				if not (exists(device) or device in ("ubi0:ubifs", "ubi0:rootfs", "ubi0:dreambox-rootfs")):
					continue
				slot.setdefault("device", device)
				slot.setdefault("bootCodes", {})[boot_code] = {"startupfile": file, "cmdline": line}
				if "ubi.mtd=" in line:
					slot["ubi"] = True
				if "UUID=" in line:
					slot["uuid"] = True
				if "rescuemode" in line:
					slot["rootsubdir"] = "rescue"
				boot_disk = [x for x in ("sda", "sdb", "sdc", "sdd") if x in line]
				if "rootsubdir" in line:
					slot["kernel"] = _scan_get_param(line, "kernel")
					slot["rootsubdir"] = _scan_get_param(line, "rootsubdir")
				elif "flash=1" in line:
					slot["kernel"] = _scan_get_param(line, "kernel")
					slot["rootfs"] = _scan_get_param(line, "root")
				elif boot_disk:
					d = boot_disk[0]
					slot.setdefault("kernel", f"/dev/{d}{line.split(d, 1)[1].split(' ', 1)[0]}")
				else:
					parts = device.split("p")
					try:
						slot.setdefault("kernel", f"{parts[0]}p{int(parts[1]) - 1}")
					except (IndexError, ValueError):
						pass
			elif "bootcmd=" in line or " recovery " in line:
				slot.setdefault("bootCodes", {})[boot_code] = {"startupfile": file, "cmdline": line}
			else:
				_scan_log(f"error: slot line unidentifiable: {line}")
	return boot_slots


def _scan_slotnames_dict(boot_device):
	if not boot_device:
		return {}
	result = {}
	with _ScanMount(boot_device) as mount_point:
		if not mount_point:
			return result
		path = join(mount_point, SLOTNAMES_FILE)
		if not isfile(path):
			return result
		for raw in _scan_read_lines(path):
			line = raw.strip()
			if not line or line.startswith("#") or "=" not in line:
				continue
			key, _sep, val = line.partition("=")
			key = key.strip()
			val = val.strip()
			if key and val:
				result[key] = val
	return result


def _scan_current_slot(boot_slots, startup_cmd):
	if exists(DUAL_BOOT_FILE):
		try:
			with open(DUAL_BOOT_FILE, "rb") as fd:
				fmt = "B"
				slot = unpack(fmt, fd.read(calcsize(fmt)))
				return str(slot[0]), "1"
		except (OSError, error):
			return None, "1"
	if exists(DREAM_BOOT_FILE):
		running_root = None
		for token in _scan_read_first_line("/proc/cmdline").split():
			if token.startswith("root="):
				running_root = token[5:]
				break
		if running_root:
			for slot_code, slot in boot_slots.items():
				if slot.get("device") == running_root:
					return slot_code, "1"
		return None, "1"
	for slot_code in sorted(boot_slots.keys()):
		for boot_code, cfg in boot_slots[slot_code].get("bootCodes", {}).items():
			if cfg.get("cmdline") == startup_cmd:
				return slot_code, boot_code
	return None, "1"


def _scan_analyze_image_dir(image_dir, slot_code=None):
	# Detect the image in image_dir (enigma.info > image-version > enigma2 > hidden > empty) and
	# return imagename/compiledate/status/detection. slot_code only labels checksum-mismatch logs.
	info_file = join(image_dir, "usr/lib/enigma.info")
	version_file = join(image_dir, "etc/image-version")
	hidden_marker = join(image_dir, "usr/bin/enigma2x.bin")
	if isfile(info_file):
		info = _scan_read_slot_info(info_file, slot_code)
		name = _scan_format_slot_name(info) or "Unknown"
		return {
			"imagename": name,
			"displaydistro": info.get("displaydistro") or info.get("distro") or "",
			"imgversion": str(info.get("imgversion") or ""),
			"imgrevision": str(info.get("imgrevision") or ""),
			"compiledate": str(info.get("compiledate") or ""),
			"status": "active",
			"detection": "Found an enigma information file",
		}
	if isfile(version_file):
		info = _scan_read_slot_info(version_file, slot_code)
		cd_raw = _scan_get_compile_date(image_dir)
		version = str(info.get("version") or "")
		if "." not in version and "-" not in version and version.isdigit():
			version = f"{int(version[0:2])}.{version[2:3]}.{version[3:5]}" if len(version) == 17 else f"{int(version[0:2])}.{int(version[3:5])}"
		creator = info.get("creator")
		base = f"{creator.split()[0]} {version}" if creator else f"Unknown Creator {version}"
		return {
			"imagename": base,
			"compiledate": cd_raw,
			"status": "active",
			"detection": "Found an image version file",
		}
	if isfile(join(image_dir, "usr/bin/enigma2")):
		info = _scan_derive_slot_info(image_dir)
		cd_raw = str(info.get("compiledate") or "")
		base = f"{info.get('displaydistro', info.get('distro'))} {info.get('imgversion')}"
		return {
			"imagename": base,
			"compiledate": cd_raw,
			"status": "active",
			"detection": "Found an enigma2 binary file",
		}
	if isfile(hidden_marker):
		return {
			"imagename": "Disabled",
			"status": "hidden",
			"detection": "Found a disabled enigma2 binary file",
		}
	return {
		"imagename": "Empty",
		"status": "empty",
		"detection": "Found no enigma files",
	}


def _scan_analyze_slot(slot_code, slot, running_slot_code):
	base = {
		"ubi": slot.get("ubi", False),
		"uuid": slot.get("uuid", False),
		"device": slot.get("device", ""),
		"kernel": slot.get("kernel", "Unknown"),
		"rootsubdir": slot.get("rootsubdir", ""),
		"bootCodes": slot.get("bootCodes", {}),
	}
	if slot_code == "A":
		return {**base, "imagename": "Android", "status": "android", "detection": "Found an Android slot"}
	if slot_code == "L":
		return {**base, "imagename": "Android Linux SE", "status": "androidlinuxse", "detection": "Found an Android Linux SE slot"}
	if slot_code == "R":
		if _scan_file_has("/proc/cmdline", "kexec=1"):
			return {**base, "imagename": "Root Image", "status": "rootimage", "detection": "Found a Root Image slot"}
		return {**base, "imagename": "Recovery", "status": "recovery", "detection": "Found a Recovery slot"}
	if slot_code == "F":
		return {**base, "imagename": "Flash", "status": "flash", "detection": "Found a Flash Image slot"}
	device = slot.get("device")
	if not device:
		return {**base, "imagename": "Unknown", "status": "unknown", "detection": "Found an unexpected/ill-defined slot"}
	# Running slot: rootfs already at /; if kernel bound rootsubdir as / then /rootsubdir doesn't exist — use /.
	if slot_code == running_slot_code:
		rootsubdir = slot.get("rootsubdir")
		image_dir = f"/{rootsubdir}" if rootsubdir and isdir(f"/{rootsubdir}") else "/"
		base.update(_scan_analyze_image_dir(image_dir, slot_code))
		return base
	opts = ["-t", "ubifs"] if slot.get("ubi") else []
	with _ScanMount(device, opts=opts) as mount_point:
		if not mount_point:
			_scan_log(f"error: cannot mount slot '{slot_code}' ({device}) for analysis")
			return {**base, "imagename": "Inaccessible", "status": "unknown", "detection": f"Cannot mount slot '{slot_code}' ({device})"}
		rootsubdir = slot.get("rootsubdir")
		image_dir = join(mount_point, rootsubdir) if rootsubdir else mount_point
		base.update(_scan_analyze_image_dir(image_dir, slot_code))
		return base


def _load_existing_json():
	try:
		with open(JSON_FILE) as fd:
			return load(fd)
	except (OSError, ValueError):
		return None


def _write_json(data):
	sorted_data = _sortDictNatural(data)
	try:
		d = dirname(JSON_FILE)
		if d:
			makedirs(d, exist_ok=True)
		with open(JSON_FILE, "w") as fd:
			dump(sorted_data, fd, indent=2, default=str)
	except OSError as err:
		_scan_log(f"error writing '{JSON_FILE}': {err}")


def _attach_slot_names(slots, slot_names_flat):
	# Fan the flat SLOTNAMES {startupfile: name} out into per-bootCodes "slotname" fields verbatim
	# (matches what sits on disk in SLOTNAMES).
	for entry in slots.values():
		for cfg in (entry.get("bootCodes") or {}).values():
			startup = cfg.get("startupfile")
			if startup and startup in slot_names_flat:
				cfg["slotname"] = slot_names_flat[startup]
			else:
				cfg.pop("slotname", None)


def _attach_display_names(slots):
	# Build cfg.displayname = (slotname or imagename) + " (YYYY-MM-DD)" — pre-formatted so the UI
	# can render slotname/imagename without knowing about the compile date.
	for entry in slots.values():
		imagename = entry.get("imagename") or ""
		cdate = str(entry.get("compiledate") or "")
		date_suffix = f" ({cdate[0:4]}-{cdate[4:6]}-{cdate[6:8]})" if len(cdate) == 8 and cdate.isdigit() and cdate != "00000000" else ""
		for cfg in (entry.get("bootCodes") or {}).values():
			base = cfg.get("slotname") or imagename
			cfg["displayname"] = f"{base}{date_suffix}" if base else ""


def scan_full():
	boot_device, startup_cmd = _scan_find_boot_device()
	boot_slots = _scan_boot_slots(boot_device)
	slot_names_flat = _scan_slotnames_dict(boot_device)
	current_slot, current_boot = _scan_current_slot(boot_slots, startup_cmd)
	slots = {}
	for slot_code in sorted(boot_slots.keys(), key=_naturalKey):
		slots[slot_code] = _scan_analyze_slot(slot_code, boot_slots[slot_code], current_slot)
	_attach_slot_names(slots, slot_names_flat)
	_attach_display_names(slots)
	return {
		"bootDevice": boot_device,
		"startupCmdLine": startup_cmd,
		"startupSlot": current_slot,
		"startupBootCode": current_boot,
		"slots": slots,
	}


def scan_slot(slot_code):
	# Refreshes every slot's slotname too — SLOTNAMES read is cheap once the boot device is mounted.
	existing = _load_existing_json()
	if not existing:
		return scan_full()
	boot_device = existing.get("bootDevice")
	if not boot_device:
		return scan_full()
	boot_slots = _scan_boot_slots(boot_device)
	slot_names_flat = _scan_slotnames_dict(boot_device)
	if slot_code not in boot_slots:
		# Slot disappeared (STARTUP file gone) — drop from JSON.
		existing.setdefault("slots", {}).pop(slot_code, None)
	else:
		current_slot = existing.get("startupSlot")
		existing.setdefault("slots", {})[slot_code] = _scan_analyze_slot(slot_code, boot_slots[slot_code], current_slot)
	_attach_slot_names(existing.get("slots") or {}, slot_names_flat)
	_attach_display_names(existing.get("slots") or {})
	return existing


def scan_slotnames_only():
	existing = _load_existing_json()
	if not existing:
		return scan_full()
	boot_device = existing.get("bootDevice")
	if not boot_device:
		return scan_full()
	slot_names_flat = _scan_slotnames_dict(boot_device)
	_attach_slot_names(existing.get("slots") or {}, slot_names_flat)
	_attach_display_names(existing.get("slots") or {})
	return existing


def _slotLine(slot_code, entry):
	status = entry.get("status", "unknown")
	imagename = entry.get("imagename") or "?"
	configs = entry.get("bootCodes") or {}
	startups = ",".join(sorted(cfg.get("startupfile") for cfg in configs.values() if cfg.get("startupfile"))) or "-"
	line = f"  slot {slot_code:>3} [{status:>14}] {imagename}  ({startups})"
	overrides = {bc: cfg["slotname"] for bc, cfg in configs.items() if cfg.get("slotname")}
	if overrides:
		items = ", ".join(f"{k}={v!r}" for k, v in sorted(overrides.items(), key=lambda kv: _naturalKey(kv[0])))
		line += f"  overrides={{{items}}}"
	if status in ("unknown", "empty", "hidden"):
		reason = entry.get("detection")
		if reason:
			line += f"  reason={reason!r}"
	return line


def _log_scan(mode, source, dur_ms, data):
	slots = data.get("slots") or {}
	status_counts = {}
	total_overrides = 0
	for entry in slots.values():
		s = entry.get("status", "unknown")
		status_counts[s] = status_counts.get(s, 0) + 1
		total_overrides += sum(1 for cfg in (entry.get("bootCodes") or {}).values() if cfg.get("slotname"))
	status_summary = " ".join(f"{k}={v}" for k, v in sorted(status_counts.items())) or "-"
	_scan_log(
		f"[{mode}/{source}] boot={data.get('bootDevice')}"
		f" current={data.get('startupSlot')}/{data.get('startupBootCode') or '-'}"
		f" slots={len(slots)}({status_summary})"
		f" overrides={total_overrides} dur={dur_ms}ms"
	)
	only_slot = mode.split("=", 1)[1] if mode.startswith("slot=") else None
	for slot_code in sorted(slots.keys(), key=_naturalKey):
		if only_slot is not None and slot_code != only_slot:
			continue
		if mode == "slotnames" and not any(cfg.get("slotname") for cfg in (slots[slot_code].get("bootCodes") or {}).values()):
			continue
		_scan_log(_slotLine(slot_code, slots[slot_code]))


def main():
	args = sysArgv[1:]
	source = "cli"
	if "--source" in args:
		idx = args.index("--source")
		if idx + 1 < len(args):
			source = args[idx + 1]
			del args[idx:idx + 2]
	started = monotonic()
	try:
		if not args:
			data = scan_full()
			mode = "full"
		elif args[0] == "--slotnames" and len(args) == 1:
			data = scan_slotnames_only()
			mode = "slotnames"
		elif args[0] == "--slot" and len(args) == 2:
			data = scan_slot(args[1])
			mode = f"slot={args[1]}"
		else:
			print(f"usage: {sysArgv[0]} [--slot N | --slotnames] [--source LABEL]", file=stderr)
			return 2
		_write_json(data)
		dur_ms = int((monotonic() - started) * 1000)
		_log_scan(mode, source, dur_ms, data)
		total_overrides = sum(1 for e in (data.get("slots") or {}).values() for cfg in (e.get("bootCodes") or {}).values() if cfg.get("slotname"))
		print(f"[MultiBoot] scan mode={mode} source={source} dur={dur_ms}ms slots={len(data.get('slots') or {})} current={data.get('startupSlot')} overrides={total_overrides}")
		return 0
	except Exception as err:
		import traceback
		_scan_log(f"CRASH source={source}: {err}\n{traceback.format_exc()}")
		raise


if __name__ == "__main__":
	sysExit(main())


# ============================================================
# enigma2 module — MultiBootClass. These imports live below the __main__
# dispatch so that shell invocation stays enigma2-independent.
# NOTE: This module must not import from SystemInfo.py as this module is
# used to populate BoxInfo / SystemInfo and will create a boot loop!
# ============================================================

from Components.Console import Console  # noqa: E402
from Tools.Directories import SCOPE_CONFIG, copyfile, fileHas, fileReadLine, fileReadLines, fileWriteLines, resolveFilename  # noqa: E402


class MultiBootClass():
	def __init__(self):
		print("[MultiBoot] MultiBoot is initializing.")
		lines = []
		lines = fileReadLines(resolveFilename(SCOPE_CONFIG, "settings"), default=lines, source=MODULE_NAME)
		self.debugMode = "config.crash.debugMultiBoot=True" in lines
		self.bootArgs = fileReadLine("/sys/firmware/devicetree/base/chosen/bootargs", default="", source=MODULE_NAME)
		self.console = Console()
		self.bootDevice = None
		self.startupCmdLine = ""
		self.bootSlot = None
		self.bootCode = ""
		self.bootSlots = {}
		self.bootSlotsKeys = []
		self._loadStateFromJson()
		# Boot-time sync tasks: STARTUP file selection and DreamNextGen bootconfig.txt.
		if exists(DREAM_BOOT_FILE):
			self.syncStartupFileFromBootSlot()
			self._syncDreamBootDefault()
			if self.bootSlot:
				self.updateDreamBootSection(self.bootSlot)

	def _loadStateFromJson(self):
		# If the JSON is missing we call the scanner inline once, then re-read. Hard-fail if it
		# still isn't there — the scan must succeed before enigma2 has usable MultiBoot state.
		data = self._readJson()
		if data is None:
			print(f"[MultiBoot] {JSON_FILE} missing, invoking inline scanner subprocess.")
			try:
				run(["/usr/bin/python3", __file__, "--source", "fallback"], check=False)
			except Exception as err:
				print(f"[MultiBoot] Emergency scanner call failed: {err}")
			data = self._readJson()
		if data is None:
			raise RuntimeError(f"[MultiBoot] {JSON_FILE} unavailable and scanner did not produce it")
		self.bootDevice = data.get("bootDevice")
		self.startupCmdLine = data.get("startupCmdLine") or ""
		self.bootSlot = data.get("startupSlot")
		self.bootCode = data.get("startupBootCode") or "1"  # "1" is the non-BOXMODE index.
		slots = dict(data.get("slots") or {})
		self.bootSlots = slots
		self.bootSlotsKeys = sorted(slots.keys(), key=_naturalKey)
		try:
			self._jsonMtime = stat(JSON_FILE).st_mtime_ns
		except OSError:
			self._jsonMtime = 0
		if self.debugMode:
			print(f"[MultiBoot] Loaded from JSON: bootDevice={self.bootDevice} startupSlot={self.bootSlot} slots={len(slots)}")

	def _collectSlotNames(self):
		# {startupfile: rawname} — pulled straight from cfg.slotname (already raw, matches
		# SLOTNAMES on disk). Used by set/clearSlotName to rewrite the file.
		names = {}
		for entry in self.bootSlots.values():
			for cfg in (entry.get("bootCodes") or {}).values():
				startup = cfg.get("startupfile")
				name = cfg.get("slotname")
				if startup and name:
					names[startup] = name
		return names

	def _reloadIfStale(self):
		# Cheap stat() on every read entry point — pick up JSON changes written by external
		# scanner invocations (init.d/multiboot-scan, manual `--source ...` runs) without a reboot.
		try:
			mtime = stat(JSON_FILE).st_mtime_ns
		except OSError:
			return
		if mtime != getattr(self, "_jsonMtime", 0):
			self._loadStateFromJson()

	def _readJson(self):
		try:
			with open(JSON_FILE) as fd:
				return load(fd)
		except (OSError, ValueError) as err:
			if self.debugMode:
				print(f"[MultiBoot] _readJson: {err}")
			return None

	def _refreshJsonSlotNames(self):
		try:
			run(["/usr/bin/python3", __file__, "--slotnames", "--source", "write"], check=False)
		except Exception as err:
			print(f"[MultiBoot] scanner --slotnames failed: {err}")
		data = self._readJson()
		if not data:
			return
		for slotCode, entry in (data.get("slots") or {}).items():
			target = self.bootSlots.get(slotCode)
			if target is None:
				continue
			for bootCode, freshCfg in (entry.get("bootCodes") or {}).items():
				targetCfg = (target.get("bootCodes") or {}).get(bootCode)
				if targetCfg is None:
					continue
				if freshCfg.get("slotname"):
					targetCfg["slotname"] = freshCfg["slotname"]
				else:
					targetCfg.pop("slotname", None)
				if freshCfg.get("displayname"):
					targetCfg["displayname"] = freshCfg["displayname"]
				else:
					targetCfg.pop("displayname", None)

	def _refreshJsonSlot(self, slotCode):
		# Spawn the scanner for this one slot, then reload it into self.bootSlots so subsequent
		# reads see the fresh state without a reboot.
		if not slotCode:
			return
		try:
			run(["/usr/bin/python3", __file__, "--slot", str(slotCode), "--source", "write"], check=False)
		except Exception as err:
			print(f"[MultiBoot] scanner --slot {slotCode} failed: {err}")
		data = self._readJson()
		if not data:
			return
		slots = data.get("slots") or {}
		if slotCode in slots:
			self.bootSlots[slotCode] = slots[slotCode]
		else:
			self.bootSlots.pop(slotCode, None)
		self.bootSlotsKeys = sorted(self.bootSlots.keys(), key=_naturalKey)

	def syncStartupFileFromBootSlot(self):
		# Embedded bootmanager picks the slot without updating /data/STARTUP, so copy STARTUP_<N> over /data/STARTUP here.
		if not self.bootDevice or not self.bootSlot:
			return
		bootSlot = self.bootSlots.get(self.bootSlot)
		if not bootSlot:
			return
		cfg = bootSlot.get("bootCodes", {}).get(self.bootCode) or {}
		cmdLine = cfg.get("cmdline")
		startupName = cfg.get("startupfile")
		if not cmdLine or not startupName or cmdLine == self.startupCmdLine:
			return
		tempDir = mkdtemp(prefix=PREFIX)
		self.console.ePopen([MOUNT, MOUNT, self.bootDevice, tempDir])
		try:
			src = join(tempDir, startupName)
			dst = join(tempDir, STARTUP_FILE)
			if isfile(src):
				copyfile(src, dst)
				self.startupCmdLine = cmdLine
				print(f"[MultiBoot] Synced '{STARTUP_FILE}' to '{startupName}' to match '/proc/cmdline'.")
		finally:
			self.console.ePopen([UMOUNT, UMOUNT, tempDir])
			rmdir(tempDir)

	def _syncDreamBootDefault(self):
		# Align /data/bootconfig.txt's default= with the running slot so a plain reboot stays in the same slot.
		if not self.bootSlot:
			return
		sectionIdx = self.getDreamBootSectionIndex(self.bootSlot)
		if sectionIdx is None:
			return
		current = None
		with open(DREAM_BOOT_FILE, "r") as fd:
			for line in fd:
				if line.startswith("default="):
					try:
						current = int(line.strip().split("=")[1])
					except (ValueError, IndexError):
						pass
					break
		if current != sectionIdx:
			self._writeDreamBoot(defaultIdx=sectionIdx)

	def getDreamBootSectionName(self, slotCode):
		# Returns the pre-formatted displayname that DreamNextGen shows in its bootmanager menu
		self._reloadIfStale()
		slot = self.bootSlots.get(slotCode) if slotCode else None
		if not slot or slotCode in ("R", "A", "L", "F"):
			return None
		if not slot.get("device"):
			return None
		cfg = (slot.get("bootCodes") or {}).get(self.bootCode) or {}
		name = cfg.get("displayname") or slot.get("imagename")
		if name:
			return name
		if slotCode and slotCode.isdecimal():
			return f"BuildIn Slot {slotCode}"
		return None

	def updateDreamBootSection(self, slotCode, setDefault=False, sectionName=None):
		sectionIdx = self.getDreamBootSectionIndex(slotCode)
		if sectionIdx is None and setDefault:
			if slotCode.isdecimal():
				sectionIdx = int(slotCode) - 1
			elif slotCode == "R":
				cmd_count = sum(1 for _ in self._iterDreamBootSections())
				if cmd_count:
					sectionIdx = cmd_count - 1
		if sectionIdx is None:
			return
		if sectionName is None:
			sectionName = self.getDreamBootSectionName(slotCode)
		sectionUpdates = {sectionIdx: sectionName} if sectionName else None
		self._writeDreamBoot(defaultIdx=sectionIdx if setDefault else None, sectionUpdates=sectionUpdates)

	def getDreamBootSectionIndex(self, slotCode):
		# Match by root partition (or 'recovery' for slotCode R) — section order is not fixed.
		isRecovery = slotCode == "R"
		targetPart = None
		if not isRecovery:
			match = search(r"p(\d+)$", self.bootSlots.get(slotCode, {}).get("device", ""))
			if not match:
				return None
			targetPart = match.group(1)
		for cur, cmd in self._iterDreamBootSections():
			if isRecovery:
				if "recovery" in cmd.lower():
					return cur
			else:
				match = search(r"\b\d+:(\d+)\b", cmd)
				if match and match.group(1) == targetPart:
					return cur
		return None

	def _iterDreamBootSections(self):
		# Yield (sectionIdx, cmdLine) for each [Section] / cmd= pair in DREAM_BOOT_FILE.
		if not exists(DREAM_BOOT_FILE):
			return
		cur = -1
		with open(DREAM_BOOT_FILE, "r") as fd:
			for line in fd:
				stripped = line.strip()
				if stripped.startswith("[") and stripped.endswith("]"):
					cur += 1
				elif stripped.startswith("cmd=") and cur >= 0:
					yield cur, stripped

	def _writeDreamBoot(self, defaultIdx=None, sectionUpdates=None):
		# Rewrite DREAM_BOOT_FILE; optionally set default= and rename [Section] headers via {idx: name}.
		if not exists(DREAM_BOOT_FILE):
			return
		sectionUpdates = sectionUpdates or {}
		with open(DREAM_BOOT_FILE, "r") as fd:
			lines = fd.readlines()
		out, cur = [], -1
		for line in lines:
			stripped = line.strip()
			if defaultIdx is not None and line.startswith("default="):
				line = f"default={defaultIdx}\n"
			elif stripped.startswith("[") and stripped.endswith("]"):
				cur += 1
				if cur in sectionUpdates:
					line = f"[{sectionUpdates[cur]}]\n"
			out.append(line)
		if out != lines:
			with open(DREAM_BOOT_FILE, "w") as fd:
				fd.writelines(out)


	def _getSlotNameOverride(self, slotCode, bootCode):
		slot = self.bootSlots.get(slotCode) if slotCode else None
		if not slot:
			return None
		cfg = (slot.get("bootCodes") or {}).get(bootCode) or {}
		return cfg.get("slotname")

	def getSlotName(self, slotCode, bootCode):
		# Raw user name for the rename dialog — matches what sits in SLOTNAMES on disk.
		self._reloadIfStale()
		return self._getSlotNameOverride(slotCode, bootCode)

	def getSlotDisplayName(self, slotCode, bootCode):
		# UI-facing: scanner-formatted displayname (slotname or imagename plus date), plus a
		# localisation pass for the fixed English placeholders (Recovery/Android/Empty/…).
		self._reloadIfStale()
		slot = self.bootSlots.get(slotCode) if slotCode else None
		cfg = (slot.get("bootCodes") if slot else {}).get(bootCode) or {}
		name = cfg.get("displayname") or (slot.get("imagename") if slot else "") or ""
		return {
			"Android":          _("Android"),
			"Android Linux SE": _("Android Linux SE"),
			"Recovery":         _("Recovery"),
			"Root Image":       _("Root Image"),
			"Flash":            _("Flash"),
			"Empty":            _("Empty"),
			"Disabled":         _("Disabled"),
			"Unknown":          _("Unknown"),
			"Inaccessible":     _("Inaccessible"),
		}.get(name, name)

	def canMultiBoot(self):
		self._reloadIfStale()
		if not self.bootSlots:
			return False
		if exists(DREAM_BOOT_FILE):
			if fileHas("/proc/cmdline", "root=/dev/mmcblk1p") and not exists("/dev/disk/by-label/DREAMCARD"):
				return False
		return True

	def getBootDevice(self):
		self._reloadIfStale()
		return self.bootDevice

	def getBootSlots(self):
		self._reloadIfStale()
		return self.bootSlots

	def getCurrentSlotAndBootCodes(self):
		self._reloadIfStale()
		return self.bootSlot, self.bootCode

	def getCurrentSlotCode(self):
		self._reloadIfStale()
		return self.bootSlot

	def getCurrentBootMode(self):
		self._reloadIfStale()
		return self.bootCode

	def hasRecovery(self):
		self._reloadIfStale()
		return "R" in self.bootSlots

	def getBootCodeDescription(self, bootCode=None):
		# Only meaningful for slots with more than one bootCodes entry (h7 BOXMODE).
		bootCodeDescriptions = {
			"1": _("Mode 1: Supports Kodi but PiP may not work"),
			"12": _("Mode 12: Supports PiP but Kodi may not work")
		}
		if bootCode is None:
			return bootCodeDescriptions
		return bootCodeDescriptions.get(bootCode, "")

	def getStartupFile(self, slotCode=None):
		self._reloadIfStale()
		slotCode = slotCode if slotCode in self.bootSlots else self.bootSlot
		return self.bootSlots[slotCode]["bootCodes"][self.bootCode]["startupfile"]

	def hasRootSubdir(self, slotCode=None):
		self._reloadIfStale()
		if slotCode is None:
			slotCode = slotCode if slotCode in self.bootSlots else self.bootSlot
		return "rootsubdir" in self.bootSlots[slotCode]

	def getSlotImageList(self, callback):
		self._reloadIfStale()
		callback(self.bootSlots)

	def activateSlot(self, slotCode, bootCode, callback):
		self.slotCode = slotCode
		self.bootCode = bootCode
		self.callback = callback
		self.tempDir = mkdtemp(prefix=PREFIX)
		self.console.ePopen([MOUNT, MOUNT, self.bootDevice, self.tempDir], self.bootDeviceMounted)

	def bootDeviceMounted(self, data, retVal, extraArgs):  # Part of activateSlot().
		if retVal:
			print(f"[MultiBoot] bootDeviceMounted Error {retVal}: Unable to mount boot device '{self.bootDevice}'!")
			self.callback(1)
		else:
			bootSlot = self.bootSlots[self.slotCode]
			startup = bootSlot["bootCodes"][self.bootCode]["startupfile"]
			if (fileHas("/proc/cmdline", "kexec=1") or self.bootSlots[self.slotCode].get("rootsubdir") == "rescue") and startup == STARTUP_RECOVERY:
				target = STARTUP_FILE
			else:
				target = STARTUP_ONCE if startup == STARTUP_RECOVERY else STARTUP_FILE
			if exists(DREAM_BOOT_FILE) and startup == STARTUP_RECOVERY:
				pass
			else:
				copyfile(join(self.tempDir, startup), join(self.tempDir, target))
			if exists(DUAL_BOOT_FILE):
				slot = self.slotCode if self.slotCode.isdecimal() else "0"
				with open(DUAL_BOOT_FILE, "wb") as fd:
					fd.write(pack("B", int(slot)))
			if exists(DREAM_BOOT_FILE):
				self.updateDreamBootSection(self.slotCode, setDefault=True)
			if self.debugMode:
				print(f"[MultiBoot] Installing '{startup}' as '{target}'.")
			self.console.ePopen([UMOUNT, UMOUNT, self.tempDir], self.bootDeviceUnmounted)

	def bootDeviceUnmounted(self, data, retVal, extraArgs):  # Part of activateSlot().
		if retVal:
			print(f"[MultiBoot] bootDeviceUnmounted Error {retVal}: Unable to mount boot device '{self.bootDevice}'!")
			self.callback(2)
		else:
			rmdir(self.tempDir)
			self._refreshJsonSlot(self.slotCode)
			self.callback(0)

	def clearSlotName(self, slotCode):
		if not self.bootSlots or slotCode not in self.bootSlots or not self.bootDevice:
			return
		slot = self.bootSlots[slotCode]
		removed = False
		for cfg in (slot.get("bootCodes") or {}).values():
			if cfg.pop("slotname", None) is not None:
				removed = True
		if not removed:
			return
		tempDir = mkdtemp(prefix=PREFIX)
		self.console.ePopen([MOUNT, MOUNT, self.bootDevice, tempDir])
		try:
			self._writeSlotNamesFile(join(tempDir, SLOTNAMES_FILE), "clearSlotName")
		finally:
			self.console.ePopen([UMOUNT, UMOUNT, tempDir])
			rmdir(tempDir)
		self._refreshJsonSlotNames()

	def _writeSlotNamesFile(self, path, caller):
		# Rewrite SLOTNAMES from the current in-memory bootCodes[*].slotname entries
		names = self._collectSlotNames()
		if names:
			lines = [f"{key}={names[key]}" for key in sorted(names.keys(), key=_naturalKey)]
			fileWriteLines(path, lines, source=MODULE_NAME)
		elif isfile(path):
			try:
				unlink(path)
			except OSError as err:
				print(f"[MultiBoot] {caller}: unable to remove '{path}': {err.strerror}")

	def setSlotName(self, slotCode, bootCode, name, callback):
		if not self.bootSlots or slotCode not in self.bootSlots:
			callback(1)
			return
		if not self.bootDevice:
			callback(1)
			return
		cfg = (self.bootSlots[slotCode].get("bootCodes") or {}).get(bootCode) or {}
		startupFile = cfg.get("startupfile")
		if not startupFile:
			callback(1)
			return
		self.slotCode = slotCode
		self.renameBootCode = bootCode
		self.renameStartupFile = startupFile
		self.newName = (name or "").strip()
		self.callback = callback
		self.tempDir = mkdtemp(prefix=PREFIX)
		self.console.ePopen([MOUNT, MOUNT, self.bootDevice, self.tempDir], self._setSlotNameMounted)

	def _setSlotNameMounted(self, data, retVal, extraArgs):
		if retVal:
			rmdir(self.tempDir)
			self.callback(2)
			return
		cfg = ((self.bootSlots.get(self.slotCode, {}).get("bootCodes") or {}).get(self.renameBootCode)) or {}
		if self.newName:
			cfg["slotname"] = self.newName
		else:
			cfg.pop("slotname", None)
		self._writeSlotNamesFile(join(self.tempDir, SLOTNAMES_FILE), "setSlotName")
		self.console.ePopen([UMOUNT, UMOUNT, self.tempDir], self._setSlotNameUnmounted)

	def _setSlotNameUnmounted(self, data, retVal, extraArgs):
		rmdir(self.tempDir)
		self._refreshJsonSlotNames()
		if exists(DREAM_BOOT_FILE):
			self.updateDreamBootSection(self.slotCode)
		self.callback(0 if not retVal else 3)

	def emptySlot(self, slotCode, callback):
		self.manageSlot(slotCode, callback, self.hideSlot)

	def restoreSlot(self, slotCode, callback):
		self.manageSlot(slotCode, callback, self.revealSlot)

	def manageSlot(self, slotCode, callback, method):  # Part of emptySlot() and restoreSlot().
		if self.bootSlots:
			self.slotCode = slotCode
			self.callback = callback
			self.device = self.bootSlots[self.slotCode]["device"]
			self.tempDir = mkdtemp(prefix=PREFIX)
			if self.bootSlots[self.slotCode].get("ubi", False):
				self.console.ePopen([MOUNT, MOUNT, "-t", "ubifs", self.device, self.tempDir], method)
			else:
				self.console.ePopen([MOUNT, MOUNT, self.device, self.tempDir], method)
		else:
			self.callback(1)

	def hideSlot(self, data, retVal, extraArgs):  # Part of emptySlot().
		if retVal:
			print(f"[MultiBoot] hideSlot Error {retVal}: Unable to mount slot '{self.slotCode}' ({self.device})!")
			self.callback(2)
		else:
			rootDir = self.bootSlots[self.slotCode].get("rootsubdir")
			imageDir = join(self.tempDir, rootDir) if rootDir else self.tempDir
			if self.bootSlots[self.slotCode].get("ubi", False) or fileHas("/proc/cmdline", "kexec=1"):
				try:
					if isfile(join(imageDir, "usr/bin/enigma2")):
						self.console.ePopen([REMOVE, REMOVE, "-rf", imageDir])
					mkdir(imageDir)
				except OSError as err:
					print(f"[MultiBoot] hideSlot Error {err.errno}: Unable to wipe all files in slot '{self.slotCode}' ({self.device})!  ({err.strerror})")
			else:
				enigmaFile = ""  # This is in case the first join fails.
				try:
					enigmaFile = join(imageDir, "usr/bin/enigma2")
					if isfile(enigmaFile):
						rename(enigmaFile, f"{enigmaFile}x.bin")
					enigmaFile = join(imageDir, "usr/lib/enigma.info")
					if isfile(enigmaFile):
						rename(enigmaFile, f"{enigmaFile}x")
					enigmaFile = join(imageDir, "etc")
					if isdir(enigmaFile):
						rename(enigmaFile, f"{enigmaFile}x")
				except OSError as err:
					print(f"[MultiBoot] hideSlot Error {err.errno}: Unable to hide item '{enigmaFile}' in slot '{self.slotCode}' ({self.device})!  ({err.strerror})")
			self.console.ePopen([UMOUNT, UMOUNT, self.tempDir], self.cleanUpSlot)

	def revealSlot(self, data, retVal, extraArgs):  # Part of restoreSlot().
		if retVal:
			print(f"[MultiBoot] revealSlot Error {retVal}: Unable to mount slot '{self.slotCode}' ({self.device})!")
			self.callback(2)
		else:
			rootDir = self.bootSlots[self.slotCode].get("rootsubdir")
			imageDir = join(self.tempDir, rootDir) if rootDir else self.tempDir
			enigmaFile = ""  # This is in case the first join fails.
			try:
				enigmaFile = join(imageDir, "usr/bin/enigma2")
				hiddenFile = f"{enigmaFile}x.bin"
				if isfile(hiddenFile):
					rename(hiddenFile, enigmaFile)
				enigmaFile = join(imageDir, "usr/lib/enigma.info")
				hiddenFile = f"{enigmaFile}x"
				if isfile(hiddenFile):
					rename(hiddenFile, enigmaFile)
				enigmaFile = join(imageDir, "etc")
				hiddenFile = f"{enigmaFile}x"
				if isdir(hiddenFile):
					rename(hiddenFile, enigmaFile)
			except OSError as err:
				print(f"[MultiBoot] revealSlot Error {err.errno}: Unable to reveal item '{enigmaFile}' in slot '{self.slotCode}' ({self.device})!  ({err.strerror})")
			self.console.ePopen([UMOUNT, UMOUNT, self.tempDir], self.cleanUpSlot)

	def cleanUpSlot(self, data, retVal, extraArgs):  # Part of emptySlot() and restoreSlot().
		if retVal:
			print(f"[MultiBoot] emptySlotCleanUp Error {retVal}: Unable to unmount slot '{self.slotCode}' ({self.device})!")
			self.callback(3)
		else:
			rmdir(self.tempDir)
			if exists(DREAM_BOOT_FILE):
				self.updateDreamBootSection(self.slotCode)
			self._refreshJsonSlot(self.slotCode)
			self.callback(0)

	def isFat32(self, device):
		try:
			with open(device, "rb") as fd:
				bootSector = fd.read(512)
				fsType = bootSector[82:90].decode("ascii", errors="ignore").strip()
				if fsType == "FAT32":
					return True
				else:
					return int.from_bytes(bootSector[36:40], "little") != 0
		except Exception:
			return False

	def resolveDevice(self, path):
		if islink(path):
			return realpath(path)
		else:
			return path

	def wipeChkroot(self, callback):
		self.callback = callback
		symlinkPath = "/dev/block/by-name/others"
		if exists(symlinkPath):
			realDevice = realpath(symlinkPath)
			if realDevice == "/dev/mmcblk0boot1":
				try:
					with open("/sys/block/mmcblk0boot1/force_ro", "w") as fn:
						fn.write("0")
				except Exception:
					self.callback(2)
					return
			if exists(realDevice) and exists(f"/sys/block/{basename(realDevice)}"):
				self.console.ePopen(["dd", "dd", "if=/dev/zero", f"of={realDevice}", "bs=512"], self.wipeChkrootComplete)
		else:
			self.callback(2)

	def wipeChkrootComplete(self, result, retval, extra_args=None):
		self.callback(retval)


MultiBoot = MultiBootClass()
