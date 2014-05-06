# 2013.05.22 08:34:42 UTC
#Embedded file name: /usr/lib/enigma2/python/Plugins/Extensions/IniAirPlayer/protocol_handler.py
import appletv
import lib.biplist
from twisted.web.resource import Resource
from twisted.internet import reactor
from httputil import HTTPHeaders
from Components.config import config
from Components.Network import iNetwork
from websocket import WebSocketSite, WebSocketHandler
import os.path
from Tools import Notifications
from Screens.MessageBox import MessageBox
from ctypes import *

class AirplayProtocolHandler(object):

    def __init__(self, port, media_backend):
        self._http_server = None
        self._media_backend = media_backend
        self._port = port
        self.reverseRequest = None
        self.sessionID = 'dummy'
        self._media_backend.setUpdateEventInfoFunc(self.sendEventInfo)
        self.reverseHandler = None
        self.event = None

    def start(self):
        try:
            root = Resource()
            root.putChild('play', PlayHandler(self._media_backend, self))
            root.putChild('scrub', ScrubHandler(self._media_backend, self))
            root.putChild('rate', RateHandler(self._media_backend, self))
            root.putChild('photo', PhotoHandler(self._media_backend, self))
            root.putChild('authorize', AuthorizeHandler(self._media_backend, self))
            root.putChild('server-info', ServerInfoHandler(self._media_backend, self))
            root.putChild('slideshow-features', SlideshowFeaturesHandler(self._media_backend, self))
            root.putChild('playback-info', PlaybackInfoHandler(self._media_backend, self))
            root.putChild('stop', StopHandler(self._media_backend, self))
            root.putChild('setProterpy', SetProterpyHandler(self._media_backend, self))
            root.putChild('getProterpy', GetProterpyHandler(self._media_backend, self))
            root.putChild('premium', PremiumHandler(self._media_backend, self))
            self.reverseHandler = ReverseHandler()
            site = WebSocketSite(root)
            site.addHandler('/reverse', self.reverseHandler)
            port = self._port
            reactor.listenTCP(port, site, interface='0.0.0.0')
        except Exception as ex:
            print ('Exception(Can be ignored): ' + str(ex), __name__, 'W')

    def sendEventInfo(self, event):
        print '[AirPlayer] REVERSE /event - event=%s' % event
        try:
            if self.reverseHandler is not None and self.reverseHandler.transport is not None:
                header_template = 'POST /event HTTP/1.1\r\nContent-Type: text/x-apple-plist+xml\r\nContent-Length: %s\r\nx-apple-session-id: %s\r\n'
                xml = appletv.EVENT_INFO % event
                header = header_template % (len(xml), self.sessionID)
                req = '%s\r\n%s\r\n' % (header, xml)
                self.reverseHandler.transport.write(req)
        except Exception as ex:
            print ('Exception(Can be ignored): ' + str(ex), __name__, 'W')


class ReverseHandler(WebSocketHandler):

    def frameReceived(self, frame):
        print '[AirPlayer] REVERSE frame : %s' % frame

    def connectionLost(self, reason):
        """
        Callback called when the underlying transport has detected that the
        connection is closed.
        """
        print '[AirPlayer] REVERSE connection lost: %s' % reason


class BaseHandler(Resource):
    """
    Base request handler, all other handlers should inherit from this class.
    
    Provides some logging and media backend assignment.
    """

    def __init__(self, media_backend, protocolHandler):
        self._media_backend = media_backend
        self._protocolHandler = protocolHandler
        self._session_id = None

    def render(self, request):
        self._session_id = request.getHeader('x-apple-session-id')
        if self._session_id == None:
            self._session_id = 'dummy'
        else:
            self._protocolHandler.sessionID = self._session_id
        request.responseHeaders.removeHeader('Content-Type')
        request.responseHeaders.removeHeader('Server')
        Resource.render(self, request)
        return 1


class PlayHandler(BaseHandler):
    """
    Handler for /play requests.
    
    Contains a header like format in the request body which should contain a
    Content-Location and optionally a Start-Position.
    """

    def render_POST(self, request):
        print '[AirPlayer] PlayHandler POST'
        if request.getHeader('Content-Type') == 'application/x-apple-binary-plist':
            body = lib.biplist.readPlistFromString(request.content.getvalue())
        else:
            body = HTTPHeaders.parse(request.content.getvalue())
        print '[AirPlayer] body:', body
        if 'Content-Location' in body:
            url = body['Content-Location']
            print '[AirPlayer] Playing ', url
            start = float(0.0)
            if 'Start-Position' in body:
                try:
                    str_pos = body['Start-Position']
                    start = float(str_pos)
                    print '[AirPlayer] start-position supplied: ', start, '%'
                except ValueError:
                    print '[AirPlayer] Invalid start-position supplied: ', str_pos
                    start = float(0.0)

            else:
                start = float(0)
            self._media_backend.play_movie(url, start)
        request.setHeader('content-length', 0)
        request.finish()
        return 1


class PremiumHandler(BaseHandler):
    """
    Handler for /premium requests.
    
    Contains a header like format in the request body which should contain a
    Content-Location and optionally a Start-Position.
    """

    def render_GET(self, request):
        self.render_POST(request)

    def getStatusText(self):
        try:
            self.libairtunes = cdll.LoadLibrary('/usr/lib/enigma2/python/Plugins/Extensions/IniAirPlayer/libairtunes.so.0')
            print '[AirPlayer] loading lib done'
            response = create_string_buffer(1024)
            if self.libairtunes.checkValidation(config.plugins.airplayer.validationKey.value, response) < 0:
                return 'You do not have a valid Premium Key<br>' + response.value
            print '[AirPlayer] valid premium user'
            return 'You are a Premium-user<br>' + response.value
        except Exception as e:
            print '[AirPlayMoviePlayer] loading lib failed'
            print e
            return 'Your Premium-Status could not be checked because:<br>' + e

    def render_POST(self, request):
        print '[AirPlayer] PremiumHandler POST'
        TEMPLATE = '<html>            <head>                <meta name="title" content="AirPlayer E2">            </head>                <body>                    <h2>Premium-Key</h2>                    <form method="post"><input type="text" name="key" size="40" value="%s"><input type="submit" value="Save and check"></form>                    <h2>Status</h2>                    %s                </body>            </html>'
        if 'key' in request.args:
            try:
                config.plugins.airplayer.premiuimKey.value = request.args['key'][0]
                config.save()
                self._media_backend.updater.checkPremiumValidation()
            except Exception as e:
                print '[AirPlayMoviePlayer] loading lib failed'
                print e

        statusText = self.getStatusText()
        request.write(TEMPLATE % (config.plugins.airplayer.premiuimKey.value, statusText))
        request.finish()
        return 1


class ScrubHandler(BaseHandler):
    """
    Handler for /scrub requests.
    
    Used to perform seeking (POST request) and to retrieve current player position (GET request).
    """

    def render_GET(self, request):
        """
        Will return None, None if no media is playing or an error occures.
        """
        position, duration, bufferPosition = self._media_backend.get_player_position()
        if not position:
            duration = position = 0
        body = 'duration: %f\r\nposition: %f\r\n' % (duration, position)
        request.setHeader('content-length', len(body))
        request.write(body)
        request.finish()
        return 1

    def render_POST(self, request):
        """
        Immediately finish this request, no need for the client to wait for
        backend communication.
        """
        if 'position' in request.args:
            try:
                str_pos = request.args['position'][0]
                position = float(str_pos)
            except ValueError:
                print '[AirPlayer] Invalid scrub value supplied: ', str_pos
            else:
                self._media_backend.set_player_position(position)

        request.setHeader('content-length', 0)
        request.finish()
        return 1


class RateHandler(BaseHandler):
    """
    Handler for /rate requests.
    
    The rate command is used to play/pause media.
    A value argument should be supplied which indicates media should be played or paused.
    
    0.000000 => pause
    1.000000 => play
    """

    def render_POST(self, request):
        print '[AirPlayer] RateHandler POST'
        if 'value' in request.args:
            play = bool(float(request.args['value'][0]))
            position, duration, bufferPosition = self._media_backend.get_player_position()
            if position < 3.0:
                print '[AirPlayer] playback not yet started skipping play/pause '
                self._protocolHandler.sendEventInfo('playing')
            else:
                print '[AirPlayer] play? ', request.args['value'][0]
                if play:
                    self._media_backend.play()
                else:
                    self._media_backend.pause()
        request.setHeader('content-length', 0)
        request.finish()
        return 1


class PhotoHandler(BaseHandler):
    """
    Handler for /photo requests.
    
    RAW JPEG data is contained in the request body.
    """

    def render_POST(self, request):
        self.render_PUT(request)

    def render_PUT(self, request):
        print '[AirPlayer] PHOTOHandler POST'
        if request.content.read() is not None:
            request.content.seek(0)
            file(config.plugins.airplayer.path.value + '/pic.jpg', 'wb').write(request.content.read())
            if os.path.isfile(config.plugins.airplayer.path.value + '/pic.jpg'):
                self._media_backend.show_picture(request.content.read())
            else:
                Notifications.AddNotification(MessageBox, _('Your Photo could not be saved to %s ! Please change the Path in the Settings to a writable location!') % config.plugins.airplayer.path.value, type=MessageBox.TYPE_INFO, timeout=10)
        request.setHeader('content-length', 0)
        request.finish()


class AuthorizeHandler(BaseHandler):
    """
    Handler for /authorize requests.
    
    This is used to handle DRM authorization.
    We currently don't support DRM protected media.
    """

    def render_GET(self, request):
        print '[AirPlayer] AuthorizeHandler GET'
        request.setHeader('content-length', 0)
        request.finish()
        return 1

    def render_POST(self, request):
        print '[AirPlayer] AuthorizeHandler POST'
        request.setHeader('content-length', 0)
        request.finish()
        return 1


class StopHandler(BaseHandler):
    """
    Handler for /stop requests.
    
    Sent when media playback should be stopped.
    """

    def render_POST(self, request):
        print '[AirPlayer] StopHandler POST'
        self._media_backend.stop_playing()
        request.setHeader('content-length', 0)
        request.finish()
        print '[AirPlayer] StopHandler done'
        return 1


class ServerInfoHandler(BaseHandler):
    """
    Handler for /server-info requests.
    
    Usage currently unknown.
    Available from IOS 4.3.
    """

    def render_GET(self, request):
        mac = iNetwork.getAdapterAttribute(config.plugins.airplayer.interface.value, 'mac')
        if mac is None:
            mac = '01:02:03:04:05:06'
        mac = mac.upper()
        response = appletv.SERVER_INFO % mac
        request.setHeader('Content-Type', 'text/x-apple-plist+xml')
        request.setHeader('content-length', len(response))
        request.write(response)
        request.finish()
        return 1


class SlideshowFeaturesHandler(BaseHandler):
    """
    Handler for /slideshow-features requests.
    
    Usage currently unknown.
    Available from IOS 4.3.
    """

    def render_GET(self, request):
        """
        I think slideshow effects should be implemented by the Airplay device.
        The currently supported media backends do not support this.
        
        We'll just ignore this request, that'll enable the simple slideshow without effects.
        """
        request.setHeader('content-length', 0)
        request.finish()
        return 1


class PlaybackInfoHandler(BaseHandler):
    """
    Handler for /playback-info requests.
    """

    def render_GET(self, request):
        playing = self._media_backend.is_playing()
        position, duration, bufferPosition = self._media_backend.get_player_position()
        if not duration and self._media_backend.MovieWindow is not None and not self._media_backend.MovieWindow.endReached:
            position = duration = 0
            body = appletv.PLAYBACK_INFO_NOT_READY
        else:
            position = round(float(position), 2)
            duration = round(float(duration), 2)
            body = appletv.PLAYBACK_INFO % (duration,
             bufferPosition,
             position,
             int(playing),
             duration)
        request.setHeader('Content-Type', 'text/x-apple-plist+xml')
        request.setHeader('content-length', len(body))
        request.write(body)
        request.finish()
        return 1


class SetProterpyHandler(BaseHandler):

    def render_GET(self, request):
        request.setHeader('content-length', 0)
        request.finish()
        return 1

    def render_POST(self, request):
        request.setHeader('content-length', 0)
        request.finish()
        return 1


class GetProterpyHandler(BaseHandler):

    def render_GET(self, request):
        request.setHeader('content-length', 0)
        request.finish()
        return 1

    def render_POST(self, request):
        request.setHeader('content-length', 0)
        request.finish()
        return 1
