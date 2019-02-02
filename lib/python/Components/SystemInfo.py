from os import path

from enigma import eDVBResourceManager, Misc_Options

from Tools.Directories import fileExists, fileCheck
from Tools.HardwareInfo import HardwareInfo

from boxbranding import getBoxType, getMachineBuild, getDisplayType, getHaveRCA, getHaveDVI, getHaveYUV, getHaveSCART, getHaveAVJACK, getHaveSCARTYUV, getHaveHDMI

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

SystemInfo["FrontpanelDisplay"] = fileExists("/dev/dbox/oled0") or fileExists("/dev/dbox/lcd0")
SystemInfo["7segment"] = getDisplayType() in ('7segment')
SystemInfo["ConfigDisplay"] = SystemInfo["FrontpanelDisplay"] and getDisplayType() not in ('7segment')
SystemInfo["LCDSKINSetup"] = path.exists("/usr/share/enigma2/display") and getDisplayType() not in ('7segment')
SystemInfo["12V_Output"] = Misc_Options.getInstance().detected_12V_output()
SystemInfo["ZapMode"] = fileCheck("/proc/stb/video/zapmode") or fileCheck("/proc/stb/video/zapping_mode")
SystemInfo["NumFrontpanelLEDs"] = countFrontpanelLEDs()
SystemInfo["OledDisplay"] = fileExists("/dev/dbox/oled0") or getBoxType() in ('osminiplus')
SystemInfo["LcdDisplay"] = fileExists("/dev/dbox/lcd0")
SystemInfo["FBLCDDisplay"] = fileCheck("/proc/stb/fb/sd_detach")
SystemInfo["DeepstandbySupport"] = HardwareInfo().has_deepstandby()
SystemInfo["Fan"] = fileCheck("/proc/stb/fp/fan")
SystemInfo["FanPWM"] = SystemInfo["Fan"] and fileCheck("/proc/stb/fp/fan_pwm")
SystemInfo["PowerLed"] = fileExists("/proc/stb/power/powerled")
SystemInfo["StandbyPowerLed"] = fileExists("/proc/stb/power/standbyled")
SystemInfo["SuspendPowerLed"] = fileExists("/proc/stb/power/suspendled")
SystemInfo["LEDButtons"] = getBoxType() == 'vuultimo'
SystemInfo["WakeOnLAN"] = fileCheck("/proc/stb/power/wol") or fileCheck("/proc/stb/fp/wol")
SystemInfo["HDMICEC"] = (fileExists("/dev/hdmi_cec") or fileExists("/dev/misc/hdmi_cec0")) and fileExists("/usr/lib/enigma2/python/Plugins/SystemPlugins/HdmiCEC/plugin.pyo")
SystemInfo["SABSetup"] = fileExists("/usr/lib/enigma2/python/Plugins/SystemPlugins/SABnzbd/plugin.pyo")
SystemInfo["SeekStatePlay"] = False
SystemInfo["GraphicLCD"] = getBoxType() in ('vuultimo', 'xpeedlx3', 'et10000', 'mutant2400', 'quadbox2400', 'sezammarvel', 'atemionemesis', 'mbultra', 'beyonwizt4')
SystemInfo["Blindscan"] = fileExists("/usr/lib/enigma2/python/Plugins/SystemPlugins/Blindscan/plugin.pyo")
SystemInfo["Satfinder"] = fileExists("/usr/lib/enigma2/python/Plugins/SystemPlugins/Satfinder/plugin.pyo")
SystemInfo["HasExternalPIP"] = getMachineBuild() not in ('et9x00', 'et6x00', 'et5x00') and fileCheck("/proc/stb/vmpeg/1/external")
SystemInfo["hasPIPVisibleProc"] = fileCheck("/proc/stb/vmpeg/1/visible")
SystemInfo["VideoDestinationConfigurable"] = fileExists("/proc/stb/vmpeg/0/dst_left")
SystemInfo["GBWOL"] = fileExists("/usr/bin/gigablue_wol")
SystemInfo["VFD_scroll_repeats"] = fileCheck("/proc/stb/lcd/scroll_repeats")
SystemInfo["VFD_scroll_delay"] = fileCheck("/proc/stb/lcd/scroll_delay")
SystemInfo["VFD_initial_scroll_delay"] = fileCheck("/proc/stb/lcd/initial_scroll_delay")
SystemInfo["VFD_final_scroll_delay"] = fileCheck("/proc/stb/lcd/final_scroll_delay")
SystemInfo["LCDMiniTV"] = fileExists("/proc/stb/lcd/mode")
SystemInfo["LCDMiniTVPiP"] = SystemInfo["LCDMiniTV"] and getBoxType() not in ('gb800ueplus','gbquad4k','gbue4k')
SystemInfo["LcdLiveTV"] = fileCheck("/proc/stb/fb/sd_detach") or fileCheck("/proc/stb/lcd/live_enable")
SystemInfo["LcdLiveTVPiP"] = fileCheck("/proc/stb/lcd/live_decoder")
SystemInfo["MiniTV"] = fileCheck("/proc/stb/fb/sd_detach") or fileCheck("/proc/stb/lcd/live_enable")
SystemInfo["FastChannelChange"] = False
SystemInfo["CIHelper"] = fileExists("/usr/bin/cihelper")
SystemInfo["grautec"] = fileExists("/tmp/usbtft")
SystemInfo["3DMode"] = fileCheck("/proc/stb/fb/3dmode") or fileCheck("/proc/stb/fb/primary/3d")
SystemInfo["3DZNorm"] = fileCheck("/proc/stb/fb/znorm") or fileCheck("/proc/stb/fb/primary/zoffset")
SystemInfo["CanUse3DModeChoices"] = fileExists('/proc/stb/fb/3dmode_choices') and True or False
SystemInfo["HaveMultiBoot"] = (fileCheck("/boot/STARTUP") or fileCheck("/boot/cmdline.txt"))
SystemInfo["HaveMultiBootHD"] = fileCheck("/boot/STARTUP") and getMachineBuild() in ('hd51','vs1500','h7')
SystemInfo["HaveMultiBootCY"] = fileCheck("/boot/STARTUP") and getMachineBuild() in ('8100s')
SystemInfo["HaveMultiBootOS"] = fileCheck("/boot/STARTUP") and getMachineBuild() in ('osmio4k')
SystemInfo["HaveMultiBootXC"] = fileCheck("/boot/cmdline.txt")
SystemInfo["HaveMultiBootGB"] = fileCheck("/boot/STARTUP") and getMachineBuild() in ('gb7252')
SystemInfo["HaveMultiBootDS"] = fileCheck("/boot/STARTUP") and getMachineBuild() in ('gbmv200','cc1','sf8008','ustym4kpro') and fileCheck("/dev/sda")
SystemInfo["need_dsw"] = getBoxType() not in ('osminiplus','osmega')
SystemInfo["HaveCISSL"] = fileCheck("/etc/ssl/certs/customer.pem") and fileCheck("/etc/ssl/certs/device.pem")
SystemInfo["HaveID"] = fileCheck("/etc/.id")
SystemInfo["HaveTouchSensor"] = getBoxType() in ('dm520', 'dm525', 'dm900', 'dm920')
SystemInfo["DefaultDisplayBrightness"] = getBoxType() in ('dm900', 'dm920') and 8 or 5
SystemInfo["RecoveryMode"] = fileCheck("/proc/stb/fp/boot_mode")
SystemInfo["ForceLNBPowerChanged"] = fileCheck("/proc/stb/frontend/fbc/force_lnbon")
SystemInfo["ForceToneBurstChanged"] = fileCheck("/proc/stb/frontend/fbc/force_toneburst")
SystemInfo["USETunersetup"] = SystemInfo["ForceLNBPowerChanged"] or SystemInfo["ForceToneBurstChanged"]
SystemInfo["XcoreVFD"] = getMachineBuild() in ('xc7346','xc7439') 
SystemInfo["HDMIin"] = getMachineBuild() in ('inihdp', 'hd2400', 'et10000', 'dm7080', 'dm820', 'dm900', 'dm920', 'vuultimo4k', 'et13000', 'sf5008', 'vuuno4kse', 'vuduo4k') or getBoxType() in ('spycat4k','spycat4kcombo','gbquad4k')
SystemInfo["HaveRCA"] = getHaveRCA() in ('True')
SystemInfo["HaveDVI"] = getHaveDVI() in ('True')
SystemInfo["HaveAVJACK"] = getHaveAVJACK() in ('True')
SystemInfo["HAVESCART"] = getHaveSCART() in ('True')
SystemInfo["HAVESCARTYUV"] = getHaveSCARTYUV() in ('True')
SystemInfo["HAVEYUV"] = getHaveYUV() in ('True')
SystemInfo["HAVEHDMI"] = getHaveHDMI() in ('True')
