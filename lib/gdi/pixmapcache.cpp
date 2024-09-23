#include <lib/gdi/pixmapcache.h>

#include <algorithm>
#include <map>
#include <string>
#include <lib/base/elock.h>

uint PixmapCache::MaximumSize = 256;

// Cache objects work best when we manage the ref counting manually. ePtr brings memory protection violations on shutdown
// We track the filesize and modified date of the file. If either change, the item is considered stale is removedand must be reloaded
// We also track the last used time so the cache can remove least recently used items when it gets too full. Full is defined
// as a number of items, rather than memory used, so there's a potential for the cache to occupy too much memory if
// many large images are loaded with the cached flag set
struct CacheItem
{
public:
	CacheItem()
	{
	}

	CacheItem& operator=(const CacheItem& p)
	{
		pixmap = p.pixmap;
		filesize = p.filesize;
		modifiedDate = p.modifiedDate;
		lastUsed = p.lastUsed;
		return *this;
	}

	CacheItem(gPixmap* p, off_t s, time_t m)
	{
		pixmap = p;
		filesize = s;
		modifiedDate = m;
		lastUsed = ::time(0);
	};

	gPixmap* pixmap;
	off_t filesize;
	time_t modifiedDate;
	int lastUsed;
};

typedef std::map<std::string, CacheItem> NameToPixmap;

static bool CompareLastUsed(NameToPixmap::value_type i, NameToPixmap::value_type j) 
{ 
	return i.second.lastUsed < j.second.lastUsed;
}

static eSingleLock pixmapCacheLock;
static NameToPixmap pixmapCache;

/* The "dispose" method isn't very efficient, but not called unless
 * a pixmap is being replaced by another when the cache is full and even then,
 * not loading the same pixmap repeatedly will probably make up for that.
 * There is a race condition, when two threads load the same image,
 * the worst case scenario is then that the pixmap is loaded twice. This
 * isn't any worse than before, and all the UI pixmaps will be loaded
 * from the same thread anyway. */
void PixmapCache::PixmapDisposed(gPixmap* pixmap)
{
	eSingleLocker lock(pixmapCacheLock);

	for (NameToPixmap::iterator it = pixmapCache.begin();
		 it != pixmapCache.end();
		 ++it)
	{
		if (it->second.pixmap == pixmap)
		{
			pixmapCache.erase(it);
			break;
		}
	}
}

gPixmap* PixmapCache::Get(const char *filename)
{
	gPixmap* disposePixmap = NULL;
	{
		eSingleLocker lock(pixmapCacheLock);
		NameToPixmap::iterator it = pixmapCache.find(filename);
		if (it != pixmapCache.end())
		{
			// find out whether the image has been modified
			// if so, it'll need to be reloaded from disk
			struct stat img_stat = {};
			if (stat(filename, &img_stat) == 0 && img_stat.st_mtime == it->second.modifiedDate && img_stat.st_size == it->second.filesize)
			{
				// file still exists and hasn't been modified
				it->second.lastUsed = ::time(0);
				return it->second.pixmap;
			}
			else
			{
				// file no longer exists, has been modified or changed size, so remove from the cache
				pixmapCache.erase(it);
				disposePixmap = it->second.pixmap;
			}
		}
	}

	// Release might cause a callback into PixmapDisposed
	// Avoid the risk of a deadlock by doing the release outside the lock
	if (disposePixmap)
		disposePixmap->Release();

	return NULL;
}

void PixmapCache::Set(const char *filename, gPixmap* pixmap)
{
	gPixmap* disposePixmap = NULL;
	{
		eSingleLocker lock(pixmapCacheLock);
		struct stat img_stat = {};
		if (stat(filename, &img_stat) == 0)
		{
			NameToPixmap::iterator it = pixmapCache.find(filename);
			if (it != pixmapCache.end())
			{
				// need to release the pixmap being replaced after we've finished updating the cache
				disposePixmap = it->second.pixmap;
				
				// swap in the updated pixmap
				pixmap->AddRef();
				it->second.pixmap = pixmap;
				it->second.filesize = img_stat.st_size;
				it->second.modifiedDate = img_stat.st_mtime;
			}
			else
			{
				if (pixmapCache.size() > MaximumSize)
				{
					// find the least recently used
					NameToPixmap::iterator it = std::min_element(pixmapCache.begin(), pixmapCache.end(), &CompareLastUsed);
					if (it != pixmapCache.end())
					{
						pixmapCache.erase(it);
						// need to release the pixmap being removed after we've finished updating the cache
						disposePixmap = it->second.pixmap;
					}
				}

				pixmap->AddRef();
				NameToPixmap::value_type pr = std::make_pair(std::string(filename), CacheItem(pixmap, img_stat.st_size, img_stat.st_mtime));
				pixmapCache.insert(pr);
			}
		}
	}

	// Release might cause a callback into PixmapDisposed
	// Avoid the risk of a deadlock by doing the release outside the lock
	if (disposePixmap)
		disposePixmap->Release();
}
