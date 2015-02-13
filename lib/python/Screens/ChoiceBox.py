from Screens.Screen import Screen
from Components.ActionMap import NumberActionMap
from Components.Label import Label
from Components.ChoiceList import ChoiceEntryComponent, ChoiceList
from Components.Sources.StaticText import StaticText
import enigma

class ChoiceBox(Screen):
	def __init__(self, session, title="", list=None, keys=None, selection=0, skin_name=None, text=""):
		if not list: list = []
		if not skin_name: skin_name = []
		Screen.__init__(self, session)

		if isinstance(skin_name, str):
			skin_name = [skin_name]
		self.skinName = skin_name + ["ChoiceBox"]
		self["text"] = Label()
		if title:
			title = _(title)
			if len(title) < 55 and title.find('\n') == -1:
				Screen.setTitle(self, title)
			elif title.find('\n') != -1:
				temptext = title.split('\n')
				if len(temptext[0]) < 55:
					Screen.setTitle(self, temptext[0])
					count = 2
					labeltext = ""
					while len(temptext) >= count:
						if labeltext:
							labeltext += '\n'
						labeltext = labeltext + temptext[count-1]
						count += 1
						print 'count',count
					self["text"].setText(labeltext)
				else:
					self["text"] = Label(title)
			else:
				self["text"] = Label(title)
		elif text:
			self["text"] = Label(_(text))
		self.list = []
		self.summarylist = []
		if keys is None:
			self.__keys = [ "1", "2", "3", "4", "5", "6", "7", "8", "9", "0", "red", "green", "yellow", "blue" ] + (len(list) - 10) * [""]
		else:
			self.__keys = keys + (len(list) - len(keys)) * [""]

		self.keymap = {}
		pos = 0
		for x in list:
			strpos = str(self.__keys[pos])
			self.list.append(ChoiceEntryComponent(key = strpos, text = x))
			if self.__keys[pos] != "":
				self.keymap[self.__keys[pos]] = list[pos]
			self.summarylist.append((self.__keys[pos], x[0]))
			pos += 1
		self["list"] = ChoiceList(list = self.list, selection = selection)
		self["summary_list"] = StaticText()
		self["summary_selection"] = StaticText()
		self.updateSummary(selection)

		self["actions"] = NumberActionMap(["WizardActions", "InputActions", "ColorActions"],
		{
			"ok": self.go,
			"1": self.keyNumberGlobal,
			"2": self.keyNumberGlobal,
			"3": self.keyNumberGlobal,
			"4": self.keyNumberGlobal,
			"5": self.keyNumberGlobal,
			"6": self.keyNumberGlobal,
			"7": self.keyNumberGlobal,
			"8": self.keyNumberGlobal,
			"9": self.keyNumberGlobal,
			"0": self.keyNumberGlobal,
			"red": self.keyRed,
			"green": self.keyGreen,
			"yellow": self.keyYellow,
			"blue": self.keyBlue,
			"up": self.up,
			"down": self.down,
			"left": self.left,
			"right": self.right
		}, -1)

		self["cancelaction"] = NumberActionMap(["WizardActions", "InputActions", "ColorActions"],
		{
			"back": self.cancel,
		}, -1)

	def autoResize(self):
		desktop_w = enigma.getDesktop(0).size().width()
		desktop_h = enigma.getDesktop(0).size().height()
		count = len(self.list)
		itemheight = self["list"].getItemHeight()
		if count > 15:
			count = 15
		if not self["text"].text:
			# move list
			textsize = (520, 0)
			listsize = (520, itemheight*count)
			self["list"].instance.move(enigma.ePoint(0, 0))
			self["list"].instance.resize(enigma.eSize(*listsize))
		else:
			textsize = self["text"].getSize()
			if textsize[0] < textsize[1]:
				textsize = (textsize[1],textsize[0]+10)
			if textsize[0] > 520:
				textsize = (textsize[0], textsize[1]+itemheight)
			else:
				textsize = (520, textsize[1]+itemheight)
			listsize = (textsize[0], itemheight*count)
			# resize label
			self["text"].instance.resize(enigma.eSize(*textsize))
			self["text"].instance.move(enigma.ePoint(10, 10))
			# move list
			self["list"].instance.move(enigma.ePoint(0, textsize[1]))
			self["list"].instance.resize(enigma.eSize(*listsize))

		wsizex = textsize[0]
		wsizey = textsize[1]+listsize[1]
		wsize = (wsizex, wsizey)
		self.instance.resize(enigma.eSize(*wsize))

		# center window
		self.instance.move(enigma.ePoint((desktop_w-wsizex)/2, (desktop_h-wsizey)/2))

	def left(self):
		if len(self["list"].list) > 0:
			while 1:
				self["list"].instance.moveSelection(self["list"].instance.pageUp)
				self.updateSummary(self["list"].l.getCurrentSelectionIndex())
				if self["list"].l.getCurrentSelection()[0][0] != "--" or self["list"].l.getCurrentSelectionIndex() == 0:
					break

	def right(self):
		if len(self["list"].list) > 0:
			while 1:
				self["list"].instance.moveSelection(self["list"].instance.pageDown)
				self.updateSummary(self["list"].l.getCurrentSelectionIndex())
				if self["list"].l.getCurrentSelection()[0][0] != "--" or self["list"].l.getCurrentSelectionIndex() == 0:
					break

	def up(self):
		if len(self["list"].list) > 0:
			while 1:
				self["list"].instance.moveSelection(self["list"].instance.moveUp)
				self.updateSummary(self["list"].l.getCurrentSelectionIndex())
				if self["list"].l.getCurrentSelection()[0][0] != "--" or self["list"].l.getCurrentSelectionIndex() == 0:
					break

	def down(self):
		if len(self["list"].list) > 0:
			while 1:
				self["list"].instance.moveSelection(self["list"].instance.moveDown)
				self.updateSummary(self["list"].l.getCurrentSelectionIndex())
				if self["list"].l.getCurrentSelection()[0][0] != "--" or self["list"].l.getCurrentSelectionIndex() == len(self["list"].list) - 1:
					break

	# runs a number shortcut
	def keyNumberGlobal(self, number):
		self.goKey(str(number))

	# runs the current selected entry
	def go(self):
		cursel = self["list"].l.getCurrentSelection()
		if cursel:
			self.goEntry(cursel[0])
		else:
			self.cancel()

	# runs a specific entry
	def goEntry(self, entry):
		if entry and len(entry) > 3 and isinstance(entry[1], str) and entry[1] == "CALLFUNC":
			arg = entry[3]
			entry[2](arg)
		elif entry and len(entry) > 2 and isinstance(entry[1], str) and entry[1] == "CALLFUNC":
			entry[2](None)
		else:
			self.close(entry)

	# lookups a key in the keymap, then runs it
	def goKey(self, key):
		if self.keymap.has_key(key):
			entry = self.keymap[key]
			self.goEntry(entry)

	# runs a color shortcut
	def keyRed(self):
		self.goKey("red")

	def keyGreen(self):
		self.goKey("green")

	def keyYellow(self):
		self.goKey("yellow")

	def keyBlue(self):
		self.goKey("blue")

	def updateSummary(self, curpos=0):
		pos = 0
		summarytext = ""
		for entry in self.summarylist:
			if curpos-2 < pos < curpos+5:
				if pos == curpos:
					summarytext += ">"
					self["summary_selection"].setText(entry[1])
				else:
					summarytext += entry[0]
				summarytext += ' ' + entry[1] + '\n'
			pos += 1
		self["summary_list"].setText(summarytext)

	def cancel(self):
		self.close(None)
