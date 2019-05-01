import os
from Components.Sources.StaticText import StaticText
from Components.ActionMap import ActionMap
from Components.ChoiceList import ChoiceList, ChoiceEntryComponent
from Components.Console import Console
from Components.Label import Label
from Components.SystemInfo import SystemInfo
from Screens.Standby import TryQuitMainloop
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Tools.BoundFunction import boundFunction
from Tools.Directories import fileExists, fileCheck, pathExists, fileHas


class SDswap(Screen):

	skin = """
	<screen name="H9SDswap" position="center,center" size="750,900" flags="wfNoBorder" backgroundColor="transparent">
		<eLabel name="b" position="0,0" size="750,700" backgroundColor="#00ffffff" zPosition="-2" />
		<eLabel name="a" position="1,1" size="748,698" backgroundColor="#00000000" zPosition="-1" />
		<widget source="Title" render="Label" position="60,10" foregroundColor="#00ffffff" size="480,50" halign="left" font="Regular; 28" backgroundColor="#00000000" />
		<eLabel name="line" position="1,60" size="748,1" backgroundColor="#00ffffff" zPosition="1" />
		<eLabel name="line2" position="1,250" size="748,4" backgroundColor="#00ffffff" zPosition="1" />
		<widget name="config" position="2,280" size="730,380" halign="center" font="Regular; 22" backgroundColor="#00000000" foregroundColor="#00e5b243" />
		<widget source="labe14" render="Label" position="2,80" size="730,30" halign="center" font="Regular; 22" backgroundColor="#00000000" foregroundColor="#00ffffff" />
		<widget source="labe15" render="Label" position="2,130" size="730,60" halign="center" font="Regular; 22" backgroundColor="#00000000" foregroundColor="#00ffffff" />
		<widget source="key_red" render="Label" position="30,200" size="150,30" noWrap="1" zPosition="1" valign="center" font="Regular; 20" halign="left" backgroundColor="#00000000" foregroundColor="#00ffffff" />
		<widget source="key_green" render="Label" position="230,200" size="150,30" noWrap="1" zPosition="1" valign="center" font="Regular; 20" halign="left" backgroundColor="#00000000" foregroundColor="#00ffffff" />
		<widget source="key_yellow" render="Label" position="430,200" size="150,30" noWrap="1" zPosition="1" valign="center" font="Regular; 20" halign="left" backgroundColor="#00000000" foregroundColor="#00ffffff" />
		<ePixmap pixmap="skin_default/buttons/red.png" position="30,200" size="40,40" alphatest="on" />
		<ePixmap pixmap="skin_default/buttons/green.png" position="230,200" size="40,40" alphatest="on" />
		<ePixmap pixmap="skin_default/buttons/yellow.png" position="430,200" size="40,40" alphatest="on" />
	</screen>
	"""

	def __init__(self, session, *args):
		Screen.__init__(self, session)
		self.skinName = "SDswap"
		screentitle = _("switch Nand and SDcard")
		self["key_red"] = StaticText(_("Cancel"))
		self["key_green"] = StaticText(_("SwaptoNand"))
		self["key_yellow"] = StaticText(_("SwaptoSD"))
		self.title = screentitle
		self.switchtype = " "
		self["actions"] = ActionMap(["ColorActions"],
		{
			"red": boundFunction(self.close, None),
			"green": self.SwaptoNand,
			"yellow": self.SwaptoSD,
		}, -1)
		self.onLayoutFinish.append(self.layoutFinished)

	def layoutFinished(self):
		self.setTitle(self.title)

	def SwaptoNand(self):
		self.switchtype = "Nand"
		f = open('/proc/cmdline', 'r').read()
		if "root=/dev/mmcblk0p1"  in f:
			self.container = Console()
			self.container.ePopen("dd if=/usr/share/bootargs-nand.bin of=/dev/mtdblock1", self.Unm)
		else:
			self.session.open(MessageBox, _("SDcard switch ERROR! - already on Nand"), MessageBox.TYPE_INFO, timeout=20)

	def SwaptoSD(self):
		self.switchtype = "mmc"
		f = open('/proc/cmdline', 'r').read()
		print "[H9SDswap] switchtype %s cmdline %s" %(self.switchtype, f) 
		if "root=/dev/mmcblk0p1" in f:
			self.session.open(MessageBox, _("SDcard switch ERROR! - already on mmc"), MessageBox.TYPE_INFO, timeout=20)
		elif os.path.isfile("/media/mmc/usr/bin/enigma2"):
			self.container = Console()
			self.container.ePopen("dd if=/usr/share/bootargs-mmc.bin of=/dev/mtdblock1", self.Unm)
		else:
			self.session.open(MessageBox, _("SDcard switch ERROR! - H9 root files not transferred to SD card"), MessageBox.TYPE_INFO, timeout=20)

	def SwaptoUSB(self):
		self.switchtype = "usb"
		f = open('/proc/cmdline', 'r').read()
		print "[H9SDswap] switchtype %s cmdline %s" %(self.switchtype, f) 
		if "root=/dev/SDA1" in f:
			self.session.open(MessageBox, _("USB switch ERROR! - already on USB"), MessageBox.TYPE_INFO, timeout=20)
		elif os.path.isfile("/media/mmc/usr/bin/enigma2"):
			self.container = Console()
			self.container.ePopen("dd if=/usr/share/bootargs-usb.bin of=/dev/mtdblock1", self.Unm)
		else:
			self.session.open(MessageBox, _("USB switch ERROR! - root files not transferred to USB"), MessageBox.TYPE_INFO, timeout=20)


	def Unm(self, data=None, retval=None, extra_args=None):
		self.container.killAll()
		self.session.open(TryQuitMainloop, 2)
