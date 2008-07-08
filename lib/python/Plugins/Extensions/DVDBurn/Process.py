from Components.Task import Task, Job, job_manager, DiskspacePrecondition, Condition

class DemuxTask(Task):
	def __init__(self, job, inputfile, cutlist):
		Task.__init__(self, job, "Demux video into ES")

		self.global_preconditions.append(DiskspacePrecondition(4*1024*1024))
		self.setTool("/opt/bin/projectx")
		self.cutfile = self.job.workspace + "/cut.Xcl"
		self.generated_files = [ ]
		self.cutlist = cutlist

		self.end = 300
		self.prog_state = 0
		self.weighting = 1000

		self.args += [inputfile, "-demux", "-out", self.job.workspace, "-cut", self.job.workspace + "/" + self.cutfile ]

	def prepare(self):
		self.writeCutfile()

	def processOutputLine(self, line):
		line = line[:-1]
		MSG_NEW_FILE = "---> new File: "
		MSG_PROGRESS = "[PROGRESS] "

		if line.startswith(MSG_NEW_FILE):
			file = line[len(MSG_NEW_FILE):]
			if file[0] == "'":
				file = file[1:-1]
			self.haveNewFile(file)
		elif line.startswith(MSG_PROGRESS):
			progress = line[len(MSG_PROGRESS):]
			self.haveProgress(progress)

	def haveNewFile(self, file):
		print "PRODUCED FILE [%s]" % file
		self.generated_files.append(file)

	def haveProgress(self, progress):
		print "PROGRESS [%s]" % progress
		MSG_CHECK = "check & synchronize audio file"
		MSG_DONE = "done..."
		if progress == "preparing collection(s)...":
			self.prog_state = 0
		elif progress[:len(MSG_CHECK)] == MSG_CHECK:
			self.prog_state += 1
		else:
			try:
				print "have progress:", progress
				p = int(progress)
				p = p - 1 + self.prog_state * 100
				if p > self.progress:
					self.progress = p
			except ValueError:
				print "val error"
				pass

	def writeCutfile(self):
		f = open(self.cutfile, "w")
		f.write("CollectionPanel.CutMode=4\n")
		for p in self.cutlist:
			s = p / 90000
			m = s / 60
			h = m / 60

			m %= 60
			s %= 60

			f.write("%02d:%02d:%02d\n" % (h, m, s))
		f.close()

	def cleanup(self, failed):
		if failed:
			import os
			for f in self.generated_files:
				os.remove(f)

class MplexTask(Task):
	def __init__(self, job, outputfile, demux_task):
		Task.__init__(self, job, "Mux ES into PS")

		self.weighting = 500
		self.demux_task = demux_task
		self.setTool("/usr/bin/mplex")
		self.args += ["-f8", "-o", self.job.workspace + "/" + outputfile, "-v1"]

	def prepare(self):
		self.args += self.demux_task.generated_files

class RemoveESFiles(Task):
	def __init__(self, job, demux_task):
		Task.__init__(self, job, "Remove temp. files")
		self.demux_task = demux_task
		self.setTool("/bin/rm")

	def prepare(self):
		self.args += ["-f"]
		self.args += self.demux_task.generated_files
		self.args += [self.demux_task.cutfile]

class DVDAuthorTask(Task):
	def __init__(self, job, inputfiles, chapterlist):
		Task.__init__(self, job, "dvdauthor")

		self.weighting = 300
		self.setTool("/usr/bin/dvdauthor")
		chapterargs = "--chapters=" + ','.join(["%d:%02d:%02d.%03d" % (p / (90000 * 3600), p % (90000 * 3600) / (90000 * 60), p % (90000 * 60) / 90000, (p % 90000) / 90) for p in chapterlist])
		self.args += ["-t", chapterargs, "-o", self.job.workspace + "/dvd", "-f"] + inputfiles

class RemovePSFile(Task):
	def __init__(self, job, psfile):
		Task.__init__(self, job, "Remove temp. files")
		self.setTool("/bin/rm")
		self.args += ["-f", psfile]

class DVDAuthorFinalTask(Task):
	def __init__(self, job):
		Task.__init__(self, job, "dvdauthor finalize")
		self.setTool("/usr/bin/dvdauthor")
		self.args += ["-T", "-o", self.job.workspace + "/dvd"]

class BurnTaskPostcondition(Condition):
	def check(self, task):
		return task.error is None

	def getErrorMessage(self, task):
		return {
			task.ERROR_MEDIA: ("Medium is not a writeable DVD!"),
			task.ERROR_SIZE: ("Content does not fit on DVD!"),
			task.ERROR_WRITE_FAILED: ("Write failed!"),
			task.ERROR_DVDROM: ("No (supported) DVDROM found!"),
			task.ERROR_UNKNOWN: ("An unknown error occured!")
		}[task.error]

class BurnTask(Task):
	ERROR_MEDIA, ERROR_SIZE, ERROR_WRITE_FAILED, ERROR_DVDROM, ERROR_UNKNOWN = range(5)
	def __init__(self, job):
		Task.__init__(self, job, "burn")

		self.weighting = 500
		self.end = 120 # 100 for writing, 10 for buffer flush, 10 for closing disc
		self.postconditions.append(BurnTaskPostcondition())
		self.setTool("/bin/growisofs")
		self.args += ["-dvd-video", "-dvd-compat", "-Z", "/dev/cdroms/cdrom0", "-V", "Dreambox_DVD", "-use-the-force-luke=dummy", self.job.workspace + "/dvd"]

	def prepare(self):
		self.error = None

	def processOutputLine(self, line):
		line = line[:-1]
		print "[GROWISOFS] %s" % line
		if line[8:14] == "done, ":
			self.progress = float(line[:6])
			print "progress:", self.progress
		elif line.find("flushing cache") != -1:
			self.progress = 100
		elif line.find("closing disc") != -1:
			self.progress = 110
		elif line.startswith(":-["):
			if line.find("ASC=30h") != -1:
				self.error = self.ERROR_MEDIA
			else:
				self.error = self.ERROR_UNKNOWN
				print "BurnTask: unknown error %s" % line
		elif line.startswith(":-("):
			if line.find("No space left on device") != -1:
				self.error = self.ERROR_SIZE
			elif line.find("write failed") != -1:
				self.error = self.ERROR_WRITE_FAILED
			elif line.find("unable to open64(\"/dev/cdroms/cdrom0\",O_RDONLY): No such file or directory") != -1: # fixme
				self.error = self.ERROR_DVDROM
			elif line.find("media is not recognized as recordable DVD") != -1:
				self.error = self.ERROR_MEDIA
			else:
				self.error = self.ERROR_UNKNOWN
				print "BurnTask: unknown error %s" % line

class RemoveDVDFolder(Task):
	def __init__(self, job):
		Task.__init__(self, job, "Remove temp. files")
		self.setTool("/bin/rm")
		self.args += ["-rf", self.job.workspace]

class DVDJob(Job):
	def __init__(self, cue):
		Job.__init__(self, "DVD Burn")
		self.cue = cue
		from time import strftime
		from Tools.Directories import SCOPE_HDD, resolveFilename, createDir
		new_workspace = resolveFilename(SCOPE_HDD) + "tmp/" + strftime("%Y%m%d%H%M%S")
		createDir(new_workspace)
		self.workspace = new_workspace
		self.fromDescription(self.createDescription())

	def fromDescription(self, description):
		nr_titles = int(description["nr_titles"])

		for i in range(nr_titles):
			inputfile = description["inputfile%d" % i]
			cutlist_entries = description["cutlist%d_entries" % i]
			cutlist = [ ]
			for j in range(cutlist_entries):
				cutlist.append(int(description["cutlist%d_%d" % (i, j)]))

			chapterlist_entries = description["chapterlist%d_entries" % i]
			chapterlist = [ ]
			for j in range(chapterlist_entries):
				chapterlist.append(int(description["chapterlist%d_%d" % (i, j)]))

			demux = DemuxTask(self, inputfile = inputfile, cutlist = cutlist)

			title_filename =  self.workspace + "/dvd_title_%d.mpg" % i

			MplexTask(self, "dvd_title_%d.mpg" % i, demux)
			RemoveESFiles(self, demux)
			DVDAuthorTask(self, [title_filename], chapterlist = chapterlist)
			RemovePSFile(self, title_filename)
		DVDAuthorFinalTask(self)
		BurnTask(self)
		RemoveDVDFolder(self)

	def createDescription(self):
		# self.cue is a list of titles, with 
		#   each title being a tuple of 
		#     inputfile,
		#     a list of cutpoints (in,out)
		#     a list of chaptermarks
		# we turn this into a flat dict with
		# nr_titles = the number of titles,
		# cutlist%d_entries = the number of cutlist entries for title i,
		# cutlist%d_%d = cutlist entry j for title i,
		# chapterlist%d_entries = the number of chapters for title i,
		# chapterlist%d_%d = chapter j for title i
		res = { "nr_titles": len(self.cue) }
		for i in range(len(self.cue)):
			c = self.cue[i]
			res["inputfile%d" % i] = c[0]
			res["cutlist%d_entries" % i] = len(c[1])
			for j in range(len(c[1])):
				res["cutlist%d_%d" % (i,j)] = c[1][j]

			res["chapterlist%d_entries" % i] = len(c[2])
			for j in range(len(c[2])):
				res["chapterlist%d_%d" % (i,j)] = c[2][j]
		return res

def Burn(session, cue):
	print "burning cuesheet!"
	j = DVDJob(cue)
	job_manager.AddJob(j)
	return j
