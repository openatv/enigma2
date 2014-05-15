# 2013.05.22 08:34:50 UTC
#Embedded file name: /usr/lib/enigma2/python/Plugins/Extensions/IniAirPlayer/rtsp.py
"""
RTSP - Real Time Streaming Protocol.

See RFC 2326, and its Robin, RFC 2068.
"""
import sys
import re
import types
from twisted.web import http
from twisted.web import server, resource
from twisted.internet import defer
from twisted.python import log, failure, reflect
try:
    from twisted.protocols._c_urlarg import unquote
except ImportError:
    from urllib import unquote

__version__ = '$Rev$'
SERVER_PROTOCOL = 'RTSP/1.0'
SERVER_STRING = 'AirPlayer RTP'
CONTINUE = 100
OK = 200
CREATED = 201
LOW_STORAGE = 250
MULTIPLE_CHOICE = 300
MOVED_PERMANENTLY = 301
MOVED_TEMPORARILY = 302
SEE_OTHER = 303
NOT_MODIFIED = 304
USE_PROXY = 305
BAD_REQUEST = 400
UNAUTHORIZED = 401
PAYMENT_REQUIRED = 402
FORBIDDEN = 403
NOT_FOUND = 404
NOT_ALLOWED = 405
NOT_ACCEPTABLE = 406
PROXY_AUTH_REQUIRED = 407
REQUEST_TIMEOUT = 408
GONE = 410
LENGTH_REQUIRED = 411
PRECONDITION_FAILED = 412
REQUEST_ENTITY_TOO_LARGE = 413
REQUEST_URI_TOO_LONG = 414
UNSUPPORTED_MEDIA_TYPE = 415
PARAMETER_NOT_UNDERSTOOD = 451
CONFERENCE_NOT_FOUND = 452
NOT_ENOUGH_BANDWIDTH = 453
SESSION_NOT_FOUND = 454
METHOD_INVALID_STATE = 455
HEADER_FIELD_INVALID = 456
INVALID_RANGE = 457
PARAMETER_READ_ONLY = 458
AGGREGATE_NOT_ALLOWED = 459
AGGREGATE_ONLY_ALLOWED = 460
UNSUPPORTED_TRANSPORT = 461
DESTINATION_UNREACHABLE = 462
INTERNAL_SERVER_ERROR = 500
NOT_IMPLEMENTED = 501
BAD_GATEWAY = 502
SERVICE_UNAVAILABLE = 503
GATEWAY_TIMEOUT = 504
RTSP_VERSION_NOT_SUPPORTED = 505
OPTION_NOT_SUPPORTED = 551
RESPONSES = {CONTINUE: 'Continue',
 OK: 'OK',
 CREATED: 'Created',
 LOW_STORAGE: 'Low on Storage Space',
 MULTIPLE_CHOICE: 'Multiple Choices',
 MOVED_PERMANENTLY: 'Moved Permanently',
 MOVED_TEMPORARILY: 'Moved Temporarily',
 SEE_OTHER: 'See Other',
 NOT_MODIFIED: 'Not Modified',
 USE_PROXY: 'Use Proxy',
 BAD_REQUEST: 'Bad Request',
 UNAUTHORIZED: 'Unauthorized',
 PAYMENT_REQUIRED: 'Payment Required',
 FORBIDDEN: 'Forbidden',
 NOT_FOUND: 'Not Found',
 NOT_ALLOWED: 'Method Not Allowed',
 NOT_ACCEPTABLE: 'Not Acceptable',
 PROXY_AUTH_REQUIRED: 'Proxy Authentication Required',
 REQUEST_TIMEOUT: 'Request Time-out',
 GONE: 'Gone',
 LENGTH_REQUIRED: 'Length Required',
 PRECONDITION_FAILED: 'Precondition Failed',
 REQUEST_ENTITY_TOO_LARGE: 'Request Entity Too Large',
 REQUEST_URI_TOO_LONG: 'Request-URI Too Large',
 UNSUPPORTED_MEDIA_TYPE: 'Unsupported Media Type',
 PARAMETER_NOT_UNDERSTOOD: 'Parameter Not Understood',
 CONFERENCE_NOT_FOUND: 'Conference Not Found',
 NOT_ENOUGH_BANDWIDTH: 'Not Enough Bandwidth',
 SESSION_NOT_FOUND: 'Session Not Found',
 METHOD_INVALID_STATE: 'Method Not Valid In This State',
 HEADER_FIELD_INVALID: 'Header Field Not Valid for Resource',
 INVALID_RANGE: 'Invalid Range',
 PARAMETER_READ_ONLY: 'Parameter is Read-Only',
 AGGREGATE_NOT_ALLOWED: 'Aggregate operation not allowed',
 AGGREGATE_ONLY_ALLOWED: 'Only aggregate operation allowed',
 UNSUPPORTED_TRANSPORT: 'Unsupported transport',
 DESTINATION_UNREACHABLE: 'Destination unreachable',
 INTERNAL_SERVER_ERROR: 'Internal Server Error',
 NOT_IMPLEMENTED: 'Not Implemented',
 BAD_GATEWAY: 'Bad Gateway',
 SERVICE_UNAVAILABLE: 'Service Unavailable',
 GATEWAY_TIMEOUT: 'Gateway Time-out',
 RTSP_VERSION_NOT_SUPPORTED: 'RTSP Version not supported',
 OPTION_NOT_SUPPORTED: 'Option not supported'}

class RTSPError(Exception):
    """An exception with the RTSP status code and a str as arguments"""
    pass


class RTSPRequest(http.Request):
    code = OK
    code_message = RESPONSES[OK]
    host = None
    port = None

    def delHeader(self, key):
        if key.lower() in self.headers.keys():
            del self.headers[key.lower()]

    def setResponseCode(self, code, message = None):
        """
        Set the RTSP response code.
        """
        self.code = code
        if message:
            self.code_message = message
        else:
            self.code_message = RESPONSES.get(code, 'Unknown Status')

    def process(self):
        if self.clientproto != SERVER_PROTOCOL:
            e = ErrorResource(BAD_REQUEST)
            self.render(e)
            return
        first = '%s %s %s' % (self.method, self.path, SERVER_PROTOCOL)
        lines = []
        for key, value in self.received_headers.items():
            lines.append('%s: %s' % (key, value))

        site = self.channel.site
        ip = self.getClientIP()
        site.logRequest(ip, first, lines)
        if not self._processPath():
            return
        try:
            resrc = site.resource
            try:
                self.render(resrc)
            except server.UnsupportedMethod:
                e = ErrorResource(OPTION_NOT_SUPPORTED)
                self.setHeader('Allow', ','.join(resrc.allowedMethods))
                self.render(e)
            except RTSPError as e:
                er = ErrorResource(e.args[0])
                self.render(er)

        except Exception as e:
            print 'failed to process %s:' % (lines and lines[0] or '[No headers]')
            print e

    def _processPath(self):
        self.prepath = []
        if self.path == '*':
            return True
        matcher = re.compile('rtspu?://([^/]*)')
        m = matcher.match(self.path)
        hostport = None
        if m:
            hostport = m.expand('\\1')
        if not hostport:
            print 'Absolute rtsp URL required: %s' % self.path
            self.render(ErrorResource(BAD_REQUEST, 'Malformed Request-URI %s' % self.path))
            return False
        rest = self.path.split(hostport)[1]
        self.host = hostport
        if ':' in hostport:
            chunks = hostport.split(':')
            self.host = chunks[0]
            self.port = int(chunks[1])
        self.postpath = map(unquote, rest.split('/'))
        return True

    def _error(self, code, *lines):
        self.setResponseCode(code)
        self.setHeader('content-type', 'text/plain')
        body = '\n'.join(lines)
        return body

    def render(self, resrc):
        result = resrc.render(self)
        self._renderCallback(result, resrc)

    def _renderErrback(self, failure, resrc):
        body = self._error(INTERNAL_SERVER_ERROR, 'Request failed: %r' % failure)
        self.setHeader('Content-Length', str(len(body)))
        lines = []
        for key, value in self.headers.items():
            lines.append('%s: %s' % (key, value))

        self.channel.site.logReply(self.code, self.code_message, lines, body)
        self.write(body)
        self.finish()

    def _renderCallback(self, result, resrc):
        body = result
        if body is None or type(body) is not types.StringType:
            print 'request did not return a string'
        else:
            self.setHeader('Content-Length', str(len(body)))
        lines = []
        for key, value in self.headers.items():
            lines.append('%s: %s' % (key, value))

        if body:
            self.write(body)
        self.finish()


class RTSPChannel(http.HTTPChannel):
    requestFactory = RTSPRequest

    def checkPersistence(self, request, version):
        if version == SERVER_PROTOCOL:
            return 1
        print 'version %s not handled' % version
        return 0


class RTSPSite(server.Site):
    """
    I am a ServerFactory that can be used in
    L{twisted.internet.interfaces.IReactorTCP}'s .listenTCP
    Create me with an L{RTSPResource} object.
    """
    protocol = RTSPChannel
    requestFactory = RTSPRequest

    def logRequest(self, ip, requestLine, headerLines):
        pass

    def logReply(self, code, message, headerLines, body):
        pass


class RTSPResource(resource.Resource):
    """
    I am a base class for all RTSP Resource classes.
    
    @type allowedMethods: tuple
    @ivar allowedMethods: a tuple of allowed methods that can be invoked
                          on this resource.
    """
    allowedMethods = ['ANNOUNCE',
     'SETUP',
     'RECORD',
     'PAUSE',
     'FLUSH',
     'TEARDOWN',
     'OPTIONS',
     'GET_PARAMETER',
     'SET_PARAMETER']

    def getChild(self, path, request):
        return NoResource()
        print 'RTSPResource.getChild(%r, %s, <request>), pre %r, post %r' % (self,
         path,
         request.prepath,
         request.postpath)
        res = resource.Resource.getChild(self, path, request)
        print 'RTSPResource.getChild(%r, %s, <request>) returns %r' % (self, path, res)
        return res

    def getChildWithDefault(self, path, request):
        print 'RTSPResource.getChildWithDefault(%r, %s, <request>), pre %r, post %r' % (self,
         path,
         request.prepath,
         request.postpath)
        print 'children: %r' % self.children.keys()
        res = resource.Resource.getChildWithDefault(self, path, request)
        print 'RTSPResource.getChildWithDefault(%r, %s, <request>) returns %r' % (self, path, res)
        return res

    def noputChild(self, path, r):
        print 'RTSPResource.putChild(%r, %s, %r)' % (self, path, r)
        return resource.Resource.putChild(self, path, r)

    def render_startCSeqDate(self, request, method):
        """
        Set CSeq and Date on response to given request.
        This should be done even for errors.
        """
        cseq = request.getHeader('CSeq')
        if cseq == None:
            cseq = 0
        request.setHeader('CSeq', cseq)
        request.setHeader('Date', http.datetimeToString())

    def render_start(self, request, method):
        ip = request.getClientIP()
        print 'RTSPResource.render_start(): client from %s requests %s' % (ip, method)
        print 'RTSPResource.render_start(): uri %r' % request.path
        self.render_startCSeqDate(request, method)
        request.setHeader('Server', SERVER_STRING)
        request.delHeader('Content-Type')
        request.setHeader('Last-Modified', http.datetimeToString())
        request.setHeader('Cache-Control', 'must-revalidate')
        if 'Real' in request.received_headers.get('user-agent', ''):
            print 'Detected Real client, sending specific headers'
            request.setHeader('Public', 'OPTIONS, DESCRIBE, ANNOUNCE, PLAY, SETUP, TEARDOWN')
            request.setHeader('RealChallenge1', '28d49444034696e1d523f2819b8dcf4c')

    def render_GET(self, request):
        raise NotImplementedError


class ErrorResource(RTSPResource):

    def __init__(self, code, *lines):
        resource.Resource.__init__(self)
        self.code = code
        self.body = ''
        if lines != (None,):
            self.body = '\n'.join(lines) + '\n\n'
        if not hasattr(self, 'method'):
            self.method = 'GET'

    def render(self, request):
        request.clientproto = SERVER_PROTOCOL
        self.render_startCSeqDate(request, request.method)
        request.setResponseCode(self.code)
        if self.body:
            request.setHeader('content-type', 'text/plain')
        return self.body

    def render_GET(self, request):
        raise NotImplementedError

    def getChild(self, chname, request):
        return self


class NoResource(ErrorResource):

    def __init__(self, message = None):
        ErrorResource.__init__(self, NOT_FOUND, message)
