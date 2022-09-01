from re import findall
import subprocess
from Screens.MessageBox import MessageBox
from Screens.VirtualKeyBoard import VirtualKeyBoard

from .unarchiver import ArchiverMenuScreen, ArchiverInfoScreen

ADDONINFO = (
	_("File Commander - unrar Addon"),
	_("unpack Rar Files"),
	"0.3"
)


class RarMenuScreen(ArchiverMenuScreen):

	DEFAULT_PW = "2D1U3MP!"

	def __init__(self, session, sourcelist, targetlist):
		ArchiverMenuScreen.__init__(self, session, sourcelist, targetlist, addoninfo=ADDONINFO)

		self.unrar = "unrar"
		self.defaultPW = self.DEFAULT_PW

		self.initList(_("Show contents of rar file"))

	def ok(self):
		selectName = self['list_left'].getCurrent()[0][0]
		self.selectId = self['list_left'].getCurrent()[0][1]
		print("[RarMenuScreen] Select: %s %s" % (selectName, self.selectId))
		self.checkPW(self.defaultPW)

	def checkPW(self, pwd):
		self.defaultPW = pwd
		print("[RarMenuScreen] Current pw: %s" % self.defaultPW)
		cmd = (self.unrar, "t", "-p" + self.defaultPW, self.sourceDir + self.filename)
		try:
			p = subprocess.Popen(cmd, shell=False, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
		except OSError as ex:
			msg = _("Can not run %s: %s.\n%s may be in a plugin that is not installed.") % (cmd[0], ex.strerror, cmd[0])
			print("[RarMenuScreen] %s" % msg)
			self.session.open(MessageBox, msg, MessageBox.TYPE_ERROR)
			return
		stdlog = p.stdout.read()
		if stdlog:
			print("[RarMenuScreen] checkPW stdout %s" % len(stdlog))
			print(stdlog)
			if 'Corrupt file or wrong password.' in stdlog:
				print("[RarMenuScreen] pw incorrect!")
				self.session.openWithCallback(self.setPW, VirtualKeyBoard, title=_("%s is password protected.") % self.filename + " " + _("Please enter password"), text="")
			else:
				print("[RarMenuScreen] pw correct!")
				self.unpackModus(self.selectId)

	def setPW(self, pwd):
		if pwd is None or pwd.strip() == "":
			self.defaultPW = self.DEFAULT_PW
		else:
			self.checkPW(pwd)

	def unpackModus(self, selectid):
		print("[RarMenuScreen] unpackModus %s" % selectid)
		if selectid == self.ID_SHOW:
			cmd = (self.unrar, "lb", "-p" + self.defaultPW, self.sourceDir + self.filename)
			self.unpackPopen(cmd, ArchiverInfoScreen, ADDONINFO)
		else:
			cmd = [self.unrar, "x", "-p" + self.defaultPW, self.sourceDir + self.filename, "-o+"]
			cmd.append(self.getPathBySelectId(selectid))
			self.unpackEConsoleApp(cmd, exePath=self.unrar, logCallback=self.log)

	def log(self, data):
		# print "[RarMenuScreen] log", data
		status = findall('(\d+)%', data)
		if status:
			if not status[0] in self.ulist:
				self.ulist.append((status[0]))
				self.chooseMenuList2.setList(list(map(self.UnpackListEntry, status)))
				self['unpacking'].selectionEnabled(0)

		if 'All OK' in data:
			self.chooseMenuList2.setList(list(map(self.UnpackListEntry, ['100'])))
			self['unpacking'].selectionEnabled(0)

	def extractDone(self, filename, data):
		if data:
			if self.errlog and not self.errlog.endswith("\n"):
				self.errlog += "\n"
			self.errlog += {
				1: "Non fatal error(s) occurred.",
				2: "A fatal error occurred.",
				3: "Invalid checksum. Data is damaged.",
				4: "Attempt to modify an archive locked by 'k' command.",
				5: "Write error.",
				6: "File open error.",
				7: "Wrong command line option.",
				8: "Not enough memory.",
				9: "File create error",
				10: "No files matching the specified mask and options were found.",
				11: "Wrong password.",
				255: "User stopped the process.",
			}.get(data, "Unknown error")
		super(RarMenuScreen, self).extractDone(filename, data)
