# 2013.05.22 08:35:32 UTC
#Embedded file name: /usr/lib/enigma2/python/Plugins/Extensions/IniAirPlayer/websocket.py
"""
WebSocket server protocol.

See U{http://tools.ietf.org/html/draft-hixie-thewebsocketprotocol} for the
current version of the specification.

@since: 10.1
"""
from twisted.web.http import datetimeToString
from twisted.web.server import Request, Site, version, unquote

class WebSocketRequest(Request):
    """
    A general purpose L{Request} supporting connection upgrade for WebSocket.
    """

    def process(self):
        if self.requestHeaders.getRawHeaders('Upgrade') == ['PTTH/1.0'] and self.requestHeaders.getRawHeaders('Connection') == ['Upgrade']:
            return self.processWebSocket()
        else:
            return Request.process(self)

    def processWebSocket(self):
        """
        Process a specific web socket request.
        """
        self.site = self.channel.site
        self.setHeader('server', version)
        self.setHeader('date', datetimeToString())
        self.prepath = []
        self.postpath = map(unquote, self.path[1:].split('/'))
        self.renderWebSocket()

    def _checkClientHandshake(self):
        """
        Verify client handshake, closing the connection in case of problem.
        
        @return: C{None} if a problem was detected, or a tuple of I{Origin}
            header, I{Host} header, I{WebSocket-Protocol} header, and
            C{WebSocketHandler} instance. The I{WebSocket-Protocol} header will
            be C{None} if not specified by the client.
        """

        def finish():
            self.channel.transport.loseConnection()

        if self.queued:
            return finish()
        handler = self.site.handlers.get(self.uri)
        if not handler:
            return finish()
        transport = WebSocketTransport(self)
        handler.registerTransport(transport)
        transport._attachHandler(handler)
        return handler

    def renderWebSocket(self):
        """
        Render a WebSocket request.
        
        If the request is not identified with a proper WebSocket handshake, the
        connection will be closed. Otherwise, the response to the handshake is
        sent and a C{WebSocketHandler} is created to handle the request.
        """
        print 'renderWebSocket'
        check = self._checkClientHandshake()
        if check is None:
            return
        handler = check
        self.startedWriting = True
        handshake = ['HTTP/1.1 101 Switching Protocols',
         'Date: %s' % datetimeToString(),
         'Upgrade: PTTH/1.0',
         'Connection: Upgrade']
        for header in handshake:
            self.write('%s\r\n' % header)

        self.write('\r\n')
        self.channel.setRawMode()
        self.channel._transferDecoder = WebSocketFrameDecoder(self, handler)


class WebSocketSite(Site):
    """
    @ivar handlers: a C{dict} of names to L{WebSocketHandler} factories.
    @type handlers: C{dict}
    @ivar supportedProtocols: a C{list} of supported I{WebSocket-Protocol}
        values. If a value is passed at handshake and doesn't figure in this
        list, the connection is closed.
    @type supportedProtocols: C{list}
    """
    requestFactory = WebSocketRequest

    def __init__(self, resource, logPath = None, timeout = 43200, supportedProtocols = None):
        Site.__init__(self, resource, logPath, timeout)
        self.handlers = {}
        self.supportedProtocols = supportedProtocols or []

    def addHandler(self, name, handlerFactory):
        """
        Add or override a handler for the given C{name}.
        
        @param name: the resource name to be handled.
        @type name: C{str}
        @param handlerFactory: a C{WebSocketHandler} factory.
        @type handlerFactory: C{callable}
        """
        if not name.startswith('/'):
            raise ValueError('Invalid resource name.')
        self.handlers[name] = handlerFactory


class WebSocketTransport(object):
    """
    Transport abstraction over WebSocket, providing classic Twisted methods and
    callbacks.
    """
    _handler = None

    def __init__(self, request):
        self._request = request
        self._request.notifyFinish().addErrback(self._connectionLost)

    def _attachHandler(self, handler):
        """
        Attach the given L{WebSocketHandler} to this transport.
        """
        self._handler = handler

    def _connectionLost(self, reason):
        """
        Forward connection lost event to the L{WebSocketHandler}.
        """
        self._handler.connectionLost(reason)

    def write(self, frame):
        """
        Send the given frame to the connected client.
        
        @param frame: a I{UTF-8} encoded C{str} to send to the client.
        @type frame: C{str}
        """
        self._request.write(frame)

    def loseConnection(self):
        """
        Close the connection.
        """
        self._request.transport.loseConnection()


class WebSocketHandler(object):
    """
    Base class for handling WebSocket connections. It mainly provides a
    transport to send frames, and a callback called when frame are received,
    C{frameReceived}.
    
    @ivar transport: a C{WebSocketTransport} instance.
    @type: L{WebSocketTransport}
    """

    def __init__(self):
        """
        Create the handler, with the given transport
        """
        pass

    def registerTransport(self, transport):
        self.transport = transport

    def frameReceived(self, frame):
        """
        Called when a frame is received.
        
        @param frame: a I{UTF-8} encoded C{str} sent by the client.
        @type frame: C{str}
        """
        pass

    def frameLengthExceeded(self):
        """
        Called when too big a frame is received. The default behavior is to
        close the connection, but it can be customized to do something else.
        """
        self.transport.loseConnection()

    def connectionLost(self, reason):
        """
        Callback called when the underlying transport has detected that the
        connection is closed.
        """
        pass


class WebSocketFrameDecoder(object):
    """
    Decode WebSocket frames and pass them to the attached C{WebSocketHandler}
    instance.
    
    @ivar MAX_LENGTH: maximum len of the frame allowed, before calling
        C{frameLengthExceeded} on the handler.
    @type MAX_LENGTH: C{int}
    @ivar request: C{Request} instance.
    @type request: L{twisted.web.server.Request}
    @ivar handler: L{WebSocketHandler} instance handling the request.
    @type handler: L{WebSocketHandler}
    @ivar _data: C{list} of C{str} buffering the received data.
    @type _data: C{list} of C{str}
    @ivar _currentFrameLength: length of the current handled frame, plus the
        additional leading byte.
    @type _currentFrameLength: C{int}
    """
    MAX_LENGTH = 16384

    def __init__(self, request, handler):
        self.request = request
        self.handler = handler
        self._data = []
        self._currentFrameLength = 0

    def dataReceived(self, data):
        """
        Parse data to read WebSocket frames.
        
        @param data: data received over the WebSocket connection.
        @type data: C{str}
        """
        if not data:
            return
        while True:
            endIndex = data.find('\xff')
            if endIndex != -1:
                self._currentFrameLength += endIndex
                if self._currentFrameLength > self.MAX_LENGTH:
                    self.handler.frameLengthExceeded()
                    break
                self._currentFrameLength = 0
                frame = ''.join(self._data) + data[:endIndex]
                self._data[:] = []
                if frame[0] != '\x00':
                    self.request.transport.loseConnection()
                    break
                self.handler.frameReceived(frame[1:])
                data = data[endIndex + 1:]
                if not data:
                    break
                if data[0] != '\x00':
                    self.request.transport.loseConnection()
                    break
            else:
                self._currentFrameLength += len(data)
                if self._currentFrameLength > self.MAX_LENGTH + 1:
                    self.handler.frameLengthExceeded()
                else:
                    self._data.append(data)
                break


___all__ = ['WebSocketHandler', 'WebSocketSite']