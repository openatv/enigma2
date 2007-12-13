from enigma import loadPNG

def LoadPixmap(path, desktop = None):
	ptr = loadPNG(path)
	if ptr and desktop:
		desktop.makeCompatiblePixmap(ptr)
	return ptr
