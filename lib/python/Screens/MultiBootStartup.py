from Screens.InfoBar import InfoBar
from Screens.Screen import Screen
from Screens.Standby import TryQuitMainloop
from Screens.MessageBox import MessageBox
from Screens.VirtualKeyBoard import VirtualKeyBoard
from Components.ActionMap import ActionMap
from Components.ConfigList import ConfigListScreen
from Components.Label import Label
from Components.Sources.StaticText import StaticText
from Components import Harddisk
from os import path, listdir, system

class MultiBootStartup(ConfigListScreen, Screen):

	skin = """
	<screen name="MultiBootStartupOPT" position="center,center" size="600,250"  flags="wfNoBorder" title="MultiBoot STARTUP Selector" backgroundColor="transparent">
		<eLabel name="b" position="0,0" size="600,250" backgroundColor="#00ffffff" zPosition="-2" />
		<eLabel name="a" position="1,1" size="598,248" backgroundColor="#00000000" zPosition="-1" />
		<widget source="Title" render="Label" position="10,10" foregroundColor="#00ffffff" size="580,50" halign="center" font="Regular; 35" backgroundColor="#00000000" />
		<eLabel name="line" position="1,69" size="598,1" backgroundColor="#00ffffff" zPosition="1" />
		<widget source="config" render="Label" position="10,90" size="580,50" halign="center" font="Regular; 30" backgroundColor="#00000000" foregroundColor="#00ffffff" />
		<widget source="options" render="Label" position="10,132" size="580,35" halign="center" font="Regular; 24" backgroundColor="#00000000" foregroundColor="#00ffffff" />
		<widget name="description" position="10,170" size="580,26" font="Regular; 19" foregroundColor="#00ffffff" halign="center" backgroundColor="#00000000" valign="center" />
		<ePixmap position="555,217" size="35,25" zPosition="2" pixmap="/usr/share/enigma2/skin_default/buttons/key_info.png" alphatest="blend" />
		<widget source="key_red" render="Label" position="35,212" size="170,30" noWrap="1" zPosition="1" valign="center" font="Regular; 20" halign="left" backgroundColor="#00000000" foregroundColor="#00ffffff" />
		<widget source="key_green" render="Label" position="228,212" size="170,30" noWrap="1" zPosition="1" valign="center" font="Regular; 20" halign="left" backgroundColor="#00000000" foregroundColor="#00ffffff" />
		<widget source="key_yellow" render="Label" position="421,212" size="170,30" noWrap="1" zPosition="1" valign="center" font="Regular; 20" halign="left" backgroundColor="#00000000" foregroundColor="#00ffffff" />
		<eLabel position="25,209" size="6,40" backgroundColor="#00e61700" />
		<eLabel position="216,209" size="6,40" backgroundColor="#0061e500" />
		<eLabel position="407,209" size="6,40" backgroundColor="#00e5b243" />
	</screen>
	"""

	def __init__(self, session):
		Screen.__init__(self, session)
		self.title = _("MultiBoot Selector")
		self.skinName = ["MultiBootStartupOPT"]

		self["key_red"] = StaticText(_("Cancel"))
		self["key_green"] = StaticText(_("Save"))
		self["key_yellow"] = StaticText(_("Rename"))
		self["config"] = StaticText()
		self["options"] = StaticText()
		self["description"] = Label()

		self["actions"] = ActionMap(["WizardActions", "SetupActions", "ColorActions"],
		{
			"left": self.left,
			"right": self.right,
			"up": self.up,
			"down": self.down,
			"green": self.save,
			"red": self.cancel,
			"yellow": self.rename,
			"cancel": self.cancel,
			"ok": self.save,
			"info": self.info,
		}, -2)

		self.getCurrent()
		self.onLayoutFinish.append(self.layoutFinished)

	def info(self):
		message = (
			#message 0
			_("*** boxmode=1 (Standard) ***\n\n" +

			"+++ Features +++\n" +
			"Single decode: " +
			"3840x2160p60 10-bit HEVC, " +
			"3840x2160p60 8-bit VP9, " +
			"1920x1080p60 8-bit AVC, " +
			"MAIN only (no PIP), " +
			"Limited display usages, " +
			"UHD only (no SD), " +
			"No multi-PIP, " +
			"No transcoding\n\n" +

			"--- Restrictions ---\n" +
			"Decoder 0: " +
			"3840x2160p60 10-bit HEVC, " +
			"3840x2160p60 8-bit VP9, " +
			"1920x1080p60 8-bit AVC\n" +
			"OSD Grafic 0: " +
			"1080p60 32 bit ARGB\n" +
			"Display 0 Encode Restrictions: " +
			"3840x2160p60 12-bit 4:2:0 (HDMI), " +
			"3840x2160p60 12-bit 4:2:2 (HDMI), " +
			"3840x2160p60 8-bit 4:4:4 (HDMI), " +
			"1920x1080p60 (component)\n" +
			"Only one display format at a time\n\n" +

			"If you want 1080p60 component, HDMI also needs to be 1080p60."),
			#message 1
			_("*** boxmode=12 (Experimental) ***\n\n" +

			"+++ Features +++\n" +
 			"3840x2160p50 10-bit decode for MAIN, " +
			"1080p25/50i PIP support, " +
 			"HDMI input supported (hd51 not available), " +
			"UHD display only, " +
 			"No SD display, " +
 			"No transcoding\n\n" +

			"--- Restrictions ---\n" +
			"Decoder 0: " +
			"3840x2160p50 10-bit HEVC, " +
			"3840x2160p50 8-bit VP9, " +
			"1920x1080p50 8-bit AVC/MPEG\n" +
 			"Decoder 1: " +
			"1920x1080p25/50i 10-bit HEVC, " +
			"1920x1080p25/50i 8-bit VP9/AVC/MPEG2, " +
			"HDMI In (hd51 not available), " +
			"3840x2160p50\n" +
			"OSD Graphic 0 (UHD): " +
			"1080p50 32-bit ARGB\n" +
			"Window 0 (MAIN/UHD): " +
			"Limited display capabilities, " +
			"1080i50 10-bit de-interlacing\n" +
			"Multi-PIP mode (3x): (Enigma2 supported no multi-PIP currently, whether something built into the future is not known), " +
			"Up to three windows where each window can cover 25% of the display canvas., " +
			"576i50 8-bit de-interlacing\n" +
			"Window 1 (PIP/UHD) (Enigma2 PIP Mode): " +
			"Up to 1/2 x 1/2 screen display, " +
			"576i50 de-interlacing\n" +
			"Display 0 (UHD) Encode Restrictions: " +
			"3840x2160p50"),
			#message 2
			_("placeholder message 2"),
			)

		if not self.option_enabled:
			idx = 0
			blv = ''
			for x in self.bootloaderList:
				if idx: blv += ', '
				blv += x
				idx += 1
			message = (_("Your box needs Bootloaderversion(s)\n%s\n to make compatible with Bootoptions!")%blv,) 
		self.session.open(MessageBox, message[self.option], MessageBox.TYPE_INFO)

	def rename(self):
		self.oldname = self.list[self.selection]
		if self.oldname:
			self.session.openWithCallback(self.renameCB, VirtualKeyBoard, title=_("Please enter new name:"), text=self.oldname)

	def renameCB(self, name):
		if name and name != 'bootname':
			if not path.exists('/boot/%s' %name) and path.exists('/boot/%s' %self.list[self.selection]):
				ret = system("mv -fn /boot/%s /boot/%s" %(self.list[self.selection],name))
				if ret:
					self.session.open(MessageBox, _('Rename failed!'), MessageBox.TYPE_ERROR)
				else:
					bootname = ''
					if path.exists('/boot/bootname'):
						f = open('/boot/bootname', 'r')
						bootname = f.readline().split('=')
						f.close()
					if bootname and bootname[1] == self.oldname:
						f = open('/boot/bootname', 'w')
						f.write('%s=%s' %(bootname[0],name))
						f.close()
						self.getCurrent()
						return
					elif self.bootname == self.oldname:
						self.getCurrent()
						return
					self.list[self.selection] = name
					self["config"].setText(_("Select Image: %s") %name)
			else:
				if not path.exists('/boot/%s' %self.list[self.selection]):
					txt = _("File not found - rename failed!")
				else:
					txt = _("Name already exists - rename failed!")
				self.session.open(MessageBox, txt, MessageBox.TYPE_ERROR)

	def getCurrent(self):
		'''
		#default
		Image 1: boot emmcflash0.kernel1 'root=/dev/mmcblk0p3 rw rootwait'
		Image 2: boot emmcflash0.kernel2 'root=/dev/mmcblk0p5 rw rootwait'
		Image 3: boot emmcflash0.kernel3 'root=/dev/mmcblk0p7 rw rootwait'
		Image 4: boot emmcflash0.kernel4 'root=/dev/mmcblk0p9 rw rootwait'
		#options
		Standard:     hd51_4.boxmode=1 (or no option)
		Experimental: hd51_4.boxmode=12
		#example
		boot emmcflash0.kernel1 'root=/dev/mmcblk0p3 rw rootwait hd51_4.boxmode=12'
		
		'''

		self.optionsList = (('boxmode=1', _('2160p60 without PiP (Standard)')), ('boxmode=12', _('2160p50 with PiP (Experimental)')))
		self.bootloaderList = ('v1.07-r19',)

		self.enable_bootnamefile = False #for compatibility set to False
		if not self.enable_bootnamefile and path.exists('/boot/bootname'):
			system("rm -f /boot/bootname")

		self.list = self.list_files("/boot")

		boot = ""
		if path.exists('/boot/STARTUP'):
			f = open('/boot/STARTUP', 'r')
			boot = f.readline()
			f.close()

		try:
			image = int(boot[22:23])
		except:
			image = _("File error - can not read")

		blv = ""
		if path.exists('/sys/firmware/devicetree/base/bolt/tag'):
			f = open('/sys/firmware/devicetree/base/bolt/tag', 'r')
			blv = f.readline().replace('\x00', '').replace('\n', '')
			f.close()

		self.selection = None
		self.currentOption = 0
		self.option_enabled = blv in self.bootloaderList

		if self.option_enabled:
			idx = 0
			for x in self.optionsList:
				if x[0] + "'" in boot or x[0] + " " in boot:
					self.currentOption = idx
					break
				idx += 1
			sep = ', '
		else:
			self.optionsList = (('',''),)
			sep = ''
			del self["actions"].actions['up']
			del self["actions"].actions['down']

		self.option = self.currentOption

		bootname = ''
		if path.exists('/boot/bootname'):
			f = open('/boot/bootname', 'r')
			bootname = f.readline().split('=')
			f.close()

		#read name from bootname file
		if bootname:
			idx = 0
			for x in self.list:
				if x == bootname[1]:
					self.selection = idx
					bootname = x
					break
				idx += 1
			if self.selection is None:
				idx = 0
				for x in self.list:
					if x == bootname[0]:
						self.selection = idx
						bootname = x
						break
					idx += 1
		#verify bootname
		if bootname in self.list and path.exists('/boot/%s' %bootname):
			f = open('/boot/%s' %bootname, 'r')
			line = f.readline()
			f.close()
			if line[22:23] != boot[22:23]:
				self.selection = None
		else:
			self.selection = None
		#bootname searching ...
		if self.selection is None:
			idx = 0
			for x in self.list:
				if path.exists('/boot/%s' %x):
					f = open('/boot/%s' %x, 'r')
					line = f.readline()
					f.close()
					if line[22:23] == boot[22:23]:
						bootname = x
						self.selection = idx
						break
					idx += 1
		#bootname not found
		if self.selection is None:
			bootname = _('unknown')
			self.selection = 0

		self.bootname = bootname
		self.startup()
		self.startup_option()
		self["description"].setText(_("Current Bootsettings: %s (Image %s)%s%s") %(bootname,image,sep,self.optionsList[self.currentOption][0]))

	def layoutFinished(self):
		self.setTitle(self.title)

	def startup_option(self):
		if self.option_enabled:
			self["options"].setText(_("Select Bootoption: %s") %self.optionsList[self.option][1])
		else:
			self["options"].setText(_("Select Bootoption: not supported - see info"))

	def startup(self):
		if len(self.list):
			self["config"].setText(_("Select Image: %s") %self.list[self.selection])
		else:
			self["config"].setText(_("Select Image: %s") %_("no image found"))
			del self["actions"].actions['left']
			del self["actions"].actions['right']
			del self["actions"].actions['green']
			del self["actions"].actions['yellow']
			del self["actions"].actions['ok']

	def save(self):
		print "[MultiBootStartup] select new startup: ", self.list[self.selection]
		system("cp -f /boot/%s /boot/STARTUP"%self.list[self.selection])

		f = open('/boot/STARTUP', 'r')
		boot = f.readline()
		f.close()

		checkboot = True #check command line on/off
		writeoption = already = failboot = False
		bootline = boot.split("=",1)[1].split(" ",1)[0]
		if checkboot and (not bootline in Harddisk.getextdevices("ext4") or ('boxmode' in boot and len(boot) > 76) or ('boxmode' not in boot and len(boot) > 58)):
			failboot = True
		elif self.option_enabled:
			for x in self.optionsList:
				if (x[0] + "'" in boot or x[0] + " " in boot) and x[0] != self.optionsList[self.option][0]:
					boot = boot.replace(x[0],self.optionsList[self.option][0])
					writeoption = True
					break
				elif (x[0] + "'" in boot or x[0] + " " in boot) and x[0] == self.optionsList[self.option][0]:
					already = True
					break
			if not (writeoption or already):
				if "boxmode" in boot:
					failboot = checkboot
				elif self.option: #write boxmode=1 is not needed ???
					boot = boot.replace("rootwait", "rootwait hd51_4.%s" %(self.optionsList[self.option][0]))
					writeoption = True

		if self.enable_bootnamefile:
			originalname = 'STARTUP_%s' %boot[22:23]
			f = open('/boot/bootname', 'w')
			if failboot:
				f.write('STARTUP_1=STARTUP_1')
			else:
				f.write('%s=%s' %(originalname,self.list[self.selection]))
			f.close()

		if failboot:
			print "[MultiBootStartup] wrong bootsettings: " + boot
			sboot = "boot emmcflash0.kernel1 'root=/dev/mmcblk0p3 rw rootwait'"
			if '/dev/mmcblk0p3' in Harddisk.getextdevices("ext4"):
				f = open('/boot/STARTUP', 'w')
				f.write(sboot)
				f.close()
				txt = "Next boot will start from Image 1."
			else:
				txt = "Alternative Image 1 partition for repair not found.\nCaution, next boot is starts with your settings!\n"
			restartbox = self.session.openWithCallback(self.restartBOX,MessageBox,_("Wrong Bootsettings detected!\n\n%s\n%s\nDo you want to reboot now?") %(boot,txt), MessageBox.TYPE_YESNO)
			return
		elif writeoption:
			f = open('/boot/STARTUP', 'w')
			f.write(boot)
			f.close()
		restartbox = self.session.openWithCallback(self.restartBOX,MessageBox,_("Do you want to reboot now with selected image?"), MessageBox.TYPE_YESNO)

	def cancel(self):
		self.close()

	def up(self):
		self.option = self.option - 1
		if self.option == -1:
			self.option = len(self.optionsList) - 1
		self.startup_option()

	def down(self):
		self.option = self.option + 1
		if self.option == len(self.optionsList):
			self.option = 0
		self.startup_option()

	def left(self):
		self.selection = self.selection - 1
		if self.selection == -1:
			self.selection = len(self.list) - 1
		self.startup()

	def right(self):
		self.selection = self.selection + 1
		if self.selection == len(self.list):
			self.selection = 0
		self.startup()

	def read_startup(self, FILE):
		self.file = FILE
		with open(self.file, 'r') as myfile:
			data=myfile.read().replace('\n', '')
		myfile.close()
		return data

	def list_files(self, PATH):
		files = []
		self.path = PATH
		for name in listdir(self.path):
			if path.isfile(path.join(self.path, name)):
				try:
					cmdline = self.read_startup("/boot/" + name).split("=",1)[1].split(" ",1)[0]
				except IndexError:
					continue
				if cmdline in Harddisk.getextdevices("ext4") and not name == "STARTUP":
					files.append(name)
		return files

	def restartBOX(self, answer):
		if answer is True:
			self.session.open(TryQuitMainloop, 2)
		else:
			self.close()
