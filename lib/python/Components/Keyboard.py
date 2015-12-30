from Components.Console import Console
import os
import re
from enigma import eEnv

class Keyboard:
	def __init__(self):
		self.keyboardmaps = []
		self.kpath = eEnv.resolve('${datadir}/keymaps')
		eq = re.compile('^\s*(\w+)\s*=\s*(.*)\s*$')
		for keymapfile in os.listdir(self.kpath):
			if (keymapfile.endswith(".info")):
				mapfile = None
				mapname = None
				for line in open(os.path.join(self.kpath, keymapfile)):
					m = eq.match(line)
					if m:
						key, val = m.groups()
						if key == 'kmap':
						    mapfile = val
						if key == 'name':
						    mapname = val
						if (mapfile is not None) and (mapname is not None):
						    self.keyboardmaps.append((mapfile, mapname))

	def activateKeyboardMap(self, index):
		try:
			keymap = self.keyboardmaps[index]
			print "Activating keymap:",keymap[1]
			keymappath = os.path.join(self.kpath, keymap[0])
			if os.path.exists(keymappath):
				Console().ePopen(("loadkmap < " + str(keymappath)))
		except:
			print "Selected keymap does not exist!"

	def getKeyboardMaplist(self):
		return self.keyboardmaps

	def getDefaultKeyboardMap(self):
		return 'default.kmap'

keyboard = Keyboard()
