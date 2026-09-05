from os import chmod, remove
from os.path import exists
from re import sub
from tempfile import NamedTemporaryFile

from enigma import eTimer, gRGB

from Components.ActionMap import HelpableActionMap
from Components.config import ConfigNumber, ConfigPassword, ConfigSelection, ConfigText, ConfigYesNo, NoSave, config
from Components.Console import Console
from Components.Label import Label
from Components.NetworkManager import NetworkMountRepository, discoveryManager
from Components.Sources.List import List
from Components.Sources.StaticText import StaticText
from Screens.ChoiceBox import ChoiceBox
from Screens.MessageBox import MessageBox
from Screens.Screen import Screen, ScreenSummary
from Screens.Setup import Setup
from Tools.ServiceAction import ServiceAction

MODULE_NAME = __name__.split(".")[-1]


class NetworkMountsOverview(Screen):
	LIST_SHARE_NAME = 0
	LIST_SERVER = 1
	LIST_REMOTE_PATH = 2
	LIST_PROTOCOL = 3
	LIST_MODE = 4
	LIST_MOUNTED = 5
	LIST_ACTIVE = 6
	LIST_DESCRIPTION = 7
	LIST_DATA = 8

	skin = """
	<screen name="NetworkMountsOverview" title="Network Mounts Overview" position="center,center" size="970,370" resolution="1280,720">
		<widget source="mountList" render="Listbox" position="10,10" size="e-20,e-70">
			<templates>
				<template name="Default" fonts="Regular;22,Regular;17" itemHeight="50">
					<mode name="default">
						<text index="ShareName" position="0,0" size="550,27" font="0" padding="5,0" verticalAlignment="center" />
						<text index="Description" position="20,27" size="530,23" font="1" padding="5,0" foregroundColor="gray" verticalAlignment="center" />
						<text index="Mounted" position="550,0" size="150,50" font="0" padding="5,0" verticalAlignment="center" />
						<text index="Active" position="700,0" size="150,50" font="0" horizontalAlignment="right" padding="5,0" verticalAlignment="center" />
					</mode>
				</template>
			</templates>
		</widget>
		<widget source="key_red" render="Label" position="10,e-50" size="180,40" backgroundColor="key_red" font="Regular;20" foregroundColor="key_text" horizontalAlignment="center" wrap="off" verticalAlignment="center">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="key_green" render="Label" position="200,e-50" size="180,40" backgroundColor="key_green" font="Regular;20" foregroundColor="key_text" horizontalAlignment="center" wrap="off" verticalAlignment="center">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="key_yellow" render="Label" position="390,e-50" size="180,40" backgroundColor="key_yellow" font="Regular;20" foregroundColor="key_text" horizontalAlignment="center" wrap="off" verticalAlignment="center">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="key_menu" render="Label" position="e-200,e-50" size="90,40" backgroundColor="key_back" font="Regular;20" foregroundColor="key_text" horizontalAlignment="center" wrap="off" verticalAlignment="center">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="key_help" render="Label" position="e-100,e-50" size="90,40" backgroundColor="key_back" font="Regular;20" foregroundColor="key_text" horizontalAlignment="center" wrap="off" verticalAlignment="center">
			<convert type="ConditionalShowHide" />
		</widget>
	</screen>"""

	MOUNT = "/bin/mount"
	UMOUNT = "/bin/umount"

	def __init__(self, session, openBrowser=False):
		Screen.__init__(self, session, enableHelp=True)
		self.setTitle(_("Network Mounts Overview"))
		indexNames = {
			"ShareName": self.LIST_SHARE_NAME,
			"Server": self.LIST_SERVER,
			"RemotePath": self.LIST_REMOTE_PATH,
			"Protocol": self.LIST_PROTOCOL,
			"Mode": self.LIST_MODE,
			"Mounted": self.LIST_MOUNTED,
			"Active": self.LIST_ACTIVE,
			"Description": self.LIST_DESCRIPTION
		}
		self["mountList"] = List([], indexNames=indexNames)
		self["mountList"].onSelectionChanged.append(self.selectionChanged)
		self["key_red"] = StaticText(_("Close"))
		self["key_green"] = StaticText(_("Browse"))
		self["key_yellow"] = StaticText("")
		self["key_menu"] = StaticText("MENU")
		self["actions"] = HelpableActionMap(self, ["OkCancelActions", "MenuActions", "ColorActions"], {
			"ok": (self.keyEdit, _("Edit the selected network mount")),
			"cancel": (self.close, _("Close the screen")),
			"close": (self.keyCloseRecursive, _("Close the screen and exit all menus")),
			"menu": (self.keyMenu, _("Open the Mount Context Menu")),
			"red": (self.close, _("Close the screen")),
			"green": (self.keyGreen, _("Open the Network Shares Browser")),
			"yellow": (self.keyYellow, _("Mount or unmount the selected share")),
		}, prio=0, description=_("Network Mount Manager Actions"))
		self.repository = NetworkMountRepository()
		self.console = Console()
		self.onChangedEntry = []
		self.buildList()
		self.onShown.append(self.selectionChanged)
		self.savedMount = None
		self.transient = openBrowser
		if openBrowser:
			self.onFirstExecBegin.append(self.keyGreen)
		self.onClose.append(self.console.killAll)

	def selectionChanged(self):
		current = self["mountList"].getCurrent()
		yellowText = ""
		if current:
			shareName = current[self.LIST_SHARE_NAME]
			description = current[self.LIST_DESCRIPTION]
			mount = current[self.LIST_DATA]
			if mount.get("mode") != "autofs":
				yellowText = _("Unmount") if self.repository.isMounted(mount) else _("Mount")
		else:
			shareName = ""
			description = ""
		self["key_yellow"].setText(yellowText)
		self["actions"].setEnabledAction("yellow", yellowText != "")
		for callback in self.onChangedEntry:
			if callable(callback):
				callback(shareName, description)

	def buildList(self):
		def sortKeyByMountName(mount):
			return (mount.get("shareName") or mount.get("id") or "").casefold()

		def sortKeyByHostname(mount):
			server = mount.get("server") or ""
			name = discoveryManager.hosts.get(server, {}).get("hostname") or server
			octets = name.split(".")
			return (0, ".".join(f"{x:0>3}" for x in octets)) if len(octets) == 4 and all(x.isdigit() or x == "." for x in name) else (1, name.casefold())

		self.mounts = sorted(self.repository.load(), key=sortKeyByMountName if config.network.mountsSortByMount.value else sortKeyByHostname)
		mountList = []
		for mount in self.mounts:
			shareName = mount.get("shareName") or mount.get("id")
			server = mount.get("server", "")
			remotePath = mount.get("remotePath", "")
			protocol = mount.get("protocol", "")
			mode = mount.get("mode", "")
			mounted = f"{_("Mounted") if self.repository.isMounted(mount) else _("Not mounted")}"
			active = f"{_("Enabled") if mount.get("enabled") else _("Disabled")}"
			description = f"{server}/{remotePath}  ({protocol}, {mode})" if server or remotePath else f"({protocol}, {mode})"
			mountList.append((shareName, server, remotePath, protocol, mode, mounted, active, description, mount))
		self["mountList"].setList(mountList)

	def keyEdit(self):
		current = self["mountList"].getCurrent()
		if current:
			self.session.openWithCallback(self.keySetupClosed, NetworkMountSetup, mount=current[self.LIST_DATA], onSaved=self.mountSaved)

	def keySetupClosed(self, *args):
		saved, self.savedMount = self.savedMount, None
		if args and args[0] is True:
			self.close(True)
			return
		self.buildList()
		self.applyMountChange(saved)

	def applyMountChange(self, mount):
		def autofsRestarted(exitCode):
			if exitCode:
				print(f"[{MODULE_NAME}] applyMountChange Error: The autofs restart failed, exitCode='{exitCode}'!")

		def mountAllDone(data, retVal, extra=None):
			if retVal:
				print(f"[{MODULE_NAME}] applyMountChange Error: The 'mount -a' failed, retVal='{retVal}', output='{data!r}'!")

		if mount and mount.get("enabled"):
			if mount.get("mode") == "autofs":
				ServiceAction("autofs").restart(autofsRestarted)
			else:
				self.console.ePopen((self.MOUNT, self.MOUNT, "-a"), mountAllDone)

	def mountSaved(self, mount):
		self.savedMount = mount

	def keyCloseRecursive(self):
		self.close(True)

	def keyMenu(self):
		def keyMenuCallback(choice=None):
			if choice:
				match choice[1]:
					case "manual":
						self.session.openWithCallback(self.keySetupClosed, NetworkMountSetup, mount=None, onSaved=self.mountSaved)
					case "delete":
						deleteMount()
					case "edit_credentials":
						editCredentials()
					case "remove_credentials":
						removeCredentials()
					case "toggle_sort":
						toggleSort()

		def deleteMount():
			def autofsRestarted(exitCode):
				if exitCode:
					print(f"[{MODULE_NAME}] deleteMount Error: The autofs restart failed, exitCode='{exitCode}'!")

			def mountAllDone(data, retVal, extra=None):
				if retVal:
					print(f"[{MODULE_NAME}] deleteMount Error: The 'mount -a' failed, retVal='{retVal}', output='{data!r}'!")

			def deleteMountCallback(answer):
				if answer:
					self.mounts = [x for x in self.mounts if x is not mount]
					self.repository.save(self.mounts)
					if mount.get("mode") == "autofs":
						ServiceAction("autofs").restart(autofsRestarted)
					else:
						self.console.ePopen((self.MOUNT, self.MOUNT, "-a"), mountAllDone)
					self.buildList()

			mount = current[self.LIST_DATA]
			name = mount.get("shareName") or mount.get("id")
			self.session.openWithCallback(deleteMountCallback, MessageBox, _("Confirm the deletion of '%s'?") % name, MessageBox.TYPE_YESNO, default=False, windowTitle=self.getTitle())

		def editCredentials():
			mount = current[self.LIST_DATA]
			self.session.open(NetworkCredentials, mount.get("server") or "", self.repository)

		def removeCredentials():
			mount = current[self.LIST_DATA]
			self.repository.credentialsClear(mount.get("server") or "")
			self.session.showInfo(_("Stored credentials deleted for this server."))

		def toggleSort():
			config.network.mountsSortByMount.value = not config.network.mountsSortByMount.value
			config.network.mountsSortByMount.save()
			self.buildList()

		choices = [(_("Add Mount Manually"), "manual")]
		current = self["mountList"].getCurrent()
		if current:
			mount = current[self.LIST_DATA]
			if not mount.get("hddReplacement"):
				choices.append((_("Delete Mount"), "delete"))
			choices.append((_("Edit Credentials"), "edit_credentials"))
			choices.append((_("Remove Credentials"), "remove_credentials"))
		choices.append((_("Sort by Hostname/IP Address") if config.network.mountsSortByMount.value else _("Sort by Mount Name"), "toggle_sort"))
		self.session.openWithCallback(keyMenuCallback, ChoiceBox, title=_("Mount Context Menu"), list=choices)

	def keyGreen(self):
		def keyGreenCallback(saved=None):
			if isinstance(saved, bool) and saved:
				self.close(True)
				return
			if saved:
				self.transient = False
				self.buildList()
				self.applyMountChange(saved)
			elif self.transient:
				self.close()
			else:
				self.buildList()

		self.session.openWithCallback(keyGreenCallback, NetworkShares)

	def keyYellow(self):
		def onMountResult(unmounting, data, retVal, extra=None):
			action = "umount" if unmounting else "mount"
			print(f"[{MODULE_NAME}] keyYellow: {action.capitalize()} '{mountPoint!r}' finished, retVal='{retVal}', output='{data!r}'.")
			if retVal:
				self.session.showError((_("Error: Unmounting '%s' failed!") if unmounting else _("Error: Mounting '%s' failed!")) % mountPoint)
			else:
				self.session.showInfo((_("'%s' unmounted.") if unmounting else _("'%s' mounted.")) % mountPoint)
			self.buildList()
			self.selectionChanged()

		current = self["mountList"].getCurrent()
		if current:
			mount = current[self.LIST_DATA]
			mountPoint = self.repository.mountPointFor(mount)
			if self.repository.isMounted(mount):
				print(f"[{MODULE_NAME}] keyYellow: Unmounting '{mountPoint!r}'.")
				self.console.ePopen((self.UMOUNT, self.UMOUNT, "-l", mountPoint), lambda data, retVal, extra=None: onMountResult(True, data, retVal, extra))
			else:
				argv, mountPoint = self.repository.buildMountCommand(mount)
				loggedArgv = sub(r"pass=[^,]*", "pass=***", " ".join(argv))
				print(f"[{MODULE_NAME}] keyYellow: Mounting '{loggedArgv!r}'.")
				self.console.ePopen(argv, lambda data, retVal, extra=None: onMountResult(False, data, retVal, extra))

	def createSummary(self):
		return NetworkMountsSummary


class NetworkMountsSummary(ScreenSummary):
	def __init__(self, session, parent):
		ScreenSummary.__init__(self, session, parent=parent)
		self.skinName = "SetupSummary"
		self["entry"] = StaticText("")
		self["value"] = StaticText("")
		self.onShow.append(self.addWatcher)
		self.onHide.append(self.removeWatcher)

	def addWatcher(self):
		self.parent.onChangedEntry.append(self.selectionChanged)
		self.parent.selectionChanged()

	def removeWatcher(self):
		self.parent.onChangedEntry.remove(self.selectionChanged)

	def selectionChanged(self, shareName, description):
		self["entry"].text = shareName
		self["value"].text = description


class NetworkMountSetup(Setup):
	def __init__(self, session, mount=None, onSaved=None):
		def default(key, default=""):
			return mount.get(key, default) if mount else default

		self.onSaved = onSaved
		self.repository = NetworkMountRepository()
		self.mountId = mount.get("id") if mount else None
		self.enabled = NoSave(ConfigYesNo(default=default("enabled", True)))
		self.protocol = NoSave(ConfigSelection(default=default("protocol", "cifs") or "cifs", choices=[
			("cifs", "SMB / CIFS"),
			("nfs", "NFS")
		]))
		self.server = NoSave(ConfigText(default=default("server"), fixed_size=False))
		self.remotePath = NoSave(ConfigText(default=default("remotePath"), fixed_size=False))
		self.mode = NoSave(ConfigSelection(default=default("mode", "autofs") or "autofs", choices=[
			("autofs", _("Mount on first access (autofs)")),
			("fstab", _("Mount at boot time (fstab)"))
		]))
		self.username = NoSave(ConfigText(default=default("username"), fixed_size=False))
		self.password = NoSave(ConfigPassword(default=default("password")))
		self.smbVersion = NoSave(ConfigSelection(default=default("smbVersion", "3.0") or "3.0", choices=[
			("3.0", "SMB3"),
			("2.0", "SMB2"),
			("1.0", _("Legacy (SMB1)"))
		]))
		self.smbCharset = NoSave(ConfigSelection(default=default("smbCharset", "utf8") or "utf8", choices=[
			("utf8", "UTF-8"),
			("iso8859-1", "ISO8859-1"),
			("iso8859-15", "ISO8859-15"),
			("cp1252", "CP1252"),
			("cp850", "CP850")
		]))
		self.shareName = NoSave(ConfigText(default=default("shareName"), fixed_size=False))
		self.accessMode = NoSave(ConfigSelection(default=default("accessMode", "rw") or "rw", choices=[
			("rw", _("Read/Write")),
			("ro", _("Read-Only"))
		]))
		self.options = NoSave(ConfigText(default=default("options"), fixed_size=False))
		self.nfsVersion = NoSave(ConfigSelection(default=default("nfsVersion", "auto") or "auto", choices=[
			("auto", _("Automatic")),
			("3", "NFSv3"),
			("4", "NFSv4")
		]))
		self.nfsLocking = NoSave(ConfigYesNo(default=default("nfsLocking", True)))
		nfsSizeChoices = [("0", _("Automatic")), ("8192", "8192"), ("32768", "32768"), ("65536", "65536"), ("131072", "131072")]
		self.nfsRsize = NoSave(ConfigSelection(default=str(default("nfsRsize", "0")) or "0", choices=nfsSizeChoices))
		self.nfsWsize = NoSave(ConfigSelection(default=str(default("nfsWsize", "0")) or "0", choices=nfsSizeChoices))
		self.nfsTimeo = NoSave(ConfigNumber(default=int(default("nfsTimeo", 0) or 0)))
		self.nfsSoft = NoSave(ConfigYesNo(default=default("nfsSoft", False)))
		self.hddReplacement = NoSave(ConfigYesNo(default=default("hddReplacement", False)))
		Setup.__init__(self, session=session, setup="NetworkMounts")
		self.setTitle(_("Network Mount Settings"))

	def keySave(self):
		server = self.server.value.strip()
		remotePath = self.remotePath.value.strip().lstrip("/")
		if not server or not remotePath:
			self.session.open(MessageBox, _("Error: Both 'server' and 'remote path' are required!"), MessageBox.TYPE_ERROR, timeout=5, windowTitle=self.getTitle())
			return
		options = self.options.value.strip()
		optionsError = self.repository.validateExtraOptions(options, self.protocol.value)
		if optionsError:
			self.session.open(MessageBox, optionsError, MessageBox.TYPE_ERROR, timeout=5, windowTitle=self.getTitle())
			return
		shareName = self.shareName.value.strip() or sub(r"\W", "", server)
		mount = {
			"id": self.mountId or self.repository.newId(),
			"enabled": self.enabled.value,
			"shareName": shareName,
			"server": server,
			"remotePath": remotePath,
			"protocol": self.protocol.value,
			"mode": self.mode.value,
			"options": options,
			"username": self.username.value if self.protocol.value == "cifs" else "",
			"password": self.password.value if self.protocol.value == "cifs" else "",
			"smbVersion": self.smbVersion.value if self.protocol.value == "cifs" else "",
			"smbCharset": self.smbCharset.value if self.protocol.value == "cifs" else "",
			"accessMode": self.accessMode.value,
			"nfsVersion": self.nfsVersion.value if self.protocol.value == "nfs" else "",
			"nfsLocking": self.nfsLocking.value if self.protocol.value == "nfs" else True,
			"nfsRsize": self.nfsRsize.value if self.protocol.value == "nfs" else "",
			"nfsWsize": self.nfsWsize.value if self.protocol.value == "nfs" else "",
			"nfsTimeo": self.nfsTimeo.value if self.protocol.value == "nfs" else "",
			"nfsSoft": self.nfsSoft.value if self.protocol.value == "nfs" else False,
			"hddReplacement": self.hddReplacement.value,
		}
		mounts = [x for x in self.repository.load() if x.get("id") != mount["id"]]
		mounts.append(mount)
		self.repository.save(mounts)
		if self.enabled.value and self.mode.value == "fstab":
			self.repository.ensureMountPoint(mount)
		if self.onSaved:
			self.onSaved(mount)
		Setup.keySave(self)


class NetworkShares(Screen):
	skin = """
	<screen name="NetworkShares" title="Network Shares Browser" position="center,center" size="1100,505" resolution="1280,720">
		<widget source="list" render="Listbox" position="10,10" size="e-20,e-105">
			<template name="Default" fonts="enigma2icons;40,Regular;25,enigma2icons;25,Regular;20" itemHeight="50">
				<rowtemplate>
					<text index="Glyph" position="0,0" size="50,50" font="0" horizontalAlignment="center" padding="5,0" verticalAlignment="center" />
					<text index="IPAddress" position="60,0" size="220,50" font="1" padding="5,0" verticalAlignment="center" />
					<text index="Name" position="280,0" size="550,50" font="1" padding="5,0" verticalAlignment="center" />
					<text index="Username" position="830,0" size="250,50" font="1" padding="5,0" verticalAlignment="center" />
				</rowtemplate>
				<rowtemplate>
					<text index="Glyph" position="60,0" size="40,50" font="2" foregroundColor="+GlyphColor" horizontalAlignment="center" padding="5,0" verticalAlignment="center" />
					<text index="Type" position="100,0" size="80,50" font="3" foregroundColor="gray" padding="5,0" verticalAlignment="center" />
					<text index="Name" position="180,0" size="230,50" font="3" padding="5,0" verticalAlignment="center" />
					<text index="Description" position="410,0" size="670,25" font="3" padding="5,0" verticalAlignment="center" />
					<text index="LocalPath" position="430,25" size="650,25" font="3" foregroundColor="gray" padding="5,0" verticalAlignment="center" />
				</rowtemplate>
			</template>
		</widget>
		<widget name="description" position="10,e-85" size="e-20,25" font="Regular;20" padding="5,0" verticalAlignment="center" widgetBorderColor="gray" widgetBorderWidth="1" />
		<widget source="key_red" render="Label" position="10,e-50" size="180,40" backgroundColor="key_red" font="Regular;20" foregroundColor="key_text" horizontalAlignment="center" wrap="off" verticalAlignment="center">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="key_green" render="Label" position="200,e-50" size="180,40" backgroundColor="key_green" font="Regular;20" foregroundColor="key_text" horizontalAlignment="center" wrap="off" verticalAlignment="center">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="key_yellow" render="Label" position="390,e-50" size="180,40" backgroundColor="key_yellow" font="Regular;20" foregroundColor="key_text" horizontalAlignment="center" wrap="off" verticalAlignment="center">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="key_blue" render="Label" position="580,e-50" size="180,40" backgroundColor="key_blue" font="Regular;20" foregroundColor="key_text" horizontalAlignment="center" wrap="off" verticalAlignment="center">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="key_menu" render="Label" position="e-200,e-50" size="90,40" backgroundColor="key_back" font="Regular;20" foregroundColor="key_text" horizontalAlignment="center" wrap="off" verticalAlignment="center">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="key_help" render="Label" position="e-100,e-50" size="90,40" backgroundColor="key_back" font="Regular;20" foregroundColor="key_text" horizontalAlignment="center" wrap="off" verticalAlignment="center">
			<convert type="ConditionalShowHide" />
		</widget>
	</screen>"""

	GLYPH_HOST = "\uEA6D"  # Host icon.
	GLYPH_MOUNTED = "\uE914"  # Green checkmark.
	GLYPH_NOT_MOUNTED = "\uE918"  # Red cross.
	COLOR_MOUNTED = gRGB(0x0000CC00).argb()
	COLOR_NOT_MOUNTED = gRGB(0x00808080).argb()  # Gray, not red - "not configured yet" isn't an error.
	TEMPLATE_HOST = 0
	TEMPLATE_SHARE = 1

	REFRESH_DEBOUNCE_MS = 300  # Coalesce bursts of discovery updates into one list rebuild instead of redrawing on every single one.
	NFS_SHOWMOUNT_BIN = "/usr/sbin/showmount"
	SMB_SMBCLIENT_BIN = "/usr/bin/smbclient"
	SMB_DIALECTS = (("SMB3", "3.0"), ("SMB2", "2.0"), ("NT1", "1.0"))
	SMB_FALLBACK_VERSION = "3.0"

	def __init__(self, session):
		Screen.__init__(self, session, enableHelp=True)
		self.setTitle(_("Network Shares Browser"))
		# Index 0 is reserved for the row template selector (which of the two
		# row layouts below to use), not a real data field.
		indexNames = {
			"Reserved_for_rowTemplate": 0,
			"Glyph": 1,         # Host row: host glyph; share row: mounted/not-mounted glyph.
			"GlyphColor": 2,    # Share row only.
			"IPAddress": 3,     # Host row only.
			"Type": 4,          # Share row only: "NFS"/"CIFS".
			"Name": 5,          # Host row: hostname; share row: share name.
			"LocalPath": 6,     # Share row only, when already configured.
			"Description": 7,   # Share row only, e.g. the SMB share comment.
			"Username": 8,      # Host row only, e.g. "(guest)" - kept separate from Name so skins can position it independently.
			"NameUsername": 9,  # Host row only: "Name (Username)" combined in one field, for skins that don't split them.
			"Data": 10,
		}
		self["list"] = List([], indexNames=indexNames)
		self["list"].onSelectionChanged.append(self.selectionChanged)
		self["description"] = Label()
		self["key_red"] = StaticText(_("Close"))
		self["key_green"] = StaticText(_("Credentials"))
		self["key_yellow"] = StaticText(_("Rescan"))
		self["key_blue"] = StaticText("")
		self["key_menu"] = StaticText(_("MENU"))
		self["actions"] = HelpableActionMap(self, ["OkCancelActions", "MenuActions", "ColorActions"], {
			"ok": (self.keySelect, _("Expand/collapse the selected host, or use the selected share")),
			"cancel": (self.close, _("Close the screen")),
			"close": (self.keyCloseRecursive, _("Close the screen and exit all menus")),
			"menu": (self.keyMenu, _("Open the Network Shares Context Menu")),
			"red": (self.close, _("Close the screen")),
			"green": (self.keyGreen, _("Edit stored username/password credentials for the selected host")),
			"yellow": (self.keyRescan, _("Rescan for available network shares")),
			"blue": (self.keyToggleUsingIP, _("Toggle picking a share by IP address or by DNS name")),
		}, prio=0, description=_("Network Share Actions"))
		self.expanded = set()
		self.shares = {}  # address -> [share dict, ...].
		self.shareState = {}  # address -> "loading" | "done" | "empty".
		self.pendingProtocols = {}  # address -> {"nfs", "smb"} remaining.
		self.smbVersions = {}  # address -> negotiated dialect as a mount "vers=" value.
		self.smbGuestCallback = {}  # address -> one-shot callback run once the guest SMB probe below finishes.
		self.savedMount = None
		self.configuredMounts = {}  # (server, remotePath) -> mount, for shares that are already configured.
		self.repository = NetworkMountRepository()
		self.menuAddress = None
		self.menuHostname = None
		self.console = Console()
		self.refreshTimer = eTimer()
		self.refreshTimer.callback.append(self.buildList)
		self.onShow.append(self.startDiscovery)
		self.onClose.append(self.stopDiscovery)

	def selectionChanged(self):
		current = self["list"].getCurrent()
		isHost = bool(current) and current[-1].get("kind") == "host"
		greenText = _("Credentials") if isHost else ""
		self["key_green"].setText(greenText)
		self["actions"].setEnabledAction("green", greenText != "")
		blueText = ""
		if current:
			address = current[-1].get("address")
			if address and (discoveryManager.hosts.get(address) or {}).get("hostname"):
				blueText = _("Using IP") if config.network.browserUsingIP.value else _("Using DNS")
		self["key_blue"].setText(blueText)
		self["actions"].setEnabledAction("blue", blueText != "")

	def buildList(self):
		def sortKeyByIP(host):
			return (not host["protocols"], ".".join(f"{x:0>3}" for x in host["address"].split(".")))

		def sortKeyByName(host):
			return (not host["protocols"], (host["hostname"] or host["address"]).lower())

		if "list" in self:
			entries = []
			protocolLabels = {
				"smb": "SMB",
				"nfs": "NFS"
			}
			hosts = {}
			for host in discoveryManager.hosts.values():
				key = (host["hostname"] or host["address"], ":" in host["address"])
				known = hosts.get(key)
				if known is None or host["address"] < known["address"]:
					hosts[key] = host
			for host in sorted(hosts.values(), key=sortKeyByIP if config.network.browserSortByIP.value else sortKeyByName):
				address = host["address"]
				name = host["hostname"] or address
				username, password = self.repository.credentialsGet(self.hostnameFor(address))
				if username is None or username == NetworkCredentials.GUEST_USERNAME:
					username = NetworkCredentials.GUEST_TRANSLATED:
				entries.append((self.TEMPLATE_HOST, self.GLYPH_HOST, 0, address, "", name, "", "", username, f"{name} ({username})", {"kind": "host", "address": address}))
				if address not in self.expanded:
					continue
				state = self.shareState.get(address)
				if state == "loading":
					entries.append((self.TEMPLATE_SHARE, "", 0, "", "", _("Scanning for shares..."), "", "", "", "", {"kind": "status"}))
				elif state == "empty":
					entries.append((self.TEMPLATE_SHARE, "", 0, "", "", _("No shares found."), "", "", "", "", {"kind": "status"}))
				for share in self.shares.get(address, []):
					typeLabel = protocolLabels.get(share["protocol"], share["protocol"])
					if share["protocol"] == "smb":
						version = self.smbVersions.get(address)
						if version:
							typeLabel = f"SMB{version.split(".")[0]}"
					existing = self.configuredMount(address, host["hostname"], share["path"])
					localPath = self.repository.mountPointFor(existing) if existing else None
					glyph = self.GLYPH_MOUNTED if localPath else self.GLYPH_NOT_MOUNTED
					glyphColor = self.COLOR_MOUNTED if localPath else self.COLOR_NOT_MOUNTED
					entries.append((self.TEMPLATE_SHARE, glyph, glyphColor, "", typeLabel, share["name"], localPath or "", share.get("description") or "", "", "", dict(share, kind="share")))
			self["list"].setList(entries)
			count = len(discoveryManager.hosts)
			self["description"].setText((ngettext("%d host found.", "%d hosts found.", count) % count) if count else _("No hosts found yet - still scanning..."))
			self.selectionChanged()

	def hostnameFor(self, address):
		host = discoveryManager.hosts.get(address) or {}
		return host.get("hostname") or address

	def configuredMount(self, address, hostname, remotePath):
		path = remotePath.lstrip("/")
		return self.configuredMounts.get((address, path)) or (self.configuredMounts.get((hostname, path)) if hostname else None)

	# Discovery only runs while this screen is open, so it stops as soon as
	# the user leaves instead of scanning the network in the background.
	def startDiscovery(self):
		self.configuredMounts = {(mount.get("server"), (mount.get("remotePath") or "").lstrip("/")): mount for mount in self.repository.load()}
		if self.onHostsChanged not in discoveryManager.onChanged:
			discoveryManager.onChanged.append(self.onHostsChanged)
		discoveryManager.start(runMs=None)
		self["description"].setText(_("Scanning..."))
		self.buildList()

	def onHostsChanged(self):
		if "list" in self and not self.refreshTimer.isActive():
			self.refreshTimer.start(self.REFRESH_DEBOUNCE_MS, True)

	def stopDiscovery(self):
		self.refreshTimer.stop()
		try:
			discoveryManager.onChanged.remove(self.onHostsChanged)
		except ValueError:
			pass
		discoveryManager.stop()
		self.console.killAll()

	def keySelect(self):
		current = self["list"].getCurrent()
		if current:
			data = current[-1]
			match data["kind"]:
				case "host":
					self.toggleExpand(data["address"])
				case "share":
					self.pickShare(data)

	def toggleExpand(self, address):
		def onGuestSmbDone(address, hostname):
			if address not in self.expanded:
				return
			if any(share["protocol"] == "smb" for share in self.shares.get(address, [])):
				return
			self.session.openWithCallback(lambda *args: self.startShareEnumeration(address), NetworkCredentials, hostname, self.repository)

		if address in self.expanded:
			self.expanded.discard(address)
			self.buildList()
			return
		self.expanded.add(address)
		self.buildList()
		hostname = self.hostnameFor(address)
		username, password = self.repository.credentialsGet(hostname)
		if username:
			self.startShareEnumeration(address)
			return
		host = discoveryManager.hosts.get(address) or {}
		if "smb" in host.get("protocols", set()):
			self.smbGuestCallback[address] = lambda: onGuestSmbDone(address, hostname)
		self.startShareEnumeration(address)

	def startShareEnumeration(self, address):
		if self.shareState.get(address) == "loading":
			return
		self.shareState[address] = "loading"
		host = discoveryManager.hosts.get(address) or {}
		# print(f"[{MODULE_NAME}] DEBUG: startShareEnumeration '{address}' protocols='{host.get("protocols")}' avahiShares='{host.get("avahiShares")}'.")
		self.shares[address] = [{
			"address": address,
			"protocol": info["protocol"],
			"name": info["name"],
			"path": "",
			"description": ""
		} for info in (host.get("avahiShares") or {}).values()]
		self.pendingProtocols[address] = {"nfs", "smb"}
		if "nfs" in host.get("protocols", set()):
			self.enumerateNfs(address)
		else:
			self.finishProtocol(address, "nfs")
		if "smb" in host.get("protocols", set()):
			self.enumerateSmb(address)
		else:
			self.finishProtocol(address, "smb")

	def finishProtocol(self, address, protocol):
		if "list" in self:
			self.shares[address] = [share for share in self.shares.get(address, []) if not (share["protocol"] == protocol and not share["path"])]
			pending = self.pendingProtocols.get(address)
			if pending is not None:
				pending.discard(protocol)
				if not pending:
					self.shareState[address] = "done" if self.shares.get(address) else "empty"
			self.buildList()
			if protocol == "smb":
				callback = self.smbGuestCallback.pop(address, None)
				if callback:
					callback()

	def enumerateNfs(self, address):
		def nfsCallback(address, data, retVal):
			if "list" in self:
				if retVal == 0 and data:
					for line in data.splitlines()[1:]:
						parts = line.split()
						if not parts:
							continue
						path = parts[0]
						name = path.rsplit("/", 1)[-1] or path
						self.mergeShare(address, "nfs", name, path, "")
				self.finishProtocol(address, "nfs")

		if not exists(self.NFS_SHOWMOUNT_BIN):
			self.finishProtocol(address, "nfs")
			return
		self.console.ePopen((self.NFS_SHOWMOUNT_BIN, self.NFS_SHOWMOUNT_BIN, "-e", address), callback=lambda data, retVal, extra=None: nfsCallback(address, data, retVal))

	def mergeShare(self, address, protocol, name, path, description):
		shares = self.shares.setdefault(address, [])
		for share in shares:
			if share["protocol"] == protocol and not share["path"] and share["name"].lower() == name.lower():
				share["path"] = path
				share["description"] = description or share["description"]
				return
		shares.append({
			"address": address,
			"protocol": protocol,
			"name": name,
			"path": path,
			"description": description
		})

	def enumerateSmb(self, address, step=0):
		def smbCallback(address, step, data, retVal, credentialPath=None):
			if credentialPath:
				try:
					remove(credentialPath)
				except OSError:
					pass
			if "list" in self:
				data = data or ""
				if retVal and not data.strip():
					self.finishProtocol(address, "smb")
					return
				if self.smbNegotiateRejected(data):
					self.enumerateSmb(address, step + 1)
					return
				self.smbVersions[address] = self.SMB_DIALECTS[step][1]
				for line in data.splitlines():
					parts = line.split("|")
					if len(parts) == 3 and parts[0] == "Disk" and not parts[1].endswith("$"):
						self.mergeShare(address, "smb", parts[1], parts[1], parts[2])
				self.finishProtocol(address, "smb")

		if not exists(self.SMB_SMBCLIENT_BIN) or step >= len(self.SMB_DIALECTS):
			self.finishProtocol(address, "smb")
			return
		dialect = self.SMB_DIALECTS[step][0]
		username, password = self.repository.credentialsGet(self.hostnameFor(address))
		credentialFile = None
		if username and username != NetworkCredentials.GUEST_USERNAME:
			credentialFile = NamedTemporaryFile(mode="w", prefix="smbcreds-", delete=False)
			credentialFile.write(f"username={username}\npassword={password}\n")
			credentialFile.close()
			chmod(credentialFile.name, 0o600)
			authArgs = ("-A", credentialFile.name)
		else:
			authArgs = ("-N",)
		cmd = (self.SMB_SMBCLIENT_BIN, self.SMB_SMBCLIENT_BIN, f"--option=clientminprotocol={dialect}", "-m", dialect, "-g", *authArgs, "-L", address)
		credentialPath = credentialFile.name if credentialFile else None
		self.console.ePopen(cmd, callback=lambda data, retVal, extra=None: smbCallback(address, step, data, retVal, credentialPath))

	@staticmethod
	def smbNegotiateRejected(data):
		return "Protocol negotiation" in data and "failed" in data

	def pickShare(self, share):
		def mountSetupCallback(*args):
			saved = self.savedMount
			self.savedMount = None
			if args and args[0] is True:
				self.close(True)
				return
			if saved:
				self.close(saved)
			else:
				self.buildList()

		host = discoveryManager.hosts.get(share["address"]) or {}
		hostname = host.get("hostname") or ""
		existing = self.configuredMount(share["address"], hostname, share["path"])
		if existing:
			self.session.openWithCallback(mountSetupCallback, NetworkMountSetup, mount=existing, onSaved=self.mountSaved)
			return
		server = hostname if (hostname and not config.network.browserUsingIP.value) else share["address"]
		mount = {
			"server": server,
			"protocol": {
				"smb": "cifs",
				"nfs": "nfs"
			}.get(share["protocol"], share["protocol"]),
			"remotePath": share["path"].lstrip("/"),
			"shareName": share["name"],
		}
		if share["protocol"] == "smb":
			mount["smbVersion"] = self.smbVersions.get(share["address"], self.SMB_FALLBACK_VERSION)
			username, password = self.repository.credentialsGet(self.hostnameFor(share["address"]))
			if username is None:
				username = NetworkCredentials.GUEST_USERNAME
			if username and username != NetworkCredentials.GUEST_USERNAME:
				mount["username"] = username
				mount["password"] = password
		self.session.openWithCallback(mountSetupCallback, NetworkMountSetup, mount=mount, onSaved=self.mountSaved)

	def mountSaved(self, mount):
		self.savedMount = mount

	def keyCloseRecursive(self):
		self.close(True)

	def keyMenu(self):
		def keyMenuCallback(self, choice=None):
			def flushNeighborCache():
				def flushDone(data, retVal, extra=None):
					if retVal:
						print(f"[{MODULE_NAME}] Error: flushNeighborCache failed, retVal='{retVal}', output='{data!r}'!")
					self.keyRescan()

				self.console.ePopen(("/sbin/ip", "/sbin/ip", "neigh", "flush", "all"), flushDone)

			if choice:
				match choice[1]:
					case "credentials":
						self.session.openWithCallback(self.credentialsClosed, NetworkCredentials, self.menuHostname, self.repository)
					case "flush_neigh":
						flushNeighborCache()
					case "clear_credentials":
						self.repository.credentialsClear(self.menuHostname)
						self.session.open(MessageBox, _("Stored credentials for this server have been deleted."), MessageBox.TYPE_INFO, timeout=3)
					case "toggle_sort":
						config.network.browserSortByIP.value = not config.network.browserSortByIP.value
						config.network.browserSortByIP.save()
						self.buildList()

		current = self["list"].getCurrent()
		isHost = bool(current) and current[-1].get("kind") == "host"
		choices = []
		if isHost:
			self.menuAddress = current[-1]["address"]
			self.menuHostname = self.hostnameFor(self.menuAddress)
			choices.append((_("Edit Username/Password Credentials"), "credentials"))
			choices.append((_("Clear Stored Credentials"), "clear_credentials"))
		else:
			self.menuAddress = None
			self.menuHostname = None
		choices.append((_("Flush Cache and Rescan"), "flush_neigh"))
		choices.append((_("Sort by Name") if config.network.browserSortByIP.value else _("Sort by IP Address"), "toggle_sort"))
		self.session.openWithCallback(keyMenuCallback, ChoiceBox, title=_("Network Shares Context Menu"), list=choices)

	def credentialsClosed(self, *args):
		if self.menuAddress in self.expanded:
			self.startShareEnumeration(self.menuAddress)

	def keyGreen(self):
		current = self["list"].getCurrent()
		if current and current[-1].get("kind") == "host":
			self.menuAddress = current[-1]["address"]
			self.menuHostname = self.hostnameFor(self.menuAddress)
			self.session.openWithCallback(self.credentialsClosed, NetworkCredentials, self.menuHostname, self.repository)

	def keyRescan(self):
		def keyRescanCallback(status):
			if "list" in self:
				self["key_yellow"].setText(_("Rescan"))
				self["actions"].setEnabledAction("yellow", True)
				if status:
					self.buildList()
				else:
					self["description"].setText(_("Error: Rescan failed!"))

		self.expanded = set()
		self.shares = {}
		self.shareState = {}
		self.smbVersions = {}
		self.pendingProtocols = {}
		self["list"].setList([])
		self["description"].setText(_("Scanning..."))
		self["key_yellow"].setText("")
		self["actions"].setEnabledAction("yellow", False)
		discoveryManager.rescan(keyRescanCallback)

	def keyToggleUsingIP(self):
		config.network.browserUsingIP.value = not config.network.browserUsingIP.value
		config.network.browserUsingIP.save()
		self.selectionChanged()


class NetworkCredentials(Setup):
	GUEST_USERNAME = "guest"
	GUEST_TRANSLATED = _("guest")

	def __init__(self, session, hostname, repository):
		self.hostname = hostname
		self.repository = repository
		username, password = repository.credentialsGet(hostname)
		if username is None:
			username = self.GUEST_USERNAME
		self.useGuest = NoSave(ConfigYesNo(default=username == self.GUEST_USERNAME))
		self.username = NoSave(ConfigText(default=username, fixed_size=False))
		self.password = NoSave(ConfigPassword(default=password))
		Setup.__init__(self, session=session, setup="NetworkCredentials")
		self.setTitle(_("Credentials for '%s'") % hostname)

	def keySave(self):
		self.repository.credentialsSave(self.hostname, self.GUEST_USERNAME if self.useGuest.value else self.username.value, "" if self.useGuest.value else self.password.value)
		Setup.keySave(self)
