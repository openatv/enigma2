from Screen import Screen
from Components.ActionMap import ActionMap
from Components.Sources.StaticText import StaticText
from Components.Harddisk import harddiskmanager
from Components.NimManager import nimmanager
from Components.About import about
from Components.config import config
from Components.ScrollLabel import ScrollLabel

from Tools.DreamboxHardware import getFPVersion
from os import path

class About(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		Screen.setTitle(self, _("System Information"))

		self["lab1"] = StaticText(_("Virtuosso Image Xtreme"))
		self["lab2"] = StaticText(_("By Team ViX"))
		if config.misc.boxtype.value == 'vuuno':
			self["lab3"] = StaticText(_("Support at") + " www.vuplus-support.co.uk")
			self["BoxType"] = StaticText(_("Hardware:") + " Vu+ Uno")
		elif config.misc.boxtype.value == 'vuuno':
			self["lab3"] = StaticText(_("Support at") + " www.vuplus-support.co.uk")
			self["BoxType"] = StaticText(_("Hardware:") + " Vu+ Uno")
		elif config.misc.boxtype.value == 'vuduo':
			self["lab3"] = StaticText(_("Support at") + " www.vuplus-support.co.uk")
			self["BoxType"] = StaticText(_("Hardware:") + " Vu+ Duo")
		elif config.misc.boxtype.value == 'et5000':
			self["lab3"] = StaticText(_("Support at") + " www.xtrend-support.co.uk")
			self["BoxType"] = StaticText(_("Hardware:") + " Xtrend ET5000")
		elif config.misc.boxtype.value == 'et9000':
			self["lab3"] = StaticText(_("Support at") + " www.xtrend-support.co.uk")
			self["BoxType"] = StaticText(_("Hardware:") + " Xtrend ET9000")
		else:
			self["lab3"] = StaticText(_("Support at") + " www.world-of-satellite.co.uk")
			self["BoxType"] = StaticText(_("Hardware:") + " " + config.misc.boxtype.value)
		self["ImageVersion"] = StaticText(_("Version:") + " " + about.getImageVersionString())
		self["BuildVersion"] = StaticText(_("Build:") + " " + about.getBuildVersionString())
		self["EnigmaVersion"] = StaticText(_("Last Update:") + " " + about.getLastUpdateString())
		self["KernelVersion"] = StaticText(_("Kernel:") + " " + about.getKernelVersionString())
		self["ImageType"] = StaticText(_("Image:") + " " + about.getImageTypeString())

		fp_version = getFPVersion()
		if fp_version is None:
			fp_version = ""
		else:
			fp_version = _("Frontprocessor version: %d") % fp_version
		self["FPVersion"] = StaticText(fp_version)

		self["actions"] = ActionMap(["SetupActions", "ColorActions", "TimerEditActions"], 
			{
				"cancel": self.close,
				"ok": self.close,
				"green": self.showTranslationInfo,
				'log': self.showAboutReleaseNotes
			})


		self["TranslationHeader"] = StaticText(_("Translation:"))
		# don't remove the string out of the _(), or it can't be "translated" anymore.
		# TRANSLATORS: Add here whatever should be shown in the "translator" about screen, up to 6 lines (use \n for newline)
		info = _("TRANSLATOR_INFO")

		if info == "TRANSLATOR_INFO":
			info = "(N/A)"

		infolines = _("").split("\n")
		infomap = {}
		for x in infolines:
			l = x.split(': ')
			if len(l) != 2:
				continue
			(type, value) = l
			infomap[type] = value
		print infomap

		self["TranslationInfo"] = StaticText(info)

		translator_name = infomap.get("Language-Team", "none")
		if translator_name == "none":
			translator_name = infomap.get("Last-Translator", "")

		self["TranslatorName"] = StaticText(translator_name)

	def showTranslationInfo(self):
		self.session.open(TranslationInfo)

	def showAboutReleaseNotes(self):
		self.session.open(AboutReleaseNotes)

	def createSummary(self):
		return AboutSummary

class Devices(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		Screen.setTitle(self, _("System Information"))
		
		self["TunerHeader"] = StaticText(_("Detected NIMs:"))
		niminfo = ""
		nims = nimmanager.nimList()
		for count in range(len(nims)):
			if niminfo:
				niminfo += "\n"
			niminfo += nims[count]
		self["nims"] = StaticText(niminfo)

		self["HDDHeader"] = StaticText(_("Detected Devices:"))
		hddlist = harddiskmanager.HDDList()
		hddinfo = ""
		if hddlist:
			for count in range(len(hddlist)):
				if hddinfo:
					hddinfo += "\n"
				hdd = hddlist[count][1]
				if int(hdd.free()) > 1024:
					hddinfo += "%s\n(%s, %d GB %s)" % (hdd.model(), hdd.capacity(), hdd.free()/1024, _("free"))
				else:
					hddinfo += "%s\n(%s, %d MB %s)" % (hdd.model(), hdd.capacity(), hdd.free(), _("free"))
		else:
			hddinfo = _("none")
		self["hdd"] = StaticText(hddinfo)

		self["MountsHeader"] = StaticText(_("Network Servers:"))
		mountinfo = ""
		f = open('/proc/mounts', 'r')
		for line in f.readlines():
			if mountinfo:
				mountinfo += "\n"
			parts = line.strip().split()
			if parts[0].startswith('192'):
				mountinfo += str(parts[0])
		f.close()
		self["mounts"] = StaticText(mountinfo)

		self["actions"] = ActionMap(["SetupActions", "ColorActions", "TimerEditActions"], 
			{
				"cancel": self.close,
				"ok": self.close,
			})

	def createSummary(self):
		return AboutSummary

class AboutSummary(Screen):
	skin = """
	<screen position="0,0" size="132,64">
		<widget source="selected" render="Label" position="0,0" size="124,32" font="Regular;16" />
	</screen>"""

	def __init__(self, session, parent):
		Screen.__init__(self, session, parent = parent)
		if about.getImageTypeString() == 'Release':
			self["selected"] = StaticText("ViX:" + about.getImageVersionString() + ' (R)')
		elif about.getImageTypeString() == 'Experimental':
			self["selected"] = StaticText("ViX:" + about.getImageVersionString() + ' (B)')

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
