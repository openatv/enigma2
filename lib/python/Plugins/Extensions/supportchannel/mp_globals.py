#	-*-	coding:	utf-8	-*-

pluginPath = ""
activeIcon = ""
proxy = False
ddlme_sortOrder = 0
premium_hosters = '(putlocker|sockshare|bitshare|movshare|nowvideo|firedrive|streamclou)'

std_headers = {
	'User-Agent': 'Mozilla/5.0 (X11; U; Linux x86_64; en-US; rv:1.9.2.6) Gecko/20100627 Firefox/3.6.6',
	'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.7',
	'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
	'Accept-Language': 'en-us,en;q=0.5',
}

from simple_lru_cache import SimpleLRUCache
lruCache = SimpleLRUCache(50)