from enigma import loadPNG, loadJPG

def LoadPixmap(path, desktop = None, cached = False):
	if path[-4:] == ".png":
		ptr = loadPNG(path)
	elif path[-4:] == ".jpg":
		ptr = loadJPG(path)
	elif path[-1:] == ".":
		alpha = loadPNG(path + "a.png")
		ptr = loadJPG(path + "rgb.jpg", alpha)
	else:
		raise Exception("neither .png nor .jpg, please fix file extension")
	if ptr and desktop:
		desktop.makeCompatiblePixmap(ptr)
	return ptr
