from Components.Task import Task, Job, DiskspacePrecondition, Condition, ToolExistsPrecondition
from Components.Harddisk import harddiskmanager
from Screens.MessageBox import MessageBox
import os

class png2yuvTask(Task):
	def __init__(self, job, inputfile, outputfile):
		Task.__init__(self, job, "Creating menu video")
		self.setTool("png2yuv")
		self.args += ["-n1", "-Ip", "-f25", "-j", inputfile]
		self.dumpFile = outputfile
		self.weighting = 15

	def run(self, callback):
		Task.run(self, callback)
		self.container.stdoutAvail.remove(self.processStdout)
		self.container.dumpToFile(self.dumpFile)

	def processStderr(self, data):
		print "[png2yuvTask]", data[:-1]

class mpeg2encTask(Task):
	def __init__(self, job, inputfile, outputfile):
		Task.__init__(self, job, "Encoding menu video")
		self.setTool("mpeg2enc")
		self.args += ["-f8", "-np", "-a2", "-o", outputfile]
		self.inputFile = inputfile
		self.weighting = 25

	def run(self, callback):
		Task.run(self, callback)
		self.container.readFromFile(self.inputFile)

	def processOutputLine(self, line):
		print "[mpeg2encTask]", line[:-1]

class spumuxTask(Task):
	def __init__(self, job, xmlfile, inputfile, outputfile):
		Task.__init__(self, job, "Muxing buttons into menu")
		self.setTool("spumux")
		self.args += [xmlfile]
		self.inputFile = inputfile
		self.dumpFile = outputfile
		self.weighting = 15

	def run(self, callback):
		Task.run(self, callback)
		self.container.stdoutAvail.remove(self.processStdout)
		self.container.dumpToFile(self.dumpFile)
		self.container.readFromFile(self.inputFile)

	def processStderr(self, data):
		print "[spumuxTask]", data[:-1]

class MakeFifoNode(Task):
	def __init__(self, job, number):
		Task.__init__(self, job, "Make FIFO nodes")
		self.setTool("mknod")
		nodename = self.job.workspace + "/dvd_title_%d" % number + ".mpg"
		self.args += [nodename, "p"]
		self.weighting = 10

class LinkTS(Task):
	def __init__(self, job, sourcefile, link_name):
		Task.__init__(self, job, "Creating symlink for source titles")
		self.setTool("ln")
		self.args += ["-s", sourcefile, link_name]
		self.weighting = 10

class CopyMeta(Task):
	def __init__(self, job, sourcefile):
		Task.__init__(self, job, "Copy title meta files")
		self.setTool("cp")
		from os import listdir
		path, filename = sourcefile.rstrip("/").rsplit("/",1)
		tsfiles = listdir(path)
		for file in tsfiles:
			if file.startswith(filename+"."):
				self.args += [path+'/'+file]
		self.args += [self.job.workspace]
		self.weighting = 15

class DemuxTask(Task):
	def __init__(self, job, inputfile):
		Task.__init__(self, job, "Demux video into ES")
		title = job.project.titles[job.i]
		self.global_preconditions.append(DiskspacePrecondition(title.estimatedDiskspace))
		self.setTool("projectx")
		self.args += [inputfile, "-demux", "-set", "ExportPanel.Streamtype.Subpicture=0", "-set", "ExportPanel.Streamtype.Teletext=0", "-out", self.job.workspace ]
		self.end = 300
		self.prog_state = 0
		self.weighting = 1000
		self.cutfile = self.job.workspace + "/cut_%d.Xcl" % (job.i+1)
		self.cutlist = title.cutlist
		self.currentPID = None
		self.relevantAudioPIDs = [ ]
		self.getRelevantAudioPIDs(title)
		self.generated_files = [ ]
		self.mplex_audiofiles = { }
		self.mplex_videofile = ""
		self.mplex_streamfiles = [ ]
		if len(self.cutlist) > 1:
			self.args += [ "-cut", self.cutfile ]

	def prepare(self):
		self.writeCutfile()

	def getRelevantAudioPIDs(self, title):
		for audiotrack in title.properties.audiotracks:
			if audiotrack.active.getValue():
				self.relevantAudioPIDs.append(audiotrack.pid.getValue())

	def processOutputLine(self, line):
		line = line[:-1]
		#print "[DemuxTask]", line
		MSG_NEW_FILE = "---> new File: "
		MSG_PROGRESS = "[PROGRESS] "
		MSG_NEW_MP2 = "++> Mpg Audio: PID 0x"
		MSG_NEW_AC3 = "++> AC3/DTS Audio: PID 0x"

		if line.startswith(MSG_NEW_FILE):
			file = line[len(MSG_NEW_FILE):]
			if file[0] == "'":
				file = file[1:-1]
			self.haveNewFile(file)
		elif line.startswith(MSG_PROGRESS):
			progress = line[len(MSG_PROGRESS):]
			self.haveProgress(progress)
		elif line.startswith(MSG_NEW_MP2) or line.startswith(MSG_NEW_AC3):
			try:
				self.currentPID = str(int(line.split(': PID 0x',1)[1].split(' ',1)[0],16))
			except ValueError:
				print "[DemuxTask] ERROR: couldn't detect Audio PID (projectx too old?)"

	def haveNewFile(self, file):
		print "[DemuxTask] produced file:", file, self.currentPID
		self.generated_files.append(file)
		if self.currentPID in self.relevantAudioPIDs:
			self.mplex_audiofiles[self.currentPID] = file
		elif file.endswith("m2v"):
			self.mplex_videofile = file

	def haveProgress(self, progress):
		#print "PROGRESS [%s]" % progress
		MSG_CHECK = "check & synchronize audio file"
		MSG_DONE = "done..."
		if progress == "preparing collection(s)...":
			self.prog_state = 0
		elif progress[:len(MSG_CHECK)] == MSG_CHECK:
			self.prog_state += 1
		else:
			try:
				p = int(progress)
				p = p - 1 + self.prog_state * 100
				if p > self.progress:
					self.progress = p
			except ValueError:
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
		print "[DemuxTask::cleanup]"
		self.mplex_streamfiles = [ self.mplex_videofile ]
		for pid in self.relevantAudioPIDs:
			if pid in self.mplex_audiofiles:
				self.mplex_streamfiles.append(self.mplex_audiofiles[pid])
		print self.mplex_streamfiles

		if failed:
			import os
			for file in self.generated_files:
				try:
					os.remove(file)
				except OSError:
					pass

class MplexTaskPostcondition(Condition):
	def check(self, task):
		if task.error == task.ERROR_UNDERRUN:
			return True
		return task.error is None

	def getErrorMessage(self, task):
		return {
			task.ERROR_UNDERRUN: ("Can't multiplex source video!"),
			task.ERROR_UNKNOWN: ("An unknown error occurred!")
		}[task.error]

class MplexTask(Task):
	ERROR_UNDERRUN, ERROR_UNKNOWN = range(2)
	def __init__(self, job, outputfile, inputfiles=None, demux_task=None, weighting = 500):
		Task.__init__(self, job, "Mux ES into PS")
		self.weighting = weighting
		self.demux_task = demux_task
		self.postconditions.append(MplexTaskPostcondition())
		self.setTool("mplex")
		self.args += ["-f8", "-o", outputfile, "-v1"]
		if inputfiles:
			self.args += inputfiles

	def setTool(self, tool):
		self.cmd = tool
		self.args = [tool]
		self.global_preconditions.append(ToolExistsPrecondition())
		# we don't want the ReturncodePostcondition in this case because for right now we're just gonna ignore the fact that mplex fails with a buffer underrun error on some streams (this always at the very end)

	def prepare(self):
		self.error = None
		if self.demux_task:
			self.args += self.demux_task.mplex_streamfiles

	def processOutputLine(self, line):
		print "[MplexTask] ", line[:-1]
		if line.startswith("**ERROR:"):
			if line.find("Frame data under-runs detected") != -1:
				self.error = self.ERROR_UNDERRUN
			else:
				self.error = self.ERROR_UNKNOWN

class RemoveESFiles(Task):
	def __init__(self, job, demux_task):
		Task.__init__(self, job, "Remove temp. files")
		self.demux_task = demux_task
		self.setTool("rm")
		self.weighting = 10

	def prepare(self):
		self.args += ["-f"]
		self.args += self.demux_task.generated_files
		self.args += [self.demux_task.cutfile]

class ReplexTask(Task):
	def __init__(self, job, outputfile, inputfile):
		Task.__init__(self, job, "ReMux TS into PS")
		self.weighting = 1000
		self.setTool("replex")
		self.args += ["-t", "DVD", "-j", "-o", outputfile, inputfile]

	def processOutputLine(self, line):
		print "[ReplexTask] ", line[:-1]

class DVDAuthorTask(Task):
	def __init__(self, job):
		Task.__init__(self, job, "Authoring DVD")
		self.weighting = 20
		self.setTool("dvdauthor")
		self.CWD = self.job.workspace
		self.args += ["-x", self.job.workspace+"/dvdauthor.xml"]
		self.menupreview = job.menupreview

	def processOutputLine(self, line):
		print "[DVDAuthorTask] ", line[:-1]
		if not self.menupreview and line.startswith("STAT: Processing"):
			self.callback(self, [], stay_resident=True)
		elif line.startswith("STAT: VOBU"):
			try:
				progress = int(line.split("MB")[0].split(" ")[-1])
				if progress:
					self.job.mplextask.progress = progress
					print "[DVDAuthorTask] update mplextask progress:", self.job.mplextask.progress, "of", self.job.mplextask.end
			except:
				print "couldn't set mux progress"

class DVDAuthorFinalTask(Task):
	def __init__(self, job):
		Task.__init__(self, job, "dvdauthor finalize")
		self.setTool("dvdauthor")
		self.args += ["-T", "-o", self.job.workspace + "/dvd"]

class WaitForResidentTasks(Task):
	def __init__(self, job):
		Task.__init__(self, job, "waiting for dvdauthor to finalize")

	def run(self, callback):
		print "waiting for %d resident task(s) %s to finish..." % (len(self.job.resident_tasks),str(self.job.resident_tasks))
		self.callback = callback
		if self.job.resident_tasks == 0:
			callback(self, [])

class BurnTaskPostcondition(Condition):
	RECOVERABLE = True
	def check(self, task):
		if task.returncode == 0:
			return True
		elif task.error is None or task.error is task.ERROR_MINUSRWBUG:
			return True
		return False

	def getErrorMessage(self, task):
		return {
			task.ERROR_NOTWRITEABLE: _("Medium is not a writeable DVD!"),
			task.ERROR_LOAD: _("Could not load medium! No disc inserted?"),
			task.ERROR_SIZE: _("Content does not fit on DVD!"),
			task.ERROR_WRITE_FAILED: _("Write failed!"),
			task.ERROR_DVDROM: _("No (supported) DVDROM found!"),
			task.ERROR_ISOFS: _("Medium is not empty!"),
			task.ERROR_FILETOOLARGE: _("TS file is too large for ISO9660 level 1!"),
			task.ERROR_ISOTOOLARGE: _("ISO file is too large for this filesystem!"),
			task.ERROR_UNKNOWN: _("An unknown error occurred!")
		}[task.error]

class BurnTask(Task):
	ERROR_NOTWRITEABLE, ERROR_LOAD, ERROR_SIZE, ERROR_WRITE_FAILED, ERROR_DVDROM, ERROR_ISOFS, ERROR_FILETOOLARGE, ERROR_ISOTOOLARGE, ERROR_MINUSRWBUG, ERROR_UNKNOWN = range(10)
	def __init__(self, job, extra_args=[], tool="growisofs"):
		Task.__init__(self, job, job.name)
		self.weighting = 500
		self.end = 120 # 100 for writing, 10 for buffer flush, 10 for closing disc
		self.postconditions.append(BurnTaskPostcondition())
		self.setTool(tool)
		self.args += extra_args

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
				self.error = self.ERROR_NOTWRITEABLE
			elif line.find("ASC=24h") != -1:
				self.error = self.ERROR_LOAD
			elif line.find("SK=5h/ASC=A8h/ACQ=04h") != -1:
				self.error = self.ERROR_MINUSRWBUG
			else:
				self.error = self.ERROR_UNKNOWN
				print "BurnTask: unknown error %s" % line
		elif line.startswith(":-("):
			if line.find("No space left on device") != -1:
				self.error = self.ERROR_SIZE
			elif self.error == self.ERROR_MINUSRWBUG:
				print "*sigh* this is a known bug. we're simply gonna assume everything is fine."
				self.postconditions = []
			elif line.find("write failed") != -1:
				self.error = self.ERROR_WRITE_FAILED
			elif line.find("unable to open64(") != -1 and line.find(",O_RDONLY): No such file or directory") != -1:
				self.error = self.ERROR_DVDROM
			elif line.find("media is not recognized as recordable DVD") != -1:
				self.error = self.ERROR_NOTWRITEABLE
			else:
				self.error = self.ERROR_UNKNOWN
				print "BurnTask: unknown error %s" % line
		elif line.startswith("FATAL:"):
			if line.find("already carries isofs!"):
				self.error = self.ERROR_ISOFS
			else:
				self.error = self.ERROR_UNKNOWN
				print "BurnTask: unknown error %s" % line
		elif line.find("-allow-limited-size was not specified. There is no way do represent this file size. Aborting.") != -1:
			self.error = self.ERROR_FILETOOLARGE
		elif line.startswith("genisoimage: File too large."):
			self.error = self.ERROR_ISOTOOLARGE

	def setTool(self, tool):
		self.cmd = tool
		self.args = [tool]
		self.global_preconditions.append(ToolExistsPrecondition())

class RemoveDVDFolder(Task):
	def __init__(self, job):
		Task.__init__(self, job, "Remove temp. files")
		self.setTool("rm")
		self.args += ["-rf", self.job.workspace]
		self.weighting = 10

class CheckDiskspaceTask(Task):
	def __init__(self, job):
		Task.__init__(self, job, "Checking free space")
		totalsize = 0 # require an extra safety 50 MB
		maxsize = 0
		for title in job.project.titles:
			titlesize = title.estimatedDiskspace
			if titlesize > maxsize: maxsize = titlesize
			totalsize += titlesize
		diskSpaceNeeded = totalsize + maxsize
		job.estimateddvdsize = totalsize / 1024 / 1024
		totalsize += 50*1024*1024 # require an extra safety 50 MB
		self.global_preconditions.append(DiskspacePrecondition(diskSpaceNeeded))
		self.weighting = 5

	def abort(self):
		self.finish(aborted = True)

	def run(self, callback):
		self.callback = callback
		failed_preconditions = self.checkPreconditions(True) + self.checkPreconditions(False)
		if len(failed_preconditions):
			callback(self, failed_preconditions)
			return
		Task.processFinished(self, 0)

class PreviewTask(Task):
	def __init__(self, job, path):
		Task.__init__(self, job, "Preview")
		self.postconditions.append(PreviewTaskPostcondition())
		self.job = job
		self.path = path
		self.weighting = 10

	def run(self, callback):
		self.callback = callback
		if self.job.menupreview:
			self.previewProject()
		else:
			import Screens.Standby
			if Screens.Standby.inStandby:
				self.previewCB(False)
			else:
				from Tools import Notifications
				Notifications.AddNotificationWithCallback(self.previewCB, MessageBox, _("Do you want to preview this DVD before burning?"), timeout = 60, default = False)

	def abort(self):
		self.finish(aborted = True)

	def previewCB(self, answer):
		if answer == True:
			self.previewProject()
		else:
			self.closedCB(True)

	def playerClosed(self):
		if self.job.menupreview:
			self.closedCB(True)
		else:
			from Tools import Notifications
			Notifications.AddNotificationWithCallback(self.closedCB, MessageBox, _("Do you want to burn this collection to DVD medium?") )

	def closedCB(self, answer):
		if answer == True:
			Task.processFinished(self, 0)
		else:
			Task.processFinished(self, 1)

	def previewProject(self):
		from Screens.DVD import DVDPlayer
		self.job.project.session.openWithCallback(self.playerClosed, DVDPlayer, dvd_filelist= [ self.path ])

class PreviewTaskPostcondition(Condition):
	def check(self, task):
		return task.returncode == 0

	def getErrorMessage(self, task):
		return "Cancel"

class ImagingPostcondition(Condition):
	def check(self, task):
		return task.returncode == 0

	def getErrorMessage(self, task):
		return _("Failed") + ": python-imaging"

class ImagePrepareTask(Task):
	def __init__(self, job):
		Task.__init__(self, job, _("please wait, loading picture..."))
		self.postconditions.append(ImagingPostcondition())
		self.weighting = 20
		self.job = job
		self.Menus = job.Menus

	def run(self, callback):
		self.callback = callback
		# we are doing it this weird way so that the TaskView Screen actually pops up before the spinner comes
		from enigma import eTimer
		self.delayTimer = eTimer()
		self.delayTimer.callback.append(self.conduct)
		self.delayTimer.start(10,1)

	def conduct(self):
		try:
			from ImageFont import truetype
			from Image import open as Image_open
			s = self.job.project.menutemplate.settings
			(width, height) = s.dimensions.getValue()
			self.Menus.im_bg_orig = Image_open(s.menubg.getValue())
			if self.Menus.im_bg_orig.size != (width, height):
				self.Menus.im_bg_orig = self.Menus.im_bg_orig.resize((width, height))
			self.Menus.fontsizes = [s.fontsize_headline.getValue(), s.fontsize_title.getValue(), s.fontsize_subtitle.getValue()]
			self.Menus.fonts = [(truetype(s.fontface_headline.getValue(), self.Menus.fontsizes[0])), (truetype(s.fontface_title.getValue(), self.Menus.fontsizes[1])),(truetype(s.fontface_subtitle.getValue(), self.Menus.fontsizes[2]))]
			Task.processFinished(self, 0)
		except:
			Task.processFinished(self, 1)

class MenuImageTask(Task):
	def __init__(self, job, menu_count, spuxmlfilename, menubgpngfilename, highlightpngfilename):
		Task.__init__(self, job, "Create Menu %d Image" % menu_count)
		self.postconditions.append(ImagingPostcondition())
		self.weighting = 10
		self.job = job
		self.Menus = job.Menus
		self.menu_count = menu_count
		self.spuxmlfilename = spuxmlfilename
		self.menubgpngfilename = menubgpngfilename
		self.highlightpngfilename = highlightpngfilename

	def run(self, callback):
		self.callback = callback
		#try:
		import ImageDraw, Image, os
		s = self.job.project.menutemplate.settings
		s_top = s.margin_top.getValue()
		s_bottom = s.margin_bottom.getValue()
		s_left = s.margin_left.getValue()
		s_right = s.margin_right.getValue()
		s_rows = s.space_rows.getValue()
		s_cols = s.space_cols.getValue()
		nr_cols = s.cols.getValue()
		nr_rows = s.rows.getValue()
		thumb_size = s.thumb_size.getValue()
		if thumb_size[0]:
			from Image import open as Image_open
		(s_width, s_height) = s.dimensions.getValue()
		fonts = self.Menus.fonts
		im_bg = self.Menus.im_bg_orig.copy()
		im_high = Image.new("P", (s_width, s_height), 0)
		im_high.putpalette(self.Menus.spu_palette)
		draw_bg = ImageDraw.Draw(im_bg)
		draw_high = ImageDraw.Draw(im_high)
		if self.menu_count == 1:
			headlineText = self.job.project.settings.name.getValue().decode("utf-8")
			headlinePos = self.getPosition(s.offset_headline.getValue(), 0, 0, s_width, s_top, draw_bg.textsize(headlineText, font=fonts[0]))
			draw_bg.text(headlinePos, headlineText, fill=self.Menus.color_headline, font=fonts[0])
		spuxml = """<?xml version="1.0" encoding="utf-8"?>
	<subpictures>
	<stream>
	<spu
	highlight="%s"
	transparent="%02x%02x%02x"
	start="00:00:00.00"
	force="yes" >""" % (self.highlightpngfilename, self.Menus.spu_palette[0], self.Menus.spu_palette[1], self.Menus.spu_palette[2])
		#rowheight = (self.Menus.fontsizes[1]+self.Menus.fontsizes[2]+thumb_size[1]+s_rows)
		menu_start_title = (self.menu_count-1)*self.job.titles_per_menu + 1
		menu_end_title = (self.menu_count)*self.job.titles_per_menu + 1
		nr_titles = len(self.job.project.titles)
		if menu_end_title > nr_titles:
			menu_end_title = nr_titles+1
		col = 1
		row = 1
		for title_no in range( menu_start_title , menu_end_title ):
			title = self.job.project.titles[title_no-1]
			col_width  = ( s_width  - s_left - s_right  ) / nr_cols
			row_height = ( s_height - s_top  - s_bottom ) / nr_rows
			left =   s_left + ( (col-1) * col_width ) + s_cols/2
			right =    left + col_width - s_cols
			top =     s_top + ( (row-1) * row_height) + s_rows/2
			bottom =    top + row_height - s_rows
			width = right - left
			height = bottom - top

			if bottom > s_height:
				bottom = s_height
			#draw_bg.rectangle((left, top, right, bottom), outline=(255,0,0))
			im_cell_bg = Image.new("RGBA", (width, height),(0,0,0,0))
			draw_cell_bg = ImageDraw.Draw(im_cell_bg)
			im_cell_high = Image.new("P", (width, height), 0)
			im_cell_high.putpalette(self.Menus.spu_palette)
			draw_cell_high = ImageDraw.Draw(im_cell_high)

			if thumb_size[0]:
				thumbPos = self.getPosition(s.offset_thumb.getValue(), 0, 0, width, height, thumb_size)
				box = (thumbPos[0], thumbPos[1], thumbPos[0]+thumb_size[0], thumbPos[1]+thumb_size[1])
				try:
					thumbIm = Image_open(title.inputfile.rsplit('.',1)[0] + ".png")
					im_cell_bg.paste(thumbIm,thumbPos)
				except:
					draw_cell_bg.rectangle(box, fill=(64,127,127,127))
				border = s.thumb_border.getValue()
				if border:
					draw_cell_high.rectangle(box, fill=1)
					draw_cell_high.rectangle((box[0]+border, box[1]+border, box[2]-border, box[3]-border), fill=0)

			titleText = title.formatDVDmenuText(s.titleformat.getValue(), title_no).decode("utf-8")
			titlePos = self.getPosition(s.offset_title.getValue(), 0, 0, width, height, draw_bg.textsize(titleText, font=fonts[1]))

			draw_cell_bg.text(titlePos, titleText, fill=self.Menus.color_button, font=fonts[1])
			draw_cell_high.text(titlePos, titleText, fill=1, font=self.Menus.fonts[1])

			subtitleText = title.formatDVDmenuText(s.subtitleformat.getValue(), title_no).decode("utf-8")
			subtitlePos = self.getPosition(s.offset_subtitle.getValue(), 0, 0, width, height, draw_cell_bg.textsize(subtitleText, font=fonts[2]))
			draw_cell_bg.text(subtitlePos, subtitleText, fill=self.Menus.color_button, font=fonts[2])

			del draw_cell_bg
			del draw_cell_high
			im_bg.paste(im_cell_bg,(left, top, right, bottom), mask=im_cell_bg)
			im_high.paste(im_cell_high,(left, top, right, bottom))

			spuxml += """
	<button name="button%s" x0="%d" x1="%d" y0="%d" y1="%d"/>""" % (str(title_no).zfill(2),left,right,top,bottom )
			if col < nr_cols:
				col += 1
			else:
				col = 1
				row += 1

		top = s_height - s_bottom - s_rows/2
		if self.menu_count < self.job.nr_menus:
			next_page_text = s.next_page_text.getValue().decode("utf-8")
			textsize = draw_bg.textsize(next_page_text, font=fonts[1])
			pos = ( s_width-textsize[0]-s_right, top )
			draw_bg.text(pos, next_page_text, fill=self.Menus.color_button, font=fonts[1])
			draw_high.text(pos, next_page_text, fill=1, font=fonts[1])
			spuxml += """
	<button name="button_next" x0="%d" x1="%d" y0="%d" y1="%d"/>""" % (pos[0],pos[0]+textsize[0],pos[1],pos[1]+textsize[1])
		if self.menu_count > 1:
			prev_page_text = s.prev_page_text.getValue().decode("utf-8")
			textsize = draw_bg.textsize(prev_page_text, font=fonts[1])
			pos = ( (s_left+s_cols/2), top )
			draw_bg.text(pos, prev_page_text, fill=self.Menus.color_button, font=fonts[1])
			draw_high.text(pos, prev_page_text, fill=1, font=fonts[1])
			spuxml += """
	<button name="button_prev" x0="%d" x1="%d" y0="%d" y1="%d"/>""" % (pos[0],pos[0]+textsize[0],pos[1],pos[1]+textsize[1])
		del draw_bg
		del draw_high
		fd=open(self.menubgpngfilename,"w")
		im_bg.save(fd,"PNG")
		fd.close()
		fd=open(self.highlightpngfilename,"w")
		im_high.save(fd,"PNG")
		fd.close()
		spuxml += """
	</spu>
	</stream>
	</subpictures>"""

		f = open(self.spuxmlfilename, "w")
		f.write(spuxml)
		f.close()
		Task.processFinished(self, 0)
		#except:
			#Task.processFinished(self, 1)

	def getPosition(self, offset, left, top, right, bottom, size):
		pos = [left, top]
		if offset[0] != -1:
			pos[0] += offset[0]
		else:
			pos[0] += ( (right-left) - size[0] ) / 2
		if offset[1] != -1:
			pos[1] += offset[1]
		else:
			pos[1] += ( (bottom-top) - size[1] ) / 2
		return tuple(pos)

class Menus:
	def __init__(self, job):
		self.job = job
		job.Menus = self

		s = self.job.project.menutemplate.settings

		self.color_headline = tuple(s.color_headline.getValue())
		self.color_button = tuple(s.color_button.getValue())
		self.color_highlight = tuple(s.color_highlight.getValue())
		self.spu_palette = [ 0x60, 0x60, 0x60 ] + s.color_highlight.getValue()

		ImagePrepareTask(job)
		nr_titles = len(job.project.titles)

		job.titles_per_menu = s.cols.getValue()*s.rows.getValue()

		job.nr_menus = ((nr_titles+job.titles_per_menu-1)/job.titles_per_menu)

		#a new menu_count every 4 titles (1,2,3,4->1 ; 5,6,7,8->2 etc.)
		for menu_count in range(1 , job.nr_menus+1):
			num = str(menu_count)
			spuxmlfilename = job.workspace+"/spumux"+num+".xml"
			menubgpngfilename = job.workspace+"/dvd_menubg"+num+".png"
			highlightpngfilename = job.workspace+"/dvd_highlight"+num+".png"
			MenuImageTask(job, menu_count, spuxmlfilename, menubgpngfilename, highlightpngfilename)
			png2yuvTask(job, menubgpngfilename, job.workspace+"/dvdmenubg"+num+".yuv")
			menubgm2vfilename = job.workspace+"/dvdmenubg"+num+".mv2"
			mpeg2encTask(job, job.workspace+"/dvdmenubg"+num+".yuv", menubgm2vfilename)
			menubgmpgfilename = job.workspace+"/dvdmenubg"+num+".mpg"
			menuaudiofilename = s.menuaudio.getValue()
			MplexTask(job, outputfile=menubgmpgfilename, inputfiles = [menubgm2vfilename, menuaudiofilename], weighting = 20)
			menuoutputfilename = job.workspace+"/dvdmenu"+num+".mpg"
			spumuxTask(job, spuxmlfilename, menubgmpgfilename, menuoutputfilename)

def CreateAuthoringXML_singleset(job):
	nr_titles = len(job.project.titles)
	mode = job.project.settings.authormode.getValue()
	authorxml = []
	authorxml.append('<?xml version="1.0" encoding="utf-8"?>\n')
	authorxml.append(' <dvdauthor dest="' + (job.workspace+"/dvd") + '">\n')
	authorxml.append('  <vmgm>\n')
	authorxml.append('   <menus lang="' + job.project.menutemplate.settings.menulang.getValue() + '">\n')
	authorxml.append('    <pgc>\n')
	authorxml.append('     <vob file="' + job.project.settings.vmgm.getValue() + '" />\n', )
	if mode.startswith("menu"):
		authorxml.append('     <post> jump titleset 1 menu; </post>\n')
	else:
		authorxml.append('     <post> jump title 1; </post>\n')
	authorxml.append('    </pgc>\n')
	authorxml.append('   </menus>\n')
	authorxml.append('  </vmgm>\n')
	authorxml.append('  <titleset>\n')
	if mode.startswith("menu"):
		authorxml.append('   <menus lang="' + job.project.menutemplate.settings.menulang.getValue() + '">\n')
		authorxml.append('    <video aspect="4:3"/>\n')
		for menu_count in range(1 , job.nr_menus+1):
			if menu_count == 1:
				authorxml.append('    <pgc entry="root">\n')
			else:
				authorxml.append('    <pgc>\n')
			menu_start_title = (menu_count-1)*job.titles_per_menu + 1
			menu_end_title = (menu_count)*job.titles_per_menu + 1
			if menu_end_title > nr_titles:
				menu_end_title = nr_titles+1
			for i in range( menu_start_title , menu_end_title ):
				authorxml.append('     <button name="button' + (str(i).zfill(2)) + '"> jump title ' + str(i) +'; </button>\n')
			if menu_count > 1:
				authorxml.append('     <button name="button_prev"> jump menu ' + str(menu_count-1) + '; </button>\n')
			if menu_count < job.nr_menus:
				authorxml.append('     <button name="button_next"> jump menu ' + str(menu_count+1) + '; </button>\n')
			menuoutputfilename = job.workspace+"/dvdmenu"+str(menu_count)+".mpg"
			authorxml.append('     <vob file="' + menuoutputfilename + '" pause="inf"/>\n')
			authorxml.append('    </pgc>\n')
		authorxml.append('   </menus>\n')
	authorxml.append('   <titles>\n')
	for i in range( nr_titles ):
		chapters = ','.join(job.project.titles[i].getChapterMarks())
		title_no = i+1
		title_filename = job.workspace + "/dvd_title_%d.mpg" % (title_no)
		if job.menupreview:
			LinkTS(job, job.project.settings.vmgm.getValue(), title_filename)
		else:
			MakeFifoNode(job, title_no)
		if mode.endswith("linked") and title_no < nr_titles:
			post_tag = "jump title %d;" % ( title_no+1 )
		elif mode.startswith("menu"):
			post_tag = "call vmgm menu 1;"
		else:	post_tag = ""

		authorxml.append('    <pgc>\n')
		authorxml.append('     <vob file="' + title_filename + '" chapters="' + chapters + '" />\n')
		authorxml.append('     <post> ' + post_tag + ' </post>\n')
		authorxml.append('    </pgc>\n')

	authorxml.append('   </titles>\n')
	authorxml.append('  </titleset>\n')
	authorxml.append(' </dvdauthor>\n')
	f = open(job.workspace+"/dvdauthor.xml", "w")
	for x in authorxml:
		f.write(x)
	f.close()

def CreateAuthoringXML_multiset(job):
	nr_titles = len(job.project.titles)
	mode = job.project.settings.authormode.getValue()
	authorxml = []
	authorxml.append('<?xml version="1.0" encoding="utf-8"?>\n')
	authorxml.append(' <dvdauthor dest="' + (job.workspace+"/dvd") + '" jumppad="yes">\n')
	authorxml.append('  <vmgm>\n')
	authorxml.append('   <menus lang="' + job.project.menutemplate.settings.menulang.getValue() + '">\n')
	authorxml.append('    <video aspect="4:3"/>\n')
	if mode.startswith("menu"):
		for menu_count in range(1 , job.nr_menus+1):
			if menu_count == 1:
				authorxml.append('    <pgc>\n')
			else:
				authorxml.append('    <pgc>\n')
			menu_start_title = (menu_count-1)*job.titles_per_menu + 1
			menu_end_title = (menu_count)*job.titles_per_menu + 1
			if menu_end_title > nr_titles:
				menu_end_title = nr_titles+1
			for i in range( menu_start_title , menu_end_title ):
				authorxml.append('     <button name="button' + (str(i).zfill(2)) + '"> jump titleset ' + str(i) +' title 1; </button>\n')
			if menu_count > 1:
				authorxml.append('     <button name="button_prev"> jump menu ' + str(menu_count-1) + '; </button>\n')
			if menu_count < job.nr_menus:
				authorxml.append('     <button name="button_next"> jump menu ' + str(menu_count+1) + '; </button>\n')
			menuoutputfilename = job.workspace+"/dvdmenu"+str(menu_count)+".mpg"
			authorxml.append('     <vob file="' + menuoutputfilename + '" pause="inf"/>\n')
			authorxml.append('    </pgc>\n')
	else:
		authorxml.append('    <pgc>\n')
		authorxml.append('     <vob file="' + job.project.settings.vmgm.getValue() + '" />\n' )
		authorxml.append('     <post> jump titleset 1 title 1; </post>\n')
		authorxml.append('    </pgc>\n')
	authorxml.append('   </menus>\n')
	authorxml.append('  </vmgm>\n')

	for i in range( nr_titles ):
		title = job.project.titles[i]
		authorxml.append('  <titleset>\n')
		authorxml.append('   <menus lang="' + job.project.menutemplate.settings.menulang.getValue() + '">\n')
		authorxml.append('    <pgc entry="root">\n')
		authorxml.append('     <pre>\n')
		authorxml.append('      jump vmgm menu entry title;\n')
		authorxml.append('     </pre>\n')
		authorxml.append('    </pgc>\n')
		authorxml.append('   </menus>\n')
		authorxml.append('   <titles>\n')
		for audiotrack in title.properties.audiotracks:
			active = audiotrack.active.getValue()
			if active:
				format = audiotrack.format.getValue()
				language = audiotrack.language.getValue()
				audio_tag = '    <audio format="%s"' % format
				if language != "nolang":
					audio_tag += ' lang="%s"' % language
				audio_tag += ' />\n'
				authorxml.append(audio_tag)
		aspect = title.properties.aspect.getValue()
		video_tag = '    <video aspect="'+aspect+'"'
		if title.properties.widescreen.getValue() == "4:3":
			video_tag += ' widescreen="'+title.properties.widescreen.getValue()+'"'
		video_tag += ' />\n'
		authorxml.append(video_tag)
		chapters = ','.join(title.getChapterMarks())
		title_no = i+1
		title_filename = job.workspace + "/dvd_title_%d.mpg" % (title_no)
		if job.menupreview:
			LinkTS(job, job.project.settings.vmgm.getValue(), title_filename)
		else:
			MakeFifoNode(job, title_no)
		if mode.endswith("linked") and title_no < nr_titles:
			post_tag = "jump titleset %d title 1;" % ( title_no+1 )
		elif mode.startswith("menu"):
			post_tag = "call vmgm menu 1;"
		else:	post_tag = ""

		authorxml.append('    <pgc>\n')
		authorxml.append('     <vob file="' + title_filename + '" chapters="' + chapters + '" />\n')
		authorxml.append('     <post> ' + post_tag + ' </post>\n')
		authorxml.append('    </pgc>\n')
		authorxml.append('   </titles>\n')
		authorxml.append('  </titleset>\n')
	authorxml.append(' </dvdauthor>\n')
	f = open(job.workspace+"/dvdauthor.xml", "w")
	for x in authorxml:
		f.write(x)
	f.close()

def getISOfilename(isopath, volName):
	from Tools.Directories import fileExists
	i = 0
	filename = isopath+'/'+volName+".iso"
	while fileExists(filename):
		i = i+1
		filename = isopath+'/'+volName + str(i).zfill(3) + ".iso"
	return filename

class DVDJob(Job):
	def __init__(self, project, menupreview=False):
		Job.__init__(self, "DVDBurn Job")
		self.project = project
		from time import strftime
		from Tools.Directories import SCOPE_HDD, resolveFilename, createDir
		new_workspace = resolveFilename(SCOPE_HDD) + "tmp/" + strftime("%Y%m%d%H%M%S")
		createDir(new_workspace, True)
		self.workspace = new_workspace
		self.project.workspace = self.workspace
		self.menupreview = menupreview
		self.conduct()

	def conduct(self):
		CheckDiskspaceTask(self)
		if self.project.settings.authormode.getValue().startswith("menu") or self.menupreview:
			Menus(self)
		if self.project.settings.titlesetmode.getValue() == "multi":
			CreateAuthoringXML_multiset(self)
		else:
			CreateAuthoringXML_singleset(self)

		DVDAuthorTask(self)

		nr_titles = len(self.project.titles)

		if self.menupreview:
			PreviewTask(self, self.workspace + "/dvd/VIDEO_TS/")
		else:
			hasProjectX = os.path.exists('/usr/bin/projectx')
			print "[DVDJob] hasProjectX=", hasProjectX
			for self.i in range(nr_titles):
				self.title = self.project.titles[self.i]
				link_name =  self.workspace + "/source_title_%d.ts" % (self.i+1)
				title_filename = self.workspace + "/dvd_title_%d.mpg" % (self.i+1)
				LinkTS(self, self.title.inputfile, link_name)
				if not hasProjectX:
					ReplexTask(self, outputfile=title_filename, inputfile=link_name).end = self.estimateddvdsize
				else:
					demux = DemuxTask(self, link_name)
					self.mplextask = MplexTask(self, outputfile=title_filename, demux_task=demux)
					self.mplextask.end = self.estimateddvdsize
					RemoveESFiles(self, demux)
			WaitForResidentTasks(self)
			PreviewTask(self, self.workspace + "/dvd/VIDEO_TS/")
			output = self.project.settings.output.getValue()
			volName = self.project.settings.name.getValue()
			if output == "dvd":
				self.name = _("Burn DVD")
				tool = "growisofs"
				burnargs = [ "-Z", "/dev/" + harddiskmanager.getCD(), "-dvd-compat" ]
				if self.project.size/(1024*1024) > self.project.MAX_SL:
					burnargs += [ "-use-the-force-luke=4gms", "-speed=1", "-R" ]
			elif output == "iso":
				self.name = _("Create DVD-ISO")
				tool = "genisoimage"
				isopathfile = getISOfilename(self.project.settings.isopath.getValue(), volName)
				burnargs = [ "-o", isopathfile ]
			burnargs += [ "-dvd-video", "-publisher", "Dreambox", "-V", volName, self.workspace + "/dvd" ]
			BurnTask(self, burnargs, tool)
		RemoveDVDFolder(self)

class DVDdataJob(Job):
	def __init__(self, project):
		Job.__init__(self, "Data DVD Burn")
		self.project = project
		from time import strftime
		from Tools.Directories import SCOPE_HDD, resolveFilename, createDir
		new_workspace = resolveFilename(SCOPE_HDD) + "tmp/" + strftime("%Y%m%d%H%M%S") + "/dvd/"
		createDir(new_workspace, True)
		self.workspace = new_workspace
		self.project.workspace = self.workspace
		self.conduct()

	def conduct(self):
		if self.project.settings.output.getValue() == "iso":
			CheckDiskspaceTask(self)
		nr_titles = len(self.project.titles)
		for self.i in range(nr_titles):
			title = self.project.titles[self.i]
			filename = title.inputfile.rstrip("/").rsplit("/",1)[1]
			link_name =  self.workspace + filename
			LinkTS(self, title.inputfile, link_name)
			CopyMeta(self, title.inputfile)

		output = self.project.settings.output.getValue()
		volName = self.project.settings.name.getValue()
		tool = "growisofs"
		if output == "dvd":
			self.name = _("Burn DVD")
			burnargs = [ "-Z", "/dev/" + harddiskmanager.getCD(), "-dvd-compat" ]
			if self.project.size/(1024*1024) > self.project.MAX_SL:
				burnargs += [ "-use-the-force-luke=4gms", "-speed=1", "-R" ]
		elif output == "iso":
			tool = "genisoimage"
			self.name = _("Create DVD-ISO")
			isopathfile = getISOfilename(self.project.settings.isopath.getValue(), volName)
			burnargs = [ "-o", isopathfile ]
		if self.project.settings.dataformat.getValue() == "iso9660_1":
			burnargs += ["-iso-level", "1" ]
		elif self.project.settings.dataformat.getValue() == "iso9660_4":
			burnargs += ["-iso-level", "4", "-allow-limited-size" ]
		elif self.project.settings.dataformat.getValue() == "udf":
			burnargs += ["-udf", "-allow-limited-size" ]
		burnargs += [ "-publisher", "Dreambox", "-V", volName, "-follow-links", self.workspace ]
		BurnTask(self, burnargs, tool)
		RemoveDVDFolder(self)

class DVDisoJob(Job):
	def __init__(self, project, imagepath):
		Job.__init__(self, _("Burn DVD"))
		self.project = project
		self.menupreview = False
		from Tools.Directories import getSize
		if imagepath.endswith(".iso"):
			PreviewTask(self, imagepath)
			burnargs = [ "-Z", "/dev/" + harddiskmanager.getCD() + '='+imagepath, "-dvd-compat" ]
			if getSize(imagepath)/(1024*1024) > self.project.MAX_SL:
				burnargs += [ "-use-the-force-luke=4gms", "-speed=1", "-R" ]
		else:
			PreviewTask(self, imagepath + "/VIDEO_TS/")
			volName = self.project.settings.name.getValue()
			burnargs = [ "-Z", "/dev/" + harddiskmanager.getCD(), "-dvd-compat" ]
			if getSize(imagepath)/(1024*1024) > self.project.MAX_SL:
				burnargs += [ "-use-the-force-luke=4gms", "-speed=1", "-R" ]
			burnargs += [ "-dvd-video", "-publisher", "Dreambox", "-V", volName, imagepath ]
		tool = "growisofs"
		BurnTask(self, burnargs, tool)
