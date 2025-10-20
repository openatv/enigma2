from enigma import loadPNG, loadJPG, loadSVG, loadGIF, loadWEBP, detectImageType, RT_HALIGN_CENTER


# If cached is not supplied, LoadPixmap defaults to caching PNGs and not caching JPGs
# Split alpha channel JPGs are never cached as the C++ layer's caching is based on
# a single file per image in the cache
def LoadPixmap(path, desktop=None, cached=None, width=0, height=0, scaletoFit=0, align=RT_HALIGN_CENTER, autoDetect=False):
	extension = path[-4:]
	if autoDetect:
		detection = {
			0: ".png",
			1: ".jpg",
			3: ".gif",
			4: ".svg",
			5: ".webp",
		}
		extension = detection.get(detectImageType(path), extension)

	if extension == ".png":
		# cache unless caller explicity requests to not cache
		ptr = loadPNG(path, 0, 0 if cached is False else 1)
	elif extension == ".jpg":
		# don't cache unless caller explicity requests caching
		ptr = loadJPG(path, 1 if cached is True else 0)
	elif extension == ".gif":
		# don't cache unless caller explicity requests caching
		ptr = loadGIF(path, 1 if cached is True else 0)
	elif extension == ".webp":
		# don't cache unless caller explicity requests caching
		ptr = loadWEBP(path, 1 if cached is True else 0)
	elif extension == ".svg":
		from skin import parameters, getSkinFactor  # imported here to avoid circular import
		autoscale = int(parameters.get("AutoscaleSVG", -1))  # skin_default only == -1, disabled == 0 or enabled == 1
		scale = height == 0 and (autoscale == -1 and "/skin_default/" in path or autoscale == 1) and getSkinFactor() or 0
		ptr = loadSVG(path, 0 if cached is False else 1, width, height, scale, scaletoFit, align)
	elif path[-1:] == ".":
		# caching mechanism isn't suitable for multi file images, so it's explicitly disabled
		alpha = loadPNG(path + "a.png", 0, 0)
		ptr = loadJPG(path + "rgb.jpg", alpha, 0)
	else:
		raise Exception("Neither .png nor .jpg nor .svg, please fix file extension")
	if ptr and desktop:
		desktop.makeCompatiblePixmap(ptr)
	return ptr
