from os import listdir

from boxbranding import getBoxType, getBrandOEM, getDisplayType, getHaveAVJACK, getHaveDVI, getHaveHDMI, getHaveRCA, getHaveSCART, getHaveSCARTYUV, getHaveYUV, getMachineBuild, getMachineMtdRoot
from enigma import Misc_Options, eDVBResourceManager

from Tools.Directories import fileCheck, fileExists, fileHas, pathExists
from Tools.HardwareInfo import HardwareInfo

SystemInfo = {}

SystemInfo["HasRootSubdir"] = False	# This needs to be here so it can be reset by getMultibootslots!
SystemInfo["RecoveryMode"] = False or fileCheck("/proc/stb/fp/boot_mode")	# This needs to be here so it can be reset by getMultibootslots!
from Tools.Multiboot import getMBbootdevice, getMultibootslots  # This import needs to be here to avoid a SystemInfo load loop!

def getNumVideoDecoders():
	numVideoDecoders = 0
	while fileExists("/dev/dvb/adapter0/video%d" % numVideoDecoders, "f"):
		numVideoDecoders += 1
	return numVideoDecoders

def countFrontpanelLEDs():
	numLeds = fileExists("/proc/stb/fp/led_set_pattern") and 1 or 0
	while fileExists("/proc/stb/fp/led%d_pattern" % numLeds):
		numLeds += 1
	return numLeds

def haveInitCam():
	for cam in listdir("/etc/init.d"):
		if cam.startswith("softcam.") and not cam.endswith("None"):
			return True
		elif cam.startswith("cardserver.") and not cam.endswith("None"):
			return True
	return False


SystemInfo["NumVideoDecoders"] = getNumVideoDecoders()
SystemInfo["PIPAvailable"] = SystemInfo["NumVideoDecoders"] > 1
SystemInfo["CanMeasureFrontendInputPower"] = eDVBResourceManager.getInstance().canMeasureFrontendInputPower()
SystemInfo["FrontpanelDisplay"] = fileExists("/dev/dbox/oled0") or fileExists("/dev/dbox/lcd0")
SystemInfo["HAVEINITCAM"] = haveInitCam()
SystemInfo["7segment"] = getDisplayType() in ("7segment",)
SystemInfo["ConfigDisplay"] = SystemInfo["FrontpanelDisplay"] and getDisplayType() not in ("7segment",)
SystemInfo["LCDSKINSetup"] = fileExists("/usr/share/enigma2/display")
SystemInfo["12V_Output"] = Misc_Options.getInstance().detected_12V_output()
SystemInfo["ZapMode"] = fileCheck("/proc/stb/video/zapmode") or fileCheck("/proc/stb/video/zapping_mode")
SystemInfo["NumFrontpanelLEDs"] = countFrontpanelLEDs()
SystemInfo["OledDisplay"] = fileExists("/dev/dbox/oled0") or getBoxType() in ("osminiplus",)
SystemInfo["LcdDisplay"] = fileExists("/dev/dbox/lcd0")
SystemInfo["FBLCDDisplay"] = fileCheck("/proc/stb/fb/sd_detach")
SystemInfo["DeepstandbySupport"] = HardwareInfo().has_deepstandby()
SystemInfo["Fan"] = fileCheck("/proc/stb/fp/fan")
SystemInfo["FanPWM"] = SystemInfo["Fan"] and fileCheck("/proc/stb/fp/fan_pwm")
SystemInfo["PowerLed"] = fileExists("/proc/stb/power/powerled")
SystemInfo["PowerLed2"] = fileExists("/proc/stb/power/powerled2")
SystemInfo["StandbyPowerLed"] = fileExists("/proc/stb/power/standbyled")
SystemInfo["SuspendPowerLed"] = fileExists("/proc/stb/power/suspendled")
SystemInfo["LedPowerColor"] = fileExists("/proc/stb/fp/ledpowercolor")
SystemInfo["LedStandbyColor"] = fileExists("/proc/stb/fp/ledstandbycolor")
SystemInfo["LedSuspendColor"] = fileExists("/proc/stb/fp/ledsuspendledcolor")
SystemInfo["Power4x7On"] = fileExists("/proc/stb/fp/power4x7on")
SystemInfo["Power4x7Standby"] = fileExists("/proc/stb/fp/power4x7standby")
SystemInfo["Power4x7Suspend"] = fileExists("/proc/stb/fp/power4x7suspend")
SystemInfo["LEDButtons"] = getBoxType() == "vuultimo"
SystemInfo["WakeOnLAN"] = fileCheck("/proc/stb/power/wol") or fileCheck("/proc/stb/fp/wol")
SystemInfo["HDMICEC"] = (fileExists("/dev/hdmi_cec") or fileExists("/dev/misc/hdmi_cec0")) and fileExists("/usr/lib/enigma2/python/Plugins/SystemPlugins/HdmiCEC/plugin.pyo")
SystemInfo["SABSetup"] = fileExists("/usr/lib/enigma2/python/Plugins/SystemPlugins/SABnzbd/plugin.pyo")
SystemInfo["SeekStatePlay"] = False
SystemInfo["StatePlayPause"] = False
SystemInfo["StandbyState"] = False
SystemInfo["GraphicLCD"] = getBoxType() in ("vuultimo", "xpeedlx3", "et10000", "mutant2400", "quadbox2400", "sezammarvel", "atemionemesis", "mbultra", "beyonwizt4", "osmio4kplus")
SystemInfo["Blindscan"] = fileExists("/usr/lib/enigma2/python/Plugins/SystemPlugins/Blindscan/plugin.pyo")
SystemInfo["Satfinder"] = fileExists("/usr/lib/enigma2/python/Plugins/SystemPlugins/Satfinder/plugin.pyo")
SystemInfo["HasExternalPIP"] = getMachineBuild() not in ("et9x00", "et6x00", "et5x00") and fileCheck("/proc/stb/vmpeg/1/external")
SystemInfo["hasPIPVisibleProc"] = fileCheck("/proc/stb/vmpeg/1/visible")
SystemInfo["VideoDestinationConfigurable"] = fileExists("/proc/stb/vmpeg/0/dst_left")
SystemInfo["GBWOL"] = fileExists("/usr/bin/gigablue_wol")
SystemInfo["VFD_scroll_repeats"] = fileCheck("/proc/stb/lcd/scroll_repeats")
SystemInfo["VFD_scroll_delay"] = fileCheck("/proc/stb/lcd/scroll_delay")
SystemInfo["VFD_initial_scroll_delay"] = fileCheck("/proc/stb/lcd/initial_scroll_delay")
SystemInfo["VFD_final_scroll_delay"] = fileCheck("/proc/stb/lcd/final_scroll_delay")
SystemInfo["LCDMiniTV"] = fileExists("/proc/stb/lcd/mode")
SystemInfo["LCDMiniTVPiP"] = SystemInfo["LCDMiniTV"] and getBoxType() not in ("gb800ueplus", "gbquad4k", "gbue4k")
SystemInfo["LcdLiveTV"] = fileCheck("/proc/stb/fb/sd_detach") or fileCheck("/proc/stb/lcd/live_enable")
SystemInfo["LcdLiveTVPiP"] = fileCheck("/proc/stb/lcd/live_decoder")
SystemInfo["MiniTV"] = fileCheck("/proc/stb/fb/sd_detach") or fileCheck("/proc/stb/lcd/live_enable")
SystemInfo["FastChannelChange"] = False
SystemInfo["CIHelper"] = fileExists("/usr/bin/cihelper")
SystemInfo["grautec"] = fileExists("/tmp/usbtft")
SystemInfo["3DMode"] = fileCheck("/proc/stb/fb/3dmode") or fileCheck("/proc/stb/fb/primary/3d")
SystemInfo["3DZNorm"] = fileCheck("/proc/stb/fb/znorm") or fileCheck("/proc/stb/fb/primary/zoffset")
SystemInfo["CanUse3DModeChoices"] = fileExists("/proc/stb/fb/3dmode_choices") and True or False
SystemInfo["need_dsw"] = getBoxType() not in ("osminiplus", "osmega")
SystemInfo["HaveCISSL"] = fileCheck("/etc/ssl/certs/customer.pem") and fileCheck("/etc/ssl/certs/device.pem")
SystemInfo["HaveID"] = fileCheck("/etc/.id")
SystemInfo["HaveTouchSensor"] = getBoxType() in ("dm520", "dm525", "dm900", "dm920")
SystemInfo["DefaultDisplayBrightness"] = getBoxType() in ("dm900", "dm920") and 8 or 5
SystemInfo["ForceLNBPowerChanged"] = fileCheck("/proc/stb/frontend/fbc/force_lnbon")
SystemInfo["ForceToneBurstChanged"] = fileCheck("/proc/stb/frontend/fbc/force_toneburst")
SystemInfo["USETunersetup"] = SystemInfo["ForceLNBPowerChanged"] or SystemInfo["ForceToneBurstChanged"]
SystemInfo["XcoreVFD"] = getMachineBuild() in ("xc7346", "xc7439") 
SystemInfo["HDMIin"] = getMachineBuild() in ("inihdp", "hd2400", "et10000", "dm7080", "dm820", "dm900", "dm920", "vuultimo4k", "et13000", "sf5008", "vuuno4kse", "vuduo4k") or getBoxType() in ("spycat4k", "spycat4kcombo", "gbquad4k")
SystemInfo["HAVEEDIDDECODE"] = fileCheck("/proc/stb/hdmi/raw_edid") and fileCheck("/usr/bin/edid-decode")
SystemInfo["HaveRCA"] = getHaveRCA() == "True"
SystemInfo["HaveDVI"] = getHaveDVI() == "True"
SystemInfo["HaveAVJACK"] = getHaveAVJACK() == "True"
SystemInfo["HAVESCART"] = getHaveSCART() == "True"
SystemInfo["HAVESCARTYUV"] = getHaveSCARTYUV() == "True"
SystemInfo["HAVEYUV"] = getHaveYUV() == "True"
SystemInfo["HAVEHDMI"] = getHaveHDMI() == "True"
SystemInfo["HasMMC"] = fileHas("/proc/cmdline", "root=/dev/mmcblk") or "mmcblk" in getMachineMtdRoot()
SystemInfo["CanProc"] = SystemInfo["HasMMC"] and getBrandOEM() != "vuplus"
SystemInfo["HasHiSi"] = pathExists("/proc/hisi")
SystemInfo["MBbootdevice"] = getMBbootdevice()
SystemInfo["canMultiBoot"] = getMultibootslots()
SystemInfo["canMode12"] = getMachineBuild() in ("hd51", "vs1500", "h7") and ("brcm_cma=440M@328M brcm_cma=192M@768M", "brcm_cma=520M@248M brcm_cma=200M@768M")
SystemInfo["HAScmdline"] = fileCheck("/boot/cmdline.txt")
SystemInfo["HasMMC"] = fileHas("/proc/cmdline", "root=/dev/mmcblk") or SystemInfo["canMultiBoot"] and fileHas("/proc/cmdline", "root=/dev/sda")
SystemInfo["HasSDmmc"] = SystemInfo["canMultiBoot"] and "sd" in SystemInfo["canMultiBoot"][2] and "mmcblk" in getMachineMtdRoot() 
SystemInfo["HasSDswap"] = getMachineBuild() in ("h9", "i55plus") and pathExists("/dev/mmcblk0p1")
SystemInfo["HasFullHDSkinSupport"] = getBoxType() not in ("et4000", "et5000", "sh1", "hd500c", "hd1100", "xp1000", "lc")
SystemInfo["CanProc"] = SystemInfo["HasMMC"] and getBrandOEM() != "vuplus"
SystemInfo["canRecovery"] = getMachineBuild() in ("hd51", "vs1500", "h7", "8100s") and ("disk.img", "mmcblk0p1") or getMachineBuild() in ("xc7439", "osmio4k", "osmio4kplus", "osmini4k") and ("emmc.img", "mmcblk1p1") or getMachineBuild() in ("gbmv200", "cc1", "sf8008", "sf8008m", "ustym4kpro", "beyonwizv2", "viper4k") and ("usb_update.bin", "none")
