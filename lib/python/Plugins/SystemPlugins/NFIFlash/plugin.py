from Plugins.Plugin import PluginDescriptor
from Tools.HardwareInfo import HardwareInfo
from Tools.Directories import fileExists
from downloader import NFIDownload, filescan

def NFIFlasherMain(session, tmp = None, **kwargs):
	session.open(NFIDownload, "/home/root" )

def NFICallFnc(tmp = None):
	return NFIFlasherMain

def Plugins(**kwargs):
	# currently only available for DM8000
	if HardwareInfo().get_device_name() != "dm8000":
		return [PluginDescriptor()]
	if fileExists("/usr/share/bootlogo-flasher.mvi"):
		import flasher
		# started from usb stick # don't try to be intelligent and trick this - it's not possible to rewrite the flash memory with a system currently booted from it
		return [PluginDescriptor(where = PluginDescriptor.WHERE_WIZARD, fnc = (9,flasher.NFIFlash))]
	else:
		# started on real enigma2
		return [PluginDescriptor(name=_("NFI Image Flashing"),
			description=_("Download .NFI-Files for USB-Flasher"),
			icon = "flash.png",
			where = PluginDescriptor.WHERE_SOFTWAREMANAGER,
			fnc={"SoftwareSupported": NFICallFnc, "menuEntryName": lambda x: _("NFI Image Flashing"),
			     "menuEntryDescription": lambda x: _("Download .NFI-Files for USB-Flasher")}),
			PluginDescriptor(name="nfi", where = PluginDescriptor.WHERE_FILESCAN, fnc = filescan)]
