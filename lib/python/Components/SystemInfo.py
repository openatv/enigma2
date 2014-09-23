from enigma import eDVBResourceManager, Misc_Options
from Tools.Directories import fileExists, fileCheck, resolveFilename, SCOPE_SKIN
from Tools.HardwareInfo import HardwareInfo
from boxbranding import getBoxType, getMachineBuild

SystemInfo = { }

#FIXMEE...
def getNumVideoDecoders():
	idx = 0
	while fileExists("/dev/dvb/adapter0/video%d"%(idx), 'f'):
		idx += 1
	return idx

SystemInfo["NumVideoDecoders"] = getNumVideoDecoders()
SystemInfo["PIPAvailable"] = SystemInfo["NumVideoDecoders"] > 1
SystemInfo["CanMeasureFrontendInputPower"] = eDVBResourceManager.getInstance().canMeasureFrontendInputPower()


def countFrontpanelLEDs():
	leds = 0
	if fileExists("/proc/stb/fp/led_set_pattern"):
		leds += 1

	while fileExists("/proc/stb/fp/led%d_pattern" % leds):
		leds += 1

	return leds

SystemInfo["12V_Output"] = Misc_Options.getInstance().detected_12V_output()
SystemInfo["ZapMode"] = fileCheck("/proc/stb/video/zapmode") or fileCheck("/proc/stb/video/zapping_mode")
SystemInfo["NumFrontpanelLEDs"] = countFrontpanelLEDs()
SystemInfo["FrontpanelDisplay"] = fileExists("/dev/dbox/oled0") or fileExists("/dev/dbox/lcd0")
SystemInfo["FrontpanelDisplayGrayscale"] = fileExists("/dev/dbox/oled0")
SystemInfo["LcdDisplay"] = fileExists("/dev/dbox/lcd0")
SystemInfo["DeepstandbySupport"] = HardwareInfo().get_device_name() != "dm800"
SystemInfo["OledDisplay"] = fileExists(resolveFilename(SCOPE_SKIN, 'lcd_skin/skin_lcd_default.xml'))
SystemInfo["GBWOL"] = fileExists("/usr/bin/gigablue_wol")
SystemInfo["Fan"] = fileCheck("/proc/stb/fp/fan")
SystemInfo["FanPWM"] = SystemInfo["Fan"] and fileCheck("/proc/stb/fp/fan_pwm")
SystemInfo["StandbyLED"] = fileCheck("/proc/stb/power/standbyled")
SystemInfo["HasExternalPIP"] = getMachineBuild() not in ('et9x00', 'et6x00', 'et5x00') and fileCheck("/proc/stb/vmpeg/1/external")
SystemInfo["VideoDestinationConfigurable"] = fileExists("/proc/stb/vmpeg/0/dst_left")
SystemInfo["hasPIPVisibleProc"] = fileCheck("/proc/stb/vmpeg/1/visible")
SystemInfo["isGBIPBOX"] = fileExists("/usr/lib/enigma2/python/Plugins/Extensions/GBIpboxClient/plugin.pyo")

#if getBoxType() in ('gbquadplus'):
#	SystemInfo["WakeOnLAN"] = False
#else:
SystemInfo["WakeOnLAN"] = fileCheck("/proc/stb/fp/wol")

