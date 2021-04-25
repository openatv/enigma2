from enigma import loadPNG, loadJPG, loadSVG

pixmap_cache = {}


def LoadPixmap(path, desktop=None, cached=False,  width=0, height=0):
	if path in pixmap_cache:
		return pixmap_cache[path]
	if path[-4:] == ".png":
		ptr = loadPNG(path)
	elif path[-4:] == ".jpg":
		ptr = loadJPG(path)
	elif path[-4:] == ".svg":
		from skin import getSkinFactor # imported here to avoid circular import
		# autoscale = int(parameters.get("AutoscaleSVG", -1)) # skin_default only == -1, disabled == 0 or enabled == 1
		autoscale = -1
		scale = height == 0 and (autoscale == -1 and "/skin_default/" in path or autoscale == 1) and getSkinFactor() or 0
		ptr = loadSVG(path, 0, width, height, scale)
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
