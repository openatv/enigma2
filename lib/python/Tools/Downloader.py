from os import unlink

from time import time

from twisted.internet import reactor
from twisted.internet.protocol import Protocol
from twisted.internet.threads import deferToThread
from twisted.web.client import Agent, RedirectAgent, BrowserLikePolicyForHTTPS, ResponseDone, ResponseFailed, PotentialDataLoss
from twisted.web.http_headers import Headers


# ------------------------------------------------------------
# USER_AGENTS
# ------------------------------------------------------------
class USER_AGENTS:
	FIREFOX = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:138.0) Gecko/20100101 Firefox/138.0"
	CHROME = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36"
	HBBTV = "HbbTV/1.1.1 (+PVR+RTSP+DL; Sonic; TV44; 1.32.455; 2.002) Bee/3.5"


# ------------------------------------------------------------
# SHARED HELPERS
# ------------------------------------------------------------
# NOTE: no Connection header here - Twisted's HTTP11ClientProtocol manages
# connection persistence itself. Accept-Encoding stays "identity" so the
# response length matches the bytes written to disk.
HTTP_DEFAULT_HEADERS = {
	"User-Agent": USER_AGENTS.CHROME,
	"Accept": "*/*",
	"Accept-Encoding": "identity",
}

# Disk writes run in the reactor's thread pool, not on the reactor thread, so a
# slow USB stick or network mount cannot stall the GUI. These control how much
# is queued before a write is handed off and before the socket is throttled.
WRITE_FLUSH_SIZE = 256 * 1024  # hand the buffer to the writer thread from here on
WRITE_PAUSE_SIZE = 4 * 1024 * 1024  # stop reading the socket while the writer lags this far behind
STALL_CHECK_INTERVAL = 5  # how often the stall watchdog looks at the clock


def makeAgent(connectTimeout=5):
	base = Agent(reactor, contextFactory=BrowserLikePolicyForHTTPS(), connectTimeout=connectTimeout)
	return RedirectAgent(base)


def normaliseHeaders(headers):
	""" normalise to str """
	return {
		k.decode("utf-8") if isinstance(k, bytes) else str(k):
		v.decode("utf-8") if isinstance(v, bytes) else str(v)
		for k, v in (headers or {}).items()
	}


def buildHeaders(headers=None):
	return Headers({
		k.encode("utf-8"): [v.encode("utf-8")]
		for k, v in {**HTTP_DEFAULT_HEADERS, **(headers or {})}.items()
	})


def formatError(error):
	""" errorCallback gets a plain str, so whatever went wrong has to be reduced
		to one readable line here. A raw Twisted Failure is unusable in a
		MessageBox: a mid-transfer abort stringifies to the repr of its reason
		list, e.g. "[<Failure ConnectionDone...>, <Failure _DataLoss: >]". """
	if hasattr(error, "check"):  # twisted Failure
		if error.check(ResponseFailed):
			return "Connection lost during transfer"
		return error.getErrorMessage() or error.type.__name__
	return str(error) or error.__class__.__name__


# ------------------------------------------------------------
# STREAM PROTOCOLS (no UI logic)
# ------------------------------------------------------------
class DiscardProtocol(Protocol):
	""" Twisted only releases a connection once its response body has been
		delivered somewhere. Responses we do not want (HTTP != 2xx, or a local
		file we failed to open) still have to be drained, else the socket stays
		registered with the reactor for the lifetime of the process. """

	def dataReceived(self, data):
		pass

	def connectionLost(self, reason):
		pass


class DownloadProtocol(Protocol):
	def __init__(self, downloader):
		self.downloader = downloader
		self.recv = 0

	def dataReceived(self, data):
		if self.downloader.done:
			return

		self.recv += len(data)
		self.downloader.progress = self.recv
		self.downloader.pendingProgress = (
			self.recv,
			self.downloader.totalSize
		)

		self.downloader.queueData(data)
		self.downloader.scheduleUi()

	def connectionLost(self, reason):
		if self.downloader.done:
			return

		if reason.check(ResponseDone, PotentialDataLoss):
			# PotentialDataLoss: connection closed to signal end of body for a
			# response with no reliable length (e.g. no Content-Length, HTTP/1.0).
			# Twisted can't tell that apart from a truncated transfer, but since
			# it's the only way to end such a response, treat it as complete.
			self.downloader.bodyFinished()
		else:
			self.downloader.finalise(error=reason)


# ------------------------------------------------------------
# DOWNLOADER
# ------------------------------------------------------------
class DownloadWithProgress:

	def __init__(self, url, outputFile, **kwargs):
		""" url and outputFile should be str type """
		self.url = url
		self.outputFile = outputFile

		self.progress = 0
		self.totalSize = -1  # means size not set

		self.progressCallback = None
		self.endCallback = None
		self.errorCallback = None

		self.protocol = None
		self.fd = None
		self.fileCreated = False  # only a file we opened ourselves may be removed again
		self.done = False

		self.pendingProgress = None
		self.uiScheduled = False
		self.uiTimer = None
		self.request = None

		# writer state, see queueData()/flushBuffer()
		self.buffer = bytearray()
		self.writeInFlight = False
		self.paused = False
		self.finishPending = False
		self.pendingCleanup = None

		# for speed/eta functions
		self.startTime = None

		# headers (stored as strings internally)
		self.rawHeaders = normaliseHeaders(kwargs.get("headers", {}))
		userAgent = kwargs.get("userAgent")
		if userAgent:
			self.rawHeaders.setdefault("User-Agent", normaliseHeaders({"User-Agent": userAgent})["User-Agent"])

		# TCP connect timeout, enforced by the Agent itself
		self.connectTimeout = int(kwargs.get("connectTimeout", 5))

		# time allowed until the response headers arrive. This is a separate
		# budget from the connect timeout above: a reachable but busy mirror may
		# take a while to start answering, and killing it after connectTimeout
		# would abort perfectly good downloads.
		self.responseTimeout = int(kwargs.get("responseTimeout", 30))
		self.responseTimer = None

		# a mirror that accepts the connection, answers, and then goes quiet mid
		# transfer is not covered by either timeout above - without this the
		# download would sit there forever with no error and no progress.
		self.stallTimeout = int(kwargs.get("stallTimeout", 60))
		self.stallTimer = None
		self.lastData = None

		self.agent = makeAgent(self.connectTimeout)

	def start(self):
		self.progress = 0
		self.totalSize = -1
		self.startTime = time()

		# No HEAD probe: it would need its own connection and TLS handshake, so
		# its answer does not arrive meaningfully earlier than the GET response
		# headers that response.length is read from anyway.
		self.startGet()
		return self

	# --------------------------------------------------------
	# GET REQUEST
	# --------------------------------------------------------
	def startGet(self):
		try:
			headers = buildHeaders(headers=self.rawHeaders)  # userAgent is already passed by headers

			self.request = self.agent.request(
				b"GET",
				self.url.encode("utf-8"),
				headers,
				None
			)

			self.request.addCallbacks(self.responseReceived, self.requestFailed)

			# RESPONSE HEADER WATCHDOG (the connect phase is the Agent's job)
			if self.responseTimeout:
				self.responseTimer = reactor.callLater(self.responseTimeout, self.onResponseTimeout)

		except Exception as err:
			self.finalise(error=err)

	# --------------------------------------------------------
	# RESPONSE
	# --------------------------------------------------------
	def responseReceived(self, response):
		self.cancelResponseTimeout()

		if self.done:
			response.deliverBody(DiscardProtocol())
			return

		# STRICT HTTP GATE
		if not (200 <= response.code < 300):  # if not 2XX code means request failed
			response.deliverBody(DiscardProtocol())
			self.finalise(error=Exception(f"HTTP {response.code}"))
			return

		# content-length hint from server
		# NOTE: response.headers never carries Content-Length; Twisted's HTTP/1.1
		# client consumes it internally for framing and exposes it as response.length.
		if isinstance(response.length, int) and response.length > 0:
			self.totalSize = response.length

		try:  # catch any exception while trying to create the local file
			self.fd = open(self.outputFile, "wb")
			self.fileCreated = True
		except Exception as err:
			response.deliverBody(DiscardProtocol())
			self.finalise(error=err)
			return

		self.protocol = DownloadProtocol(self)
		self.startStallTimeout()

		response.deliverBody(self.protocol)

	# --------------------------------------------------------
	# DISK WRITER (off the reactor thread)
	# --------------------------------------------------------
	def queueData(self, data):
		self.buffer += data

		if len(self.buffer) >= WRITE_FLUSH_SIZE:
			self.flushBuffer()

		# backpressure: the socket is faster than the storage, so stop reading
		# until the writer has caught up, otherwise the buffer grows unbounded.
		if not self.paused and len(self.buffer) >= WRITE_PAUSE_SIZE:
			transport = getattr(self.protocol, "transport", None)
			if transport:
				try:
					transport.pauseProducing()
					self.paused = True
				except Exception:
					pass

	def flushBuffer(self):
		if self.writeInFlight or not self.buffer or not self.fd:
			return

		chunk = bytes(self.buffer)
		del self.buffer[:]
		self.writeInFlight = True
		deferToThread(self.fd.write, chunk).addCallbacks(self.writeDone, self.writeFailed)

	def writeDone(self, result):
		self.writeInFlight = False
		self.lastData = time()  # a slow disk is not a stalled transfer

		if self.pendingCleanup is not None:  # teardown was waiting for this write to return
			remove, self.pendingCleanup = self.pendingCleanup, None
			self.cleanupFile(remove)
			return

		if self.done:
			return

		if self.buffer:
			self.flushBuffer()
			return

		if self.paused:
			transport = getattr(self.protocol, "transport", None)
			if transport:
				try:
					transport.resumeProducing()
				except Exception:
					pass
			self.paused = False

		if self.finishPending:
			self.completeBody()

	def writeFailed(self, failure):
		self.writeInFlight = False

		if self.pendingCleanup is not None:
			remove, self.pendingCleanup = self.pendingCleanup, None
			self.cleanupFile(remove)
			return

		self.finalise(error=failure)

	def cleanupFile(self, remove):
		# Never close the file while the writer thread is inside write(); the
		# close is repeated from writeDone()/writeFailed() instead.
		if self.writeInFlight:
			self.pendingCleanup = remove
			return

		fd, self.fd = self.fd, None
		if fd:
			try:
				fd.close()
			except Exception:
				pass

		# remove partial file, but only when this download created it. Errors
		# raised before the file was opened (HTTP != 2xx, connect timeout, DNS)
		# must not delete an existing file of the same name left by an earlier,
		# successful download.
		if remove and self.fileCreated:
			try:
				unlink(self.outputFile)
			except OSError:
				pass

	# --------------------------------------------------------
	# BODY COMPLETION
	# --------------------------------------------------------
	def bodyFinished(self):
		self.finishPending = True
		self.cancelStallTimeout()

		if self.writeInFlight or self.buffer:
			self.flushBuffer()  # completeBody() runs from writeDone() once the tail is on disk
			return

		self.completeBody()

	def completeBody(self):
		self.finishPending = False

		# With a Content-Length present Twisted reports a truncated transfer as a
		# failure, but a response without one ends in PotentialDataLoss either way.
		# Checking the byte count keeps a short read from being flashed as a
		# complete image.
		if self.totalSize > 0 and self.progress != self.totalSize:
			self.finalise(error=Exception(f"Incomplete download, got {self.progress} of {self.totalSize} bytes"))
			return

		self.finalise(success=True)

	# --------------------------------------------------------
	# RESPONSE TIMEOUT HANDLING
	# --------------------------------------------------------
	def cancelResponseTimeout(self):
		if self.responseTimer and self.responseTimer.active():
			self.responseTimer.cancel()
		self.responseTimer = None

	def onResponseTimeout(self):
		if self.done:
			return

		self.responseTimer = None

		# finalise() itself cancels self.request (step 1 below); doing it here first
		# would fire requestFailed's own CancelledError finalise() call before this
		# one, burying our "Response timeout" message behind the done-guard.
		self.finalise(error=Exception("Response timeout"))

	# --------------------------------------------------------
	# STALL TIMEOUT HANDLING
	# --------------------------------------------------------
	def startStallTimeout(self):
		if not self.stallTimeout:
			return

		self.lastData = time()
		self.stallTimer = reactor.callLater(STALL_CHECK_INTERVAL, self.onStallCheck)

	def cancelStallTimeout(self):
		if self.stallTimer and self.stallTimer.active():
			self.stallTimer.cancel()
		self.stallTimer = None

	def onStallCheck(self):
		self.stallTimer = None

		if self.done:
			return

		if self.lastData and (time() - self.lastData) > self.stallTimeout:
			self.finalise(error=Exception("Transfer stalled"))
			return

		self.stallTimer = reactor.callLater(STALL_CHECK_INTERVAL, self.onStallCheck)

	# --------------------------------------------------------
	# UI FLUSH
	# --------------------------------------------------------
	def scheduleUi(self):
		self.lastData = time()

		if not self.uiScheduled:
			self.uiScheduled = True
			self.uiTimer = reactor.callLater(0.2, self.flushUi)

	def cancelUi(self):
		if self.uiTimer and self.uiTimer.active():
			self.uiTimer.cancel()
		self.uiTimer = None
		self.uiScheduled = False

	def flushUi(self):
		self.uiTimer = None
		self.uiScheduled = False

		if self.done:
			return

		if self.pendingProgress and callable(self.progressCallback):
			progress, total = self.pendingProgress

			if total <= 0:
				total = -1

			self.progressCallback(progress, total)

	# --------------------------------------------------------
	# ERROR HANDLING
	# --------------------------------------------------------
	def requestFailed(self, failure):
		self.cancelResponseTimeout()

		if self.done:
			return

		self.finalise(error=failure)

	# --------------------------------------------------------
	# CONTROL
	# --------------------------------------------------------
	def stop(self):
		self.finalise()

	# --------------------------------------------------------
	# SINGLE EXIT POINT
	# --------------------------------------------------------
	def finalise(self, success=False, error=None):

		# Finalise download lifecycle exactly once.
		# Cleans up network/file resources and dispatches final callbacks.
		# if success=False and error=None means cancelled by stop()

		self.cancelResponseTimeout()
		self.cancelStallTimeout()

		if self.done:
			return

		self.done = True
		self.cancelUi()

		# 1. stop network
		if self.request:
			try:
				# cancel request before response body starts
				self.request.cancel()
			except Exception:
				pass

		if self.protocol and (transport := getattr(self.protocol, "transport", None)):
			try:
				# abort active response body stream
				transport.stopProducing()
			except Exception:
				pass
			self.paused = False

		# 2. close file descriptor and drop the partial file on anything but success
		if not success:
			del self.buffer[:]  # whatever is still queued is not going to disk
		self.cleanupFile(not success)

		# 3. flush a last pending progress update so fast/small downloads (which can
		# finish before the throttled 0.2s flushUi() timer ever fires) still report
		# their final progress instead of jumping straight from 0% to done.
		if success and self.pendingProgress and callable(self.progressCallback):
			progress, total = self.pendingProgress
			if total <= 0:
				total = -1
			self.progressCallback(progress, total)

		# 4. callbacks ( no callback on cancelled (i.e. forced stop()) )
		if success:
			if callable(self.endCallback):
				self.endCallback(self.outputFile)

		elif error and callable(self.errorCallback):
			self.errorCallback(formatError(error))

	# --------------------------------------------------------
	# CALLBACKS
	# --------------------------------------------------------
	def addProgress(self, progressCallback):
		""" progressCallback(bytesReceived, totalSize) - totalSize is -1 while the
			total is unknown (no Content-Length, e.g. a chunked response), so
			callers must guard before dividing by it. """
		self.progressCallback = progressCallback
		return self

	def addEnd(self, endCallback):
		self.endCallback = endCallback
		return self

	def addError(self, errorCallback):
		""" errorCallback(message) - message is always a str, never an exception
			object, so callers must not expect attributes like OSError.strerror. """
		self.errorCallback = errorCallback
		return self

	def setAgent(self, userAgent):
		self.rawHeaders["User-Agent"] = normaliseHeaders({"User-Agent": userAgent})["User-Agent"]
		return self

	def addErrback(self, errorCallback):  # Temporary support for deprecated callbacks.
		print("[Downloader] Warning: DownloadWithProgress 'addErrback' is deprecated use 'addError' instead!")
		return self.addError(errorCallback)

	def addCallback(self, endCallback):  # Temporary support for deprecated callbacks.
		print("[Downloader] Warning: DownloadWithProgress 'addCallback' is deprecated use 'addEnd' instead!")
		return self.addEnd(endCallback)

	# --------------------------------------------------------
	# SPEED / ETA, for use by newer UI
	# --------------------------------------------------------
	def getSpeed(self):
		"""
		Returns current average download speed in bytes/sec.
		Returns 0 if not enough information is available.
		"""
		if not self.startTime:
			return 0

		elapsed = time() - self.startTime

		if elapsed <= 0:
			return 0

		return float(self.progress) / elapsed

	def getEta(self):
		"""
		Returns estimated seconds remaining.
		Returns -1 if total size is unknown.
		"""
		if self.totalSize <= 0:
			return -1

		speed = self.getSpeed()

		if speed <= 0:
			return -1

		remaining = self.totalSize - self.progress

		if remaining <= 0:
			return 0

		return int(remaining / speed)


# ------------------------------------------------------------
# COMPATIBILITY,
# Class names should start with a Capital letter, this
# catches old code until that code can be updated.
# ------------------------------------------------------------
class downloadWithProgress(DownloadWithProgress):
	pass
