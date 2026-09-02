from os import access, F_OK, R_OK
from enigma import eTimer
from Plugins.Plugin import PluginDescriptor
from Components.Opkg import OpkgComponent
from Components.Scanner import scanDevice
from Components.Harddisk import harddiskmanager
from Screens.ChoiceBox import ChoiceBox
from Screens.InfoBar import InfoBar
from Screens.MessageBox import MessageBox
from Screens.Toast import Toast

parentScreen = None
global_session = None
DAB_USB_PACKAGE = "enigma2-plugin-systemplugins-dabusb"
dabUSBInstaller = None


class DABUSBInstaller:
	def __init__(self):
		self.opkg = None
		self.running = False

	def requestInstall(self):
		from Components.RTLSDR import hasRTLSDRRuntime, hasRTLSDRUSBHardware
		if self.running or hasRTLSDRRuntime() or not hasRTLSDRUSBHardware() or global_session is None:
			return
		self.running = True
		self.opkg = OpkgComponent()
		self.opkg.addCallback(self.opkgCallback)
		if Toast.instance:
			Toast.instance.showToast(
				_("An RTL-SDR receiver was detected. The optional DAB+ USB runtime is being installed from the feed."),
				Toast.TYPE_INFO, timeout=6)
		self.opkg.runCommand(self.opkg.CMD_REFRESH_INSTALL, {"arguments": [DAB_USB_PACKAGE], "lineMode": True})

	def opkgCallback(self, event, parameter):
		if event == self.opkg.EVENT_ERROR:
			self.finish(False)
		elif event == self.opkg.EVENT_DONE:
			from Components.RTLSDR import hasRTLSDRRuntime
			self.finish(hasRTLSDRRuntime())

	def finish(self, success):
		if not self.running:
			return
		self.running = False
		if self.opkg:
			self.opkg.removeCallback(self.opkgCallback)
			self.opkg = None
		if global_session and Toast.instance:
			Toast.instance.showToast(
				_("DAB+ USB support was installed. You can now enable the receiver in Reception settings.") if success else _("DAB+ USB support could not be installed from the feed."),
				Toast.TYPE_INFO if success else Toast.TYPE_ERROR, timeout=10)


def dabUSBHotplug(device, action):
	if action == "dab-sdr-add" and dabUSBInstaller:
		dabUSBInstaller.requestInstall()


def execute(option):
	if not option:
		if parentScreen:
			parentScreen.close()
		return

	(_, scanner, files, session, _) = option
	scanner.open(files, session)
	if parentScreen:
		parentScreen.close()


def mountpoint_choosen(option):
	if not option:
		if parentScreen:
			parentScreen.close()
		return

	(description, mountpoint, session, popup) = option
	res = scanDevice(mountpoint)

	list = [(r.description, r, res[r], session, popup) for r in res]

	if not list:
		if popup:
			if access(mountpoint, F_OK | R_OK):
				session.open(MessageBox, _("No displayable files on this medium found!"), MessageBox.TYPE_INFO, simple=True, timeout=5)
		if parentScreen:
			parentScreen.close()
		return

	session.openWithCallback(execute, ChoiceBox, title=_("The following files were found..."), list=list)


def scan(session, parent=None):
	global parentScreen
	parentScreen = parent
	parts = [(r.tabbedDescription(), r.mountpoint, session, True) for r in harddiskmanager.getMountedPartitions(onlyhotplug=False) if access(r.mountpoint, F_OK | R_OK)]
	parts.append((_("Temporary directory") + "\t/tmp", "/tmp", session, True))
	session.openWithCallback(mountpoint_choosen, ChoiceBox, title=_("Please select medium to be scanned"), list=parts)


def main(session, **kwargs):
	scan(session)


def partitionListChanged(action, device):
	if InfoBar.instance:
		if InfoBar.instance.execing:
			if action == 'add' and device.is_hotplug:
				mountpoint_choosen((device.description, device.mountpoint, global_session, False))


def sessionstart(reason, session):
	global global_session, dabUSBInstaller
	global_session = session
	if dabUSBInstaller is None:
		dabUSBInstaller = DABUSBInstaller()
	# A receiver can already be present before Enigma2 opens the hotplug socket.
	bootProbe = eTimer()
	bootProbe.callback.append(dabUSBInstaller.requestInstall)
	bootProbe.start(2000, True)
	dabUSBInstaller.bootProbe = bootProbe


def autostart(reason, **kwargs):
	global global_session, dabUSBInstaller
	from Plugins.SystemPlugins.Hotplug.plugin import hotplugNotifier
	if reason == 0:
		harddiskmanager.on_partition_list_change.append(partitionListChanged)
		if dabUSBHotplug not in hotplugNotifier:
			hotplugNotifier.append(dabUSBHotplug)
	elif reason == 1:
		harddiskmanager.on_partition_list_change.remove(partitionListChanged)
		if dabUSBHotplug in hotplugNotifier:
			hotplugNotifier.remove(dabUSBHotplug)
		global_session = None
		dabUSBInstaller = None


def Plugins(**kwargs):
	return [
		PluginDescriptor(name=_("Media scanner"), description=_("Scan files..."), where=PluginDescriptor.WHERE_PLUGINMENU, icon="MediaScanner.png", needsRestart=True, fnc=main),
		PluginDescriptor(where=PluginDescriptor.WHERE_SESSIONSTART, needsRestart=True, fnc=sessionstart),
		PluginDescriptor(where=PluginDescriptor.WHERE_AUTOSTART, needsRestart=True, fnc=autostart)
		]
