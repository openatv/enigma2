from Plugins.Plugin import PluginDescriptor
from Tools.HardwareInfo import HardwareInfo
from Tools.Directories import fileExists
from downloader import NFIDownload, filescan
from flasher import NFIFlash

def NFIFlasherMain(session, tmp = None, **kwargs):
	session.open(NFIDownload, "/home/root" )

def NFICallFnc(tmp = None):
	return NFIFlasherMain

def Plugins(**kwargs):
	# currently only available for DM8000
	if HardwareInfo().get_device_name() != "dm8000":
		return [PluginDescriptor()]
	#return [PluginDescriptor(where = PluginDescriptor.WHERE_WIZARD, fnc = (9,NFIFlash))]
		# it's not possible to rewrite the flash memory with a system currently booted from it
	return [PluginDescriptor(name=_("NFI image flashing"),
		description=_("Download .NFI-files for USB-flasher"),
		icon = "flash.png",
		where = PluginDescriptor.WHERE_SOFTWAREMANAGER,
		needsRestart = False,
		fnc={"SoftwareSupported": NFICallFnc, "menuEntryName": lambda x: _("NFI image flashing"),
			"menuEntryDescription": lambda x: _("Download .NFI-files for USB-flasher")}),
		PluginDescriptor(name="nfi", where = PluginDescriptor.WHERE_FILESCAN, needsRestart = False, fnc = filescan)]
