from enigma import eTimer
from Tools.SubRip import SubRipParser
from Tools.TolerantDict import TolerantDict


class SubtitleRenderer:
	def __init__(self, player):
		self.player = player
		self.subtitle_window = player.subtitle_window
		self.check_subs = eTimer()
		self.check_subs.callback.append(self._check_pts_and_show_sub)
		self.hide_subs = eTimer()
		self.hide_subs.callback.append(self._on_hide_subs)
		self.current_subs_list = TolerantDict({})
		self.current_sub_pts = -1
		self.current_sub_end_pts = -1

	def _check_pts_and_show_sub(self):
		seek = self.player.getSeek()
		if seek is None:
			return
		pos = seek.getPlayPosition()
		current_pts = int(pos[1])

		if self.current_sub_end_pts > -1 and current_pts >= self.current_sub_end_pts:
			self._on_hide_subs()

		current_line = None
		window_matches = self.current_subs_list.get_all_in_window(current_pts, 150 * 90)
		if window_matches and len(window_matches) > 0:
			current_line = window_matches[0][1]

		if current_line and (self.current_sub_pts < 0 or self.current_sub_pts != current_line["start"]) and current_pts >= current_line["start"]:
			self.current_sub_pts = current_line["start"]
			self.current_sub_end_pts = current_line["end"]
			subtitle_text = current_line["text"]
			self.subtitle_window.showSubtitles(subtitle_text)

	def _on_hide_subs(self):
		self.current_sub_end_pts = -1
		self.subtitle_window.showSubtitles("")
		self.subtitle_window.hideSubtitles()

	def loadSubtitles(self, text, subtitleType):
		if subtitleType == "SRT":
			subs_parser = SubRipParser()
			self.current_subs_list = TolerantDict(subs_parser.parse(text))
			return True
		return False

	def stopSubtitles(self):
		self.check_subs.stop()
		self.current_sub_pts = -1
		self.current_subs_list = TolerantDict({})

	def startSubtitle(self):
		self.check_subs.start(10)
