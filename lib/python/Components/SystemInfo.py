from enigma import eDVBResourceManager, Misc_Options
from Tools.Directories import fileExists, fileCheck
from Tools.HardwareInfo import HardwareInfo

from boxbranding import getMachineBuild, getBoxType

SystemInfo = { }

#FIXMEE...
def getNumVideoDecoders():
	idx = 0
	while fileExists("/dev/dvb/adapter0/video%d"% idx, 'f'):
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
SystemInfo["OledDisplay"] = fileExists("/dev/dbox/oled0")
SystemInfo["LcdDisplay"] = fileExists("/dev/dbox/lcd0")
SystemInfo["DisplayLED"] = getBoxType() in ('gb800se', 'gb800solo')
SystemInfo["LEDButtons"] = getBoxType() == 'vuultimo'
SystemInfo["DeepstandbySupport"] = HardwareInfo().has_deepstandby()
SystemInfo["Fan"] = fileCheck("/proc/stb/fp/fan")
SystemInfo["FanPWM"] = SystemInfo["Fan"] and fileCheck("/proc/stb/fp/fan_pwm")
SystemInfo["StandbyLED"] = fileCheck("/proc/stb/power/standbyled")
SystemInfo["WakeOnLAN"] = fileCheck("/proc/stb/power/wol") or fileCheck("/proc/stb/fp/wol")
SystemInfo["HDMICEC"] = (fileExists("/dev/hdmi_cec") or fileExists("/dev/misc/hdmi_cec0")) and fileExists("/usr/lib/enigma2/python/Plugins/SystemPlugins/HdmiCEC/plugin.pyo")
SystemInfo["SABSetup"] = fileExists("/usr/lib/enigma2/python/Plugins/SystemPlugins/SABnzbd/plugin.pyo")
SystemInfo["Blindscan"] = fileExists("/usr/lib/enigma2/python/Plugins/SystemPlugins/Blindscan/plugin.pyo")
SystemInfo["Satfinder"] = fileExists("/usr/lib/enigma2/python/Plugins/SystemPlugins/Satfinder/plugin.pyo")
SystemInfo["HasExternalPIP"] = getMachineBuild() not in ('et9x00', 'et6x00', 'et5x00') and fileCheck("/proc/stb/vmpeg/1/external")
SystemInfo["VideoDestinationConfigurable"] = fileExists("/proc/stb/vmpeg/0/dst_left")
SystemInfo["hasPIPVisibleProc"] = fileCheck("/proc/stb/vmpeg/1/visible")
SystemInfo["VFD_scroll_repeats"] = fileCheck("/proc/stb/lcd/scroll_repeats")
SystemInfo["VFD_scroll_delay"] = fileCheck("/proc/stb/lcd/scroll_delay")
SystemInfo["VFD_initial_scroll_delay"] = fileCheck("/proc/stb/lcd/initial_scroll_delay")
SystemInfo["VFD_final_scroll_delay"] = fileCheck("/proc/stb/lcd/final_scroll_delay")
SystemInfo["LCDMiniTV"] = fileExists("/proc/stb/lcd/mode")
SystemInfo["LCDMiniTVPiP"] = SystemInfo["LCDMiniTV"] and getBoxType() != 'gb800ueplus'
SystemInfo["LcdLiveTV"] = fileCheck("/proc/stb/fb/sd_detach")
SystemInfo["3DMode"] = fileCheck("/proc/stb/fb/3dmode") or fileCheck("/proc/stb/fb/primary/3d")
SystemInfo["3DZNorm"] = fileCheck("/proc/stb/fb/znorm") or fileCheck("/proc/stb/fb/primary/zoffset")
SystemInfo["Blindscan_t2_available"] = fileCheck("/proc/stb/info/vumodel")
