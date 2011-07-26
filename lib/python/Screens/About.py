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
		self["ImageType"] = StaticText(_("Image:") + " " + about.getImageTypeString())

		self["TunerHeader"] = StaticText(_("Detected NIMs:"))

		fp_version = getFPVersion()
		if fp_version is None:
			fp_version = ""
		else:
			fp_version = _("Frontprocessor version: %d") % fp_version

		self["FPVersion"] = StaticText(fp_version)

		nims = nimmanager.nimList()
		for count in (0, 1, 2, 3):
			if count < len(nims):
				self["Tuner" + str(count)] = StaticText(nims[count])
			else:
				self["Tuner" + str(count)] = StaticText("")

		self["HDDHeader"] = StaticText(_("Detected HDD:"))
		hddlist = harddiskmanager.HDDList()
		hdd1 = _("None")
		hdd2 = ""
		hdd3 = ""
		for count in (0, 1, 2):
			if count < len(hddlist):
				if str(count) == '0':
					hddlist0 = hddlist[0]
					hdd = hddlist0[1]
					if int(hdd.free()) > 1024:
						freespace = int(hdd.free()) / 1024
						hdd1 = str(hdd.model()) + ' ' + str(hdd.capacity()) + ', (' + str(freespace) + ' ' + _("GB") + ' ' + _("free") + ')'
					else:
						hdd1 = str(hdd.model()) + ' ' + str(hdd.capacity()) + ', (' + str(hdd.free()) + ' ' + _("MB") + ' ' + _("free") + ')'
				elif str(count) == '1':
					hddlist1 = hddlist[1]
					hdd = hddlist1[1]
					if int(hdd.free()) > 1024:
						freespace = int(hdd.free()) / 1024
						hdd2 = str(hdd.model()) + ' ' + str(hdd.capacity()) + ', (' + str(freespace) + ' ' + _("GB") + ' ' + _("free") + ')'
					else:
						hdd2 = str(hdd.model()) + ' ' + str(hdd.capacity()) + ', (' + str(hdd.free()) + ' ' + _("MB") + ' ' + _("free") + ')'
				elif str(count) == '2':
					hddlist1 = hddlist[2]
					hdd = hddlist1[1]
					if int(hdd.free()) > 1024:
						freespace = int(hdd.free()) / 1024
						hdd3 = str(hdd.model()) + ' ' + str(hdd.capacity()) + ', (' + str(freespace) + ' ' + _("GB") + ' ' + _("free") + ')'
					else:
						hdd3 = str(hdd.model()) + ' ' + str(hdd.capacity()) + ', (' + str(hdd.free()) + ' ' + _("MB") + ' ' + _("free") + ')'

		self["hddA"] = StaticText(hdd1 + '\n' + hdd2 + '\n' + hdd3)

		self["actions"] = ActionMap(["SetupActions", "ColorActions", "TimerEditActions"], 
			{
				"cancel": self.close,
				"ok": self.close,
				"green": self.showTranslationInfo,
				'log': self.showAboutReleaseNotes
			})

	def showTranslationInfo(self):
		self.session.open(TranslationInfo)

	def showAboutReleaseNotes(self):
		self.session.open(AboutReleaseNotes)

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
			self["selected"] = StaticText("ViX:" + about.getImageVersionString() + ' ' + _('(Release)'))
		elif about.getImageTypeString() == 'Experimental':
			self["selected"] = StaticText("ViX:" + about.getImageVersionString() + ' ' + _('(Beta)'))

class TranslationInfo(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
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

		self["actions"] = ActionMap(["SetupActions"], 
			{
				"cancel": self.close,
				"ok": self.close,
			})

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
