from enigma import eTimer
from Tools.SubRip import SubRipParser
from Tools.TolerantDict import TolerantDict


class SubtitleRenderer():
	def __init__(self, player):
		self.player = player
		self.subtitle_window = player.subtitle_window
		self.checkSubs = eTimer()
		self.checkSubs.callback.append(self.checkPTSAndShowSub)
		self.hideSubs = eTimer()
		self.hideSubs.callback.append(self.onhideSubs)
		self.currentSubsList = TolerantDict({})
		self.currentSubPTS = -1
		self.currentSubEndPTS = -1

	def checkPTSAndShowSub(self):
		seek = self.player.getSeek()
		if seek is None:
			return
		pos = seek.getPlayPosition()
		currentPTS = int(pos[1])

		if self.currentSubEndPTS > -1 and currentPTS >= self.currentSubEndPTS:
			self.onhideSubs()

		currentLine = None
		window_matches = self.currentSubsList.get_all_in_window(currentPTS, 150 * 90)
		if window_matches and len(window_matches) > 0:
			currentLine = window_matches[0][1]

		if currentLine and (self.currentSubPTS < 0 or self.currentSubPTS != currentLine["start"]) and currentPTS >= currentLine["start"]:
			self.currentSubPTS = currentLine["start"]
			self.currentSubEndPTS = currentLine["end"]
			subtitleText = currentLine["text"]
			self.subtitle_window.showSubtitles(subtitleText)

	def onhideSubs(self):
		self.currentSubEndPTS = -1
		self.subtitle_window.showSubtitles("")
		self.subtitle_window.hideSubtitles()

	def loadSubtitles(self, text, subtitleType):
		if subtitleType == "SRT":
			subs_parser = SubRipParser()
			self.currentSubsList = TolerantDict(subs_parser.parse(text))

	def stopSubtitles(self):
		self.checkSubs.stop()
		self.currentSubPTS = -1
		self.currentSubsList = TolerantDict({})

	def startSubtitle(self):
		self.checkSubs.start(10)
