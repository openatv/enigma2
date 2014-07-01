from Components.Task import Task, Job, DiskspacePrecondition, Condition
from Components.Harddisk import harddiskmanager
from Tools.Directories import SCOPE_HDD, resolveFilename, createDir
from time import strftime
from Process import CheckDiskspaceTask, getISOfilename, BurnTask, RemoveWorkspaceFolder
from Project import iso639language
import struct
import os
import re

zeros = bytearray(128)
VIDEO_TYPES	= { 'video/mpeg, mpegversion=(int)1': 0x01, 'video/mpeg, mpegversion=(int)2': 0x02, 'VC1': 0xEA, 'video/x-h264': 0x1B }
AUDIO_TYPES	= { 'audio/mpeg, mpegversion=(int)1': 0x03, 'audio/mpeg, mpegversion=(int)2': 0x04, 'audio/x-lpcm': 0x80, 'audio/x-ac3': 0x81, 'audio/x-dts': 0x82, 'TRUEHD': 0x83, 'AC3+': 0x84, 'DTSHD': 0x85, 'DTSHD Master': 0x86 }
VIDEO_FORMATS	= { 'i480': 1, 'i576': 2, 'p480': 3, 'i1080': 4, 'p720': 5, 'p1080': 6, 'p576': 7 }
VIDEO_RATES	= { 23976: 1, 24000: 2, 25000: 3, 29970: 4, 50000: 6, 59940: 7 }
AUDIO_CHANNELS  = { "reserved": 0, "mono": 1, "dual mono": 2, "stereo": 3, "multi": 6, "combo": 12 }
AUDIO_RATES     = { 48000: 1, 96000: 4, 192000: 5, 48/192: 12, 48/96: 14 }

class BludiscTitle(object):
	def __init__(self, title):
		object.__setattr__(self, "_title", title)
		self.__streams = {}
		self.muxed_size = 0
		self.entrypoints = []	# [(source_packet_number, presentation_time_stamp)]

	def __getattr__(self, attr):
		_title = object.__getattribute__(self, "_title")
		if hasattr(_title, attr):
			return getattr(_title, attr)
		else:
			return object.__getattribute__(self, attr)

	def addStream(self, pid):
		self.__streams[pid] = BludiscStream(self, pid)

	def getStreamByPID(self, pid):
		if pid in self.__streams:
			return self.__streams[pid]
		else: return None

	def getVideoStreams(self):
		streams = []
		for stream in self.__streams.values():
			if stream.isVideo:
				streams.append(stream)
		return streams
	
	VideoStreams = property(getVideoStreams)
	
	def getAudioStreams(self):
		streams = []
		for stream in self.__streams.values():
			if stream.isAudio:
				streams.append(stream)
		return streams

	AudioStreams = property(getAudioStreams)

	def getInTimeBytes(self):
		in_time = self.entrypoints[0][1]	# first keyframe (in 90khz pts)
		return struct.pack('>L',in_time/2)	# start time (in 45khz ticks)

	def getOutTimeBytes(self):
	      out_time = self.entrypoints[-1][1]	# last keyframe (in 90khz pts)
	      return struct.pack('>L',out_time/2)	# end time (in 45khz ticks)

	InTime = property(getInTimeBytes)
	OutTime = property(getOutTimeBytes)

	def getNumSourcePackets(self):
		num_source_packets = self.muxed_size / 192
		return struct.pack('>L',num_source_packets) 

	def getTsRecordingRate(self):
		clip_len_seconds = (self.entrypoints[-1][1] - self.entrypoints[0][1]) / 90000
		if self.length > clip_len_seconds:
			clip_len_seconds = self.length
		ts_recording_rate = self.muxed_size / clip_len_seconds	#! possible lack in accuracy 
		return struct.pack('>L',ts_recording_rate)

	def getEPforOffsetPTS(self, requested_pts):
		best_pts = 0
		for spn, ep_pts in self.entrypoints:
			if abs(requested_pts-best_pts) > abs(requested_pts-ep_pts):
				best_pts = ep_pts
			else:
				break
		return best_pts / 2

class BludiscStream(object):
	def __init__(self, parent, PID):
	  	self.__parent = parent
	  	self.__PID = PID
		self.__streamtype = 0x00
		self.__framerate = None
		self.__audiorate = 0
		self.__audiopresentation = 0
		self.languageCode = "und"
		self.isAudio = False
		self.isVideo = False

	def setStreamtype(self, streamtype):
		if isinstance(streamtype, int):
			if streamtype in dict((VIDEO_TYPES[k], k) for k in VIDEO_TYPES):
				self.__streamtype = streamtype
				self.isVideo = True
				self.isAudio = False
				return True
			elif streamtype in dict((AUDIO_TYPES[k], k) for k in AUDIO_TYPES):
				self.__streamtype = streamtype
				self.isVideo = False
				self.isAudio = True
				return True
		if isinstance(streamtype, str):
			if streamtype in VIDEO_TYPES:
				self.__streamtype = VIDEO_TYPES[streamtype]
				self.isVideo = True
				self.isAudio = False
				return True
			elif streamtype in AUDIO_TYPES:
				self.__streamtype = AUDIO_TYPES[streamtype]
				self.isVideo = False
				self.isAudio = True
				return True
		self.__streamtype = 0x00
		self.isVideo = False
		self.isAudio = False
		return False

	def getStreamtypeByte(self):
		return struct.pack('B',self.__streamtype)

	streamType = property(getStreamtypeByte, setStreamtype)
	
	def getPIDBytes(self):
		return struct.pack('>H',self.__PID)
	
	pid = property(getPIDBytes)

	def getFormatByte(self):
		val = 0
		if self.isVideo:
			yres = self.__parent.resolution[1]
			videoformat = 0
			frame_rate = 0

			if self.__parent.progressive > 0:
				videoformatstring = "p"+str(yres)
			else:
				videoformatstring = "i"+str(yres)
				
			if videoformatstring in VIDEO_FORMATS:
				videoformat = VIDEO_FORMATS[videoformatstring]
			else:
				print "BludiscStream %s object warning... PID %i video stream format %s out of spec!" % (self.__parent.inputfile, self.__PID, videoformatstring)

			if self.__parent.framerate in VIDEO_RATES:
				frame_rate = VIDEO_RATES[self.__parent.framerate]
			else:
				print "BludiscStream %s object warning... PID %i video frame rate %s out of spec!" % (self.__parent.inputfile, self.__PID, self.__parent.framerate)

			byteval = (videoformat << 4) + frame_rate

		if self.isAudio: 
			byteval = (self.__audiopresentation << 4) + self.__audiorate

		return struct.pack('B',byteval)
	
	formatByte = property(getFormatByte)

	def setAudioPresentation(self, channels):
		presentation = "reserved"
		if channels in [1, 2]:
			presentation = {1: "mono", 2: "stereo"}[channels]
		if channels > 2:
			presentation = "multi"
		self.__audiopresentation = AUDIO_CHANNELS[presentation]

	def setAudioRate(self, samplerate):
		if samplerate in AUDIO_RATES:
			self.__audiorate = AUDIO_RATES[samplerate]

	def getAspectByte(self):
		aspect = self.__parent.properties.aspect.value
		if self.isVideo:
		      if aspect == "16:9":
			    return struct.pack('B',0x30)
		      elif aspect == "4:3":
			    return struct.pack('B',0x20)

	aspect = property(getAspectByte)

class RemuxTask(Task):
	def __init__(self, job, title, title_no):
		Task.__init__(self, job, "Remultiplex Movie")
		self.global_preconditions.append(DiskspacePrecondition(title.estimatedDiskspace))
		self.postconditions.append(GenericPostcondition())
		self.setTool("bdremux")
		self.title = title
		self.title_no = title_no
		self.job = job
		inputfile = title.inputfile
		self.outputfile = self.job.workspace+'BDMV/STREAM/%05d.m2ts' % self.title_no
		self.args += [inputfile, self.outputfile, "--entrypoints", "--cutlist"]
		self.args += self.getPIDs()
		self.end = ( self.title.filesize / 188 )
		self.weighting = 1000

	def getPIDs(self):
		dvbpids = [self.title.VideoPID]
		for audiotrack in self.title.properties.audiotracks:
			if audiotrack.active.getValue():
				if audiotrack.format.value == "AC3": #! only consider ac3 streams at the moment
					dvbpids.append(int(audiotrack.pid.getValue()))
		sourcepids = "--source-pids=" + ",".join(["0x%04x" % pid for pid in dvbpids])
		self.bdmvpids = [0x1011]+range(0x1100,0x1107)[:len(dvbpids)-1]
		resultpids = "--result-pids=" + ",".join(["0x%04x" % pid for pid in self.bdmvpids])
		return [sourcepids, resultpids]

	def processOutputLine(self, line):
		if line.startswith("entrypoint:"):
			values = line[:-1].split(' ')
			(spn, pts) = (int(values[1]), int(values[2]))
			if spn > 0 and pts > 0:
				self.title.entrypoints.append((spn, pts))
				print "[bdremux] added new entrypoint", self.title.entrypoints[-1]
			self.progress = spn
		elif line.startswith("linked:"):	
			words = line[:-1].split(' ')
			pid = int(words[5].split('_')[1])
			self.title.addStream(pid)
			print "[bdremux] added stream with pid", pid
		elif line.find("has CAPS:") > 0:
			words = line[:-1].split(' ')
			pid = int(words[0].split('_')[1])
			stype = words[3][:-1]
			if words[3].find("mpeg") > 0:
				stype = words[3]+' '+words[4][:-1]

			stream = self.title.getStreamByPID(pid)
			if stream == None:
				print "[bdremux] invalid stream!"
				return

			sdict = {}
			if stype.startswith("audio"):
				sdict = AUDIO_TYPES
			elif stype.startswith("video"):
				sdict = VIDEO_TYPES
			if stype in sdict:
				stream.streamType = sdict[stype]

			for field in words[4:]:
				key, val = field.split('=')
				m = re.search('\(int\)(\d*).*', val)
				if m and m.groups() > 1:
					v = int(m.group(1))
					if key == "rate":
						stream.setAudioRate(v)
					elif key == "channels":
						stream.setAudioPresentation(v)
			print "[bdremux] discovered caps for pid %i (%s)" % (pid, stype)
		elif line.startswith("ERROR:"):
			self.error_text = line[7:-1]
			print "[bdremux] error:", self.error_text
			Task.processFinished(self, 1)
		else:
			print "[bdremux]", line[:-1]

	def cleanup(self, failed):
		if not failed:
			self.title.muxed_size = os.path.getsize(self.outputfile)

class GenericPostcondition(Condition):
	def check(self, task):
		return task.returncode == 0

	def getErrorMessage(self, task):
		if hasattr(task, "error_text"):
			error_text = task.error_text
		else:
			error_text = _("An unknown error occured!")
		return '%s (%s)' % (task.name, error_text)

class CreateStructureTask(Task):
	def __init__(self, job):
		Task.__init__(self, job, "Creating BDMV Directory Structure")
		self.job = job
		self.weighting = 10
		self.postconditions.append(GenericPostcondition())

	def run(self, callback):
		self.callback = callback
		self.conduct()
		Task.processFinished(self, 0)

	def conduct(self):
		for directory in ['BDMV','BDMV/AUXDATA','BDMV/BACKUP','BDMV/BACKUP/BDJO','BDMV/BACKUP/CLIPINF','BDMV/BACKUP/JAR','BDMV/BACKUP/PLAYLIST','BDMV/BDJO','BDMV/CLIPINF','BDMV/JAR','BDMV/META','BDMV/META/DL','BDMV/PLAYLIST','BDMV/STREAM']:
			if not createDir(self.job.workspace+directory):
				Task.processFinished(self, 1)

class CreateIndexTask(Task):
	def __init__(self, job):
		Task.__init__(self, job, "Create BDMV Index File")
		self.job = job
		self.weighting = 10
		self.postconditions.append(GenericPostcondition())

	def run(self, callback):
		self.callback = callback
		self.conduct()
		Task.processFinished(self, 0)
		#try:
			#self.conduct()
			#Task.processFinished(self, 0)
		#except:
			#Task.processFinished(self, 1)

	def conduct(self):
		indexbuffer = bytearray("INDX0200")
		indexbuffer += '\x00\x00\x00\x4E'	# index_start
		indexbuffer += zeros[0:4]		# extension_data_start
		indexbuffer += zeros[0:24]		# reserved
		indexbuffer += '\x00\x00\x00\x22'	# app_info length
		indexbuffer += '\x00' 			# 1 bit reserved, 1 bit initial_output_mode_preference, 1 bit content_exist_flag, 5 bits reserved

		num_titles = len(self.job.titles)
		if (num_titles == 1 and len(self.job.titles[0].VideoStreams) == 1):
			indexbuffer += self.job.titles[0].VideoStreams[0].formatByte	# video_format & frame_rate
		else:
			indexbuffer += '\x00' 		# video_format & frame_rate
		indexbuffer += 'Provider Name: Dream Multimedia ' # 32 byte user data

		INDEXES = bytearray(4)			# length of indexes
		INDEXES += '\x40'			# object_type (HDMV = 0x40)
		INDEXES += zeros[0:3] 			# first playback:
		INDEXES += '\x00\x00' 			# playback_type (Movie = 0x00)
		INDEXES += '\x00\x00' 			# id_ref
		INDEXES += zeros[0:4] 			# skip
		INDEXES += '\x40'
		INDEXES += zeros[0:3]			# top menu:
		INDEXES += '\x40\x00'			# playback_type (Interactive = 0x40)
		INDEXES += '\xFF\xFF'			# id_ref 
		INDEXES += zeros[0:4]

		INDEXES += struct.pack('>H',num_titles)
		for i in range(num_titles):
			HDMV_OBJ = bytearray('\x40')	# object_type & access_type
			HDMV_OBJ += zeros[0:3]		# skip 3 bytes
			HDMV_OBJ += zeros[0:2]
			HDMV_OBJ += struct.pack('>H',i) # index 2 bytes
			HDMV_OBJ += zeros[0:4]		# skip 4 bytes
			INDEXES += HDMV_OBJ
		INDEXES[0:4] = struct.pack('>L',len(INDEXES)-4)
		indexbuffer += INDEXES

		f = open(self.job.workspace+"BDMV/index.bdmv", 'w')
		f.write(buffer(indexbuffer))
		f.close()
		f = open(self.job.workspace+"BDMV/BACKUP/index.bdmv", 'w')
		f.write(buffer(indexbuffer))
		f.close()

class CreateMobjTask(Task):
	def __init__(self, job):
		Task.__init__(self, job, "Create BDMV Movie Objects File")
		self.job = job
		self.weighting = 10
		self.postconditions.append(GenericPostcondition())

	def run(self, callback):
		self.callback = callback
		self.conduct()
		Task.processFinished(self, 0)
		#try:
			#self.conduct()
			#Task.processFinished(self, 0)
		#except:
			#Task.processFinished(self, 1)

	def conduct(self):
		mob = bytearray("MOBJ0200")
		mob += zeros[0:4] #extension_data_start
		mob += zeros[0:28] #reserved?

		instructions = []

		for i in range(len(self.job.titles)):
			instructions.append(	# load title number into register0 \
				 [['\x50\x40\x00\x01','\x00\x00\x00\x00',struct.pack('>L',i)],\
						# PLAY_PL
				  ['\x22\x00\x00\x00','\x00\x00\x00\x00','\x00\x00\x00\x00']])
			if i < len(self.job.titles)-1: # on all except last title JUMP_TITLE i+2 (JUMP_TITLE is one-based)
				instructions[-1].append(['\x21\x81\x00\x00',struct.pack('>L',i+2),'\x00\x00\x00\x00'])

		#SETSTREAM (first audio stream as default track) ['\x51\xC0\x00\x01','\x00\x00\x00\x00','\x80\x01\x00\x00'] #!

		num_objects = len(instructions)
		OBJECTS = bytearray(4) #length of objects
		OBJECTS += zeros[0:4] #reserved
		OBJECTS += struct.pack('>H',num_objects)
		for i in range(num_objects):
			MOBJ = bytearray()
			MOBJ += '\x80\x00' # resume_intention_flag, menu_call_mask, title_search_maskplayback_type, 13 reserved
			num_commands = len(instructions[i])
			MOBJ += struct.pack('>H',num_commands)
			for c in range(num_commands):
				CMD = bytearray()
				CMD += instructions[i][c][0] #options
				CMD += instructions[i][c][1] #destination
				CMD += instructions[i][c][2] #source
				MOBJ += CMD
			OBJECTS += MOBJ
		OBJECTS[0:4] = struct.pack('>L',len(OBJECTS)-4)

		mob += OBJECTS

		f = open(self.job.workspace+"BDMV/MovieObject.bdmv", 'w')
		f.write(buffer(mob))
		f.close()
		f = open(self.job.workspace+"BDMV/BACKUP/MovieObject.bdmv", 'w')
		f.write(buffer(mob))
		f.close()

class CreateMplsTask(Task):
	def __init__(self, job, title, mpls_num):
		Task.__init__(self, job, "Create BDMV Playlist File")
		self.title = title
		self.mpls_num = mpls_num
		self.job = job
		self.weighting = 10
		self.postconditions.append(GenericPostcondition())

	def run(self, callback):
		self.callback = callback
		try:
			self.conduct()
			Task.processFinished(self, 0)
		except Exception:
			Task.processFinished(self, 1)

	def conduct(self):
		mplsbuffer = bytearray("MPLS0200")

		mplsbuffer += '\x00\x00\x00\x3a'	#playlist_start_address #Position of PlayList, from beginning of file

		mplsbuffer += zeros[0:4]	#playlist_mark_start_address Position of PlayListMark, from beginning of file
		mplsbuffer += zeros[0:4]	#extension_data_start_address= bytearray(4)
		mplsbuffer += zeros[0:20]	#reserved

		AppInfoPlayList = bytearray()	#length of AppInfoPlayList (4 bytes)

		AppInfoPlayList += '\x00'	#reserved 1 byte
		AppInfoPlayList += '\x01'	#playlist_playback_type
		AppInfoPlayList += zeros[0:2]	#reserved 2 bytes
		AppInfoPlayList += zeros[0:8]	#UO_mask_table

		AppInfoPlayList += '\x40\x00'	#playlist_random_access_flag, audio_mix_app_flag, lossless_may_bypass_mixer_flag, 13 bit reserved_for_word_align

		mplsbuffer += bytearray(struct.pack('>L',len(AppInfoPlayList)))
		mplsbuffer += AppInfoPlayList

		PlayList = bytearray()		#length of PlayList (4 bytes)

		PlayList += zeros[0:2]		#reserved 2 bytes

		num_of_playitems = 1
		PlayList += struct.pack('>H',num_of_playitems)

		num_of_subpaths = 0
		PlayList += struct.pack('>H',num_of_subpaths)

		num_primary_video = len(self.title.VideoStreams)
		
		if num_primary_video == 0:
			self.error_text = "Title %05d has no valid video streams!" % self.mpls_num
			raise Exception, self.error_text

		num_primary_audio = len(self.title.AudioStreams)

		num_pg = 0			# (presentation graphics, subtitle)
		num_ig = 0			# (interactive graphics)
		num_secondary_audio = 0
		num_secondary_video = 0
		num_PIP_PG = 0

		for item_i in range(num_of_playitems):
			PlayItem = bytearray()
			clip_no = "%05d" % self.mpls_num
			PlayItem += bytearray(clip_no)
			PlayItem += "M2TS"
			PlayItem += '\x00\x01'			# reserved 11 bits & 1 bit is_multi_angle & connection_condition
			PlayItem += '\x00'			# stc_id
			PlayItem += self.title.InTime		# start time (in 45khz ticks)
			PlayItem += self.title.OutTime		# end time (in 45khz ticks)
			PlayItem += zeros[0:8]			# UO_mask_table
			PlayItem += '\x00'			# random_access_flag (uppermost bit, 0=permit) & reserved 7 bits
			PlayItem += '\x01\x00\x02'		# still_mode & still_time (in s)

			StnTable = bytearray()	# len 4 bytes
			StnTable += zeros[0:2]	# reserved
			StnTable += struct.pack('B',num_primary_video)
			StnTable += struct.pack('B',num_primary_audio)
			StnTable += struct.pack('B',num_pg)
			StnTable += struct.pack('B',num_ig)
			StnTable += struct.pack('B',num_secondary_audio)
			StnTable += struct.pack('B',num_secondary_video)
			StnTable += struct.pack('B',num_PIP_PG)
			StnTable += zeros[0:5]	# reserved

			for vid in self.title.VideoStreams:
				print "adding vid", vid, type(vid)
				VideoEntry = bytearray(1)	# len
				VideoEntry += '\x01'		# type 01 = elementary stream of the clip used by the PlayItem

				VideoEntry += vid.pid		# stream_pid
				VideoEntry += zeros[0:6]	# reserved
				VideoEntry[0] = struct.pack('B',len(VideoEntry)-1)

				VideoAttr = bytearray(1)	# len
				VideoAttr += vid.streamType	# Video type
				VideoAttr += vid.formatByte	# Format & Framerate
				VideoAttr += zeros[0:3]		# reserved
				VideoAttr[0] = struct.pack('B',len(VideoAttr)-1)
				
				StnTable += VideoEntry
				StnTable += VideoAttr

			for aud in self.title.AudioStreams:
				AudioEntry = bytearray(1)	# len
				AudioEntry += '\x01'		# type 01 = elementary stream of the clip used by the PlayItem
				AudioEntry += aud.pid		# stream_pid
				AudioEntry += zeros[0:6]	# reserved
				AudioEntry[0] = struct.pack('B',len(AudioEntry)-1)

				AudioAttr = bytearray(1)	# len
				AudioAttr += aud.streamType	# stream_coding_type
				AudioAttr += aud.formatByte	# Audio Format & Samplerate
				AudioAttr += aud.languageCode	# Audio Language Code
				AudioAttr[0] = struct.pack('B',len(AudioAttr)-1)

				StnTable += AudioEntry
				StnTable += AudioAttr

			PlayItem += struct.pack('>H',len(StnTable))
			PlayItem += StnTable
			
			PlayList += struct.pack('>H',len(PlayItem))
			PlayList += PlayItem

		mplsbuffer += struct.pack('>L',len(PlayList))
		mplsbuffer += PlayList

		PlayListMarkStartAdress = bytearray(struct.pack('>L',len(mplsbuffer)))
		mplsbuffer[0x0C:0x10] = PlayListMarkStartAdress
		
		if len(self.title.entrypoints) == 0:
			print "no entry points found for this title!"
			self.title.entrypoints.append(0)

		#playlist mark list [(id, type, timestamp, skip duration)]
		#! implement cutlist / skip marks
		markslist = [(0, 1, self.title.entrypoints[0][1]/2, 0)]
		mark_id = 1
		try:
			for chapter_pts in self.title.chaptermarks:
				if (chapter_pts):
					ep_pts = self.title.getEPforOffsetPTS(chapter_pts)
					if ( ep_pts > markslist[0][2] ):
						markslist.append((mark_id, 1, ep_pts, 0))
						mark_id += 1
		except AttributeError:
			print "title has no chaptermarks"
		print "**** final markslist", markslist

		num_marks = len(markslist)
		PlayListMark = bytearray()			# len 4 bytes
		PlayListMark += struct.pack('>H',num_marks)
		for mark_id, mark_type, mark_ts, skip_dur in markslist:
			MarkEntry = bytearray()
			MarkEntry += struct.pack('B',mark_id)	# mark_id
			MarkEntry += struct.pack('B',mark_type)	# mark_type 00=resume, 01=bookmark, 02=skip mark
			MarkEntry += struct.pack('>H',item_i)	# play_item_ref (number of PlayItem that the mark is for
			MarkEntry += struct.pack('>L',mark_ts)	# (in 45khz time ticks)
			MarkEntry += '\xFF\xFF'			# entry_ES_PID
			MarkEntry += struct.pack('>L',skip_dur)	# for skip marks: skip duration
			PlayListMark += MarkEntry

		mplsbuffer += struct.pack('>L',len(PlayListMark))
		mplsbuffer += PlayListMark

		f = open(self.job.workspace+"BDMV/PLAYLIST/%05d.mpls" % self.mpls_num, 'w')
		f.write(buffer(mplsbuffer))
		f.close()
		f = open(self.job.workspace+"BDMV/BACKUP/PLAYLIST/%05d.mpls" % self.mpls_num, 'w')
		f.write(buffer(mplsbuffer))
		f.close()

class CreateClpiTask(Task):
	def __init__(self, job, title, clip_num):
		Task.__init__(self, job, "Create BDMV Clip Info File")
		self.title = title
		self.clip_num = clip_num
		self.job = job
		self.weighting = 10
		self.postconditions.append(GenericPostcondition())

	def run(self, callback):
		self.callback = callback
		self.conduct()
		Task.processFinished(self, 0)
		#try:
			#self.conduct()
			#Task.processFinished(self, 0)
		#except:
			#Task.processFinished(self, 1)

	def conduct(self):
		clpibuffer = bytearray("HDMV0200")		#type_indicator

		clpibuffer += '\x00\x00\x00\xdc'		#sequence_info_start_address
		clpibuffer += '\x00\x00\x00\xf6'		#program_info_start_address
		clpibuffer += zeros[0:4]			#cpi_start_address
		clpibuffer += zeros[0:4]			#clip_mark_start_address
		clpibuffer += zeros[0:4]			#ext_data_start_address
		clpibuffer += zeros[0:12]			#reserved

		ClipInfo = bytearray(4)				# len 4 bytes
		ClipInfo += zeros[0:2]				# reserved
		ClipInfo += '\x01'				# clip_stream_type
		ClipInfo += '\x01'				# application_type
		ClipInfo += '\x00\x00\x00\x00'			# 31 bit reserved + 1 bit is_cc5 (seamless connection condition)
		ClipInfo += self.title.getTsRecordingRate()	# transport stream bitrate
		ClipInfo += self.title.getNumSourcePackets()	# number_source_packets
		ClipInfo += zeros[0:128]

		TS_type_info_block = bytearray('\x00\x1E')	# len 2 bytes
		TS_type_info_block += '\x80'			# validity flags
		TS_type_info_block += 'HDMV'			# format_id
		TS_type_info_block += zeros[0:25]		# nit/stream_format_name?
		ClipInfo += TS_type_info_block

		ClipInfo[0:4] = bytearray(struct.pack('>L',len(ClipInfo)-4))

		num_stc_sequences = 1
		SequenceInfo = bytearray(4)			# len 4 bytes
		SequenceInfo += '\x00'				# reserved
		SequenceInfo += '\x01'				# num_atc_sequences
		SequenceInfo += '\x00\x00\x00\x00'		# spn_atc_start
		SequenceInfo += struct.pack('B',num_stc_sequences)
		SequenceInfo += '\x00'				# offset_stc_id
		num_of_playitems = 1
		for pi in range(num_of_playitems):
			STCEntry = bytearray()
			STCEntry += '\x10\x01'			# pcr_pid #!
			STCEntry += '\x00\x00\x00\x00'		# spn_stc_start
			STCEntry += self.title.InTime		# presentation_start_time (in 45khz)
			STCEntry += self.title.OutTime		# presentation_end_time (in 45khz)
			SequenceInfo += STCEntry
		SequenceInfo[0:4] = struct.pack('>L',len(SequenceInfo)-4)

		num_program_sequences = 1
		num_streams_in_ps = len(self.title.VideoStreams)+len(self.title.AudioStreams)

		ProgramInfo = bytearray(4)			# len 4 bytes
		ProgramInfo += '\x00'				# reserved align
		ProgramInfo += struct.pack('B',num_program_sequences)
		for psi in range(num_program_sequences):
			ProgramEntry = bytearray()
			ProgramEntry += '\x00\x00\x00\x00'	# spn_program_sequence_start
			ProgramEntry += '\x01\x00'		# program_map_pid
			ProgramEntry += struct.pack('B',num_streams_in_ps)
			ProgramEntry += '\x00'			# num_groups
			for stream in self.title.VideoStreams+self.title.AudioStreams:
				StreamEntry = bytearray()
				StreamEntry += stream.pid	# stream_pid
				StreamCodingInfo = bytearray('\x15')		# len 1 byte
				StreamCodingInfo += stream.streamType
				if stream.isVideo:
					StreamCodingInfo += stream.formatByte	# video_format & framerate
					StreamCodingInfo += stream.aspect	# aspect (4 bit) & 2 reserved & 1 oc_flag & 1 reserved
					StreamCodingInfo += zeros[0:2]		#reserved
				elif stream.isAudio:
					StreamCodingInfo += stream.formatByte	# audio_presentation_type & samplerate
					StreamCodingInfo += stream.languageCode	# audio language code
				for i in range(12):
					StreamCodingInfo += '\x30'	# 12 byte padding with ascii char '0'
				StreamCodingInfo += zeros[0:4]		# 4 byte reserved
				StreamEntry += StreamCodingInfo
				ProgramEntry += StreamEntry
			ProgramInfo += ProgramEntry
		ProgramInfo[0:4] = struct.pack('>L',len(ProgramInfo)-4)

		coarse_entrypoints = []	# [(presentation_time_stamp, source_packet_number, ref_ep_fine_id)]
		fine_entrypoints = []	# [(presentation_time_stamp, source_packet_number)]

		prev_coarse = -1
		prev_spn = -1
		fine_ref = -1
		for entrypoint in self.title.entrypoints:
			fine_entrypoints.append((entrypoint[1],entrypoint[0]))
			coarse_pts = entrypoint[1] & 0x1FFF80000
			high_spn = ( entrypoint[0] & 0xFFFE0000 )
			fine_ref += 1

			if coarse_pts > prev_coarse or high_spn > prev_spn:
				coarse_entrypoints.append((entrypoint[1],entrypoint[0],fine_ref))
			prev_coarse = coarse_pts
			prev_spn = high_spn

		CPI = bytearray(4)		# len 4 bytes
		CPI += '\x00\x01' 		# reserved_align & cpi_type = ep_map
		EP_MAP = bytearray('\x00')	# reserved_align
		num_stream_pid = len(self.title.VideoStreams)
		EP_MAP += struct.pack('B',num_stream_pid)

		for stream in self.title.VideoStreams:
			EP_STREAMS = bytearray()
			EP_STREAMS += stream.pid

			ap_stream_type = 1
			num_ep_coarse = len(coarse_entrypoints)
			num_ep_fine = len(fine_entrypoints)
			ep_bits = ((num_ep_fine & 0x3FFFF) + ((num_ep_coarse & 0xFFFF) << 0x12) + ((ap_stream_type & 0xF) << 0x22))
			# 10 bits align, 4 bits ap_stream_type, 16 bits number_ep_coarse, 18 bits number_ep_fine
			EP_STREAMS += struct.pack('>3H',((ep_bits&0xFFFF00000000)>>0x20),((ep_bits&0xFFFF0000)>>0x10),ep_bits&0xFFFF)
			EP_STREAMS += '\x00\x00\x00\x0e'	# ep_map_stream_start_addr
			EP_MAP += EP_STREAMS

		EP_MAP_STREAM = ""
		for stream in self.title.VideoStreams:
			EP_MAP_STREAM = bytearray(4)	# len
			for ep in coarse_entrypoints:
				EP_MAP_STREAM_COARSE = bytearray()

				pts_ep_coarse = ( ep[0] & 0x1FFF80000 ) >> 19
				spn_ep_coarse = ep[1]
				ref_ep_fine_id = ep[2]

				coarse_bits = (pts_ep_coarse & 0x3FFF) + ((ref_ep_fine_id & 0x3FFFF) << 0xE)

				EP_MAP_STREAM_COARSE += struct.pack('>L',coarse_bits)
				EP_MAP_STREAM_COARSE += struct.pack('>L',spn_ep_coarse)

				EP_MAP_STREAM += EP_MAP_STREAM_COARSE

			EP_MAP_STREAM[0:4] = struct.pack('>L',len(EP_MAP_STREAM))

			for ep in fine_entrypoints:
				EP_MAP_STREAM_FINE = bytearray()

				is_angle_change_point = 0
				i_end_position_offset = 1

				pts_ep_fine = ( ep[0] & 0xFFE00 ) >> 0x09
				spn_ep_fine = ( ep[1] & 0x1FFFF )

				fine_bits = (spn_ep_fine & 0x1FFFF) + ((pts_ep_fine & 0x7FF) << 0x11) + (i_end_position_offset << 0x1C) + (is_angle_change_point << 0x1F)

				EP_MAP_STREAM_FINE += struct.pack('>L',fine_bits)

				EP_MAP_STREAM += EP_MAP_STREAM_FINE

		EP_MAP += EP_MAP_STREAM
		CPI += EP_MAP
		CPI[0:4] = struct.pack('>L',len(CPI)-4)

		clpibuffer += ClipInfo
		while len(clpibuffer) < 0xDC:
			clpibuffer += '\x30'	# insert padding
		clpibuffer += SequenceInfo
		while len(clpibuffer) < 0xF6:
			clpibuffer += '\x30'	# insert padding
		clpibuffer += ProgramInfo
		while len(clpibuffer) < 0x134:
			clpibuffer += '\x30'	# insert padding
		clpibuffer[0x10:0x14] = struct.pack('>L',len(clpibuffer)) #cpi_start_address

		clpibuffer += CPI
		clpibuffer[0x14:0x18] = struct.pack('>L',len(clpibuffer)) #clip_mark_start_address
		clpibuffer += zeros[0:4]

		f = open(self.job.workspace+"BDMV/CLIPINF/%05d.clpi" % self.clip_num, 'w')
		f.write(buffer(clpibuffer))
		f.close()
		f = open(self.job.workspace+"BDMV/BACKUP/CLIPINF/%05d.clpi" % self.clip_num, 'w')
		f.write(buffer(clpibuffer))
		f.close()

class CopyThumbTask(Task):
	def __init__(self, job, sourcefile, title_no):
		Task.__init__(self, job, "Copy thumbnail")
		self.setTool("cp")
		source = sourcefile.rsplit('.',1)[0] + ".png"
		dest = self.job.workspace+'BDMV/META/DL/thumb_%05d.png' % title_no
		self.args += [source, dest]
		self.weighting = 10

class CreateMetaTask(Task):
	def __init__(self, job, project):
		Task.__init__(self, job, "Create BDMV Meta Info Files")
		self.project = project
		self.job = job
		self.weighting = 10
		self.postconditions.append(GenericPostcondition())
		self.languageCode = iso639language.get_dvd_id(self.project.menutemplate.settings.menulang.getValue())

	def run(self, callback):
		self.callback = callback
		self.conduct()

	def conduct(self):
		from Tools.XMLTools import stringToXML
		dl = ['<?xml version="1.0" encoding="utf-8" ?>']
		dl.append('<disclib xmlns="urn:BDA:bdmv;disclib" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="urn:BDA:bdmv;disclib disclib.xsd">')
		dl.append('\t<di:discinfo xmlns:di="urn:BDA:bdmv;discinfo">')
		dl.append(strftime("\t<di:date>%Y-%m-%d</di:date>"))
		dl.append('\t\t<di:creator>Dream Multimedia Enigma2</di:creator>')
		dl.append('\t\t<di:title>')
		dl.append('\t\t\t<di:name>'+stringToXML(self.project.settings.name.value)+'</di:name>')
		dl.append('\t\t\t<di:numSets>1</di:numSets>')
		dl.append('\t\t\t<di:setNumber>1</di:setNumber>')
		dl.append('\t\t</di:title>')
		dl.append('\t\t<di:description>')
		dl.append('\t\t\t<di:tableOfContents>')
		for title_no, title in enumerate(self.job.titles):
			dl.append('\t\t\t\t<di:titleName titleNumber="%d">%s</di:titleName>' % (title_no, stringToXML(title.properties.menutitle.value)))
		dl.append('\t\t\t</di:tableOfContents>')
		for title_no in range(len(self.job.titles)):
			dl.append('\t\t\t<di:thumbnail href="thumb_%05d.png" />' % title_no)
		dl.append('\t\t</di:description>')
		dl.append('\t\t<di:language>'+stringToXML(self.languageCode)+'</di:language>')
		dl.append('\t</di:discinfo>')
		dl.append('</disclib>')

		filename = self.job.workspace+'BDMV/META/DL/bdmt_%s.xml' % self.languageCode
		try:	
			file = open(filename, "w")
			for line in dl:
				file.write(line+'\n')
			file.close()
		except:
			Task.processFinished(self, 1)
		Task.processFinished(self, 0)
		self.project.finished_burning = True

class BDMVJob(Job):
	def __init__(self, project):
		Job.__init__(self, "Bludisc Burn")
		self.project = project
		new_workspace = resolveFilename(SCOPE_HDD) + "tmp/" + strftime("bludisc_%Y%m%d%H%M/")
		createDir(new_workspace, True)
		self.workspace = new_workspace
		self.project.workspace = self.workspace
		self.titles = []
		for title in self.project.titles:
			self.titles.append(BludiscTitle(title))	# wrap original DVD-Title into new BludiscTitle objects
		self.conduct()

	def conduct(self):
		if self.project.settings.output.getValue() == "iso":
			CheckDiskspaceTask(self)
		CreateStructureTask(self)
		for i, title in enumerate(self.titles):
			RemuxTask(self, title, i)
		CreateIndexTask(self)
		CreateMobjTask(self)
		for i, title in enumerate(self.titles):
			CreateMplsTask(self, title, i)
			CreateClpiTask(self, title, i)
			CopyThumbTask(self, title.inputfile, i)
		CreateMetaTask(self, self.project)
		output = self.project.settings.output.getValue()
		volName = self.project.settings.name.getValue()
		tool = "growisofs"
		if output == "medium":
			self.name = _("Burn Bludisc")
			burnargs = [ "-Z", "/dev/" + harddiskmanager.getCD(), "-dvd-compat", "-use-the-force-luke=tty"]
		elif output == "iso":
			tool = "genisoimage"
			self.name = _("Create Bludisc ISO file")
			isopathfile = getISOfilename(self.project.settings.isopath.getValue(), volName)
			burnargs = [ "-o", isopathfile ]
		burnargs += [ "-udf", "-allow-limited-size", "-publisher", "Dreambox", "-V", volName, self.workspace ]
		BurnTask(self, burnargs, tool)
		RemoveWorkspaceFolder(self)
