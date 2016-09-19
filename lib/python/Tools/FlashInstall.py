from Components.config import config
from Tools.Directories import fileExists
from time import time
from datetime import datetime

def FlashInstallTime():
	if config.misc.firstrun.value and not fileExists('/etc/install'):
		f = open("/etc/install", "w")
		now = datetime.now()
		flashdate = now.strftime("%Y-%m-%d")
		print '[Setting Flash date]', flashdate
		f.write(flashdate)
		f.close()
	elif fileExists('/etc/install'):
		f = open("/etc/install","r")
		flashdate = f.read()
		f.close()
		print '[Image Flashed]', flashdate
