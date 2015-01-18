from twisted.internet import reactor, defer
from twisted.internet.protocol import Protocol, ClientCreator
from twisted.protocols.ftp import FTPClient, FTPFileListProtocol
from os import SEEK_END

class FTPDownloader(Protocol):
	def __init__(self, host, port, path, fileOrName, username = 'root', \
		password = '', passive = True, supportPartial = False, \
		*args, **kwargs):
		timeout = 30
		self.path = path
		self.resume = supportPartial
		if isinstance(fileOrName, str):
			self.filename = fileOrName
			self.file = None
		else:
			self.file = fileOrName
		creator = ClientCreator(reactor, FTPClient, username, password, passive = passive)
		creator.connectTCP(host, port, timeout).addCallback(self.controlConnectionMade).addErrback(self.connectionFailed)
		self.deferred = defer.Deferred()

	def controlConnectionMade(self, ftpclient):
		self.ftpclient = ftpclient
		self.ftpFetchSize()

	def sizeRcvd(self, msgs):
		code, msg = msgs[0].split()
		if code == '213':
			self.totallength = int(msg)
			self.ftpFetchFile()
		else:
			self.ftpFetchList()

	def ftpFetchSize(self):
		d = self.ftpclient.queueStringCommand('SIZE ' + self.path)
		d.addCallback(self.sizeRcvd).addErrback(self.ftpFetchList)

	def listRcvd(self, *args):
		if not len(self.filelist.files):
			self.connectionFailed()
			return
		self.totallength = self.filelist.files[0]['size']
		self.filelist = None
		self.ftpFetchFile()

	def ftpFetchList(self, *args, **kwargs):
		self.filelist = FTPFileListProtocol()
		d = self.ftpclient.list(self.path, self.filelist)
		d.addCallback(self.listRcvd).addErrback(self.connectionFailed)

	def openFile(self):
		if self.resume:
			file = open(self.filename, 'ab')
		else:
			file = open(self.filename, 'wb')
		return (file, file.tell())

	def ftpFetchFile(self):
		offset = 0
		if self.file is None:
			try:
				self.file, offset = self.openFile()
			except IOError, ie:
				self.connectionFailed()
				return
		offset = self.resume and offset or 0
		d = self.ftpclient.retrieveFile(self.path, self, offset = offset)
		d.addCallback(self.ftpFinish).addErrback(self.connectionFailed)

	def dataReceived(self, data):
		if not self.file:
			return
		try:
			self.file.seek(0, SEEK_END)

			self.file.write(data)
		except IOError, ie:
			self.connectionFailed()

	def ftpFinish(self, code = 0, message = None):
		self.ftpclient.quit()
		if self.file is not None:
			self.file.close()
		self.deferred.callback(code)

	def connectionFailed(self, reason = None):
		if self.file is not None:
			self.file.close()
		self.deferred.errback(reason)

