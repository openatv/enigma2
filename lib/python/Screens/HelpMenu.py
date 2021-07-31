from __future__ import print_function
from enigma import eActionMap, eListboxPythonMultiContent, eListbox, gFont
from keyids import KEYIDS
from Components.ActionMap import ActionMap, queryKeyBinding
from Components.config import config
from Components.GUIComponent import GUIComponent
from Components.InputDevice import remoteControl
from Components.Label import Label
from Components.Pixmap import MovingPixmap, Pixmap
from Components.SystemInfo import BoxInfo
from Components.Sources.List import List
from Screens.Rc import Rc
from Screens.Screen import Screen
from Tools.KeyBindings import getKeyDescription
from Tools.LoadPixmap import LoadPixmap
from skin import parameters, fonts


class HelpableScreen:
	def __init__(self):
		self["helpActions"] = ActionMap(["HelpActions"],
			{
				"displayHelp": self.showHelp,
			})

	def showHelp(self):
		try:
			if self.secondInfoBarScreen and self.secondInfoBarScreen.shown:
				self.secondInfoBarScreen.hide()
		except:
			pass
		self.session.openWithCallback(self.callHelpAction, HelpMenu, self.helpList)

	def callHelpAction(self, *args):
		if args:
			(actionmap, context, action) = args
			actionmap.action(context, action)


class ShowRemoteControl:
	def __init__(self):
		self["rc"] = Pixmap()
		self.rcPosition = None
		buttonImages = 16
		rcHeights = (500,) * 2
		self.selectPics = []
		for indicator in range(buttonImages):
			self.selectPics.append(self.KeyIndicator(self, rcHeights, ("indicatorU%d" % indicator, "indicatorL%d" % indicator)))
		self.nSelectedKeys = 0
		self.oldNSelectedKeys = 0
		self.clearSelectedKeys()
		self.wizardConversion = {  # This dictionary converts named buttons in the Wizards to keyIds.
			"OK": KEYIDS.get("KEY_OK"),
			"EXIT": KEYIDS.get("KEY_EXIT"),
			"LEFT": KEYIDS.get("KEY_LEFT"),
			"RIGHT": KEYIDS.get("KEY_RIGHT"),
			"UP": KEYIDS.get("KEY_UP"),
			"DOWN": KEYIDS.get("KEY_DOWN"),
			"RED": KEYIDS.get("KEY_RED"),
			"GREEN": KEYIDS.get("KEY_GREEN"),
			"YELLOW": KEYIDS.get("KEY_YELLOW"),
			"BLUE": KEYIDS.get("KEY_BLUE")
		}
		self.onLayoutFinish.append(self.initRemoteControl)

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
				owner[pixmap] = pm
				self.pixmaps.append(pm)
			self.pixmaps.sort(key=lambda x: x.activeYPos)

		def slideTime(self, start, end, time=20):
			if not self.pixmaps:
				return time
			dist = ((end[0] - start[0]) ** 2 + (end[1] - start[1]) ** 2) ** 0.5
			slide = int(round(dist / self.pixmaps[-1].activeYPos * time))
			return slide if slide > 0 else 1

		def moveTo(self, pos, rcPos, moveFrom=None, time=20):
			foundActive = False
			for index, pixmap in enumerate(self.pixmaps):
				fromX, fromY = pixmap.getPosition()
				if moveFrom:
					fromX, fromY = moveFrom.pixmaps[index].getPosition()
				x = pos[0] + rcPos[0]
				y = pos[1] + rcPos[1]
				if pos[1] <= pixmap.activeYPos and not foundActive:
					pixmap.move(fromX, fromY)
					pixmap.moveTo(x, y, self.slideTime((fromX, fromY), (x, y), time))
					pixmap.show()
					pixmap.startMoving()
					foundActive = True
				else:
					pixmap.move(x, y)

		def hide(self):
			for pixmap in self.pixmaps:
				pixmap.hide()

	def initRemoteControl(self):
		rc = LoadPixmap(BoxInfo.getItem("RCImage"))
		if rc:
			self["rc"].instance.setPixmap(rc)
			self.rcPosition = self["rc"].getPosition()
			rcHeight = self["rc"].getSize()[1]
			for selectPic in self.selectPics:
				nBreaks = len(selectPic.pixmaps)
				roundup = nBreaks - 1
				n = 1
				for pic in selectPic.pixmaps:
					pic.activeYPos = (rcHeight * n + roundup) / nBreaks
					n += 1

	def selectKey(self, keyId):
		if self.rcPosition:
			if isinstance(keyId, str):  # This test looks for named buttons in the Wizards and converts them to keyIds.
				keyId = self.wizardConversion.get(keyId, 0)
			pos = remoteControl.getRemoteControlKeyPos(keyId)
			if pos and self.nSelectedKeys < len(self.selectPics):
				selectPic = self.selectPics[self.nSelectedKeys]
				self.nSelectedKeys += 1
				if self.oldNSelectedKeys > 0 and self.nSelectedKeys > self.oldNSelectedKeys:
					selectPic.moveTo(pos, self.rcPosition, moveFrom=self.selectPics[self.oldNSelectedKeys - 1], time=int(config.usage.helpAnimationSpeed.value))
				else:
					selectPic.moveTo(pos, self.rcPosition, time=int(config.usage.helpAnimationSpeed.value))

	def clearSelectedKeys(self):
		self.hideSelectPics()
		self.oldNSelectedKeys = self.nSelectedKeys
		self.nSelectedKeys = 0

	def hideSelectPics(self):
		for selectPic in self.selectPics:
			selectPic.hide()

	# Visits all the buttons in turn, sliding between them.  Starts with
	# the top left button and finishes on the bottom right button.
	# Leaves the highlight on the bottom right button at the end of
	# the test run.  The callback method can be used to restore the
	# highlight(s) to their correct position(s) when the animation
	# completes.
	#
	def testHighlights(self, callback=None):
		if not self.selectPics or not self.selectPics[0].pixmaps:
			return
		self.hideSelectPics()
		pixmap = self.selectPics[0].pixmaps[0]
		pixmap.show()
		rcPos = self["rc"].getPosition()
		pixmap.clearPath()
		for keyId in remoteControl.getRemoteControlKeyList():
			pos = remoteControl.getRemoteControlKeyPos(keyId)
			pixmap.addMovePoint(rcPos[0] + pos[0], rcPos[1] + pos[1], time=5)
			pixmap.addMovePoint(rcPos[0] + pos[0], rcPos[1] + pos[1], time=10)
		pixmap.startMoving(callback)


class HelpMenu(Screen, Rc):
	def __init__(self, session, list):
		Screen.__init__(self, session)
		Screen.setTitle(self, _("Help"))
		self.onSelChanged = []
		self["list"] = HelpMenuList(list, self.close)
		self["list"].onSelChanged.append(self.SelectionChanged)
		Rc.__init__(self)
		self["long_key"] = Label("")

		self["actions"] = ActionMap(["WizardActions"],
		{
			"ok": self["list"].ok,
			"back": self.close,
		}, -1)

		self.onLayoutFinish.append(self.SelectionChanged)

	def SelectionChanged(self):
		self.clearSelectedKeys()
		selection = self["list"].getCurrent()
		if selection:
			selection = selection[3]
		#arrow = self["arrowup"]
		print("[HelpMenu] selection:", selection)

		longText = ""
		if selection and len(selection) > 1:
			if selection[1] == "SHIFT":
				self.selectKey("SHIFT")
			elif selection[1] == "long":
				longText = _("Long key press")
		self["long_key"].setText(longText)

		self.selectKey(selection[0])
		#if selection is None:
		print("[HelpMenu] select arrow")
		#	arrow.moveTo(selection[1], selection[2], 1)
		#	arrow.startMoving()
		#	arrow.show()


class HelpMenuList(GUIComponent):
	def __init__(self, helplist, callback):
		GUIComponent.__init__(self)
		self.onSelChanged = []
		self.l = eListboxPythonMultiContent()
		self.callback = callback
		self.extendedHelp = False

		l = []
		for (actionmap, context, actions) in helplist:
			for (action, help) in actions:
				if hasattr(help, '__call__'):
					help = help()
				if not help:
					continue
				buttons = queryKeyBinding(context, action)

				# do not display entries which are not accessible from keys
				if not len(buttons):
					continue

				name = None
				flags = 0

				for n in buttons:
					(name, flags) = (getKeyDescription(n[0]), n[1])
					if name is not None:
						break

				# only show entries with keys that are available on the used rc
				if name is None:
					continue

				if flags & 8: # for long keypresses, prepend l_ into the key name.
					name = (name[0], "long")

				entry = [(actionmap, context, action, name)]

				if isinstance(help, list):
					self.extendedHelp = True
					print("[HelpMenuList] extendedHelpEntry found")
					x, y, w, h = parameters.get("HelpMenuListExtHlp0", (0, 0, 600, 26))
					x1, y1, w1, h1 = parameters.get("HelpMenuListExtHlp1", (0, 28, 600, 20))
					entry.extend((
						(eListboxPythonMultiContent.TYPE_TEXT, x, y, w, h, 0, 0, help[0]),
						(eListboxPythonMultiContent.TYPE_TEXT, x1, y1, w1, h1, 1, 0, help[1])
					))
				else:
					x, y, w, h = parameters.get("HelpMenuListHlp", (0, 0, 600, 28))
					entry.append((eListboxPythonMultiContent.TYPE_TEXT, x, y, w, h, 0, 0, help))

				l.append(entry)

		self.l.setList(l)
		if self.extendedHelp is True:
			font = fonts.get("HelpMenuListExt0", ("Regular", 24, 50))
			self.l.setFont(0, gFont(font[0], font[1]))
			self.l.setItemHeight(font[2])
			font = fonts.get("HelpMenuListExt1", ("Regular", 18))
			self.l.setFont(1, gFont(font[0], font[1]))
		else:
			font = fonts.get("HelpMenuList", ("Regular", 24, 38))
			self.l.setFont(0, gFont(font[0], font[1]))
			self.l.setItemHeight(font[2])

	def ok(self):
		# a list entry has a "private" tuple as first entry...
		l = self.getCurrent()
		if l is None:
			return
		# ...containing (Actionmap, Context, Action, keydata).
		# we returns this tuple to the callback.
		self.callback(l[0], l[1], l[2])

	def getCurrent(self):
		sel = self.l.getCurrentSelection()
		return sel and sel[0]

	GUI_WIDGET = eListbox

	def postWidgetCreate(self, instance):
		instance.setContent(self.l)
		instance.selectionChanged.get().append(self.selectionChanged)
		self.instance.setWrapAround(True)

	def preWidgetRemove(self, instance):
		instance.setContent(None)
		instance.selectionChanged.get().remove(self.selectionChanged)

	def selectionChanged(self):
		for x in self.onSelChanged:
			x()
