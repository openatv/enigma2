# 2013.05.22 08:34:34 UTC
#Embedded file name: /usr/lib/enigma2/python/Plugins/Extensions/IniAirPlayer/__init__.py
from enigma import getDesktop
from skin import loadSkin
import os
from sys import version_info
from Components.config import config, ConfigSubsection, ConfigSelection

def getSkins():
    print '[AirPlayer] search for Skins'
    skins = []
    skindir = '/usr/lib/enigma2/python/Plugins/Extensions/IniAirPlayer/Skins/'
    for o in os.listdir(skindir):
        if os.path.isdir(skindir + o):
            print '[AirPlayer] found Skin', o
            skins.append((o, o))

    return skins


currentArch = 'mips32el'

def getSkinPath(name):
    skinName = name
    dSize = getDesktop(0).size()
    skinpath = '/usr/lib/enigma2/python/Plugins/Extensions/IniAirPlayer/Skins/%s/%sx%s/skin.xml' % (skinName, str(dSize.width()), str(dSize.height()))
    if os.path.exists(skinpath):
        return skinpath
    else:
        print '[AirPlayer] skin ', skinpath, 'does not exist'
        return None


def installIpk(link):
    cmd = '\nBIN=""\nopkg > /dev/null 2>/dev/null\nif [ $? == "1" ]; then\n BIN="opkg"\nelse\n ipkg > /dev/null 2>/dev/null\n if [ $? == "1" ]; then\n  BIN="ipkg"\n fi\nfi\necho "Binary: $BIN"\n\nif [ $BIN != "" ]; then\n $BIN update\n if [ $BIN == "opkg" ]; then\n   OPARAM="--force-overwrite --force-downgrade --force-reinstall"\n else\n   OPARAM="-force-overwrite -force-downgrade -force-reinstall"\n fi\n ( $BIN install %s $OPARAM; )\nfi' % link
    os.system(cmd)


config.plugins.airplayer = ConfigSubsection()
config.plugins.airplayer.skin = ConfigSelection(default='Classic', choices=getSkins())
skinPath = getSkinPath('Classic')
try:
    path = getSkinPath(config.plugins.airplayer.skin.value)
    if path is not None:
        skinPath = path
except Exception as e:
    print '[AirPlayer] error reading skin ', e

# new oe-a have some kind of issues in libcrypto-compat
from Tools.Directories import fileExists
if  not fileExists("/usr/lib/libssl.so.0.9.8"):
	os.system("ln -s /usr/lib/libssl.so.1.0.0 /usr/lib/libssl.so.0.9.8")
	
print '[AirPlayer] using skin ', skinPath
loadSkin(skinPath)
print '[AirPlayer] running python ', version_info
try:
    import ctypes
except Exception as e:
    print '[AirPlayer] ctypes missing'
    print '[AirPlayer] inst python-ctypes 2.7'
    installIpk('http://airplayer.googlecode.com/files/python-ctypes_2.7_mips32el.ipk')

try:
    import plistlib
except Exception as e:
    print '[AirPlayer] python-plistlibb missing'
    print '[AirPlayer] install python-plistb 2.7'
    installIpk('http://airplayer.googlecode.com/files/python-plistlibb_2.7_all.ipk')

try:
    import shutil
except Exception as e:
    print '[AirPlayer] python-shell missing'
    print '[AirPlayer] install python-shell 2.7'
    installIpk('http://airplayer.googlecode.com/files/python-shell_2.7_all.ipk')

try:
    import subprocess
except Exception as e:
    print '[AirPlayer] python-subprocess missing'
    print '[AirPlayer] install python-subprocess 2.7'
    installIpk('http://airplayer.googlecode.com/files/python-subprocess_2.7_all.ipk')

if currentArch != 'sh4' and currentArch != 'sh4p27':
    if not os.path.isfile('/usr/lib/gstreamer-0.10/libgstfragmented.so'):
        installIpk('gst-plugins-bad-fragmented')
        installIpk('gst-plugins-fragmented')
try:
    if os.path.exists('/etc/avahi/services/airplay.service'):
        print '[AirPlayer] try to remove avahi service file'
        os.remove('/etc/avahi/services/airplay.service')
except Exception:
    pass