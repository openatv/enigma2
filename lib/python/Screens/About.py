from Screen import Screen
from Components.ActionMap import ActionMap
from Components.Sources.StaticText import StaticText
from Components.Harddisk import harddiskmanager
from Components.NimManager import nimmanager
from Components.About import about
from Components.config import config
from Components.ScrollLabel import ScrollLabel
from Components.Console import Console
from enigma import eTimer

from Tools.DreamboxHardware import getFPVersion
from os import path, popen

class About(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		Screen.setTitle(self, _("Image Information"))
		self.populate()
		
		self["actions"] = ActionMap(["SetupActions", "ColorActions", "TimerEditActions"], 
			{
				"cancel": self.close,
				"ok": self.close,
				'log': self.showAboutReleaseNotes,
				"up": self["AboutScrollLabel"].pageUp,
				"down": self["AboutScrollLabel"].pageDown
			})

	def populate(self):
		self["lab1"] = StaticText(_("Virtuosso Image Xtreme"))
		self["lab2"] = StaticText(_("By Team ViX"))
		if config.misc.boxtype.value == 'vuuno':
			self["lab3"] = StaticText(_("Support at") + " www.vuplus-support.co.uk")
			self["BoxType"] = StaticText(_("Hardware:") + " Vu+ Uno")
			AboutText = _("Hardware:") + " Vu+ Uno\n"
		elif config.misc.boxtype.value == 'vusolo':
			self["lab3"] = StaticText(_("Support at") + " www.vuplus-support.co.uk")
			self["BoxType"] = StaticText(_("Hardware:") + " Vu+ Solo")
			AboutText = _("Hardware:") + " Vu+ Solo\n"
		elif config.misc.boxtype.value == 'vuduo':
			self["lab3"] = StaticText(_("Support at") + " www.vuplus-support.co.uk")
			self["BoxType"] = StaticText(_("Hardware:") + " Vu+ Duo")
			AboutText = _("Hardware:") + " Vu+ Duo\n"
		elif config.misc.boxtype.value == 'et5x00':
			self["lab3"] = StaticText(_("Support at") + " www.xtrend-support.co.uk")
			self["BoxType"] = StaticText(_("Hardware:") + " Xtrend ET5x00 Series")
			AboutText = _("Hardware:") + "  Xtrend ET5x00 Series\n"
		elif config.misc.boxtype.value == 'et6x00':
			self["lab3"] = StaticText(_("Support at") + " www.xtrend-support.co.uk")
			self["BoxType"] = StaticText(_("Hardware:") + " Xtrend ET6x00 Series")
			AboutText = _("Hardware:") + "  Xtrend ET6x00 Series\n"
		elif config.misc.boxtype.value == 'et9x00':
			self["lab3"] = StaticText(_("Support at") + " www.xtrend-support.co.uk")
			self["BoxType"] = StaticText(_("Hardware:") + " Xtrend ET9x00 Series")
		elif config.misc.boxtype.value == 'maram9':
			self["lab3"] = StaticText(_("Support at") + " www.mara-support.co.uk")
			self["BoxType"] = StaticText(_("Hardware:") + " MarA M9")
			AboutText = _("Hardware:") + " Xtrend ET9x00 Series\n"
		else:
			self["lab3"] = StaticText(_("Support at") + " www.world-of-satellite.co.uk")
			self["BoxType"] = StaticText(_("Hardware:") + " " + config.misc.boxtype.value)
			AboutText = _("Hardware:") + " " + config.misc.boxtype.value + "\n"

		self["KernelVersion"] = StaticText(_("Kernel:") + " " + about.getKernelVersionString())
		AboutText += _("Kernel:") + " " + about.getKernelVersionString() + "\n"
		self["DriversVersion"] = StaticText(_("Drivers:") + " " + about.getDriversString())
		AboutText += _("Drivers:") + " " + about.getDriversString() + "\n"
		self["ImageType"] = StaticText(_("Image:") + " " + about.getImageTypeString())
		AboutText += _("Image:") + " " + about.getImageTypeString() + "\n"
		self["ImageVersion"] = StaticText(_("Version:") + " " + about.getImageVersionString())
		AboutText += _("Version:") + " " + about.getImageVersionString() + "\n"
		self["BuildVersion"] = StaticText(_("Build:") + " " + about.getBuildVersionString())
		AboutText += _("Build:") + " " + about.getBuildVersionString() + "\n"
		self["EnigmaVersion"] = StaticText(_("Last Update:") + " " + about.getLastUpdateString())
		AboutText += _("Last Update:") + " " + about.getLastUpdateString() + "\n\n"

		fp_version = getFPVersion()
		if fp_version is None:
			fp_version = ""
		elif fp_version != 0:
			fp_version = _("Frontprocessor version: %d") % fp_version
			AboutText += fp_version + "\n"
		self["FPVersion"] = StaticText(fp_version)

		self["TranslationHeader"] = StaticText(_("Translation:"))
		AboutText += _("Translation:") + "\n"

		# don't remove the string out of the _(), or it can't be "translated" anymore.
		# TRANSLATORS: Add here whatever should be shown in the "translator" about screen, up to 6 lines (use \n for newline)
		info = _("TRANSLATOR_INFO")

		if info == _("TRANSLATOR_INFO"):
			info = ""

		infolines = _("").split("\n")
		infomap = {}
		for x in infolines:
			l = x.split(': ')
			if len(l) != 2:
				continue
			(type, value) = l
			infomap[type] = value

		translator_name = infomap.get("Language-Team", "none")
		if translator_name == "none":
			translator_name = infomap.get("Last-Translator", "")

		self["TranslatorName"] = StaticText(translator_name)
		AboutText += translator_name + "\n\n"

		self["TranslationInfo"] = StaticText(info)
		AboutText += info

		self["AboutScrollLabel"] = ScrollLabel(AboutText)

	def showAboutReleaseNotes(self):
		self.session.open(AboutReleaseNotes)

	def createSummary(self):
		return AboutSummary

class Devices(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		Screen.setTitle(self, _("Device Information"))
		self["TunerHeader"] = StaticText(_("Detected NIMs:"))
		self["HDDHeader"] = StaticText(_("Detected Devices:"))
		self["MountsHeader"] = StaticText(_("Network Servers:"))
		self["nims"] = StaticText()
		self["hdd"] = StaticText()
		self["mounts"] = StaticText()
		self.activityTimer = eTimer()
		self.activityTimer.timeout.get().append(self.populate2)
		self.populate()
		
		self["actions"] = ActionMap(["SetupActions", "ColorActions", "TimerEditActions"], 
			{
				"cancel": self.close,
				"ok": self.close,
			})

	def populate(self):
		scanning = _("Wait please while scanning for devices...")
		self["nims"].setText(scanning)
		self["hdd"].setText(scanning)
		self['mounts'].setText(scanning)
		self.activityTimer.start(10)

	def populate2(self):
		self.activityTimer.stop()
		self.Console = Console()
		niminfo = ""
		nims = nimmanager.nimList()
		for count in range(len(nims)):
			if niminfo:
				niminfo += "\n"
			niminfo += nims[count]
		self["nims"].setText(niminfo)

		hddlist = harddiskmanager.HDDList()
		hddinfo = ""
		if hddlist:
			for count in range(len(hddlist)):
				if hddinfo:
					hddinfo += "\n"
				hdd = hddlist[count][1]
				if int(hdd.free()) > 1024:
					hddinfo += "%s (%s, %d GB %s)" % (hdd.model(), hdd.capacity(), hdd.free()/1024, _("free"))
				else:
					hddinfo += "%s (%s, %d MB %s)" % (hdd.model(), hdd.capacity(), hdd.free(), _("free"))
		else:
			hddinfo = _("none")
		self["hdd"].setText(hddinfo)

		self.mountinfo = ""
		f = open('/proc/mounts', 'r')
		for line in f.readlines():
			self.parts = line.strip().split()
			if self.parts[0].startswith('192') or self.parts[0].startswith('//192'):
				self.Console.ePopen("df -mh " + self.parts[1] + " | grep -v '^Filesystem'", self.Stage1Complete)
		f.close()

	def Stage1Complete(self,result, retval, extra_args = None):
		mount = str(result).replace('\n','')
		mount = mount.split()
		ipaddress = mount[0]
		mounttotal = mount[1]
		mountfree = mount[3]
		if self.mountinfo:
			self.mountinfo += "\n"
		self.mountinfo += "%s (%sB, %sB %s)" % (ipaddress, mounttotal, mountfree, _("free")) 
		self["mounts"].setText(self.mountinfo)

	def createSummary(self):
		return AboutSummary

class SystemInfo(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		Screen.setTitle(self, _("System Information"))
		self.skinName = "About"
		self.populate()
		
		self["actions"] = ActionMap(["SetupActions", "ColorActions", "TimerEditActions"], 
			{
				"cancel": self.close,
				"ok": self.close,
			})

	def populate(self):
		out_lines = file("/proc/meminfo").readlines()
		for lidx in range(len(out_lines)-1):
			tstLine = out_lines[lidx].split()
			if "MemTotal:" in tstLine:
				MemTotal = out_lines[lidx].split()
				AboutText = _("Total Memory:") + " " + MemTotal[1] + "\n"
			if "MemFree:" in tstLine:
				MemFree = out_lines[lidx].split()
				AboutText += _("Free Memory:") + " " + MemFree[1] + "\n"
			if "SwapTotal:" in tstLine:
				SwapTotal = out_lines[lidx].split()
				AboutText += _("Total Swap:") + " " + SwapTotal[1] + "\n"
			if "SwapFree:" in tstLine:
				SwapFree = out_lines[lidx].split()
				AboutText += _("Free Swap:") + " " + SwapFree[1] + "\n"

		self["AboutScrollLabel"] = ScrollLabel(AboutText)

	def createSummary(self):
		return AboutSummary

class AboutSummary(Screen):
	skin = """
	<screen name="AboutSummary" position="0,0" size="132,64">
		<widget source="selected" render="Label" position="0,0" size="124,32" font="Regular;16" />
	</screen>"""

	def __init__(self, session, parent):
		Screen.__init__(self, session, parent = parent)
		if about.getImageTypeString() == 'Release':
			self["selected"] = StaticText("ViX:" + about.getImageVersionString() + ' (R)')
		elif about.getImageTypeString() == 'Experimental':
			self["selected"] = StaticText("ViX:" + about.getImageVersionString() + ' (B)')
		if config.misc.boxtype.value == 'vuuno':
			self["BoxType"] = StaticText(_("Hardware:") + " Vu+ Uno")
		elif config.misc.boxtype.value == 'vusolo':
			self["BoxType"] = StaticText(_("Hardware:") + " Vu+ Solo")
		elif config.misc.boxtype.value == 'vuduo':
			self["BoxType"] = StaticText(_("Hardware:") + " Vu+ Duo")
		elif config.misc.boxtype.value == 'et5x00':
			self["BoxType"] = StaticText(_("Hardware:") + " Xtrend ET5x00 Series")
		elif config.misc.boxtype.value == 'et6x00':
			self["BoxType"] = StaticText(_("Hardware:") + " Xtrend ET6x00 Series")
		elif config.misc.boxtype.value == 'et9x00':
			self["BoxType"] = StaticText(_("Hardware:") + " Xtrend ET9x00 Series")
		elif config.misc.boxtype.value == 'maram9':
			self["BoxType"] = StaticText(_("Hardware:") + " MarA M9")
		else:
			self["BoxType"] = StaticText(_("Hardware:") + " " + config.misc.boxtype.value)
		self["KernelVersion"] = StaticText(_("Kernel:") + " " + about.getKernelVersionString())
		self["ImageType"] = StaticText(_("Image:") + " " + about.getImageTypeString())
		self["ImageVersion"] = StaticText(_("Version:") + " " + about.getImageVersionString() + "   " + _("Build:") + " " + about.getBuildVersionString())
		self["EnigmaVersion"] = StaticText(_("Last Update:") + " " + about.getLastUpdateString())

class AboutReleaseNotes(Screen):
	skin = """
<screen name="AboutReleaseNotes" position="center,center" size="560,400" title="Release Notes" >
	<widget name="list" position="0,0" size="560,400" font="Regular;16" />
</screen>"""
	def __init__(self, session):
		self.session = session
		Screen.__init__(self, session)
		self.skinName = "AboutReleaseNotes"
		if path.exists('/etc/releasenotes'):
			releasenotes = file('/etc/releasenotes').read()
		else:
			releasenotes = ""
		self["list"] = ScrollLabel(str(releasenotes))
		self["setupActions"] = ActionMap(["SetupActions", "ColorActions", "DirectionActions"],
		{
			"cancel": self.cancel,
			"ok": self.cancel,
			"up": self["list"].pageUp,
			"down": self["list"].pageDown
		}, -2)

	def cancel(self):
		self.close()
