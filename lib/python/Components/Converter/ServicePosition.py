from Components.Converter.Converter import Converter
from time import time as getTime, localtime, strftime
from Components.Converter.Poll import Poll
from enigma import iPlayableService
from Components.Element import cached, ElementError
from Components.config import config


class ServicePosition(Poll, Converter):
	TYPE_LENGTH = 0
	TYPE_POSITION = 1
	TYPE_REMAINING = 2
	TYPE_GAUGE = 3
	TYPE_SUMMARY = 4
	TYPE_ENDTIME = 5
	TYPE_VFD_LENGTH = 6
	TYPE_VFD_POSITION = 7
	TYPE_VFD_REMAINING = 8
	TYPE_VFD_GAUGE = 9
	TYPE_VFD_SUMMARY = 10

	def __init__(self, type):
		Poll.__init__(self)
		Converter.__init__(self, type)

		args = type.split(',')
		type = args.pop(0)

		self.negate = 'Negate' in args
		self.detailed = 'Detailed' in args
		self.showHours = 'ShowHours' in args
		self.showNoSeconds = 'ShowNoSeconds' in args
		self.showNoSeconds2 = 'ShowNoSeconds2' in args
		self.OnlyMinute = 'OnlyMinute' in args
		self.vfd = '7segment' in args

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
		elif type == "EndTime":
			self.type = self.TYPE_ENDTIME
		else:
			raise ElementError("type must be {Length|Position|Remaining|Gauge|Summary} with optional arguments {Negate|Detailed|ShowHours|ShowNoSeconds|ShowNoSeconds2} for ServicePosition converter")

		if self.detailed:
			self.poll_interval = 100
		elif self.type == self.TYPE_LENGTH or self.type == self.TYPE_VFD_LENGTH:
			self.poll_interval = 2000
		elif self.type == self.TYPE_ENDTIME:
			self.poll_interval = 1000
		else:
			self.poll_interval = 500

		self.poll_enabled = True

	def getSeek(self):
		sVal = self.source.service
		return sVal and sVal.seek()

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
		if self.type in (self.TYPE_SUMMARY, self.TYPE_ENDTIME):
			sVal = self.position / 90000
			eVal = (self.length / 90000) - sVal
			if self.type == self.TYPE_SUMMARY:
				return "%02d:%02d +%2dm" % (sVal / 60, sVal % 60, eVal / 60)
			else:
				if self.showNoSeconds or self.showNoSeconds2:
					return strftime("%H:%M", localtime(getTime() + eVal))
				else:
					return strftime("%H:%M:%S", localtime(getTime() + eVal))

		lVal = self.length
		pVal = self.position
		rVal = self.length - self.position  # Remaining

		if lVal < 0:
			return ""

		if not self.detailed:
			lVal /= 90000
			pVal /= 90000
			rVal /= 90000

		if lVal == 0 and pVal > 0:  # Set position to 0 if length = 0 and pos > 0
			pVal = 0

		if self.negate:
			lVal = -lVal
			pVal = -pVal
			rVal = -rVal

		if lVal >= 0:
			sign_l = ""
		else:
			lVal = -lVal
			sign_l = "-"

		if pVal >= 0:
			sign_p = ""
		else:
			pVal = -pVal
			sign_p = "-"

		if rVal >= 0:
			sign_r = ""
		else:
			rVal = -rVal
			sign_r = "-"

		if self.type < self.TYPE_VFD_LENGTH:
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
					return ngettext("%d Min", "%d Mins", (lVal / 60)) % (lVal / 60)
				elif self.type == self.TYPE_POSITION:
					if config.usage.swap_time_remaining_on_osd.value == "1":  # Elapsed
						return sign_p + ngettext("%d Min", "%d Mins", (pVal / 60)) % (pVal / 60)
					elif config.usage.swap_time_remaining_on_osd.value == "2":  # Elapsed & Remaining
						return sign_p + "%d  " % (pVal / 60) + sign_r + ngettext("%d Min", "%d Mins", (rVal / 60)) % (rVal / 60)
					elif config.usage.swap_time_remaining_on_osd.value == "3":  # Remaining & Elapsed
						return sign_r + "%d  " % (rVal / 60) + sign_p + ngettext("%d Min", "%d Mins", (pVal / 60)) % (pVal / 60)
					else:
						return sign_r + ngettext("%d Min", "%d Mins", (rVal / 60)) % (rVal / 60)
				elif self.type == self.TYPE_REMAINING:
					if config.usage.swap_time_remaining_on_osd.value == "1":  # Elapsed
						return sign_p + ngettext("%d Min", "%d Mins", (pVal / 60)) % (pVal / 60)
					elif config.usage.swap_time_remaining_on_osd.value == "2" or config.usage.swap_time_remaining_on_osd.value == "3":  # Remaining & Elapsed
						return ""
					else:
						return sign_r + ngettext("%d Min", "%d Mins", (rVal / 60)) % (rVal / 60)
			elif config.usage.swap_media_time_display_on_osd.value == "2":  # Mins Secs
				if self.type == self.TYPE_LENGTH:
					return sign_l + "%d:%02d" % (lVal / 60, lVal % 60)
				elif self.type == self.TYPE_POSITION:
					if config.usage.swap_time_remaining_on_osd.value == "1":  # Elapsed
						return sign_p + "%d:%02d" % (pVal / 60, pVal % 60)
					elif config.usage.swap_time_remaining_on_osd.value == "2":  # Elapsed & Remaining
						return sign_p + "%d:%02d  " % (pVal / 60, pVal % 60) + sign_r + "%d:%02d" % (rVal / 60, rVal % 60)
					elif config.usage.swap_time_remaining_on_osd.value == "3":  # Remaining & Elapsed
						return sign_r + "%d:%02d  " % (rVal / 60, rVal % 60) + sign_p + "%d:%02d" % (pVal / 60, pVal % 60)
					else:
						return sign_r + "%d:%02d" % (rVal / 60, rVal % 60)
				elif self.type == self.TYPE_REMAINING:
					if config.usage.swap_time_remaining_on_osd.value == "1":  # Elapsed
						return sign_p + "%d:%02d" % (pVal / 60, pVal % 60)
					elif config.usage.swap_time_remaining_on_osd.value == "2" or config.usage.swap_time_remaining_on_osd.value == "3":  # Remaining & Elapsed
						return ""
					else:
						return sign_r + "%d:%02d" % (rVal / 60, rVal % 60)
			elif config.usage.swap_media_time_display_on_osd.value == "3":  # Hours Mins
				if self.type == self.TYPE_LENGTH:
					return sign_l + "%d:%02d" % (lVal / 3600, lVal % 3600 / 60)
				elif self.type == self.TYPE_POSITION:
					if config.usage.swap_time_remaining_on_osd.value == "1":  # Elapsed
						return sign_p + "%d:%02d" % (pVal / 3600, pVal % 3600 / 60)
					elif config.usage.swap_time_remaining_on_osd.value == "2":  # Elapsed & Remaining
						return sign_p + "%d:%02d  " % (pVal / 3600, pVal % 3600 / 60) + sign_r + "%d:%02d" % (rVal / 3600, rVal % 3600 / 60)
					elif config.usage.swap_time_remaining_on_osd.value == "3":  # Remaining & Elapsed
						return sign_r + "%d:%02d  " % (rVal / 3600, rVal % 3600 / 60) + sign_p + "%d:%02d" % (pVal / 3600, pVal % 3600 / 60)
					else:
						return sign_r + "%d:%02d" % (rVal / 3600, rVal % 3600 / 60)
				elif self.type == self.TYPE_REMAINING:
					if config.usage.swap_time_remaining_on_osd.value == "1":  # Elapsed
						return sign_p + "%d:%02d" % (pVal / 3600, pVal % 3600 / 60)
					elif config.usage.swap_time_remaining_on_osd.value == "2" or config.usage.swap_time_remaining_on_osd.value == "3":  # Remaining & Elapsed
						return ""
					else:
						return sign_r + "%d:%02d" % (rVal / 3600, rVal % 3600 / 60)
			elif config.usage.swap_media_time_display_on_osd.value == "4":  # Hours Mins Secs
				if self.type == self.TYPE_LENGTH:
					return sign_l + "%d:%02d:%02d" % (lVal / 3600, lVal % 3600 / 60, lVal % 60)
				elif self.type == self.TYPE_POSITION:
					if config.usage.swap_time_remaining_on_osd.value == "1":  # Elapsed
						return sign_p + "%d:%02d:%02d" % (pVal / 3600, pVal % 3600 / 60, pVal % 60)
					elif config.usage.swap_time_remaining_on_osd.value == "2":  # Elapsed & Remaining
						return sign_p + "%d:%02d:%02d  " % (pVal / 3600, pVal % 3600 / 60, pVal % 60) + sign_r + "%d:%02d:%02d" % (rVal / 3600, rVal % 3600 / 60, rVal % 60)
					elif config.usage.swap_time_remaining_on_osd.value == "3":  # Remaining & Elapsed
						return sign_r + "%d:%02d:%02d  " % (rVal / 3600, rVal % 3600 / 60, rVal % 60) + sign_p + "%d:%02d:%02d" % (pVal / 3600, pVal % 3600 / 60, pVal % 60)
					else:
						return sign_r + "%d:%02d:%02d" % (rVal / 3600, rVal % 3600 / 60, rVal % 60)
				elif self.type == self.TYPE_REMAINING:
					if config.usage.swap_time_remaining_on_osd.value == "1":  # Elapsed
						return sign_p + "%d:%02d:%02d" % (pVal / 3600, pVal % 3600 / 60, pVal % 60)
					elif config.usage.swap_time_remaining_on_osd.value == "2" or config.usage.swap_time_remaining_on_osd.value == "3":  # Remaining & Elapsed
						return ""
					else:
						return sign_r + "%d:%02d:%02d" % (rVal / 3600, rVal % 3600 / 60, rVal % 60)
			elif config.usage.swap_media_time_display_on_osd.value == "5":  # Percentage
				if self.type == self.TYPE_LENGTH:
					return sign_l + "%d:%02d" % (lVal / 3600, lVal % 3600 / 60)
				elif self.type == self.TYPE_POSITION:
					if config.usage.swap_time_remaining_on_osd.value == "1":  # Elapsed
						try:
							return sign_p + "%d%%" % ((float(pVal + 0.0) / float(lVal + 0.0)) * 100)
						except Exception:
							return ""
					elif config.usage.swap_time_remaining_on_osd.value == "2":  # Elapsed & Remaining
						try:
							return sign_p + "%d%%  " % ((float(pVal + 0.0) / float(lVal + 0.0)) * 100) + sign_r + "%d%%" % ((float(rVal + 0.0) / float(lVal + 0.0)) * 100 + 1)
						except Exception:
							return ""
					elif config.usage.swap_time_remaining_on_osd.value == "3":  # Remaining & Elapsed
						try:
							return sign_r + "%d%%  " % ((float(rVal + 0.0) / float(lVal + 0.0)) * 100 + 1) + sign_p + "%d%%" % ((float(pVal + 0.0) / float(lVal + 0.0)) * 100)
						except Exception:
							return ""
					else:
						try:
							return sign_r + "%d%%" % ((float(pVal + 0.0) / float(lVal + 0.0)) * 100)
						except Exception:
							return ""
				elif self.type == self.TYPE_REMAINING:
					# test = 0
					if config.usage.swap_time_remaining_on_osd.value == "1":  # Elapsed
						try:
							return sign_p + "%d%%" % ((float(pVal + 0.0) / float(lVal + 0.0)) * 100)
						except Exception:
							return ""
					elif config.usage.swap_time_remaining_on_osd.value == "2" or config.usage.swap_time_remaining_on_osd.value == "3":  # Elapsed & Remaining
						return ""
					else:
						try:
							return sign_r + "%d%%" % ((float(pVal + 0.0) / float(lVal + 0.0)) * 100)
						except Exception:
							return ""

			else:  # Skin Setting
				if not self.detailed:
					if not self.vfd:
						if self.showHours:
							if self.showNoSeconds or self.showNoSeconds2:
								if self.type == self.TYPE_LENGTH:
									return sign_l + "%d:%02d" % (lVal / 3600, lVal % 3600 / 60)
								elif self.type == self.TYPE_POSITION:
									return sign_p + "%d:%02d" % (pVal / 3600, pVal % 3600 / 60)
								elif self.type == self.TYPE_REMAINING:
									return sign_r + "%d:%02d" % (rVal / 3600, rVal % 3600 / 60)
							else:
								if self.type == self.TYPE_LENGTH:
									return sign_l + "%d:%02d:%02d" % (lVal / 3600, lVal % 3600 / 60, lVal % 60)
								elif self.type == self.TYPE_POSITION:
									return sign_p + "%d:%02d:%02d" % (pVal / 3600, pVal % 3600 / 60, pVal % 60)
								elif self.type == self.TYPE_REMAINING:
									return sign_r + "%d:%02d:%02d" % (rVal / 3600, rVal % 3600 / 60, rVal % 60)
						else:
							if self.showNoSeconds:
								if self.type == self.TYPE_LENGTH:
									return ngettext("%d Min", "%d Mins", (lVal / 60)) % (lVal / 60)
								elif self.type == self.TYPE_POSITION:
									return sign_p + ngettext("%d Min", "%d Mins", (pVal / 60)) % (pVal / 60)
								elif self.type == self.TYPE_REMAINING and self.OnlyMinute:
									return ngettext("%d", "%d", (rVal / 60)) % (rVal / 60)
								elif self.type == self.TYPE_REMAINING:
									return sign_r + ngettext("%d Min", "%d Mins", (rVal / 60)) % (rVal / 60)
							elif self.showNoSeconds2:
								if self.type == self.TYPE_LENGTH:
									return ngettext("%d Min", "%d Mins", (lVal / 60)) % (lVal / 60)
								elif self.type == self.TYPE_POSITION:
									return sign_p + ngettext("%d Min", "%d Mins", (pVal / 60)) % (pVal / 60)
								elif self.type == self.TYPE_REMAINING and self.OnlyMinute:
									if config.usage.elapsed_time_positive_vfd.value:
										myRestMinuten = "%+6d" % (rVal / 60)
									else:
										myRestMinuten = "%+6d" % (rVal / 60 * -1)
									if (rVal / 60) == 0:
										myRestMinuten = " "
									time = getTime()
									t = localtime(time)
									d = _("%-H:%M")
									return strftime(d, t) + myRestMinuten
								elif self.type == self.TYPE_REMAINING:
									return sign_r + ngettext("%d Min", "%d Mins", (rVal / 60)) % (rVal / 60)
							else:
								if self.type == self.TYPE_LENGTH:
									return sign_l + "%d:%02d" % (lVal / 60, lVal % 60)
								elif self.type == self.TYPE_POSITION:
									return sign_p + "%d:%02d" % (pVal / 60, pVal % 60)
								elif self.type == self.TYPE_REMAINING:
									return sign_r + "%d:%02d" % (rVal / 60, rVal % 60)
					else:
						f = rVal / 60
						if f < 60:
							sVal = rVal % 60
						else:
							f /= 60
							sVal = rVal % 3600 / 60
						return "%2d:%02d" % (f, sVal)
				else:
					if self.showHours:
						if self.type == self.TYPE_LENGTH:
							return sign_l + "%d:%02d:%02d:%03d" % ((lVal / 3600 / 90000), (lVal / 90000) % 3600 / 60, (lVal / 90000) % 60, (lVal % 90000) / 90)
						elif self.type == self.TYPE_POSITION:
							return sign_r + "%d:%02d:%02d:%03d" % ((rVal / 3600 / 90000), (rVal / 90000) % 3600 / 60, (rVal / 90000) % 60, (rVal % 90000) / 90)
						elif self.type == self.TYPE_REMAINING:
							return sign_p + "%d:%02d:%02d:%03d" % ((pVal / 3600 / 90000), (pVal / 90000) % 3600 / 60, (pVal / 90000) % 60, (pVal % 90000) / 90)
					else:
						if self.type == self.TYPE_LENGTH:
							return sign_l + "%d:%02d:%03d" % ((lVal / 60 / 90000), (lVal / 90000) % 60, (lVal % 90000) / 90)
						elif self.type == self.TYPE_POSITION:
							return sign_p + "%d:%02d:%03d" % ((pVal / 60 / 90000), (pVal / 90000) % 60, (pVal % 90000) / 90)
						elif self.type == self.TYPE_REMAINING:
							return sign_r + "%d:%02d:%03d" % ((rVal / 60 / 90000), (rVal / 90000) % 60, (rVal % 90000) / 90)
		else:
			if config.usage.elapsed_time_positive_vfd.value:
				sign_p = "+"
				sign_r = "-"
			else:
				sign_p = "-"
				sign_r = "+"
			if config.usage.swap_media_time_display_on_vfd.value == "1":  # Mins
				if self.type == self.TYPE_VFD_LENGTH:
					return ngettext("%d Min", "%d Mins", (lVal / 60)) % (lVal / 60)
				elif self.type == self.TYPE_VFD_POSITION:
					if config.usage.swap_time_remaining_on_vfd.value == "1":  # Elapsed
						return sign_p + ngettext("%d Min", "%d Mins", (pVal / 60)) % (pVal / 60)
					elif config.usage.swap_time_remaining_on_vfd.value == "2":  # Elapsed & Remaining
						return sign_p + "%d  " % (pVal / 60) + sign_r + ngettext("%d Min", "%d Mins", (rVal / 60)) % (rVal / 60)
					elif config.usage.swap_time_remaining_on_vfd.value == "3":  # Remaining & Elapsed
						return sign_r + "%d  " % (rVal / 60) + sign_p + ngettext("%d Min", "%d Mins", (pVal / 60)) % (pVal / 60)
					else:
						return sign_r + ngettext("%d Min", "%d Mins", (rVal / 60)) % (rVal / 60)
				elif self.type == self.TYPE_VFD_REMAINING:
					if config.usage.swap_time_remaining_on_vfd.value == "1":  # Elapsed
						return sign_p + ngettext("%d Min", "%d Mins", (pVal / 60)) % (pVal / 60)
					elif config.usage.swap_time_remaining_on_vfd.value == "2" or config.usage.swap_time_remaining_on_vfd.value == "3":  # Remaining & Elapsed
						return ""
					else:
						return sign_r + ngettext("%d Min", "%d Mins", (rVal / 60)) % (rVal / 60)
			elif config.usage.swap_media_time_display_on_vfd.value == "2":  # Mins Secs
				if self.type == self.TYPE_VFD_LENGTH:
					return sign_l + "%d:%02d" % (lVal / 60, lVal % 60)
				elif self.type == self.TYPE_VFD_POSITION:
					if config.usage.swap_time_remaining_on_vfd.value == "1":  # Elapsed
						return sign_p + "%d:%02d" % (pVal / 60, pVal % 60)
					elif config.usage.swap_time_remaining_on_vfd.value == "2":  # Elapsed & Remaining
						return sign_p + "%d:%02d  " % (pVal / 60, pVal % 60) + sign_r + "%d:%02d" % (rVal / 60, rVal % 60)
					elif config.usage.swap_time_remaining_on_vfd.value == "3":  # Remaining & Elapsed
						return sign_r + "%d:%02d  " % (rVal / 60, rVal % 60) + sign_p + "%d:%02d" % (pVal / 60, pVal % 60)
					else:
						return sign_r + "%d:%02d" % (rVal / 60, rVal % 60)
				elif self.type == self.TYPE_VFD_REMAINING:
					if config.usage.swap_time_remaining_on_vfd.value == "1":  # Elapsed
						return sign_p + "%d:%02d" % (pVal / 60, pVal % 60)
					elif config.usage.swap_time_remaining_on_vfd.value == "2" or config.usage.swap_time_remaining_on_vfd.value == "3":  # Remaining & Elapsed
						return ""
					else:
						return sign_r + "%d:%02d" % (rVal / 60, rVal % 60)
			elif config.usage.swap_media_time_display_on_vfd.value == "3":  # Hours Mins
				if self.type == self.TYPE_VFD_LENGTH:
					return sign_l + "%d:%02d" % (lVal / 3600, lVal % 3600 / 60)
				elif self.type == self.TYPE_VFD_POSITION:
					if config.usage.swap_time_remaining_on_vfd.value == "1":  # Elapsed
						return sign_p + "%d:%02d" % (pVal / 3600, pVal % 3600 / 60)
					elif config.usage.swap_time_remaining_on_vfd.value == "2":  # Elapsed & Remaining
						return sign_p + "%d:%02d  " % (pVal / 3600, pVal % 3600 / 60) + sign_r + "%d:%02d" % (rVal / 3600, rVal % 3600 / 60)
					elif config.usage.swap_time_remaining_on_vfd.value == "3":  # Remaining & Elapsed
						return sign_r + "%d:%02d  " % (rVal / 3600, rVal % 3600 / 60) + sign_p + "%d:%02d" % (pVal / 3600, pVal % 3600 / 60)
					else:
						return sign_r + "%d:%02d" % (rVal / 3600, rVal % 3600 / 60)
				elif self.type == self.TYPE_VFD_REMAINING:
					if config.usage.swap_time_remaining_on_vfd.value == "1":  # Elapsed
						return sign_p + "%d:%02d" % (pVal / 3600, pVal % 3600 / 60)
					elif config.usage.swap_time_remaining_on_vfd.value == "2" or config.usage.swap_time_remaining_on_vfd.value == "3":  # Remaining & Elapsed
						return ""
					else:
						return sign_r + "%d:%02d" % (rVal / 3600, rVal % 3600 / 60)
			elif config.usage.swap_media_time_display_on_vfd.value == "4":  # Hours Mins Secs
				if self.type == self.TYPE_VFD_LENGTH:
					return sign_l + "%d:%02d:%02d" % (lVal / 3600, lVal % 3600 / 60, lVal % 60)
				elif self.type == self.TYPE_VFD_POSITION:
					if config.usage.swap_time_remaining_on_vfd.value == "1":  # Elapsed
						return sign_p + "%d:%02d:%02d" % (pVal / 3600, pVal % 3600 / 60, pVal % 60)
					elif config.usage.swap_time_remaining_on_vfd.value == "2":  # Elapsed & Remaining
						return sign_p + "%d:%02d:%02d  " % (pVal / 3600, pVal % 3600 / 60, pVal % 60) + sign_r + "%d:%02d:%02d" % (rVal / 3600, rVal % 3600 / 60, rVal % 60)
					elif config.usage.swap_time_remaining_on_vfd.value == "3":  # Remaining & Elapsed
						return sign_r + "%d:%02d:%02d  " % (rVal / 3600, rVal % 3600 / 60, rVal % 60) + sign_p + "%d:%02d:%02d" % (pVal / 3600, pVal % 3600 / 60, pVal % 60)
					else:
						return sign_r + "%d:%02d:%02d" % (rVal / 3600, rVal % 3600 / 60, rVal % 60)
				elif self.type == self.TYPE_VFD_REMAINING:
					if config.usage.swap_time_remaining_on_vfd.value == "1":  # Elapsed
						return sign_p + "%d:%02d:%02d" % (pVal / 3600, pVal % 3600 / 60, pVal % 60)
					elif config.usage.swap_time_remaining_on_vfd.value == "2" or config.usage.swap_time_remaining_on_vfd.value == "3":  # Remaining & Elapsed
						return ""
					else:
						return sign_r + "%d:%02d:%02d" % (rVal / 3600, rVal % 3600 / 60, rVal % 60)
			elif config.usage.swap_media_time_display_on_vfd.value == "5":  # Percentage
				if self.type == self.TYPE_VFD_LENGTH:
					return sign_l + "%d:%02d" % (lVal / 3600, lVal % 3600 / 60)
				elif self.type == self.TYPE_VFD_POSITION:
					if config.usage.swap_time_remaining_on_vfd.value == "1":  # Elapsed
						try:
							return sign_p + "%d%%" % ((float(pVal + 0.0) / float(lVal + 0.0)) * 100)
						except Exception:
							return ""
					elif config.usage.swap_time_remaining_on_vfd.value == "2":  # Elapsed & Remaining
						try:
							return sign_p + "%d%%  " % ((float(pVal + 0.0) / float(lVal + 0.0)) * 100) + sign_r + "%d%%" % ((float(rVal + 0.0) / float(lVal + 0.0)) * 100 + 1)
						except Exception:
							return ""
					elif config.usage.swap_time_remaining_on_vfd.value == "3":  # Remaining & Elapsed
						try:
							return sign_r + "%d%%  " % ((float(rVal + 0.0) / float(lVal + 0.0)) * 100 + 1) + sign_p + "%d%%" % ((float(pVal + 0.0) / float(lVal + 0.0)) * 100)
						except Exception:
							return ""
					else:
						try:
							return sign_r + "%d%%" % ((float(pVal + 0.0) / float(lVal + 0.0)) * 100)
						except Exception:
							return ""
				elif self.type == self.TYPE_VFD_REMAINING:
					# test = 0
					if config.usage.swap_time_remaining_on_vfd.value == "1":  # Elapsed
						try:
							return sign_p + "%d%%" % ((float(pVal + 0.0) / float(lVal + 0.0)) * 100)
						except Exception:
							return ""
					elif config.usage.swap_time_remaining_on_vfd.value == "2" or config.usage.swap_time_remaining_on_vfd.value == "3":  # Elapsed & Remaining
						return ""
					else:
						try:
							return sign_r + "%d%%" % ((float(pVal + 0.0) / float(lVal + 0.0)) * 100)
						except Exception:
							return ""

			else:  # Skin Setting
				if not self.detailed:
					if self.showHours:
						if self.showNoSeconds:
							if self.type == self.TYPE_VFD_LENGTH:
								return sign_l + "%d:%02d" % (lVal / 3600, lVal % 3600 / 60)
							elif self.type == self.TYPE_VFD_POSITION:
								return sign_p + "%d:%02d" % (pVal / 3600, pVal % 3600 / 60)
							elif self.type == self.TYPE_REMAINING:
								return sign_r + "%d:%02d" % (rVal / 3600, rVal % 3600 / 60)
						else:
							if self.type == self.TYPE_VFD_LENGTH:
								return sign_l + "%d:%02d:%02d" % (lVal / 3600, lVal % 3600 / 60, lVal % 60)
							elif self.type == self.TYPE_VFD_POSITION:
								return sign_p + "%d:%02d:%02d" % (pVal / 3600, pVal % 3600 / 60, pVal % 60)
							elif self.type == self.TYPE_REMAINING:
								return sign_r + "%d:%02d:%02d" % (rVal / 3600, rVal % 3600 / 60, rVal % 60)
					else:
						if self.showNoSeconds:
							if self.type == self.TYPE_VFD_LENGTH:
								return ngettext("%d Min", "%d Mins", (lVal / 60)) % (lVal / 60)
							elif self.type == self.TYPE_VFD_POSITION:
								return sign_p + ngettext("%d Min", "%d Mins", (pVal / 60)) % (pVal / 60)
							elif self.type == self.TYPE_VFD_REMAINING:
								return sign_r + ngettext("%d Min", "%d Mins", (rVal / 60)) % (rVal / 60)
						else:
							if self.type == self.TYPE_VFD_LENGTH:
								return sign_l + "%d:%02d" % (lVal / 60, lVal % 60)
							elif self.type == self.TYPE_VFD_POSITION:
								return sign_p + "%d:%02d" % (pVal / 60, pVal % 60)
							elif self.type == self.TYPE_REMAINING:
								return sign_r + "%d:%02d" % (rVal / 60, rVal % 60)
				else:
					if self.showHours:
						if self.type == self.TYPE_VFD_LENGTH:
							return sign_l + "%d:%02d:%02d:%03d" % ((lVal / 3600 / 90000), (lVal / 90000) % 3600 / 60, (lVal / 90000) % 60, (lVal % 90000) / 90)
						elif self.type == self.TYPE_VFD_POSITION:
							return sign_r + "%d:%02d:%02d:%03d" % ((rVal / 3600 / 90000), (rVal / 90000) % 3600 / 60, (rVal / 90000) % 60, (rVal % 90000) / 90)
						elif self.type == self.TYPE_REMAINING:
							return sign_p + "%d:%02d:%02d:%03d" % ((pVal / 3600 / 90000), (pVal / 90000) % 3600 / 60, (pVal / 90000) % 60, (pVal % 90000) / 90)
					else:
						if self.type == self.TYPE_VFD_LENGTH:
							return sign_l + "%d:%02d:%03d" % ((lVal / 60 / 90000), (lVal / 90000) % 60, (lVal % 90000) / 90)
						elif self.type == self.TYPE_VFD_POSITION:
							return sign_p + "%d:%02d:%03d" % ((pVal / 60 / 90000), (pVal / 90000) % 60, (pVal % 90000) / 90)
						elif self.type == self.TYPE_REMAINING:
							return sign_r + "%d:%02d:%03d" % ((rVal / 60 / 90000), (rVal / 90000) % 60, (rVal % 90000) / 90)

	# range/value are for the Progress renderer
	range = 10000

	@cached
	def getValue(self):
		pVal = self.position
		lVal = self.length
		if pVal is None or lVal is None or lVal <= 0:
			return None
		return pVal * 10000 // lVal

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
