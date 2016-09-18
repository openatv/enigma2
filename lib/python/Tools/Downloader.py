from boxbranding import getMachineBrand, getMachineName

from twisted.web import client
from twisted.internet import reactor, defer, ssl


class HTTPProgressDownloader(client.HTTPDownloader):
	def __init__(self, url, outfile, headers=None):
		client.HTTPDownloader.__init__(self, url, outfile, headers=headers, agent="Enigma2 HbbTV/1.1.1 (+PVR+RTSP+DL;OpenATV;;;)")
		self.status = None
		self.progress_callback = None
		self.deferred = defer.Deferred()

	def noPage(self, reason):
		if self.status == "304":
			print reason.getErrorMessage()
			client.HTTPDownloader.page(self, "")
		else:
			client.HTTPDownloader.noPage(self, reason)

	def gotHeaders(self, headers):
		if self.status == "200":
			if headers.has_key("content-length"):
				self.totalbytes = int(headers["content-length"][0])
			else:
				self.totalbytes = 0
			self.currentbytes = 0.0
		return client.HTTPDownloader.gotHeaders(self, headers)

	def pagePart(self, packet):
		if self.status == "200":
			self.currentbytes += len(packet)
		if self.totalbytes and self.progress_callback:
			self.progress_callback(self.currentbytes, self.totalbytes)
		return client.HTTPDownloader.pagePart(self, packet)

	def pageEnd(self):
		return client.HTTPDownloader.pageEnd(self)

class downloadWithProgress:
	def __init__(self, url, outputfile, contextFactory=None, *args, **kwargs):
		if hasattr(client, '_parse'):
			scheme, host, port, path = client._parse(url)
		else:
			# _URI class renamed to URI in 15.0.0
 			try:
 				from twisted.web.client import _URI as URI
 			except ImportError:
 				from twisted.web.client import URI
 			uri = URI.fromBytes(url)
			scheme = uri.scheme
			host = uri.host
			port = uri.port
			path = uri.path

		self.factory = HTTPProgressDownloader(url, outputfile, *args, **kwargs)
		if scheme == "https":
			self.connection = reactor.connectSSL(host, port, self.factory, ssl.ClientContextFactory())
		else:
			self.connection = reactor.connectTCP(host, port, self.factory)

	def start(self):
		return self.factory.deferred

	def stop(self):
		if self.connection:
			print "[stop]"
			self.connection.disconnect()

	def addProgress(self, progress_callback):
		print "[addProgress]"
		self.factory.progress_callback = progress_callback
