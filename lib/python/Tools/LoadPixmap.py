from enigma import loadPNG, loadJPG
from Tools.LRUCache import lru_cache

def LoadPixmap(path, desktop=None, cached=None):
	if cached is None or cached:
		ret = _cached_load(path, desktop)
		return ret
	else:
		return _load(path, desktop)

@lru_cache(maxsize=256)
def _cached_load(path, desktop):
	return _load(path, desktop)

def _load(path, desktop):
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
