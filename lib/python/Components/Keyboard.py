from Components.Console import Console
from os import listdir as os_listdir, path as os_path
from re import compile as re_compile
from enigma import eEnv

class Keyboard:
	def __init__(self):
		self.keyboardmaps = []
		self.readKeyboardMapFiles()

	def readKeyboardMapFiles(self):
		for keymapfile in os_listdir(eEnv.resolve('${datadir}/keymaps/')):
			if (keymapfile.endswith(".info")):
				f = open(eEnv.resolve('${datadir}/keymaps/') + keymapfile)
				mapfile = None
				mapname = None
				for line in f:
					m = re_compile('^\s*(\w+)\s*=\s*(.*)\s*$').match(line)
					if m:
						key, val = m.groups()
						if key == 'kmap':
						    mapfile = val
						if key == 'name':
						    mapname = val
						if (mapfile is not None) and (mapname is not None):
						    self.keyboardmaps.append(( mapfile,mapname))
				f.close()

		if len(self.keyboardmaps) == 0:
			self.keyboardmaps = [('dream-de.kmap', 'Dreambox Keyboard Deutsch'), ('eng.kmap', 'Keyboard English')]

	def activateKeyboardMap(self, index):
		try:
			keymap = self.keyboardmaps[index]
			print "Activating keymap:",keymap[1]
			keymappath = eEnv.resolve('${datadir}/keymaps/') + keymap[0]
			if os_path.exists(keymappath):
				Console().ePopen(("loadkmap < " + str(keymappath)))
		except:
			print "Selected keymap does not exist!"

	def getKeyboardMaplist(self):
		return self.keyboardmaps

	def getDefaultKeyboardMap(self):
		return 'eng.kmap'

keyboard = Keyboard()
