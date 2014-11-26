from Components.Pixmap import MovingPixmap, MultiPixmap
from Tools.Directories import resolveFilename, SCOPE_SKIN
from xml.etree.ElementTree import ElementTree
from Components.config import config, ConfigInteger
from Components.RcModel import rc_model
from boxbranding import getBoxType
from enigma import ePoint

config.misc.rcused = ConfigInteger(default=1)


class Rc:
	def __init__(self):
		self["rc"] = MultiPixmap()

		config.misc.rcused = ConfigInteger(default=1)
		self.isDefaultRc = rc_model.rcIsDefault()
		nSelectPics = 16
		rcheights = (500,) * 2
		self.selectpics = []
		for i in range(nSelectPics):
			self.selectpics.append(
				self.KeyIndicator(
					self, rcheights,
					("indicator_l" + str(i), "indicator_u" + str(i))
				)
			)
		self.rcPositions = RcPositions()
		self.oldNSelectedKeys = self.nSelectedKeys = 0
		self.clearSelectedKeys()
		self.onLayoutFinish.append(self.initRc)

		# Test code to visit every button in turn
		# self.onExecBegin.append(self.test)

	class KeyIndicator:

		class KeyIndicatorPixmap(MovingPixmap):
			def __init__(self, activeYPos, pixmap):
				MovingPixmap.__init__(self)
				self.activeYPos = activeYPos
				self.pixmapName = pixmap

		def __init__(self, owner, activeYPos, pixmaps):
			self.pixmaps = []
			for actYpos, pixmap in zip(activeYPos, pixmaps):
				pm = self.KeyIndicatorPixmap(actYpos, pixmap)
				print "[KeyIndicator]", actYpos, pixmap
				owner[pixmap] = pm
				self.pixmaps.append(pm)
			self.pixmaps.sort(key=lambda x: x.activeYPos)

		def slideTime(self, frm, to, time=20):
			if not self.pixmaps:
				return time
			dist = ((to[0] - frm[0]) ** 2 + (to[1] - frm[1]) ** 2) ** 0.5
			slide = int(round(dist / self.pixmaps[-1].activeYPos * time))
			return slide if slide > 0 else 1

		def moveTo(self, pos, rcpos, moveFrom=None, time=20):
			foundActive = False
			for i in range(len(self.pixmaps)):
				pm = self.pixmaps[i]
				fromx, fromy = pm.getPosition()
				if moveFrom:
					fromPm = moveFrom.pixmaps[i]
					fromx, fromy = fromPm.getPosition()

				x = pos[0] + rcpos[0]
				y = pos[1] + rcpos[1]
				if pos[1] <= pm.activeYPos and not foundActive:
					st = self.slideTime((fromx, fromy), (x, y), time)
					pm.move(fromx, fromy)
					pm.moveTo(x, y, st)
					pm.show()
					pm.startMoving()
					foundActive = True
				else:
					pm.move(x, y)

		def hide(self):
			for pm in self.pixmaps:
				pm.hide()

	def initRc(self):
		if self.isDefaultRc:
			self["rc"].setPixmapNum(config.misc.rcused.value)
		else:
			self["rc"].setPixmapNum(0)
		rcHeight = self["rc"].getSize()[1]
		for kp in self.selectpics:
			nbreaks = len(kp.pixmaps)
			roundup = nbreaks - 1
			n = 1
			for pic in kp.pixmaps:
				pic.activeYPos = (rcHeight * n + roundup) / nbreaks
				n += 1

	def getRcPositions(self):
		return self.rcPositions

	def hideRc(self):
		self["rc"].hide()
		self.hideSelectPics()

	def showRc(self):
		self["rc"].show()

	def selectKey(self, key):
		pos = self.rcPositions.getRcKeyPos(key)

		if pos and self.nSelectedKeys < len(self.selectpics):
			rcpos = self["rc"].getPosition()
			selectPic = self.selectpics[self.nSelectedKeys]
			self.nSelectedKeys += 1
			if self.oldNSelectedKeys > 0 and self.nSelectedKeys > self.oldNSelectedKeys:
				selectPic.moveTo(pos, rcpos, moveFrom=self.selectpics[self.oldNSelectedKeys - 1], time=10)
			else:
				selectPic.moveTo(pos, rcpos, time=10)

	def clearSelectedKeys(self):
		self.showRc()
		self.oldNSelectedKeys = self.nSelectedKeys
		self.nSelectedKeys = 0
		self.hideSelectPics()

	def hideSelectPics(self):
		for selectPic in self.selectpics:
			selectPic.hide()

	# Visits all the buttons in turn, sliding between them.
	# Leaves the indicator at the incorrect position at the end of
	# the test run. Change to another entry in the help list to
	# get the indicator in the correct position
	# def test(self):
	# 	if not self.selectpics or not self.selectpics[0].pixmaps:
	# 		return
	# 	self.hideSelectPics()
	# 	pm = self.selectpics[0].pixmaps[0]
	# 	pm.show()
	# 	rcpos = self["rc"].getPosition()
	# 	for key in self.rcPositions.getRcKeyList():
	# 		pos = self.rcPositions.getRcKeyPos(key)
	# 		pm.addMovePoint(rcpos[0] + pos[0], rcpos[1] + pos[1], time=5)
	# 		pm.addMovePoint(rcpos[0] + pos[0], rcpos[1] + pos[1], time=10)
	# 	pm.startMoving()


class RcPositions:
	def __init__(self):
		isDefaultRc = rc_model.rcIsDefault()
		if isDefaultRc:
			target = resolveFilename(SCOPE_SKIN, "rcpositions.xml")
		else:
			target = rc_model.getRcLocation() + 'rcpositions.xml'
		tree = ElementTree(file=target)
		rcs = tree.getroot()
		self.rcs = {}
		for rc in rcs:
			id = int(rc.attrib["id"])
			self.rcs[id] = {"names": [], "keypos": {}}
			for key in rc:
				name = key.attrib["name"]
				pos = key.attrib["pos"].split(",")
				self.rcs[id]["keypos"][name] = (int(pos[0]), int(pos[1]))
				self.rcs[id]["names"].append(name)
		if isDefaultRc:
			self.rc = self.rcs[config.misc.rcused.getValue()]
		else:
			try:
				self.rc = self.rcs[2]
			except:
				self.rc = self.rcs[config.misc.rcused.getValue()]

	def getRc(self):
		return self.rc

	def getRcKeyPos(self, key):
		return self.rc["keypos"].get(key)

	def getRcKeyList(self):
		return self.rc["names"]
