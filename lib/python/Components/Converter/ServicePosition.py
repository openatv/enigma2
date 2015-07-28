from Converter import Converter
from Poll import Poll
from enigma import iPlayableService
from Components.Element import cached, ElementError
from Components.config import config

class ServicePosition(Poll, Converter, object):
	TYPE_LENGTH = 0
	TYPE_POSITION = 1
	TYPE_REMAINING = 2
	TYPE_GAUGE = 3
	TYPE_SUMMARY = 4
	TYPE_VFD_LENGTH = 5
	TYPE_VFD_POSITION = 6
	TYPE_VFD_REMAINING = 7
	TYPE_VFD_GAUGE = 8
	TYPE_VFD_SUMMARY = 9

	def __init__(self, type):
		Poll.__init__(self)
		Converter.__init__(self, type)

		args = type.split(',')
		type = args.pop(0)

		self.negate = 'Negate' in args
		self.detailed = 'Detailed' in args
		self.showHours = 'ShowHours' in args
		self.showNoSeconds = 'ShowNoSeconds' in args
		self.OnlyMinute = 'OnlyMinute' in args

		if type == "Length":
			self.type = self.TYPE_LENGTH
		elif type == "Position":
			self.type = self.TYPE_POSITION
		elif type == "Remaining":
			self.type = self.TYPE_REMAINING
		elif type == "Gauge":
			self.type = self.TYPE_GAUGE
		elif type == "Summary":
			self.type = self.TYPE_SUMMARY
		elif type == "VFDLength":
			self.type = self.TYPE_VFD_LENGTH
		elif type == "VFDPosition":
			self.type = self.TYPE_VFD_POSITION
		elif type == "VFDRemaining":
			self.type = self.TYPE_VFD_REMAINING
		elif type == "VFDGauge":
			self.type = self.TYPE_VFD_GAUGE
		elif type == "VFDSummary":
			self.type = self.TYPE_VFD_SUMMARY
		else:
			raise ElementError("type must be {Length|Position|Remaining|Gauge|Summary} with optional arguments {Negate|Detailed|ShowHours|ShowNoSeconds} for ServicePosition converter")

		if self.detailed:
			self.poll_interval = 100
		elif self.type == self.TYPE_LENGTH or self.type == self.TYPE_VFD_LENGTH:
			self.poll_interval = 2000
		else:
			self.poll_interval = 500

		self.poll_enabled = True

	def getSeek(self):
		s = self.source.service
		return s and s.seek()

	@cached
	def getPosition(self):
		seek = self.getSeek()
		if seek is None:
			return None
		pos = seek.getPlayPosition()
		if pos[0]:
			return 0
		return pos[1]

	@cached
	def getLength(self):
		seek = self.getSeek()
		if seek is None:
			return None
		length = seek.getLength()
		if length[0]:
			return 0
		return length[1]

	@cached
	def getCutlist(self):
		service = self.source.service
		cue = service and service.cueSheet()
		return cue and cue.getCutList()

	@cached
	def getText(self):
		seek = self.getSeek()
		if seek is None:
			return ""

		if self.type == self.TYPE_SUMMARY or self.type == self.TYPE_SUMMARY:
			s = self.position / 90000
			e = (self.length / 90000) - s
			return "%02d:%02d +%2dm" % (s/60, s%60, e/60)

		l = self.length
		p = self.position
		r = self.length - self.position  # Remaining

		if l < 0:
			return ""

		if not self.detailed:
			l /= 90000
			p /= 90000
			r /= 90000

		if self.negate: l = -l
		if self.negate: p = -p
		if self.negate: r = -r

		if l >= 0:
			sign_l = ""
		else:
			l = -l
			sign_l = "-"

		if p >= 0:
			sign_p = ""
		else:
			p = -p
			sign_p = "-"

		if r >= 0:
			sign_r = ""
		else:
			r = -r
			sign_r = "-"

		if self.type < 5:
			if config.usage.elapsed_time_positive_osd.value:
				sign_p = "+"
				sign_r = "-"
				sign_l = ""
			else:
				sign_p = "-"
				sign_r = "+"
				sign_l = ""

			if config.usage.swap_media_time_display_on_osd.value == "1":  # Mins
				if self.type == self.TYPE_LENGTH:
					return ngettext("%d Min", "%d Mins", (l/60)) % (l/60)
				elif self.type == self.TYPE_POSITION:
					if config.usage.swap_time_remaining_on_osd.value == "1": # Elapsed
						return sign_p + ngettext("%d Min", "%d Mins", (p/60)) % (p/60)
					elif config.usage.swap_time_remaining_on_osd.value == "2": # Elapsed & Remaining
						return sign_p + "%d  " % (p/60) + sign_r + ngettext("%d Min", "%d Mins", (r/60)) % (r/60)
					elif config.usage.swap_time_remaining_on_osd.value == "3": # Remaining & Elapsed
						return sign_r + "%d  " % (r/60) + sign_p + ngettext("%d Min", "%d Mins", (p/60)) % (p/60)
					else:
						return sign_r + ngettext("%d Min", "%d Mins", (r/60)) % (r/60)
				elif self.type == self.TYPE_REMAINING:
					if config.usage.swap_time_remaining_on_osd.value == "1": # Elapsed
						return sign_p + ngettext("%d Min", "%d Mins", (p/60)) % (p/60)
					elif config.usage.swap_time_remaining_on_osd.value == "2" or config.usage.swap_time_remaining_on_osd.value == "3": # Remaining & Elapsed
						return ""
					else:
						return sign_r + ngettext("%d Min", "%d Mins", (r/60)) % (r/60)
			elif config.usage.swap_media_time_display_on_osd.value == "2":  # Mins Secs
				if self.type == self.TYPE_LENGTH:
						return sign_l + "%d:%02d" % (l/60, l%60)
				elif self.type == self.TYPE_POSITION:
					if config.usage.swap_time_remaining_on_osd.value == "1":  # Elapsed
						return sign_p + "%d:%02d" % (p/60, p%60)
					elif config.usage.swap_time_remaining_on_osd.value == "2": # Elapsed & Remaining
						return sign_p + "%d:%02d  " % (p/60, p%60) + sign_r + "%d:%02d" % (r/60, r%60)
					elif config.usage.swap_time_remaining_on_osd.value == "3": # Remaining & Elapsed
						return sign_r + "%d:%02d  " % (r/60, r%60) + sign_p + "%d:%02d" % (p/60, p%60)
					else:
						return sign_r + "%d:%02d" % (r/60, r%60)
				elif self.type == self.TYPE_REMAINING:
					if config.usage.swap_time_remaining_on_osd.value == "1":  # Elapsed
						return sign_p + "%d:%02d" % (p/60, p%60)
					elif config.usage.swap_time_remaining_on_osd.value == "2" or config.usage.swap_time_remaining_on_osd.value == "3": # Remaining & Elapsed
						return ""
					else:
						return sign_r + "%d:%02d" % (r/60, r%60)
			elif config.usage.swap_media_time_display_on_osd.value == "3":  # Hours Mins
				if self.type == self.TYPE_LENGTH:
					return sign_l + "%d:%02d" % (l/3600, l%3600/60)
				elif self.type == self.TYPE_POSITION:
					if config.usage.swap_time_remaining_on_osd.value == "1":  # Elapsed
						return sign_p + "%d:%02d" % (p/3600, p%3600/60)
					elif config.usage.swap_time_remaining_on_osd.value == "2": # Elapsed & Remaining
						return sign_p + "%d:%02d  " % (p/3600, p%3600/60) + sign_r + "%d:%02d" % (r/3600, r%3600/60)
					elif config.usage.swap_time_remaining_on_osd.value == "3": # Remaining & Elapsed
						return sign_r + "%d:%02d  " % (r/3600, r%3600/60) + sign_p + "%d:%02d" % (p/3600, p%3600/60)
					else:
						return sign_r + "%d:%02d" % (r/3600, r%3600/60)
				elif self.type == self.TYPE_REMAINING:
					if config.usage.swap_time_remaining_on_osd.value == "1":  # Elapsed
						return sign_p + "%d:%02d" % (p/3600, p%3600/60)
					elif config.usage.swap_time_remaining_on_osd.value == "2" or config.usage.swap_time_remaining_on_osd.value == "3": # Remaining & Elapsed
						return ""
					else:
						return sign_r + "%d:%02d" % (r/3600, r%3600/60)
			elif config.usage.swap_media_time_display_on_osd.value == "4":  # Hours Mins Secs
				if self.type == self.TYPE_LENGTH:
					return sign_l + "%d:%02d:%02d" % (l/3600, l%3600/60, l%60)
				elif self.type == self.TYPE_POSITION:
					if config.usage.swap_time_remaining_on_osd.value == "1":  # Elapsed
						return sign_p + "%d:%02d:%02d" % (p/3600, p%3600/60, p%60)
					elif config.usage.swap_time_remaining_on_osd.value == "2": # Elapsed & Remaining
						return sign_p + "%d:%02d:%02d  " % (p/3600, p%3600/60, p%60) + sign_r + "%d:%02d:%02d" % (r/3600, r%3600/60, r%60)
					elif config.usage.swap_time_remaining_on_osd.value == "3": # Remaining & Elapsed
						return sign_r + "%d:%02d:%02d  " % (r/3600, r%3600/60, r%60) + sign_p + "%d:%02d:%02d" % (p/3600, p%3600/60, p%60)
					else:
						return sign_r + "%d:%02d:%02d" % (r/3600, r%3600/60, r%60)
				elif self.type == self.TYPE_REMAINING:
					if config.usage.swap_time_remaining_on_osd.value == "1":  # Elapsed
						return sign_p + "%d:%02d:%02d" % (p/3600, p%3600/60, p%60)
					elif config.usage.swap_time_remaining_on_osd.value == "2" or config.usage.swap_time_remaining_on_osd.value == "3": # Remaining & Elapsed
						return ""
					else:
						return sign_r + "%d:%02d:%02d" % (r/3600, r%3600/60, r%60)
			elif config.usage.swap_media_time_display_on_osd.value == "5":  # Percentage
				if self.type == self.TYPE_LENGTH:
					return sign_l + "%d:%02d" % (l/3600, l%3600/60)
				elif self.type == self.TYPE_POSITION:
					if config.usage.swap_time_remaining_on_osd.value == "1":  # Elapsed
						try:
							return sign_p + "%d%%" % ((float(p + 0.0) / float(l + 0.0)) * 100)
						except:
							return ""
					elif config.usage.swap_time_remaining_on_osd.value == "2": # Elapsed & Remaining
						try:
							return sign_p + "%d%%  " % ((float(p + 0.0) / float(l + 0.0)) * 100) + sign_r + "%d%%" % ((float(r + 0.0) / float(l + 0.0)) * 100 + 1)
						except:
							return ""
					elif config.usage.swap_time_remaining_on_osd.value == "3": # Remaining & Elapsed
						try:
							return sign_r + "%d%%  " % ((float(r + 0.0) / float(l + 0.0)) * 100 +1 ) + sign_p + "%d%%" % ((float(p + 0.0) / float(l + 0.0)) * 100)
						except:
							return ""
					else:
						try:
							return sign_r + "%d%%" % ((float(p + 0.0) / float(l + 0.0)) * 100)
						except:
							return ""
				elif self.type == self.TYPE_REMAINING:
					test = 0
					if config.usage.swap_time_remaining_on_osd.value == "1":  # Elapsed
						try:
							return sign_p + "%d%%" % ((float(p + 0.0) / float(l + 0.0)) * 100)
						except:
							return ""
					elif config.usage.swap_time_remaining_on_osd.value == "2" or config.usage.swap_time_remaining_on_osd.value == "3": # Elapsed & Remaining
						return ""
					else:
						try:
							return sign_r + "%d%%" % ((float(p + 0.0) / float(l + 0.0)) * 100)
						except:
							return ""

			else: # Skin Setting
				if not self.detailed:
					if self.showHours:
						if self.showNoSeconds:
							if self.type == self.TYPE_LENGTH:
								return sign_l + "%d:%02d" % (l/3600, l%3600/60)
							elif self.type == self.TYPE_POSITION:
								return sign_p + "%d:%02d" % (p/3600, p%3600/60)
							elif self.type == self.TYPE_REMAINING:
								return sign_r + "%d:%02d" % (r/3600, r%3600/60)
						else:
							if self.type == self.TYPE_LENGTH:
								return sign_l + "%d:%02d:%02d" % (l/3600, l%3600/60, l%60)
							elif self.type == self.TYPE_POSITION:
								return sign_p + "%d:%02d:%02d" % (p/3600, p%3600/60, p%60)
							elif self.type == self.TYPE_REMAINING:
								return sign_r + "%d:%02d:%02d" % (r/3600, r%3600/60, r%60)
					else:
						if self.showNoSeconds:
							if self.type == self.TYPE_LENGTH:
								return ngettext("%d Min", "%d Mins", (l/60)) % (l/60)
							elif self.type == self.TYPE_POSITION:
								return sign_p + ngettext("%d Min", "%d Mins", (p/60)) % (p/60)
							elif self.type == self.TYPE_REMAINING and self.OnlyMinute:
								return ngettext("%d", "%d", (r/60)) % (r/60)
							elif self.type == self.TYPE_REMAINING:
								return sign_r + ngettext("%d Min", "%d Mins", (r/60)) % (r/60)
						else:
							if self.type == self.TYPE_LENGTH:
								return sign_l + "%d:%02d" % (l/60, l%60)
							elif self.type == self.TYPE_POSITION:
								return sign_p + "%d:%02d" % (p/60, p%60)
							elif self.type == self.TYPE_REMAINING:
								return sign_r + "%d:%02d" % (r/60, r%60)
				else:
					if self.showHours:
						if self.type == self.TYPE_LENGTH:
							return sign_l + "%d:%02d:%02d:%03d" % ((l/3600/90000), (l/90000)%3600/60, (l/90000)%60, (l%90000)/90)
						elif self.type == self.TYPE_POSITION:
							return sign_r + "%d:%02d:%02d:%03d" % ((r/3600/90000), (r/90000)%3600/60, (r/90000)%60, (r%90000)/90)
						elif self.type == self.TYPE_REMAINING:
							return sign_p + "%d:%02d:%02d:%03d" % ((p/3600/90000), (p/90000)%3600/60, (p/90000)%60, (p%90000)/90)
					else:
						if self.type == self.TYPE_LENGTH:
							return sign_l + "%d:%02d:%03d" % ((l/60/90000), (l/90000)%60, (l%90000)/90)
						elif self.type == self.TYPE_POSITION:
							return sign_p + "%d:%02d:%03d" % ((p/60/90000), (p/90000)%60, (p%90000)/90)
						elif self.type == self.TYPE_REMAINING:
							return sign_r + "%d:%02d:%03d" % ((r/60/90000), (r/90000)%60, (r%90000)/90)

		else:
			if config.usage.elapsed_time_positive_vfd.value:
				sign_p = "+"
				sign_r = "-"
			else:
				sign_p = "-"
				sign_r = "+"
			if config.usage.swap_media_time_display_on_vfd.value == "1":  # Mins
				if self.type == self.TYPE_VFD_LENGTH:
					return ngettext("%d Min", "%d Mins", (l/60)) % (l/60)
				elif self.type == self.TYPE_VFD_POSITION:
					if config.usage.swap_time_remaining_on_vfd.value == "1": # Elapsed
						return sign_p + ngettext("%d Min", "%d Mins", (p/60)) % (p/60)
					elif config.usage.swap_time_remaining_on_vfd.value == "2": # Elapsed & Remaining
						return sign_p + "%d  " % (p/60) + sign_r + ngettext("%d Min", "%d Mins", (r/60)) % (r/60)
					elif config.usage.swap_time_remaining_on_vfd.value == "3": # Remaining & Elapsed
						return sign_r + "%d  " % (r/60) + sign_p + ngettext("%d Min", "%d Mins", (p/60)) % (p/60)
					else:
						return sign_r + ngettext("%d Min", "%d Mins", (r/60)) % (r/60)
				elif self.type == self.TYPE_VFD_REMAINING:
					if config.usage.swap_time_remaining_on_vfd.value == "1": # Elapsed
						return sign_p + ngettext("%d Min", "%d Mins", (p/60)) % (p/60)
					elif config.usage.swap_time_remaining_on_vfd.value == "2" or config.usage.swap_time_remaining_on_vfd.value == "3": # Remaining & Elapsed
						return ""
					else:
						return sign_r + ngettext("%d Min", "%d Mins", (r/60)) % (r/60)
			elif config.usage.swap_media_time_display_on_vfd.value == "2":  # Mins Secs
				if self.type == self.TYPE_VFD_LENGTH:
						return sign_l + "%d:%02d" % (l/60, l%60)
				elif self.type == self.TYPE_VFD_POSITION:
					if config.usage.swap_time_remaining_on_vfd.value == "1":  # Elapsed
						return sign_p + "%d:%02d" % (p/60, p%60)
					elif config.usage.swap_time_remaining_on_vfd.value == "2": # Elapsed & Remaining
						return sign_p + "%d:%02d  " % (p/60, p%60) + sign_r + "%d:%02d" % (r/60, r%60)
					elif config.usage.swap_time_remaining_on_vfd.value == "3": # Remaining & Elapsed
						return sign_r + "%d:%02d  " % (r/60, r%60) + sign_p + "%d:%02d" % (p/60, p%60)
					else:
						return sign_r + "%d:%02d" % (r/60, r%60)
				elif self.type == self.TYPE_VFD_REMAINING:
					if config.usage.swap_time_remaining_on_vfd.value == "1":  # Elapsed
						return sign_p + "%d:%02d" % (p/60, p%60)
					elif config.usage.swap_time_remaining_on_vfd.value == "2" or config.usage.swap_time_remaining_on_vfd.value == "3": # Remaining & Elapsed
						return ""
					else:
						return sign_r + "%d:%02d" % (r/60, r%60)
			elif config.usage.swap_media_time_display_on_vfd.value == "3":  # Hours Mins
				if self.type == self.TYPE_VFD_LENGTH:
					return sign_l + "%d:%02d" % (l/3600, l%3600/60)
				elif self.type == self.TYPE_VFD_POSITION:
					if config.usage.swap_time_remaining_on_vfd.value == "1":  # Elapsed
						return sign_p + "%d:%02d" % (p/3600, p%3600/60)
					elif config.usage.swap_time_remaining_on_vfd.value == "2": # Elapsed & Remaining
						return sign_p + "%d:%02d  " % (p/3600, p%3600/60) + sign_r + "%d:%02d" % (r/3600, r%3600/60)
					elif config.usage.swap_time_remaining_on_vfd.value == "3": # Remaining & Elapsed
						return sign_r + "%d:%02d  " % (r/3600, r%3600/60) + sign_p + "%d:%02d" % (p/3600, p%3600/60)
					else:
						return sign_r + "%d:%02d" % (r/3600, r%3600/60)
				elif self.type == self.TYPE_VFD_REMAINING:
					if config.usage.swap_time_remaining_on_vfd.value == "1":  # Elapsed
						return sign_p + "%d:%02d" % (p/3600, p%3600/60)
					elif config.usage.swap_time_remaining_on_vfd.value == "2" or config.usage.swap_time_remaining_on_vfd.value == "3": # Remaining & Elapsed
						return ""
					else:
						return sign_r + "%d:%02d" % (r/3600, r%3600/60)
			elif config.usage.swap_media_time_display_on_vfd.value == "4":  # Hours Mins Secs
				if self.type == self.TYPE_VFD_LENGTH:
					return sign_l + "%d:%02d:%02d" % (l/3600, l%3600/60, l%60)
				elif self.type == self.TYPE_VFD_POSITION:
					if config.usage.swap_time_remaining_on_vfd.value == "1":  # Elapsed
						return sign_p + "%d:%02d:%02d" % (p/3600, p%3600/60, p%60)
					elif config.usage.swap_time_remaining_on_vfd.value == "2": # Elapsed & Remaining
						return sign_p + "%d:%02d:%02d  " % (p/3600, p%3600/60, p%60) + sign_r + "%d:%02d:%02d" % (r/3600, r%3600/60, r%60)
					elif config.usage.swap_time_remaining_on_vfd.value == "3": # Remaining & Elapsed
						return sign_r + "%d:%02d:%02d  " % (r/3600, r%3600/60, r%60) + sign_p + "%d:%02d:%02d" % (p/3600, p%3600/60, p%60)
					else:
						return sign_r + "%d:%02d:%02d" % (r/3600, r%3600/60, r%60)
				elif self.type == self.TYPE_VFD_REMAINING:
					if config.usage.swap_time_remaining_on_vfd.value == "1":  # Elapsed
						return sign_p + "%d:%02d:%02d" % (p/3600, p%3600/60, p%60)
					elif config.usage.swap_time_remaining_on_vfd.value == "2" or config.usage.swap_time_remaining_on_vfd.value == "3": # Remaining & Elapsed
						return ""
					else:
						return sign_r + "%d:%02d:%02d" % (r/3600, r%3600/60, r%60)
			elif config.usage.swap_media_time_display_on_vfd.value == "5":  # Percentage
				if self.type == self.TYPE_VFD_LENGTH:
					return sign_l + "%d:%02d" % (l/3600, l%3600/60)
				elif self.type == self.TYPE_VFD_POSITION:
					if config.usage.swap_time_remaining_on_vfd.value == "1":  # Elapsed
						try:
							return sign_p + "%d%%" % ((float(p + 0.0) / float(l + 0.0)) * 100)
						except:
							return ""
					elif config.usage.swap_time_remaining_on_vfd.value == "2": # Elapsed & Remaining
						try:
							return sign_p + "%d%%  " % ((float(p + 0.0) / float(l + 0.0)) * 100) + sign_r + "%d%%" % ((float(r + 0.0) / float(l + 0.0)) * 100 + 1)
						except:
							return ""
					elif config.usage.swap_time_remaining_on_vfd.value == "3": # Remaining & Elapsed
						try:
							return sign_r + "%d%%  " % ((float(r + 0.0) / float(l + 0.0)) * 100 +1 ) + sign_p + "%d%%" % ((float(p + 0.0) / float(l + 0.0)) * 100)
						except:
							return ""
					else:
						try:
							return sign_r + "%d%%" % ((float(p + 0.0) / float(l + 0.0)) * 100)
						except:
							return ""
				elif self.type == self.TYPE_VFD_REMAINING:
					test = 0
					if config.usage.swap_time_remaining_on_vfd.value == "1":  # Elapsed
						try:
							return sign_p + "%d%%" % ((float(p + 0.0) / float(l + 0.0)) * 100)
						except:
							return ""
					elif config.usage.swap_time_remaining_on_vfd.value == "2" or config.usage.swap_time_remaining_on_vfd.value == "3": # Elapsed & Remaining
						return ""
					else:
						try:
							return sign_r + "%d%%" % ((float(p + 0.0) / float(l + 0.0)) * 100)
						except:
							return ""


			else: # Skin Setting
				if not self.detailed:
					if self.showHours:
						if self.showNoSeconds:
							if self.type == self.TYPE_VFD_LENGTH:
								return sign_l + "%d:%02d" % (l/3600, l%3600/60)
							elif self.type == self.TYPE_VFD_POSITION:
								return sign_p + "%d:%02d" % (p/3600, p%3600/60)
							elif self.type == self.TYPE_REMAINING:
								return sign_r + "%d:%02d" % (r/3600, r%3600/60)
						else:
							if self.type == self.TYPE_VFD_LENGTH:
								return sign_l + "%d:%02d:%02d" % (l/3600, l%3600/60, l%60)
							elif self.type == self.TYPE_VFD_POSITION:
								return sign_p + "%d:%02d:%02d" % (p/3600, p%3600/60, p%60)
							elif self.type == self.TYPE_REMAINING:
								return sign_r + "%d:%02d:%02d" % (r/3600, r%3600/60, r%60)
					else:
						if self.showNoSeconds:
							if self.type == self.TYPE_VFD_LENGTH:
								return ngettext("%d Min", "%d Mins", (l/60)) % (l/60)
							elif self.type == self.TYPE_VFD_POSITION:
								return sign_p + ngettext("%d Min", "%d Mins", (p/60)) % (p/60)
							elif self.type == self.TYPE_VFD_REMAINING:
								return sign_r + ngettext("%d Min", "%d Mins", (r/60)) % (r/60)
						else:
							if self.type == self.TYPE_VFD_LENGTH:
								return sign_l + "%d:%02d" % (l/60, l%60)
							elif self.type == self.TYPE_VFD_POSITION:
								return sign_p + "%d:%02d" % (p/60, p%60)
							elif self.type == self.TYPE_REMAINING:
								return sign_r + "%d:%02d" % (r/60, r%60)
				else:
					if self.showHours:
						if self.type == self.TYPE_VFD_LENGTH:
							return sign_l + "%d:%02d:%02d:%03d" % ((l/3600/90000), (l/90000)%3600/60, (l/90000)%60, (l%90000)/90)
						elif self.type == self.TYPE_VFD_POSITION:
							return sign_r + "%d:%02d:%02d:%03d" % ((r/3600/90000), (r/90000)%3600/60, (r/90000)%60, (r%90000)/90)
						elif self.type == self.TYPE_REMAINING:
							return sign_p + "%d:%02d:%02d:%03d" % ((p/3600/90000), (p/90000)%3600/60, (p/90000)%60, (p%90000)/90)
					else:
						if self.type == self.TYPE_VFD_LENGTH:
							return sign_l + "%d:%02d:%03d" % ((l/60/90000), (l/90000)%60, (l%90000)/90)
						elif self.type == self.TYPE_VFD_POSITION:
							return sign_p + "%d:%02d:%03d" % ((p/60/90000), (p/90000)%60, (p%90000)/90)
						elif self.type == self.TYPE_REMAINING:
							return sign_r + "%d:%02d:%03d" % ((r/60/90000), (r/90000)%60, (r%90000)/90)



	# range/value are for the Progress renderer
	range = 10000

	@cached
	def getValue(self):
		pos = self.position
		len = self.length
		if pos is None or len is None or len <= 0:
			return None
		return pos * 10000 / len

	position = property(getPosition)
	length = property(getLength)
	cutlist = property(getCutlist)
	text = property(getText)
	value = property(getValue)

	def changed(self, what):
		cutlist_refresh = what[0] != self.CHANGED_SPECIFIC or what[1] in (iPlayableService.evCuesheetChanged,)
		time_refresh = what[0] == self.CHANGED_POLL or what[0] == self.CHANGED_SPECIFIC and what[1] in (iPlayableService.evCuesheetChanged,)

		if cutlist_refresh:
			if self.type == self.TYPE_GAUGE:
				self.downstream_elements.cutlist_changed()

		if time_refresh:
			self.downstream_elements.changed(what)
