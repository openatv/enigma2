from Screens.Screen import Screen
from Components.ActionMap import ActionMap
from Components.config import config, configfile, getConfigListEntry
from Components.ConfigList import ConfigListScreen
from Components.SystemInfo import SystemInfo
from Components.Sources.StaticText import StaticText
from Components.Pixmap import Pixmap
from Components.Console import Console
from Components.Label import Label
from enigma import getDesktop
from os import access, R_OK
from boxbranding import getBoxType, getBrandOEM

def InitOsd():
	SystemInfo["CanChange3DOsd"] = access('/proc/stb/fb/3dmode', R_OK) and True or False
	SystemInfo["CanChangeOsdAlpha"] = access('/proc/stb/video/alpha', R_OK) and True or False
	SystemInfo["CanChangeOsdPosition"] = access('/proc/stb/fb/dst_left', R_OK) and True or False
	SystemInfo["OsdSetup"] = SystemInfo["CanChangeOsdPosition"]
	if SystemInfo["CanChangeOsdAlpha"] == True or SystemInfo["CanChangeOsdPosition"] == True:
		SystemInfo["OsdMenu"] = True
	else:
		SystemInfo["OsdMenu"] = False
		
	if getBrandOEM() in ('fulan'):
		SystemInfo["CanChangeOsdPosition"] = False
		SystemInfo["CanChange3DOsd"] = False

	def setOSDLeft(configElement):
		if SystemInfo["CanChangeOsdPosition"]:
			f = open("/proc/stb/fb/dst_left", "w")
			f.write('%X' % configElement.value)
			f.close()
	config.osd.dst_left.addNotifier(setOSDLeft)

	def setOSDWidth(configElement):
		if SystemInfo["CanChangeOsdPosition"]:
			f = open("/proc/stb/fb/dst_width", "w")
			f.write('%X' % configElement.value)
			f.close()
	config.osd.dst_width.addNotifier(setOSDWidth)

	def setOSDTop(configElement):
		if SystemInfo["CanChangeOsdPosition"]:
			f = open("/proc/stb/fb/dst_top", "w")
			f.write('%X' % configElement.value)
			f.close()
	config.osd.dst_top.addNotifier(setOSDTop)

	def setOSDHeight(configElement):
		if SystemInfo["CanChangeOsdPosition"]:
			f = open("/proc/stb/fb/dst_height", "w")
			f.write('%X' % configElement.value)
			f.close()
	config.osd.dst_height.addNotifier(setOSDHeight)
	print 'Setting OSD position: %s %s %s %s' %  (config.osd.dst_left.value, config.osd.dst_width.value, config.osd.dst_top.value, config.osd.dst_height.value)

	def setOSDAlpha(configElement):
		if SystemInfo["CanChangeOsdAlpha"]:
			print 'Setting OSD alpha:', str(configElement.value)
			config.av.osd_alpha.setValue(configElement.value)
			f = open("/proc/stb/video/alpha", "w")
			f.write(str(configElement.value))
			f.close()
	config.osd.alpha.addNotifier(setOSDAlpha)

	def set3DMode(configElement):
		if SystemInfo["CanChange3DOsd"]:
			print 'Setting 3D mode:',configElement.value
			try:
				f = open("/proc/stb/fb/3dmode", "w")
				f.write(configElement.value)
				f.close()
			except:
				pass
	config.osd.threeDmode.addNotifier(set3DMode)

	def set3DZnorm(configElement):
		if SystemInfo["CanChange3DOsd"]:
			print 'Setting 3D depth:',configElement.value
			try:
				f = open("/proc/stb/fb/znorm", "w")
				f.write('%d' % int(configElement.value))
				f.close()
			except:
				pass	
	config.osd.threeDznorm.addNotifier(set3DZnorm)
	
class UserInterfacePositioner2(Screen, ConfigListScreen):
	if (getDesktop(0).size().width() == 1280):
		skin = """
			<screen position="center,center" size="1280,720" backgroundColor="#000000" title="OSD Adjustment" >

				<widget source="text" render="Label" position="200,110" zPosition="1" size="880,100" font="Regular;21" halign="center" valign="center" foregroundColor="yellow" backgroundColor="#1f771f" transparent="1" />
				<widget name="config" position="150,250" zPosition="1" size="980,150" font="Regular;20" halign="center" valign="center" transparent="1" />
				<widget source="status" render="Label" position="200,450" zPosition="1" size="880,80" font="Regular;21" halign="center" valign="center" foregroundColor="yellow" backgroundColor="#1f771f" transparent="1" />
				
				<eLabel backgroundColor="red" position="0,0" size="1280,1" zPosition="0" />
				<eLabel backgroundColor="red" position="0,719" size="1280,1" zPosition="0" />
				<eLabel backgroundColor="red" position="0,0" size="1,720" zPosition="0" />
				<eLabel backgroundColor="red" position="1279,0" size="1,720" zPosition="0" />
				<eLabel backgroundColor="green" position="25,25" size="1230,1" zPosition="0" />
				<eLabel backgroundColor="green" position="25,694" size="1230,1" zPosition="0" />
				<eLabel backgroundColor="green" position="25,25" size="1,670" zPosition="0" />
				<eLabel backgroundColor="green" position="1254,25" size="1,670" zPosition="0" />
				<eLabel backgroundColor="yellow" position="50,50" size="1180,1" zPosition="0" />
				<eLabel backgroundColor="yellow" position="50,669" size="1180,1" zPosition="0" />
				<eLabel backgroundColor="yellow" position="50,50" size="1,620" zPosition="0" />
				<eLabel backgroundColor="yellow" position="1229,50" size="1,620" zPosition="0" />
				<eLabel backgroundColor="blue" position="75,75" size="1130,1" zPosition="0" />
				<eLabel backgroundColor="blue" position="75,644" size="1130,1" zPosition="0" />
				<eLabel backgroundColor="blue" position="75,75" size="1,570" zPosition="0" />
				<eLabel backgroundColor="blue" position="1204,75" size="1,570" zPosition="0" />

				<eLabel backgroundColor="red" position="189,627" size="140,3" zPosition="0" />
				<eLabel backgroundColor="green" position="443,627" size="140,3" zPosition="0" />
				<eLabel backgroundColor="yellow" position="697,627" size="140,3" zPosition="0" />
				<eLabel backgroundColor="blue" position="951,627" size="140,3" zPosition="0" />
				<widget source="key_red" render="Label" position="189,605" zPosition="1" size="140,22" font="Regular;18" halign="center" valign="center" backgroundColor="#1f771f" transparent="1" />
				<widget source="key_green" render="Label" position="443,605" zPosition="1" size="140,22" font="Regular;18" halign="center" valign="center" backgroundColor="#1f771f" transparent="1" />
				<widget source="key_yellow" render="Label" position="697,605" zPosition="1" size="140,22" font="Regular;18" halign="center" valign="center" backgroundColor="#1f771f" transparent="1" />
				<widget source="key_blue" render="Label" position="951,605" zPosition="1" size="140,22" font="Regular;18" halign="center" valign="center" backgroundColor="#1f771f" transparent="1" />

			</screen>"""

	elif (getDesktop(0).size().width() == 1024):
		skin = """
			<screen position="center,center" size="1024,576" backgroundColor="#000000" title="OSD Adjustment" >

				<widget source="text" render="Label" position="200,180" zPosition="1" size="624,100" font="Regular;21" halign="center" valign="center" foregroundColor="yellow" backgroundColor="#1f771f" transparent="1" />
				<widget source="config" render="Label" position="100,180" zPosition="1" size="824,50" font="Regular;24" halign="center" valign="center" transparent="1" />
				<widget source="status" render="Label" position="200,450" zPosition="1" size="624,80" font="Regular;21" halign="center" valign="center" foregroundColor="yellow" backgroundColor="#1f771f" transparent="1" />
				
				<eLabel backgroundColor="red" position="0,0" size="1024,1" zPosition="0" />
				<eLabel backgroundColor="red" position="0,575" size="1024,1" zPosition="0" />
				<eLabel backgroundColor="red" position="0,0" size="1,576" zPosition="0" />
				<eLabel backgroundColor="red" position="1023,0" size="1,576" zPosition="0" />
				<eLabel backgroundColor="green" position="25,25" size="974,1" zPosition="0" />
				<eLabel backgroundColor="green" position="25,551" size="974,1" zPosition="0" />
				<eLabel backgroundColor="green" position="25,25" size="1,526" zPosition="0" />
				<eLabel backgroundColor="green" position="999,25" size="1,526" zPosition="0" />
				<eLabel backgroundColor="yellow" position="50,50" size="924,1" zPosition="0" />
				<eLabel backgroundColor="yellow" position="50,526" size="924,1" zPosition="0" />
				<eLabel backgroundColor="yellow" position="50,50" size="1,476" zPosition="0" />
				<eLabel backgroundColor="yellow" position="974,50" size="1,476" zPosition="0" />
				<eLabel backgroundColor="blue" position="75,75" size="874,1" zPosition="0" />
				<eLabel backgroundColor="blue" position="75,501" size="874,1" zPosition="0" />
				<eLabel backgroundColor="blue" position="75,75" size="1,426" zPosition="0" />
				<eLabel backgroundColor="blue" position="949,75" size="1,426" zPosition="0" />

				<eLabel backgroundColor="red" position="138,477" size="140,3" zPosition="0" />
				<eLabel backgroundColor="green" position="341,477" size="140,3" zPosition="0" />
				<eLabel backgroundColor="yellow" position="544,477" size="140,3" zPosition="0" />
				<eLabel backgroundColor="blue" position="747,477" size="140,3" zPosition="0" />
				<widget source="key_red" render="Label" position="138,455" zPosition="1" size="140,22" font="Regular;18" halign="center" valign="center" backgroundColor="#1f771f" transparent="1" />
				<widget source="key_green" render="Label" position="341,455" zPosition="1" size="140,22" font="Regular;18" halign="center" valign="center" backgroundColor="#1f771f" transparent="1" />
				<widget source="key_yellow" render="Label" position="544,455" zPosition="1" size="140,22" font="Regular;18" halign="center" valign="center" backgroundColor="#1f771f" transparent="1" />
				<widget source="key_blue" render="Label" position="747,455" zPosition="1" size="140,22" font="Regular;18" halign="center" valign="center" backgroundColor="#1f771f" transparent="1" />
			</screen>"""

	else:
		skin = """
			<screen position="center,center" size="720,576" backgroundColor="#000000" title="OSD Adjustment" >

				<widget source="text" render="Label" position="75,80" zPosition="1" size="570,100" font="Regular;21" halign="center" valign="center" foregroundColor="yellow" backgroundColor="#1f771f" transparent="1" />
				<widget source="config" render="Label" position="75,180" zPosition="1" size="570,50" font="Regular;21" halign="center" valign="center" transparent="1" />
				<widget source="status" render="Label" position="75,450" zPosition="1" size="570,80" font="Regular;21" halign="center" valign="center" foregroundColor="yellow" backgroundColor="#1f771f" transparent="1" />
				
				<eLabel backgroundColor="red" position="0,0" size="720,1" zPosition="0" />
				<eLabel backgroundColor="red" position="0,575" size="720,1" zPosition="0" />
				<eLabel backgroundColor="red" position="0,0" size="1,576" zPosition="0" />
				<eLabel backgroundColor="red" position="719,0" size="1,576" zPosition="0" />
				<eLabel backgroundColor="green" position="25,25" size="670,1" zPosition="0" />
				<eLabel backgroundColor="green" position="25,551" size="670,1" zPosition="0" />
				<eLabel backgroundColor="green" position="25,25" size="1,526" zPosition="0" />
				<eLabel backgroundColor="green" position="694,25" size="1,526" zPosition="0" />
				<eLabel backgroundColor="yellow" position="50,50" size="620,1" zPosition="0" />
				<eLabel backgroundColor="yellow" position="50,526" size="620,1" zPosition="0" />
				<eLabel backgroundColor="yellow" position="50,50" size="1,476" zPosition="0" />
				<eLabel backgroundColor="yellow" position="670,50" size="1,476" zPosition="0" />
				<eLabel backgroundColor="blue" position="75,75" size="570,1" zPosition="0" />
				<eLabel backgroundColor="blue" position="75,501" size="570,1" zPosition="0" />
				<eLabel backgroundColor="blue" position="75,75" size="1,426" zPosition="0" />
				<eLabel backgroundColor="blue" position="645,75" size="1,426" zPosition="0" />

				<eLabel backgroundColor="red" position="80,477" size="140,3" zPosition="0" />
				<eLabel backgroundColor="green" position="220,477" size="140,3" zPosition="0" />
				<eLabel backgroundColor="yellow" position="360,477" size="140,3" zPosition="0" />
				<eLabel backgroundColor="blue" position="500,477" size="140,3" zPosition="0" />
				<widget source="key_red" render="Label" position="80,455" zPosition="1" size="140,22" font="Regular;18" halign="center" valign="center" backgroundColor="#1f771f" transparent="1" />
				<widget source="key_green" render="Label" position="220,455" zPosition="1" size="140,22" font="Regular;18" halign="center" valign="center" backgroundColor="#1f771f" transparent="1" />
				<widget source="key_yellow" render="Label" position="360,455" zPosition="1" size="140,22" font="Regular;18" halign="center" valign="center" backgroundColor="#1f771f" transparent="1" />
				<widget source="key_blue" render="Label" position="500,455" zPosition="1" size="140,22" font="Regular;18" halign="center" valign="center" backgroundColor="#1f771f" transparent="1" />

			</screen>"""
	def __init__(self, session):
		Screen.__init__(self, session)
		self.setup_title = _("Position Setup")
#		self.Console = Console()
		self["status"] = StaticText()
		self["key_red"] = StaticText(_("Cancel"))
		self["key_green"] = StaticText(_("save"))
		self["key_yellow"] = StaticText(_("Defaults"))
		
		self["title"] = StaticText(_("OSD Adjustment"))
		self["text"] = StaticText(_("Please setup your user interface by adjusting the values till the edges of the red box are touching the edges of your TV.\nWhen you are ready press green to continue."))

		self["actions"] = ActionMap(["SetupActions", "ColorActions"],
			{
				"cancel": self.keyCancel,
				"save": self.keySave,
				"left": self.keyLeft,
				"right": self.keyRight,
				"yellow": self.keyDefault,
			}, -2)

		self.onChangedEntry = [ ]
		self.list = []
		ConfigListScreen.__init__(self, self.list, session = self.session, on_change = self.changedEntry)
		if SystemInfo["CanChangeOsdAlpha"]:
			self.list.append(getConfigListEntry(_("User interface visibility"), config.osd.alpha, _("This option lets you adjust the transparency of the user interface")))
			self.list.append(getConfigListEntry(_("Teletext base visibility"), config.osd.alpha_teletext, _("Base transparency for teletext, more options available within teletext screen.")))
			self.list.append(getConfigListEntry(_("Web browser base visibility"), config.osd.alpha_webbrowser, _("Base transparency for OpenOpera web browser")))
		if SystemInfo["CanChangeOsdPosition"]:
			self.list.append(getConfigListEntry(_("Move Left/Right"), config.osd.dst_left, _("Use the Left/Right buttons on your remote to move the user interface left/right")))
			self.list.append(getConfigListEntry(_("Width"), config.osd.dst_width, _("Use the Left/Right buttons on your remote to adjust the size of the user interface. Left button decreases the size, Right increases the size.")))
			self.list.append(getConfigListEntry(_("Move Up/Down"), config.osd.dst_top, _("Use the Left/Right buttons on your remote to move the user interface up/down")))
			self.list.append(getConfigListEntry(_("Height"), config.osd.dst_height, _("Use the Left/Right buttons on your remote to adjust the size of the user interface. Left button decreases the size, Right increases the size.")))
		self["config"].list = self.list
		self["config"].l.setList(self.list)

		self.onLayoutFinish.append(self.layoutFinished)
		if not self.selectionChanged in self["config"].onSelectionChanged:
			self["config"].onSelectionChanged.append(self.selectionChanged)
		self.selectionChanged()

	def selectionChanged(self):
		if getBoxType().startswith('azbox'):
			pass
		else:
			self["status"].setText(self["config"].getCurrent()[2])

	def layoutFinished(self):
		self.setTitle(_(self.setup_title))
#		self.Console.ePopen('/usr/bin/showiframe /usr/share/enigma2/hd-testcard.mvi')

	def createSummary(self):
		from Screens.Setup import SetupSummary
		return SetupSummary

	# for summary:
	def changedEntry(self):
		for x in self.onChangedEntry:
			x()

	def getCurrentEntry(self):
		return self["config"].getCurrent()[0]

	def getCurrentValue(self):
		return str(self["config"].getCurrent()[1].getText())

	def keyLeft(self):
		ConfigListScreen.keyLeft(self)
		self.setPreviewPosition()

	def keyRight(self):
		ConfigListScreen.keyRight(self)
		self.setPreviewPosition()

	def keyDefault(self):
		config.osd.alpha.setValue(255)
		config.osd.alpha_teletext.setValue(255)
		config.osd.alpha_webbrowser.setValue(255)

		config.osd.dst_left.setValue(0)
		config.osd.dst_width.setValue(720)
		config.osd.dst_top.setValue(0)
		config.osd.dst_height.setValue(576)

	def setPreviewPosition(self):
		size_w = getDesktop(0).size().width()
		size_h = getDesktop(0).size().height()
		dsk_w = int(float(size_w)) / float(720)
		dsk_h = int(float(size_h)) / float(576)
		dst_left = int(config.osd.dst_left.value)
		dst_width = int(config.osd.dst_width.value)
		dst_top = int(config.osd.dst_top.value)
		dst_height = int(config.osd.dst_height.value)
		while dst_width + (dst_left / float(dsk_w)) >= 720.5 or dst_width + dst_left > 720:
			dst_width = int(dst_width) - 1
		while dst_height + (dst_top / float(dsk_h)) >= 576.5 or dst_height + dst_top > 576:
			dst_height = int(dst_height) - 1

		config.osd.dst_left.setValue(dst_left)
		config.osd.dst_width.setValue(dst_width)
		config.osd.dst_top.setValue(dst_top)
		config.osd.dst_height.setValue(dst_height)
		print 'Setting OSD position: %s %s %s %s' %  (config.osd.dst_left.value, config.osd.dst_width.value, config.osd.dst_top.value, config.osd.dst_height.value)

	def saveAll(self):
		for x in self["config"].list:
			x[1].save()
		configfile.save()

	# keySave and keyCancel are just provided in case you need them.
	# you have to call them by yourself.
	def keySave(self):
		self.saveAll()
		self.close()

	def cancelConfirm(self, result):
		if not result:
			return

		for x in self["config"].list:
			x[1].cancel()
		self.close()

	def keyCancel(self):
		if self["config"].isChanged():
			from Screens.MessageBox import MessageBox
			self.session.openWithCallback(self.cancelConfirm, MessageBox, _("Really close without saving settings?"), default = False)
		else:
			self.close()

	def run(self):
		config.osd.dst_left.save()
		config.osd.dst_width.save()
		config.osd.dst_top.save()
		config.osd.dst_height.save()
		configfile.save()
		self.close()

class UserInterfacePositioner(Screen, ConfigListScreen):
	def __init__(self, session):
		Screen.__init__(self, session)
		self.setup_title = _("Position Setup")
#		self.Console = Console()
		self["status"] = StaticText()
		self["key_red"] = StaticText(_("Cancel"))
		self["key_green"] = StaticText(_("save"))
		self["key_yellow"] = StaticText(_("Defaults"))
		

		self["actions"] = ActionMap(["SetupActions", "ColorActions"],
			{
				"cancel": self.keyCancel,
				"save": self.keySave,
				"left": self.keyLeft,
				"right": self.keyRight,
				"yellow": self.keyDefault,
			}, -2)

		self.onChangedEntry = [ ]
		self.list = []
		ConfigListScreen.__init__(self, self.list, session = self.session, on_change = self.changedEntry)
		if SystemInfo["CanChangeOsdAlpha"] == True:
			self.list.append(getConfigListEntry(_("User interface visibility"), config.osd.alpha, _("This option lets you adjust the transparency of the user interface")))
			self.list.append(getConfigListEntry(_("Teletext base visibility"), config.osd.alpha_teletext, _("Base transparency for teletext, more options available within teletext screen.")))
			self.list.append(getConfigListEntry(_("Web browser base visibility"), config.osd.alpha_webbrowser, _("Base transparency for OpenOpera web browser")))
		if SystemInfo["CanChangeOsdPosition"] == True:
			self.list.append(getConfigListEntry(_("Move Left/Right"), config.osd.dst_left, _("Use the Left/Right buttons on your remote to move the user interface left/right")))
			self.list.append(getConfigListEntry(_("Width"), config.osd.dst_width, _("Use the Left/Right buttons on your remote to adjust the size of the user interface. Left button decreases the size, Right increases the size.")))
			self.list.append(getConfigListEntry(_("Move Up/Down"), config.osd.dst_top, _("Use the Left/Right buttons on your remote to move the user interface up/down")))
			self.list.append(getConfigListEntry(_("Height"), config.osd.dst_height, _("Use the Left/Right buttons on your remote to adjust the size of the user interface. Left button decreases the size, Right increases the size.")))
		self["config"].list = self.list
		self["config"].l.setList(self.list)

		self.onLayoutFinish.append(self.layoutFinished)
		if not self.selectionChanged in self["config"].onSelectionChanged:
			self["config"].onSelectionChanged.append(self.selectionChanged)
		self.selectionChanged()

	def selectionChanged(self):
		if getBoxType().startswith('azbox'):
			pass
		else:
			self["status"].setText(self["config"].getCurrent()[2])

	def layoutFinished(self):
		self.setTitle(_(self.setup_title))
#		self.Console.ePopen('/usr/bin/showiframe /usr/share/enigma2/hd-testcard.mvi')

	def createSummary(self):
		from Screens.Setup import SetupSummary
		return SetupSummary

	# for summary:
	def changedEntry(self):
		for x in self.onChangedEntry:
			x()

	def getCurrentEntry(self):
		return self["config"].getCurrent()[0]

	def getCurrentValue(self):
		return str(self["config"].getCurrent()[1].getText())

	def keyLeft(self):
		ConfigListScreen.keyLeft(self)
		self.setPreviewPosition()

	def keyRight(self):
		ConfigListScreen.keyRight(self)
		self.setPreviewPosition()

	def keyDefault(self):
		config.osd.alpha.setValue(255)
		config.osd.alpha_teletext.setValue(255)
		config.osd.alpha_webbrowser.setValue(255)

		config.osd.dst_left.setValue(0)
		config.osd.dst_width.setValue(720)
		config.osd.dst_top.setValue(0)
		config.osd.dst_height.setValue(576)

	def setPreviewPosition(self):
		size_w = getDesktop(0).size().width()
		size_h = getDesktop(0).size().height()
		dsk_w = int(float(size_w)) / float(720)
		dsk_h = int(float(size_h)) / float(576)
		dst_left = int(config.osd.dst_left.value)
		dst_width = int(config.osd.dst_width.value)
		dst_top = int(config.osd.dst_top.value)
		dst_height = int(config.osd.dst_height.value)
		while dst_width + (dst_left / float(dsk_w)) >= 720.5 or dst_width + dst_left > 720:
			dst_width = int(dst_width) - 1
		while dst_height + (dst_top / float(dsk_h)) >= 576.5 or dst_height + dst_top > 576:
			dst_height = int(dst_height) - 1

		config.osd.dst_left.setValue(dst_left)
		config.osd.dst_width.setValue(dst_width)
		config.osd.dst_top.setValue(dst_top)
		config.osd.dst_height.setValue(dst_height)
		print 'Setting OSD position: %s %s %s %s' %  (config.osd.dst_left.value, config.osd.dst_width.value, config.osd.dst_top.value, config.osd.dst_height.value)

	def saveAll(self):
		for x in self["config"].list:
			x[1].save()
		configfile.save()

	# keySave and keyCancel are just provided in case you need them.
	# you have to call them by yourself.
	def keySave(self):
		self.saveAll()
		self.close()

	def cancelConfirm(self, result):
		if not result:
			return

		for x in self["config"].list:
			x[1].cancel()
		self.close()

	def keyCancel(self):
		if self["config"].isChanged():
			from Screens.MessageBox import MessageBox
			self.session.openWithCallback(self.cancelConfirm, MessageBox, _("Really close without saving settings?"), default = False)
		else:
			self.close()

	def run(self):
		config.osd.dst_left.save()
		config.osd.dst_width.save()
		config.osd.dst_top.save()
		config.osd.dst_height.save()
		configfile.save()
		self.close()
		
class OSD3DSetupScreen(Screen, ConfigListScreen):
	def __init__(self, session):
		Screen.__init__(self, session)
		self.setup_title = _("OSD 3D Setup")
		self.skinName = "Setup"
		self["status"] = StaticText()		

		self["key_red"] = StaticText(_("Cancel"))
		self["key_green"] = StaticText(_("OK"))

		self["actions"] = ActionMap(["SetupActions"],
			{
				"cancel": self.keyCancel,
				"save": self.keySave,
			}, -2)

		self.onChangedEntry = [ ]
		self.list = []
		ConfigListScreen.__init__(self, self.list, session = self.session, on_change = self.changedEntry)
		self.list.append(getConfigListEntry(_("3D Mode"), config.osd.threeDmode, _("This option lets you choose the 3D mode")))
		self.list.append(getConfigListEntry(_("Depth"), config.osd.threeDznorm, _("This option lets you adjust the 3D depth")))
		self.list.append(getConfigListEntry(_("Show in extensions list ?"), config.osd.show3dextensions, _("This option lets you show the option in the extension screen")))
		self["config"].list = self.list
		self["config"].l.setList(self.list)

		self.onLayoutFinish.append(self.layoutFinished)
		if not self.selectionChanged in self["config"].onSelectionChanged:
			self["config"].onSelectionChanged.append(self.selectionChanged)
		self.selectionChanged()

	def selectionChanged(self):
		self["status"].setText(self["config"].getCurrent()[2])

	def layoutFinished(self):
		self.setTitle(_(self.setup_title))

	def createSummary(self):
		from Screens.Setup import SetupSummary
		return SetupSummary

	# for summary:
	def changedEntry(self):
		for x in self.onChangedEntry:
			x()

	def getCurrentEntry(self):
		return self["config"].getCurrent()[0]

	def getCurrentValue(self):
		return str(self["config"].getCurrent()[1].getText())

	def saveAll(self):
		for x in self["config"].list:
			x[1].save()
		configfile.save()

	# keySave and keyCancel are just provided in case you need them.
	# you have to call them by yourself.
	def keySave(self):
		self.saveAll()
		self.close()

	def cancelConfirm(self, result):
		if not result:
			return

		for x in self["config"].list:
			x[1].cancel()
		self.close()

	def keyCancel(self):
		if self["config"].isChanged():
			from Screens.MessageBox import MessageBox
			self.session.openWithCallback(self.cancelConfirm, MessageBox, _("Really close without saving settings?"))
		else:
			self.close()
