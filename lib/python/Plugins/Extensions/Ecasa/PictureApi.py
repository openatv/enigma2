from __future__ import print_function

import os
import shutil

def list_recursive(dirname):
	for file in os.listdir(dirname):
		fn = os.path.join(dirname, file)
		if os.path.isfile(fn):
			yield fn
		elif os.path.isdir(fn):
			for f in list_recursive(fn):
				yield f

def remove_empty(dirname):
	files = os.listdir(dirname)
	if files:
		for file in os.listdir(dirname):
			fn = os.path.join(dirname, file)
			if os.path.isdir(fn):
				remove_empty(fn)
	else:
		try:
			os.rmdir(dirname)
		except OSError as ose:
			print("Unable to remove directory", dirname + ":", ose)

class PictureApi:
	"""Base class for browser APIs"""
	def __init__(self, cache='/tmp/ecasa'):
		self.cache = cache

	def setCredentials(self, email, password):
		pass

	def getAlbums(self, user='default'):
		pass

	def getSearch(self, query, limit='10'):
		pass

	def getAlbum(self, album):
		pass

	def getTags(self, feed):
		pass

	def getComments(self, feed):
		pass

	def getFeatured(self):
		pass

	def downloadPhoto(self, photo, thumbnail=False):
		pass

	def downloadThumbnail(self, photo):
		return self.downloadPhoto(photo, thumbnail=True)

	def copyPhoto(self, photo, target, recursive=True):
		"""Attempt to copy photo from cache to given destination.

		Arguments:
		photo: photo object to download.
		target: target filename
		recursive (optional): attempt to download picture if it does not exist yet

		Returns:
		True if image was copied successfully,
		False if image did not exist and download was initiated,
		otherwise None.

		Raises:
		shutil.Error if an error occured during moving the file.
		"""
		pass

	def cleanupCache(self, maxSize):
		"""Housekeeping for our download cache.

		Removes pictures and thumbnails (oldest to newest) until the cache is smaller than maxSize MB.

		Arguments:
		maxSize: maximum size of cache im MB.
		"""
		stat = os.stat
		maxSize *= 1048576 # input size is assumed to be in mb, but we work with bytes internally

		files = [(f, stat(f)) for f in list_recursive(self.cache)]
		curSize = sum(map(lambda x: x[1].st_size, files))
		if curSize > maxSize:
			files.sort(key=lambda x: x[1].st_mtime)
			while curSize > maxSize:
				file, stat = files.pop(0)
				try:
					os.unlink(file)
				except Exception as e:
					print("[PicasaApi] Unable to unlink file", file + ":", e)
				else:
					curSize -= stat.st_size
			remove_empty(self.cache)

__all__ = ['PictureApi']
