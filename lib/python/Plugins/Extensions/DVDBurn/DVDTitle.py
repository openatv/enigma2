
class DVDTitle:
	def __init__(self):
		self.cuesheet = [ ]
		self.source = None
		self.name = ""
		self.descr = ""
		self.filesize = 0
		self.estimatedDiskspace = 0
		self.inputfile = ""
		self.cutlist = [ ]
		self.chaptermarks = [ ]

	def addService(self, service):
		from os import path
		from enigma import eServiceCenter, iServiceInformation
		self.source = service
		serviceHandler = eServiceCenter.getInstance()
		info = serviceHandler.info(service)
		self.descr = info and " " + info.getInfoString(service, iServiceInformation.sDescription) or ""
		self.name = info and info.getName(service) or "Title" + t.descr
		self.inputfile = service.getPath()
		self.filesize = path.getsize(self.inputfile)
		self.estimatedDiskspace = self.filesize

	def produceFinalCuesheet(self):
		print "[produceFinalCuesheet] >>> ", self.inputfile, self.cuesheet

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
				
		print "cutlist =", self.cutlist, "chaptermarks =", self.chaptermarks, "accumulated_in =", accumulated_in

		if len(self.cutlist) > 1:
			from enigma import eServiceCenter, iServiceInformation
			serviceHandler = eServiceCenter.getInstance()
			service = self.source
			info = serviceHandler.info(service)
			lenpts = info.getLength(service) * 90000
			part = accumulated_in / float(lenpts)
			usedsize = int ( part * self.filesize )
			print "lenpts=", lenpts, "part=", part, "filesize=", self.filesize, "estimatedDiskspace=", usedsize
			self.estimatedDiskspace = usedsize
