from Components.config import config, ConfigSubsection, ConfigSubList, ConfigInteger, ConfigText, ConfigSelection, getConfigListEntry, ConfigSequence, ConfigYesNo
import TitleCutter

class ConfigFixedText(ConfigText):
	def __init__(self, text, visible_width=60):
		ConfigText.__init__(self, default = text, fixed_size = True, visible_width = visible_width)
	def handleKey(self, key):
		pass

class DVDTitle:
	def __init__(self, project):
		self.properties = ConfigSubsection()
		self.properties.menutitle = ConfigText(fixed_size = False, visible_width = 80)
		self.properties.menusubtitle = ConfigText(fixed_size = False, visible_width = 80)
		self.properties.aspect = ConfigSelection(choices = [("4:3", _("4:3")), ("16:9", _("16:9"))])
		self.properties.widescreen = ConfigSelection(choices = [("nopanscan", "nopanscan"), ("noletterbox", "noletterbox")])
		self.properties.autochapter = ConfigInteger(default = 0, limits = (0, 60))
		self.properties.audiotracks = ConfigSubList()
		self.DVBname = _("Title")
		self.DVBdescr = _("Description")
		self.DVBchannel = _("Channel")
		self.cuesheet = [ ]
		self.source = None
		self.filesize = 0
		self.estimatedDiskspace = 0
		self.inputfile = ""
		self.cutlist = [ ]
		self.chaptermarks = [ ]
		self.timeCreate = None
		self.VideoType = -1
		self.project = project
		self.length = 0

	def addService(self, service):
		from os import path
		from enigma import eServiceCenter, iServiceInformation
		from ServiceReference import ServiceReference
		from time import localtime, time
		self.source = service
		serviceHandler = eServiceCenter.getInstance()
		info = serviceHandler.info(service)
		sDescr = info and info.getInfoString(service, iServiceInformation.sDescription) or ""
		self.DVBdescr = sDescr
		sTimeCreate = info.getInfo(service, iServiceInformation.sTimeCreate)
		if sTimeCreate > 1:
			self.timeCreate = localtime(sTimeCreate)
		serviceref = ServiceReference(info.getInfoString(service, iServiceInformation.sServiceref))
		name = info and info.getName(service) or "Title" + sDescr
		self.DVBname = name
		self.DVBchannel = serviceref.getServiceName()
		self.inputfile = service.getPath()
		self.filesize = path.getsize(self.inputfile)
		self.estimatedDiskspace = self.filesize
		self.length = info.getLength(service)

	def addFile(self, filename):
		from enigma import eServiceReference
		ref = eServiceReference(1, 0, filename)
		self.addService(ref)
		self.project.session.openWithCallback(self.titleEditDone, TitleCutter.CutlistReader, self)

	def titleEditDone(self, cutlist):
		self.initDVDmenuText(len(self.project.titles))
		self.cuesheet = cutlist
		self.produceFinalCuesheet()

	def initDVDmenuText(self, track):
		s = self.project.menutemplate.settings
		self.properties.menutitle.setValue(self.formatDVDmenuText(s.titleformat.getValue(), track))
		self.properties.menusubtitle.setValue(self.formatDVDmenuText(s.subtitleformat.getValue(), track))

	def formatDVDmenuText(self, template, track):
		template = template.replace("$i", str(track))
		template = template.replace("$t", self.DVBname)
		template = template.replace("$d", self.DVBdescr)
		template = template.replace("$c", str(len(self.chaptermarks)+1))
		template = template.replace("$f", self.inputfile)
		template = template.replace("$C", self.DVBchannel)

		#if template.find("$A") >= 0:
		from TitleProperties import languageChoices
		audiolist = [ ]
		for audiotrack in self.properties.audiotracks:
			active = audiotrack.active.getValue()
			if active:
				trackstring = audiotrack.format.getValue()
				language = audiotrack.language.getValue()
				if languageChoices.langdict.has_key(language):
					trackstring += ' (' + languageChoices.langdict[language] + ')'
				audiolist.append(trackstring)
		audiostring = ', '.join(audiolist)
		template = template.replace("$A", audiostring)

		if template.find("$l") >= 0:
			l = self.length
			lengthstring = "%d:%02d:%02d" % (l/3600, l%3600/60, l%60)
			template = template.replace("$l", lengthstring)
		if self.timeCreate:
			template = template.replace("$Y", str(self.timeCreate[0]))
			template = template.replace("$M", str(self.timeCreate[1]))
			template = template.replace("$D", str(self.timeCreate[2]))
			timestring = "%d:%02d" % (self.timeCreate[3], self.timeCreate[4])
			template = template.replace("$T", timestring)
		else:
			template = template.replace("$Y", "").replace("$M", "").replace("$D", "").replace("$T", "")
		return template

	def produceFinalCuesheet(self):
		CUT_TYPE_IN = 0
		CUT_TYPE_OUT = 1
		CUT_TYPE_MARK = 2
		CUT_TYPE_LAST = 3

		accumulated_in = 0
		accumulated_at = 0
		last_in = 0

		self.cutlist = [ ]
		self.chaptermarks = [ ]

		# our demuxer expects *strictly* IN,OUT lists.
		currently_in = not any(type == CUT_TYPE_IN for pts, type in self.cuesheet)
		if currently_in:
			self.cutlist.append(0) # emulate "in" at first

		for (pts, type) in self.cuesheet:
			#print "pts=", pts, "type=", type, "accumulated_in=", accumulated_in, "accumulated_at=", accumulated_at, "last_in=", last_in
			if type == CUT_TYPE_IN and not currently_in:
				self.cutlist.append(pts)
				last_in = pts
				currently_in = True

			if type == CUT_TYPE_OUT and currently_in:
				self.cutlist.append(pts)

				# accumulate the segment
				accumulated_in += pts - last_in
				accumulated_at = pts
				currently_in = False

			if type == CUT_TYPE_MARK and currently_in:
				# relocate chaptermark against "in" time. This is not 100% accurate,
				# as the in/out points are not.
				reloc_pts = pts - last_in + accumulated_in
				self.chaptermarks.append(reloc_pts)

		if len(self.cutlist) > 1:
			part = accumulated_in / (self.length*90000.0)
			usedsize = int ( part * self.filesize )
			self.estimatedDiskspace = usedsize
			self.length = accumulated_in / 90000

	def getChapterMarks(self, template="$h:$m:$s.$t"):
		timestamps = [ ]
		chapters = [ ]
		minutes = self.properties.autochapter.getValue()
		if len(self.chaptermarks) < 1 and minutes > 0:
			chapterpts = 0
			while chapterpts < (self.length-60*minutes)*90000:
				chapterpts += 90000 * 60 * minutes
				chapters.append(chapterpts)
		else:
			chapters = self.chaptermarks
		for p in chapters:
			timestring = template.replace("$h", str(p / (90000 * 3600)))
			timestring = timestring.replace("$m", ("%02d" % (p % (90000 * 3600) / (90000 * 60))))
			timestring = timestring.replace("$s", ("%02d" % (p % (90000 * 60) / 90000)))
			timestring = timestring.replace("$t", ("%03d" % ((p % 90000) / 90)))
			timestamps.append(timestring)
		return timestamps
