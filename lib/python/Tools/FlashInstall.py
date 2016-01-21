from Components.config import config
from Tools.Directories import fileExists
from time import time
from datetime import datetime

def FlashInstallTime():
	print 'INSTALLTIME: RUNNING'
	print 'FIRST RUN: ', config.misc.firstrun.value
	print 'INSTAL FILE EXSITS:', fileExists('/etc/install')
	if config.misc.firstrun.value and not fileExists('/etc/install'):
		f = open("/etc/install", "w")
		now = datetime.now()
		f.write(now.strftime("%Y-%m-%d"))
		f.close()

