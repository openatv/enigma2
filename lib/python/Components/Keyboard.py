from __future__ import print_function
from __future__ import absolute_import
from os import listdir

from Components.Console import Console
# from Components.Language import language
from Tools.Directories import SCOPE_KEYMAPS, pathExists, resolveFilename


class Keyboard:
	def __init__(self):
		self.keyboardMaps = []
		self.readKeyboardMapFiles()

	def readKeyboardMapFiles(self):
		for keymapFile in listdir(resolveFilename(SCOPE_KEYMAPS)):
			if keymapFile.endswith(".info"):
				mapFile = None
				mapName = None
				try:
					with open(resolveFilename(SCOPE_KEYMAPS, keymapFile), "r") as fd:
						for line in fd.readlines():
							key, val = [x.strip() for x in line.split("=", 1)]
							if key == "kmap":
								mapFile = val
							if key == "name":
								mapName = val
				except (IOError, OSError) as err:
					print("[Keyboard] Error %d: Opening keymap file '%s'! (%s)" % (err.errno, filename, err.strerror))
				if mapFile is not None and mapName is not None:
					print("[Keyboard] Adding keymap '%s' ('%s')." % (mapName, mapFile))
					self.keyboardMaps.append((mapFile, mapName))

	def activateKeyboardMap(self, index):
		try:
			keymap = self.keyboardMaps[index]
			print("[Keyboard] Activating keymap: '%s'." % keymap[1])
			keymapPath = resolveFilename(SCOPE_KEYMAPS, keymap[0])
			if pathExists(keymapPath):
				Console().ePopen("loadkmap < %s" % keymapPath)
		except IndexError:
			print("[Keyboard] Error: Selected keymap does not exist!")

	def getKeyboardMaplist(self):
		return self.keyboardMaps

	def getDefaultKeyboardMap(self):
		# This is a code proposal to make the default keymap respond
		# to the currently defined locale.  OpenATV initialises the
		# keymap based on hardware manufacturer.  Making the
		# selection based on language locale makes more sense.  There
		# are other code changes coming that will allow this to happen.
		#
		# locale = language.getLocale()
		# if locale.startswith("de_") and "de.kmap" in self.keyboardMaps:
		# 	return "de.kmap"
		from boxbranding import getMachineBrand
		if getMachineBrand() in ("Zgemma", "Atto.TV"):
			return "us.kmap"
		elif getMachineBrand() == "Beyonwiz":
			return "eng.kmap"
		return "de.kmap"


keyboard = Keyboard()
