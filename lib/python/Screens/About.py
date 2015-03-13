from Screen import Screen
from Components.config import config
from Components.ActionMap import ActionMap
from Components.Sources.StaticText import StaticText
from Components.Harddisk import harddiskmanager
from Components.NimManager import nimmanager
from Components.About import about
from Components.ScrollLabel import ScrollLabel
from Components.Button import Button

from Components.Label import Label
from Components.ProgressBar import ProgressBar

from Tools.StbHardware import getFPVersion
from enigma import eTimer, eLabel

from Components.HTMLComponent import HTMLComponent
from Components.GUIComponent import GUIComponent
import skin

class About(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		hddsplit, = skin.parameters.get("AboutHddSplit", (0,))

		AboutText = _("Hardware: ") + about.getHardwareTypeString() + "\n"
		AboutText += _("CPU: ") + about.getCPUInfoString() + "\n"
		AboutText += _("Image: ") + about.getImageTypeString() + "\n"
		AboutText += _("Installed: ") + about.getFlashDateString() + "\n"
		AboutText += _("Kernel version: ") + about.getKernelVersionString() + "\n"

		EnigmaVersion = "Enigma: " + about.getEnigmaVersionString()
		self["EnigmaVersion"] = StaticText(EnigmaVersion)
		AboutText += EnigmaVersion + "\n"
		AboutText += _("Enigma (re)starts: %d\n") % config.misc.startCounter.value

		GStreamerVersion = "GStreamer: " + about.getGStreamerVersionString().replace("GStreamer","")
		self["GStreamerVersion"] = StaticText(GStreamerVersion)
		AboutText += GStreamerVersion + "\n"

		ImageVersion = _("Last upgrade: ") + about.getImageVersionString()
		self["ImageVersion"] = StaticText(ImageVersion)
		AboutText += ImageVersion + "\n"

		AboutText += _("DVB drivers: ") + about.getDriverInstalledDate() + "\n"

		AboutText += _("Python version: ") + about.getPythonVersionString() + "\n"

		fp_version = getFPVersion()
		if fp_version is None:
			fp_version = ""
		else:
			fp_version = _("Frontprocessor version: %d") % fp_version
			AboutText += fp_version + "\n"

		self["FPVersion"] = StaticText(fp_version)

		self["TunerHeader"] = StaticText(_("Detected NIMs:"))
		AboutText += "\n" + _("Detected NIMs:") + "\n"

		nims = nimmanager.nimList()
		for count in range(len(nims)):
			if count < 4:
				self["Tuner" + str(count)] = StaticText(nims[count])
			else:
				self["Tuner" + str(count)] = StaticText("")
			AboutText += nims[count] + "\n"

		self["HDDHeader"] = StaticText(_("Detected HDD:"))
		AboutText += "\n" + _("Detected HDD:") + "\n"

		hddlist = harddiskmanager.HDDList()
		hddinfo = ""
		if hddlist:
			formatstring = hddsplit and "%s:%s, %.1f %sB %s" or "%s\n(%s, %.1f %sB %s)"
			for count in range(len(hddlist)):
				if hddinfo:
					hddinfo += "\n"
				hdd = hddlist[count][1]
				if int(hdd.free()) > 1024:
					hddinfo += formatstring % (hdd.model(), hdd.capacity(), hdd.free()/1024, "G", _("free"))
				else:
					hddinfo += formatstring % (hdd.model(), hdd.capacity(), hdd.free()/1024, "M", _("free"))
		else:
			hddinfo = _("none")
		self["hddA"] = StaticText(hddinfo)
		AboutText += hddinfo
		self["AboutScrollLabel"] = ScrollLabel(AboutText)
		self["key_green"] = Button(_("Translations"))
		self["key_red"] = Button(_("Latest Commits"))
		self["key_blue"] = Button(_("Memory Info"))

		self["actions"] = ActionMap(["ColorActions", "SetupActions", "DirectionActions"],
			{
				"cancel": self.close,
				"ok": self.close,
				"red": self.showCommits,
				"green": self.showTranslationInfo,
				"blue": self.showMemoryInfo,
				"up": self["AboutScrollLabel"].pageUp,
				"down": self["AboutScrollLabel"].pageDown
			})

	def showTranslationInfo(self):
		self.session.open(TranslationInfo)

	def showCommits(self):
		self.session.open(CommitInfo)

	def showMemoryInfo(self):
		self.session.open(MemoryInfo)

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

		self["key_red"] = Button(_("Cancel"))
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

class CommitInfo(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		self.skinName = ["CommitInfo", "About"]
		self["AboutScrollLabel"] = ScrollLabel(_("Please wait"))

		self["actions"] = ActionMap(["SetupActions", "DirectionActions"],
			{
				"cancel": self.close,
				"ok": self.close,
				"up": self["AboutScrollLabel"].pageUp,
				"down": self["AboutScrollLabel"].pageDown,
				"left": self.left,
				"right": self.right
			})

		self["key_red"] = Button(_("Cancel"))

		self.project = 0
		self.projects = [
			("enigma2", "Enigma2"),
			("openpli-oe-core", "Openpli Oe Core"),
			("enigma2-plugins", "Enigma2 Plugins"),
			("aio-grab", "Aio Grab"),
			("gst-plugin-dvbmediasink", "Gst Plugin Dvbmediasink"),
			("openembedded", "Openembedded"),
			("plugin-xmltvimport", "Plugin Xmltvimport"),
			("plugins-enigma2", "Plugins Enigma2"),
			("skin-magic", "Skin Magic"),
			("tuxtxt", "Tuxtxt")
		]
		self.cachedProjects = {}
		self.Timer = eTimer()
		self.Timer.callback.append(self.readCommitLogs)
		self.Timer.start(50, True)

	def readCommitLogs(self):
		url = 'http://sourceforge.net/p/openpli/%s/feed' % self.projects[self.project][0]
		commitlog = ""
		from urllib2 import urlopen
		try:
			commitlog += 80 * '-' + '\n'
			commitlog += url.split('/')[-2] + '\n'
			commitlog += 80 * '-' + '\n'
			for x in  urlopen(url, timeout=5).read().split('<title>')[2:]:
				for y in x.split("><"):
					if '</title' in y:
						title = y[:-7]
					if '</dc:creator' in y:
						creator = y.split('>')[1].split('<')[0]
					if '</pubDate' in y:
						date = y.split('>')[1].split('<')[0][:-6]
				commitlog += date + ' ' + creator + '\n' + title + 2 * '\n'
			self.cachedProjects[self.projects[self.project][1]] = commitlog
		except:
			commitlog = _("Currently the commit log cannot be retrieved - please try later again")
		self["AboutScrollLabel"].setText(commitlog)

	def updateCommitLogs(self):
		if self.cachedProjects.has_key(self.projects[self.project][1]):
			self["AboutScrollLabel"].setText(self.cachedProjects[self.projects[self.project][1]])
		else:
			self["AboutScrollLabel"].setText(_("Please wait"))
			self.Timer.start(50, True)

	def left(self):
		self.project = self.project == 0 and len(self.projects) - 1 or self.project - 1
		self.updateCommitLogs()

	def right(self):
		self.project = self.project != len(self.projects) - 1 and self.project + 1 or 0
		self.updateCommitLogs()

class MemoryInfo(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)

		self["actions"] = ActionMap(["SetupActions", "ColorActions"],
			{
				"cancel": self.close,
				"ok": self.getMemoryInfo,
				"green": self.getMemoryInfo,
				"blue": self.clearMemory,
			})

		self["key_red"] = Label(_("Cancel"))
		self["key_green"] = Label(_("Refresh"))
		self["key_blue"] = Label(_("Clear"))

		self['lmemtext'] = Label()
		self['lmemvalue'] = Label()
		self['rmemtext'] = Label()
		self['rmemvalue'] = Label()

		self['pfree'] = Label()
		self['pused'] = Label()
		self["slide"] = ProgressBar()
		self["slide"].setValue(100)

		self["params"] = MemoryInfoSkinParams()

		self['info'] = Label(_("This info is for developers only.\nFor a normal users it is not important.\nDon't panic, please, when here will be displayed any suspicious informations!"))

		self.setTitle(_("Memory Info"))
		self.onLayoutFinish.append(self.getMemoryInfo)

	def getMemoryInfo(self):
		try:
			ltext = rtext = ""
			lvalue = rvalue = ""
			mem = 1
			free = 0
			i = 0
			for line in open('/proc/meminfo','r'):
				( name, size, units ) = line.strip().split()
				if "MemTotal" in name:
					mem = int(size)
				if "MemFree" in name:
					free = int(size)
				if i < self["params"].rows_in_column:
					ltext += "".join((name,"\n"))
					lvalue += "".join((size," ",units,"\n"))
				else:
					rtext += "".join((name,"\n"))
					rvalue += "".join((size," ",units,"\n"))
				i += 1
			self['lmemtext'].setText(ltext)
			self['lmemvalue'].setText(lvalue)
			self['rmemtext'].setText(rtext)
			self['rmemvalue'].setText(rvalue)

			self["slide"].setValue(int(100.0*(mem-free)/mem+0.25))
			self['pfree'].setText("%.1f %s" % (100.*free/mem,'%'))
			self['pused'].setText("%.1f %s" % (100.*(mem-free)/mem,'%'))

		except Exception, e:
			print "[About] getMemoryInfo FAIL:", e

	def clearMemory(self):
		from os import system
		system("sync")
		system("echo 3 > /proc/sys/vm/drop_caches")
		self.getMemoryInfo()

class MemoryInfoSkinParams(HTMLComponent, GUIComponent):
	def __init__(self):
		GUIComponent.__init__(self)
		self.rows_in_column = 25

	def applySkin(self, desktop, screen):
		if self.skinAttributes is not None:
			attribs = [ ]
			for (attrib, value) in self.skinAttributes:
				if attrib == "rowsincolumn":
					self.rows_in_column = int(value)
			self.skinAttributes = attribs
		return GUIComponent.applySkin(self, desktop, screen)

	GUI_WIDGET = eLabel
