from __future__ import print_function

#pragma mark - Picasa API

import gdata.photos.service
import gdata.media
import gdata.geo
import os
import shutil

from twisted.internet import reactor
from twisted.internet.defer import Deferred
from twisted.web.client import downloadPage

#_PicasaApi__returnPhotos = lambda photos: [(photo.title.text, photo) for photo in photos.entry]
_PicasaApi__returnPhotos = lambda photos: photos.entry

from PictureApi import PictureApi
class PicasaApi(PictureApi):
	"""Wrapper around gdata/picasa API to make our life a little easier."""
	def __init__(self, email=None, password=None, cache='/tmp/ecasa'):
		"""Initialize API, login to google servers"""
		PictureApi.__init__(self, cache=cache)
		gd_client = gdata.photos.service.PhotosService()
		gd_client.source = 'enigma2-plugin-extensions-ecasa'
		if email and password:
			gd_client.email = email
			gd_client.password = password
			# NOTE: this might fail
			gd_client.ProgrammaticLogin()

		self.gd_client = gd_client

	def setCredentials(self, email, password):
		# TODO: check if this is sane
		gd_client = self.gd_client
		gd_client.email = email
		gd_client.password = password
		if email and password:
			# NOTE: this might fail
			gd_client.ProgrammaticLogin()

	def getAlbums(self, user='default'):
		albums = self.gd_client.GetUserFeed(user=user)
		return [(album.title.text, album.numphotos.text, album) for album in albums.entry]

	def getSearch(self, query, limit='10'):
		photos = self.gd_client.SearchCommunityPhotos(query, limit=str(limit))
		return __returnPhotos(photos)

	def getAlbum(self, album):
		photos = self.gd_client.GetFeed(album.GetPhotosUri())
		return __returnPhotos(photos)

	def getTags(self, feed):
		tags = self.gd_client.GetFeed(feed.GetTagsUri())
		return [(tag.summary.text, tag) for tag in tags.entry]

	def getComments(self, feed):
		comments = self.gd_client.GetCommentFeed(feed.GetCommentsUri())
		return [(comment.summary.text, comment) for comment in comments.entry]

	def getFeatured(self):
		featured = self.gd_client.GetFeed('/data/feed/base/featured')
		return __returnPhotos(featured)

	def downloadPhoto(self, photo, thumbnail=False):
		if not photo: return

		cache = os.path.join(self.cache, 'thumb', photo.albumid.text) if thumbnail else os.path.join(self.cache, photo.albumid.text)
		try: os.makedirs(cache)
		except OSError: pass

		url = photo.media.thumbnail[0].url if thumbnail else photo.media.content[0].url
		filename = url.split('/')[-1]
		fullname = os.path.join(cache, filename)
		d = Deferred()
		# file exists, assume it's valid...
		if os.path.exists(fullname):
			reactor.callLater(0, d.callback, (fullname, photo))
		else:
			downloadPage(url, fullname).addCallbacks(
				lambda value:d.callback((fullname, photo)),
				lambda error:d.errback((error, photo)))
		return d

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
		if not photo: return

		cache = os.path.join(self.cache, photo.albumid.text)
		filename = photo.media.content[0].url.split('/')[-1]
		fullname = os.path.join(cache, filename)

		# file exists, assume it's valid...
		if os.path.exists(fullname):
			shutil.copy(fullname, target)
			return True
		else:
			print("[PicasaApi] Photo does not exist in cache, trying to download with deferred copy operation")
			self.downloadPhoto(photo).addCallback(
				lambda value:self.copyPhoto(photo, target, recursive=False)
			)
			return False

__all__ = ['PicasaApi']
