from enigma import loadPNG, loadJPG

pixmap_cache = {}

def LoadPixmap(path, desktop = None, cached = False):
	if path in pixmap_cache:
		return pixmap_cache[path]
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
	if cached:
		pixmap_cache[path] = ptr
	return ptr
