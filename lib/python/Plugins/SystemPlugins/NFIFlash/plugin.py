# -*- coding: utf8 -*-

def Plugins(**kwargs):
	from Plugins.Plugin import PluginDescriptor
	from Tools.Directories import fileExists
	if fileExists("/usr/share/bootlogo-flasher.mvi"):
		import flasher
		# started from usb stick # don't try to be intelligent and trick this - it's not possible to rewrite the flash memory with a system currently booted from it
		return [PluginDescriptor(where = PluginDescriptor.WHERE_WIZARD, fnc = (9,flasher.NFIFlash))]
	else:
		# started on real enigma2
		import downloader
		return [PluginDescriptor(name="NFI Image Flashing",
			description = _("Download .NFI-Files for USB-Flasher"),
			icon = "flash.png",
			where = [PluginDescriptor.WHERE_PLUGINMENU],
			fnc = downloader.main), PluginDescriptor(name="nfi", where = PluginDescriptor.WHERE_FILESCAN, fnc = downloader.filescan)
			]
			#,
			#PluginDescriptor(name="nfi", where = PluginDescriptor.WHERE_WIZARD, fnc = (1,downloader.NFIDownload)) ]
