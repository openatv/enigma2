from Components.Task import Task, Job, job_manager, DiskspacePrecondition, Condition, ToolExistsPrecondition
from Screens.MessageBox import MessageBox

class png2yuvTask(Task):
	def __init__(self, job, inputfile, outputfile):
		Task.__init__(self, job, "Creating menu video")
		self.setTool("/usr/bin/png2yuv")
		self.args += ["-n1", "-Ip", "-f25", "-j", inputfile]
		self.dumpFile = outputfile
		self.weighting = 10

	def run(self, callback, task_progress_changed):
		Task.run(self, callback, task_progress_changed)
		self.container.stdoutAvail.get().remove(self.processStdout)
		self.container.dumpToFile(self.dumpFile)

	def processStderr(self, data):
		print "[png2yuvTask]", data[:-1]

class mpeg2encTask(Task):
	def __init__(self, job, inputfile, outputfile):
		Task.__init__(self, job, "Encoding menu video")
		self.setTool("/usr/bin/mpeg2enc")
		self.args += ["-f8", "-np", "-a2", "-o", outputfile]
		self.inputFile = inputfile
		self.weighting = 10
		
	def run(self, callback, task_progress_changed):
		Task.run(self, callback, task_progress_changed)
		self.container.readFromFile(self.inputFile)

	def processOutputLine(self, line):
		print "[mpeg2encTask]", line[:-1]

class spumuxTask(Task):
	def __init__(self, job, xmlfile, inputfile, outputfile):
		Task.__init__(self, job, "Muxing buttons into menu")
		self.setTool("/usr/bin/spumux")
		self.args += [xmlfile]
		self.inputFile = inputfile
		self.dumpFile = outputfile
		self.weighting = 10

	def run(self, callback, task_progress_changed):
		Task.run(self, callback, task_progress_changed)
		self.container.stdoutAvail.get().remove(self.processStdout)
		self.container.dumpToFile(self.dumpFile)
		self.container.readFromFile(self.inputFile)

	def processStderr(self, data):
		print "[spumuxTask]", data[:-1]

class MakeFifoNode(Task):
	def __init__(self, job, number):
		Task.__init__(self, job, "Make FIFO nodes")
		self.setTool("/bin/mknod")
		nodename = self.job.workspace + "/dvd_title_%d" % number + ".mpg"
		self.args += [nodename, "p"]
		self.weighting = 10

class LinkTS(Task):
	def __init__(self, job, sourcefile, link_name):
		Task.__init__(self, job, "Creating symlink for source titles")
		self.setTool("/bin/ln")
		self.args += ["-s", sourcefile, link_name]
		self.weighting = 10

class CopyMeta(Task):
	def __init__(self, job, sourcefile):
		Task.__init__(self, job, "Copy title meta files")
		self.setTool("/bin/cp")
		from os import listdir
		path, filename = sourcefile.rstrip("/").rsplit("/",1)
		tsfiles = listdir(path)
		for file in tsfiles:
			if file.startswith(filename+"."):
				self.args += [path+'/'+file]
		self.args += [self.job.workspace]
		self.weighting = 10

class DemuxTask(Task):
	def __init__(self, job, inputfile):
		Task.__init__(self, job, "Demux video into ES")
		title = job.project.titles[job.i]
		self.global_preconditions.append(DiskspacePrecondition(title.estimatedDiskspace))
		self.setTool("/usr/bin/projectx")
		self.generated_files = [ ]
		self.end = 300
		self.prog_state = 0
		self.weighting = 1000
		self.cutfile = self.job.workspace + "/cut_%d.Xcl" % (job.i+1)
		self.cutlist = title.cutlist
		self.args += [inputfile, "-demux", "-out", self.job.workspace ]
		if len(self.cutlist) > 1:
			self.args += [ "-cut", self.cutfile ]

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

class MplexTaskPostcondition(Condition):
	def check(self, task):
		if task.error == task.ERROR_UNDERRUN:
			return True
		return task.error is None

	def getErrorMessage(self, task):
		print "[MplexTaskPostcondition] getErrorMessage", task
		return {
			task.ERROR_UNDERRUN: ("Can't multiplex source video!"),
			task.ERROR_UNKNOWN: ("An unknown error occured!")
		}[task.error]

class MplexTask(Task):
	ERROR_UNDERRUN, ERROR_UNKNOWN = range(2)
	def __init__(self, job, outputfile, inputfiles=None, demux_task=None):
		Task.__init__(self, job, "Mux ES into PS")
		self.weighting = 500
		self.demux_task = demux_task
		self.postconditions.append(MplexTaskPostcondition())
		self.setTool("/usr/bin/mplex")
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
			self.args += self.demux_task.generated_files

	def processOutputLine(self, line):
		print "[MplexTask] processOutputLine=", line[:-1]
		if line.startswith("**ERROR:"):
			if line.find("Frame data under-runs detected") != -1:
				self.error = self.ERROR_UNDERRUN
			else:
				self.error = self.ERROR_UNKNOWN

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
	def __init__(self, job, diskspaceNeeded):
		Task.__init__(self, job, "Authoring DVD")

		self.global_preconditions.append(DiskspacePrecondition(diskspaceNeeded))
		self.weighting = 300
		self.setTool("/usr/bin/dvdauthor")
		self.CWD = self.job.workspace
		self.args += ["-x", self.job.workspace+"/dvdauthor.xml"]
		self.menupreview = job.menupreview

	def processOutputLine(self, line):
		print "[DVDAuthorTask] processOutputLine=", line[:-1]
		if not self.menupreview and line.startswith("STAT: Processing"):
			self.callback(self, [], stay_resident=True)

class DVDAuthorFinalTask(Task):
	def __init__(self, job):
		Task.__init__(self, job, "dvdauthor finalize")
		self.setTool("/usr/bin/dvdauthor")
		self.args += ["-T", "-o", self.job.workspace + "/dvd"]

class WaitForResidentTasks(Task):
	def __init__(self, job):
		Task.__init__(self, job, "waiting for dvdauthor to finalize")
		
	def run(self, callback, task_progress_changed):
		print "waiting for %d resident task(s) %s to finish..." % (len(self.job.resident_tasks),str(self.job.resident_tasks))
		if self.job.resident_tasks == 0:
			callback(self, [])

class BurnTaskPostcondition(Condition):
	RECOVERABLE = True
	def check(self, task):
		return task.error is None

	def getErrorMessage(self, task):
		return {
			task.ERROR_MEDIA: _("Medium is not a writeable DVD!"),
			task.ERROR_SIZE: _("Content does not fit on DVD!"),
			task.ERROR_WRITE_FAILED: _("Write failed!"),
			task.ERROR_DVDROM: _("No (supported) DVDROM found!"),
			task.ERROR_ISOFS: _("Medium is not empty!"),
			task.ERROR_UNKNOWN: _("An unknown error occured!")
		}[task.error]

class BurnTask(Task):
	ERROR_MEDIA, ERROR_SIZE, ERROR_WRITE_FAILED, ERROR_DVDROM, ERROR_ISOFS, ERROR_UNKNOWN = range(6)
	def __init__(self, job, extra_args=[]):
		Task.__init__(self, job, "burn")

		self.weighting = 500
		self.end = 120 # 100 for writing, 10 for buffer flush, 10 for closing disc
		self.postconditions.append(BurnTaskPostcondition())
		self.setTool("/bin/growisofs")
		volName = self.getASCIIname(job.project.settings.name.getValue())
		self.args += ["-dvd-compat", "-Z", "/dev/cdroms/cdrom0", "-V", volName, "-P", "Dreambox", "-use-the-force-luke=dummy", self.job.workspace + "/dvd"]
		self.args += extra_args

	def getASCIIname(self, name):
		ASCIIname = ""
		for char in name.decode("utf-8").encode("ascii","replace"):
			if ord(char) <= 0x20 or ( ord(char) >= 0x3a and ord(char) <= 0x40 ):
				ASCIIname += '_'
			else:
				ASCIIname += char
		return ASCIIname
		
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
		elif line.startswith("FATAL:"):
			if line.find("already carries isofs!"):
				self.error = self.ERROR_ISOFS
			else:
				self.error = self.ERROR_UNKNOWN
				print "BurnTask: unknown error %s" % line

class RemoveDVDFolder(Task):
	def __init__(self, job):
		Task.__init__(self, job, "Remove temp. files")
		self.setTool("/bin/rm")
		self.args += ["-rf", self.job.workspace]

class PreviewTask(Task):
	def __init__(self, job):
		Task.__init__(self, job, "Preview")
		self.postconditions.append(PreviewTaskPostcondition())
		self.job = job

	def run(self, callback, task_progress_changed):
		self.callback = callback
		self.task_progress_changed = task_progress_changed
		if self.job.project.waitboxref:
			self.job.project.waitboxref.close()
		if self.job.menupreview:
			self.waitAndOpenPlayer()
		else:
			self.job.project.session.openWithCallback(self.previewCB, MessageBox, _("Do you want to preview this DVD before burning?"), timeout = 60, default = False)
	
	def previewCB(self, answer):
		if answer == True:
			self.waitAndOpenPlayer()
		else:
			self.closedCB(True)

	def playerClosed(self):
		if self.job.menupreview:
			self.closedCB(True)
		else:
			self.job.project.session.openWithCallback(self.closedCB, MessageBox, _("Do you want to burn this collection to DVD medium?") )

	def closedCB(self, answer):
		if answer == True:
			Task.processFinished(self, 0)
		else:
			Task.processFinished(self, 1)

	def waitAndOpenPlayer(self):
		from enigma import eTimer
		self.delayTimer = eTimer()
		self.delayTimer.callback.append(self.previewProject)
		self.delayTimer.start(10,1)
		
	def previewProject(self):
		from Plugins.Extensions.DVDPlayer.plugin import DVDPlayer
		self.job.project.session.openWithCallback(self.playerClosed, DVDPlayer, dvd_filelist= [ self.job.project.workspace + "/dvd/VIDEO_TS/" ])

class PreviewTaskPostcondition(Condition):
	def check(self, task):
		return task.returncode == 0

	def getErrorMessage(self, task):
		return "Cancel"

def getTitlesPerMenu(nr_titles):
	if nr_titles < 6:
		titles_per_menu = 5
	else:
		titles_per_menu = 4
	return titles_per_menu

def formatTitle(template, title, track):
	template = template.replace("$i", str(track))
	template = template.replace("$t", title.name)
	template = template.replace("$d", title.descr)
	template = template.replace("$c", str(len(title.chaptermarks)+1))
	template = template.replace("$A", str(title.audiotracks))
	template = template.replace("$f", title.inputfile)
	template = template.replace("$C", title.channel)
	l = title.length
	lengthstring = "%d:%02d:%02d" % (l/3600, l%3600/60, l%60)
	template = template.replace("$l", lengthstring)
	if title.timeCreate:
		template = template.replace("$Y", str(title.timeCreate[0]))
		template = template.replace("$M", str(title.timeCreate[1]))
		template = template.replace("$D", str(title.timeCreate[2]))
		timestring = "%d:%02d" % (title.timeCreate[3], title.timeCreate[4])
		template = template.replace("$T", timestring)
	else:
		template = template.replace("$Y", "").replace("$M", "").replace("$D", "").replace("$T", "")
	return template.decode("utf-8")

def CreateMenus(job):
	try:
		from ImageFont import truetype
		import ImageDraw, Image, os
	except ImportError:
		job.project.session.open(MessageBox, ("missing python-imaging"), type = MessageBox.TYPE_ERROR)
		if job.project.waitboxref:
			job.project.waitboxref.close()
		return False

	imgwidth = 720
	imgheight = 576
	s = job.project.settings
	im_bg_orig = Image.open(s.menubg.getValue())
	if im_bg_orig.size != (imgwidth, imgheight):
		im_bg_orig = im_bg_orig.resize((720, 576))
	
	fontsizes = s.font_size.getValue()
	fontface = s.font_face.getValue()
	
	font0 = truetype(fontface, fontsizes[0])
	font1 = truetype(fontface, fontsizes[1])
	font2 = truetype(fontface, fontsizes[2])

	color_headline = tuple(s.color_headline.getValue())
	color_button = tuple(s.color_button.getValue())
	color_highlight = tuple(s.color_highlight.getValue())
	spu_palette = [	0x60, 0x60, 0x60 ] + s.color_highlight.getValue()

	nr_titles = len(job.project.titles)
	titles_per_menu = getTitlesPerMenu(nr_titles)
	job.nr_menus = ((nr_titles+titles_per_menu-1)/titles_per_menu)

	#a new menu_count every 5 titles (1,2,3,4,5->1 ; 6,7,8,9,10->2 etc.)
	for menu_count in range(1 , job.nr_menus+1):
		im_bg = im_bg_orig.copy()
		im_high = Image.new("P", (imgwidth, imgheight), 0)
		im_high.putpalette(spu_palette)
		draw_bg = ImageDraw.Draw(im_bg)
		draw_high = ImageDraw.Draw(im_high)

		if menu_count == 1:
			headline = s.name.getValue().decode("utf-8")
			textsize = draw_bg.textsize(headline, font=font0)
			if textsize[0] > imgwidth:
				offset = (0 , 20)
			else:
				offset = (((imgwidth-textsize[0]) / 2) , 20)
			draw_bg.text(offset, headline, fill=color_headline, font=font0)
		
		menubgpngfilename = job.workspace+"/dvd_menubg"+str(menu_count)+".png"
		highlightpngfilename = job.workspace+"/dvd_highlight"+str(menu_count)+".png"
		spuxml = """<?xml version="1.0" encoding="utf-8"?>
	<subpictures>
	<stream>
	<spu 
	highlight="%s"
	transparent="%02x%02x%02x"
	start="00:00:00.00"
	force="yes" >""" % (highlightpngfilename, spu_palette[0], spu_palette[1], spu_palette[2])
		s_top, s_rows, s_left = s.space.getValue()
		rowheight = (fontsizes[1]+fontsizes[2]+s_rows)
		menu_start_title = (menu_count-1)*titles_per_menu + 1
		menu_end_title = (menu_count)*titles_per_menu + 1
		if menu_end_title > nr_titles:
			menu_end_title = nr_titles+1
		menu_i = 0
		for title_no in range( menu_start_title , menu_end_title ):
			i = title_no-1
			top = s_top + ( menu_i * rowheight )
			menu_i += 1
			title = job.project.titles[i]
			titleText = formatTitle(s.titleformat.getValue(), title, title_no)
			draw_bg.text((s_left,top), titleText, fill=color_button, font=font1)
			draw_high.text((s_left,top), titleText, fill=1, font=font1)
			subtitleText = formatTitle(s.subtitleformat.getValue(), title, title_no)
			draw_bg.text((s_left,top+36), subtitleText, fill=color_button, font=font2)
			bottom = top+rowheight
			if bottom > imgheight:
				bottom = imgheight
			spuxml += """
	<button name="button%s" x0="%d" x1="%d" y0="%d" y1="%d"/>""" % (str(title_no).zfill(2),s_left,imgwidth,top,bottom )
		if menu_count > 1:
			prev_page_text = "<<<"
			textsize = draw_bg.textsize(prev_page_text, font=font1)
			offset = ( 2*s_left, s_top + ( titles_per_menu * rowheight ) )
			draw_bg.text(offset, prev_page_text, fill=color_button, font=font1)
			draw_high.text(offset, prev_page_text, fill=1, font=font1)
			spuxml += """
	<button name="button_prev" x0="%d" x1="%d" y0="%d" y1="%d"/>""" % (offset[0],offset[0]+textsize[0],offset[1],offset[1]+textsize[1])

		if menu_count < job.nr_menus:
			next_page_text = ">>>"
			textsize = draw_bg.textsize(next_page_text, font=font1)
			offset = ( imgwidth-textsize[0]-2*s_left, s_top + ( titles_per_menu * rowheight ) )
			draw_bg.text(offset, next_page_text, fill=color_button, font=font1)
			draw_high.text(offset, next_page_text, fill=1, font=font1)
			spuxml += """
	<button name="button_next" x0="%d" x1="%d" y0="%d" y1="%d"/>""" % (offset[0],offset[0]+textsize[0],offset[1],offset[1]+textsize[1])
				
		del draw_bg
		del draw_high
		fd=open(menubgpngfilename,"w")
		im_bg.save(fd,"PNG")
		fd.close()
		fd=open(highlightpngfilename,"w")
		im_high.save(fd,"PNG")
		fd.close()
	
		png2yuvTask(job, menubgpngfilename, job.workspace+"/dvdmenubg"+str(menu_count)+".yuv")
		menubgm2vfilename = job.workspace+"/dvdmenubg"+str(menu_count)+".mv2"
		mpeg2encTask(job, job.workspace+"/dvdmenubg"+str(menu_count)+".yuv", menubgm2vfilename)
		menubgmpgfilename = job.workspace+"/dvdmenubg"+str(menu_count)+".mpg"
		menuaudiofilename = s.menuaudio.getValue()
		MplexTask(job, outputfile=menubgmpgfilename, inputfiles = [menubgm2vfilename, menuaudiofilename])
	
		spuxml += """
	</spu>
	</stream>
	</subpictures>"""
		spuxmlfilename = job.workspace+"/spumux"+str(menu_count)+".xml"
		f = open(spuxmlfilename, "w")
		f.write(spuxml)
		f.close()
		
		menuoutputfilename = job.workspace+"/dvdmenu"+str(menu_count)+".mpg"
		spumuxTask(job, spuxmlfilename, menubgmpgfilename, menuoutputfilename)
	return True
		
def CreateAuthoringXML(job):
	nr_titles = len(job.project.titles)
	titles_per_menu = getTitlesPerMenu(nr_titles)
	mode = job.project.settings.authormode.getValue()
	authorxml = []
	authorxml.append('<?xml version="1.0" encoding="utf-8"?>\n')
	authorxml.append(' <dvdauthor dest="' + (job.workspace+"/dvd") + '">\n')
	authorxml.append('  <vmgm>\n')
	authorxml.append('   <menus>\n')
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
		authorxml.append('   <menus>\n')
		authorxml.append('    <video aspect="4:3"/>\n')
		for menu_count in range(1 , job.nr_menus+1):
			if menu_count == 1:
				authorxml.append('    <pgc entry="root">\n')
			else:
				authorxml.append('    <pgc>\n')
			menu_start_title = (menu_count-1)*titles_per_menu + 1
			menu_end_title = (menu_count)*titles_per_menu + 1
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
		for audiotrack in job.project.titles[i].audiotracks:
			authorxml.append('    <audio lang="'+audiotrack[0][:2]+'" format="'+audiotrack[1]+'" />\n')
		chapters = ','.join(["%d:%02d:%02d.%03d" % (p / (90000 * 3600), p % (90000 * 3600) / (90000 * 60), p % (90000 * 60) / 90000, (p % 90000) / 90) for p in job.project.titles[i].chaptermarks])
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

class DVDJob(Job):
	def __init__(self, project, menupreview=False):
		Job.__init__(self, "DVD Burn")
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
		if self.project.settings.authormode.getValue().startswith("menu") or self.menupreview:
			if not CreateMenus(self):
				return
		CreateAuthoringXML(self)

		totalsize = 50*1024*1024 # require an extra safety 50 MB
		maxsize = 0
		for title in self.project.titles:
			titlesize = title.estimatedDiskspace
			if titlesize > maxsize: maxsize = titlesize
			totalsize += titlesize
		diskSpaceNeeded = totalsize + maxsize

		DVDAuthorTask(self, diskSpaceNeeded)
		
		nr_titles = len(self.project.titles)
		
		if self.menupreview:
			PreviewTask(self)
		else:
			for self.i in range(nr_titles):
				title = self.project.titles[self.i]
				link_name =  self.workspace + "/source_title_%d.ts" % (self.i+1)
				title_filename = self.workspace + "/dvd_title_%d.mpg" % (self.i+1)
				LinkTS(self, title.inputfile, link_name)
				demux = DemuxTask(self, link_name)
				MplexTask(self, outputfile=title_filename, demux_task=demux)
				RemoveESFiles(self, demux)
			WaitForResidentTasks(self)
			PreviewTask(self)
			BurnTask(self,["-dvd-video"])
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
		diskSpaceNeeded = 50*1024*1024 # require an extra safety 50 MB
		for title in self.project.titles:
			diskSpaceNeeded += title.filesize
		nr_titles = len(self.project.titles)

		for self.i in range(nr_titles):
			title = self.project.titles[self.i]
			filename = title.inputfile.rstrip("/").rsplit("/",1)[1]
			link_name =  self.workspace + filename
			LinkTS(self, title.inputfile, link_name)
			CopyMeta(self, title.inputfile)
		BurnTask(self)
		RemoveDVDFolder(self)

def Burn(session, project):
	j = DVDJob(project)
	job_manager.AddJob(j)
	return j

def PreviewMenu(session, project):
	j = DVDJob(project, menupreview=True)
	job_manager.AddJob(j)
	return j

def BurnDataTS(session, project):
	j = DVDdataJob(project)
	job_manager.AddJob(j)
	return j
