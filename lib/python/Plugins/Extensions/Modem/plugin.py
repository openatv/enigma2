def getDefaultGateway():
	f = open("/proc/net/route", "r")
	if f:
		for line in f.readlines():
			tokens = line.split('\t')
			if tokens[1] == '00000000': #dest 0.0.0.0
				return int(tokens[2], 16)
	return None

def getTelephone():
	f = open("/etc/ppp/options", "r")
	if f:
		for line in f.readlines():
			if line.find('connect') == 0:
				line = line[line.find(' ')+1:]
				line = line[line.find(' ')+1:]
				line = line[:line.find('"')]
				return line
	return ""

def setOptions(tel, user):
	f = open("/etc/ppp/options", "r+")
	if f:
		lines = f.readlines()
		f.seek(0)
		for line in lines:
			if line.find('connect') == 0:
				p = line.find(' ')
				p = line.find(' ', p+1)
				line = line[:p+1]
				f.write(line+tel+'"\n')
			elif line.find('user') == 0:
				f.write('user '+user+'\n')
			else:
				f.write(line)

def getSecretString():
	f = open("/etc/ppp/pap-secrets", "r")
	if f:
		for line in f.readlines():
			if line[0] == '#' or line.find('*') == -1:
				continue
			for ch in (' ', '\t', '\n', '"'):
				line = line.replace(ch, '')
			return line
	return None

def setSecretString(secret):
	f = open("/etc/ppp/pap-secrets", 'r+')
	if f:
		lines = f.readlines()
		f.seek(0)
		for line in lines:
			if line[0] == '#' or line.find('*') == -1:
				f.write(line)
				continue
			f.write(secret+'\n')

from Screens.Screen import Screen
from Plugins.Plugin import PluginDescriptor
from enigma import eConsoleAppContainer, eTimer
from Components.Label import Label
from Components.Button import Button
from Components.ConfigList import ConfigList
from Components.config import ConfigText, ConfigPassword, KEY_LEFT, KEY_RIGHT, KEY_0, KEY_DELETE, KEY_BACKSPACE
from Components.ActionMap import NumberActionMap, ActionMap
from os import system

NONE = 0
CONNECT = 1
ABORT = 2
DISCONNECT = 3

gateway = None

def pppdClosed(ret):
	global gateway
	print "modem disconnected", ret
	if gateway:
		#FIXMEEE... hardcoded for little endian!!
		system("route add default gw %d.%d.%d.%d" %(gateway&0xFF, (gateway>>8)&0xFF, (gateway>>16)&0xFF, (gateway>>24)&0xFF))

connected = False
conn = eConsoleAppContainer()
conn.appClosed.append(pppdClosed)

class ModemSetup(Screen):
	skin = """
		<screen position="180,100" size="320,300" title="Modem" >
		<ePixmap pixmap="skin_default/buttons/green.png" position="10,10" size="140,40" alphatest="on" />
		<ePixmap pixmap="skin_default/buttons/red.png" position="160,10" size="140,40" alphatest="on" />
		<widget name="key_green" position="10,10" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" transparent="1" />
		<widget name="key_red" position="160,10" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" transparent="1" />
		<widget name="list" position="10,60" size="300,120" />
		<widget name="state" position="10,210" size="300,80" font="Regular;20" />
		</screen>"""

	def nothing(self):
		print "nothing!"

	def __init__(self, session, args = None):
		global connected
		global conn
		self.skin = ModemSetup.skin
		secret = getSecretString()
		user = secret[:secret.find('*')]
		password = secret[secret.find('*')+1:]
		self.username = ConfigText(user, fixed_size=False)
		self.password = ConfigPassword(password, fixed_size=False)
		self.phone = ConfigText(getTelephone(), fixed_size=False)
		self.phone.setUseableChars(u"0123456789")
		lst = [ (_("Username"), self.username),
			(_("Password"), self.password),
			(_("Phone number"), self.phone) ]
		self["list"] = ConfigList(lst)
		self["key_green"] = Button("")
		self["key_red"] = Button("")
		self["state"] = Label("")
		self["actions"] = NumberActionMap(["ModemActions"],
		{
			"cancel": self.close,
			"left": self.keyLeft,
			"right": self.keyRight,
			"connect": self.connect,
			"disconnect": self.disconnect,
			"deleteForward": self.deleteForward,
			"deleteBackward": self.deleteBackward,
			"0": self.keyNumber,
			"1": self.keyNumber,
			"2": self.keyNumber,
			"3": self.keyNumber,
			"4": self.keyNumber,
			"5": self.keyNumber,
			"6": self.keyNumber,
			"7": self.keyNumber,
			"8": self.keyNumber,
			"9": self.keyNumber
		}, -1)

		self["ListActions"] = ActionMap(["ListboxDisableActions"],
		{
			"moveUp": self.nothing,
			"moveDown": self.nothing,
			"moveTop": self.nothing,
			"moveEnd": self.nothing,
			"pageUp": self.nothing,
			"pageDown": self.nothing
		}, -1)

		self.stateTimer = eTimer()
		self.stateTimer.callback.append(self.stateLoop)

		conn.appClosed.append(self.pppdClosed)
		conn.dataAvail.append(self.dataAvail)

		Screen.__init__(self, session)
		self.onClose.append(self.__closed)
		self.onLayoutFinish.append(self.__layoutFinished)

	def __layoutFinished(self):
		global conn
		if conn.running():
			self["state"].setText(_("Connected!"));
			self.green_function = NONE
			self.red_function = DISCONNECT
		else:
			self.green_function = CONNECT
			self.red_function = NONE
		self.updateGui()

	def __closed(self):
		global connected
		conn.appClosed.remove(self.pppdClosed)
		conn.dataAvail.remove(self.dataAvail)
		if not connected:
			conn.sendCtrlC()
		setOptions(self.phone.getText(), self.username.getText())
		setSecretString(self.username.getText() + ' * ' + self.password.getText())

	def stateLoop(self):
		txt = self["state"].getText()
		txt += '.'
		self["state"].setText(txt)

	def connect(self):
		if self.green_function == CONNECT:
			global gateway
			gateway = getDefaultGateway()
			self["state"].setText(_("Dialing:"))
			system("route del default")
			system("modprobe ppp_async");
			self.stateTimer.start(1000,False)
			setOptions(self.phone.getText(), self.username.getText())
			setSecretString(self.username.getText() + ' * ' + self.password.getText())
			ret = conn.execute("pppd", "pppd", "-d", "-detach")
			if ret:
				print "execute pppd failed!"
				self.pppdClosed(ret)
				pppdClosed(ret)
			self.green_function = NONE
			self.red_function = ABORT
			self.updateGui()

	def disconnect(self):
		conn.sendCtrlC()
		self.red_function = NONE
		self.updateGui()

	def keyLeft(self):
		if self.green_function == CONNECT:
			self["list"].handleKey(KEY_LEFT)

	def keyRight(self):
		if self.green_function == CONNECT:
			self["list"].handleKey(KEY_RIGHT)

	def keyNumber(self, number):
		if self.green_function == CONNECT:
			self["list"].handleKey(KEY_0 + number)

	def deleteForward(self):
		if self.green_function == CONNECT:
			self["list"].handleKey(KEY_DELETE)

	def deleteBackward(self):
		if self.green_function == CONNECT:
			self["list"].handleKey(KEY_BACKSPACE)

	def pppdClosed(self, retval):
		global connected
		self.stateTimer.stop()
		self.red_function = NONE
		self.green_function = CONNECT
		self["state"].setText("")
		self.updateGui()
		connected = False

	def dataAvail(self, text):
		if text.find("Serial connection established") != -1:
			tmp = self["state"].getText()
			tmp += "OK\nLogin:"
			self["state"].setText(tmp)
		if text.find("PAP authentication succeeded") != -1:
			tmp = self["state"].getText()
			tmp += "OK\n";
			self["state"].setText(tmp)
			self.stateTimer.stop()
		if text.find("ip-up finished") != -1:
			global connected
			tmp = self["state"].getText()
			tmp += "Connected :)\n"
			self["state"].setText(tmp)
			self.red_function = DISCONNECT
			connected=True
		if text.find("Connect script failed") != -1:
			tmp = self["state"].getText()
			tmp += "FAILED\n"
			self["state"].setText(tmp)
			self.stateTimer.stop()
			self.red_function = NONE
			self.green_function = CONNECT
		self.updateGui()

	def updateGui(self):
		if self.red_function == NONE:
			self["key_red"].setText("")
		elif self.red_function == DISCONNECT:
			self["key_red"].setText(_("Disconnect"))
		elif self.red_function == ABORT:
			self["key_red"].setText(_("Abort"))
		if self.green_function == NONE:
			self["key_green"].setText("")
		elif self.green_function == CONNECT:
			self["key_green"].setText(_("Connect"))
		focus_enabled = self.green_function == CONNECT
		self["list"].instance.setSelectionEnable(focus_enabled)
		self["ListActions"].setEnabled(not focus_enabled)

def main(session, **kwargs):
	session.open(ModemSetup)

def Plugins(**kwargs):
	return PluginDescriptor(name="Modem", description="plugin to connect to internet via builtin modem", where = PluginDescriptor.WHERE_PLUGINMENU, needsRestart = False, fnc=main)
