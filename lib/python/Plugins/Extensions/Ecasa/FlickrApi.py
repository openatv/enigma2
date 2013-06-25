from __future__ import print_function

#pragma mark - Flickr API

import flickrapi
import os
import shutil
import types

from twisted.internet import reactor
from twisted.internet.defer import Deferred
from twisted.web.client import downloadPage

our_print = lambda *args, **kwargs: print("[FlickrApi]", *args, **kwargs)

class FakeExif:
	def __init__(self):
		pass
	def __getattr__(self, attr):
		if attr == 'make':
			return None
		elif attr == 'model':
			return None

class FakeNode:
	def __init__(self, value):
		self.text = value

class Picture:
	"""A picture from Flickr. Makes API compatible with the one from gdata as straight-forward as possible."""
	def __init__(self, obj, owner=None):
		self.__obj = obj
		self.__owner = owner
	@property
	def obj(self):
		return self.__obj
	def __getattr__(self, attr):
		if attr == 'title':
			return FakeNode(self.__obj.get('title'))
		elif attr == 'exif':
			return FakeExif()
		elif attr == 'summary':
			return self.__obj.find('description')
		elif attr == 'width':
			obj = self.__obj
			return obj.get('width_l') or obj.get('width_o') or obj.get('width_m') or obj.get('width_s')
		elif attr == 'height':
			obj = self.__obj
			return obj.get('height_l') or obj.get('height_o') or obj.get('height_m') or obj.get('height_s')
		elif attr == 'media' or attr == 'content':
			return self
		elif attr == 'author':
			if self.owner:
				return self
		elif attr == 'url':
			obj = self.__obj
			return obj.get('url_l') or obj.get('url_o') or obj.get('url_m') or obj.get('url_s')
		elif attr == 'name':
			obj = self.__obj
			return FakeNode(obj.get('ownername') or self.__owner or obj.get('owner'))
		elif attr == 'email':
			return FakeNode(self.__owner or self.__obj.get('owner'))
		elif attr == 'owner':
			return self.__owner or self.__obj.get('owner')
		elif attr.startswith('_'):
			raise AttributeError("No such attribute '%s'" % (attr,))
		return self.__obj.get(attr)
	def __getitem__(self, idx):
		if idx != 0:
			raise IndexError("no such index")
		return self
	def __repr__(self):
		return '<Ecasa.FlickrApi.Picture: %s>' % (self.title.text,)
	__str__ = __repr__
#	def dump(self):
#		from xml.etree.cElementTree import dump
#		dump(self.__obj)

class PictureGenerator:
	def __init__(self, fset, owner=None):
		self.__list = fset
		self.__owner = owner
	def __getitem__(self, idx):
		return Picture(self.__list[idx], owner=self.__owner)
	def __iter__(self):
		self.idx = 0
		self.len = len(self)-1
		return self
	def next(self):
		idx = self.idx
		if idx > self.len:
			raise StopIteration
		self.idx = idx+1
		return self[idx]
	__next__ = next
	def __len__(self):
		return len(self.__list)
	def index(self, obj):
		return self.__list.index(obj.obj)

from PictureApi import PictureApi
class FlickrApi(PictureApi):
	"""Wrapper around flickr API to make our life a little easier."""
	def __init__(self, api_key=None, cache='/tmp/ecasa'):
		"""Initialize API, login to flickr servers"""
		PictureApi.__init__(self, cache=cache)
		self.flickr_api = flickrapi.FlickrAPI(api_key)

	def setCredentials(self, email, password):
		pass

	def getAlbums(self, user='default'):
		flickr_api = self.flickr_api
		if user == 'default': user = ''
		elif '@' not in user:
			users = flickr_api.people_findByUsername(username=user)
			try: user = users.find('user').get('nsid')
			except Exception as e: our_print("getAlbums failed to retrieve nsid:", e)
		albums = flickr_api.photosets_getList(user_id=user, per_page='90', total='90')

		albums = [(album.find('title').text.encode('utf-8'), album.get('photos'), album) for album in albums.find('photosets').findall('photoset')]
		albums.insert(0, (_("All Photos"), '?', user))
		return albums

	def getSearch(self, query, limit='10'):
		photos = self.flickr_api.photos_search(text=query, per_page=str(limit), total=str(limit), extras='url_l,url_o,url_m,url_s,url_t,description,owner_name', media='photos')
		return PictureGenerator(photos.find('photos').findall('photo'))

	def getAlbum(self, album):
		# workaround to allow displaying the photostream without changes to the gui. we use it as a virtual album (or 'set' in flickr) and use the nsid as album object
		if isinstance(album, types.StringType):
			photos = self.flickr_api.people_getPublicPhotos(user_id=album, per_page='500', total='500', extras='url_l,url_o,url_m,url_s,url_t,description')
			pset = photos.find('photos')
		else:
			numphotos = album.get('photos')
			photos = self.flickr_api.photosets_getPhotos(photoset_id=album.get('id'), per_page=numphotos, total=numphotos, extras='url_l,url_o,url_m,url_s,url_t,description', media='photos')
			pset = photos.find('photoset')
		return PictureGenerator(pset.findall('photo'), owner=pset.get('owner'))

	def getTags(self, feed):
		pass

	def getComments(self, feed):
		pass

	def getFeatured(self):
		# XXX: limit to 6 pages for now
		photos = self.flickr_api.interestingness_getList(per_page='90', total='90', extras='url_l,url_o,url_m,url_s,url_t,description,owner_name')
		return PictureGenerator(photos.find('photos').findall('photo'))

	def downloadPhoto(self, photo, thumbnail=False):
		if not photo: return

		cache = os.path.join(self.cache, 'thumb', photo.owner) if thumbnail else os.path.join(self.cache, photo.owner)
		try: os.makedirs(cache)
		except OSError: pass

		url = photo.url_t if thumbnail else photo.url
		print(url)
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
		if not photo: return

		cache = os.path.join(self.cache, photo.owner)
		filename = photo.url.split('/')[-1]
		fullname = os.path.join(cache, filename)

		# file exists, assume it's valid...
		if os.path.exists(fullname):
			shutil.copy(fullname, target)
			return True
		else:
			print("[FlickrApi] Photo does not exist in cache, trying to download with deferred copy operation")
			self.downloadPhoto(photo).addCallback(
				lambda value:self.copyPhoto(photo, target, recursive=False)
			)
			return False

__all__ = ['FlickrApi']
