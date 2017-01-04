from Screens.Console import Console
from Tools.Log import Log

from Screens.MessageBox import MessageBox

import hashlib
from distutils import spawn

class FSBLCheckerBase(object):
	def getCurrentHash(self):
		data = None
		try:
			with open("/dev/mtd0", 'r') as mtd0:
				data = mtd0.read(self.BL_SIZE)
				if data:
					h = hashlib.sha256()
					h.update(data)
					return h.hexdigest()
		except:
			pass
		return None

	def isUpdateRequired(self):
		blhash = str(self.getCurrentHash())
		Log.i("Current FSBL checksum is: %s" %(blhash,))
		if not blhash:
			Log.w("COULD NOT READ BL HASH!")
			return False
		for hsh in self.OUTDATED_HASHES:
			if hsh == blhash:
				return True
		return False

class FSBLCheckerDM900(FSBLCheckerBase):
	BL_SIZE = 3*512*1024
	OUTDATED_HASHES = ('4e0e2dcd7f3772a12c9217eab4a80e0235345d3d4ca633f6769b45a3262ecc03',)

class FSBLUpdater(Console):
	CHECKER_LUT = {
		"dm900" : FSBLCheckerDM900
	}
	FLASH_FSBL_BINARY = spawn.find_executable("flash-fsbl")

	@staticmethod
	def isUpdateRequired(boxtype):
		if not FSBLUpdater.FLASH_FSBL_BINARY:
			Log.w("FSBL flasher not available - aborting!")
			return False
		Log.i(FSBLUpdater.FLASH_FSBL_BINARY)
		checker = FSBLUpdater.CHECKER_LUT.get(boxtype, None)
		if checker:
			return checker().isUpdateRequired()
		return False

	def __init__(self, session, boxtype):
		Console.__init__(self, session, title = _("!! Bootloader Upgrade !!"), cmdlist = (self.FLASH_FSBL_BINARY,), finishedCallback = None, closeOnSuccess = False)
		self.skinName = "Console"
		self._boxtype = boxtype

	def log(self, data):
		Log.w("# %s" % (data,))

	def startRun(self):
		if self.isUpdateRequired(self._boxtype):
			Console.startRun(self)
		else:
			txt = self["text"].getText()
			txt += _("No update required!")

	def runFinished(self, retval):
		Console.runFinished(self, retval)
		Log.w(retval)
		if retval != 0:
			title = _("Update failed!")
			txt = _("Don't worry your device is still ok! There are several safety mechanisms in place!\nYour device is still as fine as it was before this procedure!")
			msgtype = MessageBox.TYPE_ERROR
		else:
			title = _("Update finished!")
			txt = _("Update succeeded!\nYour Bootloader is now up-to-date!")
			msgtype = MessageBox.TYPE_INFO
		self.session.open(MessageBox, txt, type=msgtype, title=title)

